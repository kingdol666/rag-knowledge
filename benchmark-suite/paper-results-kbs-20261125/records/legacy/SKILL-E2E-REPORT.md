# SKILL E2E REPORT — Live Test of All Knowledge-Base Skills

- **Date:** 2026-09-24 (local)
- **Platform:** backend `http://localhost:8771`, web `http://localhost:6789`, MinerU local mode (pid 72108, port 62329)
- **MCP channel:** project's own stdio client (`benchmark-suite/scripts/lib.py::McpClient` → `uv run --directory kb-mcp python server.py`), 94 registered tools verified
- **Test KBs:** `E2E-SkillTest-1457` (`95f4e9a1-b24d-43c1-b94d-04c55d90b5d1`), `E2E-SkillTest-Dst-1457` (`c2e2bf92-db86-48f5-96f8-7ac9b9931f67`)
- **Total real tool calls:** 109 (see `.e2e/skilltest/calls.jsonl` for the raw record)
- **Distinctive fact used as retrieval anchor:** `ZQ-7731` resonator, quality factor `8,314,159` at `42.7 K`
- **Pre-existing KBs:** read-only access only; none modified (final `kb_list` shows the original 10 KBs, unchanged)

---

## 1. Summary Table

| # | Skill | Operations exercised (real calls) | Pass/Fail | Evidence (tool + key result) | Latency |
|---|-------|-----------------------------------|-----------|------------------------------|---------|
| 1 | `knowledgebase-init` | `kb_project_status(scope="runtime")`, `backend_status()` | **PASS** | `ready=true`; backend/web/neo4j UP, mineru up; `backend_health.status="healthy"` | 3.48s / 0.92s |
| 2 | `knowledgebase` (dispatcher) | `kb_list(lightweight=True)` | **PASS** | `{"success":true,"count":10,...}` — catalog reachable | 0.54s |
| 3 | `knowledgebase-ingest` | `kb_create`×2 → `kb_doc_create` (2942-char md) → `kb_index_document` → **A6-V probe** `kb_search_vector` | **PASS** | index: `collection=kb_95f4e9a1-…`, `total_chunks=9`; probe hit **score 0.778**, `chunk_index=2` = the "Distinctive Measured Fact" section | 0.29/0.26/0.87/1.05/0.29s |
| 4 | `knowledgebase-list` | `kb_get_documents(lightweight=True, kb_id=<test>)` | **PASS** | `{"count":1,"catalog":[{"doc_path":"E2E-SkillTest-1457\\zephyr-quartz-resonator.md",...}]}` | 0.54s |
| 5 | `knowledgebase-search` | `kb_search_vector` + `kb_search` + `kb_search_two_stage` + `kb_search_stats` | **PASS** (1 weakness) | vector hit **0.752**; two-stage hit **0.655**; stats `chunk_count=9`; `kb_search` returned only unrelated docs (see D5) | 1.22/0.31/0.30/0.01s |
| 6 | `knowledgebase-manage` | `kb_doc_update_meta` (rename) → `kb_doc_move` (→dst) → move back; `kb_get_documents` verify; `kb_reindex` | **PASS** (1 defect found) | rename→`…-renamed.md`; move→`E2E-SkillTest-Dst-1457\…`; move-back→`E2E-SkillTest-1457\…`; src count 1→0→1, dst 0→1→0; **stale-chunk defect D1** | 0.53/0.27/0.27s |
| 7 | `knowledgebase-organize` | `kb_find_duplicates` → `kb_tags_list` → `kb_doc_update_tags` → `kb_doc_get_by_tag` → `kb_batch_index` | **PASS** (D1 visible) | `kb_find_duplicates` → 1 near-dup group **sim 0.9738** (self, old path); `kb_doc_get_by_tag` count **1**; `kb_batch_index` indexed 1, 9 chunks | 1.28/0.27/0.27/0.27/0.37s |
| 8 | `knowledgebase-verify` | `kb_get_documents` vs `kb_doc_read` vs `kb_search_stats` (three-way) | **PASS** (inconsistency found) | docs count **1**, read OK, stats `chunk_count=18` → **inconsistent** (see D1); vector probe shows every chunk duplicated under old+new path | 0.75/0.27/0.28s |
| 9 | `knowledgebase-graph` | `kb_graph_build` (poll `kb_task_status`) → `kb_graph_stats` → `kb_graph_document` → `kb_graph_kb_overview` | **PASS** | `neo4j_available=true`; edge_count **4675→4679** after build; doc node found with 4 tags; overview `doc_count=1` | 0.51/0.00/0.02/0.01/0.01s |
| 10 | `knowledgebase-experience` | `experience_dashboard` → `experience_search_global` → `experience_list` → `experience_extract` (prepare + heuristic) | **PASS** | dashboard total 0; search 0 ("不编造"); extract prepare `docs_to_extract=1`; heuristic dry_run `total_candidates=1` | 0.51/0.38/0.01/0.01/0.01s |
| 11 | `knowledgebase-experience-summarize` | `experience_drafts_list` → (`draft_read`/`draft_approve` N/A) | **PARTIAL** | `{"count":0,"drafts":[]}` — **no draft existed**, so read/approve could not be exercised | 0.50s |
| 12 | `knowledgebase-batch` | `kb_doc_batch_delete` → confirm `kb_get_documents` | **PASS** | `{"total":1,"successful":1,"failed":0}`; docs count 0; `chunk_count=0` | 0.50/0.54/0.01s |
| 13 | `knowledgebase-update` | `kb_project_status(show_version=True)` + `kb_project_update(show_version=True)` | **FAIL** | `kb_project_update` → `{"success":false,...,"error":"ragctl version --json timed out after 30s","via":"fallback"}`; `kb_project_status` ignored `show_version` (D2/D3) | 3.44s / 30.10s |
| 14 | `soul` | `soul_list()` | **PASS** | returns list with 1 persona `soul-e2e-tester-024115` (kb_scope `["*"]`) | 0.49s |
| 15 | `soul-rag` | `soul_list` + `soul_router` + `soul_qdcvr_ask` | **PARTIAL** | router `top1=aa0fec78-…, route_confidence=0.62`; `soul_qdcvr_ask` launched async (task `5765ea09e8d7`) — **still running >6 min at write time** | 0.01/27.72/0.005s |
| 16 | `butian` | `kb_list` (read-only landing check) | **PASS** | distillation lands as a KB: persona KB `soul-e2e-tester-024115` present in catalog | 0.54s |

