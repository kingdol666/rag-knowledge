---
name: knowledgebase-organize
description: Full collection restructuring engine. O0→O14 workflow: define KB standards, deep survey every KB (read 2000+ chars per doc), audit every document against compliance standards, content-driven reclassification, execute fixes (descriptions/tags/moves/merges/renames), verify each change, auto-create sub-KBs when KB grows, batch-fix non-compliant descriptions, audit vector index coverage and reindex missing docs, clean YAML/JSON/disk three-way consistency, and knowledge graph rebuild. No document splitting. Trigger keywords: 整理, 清洗, 重组, 审计, 重构, 盘点, 全面梳理, organize, restructure, audit collection, cleanup KB, reorganize, 清洗知识库, 整理知识库, 重建索引, 重新分类, 大扫除, 看看哪里有问题, 有哪些问题, consolidation.
---

# Knowledge Organize — Full Collection Restructuring & Compliance Engine

## Core Principle: Every Document Must Meet KB Standards

The goal of organizing is NOT just moving things around — it is ensuring **every single document** in the collection meets the KB Compliance Standard. A document that is in the wrong KB, has no description, has wrong tags, or has no vector index is **invisible or misleading** to retrieval.

---

## O0 — KB Compliance Standard (The Goal)

Every document in the knowledge base MUST satisfy ALL of these criteria:

| # | Criterion | Standard | How to Check |
|---|-----------|----------|--------------|
| C1 | **Real description** | Content-based, A4-format. NOT empty, NOT "Parsed from...", NOT filename-based, NOT generic ("test"/"document") | `kb_doc_read` 500 chars → compare description claims against content |
| C2 | **Tags (2-5)** | At least 2 content-relevant tags. NOT empty, NOT generic-only ("test", "doc") | `kb_get_documents` → check tags field |
| C3 | **Correct KB** | Document's true domain (from content) matches its KB's domain | Read 2000 chars → classify → compare to KB name/description |
| C4 | **Vector index** | `vector_index` field present in `.knowledge-base.yml` | `kb_get_documents` → check metadata |
| C5 | **Graph index** | Document appears in KB's graph | `kb_graph_kb_overview(kb_id)` → check doc_count |
| C6 | **Disk consistency** | File exists on disk, entry in `.tree-fs.json`, entry in `.knowledge-base.yml` — all three match | File system check + tree check |

**Any document failing any criterion is flagged for auto-fix in O4.**

---

## O1 — Full Survey

```
kb_list()                              → all KBs with names + descriptions + doc counts
kb_tags_list()                         → full tag vocabulary + usage counts
fs_get_tree(include_files=True, max_depth=0)  → complete tree with all files
```

Build a complete inventory: how many KBs, how many docs total, what tags exist, what the hierarchy looks like.

## O2 — Deep Content Evaluation (Every KB, Every Document)

**This is the most critical step. Shallow reading produces shallow classification.**

### O2a — KB-Level Evaluation

For each KB:
- Read KB name + description
- Read 2-3 documents (`kb_doc_read`, max_chars=2000) to understand the KB's true content domain
- Classify: what is this KB REALLY about (based on content, not name)?

### O2b — Document-Level Compliance Audit

For EVERY document in EVERY KB:

```
for each doc in kb_get_documents(kb_id):
    content = kb_doc_read(kb_id, doc.doc_path, max_chars=2000)

    # C1: Description check
    if doc.description is empty:
        flag(desc=MISSING)
    elif doc.description starts with "Parsed from" or contains "test":
        flag(desc=WEAK)
    else:
        # Verify description claims against content
        key_terms = extract_key_terms(doc.description)
        if key_terms not found in content[:500]:
            flag(desc=MISMATCH)

    # C2: Tags check
    if len(doc.tags) < 2:
        flag(tags=INSUFFICIENT)
    elif all tags are generic ("test", "doc", "document"):
        flag(tags=GENERIC)

    # C3: KB match check
    doc_domain = classify_domain(content)
    if doc_domain != kb_domain:
        flag(kb=MISCLASSIFIED, correct_domain=doc_domain)

    # C4: Vector index check
    if doc.vector_index is missing:
        flag(index=MISSING)

    # C5: Graph check (batch check per KB later)
    # C6: Disk consistency check (batch check later)
```

### O2c — Sub-Agent Deep Reading (for large collections)

When a KB has >10 documents, delegate deep reading to sub-agents:

```
Agent(
  subagent_type="general-purpose",
  prompt="""Read the following documents and for each one, output a compliance assessment.

KB: {kb_name} ({kb_description})

Documents to audit:
{for each doc: doc_path, description, tags, first 2000 chars of content}

Output JSON array:
[
  {
    "doc_path": "...",
    "title_from_content": "Real title extracted from content",
    "true_domain": "Domain determined from content",
    "true_sub_domain": "Sub-domain from content",
    "description_quality": "good|weak|missing|mismatch",
    "description_issues": "What's wrong (if any)",
    "suggested_description": "A4-format description based on real content (if fix needed)",
    "tags_quality": "good|insufficient|generic",
    "suggested_tags": ["tag1", "tag2", "tag3"],
    "kb_match": true|false,
    "correct_kb": "If misclassified, which KB should this be in?",
    "key_methods": ["method1", "method2"],
    "language": "zh/en/bilingual"
  }
]"""
)
```

## O3 — Categorize KBs

Based on O2 deep evaluation, categorize each KB:

| Category | Criteria | Action |
|---|---|---|
| **Compliant** | Name+desc good, all docs meet C1-C6 | Keep, minor fixes only |
| **Needs cleanup** | Good domain but some docs fail standards | Fix docs in-place (O4) |
| **Test/scratch** | Gibberish name, meaningless content | Merge useful docs, delete shell |
| **Empty parent** | 0 docs BUT has child sub-KBs | Keep as container, update desc |
| **Empty orphan** | 0 docs, no children, no purpose | Auto-delete (kb_delete) |
| **Domain overlap** | Same content domain as another KB | Merge into better-named KB |
| **Misclassified** | KB name says X but content is Y | Rename KB or move docs |

### O3b — Content-Driven Reclassification

For each document flagged as MISCLASSIFIED in O2b:

```
# Determine the correct KB from the true_domain detected in content
correct_kb = find_kb_by_domain(true_domain, kb_list())

if correct_kb exists:
    kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id=correct_kb.kb_id)
else:
    # Need to create a new KB for this domain
    kb_create(name=domain_to_kb_name(true_domain), description="...")
    kb_doc_move(doc_path, new_kb.kb_id)
```

**Key rule**: reclassification is based on content analysis from O2 (2000 chars read), NOT filename matching.

## O4 — Execute Fixes (Auto-Fix Pipeline)

Process all flagged issues from O2b in this order:

### O4a — Fix Descriptions (C1)
For every doc flagged `desc=MISSING`, `desc=WEAK`, or `desc=MISMATCH`:
```
# Use the suggested_description from O2b/O2c analysis (already content-based)
kb_doc_update_meta(kb_id, doc_path, description=suggested_description)
```
Reference: [description-guide.md](../knowledgebase-ingest/references/description-guide.md) for A4 format.

### O4b — Fix Tags (C2)
For every doc flagged `tags=INSUFFICIENT` or `tags=GENERIC`:
```
# Use suggested_tags from O2b/O2c analysis
kb_doc_update_tags(kb_id, doc_path, suggested_tags)
```
Tag rules: 2-5 tags, ≥90% vocabulary reuse, content-derived.

### O4c — Move Misclassified Docs (C3)
For every doc flagged `kb=MISCLASSIFIED`:
```
kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id=correct_kb_id)
# After move, reindex in new KB
kb_index_document(kb_id=correct_kb_id, doc_path=moved_doc_path)
```

### O4d — KB-Level Operations
- **Merge A→B**: `kb_doc_move(doc_path, B.kb_id)` for all docs → `kb_delete(A.kb_id)`
- **Rename KB**: `kb_update(kb_id, name="New", description="...")`
- **Rename doc**: `kb_doc_update_meta(kb_id, doc_path, name="new.md")`
- **Delete doc**: `kb_doc_delete(kb_id, doc_path)`
- **Delete KB**: `kb_delete(kb_id)` — confirm first unless Module Mode

## O5 — Verify Each Change

After EACH fix operation, verify immediately:
```
# After description fix:
kb_doc_read(kb_id, doc_path, max_chars=500) → confirm description matches content

# After tag fix:
kb_doc_get_by_tag(tag, kb_id) → confirm tag applied

# After move:
kb_get_documents(source_kb_id) → confirm doc removed
kb_get_documents(target_kb_id) → confirm doc added

# After KB rename/delete:
kb_list() → confirm change
fs_get_tree() → confirm tree updated
```

## O6 — Orphan Cleanup
Check for orphaned experience/ dirs whose KB was deleted. Check for phantom entries in `.tree-fs.json` pointing to deleted files.

## O7 — Compliance Scorecard

After all fixes, re-audit and score:

