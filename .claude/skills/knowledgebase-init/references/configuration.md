# Configuration & Registration

> Referenced by knowledgebase-init Phase 6 (config), Phase 7 (ragctl), Phase 8 (MCP).

## Phase 6 — Config (only ask for missing items)

Read existing `.env` and `config.yml`. For each item below, if already valid → skip. Only ask for missing/invalid.

| Config | Check | Missing default |
|--------|-------|-----------------|
| APP_MODE | .env has `APP_MODE=dev\|prod` | Ask: dev (8765/6789) vs prod (8001/3000) |
| Ports | .env has BACKEND_PORT/WEB_PORT | Ask (or use mode default) |
| Storage path | .env TREE_STORAGE_PATH or config.yml | `./storage/tree-file-system` |
| Auth | config.yml `server.auth.enabled` | Ask, default false (no token) |
| MinerU | backend/config.yml `mineru.enabled` | `true` |
| MinerU mode | backend/config.yml `mineru.mode` | Ask — Phase 6b below (`remote` default) |
| Neo4j | config.yml `graph.enabled` | Ask (needs Docker), default true |
| Neo4j password | .env NEO4J_PASSWORD | Ask, default `123456` |
| Model source | config.yml `embedding.model_source` | Ask, default modelscope |

### Phase 6b — MinerU 部署模式选择（必问一次，除非已配置）

`mineru.mode` 决定 PDF 解析引擎走哪条路（详见 [mineru-mode.md](mineru-mode.md)）：

```
MinerU 解析引擎模式？
1) 远程 API（推荐/默认）— 解析走 mineru-api HTTP 端点，不占本机 GPU/内存；
   端点不可用时自动回退本地引擎。需要提供 API 地址（+ 可选 token）。
2) 本地部署 — 本机安装 mineru + 下载模型，完全离线。
```

- **选远程**：收集 `base_url`（必填，http/https）与 token（可选，只写入 `.env` 的 `MINERU_API_TOKEN`，
  绝不写进 config.yml 或任何源码/示例）→ 写 backend/config.yml 的 `mineru.mode: remote` + `remote.base_url`
  → 立即验证 `GET {base_url}/health`（200 即通过；不通则提示检查地址/网络，或回退选择本地）。
- **选本地**：跳转 [mineru-mode.md](mineru-mode.md) §本地安装流程 —— 增量检查 venv 中 mineru 是否已装
  （`backend/.venv/Scripts/mineru-api.exe` 或 `bin/mineru-api`）、模型是否已下载（`ragctl mineru-model`），
  只补缺失项，最后以 `GET /api/v1/mineru/status` 的 `available:true` 收尾。

### All config valid → skip asking, show summary

```
📋 现有配置（已完整）  是否修改？[y/N]:
```

### Write config (only changed items)

**config.yml** (use yaml lib, not string replace):
```yaml
embedding:
  model_source: "<choice>"
graph:
  enabled: <true|false>
```

**.env** (append/update only changed keys — never overwrite existing):
```bash
APP_MODE=<dev|prod>
BACKEND_PORT=<port>
WEB_PORT=<port>
TREE_STORAGE_PATH=<path>
NEO4J_PASSWORD=<password>
HF_ENDPOINT=<per model source>
PYTHONUTF8=1
```

## Phase 7 — Global ragctl Registration (incremental)

**Check first:**
```bash
command -v ragctl || where ragctl   # found → run ragctl status to verify; skip if works
```

**Register if missing/broken:**
```bash
cd "<RAG_ROOT>" && ragctl install
```

Writes `~/.local/bin/ragctl(.cmd)` with hardcoded absolute path. Auto-adds to PATH via PowerShell `[Environment]::SetEnvironmentVariable` (Windows) or prints bashrc hint (Linux/macOS).

## Phase 8 — Global MCP Registration (optional, default skip)

**Check first:**
```bash
cat ~/.claude.json | grep -c "kb-mcp"   # >0 → already registered
```

**Ask based on install method:**
- Plugin install (Phase 2 method 1): default **n** (plugin already provides global MCP)
- Clone/manual (Phase 2 method 4): default **Y** (needed for cross-project use)

**Install only if user chooses Y:**
```bash
cd "<RAG_ROOT>/kb-mcp" && uv run python plugin_install.py install
# Verify:
cd "<RAG_ROOT>/kb-mcp" && uv run python plugin_install.py status
```

> ⚠️ Global MCP writes to `~/.claude.json` → `mcpServers` (NOT `~/.claude/.mcp.json`). Requires Claude Code restart or `/mcp` reconnect to take effect.
