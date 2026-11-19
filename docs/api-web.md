# RAG Knowledge Platform — 对外 HTTP API 文档

> **版本**: v2.0（2026-11-18 R2 轮全量补充与勘误）
> **维护**: 本文档由实机验收轮（`review/api-harness-e2e-20261118/`）背书，所有核心端点均经真实调用验证。
> **变更记录**见文末 §11。历史版本 v1.0（2026-09-09/09-13）仅覆盖 KB 核心操作，v2.0 补齐 Agent 服务面、
> 交互式对话面、自动化/冥想、Harness 注册表等全部外部调用面。

---

## 1. 概述

本平台对外的 HTTP API 由 **Web 层（Nuxt 3 server routes）** 统一暴露，外部系统（如 AgentWorkShop
插件）只需要与 Web 层对话。Web 层内部代理 FastAPI backend 与 kb-mcp MCP 工具层，调用方无需感知
内部分层。

```
外部调用方（AgentWorkShop / 任意 HTTP 客户端）
    │  HTTP + Bearer token
    ▼
Web 层 :6789（dev）/ :3000（prod）   ← 本文全部端点的宿主
    │  server-to-server 代理
    ▼
FastAPI backend :8770（解析/检索/经验/图谱引擎）  ·  kb-mcp :8000（MCP SSE 工具层）
```

**两种作业面**（按集成意图选择）：

| 作业面 | 端点 | 适用场景 |
|---|---|---|
| **Agent 服务面**（推荐主通道） | `POST /api/kb/agent/chat` | 一个任务提示进，一个完整结果出。KB 系统原生 Agent 自主执行全部技能（HMRS 检索/文档入库/经验沉淀/图谱关联），调用方不编排任何检索步骤 |
| **资源直调面** | `/api/kb/*`、`/api/search/*`、`/api/parse/*` 等 | 调用方已知确切操作（如按 path 写盘、按 query 关键词检索），走确定性端点 |

---

## 2. 快速开始（5 分钟集成）

```bash
BASE=http://localhost:6789

# ① 登录取 token（首次先 POST /api/auth/register 注册）
TOKEN=$(curl -s -X POST $BASE/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"<user>","password":"<password>"}' | jq -r .token)

# ② 发一个知识库任务（同步模式：挂起直到完成）
curl -s -X POST $BASE/api/kb/agent/chat \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"在知识库中查找 Transformer 缩放点积注意力公式并给出出处"}' | jq

# ③ 长任务用异步模式：即返 task_id，轮询取结果
TASK=$(curl -s -X POST $BASE/api/kb/agent/chat \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"<任务>","mode":"async"}' | jq -r .task_id)
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/kb/agent/tasks/$TASK | jq
```

---

## 3. 认证

| 项 | 值 |
|---|---|
| 启用条件 | `config.yml` `server.auth.enabled: true`（当前生产配置：**启用**） |
| 携带方式 | `Authorization: Bearer <token>`（亦接受 `X-KB-Token` 头） |
| 登录 token | `POST /api/auth/login` 返回，有过期时间（`token_expires_at`） |
| **长期 API Token（外部集成推荐）** | `POST /api/auth/tokens` `{name, ttl_days?, scopes?}`，**明文仅返回一次**，可 `GET /api/auth/tokens` 列出、`DELETE /api/auth/tokens/:id` 撤销 |
| 校验端点 | `POST /api/auth/verify` `{token}` → `{valid: true|false, user}` |
| 免认证端点 | `/api/health`、`/api/health/*`、`/api/auth/*` |
| 失败响应 | `401`，`data.hint` 含可读指引；无 token 与无效 token 均为 401 |

> ⚠️ backend 重启后登录 token 需重新获取（verify 缓存 60s；网络类校验失败不缓存，fail-closed）。

---

## 4. 通用约定

### 4.1 基址与环境

| 环境 | Web 层（本文端点宿主） | backend（内部） |
|---|---|---|
| dev | `http://localhost:6789` | `http://localhost:8770` |
| prod | `http://localhost:3000` | `http://localhost:8001` |

端口全部来自 `config.yml`（单一配置源），可被 `BACKEND_PORT` / `APP_MODE` 覆盖。
**注意**：`/api/kb/agent/chat` 历史上多次被误配到 backend 端口——它在 **Web 层**。

### 4.2 字段命名

