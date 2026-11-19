# HMRS 投稿发布包 — 17 页重构前版本（2026-11-19）

*HMRS: A hierarchical management-and-retrieval system for tiered knowledge
document organisation and evidence-traced access* — 投 Knowledge-Based
Systems（ISSN 0950-7051）。

**本包基线**：`paper-kbs/tex/journal_20p/`（17 页重构前版本，用户指定采用）。
区别于 14 页重构版（`journal_20p-verified-20261118/`，另行存档于
`release-20261119/`，不作投稿使用）。

## 目录结构

| 目录 | 内容 |
|---|---|
| `pdf/` | `main_20p.pdf`（双栏终稿 **17 页**）、`main_20p_review.pdf`（单栏评审版 41 页）、`supplementary.pdf` |
| `source/` | 完整 LaTeX 源（主稿 + n1–n11 章节源文件 + 补充材料 + 双 bib）、`figs/`（正文引用的 14 张 PDF 图）、`experiment_data/`（图源 CSV/manifest/SHA256SUMS）、`figure_scripts/`（建图脚本） |
| `docs/` | Overleaf 说明、投稿填空清单、cover letter、建议审稿人、highlights.docx、三份中文复核记录 |

在 `source/` 下编译顺序：`pdflatex main_20p → bibtex main_20p →
pdflatex ×2`（评审版用 `main_20p_review`）。TeX Live 2025 验证：
**主稿 17 页 / 0 错误 / 0 未定义引用；评审版 41 页 / 0 错误**。

## 2026-11-19 修复内容（相对 11-18 夜间构建）

1. **E5（n8b_eval.tex）**：新增三战役方向稳定性句——A0h 对 A0 配对方向在
   frozen/follow-up/rerun 三记录中全部保持（discordant 15/0、12/0、12/0，
   无一逆转）。核心复现证据由图内隐含升级为正文显式陈述。
2. **Threats（n10_threats.tex）**：显式披露跨战役计数波动（A0h
   52→51→48、A0 37→39→36），方向稳定、三战役分列不合并，预答审稿人
   复现性质询。
3. **E6（n8c_eval.tex）**：成本口径澄清——later run 的 \$3.10 为 10 题
   总计（约 \$0.31/题），补记与原 grid 三臂 \$0.487–0.711/题的可比口径，
   消除"涨价 4 倍"的误读空间；并注明其为单臂、无并发对照。
4. **E9（n8c_eval.tex）**：标注两个延迟中位数来源不同轮（修复前全量
   sweep vs 修复后定向 rerun），非重复同轮扫描。

## 实验数据结论支撑状态（2026-11-19 评审结论）

- 三条核心主张（collection 元数据 → 路由 / 阅读范围 → 证据包 / 排序 →
  命中）均有直接实验：路由 72/72 vs 37/72（p=5.8×10⁻¹¹）、A0h vs A0
  52/72 vs 37/72（p=6.1×10⁻⁵）三跑方向稳定、verifier 同池重放 15/16 vs
  7/16。
- 全部正文数字与 `experiment_data/*.csv` 及摘要三方对账一致
  （2026-11-19 独立复核通过）。
- 词法代理（target-string containment）失效模式已在 E5 案例解剖中主动
  演示，全文措辞已限定。
