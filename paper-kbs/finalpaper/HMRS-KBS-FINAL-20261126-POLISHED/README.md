# HMRS — Knowledge-Based Systems 投稿包

**题目：** HMRS: Content-informed hierarchical document management for scoped, source-aware retrieval

**投稿入口：** [Knowledge-Based Systems · Editorial Manager](https://submit.elsevier.com/KNOSYS)

本包以 **15 页双栏主稿（含参考文献）**为准。双倍行距版供审阅参考；投稿时请使用 Editorial Manager 中的可编辑 LaTeX 文件，并保留独立图件。本文的主张是管理—检索一体化和故障可观测性，不主张层级结构带来端到端答案质量优势。原始记录和结果数字未改，图 5 仍是独立的 BQ07 执行轨迹，不计入 E2 或 E3。

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

## 投稿上传清单

- **Manuscript / source：** 使用 `05-editorial-manager/` 的可编辑 LaTeX 源码，入口 `manuscript.tex`。15 页 PDF 用来核对系统生成的稿件，不替代源码。双倍行距审稿参考版不是默认上传文件。[KBS 作者指南](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors)允许双栏 LaTeX，同时建议研究稿不超过 20 个双倍行距页（含图表）；当前 35 页双倍行距参考版超出这项建议，不把 15 个双栏页等同为 20 个双倍行距页。若系统或编辑另要求双倍行距，以其要求为准。
- **Cover letter / Highlights：** 分别用 `01-cover-letter/cover-letter.pdf` 和 `02-manuscript/highlights.docx`。通讯信息、原创性、全体作者同意及无一稿多投由作者确认。
- **Figures / Figure captions：** 按编号分别上传 `05-editorial-manager/figures/Figure_1.pdf` 至 `Figure_8.pdf` 及 `figure-captions.docx`。表格留在可编辑的 LaTeX 主稿内。
- **Supplementary material：** 以下三份 PDF 已在正文 Data availability 点名；可使用对应的英文说明作为上传 caption：
  - `supplementary.pdf` — Supplementary methods, experiment configurations, results and evidence crosswalk.
  - `supplementary-inventory.pdf` — Companion inventory mapping the experiments to archived records and verification material. 它指向的 `supplementary-inventory-source-map.md` 随完整源码包提供，位于 `04-source/source/inventory-build/`。
  - `external-baselines-qa.pdf` — Question-by-question audit transcript of the external-baseline comparison, including prompts and answers.
- **作者确认和系统生成项：** 按 KBS 指南指定一名与期刊联系的通讯作者；当前稿面保留作者给定的两位通讯标注。上传前确认系统和稿面所需的署名方式、CRediT 分工及 AI 辅助说明（`CPT-6` 按原拼写保留，请核对正式名称与披露范围）。通过 Elsevier declarations tool 填报并上传生成的利益冲突声明 `.doc/.docx`；正文中的声明不替代此文件。
- **不上传为正文：** `04-source` 的完整源码 ZIP、`06-evidence` 的复现档案及校验清单留作归档及复现。不要将完整源码 ZIP 和 Editorial Manager ZIP 同时提交为两份主稿。

## 旧版去向

当前工作区不包含旧版投稿包副本；需要核对早期修订时，请从 Git 历史按文件路径追溯。本包自包含构建源码与证据快照，旧目录名仅作为历史出处记录。
