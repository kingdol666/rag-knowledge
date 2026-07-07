---
name: knowledgebase-organize
description: Full collection restructuring engine. O1→O14 workflow: survey every KB, read document content to classify true domains, categorize KBs (proper/test/empty-parent/empty-orphan/overlapping/misclassified), auto-process empty KBs, content-driven document re-classification (O3b), execute merges/moves/renames/descriptions, verify each change, produce structured report, split oversized documents (O9), auto-create sub-KBs when KB grows (O10), batch-fix descriptions (O11), audit vector index coverage and reindex missing docs (O12), clean YAML/JSON redundancy with disk↔YAML↔JSON↔vector four-way consistency (O13), and knowledge graph rebuild (O14). Invoked by Archival when the collection needs deep reorganization. Trigger keywords: 整理, 清洗, 重组, 审计, 重构, 盘点, 全面梳理, organize, restructure, audit collection, cleanup KB, reorganize, 清洗知识库, 整理知识库, 重建索引, 重新分类, 大扫除, 看看哪里有问题, 有哪些问题, consolidation.
---

# Knowledge Organize — Full Collection Restructuring

## O1 — Full Survey
kb_list() + kb_tags_list() + fs_get_tree(include_files=True, max_depth=0)

## O2 — Evaluate Every KB
For each KB: read 1-2 docs (kb_doc_read, max_chars=300), classify true domain from content.
Check: name quality, description quality, doc count (0=stale), domain match, oversized docs (>50KB), vector_index coverage.

### O2-E — Description Audit
For each doc: verify assertions in description match content (kb_doc_read 500 chars).
If description is empty, "Parsed from...", or term-mismatch → fix. See [description-guide.md](../knowledgebase-ingest/references/description-guide.md).

## O3 — Categorize
| Category | Criteria | Action |
|---|---|---|
| Proper domain KB | Meaningful name+desc+matching content | Keep |
| Test/scratch | Gibberish name, meaningless desc | Merge content, delete shell |
| Empty parent | 0 docs BUT has child sub-KBs | Keep as container, update desc |
| Empty orphan | 0 docs, no children, no purpose | Auto-delete (kb_delete) |
| Domain overlap | Same content as another KB | Merge into better-named KB |
| Misclassified | Content doesn't match KB name | Move docs, rename/delete shell |

### O3b — Content-Driven Reclassification
For each doc: read 500 chars, classify true domain. If current_kb_match=false → kb_doc_move(doc_path=doc.name, target_kb_id=correct_id). Use sub-agent for ≥3 docs.

## O4 — Execute Changes
- Merge A→B: kb_doc_move(doc.doc_path, B.kb_id) for all → kb_delete(A.kb_id)
- Move doc: kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id)
- Rename KB: kb_update(kb_id, name="New", description="...")
- Rename doc: kb_doc_update_meta(kb_id, doc.name, name="new.md")
- Delete doc: kb_doc_delete(kb_id, doc_path)
- Delete KB: kb_delete(kb_id) — confirm first
- Fix desc: kb_doc_update_meta(kb_id, doc.name, description="...")

## O5 — Verify Each Change
kb_get_documents(source) + kb_get_documents(target) + kb_list() + fs_get_tree()

## O6 — Orphan Cleanup
Check for orphaned experience/ dirs whose KB was deleted.

## O7 — Scorecard
Tag Coverage (30) | Description Quality (25) | Uniqueness (25) | KB Structure (20) = TOTAL /100

## O8 — Tag Hygiene
kb_tags_list() + kb_doc_get_by_tag(tag). Flag: orphans (0 docs), near-duplicates, low-usage (1 doc), generic ("test", "doc").

## O9 — Large Document Split
If >50KB or >80K chars: split by headings.
Procedure: [doc-splitting.md](../knowledgebase-ingest/references/doc-splitting.md)

## O10 — Sub-KB Auto-Creation
If parent KB has ≥5 docs across ≥3 sub-domains OR ≥10 docs total OR total_size>500KB:
Create focused sub-KBs. Procedure: [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md)
Also check and merge back single-doc sub-KBs (≥1 doc → move to parent, delete sub-KB shell).

## O11 — Description Batch Fix
For docs with weak/empty descriptions: use sub-agent to read content + generate A4-format descriptions. Apply via kb_doc_update_meta. [description-guide.md](../knowledgebase-ingest/references/description-guide.md)

## O12 — Vector Index Coverage
kb_get_documents() per KB → check each doc for vector_index field.
Missing? kb_batch_index(kb_id, [doc_paths], force=true).
Check kb_search_stats() for orphan collections (chunks>0 but KB gone).

## O13 — YAML/JSON Consistency
Three-way check: disk files ↔ YAML entries ↔ tree-fs.json
- Audit all: `python .claude/skills/knowledgebase-organize/scripts/fix_yaml_index.py audit-all`
- Clean orphans: `python fix_yaml_index.py clean <kb_path>`
- Fix parent pollution: `python fix_yaml_index.py unparent <parent_kb_path>`
- Missing entries (disk has, YAML missing): kb_doc_create to re-register

## O14 — Graph Rebuild
Check kb_graph_kb_overview(kb_id).doc_count vs kb_get_documents().count.
If coverage < 100%: kb_graph_build_kb(kb_id, force=true). Verify: kb_graph_stats().

## Critical Rules
1. O2: Read content — never classify by name alone
2. O2-E + O11: Description audit + fix is mandatory
3. O3b: Content-driven reclassification for every doc
4. O5: Verify each change immediately
5. O12: All docs must have vector_index — unindexed = invisible
6. O13: YAML ↔ disk ↔ vector three-way consistency required
7. O14: Graph coverage must be validated
8. Confirm destructive ops (kb_delete) unless Module Mode
