# RAG Knowledge Platform — API / Harness / Mechanism Audit

Date: 2026-09-13 · Auditor: DSH agent · Method: external HTTP E2E + live binary probes
Evidence: `.ui-audit/api/*.json`, `.ui-audit/e2e/results-*.json`, `.ui-audit/harness/*`

> **Concurrency note.** `backend/app/services/harness_registry.py` and
> `harness_specs.py` were modified at 11:50 by another session *while this audit
> ran*, and the backend process was restarted mid-audit. Harness findings below
> state the state I verified and flag what was fixed underneath me.

---

## 1. Verdict

| Area | State |
|---|---|
| Backend API (FastAPI, 121 ops) | **Well-designed and functional.** Self-describing, auth-gated, consistent error events. |
| Gateway API (Nuxt proxy, 124 routes) | **Incomplete and unsafe to integrate against.** 67 backend ops unreachable; unknown paths return `200 text/html`. |
| Harness layer (15 engines) | **Broad and largely correct.** 3 real defects found (1 already fixed mid-audit). |
| KB management | **Works end to end.** |
| Content retrieval | **Works**, 12/14 checks. 2 real defects (threshold, duplicate paths). |
| Experience mechanism | **Works on the backend; ~half its surface is unreachable from the gateway.** |
| Persona / SOUL | **Blocked at the gateway** (missing template dir); works on the backend. |
| Graph / meditation | **Work on the backend; most read endpoints unreachable from the gateway.** |

---

## 2. API design audit

### 2.1 The headline defect — SPA fallback swallows unknown API paths

Nuxt runs with `ssr: false`. Any `/api/**` path with no matching handler falls
through to the SPA and returns:

```
HTTP/1.1 200 OK
content-type: text/html
<!DOCTYPE html>…
```

**0 of 25 probed unknown/absent API paths returned a clean `404 application/json`.**
19 returned `200 text/html`.

Why this is the most serious finding: a caller **cannot distinguish**
"operation succeeded" from "this endpoint does not exist". Any integration that
checks `response.ok` will treat a missing endpoint as success and then fail
later on unparseable HTML. It also masks the 67 missing routes below.

**Fix:** add a Nitro catch-all `web/server/api/[...].ts` that returns
`404 {error, path}` for unmatched `/api/**`, or set `routeRules` so `/api/**`
never falls through to the SPA shell.

### 2.2 Gateway coverage

```
backend operations      : 121
gateway routes (files)  : 124
backend ops with NO gateway counterpart : 67   (55%)
```

Unreachable families (full list in `.ui-audit/api/surface-matrix.json`):

| Family | Missing |
|---|---|
| `/search/*` | `batch-index`, `index-document`, `stats`, `debug-paths`, `DELETE document`, `DELETE kb/{id}` |
| `/graph/*` | `document/related`, `document/enhanced`, `document-paths`, `central-documents`, `cross-kb-documents`, `search/{documents,kbs,tags}`, `agent-relation(s)`, `build-all`, `DELETE document`, `DELETE kb/{id}` |
| `/experience/*` | `drafts*`, `extract`, `reindex`, `sync`, `stale`, `dashboard`, `decay`, `global-search`, `stale-global` |
| `/soul/{id}/*` | `status`, `persona-docs`, `folder`, `learn`, `learn-all`, `evaluate`, `eval`, `export`, `reflect`, `checkpoint`, `rollback`, `calibrate`, `review-drafts`, `cognition-drafts`, `reward-history`, `train-rl`, `config`, `DELETE` |
| `/meditation/*` | `config`, `signals`, `feedback`, `harness-status`, `history/{run_id}` |
| `/mineru/*` | `status`, `restart` |
| other | `/health`, `/config/schema`, `/documents/split`, `/parse/file/vt*` |

The **backend is complete**; the gap is entirely in the proxy layer. kb-mcp and
the UI both go through this proxy, so these features are effectively
unavailable to every consumer.

### 2.3 Envelope inconsistency

