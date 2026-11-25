# HMRS — Knowledge-Based Systems 投稿包

**题目：** HMRS: Hierarchical document management for evidence-traced retrieval  
**投稿入口：** [Knowledge-Based Systems · Editorial Manager](https://submit.elsevier.com/KNOSYS)

本包在 2026-11-24 排版版基础上完成终审修订。图 5 展示 BQ07 一条独立留档的逐级检索轨迹；该案例不属于 E2 八臂盲评，也不计入 E3 路由审计。E2 中实际执行的两阶段检索保留为实验事实，不改称逐级检索，不改写其评分记录。补充材料和证据清单区分主结果、敏感性分析与历史记录，按表、图和实验列出证据定位路径。

| 文件或目录 | 内容 |
|---|---|
| `01-cover-letter/` | 投稿信 PDF 和源码 |
| `02-manuscript/main_20p.pdf` | 双栏正文 |
| `02-manuscript/main_20p_review.pdf` | 双倍行距审稿版 |
| `02-manuscript/highlights.docx` | 投稿亮点 |
| `02-manuscript/figure-captions.docx` / `.md` | 独立图表说明 |
| `03-supplementary/` | 补充材料、证据索引、基线逐题问答转录 |
| `04-source/source/` | LaTeX 源码、图件脚本和对应实验工件 |
| `04-source/HMRS-KBS-source-20261124-EVIDENCE-LAYOUT.zip` | 完整源码 ZIP；入口 `source/main_20p.tex` |
| `05-editorial-manager/` | 平铺投稿源码、编号图件、图注和编译稿 |
| `05-editorial-manager/HMRS-KBS-editorial-manager-20261124-EVIDENCE-LAYOUT.zip` | 平铺投稿 ZIP；入口 `manuscript.tex` |

项目结果目录：[`benchmark-suite/paper-results-kbs-20261125`](../../../benchmark-suite/paper-results-kbs-20261125/)。`records/` 保留实测工件；`tables/` 中的派生值和 `verification/` 中的逐项对账与正文、补充材料对应。原始记录与派生摘要分开，不以替换原始观测来消除批次差异。

用 TeX Live 在 `04-source/source/` 运行 `latexmk -pdf main_20p.tex` 或 `latexmk -pdf main_20p_review.tex`；平铺包入口为 `latexmk -pdf manuscript.tex`。在本目录运行 `sha256sum -c SHA256SUMS.txt` 可校验交付文件。

投稿前请作者确认 CRediT 实际分工、投稿声明、AI 辅助说明及 Editorial Manager 当前对上传格式和篇幅的要求。
