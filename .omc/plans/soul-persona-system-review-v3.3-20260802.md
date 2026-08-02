# SOUL 计划 v3.3 终审报告(五轮评审闭环 + 详细化)

- 评审对象: `.omc/plans/soul-persona-system-20260802.md`(v3.3,pending approval,约 550 行)
- 日期: 2026-08-02
- 过程: 五轮共 22 人次专家评审 + 2 轮闭环验证,全部对仓库真实代码实证

## 1. 第五轮评审团(聚焦"规范 + 详细度 + 最终可行")

| 专家 | 视角 | 结论 | 核心发现 |
|---|---|---|---|
| SpecComplianceAuditor | omc-plan 规范合规 | APPROVE-WITH-CHANGES(合规度 84%) | 4 CRITICAL: relevance_reason 二选一推迟、profile 刷新无验证落点、2.3b/2.4b 编号断裂、任务依赖隐式;AC 可自动断言率 ~77% |
| DetailGapAuditor | 详细度审计(本轮核心) | APPROVE-WITH-CHANGES(详细度 3.1/10) | B1 API schema 全缺、C1 15/16 工具签名、C2 时序、C3 算法伪代码、C4 模块接口、C5 提示词空壳、M1-M5 格式/配置/目录/验收方法 —— 完整详细化蓝图 |
| FeasibilityFinalCheck | 最终可行性终审 | APPROVE-WITH-CHANGES | 需求 6 七子句全部 PASS;3 CRITICAL(task_type 模糊匹配算法/同步超时预估/soul_list 字段)、3 MAJOR(临时上下文/多轮对话/冒烟脚本) |

## 2. v3.3 详细化交付(用户"把 plan 写详细"要求)

**新增 §11 详细契约附录(约 300 行,可直接编码):**
- **11.1 HTTP API Contract**: 8 端点完整请求/响应 JSON schema(ask 同步+异步+408 超时、status、list、init、config、delete、router、router/status)+ 错误码映射
- **11.2 MCP 工具签名表**: 16 工具完整参数(名:类型=默认,req 标记)/返回结构/异步标记
- **11.3 模块函数签名**: soul_config/profile/learn/memory/router/service 6 模块 25+ 函数完整签名
- **11.4 提示词模板结构**: soul_eval_v{N}(含四维锚点完整表+注入防御)/soul_pas/router 打分/profile-summary/合成 5 个模板的输入-输出-要点
- **11.5 数据格式规范**: memory frontmatter 17 字段 YAML schema、gaps.md TSV 行格式、checkpoint manifest JSON、router-log/approval-log JSONL 行格式、training JSONL
- **11.6 目录树与命名规范**: soul-<name>/ 全树 + qhash 算法 + 各文件生命周期
- **11.7 配置参考表**: 26 项配置的字段/类型/默认值/位置
- **11.8 关键算法**: task_type 模糊匹配(Jaccard 3-gram/cosine≥0.7)、route_weight 公式、语义 hash 碰撞处理、embedding 降级、ChromaDB score 语义、profile-summary 生成/刷新、PAS
- **11.9 关键时序**: soul_ask 同步/异步路径、soul_learn 三阶段批处理、调度器 mode 分支伪代码
- **11.10 验收构造方法**: AC22/30c/30b/10/17/M0.4/AC14 的具体测试构造
- **11.11 任务依赖图**: M0-M4 依赖链 + 可并行任务对

**正文修订(合并第五轮专家建议):** AC1 补 context_override/conversation_id/预估公式/relevance_reason 约定;AC15 硬闸门;AC20 加 task_goal;AC25 加 profile 刷新验证;AC30(b) 量化;AC18 加字段;§3 Options 补 F/G;错误码补 3 个;5.1 加通过标准+端到端冒烟脚本;§7 加 LLM 评分一致性风险;2.4/2.4b 行修复。

## 3. 最终裁决

- **五轮 74+17 项评审发现全部闭环**;规范合规 84%(关键缺口已修复,编码前无阻塞);详细度从 3.1/10 提升至可直接编码(API/签名/格式/算法/时序/依赖图齐备);最终可行性终审确认需求 6 全部子句有工具+AC+任务三重定位。
- **用户需求确认**: 多 SOUL 训练(soul_init/learn/learn_all + kb_scope 领域绑定)+ 按任务目标/任务类型自动路由(soul_router + task_goal/task_type 模糊匹配 + 校准循环)+ RAG 增强输出(结构化 citations + PAS + persona_bundle)—— 端到端可开发、可验收、可运维。
- 残余风险(可接受): 路由准确率 80% 为测试集口径,生产需 M5 A/B 监控(route_uncertain >30% 回退显式模式);LLM 评分一致性需 M5 重测信度。
- 计划状态: **pending approval**;排期 M0 0.5 + M1 3-3.5 + M2 4-5 + M3 3 天(约 12 天)+ M4 可选。

*附: 五轮专家报告 — 二轮 ExecVerifier/ArchReviewer/ReqAuditor2/EvalExpert/RiskCost;三轮 MultiSoulArch/ExecVerifier2/ReqAuditor3/EvalExpert2/RiskCost2;四轮 UserScenarioWalker/MilestoneSimulator/IntegrationAuditor/FreshRequirementAuditor/RedTeamReviewer;五轮 SpecComplianceAuditor/DetailGapAuditor/FeasibilityFinalCheck;闭环 Round4Closure/ConsistencyAuditor2*
