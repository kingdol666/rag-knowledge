---
name: knowledgebase-verify
description: Knowledge base integrity and quality validation. V1→V6: check KB health, validate index consistency, verify parse quality, detect corruption, cross-reference tree vs documents, generate structured integrity report. Invoked by Archival when the collection needs a health check. Trigger keywords: 校验, 核对, 完整性, 健康检查, 验证, 检查, 一致性, verify, validate, integrity, health check, quality audit, check KB, 检测问题, 审计知识库.
---

# Knowledge Verify -- Collection Integrity & Quality

**Read-only by default.** V4 repair requires explicit user instruction.

## V1 -- Metadata Integrity
Cross-reference `kb_list()` vs `fs_get_tree()`. Flag KBs with no tree node, orphan file nodes without KB entry, doc count mismatches.

## V2 -- Document Integrity
`kb_get_documents(kb_id)` then `kb_doc_read` sampling: 1-10 docs check all; 11-50 check 50%; >50 check first 20. Flag broken 404 references, empty descriptions, untagged docs.

## V3 -- Parse Quality
`kb_doc_read` 2000 chars on parsed docs (infer from .pdf/.docx names). Check: empty content (<100 chars), OCR garbage, binary residue (\x00 bytes), only headings (no body text).

## V4 -- Index Repair (only if user asks)
`kb_doc_delete(broken_ref)` to remove stale index entries. Report orphan file paths (on disk but not indexed) -- user decides re-import or delete.

## V5 -- Scorecard (max 115)
Metadata Consistency (25) | Document Quality (30) | Tag Coverage (25) | Description Quality (10) | Graph Health: `kb_graph_health` + `kb_graph_stats` (15) | Vector Coverage: `kb_search_stats` (10)

## V6 -- Report
Score + key findings + single most impactful recommendation.
