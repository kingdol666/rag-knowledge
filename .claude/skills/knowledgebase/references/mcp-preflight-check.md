# ⚡ MCP Connectivity + Project Service Pre-Flight (Mandatory Contract)

> The **Pre-Flight** for all knowledge base skills (the first step before each skill's job, preceding its numbered steps such as A0 / Step 0 / Step 1).
> **If Pre-Flight has not passed, no KB operation may begin.**
> This file is the authoritative detailed spec; each skill's inline Pre-Flight section is its condensed executable version.

---

## Why This Step Is Mandatory

All 91 kb-mcp tools are forwarded over HTTP to the backend service. Two things are both required — **checking only one equals checking neither**:

1. **The kb-mcp MCP server is connected to the current Claude Code session** — loaded by Claude Code **at startup** per `.mcp.json`; it cannot be changed mid-session.
2. **The backend (FastAPI) + frontend (Nuxt) services are running and HTTP-healthy** — the actual forwarding target of the MCP tools.

- MCP not connected → tool calls fail immediately with `No such tool available`.
- Services not running → tools are callable, but every call reports the backend unreachable.

So both segments must be verified, and **one call can verify both at once**.

---

## Pre-Flight Procedure (one-probe double-check)

### 1. Single probe = connectivity + service status

Call `mcp__kb-mcp__kb_project_status` (no args).

| Outcome | Verdict | Next step |
|---|---|---|
| **Call succeeds** | Segment 1 passes (MCP connected — being callable means online) | Branch on the `ready` field |
| 　└ `ready == true` | backend AND web both HTTP-healthy → **ready** | → Smoke test |
| 　└ `ready == false` | Services offline | → **Case B** || **Error `No such tool available` / tool-not-found** | Segment 1 failed: MCP not connected to this session | → **Case C** |

### 2-A. Case B — Services not running (MCP online, services offline)

1. First call `mcp__kb-mcp__kb_project_status(scope="setup")`:
   - `ready_to_start == false` → project not installed. Report `problems` and `fix` (usually `ragctl setup`) to the user, **stop**, do not blindly retry.
   - `ready_to_start == true` → continue.
2. Silently bring the services up (**no asking the user, no opening a terminal**):
   - Graph / organize / cross-KB retrieval skills (depend on Neo4j): `kb_project_start(backend=true, web=true, neo4j=true, wait=true)`
   - Other skills: `kb_project_start(backend=true, web=true, wait=true)`
   - `wait=true` blocks until HTTP is healthy or ~45s timeout, then returns the final status block.
3. **Re-check**: call `kb_project_status` again.
   - `ready == true` → proceed to the smoke test.
   - Still `false` → read `ragctl logs backend` (or `backend/logs/desktop-stdout.log`), report the error to the user, **stop**; silent retry loops are forbidden.

> Startup is performed entirely by MCP tools; dev/prod behave identically and no terminal window ever pops up. stdout/stderr go to `backend/logs/desktop-stdout.log` and `web/logs/desktop-stdout.log` (same source as `ragctl logs` / the Tauri console). If MCP tools are unavailable, fall back to `Bash: node command/ragctl.js up` (equally silent, same-source logs).

### 2-B. Case C — MCP not connected to this session

The MCP server is loaded by Claude Code **at startup** and **cannot be reconnected mid-session**. Handling:

1. Diagnose: `Bash: node command/ragctl.js status` (or `ragctl status`) to see the status of backend/web/MCP respectively.
2. Notify the user: **"⚠️ The kb-mcp MCP server is not connected to the current session (Claude Code did not load `.mcp.json`). Please restart Claude Code so it auto-loads kb-mcp; the backend/frontend can be brought up silently with `ragctl up`."**
3. **Forbidden** to continue KB operations while MCP is not connected. Only with the user's **explicit consent** may you use the HTTP/terminal fallback per the [MCP-first principle exception clause](skill-trigger-contract.md#rule-5--mcp-first-principle-added-2026-07-13-enforced-library-wide), and you must state "MCP unavailable, fell back to the HTTP API".

### 3. Connectivity Smoke Test (mandatory)

After `ready == true` and **before real operations**, do one **lightweight read-only** MCP round trip to confirm MCP↔backend is truly reachable (not just the port, but returning data):

- General first choice: `mcp__kb-mcp__kb_list(lightweight=true)` (returns the KB catalog).
- Or: `mcp__kb-mcp__kb_tags_list()` (returns the tag vocabulary).
- Each skill may also use the first read-only probe of its own flow (`kb_search` for retrieval, `kb_graph_stats` for graph, etc.).

Real data returns (non-empty, non-error) → **Pre-Flight fully passed**, start the job.

---

## Quick Decision Table

| `kb_project_status` result | Verdict | Action |
|---|---|---|
| Success + `ready==true` | Ready | Smoke test → job |
| Success + `ready==false` | Services offline | `kb_project_status(scope="setup")` → `kb_project_start(wait=true)` → re-check → smoke test |
| `No such tool` | MCP not connected | Diagnose with `ragctl status` → notify the user to restart Claude Code → stop |

---

## Per-Skill Extra Notes

- **Graph / organize / cross-KB retrieval**: `kb_project_start` must carry `neo4j=true` (depends on Neo4j, requires Docker). The smoke test may also call `kb_graph_stats()` to confirm the graph database is online (check the `neo4j_available` field).
- **Parsing skills (ingest)**: once services are ready, also call `backend_status()` to confirm the **MinerU OCR engine is available**, otherwise `parse_doc(use_ocr=true)` will fail.
- **Init / Update (lifecycle skills)**: these two are install/ops skills; MCP connectivity is their **product or prerequisite**, not a precondition of their job:
  - **init**: after completing installation/registration, it **must** run this Pre-Flight (including the smoke test) to verify connectivity, as part of the "full-chain verification" phase.
  - **update**: **before** pulling updates it should pass this Pre-Flight (MCP must be online to use `kb_project_update(show_version=true)` for version comparison); **after** pulling, re-run this Pre-Flight to confirm services are restored.

---

## Violation Self-Correction

If you find you have already skipped this Pre-Flight and performed a KB operation:
1. **Stop immediately**.
2. Run this Pre-Flight retroactively; if the services were actually down / MCP was not connected, clean up any dirty state that may have been produced.
3. Explain to the user what was corrected.
