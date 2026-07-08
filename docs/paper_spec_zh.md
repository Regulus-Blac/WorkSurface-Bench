# WorkSurface-Bench 论文规格 v1（中文，取代 story_v0/story_zh）

从"叙事"升级到"审稿人能圈起来的东西"。三部分：contributions、dataset
spec、experiment matrix。Pilot 完成后所有具体数字回填。

**前提锁定**：
- 主线 finding = **Route ≠ Answer 分离**
- 规模 = **Lite-only**（500-800 atomic tasks，5 models）
- 投稿主目标 = **NeurIPS 2027 D&B**（2027-06 截）+ 备胎 **COLM 2027**（2027-03 截）

---

## 1. Contributions（审稿人角度）

写论文时每一条要能对应一到两个具体产物（数据字段、脚本、章节图表）。
不写"我们探索了 X"，写"我们发现 X 并提供 Y"。

### C1. 一个 workspace-native、多知识面路由的评测基准

- 三个可路由 surface：RAG、Graph、Table
- 5 个 persona × 100 source tasks × 平均 6 派生 → **500-800 atomic tasks**
- Skill 作 `applicable_skills` 元数据，非路由
- 产物：`data/worksurface_lite/`（HF dataset）+ `schemas/task.schema.json`

**定位（基于 2026-07 related work 调研，见 `related_work_zh.md`）**：
第一个把四种类别上不同的知识面（unstructured docs / file dependency
graph / DuckDB-queryable tables / procedural SOPs）放在同一个企业
workspace 上评测的 benchmark。相邻工作分两类：**融合 surface 但不评
路由**（HybridQA、OTT-QA、MMQA、SPARTA 停在两面）；**评路由但没有
异构 surface**（MetaTool、T-Eval、API-Bank 只有 tool 粒度）。**没有
一篇论文同时做两件事。**

**§2 数据字段一一对应。审稿人问"到底有什么"看 §2。**

### C2. 一条从 Workspace-Bench 派生的 pipeline，不合成、不混外部

- 输入：Workspace-Bench-Lite 的 100 源任务
- 输出：三个 canonical surface + atomic tasks + 溯源
- 关键设计：**不做**跨任务事实表合成，**不**引入 RAGBench/BIRD/STaRK
- 产物：`scripts/convert_*.py`（每个 surface 一个）+ `data/wsb_lock.json`
  （commit hash + 所有输入 sha256）

**回答"你的数据从哪来"。审稿人看这一条判断诚实度。**

### C3. Route / Evidence / Answer / Efficiency 四部分诊断评分协议

- Route：precision、recall、F1（distractor pressure 下）
- Evidence：per-surface hit rate 加权 F1
- Answer：按 answer_type 归一化（`number` 5% 容差、`list` 顺序无关
  set F1、`boolean` exact、`freeform` LLM judge + operational anchors）
- Efficiency：`1 - tokens_used / (2 * oracle_optimal_tokens)`
- Safety：只在 ~15% 含威胁 task 上评（其余 NA）
- 产物：`scoring/`（Python 模块）+ `runs/*.yaml` reference configs

**这是方法论贡献。用它论证 Route ≠ Answer 之前必须先证明协议本身
可信——用 §3.5 的 ablation。**

### C4. 主 finding：Route 和 Answer 在当前 agent 上是可分离的能力

**这是论文的经验心脏。** 由 §3 的 Table 1 和 Figure 3 支撑：

- **Table 1**：Model × sub-score matrix。行是 5 个 agent 设定，
  列是 Route F1 / Evidence / Answer / Efficiency / Aggregate。
- **Figure 3 (a)**：Route F1 vs Answer 散点图（每个点一个 agent×task
  bucket），Spearman ρ 报在图注。**预期 0.4-0.7**（弱到中度相关）。
  如果 ρ > 0.85 → 主线换成 §3.6 fallback。
- **Figure 3 (b)**：Oracle-route baseline（给出正确 surface 集合）
  与 Naive-router 的 Answer 差距。**预期关闭 30-45% gap**。
- **Table 2**：per-surface breakdown。展示不同 agent 在 rag_only /
  table_only / graph_only / cross-surface 上的差异。**预期 cross-
  surface 掉分最重**。

### C5. Contamination hygiene 工具包

- `wsb_lock.json`：冻结 Workspace-Bench commit + per-file sha256
- `probe/closed_book.py`：闭卷污染 probe，报 per-model 命中率
- 每个 model 在 leaderboard 上标 contamination_flag（closed-book > 20%
  的加旗）
- 产物：随 v0.1 一同发布

**Hold-out submission server 明确写为 v0.2 future work，不承诺 v0.1
交付。**

---

## 2. Dataset 打成什么样

### 2.1 规模（回填 pilot 数字）

