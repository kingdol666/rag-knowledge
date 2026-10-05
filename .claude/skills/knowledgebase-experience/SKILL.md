---
name: knowledgebase-experience
description: "Experience full lifecycle management E0-E12. Structured practice cases (scenario/problem/solution/lessons). Auto-extract from KB docs (E0 prepare+LLM refine, E1 heuristic), quality gate (E2), draft pool (E3), experience-first retrieval (E4 with strict P0/P1/P2 credibility tiers), document linkage stale detection (E6), dashboard (E8), decay cycles (E11), auto health check+cleanup (E12). Triggered by: experience, experience library, experience, lesson, best practice, practice, case study, incident experience, ops experience, lesson learned, extract experience, extract from documents, summarize experience, experience dashboard, experience sync."
---

## Related skills

- Auto-extract after ingest → `skill://knowledgebase-ingest` A7 eight-item final check · Batch export → `skill://knowledgebase-batch` B6 · Graph-associated retrieval → `skill://knowledgebase-graph` · Restructure → `skill://knowledgebase-organize`
- Document-first retrieval → `skill://knowledgebase-search` (QDCVR v2) · Authoring/meditation/CRUD+migration → `skill://knowledgebase-experience-summarize` · Verify V8 triggers the E12 health check → `skill://knowledgebase-verify`
- Architecture mental model (5-layer model + consistency invariants + 94-tool map) → [kb-architecture.md](../knowledgebase/references/kb-architecture.md)

## Execution model (mandatory, first step of any job)

