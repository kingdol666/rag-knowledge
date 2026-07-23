# ⚡ MCP 连通性 + 项目服务预检（强制契约）

> 所有知识库 skill 的 **Pre-Flight**（每个 skill 作业前的第一步，早于各自 A0 / Step 0 / Step 1 等编号步骤）。
> **未通过预检，不得开始任何 KB 操作。**
> 本文件是权威细则；各 skill 的 Pre-Flight 内联段是其精简可执行版。
---

## 为什么必须有这一步

kb-mcp 的 76 个工具全部通过 HTTP 转发到后端服务。两件事缺一不可，**只查其一等于没查**：

1. **kb-mcp MCP server 已连接到当前 Claude Code 会话** —— 由 Claude Code **启动时**按 `.mcp.json` 加载，会话进行中无法变更。
2. **后端（FastAPI）+ 前端（Nuxt）服务已运行且 HTTP 健康** —— MCP 工具实际转发的目标。

- MCP 未连接 → 工具调用直接报 `No such tool available`。
- 服务未起 → 工具能调，但每次都报后端不可达。

所以两段都必须验，且可以**用一次调用同时验两段**。

---

## 预检流程（一探双检）

### 1. 单次探测 = 连通性 + 服务状态

调用 `mcp__kb-mcp__kb_project_status`（无参）。

| 返回情况 | 判定 | 下一步 |
|---|---|---|
| **调用成功** | 段一通过（MCP 已连接——能调即在线） | 读 `ready` 字段分支 |
| 　└ `ready == true` | backend AND web 双 HTTP 健康 → **就绪** | → 冒烟测试 |
| 　└ `ready == false` | 服务离线 | → **Case B** |
| **报错 `No such tool available` / tool-not-found** | 段一失败：MCP 未连接本会话 | → **Case C** |

### 2-A. Case B — 服务未起（MCP 在线，服务离线）

1. 先调 `mcp__kb-mcp__kb_project_preflight()`：
   - `ready_to_start == false` → 项目未安装。把 `problems` 与 `fix`（通常 `ragctl setup`）报告用户，**停止**，不盲目重试。
   - `ready_to_start == true` → 继续。
2. 静默拉起服务（**不问用户、不开终端**）：
   - 图谱 / 整理 / 跨库检索类 skill（依赖 Neo4j）：`kb_project_start(backend=true, web=true, neo4j=true, wait=true)`
   - 其他 skill：`kb_project_start(backend=true, web=true, wait=true)`
   - `wait=true` 阻塞至 HTTP 健康或 ~45s 超时，返回最终状态块。
3. **回查**：再调一次 `kb_project_status`。
   - `ready == true` → 进入冒烟测试。
   - 仍 `false` → 读 `ragctl logs backend`（或 `backend/logs/desktop-stdout.log`），把错误报告用户，**停止**，禁止静默循环重试。

> 启动全程由 MCP 工具完成，dev/prod 行为一致，不弹任何终端窗口。stdout/stderr 写入 `backend/logs/desktop-stdout.log` 与 `web/logs/desktop-stdout.log`（与 `ragctl logs` / Tauri 控制台同源）。MCP 工具不可用时兜底 `Bash: node command/ragctl.js up`（同样静默、同源日志）。

### 2-B. Case C — MCP 未连接到本会话

MCP server 由 Claude Code **启动时**加载，**会话中无法重连**。处理：

1. 诊断：`Bash: node command/ragctl.js status`（或 `ragctl status`）看 backend/web/MCP 各自状态。
2. 通知用户：**「⚠️ kb-mcp MCP 服务器未连接到当前会话（Claude Code 未加载 `.mcp.json`）。请重启 Claude Code 使其自动加载 kb-mcp；后端/前端可用 `ragctl up` 静默拉起。」**
3. **禁止**在 MCP 未连通时继续 KB 操作。仅在用户**明确同意**后，可按 [MCP 优先原则例外条款](skill-trigger-contract.md#第五条mcp-优先原则2026-07-13-新增全库强制执行) 用 HTTP/终端兜底，并须声明 "MCP 不可用，已用 HTTP API 兜底"。

### 3. 连通性冒烟测试（必做）

`ready == true` 之后、**正式操作之前**，做一次**轻量只读** MCP 往返，确认 MCP↔backend 真实可达（不仅端口通，且能返回数据）：

- 通用首选：`mcp__kb-mcp__kb_catalog()`（返回 KB 清单）。
- 或：`mcp__kb-mcp__kb_tags_list()`（返回标签词表）。
- 各 skill 也可用自己流程中的首个只读探针（检索类的 `kb_search`、图类的 `kb_graph_stats` 等）。

返回真实数据（非空、非错误）→ **预检全通过**，开始作业。

---

## 速查决策表

| `kb_project_status` 结果 | 判定 | 动作 |
|---|---|---|
| 成功 + `ready==true` | 就绪 | 冒烟测试 → 作业 |
| 成功 + `ready==false` | 服务离线 | `preflight` → `kb_project_start(wait=true)` → 回查 → 冒烟测试 |
| `No such tool` | MCP 未连接 | `ragctl status` 诊断 → 通知用户重启 Claude Code → 停止 |

---

## 各 skill 的额外注意

- **图谱 / 整理 / 跨库检索**：`kb_project_start` 须带 `neo4j=true`（依赖 Neo4j，需 Docker）。冒烟测试可顺带 `kb_graph_health()` 确认图数据库在线。
- **解析类（ingest）**：服务就绪后顺带 `backend_status()` 确认 **MinerU OCR 引擎可用**，否则 `parse_doc(use_ocr=true)` 会失败。
- **Init / Update（生命周期 skill）**：二者是安装/运维 skill，MCP 连通性是它们的**产物或前置**而非作业前提：
  - **init**：完成安装/注册后，**必须**跑本预检（含冒烟测试）验证连通，作为 Phase「全链验证」的组成。
  - **update**：拉取更新**前**应先通过本预检（MCP 在线才能用 `kb_project_version` 对比版本）；拉取**后**重跑本预检确认服务恢复。

---

## 违规自纠

若发现自己已跳过本预检直接做了 KB 操作：
1. **立即停止**当前操作。
2. 补跑本预检；若发现服务实际未起 / MCP 未连，清理可能产生的脏状态。
3. 向用户说明纠正了什么。
