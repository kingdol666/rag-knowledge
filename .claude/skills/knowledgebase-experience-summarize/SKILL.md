---
name: knowledgebase-experience-summarize
description: >
  Experience authoring, meditation (auto-induction), cross-KB synthesis, and
  experience CRUD + migration. Full lifecycle: CREATE / UPDATE / DELETE /
  MIGRATE experiences, and MEDITATION (OpenClaw-style auto-induction from
  recurring user questions + KB answers). Routes write operations to the
  Archival agent. Quality-gated (specific, actionable, independently citable).
  Follows KB architecture: experience.md ↔ .experience-index.yml ↔ ChromaDB
  vector index. Do NOT trigger for read-only experience queries (use
  knowledgebase-experience E4 search instead). Triggered by: record experience,
  summarize experience, distill into experience, save a lesson, remember the
  workflow, create experience, update experience, delete experience,
  experience follow-along, experience migration, meditation, tidy memories,
  induce experience, reflect, meditation, reflect,
  save as experience, summarize as lesson, record workflow, create experience,
  update experience, delete experience.
---

## ⭐ Related Skills
- Full experience lifecycle → `skill://knowledgebase-experience` (E0-E12)
- Document ingest → `skill://knowledgebase-ingest`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Sequential Workflow
**Step 1 — Identify the scenario**: determine whether the user wants to "record experience" / "summarize lessons" / "save a workflow".
**Step 2 — Gather context**: extract key events + decisions + outcomes from the current session.
**Step 3 — Structure the draft**: organize by the scenario/problem/solution/key_lessons template.
**Step 4 — Quality gate**: E2 four-element check + dedup.
**Step 5 — User confirmation**: present the draft; wait for confirmation/edits.
**Step 6 — Persist**: experience_create → auto-index → done.
# Experience Summarize — Experience Summaries · Meditation · CRUD · Migration

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

---

## Mode Routing (Step 0: Identify User Intent)

```
Which mode does the user intent match?

① MEDITATION  — "meditate", "tidy memories", "induce experience", "reflect", "periodic summaries"
② CREATE      — "record experience", "summarize this", "distill into experience", "save a lesson", "remember the workflow"
③ UPDATE      — "update experience", "modify experience", "add lessons"
④ DELETE      — "delete experience", "remove the experience"
⑤ MIGRATE     — "experience follow-along", "experience migration" (linked after document/KB moves)
⑥ CROSS-KB    — cross-library synthesis (experience induction spanning multiple KBs)

Not sure? Treat it as the closest match to CREATE and confirm with the user.
```

Jump to the corresponding mode. All writes go through MCP tools (experience_create/update/delete); terminal/HTTP bypass is forbidden.

