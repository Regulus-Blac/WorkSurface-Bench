# Figure 1 (Teaser) — 设计规格

## 目的

让审稿人在 3 秒内理解核心问题:

> 企业问题可能需要不同知识 surface；agent 必须先选对 surface，但选对不代表最终答对。

## 版面与输出

- 横向 16:5，页面 864 x 270 pt，论文中使用 `figure*`。
- 白底、扁平化矢量图，不使用阴影、emoji、交叉线或大面积外框。
- 输出 `figure1_teaser.pdf`、300-DPI `figure1_teaser.png` 和单页可编辑 `figure1_teaser.pptx`。
- 图内不放顶部标题或副标题；叙事直接从 Enterprise question 开始。
- 卡片使用彩色边框表达 surface 类型，不再叠加顶部彩条，避免圆角边缘凸出。
- 可复现源码: `render_figures12.py`。

## 信息结构

```text
Enterprise question --> Agent --> [RAG | Table | Graph] --> Final answer
                                |                          |
                                +-- Route F1               +-- Answer accuracy
```

### 上层:单向叙事

1. **Enterprise question**
   - 用 `DOC / TABLE / LINKS` 三个小标签表示异构 workspace，不画文件堆。
   - 问题简写为:
     `How many items have negative variance, and what is their total cost by shipping mode?`
2. **Agent**
   - 深灰卡片作为视觉中心，副标题 `route + retrieve`。
3. **Surface set**
   - 标注 `select one or more`，避免暗示每个任务只需一个 surface。
   - 三张卡片等宽等高，只保留 `RAG / documents`、`Table / SQL views`、`Graph / lineage`。
4. **Final answer**
   - 位于最右侧，用紫色和勾选图形结束因果链。

### 下层:两个独立评分头

- 左侧标注 `Scored independently`。
- 两张评分卡严格等宽等高:
  - `Route F1`: selected surface set vs. required set
  - `Answer accuracy`: final response vs. reference answer
- 仅使用两条很浅的虚线将上层决策映射到评分头。

## 字体与配色

- 标题和正文: Times New Roman。
- 源图标题 16.5--21 pt，正文不低于 12 pt，保证缩放到双栏宽后可读。
- RAG: `#56B4E9`，深色文字 `#2878A8`。
- Table: `#E69F00`。
- Graph: `#009E73`。
- Answer: `#7A5195`。
- Agent/中性线: `#475467`。

## 图注语义

Figure 1 的图注应强调:benchmark 在同一企业 workspace 上分别评估 surface selection 与 final correctness，而不是将它们合并为一个 end-to-end 分数。
