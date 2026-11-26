# paper-kbs — HMRS 论文工作区

投 **Knowledge-Based Systems**（Elsevier）的《HMRS》论文工作区。
系统实现位于仓库根的 `backend/`、`kb-mcp/`、`web/`（HMRS 平台）。

## 当前结构

| 路径 | 内容 | 状态 |
|---|---|---|
| `finalpaper/HMRS-KBS-FINAL-20261126-POLISHED/` | **当前投稿包**：双栏正文 14 页、审稿版 34 页、补充材料、源码、投稿信、亮点、两个上传 ZIP、`06-evidence/` 证据快照与复算脚本 | ✅ 投稿用 |
| `finalpaper/HMRS-KBS-FINAL-20261124-EVIDENCE-LAYOUT/` | 上一轮证据版式包；仓库冻结校验器 `benchmark-suite/…/verification/verify_all.py` 的源码路径仍指向它 | 🗄 校验依赖 |
| `experiments/` | 实验脚本与结果 JSON，补充材料证据索引依赖 | ✅ 复现用 |
| `reference/kbs/` | 29 篇 KBS 已发表文章 PDF、BibTeX 与图库 | ✅ 保留 |
| `notes/` | 引用审计、溯源记录、写作决策 | ✅ 保留 |
| `finalpaper/README.md` | 交付说明 | — |

## 2026-11-26 清理记录

删除约 210 MB 过期内容：`tex/`（含 `journal_20p/`、`journal_20p-verified-20261118/`
及 5 个一次性打包脚本）、`release-17p-20261119/`、`release-17p-final-20261119/`、
`release-17p-v2-20261119/` 及对应 ZIP、`release-20261119/`、
`finalpaper/HMRS-KBS-FINAL-20261124-VERIFIED-READING/`、
`finalpaper/HMRS-KBS-overleaf-20261119.zip`、`finalpaper/compiled/`、
`finalpaper/overleaf-source/`、`finalpaper/supplementary-source/`；另清理仓库内
`__pycache__`/`.pyc`。清理后冻结校验器与投稿包复算均通过。

> 被删内容仍在 git 历史中可追溯。历史工作区细节见 `git log -- paper-kbs/tex`。
