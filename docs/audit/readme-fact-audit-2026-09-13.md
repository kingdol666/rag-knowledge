# READ-ONLY Fact Audit — `README.md` + `README-zh.md`

> Audit date: 2026-09-13 · **No files were edited.** Verification scripts written under `.audit/` only.
> Source of truth: `kb-mcp/server.py`, `config.yml`, `command/ragctl.js`, `web/server/services/`,
> `backend/app/api/`, live services at `127.0.0.1:8770/8771/6789`, and recorded artefacts.
> Live probes used a proxy-bypassing opener (`ProxyHandler({})`) as instructed.

---

## 1. Counts

| CLAIM | VERDICT | EVIDENCE |
|---|---|---|
| 94 MCP tools (EN:13,20,92,116,363,773; ZH:13,19,89,113,357) | **TRUE** | 94 `@mcp.tool()` decorators, 94 unique fn names — `.audit/count_tools.py` parsing `kb-mcp/server.py` |
| Category partition `lifecycle 4 / KB CRUD 4 / doc 9 / search 4 / vector 6 / fs 3 / graph 11 / experience 26 / tags 4 / parse 3 / SOUL 20` (EN:781-786) | **TRUE** | Every one of the 11 buckets matches exactly; sums to 94; disjoint — same script |
| 11 graph tools (EN:114; ZH:111) | **TRUE** | 11 `kb_graph_*` functions |
| 26 experience tools (EN:784) | **TRUE** | 26 `experience_*` functions |
| 20 SOUL tools (EN:786; ZH:115) | **TRUE** | 20 `soul_*` functions |
| **19 Agent Skills** (EN:13,21,92,117; ZH:13,20,89,114) | **FALSE** | **20** directories under `.claude/skills/`, **all 20 contain `SKILL.md`** — `Get-ChildItem .claude/skills -Directory` |
| E0–E12 lifecycle (EN:12,115) | **TRUE** | 13 distinct stages E0…E12 in `.claude/skills/knowledgebase-experience/SKILL.md` |
| 5-layer storage (EN:39,709-717; ZH:38) | **TRUE** | L1–L5 table matches: `.tree-fs.json`, `.knowledge-base.yml`, `storage/tree-file-system` (22 subdirs), ChromaDB, Neo4j |
| Nine Pillars (EN:109-121) | **TRUE** | Exactly 9 rows |
| Four install methods (EN:446-449) | **TRUE** | 4 columns, all backing files exist |
| Four interfaces (EN:549) | **TRUE** | Web UI / API Docs / CLI / Agent |
| 0–8 content rubric (EN:174-181; ZH:~170) | **TRUE** | Rubric table spans 0–2 / 3–4 / 5–6 / 7–8 |
| QDCVR "**6-step** retrieval pipeline" (EN:135; ZH:132) | **DISCREPANCY** | README diagrams 6 boxes. `CLAUDE.md` documents **Step 0→Step 6 (7 steps)** incl. Intent Recognition; the paper uses **7 stages**. The README diagram omits intent recognition entirely |
| "4 parallel paths" (EN:148; ZH:145) | **DISCREPANCY** | `CLAUDE.md` "Multi-Strategy Enterprise Search" documents **"Parallel 3-path recall"** (Path A/B/C). README says 4 |

## 2. Performance / quality numbers