| 维度 | 数字 | 备注 |
| --- | --- | --- |
| Persona | 5 | 承袭 WSB |
| Source tasks | 100 | WSB-Lite-en |
| Atomic tasks | 500-800 (target 700) | pilot 决定实际 |
| Routable surfaces | 3 | RAG, Graph, Table |
| Skills as metadata | ~15-30 | leak-check 后剩下的 |
| Total input file count | ~780 | WSB-Lite-en 全部 |
| Total workspace size | ~250 MB | 已下载 |

### 2.2 Atomic task 分布（目标）

| task_type | 目标数量 | 占比 |
| --- | --- | --- |
| rag_only | 150-200 | 25-28% |
| table_only | 100-150 | 15-20% |
| graph_only | 100-150 | 15-20% |
| cross_surface | 250-350 | 40-45% |

**cross-surface 分组**（占 cross-surface 总数）：

- RAG + Table：30%
- RAG + Graph：30%
- Graph + Table：15%
- RAG + Graph + Table：15%
- 含 abstain（`INSUFFICIENT_EVIDENCE`）：8-10% 的 Lite 总量，
  分布在所有 task_type 上（不集中在某一面）

### 2.3 每条任务包含的字段

参见 `schemas/task.schema.json`。审稿人层面能圈的：

```json
{
  "id": "ws_lite_0003_q02",
  "source": {
    "benchmark": "Workspace-Bench-Lite",
    "task_id": 3,
    "wsb_commit": "60b08b1c...",
    "input_file_hashes": {"package_config.json": "sha256:..."}
  },
  "question": "According to the dependency lists, how many unique libraries...",
  "difficulty": "medium",
  "task_type": "cross_surface",
  "required_surfaces": ["rag", "table"],
  "gold_tools": ["kb_search", "table_query"],
  "applicable_skills": ["list_deduplication"],
  "gold_answer": 43,
  "answer_type": "number",
  "gold_evidence": [
    {"surface": "rag", "file": "dependency_item_1.md",
     "claim": "lists Spring Boot"},
    {"surface": "table", "table": "package_config",
     "query": "SELECT COUNT(DISTINCT name) FROM package_config"}
  ],
  "efficiency_budget_tokens": 12000,
  "safety_threats": [],
  "notes": ""
}
```

`efficiency_budget_tokens` 通过 oracle-route baseline 预跑得到。
`safety_threats` 是 §1.3 的四类枚举，只在 ~15% task 上非空。

### 2.4 Data quality 报告（放论文 Appendix A）

Pilot 完成后回填的三张统计表：

- **Table A1**：每类 rubric 转 atomic task 的转化率、reject 原因分布
- **Table A2**：Table coverage、Graph edge density、Skill leak-check
  pass rate（决定各 surface 是否留在 core 的三个 gate 数字）
- **Table A3**：人工抽检 10% (~70 task) 的一致性——两个标注员在
  { question 自然、evidence 足够、no leak、需要多面 } 上的 Cohen κ

### 2.5 Release 形态

- **HF dataset**：`WorkSurface-Bench/WorkSurface-Bench-Lite`
  - `tasks/tasks.jsonl`（原子任务）
  - `profiles/{persona}/kb_docs/`（canonical text）
  - `profiles/{persona}/tables/`（CSV + `registry.json`）
  - `profiles/{persona}/graph/surface_graph.json`
  - `profiles/{persona}/skills/*.md`（metadata）
  - `manifest.json` + `wsb_lock.json`
- **GitHub**：conversion scripts + scoring code + runner harness
- **Leaderboard**：`worksurface-bench.github.io/`

---

## 3. Experiment matrix

### 3.1 参与评测的 agent 设定

5 个，按代码复杂度递增：

| Setting | 描述 | 用途 |
| --- | --- | --- |
| **S1. No-tool** | 只 LLM，无工具 | Answer 下界 + 污染 probe |
| **S2. Always-RAG** | 强制走 `kb_search` | 单面基线 |
| **S3. Naive-router** | LLM 先猜 surface，再单面查 | 路由能力检测 |
| **S4. ReAct all-tools** | 全部 tool 暴露，agent 自选 | 现实设定 |
| **S5. Oracle-route** | 给出 gold `required_surfaces` | 执行上界 |

**Backbone models**（5 个）：

- Claude Opus 4.7
- Claude Sonnet 4.6
- GPT-5
- Gemini 3.1 Pro
- Kimi-K2.5 或 Qwen-3.6（开源代表）

**5 setting × 5 model = 25 runs on Lite**。按每 model 每 run
~$40-64 (improvements §5) 估算总花费 ~$1500。

### 3.2 主表 Table 1（论文核心）

| Agent | Model | Route F1 | Evidence | Answer | Efficiency | Aggregate |
| --- | --- | --- | --- | --- | --- | --- |
| S1 No-tool | Opus 4.7 | – | – | 0.XX | 1.00 | 0.XX |
| S2 Always-RAG | Opus 4.7 | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX |
| S3 Naive-router | Opus 4.7 | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX |
| S4 ReAct-all | Opus 4.7 | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX |
| S5 Oracle-route | Opus 4.7 | 1.00 | 0.XX | 0.XX | – | 0.XX |
| ... 其他 4 个 model 同结构 |

