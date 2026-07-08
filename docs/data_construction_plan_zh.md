# WorkSurface-Bench 数据构建方案

## 目标

WorkSurface-Bench 的数据构建目标不是重新发明一套企业数据，而是把 Workspace-Bench 的真实工作区数据转换成多知识面评测环境。

核心原则：

1. 主体数据全部来自 Workspace-Bench-derived 数据。
2. 不混合 RAGBench、BIRD、STaRK、AMA-Bench 等 public benchmark 作为主任务数据。
3. 不依赖自合成企业世界作为主数据源。
4. LLM 可以辅助抽取候选任务和改写问题，但不能单独决定 gold answer / gold evidence。
5. 评测主线是 RAG / Graph / SQL / Skills 四个企业共享知识面；Memory 暂不进入 core track。

Workspace-Bench 的公开规模为：5 个 worker profiles、74 种文件类型、20,476 个文件、388 个任务、7,399 个 rubrics，并提供 100-task Lite 子集。WorkSurface-Bench 使用这些任务、文件、依赖图和 rubrics 作为可信源。

## 数据单元

WorkSurface-Bench 的基本构建单元是：

```text
Workspace-Bench worker profile
        +
Workspace-Bench task package
        +
task-specific file dependency graph
        +
rubrics / output requirements
```

转换后形成：

```text
WorkSurface profile
  kb_docs/
  db/workspace.sqlite
  graph/surface_graph.json
  skills/
  tasks/tasks.jsonl
  manifest.json
```

其中：

- `profile` 对应 Workspace-Bench 的 worker profile；
- `task package` 对应 Workspace-Bench 的一个原始任务；
- `atomic task` 是从原始任务、dependency graph、rubrics 拆出来的路由/证据/问答子任务。

## Surface 构建

### 1. RAG / KB

输入：

- `.md`
- `.txt`
- `.pdf`
- `.docx`
- `.pptx`
- 其他能稳定转成文本的文档类文件

输出：

```text
kb_docs/<canonical_file_id>.md
```

每个文档保留：

- source path；
- file checksum；
- original extension；
- text extraction method；
- chunk ids；
- page / section / paragraph provenance，如果可用。

Core track 使用 canonical text，不把 OCR 或复杂版面解析作为主评测能力。后续可以增加 Raw-Ingest Track，专门评测从原始 PDF/Office 文件到 surfaces 的端到端解析能力。

### 2. SQL / Database

输入：

- `.csv`
- `.xlsx`
- `.xls`
- 其他结构化表格文件

输出：

```text
db/workspace.sqlite
```

表命名规则：

```text
<safe_file_stem>__<sheet_name>
```

每张表额外加入 provenance columns：

```text
_source_file
_source_sheet
_source_row_id
```

SQL gold evidence 必须可执行验证：

```json
{
  "surface": "sql",
  "table": "inventory_current",
  "sql": "SELECT COUNT(*) FROM inventory_current WHERE variance < 0",
  "expected_result": 8
}
```

### 3. Graph

输入：

- Workspace-Bench `file_dep_graph`
- `data_manifest`
- task -> file -> output 关系
- 表格转换后的 file -> table 关系
- rubric -> skill 关系

输出：

```text
graph/surface_graph.json
```

节点类型：

```text
task
file
table
document
output_artifact
rubric
skill
```

边类型：

```text
task_requires_file
file_depends_on_file
file_supports_output
file_converted_to_table
file_converted_to_document
rubric_checks_output
rubric_defines_skill
task_uses_skill
```

Graph gold evidence 必须能在 `surface_graph.json` 中找到路径。

### 4. Skills

Skills 不直接暴露 task-specific answer rubrics，避免把答案泄漏给 agent。

Skills 只来自：

- repeated workflow pattern；
- output formatting requirements；
- role-level conventions；
- rubric categories 抽象出的通用 SOP。

例如：

```text
skills/inventory_exception_analysis/SKILL.md
skills/financial_comparison_report/SKILL.md
skills/project_dependency_summary/SKILL.md
```