```
Total Documents: N
  C1 Description compliant: ___/N (target: 100%)
  C2 Tags compliant:        ___/N (target: 100%)
  C3 KB match compliant:    ___/N (target: 100%)
  C4 Vector index:          ___/N (target: 100%)
  C5 Graph index:           ___/N (target: 100%)
  C6 Disk consistency:      ___/N (target: 100%)

Overall Compliance: ___%
Tag Coverage: ___/100 | Description Quality: ___/100 | Uniqueness: ___/100 | KB Structure: ___/100
```

Any criterion below 100% must have an explanation and remediation plan.

## O8 — Tag Hygiene
`kb_tags_list()` + `kb_doc_get_by_tag(tag)`. Flag and clean:
- Orphan tags (0 docs) → delete
- Near-duplicates (e.g., "coal-mill" and "coal mill") → merge
- Low-usage (1 doc) → evaluate if tag is too specific
- Generic ("test", "doc", "document") → replace with content-specific tags

## O9 — Sub-KB Auto-Creation
If parent KB has ≥8 docs across ≥2 sub-domains (determined from O2 content analysis):
Create focused sub-KBs. Procedure: [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md)

Also check and merge back single-doc sub-KBs (≤1 doc → move to parent, delete sub-KB shell).

**Note: Documents are NOT split.** Large documents remain as single units. The vector index handles chunking internally during embedding.

## O10 — Vector Index Coverage (C4 Enforcement)

```
for each kb in kb_list():
    docs = kb_get_documents(kb_id)
    missing_index = [d for d in docs if d.vector_index is missing]
    if missing_index:
        kb_batch_index(kb_id, [d.doc_path for d in missing_index], force=true)
```

If `kb_batch_index` fails on large KBs, fall back to `kb_reindex(kb_id, force=false)`.
Check `kb_search_stats()` for orphan collections (chunks>0 but KB gone).

## O11 — YAML/JSON/Disk Three-Way Consistency (C6 Enforcement)

All three metadata layers must be consistent:
- **Disk ↔ .tree-fs.json**: every file on disk has an entry, and vice versa
- **.tree-fs.json ↔ .knowledge-base.yml**: every file in a KB folder has a corresponding document entry with matching UUID (`id` field)
- **Vector index**: docs with `vector_index` should have chunks in vector DB (`kb_search_stats`)

If inconsistencies found:
- Missing in YAML but exists on disk + .tree-fs.json: re-register via `kb_doc_create`
- Exists in YAML but not on disk: delete via `kb_doc_delete`
- Missing vector_index: `kb_index_document` or `kb_batch_index`

## O12 — Graph Rebuild (C5 Enforcement)
```
for each kb:
    graph_overview = kb_graph_kb_overview(kb_id)
    docs = kb_get_documents(kb_id)
    if graph_overview.doc_count < docs.count:
        kb_graph_build_kb(kb_id, force=true)
```
Verify: `kb_graph_stats()`.

## O13 — Final Re-Audit & Report

Re-run O2b compliance audit on the entire collection. Generate final report:

```
Knowledge Base Organization Report
===================================

Summary:
  KBs before: ___  →  KBs after: ___
  Documents: ___ (all audited)
  Moves: ___  |  Merges: ___  |  Deletions: ___
  Descriptions fixed: ___  |  Tags fixed: ___
  Reindexed: ___ docs  |  Graph rebuilt: ___ KBs

Compliance:
  C1 Description: ___/___ (___%)
  C2 Tags:        ___/___ (___%)
  C3 KB Match:    ___/___ (___%)
  C4 Vector:      ___/___ (___%)
  C5 Graph:       ___/___ (___%)
  C6 Disk:        ___/___ (___%)

KB Structure:
  {kb_name} ({doc_count} docs) — {compliance_status}
    ├── {sub_kb_name} ({doc_count} docs)
    └── {sub_kb_name} ({doc_count} docs)

Issues Remaining (if any):
  - {issue description} → {remediation plan}

Quality Notes:
  - {observations about collection quality}
```

## Critical Rules
1. **O0 is the goal** — every document must meet all 6 compliance criteria (C1-C6)
2. O2: Read 2000+ chars per doc — **never classify by name alone, never read only 300 chars**
3. O2b: Every document is audited — no skips, no sampling
4. O3b: Reclassification is content-driven (from O2 deep reading), not filename-driven
5. O4: Fixes are applied in order (descriptions → tags → moves → KB ops)
6. O5: Verify each change immediately — do not batch verifications
7. O7: Compliance must reach 100% on all criteria, or have documented remediation plans
8. O10-O12: Vector, consistency, and graph checks are mandatory — unindexed = invisible
9. Confirm destructive ops (kb_delete) unless Module Mode
10. **No document splitting** — documents stay as single units
