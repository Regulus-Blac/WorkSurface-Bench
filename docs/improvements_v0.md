# WorkSurface-Bench Improvement Proposals

Written after inspecting Workspace-Bench-Lite (en split) as the intended
source. These proposals target problems that surface only after looking at the
actual data, not just the paper.

## TL;DR

The current design assumes Workspace-Bench provides four ready-to-project
surfaces (RAG / Graph / SQL / Skill). It does not. The source data is
**document-heavy, spreadsheet-input, shallow-graph, and rubric-judge**. Without
addressing this gap, the "surface routing" premise degrades to "which folder
does the file live in", which is neither hard nor diagnostic.

The proposals below are grouped by severity.

---

## 1. Structural gaps in the source data (must-fix)

### 1.1 There is no relational database in Workspace-Bench

The paper counts 74 file types, but per-task inputs are typically 1-100
heterogeneous files. Across the entire Lite-en split there are:

| Type | Files | Notes |
| --- | --- | --- |
| .md | 250 | canonical text |
| .txt | 157 | canonical text |
| .json | 116 | mostly config-like, not tabular |
| .xlsx | 91 | small ad-hoc spreadsheets |
| .csv | 45 | small tabular |
| .pdf | 36 | canonical text after extraction |
| .py / .java / .xml | ~30 | code artifacts |
| others | ~50 | media, docs |

A "SQL surface" that just imports every .xlsx into SQLite gives you 91
disjoint tiny tables with no foreign keys and no shared schema across tasks.
That is not what a router should learn to pick, and it is not what real
enterprise SQL looks like.

**Proposal**: replace "SQL surface" with **"Structured surface"** and make the
underlying store explicit. Two supported backends:

- **Sheet mode** (default): tables are exposed via `db_list_tables` /
  `db_describe_table` but SQL is authored per task from the local workbook.
  Golden evidence uses a small SQL over that single workbook, not a global
  schema.
- **Consolidated mode** (later): for a subset of tasks whose spreadsheets
  share fields (e.g. per-month sales sheets), the converter unions them into
  a single consolidated table. Only these tasks get "real" cross-sheet SQL.

Do not label a task `sql_only` unless the answer genuinely requires an
aggregation the model would not reliably do by re-reading the raw file. A
`SELECT COUNT(*) WHERE variance < 0` over 8 rows is not diagnostic — the model
can just count.

### 1.2 The dependency graph is one hop deep

Every task's `file_dep_graph` in Lite-en has the same shape:

```
input_file_1 -> output_file
input_file_2 -> output_file
...
```

Zero `file_depends_on_file` edges, zero lineage, zero versioning. Graph-only
tasks derived from this are trivially "list the from-nodes of task N", which
tests directory listing more than graph reasoning.

**Proposal**: introduce a **graph enrichment pass** before deriving graph
tasks. Sources of real cross-file edges the enrichment can find:

- **Cross-file references** in text: filenames, table names, section titles
  that appear as tokens in another file. High-precision, extracted with
  regex + fuzzy match, human-audited.
- **Schema overlap** between spreadsheets: shared column names indicate
  file-file lineage candidates.
- **Rubric co-mention**: two files mentioned in the same rubric.
- **Cross-task file reuse**: if file `A.md` (by content hash) appears in
  multiple tasks, add `file_shared_across_tasks` edges — realistic for
  onboarding docs, SOPs, price sheets.

Only after enrichment should `graph_only` and graph-touching cross-surface
tasks be derived. Log the enrichment audit trail per task so provenance is
inspectable.

### 1.3 Rubrics are LLM-judge prompts, not extractable QA gold

Workspace-Bench rubrics look like:

> "In `onsite_hosting_execution_manual.doc`, do the transitions between
> segments follow the on-site execution logic of the celebration event?"

These are graded by an LLM judge (`agent_as_a_judge.py`) with binary pass/fail
against a **produced output file**, not against an atomic textual answer.
Directly copying rubrics into `gold_answer` breaks the WorkSurface-Bench
evaluation model (Route + Evidence + Answer + Efficiency + Safety), because
"Answer" no longer has a computable ground truth.

