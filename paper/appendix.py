"""Appendix tables (paper_spec §3.0 Appendix list).

  A1  rubric-to-task conversion stats: how many source rubrics of each WSB
      rubric_type became atomic tasks, and the overall yield.
  A2  surface eligibility gates — pulled straight from gates.json (table
      coverage, graph task-pass fraction, skill retention).
  A5  contamination probe = S1 (no-tool) closed-book pass rate per model;
      >20% flags a model as potentially contaminated.
  A11 Route confusion matrix — for a chosen setting, how often each needed
      surface was correctly selected vs confused for another.

Emits results/appendix.json + per-table markdown. Robust to runs not yet
present (A5/A11 skipped with a note).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter, defaultdict

from scoring.answer import ABSTAIN_TOKEN, score_answer

ROUTABLE = ["rag", "table", "graph"]


# ---- A1: rubric -> task conversion ---------------------------------------

def appendix_a1(data_root):
    from worksurface.common import load_tasks
    src = load_tasks()
    n_rubrics = sum(len(t.rubrics) for t in src)
    rubric_types = Counter()
    for t in src:
        rubric_types.update(t.rubric_types)
    tasks = [json.loads(l) for l in
             open(os.path.join(data_root, "tasks", "tasks.jsonl"))]
    n_atomic = len(tasks)
    by_type = Counter(t["task_type"] for t in tasks)
    return {
        "n_source_tasks": len(src),
        "n_source_rubrics": n_rubrics,
        "source_rubric_types": dict(rubric_types),
        "n_atomic_tasks": n_atomic,
        "atomic_by_type": dict(by_type),
        "atomic_per_source_task": round(n_atomic / len(src), 2),
        "note": ("Deterministic extractive path only; the LLM-assisted "
                 "rewriter/anchor path (worksurface/llm_hooks.py) is off, "
                 "so yield is a conservative lower bound."),
    }


# ---- A2: surface gates ----------------------------------------------------

def appendix_a2(data_root):
    gates = json.load(open(os.path.join(data_root, "gates.json")))
    return {"summary": gates["summary"],
            "per_profile": {p: {"table_coverage": g["table"]["table_track_coverage"],
                                "graph_median_nontrivial": g["graph"]["median_nontrivial_edges_per_task"],
                                "graph_eligible": g["graph"]["graph_only_eligible"]}
                            for p, g in gates["per_profile"].items()}}


# ---- A5: contamination probe (S1 no-tool closed-book) --------------------

def appendix_a5(runs_dir, data_root):
    tasks = {t["id"]: t for t in
             (json.loads(l) for l in
              open(os.path.join(data_root, "tasks", "tasks.jsonl")))}
    out = {}
    for p in glob.glob(os.path.join(runs_dir, "S1_*.jsonl")):
        model = os.path.basename(p)[3:].replace(".jsonl", "")
        traces = [json.loads(l) for l in open(p)]
        n = passed = 0
        for tr in traces:
            task = tasks.get(tr["id"])
            if not task:
                continue
            n += 1
            if score_answer(task, tr.get("answer")).score >= 0.999:
                passed += 1
        rate = passed / n if n else 0
        out[model] = {"n": n, "closed_book_pass": passed,
                      "closed_book_rate": round(rate, 4),
                      "contamination_flag": rate > 0.20}
    return out or {"note": "no S1 run present"}


# ---- A11: route confusion matrix -----------------------------------------

def appendix_a11(runs_dir, data_root, setting="S4"):
    tasks = {t["id"]: t for t in
             (json.loads(l) for l in
              open(os.path.join(data_root, "tasks", "tasks.jsonl")))}
    cands = glob.glob(os.path.join(runs_dir, f"{setting}_*.jsonl"))
    if not cands:
        return {"note": f"no {setting} run present"}
    traces = {t["id"]: t for t in (json.loads(l) for l in open(cands[0]))}
    # matrix[needed][chosen] += 1 over all (needed,chosen) surface pairs
    matrix = {s: Counter() for s in ROUTABLE}
    missed = Counter()   # needed but not chosen
    spurious = Counter()  # chosen but not needed
    for tid, tr in traces.items():
        task = tasks.get(tid)
        if not task:
            continue
        needed = set(task.get("required_surfaces", [])) & set(ROUTABLE)
        chosen = set(tr.get("chosen_surfaces", [])) & set(ROUTABLE)
        for s in needed:
            if s in chosen:
                matrix[s][s] += 1
            else:
                missed[s] += 1
        for s in chosen - needed:
            spurious[s] += 1
    return {"source_run": os.path.basename(cands[0]),
            "correct_by_surface": {s: matrix[s][s] for s in ROUTABLE},
            "missed_by_surface": dict(missed),
            "spurious_by_surface": dict(spurious)}


def _md_kv(d, path, title):
    lines = [f"### {title}", "", "| Key | Value |", "| --- | --- |"]
    for k, v in d.items():
        lines.append(f"| {k} | {json.dumps(v, ensure_ascii=False) if isinstance(v,(dict,list)) else v} |")
    open(path, "w").write("\n".join(lines) + "\n")


def build_appendix(runs_dir, data_root):
    return {
        "A1_rubric_conversion": appendix_a1(data_root),
        "A2_surface_gates": appendix_a2(data_root),
        "A5_contamination_probe": appendix_a5(runs_dir, data_root),
        "A11_route_confusion": appendix_a11(runs_dir, data_root),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--data-root", default="data/worksurface_lite")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    app = build_appendix(args.runs, args.data_root)
    json.dump(app, open(os.path.join(args.out, "appendix.json"), "w"),
              indent=2, ensure_ascii=False)
    _md_kv(app["A1_rubric_conversion"],
           os.path.join(args.out, "appendixA1_conversion.md"), "A1 Rubric conversion")
    print("[appendix] A1 conversion:", app["A1_rubric_conversion"]["atomic_per_source_task"],
          "atomic/source")
    print("[appendix] A5 contamination:", app["A5_contamination_probe"])
    print("[appendix] A11 route confusion:", app["A11_route_confusion"])
    print(f"[appendix] -> {args.out}/appendix.json")


if __name__ == "__main__":
    main()
