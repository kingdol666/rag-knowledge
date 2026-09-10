---
name: knowledgebase-batch
description: >
  High-volume batch operations. B1→B7: bulk tag migration, bulk description updates, directory mass ingestion (file-type routing), mass document move, cross-KB dedup, export summary, graph rebuild. All batch ops follow survey→plan→confirm→execute→verify. Triggered by: batch, all documents, everything, large-scale, batch operations, batch, bulk, mass, all documents, every KB, repetitive, full volume, one-shot processing, modify uniformly.
---

# Knowledge Batch — High-Volume Operations

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

---


## ⭐ Related Skills
- Single-document ingest → `skill://knowledgebase-ingest` (A0-A9 pipeline)
- KB management → `skill://knowledgebase-manage`
- Organize & restructure → `skill://knowledgebase-organize`
- Validation & verification → `skill://knowledgebase-verify`
- Graph rebuild → `skill://knowledgebase-graph`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Sequential Workflow
**Step 1 — Pre-Flight check**: run the mcp-preflight-check one-probe double-check; if not ready, silently kb_project_start to bring services up.
**Step 2 — Survey scope confirmation**: kb_list() + kb_get_documents() confirm the operation scope and estimate target scale (document count/KB count).
**Step 3 — Operation-type routing**: match the user request to B1-B7 batch operation types; combine types if needed.
**Step 4 — Plan presentation**: show the user a dry_run preview + batching strategy (20 per batch) + rate limits; wait for confirmation.
**Step 5 — B1 bulk tag migration**: kb_tags_list() → build tag mapping → kb_doc_update_tags() 30 per batch → kb_doc_get_by_tag() verification.
**Step 6 — B2 bulk description update**: identify weak descriptions → kb_doc_read(2000 chars) → four-element content descriptions → kb_doc_update_meta() 10-15 per batch.
**Step 7 — B3 directory mass ingestion**: parse_doc_batch(20 per batch) → A0 dedup + A2-Q check + A3b tag gate + A3c description gate + A6 indexing + A7 final check.
**Step 8 — B4 mass document move**: kb_doc_move() + kb_index_document(force=true) → kb_search_stats() verification on both source and target.
**Step 9 — B5 cross-KB dedup**: kb_search_vector(score_threshold=0.85) fingerprint dedup → user confirmation → kb_doc_delete().
**Step 10 — B6 export summary**: kb_list() + kb_get_documents() → statistics table (doc count/tag coverage/index coverage/top docs).
**Step 11 — B7 full graph rebuild**: kb_graph_build(kb_id="", force=true) → kb_graph_stats() verify node/edge counts.
**Step 12 — Execute in batches**: 20 per batch, record a checkpoint per completed batch, verify success rate.
**Step 13 — Verify final check**: sample 20% + before/after statistics comparison (doc count/tag count/index coverage).

## Mental Framework: Which Batch Operation? ⭐

```
User asks for "batch/all/everything"
    │
    ├── Modify tags uniformly? → B1 Bulk Tag Migration
    ├── Add descriptions uniformly? → B2 Bulk Description Update
    ├── Mass ingest from a directory? → B3 Directory Mass Ingestion
    ├── Batch move documents to another KB? → B4 Mass Document Move
    ├── Dedup the whole library? → B5 Cross-KB Dedup
    ├── Export a whole-library overview? → B6 Export Summary
    └── Rebuild the graph for the whole library? → B7 Graph Rebuild
```

### Pre-Batch Self-Check

| Question | Consequence if skipped |
|------|------------|
| How big is the target scope? (10 docs or 1000?) | Timeouts / resource exhaustion |
| Can you `dry_run` pre-check? | Irreversible changes with no rollback |
| Rate limits? How much concurrency can the tools take? | Mid-run failures are hard to recover |
| Need batching + resumable checkpoints? | Starting over wastes time |

---

## B1 — Bulk Tag Migration

1. `kb_tags_list()` — current vocabulary
2. Build the tag mapping: old→new, merge duplicates, split overly generic tags
3. For each KB: `kb_get_documents(kb_id)` → filter documents containing the target tags
4. For each document: `kb_doc_update_tags(kb_id, doc_path, new_tags)`
5. Verify: `kb_doc_get_by_tag(new_tag)` — confirm document counts

### Bulk Tag Cautions
- Execute in batches (30 documents at a time) to prevent timeouts
- Verify success rate after each batch and log it
- Flag failing documents individually; don't wait for everything to fail

---

## B2 — Bulk Description Update

1. `kb_get_documents(kb_id)` — identify weak-description documents (empty/filename/generic)
2. For each document, read 2000 chars: `kb_doc_read(kb_id, doc_path, max_chars=2000)`
3. Generate content-based descriptions per [description-guide.md](../knowledgebase-ingest/references/description-guide.md)
4. For each document: `kb_doc_update_meta(kb_id, doc_path, description=new_desc)`
5. Verify: randomly sample 20% of documents, `kb_doc_read` 500 chars to confirm the description matches content

### Bulk Description Cautions
- For large libraries (>50 documents), batch in groups of 10-15
- Delegate sub-agents to generate descriptions in parallel (split by KB)
- Self-check each generated description against the four elements (subject/method/scenario/data)

---

## B3 — Directory → KB Mass Ingestion

