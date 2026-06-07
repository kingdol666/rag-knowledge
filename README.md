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
  frontend/            # Git submodule → rag-knowledge-frontend
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

# Frontend (requires Node.js 18+)
cd frontend && npm install && cd ..
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
| `FRONTEND_PORT` | `3000` | Frontend dev server port |
| `FRONTEND_PREVIEW_PORT` | `4173` | Frontend preview (prod) port |
| `VITE_API_BASE` | `http://localhost:8001` | Backend URL for frontend proxy |
| `PDF_PARSER_API_URL` | `http://localhost:8001` | PDF parser service URL |
| `DEEPAGENT_API_URL` | `http://localhost:8001` | DeepAgent service URL |

## Architecture

- **Backend**: FastAPI + Uvicorn, MinerU 3.x for PDF parsing
- **Frontend**: Vue 3 + Vite + Ant Design Vue
- **PDF Parsing**: OCR (pipeline) and VLM backends via MinerU SDK

## Submodules

| Submodule | Repository |
|-----------|------------|
| `backend/` | [rag-knowledge-backend](https://github.com/kingdol666/rag-knowledge-backend) |
| `frontend/` | [rag-knowledge-frontend](https://github.com/kingdol666/rag-knowledge-frontend) |
