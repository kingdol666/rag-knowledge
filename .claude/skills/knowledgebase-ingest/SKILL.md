---
name: knowledgebase-ingest
description: "Content-first document ingestion with deduplication, parse-quality checks, structure-aware Markdown splitting, optional Agent boundary planning, source-span preservation, five-dimension description generation and readback, KB/sub-KB attribution, indexing verification, and fail-closed storage. Use when importing, uploading, parsing, saving, splitting, or adding documents to the knowledge base, especially oversized documents or requests mentioning ingest, parse PDF, maxChars, 分块, 拆分, or 大文档入库."
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
**Step 4.5 — Split Gate (A2.5, scripted + Agent-planned)**: count parsed Markdown with the shared Unicode code-point contract; if over `ingestion.large_doc.max_chars`, scan structure, validate an optional Agent boundary plan, and run `scripts/split_large_doc.py`. All later steps operate on source-backed parts; invalid plans and source deletion failures are blocking.
**Step 5 — Save (A3)**: kb_doc_save_parsed writes into the KB (or kb_doc_create per part after A2.5).
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
| A0 dedup / A2-Q parse quality / **A2.5 split gate** / A3b tags / A3c description / A5 storage / A6-V index verification | 🔒 **Mandatory** (low freedom) | Quality gates; must execute strictly; no skipping or workarounds |
| A1 survey / A3 content analysis | 🎯 **Execute** (medium freedom) | Read content per the flow; analysis results feed later decisions |
| A3d KB attribution / A8 sub-KB evaluation | 🧠 **Judgment** (high freedom) | Requires domain judgment based on content; the decision tree guides but is not mechanical |

**Four iron rules**:
1. **Store the whole document** — a single document is a complete unit; never truncate/summarize. Oversize is handled by the **A2.5 split gate**: when the parsed markdown's char count exceeds `ingestion.large_doc.max_chars` (Settings → Ingestion Standards (入库规范), hot-effective), run `scripts/split_large_doc.py` — it writes part documents and deletes the temp original; each part then enters the flow as a complete unit with its own content-based description. **Never split by hand, never use the raw oversized file downstream.**
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
kb_list()                    # all KBs (UUID field is named kbId; description; docCount)
kb_tags_list()               # tag vocabulary (used by A3b normalization; reuse is a SOFT target, see A3b T4/T5)
fs_get_tree(max_depth=3)     # KB hierarchy structure (sub-KBs visible)
```
> ⚠️ `kb_list` may transiently return an **empty catalog** (60s auth-poisoning window) — an empty result cannot be distinguished from "the project really is empty" from the return value alone.
> **You must cross-check with `fs_get_tree()`** before concluding; wait 20-30s and retry, up to 3 times.

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

## A2.5 — Structure-Aware Split Gate (Scripted + Agent-Planned) ⭐

`max_chars` is a storage and retrieval guardrail, **not a command to cut at an arbitrary character offset**. A split is valid only when the original text remains a sequence of source-backed logical units. The goal is to make every stored part independently retrievable without breaking a coherent argument.

### 1) Scan the parsed Markdown before planning

Run the bundled gate script (or the same shared backend splitter) against the parsed markdown. The scanner records contiguous units with:

- `unit_id`, `kind`, `heading_path`, `start_char`, `end_char`;
- ATX and Setext headings, with headings inside fenced code ignored;
- complete paragraphs, lists with continuations, tables, fenced code, blockquotes, figures/captions, and sentence boundaries inside oversized prose sections;
- `source_sha256`, `section_range`, head/tail probes, and safe boundary type.

The scanner's source-span invariant is strict: concatenating every unit must reproduce the input byte-for-character (Python character count) with no gap or accidental overlap.

### 2) Ask an Agent to choose boundaries, never to rewrite text

For an oversized document, provide the Agent the unit manifest plus bounded head/tail excerpts. The Agent may group adjacent scanner units and write a detailed part description, but it may not return replacement prose or arbitrary offsets:

```json
{
  "source_sha256": "<sha256>",
  "parts": [
    {
      "part_index": 1,
      "unit_ids": ["u0001", "u0002"],
      "section_range": "Introduction – Methods",
      "boundary_reason": "complete subsection boundary",
      "description": "paper-level subject/method + this-part content, <=220 chars",
      "evidence": ["literal body evidence used for the description"]
    }
  ]
}
```

Validate before writing: hash, contiguous unit coverage, unit order, safe boundaries, description length, and evidence readback. An invalid or absent plan automatically uses the deterministic structural fallback and records `planner=deterministic`; it must never be presented as Agent segmentation.

### 3) Materialize and act on the JSON

```bash
python "<this-skill-dir>/scripts/split_large_doc.py" "<markdown_path>" \
  [--agent-plan "<validated-plan.json>"]
