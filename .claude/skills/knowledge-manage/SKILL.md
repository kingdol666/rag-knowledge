---
name: knowledge-manage
description: >
  Document and KB administration operations. M1→M5 workflow: move documents
  between KBs, rename/rediscribe KBs or documents, delete documents or
  empty KBs, merge KBs, update document content. Invoked by Archival when
  the task involves moving, renaming, deleting, or updating existing items.
---

# Knowledge Manage — Document & KB Administration

Invoked by Archival when the scenario is diagnosed as **Manage**
(move, rename, delete, merge, update content/description).

## M1 — Survey

```
kb_list()          → load all KBs to find source and target
kb_get_documents(source_kb_id)  → find the document(s) to operate on
```

## M2 — Confirm Destructive Operations

**Before any action that destroys data**, confirm with the user:
- `kb_delete(kb_id)` — "This will permanently delete KB '[name]' and all its [N] documents. Confirm?"
- `kb_doc_delete(kb_id, doc_path)` — "Delete '[name]'? This is irreversible."
- `kb_doc_batch_delete(kb_id, [paths])` — "Delete [N] documents? This is irreversible."
- `kb_doc_move(doc_path, target_kb_id)` — No confirmation needed (non-destructive).
- `kb_update(kb_id, name, description)` — No confirmation needed.
- `kb_doc_update_meta(kb_id, doc_path, name, description)` — No confirmation needed.
- `kb_doc_update_content(kb_id, doc_path, content)` — No confirmation needed.

**In Module Mode**: execute without confirmation. Choose the most reasonable option.

## M3 — Execute

### Move Document
```
kb_doc_move(doc_path="SourceKB/doc-name.md", target_kb_id="target-UUID")
```
**⚠️ Real signature is `(doc_path, target_kb_id)`, NOT `(doc_id, target_parent_id)`.**

### Rename KB
```
kb_update(kb_id, name="New-Name", description="Updated description")
```
**Bug**: `path` does NOT refresh on rename. Use UUID for subsequent calls.

### Rename Document
```
kb_doc_update_meta(kb_id, doc_path, name="new-name.md", description="Updated description")
```
**Bug**: `path` stays on old name. Use old path for subsequent calls.

### Update Document Content
```
kb_doc_update_content(kb_id, doc_path, "<new content>")
```
**Bug**: `file_size` in `kb_get_documents` stays stale. Use `fs_get_children` for real size.

### Delete Document
```
kb_doc_delete(kb_id, doc_path)
```
Accepts bare filename OR full path.

### Batch Delete Documents
```
kb_doc_batch_delete(kb_id, ["KB/doc1.md", "KB/doc2.md"])
```
**⚠️ MUST use full relative paths** ("KB/doc.md"). Bare filenames return "Not found".

### Delete KB
```
kb_delete(kb_id)
```
Irreversible. Must confirm first (unless Module Mode).

### Merge KB A into KB B
```
for each doc in kb_get_documents(A.kb_id):
    kb_doc_move(doc.doc_path, B.kb_id)
kb_delete(A.kb_id)   # only after all docs moved
```
**Always confirm before merging** (unless Module Mode).

### Create Folder or KB in Tree
```
fs_create_folder(name, parent_id, description, is_knowledge_base=True)
fs_create_file(name, parent_id, description)
fs_update_node(node_id, name, description)
fs_delete_node(node_id)             # recursive — irreversible
```

## M4 — Verify

After every operation:
1. `kb_get_documents(source_kb_id)` — confirm source changed as expected.
2. `kb_get_documents(target_kb_id)` — confirm target reflects the change.
3. If KB deleted: confirm gone from `kb_list()`.
4. `fs_get_tree(include_files=True)` — confirm tree is clean.

## M5 — Report

Summarize concisely:
"Moved 'filename.pdf' from [SourceKB] to [TargetKB]. [N] documents
in source remaining. Tags preserved."
