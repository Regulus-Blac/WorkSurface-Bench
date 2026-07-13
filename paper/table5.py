"""Table 5 — failure-mode taxonomy (paper_spec §3.5).

Classifies each incorrect S4-ReAct task into one bucket by comparing the
trace against gold, so the "cross-surface is hard because of routing" claim
is backed by counts rather than anecdote. Categories:

  wrong_surface          chosen surfaces != needed surfaces
  right_surface_wrong_evidence   surfaces ok but evidence hit rate < 1
  right_evidence_wrong_compute   evidence ok, numeric/list answer still wrong
  format_mismatch        answer is arguably right but fails normalization
                         (e.g. within 2x tolerance band but not 5%)
  abstain_when_should_answer     predicted INSUFFICIENT_EVIDENCE, gold concrete
  answer_when_should_abstain     gold is abstain, model answered
  other

Emits results/table5_failure_modes.md + .json, plus a few worked examples.
"""

from __future__ import annotations

import argparse
import glob
import json
import os

from scoring.answer import ABSTAIN_TOKEN, score_answer
from scoring.route_evidence import score_evidence, score_route

CATEGORIES = [
    "wrong_surface", "right_surface_wrong_evidence",
    "right_evidence_wrong_compute", "format_mismatch",
    "abstain_when_should_answer", "answer_when_should_abstain", "other",
]


def _find_s4(runs_dir):
    preferred = os.path.join(runs_dir, "S4_gpt-4o-mini.jsonl")
    if os.path.exists(preferred):
        return preferred
    cands = glob.glob(os.path.join(runs_dir, "S4_*.jsonl"))
    cands = [c for c in cands if not c.endswith(".scored.json")]
    return cands[0] if cands else None


def classify(task, trace):
    gold_ab = task.get("gold_answer") == ABSTAIN_TOKEN or task.get("answer_type") == "abstain"
    pred = trace.get("answer")
    pred_ab = str(pred).strip().upper() == ABSTAIN_TOKEN

    if gold_ab and not pred_ab:
        return "answer_when_should_abstain"
    if pred_ab and not gold_ab:
        return "abstain_when_should_answer"

    route = score_route(task.get("required_surfaces", []),
                        trace.get("chosen_surfaces", []))
    if route.f1 < 0.999:
        return "wrong_surface"

    ev = score_evidence(task.get("gold_evidence", []), trace)
    if ev.score < 0.999:
        return "right_surface_wrong_evidence"

    # surfaces + evidence fine, answer still wrong
    ans = score_answer(task, pred)
    if ans.score >= 0.999:
        return None  # not a failure
    # near-miss numeric within 2x tolerance -> format/normalization
    if task.get("answer_type") == "number":
        try:
            import re
            p = float(re.sub(r"[,$%\s]", "", str(pred)))
            g = float(task["gold_answer"])
            if g and abs(p - g) / max(abs(g), 1e-9) <= 0.10:
                return "format_mismatch"
        except (TypeError, ValueError):
            pass
    return "right_evidence_wrong_compute"


def build_table5(runs_dir, data_root):
    s4 = _find_s4(runs_dir)
    if not s4:
        return None
    traces = {t["id"]: t for t in (json.loads(l) for l in open(s4))}
    tasks = {t["id"]: t for t in
             (json.loads(l) for l in
              open(os.path.join(data_root, "tasks", "tasks.jsonl")))}

    counts = {c: 0 for c in CATEGORIES}
    examples = {c: None for c in CATEGORIES}
    n_fail = 0
    for tid, tr in traces.items():
        task = tasks.get(tid)
        if not task:
            continue
        cat = classify(task, tr)
        if cat is None:
            continue
        n_fail += 1
        counts[cat] += 1
        if examples[cat] is None:
            examples[cat] = {
                "id": tid, "task_type": task["task_type"],
                "question": task["question"][:90],
                "gold": task["gold_answer"] if not isinstance(task["gold_answer"], list)
                        else task["gold_answer"][:3],
                "pred": str(tr.get("answer"))[:60],
                "chosen": tr.get("chosen_surfaces"),
                "needed": task.get("required_surfaces"),
            }
    return {"source_run": os.path.basename(s4), "n_failures": n_fail,
            "counts": counts, "examples": examples,
            "fractions": {c: (round(counts[c] / n_fail, 3) if n_fail else 0)
                          for c in CATEGORIES}}


def write_md(t5, path):
    lines = ["| Failure category | Count | Fraction | Example |",
             "| --- | --- | --- | --- |"]
    for c in CATEGORIES:
        ex = t5["examples"][c]
        exs = "" if not ex else f"{ex['id']} ({ex['task_type']}): needed {ex['needed']} chose {ex['chosen']}"
        lines.append(f"| {c} | {t5['counts'][c]} | {t5['fractions'][c]} | {exs} |")
    lines.append(f"\n_Source: {t5['source_run']}, {t5['n_failures']} failures._")
    open(path, "w").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--data-root", default="data/worksurface_lite")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    t5 = build_table5(args.runs, args.data_root)
    if not t5:
        print("[table5] no S4 run found")
        return
    json.dump(t5, open(os.path.join(args.out, "table5_failure_modes.json"), "w"),
              indent=2, ensure_ascii=False)
    write_md(t5, os.path.join(args.out, "table5_failure_modes.md"))
    print(f"[table5] {t5['n_failures']} failures from {t5['source_run']}")
    for c in CATEGORIES:
        print(f"    {c:<32} {t5['counts'][c]:>3}  ({t5['fractions'][c]:.2f})")


if __name__ == "__main__":
    main()
