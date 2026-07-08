# WorkSurface-Bench

**Benchmarking enterprise agents on multi-surface knowledge routing.**

WorkSurface-Bench is a benchmark proposal for evaluating whether enterprise
agents can route questions across heterogeneous knowledge surfaces, use the
right tools, ground their answers in evidence, and avoid treating every
enterprise question as a vanilla RAG problem.

The benchmark is designed to be derived from Workspace-Bench-style enterprise
workspaces. Instead of aggregating unrelated public RAG, SQL, graph, and memory
datasets, WorkSurface-Bench starts from one coherent workspace and projects its
files, dependency graph, rubrics, and workflow conventions into multiple
enterprise knowledge surfaces.

## Motivation

Most RAG benchmarks provide documents, queries, and answers. They primarily
measure document retrieval and grounded generation. Real enterprise agents,
however, rarely operate over a single document retriever. Enterprise knowledge
is distributed across:

- unstructured documents and reports;
- structured tables and spreadsheets;
- file, entity, project, and workflow dependency graphs;
- SOPs, runbooks, and reusable procedural knowledge.

WorkSurface-Bench asks a different question:

> Given a realistic enterprise workspace represented as multiple knowledge
> surfaces, can an agent choose and combine the right surfaces to answer a task?

## Core Surfaces

The core benchmark focuses on three routable enterprise knowledge surfaces:

| Surface | Source in Workspace-Bench-style data | Example tools |
| --- | --- | --- |
| RAG / KB | Documents, reports, PDFs, text files, slide text | `kb_search` |
| Graph | File dependency graph, task-file-output links, lineage | `graph_search_entities`, `graph_traverse`, `graph_neighbors` |
| Table | CSV/XLSX spreadsheets and structured business records | `table_list`, `table_describe`, `table_query` |

The Table surface is deliberately not framed as an enterprise SQL benchmark
(cf. BIRD, Spider). Workspace-Bench-derived spreadsheets are typically small,
per-task, and disjoint. Our claim is only that the agent should recognize
when a question needs aggregation or filtering over structured rows and route
to `table_query` (backed by DuckDB / pandas), instead of reading the sheet as
prose. That routing decision is what we measure.

**Skills as task metadata (v0.1).** In v0.1 we do not treat Skill / SOP as
a routable surface. Rubric-derived workflows are attached to each task as
`applicable_skills` metadata: the agent may consult them but Route
precision/recall is scored only over `{rag, graph, table}`. Rationale in
[`docs/open_questions.md`](docs/open_questions.md) Q1 — Workspace-Bench
rubrics are per-task and leak answers when directly promoted to shared
skills. Once leak-check on Full source data yields ≥ 20 clean skills we
will revisit and add Skill as a fourth routable surface in v0.2.

Personal or session memory is intentionally not part of the core benchmark. It
can be added later as a stateful personalization extension, but the main task is
shared enterprise knowledge routing.

## Relationship to Workspace-Bench

Workspace-Bench evaluates whether agents can learn and operate over realistic
workspace files. WorkSurface-Bench uses the same kind of enterprise-validated
source data, but changes the evaluation target:

| Benchmark | Main question |
| --- | --- |
| Workspace-Bench | Can the agent find and use the right workspace files to complete tasks? |
| WorkSurface-Bench | Can the agent route across RAG, graph, and tables to produce grounded answers? |

The intended pipeline is:

```text
Workspace files + manifests + file dependency graph + rubrics
        |
        v
Canonical multi-surface profile
        |
        v
RAG docs + tables + surface graph + skills-as-metadata
        |
        v
Routing/evidence/answer evaluation
```

## What the Benchmark Provides

Each benchmark profile should contain:

```text
profile_<name>/
  kb_docs/                 # canonical text documents for RAG
  tables/                  # per-task CSVs, plus a DuckDB view registry
  graph/surface_graph.json # file/task/output/entity dependency graph
  skills/                  # SOP hints attached as task metadata (v0.1)
  tasks/tasks.jsonl        # atomic routing tasks
  manifest.json            # provenance and conversion metadata
```

