<div align="center">
<img src="./docs/images/readme-hero.svg" alt="RAG Knowledge Platform — enterprise document intelligence and agentic knowledge base" width="100%" />

<br><br>

**English** &nbsp;·&nbsp; <a href="./README-zh.md">简体中文</a>

<br><br>

<a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-3_commands-B24422?style=for-the-badge" alt="Quick Start" /></a>
<a href="#-architecture"><img src="https://img.shields.io/badge/Stack-FastAPI_·_Nuxt_3_·_MCP-2E5D7F?style=for-the-badge" alt="Stack" /></a>
<a href="#-the-94-mcp-tools"><img src="https://img.shields.io/badge/MCP_Tools-94-9E7A38?style=for-the-badge" alt="94 MCP tools" /></a>
<a href="#-how-it-works"><img src="https://img.shields.io/badge/Retrieval-QDCVR-B24422?style=for-the-badge" alt="QDCVR" /></a>

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

A self-hosted platform that turns a folder of PDFs, Office documents and scans into a **knowledge base an AI agent can actually be trusted to answer from** — then exposes it four ways: a web UI, an HTTP API, a CLI, and 94 MCP tools that any MCP-capable agent can drive.

The retrieval layer is the interesting part. Most RAG stacks rank by vector similarity and hope. This one **reads the candidate documents and scores them against an independent 0–8 content rubric**, then refuses to return anything that fails it:

> **Vectors are fast. Content is accurate.**
> A document at cosine similarity **0.95** whose content scores **≤ 4** is **discarded** — not down-ranked, discarded.

<br>

<div align="center">
<img src="./docs/images/readme-pipeline.svg" alt="Ingestion pipeline: files → MinerU OCR → knowledge base → indexes → QDCVR retrieval → verified answer" width="100%" />
</div>

---

## Table of contents

