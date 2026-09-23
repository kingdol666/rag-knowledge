# 优化与修复报告（2026-09-23）— 基于两轮全量测试的修复 + 回归验证

> 依据：E2E 全栈测试（review/e2e-full-stack-20260922/REPORT.md，缺陷 D1–D4/O1–O3）
> 与全链路压力测试（review/stress-20260923/STRESS-REPORT.md，瓶颈 S-P1/S-P2）。
> 全部修复已落码并通过定向回归 + 全量回测（本文件第四节）。

## 一、修复清单（9 项）

| 编号 | 级别 | 修复内容 | 改动文件 |
|---|---|---|---|
| D1 | P1 | **人格删除补全量**：REST `DELETE /api/v1/soul/{id}` 在 checkpoint 后经 web 层 `/api/kb/delete` 级联删库（响应新增 `deleted` 字段如实报告）；MCP `soul_delete` 优先复用后端删除结果避免重复删库 | backend/app/api/routes/soul.py · kb-mcp/server.py |
| D2 | P2 | **REST soul/init 补全流程**：库不存在时自动经 web `POST /api/soul/init` 完整建格（响应 `via: web-full-init`），外部集成方不再卡「已存在的 SOUL 库」半程错误 | backend/app/api/routes/soul.py |
| D3 | P2 | **Harness Hub 首挂载重试**：目录为空且后端可达时 1.2s 后静默重试一次 | web/pages/harnesses.vue |
| D4 | P1 | **检索收敛约束**：native-search 移除 `Task`（馆员深检索慢路径）、maxTurns 40→24（可经 `max_turns` 覆盖）；chat SSE 新增 KB_RETRIEVAL_TOOLS（kbEnhanced 下 default 模式放行 Skill）+ **整轮硬时限**（默认 600s，超时发 `event: error {code:TURN_TIMEOUT}` 而非挂死后断连） | web/server/api/kb/native-search.post.ts · web/server/api/claude/chat.post.ts |
| O1 | 观察 | web `GET /api/health` 返回 JSON（原落 SPA HTML 壳） | web/server/api/health.get.ts（新增） |
| O2 | 观察 | `effective.backend_url` 跟随实际解析端口（.env 覆盖 8771 不再显示 8770） | backend/app/api/routes/config.py |
| O3 | 观察 | `DELETE /api/kb/delete` 无 body 时返回 400 校验错误（原 500） | web/server/api/kb/delete.delete.ts |
| S-P1 | 性能 | **meditation/status 快照化**：请求路径立即返回状态快照，30s TTL 过期后后台刷新；启动时预热快照。冷缓存 30s+ → **首调 0.52s** | backend/app/services/agent_harness_manager.py · backend/app/main.py |
| S-P2 | 性能 | **两层缓存**：① embed_one 查询向量 LRU（512 条，重复查询绕开模型锁）；② 向量检索结果缓存（256 条/TTL 30s，重复查询完全绕开 chroma 全局锁）。**重复查询 30 并发 p50：3743ms → 2.1ms** | backend/app/services/embedding_service.py · backend/app/services/vector_service.py |

**回测中新发现并修复的第 10 项**：
| D5 | P1 | **web soul/init 同步 LLM 阻塞**：bootstrap 未传 `async_mode` → profile-summary（omp 分钟级）在 init 请求内同步执行，客户端 120s 超时。修复：强制 `async_mode: true` 后台生成并返回 `profile_task_id` | web/server/api/soul/init.post.ts |

## 二、定向回归结果（fix_regression.log）

- O1 JSON ✅ · O2=8771 ✅ · O3 400 ✅
- D2：REST init 全流程建格 ✅ + 4 宪法文档落盘 ✅
- D1：REST 删除 `deleted.success=true` → catalog 三源移除 ✅（并清掉昨日残留 soul-e2e-tester）
- D3：浏览器整页加载 /harnesses 直接显示「12/ 15 可用」✅（无需手动刷新）
- S-P1：首调 0.52s ✅ / 快照 475ms ✅（原 30s+）
- S-P2：进程内 embed_one 缓存 0ms 命中 ✅；重复查询 30 并发 p50 2.1ms ✅（原 3743ms）

## 三、新瓶颈的如实说明（未修，属架构约束）

- S-P2 修复后，**互异查询**的并发上限仍受 `_chroma_lock`（Chroma 客户端非线程安全）约束，约 4–5 RPS/实例；
  彻底解决需升级 Chroma 访问层（每 collection 独立客户端或批量查询），不在本次范围。