| Endpoint | Shape |
|---|---|
| `/api/kb/catalog` | `{success, knowledgeBases:[…]}` |
| `/api/soul/list` | **bare array** `[{…}]` |
| `/api/graph/stats` | `{success, stats:{…}}` |
| `/api/graph/health` | `{success, health:{…}}` |
| `/api/health/stats` | **bare object** `{status, backend, storage, vector, graph}` |
| `/api/auth/me` | `{success, user:{…}}` |
| `/api/auth/verify` | `{valid, user, token}` |

No single envelope rule. Recommend `{success, data, error}` everywhere, or at
minimum a documented per-family convention.

### 2.4 Request-contract drift

Three different spellings for the same concept across one API:

| Endpoint | Param for "which KB" | Param for "which doc" |
|---|---|---|
| `GET /api/kb/document` | `kb_id` / `kbId` | `path` **or** `doc_path` / `doc_id` |
| `PATCH /api/kb/documents/update` | `kb_id`/`kbId` | `doc_path`/`docPath` only |
| `POST /api/kb/documents/move` | `target_kb_id` (no source kb) | `doc_path` |
| `GET /api/graph/documents-by-tag` | `kb_id` | – (needs `tag_name`, **not** `tag`) |
| `GET /api/graph/neighbors` | – | `node_id` + `node_type` (**not** `doc_path`) |
| `POST /api/v1/graph/agent-relation` | – | `doc_path` + `target_doc_path` (**not** `from_doc`/`to_doc`) |
| `POST /api/v1/search/batch-vector` | `kb_id` | `query_doc_paths` |

`coerceKbPayload` bridges snake↔camel but **not** `path`↔`docPath`, so the
natural round-trip `GET ?path=X` → `PATCH {path:X}` returns `404` then `400`.

### 2.5 Silent field drops and error masking

* **`POST /api/kb/documents/create` silently ignores `tags`.** Verified: created
  a doc with `tags:["thermal","ev"]`, response `200 success`, document stored
  with `metadata:{}` and no tags; `by-tag?tag=thermal` returned 0 until an
  explicit `PATCH …/tags`. Unknown fields should be rejected or echoed.
* **Backend 4xx is re-wrapped as `200 {success:false, error:"Backend unreachable: … 422"}`.**
  A *validation* failure is reported as a *connectivity* failure, with a success
  status code. Both the status and the message are wrong.
* **Silent rename on move collision**: moving `e2e-gamma.md` onto itself
  produced `e2e-gamma (1).md`. Reasonable behaviour, but undocumented and
  invisible to a caller tracking by name.

---

## 3. Harness support

### 3.1 Registry

15 engines registered (`mock`, `omp`, `opencode`, `codex`, `dsh`, `claude`,
`gemini`, `copilot`, `cursor`, `crush`, `goose`, `qwen`, `pi`, `hermes`,
`heuristic`). Live probe on this machine: **13 installed**.

| Engine | Installed | Version | Notes |
|---|---|---|---|
| mock | ✅ | – | in-process, always available |
| omp | ✅ | 18.1.15 | default; `omp models --json` returns 26 models |
| opencode | ✅ | 1.18.29 | |
| codex | ✅ | 0.154.0 | |
| dsh | ✅ | 0.1.5-rc.1 | ACP v1 verified against the live binary |
| claude | ⚠️ binary present | 2.1.267 | marked not-installed: `ANTHROPIC_API_KEY` absent |
| gemini | ✅ | 0.51.0 | |
| copilot | ✅ | 1.0.83 | |
| cursor | ❌ | – | `cursor-agent` not on PATH (see defect H1) |
| crush | ⚠️ binary present | v0.92.0 | runs but exits 1: *"No providers configured"* |
| goose | ⚠️ binary present | 1.50.0 | runs but exits 1: *"No provider configured"* |
| qwen | ✅ | 0.0.6 | |
| pi | ✅ | – | |
| hermes | ❌ | – | not installed (`pip install -e '.[acp]'` needed) |

