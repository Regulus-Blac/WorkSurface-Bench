# Related-work survey raw output (2026-07-09)

Verbatim from the general-purpose research agent invoked on 2026-07-09.
Preserved for future reference and citation checking.

---

Baseline paper confirmed: **Workspace-Bench 1.0** (arXiv:2605.03596,
May 2026; SJTU + Feishu/Lark; 5 profiles, 74 file types, 20,476 files,
388 tasks, 7,399 rubrics; best agent 60%, human 80.7%). Authors led by
Zirui Tang, Xuanhe Zhou, Guoliang Li.

## 1. RAG benchmarks

- **KILT** — arXiv 2009.02252 (2020) — Multi-task retrieval-heavy QA
  over Wikipedia; single-corpus, single-modality; WorkSurface-Bench
  adds three non-text surfaces plus routing.
- **MTEB** — arXiv 2210.07316 (2022) — Embedding-model retrieval
  leaderboard (semantic, not agentic); orthogonal — could be the
  retriever inside our RAG surface.
- **MultiHop-RAG** — arXiv 2401.15391 (2024) — Multi-hop over news
  docs; still text-only, no surface routing.
- **CRAG (Comprehensive RAG)** — arXiv 2406.04744 (2024, Meta KDD Cup)
  — Factoid QA with dynamic + noisy corpora and mock KG APIs; touches
  KG lightly, but the "route" is not scored and enterprise files are
  absent.
- **RAGBench** — arXiv 2407.11005 (2024) — 100k industry-domain QA
  with the TRACe eval framework; evaluates the RAG *system quality*
  not surface selection.
- **LongBench v2** — arXiv 2412.15204 (2024) — Long-context multitask
  reasoning up to 2M words; tests context length, not tool/surface
  routing.

## 2. Text-to-SQL / Table QA

- **WikiTableQuestions** — arXiv 1508.00305 (2015)
- **Spider** — arXiv 1809.08887 (2018)
- **TAT-QA** — arXiv 2105.07624 (2021) — Hybrid table+text QA on
  finance reports; two surfaces but no explicit routing metric and no
  enterprise-workspace framing.
- **BIRD** — arXiv 2305.03111 (2023)
- **Spider 2.0** — arXiv 2411.07763 (2024)
- **BEAVER** — arXiv 2409.02038 (2024)

Family asks "can you write correct SQL when told the answer is in a
table?" WorkSurface-Bench asks "can you decide the answer is in the
table?" Could cite BIRD/Spider 2.0 as the natural Table sub-benchmark
our Table-router should dispatch to.

## 3. Graph-RAG / KG QA

- **HotpotQA** — arXiv 1809.09600 (2018)
- **STaRK** — arXiv 2404.13207 (2024) — Retrieval over semi-structured
  KBs (Amazon, MAG, PrimeKG); closest KG-flavored analog to our Graph
  surface, but KG-of-concepts not file-dependency.
- **GraphRAG (Microsoft)** — arXiv 2404.16130 (2024)
- **HippoRAG** — arXiv 2405.14831 (2024)
- **LightRAG** — arXiv 2410.05779 (2024)
- **GRAG** — arXiv 2405.16506 (2024)

File-dep-graph flag: no published KG-QA benchmark uses a
*file-dependency* graph. Closest concept lives in repo-level coding:
**RepoBench** (arXiv 2306.03091, 2023), **SWE-Explore**
(arXiv 2606.07297, 2026), **Repository Intelligence Graph / RIG**
(arXiv 2601.10112, 2026), **Repository-Aware File Path Retrieval**
(arXiv 2510.08850, 2025) — but only over code repos.

**Workspace-Bench itself is the only benchmark whose file-dep graph
mixes code, docs, spreadsheets, slides, images.**

## 4. Agent / tool-use benchmarks

- **AgentBench** — arXiv 2308.03688 (2023)
- **ToolBench / ToolLLM** — arXiv 2307.16789 (2023)
- **WebArena** — arXiv 2307.13854 (2023)
- **SWE-bench** — arXiv 2310.06770 (2023)
- **OSWorld** — arXiv 2404.07972 (2024)
- **τ-bench** — arXiv 2406.12045 (2024) — Airline/retail customer-
  service with policy adherence; policy ≈ our Skills, but only one
  policy source.
- **MLE-bench** — arXiv 2410.07095 (2024)
- **TheAgentCompany** — arXiv 2412.14161 (2024) — Multi-app enterprise
  simulation.
- **AppWorld** — arXiv 2407.18901 (2024)

## 5. Enterprise / workspace-agent benchmarks