rubrics 的具体答案仍只用于生成 gold answer / gold evidence，不作为 agent 可见 skill 内容。

## Atomic Task 生成

每个 Workspace-Bench 原始任务被拆成多个 atomic tasks。目标是让每个 atomic task 都能明确标注：

- required surfaces；
- gold tools；
- gold evidence；
- gold answer。

### Task 类型

1. `rag_only`

从文档内容回答，例如报告中的结论、政策中的阈值、说明文档中的定义。

2. `sql_only`

从表格或 spreadsheet 计算答案，例如 count、sum、top-k、filter、group-by。

3. `graph_only`

从 dependency graph / lineage / task-file-output 关系回答，例如哪些文件是某个输出的必要依赖。

4. `skill_only`

查找并应用通用 SOP，例如某类报告应该按什么流程检查。

5. `cross_surface`

需要至少两个 surface。优先构造以下组合：

```text
RAG + SQL
RAG + Graph
SQL + Skill
Graph + Skill
RAG + Graph + SQL
RAG + SQL + Skill
```

### 每个原始任务的派生配额

对每个 Workspace-Bench source task，目标派生：

```text
1 个 route overview task
1-2 个 graph/dependency task
1-3 个 rubric-derived answer task
0-2 个 sql task，取决于是否有 CSV/XLSX
0-2 个 cross-surface task，取决于是否天然跨文件类型
0-1 个 skill task，取决于是否能抽象出通用 workflow
```

平均目标：每个 source task 派生 5-8 个 atomic tasks。

## 质量控制

### 1. 来源约束

每条 atomic task 必须引用一个 Workspace-Bench source task：

```json
{
  "source": {
    "benchmark": "Workspace-Bench-Lite",
    "task_id": "...",
    "rubric_refs": ["..."]
  }
}
```

没有 Workspace-Bench 来源的任务不进入 core benchmark。

### 2. Evidence-first 标注

每个答案必须对应至少一个 gold evidence：

- RAG: file + span / chunk id；
- SQL: executable SQL + expected rows；
- Graph: graph path / edge list；
- Skill: skill name + section。

### 3. 程序验证

必须自动验证：

- JSON schema 合法；
- gold SQL 可执行；
- SQL expected result 和 gold answer 一致；
- graph path 存在；
- gold evidence 的 source file 存在；
- required surfaces 和 gold evidence surfaces 一致；
- cross_surface 任务至少包含两个 surface。

### 4. LLM 使用边界

LLM 可以做：

- rubric 改写为自然语言问题；
- candidate evidence 抽取；
- 问题润色；
- task type 分类初稿。

LLM 不可以单独决定：

- final gold answer；
- final gold evidence；
- whether a task is valid。

最终 gold 必须通过程序验证，困难样本再人工抽检。

### 5. 人工抽检

建议抽检比例：

```text
Pilot: 100%
Lite v0.1: 20%
Lite release: 10%
Full release: 5-10%
```

人工抽检重点：

- 问题是否自然；
- gold evidence 是否足以推出答案；
- 是否存在答案泄漏；
- 是否真的需要标注的 required surfaces；
- cross-surface 是否不是伪跨面。

## 数据规模

### Pilot

用途：验证转换器和 scorer。

```text
Source: Workspace-Bench-Lite 中 20 个任务
Profiles: 覆盖 5 个 worker profiles，尽量均衡
Atomic tasks: 100-150
Surfaces: RAG + Graph + SQL
Skills: 可选
```

建议分布：

```text
RAG-only:        25-35
SQL-only:        20-30
Graph-only:      20-30
Cross-surface:   30-50
Skill-only:       0-10
```

### WorkSurface-Bench-Lite v0.1

用途：第一版公开/内部实验。

```text
Source: Workspace-Bench-Lite 100 个任务
Profiles: 5
Atomic tasks: 500-800
Core surfaces: RAG + Graph + SQL + Skills
```

目标分布：

