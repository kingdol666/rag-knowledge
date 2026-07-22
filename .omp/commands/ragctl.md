---
name: ragctl
description: Unified CLI for RAG Knowledge Platform — start, stop, status, logs, restart, test, config, clean, and KB operations
argument-hint: <command> [options]
---

# ragctl — RAG Knowledge Platform CLI

Execute ragctl commands. Use the appropriate shell for the platform:

- **Windows:** PowerShell — `ragctl <command>`
- **Linux/macOS:** Bash — `./ragctl <command>`

## Available Commands

| Command | Description |
|---------|-------------|
| `status` | Show all service statuses (backend, web, kb-mcp, Neo4j) |
| `up` | Start all services silently (backend + web + kb-mcp) |
| `down` | Stop all running services |
| `restart` | Restart all services |
| `logs` | Tail recent logs from all services |
| `setup` | One-time dependency install + config |
| `test` | Run full-stack validation tests |
| `config` | Show current configuration |
| `health` | Quick health check on all endpoints |
| `model` | Download BGE-M3 embedding model (~2.2GB). Supports `--source modelscope\|hf-mirror\|huggingface` |
| `clean` | Clean caches — MinerU parse artifacts (default), logs, pycache, or model cache |
| `install` | Register ragctl globally to `~/.local/bin` |
| `version` | Show local + remote version |
| `update` | Check GitHub for newer release and pull if available |

## Clean Command (cache & artifact cleanup)

| Flag | Scope |
|------|-------|
| *(none)* | MinerU parse output only — `backend/output/` (md/images/uploads, safe) |
| `--dry-run` / `-n` | Scan and show sizes without deleting |
| `--mineru` | Only `backend/output/` (PDF parse artifacts) |
| `--logs` | Also clean `backend/logs/` + `web/logs/` |
| `--pycache` | Also clean `__pycache__` / `.pytest_cache` |
| `--all` | All safe categories (mineru + logs + pycache — NOT models) |
| `--model` | Include model cache (BGE-M3 ~4 GB — requires re-download, double confirm) |
| `--force` / `-y` | Skip confirmation prompt |

**Examples:**
- `/ragctl clean` → scan + clean MinerU output (with confirm)
- `/ragctl clean --dry-run` → see what would be cleaned
- `/ragctl clean --all -y` → clean all safe caches without prompting
- `/ragctl clean --model` → reclaim ~4 GB (requires explicit `yes`)

## Execution

When the user invokes `/ragctl <command>`:
1. Determine the platform (Windows → PowerShell, Linux/macOS → Bash)
2. Run the corresponding ragctl command from the project root via `bash`
3. Display the output to the user

**Examples:**
- `/ragctl status` → `ragctl status`
- `/ragctl up` → `ragctl up`
- `/ragctl clean --dry-run` → `ragctl clean --dry-run`
- `/ragctl model --source modelscope` → download BGE-M3 from ModelScope (China-recommended)