```

The script reads `ingestion.large_doc` from the repository-root `config.yml` (or `--config` / `--max-chars`) and prints one JSON object:

```json
{
  "success": true,
  "source_chars": 84320,
  "max_chars": 30000,
  "split": true,
  "strategy": "agent_semantic|structural_fallback",
  "planner": "agent|deterministic",
  "source_sha256": "...",
  "parts": [{"file": "... (part 1 of 3).md", "source_start": 0,
             "source_end": 28100, "section_range": "...",
             "description_seed": "...", "warnings": []}]
}
```

| Result | Meaning | Next |
|---|---|---|
| `split: false` | source is within the limit | continue with the original unit |
| `split: true` | parts were materialized from source spans | run A3/A3b/A3c/A5/A6 per part; never save the deleted source |
| `warnings` contains `oversized_atomic_unit` | one indivisible logical block is larger than the target | keep it whole, show the warning, and do not hard-cut unless `allow_hard_fallback=true` is explicitly approved |
| `success: false` | scanner/config/IO/plan error | fix or report; do not pass an oversized raw source downstream |

The script defaults to zero character overlap. Continuity comes from preserving complete logical units and explicit section context, not from duplicate slices. `--dry-run` performs no writes/deletion. If splitting is required, the temporary unsplit markdown is deleted after successful materialization; any deletion warning is a blocking condition for downstream ingest.

Parts keep the original body exactly and add a synthetic header (`source title + part i/N + section range`) outside the source span. Parse images remain relative to the KB; upload them once before saving the parts.

## A3 — Structured Content Analysis

**A3 structured analysis:** read the part body and, for long documents or parts, use bounded head/middle/tail evidence windows to produce the five-dimensional description. This sampling is for description analysis only; Librarian retrieval later reads every candidate segment.

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
4. Vocabulary comparison    → SOFT target: reuse existing words from kb_tags_list() when they fit the content
5. Content readback    → every tag actually appears within the ≥2000 chars sample
```
**Priority: T5 content anchoring > T3 count > T2 normalization > T4 vocabulary reuse.** T4 is a SOFT target — when the vocabulary has no fitting word, coin new content-derived tags (the Organize phase L2 will normalize them);
**never use words absent from the body just to pad the reuse rate** (that violates T5). Field-tested: when a 364-word vocabulary had no environment-related Chinese tags, coining all-new tags was the correct behavior.
**Failing the bar → return to A3 to re-extract; do not release to A5.**

## A3c — Description Quality Gate ⭐

Write descriptions per [description-guide.md](references/description-guide.md); **four elements + content readback are mandatory**:

```
Description = [Subject] + [Method/Technology] + [Scenario/Problem] + [Key data/Conclusion] + [Language]
```
- **At least 2 concrete nouns among the four elements** (method names/material names/equipment names/datasets) — generic phrases like "a paper about X" are forbidden.
- **Must verify every claim against the body**: direct path → verify against the source file before saving; parse path → verify against the `parse_task_status` markdown BEFORE saving (the description gate runs pre-save), then C1 re-verifies the stored copy via `kb_doc_read(..., max_chars=800)` after A5.
- **Mismatch → rewrite the description** (never change the body to fit the description).

**D8 multi-dimension + query orientation:** cover domain, method, object, problem-in-user-voice, and conclusion dimensions; preserve bilingual method anchors; and use evidence from the part itself. Long-document windows support description analysis only and never authorize retrieval to prune unseen segments. Every split part must retain a complete `Part i/N · section range` marker and stay ≤220 characters.

**⭐ A3c-P Part-label integrity check (mandatory for split parts).** The `【Part i/N · <range>】` label is what the librarian reads to pick a part — a wrong label silently breaks hierarchical retrieval. Measured failure (2026-09-24): a 26-part novel was ingested with **24 of 26** labels reading `Gutenberg front/back matter` while the parts actually held novel chapters; a description-driven librarian then selected 2 parts instead of 7 and lost 2 of 7 key scenes. Before saving, check **every** split part's label:
- **Non-boilerplate**: the same label value must not repeat across ≥3 siblings.
- **Non-degenerate**: no inverted or single-point span (`XV–I`, `XLVI–XLVI`).
- **Content-derived**: the range must come from reading the part's own head/tail windows — never copied from part 1, never assumed from the document type.
- **Any violation → regenerate that part's label from its own content** before A5. Do not save a part whose label fails this check.

