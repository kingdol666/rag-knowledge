---
name: knowledge-ingest
description: >
  Document ingestion pipeline for knowledge bases. Complete A1→A8 workflow:
  survey collection, classify each document by domain, find or create the
  correct KB, select tags from vocabulary, execute storage (parse-path or
  direct), assign tags, and verify. Invoked by Archival when documents
  need to be stored.
---

# Knowledge Ingest — Document Ingestion Pipeline

Invoked by Archival when the scenario is diagnosed as **Ingest**.
Follow these steps EXACTLY. Do not skip any step.

## A0 — Duplicate Pre-Check

Before surveying, check if this document already exists in the collection:

```
kb_search(query="<filename without extension>", top_k=5)
```

**For each result:**
- Compare the result's **name** with the incoming document's name (case-insensitive)
- If name matches AND file_size/line_count are similar → **likely duplicate**
- If name differs but content is about the same topic → **possible related doc to note**

**Decision:**
- Duplicate found → Report to user: "This document appears to already exist in [KB-Name]. Skip or re-parse?"
- No duplicate → Proceed to A1

**Rationale**: Most duplicates in the collection come from parsing the same PDF
multiple times into different test KBs. A simple name match catches >90% of these.

### A0b — Content-Hash Dedup (enhanced)

For suspicious duplicates (same file size, similar topic but different name):

1. Read the first 500 chars of the incoming document.
2. Compare against the first 500 chars of the existing document in the matched KB:
   `kb_doc_read(kb_id, doc_path, max_chars=500)`
3. Compute a simple signature: word-count + first-sentence similarity.
4. If content is clearly the same: "Content matches '[existing-doc]' in [KB-Name].
   This is a duplicate. Skipping. Would you like to rename the copy or keep both?"

This catches renamed PDFs and version copies that filename-only dedup misses.

## A1 — Survey First

```
kb_list()          → load all KBs
kb_tags_list()     → load the vocabulary
```

You cannot make good decisions without knowing what exists.

## A2 — Classify Each Document

For each item, determine its domain:

| Domain | Signal keywords |
|--------|----------------|
| **Energy/Power** | turbine, thermal, boiler, generator, combustion, 火电, 风机, 涡轮, 磨煤机, 空预器 |
| **AI/Machine Learning** | deep learning, neural network, NLP, LLM, RAG, CNN, LSTM, 机器学习, 深度学习 |
| **Healthcare** | clinical, diagnosis, patient, pharmaceutical, medical imaging |
| **Legal/Compliance** | regulation, law, contract, policy, compliance |
| **Finance/Economics** | market, investment, accounting, revenue, 金融 |
| **Engineering/Manufacturing** | mechanical, electrical, production, 故障诊断, 数据驱动, predictive maintenance |
| **Environmental/Climate** | emission, sustainability, 环境, 排放, CO2 |
| **CS/Software** | algorithm, code, API, architecture, .py, .js, config |
| **Business/Management** | strategy, operations, HR, marketing, 管理 |
| **Education/Research** | academic paper, textbook, study, 论文, 研究 |
| **Test/Scratch** | test, scratch, 测试, meaningless content |

**Rule**: If multiple domains match, pick the most SPECIFIC application domain.
"CNN+LSTM for coal mill fault prediction" → Energy/Power, not CS/AI.

## A3 — Find or Create the Right KB

For each document's domain, scan `kb_list()` results:

| Match level | Criteria | Action |
|-------------|----------|--------|
| **Exact** | KB name/description contains the domain | Use it |
| **Partial** | KB description overlaps with domain | Check documents inside via `kb_get_documents()`. If they match → use it |
| **Category** | KB covers a broader category containing this domain | Use it, note the match |
| **None** | No KB matches | **Create**: `kb_create(name="Domain-Name", description="<1-3 sentences: domain + content types + language>")` |
| **User-specified** | User said "put it in X" | Respect, but note if it seems wrong |

**When NOT to create**: a single obscure document belongs in the closest existing KB, not its own.

## A4 — Write the Description

Every document needs a 1-2 sentence description based on ACTUAL content:
- Read the content preview (first ~2000 chars for parsed docs, or first few hundred for direct-text)
- NEVER guess from filename alone
- Format: "A [type of doc] about [main topic]. It covers [what it does/finds]."

KB description standard:
- Domain + content types + primary language
- Example: "Energy industry technical reports covering thermal power plant monitoring, emissions analysis, and turbine diagnostics. Primarily Chinese."

## A5 — Choose Tags

