# WorkSurface-Bench 故事草稿 v0（中文版）

本文档是 `story_v0.md` 的中文对照版。写作时相关工作调研尚未回来，因此
positioning 一节先用三个最有可能的场景做后手，等调研完成后再针对真实
论文重写。

## 核心 wedge（论文标题背后的一句话）

> **Workspace routing 是一种与 workspace learning 不同的能力。**
> 现有的企业 agent benchmark 给 agent 一个平铺的 workspace，问它
> "能不能产出交付物"。我们把同一个 workspace 投影到四个（v0.1 是三个）
> 规范知识面（documents、dependency graph、tables，以及 v0.2 之后可能
> 恢复为 routable 的 SOPs），并且问：**agent 是否知道每个问题该去查
> 哪一个 surface**。路由选择原来是一个可以分离的、被严重欠测量的失败
> 模式。

论文围绕这句话展开，其他都是支撑材料。

## 三大主张

1. **企业知识分布在多个 surface，但目前没有 benchmark 在真实企业数据
   上评过它们之间的路由。**  
   多源 QA 类 benchmark（HybridQA、OTT-QA、TAT-QA）把不相关的公开数据
   拼在一起——比如 Wikipedia 文本 + Web 表格——然后问一个整合问题。
   那评的是"整合"，不是"路由"。而且这些 surface 也不是同一个工作空间
   自然生成的，是事后策划出来的。

2. **Workspace-Bench 派生的源数据带来天然的路由信号。**  
   Workspace-Bench（2026 年 5 月）包含 388 个真实 workspace × 20k 个
   文件 × 5 种 persona。我们把每个 workspace 投影到 RAG / Graph /
   Table 三个 surface，**不合成任何东西**，**不混任何外部数据集**。
   路由信号继承自 workspace 里真实存在的内容。

3. **Route / Evidence / Answer 分解会改变诊断图景。**  
   单一的"任务通过率"把三种失败模式混在一起：agent 是没找对文件、
   还是选错了知识形式、还是找到了证据但算不出结果。我们分开报这三
   个子分数，并预期它们不会高度相关——一个 Answer 强的 agent 可能
   Route 弱，反之亦然。**如果它们完美相关，那本身也是一个负结果，
   而且同样新颖。**

主张 3 是经验性的，只能在 pilot 数据上验证。如果 pilot 显示
Route 和 Answer 的相关性 > 0.85，我们放弃主张 3，改靠主张 1 + 2 撑。
这个决定必须在 pilot 阶段做出，不能拖到 paper 提交前。

## 相邻工作的 positioning（三种后手场景）

以下是"如果调研发现最近的邻居是 X"的三种应对。等调研回来我会用
真实论文替换这三个场景。

### 场景 A：已经有人做过多面路由（例如 AMA-Bench、HybridQA-style 扩展）

我们的差异化点，按强度递减：

- **单一世界的源数据。** 他们的 surface 来自互不相关的公开数据集，
  我们的来自同一个 workspace。他们的模型可以靠领域线索走捷径
  （"这个表是金融 → SQL"），我们的模型不能。
- **File-dependency graph 作为一个 surface。** 没有人有真正来自
  workspace 的、原生的文件依赖图。STaRK 是 Freebase 风格的 KG；
  我们是文件血缘。
- **Route Precision + Route Recall 作为分离指标。** 大多数已有工作只
  报单个 "correct tool called" 的布尔值。加了 distractor pressure
  之后（4 个 surface 都装载），precision 才有意义。

如果命中这个场景，论文标题会从"first" 改成 "workspace-derived
multi-surface routing"。

### 场景 B：Workspace-Bench 2.0 自己加了路由（近期不太可能）

差异化点：

- 我们把 routing 和 workspace learning 分开评。WSB 评的是交付物；
  我们评的是 agent 是否在动笔之前就选对了 surface。
- 我们的 Graph surface 做了增强（见 solutions_v0 §1.2），加入了 WSB
  没有物化的跨文件边。他们的 file_dep_graph 只有一跳。
- Table surface 通过 DuckDB view registry 提供可执行 SQL 作为 gold
  evidence，WSB 的 rubric 无法程序化验证这些。

**如果调研发现 SJTU 团队有往这个方向走的迹象，抢发是首要任务。**

### 场景 C：Agent tool-use benchmark（τ-bench、ToolBench）自称评了路由

差异化点：

- 他们的 tool 操作的 state 是合成的、狭窄的（订票、零售）。我们的
  tool 操作的是真实 workspace 的真实文件。
- 他们评 agent 是否调对了 tool；我们评 agent 是否选对了知识形式。
  这是不同的问题——tool 是**动作**，surface 是**信息类型**。
- 我们把 route / evidence / answer 分开评；他们通常只报最终任务成功
  率。

## 论文贡献列表（应用 Q1 = B：Skill 降级为 metadata）

