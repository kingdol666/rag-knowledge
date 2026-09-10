---
name: knowledgebase-ingest
description: >
  Document ingestion pipeline with quality gates A0→A9. Content-first workflow: dedup (content fingerprint), survey, parse with quality check, structured analysis, tag quality gate (blocklist+normalize+verify), description quality gate (4-elements+content-readback), KB-attribution decision tree (sub-KB first), store by file type, index+tag with post-index verification. No document splitting. Triggered by: ingest, upload, import, store, parse, parse PDF, save to, store, upload, import, parse, save to KB, ingest, ingest a document, upload a document, store into the knowledge base, put a document, add a document, add doc, put document.
---

## ⭐ Related Skills
- Parse documents → the parse_doc tools of `skill://knowledgebase`
- Post-ingest validation → the V1-V9 flow of `skill://knowledgebase-verify`
- Auto-extract experiences after ingest → E0/E1 auto-extraction of `skill://knowledgebase-experience`
- Batch ingestion → `skill://knowledgebase-batch`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Sequential Workflow
**Step 1 — Pre-Flight**: MCP connectivity + service status pre-check.
**Step 2 — Dedup (A0)**: content fingerprint detection; skip duplicate documents.
**Step 3 — Survey (A1)**: browse the document content; determine KB ownership.
**Step 4 — Parse (A2)**: call parse_doc to parse PDF/Word/Excel/Image.
**Step 5 — Save (A3)**: kb_doc_save_parsed writes into the KB.
**Step 6 — Tag+Describe (A3b-c)**: auto-generate tags + content-based descriptions.
**Step 7 — Index (A6)**: vector index + graph index.
**Step 8 — Verify (A6-V)**: kb_search_vector verifies retrievability.
**Step 9 — Report (A9)**: ingestion report.

# Knowledge Ingest — Content-Driven Standard Ingestion Pipeline

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

- Archival is forbidden from: skipping steps, bypassing gates, using the wrong storage tool

**Freedom Map** (freedom level per step):
| Step | Freedom | Notes |
|------|--------|------|
| A0 dedup / A2-Q parse quality / A3b tags / A3c description / A5 storage / A6-V index verification | 🔒 **Mandatory** (low freedom) | Quality gates; must execute strictly; no skipping or workarounds |
| A1 survey / A3 content analysis | 🎯 **Execute** (medium freedom) | Read content per the flow; analysis results feed later decisions |
| A3d KB attribution / A8 sub-KB evaluation | 🧠 **Judgment** (high freedom) | Requires domain judgment based on content; the decision tree guides but is not mechanical |

**Four iron rules**:
1. **Store the whole document** — a single document is a complete unit; never truncate/summarize/split.
2. **Content-driven** — all decisions (KB attribution, tags, descriptions) are based on the actual body text read, not filenames/guesses.
3. **Quality gates** — A2 parse quality / A3b tags / A3c description: any gate failed means rework; do not let it through.
4. ⭐ **MCP-first principle** — all operations must go through MCP tools (`mcp__kb-mcp__*`).

---

## Mental Framework: Three Things to Settle Before Ingesting ⭐

1. **What kind of file is this?** — Parsed-type (PDF/Office/images) or direct-type (MD/TXT/code)? Route to different tool chains.
2. **Which KB does it go to?** — Based on content domain, not the filename. Sub-KB first, parent KB second, create-new third (A3d decision tree).
3. **Did it pass the quality gates?** — Garbled text? Tags normalized? Four-element description? If not, rework — no compromise ingestion.

---

## A0 — Dedup (Content Fingerprint, Not Just Filename) ⭐

**Automated tool (recommended)**:
```
# Single call: SHA256 exact hash + vector similarity dual detection
kb_find_duplicates(kb_id="<target KB>", threshold=0.90)
```
- Returns `{duplicate_groups: [{type: "exact"|"near", similarity, documents, recommendation}]}`
- `exact` (SHA256 match) → skip directly; report "already exists @ <path>"
- `near` (vector similarity ≥ threshold) → read the first 800 chars of both and compare → if duplicate, skip; only supplement tag/description differences

