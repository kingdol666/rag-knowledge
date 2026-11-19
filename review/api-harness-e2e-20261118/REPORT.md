# 对外 API × Harness × Skill 规范 — 实机验收报告（2026-11-18）

**验收对象**：`POST /api/kb/agent/chat`（对外唯一入口，sync/async 双模式）+ `POST /api/claude/chat`（交互式 kbEnhanced 车道）
**结论**：**核心能力全部验证通过**——外部调用 harness 执行知识库任务成立、知识库增强提示词自动注入成立、skill 规范作业成立；同步与异步两种模式都能拿到有效信息并完成任务。
**工件目录**：`review/api-harness-e2e-20261118/`（runner.py + 全部 *_result.json 原始信封）

## 一、代码链路审查（静态）

| 环节 | 位置 | 结论 |
|---|---|---|
| 对外入口 | `web/server/api/kb/agent/chat.post.ts` | 单一入口、prompt 消毒（控制字符/16k 上限）、600s 默认与硬顶超时 |
| 提示词注入 | `chat.post.ts:106` `fullPromptText: buildAgentChatPreamble() + task` | **每次调用无条件注入**知识库服务代理增强提示词（检索→/knowledgebase-search skill HMRS 管线；入库→写+索引+回查报告；工具纪律；禁止编造；强制 `## Result` 段） |
| harness 派发 | `web/server/engines/index.ts` | 14 个 chat-capable 引擎，默认 claude + bypassPermissions；`requireKbMcp: true` 强制 kb-mcp 可用 |
| 鉴权 | `web/server/middleware/auth.ts` | 全局 Bearer 中间件 → backend `/api/v1/auth/verify` 校验（60s 缓存，fail-closed，网络失败不毒化缓存） |
| 异步契约 | `agent-task-registry.ts` + `tasks/[taskId].get.ts` | 即返 task_id → 后台必达执行 → `GET /api/kb/agent/tasks/:id` 轮询全信封；单进程内存注册表，2h TTL/200 条上限 |

## 二、实机测试矩阵（全部带 Bearer token）

| # | 模式 | 任务 | 结果 | 耗时 | 成本 | 关键证据 |
|---|---|---|---|---|---|---|
| T0a/T0b | 鉴权负测试 | 无 token / 伪 token | **PASS** | - | - | 双双 401 |
| T1 | meta | GET /api/kb/agent/meta | **PASS** | - | - | 14 引擎清单 + 契约说明 |
| T5-1 | 交互 kbEnhanced | 傲慢与偏见·达西求婚场合 | **PASS** | 160.1s (8 turns) | $0.37 | toolCalls=`kb_list→kb_get_documents×2→kb_laya_judge→kb_doc_read×3`，第34章+逐字原文引文 |
| T5-2 | 交互续轮 resume | "上轮那次求婚被拒的理由" | **PASS** | 104.7s (**2 turns**) | - | 会话连续性实锤：零重问直接命中上轮语境 |
| T2r | **同步** agent/chat | Transformer 缩放点积注意力公式 | **PASS** | 442.4s (11 turns) | $1.23 | 金标公式逐字正确；doc_path+P0 标注；tools_used=`Skill→kb_search_vector→kb_laya_judge→kb_doc_read×2`；`## Result` 段 |
| T3r | **同步** OOD | 四川泡菜工艺（域外） | **PASS** | 99.3s (6 turns) | $0.38 | **诚实拒答**：扫描 61 库→无食品域判定→全库向量检索→最高 0.477 全无关→如实列出检索范围，零编造 |
| T4r | **异步** agent/chat | 傲慢与偏见·女儿数/长女名 | **PASS** | 272.3s (6 turns) | $0.55 | **0.0s 即返 task_id**→后台完成→轮询得全信封；金标=五个女儿/长女 Jane；遵守 ≤1 次 doc_read 约束 |
| T6 | **异步** agent/chat | 建库+入库+索引+回查 | **PASS** | 194.2s (12 turns) | $0.57 | 全管线 skill 规范：预检→**建库前去重**→kb_create→文件名合法化+四要素描述+标签→**显式 kb_index_document**→三重回查（读回一致/向量命中 0.6521/chunks=1） |
| T2/T3/T4 首轮 | 3 并发无界提示 | 深检索 | ⚠️ 超时 | >600s | - | 管线轨迹完整但撞 600s 硬顶（见发现 F1） |

**三源独立对账（T6 防幻觉验证）**：磁盘 `storage/tree-file-system/api-e2e-20261118/HMRS-对外API验收记录-20261118.md` ✅ ｜ `.knowledge-base.yml`（文档+标签+四要素描述）✅ ｜ catalog API（kbId `c286bb1c…`、documentCount=1）✅ ——与 agent 自述逐字吻合。

## 三、发现（按严重度）

**F1【运营】无界深检索提示词会撞 600s 硬顶**。首轮 3 并发 + 无界提示（"请依据知识库文档回答"）触发了完整 skill 深管线（Skill 加载+子代理+多次 doc_read+仓库浏览），叠加冷 MCP 暖机与并发竞争，600s MAX_TIMEOUT_MS 内无法出终帧。异步契约本身经受住了考验（task_id 即返、后台继续执行、事后可取全信封）。**缓解**：外部调用方按 T2r/T3r/T4r 方式限定检索深度与答案预算；或平台侧考虑为 agent/chat 暴露 fast-path 开关/提高上限。

**F2【环境缺陷】kb_laya_judge 判卷引擎不可用**：`ModuleNotFoundError: No module named 'laya'`，fail-closed 返回 unavailable。三个回合均如实声明盲点并回退到直接读原文核验（行为正确），但判卷层当天全局降级。**待修**：恢复 laya 模块安装。

**F3【轻微】resume 轮响应未回显 sessionId**（turn1 有、turn2 捕获为 null）——连续性功能正常（内容证明），外部方做长对话时应以首个 session_id 为准。建议核对 resume 分支的响应字段回显。

**F4【备忘】** T6 在生产存储留下测试库 `api-e2e-20261118`（1 doc）作为验收工件；如需清理可指示删除。

## 四、答案汇总（对应用户四问）

1. **能否真正实现外部调用 harness 执行知识库任务？** —— 能。web 层 spawn 真实 claude.exe 子进程（PID 实证），回合内真实调用 kb-mcp 工具（tools_used 全录），产物落盘可独立对账。
2. **是否自动注入知识库增强提示词？** —— 是。`buildAgentChatPreamble()` 每次无条件前置；行为证据：agent 主动调用 Skill、按 HMRS 管线作业、文件名合法化、P0 可信度标注、诚实盲点声明、`## Result` 段——全部是提示词的强制项。
3. **是否基于 skill 规范作业？** —— 是。检索走 knowledgebase-search 管线（改写→向量→judge→幸存者核验→引用作答）；入库走 ingest 规范（去重→质量门→显式索引→A6-V 回查）；OOD 走拒答预算（目录甄别→一轮检索→如实报告）。
4. **同步/异步是否都拿到有效信息并完成任务？** —— 都是。同步 442s 拿到完整信封（reply+tools_used+cost+session）；异步 0s 提交→272s/194s 后台完成→轮询取得同等完整信封。

**当日总成本**：约 $3.10（7 个完成回合）。