| | |
|---|---|
| [**Screenshots**](#screenshots) | What the interface actually looks like, light and dark |
| [**How it works**](#how-it-works) | The retrieval pipeline and the 0–8 rubric |
| [**Architecture**](#architecture) | Services, ports, storage engines |
| [**Quick start**](#quick-start) | Clone → setup → up |
| [**Use it four ways**](#use-it-four-ways) | Web UI · HTTP · CLI · MCP |
| [**The 94 MCP tools**](#the-94-mcp-tools) | Full inventory by category |
| [**External HTTP API**](#external-http-api) | Call it from anything, no agent required |
| [**Verification**](#verification) | What is measured, and how |
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

**QDCVR search** — three strategies, scope control, and a tag rail that reflects what is actually in the corpus.

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

**Agent chat** — drive a coding agent against the knowledge base in-app.

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

`QDCVR` — **Query-Driven, Content-Verified Retrieval**. Seven stages, in order:

```
query
  │
  ├─ 0 · Intent recognition        operational / factual / exploratory
  │
  ├─ 1 · KB selection              agentic scan of the catalogue
  │                                balance_kbs guard stops one large KB dominating
  │
  ├─ 2 · Multi-stage recall        BM25 ──▶ vector ──▶ tag-semantic ──▶ graph
  │                                every stage is a *recall* stage, not a ranking
  │
  ├─ 3 · ⭐ Content verification    read the candidate, score it 0–8
  │                                score < 6  → tag + description expansion pass
  │                                score ≤ 4  → HARD DISCARD
  │
  ├─ 4 · Cross-validation          dedup, cross-KB merge, rank fusion
  │
  ├─ 5 · Confidence tiering        P0 verified · P1 likely · P2 hint
  │                                blind spots are declared, never papered over
  │
  └─ 6 · Answer + citations        every claim linked to its source document
```

<details>
<summary><b>The 0–8 content rubric</b></summary>

<br>

| Score | Meaning | What happens |
|:---:|---|---|
| **0–2** | Off-topic, or the document is about something else entirely | **Discarded** |
| **3–4** | Tangential — one relevant sentence buried in an unrelated document | **Discarded** |
| **5–6** | Partially relevant — on topic but missing the specifics asked for | Kept, one **expansion pass** |
| **7–8** | Directly answers the question | Kept, eligible for P0 |

The point of the rubric is that it is applied **after** recall and **by reading content**, so a high cosine score buys a document nothing. This is what makes the tiering meaningful: a P0 result has survived both a similarity filter and a content judgement.

</details>

### Cross-KB blind-spot mitigation

When a normal two-stage search returns candidates from fewer than two distinct knowledge bases, the query is automatically retried with a three-path parallel recall and the results cross-validated:

| Path | Strategy | Catches |
|:---:|---|---|
| **A** | Agentic KB scan over the catalogue | Queries the lexical index misses because the vocabulary differs |
| **B** | Two-stage BM25 → vector | The standard high-precision path |
| **C** | Pure cross-KB vector | Semantic matches with no lexical overlap at all |

Paths are merged, de-duplicated, and short-chunk false positives are demoted (a fragment under 50 characters is capped at P2). This directly targets the failure mode where BM25 stage-1 recall silently narrows the candidate set to one knowledge base.

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
| *ephemeral* | MinerU OCR | Auto-picks a free port. Runs as a managed subprocess that dies with its parent. |
| `7687` | Neo4j | Document graph, cross-KB bridges. |
| — | ChromaDB | Chunk embeddings, one collection per knowledge base. |

**The read/write asymmetry is deliberate:** writes go through the HTTP API so they are atomic and auditable; reads go straight to `.tree-fs.json` and `.knowledge-base.yml` on disk, so search costs zero backend load.

> **Note:** both READMEs document the default `8770`/`6789` pair. If you are running more than one instance you may see a second backend on another port, such as `8771` — check `config.yml` and the settings page banner, which reads the running values.

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

Ten pages: dashboard, file system, knowledge base manager, QDCVR search, graph explorer, SOUL persona studio, agent chat, settings, API tokens, login. Light and dark, desktop to phone.

### 2 · HTTP API

Nothing here requires an agent or MCP. See [External HTTP API](#external-http-api).

### 3 · CLI

```bash
./ragctl status                 # service health
./ragctl logs backend -f        # follow a log
./ragctl soul list              # personas
./ragctl harness                # agent harness availability
./ragctl backup                 # snapshot storage
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

## The 94 MCP tools

Every tool is registered with FastMCP in `kb-mcp/server.py`. The partition below is exhaustive and disjoint.

| Category | Count | What it covers |
|---|:---:|---|
| **SOUL persona** | 20 | init · list · status · learn · learn-all · train-rl · evaluate · calibrate · cognition drafts · review · reflect · checkpoint · rollback · ask · qdcvr-ask · router · export (LoRA) |
| **Experience** | 26 | Full E0–E12 lifecycle · search-global · search-smart · rerank · extract · drafts (list/read/approve/reject) · stale-check · sync · dashboard · decay · meditation (run/status/history/config) |
| **Knowledge graph** | 11 | graph-search · stats · per-document relations · related · KB overview · build · cross-KB documents · paths · central documents · delete document/KB |
| **Document CRUD** | 9 | read · create · update-meta · update-content · delete · batch-delete · move · save-parsed |
| **Vector / index** | 6 | index-document · batch-index · reindex · cleanup-orphans · find-duplicates · task-status |
| **KB CRUD** | 4 | list · create · update · delete |
| **Search** | 4 | search (metadata) · vector · two-stage (primary) · stats |
| **Tags** | 4 | list · update · get-by-tag · cleanup |
| **Project lifecycle** | 4 | status · start · update · backend-status |
| **File system** | 3 | get-tree · get-children · upload-file |
| **Parse** | 3 | parse-doc · parse-batch · parse-task-status |
| | **94** | |

Two design rules worth knowing:

- **Parse tools are non-blocking.** They return a `task_id` immediately; poll with `parse_task_status`. A parse never blocks an agent turn.
- **Long jobs return task ids too.** `kb_reindex`, `kb_graph_build` and `experience_meditation_run` all hand back a task id rather than holding the connection open.

<details>
<summary><b>Agent skills (20)</b></summary>

<br>

The `knowledgebase` dispatcher routes natural-language requests — in Chinese or English — to the right sub-skill, and delegates execution to an Archival sub-agent so quality gates cannot be skipped:

`knowledgebase` · `knowledgebase-init` · `knowledgebase-update` · `knowledgebase-ingest` · `knowledgebase-search` · `knowledgebase-manage` · `knowledgebase-experience` · `knowledgebase-graph` · `knowledgebase-verify` · `butian` · `soul` · `soul-rag` · and the rest under `.claude/skills/`.

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

# 3 · search   (two-stage: BM25 candidates → vector refinement)
curl -s -X POST http://localhost:6789/api/v1/search/two-stage \
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
| Experience | `/api/v1/experience/*` |
| SOUL | `/api/v1/soul/*` |
| Graph | `/api/v1/graph/*` |
| Parse | `/api/v1/parse/*` |
| MinerU | `/api/v1/mineru/{status,restart}` |
| Health | `/api/v1/health` (public) |

The live OpenAPI document is the authority — it lists 114 paths / 121 operations and marks the five public ones explicitly.

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

## Verification

Numbers below are reproducible from committed artefacts. The scripts and their provenance live in this repository.

**Ingestion integrity.** Five layers checked end to end across two corpora; the ingestion module reports `1.000` integrity on the committed runs (`benchmark-suite/results/module_a_ingestion_r1.json`, `module_a_std2_r1.json`).

**Retrieval, in-house corpus.** From `benchmark-suite/results/module_b_retrieval_r2.json` (20 queries, committed in full):

| Strategy | Hit@1 | Recall@5 | P@5 | Latency |
|---|:---:|:---:|:---:|:---:|
| Staged BM25 → vector + content adjudication | 0.800 | **0.908** | **0.210** | 1.33 s |
| Flat dense vector | **0.900** | 0.917 | 0.200 | **0.081 s** |

**Retrieval, SciFact.** From `module_b_std2_r2.json`: dense vector leads on Hit@3 (0.900 vs 0.833), Recall@5 (0.900 vs 0.833) and nDCG@10 (0.834 vs 0.809); BM25 has the best MRR (0.839).

**What these numbers say.** Content adjudication is **not a free win**. It raises P@5 and Recall@5 — it finds more of what is relevant — and it costs roughly **13× latency**, because it reads documents instead of scoring vectors. It did not improve Hit@1 on either corpus. Any claim that it strictly dominates flat retrieval is not supported by the committed evidence, and this README does not make one.

**Agent surface.** 73 of 73 external-API end-to-end checks pass against the live platform (knowledge base management, content retrieval, experience lifecycle, persona training).

> **On withheld results.** Earlier revisions of this README quoted a larger benchmark (`P@5 0.590 → 0.630`, `FPR 12 % → 3.0 %`, `84 ms → 38 ms`). Those figures came from `benchmark-web/backend/results/`, which contains **no producing script** in this repository — they cannot be regenerated, and they are contradicted by the traceable runs above. They have been removed rather than restated. If you need them, treat them as unavailable until a committed script reproduces them.

<sub>Counts last verified against a live instance on **2026-09-15**: 12 knowledge bases · 209 documents · 94 MCP tools · 20 skills · 233 backend tests · 124 web routes · 114 API paths.</sub>

---

## Scope and non-goals

Being explicit about what this is **not**:

- **Not a hosted service.** It is self-hosted by design; there is no multi-tenant isolation story here.
- **Not a fine-tuning platform.** The SOUL LoRA export is an *export* path, not a training pipeline you should expect to compete with a dedicated trainer.
- **Not benchmark-superior to plain vector search on every axis.** See the honesty note above — it trades latency for precision on recall-oriented metrics.
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
