# Document Splitting Procedure (A5b / O9)

> **Core principle**: large documents must be split for retrieval and readability. When a document exceeds 2000 lines or 50 KB, `kb_doc_read` cannot load the full content at once, and vector search precision degrades because chunks are too broad.
> **Splitting is sectioning, not chunking** -- split by logical document structure into independent documents, each with its own description, tags, and vector index.
>
> Large-document splitting must be executed **after parse completion** (for Parse-path files). You cannot read content for splitting until `parse_task_status` returns "done".

---

## A5b-0 — Size Detection

**Auto-detection thresholds (splitting is triggered when ANY threshold is exceeded):**

| Metric | Threshold | Trigger condition |
|--------|-----------|-------------------|
| File size | `file_size` > 50 KB | Always check |
| Estimated lines | > 2000 lines | Always check (`content.count('\n')`) |
| Character count | > 80,000 chars | Always check (beyond this, `kb_doc_read` cannot read at once) |

**Detection timing (Parse-path):**

```
1. parse_task_status(task_id) returns "done"
2. Check markdown_chars in the result:
   - markdown_chars > 80000 -> must split
   - markdown_chars > 50000 -> recommended to split, check section heading count
3. Read actual line count from file system
```

---

## A5b-1 — Pre-Read Outline (Table of Contents Scan)

Before splitting, **read the document structure first** -- do not split blindly.

**Step 1: Extract document structure with `kb_doc_read`**

```
# Document already in KB, read first 3000 characters with kb_doc_read
content = kb_doc_read(kb_id, doc_path, max_chars=3000, offset=0)

# Extract all #/## headings from content
import re
headings = re.findall(r'^(#{1,3})\s+(.+)$', content, re.MULTILINE)
# headings output: [('##', 'ABSTRACT'), ('#', 'Simulation of Micro-Void...'), ...]
```

**Step 2: Analyze section structure**

```
# Estimate section boundaries across full document
# Use kb_doc_read with offset/limit pagination to read complete content
lines = content.split('\n')
# Find 1st ## heading line -> 2nd ## heading line = Chapter 1 range
# ...

AI analysis output:
Document Structure Analysis:
- Total characters: {markdown_chars}
- H1/H2 heading count: {len(headings)}
- Main sections: [section list]
- Recommended split points: [by #/## heading line positions]
- Estimated size per section: [section1: ~N lines, section2: ~N lines, ...]
```

**Key rule**: section boundaries are determined by **heading positions**. Use `kb_doc_read(offset=N, limit=M)` to paginate and read each section's full content.

---

## A5b-2 — Determine Split Plan

**Split decision matrix:**

| Document structure | Recommended split strategy | Target size per chunk |
|-------------------|---------------------------|-----------------------|
| Has `#` or `##` section headings | Split by section, one document per section | 1000-2000 lines |
| Has `###` sub-sections but no major sections | Split by `##`, `###` belongs naturally | 800-1500 lines |
| Plain paragraphs, no headings (novels/reports) | Split every ~800 lines at a sentence boundary | 500-1000 lines |
| Paper (Abstract->Intro->Method->Result->Conclusion) | Split into 4-6 segments by standard paper structure | 500-1500 lines per segment |
| Textbook/manual (multi-level nesting) | Split by `#` top-level sections, preserve `##` belonging | < 2000 lines per chapter |

**Chunk naming convention:**

```
{original_filename}_s{N}_{short_section_title}.md
# Examples:
# 03-Micro-Void-AM-2025_s01_Introduction.md
# 03-Micro-Void-AM-2025_s02_Methodology.md
# 03-Micro-Void-AM-2025_s03_Results.md
# 03-Micro-Void-AM-2025_s04_Conclusion.md
```

---

## A5b-3 — Section-by-Section Reading + Smart Summary Generation

**This is the core step -- independent content verification and description generation for each section.**

For each split segment index=1..M, with known range [char_start, char_end] in the full document:

```
Step 1: Read section content with kb_doc_read (pagination)
  SECTION_CONTENT = kb_doc_read(
    kb_id, doc_path,
    offset=char_start // 2000,        # Page offset at 2000-char intervals
    limit=(char_end - char_start) // 2000 + 1
  )

Step 2: AI analyzes section content, generates structured metadata
  # Delegate to sub-agent to avoid main context bloat:
  Agent(
    subagent_type="general-purpose",
    prompt="""Analyze the following document section content, output JSON:

    Section title: {extracted from first line of content}
    Document main title: {extracted from document top}

    Content ({end_line - start_line} lines):
    {SECTION_CONTENT first 2000 characters}

    Output JSON:
    {
      "section_title": "This section's heading",
      "content_summary": "1-2 sentence core summary",
      "methods": ["method1", "method2"],
      "scenario": "What question does this section answer / what scenario",
      "key_data": "Key data / findings (if any)",
      "section_tags": ["section-specific tag1", "tag2"],
      "section_description": "Full A4-format description"
    }"""
  )

Step 3: Write description (A4 specification):
  "{Document main title} -- {Section title}. {1-2 sentence core summary}.
   Applicable to {scenario}. {Language}."

Step 4: Generate independent tags for this section:
  - Inherit original document's general tags
  - Add section-specific domain tags (from sub-agent section_tags)
  - Ensure 3-6 tags per section
```