- HTTP body 以 **camelCase** 为准，同时接受 snake_case 别名（`kb_id`/`doc_path`/`doc_id`/`target_kb_id`/`top_k`/`max_chars`…自动归一化）；查询参数 `?kb_id=` 与 `?kbId=` 等价。
- KB 标识 `kbId` 可传 UUID 或库的相对路径名。
- ⚠️ **跨通道字段名差异**（实测钉死）：`/api/claude/chat`（交互面）响应会话字段为 **`sessionId`**（驼峰）；`/api/kb/agent/chat`（Agent 面）响应为 **`session_id`**（下划线）。续轮/续会话时以各自通道返回的字段名为准。

### 4.3 错误结构

h3 统一错误壳（全部命名空间一致）：

```json
{
  "error": true,
  "statusCode": 401,
  "statusMessage": "Unauthorized",
  "message": "...",
  "data": { "error": "unauthorized", "message": "认证失败: 缺少 token", "hint": "..." }
}
```

| 码 | 场景 |
|---|---|
| 400 | 参数校验失败（如 `prompt (string) 必填`） |
| 401 | 未认证 / token 无效或过期 |
| 404 | 资源不存在（如异步 task 已过期：`task not found …（不存在、已过期(2h) 或服务已重启）`） |
| 409 | 重名知识库等冲突 |
| 429 | 限流（见 4.5） |
| 502/503 | 上游不可用（backend 宕机、kb-mcp 挂载失败 `KB_MCP_DOWN`） |

### 4.4 超时与规模上限（Agent 面）

| 上限 | 值 | 说明 |
|---|---|---|
| `prompt` 长度 | **16,000 字符**，超出静默截断 | 控制字符会被消毒替换 |
| 单回合超时 | **600s 默认 = 600s 硬顶** | `timeout_ms` 可传 10,000–600,000，超出钳位 |
| agent 最大轮数 | 40 | 引擎侧 maxTurns |
| 异步任务保留 | **2h TTL / 200 条**（单进程内存注册表） | 超过即 404；Web 进程重启清空 |

### 4.5 限流

per-IP 滑动窗口 **600 req/60s**（heavy 类 60 req/60s，`server.rate_limit`）。超限 429，调用方应做退避。

---

## 5. 端点参考

### 5.1 健康与元信息

#### `GET /api/health`（免认证）

存活探针。响应：`{status:"ok", service:"rag-knowledge-web", time, stats:"/api/health/stats"}`。

#### `GET /api/health/stats`（免认证）

聚合指标仪表盘。

#### `GET /api/kb/agent/meta`（Bearer）

Agent 服务面的自描述契约：可选引擎清单 + 各引擎 permission modes + 请求体说明。
响应核心：`{success, chat:{endpoint, body{...}}, engines:[{id, permissionModes:[{id}...]}], ...}`。
当前 chat-capable 引擎：`claude, omp, dsh, hermes, codex, gemini, copilot, cursor, opencode, crush, goose, qwen, pi, mock`。

#### `GET /api/harnesses`（Bearer）

统一 Harness 注册表（合并 backend 注册探测 + web 层 chat 能力矩阵）：
`{success, backend_reachable, default, count, harnesses:[{id, installed, available, version, models, capabilities, transport, hitl, chat, permissionModes, defaultMode, requires_env, issues, hint}...]}`。

### 5.2 Agent 服务面（核心集成通道）

#### `POST /api/kb/agent/chat`（Bearer）⭐

一个任务提示进，一个完整结果出。KB 系统的原生 Agent（默认 claude harness，进程内 Agent SDK）
自主决定执行方式：检索问答走 `/knowledgebase-search` skill 的 HMRS 管线；入库走写+索引+回查；
经验/图谱等用原生 kb-mcp 工具。**系统会自动注入知识库服务增强提示词**（服务代理契约：工具纪律、
禁编造、doc_path 引用与 P0/P1/P2 可信度标注、强制 `## Result` 结构化收尾段），调用方无需也不应
自行拼装检索步骤。

请求体：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `prompt` | string | ✅ | — | 任务描述（≤16,000 字符） |
| `harness` | string | — | `claude` | 引擎 id（见 `GET /api/kb/agent/meta`） |
| `permission` | string | — | `bypassPermissions` | 权限模式；须为所选引擎真实暴露的模式，未知值回退安全模式 |
| `mode` | string | — | `sync` | `sync`=挂起至完成；`async`=即返 task_id |
| `timeout_ms` | number | — | 600000 | 10,000–600,000，越界钳位 |

