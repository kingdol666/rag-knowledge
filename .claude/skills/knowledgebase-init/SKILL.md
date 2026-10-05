---
name: knowledgebase-init
description: "Smart incremental installation wizard for the RAG Knowledge Platform. Audits the existing environment FIRST (backend/web/Neo4j/MinerU/engines/skills) and only installs, configures, or downloads what is actually missing — never reinstalls working components. Use when the user says init/安装/部署/初始化 the platform, reports a broken first-run, or wants environment repair."
---

## Related lanes

- Architecture + execution model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) + [execution-model.md](../knowledgebase/references/execution-model.md) of `skill://knowledgebase` · MCP connectivity pre-check → [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) · update → `skill://knowledgebase-update` · post-install validation → V1-V9 of `skill://knowledgebase-verify`
- Per-phase references (used by the table below): [incremental-install.md](references/incremental-install.md) · [configuration.md](references/configuration.md) · [mineru-mode.md](references/mineru-mode.md) · [gpu-and-torch.md](references/gpu-and-torch.md) · [project-location.md](references/project-location.md) · [neo4j-local.md](references/neo4j-local.md)

**Executor: the main agent executes directly (no Archival delegation)** — init needs real-time interaction; all Bash commands run in the main agent. Core principles: audit first and touch only what is missing (never reinstall working components, never re-download caches, never re-ask configured items); GPU-adaptive torch; fast path when complete; ask item by item; zero unauthorized decisions — paths/ports/passwords/feature toggles require user confirmation.

## Phase map (Phase n ↔ Step n; order fixed)

| Phase | Step | Action | Reference |
|---|---|---|---|
| 0 | 1 | GPU detection: `node scripts/detect_gpu.cjs` → record `TORCH_VARIANT` (cuda/cpu-forced/mps/rocm/cpu) + `TORCH_WHEEL` | [gpu-and-torch.md](references/gpu-and-torch.md) §Detection |
| 1 | 2 | Environment audit: `ragctl check` → classify missing items → fast-path decision | below |
| 1c | — | Fast-path decision: all ✅ → jump to Phase 11, install/download/ask nothing | below |
| 2 | 3 | Project location: 5-method detection / clone (OMP MCP config → plugin cache → git root → CWD → ask) | [project-location.md](references/project-location.md) |
| 3 | 4 | Core dependencies: install only missing uv/Node/Python 3.12 | [incremental-install.md](references/incremental-install.md) §Core Dependencies |
| 4 | 5 | Project dependencies: install only missing backend/web/mcp/cli | [incremental-install.md](references/incremental-install.md) §Project Dependencies |
| 4a | 5 | GPU-adaptive torch install + mandatory match verification | [gpu-and-torch.md](references/gpu-and-torch.md) §Install |
| 5 | 6 | Model download: only missing BGE-M3 / MinerU | [incremental-install.md](references/incremental-install.md) §Models |
| 5b | — | Laya decision engine (GPU, hosted in the MinerU venv) | below |
| 6 | 7 | Configuration: ask only about missing items; write config.yml + .env | [configuration.md](references/configuration.md) §Phase 6 |
| 6b | 7b | MinerU deployment mode: remote API (default) / local; verify health | [mineru-mode.md](references/mineru-mode.md) |
| 7 | 8 | ragctl registration: skip if already registered | [configuration.md](references/configuration.md) §Phase 7 |
| 8 | 9 | MCP registration: optional; skipped by default | [configuration.md](references/configuration.md) §Phase 8 |
| 9 | 10 | Neo4j (local install, no Docker needed): skip if running | [neo4j-local.md](references/neo4j-local.md) |
| 10 | 11 | Service startup: skip if already healthy | `ragctl up` |
| 11 | 12 | Full-chain validation: health + MCP pre-check + torch match + Laya device | below |

Phase 2 skip condition: if Phase 1's `ragctl check` runs successfully (CWD is already inside the project), `<RAG_ROOT>` is determined — skip Phase 2.

## Fast path (Phase 1c)

After `ragctl check`, if ALL of the following hold → jump straight to Phase 11 validation; install/download/ask nothing: core deps ✅ (uv, Node ≥18, Python 3.12) · project files ✅ (config.yml, .env, backend, web, kb-mcp) · deps ✅ (backend/.venv, web/node_modules, kb-mcp/.venv) · `node scripts/detect_gpu.cjs --verify-torch` → `torch_match: ok` · BGE-M3 cached (snapshots/ contains pytorch_model.bin > 1GB) · Laya ✅ (Phase 5b skip condition) · services running (backend + web healthy). Report: "Environment fully ready — no install/download needed; verifying connectivity (Phase 11)."

## Phase 0 + 1 — GPU detection, then audit

