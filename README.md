<div align="center">
<img src="./docs/images/readme-hero.svg" alt="QDCVR — a deployable knowledge-base management platform with content-based organization and content-verified retrieval" width="100%" />

<br><br>

**English** &nbsp;·&nbsp; <a href="./README-zh.md">简体中文</a>

<br><br>

<a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-3_commands-B24422?style=for-the-badge" alt="Quick Start" /></a>
<a href="#mcp-tools"><img src="https://img.shields.io/badge/kb_*_MCP_Tools-41-2E5D7F?style=for-the-badge" alt="41 kb_* MCP tools" /></a>
<a href="#how-it-works"><img src="https://img.shields.io/badge/Retrieval-QDCVR_v2-B24422?style=for-the-badge" alt="QDCVR" /></a>
<a href="#publications"><img src="https://img.shields.io/badge/CIKM_%2726_Demo-Paper-9E7A38?style=for-the-badge" alt="CIKM Demo paper" /></a>

<br>

<img src="https://img.shields.io/badge/Platform-Windows_·_Linux_·_macOS-334155?style=flat-square" alt="Platform" />
<img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12" />
<img src="https://img.shields.io/badge/Node.js-≥18-339933?style=flat-square&logo=nodedotjs&logoColor=white" alt="Node 18+" />
<img src="https://img.shields.io/badge/License-MIT-3D6E3D?style=flat-square" alt="MIT" />
<a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=flat-square&color=C49846" alt="Stars" /></a>
<a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=flat-square&color=9E7A38&label=release" alt="Release" /></a>

</div>

---

## What this is

A self-hosted platform that turns a folder of PDFs, Office documents and scans into a **knowledge base an AI agent can actually be trusted to answer from** — organized by what documents *say*, not by which folder they sat in, and exposed four ways: a web UI, an HTTP API, a CLI, and MCP tools that any MCP-capable agent can drive.

The retrieval layer is the interesting part. Most RAG stacks rank by vector similarity and hope. This one runs a query protocol — **QDCVR, Query-Driven Content-Verified Retrieval** — that **reads the candidate documents and scores them against an interpretable 0–8 content rubric**, escalates gate failures to a librarian fallback, and returns an explicit not-found report instead of a fabricated answer:

> **Vectors are fast. Content is accurate.**
> A document at cosine similarity **0.95** whose content scores **≤ 4** is **discarded** — not down-ranked, discarded.

This is the system demonstrated in our CIKM '26 demo paper, *QDCVR: A Deployable Knowledge-Base Management Platform with Content-Based Organization and Content-Verified Retrieval* ([paper + demo video](#publications)).

<br>

<div align="center">
<img src="./docs/images/readme-pipeline.svg" alt="Ingestion pipeline: files → MinerU OCR → content-routed category knowledge bases → indexes → QDCVR retrieval → verified answer" width="100%" />
</div>

---

## Table of contents