| CLAIM | VERDICT | EVIDENCE |
|---|---|---|
| Flat vector **P@5 0.590, FPR 12.0%, 84 ms** (EN:193; ZH:189) | **UNVERIFIABLE** | Only artefact containing both 0.590 and 0.630 is `benchmark-web/backend/results/v4/benchmark_report.json` — a **withheld artefact with no producing script**. The *traceable* in-house run (`module_b_retrieval_r2.json`) gives **P@5 0.21 (staged) / 0.20 (vector), latency 1.33 s / 0.081 s** — the README's numbers **contradict** the reproducible data |
| QDCVR Domain **P@5 0.630, FPR 3.0%, 38 ms** (EN:194; ZH:190) | **UNVERIFIABLE** | Same source; contradicted by `module_b` |
| Cross-domain adversarial **0.00%** (EN:195; ZH:191) | **UNVERIFIABLE** | No artefact records a 0.00% FPR |
| "**0%** (vs **50–77%** for flat vector)" (EN:197; ZH:193) | **UNVERIFIABLE** | No artefact; the comparable traceable figure is 73.0% for flat retrieval (withheld family) |
| "6 domains (20 adversarial queries)" (EN:191; ZH:185) | **UNVERIFIABLE** | `docs/paper/benchmark/datasets/queries.json` holds **50** entries, **none with a `domain` field** |
| "5 methods × 50 queries × 157 docs" (EN:799; ZH:734) | **UNVERIFIABLE** | Traces only to `cikm_summary.json` (`n_queries 50, n_docs 157`) — **no producer script** |
| "60 / 60 passed (`tmp/test_full_smoke.py`)" (EN:414) | **UNVERIFIABLE** | `tmp/test_full_smoke.py` **does not exist** |
| "139 backend tests, 139 passed" (EN:415; ZH:409) | **STALE** | `backend/tests` now contains **233** `def test_` functions |
| "57 MCP-tool E2E tests, 57 passed" (EN:416; ZH:410) | **STALE** | `kb-mcp/tests` contains **39** test functions |
| "106 backend endpoints" (ZH:371,383) | **STALE** | Live `/openapi.json`: **114 paths / 121 operations** |
| "122 web routes" (ZH:371,384) | **STALE** | **124** `.ts` route files under `web/server/api` |
| "rate limit 600 req/60s" (EN:408,749) | **TRUE** | `config.yml`: `window_sec: 60, max_requests: 600` |
| "~5 GB disk · BGE-M3 ~2.2 GB" (EN:545) | **UNVERIFIABLE** | No measurement recorded |
| "persona Q&A takes ~7 min" (EN:419) | **UNVERIFIABLE** | No measurement recorded |

*No index-coverage percentage appears in either README.*

## 3. Architecture claims

| CLAIM | VERDICT | EVIDENCE |
|---|---|---|
| dev: backend 8770 / web 6789 (EN:679,730,731) | **TRUE** | `config.yml:21-22` |
| prod: backend 8001 / web 3000 (EN:679,731) | **TRUE** | `config.yml:26-27` |
| Backend at `http://localhost:8770` (EN:369,388) | **TRUE** | Live: 8770 listening, `/api/v1/health` → 200. **Note:** a *second* backend also runs on **8771** (undocumented in both READMEs) |
| **"Auth is off for trusted networks"** (EN:407) | **FALSE** | `config.yml` → `server.auth.enabled: true`. Live: `GET /api/v1/kb/list` → **401**, `GET /api/kb/catalog` → **401**. OpenAPI declares **116 of 121 operations** require `bearerAuth`; only 5 are public |
| README's 3 curl examples work as printed (EN:391-403) | **FALSE** | No `Authorization` header on any of them; all three endpoints are non-public → **401** |
| Browser → Nuxt (proxy) → FastAPI → file I/O (EN:685-707) | **TRUE** | Matches `web/server/api/` route layout and `backend/app/api/` |
| `.tree-fs.json` global tree index (EN:701,714) | **TRUE** | Used in `web/server/services/tree-file-system-service.ts`, `kb-search-service.ts` |
| `.knowledge-base.yml` document registry (EN:702,715) | **TRUE** | `web/server/services/knowledge-base-yaml-service.ts` |
| L1 path `storage/tree-file-system/{KB}/{doc}.md` (EN:713) | **TRUE** | Directory exists, 22 subdirs |
| Neo4j `bolt://127.0.0.1:7687` (EN:705) | **TRUE** | Port 7687 listening |
| ChromaDB + BGE-M3 1024-dim (EN:704,716) | **TRUE** | `config.yml` embedding `BAAI/bge-m3`; 26 collections live |
| Writes→API, reads→direct file (EN:719; ZH:657) | **TRUE** | Matches service implementations |
| L5 graph = Document/Tag/KB nodes (EN:717) | **PARTIAL** | Live `/api/v1/graph/stats`: nodes 16, edges 56, docs 14, kbs 2, **`tag_count: 0`** |
| `soul` + `mineru` sections live in `backend/config.yml` (EN:767) | **TRUE** | Both present (`mineru:` L5, `soul:` L16) |
| Documented endpoints `/api/kb/create`, `/api/kb/documents/create`, `/api/v1/search/two-stage` | **TRUE** | Route files exist; `/api/v1/search/two-stage` present in live OpenAPI |

## 4. Install / CLI claims

