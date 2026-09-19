# Round 3 Fix Report

> 执行者：主会话（原 fixer subagent 因账户限流中断于收尾阶段，内容修复已基本完成，由主会话接手收尾）。

## 处置统计：9/9 done

| # | 问题 | 处置 |
|---|---|---|
| 1 | kw 计数口径（R2 major） | done：Table 1 all-keywords 行改严格口径 7/10（Answer section 内），caption 注明含盲区句则 10/10、9/10；Results 段同步（BQ01/BQ03 关键词仅现于盲区句） |
| 2 | untimed 措辞对 B/C 不成立（R2 major） | done：改为 "Track A's latency covers retrieval and evidence reads only; Tracks B and C are end-to-end and include generation (11.6 s of Track C's 12.2 s is generation)"；Conclusion 改 "lowest end-to-end latency" |
| 3 | 48s tagging 无工件（R2 major） | done：删 "48 s / zero failures"，改为 "165 of 165 tagged (tag_count=165 in the graph snapshot); the tagging pass is recorded in the run logs" |
| 4 | Scenario 2 part 号（minor） | done：part 1 of 3 → part 2 of 3（与 skill_track_evidence.json BQ02 top-1 一致） |
| 5 | 图 1 caption 节号误引（minor） | done：Section 3 → Section 4 |
| 6 | 860 vs 1671 口径（minor） | done：补注 "the snapshot's total edge count also includes structural edges" |
| 7 | 图 2 代号（minor） | done：Archival → The agent；A3b quality gates → tag quality gates；已重截 |
| 8 | 图 3 脚注裁切（minor） | done：画布 1352→1372；已重截 |
| 9 | 图印刷字号（R1+R3 major） | done：\textwidth 0.50/0.56/0.52 → 0.72/0.82/0.78（图内有效字号约 +44%）；编译验证正文仍在第 4 页内结束 |

## 最终状态
- 页数：5 页（正文 Abstract→Conclusion 于第 4 页内结束；第 5 页 = Acknowledgments / Data Availability / GenAI 披露 / Competing Interests / References）
- 编译：0 error、0 Overfull
- 数字：未改动任何实验数值；全部可溯源到 benchmark-suite/results/ 工件（含新增 graph_stats.json）

## 备注
- 作者区占位符（Author Name / Affiliation）需作者投稿前自行填写（single-blind 实名要求），agent 不可代填。
- 三位 Round-2 审稿人的 minor 中还有少量措辞类建议（如 Fig.1 底栏 C 列延迟标签口径）已在 #2/#9 的重截中一并覆盖或属于可接受的图形内简写。
