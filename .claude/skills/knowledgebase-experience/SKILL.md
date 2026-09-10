---
name: knowledgebase-experience
description: >
  Experience full lifecycle management E0-E12. Structured practice cases
  (scenario/problem/solution/lessons). Auto-extract from KB docs
  (E0 prepare+LLM refine, E1 heuristic), quality gate (E2), draft pool (E3),
  experience-first retrieval (E4 with strict P0/P1/P2 credibility tiers),
  document linkage stale detection (E6), dashboard (E8), decay cycles (E11),
  auto health check+cleanup (E12). Triggered by: experience, experience library,
  experience, lesson, best practice, practice, case study, incident experience,
  ops experience, lesson learned,
  extract experience, extract from documents, summarize experience, experience dashboard, experience sync.
---

## ⭐ Related Skills
- Auto-extract experiences after document ingest → `skill://knowledgebase-ingest` A7 eight-item final check
- Document-first retrieval → `skill://knowledgebase-search` (QDCVR) / `skill://knowledgebase-search-enterprise` (cross-library)
- Batch experience operations → `skill://knowledgebase-batch` B6 export step
- Experience summarization & ingestion → `skill://knowledgebase-experience-summarize` (full E0-E12 extraction+review flow)
- KB integrity validation → `skill://knowledgebase-verify` V8 experience health check
- KB organize & restructure → `skill://knowledgebase-organize`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Sequential Workflow (Choose Entry by Scenario)

**Step 1 — Pre-Flight check**: run the mcp-preflight-check one-probe double-check to confirm MCP+backend+web health.
**Step 2 — Scenario routing**: determine which entry the user request belongs to (incident lookup/new documents/management/maintenance).
**Step 3 — Incident lookup (experience first)**: experience_search_smart(query) → E4a content ruling (0-6 scoring) → content>=5 answer directly / otherwise fall back to kb_search_two_stage.
**Step 4 — Auto-extract from new documents**: after ingest → `experience_extract(kb_id, mode="prepare")` to get documents+template → Agent LLM refinement → E2 quality gate → publish directly or enter the draft pool. For bulk scans, first `experience_extract(kb_id, mode="heuristic", dry_run=True)` to filter high-confidence candidates.
**Step 5 — Experience management (CRUD)**: experience_create/update/delete/apply/review → auto-indexing + metadata writes.
**Step 6 — Periodic maintenance**: experience_check_stale → E6a stale update flow → experience_apply_decay → experience_sync_kb.
**Step 7 — Draft review (E3)**: drafts_list → draft_read → draft_approve(edits=refined fields) or draft_reject.
**Step 8 — Dashboard monitoring (E8)**: experience_dashboard(kb_id) → full statistics + pending counts.

# Experience — Full Lifecycle Management (E0-E12)

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

## Mental Framework: When to Use Experiences? When to Use Documents? [IMPORTANT]

```
The user asked a question
  ├── Ops/incident/operational ("how do I XX", "it errored") → experience first! E4 retrieval
  ├── Theory/principle/overview ("what is XX") → document first
  └── "Summarize XX as an experience" → experience-summarize (experience summarization & ingestion)
```

---

## Core Concepts
- **Document**: full text, free-form markdown, for reading and learning
- **Experience**: single-point, structured JSON, for retrieval and application, dynamic credibility
- **Linkage**: document updates → experiences auto-detected as stale → triggers re-extraction

---

## E0/E1 — Auto-Extraction (Mining Experiences from Documents) [IMPORTANT]

### E0 Extraction Task Package (LLM high-quality refinement)
```
experience_extract(kb_id="<KB>", mode="prepare")
→ {documents: [{path, content}], existing_scenarios, extraction_template, hint}
```
After receiving the task package, the Agent uses the LLM to distill per `extraction_template` (deduplicating against `existing_scenarios`), producing high-quality candidates.

