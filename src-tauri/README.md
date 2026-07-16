# RAG Knowledge Desktop

[![Tauri](https://img.shields.io/badge/Tauri-2.x-FFC131)](https://tauri.app)
[![Rust](https://img.shields.io/badge/Rust-2021%20edition-orange)](https://rust-lang.org)
[![Platform](https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey)]()

> Tauri v2 desktop console for the RAG Knowledge Platform — one-click bootstrap, service management, real-time logs, and visual config editing.

## ✨ Features

- ⚡ **One-Click Bootstrap** — Auto-installs uv, Python 3.12, all dependencies, and the BGE-M3 embedding model. Works on a fresh OS install.
- 🔍 **22-Point Environment Audit** — Checks all prerequisites, project files, dependencies, AI models, and port status. Each failure shows the exact fix command.
- ▶ **Service Management** — Start/stop/monitor backend, web, Neo4j, and MinerU services with real-time status indicators.
- 📊 **Real-Time Log Streaming** — Four log panels (backend, web, MinerU, CLI) with live `tail -f` streaming from Rust.
- ⚙️ **Visual Config Editor** — Edit `config.yml`, `backend/config.yml`, and `.env` with inline validation and hot-reload.
- 🌐 **Environment Switching** — Toggle between `dev` and `prod` modes with automatic port management.
- 🤖 **Claude Code Detection** — Shows CLI installation status, authentication method, MCP server count, and config path.
- 🖥️ **Cross-Platform** — Windows, Linux, macOS with native look and feel.

## 🚀 Quick Start

### Pre-built (recommended)

Download the latest release from [Releases](https://github.com/kingdol666/rag-knowledge/releases).

### Build from source

```bash
cd src-tauri

# Prerequisites: Rust + Tauri CLI
# https://tauri.app/start/prerequisites/

# Development
cargo tauri dev

# Production build
cargo tauri build
# → src-tauri/target/release/rag-knowledge-desktop
```

## 🏗️ Architecture

```
src-tauri/
├── Cargo.toml              # Rust dependencies
├── tauri.conf.json         # Tauri configuration
├── build.rs                # Build script
├── src/
│   ├── main.rs             # Tauri entry + invoke handler
│   └── commands.rs         # All backend commands (Rust)
├── frontend/
│   └── index.html          # Single-file vanilla HTML/JS UI
├── icons/                  # App icons (all platforms)
└── capabilities/
    └── default.json        # Tauri v2 capability permissions
```

## 🔧 Rust Commands

| Command | Description |
|---------|-------------|
| `check_status` | Probe backend/web/Neo4j/MinerU via TCP + HTTP |
| `start_service` / `stop_service` | Start/stop backend, web, or Neo4j |
| `stop_all_services` | Stop all services with orphan cleanup |
| `detect_features` | Read config.yml for feature flags |
| `get_environment` / `set_environment` | Read/write APP_MODE with port sync |
| `check_dependencies` | 11-point dependency audit |
| `install_dependency` | Install uv, Python, deps, or models |
| `bootstrap_all` | Full zero-to-ready pipeline |
| `ragctl_check` | Native 22-point audit (no Node needed) |
| `ragctl_deps` | Install all deps with progress streaming |
| `ragctl_model` | Pre-download BGE-M3 (~2.2GB) |
| `read_config_full` / `save_config` | Visual YAML config editor |
| `read_log_tail` / `watch_log` | Real-time log streaming |
| `check_claude_code` | Claude Code CLI detection |
| `run_ragctl` | Execute ragctl commands via Node |
| `open_web_ui` | Open browser to Web UI |

## 🖥️ UI Layout

```
┌─────────────────────────────────────────────────┐
│  [Logo] RAG Knowledge Platform    [Dev] [▶Start]│
│  📁 project root · backend :8765 · web :6789    │
├─────────────────────────────────────────────────┤
│  🚀 One-Click Bootstrap ────────────────────────│
│  [⚡Bootstrap] [🔍Check] [📦Deps] [🧠Model]    │
│  ┌─────────────────────────────────────────────┐│
│  │ uv ✓ │ Node ✓ │ Python ✓ │ Git ✓ │ Docker ✓ ││
│  └─────────────────────────────────────────────┘│
├─────────────────────────────────────────────────┤
│  ● Services ────────────────────────────────────│
│  [Backend ●] [Web ●] [Neo4j ●] [MinerU ●]    │
├─────────────────────────────────────────────────┤
│  Logs ──────────────────────────────────────────│
│  [Backend] [Web] [MinerU] [ragctl]              │
├─────────────────────────────────────────────────┤
│  ⚙️ Config Editor ──────────────────────────────│
│  [server] [storage] [vector] [graph] [mineru]   │
└─────────────────────────────────────────────────┘
```

## 📦 Dependencies

```toml
[dependencies]
tauri = { version = "2" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"
reqwest = { version = "0.12", features = ["json", "rustls-tls"] }
tokio = { version = "1", features = ["rt-multi-thread", "macros", "net", "io-util", "fs", "process"] }
```

## 📄 License

MIT · Part of the [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)
