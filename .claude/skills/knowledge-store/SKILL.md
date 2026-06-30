---
name: knowledge-store
description: >
  Intelligent knowledge base document storage and organization. Use when the user
  wants to store documents into the knowledge base, upload and parse files (PDF,
  DOCX, Excel, images) into a KB, organize knowledge into categories, add tags
  to documents, batch-import files, or any task involving "save this to the
  knowledge base", "parse and store", "upload to KB", "organize knowledge",
  "knowledge base storage", "文档入库", "知识库存储", "解析上传", "分类管理".
  Also serves as a module for other skills (deep-research, web-search, data
  analysis) that need to persist their outputs into the KB. When another skill
  completes research and needs to store findings, follow the Module Protocol
  section — no user interaction required; operate silently and return a summary.
---

# Knowledge Store

Two-in-one skill: acts as a **user-facing librarian** when triggered directly,
and as a **silent storage module** when called by another skill or agent task.

All operations use the `kb-mcp` MCP tools. Every stored document gets placed
in the right knowledge base, tagged with vocabulary-aware labels, and annotated
with a content-accurate description so the companion `knowledge-query` skill
can find it later.

---

## Mode Detection

At the start, determine which mode you are in:

**User Mode** — the user spoke to you directly about storing documents.
- Interact with the user: show them the KB landscape, ask for confirmation
  before creating new KBs, report progress at each phase.
- If the user says "just do it" or "auto", skip confirmations but still report.

**Module Mode** — another skill or agent task asked you to store content.
- Operate SILENTLY. No questions to the user. No progress narration.
- Make decisions autonomously: pick or create KBs, choose tags, write descriptions.
- At the end, return ONLY a compact JSON summary block the calling skill can read.
- Detect this mode when the context shows a parent task that is NOT the user
  directly asking about storage (e.g., a deep-research result set, scraped content,
  or an agent pipeline step).

---

## Tool Reference

| Category | Tools |
|---|---|
| **Survey** | `kb_list`, `kb_get_documents`, `kb_tags_list`, `kb_doc_get_by_tag` |
| **KB CRUD** | `kb_create`, `kb_update`, `kb_delete` |
| **Doc CRUD** | `kb_doc_create`, `kb_doc_read`, `kb_doc_update_meta`, `kb_doc_update_content`, `kb_doc_delete`, `kb_doc_move` |
| **Parse** | `parse_pdf_to_kb`, `parse_pdf_to_kb_batch`, `parse_task_status`, `parse_tasks_list` |
| **Tags** | `kb_tag_create`, `kb_doc_update_tags` |

`parse_pdf*` accepts PDF, DOCX, XLSX, PPTX, images via MinerU. Returns
`task_id` immediately (non-blocking). Poll with `parse_task_status`.

---

## Shared Workflow (both modes)

Both modes follow the same 6-phase pipeline. The only difference is whether
you interact with the user along the way or operate silently.

---

### Phase 1 — Survey Existing KBs

```
kb_list() -> { knowledgeBases: [{ kbId, name, description, documentCount, path }] }
```

User Mode: show the list to the user.
Module Mode: keep it in memory for matching.

---

### Phase 2 — Determine Storage Method

Inspect each item's source and pick the appropriate path:

#### A. File on disk (any extension)
The item has an absolute file path. Check the extension:

**Parse path** — extensions: `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`,
`.pptx`, `.ppt`, `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`
→ Use `parse_pdf_to_kb(file_path, kb_id, ...)`. MinerU extracts text+images
into Markdown, then saves it into the KB. Do NOT use `kb_doc_create`.

**Direct path** — extensions: `.md`, `.txt`, `.csv`, `.json`, `.yaml`,
`.yml`, `.xml`, `.html`, `.log`
→ Read the file content, then use `kb_doc_create(kb_id, name, content, description)`.

#### B. Content in memory (no file on disk)
The content is a string the calling skill already has (research results,
scraped text, generated summary, structured data).
→ Always use `kb_doc_create(kb_id, name, content, description)`.
→ The `name` should be descriptive: `"deep-research-llm-safety-2026.md"`,
  `"web-scrape-wikipedia-fusion-energy.md"`, not `"output.md"`.

---

### Phase 3 — Match Content to KB

For each item, determine its topic domain from the content itself (read first
~1000 chars if needed). Infer the domain from keywords, subject matter, and
terminology.

Compare against existing KBs' `name` and `description`:

| Match quality | Action |
|---|---|
| Strong (domain keyword in name/desc) | Use that `kbId` |
| Weak or none | `kb_create(name="DomainName", description="...")` |

**KB description rules** (critical for later retrieval):
- 1-3 sentences covering: domain, typical content types, primary language
- Good: "Energy industry technical reports on thermal power plants, emissions
  monitoring, turbine diagnostics, and grid management. Mostly Chinese."
- Bad: "test", "docs", "", "Energy"

User Mode: ask "I'll create a new KB 'Energy-Technical' — OK?"
Module Mode: create it silently.