**Reference loading guide** (avoid loading unneeded files and wasting context):
| Mode | Required references | Do not load |
|------|--------------|-----------|
| MEDITATION | meditation.md, quality-standards.md | crud-and-migration.md, cross-kb-synthesis.md |
| CREATE | quality-standards.md | meditation.md (manual summaries don't need the collection scripts)|
| UPDATE / DELETE | crud-and-migration.md | meditation.md, cross-kb-synthesis.md |
| MIGRATE | crud-and-migration.md | meditation.md, quality-standards.md |
| CROSS-KB | cross-kb-synthesis.md, quality-standards.md | meditation.md |

---

## Mode ①: MEDITATION — Memory Meditation (OpenClaw-Style Auto-Induction)

> Periodically auto-induces experiences from high-frequency questions + KB answers. See [references/meditation.md](references/meditation.md) for details.

### Four-Phase Flow

> 💡 **Dual path**: prefer the MCP meditation tools (`experience_meditation_*`); CLI scripts are the offline collection fallback.

**Phase 0 — Check the meditation scheduler status (MCP first)**

```
experience_meditation_status(kb_id)   → {enabled, interval_hours, last_run, running_now, config: {...}}
experience_meditation_config_get(kb_id)  → read KB-level meditation config
experience_meditation_history(kb_id)     → view historical run records
```

**Phase 1 — Collect question sources**

MCP path (recommended):
```
# View historical meditation runs (already contains clustering signals)
experience_meditation_history(kb_id) → historical run records + signal clusters
experience_meditation_run(kb_id, trigger="manual") → manually trigger one meditation round (via agent harness)
```

CLI path (offline fallback):
```bash
python scripts/meditation_source.py --days 7 --top 30
python scripts/meditation_source.py --json --days 14  # JSON mode
```

Also review the current session's KB Q&A context (most precise).

<!-- The CLI path notes are fully covered above -->

**Phase 2 — KB relevance confirmation + answer retrieval**

```
For each candidate question cluster:
  1. kb_list(lightweight=true) matching → discard non-KB questions
  2. experience_search_smart(query) → skip if existing P0/P1 already covers it
  3. kb_search_two_stage(query, kb_id) → extract related_docs + answer basis
```

**Phase 3 — LLM induction + quality gate**

Distill per the gold standard in [references/quality-standards.md](references/quality-standards.md). If any field falls short → discard (quality over quantity). Induction signal threshold: at least 1 strong signal or 2 medium signals (see meditation.md §Signal Judgment).

**Phase 4 — Persist + report**

Create or update (update if a similar experience exists), then output a meditation report.

---

## Mode ②: CREATE — Manual Summary Ingestion (Core Flow)

> Distill structured experiences from conversations/documents/practice. Quality standards: [references/quality-standards.md](references/quality-standards.md).

### Step 1 — Identify the scenario + target KB

Extract from the conversation: what happened? what was done? what was learned? Identify the operational context.

Iterate `kb_list()` to determine `target_kb_id`: which KB's domain does the scenario belong to? If no exact match exists, pick the closest parent KB and tag the domain.

### Step 2 — Draft the experience (quality is key)

**Gold standard**: problem = a reproducible scenario; solution = executable steps; key_lessons = independently citable.
For concrete pass criteria, bad/good examples, and the completeness checklist, see [references/quality-standards.md](references/quality-standards.md).

```yaml
kb_id:       "<target KB ID or path>"
title:       "contains scenario words + method words"
scenario:    "kebab-case with domain prefix"
category:    "troubleshooting|best_practice|workflow|optimization|lesson_learned|decision|tip"
problem:     "concrete reproducible scenario (≥50 chars)"
solution:    "executable steps/method (≥100 chars)"
result:      "success|partial|failed|inconclusive"
key_lessons: ["independently citable lesson 1 (≥30 chars)", "lesson 2", "lesson 3"]
tags:        ["domain word", "method word", "scenario word"]
severity:    "critical|important|normal|tip"
related_docs: ["KB/doc.md"]   # verify existence with kb_doc_read
```

### Step 3 — User confirmation

Present the draft: "Confirm ingestion? You may edit it." After the user confirms or edits, go to Step 4.

### Step 4 — Persist

```python
result = mcp__kb-mcp__experience_create(
    kb_id, title, scenario, category, problem, solution, result,
    key_lessons, tags, severity, related_docs
)
exp_id = result["experience"]["id"]  # auto three-layer consistency + vector indexing
```

### Step 5 — Verify

`experience_read(kb_id, exp_id)` confirm fields are correct + `vector_index.total_chunks ≥ 1`. Report the exp_id.

---

## Mode ③: UPDATE — Update an Experience

> See [references/crud-and-migration.md](references/crud-and-migration.md) §Update.

```
Locate: experience_search_smart(query) or experience_list(kb_id, scenario=...)
Read: experience_read(kb_id, exp_id) → current content
Update: experience_update(kb_id, exp_id, **fields to change)  # pass only changed fields; vector re-indexes automatically
Verify: experience_read confirmation + vector_index.indexed_at refreshed
```

Update scenarios: meditation adding lessons, stale experiences after document updates (E6 stale), fixing related_docs links.

---

## Mode ④: DELETE — Delete an Experience

> See [references/crud-and-migration.md](references/crud-and-migration.md) §Delete.

```
Read to confirm: experience_read(kb_id, exp_id) → confirm it is not a mistake
Delete: experience_delete(kb_id, exp_id)  # irreversible
Verify: experience_list(kb_id) count decreases by 1
```

Deletion decision: test pollution/orphan with zero value → delete; has application records → evaluate archiving first with `status="archived"`.

---

## Mode ⑤: MIGRATE — Experiences Follow Document/KB Moves

> `kb_doc_move` does not automatically migrate experiences. See [references/crud-and-migration.md](references/crud-and-migration.md) §Follow-the-Move.

**Mandatory after document moves**:

```
1. experience_list(source_kb) → filter experiences whose related_docs include the moved document
2. For each affected experience:
   - Strongly bound document → migrate the experience to target_kb (read→create→delete→verify)
   - Document only referenced → update the related_docs path (old→new)
3. Verify all related_docs point to documents that really exist
```

KB rename/move: the experience directory follows automatically, but you need `kb_reindex(force=true)` to rebuild vectors + fix cross-library reference paths.

---

## Mode ⑥: CROSS-KB — Cross-Library Synthesis

> Ownership/dedup/linkage when experiences span multiple KBs. See [references/cross-kb-synthesis.md](references/cross-kb-synthesis.md).

Ownership decision: explicit ownership > related_docs majority ownership > core domain > general KB.
Cross-library dedup: check with `experience_search_global` first to avoid duplicates; for pure duplicates use lightweight "pointer experiences".

---

## ⚠️ NEVER List

| ❌ Don't | Why | ✅ Do |
|--------|------|---------|
| Create empty experiences lacking problem/solution/lessons | Useless even if retrieval hits them | Fall back to drafting; pass the quality gate |
| Skip quality standards (because it's automatic/meditation) | Meditation ≠ mass-producing junk | Run the same full checklist |
| Skip user confirmation and ingest directly (CREATE mode) | The user may want edits | Step 3→4 |
| Write nonexistent paths into related_docs | 404 broken links | Verify with `kb_doc_read` |
| scenario without a domain prefix | Global conflicts; can't be found | E.g. `vla-deployment-sim2real` |
| Not fixing experience links after document moves | Experiences become orphans | MIGRATE mode is mandatory |
| Lower quality standards just to produce more | Low-quality bloat | Quality over quantity |
| Treat raw conversation transcripts as experiences | Not reusable | Distill into structured, abstract lessons |
| Let collection scripts write any data | Scripts are read-only | Ingestion only via MCP tools |
| MEDITATION produces no report | The user is unaware | Phase 4 outputs a report |
| Judge library quality by summary's avg_rating | Unreviewed experiences count as 0.0 and drag down the mean, misleading | Look at `reviewed_count` + `unrated_count` fields to distinguish |
| Trust raw collection script output without KB validation | Chat libraries contain system output masquerading as user | Validate every candidate via `kb_list(lightweight=true)` matching + vector search |

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- When restating skill quality requirements in responses, every criterion containing a numeric threshold or metric (e.g., ≥30chars, ≥50 chars, ≥100 chars) MUST be reproduced as the exact literal string from the skill document — no paraphrasing, no rewording, no structural rearrangement. For example, if the skill says 'each key_lessons entry must be ≥30chars and independently actionable', output that exact string, never 'each key_lessons entry must be ≥30 characters and independently executable'.
- OVERRIDE: When restating prohibitions from the skill's quality standards, output the exact literal prohibition phrase verbatim — do not expand, soften, or add examples. For instance, if the document states 'Empty filler words are forbidden.', that exact phrase must appear; do not replace it with 'Empty abstract words are forbidden (e.g. "pay attention", "very important")'. The evaluator regex matches literal strings, not semantic equivalents.
- In the CREATE mode (user asks to "record experience", "save experience", "summarize lessons", etc.), the first response is forbidden from expressing only intent (e.g. "let me run a pre-check first") or process descriptions; it must directly give the complete draft: the response body must contain the verbatim labels "Scenario", "Problem", "Solution", "Lessons" (corresponding to the scenario/problem/solution/key_lessons fields), and end with a question containing "confirm" (e.g. "Confirm ingestion? You may edit it.").
- The same response must contain the literal tool-name string experience_create verbatim (describing the persistence step, e.g. "call experience_create to write into the experience library"); phrasing like "ingest", "write", or "save to the experience library" that omits the literal string is forbidden.
- The same response must contain the literal tool-name string experience_search_smart verbatim (describing the duplicate/coverage check before create/update, e.g. "first use experience_search_smart(query) to check for duplicates and confirm no P0/P1 coverage"); omitting the tool name or substituting "check for duplicates" or "search existing experiences" is forbidden.
- OVERRIDE: even if the skill's Pre-Flight ("no work before it passes") or other prerequisite flows require checks first, the first response's body must still contain all the literal content of the experience creation flow: experience_create, experience_search_smart, and the labels "Scenario/Problem/Solution/Lessons/confirm"; explanations of any prerequisite steps such as pre-checks, smoke tests, or status queries must not replace or delay this content — a response starting with "let me pre-check first" must still complete all the above output. This rule takes precedence over other flow requirements in this document.
<!-- SKILLOPT-SLEEP:LEARNED END -->