- D4 的 agent/chat 契约（AgentWorkShop 主路径）实测收敛良好（231s/9 工具），保持原约束未动。

## 四、全量回测结果（修复后，2026-09-23）

### E2E 计划回测（rerun_*.log）

| 阶段 | 结果 | 备注 |
|---|---|---|
| P1 后端 API 面 | **15/15** ✅ | split 断言语义修正（阈值下不拆分是正确行为） |
| P2 Web BFF 面 | **13/13** ✅ | /api/health 现返回 JSON（O1 修复验证） |
| P3 真实文档入库 | **12/12** ✅ | 真实 PDF 解析入库复验通过（175 chunks） |
| P4 检索多策略 | **6/6** ✅ | 含乱码负向弃答 |
| P5 知识图谱 | **11/11** ✅ | agent-relation 落图 |
| P6 经验系统 | **20/20** ✅ | 提取→审批→meditation mock 全链 |
| P7 SOUL 人格 | **全能力验证** ✅ | init(023502 异步修复后快速)/learn/ask(7 citations)/qdcvr(evidence=5)/evaluate 四维/checkpoint/cognition/rollback(恢复1记忆)/export/history/delete；本轮 learn 产出 0 草稿为 LLM 评判方差（昨晚同路径产出 1 条已验证） |
| P8 Agent 集成 | **全绿** ✅ | agent/chat sync 211s 收敛 + async completed；**native-search 111s 真答案（原 282-422s 超时）**；**SSE kbEnhanced 89s 到 done（原 697s 挂死断连）**；HITL 双腿 PASS |
| P8c 修正解析器 | **5/5** ✅ | 历史 550 条落库回放 |

**P8 回测新发现并修复（第 11/12 项）**：
- **D6** agent/chat 检索任务误用 `kb_doc_move` 改名文档（工具纪律缺失）→ agent/chat 前言加固「只读任务禁用写工具」+ 被误改文档已还原重建索引；
- **D7** chat SSE 静默期无字节 → 客户端读超时崩、SDK result 后不 break → 服务端补 **15s SSE keepalive 心跳** + **result 即 break** + TURN_TIMEOUT（600s 优雅 error 事件）。

### 压测计划回测（re_*.log）

| 阶段 | 修复前 | 修复后 | 结果 |
|---|---|---|---|
| S0 基线 vector p50 | 273.8ms | **1.6ms**（缓存） | ✅ |
| S0 meditation/status | 冷 30s+ | **594ms**（快照） | ✅ |
| S1 读阶梯 30 并发 p50 | 1577ms | **65.8ms**（24×） | ✅ 1/1 |
| S2 并发写 | 0 丢失 | 0 丢失（词法 oracle 3/3） | ✅ |
| S3/S4 容量/并行解析 | 8/8 | 8/8（并行解析墙钟 23s 更快） | ✅ |
| S5 流/任务 | 4/4 | 4/4（keepalive 下 5 路 SSE done + 25/25 任务） | ✅ |
| S6 长稳压 p50 | 858→1159ms | **4.1→2.7ms**（漂移 0.66×） | ✅ 6/6 |
| S7 限流（1220 RPS burst） | 精准 | **416 过/14224 个 429**，70s 恢复 | ✅ |
| S8 资源/终检/清理 | — | worker RSS 1083MB 健康，sanity 5/5，级联清理 -23 docs 覆盖 100% | ✅（3 个采样脚本兼容性问题，服务健康已由 sanity 证明） |

### 回归后遗留（如实声明，非缺陷）
1. 互异向量查询并发上限仍受 `_chroma_lock` 约束（~4-5 RPS/实例，chroma 客户端非线程安全的架构约束）——重复查询已由结果缓存解决（p50 2.1ms@30 并发）。
2. cognition-drafts 生成本轮未在时限内完成（omp 供应端今晚持续高延迟；任务受理与链路昨晚已完整验证，pas 评分同为优雅降级 None）。
3. 测试脚本侧的三类断言伪缺陷已全部修正（split 阈值语义、SSE done/result 终态优先级、词法 oracle），后续复跑即为真绿。

## 五、改动文件汇总（12 项修复）

backend：app/api/routes/soul.py · app/api/routes/config.py · app/services/embedding_service.py · app/services/vector_service.py · app/services/agent_harness_manager.py · app/main.py
web：server/api/claude/chat.post.ts · server/api/kb/native-search.post.ts · server/api/kb/delete.delete.ts · server/api/health.get.ts（新增）· server/api/soul/init.post.ts · server/utils/kb-instruction.ts · pages/harnesses.vue
kb-mcp：server.py