---

### Phase 4 — Execute Storage

**For disk files (parse path):**
```
parse_pdf_to_kb(
    file_path="/abs/path/doc.pdf",
    kb_id="<uuid>",
    use_ocr=True,
    description="<1-2 sentences summarizing the document>",
    tags=["tag1", "tag2"]
)
```
Returns `{ task_id, status: "running" }`. Note the task_id for later polling.

**For disk files (direct path) or in-memory content:**
```
kb_doc_create(
    kb_id="<uuid>",
    name="descriptive-filename.md",
    content="<full text content>",
    description="<1-2 sentence summary>"
)
```
Returns immediately with the created document record.

**Batch rule:** Files going to the same KB can use `parse_pdf_to_kb_batch`.
Files going to different KBs must be grouped by target KB first.

---

### Phase 5 — Tag Documents

Tags are essential for `kb_doc_get_by_tag` discovery.

1. ALWAYS call `kb_tags_list()` first to load the vocabulary
2. For each document, select 2-5 tags:
   - **Prefer existing tags** from the vocabulary (90%+ should reuse)
   - **Create new tags** via `kb_tag_create(tag)` only when the concept is absent
3. Tags: short (1-3 words), lowercase, domain-specific
   - Good: `"deep-learning"`, `"emissions-monitoring"`, `"turbine-fault"`
   - Bad: `"test"`, `"doc"`, `"pdf"`, `"important"`, `"misc"`
4. Apply: `kb_doc_update_tags(kb_id="<uuid>", doc_path="<relpath>", tags=[...])`

---

### Phase 6 — Verify and Report

Poll parse tasks: `parse_task_status(task_id="...")`.

**User Mode report:** table of file → KB → tags → status.
**Module Mode report:** a single compact JSON block (see Module Protocol below).

---

## Module Protocol

When another skill or agent pipeline calls knowledge-store as a module,
follow this compact protocol. Read the content, then execute WITHOUT
any user interaction.

### Entry contract

The calling context will contain content to store — as file paths, as
in-memory strings, or both. Look for:
- Absolute file paths mentioned in the task (research downloaded files)
- Text blocks labeled as "findings", "results", "summary", "output"
- Structured data the calling skill wants persisted

### Silent execution checklist

```
[ ] Survey:   kb_list() — memorize KB landscape
[ ] Classify: for each item, read content, infer domain
[ ] Match:    for each item, pick existing kbId OR kb_create() silently
[ ] Tags:     kb_tags_list() — load vocabulary
[ ] Store:    parse_pdf_to_kb() for binary files, kb_doc_create() for text
[ ] Tag:      kb_doc_update_tags() for each stored doc
[ ] Verify:   poll parse_task_status() if any parse tasks were submitted
[ ] Report:   output the summary block below
```

### Module output format

After ALL items are processed (parse tasks complete), output exactly:

```json
{
  "stored_by": "knowledge-store",
  "total_items": 3,
  "results": [
    {
      "item": "Deep Research: LLM Safety 2026",
      "kb_name": "AI-Safety",
      "kb_id": "uuid",
      "doc_name": "deep-research-llm-safety-2026.md",
      "doc_path": "AI-Safety/deep-research-llm-safety-2026.md",
      "tags": ["llm-safety", "alignment", "red-teaming"],
      "method": "kb_doc_create"
    }
  ],
  "new_kbs_created": ["AI-Safety"],
  "new_tags_created": ["red-teaming"]
}
```

This JSON is machine-readable by the calling skill so it can reference
stored documents in its own workflow.

---

## Description Quality Rules

| Target | Requirement |
|---|---|
| KB description | Domain + typical content + language. 1-3 sentences. |
| Doc description | What THIS document is about. 1-2 sentences. Read content to write it. |
| Forbidden | Empty string, "test", filename repeated, "TBD", placeholder |

---

## Edge Cases

- **Duplicate doc name in KB**: auto-rename with `(1)`, `(2)` suffix via
  `kb_doc_create`'s built-in dedup
- **No KBs exist**: create the first KB based on the first document's domain
- **Mixed binary+text batch**: split into parse and direct groups, process in parallel
- **parse_pdf fails**: retry once with `use_ocr=true`. If still failing, report error
- **Files >50MB**: in User Mode warn the user; in Module Mode proceed (parse is
  non-blocking anyway)
- **Module called with zero content**: return `{ "stored_by": "knowledge-store",
  "total_items": 0, "results": [], "note": "No content to store" }`

---

## Anti-Patterns

- ❌ `kb_doc_create` for PDF/DOCX/XLSX → must use `parse_pdf_to_kb`
- ❌ Skipping `kb_tags_list()` → always load vocabulary first
- ❌ Empty or placeholder descriptions → read content, write real summary
- ❌ One KB per document → group related docs into shared KBs
- ❌ Synchronous wait for parse → submit task_id, poll later
- ❌ Module Mode asking the user questions → operate silently
