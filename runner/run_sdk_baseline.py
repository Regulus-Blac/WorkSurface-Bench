"""Run the restricted Claude Agent SDK baseline and score its traces.

Example::

    WSB_API_BASE=https://provider.example/v1 WSB_API_KEY=... \
      python -m runner.run_sdk_baseline \
      --model claude-sonnet-4-6 \
      --tasks data/worksurface_lite/tasks/tasks_final_1151.jsonl \
      --data-root data/worksurface_lite \
      --concurrency 5 --resume
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from scoring.score_run import score_run
from worksurface.common import OUT_DIR

from .claude_sdk_baseline import (
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_MAX_TURNS,
    SETTING_NAME,
    run_claude_sdk_task,
)


def _safe_model(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument(
        "--tasks",
        default=os.path.join(OUT_DIR, "tasks", "tasks_final_1151.jsonl"),
    )
    ap.add_argument("--data-root", default=OUT_DIR)
    ap.add_argument("--runs-dir", default="runs_sdk")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    ap.add_argument(
        "--max-tool-calls",
        type=int,
        default=DEFAULT_MAX_TOOL_CALLS,
        help="executed WorkSurface calls per task; defaults to the S4 budget",
    )
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.concurrency < 1:
        ap.error("--concurrency must be at least 1")
    if args.max_turns < 1:
        ap.error("--max-turns must be at least 1")
    if args.max_tool_calls < 1:
        ap.error("--max-tool-calls must be at least 1")

    with open(args.tasks, encoding="utf-8") as stream:
        tasks = [json.loads(line) for line in stream]
    if args.ids:
        selected = set(args.ids)
        tasks = [task for task in tasks if task["id"] in selected]
    if args.limit is not None:
        tasks = tasks[: args.limit]
    if not tasks:
        raise SystemExit("No tasks selected")

    os.makedirs(args.runs_dir, exist_ok=True)
    stem = f"{SETTING_NAME}_{_safe_model(args.model)}"
    out = os.path.join(args.runs_dir, stem + ".jsonl")
    partial = out + ".partial"

    results: dict[str, dict] = {}
    if args.resume and os.path.exists(partial):
        with open(partial, encoding="utf-8") as stream:
            for line in stream:
                try:
                    trace = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if trace.get("id") and not trace.get("error"):
                    results[trace["id"]] = trace

    todo = [task for task in tasks if task["id"] not in results]
    if results:
        print(f"[sdk] resume: {len(results)} done, {len(todo)} remaining")

    def run_one(task: dict) -> dict:
        try:
            return run_claude_sdk_task(
                task,
                model=args.model,
                out_root=args.data_root,
                max_turns=args.max_turns,
                max_tool_calls=args.max_tool_calls,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "id": task["id"],
                "setting": SETTING_NAME,
                "model": f"claude-agent-sdk:{args.model}",
                "error": repr(exc),
                "chosen_surfaces": [],
                "rag_files": [],
                "tables": [],
                "graph_nodes": [],
                "answer": "",
                "total_tokens": 0,
                "tool_trace": [],
                "question_text": task["question"],
                "output_text": "",
            }

    lock = Lock()
    with open(partial, "a", encoding="utf-8") as partial_stream:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = {executor.submit(run_one, task): task["id"] for task in todo}
            done = len(results)
            for future in as_completed(futures):
                trace = future.result()
                results[trace["id"]] = trace
                with lock:
                    partial_stream.write(
                        json.dumps(trace, ensure_ascii=False) + "\n"
                    )
                    partial_stream.flush()
                done += 1
                print(
                    f"[sdk/{args.model}] {done}/{len(tasks)} "
                    f"id={trace['id']} error={bool(trace.get('error'))}",
                    flush=True,
                )

    with open(out, "w", encoding="utf-8") as stream:
        for task in tasks:
            if task["id"] in results:
                stream.write(
                    json.dumps(results[task["id"]], ensure_ascii=False) + "\n"
                )

    traces = {task_id: trace for task_id, trace in results.items()}
    report = score_run(tasks, traces)
    scored_path = out.rsplit(".", 1)[0] + ".scored.json"
    with open(scored_path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)

    if os.path.exists(partial):
        os.remove(partial)
    errors = sum(bool(results.get(task["id"], {}).get("error")) for task in tasks)
    print(f"[sdk] {errors} errors; overall={report['overall']}")
    print(f"[sdk] traces={out}")
    print(f"[sdk] scored={scored_path}")


if __name__ == "__main__":
    main()
