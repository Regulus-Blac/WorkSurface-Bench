"""Figure 3 — the empirical heart (paper_spec §3.3). Three subplots:

  3(a) Route-Answer scatter: one point per (model, task_type) bucket; x=Route
       F1, y=Answer. Reports Spearman rho + p. Target rho in [0.4, 0.7] (weak-
       to-moderate) supports the Route != Answer separability claim; rho > 0.85
       would trigger the §3.10 fallback.
  3(b) Gold-guidance bars: per model, Answer for Naive-router (S3) / ReAct-all
       (S4) / Gold-surface guided (S5). Shows the effect of supplying gold
       surface information while leaving execution to the model.
  3(c) Per-surface Answer lines: x=task_type, y=Answer, one line per setting.
       cross_surface expected lowest.

Emits results/figure3_data.json (plot-ready) + results/plot_figure3.py
(matplotlib). Consumes runs/*.scored.json.
"""

from __future__ import annotations

import argparse
import glob
import json
import os

from scipy import stats

TASK_TYPES = ["rag_only", "table_only", "graph_only", "cross_surface"]


def _parse_name(path):
    base = os.path.basename(path).replace(".scored.json", "")
    setting, _, model = base.partition("_")
    return setting, (model or "?")


def load_scored(runs_dir):
    runs = {}
    for p in sorted(glob.glob(os.path.join(runs_dir, "*.scored.json"))):
        setting, model = _parse_name(p)
        runs[(setting, model)] = json.load(open(p))
    return runs


def build_figure3(runs_dir):
    runs = load_scored(runs_dir)
    models = sorted({m for _, m in runs})

    # 3(a) scatter over (model, task_type) buckets, exclude S1 (no route)
    xs, ys, labels = [], [], []
    for (setting, model), rep in runs.items():
        if setting == "S1":
            continue
        for tt, agg in rep["by_task_type"].items():
            if agg["route_f1"] is None or agg["answer"] is None:
                continue
            xs.append(agg["route_f1"])
            ys.append(agg["answer"])
            labels.append(f"{setting}:{model}:{tt}")
    rho = p = None
    if len(xs) >= 3:
        rho, p = stats.spearmanr(xs, ys)
    scatter = {"x_route_f1": xs, "y_answer": ys, "labels": labels,
               "spearman_rho": None if rho is None else round(float(rho), 4),
               "p_value": None if p is None else float(f"{p:.3e}"),
               "interpretation": _interpret(rho)}

    # 3(b) oracle-gap bars: Answer for S3/S4/S5 per model
    gap = {"models": models, "S3_naive": [], "S4_react": [], "S5_oracle": []}
    for m in models:
        for s, key in (("S3", "S3_naive"), ("S4", "S4_react"), ("S5", "S5_oracle")):
            rep = runs.get((s, m))
            gap[key].append(rep["overall"]["answer"] if rep else None)
    gap["oracle_minus_naive"] = [
        (o - n) if (o is not None and n is not None) else None
        for o, n in zip(gap["S5_oracle"], gap["S3_naive"])]

    # 3(c) per-surface Answer lines per setting (aggregate across models)
    per_surface = {"task_types": TASK_TYPES, "lines": {}}
    settings = sorted({s for s, _ in runs})
    for s in settings:
        vals = []
        for tt in TASK_TYPES:
            # mean over models present for this setting
            cell = [runs[(s, m)]["by_task_type"].get(tt, {}).get("answer")
                    for m in models if (s, m) in runs]
            cell = [c for c in cell if c is not None]
            vals.append(round(sum(cell) / len(cell), 4) if cell else None)
        per_surface["lines"][s] = vals

    return {"scatter_3a": scatter, "oracle_gap_3b": gap,
            "per_surface_3c": per_surface}


def _interpret(rho):
    if rho is None:
        return "insufficient points"
    if rho > 0.85:
        return "rho>0.85 — Route and Answer nearly collinear; §3.10 fallback triggered"
    if rho >= 0.4:
        return "rho in [0.4,0.85] — weak-to-moderate coupling; supports Route != Answer"
    return "rho<0.4 — Route and Answer largely decoupled; strongly supports separability"


PLOT_SCRIPT = '''"""Render Figure 3 from figure3_data.json. Usage: python plot_figure3.py"""
import json, os
import matplotlib.pyplot as plt

d = json.load(open(os.path.join(os.path.dirname(__file__), "figure3_data.json")))
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))

a = d["scatter_3a"]
ax[0].scatter(a["x_route_f1"], a["y_answer"], alpha=0.7)
ax[0].set_xlabel("Route F1"); ax[0].set_ylabel("Answer")
ax[0].set_title(f"(a) Route vs Answer  rho={a['spearman_rho']} p={a['p_value']}")
ax[0].set_xlim(-0.05, 1.05); ax[0].set_ylim(-0.05, 1.05)

g = d["oracle_gap_3b"]
import numpy as np
x = np.arange(len(g["models"])); w = 0.25
for i, (k, lbl) in enumerate([("S3_naive","Naive"),("S4_react","ReAct"),("S5_oracle","Gold-guided")]):
    ax[1].bar(x + (i-1)*w, [v or 0 for v in g[k]], w, label=lbl)
ax[1].set_xticks(x); ax[1].set_xticklabels(g["models"], rotation=20)
ax[1].set_ylabel("Answer"); ax[1].set_title("(b) Gold-surface guidance"); ax[1].legend()

c = d["per_surface_3c"]
for s, vals in c["lines"].items():
    ax[2].plot(c["task_types"], [v if v is not None else float("nan") for v in vals],
               marker="o", label=s)
ax[2].set_ylabel("Answer"); ax[2].set_title("(c) Per-surface Answer")
ax[2].tick_params(axis="x", rotation=20); ax[2].legend()

plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__), "figure3.png"), dpi=150)
print("wrote figure3.png")
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    data = build_figure3(args.runs)
    json.dump(data, open(os.path.join(args.out, "figure3_data.json"), "w"),
              indent=2, ensure_ascii=False)
    # Keep a hand-tuned plotting script if one already exists; the embedded
    # fallback is only for a fresh output directory.
    plot_script = os.path.join(args.out, "plot_figure3.py")
    if not os.path.exists(plot_script):
        open(plot_script, "w").write(PLOT_SCRIPT)

    s = data["scatter_3a"]
    print(f"[fig3] scatter: {len(s['x_route_f1'])} buckets, "
          f"rho={s['spearman_rho']} p={s['p_value']}")
    print(f"       {s['interpretation']}")
    print(f"[fig3] oracle-minus-naive Answer: {data['oracle_gap_3b']['oracle_minus_naive']}")
    print(f"[fig3] per-surface (mean over models): "
          f"{data['per_surface_3c']['lines']}")
    print(f"[fig3] -> {args.out}/figure3_data.json + plot_figure3.py")


if __name__ == "__main__":
    main()
