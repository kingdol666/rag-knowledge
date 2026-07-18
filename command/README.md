# ragctl — RAG Knowledge Platform CLI

Unified command-line interface for the entire RAG Knowledge Platform.
Built with Node.js, zero external dependencies except `js-yaml`.

## Quick Install

```bash
# One-click setup (first time)
ragctl setup

# Register globally (available from any directory)
ragctl install
```

After `ragctl install`, `ragctl` is available globally in any terminal via `~/.local/bin`.

## Commands

### Core Commands (One-Click)

| Command | Description |
|---------|-------------|
| `ragctl setup` | One-click full deployment (uv + submodules + .env + deps + model) |
| `ragctl check` | Comprehensive environment health check with fix suggestions |
| `ragctl deps` | Install all dependencies with real-time progress |
| `ragctl model` | Pre-download BGE-M3 embedding model (~2.2GB) |

### Service Management (Silent — No Terminal Windows)

| Command | Description |
|---------|-------------|
| `ragctl up` / `ragctl start-all` | Start all services (Neo4j + Backend + Web) |
| `ragctl down` / `ragctl stop-all` | Stop all services |
| `ragctl start [backend\|web\|neo4j\|all]` | Start specific service |
| `ragctl stop [backend\|web\|neo4j\|all]` | Stop specific service |
| `ragctl restart [backend\|web\|neo4j\|all]` | Restart specific service |
| `ragctl status` | Show service status (Backend/Web/Neo4j/MinerU/kb-mcp) |

### Logs (Shared with Tauri Desktop Console)

| Command | Description |
|---------|-------------|
| `ragctl logs [backend\|web\|mineru]` | View recent logs (default: backend, 80 lines) |
| `ragctl logs <svc> --tail` / `-f` | Real-time log tail (Ctrl+C to exit) |
| `ragctl logs <svc> --lines N` / `-n N` | Specify number of lines |

### Global Registration & Desktop

| Command | Description |
|---------|-------------|
| `ragctl install` | Register `ragctl` globally in `~/.local/bin` |
| `ragctl desktop` / `ragctl ui` | Launch Tauri desktop console (GUI launcher) |

### Options

- `--mode dev\|prod` — Override .env APP_MODE (affects ports and behavior)
- `--help` — Show help
- `--version` — Show version (2.1.0)

## Examples

```bash
# First-time setup
ragctl setup

# Start everything silently (no terminal windows)
ragctl up

# Check what's running
ragctl status

# View backend logs
ragctl logs backend

# Tail backend logs in real-time
ragctl logs backend --tail

# Start in production mode
ragctl up --appmode prod

# Register globally for use from any directory
ragctl install
```

## Architecture

```
ragctl (global bin, ~/.local/bin)
  └── command/ragctl.js (main CLI, Node.js)
       ├── Reads: config.yml, .env
       ├── spawnService(): silent detached launch (Windows: CREATE_NO_WINDOW for backend,
       │                  DETACHED_PROCESS for web/Nuxt)
       ├── HTTP: health probes for status
       └── YAML: js-yaml for config reading
```

The CLI has **zero Python dependencies** — it runs entirely on Node.js.
Only `js-yaml` npm package is required.

## Log Paths (Shared Across All Launchers)

| Service | Log Path |
|---------|----------|
| Backend | `backend/logs/desktop-stdout.log` |
| Web | `web/logs/desktop-stdout.log` |
| MinerU | `backend/logs/mineru-api.log` |

All three surfaces (ragctl logs, Tauri desktop console, on-disk files) read the same files.