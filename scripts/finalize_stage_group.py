#!/usr/bin/env python3
"""Validate and checksum an arbitrary variant matrix from run_stage_matrix."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from finalize_pilot_group import (
    load_json,
    validate_run,
    write_checksums,
    write_json_atomic,
)


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    result_dir = args.result_dir.resolve()
    manifest = load_json(result_dir / "run_manifest.json")
    matrix = manifest.get("matrix", [])
    if not matrix:
        raise ValueError("run manifest has no matrix")

    rows = []
    by_variant: dict[str, list[dict]] = defaultdict(list)
    total_tokens = 0
    for item in matrix:
        stem = f"{item['public_id']}__{item['variant']}"
        task, trace, score = validate_run(result_dir / f"{stem}.run.jsonl")
        total_tokens += int(trace.get("total_tokens") or 0)
        row = {
            "original_id": item["original_id"],
            "public_id": item["public_id"],
            "variant": item["variant"],
            "task_id": task["id"],
            "allowed_surfaces": task.get("_allowed_surfaces"),
            "answer_score": score["answer"]["score"],
            "route_f1": score["route"]["f1"],
            "evidence": score["evidence"]["score"],
            "aggregate": score["aggregate"],
            "tokens": int(trace.get("total_tokens") or 0),
            "answer": trace.get("answer"),
        }
        rows.append(row)
        by_variant[item["variant"]].append(row)

    summary = {
        "state": "completed",
        "stage": manifest.get("stage"),
        "model": manifest.get("model"),
        "runner_commit": manifest.get("runner_commit"),
        "scope": manifest.get("scope"),
        "runs": len(rows),
        "errors": 0,
        "total_tokens": total_tokens,
        "by_variant": {
            variant: {
                "runs": len(group),
                "answer_correct": sum(row["answer_score"] == 1.0 for row in group),
                "mean_answer": mean([row["answer_score"] for row in group]),
                "mean_evidence": mean([row["evidence"] for row in group]),
                "mean_aggregate": mean([row["aggregate"] for row in group]),
                "tokens": sum(row["tokens"] for row in group),
            }
            for variant, group in sorted(by_variant.items())
        },
        "per_run": rows,
    }
    write_json_atomic(result_dir / "summary.json", summary)
    write_checksums(result_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