**Manual fallback (when the tool is unavailable)**:
```
# First pass: filename + metadata
kb_search(query="<filename without ext>", top_k=5)

# Second pass: content fingerprint (guards against "rename and re-ingest")
kb_search_vector(query="<first 500 chars of body rewritten as a declarative sentence>", top_k=5, score_threshold=0.85)
```
- Filename hit + similar file size (±10%) → read 500 chars for a second confirmation → **skip if duplicate**
- Vector hit score ≥ 0.85 → read the first 800 chars of both and compare → if duplicate, skip; only supplement tag/description differences
- **Not duplicate** → proceed to A1.

## A1 — Survey (Whole-Library Current State)

```
kb_list()                    # all KBs (including UUID + description + doc_count)
kb_tags_list()               # tag vocabulary (used by A3b normalization; ≥90% reuse target)
fs_get_tree(max_depth=3)     # KB hierarchy structure (sub-KBs visible)
```

## A2 — Acquire Content + Parse Quality Detection

### Path Selection
| Type | Path | Tool |
|---|---|---|
| PDF/Word/Excel/PPTX/images | Parse path | `parse_doc` / `parse_doc_batch` |
| MD/TXT/Code/JSON/YAML | Direct path | Read the file directly |
| Binary (non-text) | Metadata path | `fs_upload_file` (not indexed; storage only)|

### Parse Path
```
parse_doc(file_path="<abs_path>", use_ocr=true)   # non-blocking; returns task_id
# Poll until complete:
parse_task_status(task_id) → {markdown, markdown_path, images_dir, image_count}
```
For ≥3 files use `parse_doc_batch(file_paths=[...], use_ocr=true)` — managed under a single task_id.

### ⚠️ A2-Q Parse Quality Gate (Reject Junk Ingestion)
Inspect the first 1500 chars of the parsed markdown; **any hit means reject and report** (do not proceed to A3):

| Symptom | Detection | Handling |
|---|---|---|
| **OCR garbage** | Garbled rate >30% (abnormal proportion of non-ASCII/non-Chinese) | Re-parse with a different OCR mode |
| **Binary residue** | Body contains lots of `\x00`/base64 fragments | Source file may be corrupted; report to the user |
| **Headings without body** | Whole text is only `#` headings + ≤200 chars body | Parse failed; retry or report |
| **Excess whitespace** | >50 consecutive blank lines or body <100 chars | Treat as parse failure |
| **Language mismatch** | Chinese PDF parses into all-English garbage | Encoding/OCR issue; retry |

## A3 — Structured Content Analysis

Read a 3000-char sample and output a structured result (**this is the basis for all later decisions**):

```json
{
  "title": "real title (taken from the body H1, not the filename)",
  "domain": "main domain (e.g. polymer materials / AI / energy)",
  "sub_domain": "sub-domain (e.g. PET biaxial stretching / RAG / lithium batteries)",
  "methods": ["specific methods/models/processes"],
  "materials": ["specific materials/equipment/datasets"],
  "scenario": "problem solved / applicable scenario",
  "key_findings": ["key data/conclusions"],
  "language": "zh|en|mixed",
  "raw_tags": ["5-8 candidate domain words extracted from content (before A3b cleaning)"],
  "target_kb_decision": "see the A3d decision tree"
}
```

**≥3 documents or a single document >50KB**: delegate sub-agents for analysis, passing content samples + KB list + tag vocabulary, and accept per the [description-guide.md D5](references/description-guide.md) contract.

## A3b — Tag Quality Gate ⭐

Clean A3's `raw_tags`; **skipping is strictly forbidden**. Full rules in [tag-quality-rules.md](references/tag-quality-rules.md).

```
1. T1 blocklist filtering → discard section titles ("Abstract"/"1 Introduction"/"References")/test tags (test-*)/descriptive tags
2. T2 normalization    → unify casing (pet→PET) + merge Chinese/English synonyms (polyethylene/PE: keep the one already in the vocabulary)
3. T3 count trimming  → keep 2-5: material words + method words + scenario words (+ 0-2 attributes)
4. Vocabulary comparison    → ≥90% reuse of existing words from kb_tags_list(); new words only for entirely new concepts
5. Content readback    → every tag actually appears within the ≥2000 chars sample
```
**Failing the bar → return to A3 to re-extract; do not release to A5.**

## A3c — Description Quality Gate ⭐

Write descriptions per [description-guide.md](references/description-guide.md); **four elements + content readback are mandatory**:

