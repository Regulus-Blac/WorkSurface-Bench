#!/usr/bin/env python3
"""Validate and archive the repeated Pro sensitivity pilot.

The pilot predates ``run_stage_matrix`` and stores the first repetition as
``*.run.jsonl`` and the second as ``*.rep2.jsonl``.  This command validates
both layouts without making model calls or rewriting any existing run file.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from finalize_pilot_group import (
    load_json,
    load_jsonl,
    write_checksums,
    write_json_atomic,
)


def validate_repetition(result_dir: Path, task_id: str, variant: str, repeat: int) -> dict:
    stem = f"{task_id}__{variant}"
    suffix = "run" if repeat == 1 else f"rep{repeat}"
    trace_path = result_dir / f"{stem}.{suffix}.jsonl"
    status_path = result_dir / f"{stem}.{suffix if repeat > 1 else ''}status.json"
    scored_path = result_dir / f"{stem}.{suffix}.scored.json"
    task_path = result_dir / f"{stem}.jsonl"
    manifest_path = result_dir / f"{stem}.{suffix if repeat > 1 else ''}manifest.json"

    missing = [
        path.name
        for path in (trace_path, status_path, scored_path, task_path, manifest_path)
        if not path.is_file()
    ]
    if missing:
        raise ValueError(f"{stem} repetition {repeat}: missing {', '.join(missing)}")

    tasks = load_jsonl(task_path)
    traces = load_jsonl(trace_path)
    status = load_json(status_path)
    scored = load_json(scored_path)
    manifest = load_json(manifest_path)
    if len(tasks) != 1 or len(traces) != 1:
        raise ValueError(f"{stem} repetition {repeat}: expected one task and one trace")
    if tasks[0].get("id") != task_id or traces[0].get("id") != task_id:
        raise ValueError(f"{stem} repetition {repeat}: task/trace ID mismatch")
    if status.get("expected_ids") != [task_id] or status.get("completed_ids") != [task_id]:
        raise ValueError(f"{stem} repetition {repeat}: status ID mismatch")
    if status.get("state") != "completed" or not status.get("completed"):
        raise ValueError(f"{stem} repetition {repeat}: incomplete status")
    if status.get("errors") != 0 or "error" in traces[0]:
        raise ValueError(f"{stem} repetition {repeat}: contains an execution error")
    per_task = scored.get("per_task", [])
    if len(per_task) != 1 or per_task[0].get("id") != task_id:
        raise ValueError(f"{stem} repetition {repeat}: scored task mismatch")
    if manifest.get("expected_ids") != [task_id]:
        raise ValueError(f"{stem} repetition {repeat}: manifest ID mismatch")

    return {
        "task_id": task_id,
        "variant": variant,
        "repeat": repeat,
        "answer": traces[0].get("answer"),
        "answer_score": per_task[0]["answer"]["score"],
        "total_tokens": int(traces[0].get("total_tokens") or 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--expected-tasks", type=int, default=6)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()

    result_dir = args.result_dir.resolve()
    group_manifest = load_json(result_dir / "run_manifest.json")
    task_ids = group_manifest.get("tasks", [])
    if len(task_ids) != args.expected_tasks or len(task_ids) != len(set(task_ids)):
        raise ValueError(
            f"expected {args.expected_tasks} unique tasks, found {len(task_ids)}"
        )

    rows = []
    for task_id in task_ids:
        for variant in ("full", "subset"):
            for repeat in range(1, args.repeats + 1):
                rows.append(validate_repetition(result_dir, task_id, variant, repeat))

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["task_id"], row["variant"])].append(row)
    answer_stable = sum(
        len({row["answer"] for row in group}) == 1 for group in grouped.values()
    )
    score_stable = sum(
        len({row["answer_score"] for row in group}) == 1 for group in grouped.values()
    )
    pairs = len(grouped)

    summary = {
        "state": "completed",
        "stage": "Pro sensitivity pilot",
        "model": group_manifest.get("model"),
        "runner_commit": group_manifest.get("runner_commit"),
        "scope": group_manifest.get("scope"),
        "tasks": len(task_ids),
        "variants_per_task": 2,
        "repeats": args.repeats,
        "runs": len(rows),
        "errors": 0,
        "answer_stable_pairs": answer_stable,
        "score_stable_pairs": score_stable,
        "pairs": pairs,
        "total_tokens": sum(row["total_tokens"] for row in rows),
        "per_run": rows,
    }
    write_json_atomic(result_dir / "summary.json", summary)
    write_checksums(result_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
