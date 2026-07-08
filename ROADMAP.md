# Roadmap

## Milestone 0: Concept and Schema

- [x] Define benchmark name and scope.
- [x] Decide that the main data source is Workspace-Bench-derived.
- [x] Exclude memory from the core shared-enterprise benchmark.
- [x] Add initial task schema and example JSONL format.
- [x] Draft data construction plan and scale targets.

## Milestone 1: Workspace-Bench-Lite Conversion

- [ ] Download or link Workspace-Bench-Lite.
- [ ] Inspect `data_manifest`, `file_dep_graph`, rubrics, and output files.
- [ ] Implement file-type routing:
  - documents to `kb_docs/`;
  - CSV/XLSX to SQLite;
  - dependency graph to `surface_graph.json`;
  - rubrics/workflows to skills.
- [ ] Produce the first canonical profile.

## Milestone 2: Task Derivation

- [ ] Convert rubrics into atomic QA tasks.
- [ ] Convert dependency graph entries into routing/evidence tasks.
- [ ] Generate cross-surface tasks for RAG + SQL, Graph + RAG, SQL + Skill,
      and RAG + Graph + SQL.
- [ ] Manually audit the first 100 derived tasks.

## Milestone 3: Runner and Scoring

- [ ] Implement an agent runner with tool trace logging.
- [ ] Implement route scorer.
- [ ] Implement evidence scorer.
- [ ] Implement answer scorer.
- [ ] Implement aggregate reporting.

## Milestone 4: Baselines

- [ ] No-tool LLM.
- [ ] Always-RAG.
- [ ] Naive router.
- [ ] ReAct all-tools.
- [ ] Oracle route.
- [ ] DataMind-style agent.

## Milestone 5: WorkSurface-Bench-Lite Release

- [ ] Release schema.
- [ ] Release conversion scripts.
- [ ] Release derived task metadata where licensing allows.
- [ ] Release baseline results.
- [ ] Write the technical report.
