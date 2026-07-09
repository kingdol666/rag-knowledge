---
name: knowledgebase-manage
description: Document and KB administration operations. M1→M6 workflow: move documents between KBs, rename/redescribe KBs or documents, delete documents or empty KBs, merge KBs, update document content. Invoked by Archival when the task involves moving, renaming, deleting, or updating existing items. Trigger keywords: 移动, 改名, 重命名, 删除文档, 删除KB, 合并KB, move, rename, delete, merge, update content, update description, 移动文档, 更新内容, 修改描述, change description.
---

# Knowledge Manage — Document & KB Administration

All operations are **atomic**: each call syncs disk file + `.tree-fs.json` + `.knowledge-base.yml`.

## M1 — Survey
`kb_list()` + `kb_get_documents(source_kb_id)`

## M2 — Confirm Destructive
Ask user before `kb_delete` / `kb_doc_delete` (skip in Module Mode).

## M3 — Execute

### KB Operations
| Op | Tool |
|---|---|
| Rename/redescribe KB | `kb_update(kb_id, name, description)` |
| Delete KB | `kb_delete(kb_id)` — irreversible |

### Document Operations
| Op | Tool | Notes |
|---|---|---|
| Move | `kb_doc_move(doc_path, target_kb_id)` | UUID preserved. Does NOT reindex. |
| Rename/redescribe | `kb_doc_update_meta(kb_id, doc_path, name, description)` | UUID preserved. |
| Update content | `kb_doc_update_content(kb_id, doc_path, content)` | Does NOT auto-reindex. |
| Delete | `kb_doc_delete(kb_id, doc_path)` | Accepts bare name or full path. |
| Batch delete | `kb_doc_batch_delete(kb_id, ["KB/doc1.md", ...])` | **Must use full relative paths.** |
| Merge A→B | Move all docs from A to B, then `kb_delete(A)` | Confirm first. |

## M4 — Reindex After Changes
- **After move**: `kb_index_document(kb_id=target, doc_path=new_path)`
- **After content update**: `kb_index_document(kb_id, doc_path)` (old index invalidated)
- **After delete**: optionally `kb_graph_delete_document(doc_path=old_path)` to clean graph
- **After merge**: `kb_graph_build_kb(target_kb_id, force=false)`

## M5 — Verify + Report
`kb_get_documents(source)` + `kb_get_documents(target)` + `kb_list()` + `fs_get_tree()`

## M6 — Update Content Flow
1. `kb_doc_read(kb_id, doc_path, max_chars=20000)` → present current content
2. User provides new content
3. `kb_doc_update_content(kb_id, doc_path, content)` → file + metadata synced
4. `kb_doc_read(kb_id, doc_path)` → verify
5. `kb_index_document(kb_id, doc_path)` → rebuild vector index
