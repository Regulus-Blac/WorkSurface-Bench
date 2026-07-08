# Open Questions

Decisions still pending your input before we start the pilot. Ordered
roughly by "how much do we lock in if we default without asking".

## 1. Should Skill remain a first-class surface?

Skills are the surface most at risk of being cut. Concerns:

- Every workable Skill has to pass the leak-check (solutions_v0 §1.4),
  which drops candidates aggressively.
- If Skills clusters are too generic ("check output file exists"), the
  agent's ability to route to them isn't diagnostic.
- If they're specific enough to be interesting, they leak the answer.

Options:
- **A. Keep as core surface** (current plan). Requires the leak-check
  procedure and a real skill authoring pass.
- **B. Demote to metadata**. Skills exist but are attached to tasks as
  hints, not a routable surface. Router decides only among RAG / Graph /
  Table. Cleaner benchmark, weaker "workflow" story.
- **C. Split off as an extension track**. Ship WorkSurface-Bench-Core as
  3-surface, and a WorkSurface-Bench-SOP extension for skill routing.

Default without your input: A. But if the pilot's leak-check kills most
candidates, we should fall back to B or C rather than ship a synthetic
skills layer.

## 2. Bilingual (en + cn) or English only?

Workspace-Bench-Lite has parallel en / cn splits. Do we release a bilingual
benchmark from day 1?

- **A. English only for Lite v0.1**. Half the download, half the LLM cost
  during construction, one language for judge calibration.
- **B. Bilingual from day 1**. Doubles construction work but reveals
  whether routing generalizes across languages — a real question.
- **C. English Lite, Chinese Full**. Only meaningful if we ship Full.

Default without input: A. Bilingual matters more at Full than at Lite.

## 3. Agent read-only or read-write on the profile?

Workspace-Bench tasks require file *writing* (produce
`onsite_hosting_execution_manual.doc`). WorkSurface-Bench atomic tasks are
QA-style — no output file required. But:

- If the agent gets a `write_file` tool, some tasks might be "solved" by
  producing an output file that fools the judge (safety threat 4 in §2.4).
- If it's strictly read-only, we can't reuse WSB's own agent harnesses
  (Codex, ClaudeCode) — they assume write access.

Options:
- **A. Read-only, no output file expected.** Simpler scoring; agents just
  return an answer.
- **B. Read-write, but scored on the returned answer, not the files.**
  Enables WSB harness reuse.
- **C. Read-write, output file counts.** Blurs the line with WSB itself
  and defeats the "atomic routing task" premise.

Default without input: A for Lite v0.1, revisit for Full.

## 4. Who runs the judge model?

Qualitative rubrics (solutions_v0 §1.3) need an LLM judge. Two decisions:

- **Judge model.** Options: `claude-opus-4-7`, `claude-opus-4-8`,
  `claude-sonnet-4-6`, `gpt-5`, or a smaller/cheaper judge. WSB uses
  Anthropic-compatible endpoints only.
- **Judge access.** For the held-out slice (§3), we need judge calls
  during eval — either the submitter provides judge credentials, or the
  submission server provides them and eats the cost.

Default without input: judge = `claude-opus-4-7`, submitter provides key.
Anchor cost per Lite eval: ~7,000 rubric-judgments × ~$0.03 per call =
~$210 per model per Lite run. Not cheap. Trigger for revisit: if pilot
shows a smaller judge (`sonnet-4-6`, `haiku-4-5`) reproduces the opus
judgments at ≥ 95% agreement, switch.

## 5. What's the total budget cap on Full?

Improvements §5 anchored costs at ~$200-300 for Full at $10/M output. But
that only counts the target model. Add:

- Judge calls: ~$100-200 per Full run
- Held-out probe (closed-book): ~$30
- Baseline suite (7 baselines × Full) if we want them: $2,000-3,000

Options:
- **A. Cap Full at 2,000 tasks.** Bottom of paper's range. Fits ~$500 per
  target model, judge included.