Each task includes:

- a natural-language question;
- gold answer;
- required surfaces;
- expected tool types;
- evidence annotations;
- source Workspace-Bench task/rubric references.

See [`schemas/task.schema.json`](schemas/task.schema.json) and
[`examples/tasks.example.jsonl`](examples/tasks.example.jsonl).

The data construction plan and scale targets are documented in
[`docs/data_construction_plan_zh.md`](docs/data_construction_plan_zh.md).

## Task Types

WorkSurface-Bench decomposes workspace tasks into atomic diagnostic tasks:

1. **RAG-only**: answer from documents and reports.
2. **Table-only**: answer from structured tables and spreadsheets (aggregation, filtering, top-k).
3. **Graph-only**: answer from file, task, lineage, or entity relations.
4. **Cross-surface**: combine at least two routable surfaces, such as
   RAG + Table, Graph + RAG, RAG + Graph + Table.

Skill-flavored tasks (following a rubric-derived SOP) are represented by
attaching `applicable_skills` metadata to tasks of the four types above;
they do not form their own task type in v0.1.

The cross-surface tasks are the main contribution. They test whether a model can
decide that a question needs more than one knowledge representation.

## Evaluation

WorkSurface-Bench is designed to score more than final-answer correctness.

| Score | What it measures |
| --- | --- |
| Route score | Whether the agent selected the correct surfaces |
| Tool trace score | Whether the agent called appropriate tools in a reasonable order |
| Evidence score | Whether the answer is supported by the correct documents, rows, graph paths, or skills |
| Answer score | Whether the final answer is correct |
| Efficiency score | Tool calls, latency, and token cost |
| Safety score | Whether the agent avoided disallowed or destructive actions |

A default aggregate score can be:

```text
Final = 0.30 Answer
      + 0.30 Evidence
      + 0.25 Route
      + 0.10 Efficiency
      + 0.05 Safety
```

## Baselines

The initial benchmark should include:

- **No-tool LLM**: answer directly.
- **Always-RAG**: force every task through document search.
- **Naive router**: ask an LLM to choose one surface before answering.
- **ReAct all-tools**: expose all tools and let the agent explore.
- **Oracle route**: provide gold surfaces to estimate execution upper bound.
- **DataMind-style agent**: multi-tool enterprise agent over the full profile.

## Initial Build Plan

1. Start from Workspace-Bench-Lite.
2. Convert each workspace/persona into one multi-surface profile.
3. Convert documents into RAG-ready canonical text.
4. Convert CSV/XLSX files into a per-task table registry (DuckDB views over
   raw CSV, no cross-task schema unification) with provenance.
5. Convert file dependency graphs into surface graphs.
6. Convert rubrics and repeated workflow requirements into skill metadata
   attached to each task (Skill is not a routable surface in v0.1).
7. Derive atomic routing tasks from rubrics and task dependencies.
8. Implement route, evidence, and answer scorers.
9. Run the baselines and perform error analysis.

The first milestone is a small but complete **WorkSurface-Bench-Lite**:

```text
100 Workspace-Bench-derived tasks
300-800 atomic WorkSurface tasks
RAG + Graph + Table (Skills as task metadata)
No external benchmark mixing
No synthetic enterprise world as the main data source
```

## Design Principles

- **One coherent enterprise world** instead of a mixture of unrelated public
  datasets.
- **Workspace-Bench-derived source data** for realism and enterprise validity.
- **Canonical surfaces** so routing is evaluated separately from OCR and raw
  document parsing.
- **Evidence-first evaluation** so answers must be traceable.
- **Memory as an optional extension**, not a core shared-enterprise surface.

## Status

This repository currently contains the benchmark concept, initial schema, and
example task format. Conversion scripts, runners, and scoring utilities will be
added next.
