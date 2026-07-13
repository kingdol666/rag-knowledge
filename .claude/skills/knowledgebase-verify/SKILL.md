---
name: knowledgebase-verify
description: Knowledge base integrity and quality validation. V1→V6: check KB health, validate three-way metadata consistency (disk ↔ .tree-fs.json ↔ .knowledge-base.yml), verify parse quality, detect corruption, check vector_index/graph_index coverage, generate structured integrity report. Invoked by Archival when the collection needs a health check. Trigger keywords: 校验, 核对, 完整性, 健康检查, 验证, 检查, 一致性, verify, validate, integrity, health check, quality audit, check KB, 检测问题, 审计知识库.
---

# Knowledge Verify — Integrity & Quality

**Read-only by default.** V4 repair requires explicit user instruction.

## V1 — Three-Way Metadata Integrity
1. `kb_list()` vs `fs_get_tree()` — flag KBs with no tree node, orphan nodes, doc count mismatches.
2. For each KB: `kb_get_documents(kb_id)` — check each doc has a matching file on disk.
3. Check UUID consistency between `.tree-fs.json` and `.knowledge-base.yml`.
4. Flag: phantom entries (metadata but no disk file), orphan files (disk but no metadata), UUID mismatches.

## V2 — Document Integrity
`kb_get_documents(kb_id)` → sample `kb_doc_read` (1-10 docs: all; 11-50: 50%; >50: first 20).
Flag: broken 404s, empty descriptions, untagged docs.

## V3 — Parse Quality
`kb_doc_read` 2000 chars on parsed docs (infer from .pdf/.docx names).
Flag: empty content (<100 chars), OCR garbage, binary residue, heading-only (no body).

Use `backend_status()` for MinerU health (authoritative).

## V4 — Index Coverage & Repair
### Vector
`kb_get_documents(kb_id)` → check `vector_index` field per doc. `kb_search_stats(kb_id)` → check chunk counts.
**Repair**: `kb_index_document(kb_id, doc_path)` or `kb_batch_index(kb_id, [paths], force=true)`.

### Graph
`kb_graph_health()` → Neo4j available? `kb_graph_kb_overview(kb_id)` → doc_count vs actual.
**Repair**: `kb_graph_build_kb(kb_id, force=true)`.
**Clean stale**: `kb_graph_delete_document(doc_path)` for deleted docs.

## V5 — Scorecard (max 115)
Metadata Consistency (25) | Document Quality (30) | Tag Coverage (25) | Description Quality (10) | Graph Health (15) | Vector Coverage (10)

## V6 — Report
Score + key findings + single most impactful recommendation.