**同步响应**（`mode=sync`，HTTP 200）：

```json
{
  "success": true,
  "reply": "…完整答案…\n## Result\n- …",
  "engine": "claude",
  "permission": "bypassPermissions",
  "tools_used": ["Skill", "mcp__kb-mcp__kb_search_vector", "mcp__kb-mcp__kb_laya_judge", "mcp__kb-mcp__kb_doc_read"],
  "session_id": "90894e5a-…",
  "duration_ms": 438826,
  "total_cost_usd": 1.23,
  "num_turns": 11,
  "stop_reason": "end_turn"
}
```

**异步响应**（`mode=async`，**<1s 即返**）：

```json
{ "success": true, "mode": "async", "task_id": "kbt_…", "status": "running",
  "engine": "claude", "permission": "bypassPermissions", "poll": "GET /api/kb/agent/tasks/kbt_…" }
```

**失败响应**：`{success:false, error, stage:"timeout"|"engine"|"validation", hint?, partial_text?, tools_used?, session_id?}`。
`partial_text` 尽力保留超时前的部分输出；`tools_used` 保留已发生的工具轨迹（超时回合依然可用于归因）。

> 💡 **延迟预算（实测）**：有界快速检索回合 ~100–450s（$0.4–1.3）；无界"完整深检索"提示可能超 600s 硬顶
> （见 §8 L1）。**集成方务必在 prompt 中限定检索深度与答案预算**（示例见 §7）。

#### `GET /api/kb/agent/tasks/:taskId`（Bearer）

异步回调面。运行中返回 `{...,status:"running",result:null}`；终态返回完整 chat 信封
（`status:"completed"|"failed"`，`result` = 同步响应同构对象）。任务不存在/过期 → 404。

#### `GET /api/kb/agent/meta` — 见 §5.1。

### 5.3 交互式对话面

#### `POST /api/claude/chat`（Bearer）

面向多轮会话的对话端点（Web UI 同款通道，外部系统亦可直调）。支持 SSE 流式与 final-only JSON。

请求体（常用字段）：

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `prompt` | string | ✅ | 用户消息 |
| `stream` | boolean | `true` | `true`=SSE 流帧；`false`=完成后单个 JSON |
| `kbEnhanced` | boolean | `false` | **注入知识库检索增强提示词**（HMRS 快速管线，钉 6–10 次工具调用内完成）并挂载 kb-mcp |
| `kbIds` | string[] | — | 钉定检索的知识库集合（配合 kbEnhanced） |
| `resume` | string | — | 上一轮响应的 `sessionId`，续会话（无原生会话的引擎由服务端重放历史） |
| `engine` | string | `claude` | `claude` \| `omp` |
| `timeout_ms` | number | — | 本轮墙钟预算 |
| `mcpMount` | string | `sse` | `stdio` 可消除 MCP 注册竞态（需要保证首轮工具面时用） |
| `maxTurns` / `permissionMode` / `model` / `reasoningEffort` / `allowedTools` / `attachments` | — | — | 进阶控制，见实现 `chat.post.ts` |

**非流式响应**：`{success, toolCalls[], toolCallCount, engine, sessionId, model, subtype, answer, duration_ms, duration_api_ms, num_turns, total_cost_usd, elapsed_ms}`。

**流式**：SSE 帧（`event: …`），权限请求帧含 `{toolName, input, toolUseId, sessionId}`；`stream=false` 时权限请求自动拒绝（无人工审批面）。

#### `GET /api/claude/engines`（Bearer）

兼容端点（自 `GET /api/harnesses` 派生）：`{engines:{claude:{available}, omp:{available}, …}}`。

#### `GET /api/claude/history` / `GET /api/claude/history/:sessionId` / `DELETE /api/claude/history/:sessionId`（Bearer）

会话历史列表 / 单会话消息 / 删除。

### 5.4 知识库目录与检索

| 方法 | 路径 | 说明 | 关键参数 |
|---|---|---|---|
| GET | `/api/kb/catalog` | 全库目录（含 docCount） | — |
| GET | `/api/kb/search` | 跨库**关键词**检索 | `?query=&top_k=10` |
| POST | `/api/search/vector` | 语义向量检索（代理 backend） | `{query, kb_id?, top_k?}` |
| POST | `/api/search/two-stage` | BM25→向量两阶段（主检索入口） | `{query, kb_id?, stage2_top_k?}`；断言 `body.success`，命中在 `body.stage2.results` |
| POST | `/api/search/batch-vector` | 批量向量检索 | `{queries[], …}` |
| POST | `/api/search/reindex` | 重建索引 | `{kb_id, force?}` |