**`installed: true` ≠ usable.** `probe_harness` only runs `--version`; crush and
goose report installed but fail at run time because no provider is configured.
Consider a `configured` field distinct from `installed`.

### 3.2 Runtime verification performed

| Check | Method | Result |
|---|---|---|
| omp event vocabulary | ran `omp -p --mode=json @file` | ✅ 116 events; `agent_end`/`turn_end`/`message_end`/`message_update` all present — parser correct |
| codex NDJSON | ran `codex exec --json -` | ✅ `turn.completed` + `item.completed{agent_message}` — parser correct |
| dsh ACP | drove `dsh --profile acp` over stdio | ✅ `initialize`→`session/new`→`session/prompt` works; emits **`agent_message_chunk`** |
| flags vs real `--help` | grepped captured help for all 8 CLIs | ✅ all platform flags exist (incl. claude `--system-prompt-file`, copilot `--output-format json`, dsh `--profile acp`) |
| omp model discovery | `omp models --json` | ✅ 26 models with context/cost metadata |

### 3.3 Defects found

**H1 — cursor binary name is wrong (open).**
`_CLI_COMMANDS["cursor"] = "cursor-agent"`. Official docs use the binary
**`agent`** (`agent --version`, `agent -p`); `cursor-agent` appears nowhere in
Cursor's CLI reference. `-m` is also undocumented (only `--model`).
→ https://cursor.com/docs/cli/reference/parameters

**H2 — omp `harness_models()` does not implement the documented discovery (open).**
The registry docstring says *"omp 走 `omp models --json` 动态发现"*, but
`harness_models()` returns `[""] + _STATIC_MODELS.get("omp", [])` → `[""]`.
`/api/meditation/models` does return the 26 live models, so discovery exists
elsewhere; the registry accessor and its docstring disagree.

**H3 — goose parser was broken (FIXED mid-audit by another session).**
The parser looked for `turn.completed`/`usage` and a top-level `role`; the real
`StreamEvent` enum emits `message`/`notification`/`error`/`complete` with the
role nested in `message`. Independent doc research flagged it; the file was then
patched (now reads `complete` + nested `message.role`). Not runtime-verified
here because goose has no provider configured.

**H4 — ACP discriminator was wrong (FIXED mid-audit).**
`run_acp_oneshot` matched `sessionUpdate == "agent_message_text"`. I drove the
live `dsh` binary: it emits **`agent_message_chunk`**. With the old code the
driver discarded every assistant message; the current file accepts
`agent_message_chunk`/`agent_message`/`agent_message_text`. Same driver serves
`hermes`. *(The stale docstring at the function header still says
`agent_message_text` — cosmetic, worth aligning.)*

### 3.4 Additional research findings (documentation, not runtime-verified)

* **opencode**: `--format json` is documented; plain-text stdout is not
  guaranteed to contain only the reply. Consider `--format json` or a tolerant
  parse.
* **copilot**: `--allow-all-tools` is documented as *required for programmatic
  use*; the platform now passes it only when `cfg["allow_all_tools"]` is set.
  Confirm the meditation/soul call sites enable it.
* **claude**: with `--json-schema` the structured value lands in
  `structured_output`, not `result`; `--bare` requires `--mcp-config` because it
  disables MCP auto-discovery.
* **pi**: skip the leading `{"type":"session",…}` header line (already handled).
* **URLs/docs to refresh**: omp → `can1357/oh-my-pi` (done), goose →
  `aaif-goose/goose` + `goose-docs.ai`, pi → `earendil-works/pi`.

---

## 4. Mechanism E2E results

All via external HTTP (gateway `:6789/api`, backend `:8771/api/v1`).

### 4.1 Knowledge-base management — works

Auth (login/token mint/list/revoke/verify/me, anonymous rejected 401), health,
config, `kb/create`, `kb/catalog`, document create/read/list/update/tags/move,
tag registry + hygiene analysis, reindex, MinerU status, preview. The only
friction was the `path` vs `docPath` asymmetry (§2.4).

