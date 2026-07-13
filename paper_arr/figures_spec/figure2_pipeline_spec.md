# Figure 2 (Construction Pipeline) — 设计规格

## 目的

以学术论文方法图的形式，清楚说明数据构建链路：冻结来源、投影知识表面、生成确定性 gold、进行受验证扩展、审计并发布 517 条原子任务。

## 视觉原则

- 保留五阶段结构，因为它对应正文中的可复现构造协议，而不是演示型信息图。
- 使用 Times New Roman、白底、细边框和低饱和配色；不使用阴影、顶部彩条、emoji 或商业化大图标。
- 阶段标题、关键操作和精确数量形成三级层级；文字只保留复核构造流程所需的信息。
- 连续箭头表示因果顺序；阶段 3/4 用稍强边框强调 gold 生成与验证，避免将所有卡片做成同等权重的 UI 组件。

## 五阶段内容

1. **Freeze source**：Workspace-Bench-Lite English split；commit + SHA-256；100 source tasks、5 personas、493 docs。
2. **Project surfaces**：RAG 493 docs、Table 207 views、Graph 1,438 edges；SOP 仅作为 metadata。
3. **Derive gold**：rubric numbers、dependency edges、executed SQL；174 deterministic tasks。
4. **Expand tasks**：158 LLM-assisted、124 Graph+Table、61 RAG+Graph；合计 343 verified tasks；模型自由文本不直接作为 gold。
5. **Audit & release**：517 atomic tasks；Cross 192、RAG 130、Graph 99、Table 96；29 abstain。

## 配色

- RAG：`#3B82F6` / pale blue。
- Table：`#F59E0B` / pale amber。
- Graph 与验证：`#10B981` / pale green。
- Cross 与受验证扩展：`#7A5195` / pale purple。
- 主线、标题、边框：深 slate 与浅灰。

## 输出

- 单页可编辑 PPT：`figure2_pipeline.pptx`。
- 论文矢量 PDF：`figure2_pipeline.pdf`。
- 300-DPI PNG：`figure2_pipeline.png`。
