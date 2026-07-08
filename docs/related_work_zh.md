# WorkSurface-Bench Related Work（中文）

本文档整理了论文 Related Work 章节可直接引用的核心对比对象。基于
2026-07-09 完成的相关工作调研（见 `related_work_survey_raw.md`）。

## 一句话差异化（可放 Intro / Abstract 结尾）

> **WorkSurface-Bench is the first benchmark to (a) place four
> categorically distinct knowledge surfaces — unstructured docs, file
> dependency graph, DuckDB-queryable tables, and procedural SOPs/rubrics
> — over the same enterprise workspace, and (b) score the router as a
> first-class metric decoupled from answer correctness.**

Prior work 只做二选一：
- **要么融合 surface 但不评路由**（HybridQA、OTT-QA、MMQA、SPARTA）
- **要么评路由但没有异构 surface**（MetaTool、T-Eval、API-Bank）

## 五个必须放进 Related Work 章节的对比对象

（每个都要在论文 Section 2 独立段落 + 出现在 Table 1 comparison
matrix 里）

### 1. Workspace-Bench 1.0（我们的源数据 + 最直接的 baseline）

- arXiv 2605.03596，SJTU + Feishu/Lark，2026-05
- 388 tasks, 20k files, 7,399 rubrics
- **差异**：WSB 评"能不能产出交付物 (end-to-end)"；我们评"能不能
  路由到正确 surface (decomposed)"。WSB 的 file_dep_graph 只有一跳；
  我们做了增强。
- **关键 sentence**："We build on Workspace-Bench source data but change
  the evaluation target from workspace learning (produce the deliverable)
  to workspace routing (choose the right knowledge form)."

### 2. STaRK (Leskovec, Stanford, 2024)

- arXiv 2404.13207
- Retrieval over semi-structured KBs（Amazon、MAG、PrimeKG），blend
  text + entity relations
- **差异**：他们的 graph 是**概念级 KG**（entity-relation-entity）；
  我们的 graph 是**文件级 dependency**（file-depends-on-file、
  file-supports-output）。KG 是本体，file-dep 是工件血缘。
- **关键 sentence**："STaRK evaluates KG-augmented retrieval; our Graph
  surface encodes workspace-native file lineage, a category not covered
  by any published KG-QA benchmark."

### 3. HybridQA / OTT-QA / T²-RAGBench（多面 QA 但两面封顶）

- HybridQA (arXiv 2004.07347, 2020) — Wikipedia table + linked passages
- OTT-QA (arXiv 2010.10439, 2020) — 400k tables + 5M passages
- T²-RAGBench (arXiv 2506.12071, 2025) — 23k text-and-table QA
- **差异**：他们把 text + table 融合起来问一个整合问题，surface
  routing 不是评测目标。**只有两个 surface，没有 KG，没有 SOP。**
- **关键 sentence**："Multi-source QA benchmarks fuse two surfaces (text
  and table) and evaluate integrated answering. WorkSurface-Bench treats
  surface selection as a separately scored capability across four
  surfaces."

### 4. MetaTool / T-Eval / API-Bank（路由但只有 tool 粒度）

- MetaTool (arXiv 2310.03128, 2023) — 200 tools, "should I use tool?"
  + "which tool?" 分别打分
- T-Eval (arXiv 2312.14033, 2023) — 分 instruct/plan/reason/retrieve/
  understand/review 六个步骤打分
- API-Bank (arXiv 2304.08244, 2023) — ~50 APIs 的 tool-call
- **差异**：他们的粒度是**工具**（数以百计），我们的粒度是**知识面**
  （4 个）。tool 是操作载体，surface 是信息类型。
- **关键 sentence**："Routing benchmarks like MetaTool score tool-level
  selection over hundreds of APIs; WorkSurface-Bench introduces
  knowledge-surface-level routing, a distinct abstraction that groups
  many tools by the type of information they access."

### 5. TheAgentCompany (CMU, 2024)

- arXiv 2412.14161
- 企业模拟：GitLab、RocketChat、OwnCloud 上的多 app 任务，跨部门
- **差异**：他们评的是"app 切换"（该开 GitLab 还是 RocketChat），
  我们评的是"知识形式切换"（该查文档还是查表格）。**app 是动作
  载体，surface 是信息类型**——同一个 app 里可以有多个 surface
  （GitLab 里既有 markdown docs 又有 CSV），同一个 surface 可以在
  多个 app 里（docs 分散在 Confluence + Google Drive）。
- **关键 sentence**："App-level enterprise benchmarks like
  TheAgentCompany measure application switching; we measure
  knowledge-form switching, which is orthogonal — a single application
  can host multiple surfaces, and a single surface can span multiple
  applications."

## Comparison table（论文 Section 2 或 Table 1）

