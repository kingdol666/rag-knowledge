---
name: knowledgebase-verify
description: Knowledge base integrity and quality validation. V1→V6: check KB health, validate three-way metadata consistency (disk ↔ .tree-fs.json ↔ .knowledge-base.yml), verify parse quality, detect corruption, check vector_index/graph_index coverage, generate structured integrity report. Invoked by Archival when the collection needs a health check. Trigger keywords: 校验, 核对, 完整性, 健康检查, 验证, 检查, 一致性, verify, validate, integrity, health check, quality audit, check KB, 检测问题, 审计知识库.
---

# Knowledge Verify — Collection Integrity & Quality

**Read-only by default.** V4 repair requires explicit user instruction.

## V1 — Three-Way Metadata Integrity
Cross-reference three layers: **disk files ↔ `.tree-fs.json` ↔ `.knowledge-base.yml`**.

1. `kb_list()` vs `fs_get_tree()` — flag KBs with no tree node, orphan file nodes without KB entry, doc count mismatches.
2. For each KB: `kb_get_documents(kb_id)` — check each doc has a matching file on disk (via `fs_get_node` or path check).
3. Check UUID consistency: file `id` in `.tree-fs.json` should match `id` in `.knowledge-base.yml` documents.
4. Flag: phantom entries (in metadata but not on disk), orphan files (on disk but not in metadata), UUID mismatches.

## V2 — Document Integrity
`kb_get_documents(kb_id)` then `kb_doc_read` sampling: 1-10 docs check all; 11-50 check 50%; >50 check first 20. Flag broken 404 references, empty descriptions, untagged docs.
Supports `doc_id` (UUID) for resolution: `kb_doc_read(doc_id="<UUID>")`.

## V3 — Parse Quality
`kb_doc_read` 2000 chars on parsed docs (infer from .pdf/.docx names). Check: empty content (<100 chars), OCR garbage, binary residue (\x00 bytes), only headings (no body text).

**MinerU engine health**: query the backend via `backend_status()` (authoritative — returns `mineru` running state + resolved port). Do NOT trust `health_check()` for MinerU status (known false negatives). If parse quality is poor across many docs, first confirm MinerU is up via `backend_status` before flagging individual docs.

## V4 — Index Coverage & Repair (repair only if user asks)

### Vector index check
For each KB: `kb_get_documents(kb_id)` → check each doc for `vector_index` field in metadata.
- Missing `vector_index` → doc not indexed, invisible to vector search
- `kb_search_stats(kb_id)` → check chunk counts per collection
- Orphan collections (chunks>0 but KB deleted) → flag

**Repair**: `kb_index_document(kb_id, doc_path)` for single doc, or `kb_batch_index(kb_id, [doc_paths], force=true)` for batch.

### Graph index check
`kb_graph_health()` → is Neo4j available?
`kb_graph_kb_overview(kb_id)` → doc_count vs actual doc count
`kb_graph_stats()` → total entities/relations

**Repair**: `kb_graph_build_kb(kb_id, force=true)` to rebuild.
**Clean stale**: `kb_graph_delete_document(doc_path)` for deleted docs, `kb_graph_delete_kb(kb_id)` for deleted KBs.

### Stale entry cleanup
`kb_doc_delete(broken_ref)` to remove stale entries from `.tree-fs.json` + `.knowledge-base.yml`. Report orphan file paths (on disk but not indexed) — user decides re-import or delete.

## V5 — Scorecard (max 115)
Metadata Consistency — three-way sync (25) | Document Quality (30) | Tag Coverage (25) | Description Quality (10) | Graph Health: `kb_graph_health` + `kb_graph_stats` (15) | Vector Coverage: `kb_search_stats` (10)

## V6 — Report
Score + key findings + single most impactful recommendation.
