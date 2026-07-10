# ragctl — RAG Knowledge Platform CLI

Unified command-line interface for the entire RAG Knowledge Platform.
Built with Node.js, zero external dependencies except `js-yaml`.

## Quick Install

```bash
cd command
npm install
npm link
```

After `npm link`, `ragctl` is available globally in any terminal — just like `claude` or `git`.

## Usage

```bash
ragctl <command> [subcommand] [options]
```

## Commands

### Service Management

| Command | Description |
|---------|-------------|
| `ragctl start [backend\|web\|neo4j\|mcp\|all]` | Start services |
| `ragctl stop [backend\|web\|neo4j\|mcp\|all]` | Stop services |
| `ragctl restart [backend\|web\|neo4j\|all]` | Restart services |
| `ragctl status` | Show service status with health info |
| `ragctl health` | Health check for all services |

### Configuration

| Command | Description |
|---------|-------------|
| `ragctl config show` | Show all configuration (config.yml + .env + effective) |
| `ragctl config get <key>` | Get a config value (dot notation, e.g. `server.dev.backend_port`) |
| `ragctl config set <key> <value>` | Set a config value (auto-writes to .env or config.yml, hot-reloads) |
| `ragctl config reload` | Hot-reload config from files via backend API |
| `ragctl config edit [shared\|backend\|env]` | Open config file in editor |

### Diagnostics

| Command | Description |
|---------|-------------|
| `ragctl doctor` | Diagnose system requirements, config files, submodules, deps, ports |
| `ragctl logs [backend\|web\|mineru] --lines N` | View last N lines of service logs |

### Dependencies & Tests

| Command | Description |
|---------|-------------|
| `ragctl install [backend\|web\|mcp\|neo4j\|all]` | Install dependencies |
| `ragctl test [backend\|web\|mcp\|all] [--integration]` | Run tests |

### MCP Server

| Command | Description |
|---------|-------------|
| `ragctl mcp start` | Start MCP server (stdio mode) |
| `ragctl mcp stop` | Stop MCP server |
| `ragctl mcp status` | Check MCP server status |
| `ragctl mcp tools` | List all available MCP tools |

### Knowledge Base

| Command | Description |
|---------|-------------|
| `ragctl kb list` | List all knowledge bases |
| `ragctl kb search "<query>"` | Search knowledge bases |
| `ragctl kb stats` | Show KB statistics |

## Options

- `--mode <dev\|prod>` — Mode override (for `start` and `restart`)
- `--lines N` / `-n N` — Number of log lines (for `logs`, default: 50)
- `--integration` / `-i` — Include integration tests (for `test`)
- `--help` / `-h` — Show help
- `--version` / `-V` — Show version

## Examples

```bash
# Start all services in dev mode
ragctl start all

# Start backend in production mode
ragctl start backend --mode prod

# Stop everything
ragctl stop all

# Check what's running
ragctl status

# Change backend port
ragctl config set server.dev.backend_port 9000

# Run diagnostics
ragctl doctor

# View last 100 lines of backend logs
ragctl logs backend --lines 100

# Install everything
ragctl install all

# Run backend tests
ragctl test backend

# List MCP tools
ragctl mcp tools

# Search knowledge bases
ragctl kb search "vector search"
```

## Architecture

```
ragctl (global bin, via npm link)
  └── command/ragctl.js (main CLI, Node.js)
       ├── Reads: config.yml, .env, backend/config.yml
       ├── HTTP:  calls backend API for health/config-reload/kb ops
       ├── Process: netstat/wmic/taskkill (Windows), lsof/kill (Linux)
       └── YAML:  js-yaml for config read/write
```

The CLI has **zero Python dependencies** — it runs entirely on Node.js.
Only `js-yaml` npm package is required (installed via `npm install`).