```
Description = [Subject] + [Method/Technology] + [Scenario/Problem] + [Key data/Conclusion] + [Language]
```
- **At least 2 concrete nouns among the four elements** (method names/material names/equipment names/datasets) — generic phrases like "a paper about X" are forbidden.
- **Must read back after writing**: `kb_doc_read(..., max_chars=800)` to verify every key claim in the description actually appears in the body.
- **Mismatch → rewrite the description** (never change the body to fit the description).

✅ "Coal mill blockage early warning based on CNN-LSTM, trained on DCS historical data, 660MW unit field-tested with 315min advance warning. In Chinese."
❌ "Coal mill paper" / "Parsed from xxx.pdf" / "test" / "polymer research"

## A3d — KB Attribution Decision Tree ⭐ (Ensures "Put It in the Right Place")

Determine the target KB by priority (**this is the core of ingestion quality**):

```
① Sub-KB exact match?
   Read A1's fs_get_tree; find a [sub-KB] whose description strongly matches this document's sub_domain
   → Hit: target = that sub-KB (✅ best)

② Parent KB domain match + no suitable sub-KB yet?
   The parent KB's domain matches the document but there is no precise sub-KB
   → Hit: target = parent KB; record "may need a sub-KB in the future" (A8 evaluation)

③ No match at all?
   → kb_create(name="<Domain>-<SubDomain>", description=per the D3 template, parent_id="<parent KB or empty>")
   → The new KB's description must meet the bar (A3c); "to be filled later" is not allowed
```

**Mis-attribution detection**: after deciding, compare the target KB's description against the document's `sub_domain + methods` — an obvious domain conflict (e.g. putting an RAG document into the "polymer library") → rerun the decision tree.

## A4 — Find/Create KB (Execute the A3d Decision)

- **Match an existing KB**: use its UUID.
- **Create new**: `kb_create(name, description, parent_id)`, with the description per the [D3 KB-level template](references/description-guide.md).
- **Create a sub-KB**: point `parent_id` at the parent KB's `kb_id`.

## A5 — Store the Document (Routed by Path; Whole Document, No Truncation)

