# AgentWorkShop 集成说明(rag-bridge 插件消费契约)

> 本项目作为 [AgentWorkShop](https://github.com/kingdol666/AgentWorkShop) 的**知识持久化与检索插件**后端。
> AgentWorkShop 侧插件:`.AgentWorkShop/plugins/rag-bridge/`(以及 diag-bridge 的报告自动入库)。
> 本文记录 2026-09-07 三系统集成时钉死的端口与端点契约,供两边任一方升级时对照。

## 端口约定(重要)

- 后端 FastAPI:**8770**(不再是默认 8765——该端口在本部署机被无关进程占用;`config.yml` 的 `server.dev.backend_port` 与 `.env` 的 `BACKEND_PORT` 已同步改为 8770)
- Web (Nuxt,TreeFileSystem 文档写盘):**6789**
- 启动:`cd backend && BACKEND_PORT=8770 APP_MODE=prod uv run python main.py`;web:`cd web && BACKEND_PORT=8770 npx nuxt dev --port 6789`

## 被 AgentWorkShop 插件消费的端点

| 用途 | 端点 | 关键约定 |
|---|---|---|
| 健康检查 | `GET :8770/api/v1/health` | `{"status":"healthy"}` |
| 图谱可用性 | `GET :8770/api/v1/graph/health` | `health.available` |
| 检索(主入口) | `POST :8770/api/v1/search/two-stage` | `{query, kb_id?, stage2_top_k?}`;**断言 `body.success`** |
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

⚠️ **rag-bridge / diag-bridge 插件现状**：`callJson/jpost` 未携带 Authorization 头，
在 auth.enabled=true 下会收到 401。需要插件侧升级：从 `kv["kb.token"]` 读取并在
callJson 统一注入 `Authorization: Bearer <token>`（token 用上面外部用户通道铸造）。
本仓库 `scripts/e2e_agentworkshop_api.py` 已按"带 token"的真实场景全量验证（21/21）。

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
