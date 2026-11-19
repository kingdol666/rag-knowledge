# paper-kbs — HMRS 论文工作区（2026-11-19 清理后）

投 **Knowledge-Based Systems**（Elsevier）的《HMRS》论文工作区。
系统实现 = 仓库根的 `backend/`、`kb-mcp/` 等（HMRS 平台）。

## 当前结构

| 路径 | 内容 | 状态 |
|---|---|---|
| `tex/journal_20p/` | **投稿正本（17 页重构前版，用户指定）**。2026-11-19 已落 4 处修复（E5 三战役方向稳定性 / threats 波动披露 / E6 成本口径 / E9 延迟口径），编译 17 页 / 0 错误 / 0 未定义 | ✅ 投稿用 |
| `tex/journal_20p-verified-20261118/` | 14 页重构版（recast），暂留对照 | 🗄 存档 |
| `release-17p-20261119/` + `.zip` | 17p 完整交付包（源码+PDF+docs，76 条目，完整性已验） | ✅ 交付物 |
| `release-20261119/` | 14p 版交付包 | 🗄 存档 |
| `reference/kbs/` | 29 篇 KBS 已发表文章 PDF（合法 OA 渠道：2 篇 VoR + 26 篇接受稿/arXiv 版 + 1 篇预印本）+ BibTeX + 图库，Related Work 依赖 | ✅ 保留 |
| `notes/` | 引用一致性审计、下载清单、溯源 JSON（被 reference/kbs/README 与溯源链引用） | ✅ 保留 |
| `experiments/` | 实验结果 JSON（被 14p 版 experiment-source-map 引用） | ✅ 保留 |
| `tex/_package_release_*.py` | 两个打包脚本（可重跑生成 release） | 🔧 工具 |

## 2026-11-19 清理记录

删除（约 538 MB）：`_archive_20261111/`、`figures/`、`overleaf*/`（4 个目录）、
`KBS-Revision-20261112(-20p)/`、`figure-reconstruction-20261116/`、
`review/`、`review_results/`、`supplementary/`、`templates/`、
3 个 HMRS-Overleaf zip、根层过期 md ×3；`tex/` 下 `journal_opt_20261115/`、
`journal_20p-word-work-20261118/`、`journal_20p_relwork/`、`preview_pages/`、
`release-9694b73a/`、`FinalPaper/`、`_zip_selftest/`、旧 `figs/`、`notes/`、
根层散落孤儿文件；`journal_20p/` 内约 150 个历史编译日志、11 个 render 目录、
旧 hmrs_kbs 独立稿、备份 docx/png/txt。清理后复编译验证通过。

> 历史工作区（KBS-Revision、overleaf 各轮、journal_opt 等）内容已按
> 2026-11-19 用户决定清除；git 历史中已提交的部分仍可追溯。
