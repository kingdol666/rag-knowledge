# HMRS — Knowledge-Based Systems 投稿包

**题目：** HMRS: Content-informed hierarchical document management for scoped, source-aware retrieval

**投稿入口：** [Knowledge-Based Systems · Editorial Manager](https://submit.elsevier.com/KNOSYS)

本版在上一轮投稿包基础上进行新一轮系统与方法审读，重写题目、摘要、引言、相关工作、状态模型、评价解释、讨论和结论，并删除可见实验叙述中的日历日期。核心主张收敛为管理—检索一体化和故障可观测性，不主张层级结构带来端到端答案质量优势。实验原始记录及结果数字未改；复算脚本同步更新了摘要断言，图表、补充材料和投稿信按新表述重建。图 5 仍是独立的 BQ07 执行轨迹，不计入 E2 或 E3。

| 文件或目录 | 内容 |
|---|---|
| `01-cover-letter/` | 投稿信 PDF 和源码 |
| `02-manuscript/main_20p.pdf` | 双栏正文 |
| `02-manuscript/main_20p_review.pdf` | 双倍行距审稿版 |
| `02-manuscript/highlights.docx` | 投稿亮点 |
| `02-manuscript/figure-captions.docx` / `.md` | 独立图表说明 |
| `03-supplementary/` | 补充材料、证据索引、基线逐题问答转录 |
| `04-source/source/` | LaTeX 源码、图件脚本和对应实验工件 |
| `04-source/HMRS-KBS-source-20261126-POLISHED.zip` | 完整源码 ZIP；入口 `source/main_20p.tex` |
| `05-editorial-manager/` | 平铺投稿源码、编号图件、图注和编译稿 |
| `05-editorial-manager/HMRS-KBS-editorial-manager-20261126-POLISHED.zip` | 平铺投稿 ZIP；入口 `manuscript.tex` |
| `06-evidence/paper-results-kbs-20261125/` | 本地实验记录、派生表及复算报告；留作复现，不是正文上传文件 |

补充材料中 `benchmark-suite/paper-results-kbs-20261125/` 下的记录可以在上述本地副本中找到。原始记录保持不变；副本的验证器改为读取本包源码，并更新了六项摘要文字检查。进入 `06-evidence/paper-results-kbs-20261125/` 后，可运行 `python -I -X utf8 verification/verify_all.py` 和 `sha256sum -c verification/records-sha256.txt`。

用 TeX Live 在 `04-source/source/` 运行 `latexmk -pdf main_20p.tex` 或 `latexmk -pdf main_20p_review.tex`；平铺包入口为 `latexmk -pdf manuscript.tex`。在本目录运行 `sha256sum -c SHA256SUMS.txt` 可校验交付文件。

投稿前请作者确认 CRediT 实际分工、投稿声明、AI 辅助说明及 Editorial Manager 当前对上传格式和篇幅的要求。AI 声明按作者提供的拼写保留 `CPT-6`；请核对正式名称，并确认精简后的声明完整反映实际使用（旧稿曾提到其他工具、从归档结果制表及初期图件构思）。旧稿 §10 的 52/47 题描述未注明可核对的批次或子集，本轮只保留可支持的域内测试和外推局限，未改 §8.4、图 6 或每轮 72 题的分母。

## 旧版去向

当前工作区不包含旧版投稿包副本；需要核对早期修订时，请从 Git 历史按文件路径追溯。本包自包含构建源码与证据快照，旧目录名仅作为历史出处记录。
