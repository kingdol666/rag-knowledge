---
name: knowledge-store
description: >
  Intelligent knowledge base document storage and organization. Use when the user
  wants to store documents into the knowledge base, upload and parse files (PDF,
  DOCX, Excel, images) into a KB, organize knowledge into categories, add tags
  to documents, batch-import files, or any task involving "save this to the
  knowledge base", "parse and store", "upload to KB", "organize knowledge",
  "knowledge base storage", "文档入库", "知识库存储", "解析上传", "分类管理".
  This skill handles the full lifecycle: discovering existing KB structure,
  matching documents to the right KB (or creating one), parsing non-text formats
  via MinerU OCR, applying relevant tags from the existing tag vocabulary,
  and writing accurate descriptions for future retrievability.
---

# Knowledge Store

Automatically classify, parse, tag, and store documents into the RAG Knowledge
Platform via the `kb-mcp` MCP tools. This skill makes the Agent act as a
librarian: survey the shelves, find the right one, describe what is stored,
and label it so later retrieval is fast and precise.

---

## Tool Reference

All operations use `kb-mcp` MCP tools. The full tool list:

| Category | Tools |
|---|---|
| **Survey** | `kb_list`, `kb_get_documents`, `kb_tags_list`, `kb_doc_get_by_tag` |
| **KB CRUD** | `kb_create`, `kb_update`, `kb_delete` |
| **Doc CRUD** | `kb_doc_create`, `kb_doc_read`, `kb_doc_update_meta`, `kb_doc_update_content`, `kb_doc_delete`, `kb_doc_move` |
| **Parse** | `parse_pdf_to_kb`, `parse_pdf_to_kb_batch`, `parse_task_status`, `parse_tasks_list` |
| **Tags** | `kb_tag_create`, `kb_doc_update_tags` |

The `parse_pdf*` tools accept PDF, DOCX, XLSX, PPTX, and image files via the
backend MinerU engine. They return a `task_id` immediately (non-blocking);
poll with `parse_task_status`.

---

## Phase 1 — Survey Existing KBs

Before storing anything, call `kb_list()` to get every KB with its `kbId`,
`name`, `description`, and `documentCount`. Report this landscape to the user
so they see what "bookshelves" exist.

```
kb_list() → { knowledgeBases: [{ kbId, name, description, documentCount, path }] }
```

---

## Phase 2 — Determine File Handling Strategy

For each file the user wants to store, inspect the extension FIRST:

### Parse path (binary / rich formats)
Extensions: `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`,
`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`

These MUST go through MinerU parsing. Use `parse_pdf_to_kb(file_path, kb_id, ...)`.
The backend extracts text + images into Markdown, then saves the Markdown into
the KB. Do NOT use `kb_doc_create` for these — the parse pipeline handles
everything end-to-end.

### Direct upload path (already-readable formats)
Extensions: `.md`, `.txt`, `.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.html`, `.log`

These can be read directly and stored via `kb_doc_create(kb_id, name, content, description)`.
Read the file content with a file-read tool first, then pass it as the `content`
parameter.

---

## Phase 3 — Match Document to KB

For each document, determine its topic domain. Use the filename and any
available context (user-provided description, file content preview) to infer
the domain. Common domains: energy, medical, legal, finance, computer-science,
manufacturing, education, etc.

### Match against existing KBs

Compare the inferred domain against each KB's `name` and `description`:

- **Strong match** (name or description contains the domain keyword, or is
  clearly the same subject) → use that `kbId`
- **Weak / no match** → create a new KB

### Creating a new KB

When no suitable KB exists:
```
kb_create(name="DomainName", description="...")
```

Rules for `description`:
- Must be a 1-3 sentence summary of what this KB holds
- Must mention the domain and typical document types
- Example: "Energy industry documents including coal-fired power plant
  monitoring reports, turbine maintenance logs, and emissions analysis.
  Primarily Chinese technical documents."
- Never leave it empty or use a placeholder like "test"

---

## Phase 4 — Execute Storage

### Parse path (per document)

