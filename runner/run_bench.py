"""Run a WorkSurface-Bench setting x model over the task set -> trace JSONL.

    python -m runner.run_bench --setting S4 --model mock \
        --tasks data/worksurface_lite/tasks/tasks.jsonl \
        --out runs/S4_mock.jsonl [--limit 50] [--score]

With --score it immediately scores the run via scoring.score_run and writes
<out>.scored.json. Use --model mock for a no-API smoke run; a real model name
(with WSB_API_BASE + WSB_API_KEY set) runs the actual backbone.
"""

from __future__ import annotations

import argparse
import json
import os

from worksurface.common import OUT_DIR

from .agents import SETTINGS, run_task
from .backbone import make_backbone


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--setting", required=True, choices=list(SETTINGS))
    ap.add_argument("--model", default="mock")
    ap.add_argument("--tasks", default=os.path.join(OUT_DIR, "tasks", "tasks.jsonl"))
    ap.add_argument("--data-root", default=OUT_DIR)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--scope", choices=("task", "persona"), default="task")
    ap.add_argument("--manifest", default=None,
                    help="JSON manifest path to write before the run")
    ap.add_argument("--status", default=None,
                    help="Atomic checkpoint status JSON path")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(args.tasks)]
    if args.limit:
        tasks = tasks[: args.limit]
    backbone = make_backbone(args.model)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    status_path = args.status or args.out.rsplit(".", 1)[0] + ".status.json"
    manifest_path = args.manifest
    expected_ids = [t["id"] for t in tasks]

    def write_atomic(path, payload):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as sf:
            json.dump(payload, sf, ensure_ascii=False, indent=2)
            sf.flush()
            os.fsync(sf.fileno())
        os.replace(tmp, path)

    if manifest_path:
        os.makedirs(os.path.dirname(manifest_path) or ".", exist_ok=True)
        write_atomic(manifest_path, {
            "model": args.model,
            "setting": args.setting,
            "scope": args.scope,
            "tasks": args.tasks,
            "data_root": args.data_root,
            "expected_ids": expected_ids,
        })
    status = {"state": "running", "expected_ids": expected_ids,
              "completed_ids": [], "errors": 0, "out": args.out}
    write_atomic(status_path, status)

    n_err = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for i, task in enumerate(tasks, 1):
            try:
                trace = run_task(task, args.setting, backbone, args.data_root,
                                 scope=args.scope)
            except Exception as e:  # noqa: BLE001
                n_err += 1
                trace = {"id": task["id"], "setting": args.setting,
                         "model": backbone.name, "error": repr(e),
                         "chosen_surfaces": [], "rag_files": [], "tables": [],
                         "graph_nodes": [], "answer": "", "total_tokens": 0}
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
            status["completed_ids"].append(task["id"])
            if "error" in trace:
                status["errors"] += 1
            write_atomic(status_path, status)
            if i % 50 == 0:
                print(f"  [{args.setting}/{args.model}] {i}/{len(tasks)}")
    print(f"[run] {len(tasks)} tasks, {n_err} errors -> {args.out}")

    status["state"] = "completed" if not n_err else "completed_with_errors"
    status["completed"] = len(status["completed_ids"]) == len(expected_ids)
    write_atomic(status_path, status)

    if args.score:
        from scoring.score_run import score_run
        traces = {t["id"]: t for t in
                  (json.loads(l) for l in open(args.out))}
        report = score_run(tasks, traces)
        scored_path = args.out.rsplit(".", 1)[0] + ".scored.json"
        scored_tmp = scored_path + ".tmp"
        with open(scored_tmp, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(scored_tmp, scored_path)
        print(f"[run] overall={report['overall']}")
        print(f"[run] scored -> {scored_path}")


if __name__ == "__main__":
    main()
