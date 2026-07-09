---
name: knowledgebase-list
description: Knowledge base listing and discovery. L1→L3 workflow: full inventory of all KBs with document counts, KB drill-down with document metadata, folder tree browsing. Read-only. Invoked by Archival when information needs to be found or displayed. Trigger keywords: 查看, 列出, 展示, 浏览, 有什么, 列出来, 清单, list, show, overview, tree, browse, display, 知识库内容, 知识库有什么, 查看知识库, 有哪些知识库.
---

# Knowledge List — Collection Overview

**Read-only. Never modify anything.**

## L1 — Full Inventory
```
kb_list()                    # all KBs: id, name, description, docCount
kb_tags_list()               # full tag vocabulary
fs_get_tree(max_depth=2)     # KB hierarchy
```
Lightweight: `kb_catalog()` returns `[{kb_id, name, description, doc_count}]`.

Present as table: KB Name | Description | Docs.

## L2 — KB Drill-Down
```
kb_get_documents(kb_id)      # docs with name, path, tags, size, vector_index, dates
```
Lightweight: `kb_doc_catalog(kb_id)` returns `[{doc_path, name, description}]`.

Check `vector_index` field per doc. Offer `kb_doc_read` or `preview_file` for details.

## L3 — Browse Tree
```
fs_get_tree(include_files=True, max_depth=0)   # 0 = unlimited
fs_get_count()                                  # folder/file/total counts
```
Lightweight: `fs_catalog_all(include_files=True)` — flat list in one call.
