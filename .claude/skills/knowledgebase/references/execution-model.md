# ⚙️ 执行模型与委托契约（共享参考）

> 本文件是 14 个 knowledgebase skill 的**唯一权威源**：执行角色、委托模板、Pre-Flight、MCP 优先原则。
> 各 skill 不再内联重复这些内容，统一引用本文件 + [mcp-preflight-check.md](mcp-preflight-check.md) + [kb-architecture.md](kb-architecture.md)。

---

## 三角色执行模型

```
用户请求
  │  命中 KB 关键词
  ▼
① Dispatcher (skill://knowledgebase)
  │  纯路由：读输入 → 匹配场景 → 委托
  │  ⚠️ 严禁自行执行任何 KB 操作
  ▼
② Sub-Skill (skill://knowledgebase-<scenario>)
  │  提供步骤流程、决策树、质量门控、工具用法
  │  ⚠️ skill 本身不直接调 MCP 工具
  ▼
③ Archival agent (task 工具委托)
     自主确认场景 → 读 kb-architecture.md → 严格按子 skill 步骤执行
     所有 MCP 工具调用只发生在这里
```

**关键不变量**：
- **Dispatcher 只路由**——不做任何 KB 操作（增删改查索引图谱经验全部禁止）。
- **Skill 不执行**——skill 是知识载体，不直接调 MCP 工具；执行权属于 Archival。
- **Archival 是唯一执行者**——接收委托后自主确认场景，严格跑完子 skill 的全部步骤与质量门控。

**例外**：`knowledgebase-init` 与 `knowledgebase-update` 是**运维/安装类** skill，由**主 Agent 直接执行**（跑 CLI、展示版本对比），**不委托 Archival**——它们不涉及文档 CRUD。

---

## 委托模板（Archival skill 必用）

Archival-delegated skill 委托时，用 `task` 工具：

```
task(
  tasks=[{
    "agent": "archival",
    "name": "KB-<Scenario>",
    "task": "[场景: <场景标签>]\n⭐ 操作前必读 skill://knowledgebase/references/kb-architecture.md\n\n用户需求：<原始需求>",
    "effort": "med"
  }],
  context="RAG Knowledge Platform — MCP tools via kb-mcp, backend on :8765"
)
```

- `task` 字段必须含：**场景标签** + **架构必读引用** + **用户原始需求**。
- 每个 `task(tasks=[{"agent":"archival",...}])` 是**独立上下文**——Archival 看不到主调度器的历史。多步组合任务必须在前序委托 prompt 里**显式传递**关键状态（KB id / 文档路径 / 已变更项 / 已发现问题）。
- **Claude Code 等价写法**：`Agent(subagent_type="archival", prompt=...)`，OMP 自动适配。

### 组合任务（≥2 场景）委托边界

| 阶段 | 动作 | 产出契约 |
|------|------|---------|
| 路由前确认 | 向用户确认完整路由顺序 + 每步子 skill | "将按 A→B→C 执行" |
| 步间委托带上下文 | 每次 Archival 委托 prompt **显式附带前序产出** | `[场景B: Search] 前序 ingest 完成：KB=<名>, 文档=<路径>. 现需检索：<query>` |
| 步后即汇报 | 每步完成即汇报，确认后再进下一步 | 禁止静默连续执行 |
| 失败隔离 | 某步失败：独立后续场景继续；有依赖则停下问用户 | "Ingest 失败。Search 不依赖它，是否继续？" |

> **组合规模上限**：单次会话组合 ≤ 3 个 skill（4+ 组合历史 100% fail）。

---

## Pre-Flight（作业首步，强制）

**未通过预检禁止任何 KB 操作。** 完整流程见 [mcp-preflight-check.md](mcp-preflight-check.md)：

1. **一探双检**：`mcp__kb-mcp__kb_project_status`（无参）→ 成功= MCP 已连接；读 `ready` 字段 = 服务健康。
2. `ready==false` → 静默 `kb_project_start(wait=true)`（图谱/整理/跨库类带 `neo4j=true`）→ 回查。
3. `No such tool` → MCP 未连接本会话：通知用户重启 Claude Code，停止作业。
4. **冒烟测试**：`ready==true` 后，`kb_list(lightweight=true)` 确认 MCP↔backend 真实返回数据。

---

## MCP 优先原则（全库强制）

MCP 工具已连接时，**所有 KB 操作必须通过 `mcp__kb-mcp__*` 工具执行**：

| ❌ 禁止 | ✅ 必须 |
|---------|---------|
| `curl`/`wget`/`httpx` 终端命令操作 KB | `mcp__kb-mcp__kb_*` 工具 |
| `python -c` 调 HTTP API | `mcp__kb-mcp__parse_doc` 工具 |
| Bash 中硬编码 API URL | MCP 保证原子操作 + 审计追踪 |

**例外**：仅当 MCP 明确不可用且用户确认后，才可用终端/HTTP 兜底，并须声明 "MCP 不可用，已用 HTTP API 兜底"。`init`/`update` 走 `ragctl` CLI 不受此约束。完整条款见 [skill-trigger-contract.md](skill-trigger-contract.md) 第五条。

---

## 跨 skill 引用路径约定

14 个 skill 作为同一插件打包发布（见 `.claude-plugin/plugin.json`），始终同目录共存。引用**共享参考**统一用相对路径：

```
../knowledgebase/references/kb-architecture.md        ← 5 层数据模型 + 一致性不变量 + 71 工具地图
../knowledgebase/references/execution-model.md         ← 本文件
../knowledgebase/references/mcp-preflight-check.md     ← Pre-Flight 完整流程
../knowledgebase/references/skill-trigger-contract.md  ← 触发契约 + 五条强制规则
```

引用 **ingest 私有参考**（标签/描述/子KB 规则）：`../knowledgebase-ingest/references/<file>.md`。
