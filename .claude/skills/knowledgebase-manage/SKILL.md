---
name: knowledgebase-manage
description: >
  Document and KB administration operations. M1→M6 workflow (M6 = content
  update): move documents between KBs, rename/rediscribe KBs or documents,
  delete documents or empty KBs, merge KBs, update document content.
  Invoked by Archival when the task involves moving, renaming, deleting,
  or updating existing items.
  Trigger keywords: 移动, 改名, 重命名, 删除文档, 删除KB, 合并KB,
  move, rename, delete, merge, update content, update description,
  移动文档, 更新内容, 修改描述, change description.
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

## M4 — Verify（含知识图谱联动）📍 GRAPH

After every operation:
1. `kb_get_documents(source_kb_id)` — confirm source changed as expected.
2. `kb_get_documents(target_kb_id)` — confirm target reflects the change.
3. If KB deleted: confirm gone from `kb_list()`.
4. `fs_get_tree(include_files=True)` — confirm tree is clean.

### M4-G — 图谱联动清理 📍 GRAPH v4

管理操作后必须同步更新知识图谱（MCP 工具为主，API 为备用）：

| 管理操作 | 图谱联动 | 首选 MCP 工具 |
|---------|---------|------|
| **移动文档** | 删除旧路径图谱节点，重建新 KB 图谱 | `kb_graph_delete_document(old_doc_path)` |
| | | `kb_graph_build_kb(target_kb_id, force=false)` |
| **删除文档** | 删除图谱中的文档节点（级联清理边） | `kb_graph_delete_document(doc_path)` |
| **删除 KB** | 删除整个 KB 的图谱（级联清理） | `kb_graph_delete_kb(kb_id)` |
| **合并 KB-A 到 B** | 删除 KB-A 图谱，重建 KB-B 图谱 | `kb_graph_delete_kb(A_kb_id)` |
| | | `kb_graph_build_kb(B_kb_id, force=true)` |
| **重命名文档** | 图谱中 path 自动更新（无需手动操作） | — |
| **更新内容** | 重建向量索引时自动触发图谱更新 | `kb_batch_index(kb_id, [doc_path], force=true)` |

**图谱清理验证**：
```
# 验证删除是否成功
kb_graph_document(doc_path="<旧路径>")
→ 应返回空 document

# 验证新建是否成功
kb_graph_document(doc_path="<新路径>", limit=5)
→ 应显示文档信息 + 关联文档

# 验证 KB 概览是否更新
kb_graph_stats()
→ 检查 node_count / edge_count 是否合理
```

**MCP 工具不可用时**使用同功能的原始 API（`DELETE /api/v1/graph/document` 等）。

## M5 — Report

Summarize concisely:
"Moved 'filename.pdf' from [SourceKB] to [TargetKB]. [N] documents
in source remaining. Tags preserved."

## M6 — Update Document Content

Invoked when the user says "update this document" or "change the content".

### M6a — Read Current Content
```
kb_doc_read(kb_id, doc_path, max_chars=20000)
```
Present the current content to the user so they know what they're changing.

### M6b — Execute Update
```
kb_doc_update_content(kb_id, doc_path, "<new content>")
```
**Bug**: `file_size` in `kb_get_documents` stays stale after update (Known Gotcha #3).
Use `fs_get_children` for the real size if needed.

### M6c — Verify
```
kb_doc_read(kb_id, doc_path, max_chars=2000)
```
Confirm the first ~2000 chars show the updated content.

### M6d — Report
"Updated '[name]' content. [N] characters written. Old description unchanged."

