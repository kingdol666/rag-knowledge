---
name: knowledgebase-list
description: Knowledge base listing and discovery. L1→L3 workflow: full inventory of all KBs with document counts, KB drill-down with document metadata, folder tree browsing. Read-only. Invoked by Archival when information needs to be found or displayed. Trigger keywords: 查看, 列出, 展示, 浏览, 有什么, 列出来, 清单, list, show, overview, tree, browse, display, 知识库内容, 知识库有什么, 查看知识库, 有哪些知识库.
---

# Knowledge List — Collection Overview & Discovery

**Read-only. Never modify anything.**

## L1 — Full Inventory
`kb_list()` + `kb_tags_list()` + `fs_get_tree(max_depth=2)`
Present as: `KB Name | Description | Docs` table.
Tags list.

**Lightweight alternative**: `kb_catalog()` returns only `[{kb_id, name, description, doc_count}]` — minimal context, ideal for agentic first-pass scan.

## L2 — KB Drill-Down
`kb_get_documents(kb_id)` → table: Name | Description | Type | Tags | Size | Added
Check `vector_index` field presence per doc (indexed or not).
Offer to read (`kb_doc_read`) or preview (`preview_file`). If 0 docs → "This KB is empty."

**Lightweight alternative**: `kb_doc_catalog(kb_id)` returns only `[{doc_path, name, description}]` — minimal context for agentic scan.

## L3 — Browse Tree
`fs_get_tree(include_files=True, max_depth=0)` + `fs_get_count()`
Indented tree: KBs → sub-KBs → docs. Offer to drill with `fs_get_children`.

**Lightweight alternative**: `fs_catalog_all(include_files=True)` returns flat `[{id, path, name, description, type, is_kb, doc_count, parent_id}]` — one call, minimal fields.
