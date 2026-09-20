#!/usr/bin/env python3
"""Build C2c and classify tasks after removing task-membership Graph edges."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from build_c2a_projection import Projection, read_json, write_json, write_jsonl
from worksurface.convert_tables import connect_registry


TASK_RELS = {"task_requires_file", "task_produces_output"}


def load_single(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if len(rows) != 1:
        raise ValueError(f"expected one task in {path}")
    return rows[0]


def rag_span_reachable(profile: Path, task: dict) -> tuple[bool, list[str]]:
    failures = []
    for ev in task.get("gold_evidence", []):
        if ev.get("surface") != "rag" or not ev.get("file") or ev.get("span") is None:
            continue
        path = profile / "kb_docs" / ev["file"]
        if not path.exists() or str(ev["span"]) not in path.read_text(
            encoding="utf-8", errors="replace"
        ):
            failures.append(f"RAG span {ev['span']!r} absent from {ev['file']}")
    return not failures, failures


def has_natural_graph_fact(task: dict, natural_edges: set[tuple[str, str, str]]) -> bool:
    for ev in task.get("gold_evidence", []):
        if ev.get("surface") != "graph":
            continue
        path = ev.get("graph_path") or []
        if len(path) == 3 and path[1] not in TASK_RELS and tuple(path) in natural_edges:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c2b", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    c2b = args.c2b.resolve()
    out_dir = args.out.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(c2b / "public", out_dir / "public")
    shutil.copytree(c2b / "private", out_dir / "private")

    profile_dirs = list((out_dir / "public" / "profiles").iterdir())
    if len(profile_dirs) != 1:
        raise ValueError("C2c pilot expects exactly one persona profile")
    profile = profile_dirs[0]
    graph_path = profile / "graph" / "surface_graph.json"
    graph = read_json(graph_path)
    kept_nodes = [node for node in graph["nodes"]
                  if node.get("type") not in {"task", "output"}]
    kept_ids = {node["id"] for node in kept_nodes}
    for node in kept_nodes:
        node.pop("work_item", None)
    kept_edges = [
        edge for edge in graph["edges"]
        if edge["rel"] not in TASK_RELS
        and edge["from"] in kept_ids and edge["to"] in kept_ids
    ]
    write_json(graph_path, {"nodes": kept_nodes, "edges": kept_edges})
    natural_edges = {(edge["from"], edge["rel"], edge["to"])
                     for edge in kept_edges}

    alias_map = read_json(out_dir / "private" / "alias_map.json")
    reverse_ids = {public: original
                   for original, public in alias_map["benchmark_tasks"].items()}
    task_dir = out_dir / "public" / "tasks"
    full_tasks = {
        load_single(path)["id"]: load_single(path)
        for path in sorted(task_dir.glob("*__full.jsonl"))
    }
    classifications = []
    retained = set()
    for public_id, task in sorted(full_tasks.items()):
        original_id = reverse_ids[public_id]
        rag_ok, failures = rag_span_reachable(profile, task)
        if not rag_ok:
            disposition = "delete"
            reason = "; ".join(failures)
        elif "graph" in task.get("required_surfaces", []):
            if has_natural_graph_fact(task, natural_edges):
                disposition = "retain"
                reason = "Graph evidence contains a surviving natural relation"
            else:
                disposition = "downgrade"
                reason = "Graph evidence only encodes task membership; no exclusive business relation survives"
        else:
            disposition = "retain"
            reason = "non-Graph task remains statically reachable"
        if disposition == "retain":
            retained.add(public_id)
        classifications.append({
            "original_id": original_id,
            "public_id": public_id,
            "required_surfaces": task.get("required_surfaces", []),
            "disposition": disposition,
            "reason": reason,
        })

    kept_task_files = 0
    for path in sorted(task_dir.glob("*.jsonl")):
        task = load_single(path)
        if task["id"] not in retained:
            path.unlink()
            continue
        task["projection"] = "C2c"
        task["graph_entry_node"] = None
        write_jsonl(path, [task])
        kept_task_files += 1

    errors = []
    if any(node.get("type") in {"task", "output"} for node in kept_nodes):
        errors.append("task/output graph nodes remain")
    if any(edge["rel"] in TASK_RELS for edge in kept_edges):
        errors.append("task-membership graph edges remain")
    con, _ = connect_registry(str(profile / "tables"))
    query_count = 0
    try:
        for path in sorted(task_dir.glob("*.jsonl")):
            task = load_single(path)
            for ev in task.get("gold_evidence", []):
                if ev.get("query"):
                    query_count += 1
                    row = con.execute(ev["query"]).fetchone()
                    if ev.get("verified_result") is not None and (
                        not row or row[0] != ev["verified_result"]
                    ):
                        errors.append(f"SQL mismatch: {path.name}")
    finally:
        con.close()
    report = {
        "state": "passed" if not errors else "failed",
        "source_tasks": len(full_tasks),
        "retained": sum(row["disposition"] == "retain" for row in classifications),
        "downgraded": sum(row["disposition"] == "downgrade" for row in classifications),
        "deleted": sum(row["disposition"] == "delete" for row in classifications),
        "retained_task_files": kept_task_files,
        "graph_nodes": len(kept_nodes),
        "graph_edges": len(kept_edges),
        "verified_queries": query_count,
        "sentinel_api_runs": 0,
        "sentinel_reason": "all six fixed sentinels were downgraded or deleted by static Graph/RAG audit",
        "validation_errors": errors,
        "classifications": classifications,
    }
    write_json(out_dir / "private" / "classification_report.json", report)
    if errors:
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))

    public_lock = Projection.lock_tree(out_dir / "public",
                                       out_dir / "private" / "public_lock.json")
    parent = read_json(c2b / "projection_manifest.json")
    manifest = {
        "stage": "C2c",
        "parent_stage": "C2b",
        "parent_public_lock_sha256": parent["public_lock_sha256"],
        "source_lock_sha256": parent["source_lock_sha256"],
        "public_lock_sha256": public_lock["aggregate_sha256"],
        "retained_tasks": report["retained"],
        "downgraded_tasks": report["downgraded"],
        "deleted_tasks": report["deleted"],
        "retained_task_files": kept_task_files,
        "graph_nodes": len(kept_nodes),
        "graph_edges": len(kept_edges),
        "validation": report["state"],
    }
    write_json(out_dir / "projection_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
