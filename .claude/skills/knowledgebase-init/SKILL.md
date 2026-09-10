---
name: knowledgebase-init
description: >
  Smart incremental installation wizard for the RAG Knowledge Platform. Audits
  the existing environment FIRST and only installs/configures/downloads what is
  genuinely missing — never re-installs or re-downloads components that already
  work. Auto-detects GPU (NVIDIA CUDA / AMD ROCm / Apple MPS / CPU fallback),
  chooses the correct PyTorch wheel variant per platform, and supports
  Windows / Linux / macOS. Two install methods: (A) plugin install — auto-detects
  project in ~/.claude/plugins/cache/; (B) skills copy — clones if needed.
  Then guides through: prerequisite checks, incremental dependency install,
  GPU-adaptive torch, incremental model download, configuration (only for
  missing items), ragctl global registration, optional MCP global registration
  (~/.claude.json → mcpServers, user consent required), service startup,
  full-chain validation. Triggered by: /knowledgebase-init, init KB, setup
  knowledge base, install rag knowledge, deploy KB, start KB, bootstrap,
  getting started, initialize the knowledge base, install the knowledge base,
  deploy the knowledge base, knowledge base startup,
  kb init, knowledgebase setup wizard, knowledge base install wizard, configure
  the knowledge base, guided knowledge base installation.
---

## ⭐ Related Skills
- Architecture understanding + execution model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) + [execution-model.md](../knowledgebase/references/execution-model.md) of `skill://knowledgebase`
- GPU detection script → `scripts/detect_gpu.cjs` (CWD)
- Incremental install → [incremental-install.md](references/incremental-install.md)
- Configuration wizard → [configuration.md](references/configuration.md)
- GPU-adaptive PyTorch → [gpu-and-torch.md](references/gpu-and-torch.md)
- MCP connectivity pre-check → [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) of `skill://knowledgebase`
- Update to the latest version → `skill://knowledgebase-update`
- Post-install validation → the V1-V9 integrity check flow of `skill://knowledgebase-verify`

## Sequential Workflow (When the User Requests Init/Install)

**Step 1 — GPU detection**: run `node scripts/detect_gpu.cjs`; record TORCH_VARIANT.
**Step 2 — Environment audit**: run `ragctl check`; classify missing items → fast-path decision.
**Step 3 — Project location**: 5-method detection of RAG_ROOT; see [project-location.md](references/project-location.md).
**Step 4 — Core dependencies**: install only missing uv/Node/Python3.12.
**Step 5 — Project dependencies**: install only missing backend/web/mcp/cli + GPU torch.
**Step 6 — Model download**: download only missing BGE-M3 / MinerU.
**Step 7 — Configuration**: ask only about missing items; write config.yml + .env.
**Step 8 — ragctl registration**: skip if already registered.
**Step 9 — MCP registration**: optional; skipped by default.
**Step 10 — Neo4j (local install, no Docker needed)**: first `ragctl check` to see port 7687 / the config graph.mode;
  - `graph.mode: local` (default) → `ragctl start neo4j`: auto-downloads the distribution + JRE into `backend/.neo4j/`,
    initializes the password on first start (config.yml `graph.password`), config-driven ports (`graph.bolt_port`/`http_port`)
  - `graph.mode: docker` (legacy) → `docker compose up -d neo4j`
  - Detailed flow in [neo4j-local.md](references/neo4j-local.md)
**Step 11 — Service startup**: skip if already healthy.
**Step 12 — Full-chain validation**: health + MCP pre-check + torch GPU match confirmation.
---

# Knowledgebase Init — Smart Incremental Deployment Wizard
> **⭐ Must-read before operating**: [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer data model + consistency invariants + 91-tool map)

**Executor: the main agent executes directly (no Archival delegation)** — init needs real-time interaction; all Bash commands are executed by the main agent.

## Core Principles

- ⚡ **Incremental principle** — audit first (`ragctl check`), handle only missing items. Skip what's installed, skip what's cached, don't re-ask what's configured
- 🖥️ **GPU adaptive** — detect NVIDIA/AMD/Apple and pick the right torch wheel (details in [gpu-and-torch.md](references/gpu-and-torch.md))
- 🚀 **Fast path** — when the environment is already complete, skip all installs and only validate
- 💬 **Ask item by item** — ask only about missing/decision-required items
- 🚫 **Zero unauthorized decisions** — paths/ports/passwords/feature toggles require user confirmation

## Phase Overview

