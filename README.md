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
├── config.yml          # ☝ 唯一端口 / CORS / URL 配置来源（dev + prod 双模式）
├── .env                # Environment variables (overrides)
├── .env.example        # Template .env file
├── start.bat           # Windows launcher
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

### 2. Install dependencies

```bash
# Backend (Python) — requires uv: https://docs.astral.sh/uv/
cd backend
uv sync
cd ..

# Web frontend (Nuxt 3)
cd web
npm install
cd ..
```

### 3. Start — choose your mode

The entire platform is **configuration-driven**: all ports, URLs, and CORS origins come
from `config.yml`. Simply set `APP_MODE` to switch between development and production.
No code changes needed.

---

#### 🧑‍💻 Development Mode （`APP_MODE=dev` — default）

```bash
# Terminal 1 — Backend
cd backend
APP_MODE=dev uv run python main.py
# → http://localhost:8765  (API)
# → http://localhost:8765/docs  (Swagger)

# Terminal 2 — Web frontend
cd web
APP_MODE=dev npm run start
# → http://localhost:6789  (UI)
```

```yaml
# config.yml (dev section — no changes needed, this is the default)
server:
  dev:
    host: "0.0.0.0"
    backend_port: 8765              # Backend port
    frontend_port: 6789             # Frontend port
    backend_url: "http://localhost:8765"
    cors_origins:
      - "http://localhost:6789"
      - "http://127.0.0.1:6789"
```

> When `APP_MODE` is unset or set to `dev`, the backend listens on **8765** and the
> frontend on **6789**. The frontend's server routes proxy API calls to `localhost:8765`.
> CORS is configured for `localhost:6789`.

---

#### 🚀 Production Mode （`APP_MODE=prod`）

```bash
# Terminal 1 — Backend (no reload)
cd backend
APP_MODE=prod uv run python main.py
# → http://localhost:8001  (API)

# Terminal 2 — Web frontend
cd web
APP_MODE=prod npm run start
# → http://localhost:3000  (UI)
```

```yaml
# config.yml (prod section)
server:
  prod:
    host: "0.0.0.0"
    backend_port: 8001              # Backend port
    frontend_port: 3000             # Frontend port
    backend_url: "http://localhost:8001"
    cors_origins:
      - "http://localhost:3000"
      - "http://127.0.0.1:3000"
```

> In production mode both services use conventional ports (**8001** / **3000**).
> CORS is configured for `localhost:3000`.

---

### 4. Open

| Service | Dev (`APP_MODE=dev`) | Prod (`APP_MODE=prod`) |
|---------|----------------------|------------------------|
| Web UI  | [http://localhost:6789](http://localhost:6789) | [http://localhost:3000](http://localhost:3000) |
| API     | [http://localhost:8765](http://localhost:8765) | [http://localhost:8001](http://localhost:8001) |
| API Docs | [http://localhost:8765/docs](http://localhost:8765/docs) | [http://localhost:8001/docs](http://localhost:8001/docs) |

---

### 5. Verify

```bash
# Health check
curl http://localhost:8765/api/v1/health    # dev
curl http://localhost:8001/api/v1/health    # prod

# PDF conversion (upload any PDF)
curl -X POST -F "file=@your-document.pdf" http://localhost:8765/api/v1/parse/file/vt
```

---

## Configuration Reference

`config.yml` is the **single source of truth**:

```yaml
server:
  dev:                               # Used when APP_MODE is unset or "dev"
    host: "0.0.0.0"
    backend_port: 8765
    frontend_port: 6789
    backend_url: "http://localhost:8765"
    cors_origins:
      - "http://localhost:6789"

  prod:                              # Used when APP_MODE=prod
    host: "0.0.0.0"
    backend_port: 8001
    frontend_port: 3000
    backend_url: "http://localhost:8001"
    cors_origins:
      - "http://localhost:3000"
```

Port resolution priority（high to low）：

```
APP_MODE env var → config.yml <mode> section → code default (fallback)
```

The project contains **zero hardcoded port numbers** in source files. Everything reads
from `config.yml` at startup.

---

## Architecture Detail: Why No CORS?

The frontend uses Nuxt 3 **server routes** to proxy requests to the Python backend.
The browser talks only to the Nuxt server on the same origin.

```
 Browser (port 6789 / 3000)
    │
    │  /api/parse/file-vt
    ▼
 Nuxt server handler             (server-side, no browser CORS)
    │
    │  http://localhost:8765/api/v1/parse/file/vt
    ▼
 Python FastAPI backend
```

For normal usage the browser never makes a cross-origin request. CORS headers only
matter when accessing the backend directly from a different origin (e.g., the Swagger
UI or a custom script).

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

The project uses only **relative paths** derived from module location — you can clone
it anywhere and it will work without modifying any config file.

---

## License

MIT
