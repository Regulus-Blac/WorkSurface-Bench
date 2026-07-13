# 主图规格总说明

给画图 agent 的两份规格,分别对应论文的两张需要手绘的主图。

## 两张图的定位

| 图 | 位置 | 目的 | 尺寸建议 |
|---|---|---|---|
| **Figure 1 (Teaser)** | 第 1 页顶部 | 3 秒说清"这个 benchmark 是什么" | 16:5 横向 |
| **Figure 2 (Pipeline)** | Section 3 顶部 | 展示"数据怎么造出来、gold 怎么可验证" | 16:5 横向 |

## Figure 3 已经是真图,不用画

Figure 3 (Route-Answer 散点 + Oracle gap 柱状 + per-surface 折线) 是 matplotlib 从真实实验数据生成的,已在 `paper_arr/figure3.png`,不用手绘。

## 三张图配色统一

三个 surface 的颜色贯穿所有图:
- **RAG** = 蓝 `#3B82F6`
- **Table** = 橙 `#F59E0B`
- **Graph** = 绿 `#10B981`

Figure 3 的 matplotlib 用默认色板,如果画图 agent 想让 Figure 1/2 完全统一,可以在 spec 里备注。

## 交付要求

- 每张图**PDF 矢量 + PNG 备份 (3000+ px 宽)**
- 命名:`figure1_teaser.{pdf,png}`, `figure2_pipeline.{pdf,png}`
- 放到 `paper_arr/` 根目录

## 我这边怎么接入

拿到 PDF 后,我把 main.tex 里那两处占位框换成:
```latex
\includegraphics[width=\textwidth]{figure1_teaser.pdf}
\includegraphics[width=\textwidth]{figure2_pipeline.pdf}
```
重编译就行,不用改任何其他内容。

## PPT 画的注意事项

- **原生 PPT 元素**(形状/文字框/箭头),不要贴位图 —— 这样导出 PDF 是矢量的,论文里放大不糊
- **一张幻灯片一张图**,幻灯片本身设成 16:5 的自定义尺寸(设计 → 幻灯片大小 → 自定义 → 宽度 12"、高度 3.75")
- 导出:文件 → 另存为 → PDF,选"最佳画质"

## 我的两条建议

1. **Figure 2 (Pipeline) 优先**,因为它信息密度高、直接回答"你的数据可信吗",评审最看重这个
2. **Figure 1 (Teaser)** 可以简约些,不要塞满字。teaser 靠视觉,不靠文字
