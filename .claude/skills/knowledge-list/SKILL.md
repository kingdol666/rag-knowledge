---
name: knowledge-list
description: >
  Knowledge base listing and discovery. L1→L3 workflow: full inventory of
  all KBs with document counts, KB drill-down with document metadata,
  folder tree browsing. Read-only. Invoked by Archival when information
  needs to be found or displayed.
---

# Knowledge List — Collection Overview & Discovery

Invoked by Archival when the scenario is diagnosed as **List**
(list, show, what KBs, overview, tree, 列, 查, 查看).

**Read-only.** Never modify any KB, document, or tag.

## L1 — Full Inventory

```
kb_list()         → all KBs with names, descriptions, document counts
kb_tags_list()    → all tags (for context)
fs_get_tree(include_files=False, max_depth=2)   → folder outline
```

Present as structured text, NOT raw JSON:

```
The collection holds [N] knowledge bases with [total_docs] documents.

| KB Name | Description | Docs |
|---------|-------------|------|
| Name | Domain summary | N |
| ... | | |

Tags ([N]): tag1, tag2, ...
```

Offer to drill into any KB.

## L2 — KB Drill-Down

For "what is in [KB]?":

1. Find the KB in `kb_list()` by matching name or description.
2. `kb_get_documents(kb_id)` → all docs with metadata.

Present as a table:

```
## KB Name
Description: ...
Documents: N

| Name | Description | Type | Tags | Added |
|------|-------------|------|------|-------|
| doc | ... | .md | tags | date |
```

Offer to read any document (`kb_doc_read`) or preview (`preview_file`).

If 0 documents: "This KB is empty."

## L3 — Browse Tree

```
fs_get_tree(include_files=True, max_depth=0)
fs_get_count()
```

Present as:

```
├─ KB Name (N docs)
│  ├─ SubKB (N docs)
│  └─ doc.md
├─ KB Name (N docs)
├─ Folder (0 docs)
```

Offer to drill into any folder with `fs_get_children(parent_id)`.

---

## CRITICAL
- Read-only. Never modify. Refuse politely if asked.
- Format for humans — tables, lists, trees. Not raw JSON.
