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

## O6 — Report

Present a structured summary of everything done:

```
## Collection Restructure Complete

### KBs Created: N
- Name (domain, content types, language)

### KBs Deleted: N
- Name (reason)

### KBs Merged: N
- Name → Name (N docs moved)

### Documents Moved: N
- (detail)

### Descriptions Updated: N
- (detail)

### Tags Applied: N
- (detail)

### Remaining Issues: N
- (what couldn't be fixed)
```

---

## CRITICAL RULES
1. O2 (read content) is NOT optional. Never classify a KB by name alone.
2. Merges: move docs FIRST, delete SECOND. Deleting first loses data.
3. Confirm destructive operations unless Module Mode.
4. O5 (verify) catches mistakes. Do not skip.
