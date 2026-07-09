---
name: knowledgebase-batch
description: High-volume and batch operations for knowledge base management. B1-B7: bulk tag migration, bulk description updates, directory-to-KB mass ingestion (file-type routing, no splitting), mass document move between KBs, cross-KB dedup, export summary, and graph rebuild. Invoked by Archival when operations involve multiple documents, batch processing, or repetitive updates. Trigger keywords: 批量, 所有文档, 全部, 大规模, 批量操作, 批量标签, batch, bulk, mass, all documents, every KB, repetitive, 全量, 一次性处理, 统一修改.
---

# Knowledge Batch — High-Volume Operations

Each batch op follows: **survey → plan → confirm → execute → verify**.

## B1 — Bulk Tag Migration
1. `kb_tags_list()` — current vocabulary
2. Build tag mapping: old → new, merge duplicates, split generics
3. For each KB: `kb_get_documents(kb_id)` → filter docs with target tags
4. For each doc: `kb_doc_update_tags(kb_id, doc_path, new_tags)`
5. Verify: `kb_doc_get_by_tag(new_tag)` — confirm doc count

## B2 — Bulk Description Update
1. `kb_get_documents(kb_id)` — identify docs with empty/weak descriptions
2. Read 2000 chars per doc: `kb_doc_read(kb_id, doc_path, max_chars=2000)`
3. Generate content-based description per [description-guide.md](../knowledgebase-ingest/references/description-guide.md)
4. For each doc: `kb_doc_update_meta(kb_id, doc_path, description=new_desc)`
5. Verify: re-read 500 chars of a random sample

## B3 — Directory → KB Mass Ingestion
1. Survey directory: list all files, classify by type
2. File-type routing:
   - PDF/DOCX/PPTX/images → `parse_doc_batch(file_paths=[...], use_ocr=true)`
   - MD/TXT/JSON/YAML/code → read directly
   - Binary → `fs_upload_file(file_path, parent_id)`
3. Wait for all parse tasks, then store each via `kb_doc_save_parsed(parent_id, task_id, description)`
4. For each new doc: `kb_index_document` + `kb_doc_update_tags`
5. Verify: `kb_search_stats(kb_id)` — confirm chunk count

## B4 — Mass Document Move (KB→KB)
1. `kb_get_documents(source_kb_id)` — full doc list
2. Confirm with user
3. For each doc: `kb_doc_move(doc_path, target_kb_id)` → `kb_index_document(target_kb_id, new_path)`
4. `kb_search_stats(target_kb_id)` + `kb_get_documents(source_kb_id)` — verify

## B5 — Cross-KB Dedup
1. `kb_list()` → all KBs
2. For each KB pair: `kb_get_documents` → compare by name, then by content (500 chars)
3. Flag duplicates: same title or >80% content overlap
4. Confirm → keep one, delete others: `kb_doc_delete(kb_id, doc_path)`
5. Verify: no duplicate titles remain

## B6 — Export Summary
1. `kb_list()` + `kb_get_documents` per KB
2. Generate: KB name, doc count, total size, tag coverage, vector/graph index coverage, top docs by size
3. Output as table

## B7 — Graph Rebuild
1. `kb_list()` → all KB IDs
2. `kb_graph_build_all(force=true)` — batch rebuild
3. Verify: `kb_graph_stats()` → check node/edge counts
