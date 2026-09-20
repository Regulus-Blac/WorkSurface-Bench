#!/usr/bin/env python3
"""Build C2b by tightening C2a's public RAG/Table contracts."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq

from build_c2a_projection import Projection, read_json, write_json, write_jsonl
from worksurface.convert_tables import connect_registry


PRIVATE_COLUMNS = {"_source_file", "_source_sheet", "_source_row_id"}


def rewrite_tasks(public_tasks: Path) -> int:
    count = 0
    for path in sorted(public_tasks.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        for task in rows:
            task["projection"] = "C2b"
            task["tool_contract"] = "c2b"
        write_jsonl(path, rows)
        count += len(rows)
    return count


def rewrite_kb_registry(profile: Path) -> int:
    path = profile / "kb_docs" / "registry.json"
    registry = read_json(path)
    for meta in registry.values():
        meta["artifact_id"] = meta.pop("source_file")
    write_json(path, registry)
    return len(registry)


def rewrite_tables(profile: Path) -> int:
    tables_dir = profile / "tables"
    registry_path = tables_dir / "registry.json"
    registry = read_json(registry_path)
    for meta in registry.values():
        parquet_path = tables_dir / meta["parquet"]
        table = pq.read_table(parquet_path)
        keep = [name for name in table.column_names if name not in PRIVATE_COLUMNS]
        pq.write_table(table.select(keep), parquet_path)
        meta["artifact_id"] = meta.pop("source_file")
        for key in ("sheet", "rows"):
            meta.pop(key, None)
    write_json(registry_path, registry)
    return len(registry)


def validate(out_dir: Path, profile_slug: str) -> dict:
    public = out_dir / "public"
    profile = public / "profiles" / profile_slug
    kb = read_json(profile / "kb_docs" / "registry.json")
    tables = read_json(profile / "tables" / "registry.json")
    errors = []
    for doc, meta in kb.items():
        if "source_file" in meta:
            errors.append(f"KB registry exposes source_file: {doc}")
        if not meta.get("artifact_id"):
            errors.append(f"KB registry lacks public artifact_id: {doc}")
    for view, meta in tables.items():
        leaked = {"source_file", "sheet", "rows"} & set(meta)
        if leaked:
            errors.append(f"table registry exposes {sorted(leaked)}: {view}")
        if not meta.get("artifact_id"):
            errors.append(f"table registry lacks public artifact_id: {view}")
        columns = set(pq.read_schema(profile / "tables" / meta["parquet"]).names)
        private = columns & PRIVATE_COLUMNS
        if private:
            errors.append(f"table parquet exposes {sorted(private)}: {view}")

    con, views = connect_registry(str(profile / "tables"))
    query_count = 0
    task_count = 0
    try:
        for path in sorted((public / "tasks").glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                task = json.loads(line)
                task_count += 1
                if task.get("tool_contract") != "c2b":
                    errors.append(f"task missing c2b contract: {path.name}")
                for ev in task.get("gold_evidence", []):
                    query = ev.get("query")
                    if not query:
                        continue
                    query_count += 1
                    try:
                        row = con.execute(query).fetchone()
                        if ev.get("verified_result") is not None and (
                            not row or row[0] != ev["verified_result"]
                        ):
                            errors.append(f"SQL result mismatch: {path.name}")
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"SQL failed: {path.name}: {exc}")
    finally:
        con.close()
    report = {
        "state": "passed" if not errors else "failed",
        "tasks": task_count,
        "kb_docs": len(kb),
        "table_views": len(views),
        "verified_queries": query_count,
        "validation_errors": errors,
    }
    write_json(out_dir / "contract_report.json", report)
    if errors:
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c2a", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    c2a = args.c2a.resolve()
    out_dir = args.out.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(c2a / "public", out_dir / "public")
    (out_dir / "private").mkdir()
    for name in ("alias_map.json", "source_lock.json"):
        shutil.copy2(c2a / "private" / name, out_dir / "private" / name)

    profile_dirs = list((out_dir / "public" / "profiles").iterdir())
    if len(profile_dirs) != 1:
        raise ValueError("C2b pilot expects exactly one persona profile")
    profile = profile_dirs[0]
    task_count = rewrite_tasks(out_dir / "public" / "tasks")
    kb_count = rewrite_kb_registry(profile)
    table_count = rewrite_tables(profile)
    report = validate(out_dir, profile.name)
    public_lock = Projection.lock_tree(out_dir / "public",
                                       out_dir / "private" / "public_lock.json")
    parent = read_json(c2a / "projection_manifest.json")
    manifest = {
        "stage": "C2b",
        "parent_stage": "C2a",
        "parent_public_lock_sha256": parent["public_lock_sha256"],
        "source_lock_sha256": parent["source_lock_sha256"],
        "public_lock_sha256": public_lock["aggregate_sha256"],
        "tasks": task_count,
        "kb_docs": kb_count,
        "table_views": table_count,
        "verified_queries": report["verified_queries"],
        "validation": report["state"],
    }
    write_json(out_dir / "projection_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