---

## A5b-4 — Create Chunk Documents

For each split segment, use `kb_doc_create` to create an independent document:

```
# SECTION_CONTENT extracted in A5b-3 Step 1 via kb_doc_read
# SECTION_DESCRIPTION generated in A5b-3 Step 3

kb_doc_create(
  kb_id=same_kb_id,
  name="{original_filename}_s{index}_{section_english_slug}.md",
  content=SECTION_CONTENT,                    # Section text from kb_doc_read
  description=SECTION_DESCRIPTION             # A4-format real description
)
```

**Tool signature (`kb_doc_create`):**
- `kb_id` (required): Target KB UUID
- `name` (required): Chunk document name, e.g. `03-Micro-Void-AM-2025_s01_Introduction.md`
- `content` (required): Complete markdown text for this section (from `kb_doc_read` pagination)
- `description` (optional but must be provided): A4-format real content description

**Important:**
- Each section's content must be **complete** -- include the section heading and all its sub-headings and body text
- Do not truncate sentences or paragraphs (use section boundaries, not line counts)
- Preserve image references (keep markdown references like `![](images/xxx.jpg)`)
- Attach references section as an independent segment or as an appendix to the last section
- If a single section > 100 KB (rare), further split by `###` sub-headings

---

## A5b-5 — Copy Tags to Each Chunk

```
# For each chunk document, apply unified inherited tags + unique tags
kb_doc_update_tags(kb_id, "{chunk_doc_path}",
  ["inherited_tag1", "inherited_tag2", "section_specific_tag1", "section_specific_tag2"])
```

**Tag strategy:**
- All parent document tags are inherited (ensures findability during search)
- Each section adds its own domain-specific tags (improves precision)
- Example: Methodology section -> add "methodology", "experimental-setup"
- Example: Results section -> add "results", "discussion"

---

## A5b-6 — Delete Original Large Document

Once all chunks are created and verified, delete the original document:

```
kb_doc_delete(kb_id, original_doc_path)
```

**Deletion conditions (ALL must be met):**
1. All M chunks confirmed present via `kb_get_documents()`
2. At least 1 randomly sampled chunk verified content-complete via `kb_doc_read()`
3. Tags assigned to all chunks

---

## A5b-7 — Vector Index for Chunk Documents

```
# Batch index all chunk document paths
kb_batch_index(kb_id, [part1_path, part2_path, ...], force=true)

# Verify
kb_search_stats(kb_id) -> confirm chunk_count covers all chunks
```

---

## A5b-8 — Split Report Template

```
Document Split Report:
  Original: {filename} ({size}KB, {lines} lines)
  Split into: {M} independent documents

  +-- s01_{section_title}: {description snippet} ({size}KB)
  +-- s02_{section_title}: {description snippet} ({size}KB)
  +-- ...
  +-- s0M_{section_title}: {description snippet} ({size}KB)

  Tags: unified inherited [{tag1, tag2}] + per-section unique tags
  Vector index: {total_chunks} chunks
  Original document deleted:
```

---

## A5b-9 — Special Cases

| Situation | Handling |
|-----------|----------|
| **Document too large to read at once** (>500KB md) | Read TOC/first 3K chars -> determine section boundaries -> use `kb_doc_read(offset=0, limit=N)` pagination per segment |
| **Paper with figures/charts** | Each chunk retains its figures and image references; do not split figures from their explanatory paragraphs |
| **Reference list** | Append to last section as appendix, or create a standalone references section |
| **JSON/CSV structured files** | Split by logical grouping (by year/category/table), add schema description per chunk |
| **Code files** | Split by module/function/class, prepend import declarations for standalone readability |
| **Multilingual mixed documents** | Do not split by language, but annotate "bilingual zh/en" in description |

---

## A5b-10 — Graph Index for Chunk Documents

Once all chunk documents are created, `kb_batch_index` automatically builds both vector indices and graph associations (via `shared_tag` + `vector_similar`). There is no need to manually link chunks -- the graph's `shared_tag` mechanism automatically associates chunks with overlapping tags.

**Verify graph construction:**

```
# Batch index all chunk documents
kb_batch_index(kb_id, [chunk_paths...], force=true)

# Verify graph status
kb_graph_kb_overview(kb_id)
-> Confirm doc_count equals number of chunks
-> Check tag_distribution covers chunk tags
```