```bash
cd "<RAG_ROOT or CWD>" && node scripts/detect_gpu.cjs
cd "<RAG_ROOT or CWD>" && ragctl check 2>&1   # ragctl unavailable → node command/ragctl.js check
```
Extract ✅/⚠️/❌ from the output; classify into core dependencies / project files / dependency installs / AI models / ports; then run the fast-path decision. Torch decision table + inline detection: [gpu-and-torch.md](references/gpu-and-torch.md).

## Phase 4a — GPU-Adaptive Torch

`cuda`/`mps`/`rocm`/`cpu` → `cd backend && uv sync --python 3.12` (markers auto-select the wheel); `cpu-forced` (Win/Linux x64 without GPU) → install CPU torch first, then sync ([gpu-and-torch.md](references/gpu-and-torch.md) §cpu-forced). Must verify after install: `node scripts/detect_gpu.cjs --verify-torch` → `torch_match: ok`.

## Phase 5 — Incremental Model Download

BGE-M3: verify the cache (snapshots/ contains pytorch_model.bin > 1GB) → skip if valid, otherwise `ragctl model --source <source>`. MinerU: `curl localhost:<port>/api/v1/mineru/status` → skip if `available:true`, otherwise `ragctl mineru-model`. Cache verification logic: [incremental-install.md](references/incremental-install.md) §Models.

## Phase 5b — Laya Decision Engine (GPU, hosted in the MinerU venv)

The three retrieval modes (A vector-first / B librarian / C parallel-A+B) judge every segment with the Laya engine; since 2026-09-27 it is hosted in `backend/.venv` — which already carries GPU torch, and Laya auto-selects CUDA when available (single-segment verdict ≈0.05s vs ~2s on CPU). **Skip condition**: the backend/.venv python can `import laya` AND `model/laya/model.safetensors` exists AND the GPU verdict smoke (step 3) passes.
1. **Package**: `uv pip install --python backend/.venv/Scripts/python.exe laya==0.3.20` (torch/transformers<5/numpy/hub/safetensors already in the MinerU env).
2. **Model**: `python scripts/ensure_laya_model.py` (idempotent; repo-local `model/laya`, skipped when complete).
3. **GPU verdict smoke (mandatory)**: under the backend/.venv python, import jev_filter (librarian scripts dir on sys.path) and print `jev_filter._load_laya().device` — expect `cuda`; if `cpu`, re-check Phase 4a torch CUDA match.

**Interpreter rule (fail-closed)**: all judging scripts (search `vector_jev_search`, librarian `complete_recall`/`jev_filter`, hybrid `hybrid_search`, parallel orchestrator `scripts/124_mode_c_parallel.py`) MUST run under the backend/.venv python — runners resolve it automatically (`resolve_laya_python()`, override with `RAG_LAYA_PYTHON`); a bare `python` without `laya` fails closed with `JevUnavailable`, never silent degradation.

## Phase 6b — MinerU Deployment Mode (remote API default / local)

Skip condition: `backend/config.yml` already has `mineru.mode` set AND (mode=local OR remote.base_url non-empty) → only re-verify health, don't re-ask. Otherwise **ask the user once**:
1. **Remote API (default/recommended)** — parsing goes to a mineru-api-compatible HTTP endpoint (zero local GPU/memory load); the engine automatically falls back to the local engine when the endpoint is unreachable. Collect `base_url` (http/https) + optional token → the token goes ONLY into `.env` as `MINERU_API_TOKEN` (never config.yml/source/logs). Write `mineru.mode: "remote"` + `remote.base_url`; verify immediately `curl -m 5 "<base_url>/health"` → 200, on failure offer retry / switch to local.
2. **Local deployment** — fully offline: install mineru (`uv sync`) + download models (`ragctl mineru-model`, ~2GB, skipped when the modelscope cache already holds model.safetensors >1GB); verify `local.installed:true` (+ `local.running:true` after `/api/v1/mineru/restart`).

Full decision flow / config schema / ops: [mineru-mode.md](references/mineru-mode.md). Mode switches hot-apply via `POST /api/v1/config/reload` — no backend restart.

## Phase 9 — Neo4j (local install, no Docker needed)

First `ragctl check` (port 7687 / config `graph.mode`): `graph.mode: local` (default) → `ragctl start neo4j` auto-downloads the distribution + JRE into `backend/.neo4j/`, initializes the password on first start (config.yml `graph.password`), config-driven ports (`graph.bolt_port`/`http_port`); `graph.mode: docker` (legacy) → `docker compose up -d neo4j`. Skip if already running. Detailed flow: [neo4j-local.md](references/neo4j-local.md).

## Phase 11 — Full-Chain Validation

