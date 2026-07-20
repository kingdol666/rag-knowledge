<h1 align="center">
  <img src="../docs/images/logo.svg" alt="RAG Knowledge Web" width="80" />
  <br/>
  RAG Knowledge Web
</h1>

<p align="center">
  <strong>Nuxt 3 Frontend · Claude AI Chat · Knowledge Base UI · Graph Visualization</strong><br/>
  <em>The user-facing web application for the RAG Knowledge Platform</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-2%20steps-blue?style=for-the-badge" /></a>
  <a href="#-features"><img src="https://img.shields.io/badge/Pages-9%20pages-9cf?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Nuxt-3.x-00DC82?style=for-the-badge" /></a>
</p>

---

<p align="center">
  <sub><a href="./README.md"><b>English</b></a> · <a href="./README-zh.md">中文</a></sub>
</p>

---

## 📌 Table of Contents

- [🌟 Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [📡 API Routes](#-api-routes)
- [📱 Pages](#-pages)
- [⚙️ Configuration](#️-configuration)
- [📁 Project Structure](#-project-structure)
- [🔧 Tech Stack](#-tech-stack)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## 🌟 Features

**🤖 Claude AI Chat**
Full Claude Code SDK integration with streaming responses, permission approval UI, KB-enhanced mode (inject retrieved context into prompts), message queue with concurrency control, reasoning depth slider, multimodal file upload (images + documents), and session history management.

**📁 Visual File System**
Drag-and-drop file browser with tree navigation, multi-format upload (PDF/Word/Excel/PPT/images), one-click parse triggers, file preview (markdown + images), and folder CRUD operations.

**🔍 Knowledge Base Search**
QDCVR (Query-Driven Content-Verified Retrieval) pipeline UI — semantic + keyword two-stage search with 0–8 content scoring, cross-KB enterprise search, tag-based filtering, and result ranking with source citations.

**🕸️ Knowledge Graph**
Neo4j-powered interactive visualization of document relationships — KB overview graphs, document-centric entity networks, cross-KB discovery paths, centrality analysis, and tag-based document clustering.

**💡 Experience Library**
Structured experience browsing with P0/P1/P2 credibility tiers, draft approval workflow, decay tracking, and dashboard analytics.

**⚙️ Settings & Configuration**
Runtime environment editor with hot-reload, backend API integration, and schema-validated config management.

**🌐 Bilingual**
Full Chinese/English internationalization — every label, message, and UI element supports both languages with instant toggle.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Browser                            │
│           Nuxt 3 SPA (Vue 3 + Ant Design Vue)        │
│           http://localhost:6789 (dev)                │
│           http://localhost:3000  (prod)              │
└─────────────────────┬───────────────────────────────┘
                      │ fetch() / SSE
┌─────────────────────▼───────────────────────────────┐
│              Nuxt 3 Server (Proxy Layer)              │
│                                                      │
│  ┌────────────┐ ┌───────────┐ ┌────────────────┐    │
│  │ /api/claude│ │ /api/kb   │ │ /api/filesystem│    │
│  │  chat      │ │  search   │ │  tree CRUD     │    │
│  │  sessions  │ │  catalog  │ │  upload        │    │
│  │  skills    │ │  tags     │ │  preview       │    │
│  │  workspaces│ │  docs     │ │                │    │
│  └────────────┘ └───────────┘ └────────────────┘    │
│                                                      │
│  ┌────────────┐ ┌───────────┐ ┌────────────────┐    │
│  │ /api/graph │ │ /api/parse│ │ /api/health    │    │
│  │  search    │ │  PDF proxy│ │  system stats  │    │
│  │  overview  │ │           │ │                │    │
│  └────────────┘ └───────────┘ └────────────────┘    │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │         server/services/ (business logic)     │    │
│  │  TreeFileSystem · KnowledgeBaseYaml ·         │    │
│  │  KbSearch · PdfParse · TagManagement          │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────┘
                      │ server-to-server (trust_env=False)
┌─────────────────────▼───────────────────────────────┐
│              FastAPI Backend (:8765 / :8001)          │
│              MinerU OCR · ChromaDB · Neo4j            │
└─────────────────────────────────────────────────────┘
```

**Key design decisions:**

| Decision | Rationale |
|----------|-----------|
| Server-to-server proxy | Nuxt server routes forward to backend — zero CORS issues. Browser never directly hits FastAPI. |
| Parse data flow | Browser → Nuxt proxy → Backend parse → returns `markdown_path` → Nuxt reads file → backfills content → writes into KB storage. |
| KB search is file-read only | `kb-search-service.ts` reads `.tree-fs.json` + `.knowledge-base.yml` directly — zero backend load for search. |
| Single source of truth | All ports, URLs, and paths are read from root `config.yml` via `utils/paths.mjs` (manual YAML parser, zero npm dependency). |

## 🚀 Quick Start

```bash
# 1. Install
npm install

# 2. Dev mode (hot reload, port 6789)
APP_MODE=dev npm run dev
# → http://localhost:6789

# Production mode (port 3000)
APP_MODE=prod npm run start
# → http://localhost:3000
```

```bash
# Build for production
npm run build
npm run preview

# Type check
npx vue-tsc --noEmit --skipLibCheck
```

> **Prerequisites:** Node.js 18+, npm. The backend must be running for parse, search, and graph features. Start it with `ragctl up` from the monorepo root, or `cd backend && uv run python main.py`.

## 📡 API Routes

The Nuxt server acts as a **proxy layer** between the browser and the FastAPI backend. All routes are defined under `server/api/`:

### Claude AI (`/api/claude`)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/claude/chat` | `POST` | Streaming chat with Claude Code SDK |
| `/api/claude/sessions` | `GET` | List active chat sessions |
| `/api/claude/history` | `GET` | Retrieve conversation history |
| `/api/claude/skills` | `GET` | List available skills |
| `/api/claude/permission` | `POST` | Handle permission approval/denial |
| `/api/claude/upload` | `POST` | Upload files for multimodal messages |
| `/api/claude/workspaces` | `GET/POST` | Manage workspace contexts |

### Knowledge Base (`/api/kb`)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/kb/search` | `GET` | Cross-KB search (keyword + vector) |
| `/api/kb/catalog` | `GET` | KB catalog with doc counts |
| `/api/kb/documents` | `GET` | List documents in a KB |
| `/api/kb/document` | `GET` | Get single document with metadata |
| `/api/kb/create` | `POST` | Create a new knowledge base |
| `/api/kb/update` | `PUT` | Update KB metadata |
| `/api/kb/delete` | `DELETE` | Delete a knowledge base |
| `/api/kb/tags` | `GET/POST` | List / update document tags |

### File System (`/api/filesystem`)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/filesystem/tree` | `GET` | Full file tree with metadata |
| `/api/filesystem/children` | `GET` | Children of a folder node |
| `/api/filesystem/upload` | `POST` | Upload + register file |
| `/api/filesystem/preview` | `GET` | File content preview |

### Parse (`/api/parse`)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/parse/file-vt` | `POST` | Proxy to backend parse endpoint |

### Graph (`/api/graph`)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/graph/search` | `GET` | Search knowledge graph |
| `/api/graph/kb-overview` | `GET` | KB-level graph overview |
| `/api/graph/document` | `GET` | Document-centric graph |
| `/api/graph/neighbors` | `GET` | Neighborhood exploration |
| `/api/graph/build-kb` | `POST` | Trigger graph build for a KB |
| `/api/graph/build-all` | `POST` | Build graphs for all KBs |
| `/api/graph/stats` | `GET` | Graph statistics |

### Health (`/api/health`)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/health` | `GET` | System health + service statuses |

## 📱 Pages

| Page | Route | Description |
|------|-------|-------------|
| **Home** | `/` | Dashboard overview with quick actions |
| **Claude Chat** | `/claude-chat` | Full Claude Code SDK chat with streaming, KB-enhanced mode, multimodal input |
| **File System** | `/file-system` | Drag-and-drop file browser, upload, parse triggers, preview |
| **Knowledge Base** | `/knowledge-base` | KB management — create, edit, delete KBs + document list |
| **KB Search** | `/knowledge-search` | QDCVR search interface with filtering, ranking, and source display |
| **Knowledge Graph** | `/knowledge-graph` | Neo4j-powered interactive graph visualization |
| **Settings** | `/settings` | Environment configuration with hot-reload |
| **About** | `/about` | Project information and release notes |
| **About Project** | `/about-project` | Technical architecture and roadmap |

## ⚙️ Configuration

All ports and URLs come from the **root `config.yml`** — never hardcoded. `utils/paths.mjs` provides a zero-dependency manual YAML parser.

| Variable | Default (dev / prod) | Description |
|----------|----------------------|-------------|
| `APP_MODE` | `dev` | Selects config section (`dev` → 6789, `prod` → 3000) |
| `WEB_PORT` | from config.yml | Override web listen port |
| `BACKEND_URL` | from config.yml | Backend API base URL for proxy |

The `server/` directory code runs on the Nuxt server (Node.js), not in the browser. It acts as a **BFF (Backend For Frontend)** — proxying requests, reading local KB storage files, and orchestrating business logic.

## 📁 Project Structure

```
web/
├── start.mjs                        # Launch script (reads config.yml, resolves port)
├── nuxt.config.ts                   # Nuxt config + runtimeConfig from config.yml
├── utils/
│   └── paths.mjs                    # Manual YAML config reader (zero npm deps)
├── pages/
│   ├── index.vue                    # Home dashboard
│   ├── claude-chat.vue              # Claude Code SDK streaming chat
│   ├── file-system.vue              # Visual file tree browser + upload
│   ├── knowledge-base.vue           # KB management + document list
│   ├── knowledge-search.vue         # QDCVR search interface
│   ├── knowledge-graph.vue          # Neo4j graph visualization
│   └── settings.vue                 # Configuration editor
├── composables/                     # Vue composables
│   ├── useTreeFileSystem.ts         # File tree state + operations
│   ├── usePDFParser.ts              # Parse trigger + progress tracking
│   └── ...                          # Other reusable composables
├── components/                      # Shared Vue components (modals, viewers, etc.)
├── server/
│   ├── api/                         # Nuxt server API routes (proxy layer)
│   │   ├── claude/                  # Chat, sessions, skills, workspaces
│   │   ├── kb/                      # Search, catalog, documents, tags
│   │   ├── filesystem/              # Tree, upload, preview
│   │   ├── parse/                   # PDF parse proxy
│   │   ├── graph/                   # Neo4j graph queries
│   │   ├── experience/              # Experience CRUD
│   │   ├── config/                  # Runtime config
│   │   └── health/                  # System health
│   ├── services/                    # Business logic (runs server-side)
│   │   ├── tree-file-system-service.ts   # .tree-fs.json + disk operations
│   │   ├── knowledge-base-yaml-service.ts # .knowledge-base.yml management
│   │   ├── kb-search-service.ts          # Cross-KB keyword search
│   │   ├── pdf-parse-service.ts          # Backend proxy + markdown backfill
│   │   └── tag-management-service.ts     # Tag registry
│   └── utils/
│       ├── runtime-paths.ts          # Tree-storage path resolution
│       └── tree-service.ts           # Singleton helpers
├── types/                           # TypeScript interface definitions
└── storage/
    └── tree-file-system/            # Default KB file storage (configurable path)
        ├── .tree-fs.json            # Global file tree index
        └── {kb-name}/               # Per-KB markdown docs + images
            └── .knowledge-base.yml  # Per-KB document index
```

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Nuxt 3 · Vue 3.5 · TypeScript |
| UI Library | Ant Design Vue 4 · Ant Design Icons |
| AI Integration | `@anthropic-ai/claude-agent-sdk` (streaming chat, multimodal) |
| State Management | Pinia + persistedstate plugin |
| i18n | vue-i18n (Chinese/English bilingual) |
| Markdown | marked (rendering) · mammoth (Word import) |
| Graph | Neo4j JavaScript driver (via server proxy) |
| Build | Vite (via Nuxt) · cross-env |
| Testing | Playwright (e2e) |

## 🤝 Contributing

1. Fork → feature branch → commit → push → PR
2. Run `npx vue-tsc --noEmit --skipLibCheck` before submitting — type check must pass
3. Test on both dev and prod modes before submitting UI changes
4. New API routes: follow the existing pattern — route file → service → utility

## 📄 License

MIT · Part of the [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)
