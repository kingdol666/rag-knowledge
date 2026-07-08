---
name: knowledgebase-ingest
description: Document ingestion pipeline for knowledge bases. Content-first workflow A0→A9: survey collection, acquire real content (parse or read), analyze content to determine domain/target-KB/tags/description, find or create the correct KB (hierarchical with sub-KB support), execute storage by file type, assign content-derived tags, build vector index + knowledge graph, verify, and auto-create sub-KBs when a parent KB grows too large. No document splitting. Trigger keywords: 入库, 上传, 导入, 存储, 解析, 解析PDF, 保存到, store, upload, import, parse, save to KB, ingest, 入库文档, 上传文档, 存入知识库, 放文档, 添加文档, add doc, put document.
---

# Knowledge Ingest — Content-First Document Ingestion Pipeline

## Core Principle: Content First, Decision Second

Every document is ingested as a **single unit**. No splitting, no chunking into separate documents.

**The fundamental shift**: we acquire real content FIRST, then use that content to decide which KB, what tags, and what description. Decisions are never based on filenames alone.

The pipeline routes by file type:

- **Parse-path** (`.pdf .docx .xlsx .pptx .jpg .png .bmp .tiff`): parse → **read content** → analyze → create doc → index
- **Direct-path** (`.md .txt .csv .json .yaml .html .py .js .ts .sh .log .xml`): **read content** → analyze → create doc → index
- **In-memory text**: analyze → create doc → index

---

## A0 — Duplicate Pre-Check
`kb_search(query=filename, top_k=5)` for possible match. If name matches AND similar size, read 500 chars to confirm. Skip ingestion if duplicate confirmed.

## A1 — Survey (Understand the KB Landscape)
```
kb_list()                    → all existing KBs with descriptions
kb_tags_list()               → full tag vocabulary
fs_get_tree(max_depth=3)     → KB hierarchy and folder structure
```
Build a mental model of what KBs exist, their domains, and their sub-KB structure. This is the **candidate pool** for A4 matching — but the final decision comes only after reading content in A3.

## A2 — Content Acquisition (Get Real Content)

**This is the critical step that separates content-first ingestion from blind ingestion.**

### Parse-path: PDF / Word / Excel / PPTX / Images

```
# Step 1: Parse — returns markdown content + paths, does NOT save to KB
parse_doc(file_path="<abs_path>", use_ocr=true)
# Poll for result (non-blocking):
parse_task_status(task_id)  →  {markdown, markdown_path, images_dir, image_count, ...}

# Step 2: READ the parsed markdown content (mandatory before any decision)
#   Read first 3000 chars for domain analysis + description generation
#   If document is long, also read a middle section (offset=1500, limit=100) for deeper classification
parsed_content = parse_task_status(task_id).markdown  # or read from markdown_path
```

For batch parsing (≥3 files): `parse_doc_batch(file_paths=[...], use_ocr=true)` — single task_id for all files, poll `parse_task_status`.

To list all running parse tasks: `parse_tasks_list(status="running")`.

### Direct-path: MD / TXT / Code / JSON / YAML

```
# Read file content directly (no parsing needed)
content = read_file(file_path)  # or: kb_doc_read after temporary upload
# Read first 3000 chars for analysis
```

### In-memory text
Content is already available — proceed directly to A3.

### Binary upload (non-text files that can't be parsed or indexed)
Skip A3 analysis. Use `fs_upload_file(file_path, parent_id, description)` directly. No vector index for binary files.

---

## A3 — Content Analysis (The Brain)

**Read the real content acquired in A2 and produce structured intelligence.**

