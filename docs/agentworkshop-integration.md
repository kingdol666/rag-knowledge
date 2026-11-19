# AgentWorkShop 集成说明(rag-bridge 插件消费契约)

> 本项目作为 [AgentWorkShop](https://github.com/kingdol666/AgentWorkShop) 的**知识持久化与检索插件**后端。
> AgentWorkShop 侧插件:`.AgentWorkShop/plugins/rag-bridge/`(以及 diag-bridge 的报告自动入库)。
> 本文记录 2026-09-07 三系统集成时钉死的端口与端点契约,供两边任一方升级时对照。

## 端口约定(重要)

> ⚠️ **2026-11-18 勘误（R2 轮实测）**:backend 实际端口为 **8770**(`config.yml` `server.dev.backend_port`,2026-11-17 CleanPort 轮已统一)。
> 历史上出现过 8765/8771 的漂移注记,均以下述为准。**`POST /api/kb/agent/chat` 在 Web 层 :6789,不在 backend**——
> 这是插件集成最常踩的端口坑(run5 2026-10-21 再次实锤)。rag-bridge 插件默认 web 地址 6789 无需改动。

- backend FastAPI:**8770**(`config.yml` `server.dev.backend_port`;prod 模式为 8001)
- Web (Nuxt,TreeFileSystem 文档写盘 + agent/chat 宿主):**6789**
- kb-mcp (MCP SSE):**8000**
- 启动:`cd backend && APP_MODE=prod uv run python main.py`;web:`cd web && APP_MODE=prod npm run start`(或 dev `npm run dev`)
- 完整对外 API 契约见 **`docs/api-web.md` v2.0**(2026-11-18 R2 轮全量补充)

## 被 AgentWorkShop 插件消费的端点

| 用途 | 端点 | 关键约定 |
|---|---|---|
| 健康检查 | `GET :8770/api/v1/health` | `{"status":"healthy"}` |
| 图谱可用性 | `GET :8770/api/v1/graph/health` | `health.available` |
| **Agent 对话(推荐,2026-09-30 起)** | `POST :6789/api/kb/agent/chat` | `{prompt, harness?, permission?, mode?, timeout_ms?}` → KB 系统原生 Agent 自主执行**全部技能**(检索 HMRS/文档入库/经验沉淀/图谱关联),sync 模式阻塞返回完整结果 `{success, reply, tools_used, duration_ms, num_turns, stop_reason}`;`mode:"async"` 立即返回 `{task_id, poll}`,后台执行完后 `GET :6789/api/kb/agent/tasks/:taskId` 取结果。鉴权 `Authorization: Bearer <token>`。旧 `/api/kb/native-search` 已删除 |
| 检索(chunk 级兜底) | `POST :8770/api/v1/search/two-stage` | `{query, kb_id?, stage2_top_k?}`;**断言 `body.success`**;`body.stage2.results` 为分块命中 |
| 文档写盘 | `POST :6789/api/kb/documents/create` | `{kbId, name, content, description?}` → 返回文档 path,作下一步 doc_path |
| 向量索引 | `POST :8770/api/v1/search/index-document` | `{kb_id, doc_path, content, tags}`(content 直传) |
| 结构化经验 | `POST :8770/api/v1/experience/{kb_id}` | `{title, category, problem, solution, key_lessons?, tags?}`;category 枚举见 `experience_models.py` |
| 经验库初始化 | `POST :8770/api/v1/experience/{kb_id}/init` | 幂等 |
| 跨库经验检索 | `POST :8770/api/v1/experience/global-search` | `{query, top_k?}`,零 LLM |
| 图谱关联 | `POST :8770/api/v1/graph/agent-relation` | `{doc_path, target_doc_path, relation_type, reasoning}` |

## 约定的知识库分区

- 库名 **`aw-industrial`**(由插件 ensureKB 幂等创建):存放 AgentWorkShop 诊断报告(`diagnostics/`)与经验(`experience`)。
- 诊断报告入库 tags 约定:`[<产线>, "诊断", "source:diag-bridge"]`;Agent 人工沉淀的经验由 `kb_store` 工具写入,与自动入库按 source 区分,不双写。

## 已知限制

- 限流:per-IP 滑动窗口 600 req/60s(heavy 60),插件侧已做 429 退避;web UI 与插件共享 127.0.0.1 配额。
- 认证:当前 `server.auth.enabled: false`;生产启用后需将 `KB_AUTH_TOKEN` 同步给插件(kv `kb.token`)。

## 认证（2026-09-10 更新）

`server.auth.enabled: true` 已生效。三条接入通道（中间件 `auth_middleware`）：

| 通道 | 凭据 | 适用 |
|---|---|---|
| MCP 服务 token | `Authorization: Bearer $MCP_AUTH_TOKEN`（.env 自动生成） | kb-mcp 工具通道、平台内部服务（全 access） |
| 外部用户 API token | `POST /api/v1/auth/register` → `/auth/login` → `POST /api/v1/auth/tokens`（ scopes=[read,write]，ttl 可选）铸长期 token | **外部系统/插件直调 HTTP 的推荐方式** |
| 无 token | — | 仅 health 等公开端点；其余返回 401 + 可读 hint |

✅ **rag-bridge / diag-bridge 插件现状（2026-09-20 更新）**：插件 v1.1.0+ 已在
`callJson` 统一注入 `Authorization: Bearer <token>` + `X-KB-Token`（token 从
`plugins.rag-bridge.token` 系统配置或 `kv["kb.token"]` 读取，用外部用户通道铸造）。
kb_search 自 v1.3.0 起走 `/api/kb/agent/chat` 原生 Agent 对话（检索/入库/经验/图谱全技能），不再经 native-search（该端点 2026-09-30 删除）；chunk 级 two-stage 仍作降级兜底。

## 多 Harness 作业 API（2026-09-10 新增）

| 端点 | 说明 |
|---|---|
| `GET /api/v1/meditation/harnesses` | 14+1 引擎注册表全景（能力/模型目录/实时可用性/`default`） |
| `GET /api/v1/meditation/models?harness=<id>` | 按引擎的模型目录（omp 动态发现） |
| `POST /api/v1/meditation/run` | body 支持 `harness` 字段指定本次作业引擎 |

错误契约（外部调用者可读）：
- 未知引擎 → `400 {"detail":{"code":"HARNESS_UNKNOWN","message":...,"hint":...}}`
- 未安装   → `409 {"detail":{"code":"HARNESS_NOT_INSTALLED",...}}`
- 已装未配凭据 → `409 {"detail":{"code":"HARNESS_NOT_CONFIGURED","issues":["GEMINI_API_KEY not set"],...}}`
- 运行期失败 → 响应体带 `error_code`（HARNESS_TIMEOUT / HARNESS_AUTH_OR_CONFIG / ...）+ `hint`
默认引擎可用性感知：配置默认（`soul.default_harness`，本机=omp）未安装时自动回落第一个已发现引擎。

## R2 轮新发现（2026-11-18 实测，插件侧必须吸收）

1. **会话字段命名差异**：`POST :6789/api/kb/agent/chat`（Agent 面）响应会话字段为 **`session_id`**（下划线）；
   `POST :6789/api/claude/chat`（交互面）响应为 **`sessionId`**（驼峰）。两通道勿混用；
   交互面 resume 轮响应会回显同一 `sessionId`，可直接续轮。
2. **600s 单回合硬顶**：agent/chat 默认=硬顶 600s（`timeout_ms` 可传 10s–600s，越界钳位）。
   实测超时回合的服务端回包可晚于 630s（引擎子进程终止开销）——**插件客户端 HTTP 读超时须 ≥750s**。
   无界"深检索"提示词 + 机器负载波动（日间可达 2x+）会撞顶；缓解见第 4 条。
3. **kb_laya_judge 判卷引擎降级（2026-11-18 两轮复现）**：`ModuleNotFoundError: No module named 'laya'`，
   fail-closed 返回 unavailable。Agent 行为正确（如实声明盲点并回退直接读原文核验，引用仍可信），
   但每回合会白耗一次失效调用——**恢复 laya 模块前，插件 prompt 建议显式写"跳过 kb_laya_judge"**。
4. **fast-path/最小路径 prompt 缓解（实测有效）**：同一任务，无约束 prompt 2×600s 超时 vs
   带执行约束 139s 完成。模板（直接可用）：
   ```text
   在知识库中查询：<问题>。
   执行约束（最小路径）：直接对目标库做一次 kb_search_vector（slim），再对最优命中做一次 kb_doc_read 验证；
   跳过 kb_laya_judge（当前降级）；不要 kb_list 预扫描，不要委派子代理，不要浏览仓库文件。
   最终答案 ≤N 字并给出 doc_path 出处。
   ```
   完整契约见 `docs/api-web.md` v2.0（§4.2 字段差异 / §4.4 上限 / §8 已知限制 / §7 集成要点九条）。