**行的顺序想让审稿人看到**：从上到下 Answer 逐渐上升，但 Route F1
**不是** 单调。这就是 §3.3 的伏笔。

### 3.3 主 Finding：Figure 3（三小图组合）

- **3(a) Route-Answer 散点图**  
  横轴 Route F1，纵轴 Answer。每个点是 (model, task_type) bucket
  → 25 个点。**目标：Spearman ρ ∈ [0.4, 0.7]**。图注写 ρ 值 + p-value。
- **3(b) Oracle gap 柱状图**  
  x：5 个 model；y：3 根柱（Naive-router Answer / ReAct-all Answer /
  Oracle-route Answer）。**目标：Oracle - Naive 差 ≥ 15 points**。
- **3(c) Per-surface Answer 分解**  
  x：4 个 task_type；y：Answer；每个 model 一条线。**目标：cross-
  surface 比单面 task 低 20-40 points**。

### 3.4 Ablation（Table 3）

回答"§3 结果是不是评测协议本身造出来的"：

| Ablation | 变化 | 期望效果 |
| --- | --- | --- |
| A1. 去掉 distractor surface | 只暴露 gold surface | Route F1 假高，说明 distractor 必要 |
| A2. Route 只算 recall 不算 precision | 传统评测 | 抹平 Route 差异 → 支持 P+R 分离 |
| A3. Answer 用 exact match 而非归一化 | 传统评测 | Answer 分数集体下降但排序不变 |
| A4. Efficiency 换成 wallclock 而非 token | | 排序保持稳定说明预算合理 |
| A5. Judge 换 sonnet-4-6 | 替代 opus judge | 与 opus judge Spearman ρ ≥ 0.95 → 便宜 judge 可用 |

### 3.5 Analysis（论文 Section 4）

三个子问题，每个一个小图或 side-table：

- **Q: cross-surface 到底难在哪？** → S4-ReAct 的 error trace 分类：
  wrong-surface / right-surface-wrong-file / right-file-wrong-compute。
  **预期：wrong-surface 占 40-60%**。
- **Q: Skill metadata 有没有用？** → 相同 S4 model，一次 prompt 里
  暴露 `applicable_skills`，一次不暴露。**如果 Answer 差 < 2 points →
  验证 Q1=B (Skill 降级) 的决定合理**。
- **Q: 污染 probe 结果？** → 5 model 的 closed-book Answer。
  **预期：Opus/Sonnet closed-book ≤ 10%（正常），若某 model > 20%
  就打旗**。

### 3.6 Fallback plan（如果 pilot 打脸）

| Pilot 观察 | 论文调整 |
| --- | --- |
| Route-Answer ρ > 0.85 | 主线换成 §3.5 Q1（cross-surface 难在哪的错误分类），Table 1 保留但不做核心图 |
| Table coverage < 30% | 砍 Table，改 2-surface 论文（RAG + Graph），标题去掉 "multi-surface" |
| Graph edge density 中位数 < 5 | 砍 Graph，改 RAG + Table，重心放在 abstain / cross-profile |
| Oracle-Naive gap < 10 points | 主图换成 Figure 3(c) 的 per-surface breakdown |

**外部威胁**（基于 2026-07 related work 调研）：**MetaTool、STaRK 或
TheAgentCompany 团队**可能扩展工作把路由推到 knowledge-surface 粒度。
调研确认目前没有这样的 concurrent work，但相邻团队都有能力做。
**触发条件 = arXiv 预印被拖到 2027-01 之后**。应对：Timeline 2026-11
末 arXiv 挂预印，抢占位置。

---

## 4. 写作 timeline（假设投 NeurIPS 2027 D&B）

- **2026-07 (now) → 2026-09**：完成 pilot、solutions §5.1-5.5、
  数据构建全流程；产出所有 §2.4 statistics
- **2026-10**：跑完 25 run leaderboard，图表定稿
- **2026-11**：初稿完成，走内部 review + **arXiv 挂预印**（抢在
  MetaTool/STaRK/TheAgentCompany 后续工作前面占位）
- **2027-01**：可能投 COLM 2027 (03 月截) 做一次赛前热身
- **2027-06**：正式投 NeurIPS 2027 D&B

**关键节点**：每个月看一次 §3.6 的 fallback 是否触发。触发就锁定
调整方向，别等到最后一个月才改。

---

## 5. 我需要你确认的三件事

1. **主线 = Route ≠ Answer 分离**（已定，pilot 后视相关性 ρ 是否
   > 0.85 触发 fallback）
2. **Lite-only 论文**（已定，无 Full split 计划）
3. **投稿目标 = NeurIPS 2027 D&B + COLM 2027 备胎**——如果你有更
   紧的 deadline（比如内部 review、组会汇报、有主管等着看），告诉我，
   我把 timeline 往前压

其余按 §3.6 fallback plan 执行，pilot 触发再调整。