**Executor: Archival agent** — delegate via `task`; delegation template + three-role execution model + combined-task boundaries → [execution-model.md](../knowledgebase/references/execution-model.md). **Pre-Flight**: one-probe double-check `kb_project_status` → branch handling → smoke test — no work before it passes, full flow → [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). MCP-first (no terminal/HTTP bypass) → [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

**Routing — experience or documents?** Ops/incident ("how do I XX", "it errored") → experience first (E4); theory/principle/overview ("what is XX") → documents; "summarize XX as an experience" → `skill://knowledgebase-experience-summarize`.
Concepts: **document** = full text, free-form, for reading · **experience** = single-point structured JSON, for retrieval, dynamic credibility · **linkage** = document update → experiences auto-detected stale → re-extract.

## Sequential workflow (choose entry by scenario)

- **Step 1 — Pre-Flight check**: run the mcp-preflight-check one-probe double-check (MCP+backend+web health).
- **Step 2 — Scenario routing**: incident lookup / new documents / management / maintenance.
- **Step 3 — Incident lookup (experience first)**: `experience_search_smart(query)` → E4a content ruling → content ≥5 answer directly, otherwise fall back to `kb_search_two_stage`.
- **Step 4 — Auto-extract from new documents**: post-ingest → `experience_extract(kb_id, mode="prepare")` → Agent LLM refinement → E2 gate → publish or draft pool; bulk scans first run `experience_extract(kb_id, mode="heuristic", dry_run=True)`.
- **Step 5 — Experience management (CRUD)**: `experience_create/update/delete/apply/review` → auto-indexing + metadata writes.
- **Step 6 — Periodic maintenance**: `experience_check_stale` → E6a update flow → `experience_apply_decay` → `experience_sync_kb`.
- **Step 7 — Draft review (E3)**: `drafts_list` → `draft_read` → `draft_approve(edits=refined fields)` / `draft_reject`.
- **Step 8 — Dashboard (E8)**: `experience_dashboard(kb_id)` → full statistics + pending counts.

## E0/E1 — Auto-extraction (mining experiences from documents)

```text
experience_extract(kb_id="<KB>", mode="prepare")                  # E0 task package → Agent LLM refinement
→ {documents: [{path, content}], existing_scenarios, extraction_template, hint}
experience_extract(kb_id="<KB>", mode="heuristic", dry_run=True)  # E1 rules, no LLM
→ {total_candidates, candidates: [{title, scenario, problem, solution, key_lessons, confidence, ...}]}
```
E0: distill per `extraction_template`, dedup against `existing_scenarios`; E1: structure (## sections) + keywords (problem/solution/lesson); timing: after ingesting new documents (ingest A7 passed), bulk-learning a KB, periodic enrichment. `dry_run=False` writes candidates directly into the draft pool — heuristic extraction yields mostly low-quality candidates (section titles mistaken for key_lessons); strongly discouraged, use the E2c strategy.

## E2 — Quality gate (mandatory; both extraction and creation)

**E2a heuristic candidates** — check every E1 output item; rejected candidates are discarded, never written to the draft pool (avoids polluting the review queue):
1. key_lessons blocklist: section-title patterns (Roman numerals I./II. + INTRODUCTION/OVERVIEW/METHOD/CONCLUSION) or numbered patterns ("1 Introduction"/"3.1 Method") → reject · length <20 or >500 chars → reject · empty filler ("key points"/"summary"/"overview") → reject
2. raw dumps: problem >300 chars or solution >500 chars → reject (must be distilled concise) · 3. tags empty → reject · 4. confidence <0.8 → route to the draft pool + LLM refinement, never publish directly

**E2b manual creation**: scenario needs a domain prefix (`llm-hallucination`; `test` forbidden) · solution ≥50 chars with concrete methods (not "modified the code/adjusted parameters") · each key_lessons entry ≥30 chars, independently actionable (not "needs debugging") · related_docs must point to real documents · tags ≥2 (domain word + scenario word) · a similar scenario already exists → draft review instead of new create.

**E2c recommended strategy**: post-ingest → `mode="prepare"` + LLM refinement → publish directly (skip draft pool); bulk scan → `mode="heuristic"` + `dry_run=True`, keep only confidence ≥0.8, refine with `prepare`; forbidden: heuristic + `dry_run=False` (empirically junk).

## E3 — Draft pool (candidate review)

```text
experience_drafts_list(kb_id)                       → drafts pending review
experience_draft_read(kb_id, draft_id)              → details incl. source-document evidence
experience_draft_approve(kb_id, draft_id, edits={}) → approve → formal experience
experience_draft_reject(kb_id, draft_id, reason)    → reject → rejected/ (reason preserved)
```
Review flow: list → read one by one → after LLM refinement `draft_approve(edits=refined fields)` or `draft_reject`.

## E4 — Experience-first retrieval (content ruling)

Core principle: content first; better to give nothing than something wrong — no confirmed experience → declare the blind spot honestly.

```text
Step 1 — experience first: experience_search_smart(query, top_k=8)   # recommended entry
  (low-level compatible: experience_search_global(query, top_k=8, score_threshold=0.45, verify_content=True))
Step 2 — content ruling (mandatory, non-skippable): for every P0/P1, experience_read(kb_id, exp_id, max_chars=2000), then score 0-6 independently (vector score does not influence the decision):
  scenario match 0-2 (2=directly matches the query scenario · 1=related domain, transferable · 0=irrelevant)
  solution executability 0-2 (2=concrete steps/configs/commands · 1=directional guidance · 0=generic description)
  lesson citability 0-2 (2=concrete, independently citable · 1=needs the original text · 0=empty)
  content <3 → discard no matter how high the vector score · 3-4 → P2 weak reference, flag low confidence · ≥5 → include
Step 3 — content ≥5 → answer directly (skip document retrieval); no P0/P1 or all <3 → supplement kb_search_two_stage
```
Presentation (E4b): `- [P0/P1/P2] <title> @ <KB/exp_id>` + scenario, content score X/6 (breakdown), credibility · applied · reviewed counts, related_docs — only content ≥5 enters the answer body; none ≥3 → honestly say "no relevant experiences", then document retrieval.
Transparency fields (E4c): `vector_recall`, `tier_counts`, `content_ruling`, per-experience `vector_score`+`content_score`+`tier`+`tier_reason`.

## E4d — Smart search enhancement

`experience_search_smart(query, top_k=8)` = intent recognition + adaptive thresholds (troubleshooting 0.55 / best_practice 0.45 / learning 0.35 / decision 0.50) + multi-round downgrade + counter-example detection. Prefer it; `experience_search_global` only for manual threshold control. Details (3-round downgrade logic, rerank weights, relation to E4a) → [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E4d.

## E5 — Credibility tiering

| Condition | Tier | Action |
|---|---|---|
| vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ review≥1 | **P0 Strong** | Cite directly, place at top |
| vector≥0.45 ∧ content≥4 | **P1 Reference** | Adopt with attribution |
| vector≥0.35 ∧ content≥3 | **P2 Weak** | Suppressed by default (only when P0/P1 insufficient) |
| Content verification fails OR vector<0.35 | **DISCARD** | Never returned |
| disputed (review≥3 ∧ rating<2) | downgrade→max P2 | Downgraded due to dispute |
| unvetted (0 review ∧ 0 applied) | downgrade→max P1 | Unreviewed suppression |

Modifier details + short-content false-hit protection (<50 chars downgrade rule) → [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E5.

## E6 — Document linkage / stale detection + auto-update

```text
experience_check_stale(kb_id)  → KB experience-document consistency (empty kb_id = whole library)
experience_sync_kb(kb_id)      → mark the entire KB needs_sync
```
Detection: document mtime > experience updated_at → **stale**; document missing → **orphan**.

**E6a update flow (stale → re-extract → update)**: `experience_read(kb_id, exp_id)` → `kb_doc_read(kb_id, related_doc_path, max_chars=5000)` → LLM compares (what did the document add; are problem/solution/key_lessons still accurate; anything new to extract) → 4a still accurate: `experience_update(kb_id, exp_id, updated_at=now)` · 4b needs update: distill new problem/solution/key_lessons → `experience_update(kb_id, exp_id, **updated_fields)` (vector index rebuilds automatically) · 4c document no longer contains it → orphan, handle per the E12 matrix → `experience_sync_kb(kb_id)` clears the flag.
Priority: stale + P0/P1 + applied>0 → update first (high value) · stale + P2 + applied=0 → defer, mark silently · orphan + applied>0 → keep content, clear related_docs · orphan + applied=0 + rating=0 → delete (zero-value residue).

## E7 — Search paths

Incident-type: `experience_search_smart` → answer directly from P0 · optimized: smart → `experience_rerank` → final ranking · general: `kb_search_two_stage` → `experience_search_global` as supplement.

## E8 — Dashboard

`experience_dashboard(kb_id)` → `{total, by_tier:{P0,P1,P2}, summary, drafts_pending, stale, orphan, needs_sync}`

## E8a — Meditation auto-induction

```text
experience_meditation_status()              → scheduler state (enabled/interval/last_run/harnesses/circuit_breakers) — check before every experience operation
experience_meditation_run(kb_id)            → manual trigger after ingest; non-blocking (returns task_id, runs minutes in background)
experience_meditation_task_status(task_id)  → poll (running→done; done includes experiences/summary)
experience_meditation_config_get(kb_id) / experience_meditation_config_update(kb_id, enabled, auto_publish, ...)
experience_meditation_history(kb_id, limit) → audit historical runs and output counts
```

## E9-E10 — Export and batch

No dedicated export tool: `experience_list(kb_id)` → Agent formats JSON/CSV/Markdown; batch via `skill://knowledgebase-batch` B6 (export summary) or loop `experience_read`.

## E11 — Decay cycles

`experience_apply_decay(kb_id)` applies rules and marks: stale_unverified (created >30 days ∧ 0 applications → retrieval downgrade) · disputed (≥3 reviews ∧ rating<2.0 → down to P2) · unvetted (0 reviews ∧ 0 applications → max P1). Run periodically (e.g. weekly) to keep experiences fresh.

## E12 — Experience auto health check and cleanup

Trigger: every `knowledgebase-verify` V8 / monthly scheduled / after document deletion. Flow: `experience_check_stale()` (empty kb_id = whole library) → stale/orphan detection → categorized handling → test-pollution cleanup. Decision matrix + detection detail → [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E12. Test-pollution detection must use `experience_list` (not summary — it returns top 5 only), reading `created_at` for the >7d aging judgment.

## Basic CRUD

```text
experience_create(kb_id, title, scenario, category, problem, solution, result, key_lessons, tags, severity, related_docs, prerequisites, metrics)
# auto after create: vector indexing (6 chunks) + metadata writes + disk file — all three consistent
experience_read(kb_id, exp_id)                               → includes the .md body
experience_list(kb_id, scenario="", category="", tag="")     → sorted by rating
experience_update(kb_id, exp_id, **fields)                   → rebuilds the index automatically
experience_delete(kb_id, exp_id)                             → permanent deletion
experience_apply(kb_id, exp_id, user, context, result, notes) → applied_count+1
experience_review(kb_id, exp_id, reviewer, rating, comment)   → recalculates rating_avg
```
Valid enums only (invalid → HTTP 422): `category` ∈ {best_practice, troubleshooting, lesson_learned, optimization, tip, workflow, decision} (not `bug`/`issue`); `severity` ∈ {critical, important, normal, tip} (not `high`/`low`); `tip` is valid for both; `result` defaults to `success`.
Search: `experience_search_smart(query, top_k)` (recommended) · `experience_search_global(query, top_k)` cross-library · `experience_search_global(kb_id, query, top_k)` metadata/vector · `experience_list(kb_id, scenario="…")` · `experience_rerank(query, experiences_json)` · stats `experience_summary(kb_id)` / `experience_dashboard(kb_id)`.

## Never

- Create experiences lacking problem/solution/lessons — useless even when retrieved; all three must be non-empty and specific.
- Skip the E2 quality gate — low-quality experiences pollute the library; scenario/related_docs must be verified.
- Skip stale detection during maintenance — outdated experiences mislead decisions; `check_stale` at least monthly.
- Judge library quality by summary/dashboard avg_rating — unreviewed experiences (review_count=0) don't count into it but show in unrated_count; watch `reviewed_count`+`unrated_count`, not just avg_rating.
- Run `apply_decay` when nothing changed — once a week is enough.
- Write "experiences" as documents (long prose) — experiences are single-point and structured: one problem→one solution→one lesson.
- Incident lookup without checking experiences first — misses second-level answers; `experience_search_smart` first, `experience_search_global` as backstop, documents as supplement.
- Call `experience_search_global` directly for incident lookups — loses smart intent recognition + multi-round downgrades; `_global` only for manual control.
