---
name: knowledgebase-batch
description: High-volume and batch operations for knowledge base management. B1-B6: bulk tag migration, bulk description updates, directory-to-KB ingestion, mass document move between KBs, cross-KB content sync, and export summary. Invoked by Archival when operations involve multiple documents, batch processing, or repetitive updates. Trigger keywords: 批量, 所有文档, 全部, 大规模, 批量操作, 批量标签, batch, bulk, mass, all documents, every KB, repetitive, 全量, 一次性处理, 统一修改.
---

# Knowledge Batch -- Bulk & Batch Operations

## B1 -- Bulk Tag Management

kb_tags_list() + kb_list() to survey. Add tag: for each untagged doc, kb_doc_update_tags(). Replace tag: kb_doc_get_by_tag("old") to find docs, then replace in each. Remove tag: same find-and-replace pattern, drop the old tag. Verify: kb_doc_get_by_tag("old") returns 0, kb_doc_get_by_tag("new") returns migrated docs.

## B2 -- Bulk Description Updates

kb_list() to find KBs with empty or placeholder descriptions. Read 1-2 representative docs via kb_doc_read(kb_id, doc, max_chars=300). Update: kb_update(kb_id, description="1-3 sentences: domain + content types + language"). For doc-level descriptions: kb_get_documents, then kb_doc_read -> kb_doc_update_meta for empty/placeholder only. Sample if >20 docs -- don't rewrite everything.

## B3 -- Directory-to-KB Mass Ingestion

Glob() to discover files. Classify: parse-path (.pdf .docx .jpg .png .xlsx) -> parse_doc() then poll tasks; direct (.md .txt .csv .json) -> read content, check size (>50KB split per doc-splitting.md), kb_doc_create(); binary -> fs_upload_file(). Report discovered, parsed, direct-stored, binary-uploaded counts with parse failures.

## B4 -- Mass Document Move

kb_get_documents(source) -> kb_doc_move() each doc to target. Warn if >50 docs. Verify source count decreased, target count increased by N. If source empty, ask: "Delete empty source KB?"

## B5 -- Cross-KB Dedup

kb_list() -> kb_get_documents per KB. Compare filenames across KBs. Same name + similar size -> read 500 chars to confirm. kb_doc_delete from wrong KB. Retain in domain-correct KB. Never delete without content comparison.

## B6 -- Export Summary

kb_list() + kb_tags_list() + fs_get_tree() + fs_get_count(). Per KB: kb_get_documents for doc count, size, tags, dates. Write to .claude/collection-report.md via Write tool. Include: overview numbers, per-KB table, tag list, graph health (kb_graph_stats), vector coverage (kb_search_stats). Present overview to user.

## B7 -- Graph Rebuild

After batch ops, run kb_graph_build_all(force=false) or per-impacted KB: kb_graph_build_kb(kb_id, force=true). Verify kb_graph_stats() -> edge_count increased with shared_tag relations.
