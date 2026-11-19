# HMRS 最终初稿提交包（2026-11-19 · 五席盲审修复后）

*HMRS: Hierarchical document management for evidence-traced retrieval*
投 Knowledge-Based Systems（ISSN 0950-7051）。基线 = 17 页投稿正本
（`tex/journal_20p/`），本轮经五席盲审（EIC/R1方法/R2领域/R3视角/魔鬼代言人）
→ 16 处修复 → 全页视觉验收 → 附件一致性对账后定稿。

## 目录

| 目录 | 内容 |
|---|---|
| `pdf/` | **main_20p.pdf（17 页投稿终稿）**、main_20p_review.pdf（42 页单栏评审版）、supplementary.pdf（S9–S17）、supplementary-inventory.pdf（S1–S8，42 页） |
| `source/` | 全部 LaTeX 源 + 双 bib + figs/（14 图 + 图4 drawio 源）+ experiment_data/（逐题 trace CSV/manifest/SHA256SUMS）+ figure_scripts/ |
| `docs/` | `BLIND-REVIEW-FIXES-20261119.md`（本轮盲审记录）、投稿填空、cover letter、建议审稿人、highlights、一致性审计脚本 `_verify_consistency_20261119.py`（27 项对账）、中文复核记录、figure-redesign 留档 |

## 本轮关键增量（相对 v2 包）

1. **五席盲审 16 处修复**：详见 docs/BLIND-REVIEW-FIXES-20261119.md。
   核心一击 = A0h vs A0f **预算匹配对照**（两臂均 ~300 kB，frozen 52–45 /
   followup 51–44，各 7/0 零逆转，p=0.016，由逐题 CSV 重算入文），
   数值化拒衡魔鬼代言人"读得多才命中"的最强反方论点。
2. 摘要重构（237 词，主打对比前置 + 三重诚实限定）；MCP/route card/
   臂名/Laya/collection≡library 全部首现释义；RAG 综述与联邦检索综述入引。
3. 全 17 页 visual-judge 排版验收 PASS；附件 S 表三方对账全过。

## 编译与验证

`pdflatex main_20p → bibtex main_20p → pdflatex ×2`（TeX Live 2025）：
**17 页 / 0 错误 / 0 未定义引用 / 0 overfull**。评审版与两份补充材料齐备。

## 投稿前唯一待办

`SUBMISSION-FILL-IN.md`：作者姓名/单位/通讯/ORCID、CRediT 姓名、
资助与致谢措辞（正文 AUTHOR ACTION 注释已标出全部位置）。
