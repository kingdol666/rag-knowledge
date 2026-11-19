# HMRS 投稿发布包 v2 — 图 4 单栏重绘 + 全文终检（2026-11-19）

*HMRS: Hierarchical document management for evidence-traced retrieval*
— 投 Knowledge-Based Systems（ISSN 0950-7051）。

基线：`paper-kbs/tex/journal_20p/`（17 页投稿正本，v1 发布包之后的润色轮）。

## 本轮变更

### 图 4 单栏重绘（GPT Image 2.6 原型 → drawio 1:1 复现）

- **旧图**：`fig_tiered_drawio_20261116`，`figure*` 双栏通栏（1032×456 pt 横版）
- **新图**：`fig_tiered_singlecol_20261119`，`figure` 单栏 `\columnwidth`
  （303×552 pt 竖版），**p.9 在版验收 PASS**（无溢出、字号合规、比例协调）
- 设计流程：gpt-image-2.6 生成竖版设计原型（`docs/figure-redesign/prototype.png`）
  → drawio 1:1 复现（源文件 `source/figs/fig_tiered_singlecol_20261119.drawio`，
  draw.io 桌面版 CLI 导出矢量 PDF）→ 两轮 QC 修正（右栏让位、YES/NO 标签
  位置、间距均衡、虚线加 "on failure" 标注）→ 独立视觉验收 PASS
- 装饰元素：四级编号徽章（深藏青圆标）、语义配色（过程蓝 #EAF2FB/#2C5F8A、
  决策玫瑰 #FDEEF2/#B5537A、终态琥珀 #FDF3E3/#C8963E、候选黄、异常灰虚线）、
  柔和阴影、白底 YES/NO 标签

### 全文终检（academic-paper 质量标准）

- 写作反模式扫描：清嗓开头 / 虚词（crucial 等）/ 破折号滥用 → **全零**
- 故事线：问题→管理模型→生命周期→检索→E1–E9↔RQ1–5→讨论三课→结论两实践，
  结论章数字与正文/CSV 三方一致（15/12/12、15 vs 7/16）
- KBS 格式：elsarticle-num / 摘要 217 词 / highlights 5×≤85 字符 / 六声明齐备
  （2026-11-19 对照 Guide for Authors 逐项核验，全过）
- 编译：主稿 **17 页 / 0 错误 / 0 未定义 / 0 overfull**；评审版 42 页 / 0 错误

## 目录结构

| 目录 | 内容 |
|---|---|
| `pdf/` | main_20p.pdf（17 页终稿）、main_20p_review.pdf（42 页单栏评审版）、supplementary.pdf |
| `source/` | 完整 LaTeX 源 + figs/（14 张 PDF 图 + 新图 drawio 源）+ experiment_data/ + figure_scripts/ |
| `docs/` | Overleaf 说明、投稿填空、cover letter、建议审稿人、highlights、三份中文复核、figure-redesign/（AI 原型 + prompt + 复现渲染） |

编译：`pdflatex main_20p → bibtex main_20p → pdflatex ×2`（TeX Live 2025 验证）。
投稿前唯一待办：填 `SUBMISSION-FILL-IN.md` 作者占位符。