| CLAIM | VERDICT | EVIDENCE |
|---|---|---|
| 19 top-level `ragctl` commands (EN:664-676) | **TRUE** | All present in `command/ragctl.js`: setup, up, status, down, start, stop, restart, logs, model, mineru-model, clean, backup, restore, meditation, version, update, soul, desktop, ui |
| soul subcommands `distill/learn-all/train-rl/review-cognition/harness/router/reflect` (EN:674-675) | **TRUE** | All present in `command/ragctl.js` |
| Flags `--appmode --no-neo4j --port-backend --port-web --tail --lines --check --yes --restart --all --dry-run` (EN:665-673) | **TRUE** | All found in `command/ragctl.js` |
| `node scripts/install_omp.cjs` (EN:474) | **TRUE** | `scripts/install_omp.cjs` exists |
| `/plugin marketplace add kingdol666/rag-knowledge` (EN:457) | **TRUE** | `.claude-plugin/marketplace.json` + `plugin.json` exist |
| `cp -r ~/rag-knowledge/.claude/skills/knowledgebase* ~/.claude/skills/` (EN:489) | **TRUE** | 14 `knowledgebase*` dirs present |
| `./ragctl setup && ./ragctl up` (EN:504) | **TRUE** | Both subcommands exist |
| Cross-platform Win/Linux/macOS (EN:19; ZH:19) | **TRUE** | `backend/pyproject.toml`: `required-environments` = win32/linux/darwin |
| Python 3.12 (EN:541; ZH) | **TRUE** | `requires-python = ">=3.12,<3.13"` |
| Node ≥ 18 / uv ≥ 0.7 (EN:539-540) | **UNVERIFIABLE** | No `engines` field in `web/package.json`; no uv pin found |
| `curl http://localhost:8770/api/v1/health` (EN:369) | **TRUE** | Returns `{"status":"healthy",...}` |

## Note on `backend/app/api/openapi.py` (untracked, written by another agent)

It **does not add or remove endpoints** — it replaces `app.openapi` with a
contract-accurate generator. It (a) injects an `ApiError` component schema,
(b) declares a `bearerAuth` security scheme, (c) marks the 5 `PUBLIC_PATHS`
(`/`, `/health`, `/api/v1/health`, `/api/v1/auth/{register,login,verify}`) as
`security: []` and everything else as `[{"bearerAuth": []}]`, (d) adds standard
error responses, (e) supplies 12 tag descriptions. **It does not change the
documented endpoint surface, but it does make the security model explicit — which
is exactly what the README's "Auth is off" sentence contradicts.** It is the
authoritative statement that auth is ON.

---

## MUST FIX

1. **`Auth is off for trusted networks`** (EN:407-408)
   *Current:* "Auth is off for trusted networks (rate limit 600 req/60s) — put an API gateway in front before exposing publicly."
   *Correct:* "Auth is **enabled by default** (`server.auth.enabled: true`); all endpoints except `/api/v1/health` and `/api/v1/auth/*` require `Authorization: Bearer <token>`. Rate limit 600 req/60s."
   *Evidence:* `config.yml` `auth.enabled: true`; live `GET /api/v1/kb/list` → 401; `backend/app/api/openapi.py` marks 116/121 operations bearer-protected. This is a **security-relevant** false claim.

2. **The three curl examples** (EN:391-403)
   *Current:* three unauthenticated `curl` calls.
   *Correct:* prepend a login step and add `-H "Authorization: Bearer $TOKEN"` to each.
   *Evidence:* all three endpoints return **401** unauthenticated.

3. **`19 Agent Skills`** — 5 occurrences (EN:13, 21, 92, 117; badge EN:21; ZH:13, 20, 89, 114)
   *Current:* "19 Agent Skills" / "Skills-19" badge / "🎯 **19 Agent Skills**".
   *Correct:* **20 Agent Skills** (badge `Skills-20`).
   *Evidence:* 20 directories in `.claude/skills/`, all 20 with `SKILL.md`.

