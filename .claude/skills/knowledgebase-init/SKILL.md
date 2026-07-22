---
name: knowledgebase-init
description: >
  Smart incremental installation wizard for the RAG Knowledge Platform. Audits
  the existing environment FIRST and only installs/configures/downloads what is
  genuinely missing — never re-installs or re-downloads components that already
  work. Auto-detects GPU (NVIDIA CUDA / AMD ROCm / Apple MPS / CPU fallback),
  chooses the correct PyTorch wheel variant per platform, and supports
  Windows / Linux / macOS. Two install methods: (A) plugin install — auto-detects
  project in ~/.claude/plugins/cache/; (B) skills copy — clones if needed.
  Then guides through: prerequisite checks, incremental dependency install,
  GPU-adaptive torch, incremental model download, configuration (only for
  missing items), ragctl global registration, optional MCP global registration
  (~/.claude.json → mcpServers, user consent required), service startup,
  full-chain validation. Triggered by: /knowledgebase-init, init KB, setup
  knowledge base, install rag knowledge, deploy KB, start KB, bootstrap,
  getting started, 初始化知识库, 安装知识库, 部署知识库, 知识库启动,
  kb init, knowledgebase setup wizard, 知识库安装向导, 配置知识库, 引导安装知识库.
---

# Knowledgebase Init — 智能增量部署向导
> **⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型+一致性不变量+76工具地图）


**执行者：主 Agent 直接执行（不委托 Archival）** — init 需要实时交互，所有 Bash 命令由主 Agent 执行。

## 核心原则

- ⚡ **增量原则** — 先审计（`ragctl check`），只处理缺失项。已安装的跳过，已缓存的跳过，已配置的不重复问
- 🖥️ **GPU 自适应** — 检测 NVIDIA/AMD/Apple，选对 torch wheel（详见 [gpu-and-torch.md](references/gpu-and-torch.md)）
- 🚀 **快路径** — 环境已完整时跳过所有安装，仅验证
- 💬 **逐项询问** — 仅对缺失/需决策项询问
- 🚫 **零擅自决策** — 路径/端口/密码/功能开关需用户确认

## Phase 总览

| Phase | 动作 | 详细参考 |
|-------|------|---------|
| **0** GPU 检测 | `node scripts/detect_gpu.cjs` → 确定 `TORCH_VARIANT` | [gpu-and-torch.md](references/gpu-and-torch.md) §检测 |
| **1** 环境审计 | `ragctl check` → 分类缺失项 → 快路径判定 | 见下方"快路径" |
| **2** 项目定位 | 4 方法自动检测 / clone | [project-location.md](references/project-location.md) |
| **3** 核心依赖 | 仅装缺失的 uv/Node/Python3.12 | [incremental-install.md](references/incremental-install.md) §核心依赖 |
| **4** 项目依赖 | 仅装缺失的 backend/web/mcp/cli + GPU torch | [gpu-and-torch.md](references/gpu-and-torch.md) §安装 + [incremental-install.md](references/incremental-install.md) §项目依赖 |
| **5** 模型下载 | 仅下载缺失的 BGE-M3 / MinerU | [incremental-install.md](references/incremental-install.md) §模型 |
| **6** 配置 | 仅问缺失项，写入 config.yml + .env | [configuration.md](references/configuration.md) §Phase 6 |
| **7** ragctl 注册 | 已注册则跳过 | [configuration.md](references/configuration.md) §Phase 7 |
| **8** MCP 注册 | 可选，默认跳过 | [configuration.md](references/configuration.md) §Phase 8 |
| **9** Neo4j | 已运行则跳过 | `docker compose up -d neo4j` |
| **10** 服务启动 | 已 healthy 则跳过 | `ragctl up` |
| **11** 全链验证 | health + MCP + torch match | 见下方"验证" |

> **Phase 2 跳过条件**：若 Phase 1 的 `ragctl check` 成功运行（CWD 已在项目内），说明 `<RAG_ROOT>` 已确定，跳过 Phase 2。

## 快路径判定（Phase 1c）

运行 `ragctl check` 后，若以下全部满足 → **跳到 Phase 11 验证，不安装/下载/询问任何内容**：

- 核心依赖 ✅（uv, Node≥18, Python 3.12）
- 项目文件 ✅（config.yml, .env, backend, web, kb-mcp）
- 依赖 ✅（backend/.venv, web/node_modules, kb-mcp/.venv）
- Torch GPU 匹配（`node scripts/detect_gpu.cjs --verify-torch` → `torch_match: ok`）
- BGE-M3 已缓存（snapshots/ 有 pytorch_model.bin > 1GB）
- 服务已运行（backend + web healthy）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ 环境已完整就绪 — 无需安装/下载
  ragctl check: <N>项通过  BGE-M3: ✅  Torch: ✅匹配  服务: ✅
  正在验证连通性...（Phase 11）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Phase 0 — GPU 检测