This is where the Agent reads the document content and determines:
1. **True domain** — what field/industry/equipment is this about?
2. **Sub-domain** — what specific topic within that domain?
3. **Target KB** — which existing KB (from A1 survey) matches, or should a new one be created?
4. **Tags** — 2-5 content-derived tags (≥90% vocabulary reuse from A1's `kb_tags_list()`)
5. **Description** — A4-format description based on real content (see [description-guide.md](references/description-guide.md))

### A3a — Content Reading Protocol

```
# Read the first 3000 characters of real content
content_sample = content[:3000]

# For long documents, also sample a middle section
if len(content) > 6000:
    mid_sample = content[3000:6000]
```

### A3b — Structured Analysis Output

After reading, produce this analysis (internally or via sub-agent):

```
Content Analysis:
  title:          "Real title extracted from content (not filename)"
  domain:         "Primary domain (e.g., thermal power, polymer materials, NLP)"
  sub_domain:     "Specific sub-domain (e.g., coal mill fault, PVA biaxial stretching)"
  methods:        ["CNN-LSTM", "MSET", "finite element"]  (from content)
  scenario:       "What problem does this document address?"
  key_findings:   "Key results/data mentioned in content"
  language:       "zh / en / bilingual"
  target_kb:      "Matched KB name from A1 survey, or 'CREATE_NEW: <reason>'"
  suggested_tags: ["tag1", "tag2", "tag3"]  (reuse existing tags where possible)
  description:    "A4-format description based on real content"
```

### A3c — Sub-Agent Content Analysis (for batch or large documents)

When ingesting ≥3 documents simultaneously, or a single document > 50KB, delegate to sub-agent:

```
Agent(
  subagent_type="general-purpose",
  prompt="""Read the following document content, then output a structured analysis.

Source filename: {filename}
Content (first 3000 chars):
{content_sample}

Existing KBs and their descriptions:
{kb_list_summary}

Existing tag vocabulary:
{tags_list}

Output format (pure JSON, no markdown wrapping):
{
  "title": "Real document title extracted from content",
  "domain": "Detected primary domain",
  "sub_domain": "Specific sub-domain",
  "methods": ["method1", "method2"],
  "scenario": "What problem/scenario this document addresses",
  "key_findings": "Key results or data from content",
  "language": "zh/en/bilingual",
  "target_kb_match": "Exact KB name that matches, or null if no match",
  "target_kb_reason": "Why this KB matches (or why new KB needed)",
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "suggested_description": "Full A4-format description: [Subject] + [Method] + [Scenario] + [Key findings] + [Language]"
}"""
)
```

### A3d — Validation Checks

Before proceeding to A4, validate the analysis:
- Does the description contain specific method/equipment names from the content? If not, re-analyze.
- Do the suggested tags align with the detected domain? If not, adjust.
- Is `target_kb_match` reasonable given the domain? Cross-check against A1 survey.
- **Self-check**: "If someone in the future encounters [the scenario described], would reading just this description let them be 100% sure this document is what they need?" (See [description-guide.md](references/description-guide.md) A4c)

---

## A4 — Find/Create KB (Based on A3 Analysis)

Using the `target_kb_match` from A3b/A3c:

### If matched to existing KB:
```
# Use the matched KB's UUID directly
target_kb_id = matched_kb.kb_id
```

### If no match (A3 says CREATE_NEW):
```
# Create new KB with content-derived description
kb_create(
  name="<Domain>-<SubDomain>",           # e.g. "Polymer-Biaxial-Stretching"
  description="<A4b KB-level template from description-guide.md>",
  parent_id=""                            # or parent_kb_id for sub-KB
)
```

### Sub-KB creation:
If A3 analysis shows the document fits a sub-domain of an existing parent KB, and no sub-KB exists for that sub-domain:
```
kb_create(
  name="<ParentDomain>-<SubDomain>",
  description="<focused sub-KB description>",
  parent_id=parent_kb.kb_id
)
```
See [references/sub-kb-creation.md](references/sub-kb-creation.md) for full procedure.

---

## A5 — Execute Storage (with Real Description from A3)

### Parse-path: PDF / Word / Excel / PPTX / Images (2 remaining atomic steps)

```
# Step 1: Create document — writes file + .tree-fs.json + .knowledge-base.yml (with file UUID)
#         Use the parsed markdown content from A2 and description from A3
kb_doc_create(
  kb_id=target_kb_id,
  name="doc.md",
  content=parsed_markdown,
  description=analysis.description      # ← real content-based description from A3
)

# Step 2: Index — builds vector + graph index
kb_index_document(kb_id=target_kb_id, doc_path="<returned from step 1>")
# Or: kb_index_document(doc_id="<UUID from step 1>")
```

### Direct-path: MD / TXT / Code / JSON / YAML (2 atomic steps)

```
# Step 1: Create document with real content + real description
kb_doc_create(
  kb_id=target_kb_id,
  name="doc.md",
  content=file_content,
  description=analysis.description      # ← real content-based description from A3
)

# Step 2: Index
kb_index_document(kb_id=target_kb_id, doc_path="<returned from step 1>")
```

### Binary upload (non-text files that can't be parsed or indexed)

```
fs_upload_file(file_path="<abs_path>", parent_id=target_kb_id, description="<desc>")
# Note: no vector index for binary files
```

**Important**: Parse, upload, and index are **separate atomic operations**. The Skill orchestrates the full pipeline. Each step must succeed before proceeding to the next.

---

## A6 — Assign Tags (Content-Derived from A3)

```
kb_doc_update_tags(kb_id, doc_path, analysis.suggested_tags)
```

Tag rules:
- Use 2-5 tags from A3 analysis (content-derived, not filename-derived)
- ≥90% vocabulary reuse from `kb_tags_list()` — only `kb_tag_create()` if a concept is genuinely absent
- Tags should reflect the document's **methods, domain, and scenario** — not just its file type

## A7 — Verify

- `parse_task_status` — done? (parse-path only)
- `kb_get_documents(kb_id)` — doc exists?
- Tags applied? `kb_doc_get_by_tag(tag, kb_id)`
- Vector indexed? Check `.knowledge-base.yml` for `vector_index` field. If missing: `kb_index_document(kb_id, doc_path)` or `kb_batch_index(kb_id, [doc_paths])`
- Graph built? If not: `kb_graph_build_kb(kb_id)`
- **Content verification**: `kb_doc_read(kb_id, doc_path, max_chars=500)` — does the content match what the description claims? (See [description-guide.md](references/description-guide.md) A4d)

## A8 — Sub-KB Creation Check
If parent KB has ≥8 docs across ≥2 sub-domains: create sub-KBs. See [references/sub-kb-creation.md](references/sub-kb-creation.md) for full procedure.

## A9 — Report
```
Ingestion Report:
  File: {filename}
  Type: {parse-path / direct-path / in-memory / binary}
  Content Title: {title from A3 analysis}
  Target KB: {kb_name} (matched: yes/no, created: yes/no)
  Description: {first 100 chars of description}
  Tags: {tags}
  Parse Status: {done/n/a}
  Index Status: {indexed/pending}
  Graph Status: {built/pending}
  Quality Notes: {any issues detected during verification}
```

---

## Workflow Summary: Content-First vs Old Blind-First

| Step | Old (Blind-First) | New (Content-First) |
|------|-------------------|---------------------|
| Classify | A2: Guess from filename | A3: Read real content → analyze |
| Find KB | A3: Match from guess | A4: Match from content analysis |
| Description | A4: Read after parse, then write | A3: Generated during analysis, verified in A7 |
| Tags | A5: Assigned after storage | A3: Derived during analysis, applied in A6 |

## Critical Rules
1. A1: MUST `fs_get_tree(max_depth=3)` to understand KB hierarchy
2. **A2 MUST come before A3** — content must be acquired before any classification decision
3. A3: Description, tags, and target KB are ALL derived from **real content you have read** — never from filenames, never from memory, never guessed
4. A3: For parse-path files, you cannot do content analysis until `parse_task_status` returns "done"
5. A5: Write description from A3 analysis — it was already generated from real content
6. **No document splitting** — documents are ingested as single units regardless of size
7. A5 → A6 → A7: Storage → Tags → Verify, in this order, no skipping
8. A8: Sub-KB check prevents retrieval degradation as KB grows
9. All three metadata layers (disk file + .tree-fs.json + .knowledge-base.yml) are kept in sync by the atomic API operations

## Tool Signature Reference
- `parse_doc(file_path, use_ocr=true)` — non-blocking, returns task_id. ONLY parses, does NOT save/index.
- `parse_doc_batch(file_paths, use_ocr=true)` — non-blocking batch parse. ONLY parses. Single task_id for all files.
- `parse_task_status(task_id)` — returns markdown content + paths when done
- `parse_tasks_list(status="")` — list all/running/done/error tasks
- `kb_doc_create(kb_id, name, content, description="")` — creates doc (file + .tree-fs.json + .knowledge-base.yml with file UUID). Does NOT index.
- `kb_doc_read(kb_id="", doc_path="", path="", doc_id="", max_chars=20000, offset=0, limit=200)` — supports doc_id (UUID) for automatic resolution
- `kb_doc_update_meta(kb_id, doc_path, name="", description="")` — update metadata only. Path and .knowledge-base.yml are synced.
- `kb_doc_update_content(kb_id, doc_path, content)` — overwrite content. File size synced in .tree-fs.json + .knowledge-base.yml.
- `kb_doc_update_tags(kb_id, doc_path, [tags...])` — update tags only
- `kb_doc_delete(kb_id, doc_path)` — deletes file + .tree-fs.json + .knowledge-base.yml
- `kb_doc_move(doc_path, target_kb_id)` — moves file + syncs all metadata. Does NOT reindex.
- `kb_index_document(kb_id="", doc_path="", doc_id="")` — single doc vector+graph index. Supports doc_id for auto-resolution.
- `kb_batch_index(kb_id, [paths...], force=false)` — batch vector index
- `kb_graph_build_kb(kb_id, force=false)` — build knowledge graph for entire KB
- `kb_create(name, description="", parent_id="")` — parent_id for sub-KBs
- `fs_upload_file(file_path, parent_id="", description="")` — upload file + metadata. Does NOT index.
