---
name: knowledgebase-update
description: >
  Check the installed RAG Knowledge Platform version against the latest GitHub
  release / default-branch VERSION, and pull updates when available. Safe by
  default (dirty worktree refused, dry-run first). Triggered by: /knowledgebase-update,
  update KB, upgrade knowledge base, check for updates, ragctl update, 更新知识库,
  升级知识库, 检查更新, 拉取最新版, 有新版本吗, 版本更新, project update.
---

# Knowledgebase Update — 版本检查与安全升级
> **⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型+一致性不变量+76工具地图）


**执行者：此技能由主 Agent 直接执行（不委托 Archival）**
- update 是运维/安装类操作，需要直接跑 CLI / 展示版本对比
- 所有 Bash 命令由主 Agent 执行；可用 MCP `kb_project_version` / `kb_project_update` 作为等价入口
- 不涉及文档 CRUD，无需 Archival

> **⭐ Pre-Flight 提示**：本 skill 可走 MCP（`kb_project_version` / `kb_project_update`）或 `ragctl` CLI 两条等价路径。
> - 走 MCP 路径前**必须**按 [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) 完成 MCP 连通性 + 服务预检（拉更新前验一次；pull 后重跑一次确认服务恢复）。
> - 走 `ragctl` CLI 路径不受 MCP 连通性约束（CLI 直跑），但 pull 后仍应用 `ragctl status` 验证服务恢复。
> - MCP 不可用时默认走 `ragctl` CLI，无需用户额外确认。

## 核心原则

- 🔎 **先查后更** — 默认先 dry-run（`--check`），展示本地 vs 远程，用户确认后再 pull
- 🛡️ **脏工作区保护** — 有未提交改动时拒绝自动 pull（除非用户明确要求 `--force`）
- 📦 **版本源唯一** — 以仓库根 `VERSION` 文件为准；GitHub latest release 优先，其次 default branch `VERSION`，再退回 SHA 对比
- 🔁 **全平台** — 统一走 `ragctl update`（Windows / Linux / macOS 同一命令）
- ✅ **更新后验证** — pull 后读新 VERSION，可选 `ragctl check` / `kb_project_status`

---

## Phase 0 — 定位项目根

```
1. 若当前目录（或父目录）存在 VERSION + command/ragctl.js → RAG_ROOT = 该目录
2. 否则读环境变量 RAG_PROJECT_ROOT
3. 否则读 ~/.claude.json → mcpServers → kb-mcp → env.RAG_PROJECT_ROOT
4. 仍找不到 → 提示用户先跑 knowledgebase-init，或 cd 到安装目录
```

```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version --local
```

---

## Phase 1 — 版本对比（强制 dry-run）

**优先 MCP（已连接时）：**
```
mcp__kb-mcp__kb_project_version()
# 或
mcp__kb-mcp__kb_project_update(check_only=true)
```

**CLI 兜底：**
```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js update --check --json
# 人类可读:
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version
Bash: cd "<RAG_ROOT>" && node command/ragctl.js update --check
```

向用户展示：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 版本对比
  本地:  v<local>  (<branch> @ <sha>)  [dirty?]
  远程:  v<remote> (<tag>) @ <remote_sha>
  来源:  release | branch-version | branch-sha
  状态:  已是最新 / 可更新 / 本地超前 / 未知
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 分支决策

| 状态 | 动作 |
|------|------|
| 已是最新 | 报告完成，**停止**（除非用户坚持 `--force`） |
| 可更新 | 进入 Phase 2 询问是否拉取 |
| 本地超前 | 说明本地版本号更高（开发分支），默认不降级 |
| 网络失败 | 给出手动命令：`git pull` |

---

## Phase 2 — 用户确认

```
发现新版本 v<local> → v<remote>。

是否现在更新？
  1. Y — 拉取最新（git pull --ff-only + 增量 deps）
  2. n — 仅记录，不更新
  3. Y+重启 — 拉取后 ragctl up --force
  4. 仅代码 — 拉取但跳过 deps（--no-deps）

请选择 [1/2/3/4，默认: 1]:
```

若工作区 dirty：
```
⚠️ 检测到未提交改动。自动更新已拒绝覆盖。

  A) 我先自己处理（stash/commit）后再说 update
  B) 强制更新（--force，可能覆盖本地修改）— 需二次确认
  C) 取消
```

---

## Phase 3 — 执行更新

**MCP：**
```
mcp__kb-mcp__kb_project_update(
  check_only=false,
  force=<用户确认>,
  no_deps=<选项4>,
  restart=<选项3>
)
```

**CLI：**
```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js update --yes [--force] [--no-deps] [--restart]
```

失败时：
1. 展示 stderr / exit code
2. 给 3 个选项：重试 / 手动 `git status` / 取消
3. **禁止**在失败后假装成功

---

## Phase 4 — 更新后验证

```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js version --local
Bash: cd "<RAG_ROOT>" && node command/ragctl.js check   # 可选，环境仍完整
```

若服务在跑且用户未选重启：
```
提示: 建议 ragctl up --force 加载新代码
提示: kb-mcp / server.py 变更需重启 Claude Code（或 /mcp 重连）
```

MCP 可用时：
```
mcp__kb-mcp__kb_project_status()
mcp__kb-mcp__backend_status()
```

---

## Phase 5 — 完成报告

```
═══════════════════════════════════════════════════════════
  ✅ 更新完成 / 已是最新 / 已取消

  之前: v<old> @ <old_sha>
  现在: v<new> @ <new_sha>
  远程: v<remote> (<tag>)

  后续:
    ragctl status
    ragctl up --force          # 如需重启服务
    重启 Claude Code           # 如 MCP 代码有变
═══════════════════════════════════════════════════════════
```

---

## 与 init 的关系

| 场景 | 路由 |
|------|------|
| 全新机器、无项目 | `knowledgebase-init`（clone + setup） |
| 已安装、查/拉更新 | **本 skill** `knowledgebase-update` |
| init 配置 12「自动更新」= Y | 启动时可由 agent 调 `ragctl update --check`，有更新再引导本 skill |

---

## ⚠️ NEVER

| ❌ | ✅ |
|----|----|
| 不问用户直接 `git reset --hard` | 默认 `--ff-only`；脏树拒绝；`--force` 需确认 |
| 跳过 dry-run 直接 pull | Phase 1 必须先 `--check` |
| 版本对比用硬编码字符串 | 读 `VERSION` + GitHub API / raw VERSION |
| 更新失败仍报成功 | 检查 exit code + 新 VERSION |
| 在非 git 目录硬 pull | Phase 0 检测 is_git，引导 re-clone 或 init |
| 用 curl 绕过 ragctl 自己拼 git | 统一 `ragctl update` / MCP `kb_project_update` |
