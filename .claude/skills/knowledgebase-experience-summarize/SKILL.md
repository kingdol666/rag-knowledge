---
name: knowledgebase-experience-summarize
description: "Experience authoring, meditation (auto-induction), cross-KB synthesis, and experience CRUD + migration. Full lifecycle: CREATE / UPDATE / DELETE / MIGRATE experiences, and MEDITATION (OpenClaw-style auto-induction from recurring user questions + KB answers). Routes write operations to the Archival agent. Quality-gated (specific, actionable, independently citable). Follows KB architecture: experience.md ↔ .experience-index.yml ↔ ChromaDB vector index. Do NOT trigger for read-only experience queries (use knowledgebase-experience E4 search instead). Triggered by: record experience, summarize experience, distill into experience, save a lesson, remember the workflow, create experience, update experience, delete experience, experience follow-along, experience migration, meditation, tidy memories, induce experience, reflect, meditation, reflect, save as experience, summarize as lesson, record workflow, create experience, update experience, delete experience."
---

## Related skills

- Full experience lifecycle (E0-E12 retrieval/stale/decay) → `skill://knowledgebase-experience` · Document ingest → `skill://knowledgebase-ingest` · Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Execution model (mandatory, first step of any job)

**Executor: Archival agent** — delegate via `task`; delegation template + three-role execution model + combined-task boundaries → [execution-model.md](../knowledgebase/references/execution-model.md). **Pre-Flight**: one-probe double-check `kb_project_status` → branch handling → smoke test — no work before it passes → [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) before operating; MCP-first (no terminal/HTTP bypass) → [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

## Mode routing (Step 0: identify user intent)

```
① MEDITATION — "meditate", "tidy memories", "induce experience", "reflect", "periodic summaries"
② CREATE      — "record experience", "summarize this", "distill into experience", "save a lesson", "remember the workflow"
③ UPDATE      — "update experience", "modify experience", "add lessons"
④ DELETE      — "delete experience", "remove the experience"
⑤ MIGRATE     — "experience follow-along", "experience migration" (linked after document/KB moves)
⑥ CROSS-KB    — cross-library synthesis (experience induction spanning multiple KBs)
Not sure? Treat it as the closest match to CREATE and confirm with the user.
```
All writes go through MCP tools (`experience_create/update/delete`); terminal/HTTP bypass is forbidden. Reference loading (avoid loading unneeded files and wasting context): MEDITATION → [meditation.md](references/meditation.md) + quality-standards.md · CREATE → quality-standards.md · UPDATE/DELETE/MIGRATE → crud-and-migration.md · CROSS-KB → [cross-kb-synthesis.md](references/cross-kb-synthesis.md) + quality-standards.md.

## Mode ①: MEDITATION — memory meditation (OpenClaw-style auto-induction)

Auto-induces experiences from high-frequency questions + KB answers (full detail → [references/meditation.md](references/meditation.md)); dual path: prefer the MCP `experience_meditation_*` tools, CLI scripts are the offline read-only collection fallback. **Phase 0 — Scheduler status (MCP first)** + **Phase 1 — Collect question sources**:
```text
experience_meditation_status(kb_id)                → {enabled, interval_hours, last_run, running_now, config}
experience_meditation_config_get(kb_id)            → KB-level meditation config
experience_meditation_history(kb_id)               → historical runs + signal clusters
experience_meditation_run(kb_id, trigger="manual") → manually trigger one round (via agent harness)
```
CLI fallback: `python scripts/meditation_source.py --days 7 --top 30` (or `--json --days 14`). Also review the current session's KB Q&A context (most precise).

**Phase 2 — KB relevance confirmation + answer retrieval** (per candidate question cluster):
```text
kb_list(lightweight=true) matching → discard non-KB questions
experience_search_smart(query) → skip if existing P0/P1 already covers it
kb_search_two_stage(query, kb_id) → extract related_docs + answer basis
```

**Phase 3 — LLM induction + quality gate**: distill per the gold standard in [references/quality-standards.md](references/quality-standards.md); any field short → discard (quality over quantity); signal threshold: at least 1 strong signal or 2 medium signals (meditation.md §Signal Judgment). **Phase 4 — Persist + report**: create or update (update if a similar experience exists), then output a meditation report.

## Mode ②: CREATE — manual summary ingestion (core flow)

**Step 1 — Scenario + target KB**: extract from the conversation what happened / was done / was learned; iterate `kb_list()` to pick `target_kb_id` (closest parent KB if no exact match, tag the domain).

**Step 2 — Draft (quality is key)** — gold standard: problem = a reproducible scenario; solution = executable steps; key_lessons = independently citable. Pass criteria + bad/good examples + completeness checklist → [references/quality-standards.md](references/quality-standards.md).
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

**Step 3 — User confirmation**: present the draft — "Confirm ingestion? You may edit it." — wait for confirmation/edits.

**Step 4 — Persist**:
```python
result = mcp__kb-mcp__experience_create(
    kb_id, title, scenario, category, problem, solution, result,
    key_lessons, tags, severity, related_docs
)
exp_id = result["experience"]["id"]  # auto three-layer consistency + vector indexing
```

**Step 5 — Verify**: `experience_read(kb_id, exp_id)` — fields correct + `vector_index.total_chunks ≥ 1`; report the exp_id.

## Mode ③: UPDATE — update an experience

```text
Locate: experience_search_smart(query) or experience_list(kb_id, scenario=...)
Read: experience_read(kb_id, exp_id) → current content
Update: experience_update(kb_id, exp_id, **fields)  # only changed fields; vector re-indexes automatically
Verify: experience_read confirmation + vector_index.indexed_at refreshed
```
Scenarios: meditation adding lessons, stale after document updates (E6), fixing related_docs. Details → [references/crud-and-migration.md](references/crud-and-migration.md) §Update.

## Mode ④: DELETE — delete an experience

```text
Read to confirm: experience_read(kb_id, exp_id) → confirm it is not a mistake
Delete: experience_delete(kb_id, exp_id)  # irreversible
Verify: experience_list(kb_id) count decreases by 1
```
Decision: test pollution/orphan with zero value → delete; has application records → evaluate archiving first (`status="archived"`). Details → crud-and-migration.md §Delete.

## Mode ⑤: MIGRATE — experiences follow document/KB moves

`kb_doc_move` does NOT automatically migrate experiences — this mode is mandatory after document moves (details → crud-and-migration.md §Follow-the-Move):
```text
1. experience_list(source_kb) → filter experiences whose related_docs include the moved document
2. Per affected experience: strongly bound document → migrate to target_kb (read→create→delete→verify)
   document only referenced → update the related_docs path (old→new)
3. Verify all related_docs point to documents that really exist
```
KB rename/move: the experience directory follows automatically, but run `kb_reindex(force=true)` to rebuild vectors + fix cross-library reference paths.

## Mode ⑥: CROSS-KB — cross-library synthesis

Ownership: explicit ownership > related_docs majority ownership > core domain > general KB. Dedup: check `experience_search_global` first to avoid duplicates; pure duplicates → lightweight "pointer experiences". Details → [references/cross-kb-synthesis.md](references/cross-kb-synthesis.md).

## Never

- Create experiences lacking problem/solution/lessons — useless even when retrieved; fall back to drafting and pass the quality gate.
- Skip quality standards because it's automatic/meditation — meditation ≠ mass-producing junk; run the same full checklist.
- Skip user confirmation and ingest directly (CREATE mode) — the user may want edits; Step 3 → 4.
- Write nonexistent paths into related_docs — 404 broken links; verify with `kb_doc_read`.
- Use a scenario without a domain prefix — global conflicts, can't be found; e.g. `vla-deployment-sim2real`.
- Leave experience links unfixed after document moves — experiences become orphans; MIGRATE mode is mandatory.
- Lower quality standards just to produce more — quality over quantity.
- Treat raw conversation transcripts as experiences — not reusable; distill into structured, abstract lessons.
- Let collection scripts write any data — scripts are read-only; ingestion only via MCP tools.
- Run MEDITATION without producing a report — the user is unaware; Phase 4 outputs a report.
- Judge library quality by summary's avg_rating — unreviewed experiences count 0.0 and drag down the mean; look at `reviewed_count` + `unrated_count`.
- Trust raw collection-script output without KB validation — chat libraries contain system output masquerading as user; validate every candidate via `kb_list(lightweight=true)` matching + vector search.

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