### 4.2 Content-based retrieval — **12/14**

Working and verified:
* Semantic query with **zero lexical overlap** ("How do electric car battery
  packs stay cool while fast charging?") ranks the EV battery doc #1 at
  **0.714** — real semantic retrieval, not keyword matching.
* Domain-mismatch counter-example resistance holds (battery query beats the
  data-centre doc).
* Two-stage BM25→vector fusion works, scoped (**2 hits**) and cross-KB (**51 hits**).
* Chunk text is returned for content verification.
* Incremental `index-document`, batch-vector by doc path, vector deletion.

**R1 — `score_threshold` is not enforced (open).**
```json
{"query": "zzzz qqqq xxxx nonexistent-topic-9f3a"}
→ 1 hit, score 0.1197
config.yml: vector.score_threshold: 0.35
```
A sub-threshold hit is returned on the vector path, so junk queries can produce
citations.

**R2 — duplicate documents with mixed path separators (open).**
Two-stage results contain the same document twice:
`E2E-KB/e2e-alpha.md` and `E2E-KB\e2e-alpha.md` (41 hits, several duplicate
pairs). Inflates result counts and can render the same source twice.

**R3 — stale BM25 index after `/reindex` (open, high impact).**
Observed live: kb-scoped two-stage search returned **0 candidates for 8 of 9
KBs**, including the E2E KB, while global search returned results. After the
backend was restarted by the concurrent session, the same scoped query returned
**4 candidates**.

Root cause, located precisely:
* `two_stage_search_service._keyword_built` short-circuits
  `_ensure_keyword_index()` — the BM25 index is built once and never rebuilt.
* `invalidate_keyword_index()` is called from exactly one place:
  `api/routes/search.py:396`, inside **`/batch-index`**.
* **`/reindex` (search.py:407) never calls it.**
* Consequently: create/update documents → call `/search/reindex` (the obvious
  operation) → kb-scoped search stays empty until the process restarts.

### 4.3 Experience mechanism — backend works, gateway half-missing

Verified working: `init`, create (returns `{success, experience:{id,…}}`), list,
read, update, review, apply, keyword search, vector search, dashboard (tier
rollup P0/P1/P2), summary, stale check, `stale-global`, `global-search`.
Cross-KB global search returned 3 hits with credibility metadata.

Unreachable from the gateway (SPA-HTML): `drafts`, `drafts/{id}`,
`approve`/`reject`, `extract`, `reindex`, `sync`, `decay`, `feedback`,
`dashboard`, `stale`.
→ The **extract → draft → approve** lifecycle — the mechanism's core quality
gate — cannot be driven through the gateway at all.

### 4.4 Persona / SOUL — blocked at the gateway

**S1 — `POST /api/soul/init` fails with HTTP 500 (blocking, open).**
```
500 "persona template missing: soul-template/soul-definition.md"
```
The handler requires 4 template docs at
`storage/tree-file-system/soul-template/` (`soul-definition.md`, `values.md`,
`thinking-style.md`, `memory-conventions.md`). **That directory does not exist**
anywhere in the repo. Persona creation through the UI/gateway path is therefore
impossible on this deployment.

**S2 — gateway and backend disagree on the same operation.**
`POST /api/v1/soul/init {"name":"probe-b"}` → `400 invalid_soul_name`
(requires a `soul-` prefix). The gateway handler auto-prefixes instead. Two
implementations, two contracts, for one operation.

**S3 — `POST /api/soul/distill` drops the Authorization header.**
Gateway → `200 {"error":true,"error_type":"unauthorized","message":"认证失败: 缺少 token"}`.
Backend direct with the same token → `200 {"success":true,"task_id":"5f55112e7df8"}`.
The proxy does not forward auth on this route, so distillation never works from
the gateway.

**S4** — every `/api/soul/{id}/*` route (`status`, `persona-docs`, `config`,
`learn`, `evaluate`, `reflect`, `checkpoint`, `rollback`, `export`,
`train-rl`, …) is a **SPA-HTML fallback** at the gateway. The whole training
loop is unreachable from the UI even though the backend implements it.

### 4.5 Graph — backend works, gateway missing reads

Verified working: `stats` (14 nodes / 27 edges / 4 tags), `health`
(neo4j 5.20 available, schema v4), `build-kb`, `kb-overview` (tag distribution),
`document`, `neighbors`, `documents-by-tag`, agent-relation write.

Unreachable (SPA-HTML): `document/related`, `document/enhanced`,
`document-paths`, `central-documents`, `cross-kb-documents`,
`search/{documents,kbs,tags}`, `agent-relation`, `agent-relations/batch`,
`build-all`. These are exactly the endpoints the Graph Explorer UI calls.

### 4.6 Meditation / parse / system

Working: `status`, `history` (20 runs), `/v1/config`, `/v1/signals`,
`run` with the **mock** harness (dry-run produced a scored draft in 83 ms —
in-process path verified), `models` (26 live models), `harnesses`
(15 registered / 13 installed), `filesystem`, preview (returned real document
content), `system/clean/mineru-entries`, `/v1/mineru/status`
(available, running, port 53388).

Unreachable from the gateway: `/meditation/config`, `/meditation/signals`,
`/meditation/feedback`, `/mineru/status`, `/health`, `/config/schema`.

---

## 5. Prioritised remediation

| # | Severity | Issue | Where |
|---|---|---|---|
| 1 | **Critical** | Unknown `/api/**` returns `200 text/html` instead of 404 JSON | `web/server/` (add catch-all) |
| 2 | **Critical** | 67 backend ops have no gateway route; 4 whole mechanisms unreachable from UI/MCP | `web/server/api/**` |
| 3 | **Critical** | `soul/init` 500 — template dir missing | `storage/tree-file-system/soul-template/` |
| 4 | **High** | BM25 index never invalidated by `/reindex` → kb-scoped search empty until restart | `search.py:407` |
| 5 | **High** | `/api/soul/distill` does not forward Authorization | `web/server/api/soul/distill.post.ts` |
| 6 | **Medium** | `score_threshold` not enforced on the vector path | `vector_service` / `search.py:101` |
| 7 | **Medium** | Duplicate docs with `\` vs `/` in two-stage results | path normalisation |
| 8 | **Medium** | Backend 4xx masked as `200 {"error":"Backend unreachable"}` | gateway proxy helpers |
| 9 | **Medium** | `kb/documents/create` silently drops `tags` | `kb/documents/create.post.ts` |
| 10 | **Medium** | cursor harness uses binary `cursor-agent` / `-m` | `harness_registry.py:45`, `harness_specs.py` |
| 11 | **Low** | `path` vs `docPath` asymmetry | `kb-payload.ts` |
| 12 | **Low** | Envelope inconsistency (bare array / bare object / `{success,…}`) | all routes |
| 13 | **Low** | `installed` conflates "binary present" with "usable" | `harness_registry.probe_harness` |
| 14 | **Low** | omp model discovery documented but not implemented in `harness_models()` | `harness_registry.py:501` |
| 15 | **Low** | Stale docstring `agent_message_text` in `run_acp_oneshot` | `harness_specs.py:600` |

---

## 6. Reproduction

```powershell
python .ui-audit/e2e/probe_contracts.py      # API contract probe
python .ui-audit/e2e/surface_matrix.py       # 67-route coverage gap + HTML fallback
python .ui-audit/e2e/harness_probe.py        # real binaries, real stdout
python .ui-audit/e2e/verify_flags.py         # flags vs real --help
python .ui-audit/e2e/probe_acp.py            # dsh ACP frame dump
python .ui-audit/e2e/probe_keyword_index.py  # BM25 in isolation
python .ui-audit/e2e/t2_retrieval.py         # retrieval E2E  (12/14)
python .ui-audit/e2e/t3_mechanisms.py        # mechanisms E2E (33/49)
```