4. **The benchmark table** (EN:191-197; ZH:185-193) — *highest-severity item*
   *Current:* "In benchmark tests across 6 domains (20 adversarial queries): Flat vector P@5 0.590 / FPR 12.0% / 84 ms; QDCVR Domain P@5 0.630 / FPR 3.0% / 38 ms; Cross-domain FPR 0.00%… **0%** (vs 50–77%)".
   *Correct:* either **delete the table**, or replace with the traceable in-house figures — `module_b_retrieval_r2.json` (20 queries): staged P@5 **0.21**, Hit@1 **0.80**, R@5 **0.908**, latency **1.33 s**; dense vector P@5 **0.20**, Hit@1 **0.90**, R@5 **0.917**, latency **0.081 s**. Note the README's QDCVR latency (38 ms) is **35× faster** than the reproducible measurement (1.33 s).
   *Evidence:* the only artefact holding 0.590/0.630 is `benchmark-web/backend/results/v4/benchmark_report.json`, which **has no producing script** in the repo (417 code files searched); the same family was already withheld from the CIKM paper for this reason.

5. **`60 / 60 passed (tmp/test_full_smoke.py)`** (EN:414)
   *Current:* points to `tmp/test_full_smoke.py`.
   *Correct:* remove or re-run and cite the actual harness.
   *Evidence:* `tmp/test_full_smoke.py` does not exist.

6. **`139 backend tests`** (EN:415; ZH:409)
   *Current:* "139 tests — 139 passed, 0 failed".
   *Correct:* **233** test functions currently in `backend/tests`.
   *Evidence:* count of `def test_` across `backend/tests/*.py`.

7. **`57 MCP-tool E2E tests`** (EN:416; ZH:410)
   *Current:* "57 MCP-tool E2E tests — 57 passed".
   *Correct:* **39** test functions in `kb-mcp/tests`.
   *Evidence:* count of `def test_` across `kb-mcp/tests/*.py`.

8. **`106 backend endpoints`** (ZH:371, 383)
   *Current:* "106 个端点" / "（106 endpoints）".
   *Correct:* **114 paths / 121 operations**.
   *Evidence:* live `GET /openapi.json`.

9. **`122 web routes`** (ZH:371, 384)
   *Current:* "122 个路由".
   *Correct:* **124**.
   *Evidence:* `.ts` route files under `web/server/api`.

10. **`5 methods × 50 queries × 157 docs`** (EN:799; ZH:734)
    *Current:* cited as a shipped v2.2 achievement.
    *Correct:* remove or mark unverified.
    *Evidence:* traces only to `cikm_summary.json`, which has no producer script.

11. **QDCVR "6-step" vs 7 stages** (EN:135; ZH:132) — *consistency*
    *Current:* "a 6-step retrieval pipeline"; diagram starts at "① KB Selection".
    *Correct:* either state "7 stages (Step 0 intent recognition → Step 6 synthesis)" to match `CLAUDE.md`, or explicitly label the diagram a simplification.
    *Evidence:* `CLAUDE.md` "Agentic-First Retrieval Pipeline" lists Step 0–6; the intent-recognition stage has no README equivalent.

12. **"4 parallel paths"** (EN:148; ZH:145)
    *Current:* "BM25 → Vector → Tag-semantic → Graph (4 parallel paths)".
    *Correct:* reconcile with `CLAUDE.md`, which documents "Parallel **3-path** recall" (Path A: agentic KB judgment; Path B: `kb_search_two_stage`; Path C: `kb_search_vector`).
    *Evidence:* `CLAUDE.md` → "Multi-Strategy Enterprise Search".

---

### Not defects (checked, fine)

Nine Pillars · 5-layer storage · E0–E12 · all 94 MCP tools and all 11 category
counts · 11 graph / 26 experience / 20 SOUL tools · dev+prod port pairs · four
install methods (all backing scripts exist) · all 19 `ragctl` commands and all 11
flags · cross-platform toolchain · rate limit 600/60s · storage filenames and
paths · write/read asymmetry · documented REST endpoints · the
`.claude-plugin` marketplace manifest.

### Residual uncertainty

- The **live deployment is mid-drift**: 14 top-level KBs, 26 vector collections,
  5,835 chunks, graph = 16 nodes / 56 edges / 14 docs / 2 KBs, and **two** backend
  processes (8770 *and* 8771). Neither README states a KB or document count, so
  nothing to correct — but any number added later must be pinned to a dated
  snapshot.
- `Node ≥ 18` and `uv ≥ 0.7` are stated but not machine-checkable from the repo.
- `.ui-audit/` and other untracked files kept appearing during this audit,
  indicating **a concurrent writer in this working tree**; counts involving live
  state may shift between runs.