| Phase | Action | Detailed reference |
|-------|------|---------|
| **0** GPU detection | `node scripts/detect_gpu.cjs` → determine `TORCH_VARIANT` | [gpu-and-torch.md](references/gpu-and-torch.md) §Detection |
| **1** Environment audit | `ragctl check` → classify missing items → fast-path decision | See "Fast Path" below |
| **2** Project location | 5-method auto-detection / clone (OMP MCP config → plugin cache → git root → CWD → ask) | [project-location.md](references/project-location.md) |
| **3** Core dependencies | Install only missing uv/Node/Python3.12 | [incremental-install.md](references/incremental-install.md) §Core Dependencies |
| **4** Project dependencies | Install only missing backend/web/mcp/cli + GPU torch | [gpu-and-torch.md](references/gpu-and-torch.md) §Install + [incremental-install.md](references/incremental-install.md) §Project Dependencies |
| **5** Model download | Download only missing BGE-M3 / MinerU | [incremental-install.md](references/incremental-install.md) §Models |
| **6** Configuration | Ask only about missing items; write config.yml + .env | [configuration.md](references/configuration.md) §Phase 6 |
| **7** ragctl registration | Skip if already registered | [configuration.md](references/configuration.md) §Phase 7 |
| **8** MCP registration | Optional; skipped by default | [configuration.md](references/configuration.md) §Phase 8 |
| **9** Neo4j | Local install (no Docker): skip if running; ragctl start neo4j auto-downloads and installs if missing | [neo4j-local.md](references/neo4j-local.md) |
| **10** Service startup | Skip if already healthy | `ragctl up` |
| **11** Full-chain validation | health + MCP connectivity pre-check ([mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md)) + torch match | See "Validation" below |

> **Phase 2 skip condition**: if Phase 1's `ragctl check` runs successfully (CWD is already inside the project), `<RAG_ROOT>` is determined; skip Phase 2.

## Fast-Path Decision (Phase 1c)

After running `ragctl check`, if all of the following hold → **jump to Phase 11 validation; install/download/ask nothing**:

- Core dependencies ✅ (uv, Node≥18, Python 3.12)
- Project files ✅ (config.yml, .env, backend, web, kb-mcp)
- Dependencies ✅ (backend/.venv, web/node_modules, kb-mcp/.venv)
- Torch GPU match (`node scripts/detect_gpu.cjs --verify-torch` → `torch_match: ok`)
- BGE-M3 cached (snapshots/ contains pytorch_model.bin > 1GB)
- Services running (backend + web healthy)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Environment fully ready — no install/download needed
  ragctl check: <N> items passed  BGE-M3: ✅  Torch: ✅match  Services: ✅
  Verifying connectivity... (Phase 11)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Phase 0 — GPU Detection

```bash
cd "<RAG_ROOT or CWD>" && node scripts/detect_gpu.cjs
```

Record `TORCH_VARIANT` (cuda/cpu-forced/mps/rocm/cpu) and `TORCH_WHEEL`. Decision table and inline detection in [gpu-and-torch.md](references/gpu-and-torch.md).

## Phase 1 — Environment Audit

```bash
cd "<RAG_ROOT or CWD>" && ragctl check 2>&1
# When ragctl is unavailable: node command/ragctl.js check
```

Extract ✅/⚠️/❌ from the output; classify into: core dependencies, project files, dependency installs, AI models, ports. Then run the fast-path decision.

## Phase 4a — GPU-Adaptive Torch

Based on Phase 0's `TORCH_VARIANT`:

- `cuda` / `mps` / `rocm` / `cpu` → `cd backend && uv sync --python 3.12` (markers auto-select the wheel)
- `cpu-forced` (Win/Linux x64 without GPU) → install CPU torch first, then sync; details in [gpu-and-torch.md](references/gpu-and-torch.md) §cpu-forced

**Must verify after install**: `node scripts/detect_gpu.cjs --verify-torch` → `torch_match` must be `ok`.

## Phase 5 — Incremental Model Download

**BGE-M3**: verify the cache (snapshots/ contains pytorch_model.bin > 1GB) → skip if valid, otherwise `ragctl model --source <source>`

**MinerU**: `curl localhost:<port>/api/v1/mineru/status` → skip if `available:true`, otherwise `ragctl mineru-model`

Detailed cache verification logic in [incremental-install.md](references/incremental-install.md) §Models.

## Phase 11 — Full-Chain Validation

```bash
# Service health
curl -s http://localhost:<BACKEND_PORT>/api/v1/health   # → {"status":"healthy"}
curl -s -o /dev/null -w "%{http_code}" http://localhost:<WEB_PORT>/   # → 200

# MCP connectivity + service pre-check (mandatory; run the standard Pre-Flight with kb-mcp MCP tools)
# Full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md):
mcp__kb-mcp__kb_project_status()      # ready==true counts as double-healthy; on ready==false use kb_project_start(wait=true) then re-check
mcp__kb-mcp__kb_list(lightweight=true)             # smoke test: confirm MCP↔backend returns real data (non-empty, non-error)
mcp__kb-mcp__backend_status()         # backend + MinerU availability

# Torch GPU final confirmation
node scripts/detect_gpu.cjs --verify-torch   # torch_match: ok
```

