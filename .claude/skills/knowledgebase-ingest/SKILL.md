---
name: knowledgebase-ingest
description: "Content-first document ingestion with deduplication, parse-quality checks, structure-aware Markdown splitting, optional Agent boundary planning, source-span preservation, five-dimension description generation and readback, KB/sub-KB attribution, indexing verification, and fail-closed storage. Use when importing, uploading, parsing, saving, splitting, or adding documents to the knowledge base, especially oversized documents or requests mentioning ingest, parse PDF, maxChars, 分块, 拆分, or 大文档入库."
---

## Related lanes

- Parse documents → `parse_doc` tools of `skill://knowledgebase` · post-ingest validation → V1-V9 of `skill://knowledgebase-verify` · experience auto-extraction → E0/E1 of `skill://knowledgebase-experience` · batch ingestion → `skill://knowledgebase-batch`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) · execution model → [execution-model.md](../knowledgebase/references/execution-model.md) · pre-flight → [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) · MCP-first rule → [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5
- Tag rules → [tag-quality-rules.md](references/tag-quality-rules.md) · description rules (D2-D9, D3 KB template, D5 delegation contract) → [description-guide.md](references/description-guide.md) · sub-KB split → [sub-kb-creation.md](references/sub-kb-creation.md) · split-gate scanner detail → [split-gate.md](references/split-gate.md) · ICD/part-label evidence → [icd-and-part-labels.md](references/icd-and-part-labels.md)

## Flow (Steps 1-9 = stages A0-A9)

1. **Step 1 — Pre-Flight**: MCP connectivity + service status pre-check.
2. **Step 2 (A0) — Dedup**: content fingerprint detection; skip duplicates.
3. **Step 3 (A1) — Survey**: read the document content; determine KB ownership.
4. **Step 4 (A2) — Parse**: `parse_doc` for PDF/Word/Excel/images; then the A2-Q quality gate.
5. **Step 4.5 (A2.5) — Split Gate** (scripted + Agent-planned): over `ingestion.large_doc.max_chars` → scan structure, validate the Agent boundary plan, run `scripts/split_large_doc.py`; all later steps operate on source-backed parts; invalid plans and source-deletion failures are blocking.
6. **Step 5 — Save** (`kb_doc_save_parsed`, or `kb_doc_create` per part after A2.5) → **Step 6 — Tag+Describe** (A3b tags + A3c content-based descriptions).
7. **Step 7 (A6) — Index** (vector + graph) → **Step 8 (A6-V)**: verify retrievability + A3c-R self-test → **Step 9 (A9) — report.**

Three questions before ingesting: parsed-type (PDF/Office/images) vs direct-type (MD/TXT/code) picks the tool chain; the KB comes from content domain — sub-KB first, parent second, create-new third (A3d) — never the filename; any failed gate means rework, no compromise ingestion.

## Execution contract

**Executor: Archival agent**, delegated via `task` ([execution-model.md](../knowledgebase/references/execution-model.md): three-role model + combined-task boundaries). Archival is forbidden from skipping steps, bypassing gates, and using the wrong storage tool. Pre-Flight is one probe: `kb_project_status` → branch handling → smoke test. All operations go through MCP tools — no terminal/HTTP bypass.

Freedom map: A0 dedup / A2-Q parse quality / **A2.5 split gate** / A3b tags / A3c description / A5 storage / A6-V index verification = 🔒 **mandatory** (quality gates — execute strictly, no skipping or workarounds); A1 survey / A3 content analysis = 🎯 **execute** (read per the flow; results feed later decisions); A3d KB attribution / A8 sub-KB evaluation = 🧠 **judgment** (content-domain decisions; the tree guides but is not mechanical).

Four iron rules: (1) **Store the whole document** — a document is a complete unit, never truncate/summarize; oversize is handled only by the A2.5 split gate (never split by hand, never use the raw oversized file downstream). (2) **Content-driven** — KB attribution, tags, and descriptions come from the body text actually read, not filenames/guesses. (3) **Quality gates** — A2-Q / A3b / A3c: any failed gate means rework. (4) **MCP-first** — everything through `mcp__kb-mcp__*`.

## A0 — Dedup (content fingerprint, not just filename)
```
kb_find_duplicates(kb_id="<target KB>", threshold=0.90)
# → {duplicate_groups: [{type: "exact"|"near", similarity, documents, recommendation}]}
```

- `exact` (SHA256) → skip directly, report "already exists @ <path>". `near` (vector similarity ≥ 0.90) → read the first 800 chars of both → duplicate → skip, only supplement tag/description differences.
- Tool unavailable → manual dual-channel: `kb_search(query="<filename without ext>", top_k=5)` + `kb_search_vector(query="<first 500 chars of body as a declarative sentence>", top_k=5, score_threshold=0.85)`; filename hit + size ±10%, or vector hit ≥ 0.85 → read 800 chars to confirm → skip if duplicate. Not duplicate → A1.

## A1 — Survey (whole-library current state)
```
kb_list()                    # all KBs (UUID field is named kbId; description; docCount)
kb_tags_list()               # tag vocabulary (A3b reuse is a SOFT target)
fs_get_tree(max_depth=3)     # KB hierarchy (sub-KBs visible)
```

`kb_list` may transiently return an **empty catalog** (60s auth-poisoning window) — indistinguishable from a truly empty project by return value alone. Cross-check with `fs_get_tree()` before concluding; wait 20-30s and retry, up to 3 times.

## A2 — Acquire Content + Parse Quality Gate (A2-Q)
Routing: parsed (PDF/Word/Excel/PPTX/images) → `parse_doc` / `parse_doc_batch`; direct (MD/TXT/Code/JSON/YAML) → read the file; binary non-text → `fs_upload_file` (storage only, not indexed).

```
parse_doc(file_path="<abs_path>", use_ocr=true)   # non-blocking → task_id
parse_task_status(task_id) → {markdown, markdown_path, images_dir, image_count}
```

≥3 files → `parse_doc_batch(file_paths=[...], use_ocr=true)` under a single task_id. **A2-Q gate** — inspect the first 1500 chars; **any hit → reject and report, never proceed to A3**: OCR garbage (>30% garbled) → re-parse with a different OCR mode; binary residue (`\x00`/base64 fragments) → source may be corrupted; headings without body (only `#` + ≤200 chars body) → parse failed, retry or report; excess whitespace (>50 consecutive blank lines or body <100 chars) → parse failure; language mismatch (Chinese PDF → all-English garbage) → encoding/OCR retry.

## A2.5 — Structure-Aware Split Gate (scripted + Agent-planned)

`max_chars` is a storage/retrieval guardrail, not a command to cut at an arbitrary offset: a split is valid only when the text remains a sequence of source-backed logical units, so every part is independently retrievable without breaking a coherent argument. (Scanner unit taxonomy, plan JSON schema, source-span invariant: [split-gate.md](references/split-gate.md).)

1. **Scan** the parsed markdown with the bundled gate script (or the same shared backend splitter) → unit manifest (`unit_id/kind/heading_path/start_char/end_char`), including standalone chapters in flat prose.
2. **The Agent reads the content and chooses boundaries — never offsets alone**: read the chapter map, then real content at head/middle/tail windows. Cut at the content's joints — chapter ends, then scene/section ends, then paragraph ends; a boundary inside a sentence, or one that severs a continuous scene/argument, fails the plan and must be re-planned. Pack units toward `max_chars` (budget = source body; the synthetic context header is reserved automatically). Each part carries an ICD description (identity anchor + concrete events + entities + answerable scope, ≤220 chars) grounded in that part's real body, with literal `evidence` strings.
3. **Emit the plan JSON** (keys: `source_sha256`, `parts[{part_index, unit_ids, section_range, boundary_reason, description, evidence}]`) — the Agent may group adjacent scanner units and write descriptions, but never return replacement prose or arbitrary offsets. Validate before writing — hash, contiguous unit coverage, unit order, safe boundaries, description length, evidence readback; invalid → re-planned by the Agent. A missing `--agent-plan` uses the deterministic structural fallback and records `planner=deterministic`; **a deterministic fallback must never be presented as Agent segmentation.**

```bash
python "<this-skill-dir>/scripts/split_large_doc.py" "<markdown_path>" [--agent-plan "<validated-plan.json>"]
# reads ingestion.large_doc from repo-root config.yml (or --config / --max-chars); prints one JSON object:
# success / source_chars / max_chars / split / strategy(agent_semantic|structural_fallback) / planner / source_sha256
# parts[{file, source_start, source_end, section_range, description_seed, warnings}]
```

Outcomes: `split: false` → within the limit, continue with the original unit · `split: true` → parts materialized from source spans, run A3/A3b/A3c/A5/A6 per part and never save the deleted source · `warnings` has `oversized_atomic_unit` → one indivisible block > target, keep it whole and show the warning; hard window cuts **only** when `allow_hard_fallback=true` was explicitly approved (each reported as `hard_fallback_cut`) — hard cuts sever coherent content · `success: false` → scanner/config/IO/plan error, fix or report, never pass an oversized raw source downstream.

Zero character overlap by default — continuity comes from complete logical units + explicit section context, not duplicate slices. `--dry-run` writes/deletes nothing. If splitting ran, the temporary unsplit markdown is deleted after successful materialization; any deletion warning is a blocking condition. Parts keep the original body exactly plus a synthetic header (`source title + part i/N + section range`) outside the source span; upload parse images once into the KB before saving parts.

## A3 — Structured Content Analysis
Read the part body — long documents/parts use bounded head/middle/tail evidence windows (sampling for description analysis only; Librarian retrieval later reads every candidate segment):

```json
{"title": "real title (body H1, not the filename)", "domain": "main domain", "sub_domain": "sub-domain",
 "methods": [...], "materials": [...], "scenario": "problem solved / applicable scenario",
 "key_findings": [...], "language": "zh|en|mixed", "raw_tags": ["5-8 candidate domain words (before A3b cleaning)"],
 "target_kb_decision": "see the A3d decision tree"}
```

≥3 documents or a single document >50KB → delegate sub-agents for analysis (content samples + KB list + tag vocabulary), accepted per the [description-guide.md D5](references/description-guide.md) contract.

## A3b — Tag Quality Gate
Clean A3's `raw_tags`; **skipping is strictly forbidden**. Full rules: [tag-quality-rules.md](references/tag-quality-rules.md).

```
1. T1 blocklist filtering → discard section titles ("Abstract"/"1 Introduction"/"References") / test tags (test-*) / descriptive tags
2. T2 normalization       → unify casing (pet→PET) + merge Chinese/English synonyms (polyethylene/PE: keep the in-vocabulary one)
3. T3 count trimming      → keep 2-5: material words + method words + scenario words (+ 0-2 attributes)
4. T4 vocabulary compare  → SOFT target: reuse existing kb_tags_list() words when they fit the content
5. T5 content readback    → every tag actually appears within the ≥2000-char sample
```

Priority: **T5 content anchoring > T3 count > T2 normalization > T4 vocabulary reuse.** When no vocabulary word fits, coin content-derived tags (Organize L2 normalizes them later) — never pad the reuse rate with words absent from the body (violates T5; field-tested: coining all-new tags was correct when a 364-word vocabulary had no fitting topic). Fail → return to A3 to re-extract; do not release to A5.

## A3c — Description Quality Gate

Per [description-guide.md](references/description-guide.md); **four elements + content readback are mandatory**: `Description = [Subject] + [Method/Technology] + [Scenario/Problem] + [Key data/Conclusion] + [Language]`

- **≥2 concrete nouns among the four elements** (method/material/equipment/dataset names) — "a paper about X" is forbidden. Verify every claim against the body before saving: direct path → source file; parse path → the `parse_task_status` markdown (gate runs pre-save; C1 re-verifies the stored copy via `kb_doc_read(..., max_chars=800)` after A5). Mismatch → rewrite the description, never the body.
- **D8 multi-dimension + query orientation**: cover domain, method, object, problem-in-user-voice, conclusion; preserve bilingual method anchors; evidence from the part itself. Long-document windows support description analysis only — never authorization for retrieval to prune unseen segments; >20000 chars mandates three-window sampling. Every split part keeps a complete `Part i/N · section range` marker, ≤220 chars.
- **D9 Identity-Card Description (ICD)** — mandatory for fiction/multi-work/multi-topic collections, recommended everywhere: description quality IS the librarian funnel's precision ceiling (vague descriptions give the matcher zero signal and force whole-library reads; ICDs select exactly the relevant parts). Shape: 【门类】+ 事件(1-3 个具体事实，检索钩子，正文实读所得) + 实体(3-8 个专名) + 可答/不含; D2 identity anchor repeats in every part (作品名双语并列) so any part is independently addressable; D4 event fingerprints are precision hooks (write "达西二度求婚，伊丽莎白应允", not "本章精彩纷呈"); the KB description carries the 收录清单 so L1 prunes at work level. Build/validate offline with `scripts/identity_card.py` (`build`/`validate`/`audit`); acceptance `validate` 6/6 (grade icd-ok) before saving — exact template + measured failures: [icd-and-part-labels.md](references/icd-and-part-labels.md).
- **A3c-P part-label integrity check (mandatory for split parts)** — the `【Part i/N · <range>】` label is what the librarian reads to pick a part; a wrong label silently breaks hierarchical retrieval (measured: 24 of 26 labels read "Gutenberg front/back matter" over real chapters → the librarian picked 2 parts instead of 7). Every part's label must be: non-boilerplate (same value must not repeat across ≥3 siblings); non-degenerate (no inverted/single-point span `XV–I` / `XLVI–XLVI`); non-placeholder (a literal `【?/?·` prefix is a template failure — measured 156 of 322 catalog docs — flagged `broken_part_prefix` by the librarian's L3); content-derived (from the part's own head/tail windows, never copied from part 1, never assumed from type). Any violation → regenerate that part's label from its own content before A5; do not save a failing part.
- **Audit / repair (post-hoc)** after bulk ingests — `scripts/audit_descriptions.py` (flags empty/short/broken_part_prefix 【?/?· /boilerplate ≥3 repeats/degenerate_range/part_anchor_missing) + `scripts/repair_part_prefixes.py [--apply]` (deterministic, no LLM: fills missing k/N from the path, skips rows changed since the dump; other defects need a content-based A3c rewrite), on a catalog dump (`kb_list` + `kb_get_documents(lightweight)` as JSON) — commands: [icd-and-part-labels.md](references/icd-and-part-labels.md).

- **A3c-R retrieval self-test (mandatory closed loop after A6 indexing)** — see the A3c-R section below; runs after A6-V.

✅ "Coal mill blockage early warning based on CNN-LSTM, trained on DCS historical data, 660MW unit field-tested with 315min advance warning. In Chinese." ❌ "Coal mill paper" / "Parsed from xxx.pdf" / "test" / "polymer research"

## A3d — KB Attribution Decision Tree (put it in the right place)
```
① Sub-KB exact match?  Read A1's fs_get_tree; a [sub-KB] whose description strongly matches the doc's sub_domain → target = that sub-KB (best)
② Parent KB domain match + no suitable sub-KB yet → target = parent KB; record "may need a sub-KB in the future" (A8 evaluation)
③ No match at all → kb_create(name="<Domain>-<SubDomain>", description=per the D3 template, parent_id="<parent KB or empty>")
   — the new KB description must meet the A3c bar; "to be filled later" is not allowed
```

Mis-attribution check: compare the target KB's description against the document's `sub_domain + methods` — an obvious domain conflict (RAG doc into the "polymer library") → rerun the tree.

## A4 — Find/Create KB (execute the A3d decision)

Existing KB → use its UUID. Create new/sub → `kb_create(name, description, parent_id)` (D3 KB-level template; a sub-KB points `parent_id` at the parent's `kb_id`).

## A5 — Store the Document (whole document, no truncation)
**Source rule**: a split plan that is invalid, unavailable, or not fully materialized is a hard failure — never fall back to saving the oversized raw markdown. The web/API path may keep a whole document only when the caller explicitly marks it staging (`split:false`); final ingest uses only validated parts. **Routing after A2.5**: store **each validated part** via `kb_doc_create` (one call per part with its qualified description + split metadata) — never re-store the deleted oversized original, never call `kb_doc_save_parsed` for the unsplit source.

```
save = kb_doc_save_parsed(parent_id=target_kb_id, task_id="<task_id from A2>",
                          description=the qualified A3c description)  # task_id auto-extracts full markdown + images_dir
```

⚠️ The parameter is `parent_id`, not `kb_id` (passing `kb_id` is rejected by the schema). `task_id` mode is recommended — no manual markdown_path assembly. Effects: full markdown written to disk + all images copied into the KB `images/` + atomic `.tree-fs.json`/`.knowledge-base.yml` update. **Never use `kb_doc_create` to store parsed documents** — it truncates content and drops images.

## A6 — Index + Graph + Tags + Post-Index Verification

**A6a**: `idx = kb_index_document(kb_id=target_kb_id, doc_path=doc_path)` → `{vector_index: {collection, total_chunks, graph_doc_id}, graph_stats}`.
**A6b** (immediately after vector indexing):
```
kb_graph_build(kb_id=target_kb_id, force=true)   # NON-BLOCKING → {status:"running", task_id}; poll kb_task_status(task_id)
kb_graph_document(doc_path=doc_path)             # document node exists = build landed (keys: document/tags/related_documents/related_count — no "entities" field)
```
`kb_task_status` resolves task ids across MCP processes (persisted registry `storage/mcp-task-registry.jsonl`; resolved records carry `cross_process: true`) — if a status call still reports unknown id, verify completion directly instead of retrying. Known gap: `kb_doc_update_tags` reaches `.knowledge-base.yml` immediately but may NOT appear on the graph node's `tags` (reindex lag) — C7 judges by document-node existence.
**A6c**: `kb_doc_update_tags(kb_id=target_kb_id, doc_path=doc_path, tags=<after A3b cleaning>)`.
**A6-V (mandatory)**: (1) `vector_index.collection` non-empty; (2) collection UUID == `kb_<target_kb_uuid>` — another UUID means an orphan collection; (3) `total_chunks ≥ 1`; (4) `kb_graph_document(doc_path)` finds the document node.

## A3c-R — Retrieval Self-Test (description closed loop, mandatory after indexing)

The final judge of a description is retrieval — use your own description as the query; if it cannot recall the document, the description lacks a query path.

```
kb_search(query="<problem-dimension wording from the description>", top_k=5)                      # target must appear in results
kb_search_vector(query="<paraphrased question — do not copy the sentence verbatim>", top_k=5, score_threshold=0.3)  # target must be top-5
```

Any miss → merge the missed query terms (problem/method dimensions) into the description via `kb_doc_update_meta`, then retest. A3c truly passes only when both channels hit (criteria: [description-guide.md D9](references/description-guide.md)).

## A7 — Final Checklist (all ✅ required for completion; any ✗ → rework that step)

| # | Check item | Tool | Pass criteria |
|---|---|---|---|
| C1 | Content complete, not truncated | `kb_doc_read(max_chars=500)` | body matches the A3 sample |
| C2 | Description meets the bar | read description | four elements; content readback passed |
| C3 | Tags meet the bar | read tags | 2-5 tags; no blocklist; no synonym duplicates |
| C4 | KB attribution correct | doc sub_domain vs KB description | domain consistent |
| C5 | Vector index ready | vector_index field | non-empty; correct collection |
| C6 | Images complete (parse path) | image_count comparison | matches the parse result |
| C7 | Graph index ready | `kb_graph_document(doc_path)` | document found in the graph |
| C8 | Three-layer metadata consistent | `.tree-fs.json` ↔ `.knowledge-base.yml` ↔ disk | document present in all three |
| C9 | Description self-test (A3c-R) | `kb_search` + `kb_search_vector` | both queries recall this document |

**A7-E — Experience extraction (optional)**: after the final check, if capacity allows — `experience_extract(kb_id=target_kb_id, mode="prepare")` (⚠️ prepare mode has no dry_run; always returns the LLM task package) → Agent LLM refinement → confidence ≥0.8 approved, <0.8 to the draft pool. Recommended when KB completeness/freshness requirements are high.

## A8 — Sub-KB Evaluation + Orphan Cleanup
- Parent KB reaches `SUB_KB_AUTO_SPLIT_THRESHOLD` (**≥8 documents spanning ≥2 sub-domains**) → split per [sub-kb-creation.md](references/sub-kb-creation.md) (authoritative threshold table at its top).
- Orphan cleanup (opportunistic): KBs with `doc_count=0` and empty descriptions → report to the user whether to delete. **Do not delete without permission.**

## A9 — Ingestion Report
```
✅ <filename> → <full path of target KB> | Type: PDF (parsed) | Title: <real title>
   Split (A2.5): not needed (<n> chars ≤ <max_chars>) | split into <N> parts (script), temp original deleted
   Description: <first 80 chars of the qualified description>... | Tags: [tag1, tag2, tag3] (after A3b)
   Index: vector=<collection> chunks=<n> | graph=<entities>e/<relations>r | Dedup: none / skipped (duplicate of <path>) | Final check: C1-C9 all ✅
```

## Never
- Skip A0 dedup — files renamed and re-ingested slip through; the dual channel (filename + fingerprint) exists for that.
- Skip the A2-Q gate — OCR garbage gets ingested; inspect item by item after A2.
- Skip A2.5, split by hand, or eyeball char counts — oversized docs degrade every retrieval layer and manual splits lose headers+descriptions; run `scripts/split_large_doc.py` (it reads the setting, writes parts, deletes the temp original).
- Store parsed documents with `kb_doc_create` — it truncates content and drops images; parsed documents use `kb_doc_save_parsed`.
- Tag without A3b or describe without A3c — section-title tags and filename "descriptions" get ingested.
- Skip post-index verification — you land in an orphan collection; A6-V verifies UUID + chunks.
- Continue ingesting despite a failing quality gate, or "ingest first, fix later" — garbage in, garbage out, and it never gets fixed; ingestion completes only when C1-C9 are all ✅.
- Skip A7-E experience extraction — experience factors in documents are lost (optional, but trigger it when capacity allows).
- Write a long document's description from its first 3000 chars — mid/tail meaning is lost and the description over-generalizes; >20000 chars mandates three-window sampling (D8).
- Skip the A3c-R self-test — however good a description is, it is wasted if retrieval cannot recall it; both channels must hit.
- Present a deterministic fallback split as Agent segmentation.

## Tool quick reference
- `parse_doc(file_path, use_ocr=true)` / `parse_doc_batch(file_paths, use_ocr=true)` → `parse_task_status(task_id)` — non-blocking parsing · `scripts/split_large_doc.py <md> [--agent-plan J] [--max-chars N] [--config PATH] [--dry-run]` — A2.5 split gate
- `kb_doc_save_parsed(parent_id, task_id, description)` — parse path · `kb_doc_create(kb_id, name, content, description)` — direct path / per-part storage after A2.5
- `kb_index_document(kb_id, doc_path)` · `kb_graph_build(kb_id, force=true)` → `kb_task_status(task_id)` · `kb_graph_document(doc_path)` · `kb_doc_update_tags(kb_id, doc_path, tags)` (after A3b) · `kb_doc_update_meta` · `kb_doc_read(kb_id, doc_path, max_chars)` — A3/A3c/C1
- `kb_search(query, top_k)` + `kb_search_vector(query, top_k, score_threshold)` — A0 dedup + A3c-R self-test · `kb_create(name, description, parent_id)` · `kb_tags_list()` · `fs_upload_file(file_path, parent_id, description)` — binary upload
- ⚠️ Parameter naming: `kb_list` **returns** `kbId` but most tools take `kb_id`; `kb_doc_move(doc_path, target_kb_id)` has no source-KB parameter. Print an entry confirming key names on first call.
