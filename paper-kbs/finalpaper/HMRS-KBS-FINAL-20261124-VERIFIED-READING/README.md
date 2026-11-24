# HMRS — Knowledge-Based Systems 投稿稿（阅读校订版，2026-11-24）

**题目：** HMRS: Hierarchical document management for evidence-traced retrieval  
**投稿入口：** [Knowledge-Based Systems · Editorial Manager](https://submit.elsevier.com/KNOSYS)

本目录是从 `HMRS-KBS-FINAL-20261124-READING-EDITION/` 派生的独立校订包，前版保留不变。第 8.3 节新增单栏 BQ07 案例图；已撤回的共享检索预算实验及其记录不纳入本包。本版区分早期重命名索引问题与后续缓存复测，明确 E4 检索文本累计量和最终证据包不是同一个量，并把 E7 的证据门结论限定在十题诊断内。原始实验记录、保留实验的图件及统计结果未改动，正文不引用补充材料。

| 文件或目录 | 内容 |
|---|---|
| `01-cover-letter/` | 投稿信 PDF（1 页）和源码 |
| `02-manuscript/main_20p.pdf` | 双栏正文（16 页） |
| `02-manuscript/main_20p_review.pdf` | 单栏双倍行距审稿版（34 页） |
| `02-manuscript/highlights.docx` | 投稿亮点 |
| `02-manuscript/figure-captions.docx` / `.md` | 投稿用图表说明（9 图、6 表、1 算法） |
| `03-supplementary/` | 补充材料（9 页）、证据清单（40 页）、基线问答转录（80 页） |
| `04-source/source/` | 完整源码、绘图脚本和实验工件 |
| `04-source/HMRS-KBS-source-20261124-VERIFIED-READING.zip` | 完整源码 ZIP；入口 `source/main_20p.tex` |
| `05-editorial-manager/` | 平铺投稿源码、编号图件、图注和编译稿 |
| `05-editorial-manager/HMRS-KBS-editorial-manager-20261124-VERIFIED-READING.zip` | 平铺投稿 ZIP；入口 `manuscript.tex` |

用 TeX Live 在 `04-source/source/` 运行 `latexmk -pdf main_20p.tex` 或 `latexmk -pdf main_20p_review.tex`；平铺包入口为 `latexmk -pdf manuscript.tex`。运行 `sha256sum -c SHA256SUMS.txt` 可校验交付文件。

提交前请填写作者、单位、通信信息及 CRediT 占位符，并完成投稿系统要求的声明。若投稿系统要求双倍行距版，请按当前指南复核篇幅。
