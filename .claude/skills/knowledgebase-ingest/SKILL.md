---
name: knowledgebase-ingest
description: Document ingestion pipeline for knowledge bases. Content-first workflow A0→A9: survey collection, acquire real content (parse or read), analyze content to determine domain/target-KB/tags/description, find or create the correct KB (hierarchical with sub-KB support), execute storage by file type, assign content-derived tags, build vector index + knowledge graph, verify, and auto-create sub-KBs when a parent KB grows too large. No document splitting. Trigger keywords: 入库, 上传, 导入, 存储, 解析, 解析PDF, 保存到, store, upload, import, parse, save to KB, ingest, 入库文档, 上传文档, 存入知识库, 放文档, 添加文档, add doc, put document.
---

# Knowledge Ingest — Document Ingestion Pipeline

Store each document as a **single unit** with its **COMPLETE original content**. Never truncate, summarize, or split.

## A0 — Duplicate Pre-Check
`kb_search(query=filename, top_k=5)`. If name matches and similar size, read 500 chars to confirm. Skip if duplicate.

## A1 — Survey
```
kb_list()                    # all KBs
kb_tags_list()               # tag vocabulary
fs_get_tree(max_depth=3)     # KB hierarchy
```

## A2 — Acquire Content

### Parse-path (PDF/Word/Excel/PPTX/Images)
```
parse_doc(file_path="<abs_path>", use_ocr=true)   # non-blocking, returns task_id
# Poll until done:
parse_task_status(task_id)  →  {markdown, markdown_path, images_dir, image_count}
```
For ≥3 files: `parse_doc_batch(file_paths=[...], use_ocr=true)` — single task_id for all.

Read first 3000 chars of `markdown` for analysis (A3). **This sample is for analysis only — the full content is stored automatically in A5.**

### Direct-path (MD/TXT/Code/JSON/YAML)
Read file content directly. Use first 3000 chars for analysis.

### Binary (non-text)
Skip analysis. Use `fs_upload_file(file_path, parent_id, description)`.

## A3 — Analyze Content
Read the 3000-char sample and determine:
- **Domain** + **sub-domain** from real content
- **Target KB**: match from A1 survey, or create new
- **Tags**: 2-5 content-derived tags (≥90% reuse from `kb_tags_list()`)
- **Description**: content-based, following [description-guide.md](references/description-guide.md)

For ≥3 docs or >50KB single doc: delegate analysis to a sub-agent with the content sample, existing KB list, and tag vocabulary. Request JSON output with `title, domain, sub_domain, methods, scenario, key_findings, language, target_kb_match, suggested_tags, suggested_description`.

## A4 — Find/Create KB
- **Matched**: use the matched KB's UUID.
- **No match**: `kb_create(name="<Domain>-<SubDomain>", description="...", parent_id="")`.
- **Sub-domain of existing KB**: `kb_create(name="<Parent>-<Sub>", description="...", parent_id=parent_kb.kb_id)`.

## A5 — Store Document

### Parse-path — Use kb_doc_save_parsed (stores FULL content + images)
```
save_result = kb_doc_save_parsed(
    parent_id=target_kb_id,
    task_id="<from A2>",            # auto-extracts full markdown + images_dir
    description=analysis.description
)
doc_path = save_result.files[0].path
doc_id = save_result.files[0].id
```
This writes the **complete** parsed markdown to disk, copies **all** images to the KB's `images/` folder, and updates `.tree-fs.json` + `.knowledge-base.yml` atomically.

**Never use `kb_doc_create` for parsed documents** — it truncates content and loses images.

### Direct-path — Use kb_doc_create
```
kb_doc_create(kb_id=target_kb_id, name="doc.md", content=file_content, description=analysis.description)
```

## A6 — Index + Tag
```
kb_index_document(kb_id=target_kb_id, doc_path=doc_path)    # vector + graph index
kb_doc_update_tags(kb_id=target_kb_id, doc_path=doc_path, tags=analysis.suggested_tags)
```

## A7 — Verify
- `kb_doc_read(kb_id, doc_path, max_chars=500)` — confirm content is full (not truncated)
- Check `.knowledge-base.yml` for `vector_index` field
- Check image count if parse-path

## A8 — Sub-KB Check
If parent KB has ≥8 docs across ≥2 sub-domains: create sub-KBs. See [sub-kb-creation.md](references/sub-kb-creation.md).

## A9 — Report
File, type, title, target KB, description, tags, content size, image count, index status.

## Tool Reference
- `parse_doc(file_path, use_ocr=true)` — non-blocking parse, returns task_id
- `parse_task_status(task_id)` — poll for result (markdown, images_dir, etc.)
- `kb_doc_save_parsed(parent_id, task_id="", description="")` — ⭐ save FULL content + images for parse-path docs
- `kb_doc_create(kb_id, name, content, description="")` — for direct-path/in-memory docs
- `kb_index_document(kb_id="", doc_path="", doc_id="")` — vector + graph index
- `kb_doc_update_tags(kb_id, doc_path, tags)` — assign tags
- `kb_doc_read(kb_id="", doc_path="", path="", doc_id="", max_chars=20000)` — read content
- `kb_create(name, description="", parent_id="")` — create KB or sub-KB
- `fs_upload_file(file_path, parent_id="", description="")` — binary upload, no index