**A3c-R retrieval self-test (mandatory closed loop after A6 indexing)**: see [A3c-R](#a3c-r--retrieval-self-test-description-closed-loop-mandatory-after-indexing-) below, after A6-V — run `kb_search` with the problem-dimension wording from the description + `kb_search_vector` with a paraphrase; the target document must be recalled, otherwise merge the missed query terms back into the description and retest.

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

**A5 source rule:** a split plan that is invalid, unavailable, or not fully materialized is a hard failure for a mandatory ingest path. Do not fall back to saving the oversized raw markdown. The web/API path may keep a whole document only when the caller explicitly marks it as staging (`split:false`); final ingest uses only validated parts.

**Routing after A2.5:** if the split gate produced parts, store **each validated part** via the direct path (`kb_doc_create`, one call per part with its qualified description and split metadata) — never re-store the deleted oversized original, and never call `kb_doc_save_parsed` again for the unsplit source.
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
# → NON-BLOCKING: {status:"running", task_id, ...}; poll kb_task_status(task_id)
```
> ⚠️ **kb_graph_build is asynchronous** (returns `task_id`, not the build stats). `kb_task_status` resolves task ids **across MCP processes** (a persisted registry under `storage/mcp-task-registry.jsonl`; a resolved record carries `cross_process: true`). If a status call still reports unknown id, verify completion directly instead of retrying:
```
kb_graph_document(doc_path=doc_path)   # document node exists = build landed
```
> ⚠️ **Known gap**: tag updates (`kb_doc_update_tags`) propagate to `.knowledge-base.yml` immediately but may NOT appear on the graph node's `tags` (background graph reindex lag/gap). C7 judges by document-node existence, not node tags.

Post-build verification:
```
kb_graph_document(doc_path=doc_path)  # confirm the document node exists (keys: document/tags/related_documents/related_count — no "entities" field)
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
kb_graph_document(doc_path=doc_path) finds the document node
(response keys: document / tags / related_documents / related_count — no "entities" field)
```

### A3c-R — Retrieval Self-Test (Description Closed Loop, Mandatory After Indexing) ⭐

> The final judge of a description is retrieval. Use your own description as the query; if it cannot be recalled, the description lacks a query path.

```
# 1. Metadata search (the main channel matching description/tags)
kb_search(query="<problem-dimension wording from the description>", top_k=5)
→ the target document must appear in the results

# 2. Vector search (paraphrase; do not copy the original sentence verbatim)
kb_search_vector(query="<paraphrased question>", top_k=5, score_threshold=0.3)
→ the target document must be in the top-5
```

Any miss → merge the query's keywords (problem/method dimensions) into the description (`kb_doc_update_meta`),
then retest after updating. A3c truly passes only when both channels hit. (Criteria: [description-guide.md D9](references/description-guide.md))

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
| C9 | Description retrieval self-test (A3c-R) | `kb_search` + `kb_search_vector` | Both queries recall this document |

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
   Split (A2.5): not needed (<n> chars ≤ <max_chars>) | split into <N> parts (script), temp original deleted
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
| Skip A2.5 / split by hand / eyeball the char count | Oversized docs degrade every retrieval layer; manual splits lose headers+descriptions | Run `scripts/split_large_doc.py`; it reads the setting, writes parts, deletes the temp original |
| `kb_doc_create` for parsed documents | Truncates content and drops images | Parsed documents must use `kb_doc_save_parsed` |
| Tags without A3b | Section titles/bad tags get ingested | Blocklist filtering + normalization + count trimming |
| Description without A3c | Filename used as description | Four elements + content readback |
| No collection verification after indexing | Lands in an orphan collection | A6-V verifies UUID+chunks |
| Continue ingesting despite failing quality | Garbage in, garbage out | Any C1-C8 ✗ means rework |
| "Ingest first, fix later" | Never gets fixed | Final check C1-C8 all ✅ counts as complete |
| No experience extraction triggered after ingestion | Experience factors in documents are lost | A7-E optional auto-extraction |
| Write the description from the head 3000 chars of a long document | The real meaning of the mid/tail sections is lost; the description over-generalizes | >20000 chars mandates three-window sampling (D8) |
| Skip the A3c-R retrieval self-test | However good the description is, it is wasted if retrieval cannot recall it | Passes only when both kb_search and kb_search_vector channels recall it |

## Tool Quick Reference
- `parse_doc(file_path, use_ocr=true)` / `parse_doc_batch(file_paths, use_ocr=true)` — non-blocking parsing
- `parse_task_status(task_id)` — poll parsing results
- `scripts/split_large_doc.py <md> [--max-chars N] [--config PATH] [--dry-run]` — ⭐ A2.5 split gate; reads config.yml, writes parts, deletes the temp original, prints one JSON plan
- `kb_doc_save_parsed(parent_id, task_id, description)` — ⭐ parse path; stores full content+images
- `kb_doc_create(kb_id, name, content, description)` — direct path / per-part storage after A2.5
- `kb_index_document(kb_id, doc_path)` — vector+graph+BM25 indexing
- `kb_doc_update_tags(kb_id, doc_path, tags)` — tagging (after A3b cleaning)
- `kb_doc_read(kb_id, doc_path, max_chars)` — read the body (used by A3/A3c/C1)
- `kb_search_vector(query, top_k, score_threshold)` — A0 content fingerprint dedup
- `kb_search(query, top_k)` — A0 filename dedup
- `kb_create(name, description, parent_id)` — create KB/sub-KB
- ⚠️ Parameter naming: `kb_list` **returns** `kbId`, but the input parameter of most tools is `kb_id`; `kb_doc_move(doc_path, target_kb_id)` has no source-KB parameter. On first call, print an entry to confirm the key names.
- `kb_tags_list()` — A3b vocabulary comparison
- `fs_upload_file(file_path, parent_id, description)` — binary upload