> **⭐ Mandatory quality gates**: B3 batch ingestion **must not bypass** the Ingest quality gates. Every document must pass Ingest A0-A7-equivalent checks.
> Batching is an optimization of "quantity" (parallel/batched), not a downgrade of "quality". See [knowledgebase-ingest](../knowledgebase-ingest/SKILL.md) A0-A7 for details.

1. Survey the directory: list all files, classify by type
2. **A0 dedup (mandatory per file)**: `kb_search_vector(query=<filename + first 200 chars signature>, score_threshold=0.85)` → a hit ≥0.85 means skip (already exists)
3. File-type routing:
   - PDF/DOCX/PPTX/images → `parse_doc_batch(file_paths=[...], use_ocr=true)` (non-blocking)
   - MD/TXT/JSON/YAML/code → read directly
   - Binary → `fs_upload_file(file_path, parent_id)`
4. Wait for all parsing tasks to complete → **A2-Q parse quality check** (garbled text/empty body/binary residue → reject ingestion)
5. Store: `kb_doc_save_parsed(parent_id, task_id, description)` (parsed documents must use save_parsed; kb_doc_create is forbidden)
6. **A3b tag quality gate**: every document's tags pass [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md) T1 blocklist + T2 normalization + T3 content readback
7. **A3c description quality gate**: every document's description passes the four elements (subject/method/scenario/data) + content readback
8. For every new document: `kb_index_document` + `kb_doc_update_tags`
9. **A6-V index verification**: `kb_search_stats(kb_id)` confirm the collection is correct + chunks ≥ 1
10. Verify: `kb_search_stats(kb_id)` — confirm chunk count; **A7 sampling final check** (randomly kb_doc_read 20% of documents to confirm content/tags/descriptions are consistent)

### Directory Ingestion Cautions
- When parsing >10 files, always use `parse_doc_batch` (single task_id management)
- Submit parsing in batches (20 per batch) to avoid MCP tool timeouts
- Poll the task queue status at intervals ≥5 seconds
- **Quality gates must not be skipped**: B3 is a batch wrapper around Ingest A0-A7, not a simplified version. Skipping A0 dedup → duplicate documents pile up; skipping A3b → tag pollution; skipping A6-V → vectors silently missing from the index

---

## B4 — Mass Document Move (KB→KB)

1. `kb_get_documents(source_kb_id)` — full document list
2. Confirm with the user
3. For each document: `kb_doc_move(doc_path, target_kb_id)` → `kb_index_document(target_kb_id, new_path)`
4. `kb_search_stats(target_kb_id)` + `kb_get_documents(source_kb_id)` — verify

### Bulk Move Cautions
- Do not delete a non-empty source KB (user decides after migration completes)
- After moving, reindex with `force=true` to ensure the collection UUID updates

---

## B5 — Cross-KB Dedup

> ⚠️ Note: complexity is O(n²) when the KB count is large (each pair of KBs compared). Optimization strategy: first hash documents by name into buckets (only compare same-named ones); when cross-KB pairs exceed 100, use `kb_search_vector` fingerprint dedup instead of pairwise comparison.

1. `kb_list()` → all KBs
2. Optimized path (recommended): `kb_search_vector(query=doc_name + first 200 chars signature, score_threshold=0.85)` → high-score candidates are suspected duplicates
3. Full path (small scale): preliminary filename filter for same-named documents → read 500 chars and compare → >80% overlap marks a duplicate
4. Mark duplicates → user confirmation → `kb_doc_delete(kb_id, doc_path)`
5. Verify: search to confirm no duplicate titles remain

---

## B6 — Export Summary

1. `kb_list()` + each KB's `kb_get_documents`
2. Output table: KB name | doc count | total size | tag coverage | vector/graph index coverage | top docs

---

## B7 — Graph Rebuild

1. `kb_list()` → all KB IDs
2. `kb_graph_build(force=true)` — batch rebuild (empty kb_id = whole library)
3. Verify: `kb_graph_stats()` → check node/edge counts are reasonable

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Run a batch without surveying first | Blast radius exceeds expectations — batches are irreversible amplifiers | First `kb_list`/`kb_get_documents` to confirm scope and show the user |
| Execute destructive batches without user confirmation | Deleting/moving 100 documents at once — errors can't be rolled back | survey→plan→**confirm**→execute four steps; confirmation comes first |
| Attempt to parse 100 PDFs at once | MCP 30s timeout — tasks pile up and all fail | Submit `parse_doc_batch` in batches (20 per batch); wait for each batch to finish |
| Skip verification after batch operations | Partial failures silently lost — user assumes full success | Sample 20% for verification + before/after statistics |
| Not verifying that tag mapping targets exist | `kb_doc_get_by_tag` returns empty — the mapping points at nonexistent tags | Check with `kb_tags_list()` beforehand that target tags are in the vocabulary |
| Ignore dedup in directory mass ingestion | Many duplicate documents — ChromaDB collection bloat | Fingerprint dedup with `kb_search_vector` before ingesting (skip if ≥0.85) |
| B3 batch ingestion skips quality gates | "Batch" ≠ "lower quality" — junk tags/descriptions are hard to clean later | Per document pass A0 dedup + A3b tags + A3c description gates |
| No checkpoints | Mid-run failure means starting over — 80 of 100 files done then all redone | 20 per batch; record progress after each batch completes |
