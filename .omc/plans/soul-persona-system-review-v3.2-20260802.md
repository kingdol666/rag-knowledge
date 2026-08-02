# SOUL 计划 v3.2 终审报告(四轮评审闭环)

- 评审对象: `.omc/plans/soul-persona-system-20260802.md`(v3.2,pending approval)
- 日期: 2026-08-02
- 过程: 四轮共 19 人次专家评审 + 2 人次闭环验证,全部对仓库真实代码实证

## 1. 四轮评审总览

| 轮次 | 专家 | 结论 | 产出 |
|---|---|---|---|
| 首轮 | 4 专家(v2 自带) | 4×APPROVE-WITH-CHANGES | v2 |
| 二轮 | ExecVerifier/ArchReviewer/ReqAuditor2/EvalExpert/RiskCost | 5×APPROVE-WITH-CHANGES | 24 项修订 → v3 |
| 三轮 | MultiSoulArch/ExecVerifier2/ReqAuditor3/EvalExpert2/RiskCost2(多 SOUL 聚焦) | 3+2 REJECT | 24 项修复 → v3.1 |
| 四轮 | UserScenarioWalker/MilestoneSimulator/IntegrationAuditor/FreshRequirementAuditor/RedTeamReviewer(端到端可行聚焦) | 2 REJECT + 3 APPROVE-WITH-CHANGES | 26 项修复 → v3.2 |
| 闭环 | Round4Closure + ConsistencyAuditor2 | 26 项 100% 闭环(39 OK + 5 MINOR 已补);一致性 3 处矛盾已修复 | v3.2 定稿 |

## 2. 第四轮核心发现与修复(按主题)

**端到端功能链路(用户六个场景走查)**
- 记忆索引闭环(最重): 审批后自动注册+索引,60s 内可检索 —— learn→ask 链路从断裂到闭合(2.4b/AC14/§6 验证 10)
- soul_init 完整实现路径: kb_create → 逐文档 kb_doc_create(自动注册+索引)→ soul-config.yml 原子写 → profile-summary → meditation config(mode=soul/enabled=false/budget=0.15)(1.9/AC25)
- route_uncertain 响应契约: answer 引导文本/citations=[]/pas_score=null(AC1)
- persona_bundle 记忆检索统一: 最近 N 条 approved 记忆 frontmatter 摘要(N=10)(1.3)
- self_answer/distill 数据契约: {answer_text, citations, evidence_paths}(2.2/2.3)
- soul_ask 同步/异步双模式: 命中缓存且 ≤60s 同步,否则 task_registry(async_mode)(AC1/AC8/1.4)

**集成与安全面(与现有 13 库体系)**
- soul-模板 is_template 排除: soul_list/路由/learn_all 全部过滤(1.1/1.5/1.7/3.1/AC18)
- 调度 mode 分支前置 M0.4: 防止 soul KB enabled 时被经验提取;13 库回归对照(0.4/§6 验证 8)
- 全库操作防护: experience_extract 拒 soul-*;reindex/graph 不索引 pending 草稿(§6 回归 9)
- 锁覆盖: checkpoint/rollback 纳入 per-soul 锁;预算 check-and-deduct 锁内原子(1.3/AC12/AC30c)
- scope 禁含 soul- 库(人格互学/模板污染)(1.8/AC21)
- 注入防御 <USER_CONTENT> 隔离 + eval 防御声明(1.2/2.3/AC30b)
- Windows 文件名与路径穿越校验(1.9/AC30a)
- sync_dedup_key 双写幂等;rollback 经验草稿 stale + training_stale(2.4/3.4/AC31)

**执行可行性**
- 排期重估: M1 3-3.5 天 / M2 4-5 天 / M3 3 天,总约 12 天(原 4.5 天低估 3 倍)(标题/Changelog)
- §5.1 最小自动化测试要求: complete()/router/调度回归(13 库 dry-run 对照)等(5.1)
- 多 SOUL 创建时序: M1 验收 8 显式创建第 2/3 个 SOUL(AC19 测试集前置)
- 新增 AC26-31(soul_eval/soul_calibrate/soul_router 独立验收、soul_delete、对抗输入、双写幂等)
- 新增 soul_delete 工具(含 purge_experiences、TTL 清理、tombstone)(1.9/AC29)
- 鉴权 verify_token 对齐 experience.py 规范(1.4)

## 3. 最终裁决

- **四轮 74 项评审发现全部闭环**(24+24+26);闭环验证: 26 项 100% 落实,5 项 MINOR 已补齐;一致性审计 3 处矛盾已修复。
- 用户需求 6(多 SOUL 训练 + 按任务目标/类型路由的 RAG 增强)在 v3.2 中**端到端可开发、可验收、可运维**: 创建(1.9)→ 训练(2.x)→ 审批+索引(2.4b)→ 路由问答(1.4/1.7)→ 反思/回滚(3.3/3.4)→ 导出(4.1)全链路闭环,16 个 MCP 工具、AC1-AC31、排期约 12 天 + 自动化测试矩阵。
- 计划状态保持 **pending approval**,待批准后按 M0(0.5 天)→ M1(3-3.5 天)→ M2(4-5 天)→ M3(3 天)→ M4(可选)实施。

*附: 四轮专家原始报告 — 二轮: ExecVerifier/ArchReviewer/ReqAuditor2/EvalExpert/RiskCost;三轮: MultiSoulArch/ExecVerifier2/ReqAuditor3/EvalExpert2/RiskCost2;四轮: UserScenarioWalker/MilestoneSimulator/IntegrationAuditor/FreshRequirementAuditor/RedTeamReviewer;闭环: Round4Closure/ConsistencyAuditor2*