| Benchmark | Surfaces | Route metric | Enterprise source | Skill/SOP | Year |
| --- | --- | --- | --- | --- | --- |
| KILT | 1 (docs) | – | – | – | 2020 |
| HybridQA | 2 (docs+table) | – | – | – | 2020 |
| OTT-QA | 2 (docs+table) | – | – | – | 2020 |
| MMQA | 3 (docs+table+image) | – | – | – | 2021 |
| Spider / BIRD | 1 (SQL) | – | – | – | 2018/23 |
| STaRK | 2 (docs+KG) | – | – | – | 2024 |
| MetaTool | – (tools) | ✓ | – | – | 2023 |
| T-Eval | – (tools) | ✓ (step-level) | – | – | 2023 |
| τ-bench | 2 (docs+policy) | – | – | ✓ (single) | 2024 |
| TheAgentCompany | – (apps) | – | ✓ | – | 2024 |
| OfficeQA Pro | 1 (docs+numeric) | – | – | – | 2026 |
| SPARTA | 2 (docs+table) | – | – | – | 2026 |
| LIT-RAGBench | 1 (per-category) | 部分 | – | – | 2026 |
| Workspace-Bench | 4 (混合) | – | ✓ | – | 2026 |
| **WorkSurface-Bench (ours)** | **4 (分离评测)** | **✓ (first-class)** | **✓** | **✓ (metadata)** | 2027 |

**这张表是论文的定位核弹**：只有我们最后一行同时在 4 个 column 上
打勾。审稿人扫一眼就知道差异化。

## 更新的 Fallback plan（替换 story_v0/story_zh 里的三种假设场景）

**新的 fallback plan**：调研确认场景 A（AMA-Bench 类抢跑）**不存在**，
场景 B（WSB 2.0 抢发路由）**近期概率低**（SJTU 团队专注 workspace
learning 主线），场景 C（tool-use benchmark 自称路由）**部分成立**但
可以用"知识面粒度"清楚区分。因此原故事里的三个 fallback 段落可以砍
掉，只留一个真实威胁：

**真实威胁**：**MetaTool 的作者或 STaRK 团队**可能扩展工作把路由推
到 knowledge-surface 粒度。应对：**arXiv 立即挂预印占位**（Timeline
2026-12），最迟 2027-03 投 COLM。

## 与几个 concurrent 2026 论文的距离

调研找到三篇 2026 年论文时间上紧邻我们，要在 related work 里正面
提及：

- **OfficeQA Pro (arXiv 2603.08655)** — 89k 页 Treasury Bulletins 上的
  doc + numeric 推理。**单 corpus**，我们是多 workspace。
- **SPARTA (arXiv 2602.23286)** — tree-structured multi-hop text+table
  QA。**两面**，我们是四面。
- **LIT-RAGBench (arXiv 2603.06198)** — per-category (Logic/Integration/
  Table/Reasoning/Abstention) 分别打分。**精神最像**（我们也做
  per-surface breakdown），但他们仍是单 corpus。

**Cite 这三篇**，说 "concurrent work moves toward category-decomposed
evaluation but stops short of heterogeneous surfaces or workspace source
data" 表明我们了解 landscape。

## Skill 那面的未来对比（v0.2 恢复 Skill routing 时）

- **τ-bench (2024)** — 单一 policy 源的 policy-adherence 评测。**最直
  接对比**：他们只有一个 policy document，我们如果恢复 Skill routing
  会有多个 SOP 让 agent 选。
- **AutoAct 类 self-planning** — 是训练框架不是 benchmark，暂时不用
  对比。

## 更新 paper_spec_zh 的部分

以下改动写入下一次 paper_spec 更新：

1. **§1 Contributions C1** 加一句 "the first benchmark placing four
   categorically distinct surfaces over the same workspace"，引 STaRK
   / HybridQA / MetaTool 作对比。
2. **§3.5 Analysis Q1（cross-surface 难在哪）** 加一条："comparison
   with TheAgentCompany's app-switching baseline shows our surface-
   switching failures are distinct from app-switching failures"。
3. **§3.6 Fallback plan** 去掉之前的 "AMA-Bench 类已存在" 这条
   （调研已证明不存在），换成 "MetaTool/STaRK 团队扩到 knowledge-
   surface 粒度" 的抢发威胁 → 触发条件 = arXiv 预印被拖到 2027-01
   之后。
4. **§4 Writing timeline** 12 月的 arXiv 提前到 **2026-11 末**，避免
   MetaTool/STaRK 后续工作 in-flight 阶段撞车。

## 引用格式（BibTeX，Related Work 章节用）

（略——写论文时用 `arxiv.py` 一键抓，此处只列 arXiv ID）

必引：2605.03596（Workspace-Bench）、2404.13207（STaRK）、
2004.07347（HybridQA）、2010.10439（OTT-QA）、2310.03128（MetaTool）、
2312.14033（T-Eval）、2412.14161（TheAgentCompany）、
2406.12045（τ-bench）、1809.08887（Spider）、2411.07763（Spider 2.0）、
2305.03111（BIRD）、2603.08655（OfficeQA Pro）、2602.23286（SPARTA）、
2603.06198（LIT-RAGBench）。

可选：2210.07316（MTEB）、2401.15391（MultiHop-RAG）、
2406.04744（CRAG）、2404.16130（GraphRAG）、2403.12031（RouterBench）、
2403.14403（Adaptive-RAG）、2403.07718（WorkArena）、
2411.02305（CRMArena）、2306.03091（RepoBench）、2310.06770（SWE-bench）。
