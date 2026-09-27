# Three-Mode Retrieval Test — 2026-09-26

修复 2 个 bug 后的三模式真机对比测试 + librarian skill 契约改造（去 0-8 rubric）。工件清单：

## 契约改造（2026-09-26 第二轮，用户需求）
**librarian（逐级检索）skill 去掉 0-8 打分机制**：逐级内容审查得到路径 → Jev/Laya 快速决策筛选 → **判 yes（≥threshold）的全部保留，无任何后续剪枝** → 所有幸存段作为知识增强直接作答。
- `SKILL.md`：L6 VERIFY（0-8 rubric）删除 → 新 L6 HANDOFF（引擎裁决即终审：no rubric / no retention cut / no P0-P1 tiering）；L5 的 doc-level retention（相对线+top-K floor）条款删除；NEVER 列表与 Quick rules 同步；partial/穷尽诚实条款保留。
- `knowledgebase-search/SKILL.md`：Phase 2 与独立形态说明同步为"librarian 止于引擎门，全幸存者交付"；search 自己的 Phase 1 内容门不动。
- 脚本无需改（rubric 本来就在 agent 层不在脚本层）；`retain_docs` 保留在 complete_recall.py 供 hybrid 使用。
- `sync_skills.py` 镜像同步 + `validate_skills.cjs` PASS（21 skills）。

## 优化后重测（modeB-q*-v2）
| 指标 | v1（旧：相对线+top-K+rubric） | v2（新：Jev yes 全收） |
|---|---|---|
| Q1 幸存 | 17 docs（InstructDS part3 被剪掉） | **128 段/5 docs 全收（part3 的 14 段回归）** |
| Q2 幸存 | 10 docs | **77 段全收（PCA 段+基准段零丢失）** |
| 耗时 | 6.6min / 3.7min | 5.7min / 3.9min（持平，剪枝本来就在判决后） |
| 引擎 | real Laya, 0 错误 | real Laya, 0 错误 |

v2 回答直接答出金标结论，并新增"Knowledge Enhancement"节交付全幸存集附加知识（Q1：vision-flan/how-do-lm-facts/riddle-me-this/instruction-mixing 四篇同域论文 107 段；Q2：sci2cl/连续时间模型/药物表示/肺癌分型 69 段）。

## Bug 修复（2026-09-26 第一轮）
1. **`_relabel` fail-open**（`scripts/hybrid_search.py`）：真实引擎全挂时误报 `real_engine=true`、击穿 `--require-real`。修复：仅 `status=="ok"` 才恢复真实标签。
2. **memo 键碰撞**：判决记忆化 200 字符前缀键 → 全文 SHA-256。
3. 回归测试 +5，三套件 42/42 通过。

## 脚本测试清单（本轮全过）
- pytest 三套件 42/42；`jev_filter.py --check-config`（Laya 本地模型完整/SDK 可用）；`jev_filter` CLI 真引擎判分（相关 0.664 保留 / 无关 0.005 拒绝）；空候选+--require-real exit 2；远端 Jev 无凭证 exit 2 fail-closed；`complete_recall.py` CLI 迷你清单端到端（分类/信任/分段/真判/幸存）；JSON 损坏 exit 1 fail-closed；`hybrid_search.py` 四次真机运行 exit 0；`ensure_laya_model.py` 幂等（complete=true, downloaded=false）。

## 测试设置（第一轮三模式对比）
- 11 KB / 367 docs 真库；Q1=InstructDS 方法（英文，4-part 拆分文档）；Q2=Stroke-EHR 风险因素（中文问句 vs 英文语料）。

## 第一轮结果总览
| 模式 | Q1 命中 | Q2 命中 | Q1 耗时 | Q2 耗时 | 特点 |
|---|---|---|---|---|---|
| A QDCVR 向量优先 | ✓（part2+chunk, 8/8 快速退出） | ✓（8/8 快速退出） | 13.3s | 7.4s | 最快；结论级证据 |
| B Librarian 目录道 | ✓ | ✓ | 6.6min | 3.7min | 描述排序准；已按新契约改造 |
| C Hybrid 并行 | ✓（part1 0.937+双道） | ✓（lane=both 双道） | 19.2min | 30.3min | 覆盖最全；Laya 推理是瓶颈 |

关键发现：
- 三模式全部命中金标并给出正确回答；C 的 12k evidence_pack 在大保留集下会截断金标段（契约补读步骤兜底）。
- Corpus-Chunks800 库 chunk 文档 `kb_doc_read` 一律空正文（三模式一致观察）——数据面问题待修。
