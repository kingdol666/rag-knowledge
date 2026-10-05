# ⚙️ Execution Model & Delegation Contract (Shared Reference)

> This file is the **single authoritative source** for the 14 knowledgebase skills: execution roles, delegation template, Pre-Flight, and the MCP-first principle.
> Individual skills no longer inline-duplicate this content; uniformly reference this file + [mcp-preflight-check.md](mcp-preflight-check.md) + [kb-architecture.md](kb-architecture.md).

---

## Three-Role Execution Model

```
User request
  │  hits a KB keyword
  ▼
① Dispatcher (skill://knowledgebase)
  │  Pure routing: read input → match scenario → delegate
  │  ⚠️ Strictly forbidden from executing any KB operation itself
  ▼
② Sub-Skill (skill://knowledgebase-<scenario>)
  │  Provides step flow, decision trees, quality gates, tool usage
  │  ⚠️ The skill itself never calls MCP tools directly
  ▼
③ Archival agent (delegated via the task tool)
     Autonomously confirms the scenario → reads kb-architecture.md → strictly executes the sub-skill steps
     All MCP tool calls happen only here
```

**Key invariants**:
- **Dispatcher routes only** — performs no KB operations whatsoever (add/delete/modify/query/index/graph/experience are all forbidden).
- **Skills do not execute** — a skill is a knowledge carrier and does not call MCP tools directly; execution authority belongs to Archival.
- **Archival is the sole executor** — after receiving a delegation it autonomously confirms the scenario and strictly runs every step and quality gate of the sub-skill.

**Exception**: `knowledgebase-init` and `knowledgebase-update` are **ops/install-type** skills, executed **directly by the main agent** (running the CLI, showing version comparisons) and **not delegated to Archival** — they involve no document CRUD.

---

## Delegation Template (mandatory for Archival-delegated skills)

When an Archival-delegated skill delegates, use the `task` tool:

```
task(
  tasks=[{
    "agent": "archival",
    "name": "KB-<Scenario>",
    "task": "[Scenario: <label>]\n⭐ MUST-READ skill://knowledgebase/references/kb-architecture.md before operating\n\nUser request: <original request>",
    "effort": "med"
  }],
  context="RAG Knowledge Platform — MCP tools via kb-mcp, backend on :8765"
)
```

- The `task` field must contain: **scenario label** + **mandatory architecture read reference** + **the user's original request**.
- Each `task(tasks=[{"agent":"archival",...}])` runs in an **independent context** — Archival cannot see the main dispatcher's history. Multi-step combined tasks must **explicitly pass** key state in the prior delegation's prompt (KB id / document paths / changed items / issues found).
- **Claude Code equivalent**: `Agent(subagent_type="archival", prompt=...)`, auto-adapted by OMP.

### Combined Tasks (≥2 scenarios): Delegation Boundaries

| Phase | Action | Output contract |
|------|------|---------|
| Confirm before routing | Confirm the full routing order + each step's sub-skill with the user | "Will execute A→B→C" |
| Carry context between delegation steps | Every Archival delegation prompt **explicitly attaches prior outputs** | `[Scenario B: Search] Prior ingest complete: KB=<name>, document=<path>. Now retrieve: <query>` |
| Report immediately after each step | Report as soon as each step completes; confirm before moving to the next | Silent consecutive execution forbidden |
| Failure isolation | If a step fails: continue with independent later scenarios; if there are dependencies, stop and ask the user | "Ingest failed. Search does not depend on it — continue?" |

> **Combined scale cap**: at most 3 skills combined per session (4+ skill combos have a 100% historical failure rate).

---

## Pre-Flight (mandatory first step of every job)

**No KB operation is allowed until Pre-Flight passes.** Full procedure in [mcp-preflight-check.md](mcp-preflight-check.md):

1. **One-probe double-check**: `mcp__kb-mcp__kb_project_status` (no args) → success = MCP connected; read the `ready` field = services healthy.
2. `ready==false` → silently `kb_project_start(wait=true)` (add `neo4j=true` for graph/organize/cross-KB jobs) → probe again.
3. `No such tool` → MCP is not connected to this session: notify the user to restart Claude Code and stop the job.
4. **Smoke test**: once `ready==true`, run `kb_list(lightweight=true)` to confirm MCP↔backend actually returns data.

---

## MCP-First Principle (mandatory across the whole library)

When MCP tools are connected, **all KB operations MUST go through the `mcp__kb-mcp__*` tools**:

| ❌ Forbidden | ✅ Required |
|---------|---------|
| Operating the KB with `curl`/`wget`/`httpx` terminal commands | `mcp__kb-mcp__kb_*` tools |
| Calling the HTTP API via `python -c` | `mcp__kb-mcp__parse_doc` tool |
| Hardcoding API URLs in Bash | MCP guarantees atomic operations + an audit trail |

**Exception**: only when MCP is explicitly unavailable AND the user confirms, may you use the terminal/HTTP fallback, and you must state "MCP unavailable, fell back to the HTTP API". `init`/`update` go through the `ragctl` CLI and are not subject to this constraint. Full clauses in [skill-trigger-contract.md](skill-trigger-contract.md), Rule 5.

---

## Cross-Skill Reference Path Conventions

The 14 skills ship as a single plugin package (see `.claude-plugin/plugin.json`) and always coexist in the same directory. Reference **shared references** with relative paths:

```
../knowledgebase/references/kb-architecture.md        ← 5-layer data model + consistency invariants + 94-tool map
../knowledgebase/references/execution-model.md         ← this file
../knowledgebase/references/mcp-preflight-check.md     ← full Pre-Flight procedure
../knowledgebase/references/skill-trigger-contract.md  ← trigger contract + five mandatory rules
```

Reference **ingest-private references** (tag/description/sub-KB rules): `../knowledgebase-ingest/references/<file>.md`.
