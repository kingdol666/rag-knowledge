# 多场景多文档检索测试与优化 — Round 1 / Round 2（2026-09-25）

测试对象：knowledgebase-search (A)、knowledgebase-librarian (B)、knowledgebase-hybrid (C)。
判决引擎全部为真实本地 Laya（CPU）。5 个场景问题 × 3 模式 × 2 轮，每轮 15 组运行。

## 场景设计

| 题 | 场景 | gold | Round 1 预期暴露的弱点 |
|---|---|---|---|
| T1 | 枚举（实验数据集/基线） | 2310.10981 (4 parts) | 查询词与 gold 描述零重合；答案在 part 3-4 正文 |
| T2 | 多文档综合（RAG 缺陷与防御） | 2502.00306 / 2402.12317 / 2411.18583 | 需跨文档聚合；lit-review 描述为中文无英文检索词 |
| T3 | 改述零重叠（诱虫作物不说 trap cropping） | 2508.05896 (3 parts) | 描述匹配完全失效，纯靠补齐抽签 |
| T4 | 分部定位（幻觉章节在哪） | 2503.21676 (part 2) | 描述锚点与 part 兄弟跟进 |
| T5 | 不在库（联邦学习） | 无 | 诚实 not-found 纪律 |

## Round 1 发现的薄弱环节（全部实锤、全部修复）

1. **T3 B 零遗漏失败（最严重）**：librarian 扫了 329 条描述、判了 30 篇、耗时 307s，
   gold 从未被读取（judged 0/1）。根因 = 零重合补齐按目录扫描顺序排序（稳定排序），
   偏向最先扫描的知识库；gold 在第 4 个库。
2. **T1 B 判决切点丢答案**：实验章节 part 3 判 0.84，被相对切点 0.854 切掉——
   Laya 分布顶端密集，问题关键的中分段文档不安全。
3. **T4 B 丢兄弟分部**：只读了 gold part 1，幻觉章节在 part 2——skill 文档写的
   part 兄弟分组在脚本层没有落实。
4. **T2 三模式同漏 lit-review**：中文描述无英文检索词，描述匹配/向量 top-10 双双失效。
5. **入库描述缺陷**：156/322（48%）文档描述前缀为字面 `【?/?·`（分部模板 k/N 未填充），
   且 L3 信任检查不认识该模式。
6. **跨语言匹配缺失**：英文问题 vs 中文描述，词项重合只靠文件名支撑（系统性风险）。

## 修复清单（全部落地，41/41 离线测试 + skill-creator 校验通过）

| # | 修复 | 位置 |
|---|---|---|
| 1 | 零重合补齐改为**跨库轮询**（relevant/possible 库优先）+ `--extra-terms` 双语扩展词（Phase 0 产出） | hybrid `catalog_lane` / librarian SKILL |
| 2 | 共享保留策略 `retain_docs`：相对切点 + **top-K 保底**（`--top-k-floor`，推荐 5，仅在存在真实证据时生效） | complete_recall（librarian+hybrid 共享） |
| 3 | **stem 兄弟补全**（选中 `(part k of N)` 自动带兄弟，cap 6）+ **判决后扩展**（kept 分部的兄弟全文重读再判，peek 记录原地升级，memo 使第二遍判决零重复开销） | hybrid `judge_with_expansion` |
| 4 | **peek-heads**：未选中的零重合文档全部 700 字符头部扫描+判决——引擎而非描述词汇决定其命运，扫描盲区从构造上消除 | hybrid `catalog_lane` |
| 5 | 描述审计 + 机械修复脚本：`audit_descriptions.py`（6 类缺陷）+ `repair_part_prefixes.py`（`【?/?·`→`【k/N·`，dry-run 默认）| ingest scripts；已对实库 156/156 应用并复审清零 |
| 6 | L3 信任检查新增 `broken_part_prefix` 规则 + ingest SKILL A3c-P 增加 Non-placeholder 条目 | librarian complete_recall / 两份 SKILL.md |
| 7 | `--max-kept`（默认 30）：peek 全库扫描下切点保留带可能淹没回答上下文（实测 104/329），cap 后 `kept_total` 仍如实上报 | complete_recall + hybrid |

## Round 1 → Round 2 结果对比（真实 Laya）

| 题 | 模式 | R1 golds kept | R2 golds kept | 结论 |
|---|---|---|---|---|
| T1 | A / B / C | 1 / 1 / 1 | 1 / 1 / 1 | 持平（part 3 中分段仍受 Laya 校准限制） |
| T2 | A / B / C | 1 / 2 / 2 | 1 / **3** / **3** | peek + 扩展词救回 lit-review |
| T3 | A / B / C | 1 / **0** / 1 | 1 / **1**(3 parts 全保) / 1 | 逐级检索从完全遗漏 → 全保留 |
| T4 | A / B / C | 1 / 1 / 1 | 1 / 1 / 1 | 持平；扩展使 part 2-4 进入判决与锚点可见 |
| T5 | A / B / C | not-found ✓ | not-found ✓（整库头部 < 0.5） | 诚实纪律保持 |

R2 耗时：B 546-738s、C 576-755s/题（peek +299 段判决 ≈ +4-5 分/题，CPU Laya 为瓶颈）。

## 过程中的诚实记录

- R2 的 B/C 转录 `backend` 字段误标为 `offline/False`（memo 包装真实引擎函数后
  `filter_candidates` 无法感知 real 路径）——分数本身为真实 Laya（耗时与分数结构可证）。
  已修复为恢复真实标签（`judge_with_expansion._relabel`）；注入伪分数仍正确标 offline。
- 修复过程中 Round 2 重启 3 次（发现 kept_docs 键名错误 → 扩展未覆盖 peek 记录 →
  全部修复 + 冒烟/探针验证后才放行正式轮）。
- T1 part 3 类「中分段关键文档」仍是 Laya 绝对分数校准问题（0.83 vs 切点 0.861，
  floor=5 被 12+ 篇高分层挡住）——已知限制，非流程缺陷；GPU/校准模型是根治方向。

## 产物

- `round1/`、`round2/`：15 组转录 + SUMMARY.json 各一套
- `catalog.json` / `catalog-postrepair.json` / `audit-round1.json` / `audit-postrepair.json`
- `repair-plan.json` / `repair-apply.json`（156 修复记录）
- `run_round.py` / `compare_rounds.py` / `run.log`×2
