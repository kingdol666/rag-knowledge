---
name: knowledgebase-ingest
description: >
  Document ingestion pipeline with quality gates A0→A9. Content-first workflow: dedup (content fingerprint), survey, parse with quality check, SCRIPTED split gate for oversized documents (reads ingestion.large_doc.max_chars from config.yml, never split by hand), structured analysis, tag quality gate (blocklist+normalize+verify), description quality gate (4-elements+content-readback), KB-attribution decision tree (sub-KB first), store by file type, index+tag with post-index verification. Triggered by: ingest, upload, import, store, parse, parse PDF, save to KB, ingest a document, put a document, add a document, 拆分, 分块, 大文档入库, maxChars, split large document.
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
**Step 4.5 — Split Gate (A2.5, scripted)**: count chars of the parsed markdown; if over `ingestion.large_doc.max_chars`, run `scripts/split_large_doc.py` (reads the setting, writes part files, deletes the temp original). All later steps then operate on the parts.
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
1. **Store the whole document** — a single document is a complete unit; never truncate/summarize. Oversize is handled by the **A2.5 split gate**: when the parsed markdown's char count exceeds `ingestion.large_doc.max_chars` (Settings → 入库规范, hot-effective), run `scripts/split_large_doc.py` — it writes part documents and deletes the temp original; each part then enters the flow as a complete unit with its own content-based description. **Never split by hand, never use the raw oversized file downstream.**
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
kb_list()                    # all KBs (UUID 字段名为 kbId；description；docCount)
kb_tags_list()               # tag vocabulary (used by A3b normalization; reuse is a SOFT target, see A3b T4/T5)
fs_get_tree(max_depth=3)     # KB hierarchy structure (sub-KBs visible)
```
> ⚠️ `kb_list` 可能瞬时返回**空 catalog**（60s 鉴权毒化窗）——空结果与"项目真的为空"无法从返回值区分，
> **必须用 `fs_get_tree()` 交叉验证**后再下结论；等 20-30s 重试，最多 3 次。

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

## A2.5 — Split Gate (Scripted, Mandatory) ⭐

Oversized documents destroy retrieval granularity (vector chunks, BM25 windows, graph nodes all degrade). Before saving, **always count the parsed markdown's chars and enforce the configured chunk limit with the bundled script** — never decide by eye, never split by hand.

**1) Count chars** of the parsed markdown (from `parse_task_status`'s `markdown` or `markdown_path`).

**2) Run the gate script** (resolve `scripts/split_large_doc.py` relative to this SKILL.md's directory):
```bash
python "<this-skill-dir>/scripts/split_large_doc.py" "<markdown_path>"
```
The script reads `ingestion.large_doc.max_chars` from config.yml itself (**the key lives in the REPOSITORY-ROOT config.yml under `ingestion.large_doc` — not backend/config.yml**; the script probes CWD-upward, so run it with the repo root in its path chain, or pass `--config <path>` / `--max-chars N` explicitly), and prints one JSON line:
```json
{"success": true, "source_chars": 8432, "max_chars": 1000, "split": true,
 "part_count": 9, "source_deleted": true,
 "parts": [{"file": "... (part 1 of 9).md", "chars": 990,
            "description": "<real-content excerpt of THIS part>"}, ...]}
```

**3) Act on the JSON**:
| Result | Meaning | Next |
|---|---|---|
| `split: false` | under the limit; source is kept | continue with the original file (single unit) |
| `split: true` | part files written next to the source; **temp original deleted** (`source_deleted: true`; if deletion failed a `warning` is set — delete it manually) | all later steps (A3/A3b/A3c/A5/A6) run **per part**; the original must never appear downstream |
| `success: false` | IO/config error | fix the cause; do not ingest the oversized raw file |

- `--dry-run` previews the plan without writing/deleting — use it only when the user explicitly wants to preview the split.
- Parts are named `<stem> (part i of N).md`, carry a content header (`# <title>（第 i/N 部分）` + section path), and the JSON gives a real-content `description` per part — use it as the A3c seed, then refine to the four-element standard.
- Parse images: parts reference `images/…` relatively. If `image_count > 0`, upload the parse output's images once into the KB (`fs_upload_file`) before/with the parts.

## A3 — Structured Content Analysis