- **WorkArena (ServiceNow)** — arXiv 2403.07718 (2024)
- **WorkArena++** — arXiv 2407.05291 (2024)
- **SheetAgent** — arXiv 2403.03636 (2024)
- **SpreadsheetLLM** — arXiv 2407.09025 (2024)
- **AssistantBench** — arXiv 2407.15711 (2024)
- **CRMArena (Salesforce)** — arXiv 2411.02305 (2024)
- **TheAgentCompany (CMU)** — arXiv 2412.14161 (2024)
- **UI-CUBE (UiPath)** — arXiv 2511.17131 (2025)
- **OfficeQA Pro** — arXiv 2603.08655 (2026) — 133 questions over 89k
  pages of Treasury Bulletins with 26M numeric values.
- **PPT-Eval** — arXiv 2606.31154 (2026)
- **Workspace-Bench 1.0** — arXiv 2605.03596 (2026)

"ACT" not found as enterprise-agent-workflow benchmark on arXiv.

## 6. Multi-surface / heterogeneous-source (KEY category)

- **HotpotQA** — arXiv 1809.09600 (2018)
- **HybridQA** — arXiv 2004.07347 (2020) — 2 surfaces (table, doc),
  no routing metric.
- **OTT-QA** — arXiv 2010.10439 (2020) — 2 surfaces.
- **MMQA / MultiModalQA** — arXiv 2104.06039 (2021) — 3 surfaces
  (text+tables+images), no KG, no SOP.
- **HeteroQA** — arXiv 2112.13597 (2021)
- **CARP** — arXiv 2201.05880 (2022)
- **FinanceBench** — arXiv 2311.11944 (2023) — 10k financial-report QA
  with mixed table+text.
- **MMOA-RAG / TableRAG** — arXiv 2506.10380 (2025)
- **T²-RAGBench** — arXiv 2506.12071 (2025) — 23k text-and-table QA
  requiring retrieval before numerical reasoning.
- **LIT-RAGBench** — arXiv 2603.06198 (2026) — RAG generator eval with
  categories including Logic/Integration/Table/Reasoning/Abstention;
  spirit closest to per-surface scoring.
- **UniversalRAG / Ask-in-Any-Modality survey** — arXiv 2502.08826
  (2025)
- **OmniEval** — arXiv 2412.13018 (2024)
- **MRAMG-Bench** — arXiv 2502.04176 (2025)
- **CRAG-MM** — arXiv 2510.26160 (2025)
- **SPARTA** — arXiv 2602.23286 (2026) — Tree-structured multi-hop QA
  over text + tables with aggregations; 2 surfaces.
- **OfficeQA Pro** — arXiv 2603.08655 (2026) — Doc + numeric
  reasoning; one corpus.
- **AMA-Bench** — arXiv 2602.22769 (2026) — Long-horizon agent memory,
  NOT the multi-surface AMA suspected.

**No public benchmark combines all four of {unstructured docs,
dependency graph, structured tables, procedural skills} with a routing
decision.**

## 7. Route selection as explicit metric

- **MetaTool** — arXiv 2310.03128 (2023) — Explicitly scores "should
  I use a tool?" and "which tool?" over 200 tools.
- **API-Bank** — arXiv 2304.08244 (2023)
- **T-Eval** — arXiv 2312.14033 (2023) — Step-level decomposition.
- **ToolQA** — arXiv 2306.13304 (2023)
- **RouterBench** — arXiv 2403.12031 (2024) — Multi-LLM routing,
  different problem.
- **Router-R1** — arXiv 2506.09033 (2025)
- **Retrieval Models Aren't Tool-Savvy** — arXiv 2503.01763 (2025)
- **Adaptive-RAG** — arXiv 2403.14403 (2024) — Learns to route by
  question complexity (no-retrieve / single-hop / multi-hop).

**None score selection across heterogeneous knowledge surfaces
(docs vs. dep-graph vs. table vs. SOP) as a first-class metric.**

## Bottom line

Is anyone doing what WorkSurface-Bench does? **No.** Closest neighbors
carve orthogonal axes:

- Workspace-Bench 1.0 sits on realistic file-dep workspaces but scores
  end-to-end.
- STaRK blends unstructured + relational retrieval but on product/KG
  data, no table or SOP surface.
- HybridQA / OTT-QA / MMQA / SPARTA / T²-RAGBench combine 2-3 surfaces
  but never all four and never with a file graph.
- MetaTool / T-Eval / API-Bank score selection but of tools/APIs, not
  knowledge surfaces.
