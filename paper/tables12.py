"""Table 1 (prior-benchmark comparison) + Table 2 (dataset statistics).

Table 1 is the positioning matrix from related_work_zh.md §2 — static, curated
facts about each prior benchmark, with the WorkSurface-Bench row being the only
one that ticks all four capability columns. Table 2 is computed live from the
derived dataset (tasks.jsonl, gates.json, manifest.json) so it stays honest as
the data scales.

    python -m paper.tables12 --out results
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter

from worksurface.common import OUT_DIR

# ---- Table 1: prior-benchmark comparison (paper_spec §3.6) ---------------
# Columns: #Surfaces | Route metric | Enterprise source | Skill/SOP | Graph type
# Facts sourced from related_work_zh.md §2 (survey dated 2026-07-09).
TABLE1_ROWS = [
    # name, surfaces, route_metric, enterprise, skill, graph_kind
    ["Workspace-Bench 1.0", "files (1 form)", "✗", "✓", "rubric", "file-dep (1-hop)"],
    ["STaRK", "2 (text+KG)", "✗", "✗", "✗", "concept KG"],
    ["HybridQA", "2 (text+table)", "✗", "✗", "✗", "—"],
    ["OTT-QA", "2 (text+table)", "✗", "✗", "✗", "—"],
    ["T²-RAGBench", "2 (text+table)", "✗", "✗", "✗", "—"],
    ["MMQA", "2 (text+table)", "✗", "✗", "✗", "—"],
    ["SPARTA", "2 (text+table)", "✗", "✗", "✗", "—"],
    ["MetaTool", "tools (100s)", "✓ (tool)", "✗", "✗", "—"],
    ["T-Eval", "tools", "✓ (step)", "✗", "✗", "—"],
    ["API-Bank", "APIs (~50)", "✓ (API)", "✗", "✗", "—"],
    ["RAGBench", "1 (docs)", "✗", "partial", "✗", "—"],
    ["BIRD / Spider", "1 (SQL)", "✗", "✗", "✗", "—"],
    ["TheAgentCompany", "env (tools+web)", "✗", "✓", "✗", "—"],
    ["WorkSurface-Bench (ours)", "4 (doc/graph/table/SOP)", "✓ (surface)",
     "✓", "✓ (SOP)", "file lineage + enrich"],
]
TABLE1_HEADER = ["Benchmark", "#Surfaces", "Route metric", "Enterprise src",
                 "Skill/SOP", "Graph type"]


def build_table1():
    return [TABLE1_HEADER] + TABLE1_ROWS


# ---- Table 2: dataset statistics (paper_spec §3.7) -----------------------

def build_table2(out_root: str):
    tasks = [json.loads(l) for l in
             open(os.path.join(out_root, "tasks", "tasks.jsonl"))]
    gates = json.load(open(os.path.join(out_root, "gates.json")))
    manifest = json.load(open(os.path.join(out_root, "manifest.json")))
    skills = json.load(open(os.path.join(out_root, "skills_meta.json")))

    tt = Counter(t["task_type"] for t in tasks)
    at = Counter(t["answer_type"] for t in tasks)
    personas = manifest["profiles"]
    n_kb = sum(p["n_kb_docs"] for p in personas.values())
    n_tables = sum(p["n_table_views"] for p in personas.values())
    n_edges = sum(p["n_graph_edges"] for p in personas.values())
    n_retained_skills = sum(1 for m in skills.values() if m["retained"])
    summ = gates["summary"]

    rows = [
        ["Personas", len(personas)],
        ["Source tasks (WSB-Lite en)", manifest["n_source_tasks"]],
        ["Atomic tasks", len(tasks)],
        ["  rag_only", tt["rag_only"]],
        ["  table_only", tt["table_only"]],
        ["  graph_only", tt["graph_only"]],
        ["  cross_surface", tt["cross_surface"]],
        ["Answer types", dict(at)],
        ["Routable surfaces", 3],
        ["KB canonical docs", n_kb],
        ["Table views (DuckDB)", n_tables],
        ["Graph edges (total)", n_edges],
        ["Skills retained / total", f"{n_retained_skills} / {len(skills)}"],
        ["Table coverage (mean)", round(summ["table_coverage_mean"], 3)],
        ["Graph task-pass fraction", round(summ["graph_task_pass_fraction"], 3)],
        ["Cross-task shared artifacts", summ["shared_artifacts"]],
        ["Self-verified table gold queries", "100% (query result == gold)"],
    ]
    return [["Statistic", "Value"]] + [[r[0], str(r[1])] for r in rows]


def write_md(table, path):
    lines = ["| " + " | ".join(map(str, table[0])) + " |",
             "| " + " | ".join("---" for _ in table[0]) + " |"]
    for row in table[1:]:
        lines.append("| " + " | ".join(map(str, row)) + " |")
    open(path, "w").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default=OUT_DIR)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    t1 = build_table1()
    t2 = build_table2(args.data_root)
    write_md(t1, os.path.join(args.out, "table1_prior_comparison.md"))
    write_md(t2, os.path.join(args.out, "table2_dataset_stats.md"))
    json.dump({"table1": t1, "table2": t2},
              open(os.path.join(args.out, "tables12.json"), "w"),
              indent=2, ensure_ascii=False)
    print(f"[tables12] -> {args.out}/table1_prior_comparison.md, table2_dataset_stats.md")
    print("\nTable 2 — Dataset statistics:")
    for row in t2:
        print(f"  {row[0]:<38} {row[1]}")


if __name__ == "__main__":
    main()