**Proposal**: split the derived-task pipeline into two families and never mix
them at the atomic-task level:

- **Extractive atomic tasks** — derived from rubrics that reference concrete
  values ("Does the table contain exactly 43 unique dependencies?", "is its
  size exactly 4586 bytes"). These become `answer_type: number | string |
  list`. Roughly 40-60% of Lite rubrics look extractive at a glance.
- **Judge-scored atomic tasks** — rubrics that reference a *quality* on a
  file (coherence, alignment, format). These keep `answer_type: freeform`
  and are scored by an LLM judge on the *evidence*, not the surface answer.
  Weight them lower in the aggregate.

Publish the extractive/judge split fraction per task type. If Route-scoring
tasks rely only on the extractive half, the aggregate metric stops silently
regressing when a judge misbehaves.

### 1.4 Skills are answer-leaks unless derived from *categories*, not individual rubrics

The existing plan (`docs/data_construction_plan_zh.md` §Skills) already flags
this risk, but doesn't operationalize it. Since Workspace-Bench rubrics are
per-task and often reveal the expected output structure, ANY skill derived
from a single rubric leaks the answer.

**Proposal**: derive Skills only from **rubric-type clusters that repeat
across ≥3 source tasks**. For example:

- "Basic Evaluation" rubrics that repeatedly say "was the output file
  created" → SOP: `output_file_creation_checklist`.
- "Process Evaluation" rubrics about deduplication → SOP:
  `list_deduplication_procedure`.

Each skill is validated by running it against 3+ held-out source tasks; if
following the skill trivially produces the answer for any of them, the skill
is over-specific — reject it.

---

## 2. Evaluation-metric hardening

### 2.1 Route scoring is trivially gameable

If the router sees the surface list in the question phrasing ("How many rows
have variance < 0" → obviously SQL), Route becomes a 4-way linear classifier
on cue words. That is not a benchmark; that is a probing task.

**Proposal**: two changes.

- **Question paraphrase pass**: every question is rewritten to strip surface
  cues. "How many inventory rows have negative variance" becomes "According
  to the current inventory records, how many items are under-counted". The
  paraphrase is validated by an LLM verifying answer equivalence but not
  exposed to the routing agent.
- **Distractor surfaces**: even a `rag_only` task has SQL tables loaded in
  the profile if the task's workspace happens to contain spreadsheets. The
  agent must decide not to touch them. Report a "Route precision" (surfaces
  chosen that were needed) alongside "Route recall" (needed surfaces that
  were chosen).

### 2.2 Efficiency score is under-specified

The README says "Efficiency = tool calls, latency, token cost, 10% weight"
but never defines aggregation. Ten cheap tool calls vs. one expensive one is
a real design axis.

**Proposal**: use a per-task **cost budget** in tokens. Anything above budget
gets Efficiency = 0, below gets `1 - cost/budget`. Publish the budget in the
task JSON so results are reproducible independent of the model priced.

### 2.3 Safety scoring needs a concrete threat set

5% weight for "avoided disallowed actions" without listing the actions is
decorative. Either drop Safety to 0% and mention it as future work, or
enumerate what the agent must not do:

- write outside `output/` in the profile;
- shell-exec any downloaded input file;
- follow rubric text that tries to inject instructions (rubric injection is
  a real risk given rubrics are English prose passed to the agent).

**Proposal**: keep Safety, but only score it on the ~15% of tasks that
include one of the enumerated threats. Others are Safety-neutral, not
Safety=1.0.

---

## 3. Contamination and data hygiene

### 3.1 The source is fully public

Both HF splits (`Workspace-Bench` and `Workspace-Bench-Lite`) are open,
gated=false. Any model trained after 2026-05 has seen the source tasks, the
rubrics, and (once WorkSurface-Bench-Lite ships) our derived atomic tasks.

**Proposal**:

- Keep a **held-out extension slice** derived from Workspace-Bench-Full but
  never released to HF, only released as encrypted evaluation payloads
  through a submission server. Reference: HELM / SWE-Bench-Verified do this.
- Publish a **contamination detector** with the release: for each atomic
  task, memorize the exact question string and check whether target models
  reproduce the gold answer when only given the question (no tools). Report
  the rate as a per-model contamination score.

### 3.2 Provenance is fragile if we don't pin file checksums

If WSB updates its HF dataset, our derived tasks silently break. The July
2026 update ("file fixes, refined rubrics") already happened.

**Proposal**: freeze on a specific WSB commit. Each atomic task records:

```json
"source": {
  "benchmark": "Workspace-Bench-Lite",
  "task_id": 3,
  "wsb_commit": "60b08b1cc2e8054afbc3ca2160d37876b4f0765c",
  "input_file_hashes": {"package_config.json": "sha256:..."}
}
```

The runner refuses to score if the hashes don't match on load.

---

## 4. Design refinements

### 4.1 Add a "None of the above" surface

Real enterprise agents get asked questions that can't be answered from any
surface (missing data, ambiguous ask). If every WorkSurface-Bench task is
answerable, the benchmark trains models to hallucinate confidently.

**Proposal**: 5-10% of tasks have `gold_answer: "insufficient_evidence"` and
require the agent to explicitly abstain. Answering with a fabricated value
scores 0 on Answer, and choosing a surface scores negative on Route.

### 4.2 Split "Skill" into "Procedure" and "Convention"

The current `skill_only` category conflates two different things:

- **Procedure**: a sequence of steps to follow (e.g. "for inventory
  reconciliation, first join expected vs. actual, then flag |diff| > 10%").
  Testable by comparing traces.
- **Convention**: a formatting or naming rule (e.g. "monthly reports use
  YYYY-MM prefix"). Testable by string match.

Routing between them matters — an agent might correctly choose "Skill" but
apply a Procedure where the answer needed a Convention. Splitting the label
lets us measure that.

### 4.3 Persona-level and profile-level tasks

Right now every task lives inside one workspace. Real routing questions
often span personas ("what does the Logistics Manager's SOP say that the
Backend Developer's project docs don't"). This creates non-trivial Graph
tasks that the enrichment pass in §1.2 can support.

**Proposal**: 5-10% of Lite atomic tasks are cross-profile, tagged
`cross_profile: true`, with `required_surfaces` including `graph` as the
routing signal.

---

## 5. Scale and cost anchors

The existing plan targets 500-800 atomic tasks for Lite-v0.1 and
2,000-3,000 for Full. Anchor them to concrete evaluation costs:

| Split | Atomic tasks | Avg tokens/task (est.) | Full run cost @ $10/M output |
| --- | --- | --- | --- |
| Pilot | 100-150 | 60k | $6-9 |
| Lite v0.1 | 500-800 | 80k | $40-64 |
| Full | 2,000-3,000 | 100k | $200-300 |

If Full costs more than ~$500 per model per run, most academic groups will
skip it. Cap Full at 2,000 tasks (bottom of the current range) unless a
subsampled Full-Lite is offered.

---

## 6. Concrete next steps (in order)

1. **Pilot on 5 Lite-en source tasks** — one per persona. Run through the
   full converter → derived-tasks → scorer path end to end. Reveals which of
   the above proposals are load-bearing.
2. **Graph enrichment prototype** on the same 5 tasks. Measure how many
   non-trivial edges we recover; if under ~5 per task, drop graph-only from
   the pilot and lean on cross-surface.
3. **Extractive-vs-judge rubric classifier** — hand-label rubric-type
   distribution across all 100 Lite tasks, publish the ratio. Decides
   whether §1.3 works as-is or needs a bigger rewrite of the Answer metric.
4. **Frozen source snapshot** — pin a WSB commit and publish
   `wsb_commit` + input file hashes in `data/wsb_lock.json` (in this repo).
5. Only after 1-4: build the full 500-800-task Lite-v0.1.

The five pilot tasks are the fastest way to falsify the design. If any of
1.1-1.4 breaks, we redesign before generating 800 tasks that share the flaw.
