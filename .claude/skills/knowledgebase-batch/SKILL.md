---
name: knowledgebase-batch
description: High-volume and batch operations for knowledge base management. B1-B7: bulk tag migration, bulk description updates, directory-to-KB mass ingestion (file-type routing, no splitting), mass document move between KBs, cross-KB dedup, export summary, and graph rebuild. Invoked by Archival when operations involve multiple documents, batch processing, or repetitive updates. Trigger keywords: 批量, 所有文档, 全部, 大规模, 批量操作, 批量标签, batch, bulk, mass, all documents, every KB, repetitive, 全量, 一次性处理, 统一修改.
---

# Knowledge Batch — Bulk & Batch Operations

## B1 — Bulk Tag Management

`kb_tags_list()` + `kb_list()` to survey. Add tag: for each untagged doc, `kb_doc_update_tags()`. Replace tag: `kb_doc_get_by_tag("old")` to find docs, then replace in each. Remove tag: same find-and-replace pattern, drop the old tag. Verify: `kb_doc_get_by_tag("old")` returns 0, `kb_doc_get_by_tag("new")` returns migrated docs.

## B2 — Bulk Description Updates

`kb_list()` to find KBs with empty or placeholder descriptions. Read 1-2 representative docs via `kb_doc_read(kb_id, doc_path, max_chars=300)`. Update: `kb_update(kb_id, description="1-3 sentences: domain + content types + language")`. For doc-level descriptions: `kb_get_documents`, then `kb_doc_read` → `kb_doc_update_meta` for empty/placeholder only. Sample if >20 docs — don't rewrite everything.

## B3 — Directory-to-KB Mass Ingestion (file-type routing, no splitting)

`Glob()` to discover files. Classify by extension:

### Parse-path files (`.pdf .docx .xlsx .pptx .jpg .png .bmp .tiff`)
```
# Single file: parse_doc(file_path, use_ocr=true) → poll parse_task_status
# Batch (≥3 files): parse_doc_batch(file_paths=[...], use_ocr=true) → single task_id, poll parse_task_status

# After parse done, for each file's markdown result:
kb_doc_create(kb_id, name="doc.md", content="<parsed markdown>", description="<real description>")
kb_index_document(kb_id, doc_path="<from create result>")
# Or: kb_index_document(doc_id="<UUID from create result>")
```

### Direct-path files (`.md .txt .csv .json .yaml .html .py .js .ts .sh .log .xml`)
```
# Read file content, then:
kb_doc_create(kb_id, name="doc.md", content="<text>", description="<real description>")
kb_index_document(kb_id, doc_path="<from create result>")
# Or: kb_index_document(doc_id="<UUID from create result>")
```

### Binary files (images, archives, etc.)
```
fs_upload_file(file_path, parent_id=kb_id, description="<desc>")
# No vector index for binary files
```

**No document splitting.** Each file is ingested as a single document regardless of size.
Report: discovered, parsed, direct-stored, binary-uploaded counts with parse failures.

## B4 — Mass Document Move

`kb_get_documents(source)` → `kb_doc_move(doc_path, target_kb_id)` each doc to target. Warn if >50 docs. Verify source count decreased, target count increased by N. If source empty, ask: "Delete empty source KB?"

**After mass move**: rebuild index for moved docs at new path:
```
for each moved doc:
  kb_index_document(kb_id=target, doc_path=new_path)
```
Optionally clean old graph: `kb_graph_delete_document(doc_path=old_path)` per doc.

## B5 — Cross-KB Dedup

`kb_list()` → `kb_get_documents` per KB. Compare filenames across KBs. Same name + similar size → read 500 chars to confirm. `kb_doc_delete` from wrong KB. Retain in domain-correct KB. Never delete without content comparison.

## B6 — Export Summary

`kb_list()` + `kb_tags_list()` + `fs_get_tree()` + `fs_get_count()`. Per KB: `kb_get_documents` for doc count, size, tags, dates. Write to `.claude/collection-report.md` via Write tool. Include: overview numbers, per-KB table, tag list, graph health (`kb_graph_stats`), vector coverage (`kb_search_stats`).

## B7 — Graph Rebuild

After batch ops, run `kb_graph_build_all(force=false)` or per-impacted KB: `kb_graph_build_kb(kb_id, force=true)`. Verify `kb_graph_stats()` → edge count increased with shared_tag relations.
