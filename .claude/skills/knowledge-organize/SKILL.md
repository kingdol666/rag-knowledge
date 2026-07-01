---
name: knowledge-organize
description: >
  Full collection restructuring engine. O1→O6 workflow: survey every KB,
  read document content to classify true domains, categorize KBs (proper/
  test/empty/overlapping/misclassified), execute merges/moves/
  renames/descriptions, verify each change, produce structured report.
  Invoked by Archival when the collection needs deep reorganization.
---

# Knowledge Organize — Full Collection Restructuring

Invoked by Archival when the scenario is diagnosed as **Organize**
(全盘整理, 整理, 清洗, 审计, audit, restructure).

This is the deep reorganization engine. Survey every KB, read content,
and restructure so the collection reflects the truth.

## O1 — Full Survey

```
kb_list()         → all KBs with names, descriptions, document counts
kb_tags_list()    → all registered tags
fs_get_tree(include_files=True, max_depth=0)  → full structural view
```

## O2 — Evaluate Every KB

For each KB, evaluate these metrics:

| Metric | How to evaluate | Red flag |
|--------|----------------|----------|
| Name quality | Meaningful? Describes the domain? | Gibberish: "213", "333333", "哒哒哒" |
| Description quality | Does it describe the domain? | Empty, "test", meaningless |
| Document count | How many docs inside? | 0 = stale |
| Domain match | Do the docs match the KB name? | KB says "AI" but doc content is energy |
| Overlap | Same content in another KB? | Duplicate domain coverage |

For each KB with documents:
- Read 1-2 documents: `kb_doc_read(kb_id, <doc>, max_chars=300)`
- Classify the KB's TRUE domain based on content evidence, not its name.

## O3 — Categorize Every KB

| Category | Characteristics | Action |
|----------|----------------|--------|
| **Proper domain KB** | Meaningful name + description + matching content | Keep. May offer rename/rediscribe. |
| **Test/scratch** | Gibberish name, meaningless description | Merge content into "Test-Scratch" KB, delete shell |
| **Empty stale** | 0 documents | Ask user → delete or keep as placeholder |
| **Domain overlap** | Same domain as another KB | Merge into the better-named KB |
| **Misclassified** | KB name says X, content is Y | Move docs to correct KB, rename or delete shell |

## O4 — Execute

### Merge A into B
```
docs = kb_get_documents(A.kb_id)
for each doc:
    kb_doc_move(doc.doc_path, B.kb_id)
kb_delete(A.kb_id)    # only AFTER all docs moved
```

### Move misclassified
```
kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id="target-UUID")
```

### Rename/rediscribe
```
kb_update(kb_id, name="New-Name", description="<1-3 sentences>")
```
**Bug**: path won't refresh. Use UUID for subsequent calls.

### Delete empty KBs (confirm first unless Module Mode)
```
kb_delete(kb_id)
```

### Delete test documents
```
kb_doc_delete(kb_id, doc_path)
kb_doc_batch_delete(kb_id, ["KB/doc.md"])    # ⚠️ MUST use full paths
```

### Fix document descriptions (read content first, never guess)
```
kb_doc_update_meta(kb_id, doc_path, description="<1-2 sentences from content>")
```

### Fix KB descriptions
```
kb_update(kb_id, description="<1-3 sentences: domain + content types + language>")
```

### Apply missing tags
```
kb_doc_update_tags(kb_id, doc_path, ["tag1", "tag2"])
```

## O5 — Verify Each Change

After every move/delete:
1. `kb_get_documents(source_kb_id)` — count decreased
2. `kb_get_documents(target_kb_id)` — count increased
3. If KB deleted: confirm absent from `kb_list()`
4. `fs_get_tree(include_files=True)` — confirm tree is clean

## O6 — Health Report with Scorecard

Generate a structured summary with a **quantitative scorecard**:

```
## Collection Health Report

### Scorecard
  ├── Tag Coverage:    X/30  (tagged docs / total docs × 30)
  ├── Description Quality: X/25  (good descriptions / total × 25)
  ├── Uniqueness:      X/25  (unique docs / total × 25)
  └── KB Structure:    X/20  (proper-named KBs / total × 20)
  ───────────────────────
  TOTAL: X/100

### Overview
- Total KBs: N, Total Docs: N
- Unique documents: N (duplicates: N)
- Total Tags: N, Orphan tags: N

### Actions Completed
- KBs Deleted: N (list)
- KBs Merged: N (list)
- Documents Moved: N
- Descriptions Updated: N
- Tags Applied: N
### Remaining Issues
- Orphan tags (no tool to delete): list
- Weak descriptions: list
```

## O7 — Tag Hygiene Audit

Check the health of the tag vocabulary.

### O7a — Survey
```
kb_tags_list()         → all tags
```

### O7b — Check Each Tag
For each tag:
```
kb_doc_get_by_tag(tag)  → count of documents using this tag
```

Flag these issues:
- **Orphan tags**: 0 documents use this tag (can't be deleted — MCP limitation)
- **Near-duplicate tags**: pairs like "ML" / "machine-learning", "CNN" / "CNN-LSTM"
- **Low-usage tags**: tags used on only 1 document — too specific?
- **Generic tags**: "test", "doc", "misc", "important"

### O7c — Report
```
Tag Health:
  Total tags: N
  Orphan tags: N (no documents) — cannot delete, no MCP tool
  Low-usage tags (1 doc): N
  Near-duplicate pairs: N
  Suggestions:
  - "tag-a" and "tag-b" should be merged (kb_doc_update_tags to replace)
```

### O7d — Orphan Tag Resolution

When you find orphan tags (tags with 0 documents), use this workaround:

1. For orphan tag "dead-tag":
   - Check if the tag was used on a now-deleted document's KB
   - If the KB still has related documents: create a replacement tag with
     `kb_tag_create("rescue-tag")` and assign it via `kb_doc_update_tags()`
   - This "migrates" the usage away from the orphan

2. If no documents remain in the orphan tag's original domain:
   - Report: "Tag 'dead-tag' is orphaned with no related content. 
     It remains in the registry (no MCP tool to delete orphan tags)
     but does not affect search or operations."

3. If the orphan is a misspelling and you find documents that should use it:
   - Apply `kb_doc_update_tags(kb_id, doc_path, ["correct-tag"])` to the right docs
   - The orphan stays in the registry but is now unused and harmless
## CRITICAL RULES
1. O2 (read content) is NOT optional. Never classify a KB by name alone.
2. Merges: move docs FIRST, delete SECOND. Deleting first loses data.
3. Confirm destructive operations unless Module Mode.
4. O5 (verify) catches mistakes. Do not skip.
5. O7 (tag audit) cannot delete orphan tags — MCP limitation. Report and suggest manual cleanup.