1. `kb_tags_list()` was loaded in A1. Use it.
2. Pick 2-5 tags per document from existing vocabulary (>90% reuse).
3. Only create new tags (`kb_tag_create("tag")`) if the concept is absent.
4. Tag quality rules: lowercase, 1-3 words, domain-specific.
   - Good: "turbine-diagnostics", "deep-learning", "thermal-power"
   - Bad: "test", "doc", "misc", "important", "aaa"

## A5b — Smart Size Check & Chunk Splitting ⚡

**Before storing, check if the document is too large.** If so, split it
into multiple smaller documents automatically. Each chunk gets its own
description and tags but lives in the same KB.

### Size thresholds (auto-split if ANY exceeded)

| Metric | Threshold | How to check | Activation condition |
|--------|-----------|-------------|---------------------|
| **Direct-path text** | >2000 lines or >50KB | Count lines of `content` string | Always active |
| **Parse-path result** | >2000 lines in parsed markdown | Poll parse done, then `kb_doc_read` → count lines | Always active |
| **Ratio check** | This single doc >60% of its KB total | Compare vs existing docs from `kb_get_documents(kb_id)` | **Only if KB has ≥3 docs AND total KB content >50KB** |

### Split procedure

1. **Find logical split points** (Agent analyzes content structure):
   | Signal | Split point |
   |--------|-------------|
   | `# Title` / `## Section` | Strong chapter break |
   | `Abstract`/`引言` → `Method`/`方法` → `Results`/`实验` → `Conclusion`/`结论` | Standard paper structure |
   | `---` horizontal rule | Possible thematic shift |
   | No markers | Every ~400 lines at a natural sentence boundary |

2. **Create each chunk** — same KB, same tags, sequential naming:
   ```
   kb_doc_create(
     kb_id=same_kb_id,
     name="filename_part-1.md",
     content="<chunk 1 content>",
     description="Part 1/N: <section title> — <1-sentence summary>"
   )
   ```

3. **Apply parent's tags to each chunk:**
   ```
   kb_doc_update_tags(kb_id, "filename_part-1.md", ["tag1", "tag2"])
   ```

4. **Report** — inform user what happened:
   ```
   "The document [name] was too large ([size]) so I split it into [N] smaller
   documents within the same KB:
     ├── Part 1: [title] — [summary]
     ├── Part 2: [title] — [summary]
     └── Part 3: [title] — [summary]
   All tagged with [tags]. The split improves vector search precision."
   ```

⚠️ **Parse-path caveat**: For PDFs processed by MinerU, the split happens
AFTER the parse completes. Poll `parse_task_status` first, then read the
parsed markdown content with `kb_doc_read`, then split as above.
Do NOT split before the parse finishes.

⚠️ **Confirmation**: For files >200KB or >5000 lines, ask user before
splitting. For moderate sizes (50-200KB), auto-split and report.

## A6 — Execute Storage

### Parse-path files (PDF, Word, DOCX, XLSX, PPTX, images)
```
parse_doc(
  file_path="<absolute path>",
  kb_id="<target UUID>",
  use_ocr=True,
  description="<from A4>",
  tags=["tag1", "tag2"]
)
```
→ Returns `{task_id, status:"running"}` immediately.
→ Poll `parse_task_status(task_id)` every 10-15s until `status:"done"` or `"error"`.
→ On success: verify with `kb_get_documents(kb_id)`.

### Batch parse-path
```
parse_doc_batch(file_paths=[...], kb_id, descriptions=[...], tags=[...])
```
One task_id for all. Poll same way.

### Direct-path files (MD, TXT, CSV, JSON, HTML, LOG, code files)
```
kb_doc_create(kb_id, name="filename.md", content="<full content>", description="<from A4>")
```
→ Returns immediately. Then apply tags separately.

### In-memory text (no file on disk)
Same as direct-path.

### Binary file upload (not parsed)
```
fs_upload_file(file_path="<absolute path>", parent_id="<folder UUID>", description="<from A4>")
```

## A7 — Assign Tags After Storage

```
kb_doc_update_tags(kb_id, doc_path, ["tag1", "tag2"])
```

For direct-create: `doc_path` is the returned document's path.
For parse-path: poll until done, then `doc_path` is from `kb_get_documents(kb_id)`.

## A8 — Confirm and Report

In your warm precise voice, summarize:
- **What**: filename(s), type, quantity
- **Where**: KB name (not UUID)
- **Tags**: list applied
- **Parse status**: completed/failed/still running (for parse-path)
- **Quality notes**: e.g. "The KB description still reads 'test' — shall I update it?"

---

## CRITICAL: Do NOT Skip
- A2: classify by content, not by guess
- A3: require `kb_list()` before creating anything
- A5: require `kb_tags_list()` before tagging
- A6: parse is non-blocking — always poll
- A8: verify catches mistakes
