---
name: knowledgebase-organize
description: Full collection restructuring engine. O0→O14 workflow: define KB standards, deep survey every KB (read 2000+ chars per doc), audit every document against compliance standards, content-driven reclassification, execute fixes (descriptions/tags/moves/merges/renames), verify each change, auto-create sub-KBs when KB grows, batch-fix non-compliant descriptions, audit vector index coverage and reindex missing docs, clean YAML/JSON/disk three-way consistency, and knowledge graph rebuild. No document splitting. Trigger keywords: 整理, 清洗, 重组, 审计, 重构, 盘点, 全面梳理, organize, restructure, audit collection, cleanup KB, reorganize, 清洗知识库, 整理知识库, 重建索引, 重新分类, 大扫除, 看看哪里有问题, 有哪些问题, consolidation.
---

# Knowledge Organize — Collection Restructuring

Ensure every document meets all 6 compliance criteria. Documents failing any criterion are auto-fixed.

## Compliance Criteria (O0)
| # | Criterion | Check |
|---|---|---|
| C1 | Content-based description (not empty/filename/generic) | `kb_doc_read` 500 chars → compare |
| C2 | 2-5 content-relevant tags | `kb_get_documents` → check tags |
| C3 | Document domain matches its KB | Read 2000 chars → classify |
| C4 | Vector index present | Check `vector_index` in metadata |
| C5 | Graph index present | `kb_graph_kb_overview(kb_id)` |
| C6 | Disk ↔ .tree-fs.json ↔ .knowledge-base.yml consistent | Cross-reference |

## O1 — Full Survey
```
kb_list()
kb_tags_list()
fs_get_tree(include_files=True, max_depth=0)
```

## O2 — Deep Content Audit (Every KB, Every Document)
For each document:
```
content = kb_doc_read(kb_id, doc.doc_path, max_chars=2000)
```
Check C1-C6. Flag failures: `desc=MISSING/WEAK/MISMATCH`, `tags=INSUFFICIENT/GENERIC`, `kb=MISCLASSIFIED`, `index=MISSING`.

For KBs with >10 docs: delegate to sub-agent with content samples. Request JSON array with `doc_path, true_domain, description_quality, suggested_description, suggested_tags, kb_match`.

## O3 — Categorize KBs
Classify each KB: Compliant / Needs cleanup / Test-scratch / Empty / Domain overlap / Misclassified.

Reclassify misclassified docs: find correct KB by content domain → `kb_doc_move(doc_path, correct_kb_id)`.

## O4 — Execute Fixes (in order)
1. **Fix descriptions** (C1): `kb_doc_update_meta(kb_id, doc_path, description=suggested)` — 按 [description-guide.md](../knowledgebase-ingest/references/description-guide.md) 四要素+内容回查，拒绝泛泛描述
2. **Fix tags** (C2): `kb_doc_update_tags(kb_id, doc_path, suggested_tags)` — 严格按 [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md) T1黑名单+T2归一化+T3数量执行
3. **Move misclassified** (C3): `kb_doc_move(doc_path, correct_kb_id)` → `kb_index_document(kb_id=correct, doc_path=new_path)`
4. **KB ops**: merge (`move all → kb_delete`), rename (`kb_update`), delete (`kb_delete`)

## O5 — Verify Each Change
After each fix: `kb_doc_read` / `kb_doc_get_by_tag` / `kb_get_documents` to confirm.

## O6 — Orphan Cleanup
Check for orphaned `experience/` dirs, phantom `.tree-fs.json` entries.

## O7 — Compliance Scorecard
Re-audit all docs. Score: C1-C6 each as N/total (target 100%).

## O8 — Tag Hygiene
`kb_tags_list()` → `kb_doc_get_by_tag(tag)`. Clean strictly per [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md):
- **T1 黑名单清除**：章节标题(`Abstract`/`1 Introduction`/`References`)、测试标签(`test-*`/`*-test`)、描述性标签 → 从所有文档移除
- **T2 同义合并**：大小写重复(`PET`/`pet`)、中英重复(`聚乙烯`/`PE`) → 统一到词表主词
- **孤儿清除**：0 文档引用的标签自动消失
- **单文档独有且非新概念** → 归并到主词

实测现状：~40 章节标题 + ~17 测试标签 + ~15 组同义重复待清洗。

## O9 — Sub-KB Auto-Creation
If parent KB ≥8 docs across ≥2 sub-domains: create sub-KBs. See [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md).

## O10 — Vector Index Coverage
```
for each kb: docs = kb_get_documents(kb_id)
  missing = [d for d in docs if not d.vector_index]
  if missing: kb_batch_index(kb_id, [d.path for d in missing], force=true)
```

## O11 — Three-Way Consistency
Cross-check disk ↔ `.tree-fs.json` ↔ `.knowledge-base.yml`. Fix: re-register via `kb_doc_create`, delete stale via `kb_doc_delete`, reindex via `kb_index_document`.

## O12 — Graph Rebuild
```
for each kb:
    if kb_graph_kb_overview(kb_id).doc_count < actual_doc_count:
        kb_graph_build_kb(kb_id, force=true)
```

## O13 — Final Report
KBs before/after, documents, moves, merges, deletions, fixes, reindexes, compliance scores.

## Critical Rules
- Read 2000+ chars per doc for classification — never classify by filename
- Every document is audited — no skips
- Fixes in order: descriptions → tags → moves → KB ops
- Verify each change immediately
- No document splitting — documents stay as single units
