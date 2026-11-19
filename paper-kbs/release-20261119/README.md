# HMRS 投稿发布包（2026-11-19）

*HMRS: A hierarchical management-and-retrieval system for tiered knowledge
document organisation and evidence-traced access* — 投 Knowledge-Based
Systems（ISSN 0950-7051）。

基线：`paper-kbs/tex/journal_20p-verified-20261118/`（分支
`paper/kbs-verified-20261119`，recast 版）。本包为 2026-11-19 修复轮后的
完整交付。

## 目录结构

| 目录 | 内容 |
|---|---|
| `pdf/` | `main_20p.pdf`（双栏终稿，14 页）、`main_20p_review.pdf`（单栏评审版，36 页）、`supplementary.pdf` |
| `source/` | 完整 LaTeX 源（主稿 + n1–n11 章节 + 补充材料 + 双 bib）、`figs/`（正文引用的 14 张 PDF 图）、`experiment_data/`（图源 CSV/manifest/SHA256SUMS）、`figure_scripts/`（3 个建图脚本） |
| `docs/` | Overleaf 说明、归档核验 README、投稿填空清单、11 月证据审计、实验溯源映射（主稿 + 补充材料两份）、highlights.docx |

在 `source/` 下编译顺序：`pdflatex main_20p → bibtex main_20p →
pdflatex ×2`（评审版同理用 `main_20p_review`）。TeX Live 2025 验证通过：
0 错误 / 0 未定义引用 / 0 overfull。

## 2026-11-19 修复内容（本包相对 11-19 晨间构建）

1. **E5（n8b_eval.tex）**：新增跨战役方向稳定性句——A0h 对 A0 的配对
   方向在三次战役中全部保持（discordant 15/0、12/0、12/0，无一逆转）。
   这是支撑"阅读范围"主张的最强复现证据，此前仅在图中间接可读。
2. **Threats（n10_threats.tex）**：显式披露跨战役计数波动（A0h
   52→51→48、A0 37→39→36）并说明方向稳定、三战役分列不合并，预先
   回应审稿人对复现性的追问。

## 实验数据结论支撑状态（2026-11-19 评审结论）

- 三条核心主张（collection 元数据 / 阅读范围 / 候选排序）均有直接
  实验支撑；最强对比（A0h vs A0）三次独立执行方向稳定、配对零逆转。
- 全部正文数字与 `experiment_data/*.csv` 及摘要三方对账一致。
- 词法代理（target-string containment）的失效模式已在 E5 案例解剖中
  主动演示并全程限定措辞。
