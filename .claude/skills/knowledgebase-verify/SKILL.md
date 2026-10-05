---
name: knowledgebase-verify
description: "Knowledge base integrity and quality validation. V1→V9: three-way metadata consistency (disk↔.tree-fs.json↔.knowledge-base.yml), document integrity, parse quality, index coverage+repair, scorecard (max 115), report, tag health (orphan+trash detection), experience health (stale+orphan+test pollution), auto-fix (repeat collections, orphan tags, missing indexes). Read-only by default; repair requires explicit instruction. Triggered by: validate, cross-check, integrity, health check, verify, check, consistency, verify, validate, integrity, health check, quality audit, check KB, detect issues, audit the knowledge base."
---
# Knowledge Verify — Integrity & Quality

## Related skills
Organize/cleanup → `skill://knowledgebase-organize` (O1-O8) · Document/KB management → `skill://knowledgebase-manage` · Batch ops → `skill://knowledgebase-batch` (B1-B7) · Experience health detail → `skill://knowledgebase-experience` (V8) · Platform update → `skill://knowledgebase-update` · Architecture model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md).

## Sequential workflow (when the user requests validation/checking)
**Step 1 — Determine the validation scope**: quick check (V1+V5 10% sampling) / regular health (V1→V9) / deep audit (V1→V9 full).
**Step 2 — V1 three-layer metadata consistency**: kb_list() vs fs_get_tree() vs kb_get_documents() cross-validation.
**Step 3 — V2 document integrity**: per the sampling strategy, doc_read to check documents are readable.
**Step 4 — V3 parse quality**: check OCR/Markdown quality of PDF/DOCX-sourced documents.
**Step 5 — V4 index coverage+repair**: check vector index and graph index coverage.
**Step 6 — V5 scorecard**: compute the composite health score on the 115-point scale.
**Step 7 — V6 report**: output the total score + key findings + top recommendation.
**Step 8 — V7 tag health**: detect orphan tags and junk patterns.
**Step 9 — V8 experience health**: detect stale/orphan/test-polluted experiences.
**Step 10 — V9 auto-fix (requires user confirmation)**: fix detected issues.

Route by the stated focus: suspects metadata inconsistency → V1 · document fails to open/404 → V2 · garbled content after PDF parsing → V3 · document can't be found in search → V4 · "thorough audit" → V1→V9 full flow · a specific KB named → that KB's complete flow only.