Read a 3000-char sample and output a structured result (**this is the basis for all later decisions**).
**Long documents (>20000 chars): three-window sampling is mandatory** — head 0-3000 + middle (total/2)±1500 + tail last 2000; distill 1-2 points from each window into the analysis, so the description carries the document's full real meaning, not just its opening (see [description-guide.md D8](references/description-guide.md)).
**After A2.5 split**: run A3/A3b/A3c **per part** — each part is analyzed and described on its own real body (the gate script's per-part `description` is the seed; refine it to the four-element standard below).

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
**优先级：T5 内容锚定 > T3 数量 > T2 归一 > T4 词表复用。** T4 是软目标——词表里没有贴切的词就造新的内容衍生词（整理阶段 L2 会归一）；
**绝不为凑复用率而使用正文没有的词**（那违反 T5）。实测：词表 364 词无环境类中文标签时，全部新造是正确行为。
**Failing the bar → return to A3 to re-extract; do not release to A5.**

## A3c — Description Quality Gate ⭐

Write descriptions per [description-guide.md](references/description-guide.md); **four elements + content readback are mandatory**:

```
Description = [Subject] + [Method/Technology] + [Scenario/Problem] + [Key data/Conclusion] + [Language]
```
- **At least 2 concrete nouns among the four elements** (method names/material names/equipment names/datasets) — generic phrases like "a paper about X" are forbidden.
- **Must verify every claim against the body**: direct path → verify against the source file before saving; parse path → verify against the `parse_task_status` markdown BEFORE saving (the description gate runs pre-save), then C1 re-verifies the stored copy via `kb_doc_read(..., max_chars=800)` after A5.
- **Mismatch → rewrite the description** (never change the body to fit the description).

**D8 多维 + 查询导向（检索定位的核心，强制）**：描述必须铺满五个查询维度——领域维 / 方法维 / 对象维 / 问题维（用提问者口吻写一句"本文能回答什么"）/ 结论维（带数字优先），并在中文描述中保留英文方法名原文作双语锚点。长文按三窗采样结论补中后段要点。分 part 文档用**两层描述**：`【第 i/N 部分 · <章节范围>】<论文级主体+方法> —— <本 part 特有内容>`。单条 ≤220 字符。逐维标准见 [description-guide.md D8](references/description-guide.md)。
**<20000 chars 的短文也至少双窗**（头 3000 + 尾 2000）——结论/修正系数/附录数据常埋在尾部，只读头部必漏（实测教训）。

**A3c-R 检索自检（A6 索引后强制闭环）**：见 A6-V 之后的 [A3c-R](#a3c-r--检索自检a6-索引后必做)——用描述里的问题维措辞跑 `kb_search` + 同义改写跑 `kb_search_vector`，目标文档必须被找回，否则把漏掉的查询词并回描述复测。

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

**Routing after A2.5**: if the split gate produced parts, store **each part** via the direct path (`kb_doc_create`, one call per part with its own qualified description) — never re-store the deleted oversized original, and never call `kb_doc_save_parsed` again (it would store the unsplit full markdown).

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

### A3c-R — 检索自检（描述闭环，索引后必做）⭐

> 描述写得合不合格，最终裁判是检索。用自己写的描述当查询，找不回来 = 描述缺查询路径。

```
# 1. 元数据检索（匹配 description/tags 的主通道）
kb_search(query="<描述中的问题维措辞>", top_k=5)
→ 目标文档必须在结果中

# 2. 向量检索（同义改写，不要原句照抄）
kb_search_vector(query="<同义改写的问题>", top_k=5, score_threshold=0.3)
→ 目标文档必须在 top-5
```

任一未命中 → 把查询里的关键词（问题维/方法维）并入描述（`kb_doc_update_meta`），
更新后复测。两条都命中，A3c 才算真正通过。（标准见 [description-guide.md D9](references/description-guide.md)）

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
| Write the description from the head 3000 chars of a long document | 中后段的真实含义丢失，描述以偏概全 | >20000 chars 强制三窗采样（D8） |
| Skip the A3c-R retrieval self-test | 描述写得再好，检索找不回来就是白写 | kb_search + kb_search_vector 双通道找回才通过 |

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
- ⚠️ 参数命名：`kb_list` **返回** `kbId`，但绝大多数工具的入参是 `kb_id`；`kb_doc_move(doc_path, target_kb_id)` 无源库参数。首调先打印条目确认键名。
- `kb_tags_list()` — A3b vocabulary comparison
- `fs_upload_file(file_path, parent_id, description)` — binary upload
