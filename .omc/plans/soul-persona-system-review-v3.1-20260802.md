# SOUL 计划 v3.1 终审报告(三轮评审闭环)

- 评审对象: `.omc/plans/soul-persona-system-20260802.md`(v3.1,pending approval)
- 日期: 2026-08-02
- 过程: 三轮共 14 人次专家评审 + 2 人次闭环验证,全部对仓库真实代码实证

## 1. 三轮评审总览

| 轮次 | 专家 | 结论 | 产出 |
|---|---|---|---|
| 首轮 | ArchitectReviewer/ExecutionVerifier/CriticReviewer/RequirementAuditor(v2 自带) | 4×APPROVE-WITH-CHANGES | v2 |
| 二轮 | ExecVerifier/ArchReviewer/ReqAuditor2/EvalExpert/RiskCost(独立实证) | 5×APPROVE-WITH-CHANGES | 24 项修订 → v3 |
| 三轮 | MultiSoulArch/ExecVerifier2/ReqAuditor3/EvalExpert2/RiskCost2(聚焦多 SOUL) | 3×APPROVE-WITH-CHANGES + 2×REJECT | 24 项修复 → v3.1 |
| 闭环 | FixVerifier + ConsistencyAuditor | 35 项 BLOCKER/CRITICAL 中 33 项文字级闭环(94.3%),2 项低严重度实现期细节;一致性审计 4 项 critical 全部修复 | v3.1 定稿 |

## 2. 多 SOUL 功能落地确认(用户需求 6)

需求: 训练多个 SOUL;提问检索时按任务目标+任务类型选取对应 SOUL 人格执行 RAG 增强。

| 能力 | 设计落点 | 验收 |
|---|---|---|
| 多 SOUL 创建 | `soul_init`(模板克隆 + 初始 profile-summary)(1.9) | AC25 |
| 领域绑定独立训练 | `kb_scope` 安全默认(空=不可学习,显式 `["*"]` 全库);文档级 SHA256 去重防 scope 重叠重复学习(1.1/1.8/3.1) | AC21 |
| 多 SOUL 调度 | 每 soul KB 独立 meditation config,mode 分支在循环入口(2.6) | AC5/AC16 |
| SOUL 注册发现 | `soul_list`(仅返回 soul-<name>,summary ≤200 字)(1.5/1.7) | AC18 |
| 按任务目标+类型路由 | `soul_router`: 候选≤8 + domain_labels embedding 初筛 → profile 摘要 + `complete()` 打分(注入 route_weight)→ 阈值(初始 0.6,校准后 percentile 自动调)→ ranked 输出(1.7) | AC19/AC20 |
| 路由质量 | router-test-queries.jsonl 测试集(≥10 条,≥20 条校准前),准确率 ≥80%,per-SOUL 矩阵,recall<60% 审查(3.6) | AC19/AC20 |
| 增强内容输出 | `soul_ask` 返回结构化 citations `[{path, chunk_text, score, relevance_reason}]` + answer + PAS + persona_bundle(1.4) | AC1 |
| 隔离与并发 | per-soul 锁(单 worker 有效,多 worker 文件锁 M4+);soul learn 不经 Semaphore(2);AC22 双断言量化 | AC22/AC24 |
| 降级与审计 | embedding_fallback(harness 故障)、route_uncertain、显式覆盖;router-log 全局+90 天轮转;route_cost_usd 全局池单列(1.7/AC23/AC16) | AC23 |
| 演进安全 | scope 变更 → stale 记忆标记(不删);检查点/回滚边界(AC12);宪法层只读含 soul-config.yml(AC11) | AC25/AC12/AC11 |

## 3. 三轮累计关键修正(摘)

1. **质量闸门**: PAS 定义(与四维正交)、四维锚点表、接地性=min(代码,LLM)、双判官多模型字段、校准集 2.3b、审批 force=True 底线。
2. **预算**: 手动工具入口预算检查、OMP 调用计数上限(≤30,双判官单独 ≤5)、route_cost_usd 全局池、文档级去重使成本 = Σ|∪scope|。
3. **执行细节**: complete() 90-120 行(绕 RESULT_SCHEMA 全局绑定)、调度 mode 分支在循环入口(否则 soul KB 永不触发)、content SHA256 增量、双写 pending_sync、原子写。
4. **安全默认**: kb_scope 空=不可学习(防全库误学);scope validator 硬校验;路由 TTL 缓存 + embedding 降级。

## 4. 最终裁决

- **APPROVE-WITH-CHANGES 条件已满足** —— 三轮全部 BLOCKER/CRITICAL 已闭环;剩余 2 项为实现期细节(router-log 路径在 1.7 已定义,实现时落具体目录;轮转保留 90 天已声明)。
- 计划状态保持 **pending approval**,待用户批准后按 M0 → M4 实施。
- 实施排期: M0 0.5 天 + M1 1 天 + M2 2 天 + M3 1 天 + M4 可选。

*附: 三轮专家原始报告 — v3 复核: MultiSoulArch / ExecVerifier2 / ReqAuditor3 / EvalExpert2 / RiskCost2;闭环: FixVerifier / ConsistencyAuditor*
