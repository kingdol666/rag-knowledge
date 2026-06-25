# RAG Knowledge Platform

> A RAG (Retrieval-Augmented Generation) knowledge management platform.
> PDF parsing via MinerU, LLM agents, modern web UI.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Nuxt](https://img.shields.io/badge/Nuxt-3.x-00DC82)](https://nuxt.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end document intelligence system: ingest PDFs, extract knowledge via OCR / VLM, build searchable knowledge bases, and interact with LLM agents for summarization and Q&A.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    RAG Knowledge Platform               │
├──────────────┬────────────────────┬────────────────────┤
│   backend/   │     web/           │   frontend/        │
│  FastAPI +   │   Nuxt 3 +        │   Vue 3 + Vite     │
│  MinerU 3.x  │   Ant Design Vue  │   Ant Design Vue   │
│              │   (primary UI)    │   (legacy UI)       │
├──────────────┴────────────────────┴────────────────────┤
│              config.yml  ←  shared port & CORS config  │
└────────────────────────────────────────────────────────┘

Browser ──► Nuxt server route ──► Python FastAPI backend
                  │                       │
             No browser CORS          MinerU SDK
             (server-to-server)       OCR / VLM parsing
```

---

## Repository Layout

```
rag-knowledge/
├── config.yml          # ☝ Shared ports, backend URL, CORS origins
├── .env                # Environment variables (overrides)
├── .env.example        # Template .env file
├── start.bat           # Windows launcher (opens 3 terminals)
├── start.sh            # Linux / macOS launcher
├── README.md
├── backend/            # Git submodule → rag-knowledge-backend
├── web/                # Git submodule → rag-knowledge-frondend (Nuxt 3)
└── frontend/           # Git submodule → rag-knowledge-frontend (Vue + Vite)
```

---

## Quick Start

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| [uv](https://docs.astral.sh/uv/) | latest | `uv --version` |
| [Node.js](https://nodejs.org) | ≥ 18 | `node --version` |
| Python | 3.11 or 3.12 | `python --version` |
| Git | ≥ 2.25 | `git --version` |

### 1. Clone (with submodules)

```bash
git clone --recurse-submodules https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
```

> If you cloned without `--recurse-submodules`:
> ```bash
> git submodule update --init --recursive
> ```

### 2. Configure ports

Edit `config.yml` at the repo root — it drives both services:

```yaml
server:
  host: "0.0.0.0"
  backend_port: 8765          # Backend listens here
  frontend_port: 6789         # Nuxt frontend listens here
  backend_url: "http://localhost:8765"
  cors_origins:
    - "http://localhost:6789"
```

### 3. Install dependencies

```bash
# Backend (Python)
cd backend
uv sync
cd ..

# Web frontend (Nuxt)
cd web
npm install
cd ..
```

### 4. Start

**Windows:**

```cmd
start.bat
```

**Linux / macOS:**

```bash
chmod +x start.sh
./start.sh
```

Each service opens in its own terminal window. The launcher auto-detects port settings from `.env` and `config.yml`.

### 5. Open

| Service | URL |
|---------|-----|
| Web (Nuxt) | [http://localhost:6789](http://localhost:6789) |
| Backend API | [http://localhost:8765](http://localhost:8765) |
| API Docs | [http://localhost:8765/docs](http://localhost:8765/docs) |

---

## Manual Start (without launcher)

If you prefer to start services individually:

```bash
# Terminal 1 — Backend
cd backend
uv run python main.py

# Terminal 2 — Web (Nuxt)
cd web
node start.mjs
```

---

## `config.yml` — How It Works

```
config.yml  (this repo root)
  │
  ├── read by  backend/app/utils/paths.py  → overrides config.server
  └── read by  web/utils/paths.mjs         → overrides port + backend_url
```

- **Backend** merges the shared `server` section on top of its own `config.yml`
- **Frontend** searches paths: `<parent>/rag-knowledge/config.yml` → `<parent>/config.yml`
- No file edits needed when you only change ports — edit `config.yml` in one place and restart

---

## Submodules

| Directory | Repository | Tech |
|-----------|-----------|------|
| `backend/` | [rag-knowledge-backend](https://github.com/kingdol666/rag-knowledge-backend) | Python · FastAPI · MinerU 3.x |
| `web/` | [rag-knowledge-frondend](https://github.com/kingdol666/rag-knowledge-frondend) | TypeScript · Nuxt 3 · Ant Design Vue |
| `frontend/` | [rag-knowledge-frontend](https://github.com/kingdol666/rag-knowledge-frontend) | Vue 3 · Vite · Ant Design Vue (legacy) |

---

## Platform Compatibility

| Platform | Backend | Frontend | Notes |
|----------|---------|----------|-------|
| **Windows 10/11** | ✓ | ✓ | Use Git Bash or PowerShell. `start.bat` included. |
| **Linux** | ✓ | ✓ | All features. `./start.sh`. GPU: CUDA ≥ 11.8. |
| **macOS** | ✓ | ✓ | CPU always OK. Apple Silicon GPU: `vlm.backend: mlx-engine`. |

The project uses only **relative paths** derived from module location — you can clone it anywhere and it will work without modifying any config file.

---

## License

MIT