- **B. Cap at 1,000 tasks.** Halves cost; easier for external submissions.
  Trades statistical power.
- **C. No cap; publish the cost transparently.** Academic groups skip us.

Default without input: A. Publish per-task-average token count so users
can price their own runs before submitting.

## 6. Submission server: build now or later?

Held-out slice (§3.2) requires infrastructure. Options:

- **A. Ship Lite v0.1 without a held-out slice; add later.** Faster
  release, weaker contamination story.
- **B. Ship a minimal FastAPI server on a Tencent CVM / an equivalent
  host.** ~2 weeks of engineering.
- **C. Piggyback on an existing infra** (HELM-style leaderboard, HF
  Spaces, GitHub Actions matrix). Cheaper but less control.

Default without input: A for v0.1 release, plan B for v0.2. Publish the
closed-book contamination probe with v0.1 either way; it's cheap.

## 7. Repo name — WorkSurface-Bench or something else?

The current name is fine, but a few concerns:

- "Bench" is generic; the space is crowded.
- "Surface" is a Microsoft product line.
- Alternatives: `MultiSurfaceRAG-Bench`, `EnterpriseRoute-Bench`,
  `KRoute-Bench` (Knowledge Route), `WSF-Bench`.

Default without input: keep WorkSurface-Bench. Change only if the WSB
authors object to the derived-work naming (email them before v0.1).

## 8. Where do human annotations go?

The pilot needs 60 rubric labels (§1.3) and 100 LLM-edge adjudications
(§1.2). Two options:

- **A. You / your team label them.** Highest quality; slowest.
- **B. Contract via a labeling platform** (Scale, Surge, Argilla self-host).
  Faster but costs $1-3 per label and adds vendor dependency.
- **C. LLM-only with sampled human audits** (audit 10% at high effort).
  Cheapest but weaker.

Default without input: A for the pilot's 60 rubrics (you). C for the 100
edge cases (LLM + your spot-check).

## 9. Insufficient-evidence tasks — how aggressive?

Improvements §4.1 proposes 8-10% abstain tasks. Real number depends on:

- How many WSB tasks have a single load-bearing file that we can remove?
- Does removing the file leave a plausible "no info" state, or an obvious
  "this workspace is broken" state?

Options:
- **A. 8-10% target.** Real signal on abstention.
- **B. 2-3% target.** Just enough to prevent 0% abstention baselines.
- **C. Skip for v0.1, add in v0.2.**

Default without input: B for v0.1 (safer), A once we see how natural the
removals feel.

## 10. Publication path

- Are you writing this up as a workshop paper, a full conference paper, or
  an internal-only tech report?
- Is there a target venue / deadline?
- If external, do we need to negotiate re-distribution with the WSB
  authors (SJTU + Lark)?

This affects scope: Lite v0.1 alone is workshop-scale; Full + baselines +
error analysis is conference-scale.

Default without input: assume conference-scale, but ship Lite v0.1
publicly first (workshop or arXiv) so we can iterate.

---

## Answered decisions (log)

- **SQL surface renamed to Table** (2026-07-09) — done, applied across
  README, schema, examples, idea_zh, data_construction_plan_zh,
  improvements_v0, solutions_v0.
- **Memory is not a core surface** (from original design; carried forward).
- **Workspace-Bench-Lite English split is the pilot data source**
  (2026-07-09) — 249 MB downloaded locally, 100 tasks, gitignored.
- **Q1: Skill demoted to task metadata for v0.1** (2026-07-09) — routable
  surfaces are `{rag, graph, table}` only. Skills attached as
  `applicable_skills` on each task. Revisit after leak-check on Full
  yields ≥ 20 clean skills.
- **Q2: Lite v0.1 = English only** (2026-07-09) — bilingual deferred to
  Full or v0.2.
- **Q3: Agent is read-only on the profile** (2026-07-09) — atomic tasks
  return an answer + evidence; no output-file production. Enables clean
  Route/Evidence/Answer decomposition and closes safety threat 4.