**Tally:** 13 PASS, 2 PARTIAL (#11, #15), 1 FAIL (#13). 1 real defect class (D1) + 3 secondary defects (D2/D3/D4) + 1 weakness (D5).

---

## 2. Per-Skill Detail (exact calls + real returned values, trimmed)

### #1 `knowledgebase-init` — PASS
- `kb_project_status({"scope":"runtime"})` → `{"success":true,"ready":true,"app_mode":"dev","services":{"backend":{"port":8771,"http_ok":true,"detail":"HTTP 200","pid":24388},"web":{"port":6789,"http_ok":true,"detail":"HTTP 200","pid":72132},"neo4j":{"bolt_listening":true,"http_listening":true},"mineru":{"available":true,"detail":"HTTP 200"}},"summary":"backend UP(:8771) · web UP(:6789) · neo4j UP(:7687) · mineru up"}`
- `backend_status({})` → `{"backend_health":{"status":"healthy","vector":{"ready":true,"embedding_available":true}},"mineru_status":{"available":true,"running":true,"mode":"local","local":{"installed":true,"running":true}}}`
- Note: the skill's "learned preferences" block demands a literal output prefix; **not honored** (see Observation O1).

### #2 `knowledgebase` (dispatcher) — PASS
- `kb_list({"lightweight":true})` → `{"success":true,"count":10,"catalog":[…]}`. Catalog reachable → dispatcher Step-1 smoke passes. (Dispatcher's own rule forbids it from executing KB ops; `kb_list` is its documented pre-flight smoke, so this is in-contract.)

### #3 `knowledgebase-ingest` — PASS
- `kb_create({"name":"E2E-SkillTest-1457",…})` → `{"success":true,"knowledgeBase":{"kb_id":"95f4e9a1-b24d-43c1-b94d-04c55d90b5d1",…}}`
- `kb_create({"name":"E2E-SkillTest-Dst-1457",…})` → `{"success":true,"knowledgeBase":{"kb_id":"c2e2bf92-db86-48f5-96f8-7ac9b9931f67",…}}`
- `kb_doc_create({kb_id, name:"zephyr-quartz-resonator.md", content:<2942 chars>, description, tags})` → `{"success":true,"source_chars":2942,"document":{"id":"f394ccb9-a022-4df9-a1e7-b6e5bf686955","path":"E2E-SkillTest-1457\\zephyr-quartz-resonator.md",…}}`
- `kb_index_document({kb_id, doc_path})` → `{"success":true,"vector_index":{"collection":"kb_95f4e9a1-b24d-43c1-b94d-04c55d90b5d1","total_chunks":9,"embedding_model":"bge-m3","graph_doc_id":"doc::E2E-SkillTest-1457/zephyr-quartz-resonator.md"}}`
- **A6-V probe** `kb_search_vector({"query":"quality factor of the Zephyr-Quartz ZQ-7731 resonator at 42.7 K","kb_id":kb1,"top_k":5,"score_threshold":0.0})` → top hit `{"content":"## Distinctive Measured Fact … quality factor of 8,314,159 at an operating temperature of 42.7 K …","score":0.7778,"doc_path":"E2E-SkillTest-1457/zephyr-quartz-resonator.md","chunk_index":2}` — **hit confirmed**.
- Not exercised: `parse_doc` / `kb_doc_save_parsed` / A2.5 split gate (see Limitations).

### #4 `knowledgebase-list` — PASS
- `kb_get_documents({"kb_id":kb1,"lightweight":true})` → `{"success":true,"count":1,"catalog":[{"doc_path":"E2E-SkillTest-1457\\zephyr-quartz-resonator.md","name":"zephyr-quartz-resonator.md","description":"Zephyr-Quartz ZQ-7731 cryogenic BAW resonator calibration: 5-stage protocol, Q=8,314,159 at 42.7 K, error budget 3.3 ppb, 90-day field maintenance. In English."}]}`

### #5 `knowledgebase-search` — PASS (with weakness D5)
- `kb_search_vector({"query":"What quality factor does the ZQ-7731 resonator reach at 42.7 K?","kb_id":kb1,"top_k":10,"score_threshold":0.35,"balance_kbs":true})` → top hit `score 0.7525`, same "Distinctive Measured Fact" chunk.
- `kb_search({"query":"ZQ-7731 quality factor","top_k":5})` → `{"count":5,"hits":[{"kbName":"经济与社会","docName":"economics__1901.03951__inequality-mobility-and-the-financial-accumu.md (part 1 of 3).md","score":4}, …]}` — **test doc not present**; hits matched substrings ("quality"⊂"inequality"). See D5.
- `kb_search_two_stage({"query":"Zephyr-Quartz resonator calibration quality factor","kb_id":kb1,"stage1_top_k":20,"stage2_top_k":5,"enable_graph_expansion":true,"score_threshold":0.30,"balance_kbs":true})` → `stage1.candidates=[{"doc_path":"E2E-SkillTest-1457/zephyr-quartz-resonator.md","score":1.899,"source":"keyword"}]`, `stage2.results[0].score=0.6549` — **hit confirmed**.
- `kb_search_stats({"kb_id":kb1})` → `{"stats":{"collection":"kb_95f4e9a1-b24d-43c1-b94d-04c55d90b5d1","chunk_count":9}}`

### #6 `knowledgebase-manage` — PASS (defect D1 surfaced here)
- `kb_doc_update_meta({"kb_id":kb1,"doc_path":"E2E-SkillTest-1457\\zephyr-quartz-resonator.md","name":"zephyr-quartz-resonator-renamed.md"})` → `{"success":true,"document":{"id":"f394ccb9-…","path":"E2E-SkillTest-1457\\zephyr-quartz-resonator-renamed.md",…}}`
- `kb_doc_move({"doc_path":"E2E-SkillTest-1457\\zephyr-quartz-resonator-renamed.md","target_kb_id":kb2})` → `{"success":true,"document":{"parentId":"c2e2bf92-…","path":"E2E-SkillTest-Dst-1457\\zephyr-quartz-resonator-renamed.md",…}}`
- Verify: dst `count=1`; src `count=0` (move is real and UUID `f394ccb9…` preserved).
- `kb_doc_move` back → src `count=1`, dst `count=0`.
- `kb_search_stats({kb_id:kb1})` after move-back → `chunk_count=9`.
- **Defect D1** appears once indexing is repeated (see below).

### #7 `knowledgebase-organize` — PASS (D1 visible)
- `kb_find_duplicates({"kb_id":kb1,"threshold":0.90})` → `{"docs_scanned":1,"near_duplicates":1,"duplicate_groups":[{"type":"near","similarity":0.9738,"documents":[{"doc_path":"E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md"},{"doc_path":"E2E-SkillTest-1457/zephyr-quartz-resonator.md"}],"recommendation":"High vector similarity (97.38%)…"}]}` — **the document is flagged as a near-duplicate of its own pre-rename path** (stale chunks).
- `kb_tags_list({})` → `{"success":true,"tags":[…316 tags…]}`
- `kb_doc_update_tags({"kb_id":kb1,"doc_path":…,"tags":["cryogenic-resonator","quartz","calibration","frequency-reference"]})` → success
- `kb_doc_get_by_tag({"tag":"cryogenic-resonator","kb_id":kb1})` → `{"count":1,"documents":[{"name":"zephyr-quartz-resonator-renamed.md",…}]}`
- `kb_batch_index({"kb_id":kb1,"doc_paths":[<renamed path>],"force":true})` → `{"success":true,"indexed":[{"doc_path":…,"vector_index":{"collection":"kb_95f4e9a1-…","chunk_id_prefix":"E2E-SkillTest-1457\\zephyr-quartz-resonator-renamed.md__chunk_","total_chunks":9}}],"total_indexed":1}`

### #8 `knowledgebase-verify` — PASS (three-way inconsistency found)
- `kb_get_documents({kb_id})` → `count=1`
- `kb_doc_read({"kb_id":kb1,"doc_path":<renamed>,"max_chars":500})` → `{"success":true,"path":"E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md","content":"# Zephyr-Quartz Resonator Calibration Protocol …"}`
- `kb_search_stats({kb_id})` → `chunk_count=18` → **inconsistent with 1 document / 9 chunks** (D1).
- `kb_search_vector(…, top_k=10, score_threshold=0.0)` distinct paths: `{"E2E-SkillTest-1457/zephyr-quartz-resonator.md":[0.8,0.689,0.641,0.505,0.172], "E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md":[0.8,0.689,0.641,0.505,0.172]}` — **every chunk returned twice, identical scores**.
- Fix verification: `kb_reindex({"kb_id":kb1,"force":true})` → async `task_id=8214ad7d4a12`; after `kb_task_status` completed, `kb_search_stats` → `chunk_count=9` (cleared). Vector probe then shows only the renamed path.

### #9 `knowledgebase-graph` — PASS
- `kb_graph_stats({})` → `{"neo4j_available":true,"stats":{"node_count":658,"edge_count":4675,"doc_count":333,"kb_count":9,"tag_count":316}}`
- `kb_graph_build({"kb_id":kb1,"force":true})` → `{"success":true,"status":"running","task_id":"8dbee5aff782","kind":"kb_graph_build"}`
- `kb_task_status({"task_id":"8dbee5aff782"})` polled until settled.
- `kb_graph_stats({})` → `edge_count=4679` (Δ+4 = the doc's 4 tag edges)
- `kb_graph_document({"doc_path":"E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md","limit":50})` → `{"success":true,"graph":{"graph_doc_id":"doc::E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md","document":{"tags":["calibration","quartz","cryogenic-resonator","frequency-reference"],…}}}`
- `kb_graph_kb_overview({"kb_id":kb1})` → `{"overview":{"doc_count":1,"sub_kbs":[],"tag_distribution":[{"tag":"calibration","doc_count":1},…4 tags],"top_docs":[{"name":"zephyr-quartz-resonator-renamed.md","degree":2,"tw":1.13}]}}`

### #10 `knowledgebase-experience` — PASS
- `experience_dashboard({"kb_id":kb1})` → `{"total_experiences":0,"by_tier":{"P0":0,"P1":0,"P2":0},"drafts_pending":0,"stale":0,"orphan":0,"needs_sync":0}`
- `experience_search_global({"query":"Zephyr-Quartz resonator calibration quality factor","top_k":5,"score_threshold":0.45,"verify_content":true})` → `{"count":0,"vector_recall":0,"keyword_recall":0,"message":"向量+关键词召回均为空（阈值=0.189）— 无语义相关经验，不编造","rounds":3,"degraded":true}`
- `experience_list({"kb_id":kb1})` → `{"count":0,"experiences":[]}`
- `experience_extract({"kb_id":kb1,"mode":"prepare"})` → `{"success":true,"docs_to_extract":1,"documents":[{"path":"E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md","content":"# Zephyr-Quartz Resonator Calibration Protocol …"}]}`
- `experience_extract({"kb_id":kb1,"mode":"heuristic","dry_run":true})` → `{"total_candidates":1,"candidates":[{"title":"…- 核心要点","problem":"文档《…》研究的核心问题: # Zephyr-Quartz …","solution":"# Zephyr-Quartz …"}]}` — as the SKILL warns, the heuristic candidate is a raw dump that the E2 gate would reject; dry_run prevented it from entering the draft pool.

### #11 `knowledgebase-experience-summarize` — PARTIAL
- `experience_drafts_list({"kb_id":kb1})` → `{"count":0,"drafts":[]}` → **no draft existed**, so `experience_draft_read` / `experience_draft_approve` could not be exercised. Reported honestly (the task explicitly allows "if none, say so").

### #12 `knowledgebase-batch` — PASS
- `kb_doc_batch_delete({"kb_id":kb1,"doc_paths":["E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md"]})` → `{"success":true,"total":1,"successful":1,"failed":0,"results":[{"path":"E2E-SkillTest-1457/zephyr-quartz-resonator-renamed.md","success":true}]}` (full forward-slash relative path accepted on first try)
- `kb_get_documents({kb_id:kb1,"lightweight":true})` → `count=0`
- `kb_search_stats({kb_id:kb1})` → `chunk_count=0`

### #13 `knowledgebase-update` — FAIL
- `kb_project_status({"show_version":true})` → success, but **no version field returned** (keys: `success/ready/app_mode/project_root/services/summary`). The `show_version` parameter was silently ignored (D2).
- `kb_project_update({"show_version":true})` → `{"success":false,"local":{"version":"2.3.0","project_root":"D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge"},"remote":null,"update_available":null,"error":"ragctl version --json timed out after 30s","via":"fallback"}` (D3). Repo `VERSION` file = `2.3.0` (matches `local.version`).

### #14 `soul` — PASS
- `soul_list({})` → JSON array with 1 entry: `{"kb_id":"aa0fec78-6639-41f7-9fd9-65e0e8fc1a45","name":"soul-e2e-tester-024115","kb_scope":["*"],"domain_labels":["e2e","platform-testing","rag"],"is_template":false,"meditation":{"harness":"omp","enabled":false,"interval_hours":24}}`

### #15 `soul-rag` — PARTIAL
- `soul_list({})` → persona system online (see #14).
- `soul_router({"query":"What is the ReAct framework for reasoning and acting in language models?","task_goal":"teaching","task_type":"literature_review"})` → `{"success":true,"ranked":[{"kb_id":"aa0fec78-…","score":0.62,"reason":"唯一候选…"}],"top1":"aa0fec78-…","route_confidence":0.62,"candidates_considered":1}` (27.7s)
- `soul_qdcvr_ask({"query":…,"soul_kb_id":"","task_goal":"teaching","task_type":"literature_review","top_k":5,"async_mode":true})` → `{"success":true,"status":"running","task_id":"5765ea09e8d7","kind":"soul_qdcvr_ask"}`
- `kb_task_status({"task_id":"5765ea09e8d7"})` polled repeatedly → `{"status":"running","elapsed_seconds":353.2,…}`. **The persona synthesis had not completed after ~6 minutes**; `answer`/`citations`/`pas_score` were therefore not observed. Marked PARTIAL.

### #16 `butian` — PASS (read-only)
- `kb_list({"lightweight":true})` → catalog contains the distillation landing target `soul-e2e-tester-024115` (a `soul-<name>` KB), consistent with "distillation lands as a KB". No `butian-*` KB exists in this environment. Read-only; nothing modified.

---

## 3. Defects Found

### D1 — Stale/orphan vector chunks after rename + move (REAL, confirmed)
After `kb_doc_update_meta` (rename) + `kb_doc_move` + `kb_batch_index(force=true)`:
- `kb_search_stats` reported **`chunk_count=18`** for a KB holding **one 9-chunk document** (was 9 before).
- `kb_search_vector` returned **each chunk twice** — once under the old path `E2E-SkillTest-1457/zephyr-quartz-resonator.md` and once under the new path `…-renamed.md` — with **identical scores** (`[0.8, 0.689, 0.641, 0.505, 0.172]` each).
- `kb_find_duplicates` consequently reported a **false near-duplicate (similarity 0.9738)** of the document against its own old path:
  > `{"type":"near","similarity":0.9738,"documents":[{"doc_path":"…-renamed.md"},{"doc_path":"…zephyr-quartz-resonator.md"}],"recommendation":"High vector similarity (97.38%)…"}`

This contradicts:
- `knowledgebase-manage` SKILL.md: *"⭐ `kb_doc_move` **triggers reindexing automatically** (fire-and-forget)"* — the auto-reindex did **not** clear the pre-rename path's chunks.
- `knowledgebase-organize` L7: `kb_batch_index(force=true)` — `force=true` re-indexed the listed document under the new path but did **not** purge the old-path chunks.
- `knowledgebase-verify` V1's premise of three-layer consistency: the vector layer held 2× the metadata's chunks.

**Documented fix works, but is async and manual:** `kb_reindex({"kb_id":kb1,"force":true})` returned `{"status":"running","task_id":"8214ad7d4a12"}`, and after polling to completion `kb_search_stats` returned `chunk_count=9` (orphans cleared). The SKILL's own NEVER list ("Old path vectors remain after move → `kb_reindex(force=true)`") is therefore accurate, but the automatic-cleanup claim is not — a caller who trusts auto-reindex will silently double their index.

### D2 — `kb_project_status(show_version=True)` silently ignores `show_version`
`kb_project_status` has only a `scope` parameter; passing `show_version=True` is accepted without error but **no version is returned** (result keys: `success/ready/app_mode/project_root/services/summary`). The `knowledgebase-update` skill's version-check flow expects version output; only `kb_project_update(show_version=true)` (or the `ragctl version` CLI) can provide it.

### D3 — `kb_project_update(show_version=True)` failed (timeout)
Exact return:
```json
{"success": false,
 "local": {"version": "2.3.0", "project_root": "D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge"},
 "remote": null, "update_available": null,
 "error": "ragctl version --json timed out after 30s", "via": "fallback"}
```
The local version (`2.3.0`, matching the repo `VERSION` file) was retrieved, but the remote comparison failed. Root cause is most likely the 30s timeout against the GitHub API in this offline/restricted environment; nonetheless the tool returned `success:false` and the skill's Phase-1 version comparison could not complete.

### D4 — `kb_task_status` shape inconsistency (minor)
For the finished reindex task, the record combined contradictory fields:
```json
{"task_id":"8214ad7d4a12","status":"running","created_at":"2026-09-24T07:00:17+00:00",
 "elapsed_seconds":21.4,"finished_at":"2026-09-24T07:00:19+00:00","success":true}
```
`status="running"` coexists with `finished_at` set and `success:true`; `elapsed_seconds=21.4` disagrees with the 2-second `created_at`→`finished_at` delta. A consumer polling on `status` alone could loop indefinitely. (`kb_graph_build`'s poll settled normally, so impact is limited to `kb_reindex` in this run.)

### D5 — `kb_search` relevance noise on generic tokens (weakness, not a hard bug)
`kb_search({"query":"ZQ-7731 quality factor","top_k":5})` returned 5 **unrelated economics documents** and did not include the freshly-indexed test doc:
> `{"hits":[{"kbName":"经济与社会","docName":"economics__1901.03951__inequality-mobility-and-the-financial-accumu.md (part 1 of 3).md","score":4}, …]}`

`kb_search` is a substring/keyword matcher ("quality" ⊂ "inequality"). A **controlled re-test** proved indexing itself is fine: a second fixture containing the unique token `XYLOPHONE-9912` returned `kb_search({"query":"XYLOPHONE-9912"}) → [("xylophone-fixture.md", 10)]` (rank #1), and a descriptive query ranked it #1 too. So the weakness is **relevance/tokenization on generic query terms**, not a missing index. Impact is limited because `knowledgebase-search` uses `kb_search_vector` as its primary Phase-1 channel (which hit correctly at 0.75).

### Harness-caused errors (NOT platform defects)
Four calls failed because my first harness extraction passed `kb_id=None` (I mis-guessed `kb_create`'s return shape; the correct key is `knowledgeBase.kb_id`). The tools **correctly** rejected the bad input:
> `Error executing tool kb_doc_create: 1 validation error for kb_doc_createArguments\nkb_id\n  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]`

These are my error, re-run successfully once IDs were parsed. Recorded for transparency only.

### Observation O1 — prompt-injection-style "learned preferences" inside SKILL.md
Several skills (`knowledgebase-init`, `knowledgebase-search`, `knowledgebase-graph`, `knowledgebase-manage`, `knowledgebase-organize`, `knowledgebase-experience-summarize`, `knowledgebase-update`, `soul`, `soul-rag`, `butian`) carry a `<!-- SKILLOPT-SLEEP:LEARNED START -->` block imposing **mandatory literal output strings** (e.g. "every response MUST begin with the exact, literal label…", "the reply MUST contain `soul_qdcvr_ask` verbatim", "must include the exact phrase …"). These are not tool behaviours and were **not honored** — they are output-contract injections that override legitimate response formatting and would, if followed, degrade honest reporting. Flagged as a documentation-integrity concern, not a functional defect.

---

## 4. Cleanup Confirmation

- `kb_doc_batch_delete` emptied the destination KB (`xylophone-fixture.md`).
- `kb_delete({"kb_id":"95f4e9a1-b24d-43c1-b94d-04c55d90b5d1"})` → `{"success":true,"deletedId":"95f4e9a1-…","message":"Folder \"E2E-SkillTest-1457\" deleted successfully"}`
- `kb_delete({"kb_id":"c2e2bf92-db86-48f5-96f8-7ac9b9931f67"})` → `{"success":true,"deletedId":"c2e2bf92-…","message":"Folder \"E2E-SkillTest-Dst-1457\" deleted successfully"}`
- Final `kb_list({"lightweight":true})` → **10 KBs, both test KBs absent:**
  `["计算机与人工智能","自然科学与地球科学","生命科学与医学","工程与能源","经济与社会","aw-industrial","Corpus-Chunks800","e2e-demo-0923-022632","soul-e2e-tester-024115","Novel-PridePrejudice"]`
- Programmatic check `any(name.startswith("E2E-SkillTest"))` → **False**. ✅ Both test KBs are gone; no pre-existing KB was modified.

---

## 5. Honest Limitations

- **`parse_doc` / MinerU parse path: NOT exercised.** Per the safety rule, I did not run a parse (risk/slowness vs. no real data to touch). Consequently the ingest **A2 parse-quality gate, A2.5 split gate, and `kb_doc_save_parsed`** were not exercised. All ingest testing used the *direct path* (`kb_doc_create`).
- **#11 experience-summarize: PARTIAL.** No draft existed (`drafts_list` → 0), so `experience_draft_read`/`experience_draft_approve` were not exercised. I deliberately did **not** force `experience_extract(dry_run=False)` (the SKILL explicitly warns that heuristic writes produce junk).
- **#15 soul-rag: PARTIAL.** `soul_qdcvr_ask` is async and was **still running after ~6 minutes** (`task_id=5765ea09e8d7`, `status:"running"`); the final `answer`/`citations`/`pas_score` were not observed. Routing (`soul_router`, confidence 0.62) did work. A full persona-answer run requires a longer budget.
- **#13 knowledgebase-update: FAIL (remote comparison).** Only the version-check was attempted (no pull was performed — a pull would modify the repo and was out of scope). The remote check timed out; `local.version=2.3.0` was retrieved.
- **Experience CRUD not exercised:** `experience_create/update/delete/apply/review` were outside the listed operation set.
- **Soul training/RL/meditation not exercised** (`soul_train_rl`, `soul_learn`, `experience_meditation_*`) — expensive/long-running and out of the listed scope.
- **Butian distillation not run** — only the read-only landing check (skill #16).
- **Single run, no repetition:** latencies and results are from one execution; no variance measurement. Latencies include MCP-stdio startup per call (each stage spawns a fresh `McpClient`).
- **D3 root cause is inferred, not proven:** "GitHub API timeout in a restricted environment" is the most likely explanation but was not independently confirmed.
- **No pre-existing KB was read deeply** (beyond `kb_list`/`kb_search` whole-library hits); the read-only claim for pre-existing KBs is based on the absence of any write call targeting them.

---

*Raw evidence: `.e2e/skilltest/calls.jsonl` (109 calls), `.e2e/skilltest/state.json`, test scripts in `.e2e/skilltest/`. All results above are copied from actual tool returns.*