### E1 Heuristic Extraction (Rules, No LLM)
```
experience_extract(kb_id="<KB>", mode="heuristic", dry_run=True)
→ {total_candidates, candidates: [{title, scenario, problem, solution, key_lessons, confidence, ...}]}
```
Heuristic extraction based on document structure (## sections) + keywords (problem/solution/lesson).

> [WARNING] **Dangerous operation warning**: `dry_run=False` writes candidates directly into the draft pool. In practice, heuristic extraction produces large amounts of low-quality candidates (section titles mistaken for key_lessons). Directly using dry_run=False is **strongly discouraged** — see the E2c recommended strategy below.

**Extraction timing**: after ingesting new documents (Ingest A7 passed; see the A7 eight-item final check in [knowledgebase-ingest](../knowledgebase-ingest/SKILL.md)); bulk-learning a KB; periodically enriching the experience library.

## E2 — Quality Gate (Mandatory; Applies to Both Extraction and Creation) [IMPORTANT]

### E2a Heuristic Extraction Quality Gate (Mandatory After E1 Output)
```
For every candidate from E1 heuristic, check each item:
  1. key_lessons blocklist detection:
     - Matches section-title patterns (Roman numerals I./II. + keywords like INTRODUCTION/OVERVIEW/METHOD/CONCLUSION) → ✗ reject
     - Matches numbered patterns ("1 Introduction"/"3.1 Method"/"4.2 Results") → ✗ reject
     - Length < 20 chars or > 500 chars → ✗ reject
     - Empty filler phrases like "key points"/"summary"/"overview" → ✗ reject
  2. problem/solution quality detection:
     - problem is a raw dump > 300 chars → ✗ reject (must be distilled into a concise problem statement)
     - solution is a raw dump > 500 chars → ✗ reject
  3. tags non-empty detection: tags=[ ] → ✗ reject
  4. confidence < 0.8 → route to the draft pool (do not publish directly); requires LLM refinement
```
**Rejected candidates are not written to the draft pool** — discard directly to avoid polluting the draft review queue.

### E2b Manual Creation Quality Gate
- scenario must have a domain prefix (e.g. `llm-hallucination`); `test` is forbidden
- solution ≥ 50 chars, containing concrete methods (not vague phrases like "modified the code/adjusted parameters")
- each key_lessons entry ≥ 30 chars and independently actionable (not "needs debugging"/"take a look")
- related_docs must point to real documents
- tags ≥ 2 (must include a domain word + a scenario word)
- Dedup: a similar scenario already exists in the KB → route to draft review instead of creating new

### E2c Recommended Extraction Strategy
- **Auto-extract after ingest**: use `mode="prepare"` → LLM refinement → publish directly (skip the draft pool)
- **Bulk scanning**: first `mode="heuristic"` + `dry_run=True` scan → keep only confidence≥0.8 candidates → refine with `mode="prepare"`
- **Forbidden**: heuristic + dry_run=False writing directly to the draft pool (empirically produces large amounts of junk)

## E3 — Draft Pool (Candidate Review) [IMPORTANT]
```
experience_drafts_list(kb_id)                      → list drafts pending review
experience_draft_read(kb_id, draft_id)             → read draft details (including source document evidence)
experience_draft_approve(kb_id, draft_id, edits={}) → approve → becomes a formal experience
experience_draft_reject(kb_id, draft_id, reason)    → reject → rejected/ (reason preserved)
```
**Review flow**: `drafts_list` → `draft_read` one by one → after LLM refinement, `draft_approve(edits=refined fields)` or `draft_reject`.

## E4 — Experience-First Retrieval (Content Ruling) [IMPORTANT]

**Core principle: content first; better to give nothing than to give something wrong** — with no confirmed experience, honestly declare the blind spot.

### E4a Retrieval Flow (Two Steps)

```
Step 1 — Experience first (vector recall → content ruling)
  experience_search_smart(query, top_k=8) — recommended entry (internally: intent recognition→adaptive threshold→multi-round downgrade→retrieval transparency)
  experience_search_global(query, top_k=8, score_threshold=0.45, verify_content=True) — low-level entry (compatible)
    → internally: vector recall → hard threshold → experience-level dedup → content verification → credibility tiering

Step 2 — Content second ruling (mandatory, non-skippable) ⭐
  For every P0/P1 experience returned by Step 1, must experience_read(kb_id, exp_id, max_chars=2000)
  and independently do 0-6 content scoring (vector score does not influence the decision):

  | Dimension | Pts | Criteria |
  |------|-----|------|
  | **Scenario match** (0-2) | 2=directly matches the query scenario; 1=related domain, transferable; 0=irrelevant |
  | **Solution executability** (0-2) | 2=contains concrete steps/configs/commands; 1=directional guidance; 0=generic description |
  | **Lesson citability** (0-2) | 2=concrete experience citable independently; 1=needs the original text to understand; 0=empty |

  Content score < 3 → discard (no matter how high the vector score)
  Content score 3-4 → P2 weak reference (flag insufficient confidence)
  Content score ≥ 5 → include in the answer

Step 3 — If content ≥ 5, answer directly (skip document retrieval)
  No P0/P1 or content < 3 → supplement with kb_search_two_stage document retrieval
```

### E4b Retrieval Result Presentation Standard

```
## Experiences (retrieved first)
- [P0/P1/P2] <experience title> @ <KB/exp_id>
  - Scenario: <scenario>
  - Content score: <score>/6 (scenario X + solution X + lesson X)
  - Credibility: <rating> points · applied <applied> times · reviewed <review> times
  - Related documents: <related_docs>

(Only experiences with content ≥ 5 are included in the answer body)
(No experiences with content ≥ 3 → honestly declare "no relevant experiences" → supplement with document retrieval)
```

### E4c Retrieval Transparency
- `vector_recall` — total vector recall count (before the hard threshold)
- `tier_counts` — {P0, P1, P2, discarded} tier statistics
- `content_ruling` — content ruling summary ("recall 5→read 4→qualify 2 P0:1 P1:1 P2:2")
- Each experience carries `vector_score` + `content_score` + `tier` + `tier_reason`

## E4d — Smart Search Enhancement [IMPORTANT]

**Recommended entry**: `experience_search_smart(query, top_k=8)` — internally implements query intent recognition + adaptive thresholds (troubleshooting 0.55 / best_practice 0.45 / learning 0.35 / decision 0.50) + multi-round downgrade + counter-example detection + transparency fields.

For detailed mechanisms (intent threshold table, 3-round downgrade logic, counter-example detection, rerank weights, relationship to E4a), see [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E4d.

> Agents should prefer `experience_search_smart`; use `experience_search_global` only when manually controlling thresholds.

## E5 — Credibility Tiering

| Condition | Tier | Action |
|---|---|---|
| vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ review≥1 | **P0 Strong** | Cite directly, place at top |
| vector≥0.45 ∧ content≥4 | **P1 Reference** | Adopt with attribution |
| vector≥0.35 ∧ content≥3 | **P2 Weak** | Suppressed by default (only added when P0/P1 insufficient)|
| Content verification fails OR vector<0.35 | **DISCARD** | Never returned |
| disputed (review≥3 ∧ rating<2) | downgrade→max P2 | Downgraded due to dispute |
| unvetted (0 review ∧ 0 applied) | downgrade→max P1 | Unreviewed suppression |

> Modifier details (disputed/unvetted) + short-content false-hit protection (<50 chars downgrade rule) in [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E5.

## E6 — Document Linkage / Stale Detection + Auto-Update [IMPORTANT]

```
experience_check_stale(kb_id)          → check KB experience-document consistency (empty kb_id = whole library)
experience_sync_kb(kb_id)              → mark the entire KB needs_sync
```

**Detection logic**:
- Document mtime > experience updated_at → **stale** (experience outdated)
- Document missing → **orphan** (reference broken)

### E6a Experience Update Iteration Flow (stale → re-extract → update) ⭐

When `experience_check_stale` finds stale experiences, update them per the following flow:

```
Step 1: experience_read(kb_id, exp_id) → read the current experience content
Step 2: kb_doc_read(kb_id, related_doc_path, max_chars=5000) → read the latest content of the related document
Step 3: LLM compares new document content vs old experience content to decide whether an update is needed:
        - What new content did the document add?
        - Are the old experience's problem/solution/key_lessons still accurate?
        - Are there new extractable experiences?
Step 4a: Experience still accurate → experience_update(kb_id, exp_id, updated_at=now) → refresh the timestamp
Step 4b: Experience needs updating → LLM distills new problem/solution/key_lessons
          → experience_update(kb_id, exp_id, **updated_fields) → vector index rebuilt automatically
Step 4c: Document no longer contains the original experience → mark orphan → handle per the E12 orphan matrix
Step 5: experience_sync_kb(kb_id) → clear the stale flag
```

**Update priority**:
| Experience state | Action | Reason |
|----------|------|------|
| stale + P1/P0 + applied>0 | Update with priority | High-value experience; ensure accuracy |
| stale + P2 + applied=0 | Defer | Low value; mark silently |
| orphan + applied>0 | Keep content, clear related_docs | Experience still useful |
| orphan + applied=0 + rating=0 | Delete directly | Zero-value residue |

**Linkage flow**: document updated → `check_stale` finds stale → Agent reads related_docs and re-extracts → `update_experience` updates → `sync_kb` verifies.

## E7 — Search Paths
```
Incident-type: experience_search_smart (recommended) → answer directly from P0
  Optimized: experience_search_smart → experience_rerank → final ranking
General: kb_search_two_stage → experience_search_global as supplement
```

## E8 — Experience Dashboard
```
experience_dashboard(kb_id) → {total, by_tier:{P0,P1,P2}, summary, drafts_pending, stale, orphan, needs_sync}
```

## E8a — Meditation Auto-Induction (Meditation)

The experience subsystem has a built-in auto-induction scheduler that automatically extracts experience candidates from knowledge base documents.

```
experience_meditation_status()   → scheduler status (enabled/interval/last_run/harnesses/circuit_breakers)
experience_meditation_run(kb_id) → manually trigger one meditation (**non-blocking**: returns task_id immediately; agent runs for minutes in the background)
experience_meditation_task_status(task_id) → poll meditation task results (status: running→done; when done includes experiences/summary)
experience_meditation_config_get(kb_id)   → read a KB's meditation config
experience_meditation_config_update(kb_id, enabled, auto_publish, ...) → update meditation config
experience_meditation_history(kb_id, limit) → view meditation run history
```

| Tool | Purpose | Frequency |
|------|------|------|
| `experience_meditation_status` | Inspection: scheduler enabled, harness health, circuit-breaker state | Before every experience operation |
| `experience_meditation_run` | Manual trigger: quickly extract experiences from newly ingested documents | On demand after ingest |
| `experience_meditation_config_get/update` | Config: enable/disable auto-induction, set auto_publish | On demand |
| `experience_meditation_history` | Audit: view historical runs and output counts | During inspections |


## E9-E10 — Export and Batch Operations

No dedicated export tool currently exists. Alternatives:
- **Export**: `experience_list(kb_id)` to get all experience metadata → Agent formats as JSON/CSV/Markdown
- **Batch**: use the `knowledgebase-batch` skill's B6 step (export summary) or loop `experience_read` for bulk reads

## E11 — Decay Cycles
```
experience_apply_decay(kb_id) → applies rules and marks
```
| Rule | Condition | Effect |
|---|---|---|
| stale_unverified | created >30 days ∧ 0 applications | Retrieval downgrade |
| disputed | ≥3 reviews ∧ rating<2.0 | Down to P2 |
| unvetted | 0 reviews ∧ 0 applications | Max P1 |

**Run periodically** (e.g. weekly) to keep experiences fresh.

---

## Basic CRUD

### Create
```
experience_create(kb_id, title, scenario, category, problem, solution, result,
                  key_lessons, tags, severity, related_docs, prerequisites, metrics)
```
**Auto-completed after creation**: vector indexing (6 chunks) + metadata writes + disk file — all three consistent.

**⚠️ Must use valid enum values** (invalid values return HTTP 422):
- `category` ∈ {`best_practice`, `troubleshooting`, `lesson_learned`, `optimization`, `tip`, `workflow`, `decision`} (❌ not `bug`/`issue`)
- `severity` ∈ {`critical`, `important`, `normal`, `tip`} (❌ not `high`/`low`)
- Note `tip` is a valid value for both category and severity; `result` defaults to `success`

### Read / List / Update / Delete
```
experience_read(kb_id, exp_id)                                    → includes the .md body
experience_list(kb_id, scenario="", category="", tag="")          → sorted by rating
experience_update(kb_id, exp_id, **fields)                        → rebuilds the index automatically
experience_delete(kb_id, exp_id)                                  → permanent deletion
```

### Apply / Review (Dynamic Credibility)
```
experience_apply(kb_id, exp_id, user, context, result, notes)     → applied_count+1
experience_review(kb_id, exp_id, reviewer, rating, comment)       → recalculates rating_avg
```

### Search
| Method | Tool |
|---|---|
| Smart retrieval (recommended entry) | `experience_search_smart(query, top_k)` |
| Global cross-library | `experience_search_global(query, top_k)` |
| Metadata | `experience_search_global(kb_id, query, top_k)` |
| Vector semantic | `experience_search_global(kb_id, query, top_k)` |
| By scenario | `experience_list(kb_id, scenario="...")` |
| Smart reranking | `experience_rerank(query, experiences_json)` |
| Statistics | `experience_summary(kb_id)` / `experience_dashboard(kb_id)` |

---

## Recommended Workflows

### New Document Ingested → Auto-Enrich Experiences
```
Ingest A7 passed → experience_extract(kb_id, mode="heuristic", dry_run=True)
  → candidates ≥0.8 confidence: approve into the library
  → candidates <0.8: write to the draft pool, await review
```

### Incident Lookup → Experience-First Answer
```
experience_search_global(query) → answer directly from P0 experiences (seconds)
  → only supplement kb_search_two_stage if insufficient
```

### Document Updated → Experience Linkage
```
Document updated → experience_check_stale(kb_id)
  → stale experiences → experience_extract re-extraction → update_experience
```

### Periodic Maintenance
```
Weekly: experience_apply_decay(kb_id) to keep experiences fresh
Monthly: experience_dashboard(kb_id) to assess coverage and fill gaps
```

## E12 — Experience Auto Health Check and Cleanup [IMPORTANT]

**Trigger**: every `knowledgebase-verify` V8 step / monthly scheduled / linked after document deletion.

**Flow**: `experience_check_stale()` (empty kb_id = whole library) → stale/orphan detection → categorized handling → test pollution cleanup.

For the cleanup decision matrix (orphan/stale/test pollution/disputed conditions mapped to actions) and detailed detection flow, see [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E12.

> ⚠️ Test pollution detection must use `experience_list` (not summary, which only returns top 5), getting `created_at` for the >7d aging judgment.

---

## References

- Ingest flow reference: [knowledgebase-ingest](../knowledgebase-ingest/SKILL.md) — Ingest A7 final check, document parsing submission flow
- Graph linkage reference: [knowledgebase-graph](../knowledgebase-graph/SKILL.md) — knowledge graph and experience-associated retrieval
- Validation flow reference: [knowledgebase-verify](../knowledgebase-verify/SKILL.md) — whole-library integrity validation (triggers the E12 auto health check)
- Experience enhancement mechanism design: E0-E12 full lifecycle (extract/drafts/stale/sync/dashboard/decay), layered architecture (backend data/MCP orchestration/Agent LLM)

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Create experiences lacking problem/solution/lessons | Useless even if retrieval hits them | All three must be non-empty and specific |
| Skip the E2 quality gate | Low-quality experiences pollute the library | scenario/related_docs must be verified |
| Skip stale detection during maintenance | Outdated experiences mislead decisions | `check_stale` at least monthly |
| Judge library quality by summary/dashboard avg_rating | Unreviewed experiences (review_count=0) don't count into avg_rating but show in unrated_count; check both fields | Watch `reviewed_count`+`unrated_count`, not just avg_rating |
| Run `apply_decay` when nothing changed | Unnecessary | Once a week is enough |
| Write "experiences" as documents (long prose) | Experiences are single-point and structured | One problem→one solution→one lesson |
| Incident lookup without checking experiences first | Misses second-level answers | Incident-type: `experience_search_smart` first, `experience_search_global` as backstop, documents as supplement |
| Directly call experience_search_global for incident lookups | Loses smart intent recognition + multi-round downgrades | Use `experience_search_smart` as the recommended entry; `_global` only for manual control |
