---
name: knowledgebase-ingest
description: Document ingestion pipeline for knowledge bases. Complete A1→A10 workflow: survey collection, classify each document by domain, find or create the correct KB (hierarchical with sub-KB support), select tags from vocabulary, execute storage (parse-path or direct), assign tags, verify, and auto-create sub-KBs when a parent KB grows too large. Trigger keywords: 入库, 上传, 导入, 存储, 解析, 解析PDF, 保存到, store, upload, import, parse, save to KB, ingest, 入库文档, 上传文档, 存入知识库, 放文档, 添加文档, add doc, put document.
---

# Knowledge Ingest -- Document Ingestion Pipeline

## A0 -- Duplicate Pre-Check
`kb_search(query=filename, top_k=5)` for possible match. If name matches AND similar size, read 500 chars to confirm.

## A1 -- Survey
`kb_list()` + `kb_tags_list()` + `fs_get_tree(max_depth=3)` to understand KB hierarchy.

## A2 -- Classify
Determine parent domain + sub-domain from filename and/or content sample (read first 500 chars).

## A3 -- Find/Create KB (Hierarchical)
Match against `kb_list()` using domain + sub-domain. If sub-domain clear but no matching sub-KB, create one via `kb_create(parent_id=parent_kb_id)`. See [references/sub-kb-creation.md](references/sub-kb-creation.md) for full procedure.

## A4 -- Description (基于真实内容)
**Must read content before writing.** Never guess from filename.
- Parse-path: parse, poll done, read content, write description
- Direct-path: `kb_doc_read`, write description
For templates, examples, verification rules, and sub-agent batch workflow see [references/description-guide.md](references/description-guide.md).

## A5 -- Tags
`kb_tags_list()` -- pick 2-5 tags (>=90% vocabulary reuse). `kb_tag_create()` only if concept absent.

## A5b -- Large Document Split
If markdown_chars > 80K or file_size > 50KB: split by chapter headings into separate documents. For complete procedure (size check, outline, split, create chunks, assign tags, delete original, reindex, graph verify) see [references/doc-splitting.md](references/doc-splitting.md).

## A6 -- Store
**Parse-path (PDF/DOCX/Images):**
```
parse_doc(file_path="<abs_path>", kb_id="<UUID>", description="Parsing...", tags=[])
```
Poll `parse_task_status(task_id)`. When done, use real description (from A4) via `kb_doc_update_meta`.

**Direct-path (MD/TXT/code):**
```
kb_doc_create(kb_id, name="doc.md", content="<text>", description="<from A4>")
```

Parse and create now trigger automatic vector + graph indexing.

## A7 -- Assign Tags
`kb_doc_update_tags(kb_id, doc_path, ["tag1", "tag2"])`

## A8 -- Verify
- `parse_task_status` -- done?
- `kb_get_documents(kb_id)` -- doc exists?
- Tags applied? `kb_doc_get_by_tag(tag, kb_id)`
- Vector + graph indexed? If not: `kb_batch_index(kb_id, doc_paths)` + `kb_graph_build_kb(kb_id)`

## A9 -- Sub-KB Creation Check
If parent KB has >=8 docs across >=2 sub-domains: create sub-KBs. See [references/sub-kb-creation.md](references/sub-kb-creation.md) for full procedure.

## A10 -- Report
Filename, target KB (and sub-KB if applicable), tags, parse status, hierarchy changes, quality notes.

## Critical Rules
1. A1: MUST `fs_get_tree(max_depth=3)` to understand KB hierarchy
2. A4: Read content before description -- never guess from filename. Use sub-agent for >=3 docs
3. A5b: Large doc splitting is mandatory (>80K chars or >50KB), not optional
4. A6 -> A5b: Parse then immediately check size, split if needed before A7
5. A9: Sub-KB check prevents retrieval degradation as KB grows

## Tool Signature Reference
- `parse_doc(file_path, kb_id, description="", tags=[], use_ocr=true)` -- non-blocking, returns task_id
- `kb_doc_create(kb_id, name, content, description="")` -- content is full markdown text
- `kb_create(name, description="", parent_id="")` -- parent_id for sub-KBs
- `kb_doc_read(kb_id, doc_path, max_chars=800)` -- doc_path is bare filename when kb_id provided
- `kb_doc_update_meta(kb_id, doc_path, description=...)` -- same bare filename rule
- `kb_doc_update_tags(kb_id, doc_path, [tags...])` -- same bare filename rule
- `parse_task_status(task_id)` -- returns markdown_chars/image_count when done
- `kb_doc_delete(kb_id, doc_path)` -- same bare filename rule
- `kb_doc_move(doc_path, target_kb_id)` -- moves doc between KBs
- `kb_index_document(kb_id, doc_path)` -- single doc vector+graph index
- `kb_batch_index(kb_id, [paths...], force=false)` -- batch vector+graph index