```
parse_pdf_to_kb(
    file_path="/abs/path/to/doc.pdf",
    kb_id="<uuid>",
    use_ocr=True,
    description="<1-2 sentence summary of document content>",
    tags=["tag1", "tag2"]
)
```

Returns immediately: `{ task_id, status: "running" }`. Note the `task_id`.
After submission, tell the user parsing has started.

### Direct upload path (per document)

First read the file content, then:
```
kb_doc_create(
    kb_id="<uuid>",
    name="filename.md",
    content="<full file content>",
    description="<1-2 sentence summary>"
)
```

### Batch parsing

When multiple files go to the SAME KB, use:
```
parse_pdf_to_kb_batch(
    file_paths=["/a.pdf", "/b.docx"],
    kb_id="<uuid>",
    descriptions=["Description for a", "Description for b"],
    tags=["shared-tag1", "shared-tag2"]
)
```

When files go to DIFFERENT KBs, group by target KB and call
`parse_pdf_to_kb` once per file (or per same-KB group via batch).

---

## Phase 5 — Tag Documents

Tags are essential for later retrieval via `kb_doc_get_by_tag`.

### Step 1 — Load existing tags vocabulary

Always call `kb_tags_list()` first. This returns all tags already registered
in the system.

### Step 2 — Select tags for the document

For each document, pick 2-5 tags that describe its content. Priority order:
1. **Reuse existing tags** from the vocabulary whenever they fit
2. **Create new tags** via `kb_tag_create(tag)` only when no existing tag covers the concept
3. Tags should be short (1-3 words), lower-case, and domain-relevant

Good tags: `"deep-learning"`, `"ner"`, `"emissions-monitoring"`, `"turbine-fault"`
Bad tags: `"test"`, `"doc"`, `"pdf"`, `"important"`

### Step 3 — Apply tags

After the document is stored (parse complete or direct upload done):
```
kb_doc_update_tags(kb_id="<uuid>", doc_path="<relative-path>", tags=["tag1", "tag2"])
```

---

## Phase 6 — Verify and Report

After all files are submitted, poll the parse tasks:
```
parse_task_status(task_id="...")
```

When all tasks are `done`, call `kb_get_documents(kb_id)` for each target KB
to confirm the documents appear.

Final report to user: a table mapping each file → KB → tags → status.

---

## Description Quality Rules

Every KB and document MUST have a meaningful `description`. This is critical
for the future `knowledge-query` skill, which will use descriptions to decide
which KBs to search.

- KB description: domain + typical content types + language hint
- Document description: what this specific document is about, in 1-2 sentences
- Never use: "test", "test KB", empty string, file name repeated
- Read a portion of the document content (first ~500 chars) to write an
  accurate description when the filename alone is insufficient

---

## Edge Cases

**File already exists**: Before parsing/uploading, check `kb_get_documents(kb_id)`
for a document with the same name. If found, ask the user: overwrite (re-parse)
or skip.

**No KBs at all**: If `kb_list()` returns an empty list, create the first KB
with a broad domain name based on the first document's topic.

**Mixed format batch**: When the user uploads PDF+DOCX+TXT together, separate
them by format. PDF/DOCX go through parse path; TXT/MD go through direct path.

**parse_pdf fails**: If `parse_task_status` returns `status: "error"`, report
the error to the user. Try once more with `use_ocr=true` if the first attempt
used `use_ocr=false`.

**Very large files**: For files >50MB, warn the user that parsing may take
several minutes. Submit as usual; the non-blocking design handles this.

---

## Anti-Patterns

- Do NOT call `kb_doc_create` for PDF/DOCX/XLSX files — they must go through
  `parse_pdf_to_kb` so MinerU extracts the content
- Do NOT skip `kb_tags_list()` before assigning tags — always reuse existing
  tags first
- Do NOT leave `description` empty or use placeholders
- Do NOT create a new KB for every single document — group related documents
  into shared KBs
- Do NOT wait synchronously for parse completion — use the non-blocking
  task_id/poll pattern
