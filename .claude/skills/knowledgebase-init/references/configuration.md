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

### Phase 6b — MinerU Deployment Mode Selection (ask once, mandatory, unless already configured)

`mineru.mode` decides which path the PDF parsing engine takes (see [mineru-mode.md](mineru-mode.md) for details):

```
MinerU parsing engine mode?
1) Remote API (recommended/default) — parsing goes to the mineru-api HTTP endpoint, no local GPU/memory usage;
   automatically falls back to the local engine when the endpoint is unavailable. Requires an API address (+ optional token).
2) Local deployment — install mineru on this machine + download models, fully offline.
```

- **Choose remote**: collect `base_url` (required, http/https) and the token (optional, written ONLY into `.env` as
  `MINERU_API_TOKEN`, never into config.yml or any source/examples) → write `mineru.mode: remote` + `remote.base_url`
  into backend/config.yml → immediately verify `GET {base_url}/health` (200 = pass; if unreachable, prompt to check
  the address/network or fall back to choosing local).
- **Choose local**: jump to [mineru-mode.md](mineru-mode.md) §Local install procedure — incrementally check whether
  mineru is already installed in the venv (`backend/.venv/Scripts/mineru-api.exe` or `bin/mineru-api`) and whether
  models are already downloaded (`ragctl mineru-model`), fill in only what is missing, and finish by confirming
  `available:true` from `GET /api/v1/mineru/status`.

### All config valid → skip asking, show summary

```
📋 Existing configuration (complete)  Modify? [y/N]:
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