1. **WorkSurface-Bench**——在真实企业 workspace 上做多面知识路由评测
   的 benchmark。三个可路由 surface（RAG、Graph、Table）；Skills 作
   task 元数据 hint。
2. **Workspace-Bench 派生 pipeline**——把异构文件投影到规范 surface，
   不混外部数据集、不合成企业数据。
3. **四部分评测**（Route P/R/F1、Evidence、Answer、Efficiency），
   外加 ~15% task 上的枚举 Safety 威胁集。
4. **污染卫生工具包**：frozen source snapshot、closed-book probe、
   hold-out submission server（v0.2）。
5. **Workspace-Bench-Lite 上的 pilot**（100 source tasks → ~500-800
   atomic tasks），跑 6 个 baseline（No-tool / Always-RAG /
   Always-Table / Naive-router / ReAct-all-tools / Oracle-route），
   分别报四个子分数。

第 5 项是论文的经验主线。第 1-4 项是各自独立的贡献；第 5 项让它们
可测量。

## Abstract 草稿（目标 ~200 字英文，此处给中文）

> 企业 agent 越来越多地被部署在知识以多种形式存在的 workspace 上：
> 非结构化文档、文件间的依赖图、表格化业务记录，以及成文化的工作
> 流程。大多数 benchmark 只隔离出一种形式，评它上面的检索+回答。
> 这错过了一个不同的能力：**首先选对该去查哪一种知识形式**。我们
> 提出 **WorkSurface-Bench**，把真实企业 workspace 投影到三个规范
> 知识面（documents、dependency graph、tables），并评测 agent 是否
> 能把每个问题路由到正确 surface、检索正确证据、给出正确答案。
> 源数据派生自 Workspace-Bench（2026），我们不混外部 QA 数据集，
> 不合成企业内容。评测分解为 route precision/recall、evidence
> coverage、answer correctness 和一个 token 效率预算，另配一小
> 组枚举 safety 威胁。WorkSurface-Bench-Lite（5 persona、~700 atomic
> tasks）显示：对当前 agent 而言，route selection 与 answer
> correctness 的相关性较弱——一个 router-oracle 上界，能关闭
> naive-router agent 与人类表现之间 30-45% 的差距，表明 routing
> 是一个显著且可分离的能力缺口。

30-45% 是占位数，pilot 定。如果 oracle route 没帮到 30% 那么多，
abstract 就改成负结果版：**"route selection is not the bottleneck;
retrieval on the chosen surface is."** 这个结论同样能发。

## Teaser 图构思

一张图捕捉整个 wedge：

```
        Workspace-Bench                        WorkSurface-Bench
   ┌──────────────────────┐              ┌───────────────────────┐
   │  agent + 20k 异构    │              │  agent + 同一 workspace │
   │  文件的 workspace，  │              │  投影到：              │
   │  一个任务            │      →       │    RAG surface         │
   │                      │              │    Graph surface       │
   │  → 产出交付物        │              │    Table surface       │
   │                      │              │  一个问题              │
   │                      │              │  → 答案 + evidence     │
   └──────────────────────┘              └───────────────────────┘
             ↓                                       ↓
     workspace learning                       workspace routing
    "你能不能把活干完"                        "你知不知道去哪找"
```

图下方：一个 5 agent × 4 sub-score 的柱状图。图想表达的重点是——
**Answer 领先的 agent 未必 Route 领先**。

## 这个故事可能失败的场景

- **Pilot 显示 Route ≈ Answer（相关性 > 0.85）。** 主张 3 死掉。
  应对：改成"我们把 WSB 压缩成一个更快、诊断更细的路由评测；同信号
  下便宜 70%"。
- **相关工作调研发现 AMA-Bench 在公开数据上做过完全一样的事。**
  应对：狠抓"workspace-derived、single world"这一点（场景 A）。
  论文还能发。
- **Table 覆盖率 < 30%（§1.1 gate）**。两面 benchmark 就单薄了。
  应对：扩到 Full source，或者加 cross-profile 任务作为第四种
  surface variant。
- **WSB v2.0 抢在我们前面公布 routing 工作。** 应对：pivot 到
  Graph-surface enrichment 作为主要贡献；multi-surface routing 变成
  次要卖点。

## v0.1 公开发布前，我需要你确认的事项

1. Abstract 的主打句（workspace routing ≠ workspace learning）是否
   通过。整份稿子的 framing 依赖这一句。
2. Skill = metadata（Q1 = B）绿灯——已在上面全篇应用。
3. 发表目标 / 截稿日期（Q10）。决定 Lite-only 还是 Full。当前
   建议是：**主目标 NeurIPS 2027 D&B（2027-06 截）+ 快通道备胎
   COLM 2027（2027-03 截）**。ICLR 主会需要把叙事从 "benchmark"
   改写成 "capability analysis"，是另一种写法。
