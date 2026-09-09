# RAG Knowledge 对外集成能力 — 问题清单与优化方案

> 实测日期：2026-09-09
> 实测环境：backend `:8770`、web `:6789`、Neo4j `7474/7687`、MinerU 均在运行；kb-mcp 94 个工具
> 测试方式：MCP 工具直连 + 纯 HTTP 外部调用（无认证头）双路径验证
> 测试脚本：`tmp/test_ingest_search.py`、`tmp/test_experience.py`、`tmp/test_soul_*.py`、
> `tmp/test_http_api.py`、`tmp/test_parse_ingest.py`

---

## 0. 总体结论

**API 对外集成可行。** 外部系统不依赖 MCP、不带认证头，仅用 HTTP 即可完成知识库读写；
四大场景中「文档入库 / 检索 / 经验自动总结」三项完整跑通，「人格训练」链路本身可用，
但其对外问答环节存在阻断性超时。

| 场景 | 结果 | 关键证据 |
|---|---|---|
| 文档入库 | 通过 | 建库→写文档→读回逐字一致；PDF 经 MinerU 解析 5s→入库→索引→向量可检索 |
| 检索 | 通过 | 关键词 / 向量语义 / 两阶段 / 图谱 / 标签 五种模式均返回有效结果 |
| 经验自动总结 | 通过 | 提取 2 候选→草稿池→沉淀→统计→P1 分层智能检索 |
| 人格训练 | 部分 | 建人格 2s；学习产出 3 问题 3 记忆；审批后记忆 0→4、掌握度 4.25；**问答超时** |

---

## 1. 问题清单

### P0-1　人格问答 `soul_ask` 同步超时，功能不可用

- **现象**：任何问题均以 `408 {"error":"timeout","detail":"LLM 调用超时"}` 失败。
- **证据**：三次实测——同步路径 181s、240s 失败；**异步路径（`async_mode=True`）
  同样在 190s 返回同一错误**（见下）。同一环境的 `soul_learn` 单次 LLM 调用能成功。
- **根因**：`backend/app/services/soul_config.py:43` 的 `SYNTHESIS_TIMEOUT_SECONDS = 180`，
  小于 omp harness 单次调用实际耗时。学习路径用的 `_HARNESS_TIMEOUT_SEC = 300`
  （`soul_learn.py:62`）够用，问答路径 180s 不够。
  外层 `soul_service.py:391` 仅多给 5s 缓冲，实际先触发的是 `soul_service.py:464` 的 LLM 调用超时。
- **重要更正**：MCP 层的 `async_mode=True`（`kb-mcp/server.py:2671`）**不能绕开此问题**。
  它只是把等待从 HTTP 请求内挪到后台轮询，后端 LLM 调用仍受同一个 180s 阈值约束。
  实测异步路径同样失败，因此**没有零成本绕行方案，必须调阈值**。
- **方案**：
  1. **根治（唯一有效解）**：`SYNTHESIS_TIMEOUT_SECONDS` 由 180 调整为 600，
     并与 `_HARNESS_TIMEOUT_SEC` 统一到同一个配置项，避免两条路径阈值打架。
     改后需重启 backend。
  2. 保留 `async_mode=True` 调用方式——它虽不解决超时，但能避免 MCP/HTTP 客户端侧超时，
     是长问答场景的正确用法。
  3. 建议增加失败降级：超时后返回已检索到的原文片段，而非纯错误。
- **验收**：同一问题在 600s 阈值下返回带引用的答案（同步或异步均可）。

### P0-2　同名知识库无唯一性约束，向量索引串号

- **现象**：创建两个同名 KB 后，写入新库的文档被索引进旧库的向量集合。
- **证据**：`.knowledge-base.yml` 中 `id: f7ff4aa3…`，但文档
  `vector_index.collection` 却是 `kb_7a90a053…`；后续检索返回的 `kb_id` 与实际库不符。
- **根因**：KB 标识多处按「路径/名称」解析且**取首个匹配**——
  `backend/app/services/soul_learn.py:1142 _resolve_any_kb_path()` 遍历匹配后立即 return；
  web 层 `web/server/api/kb/create.post.ts` 创建时不做重名校验。