| | |
|---|---|
| [**Screenshots**](#screenshots) | What the interface actually looks like, light and dark |
| [**How it works**](#how-it-works) | The QDCVR v2 protocol and the 0–8 rubric |
| [**Agent chat, any harness**](#agent-chat-any-harness) | 14 harnesses, per-harness models, unified HITL |
| [**Architecture**](#architecture) | Services, ports, storage engines |
| [**Quick start**](#quick-start) | Clone → setup → up |
| [**Use it four ways**](#use-it-four-ways) | Web UI · HTTP · CLI · MCP |
| [**MCP tools**](#mcp-tools) | 41 `kb_*` domain tools out of 94, by category |
| [**External HTTP API**](#external-http-api) | Call it from anything, no agent required |
| [**Benchmark**](#benchmark) | The reproducible pipeline and its numbers |
| [**Scope and non-goals**](#scope-and-non-goals) | What this does *not* do |

---

## Screenshots

All screenshots are captures of the running application, committed under [`docs/screenshots/app/`](./docs/screenshots/app/) with a [manifest](./docs/screenshots/app/MANIFEST.json) recording the source size and encoding of each. No mockups.

### Knowledge base manager

CRUD, cross-KB moves, tag management and in-place content editing.

<div align="center">
<img src="./docs/screenshots/app/desktop-knowledge-base.jpg" alt="Knowledge base manager" width="100%" />
</div>

<details>
<summary><b>More screens — click to expand</b></summary>

<br>

**QDCVR search** — vector-first retrieval, scope control, and a tag rail that reflects what is actually in the corpus.

<div align="center">
<img src="./docs/screenshots/app/desktop-knowledge-search.jpg" alt="QDCVR search interface" width="100%" />
</div>

**Knowledge graph** — Neo4j-backed document relations, cross-KB bridges, and path discovery.

<div align="center">
<img src="./docs/screenshots/app/desktop-knowledge-graph.jpg" alt="Knowledge graph explorer" width="100%" />
</div>

**SOUL persona studio** — distill a persona, train it, and query the knowledge base through it.

<div align="center">
<img src="./docs/screenshots/app/desktop-soul.jpg" alt="SOUL persona studio" width="100%" />
</div>

**File system** — the authoritative tree, backed by `.tree-fs.json`.

<div align="center">
<img src="./docs/screenshots/app/desktop-file-system.jpg" alt="File system tree" width="100%" />
</div>

**Agent chat** — 14 agent harnesses against the knowledge base in-app, with per-harness model selection and unified human-in-the-loop approvals.

<div align="center">
<img src="./docs/screenshots/app/desktop-claude-chat.jpg" alt="Agent chat" width="100%" />
</div>

**Settings and API tokens** — live port/binding banner, scoped tokens with expiry.

<div align="center">
<img src="./docs/screenshots/app/desktop-settings.jpg" alt="Settings" width="49%" />
<img src="./docs/screenshots/app/desktop-tokens.jpg" alt="API token management" width="49%" />
</div>

</details>

### Dark mode

Every surface has a real dark theme — not an inverted palette.

<div align="center">
<img src="./docs/screenshots/app/dark-desktop-home.jpg" alt="Home in dark mode" width="100%" />
</div>

<details>
<summary><b>More dark-mode screens</b></summary>

<br>

<div align="center">
<img src="./docs/screenshots/app/dark-desktop-knowledge-search.jpg" alt="Search in dark mode" width="49%" />
<img src="./docs/screenshots/app/dark-desktop-knowledge-graph.jpg" alt="Graph in dark mode" width="49%" />
<br><br>
<img src="./docs/screenshots/app/dark-desktop-knowledge-base.jpg" alt="Knowledge base in dark mode" width="49%" />
<img src="./docs/screenshots/app/dark-desktop-soul.jpg" alt="SOUL studio in dark mode" width="49%" />
</div>

</details>

### Mobile

The layout is a container-query system, so it responds to the width of its own content area rather than only the viewport. Sidebar becomes a drawer, tables become cards, touch targets are grown to the 44 px floor.

<div align="center">
<img src="./docs/screenshots/app/mobile-home.jpg" alt="Mobile home" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-base.jpg" alt="Mobile knowledge base" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-search.jpg" alt="Mobile search" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-graph.jpg" alt="Mobile graph" width="24%" />
<br>
<img src="./docs/screenshots/app/mobile-soul.jpg" alt="Mobile SOUL studio" width="24%" />
<img src="./docs/screenshots/app/mobile-tokens.jpg" alt="Mobile API tokens" width="24%" />
<img src="./docs/screenshots/app/dark-mobile-home.jpg" alt="Mobile dark home" width="24%" />
<img src="./docs/screenshots/app/dark-mobile-knowledge-base.jpg" alt="Mobile dark knowledge base" width="24%" />
</div>

---

## How it works

`QDCVR` — **Query-Driven, Content-Verified Retrieval**. One protocol per query, in order:

```
query
  │
  ├─ 0 · Query rewrite             vague ask → retrieval-shaped query
  │
  ├─ 1 · Vector-first recall       kb_search_vector over the routed category
  │                                base(s); balance_kbs stops one large KB
  │                                dominating the candidate pool
  │
  ├─ 2 · ⭐ Content gate (0–8)     an agent READS the candidate text and
  │                                scores it:  topic 0–3 · scenario 0–3 ·
  │                                evidence 0–2
  │                                score ≥ 6 → fast exit, answer now
  │                                score = 5 → keep as fallback, escalate
  │                                score ≤ 4 → discard
  │
  ├─ 3 · Librarian fallback        gate-failed? targeted re-search + deeper
  │                                reads over the routed KBs — the gate-fail
  │                                in the benchmark run was rescued here
  │
  ├─ 4 · Not-found contract        nothing passes? an explicit
  │                                not-found report — never a guess
  │
  └─ 5 · Answer + citations        five-section format: search paths ·
                                   answer · sources · confidence ·
                                   declared blind spots
```

<details>
<summary><b>The 0–8 content rubric</b></summary>

<br>

| Score | Meaning | What happens |
|:---:|---|---|
| **0–2** | Off-topic, or the document is about something else entirely | **Discarded** |
| **3–4** | Tangential — one relevant sentence buried in an unrelated document | **Discarded** |
| **5** | On topic but the specifics asked for are not in the window read | Kept as **fallback** → **librarian escalation** (targeted re-search + continuation reads) |
| **6–7** | On topic, answers the question with partial depth | Kept, fast exit |
| **8** | Directly answers the question from the text read | Kept, fast exit |

The point of the rubric is that it is applied **after** recall and **by reading content**, so a high cosine score buys a document nothing. And when the gate fails, the protocol does not silently return the least-bad candidate — it goes looking again, and if nothing passes it says so.

</details>

---

## Agent chat, any harness

The built-in chat page speaks to **14 agent harnesses** — Claude Code, OMP, Codex CLI, Gemini CLI, Copilot CLI, Cursor CLI, DeepSeek Harness, Hermes Agent, OpenCode, Crush, Goose, Qwen Code, pi, plus an in-process mock for CI — through one adapter layer:

- **Per-harness model selection** — each harness exposes its real model catalog (`omp models --json`, `opencode models`, ACP `configOptions`, …); you pick from a dropdown or type any model the harness accepts.
- **Per-harness reasoning effort** — only the levels each harness natively supports (`--thinking`, `model_reasoning_effort`, `--effort`, ACP `reasoning_effort`), nothing invented.
- **Per-harness permission modes** — the harness's own semantics: Claude's permission modes, Codex's sandbox tiers, ACP `request_permission`, and so on.
- **Unified human-in-the-loop** — every approval request (Claude's `canUseTool`, ACP's `session/request_permission`) surfaces as one approval dialog in the same chat; allow, deny, or pick a harness-provided option. The stream blocks until you decide.
- **Availability is probed, not guessed** — the platform checks each harness at startup and on demand (executable, version, credentials); unavailable harnesses are disabled in the UI with the reason, and every harness gets a one-click diagnosis plus an optional live round-trip self-test.

---

## Architecture

<div align="center">
<img src="./docs/images/readme-architecture.svg" alt="Architecture: clients, MCP tool layer, services, storage" width="100%" />
</div>

Three services and a tool layer, all reading their ports and paths from one `config.yml`:

| Port | Service | Role |
|---:|---|---|
| `6789` | Nuxt 3 | UI + server-side proxy. The browser never calls the backend directly (no CORS surface). |
| `8770` | FastAPI | Parse scheduling, vector, graph, experience, SOUL. Refuses to start if the port is already taken. |
| *ephemeral* | MinerU OCR | Dual-mode: a remote mineru-api when configured (probed at startup), otherwise a local engine auto-started on a free port as a managed subprocess. |
| `7687` | Neo4j | Document graph, cross-KB bridges. |
| — | ChromaDB | Chunk embeddings, one collection per knowledge base. |

**The read/write asymmetry is deliberate:** writes go through the HTTP API so they are atomic and auditable; reads go straight to `.tree-fs.json` and `.knowledge-base.yml` on disk, so search costs zero backend load.

> **Note:** both READMEs document the default `8770`/`6789` pair. If you are running more than one instance you may see a second backend on another port, such as `8771` — check `config.yml`, `.env` (`BACKEND_PORT`), and the settings page banner, which reads the running values.

---

## Quick start

```bash
# 1 · clone
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 2 · install every dependency + model (idempotent)
./ragctl setup          # Windows: ragctl setup

# 3 · start everything — silent, no terminal windows
./ragctl up             # Windows: ragctl up

# check
./ragctl status
```

Then open **http://localhost:6789**.

`ragctl` is the single entry point for all operations — services, models, configuration, health checks, knowledge bases, personas and harnesses.

<details>
<summary><b>All <code>ragctl</code> commands</b></summary>

<br>

| Group | Commands |
|---|---|
| **Lifecycle** | `setup` `up` `down` `start` `stop` `restart` `status` `logs` |
| **Assets** | `install` `model` `mineru-model` `clean` `backup` `restore` |
| **Interface** | `desktop` (alias `ui`) |
| **Knowledge** | `meditation` `soul` (alias `persona`) `harness` |
| **Housekeeping** | `check` `deps` `version` `update` |

`soul` subcommands: `distill` `list` `status` `init` `learn` `learn-all` `train-rl` `evaluate` `review-cognition` `harness` `ask` `router` `review` `reflect` `export` `train` `checkpoint`.

</details>

### Prerequisites

| | Requirement | Why |
|---|---|---|
| **Python** | 3.12 (`>=3.12,<3.13`) | MinerU and the backend are pinned to this range |
| **Node.js** | ≥ 18 | Nuxt 3 |
| **uv** | any recent | Python env management |
| **Disk** | a few GB | MinerU models plus your corpus |
| **Optional** | Neo4j on `7687` | Graph features degrade gracefully without it |

---

## Use it four ways

### 1 · Web UI

Eleven pages: dashboard, file system, knowledge base manager, QDCVR search, graph explorer, SOUL persona studio, agent chat, harness hub, settings, API tokens, login. Light and dark, desktop to phone.

### 2 · HTTP API

Nothing here requires an agent or MCP. See [External HTTP API](#external-http-api).

### 3 · CLI

```bash
./ragctl status                 # service health
```

### 4 · MCP — any agent

The MCP server is launched by your client over stdio via `.mcp.json` at the repo root. Claude Code, Cursor, or any MCP-capable client works; no restart of the platform is needed.

```jsonc
// .mcp.json  (already in the repo)
{
  "mcpServers": {
    "kb-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "kb-mcp", "python", "server.py"]
    }
  }
}
```

Then just talk to it — *"what do we know about biaxial stretching of PET films?"* — and the agent will route through the knowledgebase skill, which enforces the quality gates.

---

## MCP tools

Every tool is registered with FastMCP in `kb-mcp/server.py`: **94 tools in total, of which 41 are `kb_*` knowledge-base tools** — the domain surface the CIKM demo paper demonstrates. The partition below is exhaustive and disjoint.

**`kb_*` knowledge-base tools — 41** (the surface the paper's demo drives):

| Category | Count | What it covers |
|---|:---:|---|
| **Knowledge graph** | 11 | graph-search · stats · per-document relations · related · KB overview · build · cross-KB documents · paths · central documents · delete document/KB |
| **Document CRUD** | 9 | read · create · update-meta · update-content · delete · batch-delete · move · save-parsed · get-documents |
| **Vector / index** | 6 | index-document · batch-index · reindex · cleanup-orphans · find-duplicates · task-status |
| **KB CRUD** | 4 | list · create · update · delete |
| **Search** | 4 | search (metadata) · vector · two-stage · stats |
| **Tags** | 4 | list · update · get-by-tag · cleanup |
| | **41** | |

**Platform tools — 53** (everything else the platform does):

| Category | Count | What it covers |
|---|:---:|---|
| **Experience** | 26 | Full E0–E12 lifecycle · search-global · search-smart · rerank · extract · drafts (list/read/approve/reject) · stale-check · sync · dashboard · decay · meditation (run/status/history/config) |
| **SOUL persona** | 20 | init · list · status · learn · learn-all · train-rl · evaluate · calibrate · cognition drafts · review · reflect · checkpoint · rollback · ask · qdcvr-ask · router · export (LoRA) |
| **Project lifecycle** | 4 | status · start · update · backend-status |
| **File system** | 3 | get-tree · get-children · upload-file |
| | **53** | |

Two design rules worth knowing:

- **Parse tools are non-blocking.** They return a `task_id` immediately; poll with `parse_task_status`. A parse never blocks an agent turn.
- **Long jobs return task ids too.** `kb_reindex`, `kb_graph_build` and `experience_meditation_run` all hand back a task id rather than holding the connection open.

<details>
<summary><b>Agent skills</b></summary>

<br>

The `knowledgebase` dispatcher skill routes natural-language requests — in Chinese or English — to the right sub-skill (ingest, search, manage, organize, update, verify, graph, experience, …), and delegates execution to an Archival sub-agent so quality gates cannot be skipped. The QDCVR v2 search skill is the same protocol the benchmark's Track A executes.

</details>

---

## External HTTP API

Auth is **on by default** (`server.auth.enabled: true`). Every endpoint except `/api/v1/health` and `/api/v1/auth/*` requires a bearer token. The interactive spec is at **`/docs`** on the backend; the generated OpenAPI declares `bearerAuth` on the non-public operations.

```bash
# 0 · get a token  (register first if this is a fresh install)
TOKEN=$(curl -s -X POST http://localhost:6789/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"you","password":"your-password"}' | jq -r .token)

# 1 · create a knowledge base
curl -s -X POST http://localhost:6789/api/kb/create \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"name":"engineering-notes","description":"Internal engineering notes"}'

# 2 · write a document   (kbId and kb_id are both accepted; snake_case aliases normalise)
curl -s -X POST http://localhost:6789/api/kb/documents/create \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"kbId":"<kbId>","name":"pump-failure.md","content":"# Pump failure\n\nBearing temperature exceeded 90°C..."}'

# 3 · vector search   (QDCVR Phase 1's recall tool)
curl -s -X POST http://localhost:6789/api/v1/search/vector \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"query":"bearing temperature limit","limit":5}'

# health needs no token
curl -s http://localhost:8770/api/v1/health
```

Rate limiting defaults to **600 requests / 60 s**.

<details>
<summary><b>Endpoint map</b></summary>

<br>

| Area | Base path |
|---|---|
| Auth | `/api/v1/auth/{register,login,verify}` · `/api/auth/*` (web proxy) |
| Knowledge bases | `/api/kb/{create,catalog,documents}` |
| Search | `/api/v1/search/{two-stage,vector}` |
| Harnesses | `/api/v1/meditation/harnesses` (+ per-harness models / diagnostics / diagnose) |
| Experience | `/api/v1/experience/*` |
| SOUL | `/api/v1/soul/*` |
| Graph | `/api/v1/graph/*` |
| Parse | `/api/v1/parse/*` |
| MinerU | `/api/v1/mineru/{status,probe}` |
| Health | `/api/v1/health` (public) |

The live OpenAPI document is the authority.

</details>

---

## Configuration

One file. `config.yml` at the repository root is the single source of truth for ports and hosts, read by the backend, the web proxy and the MCP server alike.

```yaml
server:
  dev:
    backend_port: 8770
    frontend_port: 6789
    backend_url: "http://localhost:8770"
  prod:
    backend_port: 8001
    frontend_port: 3000
    backend_url: "http://localhost:8001"
```

Priority is `BACKEND_PORT` env var → `config.yml` → code default. `APP_MODE=dev|prod` selects the section. Nothing in the codebase hardcodes a port or a path.

> Changing `config.yml` while `APP_MODE=dev` will hot-reload the backend. In long sessions prefer `APP_MODE=prod` to avoid reload storms from log/database writes.

---

## Storage model

```
web/storage/tree-file-system/
├── .tree-fs.json                 # L1 · authoritative global tree index
└── {knowledge-base}/
    ├── .knowledge-base.yml       # L2 · per-KB document index (name, tags, metadata)
    ├── {document}.md             # L3 · parsed / uploaded markdown
    └── images/                   #      images extracted during parsing
```

| Layer | Store | Holds |
|:---:|---|---|
| **L1** | `.tree-fs.json` | Every folder and file, with metadata |
| **L2** | `.knowledge-base.yml` | Per-KB search index — read directly by search |
| **L3** | `.md` on disk | The content itself |
| **L4** | ChromaDB | Chunk embeddings, one collection per KB |
| **L5** | Neo4j | Document, tag and KB nodes plus typed relations |

> L5 is populated only for knowledge bases you have built a graph for. On a fresh install the graph is empty and the graph page will legitimately show zero nodes — tag nodes in particular appear only after a graph build over tagged documents.

---

## Benchmark

Everything runs from **one reproducible pipeline**: [`benchmark-suite/PIPELINE.md`](./benchmark-suite/PIPELINE.md) — download 50 real arXiv papers across 26 fields → parse through the production MinerU chain → route into 5 category bases by content (an agent judgment step, grounded in per-paper excerpts) → tag every part → build three replication chunk-bases (fixed-800 / structural / paragraph) → restart → run a scripted 10-question regression → answer the same 10 questions on three tracks (the QDCVR v2 skill flow vs a bare agent vs a dense baseline) → generate the reports. **One red line: nothing is fabricated — judgment artifacts must trace to exported evidence.**

**This run's committed numbers** (traceable to `benchmark-suite/results/`):

| Stage | Result |
|---|---|
| Parse (MinerU, production chain) | 50/50 papers · 3.8 M characters |
| Content routing + verification | 50/50 verified into 5 category bases (165 indexed documents) |
| Content tags | 165/165 parts tagged, 0 failures |
| Replication bases | 2 366 / 1 385 / 10 219 chunks |
| Scripted 10-question regression (vector-first) | **9/10 = 90 %** — the one miss is a long-paper chunk-window miss (`doc_hit=true`), identical across runs |
| **Live three-track answering**, same 10 questions | **A · QDCVR v2: 10/10 on-target** (gates 6–8/8, librarian rescue on the one gate-fail, top-1 gold recall 10/10, ≈1.6 s mean vector recall + 0.8 s reads) · **B · bare agent: 10/10 gold**, provenance stops at file names, 78.8 s average · **C · dense baseline: content matches**, 2/10 abstained, no source paths, 12.2 s average |
| Honest-failure probes | 3 out-of-corpus questions → explicit not-found reports, zero fabrication |

The CIKM demo paper's figures (`paper_demo/figures/`) are generated from these artifacts.

> **On withheld results.** Earlier revisions of this README quoted IR-style numbers (`Hit@k`, `nDCG@10`, etc.) from standard corpora, and before that a larger benchmark from `benchmark-web/backend/results/` which contains **no producing script** in this repository. The IR corpora were retired in the 2026-09 benchmark redesign (standard corpora measure ranking, not knowledge-base management); the superseded scripts and corpora are archived under `.bench_backup_20260917/`. Figures that cannot be regenerated from a committed script are treated as unavailable.

<sub>Counts last verified against a live instance on **2026-09-19**: 8 knowledge bases · 165 indexed documents in the category bases · 94 MCP tools (41 `kb_*`) · 286 backend tests passing.</sub>

---

## Publications

- **Designed README showcase** — an art-directed single-page view of this README: [`docs/readme-showcase/index.html`](./docs/readme-showcase/index.html) (screenshot: [`README-showcase.png`](./docs/readme-showcase/README-showcase.png)).
- **QDCVR: A Deployable Knowledge-Base Management Platform with Content-Based Organization and Content-Verified Retrieval** — CIKM '26 demo submission. Sources: [`paper_demo/tex/`](./paper_demo/tex/), figures: [`paper_demo/figures/`](./paper_demo/figures/), demo video: [paper_demo/video/qdcvr-demo.mp4](./paper_demo/video/qdcvr-demo.mp4).

---

## Scope and non-goals

Being explicit about what this is **not**:

- **Not a hosted service.** It is self-hosted by design; there is no multi-tenant isolation story here.
- **Not a fine-tuning platform.** The SOUL LoRA export is an *export* path, not a training pipeline you should expect to compete with a dedicated trainer.
- **Not a vector-search replacement.** On questions whose answer sits inside a small corpus an agent can read whole, a bare agent answers without an index; the platform earns its keep on management at scale — content-routed organization, per-part tagging, graphs, integrity, and answers whose provenance goes down to document part and section.
- **Not turnkey on Windows without Python 3.12.** The dependency pin is real; 3.13 is not supported yet.
- **Not graph-complete out of the box.** L5 is populated by an explicit graph build, per knowledge base.

---

## Contributing

Issues and pull requests are welcome. Before opening a PR:

```bash
cd backend && uv run pytest          # backend unit tests (integration tests need --run-integration)
cd web && npx nuxt build             # type-check + build
node scripts/validate_skills.cjs     # cross-skill consistency (8 checks)
```

Conventions: ports and paths always come from `config.yml`; Python uses type annotations and `logging`, never `print`; `httpx` calls pass `trust_env=False` so the localhost proxy cannot hijack them; parse tools never block.

---

## License

MIT — see [LICENSE](./LICENSE).

<div align="center">
<br>
<sub>Built as a research platform for content-verified retrieval.<br>
Screenshots are real captures of the running application; benchmark figures are traceable to committed artefacts or are not stated.</sub>
</div>
