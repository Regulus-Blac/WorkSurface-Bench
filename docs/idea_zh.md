# WorkSurface-Bench 设计草案

## 一句话定位

WorkSurface-Bench 是一个基于 Workspace-Bench-derived 企业工作区数据的多知识面路由评测。它不再只问 agent 会不会 RAG，而是问：

> 当企业知识分布在 RAG、Graph、Table、Skills 等不同 surface 中时，agent 能不能选对知识面、调用对工具、找到对证据、回答对问题？

## 为什么不用 public benchmark 拼盘

RAGBench、STaRK、BIRD、AMA-Bench 等数据集分别来自不同世界，任务目标和指标也不一致。把它们拼起来会导致：

- 世界观不统一；
- surface routing 标签不自然；
- 任务语义不一致；
- 容易被认为只是 benchmark aggregator。

因此 WorkSurface-Bench 的主体数据应该全部来自 Workspace-Bench-derived 数据。它的优势是有企业场景、workspace files、dependency graph、rubrics 和 tested capabilities。

## 和 Workspace-Bench 的关系

Workspace-Bench 考察的是 workspace learning / file dependency reasoning：

- agent 能不能在大量文件里找对资料；
- 能不能理解文件依赖、版本、lineage；
- 能不能完成报告、表格、文档等办公任务。

WorkSurface-Bench 考察的是 multi-surface enterprise knowledge routing：

- 表格类的过滤、聚合、top-k 该走 Table；
- 文档事实该走 RAG；
- 文件依赖和 lineage 该走 Graph；
- 操作规范和评分要求该走 Skills；
- 跨 surface 问题要能组合多个证据来源。

关于 Table：我们**不**把这条 surface 定位成企业 SQL benchmark（BIRD / Spider
方向）。Workspace-Bench 派生的 .xlsx / .csv 大多是小规模、per-task、跨任务
schema 不统一的。我们只主张：agent 应该识别 "这题需要聚合/过滤" 并走
`table_query`（DuckDB / pandas 底层），而不是把 sheet 当散文读。**路由决策**是
我们要评的能力，不是 SQL 表达能力。

## Core surfaces

主 benchmark 只放企业共享知识面：

- RAG / KB
- Graph / GraphRAG
- Table（表格聚合/过滤，DuckDB / pandas 底层，不做企业级 SQL benchmark）
- Skills / SOP

Memory 暂时不放进 core。Memory 更像个人偏好、历史互动、会话状态，和企业共享知识面的性质不同。后续可以做 Stateful Extension。

## 数据转换

```text
Workspace-Bench
  data_manifest
  file_dep_graph
  rubrics
  worker persona
  output files
        ↓
WorkSurface-Bench profile
  kb_docs/
  tables/
  graph/surface_graph.json
  skills/
  tasks/tasks.jsonl
```

### RAG

文档类文件、PDF、DOCX、PPTX、Markdown、TXT 等解析成 canonical text，放入 `kb_docs/`。

### Table

CSV/XLSX 文件保留原格式，用 DuckDB `read_csv_auto` / `read_xlsx` 建成 per-task
的 view registry（无跨任务 schema 合并）。工具接口：`table_list` /
`table_describe` / `table_query`（接收 DuckDB SQL）。保留 sheet name、source
file、row id、column provenance。

**不**做以下几件事：不做企业级 schema 迁移；不合成跨任务 fact table；不针对
SQL 语法难度加权。Table surface 的评测目标是**路由决策**（该不该走表格），
不是 SQL 表达能力。

### Graph

从 `file_dep_graph` 构建 surface graph。节点包括：

- task node
- file node
- output artifact node
- table node
- skill node

边包括：

- task_requires_file
- file_depends_on_file
- file_supports_output
- file_is_version_of_file
- file_converted_to_table
- rubric_defines_skill

### Skills

从 rubrics、重复 workflow、输出要求中抽取 SOP-like skills。例如：

- financial comparison workflow
- inventory exception analysis workflow
- dependency summary workflow

## 任务构建

不直接保留 Workspace-Bench 原始大任务，而是从 task/rubric/file dependency 拆出 atomic routing tasks。

任务类型：

- RAG-only
- Table-only
- Graph-only
- Skill-only
- Cross-surface

Cross-surface 是核心，例如：

- RAG + Table
- Graph + RAG
- Table + Skill
- RAG + Graph + Table

## 每条任务标注

每条任务至少包含：

- question
- gold answer
- required surfaces
- gold tools
- gold evidence
- source Workspace-Bench task id
- rubric refs

重点不是只判答案，而是判：

- route 是否对；
- tool trace 是否对；
- evidence 是否对；
- answer 是否对。

## MVP

第一版目标：

```text
Workspace-Bench-Lite
  100 source tasks
        ↓
WorkSurface-Bench-Lite
  300-800 atomic tasks
  RAG + Graph + Table + Skills
```

先不做：

- public benchmark adaptation 作为主体数据；
- 自合成企业数据作为主体数据；
- Memory core track；
- Raw OCR/ingest track。

后续可以加：

- Raw-Ingest Track：从原始文件解析到 surfaces；
- Stateful Track：加入 Memory；
- Full Track：从 Workspace-Bench-Full 扩展。

