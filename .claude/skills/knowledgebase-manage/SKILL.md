---
name: knowledgebase-manage
description: Document and KB administration operations. M1→M6 workflow: move documents between KBs, rename/redescribe KBs or documents, delete documents or empty KBs, merge KBs, update document content. Invoked by Archival when the task involves moving, renaming, deleting, or updating existing items. Trigger keywords: 移动, 改名, 重命名, 删除文档, 删除KB, 合并KB, move, rename, delete, merge, update content, update description, 移动文档, 更新内容, 修改描述, change description.
---

# Knowledge Manage — Document & KB Administration

All operations are **atomic**: each tool call updates disk file + `.tree-fs.json` + `.knowledge-base.yml` in one step. Metadata is always in sync.

## M1 — Survey
`kb_list()` + `kb_get_documents(source_kb_id)`

## M2 — Confirm Destructive
`kb_delete` / `kb_doc_delete` / `kb_doc_batch_delete` → ask user first (skip in Module Mode).

## M3 — Execute

### KB-level operations
| Operation | Tool | Notes |
|---|---|---|
| Rename KB | `kb_update(kb_id, name, description)` | Updates KB name + description. KB folder path stays the same (folder is not renamed on disk). |
| Delete KB | `kb_delete(kb_id)` | Irreversible. Deletes folder + all docs + `.knowledge-base.yml`. Confirm first. |

### Document operations
| Operation | Tool | Notes |
|---|---|---|
| Move doc | `kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id)` | Moves file on disk + syncs `.tree-fs.json` + both source/target `.knowledge-base.yml`. UUID preserved. Does NOT reindex — call `kb_index_document` on new path if needed. |
| Rename doc | `kb_doc_update_meta(kb_id, doc_path, name, description)` | Renames file on disk + syncs path in `.tree-fs.json` + `.knowledge-base.yml`. UUID preserved. |
| Update description | `kb_doc_update_meta(kb_id, doc_path, description)` | Updates description in `.tree-fs.json` + `.knowledge-base.yml`. |
| Update content | `kb_doc_update_content(kb_id, doc_path, content)` | Overwrites file on disk + syncs `file_size` in `.tree-fs.json` + `.knowledge-base.yml`. Does NOT auto-reindex — call `kb_index_document` separately if needed. |
| Delete doc | `kb_doc_delete(kb_id, doc_path)` | Deletes file from disk + `.tree-fs.json` + `.knowledge-base.yml`. Accepts bare name or full path. |
| Batch delete | `kb_doc_batch_delete(kb_id, ["KB/doc1.md", ...])` | **⚠️ MUST use full relative paths** (`"KB/doc.md"`). Bare names → "Not found". |
| Merge A→B | `for doc in docs: kb_doc_move(doc_path, B.kb_id)` then `kb_delete(A.kb_id)` | Confirm first. |

### Tree node operations (filesystem layer, not KB-indexed)
| Operation | Tool | Notes |
|---|---|---|
| Get single node | `fs_get_node(node_id)` | By UUID |
| Create folder (or sub-KB) | `fs_create_folder(name, parent_id, description, is_knowledge_base=false)` | is_knowledge_base=true makes it a KB |
| Create file (metadata only) | `fs_create_file(name, parent_id, description)` | No content — use kb_doc_create for content |
| Rename/redescribe node | `fs_update_node(node_id, name, description)` | Tree node metadata only |
| Delete node (recursive) | `fs_delete_node(node_id)` | Irreversible — confirm first |

## M4 — Verify
`kb_get_documents(source)` + `kb_get_documents(target)` + `kb_list()` + `fs_get_tree()`

### Post-operation index/graph sync (atomic — separate calls):
- **After move**: old vector/graph index points to old path. Call `kb_index_document(kb_id=target, doc_path=new_path)` to reindex at new location. Optionally clean old: `kb_graph_delete_document(doc_path=old_path)`.
- **After content update**: old vector index is stale. Call `kb_index_document(kb_id, doc_path)` to rebuild.
- **After delete**: vector/graph entries may persist. Optionally call `kb_graph_delete_document(doc_path)` to clean graph.
- **After merge**: call `kb_graph_build_kb(target_kb_id, force=false)` to rebuild graph with new doc relationships.

## M5 — Report
"Moved 'file' from Source to Target. N docs remaining in source. Vector index rebuilt at new path."

## M6 — Update Content Flow
1. `kb_doc_read(kb_id, doc_path, max_chars=20000)` → present current content
2. User provides new content
3. `kb_doc_update_content(kb_id, doc_path, content)` → file + metadata synced (file_size updated in both .tree-fs.json and .knowledge-base.yml)
4. `kb_doc_read(kb_id, doc_path)` → verify
5. `kb_index_document(kb_id, doc_path)` → rebuild vector index (old index invalidated by content change)