## Execution contract
**Executor: Archival agent**, delegated via `task` (delegation template + three-role model: [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — `kb_project_status` one-probe double-check → branch handling → smoke test, per [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). Mental model: [kb-architecture.md](../knowledgebase/references/kb-architecture.md). MCP-first — no terminal/HTTP bypass ([skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5); tool names are prefixed per harness (`mcp__kb-mcp__*` in Claude). **Read-only by default**: V4/V7/V9 repair requires explicit user instruction — validation must not become operation.

## Validation strategy
| Scenario | Breadth | Depth | Time |
|------|------|------|------|
| Quick check | V1 + V5 stats only | 10% sampling | ~10s |
| Regular health check | V1→V9 | Normal sampling | ~60s |
| Deep audit | V1→V9 full | Every document | ~5min+ |
| Post-fix verification | V4 index + V5 score | Before/after comparison | ~30s |

## Freedom map
- V1-V4 detection / V5 scoring / V7 tag health — **mandatory**: complete flows, no skipped steps; scoring follows formulas, not subjectivity.
- V6 report / V8 experience health — **execute**: per template; prioritize findings by actual impact.
- V9 auto-fix — **judgment**: explicit user instruction required; reversible fixes batched, irreversible ones per-item.
- Sampling — **execute**: pick the ratio by library size; no full scans (>100 docs), no laziness (<10%).

## V1 — Three-Way Metadata Integrity (disk ↔ .tree-fs.json ↔ .knowledge-base.yml)
1. `kb_list()` vs `fs_get_tree()` — flag KBs with no tree node, orphan nodes, doc-count mismatches.
2. Per KB, `kb_get_documents(kb_id)` — check each doc has a matching file on disk via path cross-reference.
3. Flag phantom entries (metadata but no disk file) and orphan files (disk but no metadata).

UUID-level consistency is not directly compared: MCP tools cannot read the raw files, and every CRUD updates all three layers atomically — V1 relies on path cross-reference. Known normal behavior (not an inconsistency): `kb_get_documents()` may return more entries than `kb_list(lightweight=true)`'s `doc_count` — the extras are sub-KB containers (`file_type: knowledge-base`); separate levels with `fs_get_tree(max_depth=2)`.

## V2 — Document Integrity
`kb_get_documents(kb_id)` → sample `kb_doc_read` per the table. Flag: broken 404s, empty descriptions, untagged docs.

| Library size | Sampling ratio | Minimum samples |
|--------|---------|---------|
| 1-10 | 100% | all |
| 11-50 | 50% | at least 10 |
| 51-100 | 25% | at least 25 |
| >100 | 15% | at least 50 |

## V3 — Parse Quality
`kb_doc_read` 2000 chars, only on parsed documents (.pdf/.docx/.pptx-sourced — direct-created MD/TXT has no OCR traces). Flag: empty content (<100 chars), OCR garbage, binary residue, heading-only (no body). MinerU health: `backend_status()` (authoritative).

## V4 — Index Coverage & Repair (repair needs explicit instruction)
Vector: `kb_get_documents(kb_id)` → check `vector_index` per doc; `kb_search_stats(kb_id)` → check chunk counts. Repair: `kb_index_document(kb_id, doc_path)` or `kb_batch_index(kb_id, [paths], force=true)`.
Graph: `kb_graph_stats()` → check `neo4j_available`; `kb_graph_kb_overview(kb_id)` → doc_count vs actual. Repair: `kb_graph_build(kb_id, force=true)`; stale entries for deleted docs: `kb_graph_delete_document(doc_path)`.

## V5 — Scorecard (max 115)
| Dimension | Max | Scoring method |
|------|------|---------|
| Metadata consistency | 25 | matched entries / total entries × 25 |
| Document quality | 30 | sampled pass rate × 30 |
| Tag coverage | 25 | tagged documents / total documents × 25 |
| Description quality | 10 | content-based description ratio × 10 |
| Graph health | 15 | graph coverage × 15 |
| Vector coverage | 10 | vector index coverage × 10 |

## V6 — Report
Score + key findings + the single most cost-effective fix:

```text
## Validation Report: <KB name> — Total score: XX/115
| Dimension | Score | Status |        ← the six V5 rows with ✅/⚠️/❌
### Key Findings
- <finding 1> ...
### Top Recommendation
<the single most cost-effective fix>
```

## V7 — Tag Health
Detect 0-reference orphan tags and junk patterns (section titles/test residue). Preferred: `kb_tags_cleanup(dry_run=true)` — one O(M) scan of the whole library (measured <100ms for 151 tags) returning `{orphan_tags: [{tag, refs, reason}]}`; reason is `unreferenced` (0 document references) or `garbage_pattern` (section titles/test residue/special characters, via the web layer's `isGarbageTag`). Domain core words (PET/PVA/DL/RAG/polymer/embodied intelligence, …) are protected by MCP-layer protected_patterns even at 0 references. `dry_run=false` executes the cleanup (irreversible) — preview first.

## V8 — Experience Health
`experience_check_stale()` (empty kb_id = whole-library check) + `experience_dashboard(kb_id)` for every KB with experiences. Orphan (related docs deleted) → recommend `experience_delete` or updating `related_docs`; stale (docs updated, experience not synced) → `experience_sync_kb`; test pollution (rating=0, applied=0, age>7d) → cleanup; low quality (rating<2, review≥3 disputed) → review.

## V9 — Auto-Fix (requires user confirmation)
| Detected issue | Auto-fix path |
|------------|------------|
| Duplicate collection | kb_cleanup_orphan_collections(dry_run=false) |
| Orphan tags | kb_tags_cleanup(dry_run=false) |
| Document missing vector index | kb_index_document(kb_id, doc_path) |
| Document missing graph index | kb_graph_build(kb_id, force=false) |
| Metadata inconsistency | kb_reindex(kb_id, force=true) rebuild |
| Orphan experience | experience_delete(kb_id, exp_id) or experience_update(related_docs=[]) |
| Test experience pollution | experience_delete(kb_id, exp_id) (after confirmation) |

Only fix issues that are auto-detectable + auto-fixable; destructive operations (delete documents/delete KBs/merge KBs) require user confirmation.

## NEVER
- Run V4/V7/V9 repairs without user instruction — read-only violated, validation becomes operation; report results first, act only when the user says "fix".
- Judge KB health with `kb_list` alone — KB-level OK ≠ document-level OK; pair kb_get_documents + disk verification.
- Run large doc_read batches without progress reporting — >50 docs takes non-trivial time and looks hung; report "x/N checked".
- Skip all other checks when Neo4j is down — V1-V4/V6 don't depend on it; skip only V5 Graph Health and proceed.
- Emit score reports without fix recommendations — the user won't know what to fix first; V6 must contain the top recommendation.
- Trust `kb_list(lightweight=true)`'s `doc_count` as the real document count — it includes sub-KB container entries; filter by `file_type: knowledge-base` or confirm with fs_get_tree.
- Run V3 Parse Quality on non-parsed documents — MD/TXT direct-created docs have no OCR traces; only .pdf/.docx/.pptx.
- Emit a report with sampling below the minimum — small samples mask systemic issues; strictly follow the minimums (10/25/50).