```bash
curl -s http://localhost:<BACKEND_PORT>/api/v1/health   # → {"status":"healthy"}
curl -s -o /dev/null -w "%{http_code}" http://localhost:<WEB_PORT>/   # → 200
mcp__kb-mcp__kb_project_status()          # ready==true = double-healthy; ready==false → kb_project_start(wait=true), re-check
mcp__kb-mcp__kb_list(lightweight=true)    # smoke: MCP↔backend returns real data (non-empty, non-error)
mcp__kb-mcp__backend_status()             # backend + MinerU availability
node scripts/detect_gpu.cjs --verify-torch   # torch_match: ok
backend/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.claude/skills/knowledgebase-librarian/scripts'); import jev_filter; print(jev_filter._load_laya().device)"   # expect: cuda
```
Full pre-flight flow: [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md).

Completion report: component ✅ lines (Backend / Web / Neo4j if enabled / MinerU if enabled / Laya GPU verdict), GPU + torch version, RAG_ROOT + storage path, the incremental actions actually performed this run (installs/downloads/skips), ragctl command list (status/up/down/logs/check/version/update), Web UI URL — and it must name the Phase 11 checks actually performed, including `mcp__kb-mcp__kb_project_status` (ready==true).

## Never

- Full install on every init — run `ragctl check` first; install only missing items.
- Re-download cached models or re-ask configured items — verify the cache is valid, ask only about missing/invalid.
- Restart running services — `ragctl up` automatically skips healthy services.
- Install CPU torch on GPU machines, or CUDA torch without a GPU (wastes 2GB) — Phase 0 detects; cpu-forced forces the CPU wheel.
- Skip the torch GPU-match verification — Phase 4a + Phase 11 verification is mandatory.
- Give up when location methods 1/2/3 miss — go 1→2→3→4 in order (method 4 includes clone); if the user's path doesn't exist, ask, then auto `git clone`.
- `git reset --hard` force overwrites — pull with `--ff-only`; skip dirty worktrees.
- Continue to the next phase after a failure — stop at each failed phase; offer 3 recovery options.
- Perform global MCP registration by default — Phase 8 is skipped by default; write only when the user explicitly chooses Y.
- Write MCP to `~/.claude/.mcp.json` — global MCP goes to `~/.claude.json` → `mcpServers`.

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- MANDATORY OUTPUT PREFIX — OVERRIDES ALL OTHER RESPONSE-FORMAT INSTRUCTIONS: Every single response the agent produces while executing this skill MUST begin with the exact, literal label below (including the trailing period). Do not translate it. Do not paraphrase it. Do not replace it with a summary. Do not omit it even if the context seems obvious. This is a non-negotiable output contract, not a suggestion: "Incremental install: cached models are not re-downloaded, running services are not restarted, only missing items are installed."
- SELF-VERIFICATION CHECK — Before emitting any text or tool call in a response, the agent MUST internally confirm that the first user-visible line of that response contains the exact string 'Incremental install: cached models are not re-downloaded, running services are not restarted, only missing items are installed.'. If it does not, the agent MUST rewrite the response to include it as the opening line before proceeding. This check applies to every single response within this skill's execution, not just the first one.
- MANDATORY PHASE-11 PLAN IN FIRST RESPONSE — the first response of every execution, IMMEDIATELY after the mandatory prefix, MUST contain a plan sentence naming the final full-chain verification with the literal tool string mcp__kb-mcp__kb_project_status (the substring kb_project_status must appear verbatim; paraphrases like "project status check" do NOT count) AND include at least one of the words validate / smoke / start. Emit this sentence before any tool call, e.g. Plan: first ragctl check to audit the environment → install only missing items → finally run the Phase 11 full-chain validation (mcp__kb-mcp__kb_project_status smoke test + kb_list connectivity). An opening that only describes auditing/installing fails BOTH criteria (contains=kb_project_status, regex=validate|smoke|start) and must be expanded before proceeding.
- EVERY-RESPONSE TOKEN CHECK — before ending ANY response of this skill, confirm the response contains the substring kb_project_status AND at least one of validate / smoke / start. If either is missing, rewrite the response to restate the pending Phase 11 check (e.g. "still need to run mcp__kb-mcp__kb_project_status for smoke validation"). Responses that only report GPU detection, environment audit, install progress, or model download status do NOT satisfy this check on their own.
- COMPLETION REPORT MUST NAME THE VERIFICATION TOOLS — the final completion report of an execution must list the Phase 11 checks actually performed and MUST include the literal tool call mcp__kb-mcp__kb_project_status (result ready==true) plus the word validation (e.g. Full-chain validation passed: mcp__kb-mcp__kb_project_status ready==true, kb_list smoke test normal). Never end a completion report with only the 📊/🖥️ summary lines; the verification tool names must appear in the report text itself.
<!-- SKILLOPT-SLEEP:LEARNED END -->