`GET /api/kb/catalog` 响应：`{success, count, knowledgeBases:[{kbId, name, description, documentCount, path, parentId}]}`。

### 5.5 知识库与文档管理

| 方法 | 路径 | 说明 | 关键字段 |
|---|---|---|---|
| POST | `/api/kb/create` | 创建库（**重名 409**） | `name`, `description?`, `parentId?` |
| PUT | `/api/kb/update` | 更新库元信息 | `kbId`, `name?`, `description?` |
| DELETE | `/api/kb/delete` | 删除库 | `kbId` |
| GET | `/api/kb/documents` | 库内文档列表 | `?kbId=` |
| GET | `/api/kb/document` | 单文档详情 | `?kbId=&docPath=` |
| POST | `/api/kb/documents/create` | 新建 Markdown 文档 | `kbId`, `name`, `content`, `description?` |
| PUT | `/api/kb/documents/content` | 更新正文（**自动重索引**） | `kbId`, `docPath`, `content` |
| PATCH | `/api/kb/documents/update` | 更新元信息（改名含内联索引卫生） | `kbId`, `docPath`, `name?`, `description?` |
| PATCH | `/api/kb/documents/tags` | 更新标签 | `kbId`, `docPath`, `tags[]` |
| POST | `/api/kb/documents/move` | 移动文档 | `docPath`, `targetKbId` |
| DELETE | `/api/kb/documents/delete` | 删除文档 | `kbId`, `docPath` |
| POST | `/api/kb/documents/batch-delete` | 批量删除 | `kbId`, `docPaths[]` |
| GET | `/api/kb/documents/by-tag` | 按标签查文档 | `?tag=&kbId?=` |
| GET | `/api/kb/tags` | 全局标签清单 | — |
| POST | `/api/kb/tags` | 注册新标签（≤50 字符） | `tag` |
| DELETE | `/api/kb/tags` | 删标签：`?tag=xxx` 删单个；`?cleanup_orphans=true` 批量清孤儿+垃圾标签 | — |
| GET | `/api/kb/tags/analysis` | 标签统计分析 | — |

### 5.6 解析入库（PDF/文件 → KB）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/parse/file-vt` | 单文件解析（异步任务式，返回 markdown_path 后需入库） |
| POST | `/api/parse/batch-file-vt` | 批量解析（JSON） |
| POST | `/api/parse/batch-file-vt-stream` | 批量解析（SSE 进度流） |
| POST | `/api/parse/save-parsed-files` | 解析产物入库（默认整篇；显式 `split:true` 才拆分） |

