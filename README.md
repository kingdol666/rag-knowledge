# RAG Knowledge Platform

A RAG (Retrieval-Augmented Generation) knowledge management platform with PDF parsing powered by MinerU 3.x.

## Project Structure

```
rag-knowledge/
  .env                 # Environment configuration (ports, API URLs)
  .env.example         # Example environment file
  start.bat            # Windows launcher
  start.sh             # Linux/macOS launcher
  backend/             # Git submodule → rag-knowledge-backend
  frontend/            # Git submodule → rag-knowledge-frontend (Vue + Vite)
  web/                 # Git submodule → rag-knowledge-frondend (Nuxt 3)
```

## Quick Start

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env to customize ports and API URLs
```

### 3. Install dependencies

```bash
# Backend (requires uv: https://docs.astral.sh/uv/)
cd backend && uv sync && cd ..

# Frontend (Vue + Vite)
cd frontend && npm install && cd ..

# Web (Nuxt 3)
cd web && npm install && cd ..
```

### 4. Start services

**Windows:**
```cmd
start.bat          # Dev mode (default)
start.bat prod     # Production mode
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh         # Dev mode (default)
./start.sh prod    # Production mode
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | `8001` | Backend API server port |
| `FRONTEND_PORT` | `3008` | Frontend (Vue) dev server port |
| `FRONTEND_PREVIEW_PORT` | `4173` | Frontend (Vue) preview (prod) port |
| `WEB_PORT` | `3009` | Web (Nuxt) dev server port |
| `VITE_API_BASE` | `http://localhost:8001` | Backend URL for Vite proxy |
| `NUXT_PUBLIC_API_BASE` | `http://localhost:8001/api` | Backend URL for Nuxt |
| `PDF_PARSER_API_URL` | `http://localhost:8001` | PDF parser service URL |
| `DEEPAGENT_API_URL` | `http://localhost:8001` | DeepAgent service URL |

## Architecture

- **Backend**: FastAPI + Uvicorn, MinerU 3.x for PDF parsing
- **Frontend (Vue)**: Vue 3 + Vite + Ant Design Vue
- **Web (Nuxt)**: Nuxt 3 + Ant Design Vue + Pinia
- **PDF Parsing**: OCR (pipeline) and VLM backends via MinerU SDK

## Submodules

| Submodule | Repository | Description |
|-----------|------------|-------------|
| `backend/` | [rag-knowledge-backend](https://github.com/kingdol666/rag-knowledge-backend) | FastAPI + MinerU PDF parser |
| `frontend/` | [rag-knowledge-frontend](https://github.com/kingdol666/rag-knowledge-frontend) | Vue 3 + Vite frontend |
| `web/` | [rag-knowledge-frondend](https://github.com/kingdol666/rag-knowledge-frondend) | Nuxt 3 web app |