- **影响**：数据归属错乱、检索结果指向错误知识库、删除操作可能误伤。
- **方案**：
  1. `kb_create` 增加同级重名校验（拒绝或自动加后缀），返回明确错误码。
  2. 所有解析函数改为**优先按 UUID 精确匹配**，名称/路径匹配仅在无 UUID 时兜底，
     且命中多个时报错而非静默取第一个。
  3. 提供一次性巡检脚本：扫描所有 `.knowledge-base.yml`，找出
     `vector_index.collection` 与自身 `kb_id` 不一致的文档并重建索引。
- **验收**：创建同名库被拒绝；任意文档索引后 collection 与所属库 UUID 一致。

### P1-1　SOUL 学习锁竞争，并发任务失败（审阅后收窄范围）

- **现象**：并发提交 `soul_learn` 与 `soul_train_rl` 时，后者等待 300s 后
  `lock_timeout` 失败；失败后再学习同批文档一律 `skipped=2`。
- **证据**：learn 返回 `{"error":"lock_timeout"}`；文档 metadata 带 `learned_hash`。
- **审阅修正（2026-09-09）**：`_record_soul_learned` 全项目唯一写入路径是
  `soul_learn.py:1307`，且 `_record_learned_doc` 的三个调用点（1448/2005/2310）
  均有 `total_questions > 0` 守卫。时间线重建表明 `learned_hash`（16:23:39）
  更可能来自一个持有锁约 21 分钟、最终成功学习的孤儿后台任务——即标记合法，
  skipped 是幂等去重的正常行为。「失败后误标记」证据不足，**不改守卫逻辑**（避免引入回归）。
- **确凿的问题**：锁被长任务占用时，其他任务空等 300s 后以裸错误失败，无排队、无提示。
- **方案**：
  1. 锁获取超时的错误信息增强：附带「当前有学习/训练任务在执行」提示与建议
     （等待完成后重试），不再返回裸 `lock_timeout`。
  2. 学习失败时的 `learned_hash` 写入增加审计日志（`learn.ok=false` 时记录 warning），
     便于未来验证误标记是否发生。
  3. `force` 重学参数列为遗留项（改动面大，本轮不做）。
- **验收**：并发场景下失败任务返回可理解的错误信息；守卫逻辑保持不变。

### P1-2　RL 训练「假成功」，空转 17 分钟仍返回成功

- **现象**：`soul_train_rl` 跑满 6 阶段、耗时 17 分钟，返回 `success: true`，
  但内部 `learn.ok=false / questions_generated=0 / memories_created=0`，reward 仅为基线 2.75。
- **证据**：终态 progress `reward=2.75, memories_approved=0, global_optimized=false`；
  `per_round[0].learn.error = "lock_timeout"`。
- **影响**：调用方（Agent/用户）会误以为人格已训练完成。
- **方案**：训练结果中增加 `quality` 判定——当本轮 learn 失败或产出为 0 时，
  顶层返回 `success: false`（或 `success: true, degraded: true` 并附显著提示），
  避免静默降级。
- **验收**：learn 失败时训练结果明确标记失败或降级，不再静默返回成功。

### P1-3　长任务 task_id 仅在 MCP 进程内有效

- **现象**：`parse_doc` / `soul_learn` / `soul_train_rl` 返回的 task_id，
  换一个进程或会话查询即得 `unknown task_id`。
- **根因**：`kb-mcp/task_registry.py` 是纯内存注册表（注释已说明「state does NOT survive a restart」），
  且 MCP 层未把后端 task_id 透出给调用方。
- **影响**：长任务无法跨会话追踪；进程重启后在途任务全部丢失且无痕迹。
- **方案**：
  1. 短期：MCP 工具返回值中增加 `backend_task_id` 字段，允许调用方直连后端轮询。
  2. 中期：将任务状态持久化到磁盘（如 `storage/.tasks/`），重启后可恢复查询。
- **验收**：重启 MCP 进程后仍能查询历史任务状态。

### P2-1　API 字段命名双轨，外部集成易踩坑

- **现象**：MCP 工具用 `kb_id`（snake_case），web HTTP 层要 `kbId`（camelCase），
  传错直接 `400 kbId is required`。
- **证据**：`kb-mcp/kb_client/client.py:275` 内部构造的是 `{"kbId": kb_id, ...}`。
- **方案**：web 层同时接受两种写法（归一化中间件），或在 `/openapi.json` 明确标注；
  优先推荐前者，兼容成本极低。
- **验收**：`kb_id` 与 `kbId` 均能正常写入。

### P2-2　KB 增删改查所在层缺少 OpenAPI 文档

