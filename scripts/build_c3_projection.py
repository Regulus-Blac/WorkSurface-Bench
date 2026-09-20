#!/usr/bin/env python3
"""Build the audited C3 task, mutation, negative control, and evidence DAG."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path

from build_c2a_projection import Projection, read_json, write_json, write_jsonl
from worksurface.convert_tables import connect_registry


ORIGINAL_TASK_ID = "pool_rt_0011"
MUTATION_FROM = "例如：0.2 表示 20% 的折扣，即客户支付原价的 80%。"
MUTATION_TO = "例如：0.15 表示 15% 的折扣，即客户支付原价的 85%。"


def load_single(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if len(rows) != 1:
        raise ValueError(f"expected one task in {path}")
    return rows[0]


def write_task(path: Path, task: dict, question: str, variant: str,
               profile_slug: str) -> None:
    task = copy.deepcopy(task)
    task["question"] = question
    task["projection"] = "C3"
    task["c3_variant"] = variant
    task["profile_slug"] = profile_slug
    task["graph_entry_node"] = None
    write_jsonl(path, [task])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c2c", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    c2c = args.c2c.resolve()
    out_dir = args.out.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(c2c / "public", out_dir / "public")
    shutil.copytree(c2c / "private", out_dir / "private")

    alias_map = read_json(out_dir / "private" / "alias_map.json")
    public_id = alias_map["benchmark_tasks"][ORIGINAL_TASK_ID]
    task_dir = out_dir / "public" / "tasks"
    full_path = task_dir / f"{public_id}__full.jsonl"
    rag_path = task_dir / f"{public_id}__subset.jsonl"
    table_path = task_dir / f"{public_id}__subset_table.jsonl"
    full = load_single(full_path)
    rag_only = load_single(rag_path)
    table_only = load_single(table_path)
    rag_ev = next(ev for ev in full["gold_evidence"] if ev["surface"] == "rag")
    table_ev = next(ev for ev in full["gold_evidence"] if ev["surface"] == "table")
    artifact_id = table_ev["source_file"]
    question = (
        f"Read {rag_ev['file']} and extract the decimal discount value in the "
        "explicit example sentence under its Discount section. Using the table "
        f"linked to artifact {artifact_id}, count rows whose discount equals "
        "that exact value. The normalized discount column is text: compare it "
        "to a quoted VARCHAR literal, without an implicit numeric cast or "
        "rounding. Return `<value>; <count>`."
    )
    base_slug = next((out_dir / "public" / "profiles").iterdir()).name
    write_task(full_path, full, question, "full", base_slug)
    write_task(rag_path, rag_only, question, "subset", base_slug)
    write_task(table_path, table_only, question, "subset_table", base_slug)

    mutation_slug = base_slug + "__c3_mutation"
    negative_slug = base_slug + "__c3_negative"
    base_profile = out_dir / "public" / "profiles" / base_slug
    mutation_profile = out_dir / "public" / "profiles" / mutation_slug
    negative_profile = out_dir / "public" / "profiles" / negative_slug
    shutil.copytree(base_profile, mutation_profile)
    shutil.copytree(base_profile, negative_profile)

    target_doc = mutation_profile / "kb_docs" / rag_ev["file"]
    text = target_doc.read_text(encoding="utf-8")
    if text.count(MUTATION_FROM) != 1:
        raise ValueError("expected exactly one mutation sentence")
    target_doc.write_text(text.replace(MUTATION_FROM, MUTATION_TO), encoding="utf-8")

    unrelated = next(path for path in sorted((negative_profile / "kb_docs").glob("*.md"))
                     if path.name != rag_ev["file"])
    unrelated.write_text(
        unrelated.read_text(encoding="utf-8")
        + "\n\nControl note: archive retention review completed.\n",
        encoding="utf-8",
    )

    mutation = copy.deepcopy(full)
    mutation["gold_answer"] = "0.15; 3"
    for ev in mutation["gold_evidence"]:
        if ev["surface"] == "rag":
            ev["span"] = "0.15"
            ev["claim"] = "The mutated example sentence explicitly defines 0.15."
        elif ev["surface"] == "table":
            ev["query"] = ev["query"].replace("'0.2'", "'0.15'")
            ev["verified_result"] = 3
            ev["claim"] = "The unchanged table contains three rows with discount 0.15."
    mutation_path = task_dir / f"{public_id}__mutation.jsonl"
    write_task(mutation_path, mutation, question, "mutation", mutation_slug)
    negative_path = task_dir / f"{public_id}__negative.jsonl"
    write_task(negative_path, full, question, "negative", negative_slug)

    evidence_dag = {
        "task": ORIGINAL_TASK_ID,
        "public_id": public_id,
        "answer": "format(value, count)",
        "nodes": [
            {"id": "rag.explicit_discount_value", "surface": "rag",
             "exclusive": True, "base_value": "0.2", "mutation_value": "0.15"},
            {"id": "table.discount_count", "surface": "table", "exclusive": True,
             "depends_on": ["rag.explicit_discount_value"],
             "base_value": 2, "mutation_value": 3},
            {"id": "answer", "depends_on": ["rag.explicit_discount_value",
                                               "table.discount_count"]},
        ],
        "proper_subset_oracle": {
            "rag": "value available, count unavailable",
            "table": "counts available for multiple values, selected value unavailable",
        },
        "mutation": {"from": "0.2; 2", "to": "0.15; 3"},
        "negative_control": {"change": f"append irrelevant note to {unrelated.name}",
                             "expected": "0.2; 2"},
    }
    write_json(out_dir / "private" / "evidence_dag.json", evidence_dag)

    errors = []
    for slug, expected_span, expected_count in (
        (base_slug, "0.2", 2), (mutation_slug, "0.15", 3),
        (negative_slug, "0.2", 2),
    ):
        profile = out_dir / "public" / "profiles" / slug
        doc_text = (profile / "kb_docs" / rag_ev["file"]).read_text(encoding="utf-8")
        if expected_span not in doc_text:
            errors.append(f"{slug}: expected RAG span missing")
        con, _ = connect_registry(str(profile / "tables"))
        try:
            query = table_ev["query"].replace("'0.2'", f"'{expected_span}'")
            row = con.execute(query).fetchone()
            if not row or row[0] != expected_count:
                errors.append(f"{slug}: mutation query mismatch")
        finally:
            con.close()
    if (negative_profile / "kb_docs" / rag_ev["file"]).read_bytes() != (
        base_profile / "kb_docs" / rag_ev["file"]
    ).read_bytes():
        errors.append("negative control changed the target document")
    variants = {path.stem.rsplit("__", 1)[-1] for path in task_dir.glob("*.jsonl")}
    expected_variants = {"full", "subset", "subset_table", "mutation", "negative"}
    if variants != expected_variants:
        errors.append(f"unexpected C3 variants: {sorted(variants)}")
    report = {"state": "passed" if not errors else "failed",
              "task": ORIGINAL_TASK_ID, "variants": sorted(variants),
              "validation_errors": errors}
    write_json(out_dir / "c3_validation.json", report)
    if errors:
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))

    public_lock = Projection.lock_tree(out_dir / "public",
                                       out_dir / "private" / "public_lock.json")
    parent = read_json(c2c / "projection_manifest.json")
    manifest = {
        "stage": "C3",
        "parent_stage": "C2c",
        "parent_public_lock_sha256": parent["public_lock_sha256"],
        "source_lock_sha256": parent["source_lock_sha256"],
        "public_lock_sha256": public_lock["aggregate_sha256"],
        "tasks": 1,
        "runs": 5,
        "validation": report["state"],
    }
    write_json(out_dir / "projection_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
