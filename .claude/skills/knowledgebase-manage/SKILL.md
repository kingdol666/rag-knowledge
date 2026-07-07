---
name: knowledgebase-manage
description: Document and KB administration operations. M1→M6 workflow: move documents between KBs, rename/rediscribe KBs or documents, delete documents or empty KBs, merge KBs, update document content. Invoked by Archival when the task involves moving, renaming, deleting, or updating existing items. Trigger keywords: 移动, 改名, 重命名, 删除文档, 删除KB, 合并KB, move, rename, delete, merge, update content, update description, 移动文档, 更新内容, 修改描述, change description.
---

# Knowledge Manage — Document & KB Administration

## M1 — Survey
kb_list() + kb_get_documents(source_kb_id)

## M2 — Confirm Destructive
kb_delete / kb_doc_delete / kb_doc_batch_delete → ask user first (skip in Module Mode).

## M3 — Execute
| Operation | Tool | Notes |
|---|---|---|
| Move doc | kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id) | Non-destructive |
| Rename KB | kb_update(kb_id, name, description) | Bug: path not refreshed, use UUID |
| Rename doc | kb_doc_update_meta(kb_id, doc.name, name, description) | Bug: path stays old |
| Update content | kb_doc_update_content(kb_id, doc.name, content) | Triggers auto-reindex |
| Delete doc | kb_doc_delete(kb_id, doc_path) | Accepts bare name or full path |
| Batch delete | kb_doc_batch_delete(kb_id, ["KB/doc1.md", ...]) | MUST use full relative paths! |
| Delete KB | kb_delete(kb_id) | Irreversible. Confirm first. |
| Merge A→B | for doc in docs: kb_doc_move → kb_delete(A) | Confirm first. |

## M4 — Verify
kb_get_documents(source) + kb_get_documents(target) + kb_list() + fs_get_tree()
After destructive ops: kb_graph_delete_document/delete_kb to sync graph.
After moves: kb_graph_build_kb(target_kb_id, force=false) to rebuild graph.

## M5 — Report
"Moved 'file' from Source to Target. N docs remaining in source."

## M6 — Update Content
kb_doc_read(kb_id, doc.name, max_chars=20000) → present current → kb_doc_update_content → kb_doc_read verify.
Note: file_size stays stale after update. Use fs_get_children for real size.