- **现象**：backend `:8770` 有 `/docs` 与 `/openapi.json`，但 KB CRUD 主要在 web `:6789`
  （Nuxt server routes），该层没有接口文档。
- **方案**：为 web 层补一份接口清单（可先手写 Markdown，或接入 Nuxt 的 OpenAPI 生成）。
- **验收**：外部开发者仅凭文档即可完成建库、写文档、检索。

### P2-3　对外无认证、无限流白名单（本轮不改，列为遗留）

- **现象**：`config.yml` 中 `auth.enabled = false`，限流 600 次/60 秒。
- **审阅结论**：启用认证需要 web 前端、kb-mcp、外部集成方同步携带凭据，
  是牵一发动全身的改造，不属于本轮 bug 修复范围。
- **决定**：内网部署维持现状；对外开放时前置网关加 API Key + 按 key 限流。
  列入遗留风险，不实施。

### P3-1　文档与实际不一致

- **现象**：`.claude/skills/knowledgebase/references/kb-architecture.md` 写「91 个 MCP 工具」，
  实际 `kb-mcp/server.py` 有 94 个 `@mcp.tool`。
- **方案**：把工具计数改为构建时自动生成，或纳入回归检查。
- **验收**：文档数字与实际一致。

---

## 2. 优化方案（分阶段）

### Phase 1 — 解除阻断（建议 1 天内）

| 序号 | 动作 | 改动点 | 风险 |
|---|---|---|---|
| 1 | 调大合成超时阈值（P0-1 唯一解法） | `soul_config.py:43` 180 → 600 | 低，需重启 backend |
| 2 | 禁止创建同名 KB | web `create.post.ts` 增加重名校验 | 低 |
| 3 | 长问答统一用异步调用姿势 | 调用方传 `async_mode=True` + 轮询 | 无（不解决超时，但避免客户端侧超时） |

> Phase 1 完成后，四大场景全部可用。
> 注意：第 1 项是硬阻断项，不修则人格问答完全不可用；第 3 项不能替代第 1 项。

### Phase 2 — 数据正确性（建议 3~5 天）

| 序号 | 动作 | 改动点 |
|---|---|---|
| 4 | KB 解析改为 UUID 优先 + 命中多义时报错 | `soul_learn.py:1142` 及同类解析函数 |
| 5 | 修复 `learned_hash` 误标记，补齐守卫 | `soul_learn.py:1447 / 2005 / 2310` |
| 6 | 学习/训练任务队列化，替换空等超时 | 锁机制改造，`PER_SOUL_LOCK_TIMEOUT` 语义调整 |
| 7 | RL 训练失败显性化 | 训练结果增加 `degraded` 判定 |
| 8 | 存量索引一致性巡检与修复脚本 | 新增脚本，比对 collection 与 kb_id |

### Phase 3 — 工程化与对外易用性（建议 1~2 周）

| 序号 | 动作 | 改动点 |
|---|---|---|
| 9 | 透出 `backend_task_id` + 任务状态持久化 | `task_registry.py`、各异步工具返回值 |
| 10 | 字段命名兼容（同时接受 snake/camel） | web 层归一化中间件 |
| 11 | web 层接口文档 | 新增 `docs/api-web.md` 或接入 OpenAPI |
| 12 | 对外认证与限流 | 网关层，或启用 `auth.enabled` |
| 13 | 文档自动校验工具数 | 构建脚本 / 回归检查 |

---

## 3. 回归验收清单

每次修复后，按顺序执行以下脚本（均在 `tmp/` 下，用 `kb-mcp/.venv/Scripts/python.exe` 运行）：

1. `test_http_api.py` — 纯 HTTP 外部集成：期望 11/11 通过（当前 10/11，缺 `kbId` 字段名）
2. `test_ingest_search.py` — 入库 + 五种检索：期望全部返回结果
3. `test_parse_ingest.py` — PDF 解析入库全链路：期望索引后向量可检索
4. `test_experience.py` — 经验总结：期望草稿→沉淀→统计→智能检索全通
5. `test_soul_learn_fresh.py` — 新文档学习：期望 `memories_created > 0`、`skipped = 0`
6. `test_soul_ask_async.py` — 异步人格问答：当前会因 180s 阈值失败；
   **仅在第 1 项（阈值调至 600）完成后**，期望轮询至 `done` 且答案非空

**数据面校验**：任意文档索引后，`.knowledge-base.yml` 中
`vector_index.collection` 必须等于 `kb_<所属库 kb_id>`。
