# HMRS — Knowledge-Based Systems 投稿稿（实验章润色与排版版，2026-11-24）

**题目：** HMRS: Hierarchical document management for evidence-traced retrieval  
**投稿入口：** [Knowledge-Based Systems · Editorial Manager](https://submit.elsevier.com/KNOSYS)

本目录在阅读校订版（2026-11-24）的基础上润色并重排了第 8 节（实验），并对全文论证边界与排版进行了复核。正文不引用补充材料；保留实验的原始记录未改动。

## 本版改动

- **图 5** 换为单栏案例图（BQ07）：上半部分是 HMRS agent 的真实工具调用（同一轮并行发出的两次检索 → 读金标文档 → 作答），下半部分是两个单轮 baseline 的检索步骤、证据与逐字回答。
- 已撤下旧版表 6 的共享检索预算实验；保留 8.5 节的 E4 配置表，重新编号为表 6。
- **第 8 节**重写：开头给出 RQ 路线图；8.1 只保留数据集与度量；E1 按“通过 / 两例定位 / 未通过与未测”分组；各小节统一为“问题 → 设置 → 结果 → 适用范围”的顺序。引言中的实验顺序改为与正文一致。
- 原图 5（八臂热图）与表 5 的数字完全重复，并且与新图争用同一个页顶，本版不再放入正文或补充材料；图件与生成脚本仍随源码包提供。
- 图 6、图 7 改用 Arial（与其余各图一致），图 7 的最小字号由 6.6 pt 提高到 7.2 pt；两张图的文字与数值逐项未变。
- 问答转录中的中文回答改以英文翻译呈现（原始 JSONL 记录不变），由 80 页变为 78 页。
- 生成式 AI 声明补充了图 5 的来源。

| 文件或目录 | 内容 |
|---|---|
| `01-cover-letter/` | 投稿信 PDF（1 页）和源码 |
| `02-manuscript/main_20p.pdf` | 双栏正文（15 页） |
| `02-manuscript/main_20p_review.pdf` | 单栏双倍行距审稿版（37 页） |
| `02-manuscript/highlights.docx` | 投稿亮点 |
| `02-manuscript/figure-captions.docx` / `.md` | 投稿用图表说明（8 图、7 表、1 算法） |
| `03-supplementary/` | 补充材料（10 页）、证据清单（40 页）、基线问答转录（78 页） |
| `04-source/source/` | 完整源码、绘图脚本和实验工件 |
| `04-source/HMRS-KBS-source-20261124-EVIDENCE-LAYOUT.zip` | 完整源码 ZIP；入口 `source/main_20p.tex` |
| `05-editorial-manager/` | 平铺投稿源码、编号图件、图注和编译稿 |
| `05-editorial-manager/HMRS-KBS-editorial-manager-20261124-EVIDENCE-LAYOUT.zip` | 平铺投稿 ZIP；入口 `manuscript.tex` |

用 TeX Live 在 `04-source/source/` 运行 `latexmk -pdf main_20p.tex` 或 `latexmk -pdf main_20p_review.tex`；平铺包入口为 `latexmk -pdf manuscript.tex`。运行 `sha256sum -c SHA256SUMS.txt` 可校验交付文件。

作者、单位、通信邮箱和 CRediT 角色已按作者提供的信息填写；提交前请确认 CRediT 角色是否与实际贡献一致，确认生成式 AI 声明中各图的来源，并完成投稿系统要求的声明。若投稿系统要求双倍行距版，请按当前指南复核篇幅。
