#!/usr/bin/env python3
"""Run or resume a locked pilot-stage FULL/SUBSET matrix.

The projection's private alias map resolves original benchmark IDs to public
task files. Each singleton run keeps its own manifest, status, trace, score,
and log. Failed API/platform attempts are retried without touching completed
runs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def completed(result_dir: Path, stem: str) -> bool:
    required = [
        result_dir / f"{stem}.run.jsonl",
        result_dir / f"{stem}.run.scored.json",
        result_dir / f"{stem}.status.json",
        result_dir / f"{stem}.manifest.json",
        result_dir / f"{stem}.log",
    ]
    if not all(path.exists() for path in required):
        return False
    status = read_json(result_dir / f"{stem}.status.json")
    return (status.get("state") == "completed" and status.get("completed")
            and status.get("errors") == 0)


def append_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(text)
        if text and not text.endswith("\n"):
            stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--setting", default="S4")
    parser.add_argument("--scope", choices=("task", "persona"), default="persona")
    parser.add_argument("--task-id", action="append", required=True,
                        help="Original benchmark task ID; repeat for each sentinel")
    parser.add_argument("--variants", nargs="+", default=("full", "subset"))
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=5.0)
    args = parser.parse_args()

    projection = args.projection.resolve()
    result_dir = args.result_dir.resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    alias_map = read_json(projection / "private" / "alias_map.json")
    projection_manifest = read_json(projection / "projection_manifest.json")
    public_ids = alias_map["benchmark_tasks"]
    missing = sorted(set(args.task_id) - set(public_ids))
    if missing:
        raise ValueError(f"unknown task IDs: {missing}")

    matrix = []
    for original_id in args.task_id:
        public_id = public_ids[original_id]
        for variant in args.variants:
            stem = f"{public_id}__{variant}"
            task_path = projection / "public" / "tasks" / f"{stem}.jsonl"
            if not task_path.exists():
                raise ValueError(f"missing projected task input: {task_path}")
            matrix.append({"original_id": original_id, "public_id": public_id,
                           "variant": variant, "stem": stem,
                           "task_path": str(task_path)})

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = {
        "run_group": result_dir.name,
        "stage": args.stage,
        "model": args.model,
        "api_base": os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("WSB_API_BASE"),
        "runner_commit": commit,
        "scope": args.scope,
        "setting": args.setting,
        "projection": str(projection),
        "source_lock_sha256": projection_manifest["source_lock_sha256"],
        "public_lock_sha256": projection_manifest["public_lock_sha256"],
        "matrix": [{key: row[key] for key in ("original_id", "public_id", "variant")}
                   for row in matrix],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = result_dir / "run_manifest.json"
    if manifest_path.exists():
        existing = read_json(manifest_path)
        comparable = {key: value for key, value in manifest.items() if key != "created_at"}
        old_comparable = {key: value for key, value in existing.items() if key != "created_at"}
        if comparable != old_comparable:
            raise ValueError("existing run manifest does not match requested matrix")
    else:
        write_json_atomic(manifest_path, manifest)

    group_status = {
        "state": "running",
        "expected": [row["stem"] for row in matrix],
        "completed": [],
        "failed": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    for row in matrix:
        stem = row["stem"]
        if completed(result_dir, stem):
            group_status["completed"].append(stem)
            continue
        log_path = result_dir / f"{stem}.log"
        success = False
        for attempt in range(1, args.retries + 1):
            append_log(log_path, f"[{datetime.now(timezone.utc).isoformat()}] attempt={attempt}")
            cmd = [
                sys.executable, "-m", "runner.run_bench",
                "--setting", args.setting,
                "--model", args.model,
                "--scope", args.scope,
                "--data-root", str(projection / "public"),
                "--tasks", row["task_path"],
                "--out", str(result_dir / f"{stem}.run.jsonl"),
                "--manifest", str(result_dir / f"{stem}.manifest.json"),
                "--status", str(result_dir / f"{stem}.status.json"),
                "--score",
            ]
            proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
            append_log(log_path, proc.stdout)
            append_log(log_path, proc.stderr)
            if proc.returncode == 0 and completed(result_dir, stem):
                success = True
                break
            if attempt < args.retries:
                time.sleep(args.retry_delay)
        if not success:
            group_status["failed"].append(stem)
            group_status["state"] = "incomplete"
            group_status["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_json_atomic(result_dir / "group_status.json", group_status)
            raise RuntimeError(f"run failed after {args.retries} attempts: {stem}")
        group_status["completed"].append(stem)
        group_status["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json_atomic(result_dir / "group_status.json", group_status)
        print(f"[{len(group_status['completed'])}/{len(matrix)}] {stem}", flush=True)

    group_status["state"] = "completed"
    group_status["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json_atomic(result_dir / "group_status.json", group_status)


if __name__ == "__main__":
    main()