```bash
cd "<RAG_ROOT 或 CWD>" && node scripts/detect_gpu.cjs
```

记录 `TORCH_VARIANT`（cuda/cpu-forced/mps/rocm/cpu）和 `TORCH_WHEEL`。决策表和内联检测见 [gpu-and-torch.md](references/gpu-and-torch.md)。

## Phase 1 — 环境审计

```bash
cd "<RAG_ROOT 或 CWD>" && ragctl check 2>&1
# ragctl 不可用时：node command/ragctl.js check
```

从输出提取 ✅/⚠️/❌，分类为：核心依赖、项目文件、依赖安装、AI 模型、端口。然后做快路径判定。

## Phase 4a — GPU 自适应 Torch

根据 Phase 0 的 `TORCH_VARIANT`：

- `cuda` / `mps` / `rocm` / `cpu` → `cd backend && uv sync --python 3.12`（marker 自动选 wheel）
- `cpu-forced`（无 GPU 的 Win/Linux x64）→ 先装 CPU torch 再 sync，详见 [gpu-and-torch.md](references/gpu-and-torch.md) §cpu-forced

**安装后必验证**：`node scripts/detect_gpu.cjs --verify-torch` → `torch_match` 必须为 `ok`。

## Phase 5 — 模型增量下载

**BGE-M3**：验证缓存（snapshots/ 有 pytorch_model.bin > 1GB）→ 有效跳过，否则 `ragctl model --source <source>`

**MinerU**：`curl localhost:<port>/api/v1/mineru/status` → `available:true` 跳过，否则 `ragctl mineru-model`

详细缓存验证逻辑见 [incremental-install.md](references/incremental-install.md) §模型。

## Phase 11 — 全链验证

```bash
# 服务健康
curl -s http://localhost:<BACKEND_PORT>/api/v1/health   # → {"status":"healthy"}
curl -s -o /dev/null -w "%{http_code}" http://localhost:<WEB_PORT>/   # → 200

# MCP（如已连接）
mcp__kb-mcp__backend_status()   # backend + MinerU
mcp__kb-mcp__kb_list()          # KB 列表

# Torch GPU 最终确认
node scripts/detect_gpu.cjs --verify-torch   # torch_match: ok
```

### 完成报告

```
═══════════════════════════════════════════════════════════
  ✅ RAG Knowledge Platform 初始化完成！

  📊 Backend ✅  Web ✅  Neo4j ✅(如启用)  MinerU ✅(如启用)
  🖥️  GPU: <CUDA/MPS/CPU>（<GPU名 或 "无GPU">）  Torch: <版本>
  📁 项目: <RAG_ROOT>  数据: <STORAGE_PATH>

  📦 本次增量动作:
     • <列出实际执行的安装/下载/跳过>

  🔧 ragctl status/up/down/logs/check/version/update
  🌐 Web UI: http://localhost:<WEB_PORT>
═══════════════════════════════════════════════════════════
```

## NEVER — 绝对禁止

| ❌ | ✅ |
|----|----|
| 每次初始化全量安装 | 先 `ragctl check`，只装缺失项 |
| 已缓存模型重复下载 | 验证缓存有效后跳过 |
| 已配置项重复询问 | 只问缺失/无效项 |
| 已运行服务重复重启 | `ragctl up` 自动跳过 healthy 服务 |
| 有 GPU 装 CPU torch | Phase 0 检测 GPU 选对 wheel |
| 无 GPU 装 CUDA torch（浪费 2GB） | cpu-forced 强制 CPU wheel |
| 不验证 Torch GPU 匹配 | Phase 4a + 11c 强制验证 |
| 方法 1/2/3 未命中就放弃 | 依次 1→2→3→4，方法 4 含 clone |
| 用户路径不存在直接退出 | 询问后自动 `git clone` |
| `git reset --hard` 强制覆盖 | 拉取用 `--ff-only`，脏工作区跳过 |
| 安装失败继续下一步 | 每 Phase 失败即停，给 3 个恢复选项 |
| 默认执行全局 MCP 注册 | Phase 8 默认跳过，用户明确选 Y 才写 |
| 写 MCP 到 `~/.claude/.mcp.json` | 全局 MCP 写 `~/.claude.json` → `mcpServers` |