```text
RAG-only:        100-150
SQL-only:         80-130
Graph-only:       80-130
Skill-only:       40-80
Cross-surface:   200-310
```

Cross-surface 内部目标：

```text
RAG + SQL:          60-100
RAG + Graph:        50-90
SQL + Skill:        30-50
Graph + Skill:      20-40
RAG + Graph + SQL:  40-70
RAG + SQL + Skill:  20-40
```

### WorkSurface-Bench-Full

用途：论文主结果。

```text
Source: Workspace-Bench Full 388 个任务
Profiles: 5
Atomic tasks: 2,000-3,000
Core surfaces: RAG + Graph + SQL + Skills
```

目标分布：

```text
RAG-only:         400-600
SQL-only:         300-500
Graph-only:       300-500
Skill-only:       150-300
Cross-surface:    850-1,200
```

如果某些 worker profile 的表格类文件较少，不强行补 SQL-only；保持 Workspace-Bench 原始分布优先，任务配额只作为目标，不作为硬约束。

## 数据 split

建议按 source task 切分，避免同一原始任务派生出的 atomic tasks 同时出现在 dev/test。

Lite：

```text
dev: 20 source tasks -> 100-160 atomic tasks
test: 80 source tasks -> 400-640 atomic tasks
```

Full：

```text
dev: 50 source tasks -> 250-400 atomic tasks
test: 338 source tasks -> 1,750-2,600 atomic tasks
```

如果要训练 router，可另行从 dev 中切出 small train，但 core benchmark 不应依赖训练集。

## Release 策略

需要先确认 Workspace-Bench 的数据再分发许可。稳妥做法：

1. 发布转换脚本；
2. 发布 derived metadata；
3. 不直接重新打包 Workspace-Bench 原始文件；
4. 用 source task id / file path / checksum 关联原数据；
5. 如果许可允许，再发布 canonical surfaces。

推荐目录：

```text
data/
  worksurface_lite/
    profiles/
    tasks/
    manifests/
  worksurface_full/
    profiles/
    tasks/
    manifests/
```

大文件和转换产物默认不进入 git，放 Hugging Face 或 release assets。

## 实施顺序

### Step 1: Source inspection

读取 Workspace-Bench-Lite 的：

- task metadata；
- data manifest；
- file dependency graph；
- rubrics；
- output requirements。

输出统计：

- 每个 source task 的文件类型；
- 可转 SQL 的文件数量；
- 可转 RAG 的文件数量；
- dependency graph 边数；
- rubrics 数量；
- 可派生任务候选数量。

### Step 2: Canonical surface conversion

先做 RAG + SQL + Graph：

```text
documents -> kb_docs
tables -> SQLite
file_dep_graph -> surface_graph
```

Skills 第二步再加，避免一开始引入答案泄漏。

### Step 3: Task candidate generation

规则优先，LLM 辅助：

- 从 rubrics 中抽 atomic claims；
- 从 dependency graph 中抽 route/evidence tasks；
- 从表格字段生成 SQL verification tasks；
- 从跨文件类型依赖中生成 cross-surface tasks。

### Step 4: Verification and filtering

过滤掉：

- gold evidence 不完整的任务；
- 不需要多 surface 的伪 cross-surface 任务；
- 只靠常识可答的任务；
- 答案直接出现在问题中的任务；
- SQL/Graph 无法程序验证的任务。

### Step 5: Manual audit and freeze

人工抽检后冻结：

```text
task ids
profile manifests
canonical surface checksums
gold evidence
scoring scripts
```

## 预期最终贡献

WorkSurface-Bench 的数据贡献不是规模最大，而是把一个企业验证过的 workspace 数据源重新组织成多知识面环境，并提供比普通 RAG benchmark 更细的诊断标签：

- route label；
- tool trace expectation；
- surface-specific evidence；
- cross-surface answer support；
- answer correctness。

这让 benchmark 能回答：

> 企业 agent 失败时，到底是没找对文件，还是没选对知识 surface，还是找到了证据但没有正确组合？