### Parse path — `kb_doc_save_parsed` (stores full content + images) ⭐
```
save = kb_doc_save_parsed(
    parent_id=target_kb_id,
    task_id="<task_id from A2>",     # auto-extracts full markdown + images_dir
    description=the qualified description produced by A3c
)
```
⚠️ **The parameter is `parent_id`, not `kb_id`** (unlike most tools' naming; passing `kb_id` will be rejected by the schema). The **`task_id` mode is recommended**: passing A2's task_id automatically extracts the full markdown + images_dir without manually assembling markdown_path.
Automatically: full markdown written to disk + all images copied into the KB `images/` + atomic update of `.tree-fs.json` + `.knowledge-base.yml`.

**Never use `kb_doc_create` to store parsed documents** — it truncates content and drops images.

### Direct path — `kb_doc_create`
```
kb_doc_create(kb_id=target_kb_id, name="doc.md", content=complete file content, description=A3c description)
```

## A6 — Index + Graph + Tag + Post-Index Verification ⭐

### A6a Index (Vector + BM25)
```
idx = kb_index_document(kb_id=target_kb_id, doc_path=doc_path)
```
Returns `{vector_index: {collection, total_chunks, graph_doc_id}, graph_stats}`.

### A6b Knowledge Graph Build (Immediately After Vector Indexing) ⭐
```
kb_graph_build(kb_id=target_kb_id, force=true)
```
> ⚠️ **Known issue**: `total_relations` returned by `kb_graph_build` may be 0 (a stats counting bug); **this does not mean the build failed**. The data has actually been written to Neo4j. Always verify with `kb_graph_document()` spot checks rather than relying on the return value.

Post-build verification:
```
kb_graph_document(doc_path=doc_path)  # confirm the document node exists in the graph
```

### A6c Tagging (Qualified Tags After A3b Cleaning)
```
kb_doc_update_tags(kb_id=target_kb_id, doc_path=doc_path, tags=tags after A3b cleaning)
```

### A6-V Post-Index Verification (Mandatory)
```
# 1. Was vector_index written?
Confirm vector_index.collection is non-empty
# 2. Is the collection UUID correct?
Should be "kb_<target_kb_uuid>" — pointing at another UUID means it landed in an orphan collection
# 3. Is the chunk count reasonable?
total_chunks ≥ 1
# 4. Did the graph build succeed?
kb_graph_document(doc_path) returns entities
```

## A7 — Final Checklist (All ✅ Required for Ingestion Completion)

| # | Check item | Tool | Pass criteria |
|---|---|---|---|
| C1 | Content complete, not truncated | `kb_doc_read(max_chars=500)` | Body matches the A3 sample |
| C2 | Description meets the bar | Read description | Contains the four elements; content readback passed |
| C3 | Tags meet the bar | Read tags | 2-5 tags; no blocklist; no synonym duplicates |
| C4 | KB attribution correct | doc sub_domain vs KB description | Domain consistent |
| C5 | Vector index ready | vector_index field | Non-empty; collection correct |
| C6 | Images complete (parse path) | image_count comparison | Matches the parse result |
| C7 | Graph index ready | `kb_graph_document(doc_path)` | Document found in the graph |
| C8 | Three-layer metadata consistent | `.tree-fs.json` ↔ `.knowledge-base.yml` ↔ disk | Document present in all three |

**Any ✗ → rework the corresponding step; "ingest first, fix later" is forbidden.**

### A7-E — Experience Extraction (Optional; Enrich the Experience Library After Ingestion)
After the ingestion final check passes, if capacity allows, trigger an experience scan:
```
experience_extract(kb_id=target_kb_id, mode="prepare")  # ⚠️ prepare mode does not support dry_run; always returns the LLM task package
→ Agent LLM refinement → confidence≥0.8 approved directly, <0.8 goes to the draft pool
```
An optional step, but recommended when KB completeness and freshness requirements are high.

## A8 — Sub-KB Evaluation + Orphan Cleanup

- **Automatic sub-KB creation**: parent KB reaches `SUB_KB_AUTO_SPLIT_THRESHOLD` (**≥8 documents spanning ≥2 sub-domains**) → split per [sub-kb-creation.md](references/sub-kb-creation.md). Threshold definitions are in the authoritative source table at the top of that file.
- **Orphan cleanup** (opportunistically during ingestion): KBs with `doc_count=0` and empty descriptions → report to the user whether to delete. **Do not delete without permission**.

## A9 — Ingestion Report
```
✅ <filename> → <full path of target KB>
   Type: PDF (parsed) | Title: <real title>
   Description: <first 80 chars of the qualified description>...
   Tags: [tag1, tag2, tag3] (after A3b cleaning)
   Index: vector=<collection> chunks=<n> | graph=<entities>e/<relations>r
   Dedup: no duplicates found / skipped (duplicate of <path>)
   Final check: C1-C8 all ✅
```

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Skip A0 dedup | Re-ingest under a renamed file | Dual-channel dedup: filename + fingerprint |
| Skip the A2-Q quality gate | OCR garbage gets ingested | After A2, run the gate item by item |
| `kb_doc_create` for parsed documents | Truncates content and drops images | Parsed documents must use `kb_doc_save_parsed` |
| Tags without A3b | Section titles/bad tags get ingested | Blocklist filtering + normalization + count trimming |
| Description without A3c | Filename used as description | Four elements + content readback |
| No collection verification after indexing | Lands in an orphan collection | A6-V verifies UUID+chunks |
| Continue ingesting despite failing quality | Garbage in, garbage out | Any C1-C8 ✗ means rework |
| "Ingest first, fix later" | Never gets fixed | Final check C1-C8 all ✅ counts as complete |
| No experience extraction triggered after ingestion | Experience factors in documents are lost | A7-E optional auto-extraction |

## Tool Quick Reference
- `parse_doc(file_path, use_ocr=true)` / `parse_doc_batch(file_paths, use_ocr=true)` — non-blocking parsing
- `parse_task_status(task_id)` — poll parsing results
- `kb_doc_save_parsed(parent_id, task_id, description)` — ⭐ parse path; stores full content+images
- `kb_doc_create(kb_id, name, content, description)` — direct path/in-memory documents
- `kb_index_document(kb_id, doc_path)` — vector+graph+BM25 indexing
- `kb_doc_update_tags(kb_id, doc_path, tags)` — tagging (after A3b cleaning)
- `kb_doc_read(kb_id, doc_path, max_chars)` — read the body (used by A3/A3c/C1)
- `kb_search_vector(query, top_k, score_threshold)` — A0 content fingerprint dedup
- `kb_search(query, top_k)` — A0 filename dedup
- `kb_create(name, description, parent_id)` — create KB/sub-KB
- `kb_tags_list()` — A3b vocabulary comparison
- `fs_upload_file(file_path, parent_id, description)` — binary upload
