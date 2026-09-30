---
name: knowledgebase-batch
description: "High-volume batch operations. B1→B7: bulk tag migration, bulk description updates, directory mass ingestion (file-type routing), mass document move, cross-KB dedup, export summary, graph rebuild. All batch ops follow survey→plan→confirm→execute→verify. Triggered by: batch, all documents, everything, large-scale, batch operations, batch, bulk, mass, all documents, every KB, repetitive, full volume, one-shot processing, modify uniformly."
---
# Knowledge Batch — High-Volume Operations

**Executor: Archival agent** — delegate via `task` (delegation template + three-role execution model + combined-task boundaries: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 94-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

Related: single-document ingest → `skill://knowledgebase-ingest` (A0-A9 pipeline) · KB management → `skill://knowledgebase-manage` · organize & restructure → `skill://knowledgebase-organize` · validation → `skill://knowledgebase-verify` · graph rebuild → `skill://knowledgebase-graph`.

## Sequential Workflow

**Step 1 — Pre-Flight check**: one-probe double-check; if not ready, silently kb_project_start to bring services up.
**Step 2 — Survey scope confirmation**: kb_list() + kb_get_documents() confirm the operation scope and estimate target scale (document count/KB count).
**Step 3 — Operation-type routing**: match the user request to B1-B7 batch types; combine types if needed.
**Step 4 — Plan presentation**: show a dry_run preview + batching strategy (20 per batch) + rate limits; wait for confirmation.
**Step 5 — B1 bulk tag migration**: kb_tags_list() → build tag mapping → kb_doc_update_tags() 30 per batch → kb_doc_get_by_tag() verification.
**Step 6 — B2 bulk description update**: identify weak descriptions → kb_doc_read(2000 chars) → four-element content descriptions → kb_doc_update_meta() 10-15 per batch.
**Step 7 — B3 directory mass ingestion**: parse_doc_batch(20 per batch) → A0 dedup + A2-Q check + A3b tag gate + A3c description gate + A6 indexing + A7 final check.
**Step 8 — B4 mass document move**: kb_doc_move() + kb_index_document(force=true) → kb_search_stats() verification on both source and target.
**Step 9 — B5 cross-KB dedup**: kb_search_vector(score_threshold=0.85) fingerprint dedup → user confirmation → kb_doc_delete().
**Step 10 — B6 export summary**: kb_list() + kb_get_documents() → statistics table (doc count/tag coverage/index coverage/top docs).
**Step 11 — B7 full graph rebuild**: kb_graph_build(kb_id="", force=true) → kb_graph_stats() verify node/edge counts.
**Step 12 — Execute in batches**: 20 per batch, record a checkpoint per completed batch, verify success rate.
**Step 13 — Verify final check**: sample 20% + before/after statistics comparison (doc count/tag count/index coverage).

Router: modify tags uniformly → B1 · add descriptions uniformly → B2 · mass ingest from a directory → B3 · batch move documents → B4 · dedup the whole library → B5 · export a whole-library overview → B6 · rebuild the whole-library graph → B7.

**Pre-batch self-check** (each skip has a cost): how big is the scope, 10 docs or 1000? (timeouts / resource exhaustion) · can you `dry_run` pre-check? (irreversible changes with no rollback) · rate limits / tool concurrency? (mid-run failures are hard to recover) · batching + resumable checkpoints? (starting over wastes everything).

## B1 — Bulk Tag Migration

1. `kb_tags_list()` — current vocabulary
2. Build the tag mapping old→new: merge duplicates, split overly generic tags
3. For each KB: `kb_get_documents(kb_id)` → filter documents containing the target tags
4. For each document: `kb_doc_update_tags(kb_id, doc_path, new_tags)`
5. Verify: `kb_doc_get_by_tag(new_tag)` — confirm document counts

Cautions: execute in batches of 30 documents to prevent timeouts; verify and log the success rate after each batch; flag failing documents individually.

## B2 — Bulk Description Update

1. `kb_get_documents(kb_id)` — identify weak-description documents (empty/filename/generic)
2. For each document, read 2000 chars: `kb_doc_read(kb_id, doc_path, max_chars=2000)`
3. Generate content-based descriptions per [description-guide.md](../knowledgebase-ingest/references/description-guide.md)
4. For each document: `kb_doc_update_meta(kb_id, doc_path, description=new_desc)`
5. Verify: randomly sample 20%, `kb_doc_read` 500 chars to confirm the description matches content

Cautions: libraries >50 documents batch in groups of 10-15; delegate sub-agents to generate descriptions in parallel (split by KB); self-check each description against the four elements (subject/method/scenario/data).

## B3 — Directory → KB Mass Ingestion

> **Mandatory quality gates**: B3 must not bypass the Ingest quality gates — every document passes A0-A7-equivalent checks. Batching optimizes "quantity" (parallel/batched), never "quality". See [knowledgebase-ingest](../knowledgebase-ingest/SKILL.md) A0-A7.

1. Survey the directory: list all files, classify by type
2. **A0 dedup (mandatory per file)**: `kb_search_vector(query=<filename + first 200 chars signature>, score_threshold=0.85)` → a hit ≥0.85 means skip (already exists)
3. File-type routing: PDF/DOCX/PPTX/images → `parse_doc_batch(file_paths=[...], use_ocr=true)` (non-blocking); MD/TXT/JSON/YAML/code → read directly; binary → `fs_upload_file(file_path, parent_id)`
4. Wait for all parsing tasks → **A2-Q parse quality check** (garbled text/empty body/binary residue → reject ingestion)
5. Store: `kb_doc_save_parsed(parent_id, task_id, description)` — parsed documents must use save_parsed; `kb_doc_create` is forbidden
6. **A3b tag quality gate**: every document's tags pass [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md) T1 blocklist + T2 normalization + T3 content readback
7. **A3c description quality gate**: four elements (subject/method/scenario/data) + content readback
8. For every new document: `kb_index_document` + `kb_doc_update_tags`
9. **A6-V index verification**: `kb_search_stats(kb_id)` — collection correct + chunks ≥ 1
10. Verify: `kb_search_stats(kb_id)` chunk count + **A7 sampling final check** (random `kb_doc_read` of 20% — content/tags/descriptions consistent)

Cautions: >10 files always `parse_doc_batch` (single task_id management); submit parsing 20 per batch (MCP tool timeouts); poll the task queue at intervals ≥5 seconds. Skipping gates has known costs: no A0 → duplicate documents pile up; no A3b → tag pollution; no A6-V → vectors silently missing from the index.

## B4 — Mass Document Move (KB→KB)

1. `kb_get_documents(source_kb_id)` — full document list
2. Confirm with the user
3. For each document: `kb_doc_move(doc_path, target_kb_id)` → `kb_index_document(target_kb_id, new_path)`
4. `kb_search_stats(target_kb_id)` + `kb_get_documents(source_kb_id)` — verify

Cautions: do not delete a non-empty source KB (user decides after migration completes); reindex with `force=true` so the collection UUID updates.

## B5 — Cross-KB Dedup

> Complexity is O(n²) when the KB count is large (each pair compared). Optimize: bucket documents by filename (compare same-named only); when cross-KB pairs exceed 100, use `kb_search_vector` fingerprint dedup instead of pairwise comparison.

1. `kb_list()` → all KBs
2. Recommended path: `kb_search_vector(query=doc_name + first 200 chars signature, score_threshold=0.85)` → high-score candidates are suspected duplicates
3. Full path (small scale): preliminary same-name filename filter → read 500 chars and compare → >80% overlap marks a duplicate
4. Mark duplicates → user confirmation → `kb_doc_delete(kb_id, doc_path)`
5. Verify: search to confirm no duplicate titles remain

## B6 — Export Summary

`kb_list()` + each KB's `kb_get_documents` → table: KB name | doc count | total size | tag coverage | vector/graph index coverage | top docs.

## B7 — Graph Rebuild

`kb_list()` → all KB IDs → `kb_graph_build(force=true)` (empty kb_id = whole library) → verify `kb_graph_stats()`: node/edge counts reasonable.

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
