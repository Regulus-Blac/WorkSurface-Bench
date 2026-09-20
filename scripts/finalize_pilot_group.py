#!/usr/bin/env python3
"""Validate and finalize a per-task pilot result directory.

The directory must contain one ``run_manifest.json`` plus singleton FULL and
SUBSET runs produced by ``runner.run_bench``.  No model calls are made.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from scoring.score_run import score_run


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json_atomic(path: Path, payload) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def singleton_run_files(result_dir: Path, kind: str) -> list[Path]:
    if kind == "full":
        pattern = "*__full.run.jsonl"
    else:
        pattern = "*__subset*.run.jsonl"
    return sorted(result_dir.glob(pattern))


def validate_run(run_path: Path) -> tuple[dict, dict, dict]:
    stem = run_path.name.removesuffix(".run.jsonl")
    task_path = run_path.with_name(stem + ".jsonl")
    status_path = run_path.with_name(stem + ".status.json")
    scored_path = run_path.with_name(stem + ".run.scored.json")
    missing = [p.name for p in (task_path, status_path, scored_path) if not p.exists()]
    if missing:
        raise ValueError(f"{run_path.name}: missing {', '.join(missing)}")

    tasks = load_jsonl(task_path)
    traces = load_jsonl(run_path)
    status = load_json(status_path)
    scored = load_json(scored_path)
    if len(tasks) != 1 or len(traces) != 1:
        raise ValueError(f"{run_path.name}: expected one task and one trace")
    task_id = tasks[0].get("id")
    if traces[0].get("id") != task_id:
        raise ValueError(f"{run_path.name}: task/trace ID mismatch")
    if status.get("expected_ids") != [task_id] or status.get("completed_ids") != [task_id]:
        raise ValueError(f"{run_path.name}: status ID mismatch")
    if not status.get("completed") or status.get("state") != "completed":
        raise ValueError(f"{run_path.name}: incomplete status")
    if status.get("errors") != 0 or "error" in traces[0]:
        raise ValueError(f"{run_path.name}: contains an execution error")
    per_task = scored.get("per_task", [])
    if len(per_task) != 1 or per_task[0].get("id") != task_id:
        raise ValueError(f"{run_path.name}: scored task mismatch")
    return tasks[0], traces[0], per_task[0]


def write_checksums(result_dir: Path) -> None:
    rows = []
    for path in sorted(result_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name in {"checksums.sha256", "checksums.sha256.tmp"}:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.name}\n")
    target = result_dir / "checksums.sha256"
    tmp = result_dir / "checksums.sha256.tmp"
    with tmp.open("w", encoding="ascii") as stream:
        stream.writelines(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--expected-full", type=int, required=True)
    parser.add_argument("--expected-subset", type=int, required=True)
    args = parser.parse_args()

    result_dir = args.result_dir.resolve()
    manifest = load_json(result_dir / "run_manifest.json")
    full_paths = singleton_run_files(result_dir, "full")
    subset_paths = singleton_run_files(result_dir, "subset")
    if len(full_paths) != args.expected_full:
        raise ValueError(f"expected {args.expected_full} FULL runs, found {len(full_paths)}")
    if len(subset_paths) != args.expected_subset:
        raise ValueError(
            f"expected {args.expected_subset} SUBSET runs, found {len(subset_paths)}"
        )

    full_tasks: list[dict] = []
    full_traces: list[dict] = []
    subset_scores: list[dict] = []
    all_traces: list[dict] = []
    for path in full_paths:
        task, trace, _ = validate_run(path)
        full_tasks.append(task)
        full_traces.append(trace)
        all_traces.append(trace)
    for path in subset_paths:
        _, trace, score = validate_run(path)
        subset_scores.append(score)
        all_traces.append(trace)

    full_ids = [task["id"] for task in full_tasks]
    if len(full_ids) != len(set(full_ids)):
        raise ValueError("FULL task IDs are not unique")
    combined = score_run(full_tasks, {trace["id"]: trace for trace in full_traces})
    write_json_atomic(result_dir / "full_combined.scored.json", combined)

    summary = {
        "state": "completed",
        "model": manifest.get("model"),
        "runner_commit": manifest.get("runner_commit"),
        "scope": manifest.get("scope"),
        "full_runs": len(full_paths),
        "subset_runs": len(subset_paths),
        "errors": 0,
        "full_answer_correct": sum(row["answer"]["score"] for row in combined["per_task"]),
        "full_overall": combined["overall"],
        "subset_correct_runs": sum(
            row["answer"]["score"] == 1.0 for row in subset_scores
        ),
        "total_tokens": sum(int(trace.get("total_tokens") or 0) for trace in all_traces),
    }
    write_json_atomic(result_dir / "summary.json", summary)
    write_checksums(result_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