### 5.7 经验库

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/experience/:kbId/init` | 初始化（幂等） |
| POST | `/api/experience/:kbId` | 写入结构化经验 `{title, category, problem, solution, key_lessons?, tags?}` |
| GET | `/api/experience/:kbId` | 列出库内经验 |
| GET | `/api/experience/:kbId/:expId` | 读单条 |
| PUT / DELETE | `/api/experience/:kbId/:expId` | 更新 / 删除 |
| POST | `/api/experience/:kbId/search` | 关键词检索 |
| POST | `/api/experience/:kbId/vector-search` | 向量检索 |
| GET | `/api/experience/:kbId/summary` | 摘要 |
| POST | `/api/experience/:kbId/:expId/apply` / `review` | 应用 / 评审（可信度模型输入） |

### 5.8 知识图谱（读为主）

`GET /api/graph/stats`（含 `neo4j_available`）、`GET /api/graph/search?query=`、`GET /api/graph/document?docPath=`、
`GET /api/graph/neighbors`、`GET /api/graph/paths`、`GET /api/graph/related`、`GET /api/graph/kb-overview?kbId=`、
`GET /api/graph/cross-kb`、`GET /api/graph/central`、`GET /api/graph/health`；
写构建：`POST /api/graph/build-kb`（→task）、`POST /api/graph/build-all`。

### 5.9 自动化与冥想（2026-11 新增面）

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| GET | `/api/kb/automation` | 查询库级**自动经验总结**状态（开关/计数器/下次触发/历史） | `?kb_id=` |
| POST | `/api/kb/automation/toggle` | 开/关自动经验总结 | `{kbId, enabled}` |
| POST | `/api/kb/automation/summarize` | 手动触发一次经验总结（不依赖开关） | `{kbId}` |
| GET | `/api/kb/meditation` | 读库级冥想配置（`.knowledge-base.yml` metadata） | `?kbId=` |
| PUT | `/api/kb/meditation` | 合并更新冥想配置（MERGE 语义，保留扩展字段） | `{kb_id, config}` |
| GET | `/api/meditation/harnesses` | 冥想 Harness 注册表（14+1 引擎/能力/凭据清单/默认值） | — |
| GET | `/api/meditation/models?harness=` | 按引擎模型目录 | `?harness=` |
| POST | `/api/meditation/run` | 触发一次冥想运行（body 支持 `harness` 指定引擎） | `{kb_id, harness?, …}` |
| GET | `/api/meditation/status` / `history` | 运行状态 / 历史 | — |

冥想运行错误契约（可读）：未知引擎 400 `HARNESS_UNKNOWN`；未安装 409 `HARNESS_NOT_INSTALLED`；
已装未配凭据 409 `HARNESS_NOT_CONFIGURED`（`issues` 数组）；运行期失败响应体带 `error_code`（`HARNESS_TIMEOUT` 等）+ `hint`。

### 5.10 SOUL 人格（面向人格问答的简要面）

`POST /api/soul/ask`（人格注入问答）、`POST /api/soul/hmrs-ask`（HMRS 检索集成问答，`/api/soul/qdcvr-ask` 为废弃别名）、
`POST /api/soul/router`（自动路由）、`GET /api/soul/list` / `status`；训练/蒸馏/RL/检查点等生命周期端点
（`learn`/`train-all`/`train-rl`/`evaluate`/`checkpoint`/`rollback`/`distill*`/`cognition-drafts`/`review`/`reflect`/`tasks`）详见 `docs/soul-lora-pipeline.md` 与实现。

### 5.11 其余（Web UI 专用，外部集成一般不消费）

`/api/config/*`、`/api/filesystem/*`、`/api/preview/*`、`/api/system/*`、`/api/claude/{terminal,upload,permission,sessions,skills,workspaces}`、
`/api/harnesses/:id/{diagnostics,models}`、`/api/meditation/{models,harnesses}`（UI 侧）等——完整 136 条清单见
`review/api-harness-e2e-20261118/route-inventory.txt`。

---

## 6. 异步任务集成指南（Agent 面 `mode:"async"`）

```
调用方                          Web 层                       harness 子进程
  │ POST agent/chat {mode:async}  │                              │
  │──────────────────────────────▶│ 注册 task → 即返 task_id(<1s) │
  │◀────{task_id, poll}───────────│ spawn 引擎回合（后台必达）      │──▶ 执行中…
  │                               │                              │
  │ GET tasks/:id（建议 10s 间隔） │                              │
  │──────────────────────────────▶│ running / result:null         │
  │◀──────────────────────────────│                              │
  │            …轮询…              │   settleTask(completed|failed)│◀── 结束
  │ GET tasks/:id                  │                              │
  │──────────────────────────────▶│ {status:"completed", result:{success, reply, tools_used, …}} │
  │◀──────────────────────────────│                              │
```

要点：

1. **后台必达**：task 一经受理即在后台执行完毕（HTTP 客户端断开不影响）；轮询方离线再回来取也成立（2h 内）。
2. **轮询节奏**：10s 间隔即可（回合典型 100–450s）；收到 `status!="running"` 即终态。
3. **容错**：404 = 任务过期（2h）或 Web 进程重启过 → 需重新提交；`result.stage=="timeout"` = 超 600s 硬顶 → 收紧 prompt 后重试。
4. **幂等**：平台侧无 task 去重；调用方应自行用业务键幂等（如入库任务先 `GET /api/kb/documents?kbId=` 查重）。
   Agent 侧亦有内建防线：入库前核对目录，等价文档已存在则视为完成并报告既有 doc_path。

---

## 7. AgentWorkShop 插件集成要点

1. **Base URL = Web 层**（dev `:6789`），不是 backend。历史教训：rag-bridge 默认 base_url 指错端口导致连接拒绝；`agent/chat` 端点在 web 层（2026-10-21 run5 再次实锤）。
2. **凭证通道**：用长期 API Token（`POST /api/auth/tokens`，scopes `[read,write]`），`Authorization: Bearer` 头统一注入；401 时重铸。不要把登录会话 token 硬编码进插件。
3. **主通道**：`POST /api/kb/agent/chat`。检索/入库/经验/图谱全部交给 KB Agent；插件侧不编排工具调用。
4. **prompt 模板（延迟安全）**：

   ```text
   在知识库中查询：<问题>。
   执行约束：按 /knowledgebase-search skill 的快速路径作业（kb_list 甄别 → kb_search_vector
   → kb_laya_judge 一批（≤6 refs）→ 至多 1-2 次 kb_doc_read 验证），不要委派子代理，
   不要浏览仓库文件。最终答案 ≤N 字并给出 doc_path 出处。
   ```

5. **响应消费**：`success` 必查；`reply` 内按 `## Result` 段提取结构化产物（doc_path / experience id / chunk 数）；
   `tools_used` 可作为车道合规审计（应含 `mcp__kb-mcp__*`）；引用可信度以 `reply` 内 P0/P1/P2 标注为准。
6. **双模式选型**：交互式插件（有用户在线等待）用 sync + 有界 prompt；后台批处理用 async + 轮询。
7. **字段契约**：Agent 面 `session_id`、交互面 `sessionId`——两套通道勿混用。
8. **限流共享**：插件与 Web UI 共享 per-IP 600/60s 配额，批处理场景客户端做 429 退避。
9. **降级兜底**：Agent 面不可用时（502/503），chunk 级 `POST /api/search/two-stage` 可作只读兜底（断言 `body.success`）。

---

## 8. 已知限制与调优（2026-11-18 实测）

| # | 级别 | 现象 | 缓解 |
|---|---|---|---|
| L1 | 运营 | 无界"深检索"提示词（+并发+冷 MCP 暖机）可超 600s 硬顶，超时回合 `stage:"timeout"`；**实测超时回合的服务端回包可能晚于 630s**（引擎子进程终止有额外开销） | prompt 限定快速路径与答案预算（§7.4 模板）；长任务改 async；**客户端 HTTP 读超时建议设 ≥750s**；平台侧可考虑暴露 fast-path 开关 |
| L2 | 环境 | `kb_laya_judge` 判卷引擎 `ModuleNotFoundError: No module named 'laya'`，fail-closed 降级 | Agent 行为正确：如实声明盲点并回退直接读原文核验；恢复 laya 模块即愈。集成方照常信任 doc_path 引用 |
| L3 | ~~已撤销~~ | R1 轮曾报"resume 轮不回显 sessionId"——R2 轮实测 resume 响应**正常回显** `sessionId`（同值），R1 结论系验收脚本字段提取缺陷，非平台缺陷 | 两轮对话均可用响应中的 `sessionId` 续轮 |
| L4 | 设计内 | 异步注册表为单 Web 进程内存态（2h TTL/200 条） | 重启丢失未取结果属预期；长期任务调用方应在拿到终态后即时消费 |

---

## 9. 端到端验证脚本

- `python scripts/dev_smoke.py` — 纯外部 HTTP 自检（SSRF 加固）。
- `python review/api-harness-e2e-20261118/runner.py` / `runner_r2.py` — Agent 面五组真机验收
  （sync / async / OOD 拒答 / 交互续轮 / 入库全管线），工件落盘同目录。
- `python .ui-audit/e2e_platform.py` — KB 管理→检索→图谱→经验→人格全链路（自动清理自建数据）。

## 10. backend 命名空间备注

backend（`:8770`）自带 OpenAPI：`http://localhost:8770/openapi.json`（`/api/v1/search|experience|graph|soul|automation|meditation` 等原生前缀）。本文 Web 层端点与其语义一致（Web 薄代理），集成一律走 Web 层。

## 11. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.0 | 2026-11-18 | R2 轮全量补充：Agent 服务面三端点（chat/tasks/meta）完整契约；交互式对话面（claude/chat SSE/JSON、resume、kbEnhanced、mcpMount）；自动化与冥想面（automation/meditation，11 月新增）；Harness 注册表；异步任务集成时序与容错；AgentWorkShop 集成要点九条；已知限制 L1–L4（600s 顶/laya 降级/sessionId 回显/内存注册表）；字段命名差异（sessionId vs session_id）；勘误 backend 端口 8771→8770 |
| v1.0 | 2026-09-09/13 | 初版：认证、KB/文档/文件树、字段别名契约 |