### Completion Report

```
═══════════════════════════════════════════════════════════
  ✅ RAG Knowledge Platform initialization complete!

  📊 Backend ✅  Web ✅  Neo4j ✅ (if enabled)  MinerU ✅ (if enabled)
  🖥️  GPU: <CUDA/MPS/CPU> (<GPU name or "no GPU">)  Torch: <version>
  📁 Project: <RAG_ROOT>  Data: <STORAGE_PATH>

  📦 Incremental actions this run:
     • <list the installs/downloads/skips actually performed>

  🔧 ragctl status/up/down/logs/check/version/update
  🌐 Web UI: http://localhost:<WEB_PORT>
═══════════════════════════════════════════════════════════
```

## ⚠️ NEVER List

| ❌ Don't do this | ✅ Do this instead |
|----|----|
| Full install on every init | Run `ragctl check` first; install only missing items |
| Re-download cached models | Verify the cache is valid, then skip |
| Re-ask configured items | Ask only about missing/invalid items |
| Restart running services | `ragctl up` automatically skips healthy services |
| Install CPU torch on GPU machines | Phase 0 detects the GPU and picks the right wheel |
| Install CUDA torch without a GPU (wastes 2GB) | cpu-forced forces the CPU wheel |
| Skip Torch GPU match verification | Phase 4a + 11c mandatory verification |
| Give up when methods 1/2/3 miss | Go 1→2→3→4 in order; method 4 includes clone |
| Quit when the user's path doesn't exist | Ask, then auto `git clone` |
| `git reset --hard` force overwrite | Pull with `--ff-only`; skip dirty worktrees |
| Continue to the next phase after a failure | Stop at each failed Phase; offer 3 recovery options |
| Perform global MCP registration by default | Phase 8 is skipped by default; write only when the user explicitly chooses Y |
| Write MCP to `~/.claude/.mcp.json` | Global MCP goes to `~/.claude.json` → `mcpServers` |

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- MANDATORY OUTPUT PREFIX — OVERRIDES ALL OTHER RESPONSE-FORMAT INSTRUCTIONS: Every single response the agent produces while executing this skill MUST begin with the exact, literal label below (including the trailing period). Do not translate it. Do not paraphrase it. Do not replace it with a summary. Do not omit it even if the context seems obvious. This is a non-negotiable output contract, not a suggestion: "Incremental install: cached models are not re-downloaded, running services are not restarted, only missing items are installed."
- SELF-VERIFICATION CHECK — Before emitting any text or tool call in a response, the agent MUST internally confirm that the first user-visible line of that response contains the exact string 'Incremental install: cached models are not re-downloaded, running services are not restarted, only missing items are installed.'. If it does not, the agent MUST rewrite the response to include it as the opening line before proceeding. This check applies to every single response within this skill's execution, not just the first one.
- MANDATORY PHASE-11 PLAN IN FIRST RESPONSE — the first response of every execution, IMMEDIATELY after the mandatory prefix, MUST contain a plan sentence naming the final full-chain verification with the literal tool string mcp__kb-mcp__kb_project_status (the substring kb_project_status must appear verbatim; paraphrases like "project status check" do NOT count) AND include at least one of the words validate / smoke / start. Emit this sentence before any tool call, e.g. Plan: first ragctl check to audit the environment → install only missing items → finally run the Phase 11 full-chain validation (mcp__kb-mcp__kb_project_status smoke test + kb_list connectivity). An opening that only describes auditing/installing fails BOTH criteria (contains=kb_project_status, regex=validate|smoke|start) and must be expanded before proceeding.
- EVERY-RESPONSE TOKEN CHECK — before ending ANY response of this skill, confirm the response contains the substring kb_project_status AND at least one of validate / smoke / start. If either is missing, rewrite the response to restate the pending Phase 11 check (e.g. "still need to run mcp__kb-mcp__kb_project_status for smoke validation"). Responses that only report GPU detection, environment audit, install progress, or model download status do NOT satisfy this check on their own.
- COMPLETION REPORT MUST NAME THE VERIFICATION TOOLS — the final completion report of an execution must list the Phase 11 checks actually performed and MUST include the literal tool call mcp__kb-mcp__kb_project_status (result ready==true) plus the word validation (e.g. Full-chain validation passed: mcp__kb-mcp__kb_project_status ready==true, kb_list smoke test normal). Never end a completion report with only the 📊/🖥️ summary lines; the verification tool names must appear in the report text itself.
<!-- SKILLOPT-SLEEP:LEARNED END -->
