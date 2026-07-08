# WorkSurface-Bench Story Draft v0

**⚠️ 2026-07-09 UPDATE**: This doc was written before the related-work
survey returned. Its three-scenario fallback positioning is superseded
by the actual survey findings in `related_work_survey_raw.md` +
`related_work_zh.md`.

- Scenario A (someone already did multi-surface routing on public data
  like an "AMA-Bench"): **does not exist**. No published benchmark
  combines all four surfaces {docs, dep-graph, table, SOP} with a
  routing decision.
- Scenario B (WSB 2.0 adds routing): **low near-term probability** —
  SJTU team focused on workspace learning main track.
- Scenario C (tool-use benchmarks claim routing): **partially true** —
  MetaTool / T-Eval / API-Bank score routing at tool granularity
  (hundreds of tools); we score at surface granularity (4 surfaces).
  Clean distinction.

**Current paper-grade specification: `paper_spec_zh.md`.**
**Current related-work positioning: `related_work_zh.md`.**

This draft is preserved as historical thinking. Use the two docs above
for actual paper writing.

---
Written before the related-work survey returns. Pitch angle plus fallback
positioning for the three most-likely related-work scenarios. When the
survey lands, we tighten the differentiation section against real papers,
not hypothetical ones.

## The wedge (working headline)

> **Workspace routing is a distinct capability from workspace learning.**
> Existing enterprise agent benchmarks give the agent a flat workspace and
> ask "can you produce the deliverable". We project that same workspace
> onto four canonical knowledge surfaces (documents, dependency graph,
> tables, SOPs) and ask "do you know which surface to query for each
> question". Route selection turns out to be a separable — and severely
> under-measured — failure mode.

This is the sentence we build the paper around. Everything else is
support.

## The three claims

1. **Enterprise knowledge lives on multiple surfaces, but no current
   benchmark scores routing among them on realistic enterprise data.**
   Multi-surface QA benchmarks (HybridQA, OTT-QA, TAT-QA) stitch together
   unrelated public sources — Wikipedia text + web tables — and ask an
   integrated question. That measures integration, not routing. The
   knowledge surfaces are also not naturally present in one workplace;
   they are curated after the fact.

2. **Workspace-Bench-derived source data gives us naturalistic routing
   signal.** Workspace-Bench (2026) contains 388 real workspaces × 20k
   files across 5 personas. We project each workspace onto RAG / Graph /
   Table surfaces without synthesizing anything and without mixing
   external datasets. The routing signal is inherited from what the
   workspace actually contains.

3. **Route / Evidence / Answer decomposition changes the diagnostic
   picture.** A monolithic "task pass rate" hides whether an agent failed
   because it couldn't find the right files, chose the wrong knowledge
   form, or couldn't compute over what it found. We report those
   sub-scores and show they don't correlate — an agent good at Answer
   can be bad at Route, and vice versa. If they DO correlate perfectly,
   that's a negative result and still novel.

Claim 3 is empirical; it can only be validated on pilot data. If pilot
shows Route and Answer are 0.9 correlated, we drop claim 3 and lean on
1 + 2. Better to know this at pilot, not at paper submission.

## Positioning against likely neighbors

Fallback positioning for the three most-likely related-work scenarios.
When the survey returns, I'll replace these with the actual closest
papers.

### Scenario A: Someone already did multi-surface routing (e.g., AMA-Bench, HybridQA-style extended)

Our differentiators, in decreasing order of strength:

- **Single-world source data.** Their surfaces come from unrelated public
  datasets; ours from one workspace at a time. Their model can shortcut
  through domain cues ("this table is finance → SQL"); ours can't.
- **File-dependency graph as a surface.** Nobody else has a real,
  workspace-native dependency graph. STaRK is Freebase-style; ours is
  file lineage.
- **Route-Precision + Route-Recall as separate scores.** Most prior work
  reports a single "correct tool called" boolean. Distractor pressure
  (all surfaces loaded) makes precision meaningful.

If this scenario hits, the paper title becomes "workspace-derived
multi-surface routing" and we drop the "first" claim.

### Scenario B: Workspace-Bench 2.0 adds routing (unlikely near-term)

Differentiators:

- We split routing from workspace learning. WSB scores the deliverable;
  we score whether the agent chose the right surface even before writing.
- Our Graph surface is enriched (see solutions_v0 §1.2) with cross-file
  edges WSB doesn't materialize. Their file_dep_graph is one-hop only.
- Table surface via DuckDB view registry gives verifiable per-task SQL
  gold evidence that WSB rubrics can't check.

Move to publish before WSB releases v2.0 if signals suggest they're
heading in this direction.

### Scenario C: Agent tool-use benchmarks (τ-bench, ToolBench) claim they measure routing

Differentiators:

- Their tools operate on state that's synthetic and narrow (booking,
  retail). Ours operate on real workspaces with real files.
- They test whether the agent calls the right tool; we test whether the
  agent picks the right knowledge form. Different question — a tool is
  an *action*, a surface is an *information type*.
- We separate route from evidence from answer; they typically report
  final task success only.

## Contribution list (paper-style)

Applying Q1 = B (Skill demoted to task metadata):

1. **WorkSurface-Bench**, a benchmark for multi-surface knowledge routing
   on realistic enterprise workspaces. Three routable surfaces (RAG,
   Graph, Table); Skills as task-level metadata hints.
2. **Workspace-Bench derivation pipeline** that projects heterogeneous
   files onto canonical surfaces without mixing external datasets or
   synthesizing enterprise data.
3. **A four-part evaluation** (Route P/R/F1, Evidence, Answer, Efficiency)
   with an enumerated Safety threat set on ~15% of tasks.
4. **A contamination hygiene toolkit**: frozen source snapshot, closed-book
   probe, and hold-out submission server (v0.2).
5. **A pilot on Workspace-Bench-Lite (100 source tasks → ~500-800 atomic
   tasks)** with 6 baselines (No-tool / Always-RAG / Always-Table /
   Naive-router / ReAct-all-tools / Oracle-route) reporting the four sub-
   scores separately.

Item 5 is the empirical spine of the paper. Items 1-4 are contributions
in kind; item 5 is what makes them measurable.

## Abstract draft (target 200 words)

> Enterprise agents are increasingly deployed against workspaces where
> knowledge lives in many forms: unstructured documents, dependency graphs
> between files, tabular business records, and codified workflows. Most
> benchmarks isolate one form and evaluate retrieval-and-answer on it.
> This misses a distinct capability: **choosing which form of knowledge
> to query in the first place**. We introduce **WorkSurface-Bench**, a
> benchmark that projects real enterprise workspaces onto three canonical
> knowledge surfaces (documents, dependency graph, tables) and evaluates
> whether agents can route each question to the right surface, retrieve
> the right evidence, and produce the right answer. Source data derives
> from Workspace-Bench (2026); we do not mix external QA datasets or
> synthesize enterprise content. Evaluation decomposes into route
> precision/recall, evidence coverage, answer correctness, and a token
> efficiency budget, with a small enumerated safety threat set.
> WorkSurface-Bench-Lite (5 personas, ~700 atomic tasks) shows that
> route selection and answer correctness are weakly correlated for
> current agents: a router-oracle upper bound closes 30-45% of the gap
> between naive-routing agents and human performance, indicating that
> routing is a substantial, separable capability gap.

The 30-45% number is a placeholder; the pilot decides whether it's real.
If oracle-route doesn't help by that much, the abstract shifts to the
negative result: "route selection is not the bottleneck; retrieval on
the chosen surface is."

## Teaser figure sketch

One figure that captures the wedge:

```
        WorkSpace-Bench                          WorkSurface-Bench
   ┌────────────────────────┐              ┌────────────────────────┐
   │  agent, workspace of   │              │  agent, same workspace │
   │  20k heterogeneous     │              │  projected onto:       │
   │  files, one task       │              │    RAG surface         │
   │                        │      →       │    Graph surface       │
   │  → produce deliverable │              │    Table surface       │
   │                        │              │  one question          │
   │                        │              │  → answer + evidence   │
   └────────────────────────┘              └────────────────────────┘
             ↓                                       ↓
     workspace learning                       workspace routing
     "did you finish the job"                 "did you know where to look"
```

Below, a bar chart with 5 agent settings × 4 sub-scores. The intended
punchline visible in the figure: agents that lead on Answer don't
always lead on Route.

## Failure modes for this story

- **Pilot shows Route ≈ Answer (correlation > 0.85)**. Then claim 3 dies.
  Recovery: reposition as "we compress WSB into a fast, diagnostic
  routing eval; 70% cheaper for same signal".
- **Related-work has AMA-Bench doing this exact thing on public data**.
  Recovery: lean hard on "workspace-derived, single world" (scenario A
  above). Still publishable.
- **Table coverage < 30% (§1.1 gate)**. Two-surface benchmark = weak.
  Recovery: expand to Full-source or add cross-profile tasks as a fourth
  surface variant.
- **WSB v2.0 announces routing before we publish**. Recovery: pivot to
  Graph-surface enrichment as the primary contribution; multi-surface
  routing becomes secondary.

## What I need from you before v0.1 publication

1. Confirmation of the abstract's headline claim (workspace routing
   ≠ workspace learning). Everything above depends on this framing.
2. Green light on Skill = metadata (Q1 = B) — applied throughout the
   story above.
3. Publication venue / deadline (Q10). Determines Lite-only vs Full.
