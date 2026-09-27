---
name: knowledgebase-librarian
description: "Complete-recall librarian retrieval for unknown shelves, heterogeneous libraries, long-document questions, vector misses, and explicit all/every requests. Read every KB and unlimited-depth sub-KB description, keep all relevant or possible shelves, read every document description with doc IDs/paths, verify metadata against content, read every candidate segment, send every segment to the real Jev/Laya filter, keep EVERY segment the engine scores yes (>= threshold) — no re-scoring and no pruning — aggregate all survivors with provenance into one evidence pack, and answer from all of it or report exact blind spots. Use for librarian, shelf scan, catalog search, coarse-to-fine, 逐级检索, 全库粗检索, 哪个知识库, 穷尽召回, Jev 判断, or 完整召回."
---
## ⭐ Related Skills
- **Vector + Jev-gate path** → `skill://knowledgebase-search` — the companion fast lane: `kb_search_vector` wide net first, then the Laya/Jev verify gate. This skill performs complete-recall catalog/read/Jev work when required.
- **Parallel hybrid of both lanes** → `skill://knowledgebase-hybrid` — runs this lane and the vector lane concurrently on separate MCP connections, dedups on (kb_id, doc_path), one unified reread, then the same engine gate.
- Document ingest → `skill://knowledgebase-ingest` — description quality is produced there (A3c / A3c-P)
- KB integrity → `skill://knowledgebase-verify` — three-way consistency
- Knowledge graph → `skill://knowledgebase-graph` — cross-library bridges

## The two retrieval lanes (do not confuse them)

| Lane | Skill | Mechanism | Use when |
|---|---|---|---|
| **A · vector + Jev gate** | `knowledgebase-search` | `kb_search_vector` wide net → dedup/threshold → **Laya/Jev verify gate** (read the body, engine scores every segment) → librarian fallback | default; fast semantic candidate proposal |
| **B · complete-recall librarian** | **this skill** | all-KB catalog → all possible shelves → all document descriptions → description trust check → **all candidate parts/segments** → **real Jev gate** (yes = keep, nothing else) → aggregate ALL survivors → answer from the whole evidence pack | unknown shelf, heterogeneous library, vector miss, long-document enumeration, or explicit “all/every/complete” request |

Lane B is intentionally more expensive. Its promise is high recall, not an unbounded latency guarantee: every scanned KB/document/segment is counted, and any unscanned scope is reported as a blind spot. Description matching only decides which records are *possible*; it never decides the final answer.

## When to use this skill

| Situation | Use librarian? |
|---|---|
| You know the KB, a simple fact question | No — `knowledgebase-search` Phase 1 (vector) is enough |
| You don't know **which** KB holds the answer | **Yes** — L0–L1 |
| Library is large / many heterogeneous KBs | **Yes** — shelf ranking is the whole point |
| Vector-first gate scored ≤5 | **Yes** (this is search's Phase 2) |
| Question spans a **whole long document** | **Yes** — L4 part selection + L5 targeted reads |
| Question needs a **specific chapter/section** of a long doc | **Yes** — read every candidate part/segment, then let Jev retain answering evidence |

## The One Picture

```
query entities (subject × attribute × constraints)
  │
  ├─ L0 CATALOG      kb_list(lightweight=True)        → EVERY KB: id + name + description + doc_count
  │
  ├─ L1 HIGH-RECALL SHELF LABEL
  │                  label every KB relevant / possible / out_of_scope
  │                  complete mode keeps relevant + possible (no fixed top-2/3)
  │
  ├─ L2 DOCUMENT CATALOG
  │                  kb_get_documents(lightweight=True, kb_id) → EVERY doc:
  │                  doc_id/file_id + path + name + description
  │                  group split siblings logically but retain every concrete part
  │
  ├─ L3 ⭐ TRUST CHECK  description is a claim, not a fact
  │                  boilerplate / empty / contradictory → mark untrusted and
  │                  require a content read; never prune solely on description
  │
  ├─ L4 RECALL ALL SEGMENTS ⭐
  │                  kb_doc_read with pagination → structure-aware paragraph,
  │                  list, table, code, section/sentence segments with offsets
  │                  every possible segment enters the Jev manifest
  │
  ├─ L5 ⭐ REAL JEV GATE
  │                  scripts/jev_filter.py (JSON in/out), every segment scored
  │                  noul ≥ threshold survives; missing/error scores are rejected
  │
  ├─ L5.5 AGGREGATE  sort by KB/doc/part/offset, deduplicate overlaps, preserve
  │                  doc_id/path/section/line/char + Jev score provenance
  │
  ├─ L6 HANDOFF      answer from the FULL Jev-yes evidence pack — no re-scoring,
                     no pruning; report counts, backend/threshold, citations
                     and any unscanned blind spot
```

**The engine verdict is final.** Lane B has exactly one gate: the real Jev/Laya
decision. Every segment scoring ≥ threshold is kept and becomes answer
material — no content rubric, no doc-level retention cut, no P0/P1 tiering
after the fact. The lanes differ on purpose: lane A double-checks its fast
candidates with a rubric because vectors are only proposals; lane B has
already read the real body text end-to-end before judging, so the engine's
yes on real text is the last word.

**Jev/Laya decision guidance:** [references/laya-sdk.md](references/laya-sdk.md) documents the default local Laya SDK, model/cache setup, `noul=P(true)`, threshold, and fail-closed behavior. [references/jev-judgment-layer.md](references/jev-judgment-layer.md) documents the explicit remote Jev option. The bundled `scripts/jev_filter.py` defaults to `engine=laya`; pass `--engine jev` only when remote Jev is intentionally selected. Every scored candidate is returned in `result_list` with doc ID/path/part/section/offset provenance.

```
kb_list(lightweight=True)     # {kb_id, name, description, doc_count} for every KB
```
Do **not** skip this. The librarian's whole edge is having read *every* summary before judging —
guessing KBs by name is forbidden.

## L1 — High-recall shelf labeling

Match the query's **subject × attribute × constraints** against every KB description and label each shelf:

- `relevant`: multiple query dimensions match;
- `possible`: one dimension matches, the description is missing/ambiguous, or terminology may be multilingual;
- `out_of_scope`: no observed match and the description is specific enough to trust.

**Work-level pruning for multi-work KBs (ICD contract):** a well-formed KB description carries a 收录清单 (work inventory). Match the query's work identity (e.g. 《傲慢与偏见》/ Pride and Prejudice) against the inventory BEFORE doc-level work: a "小说库" that does not list the queried work is `out_of_scope` even though its genre matches — genre overlap alone never justifies reading a whole multi-work library. Conversely, a KB listing the work stays `relevant` and its parts are matched per-work at L2 via the identity+事件 dimensions of each part's ICD description.

In **complete-recall mode**, keep every `relevant` and `possible` KB, including unlimited-depth sub-KBs discovered from the tree. Do not use a fixed top-2/3 cutoff — multiple shelves may hold the answer and all of them are kept. An `out_of_scope` label is allowed to prune only when the catalog description is present and trustworthy; if all shelves appear out of scope because vocabulary differs, expand to the full catalog and report the expansion.

## L2 — Full document catalog (all kept shelves)

```
kb_get_documents(lightweight=true, kb_id=<every relevant/possible shelf>)
# [{doc_id, file_id, doc_path, name, description}]
```

Read every returned description. Group `(part k of N)` siblings for logical-document reasoning, but retain every concrete `doc_id`/`doc_path` and part number for reads and citations. A description match is a candidate-generation signal only; it is not a relevance verdict.

## L3 — ⭐ Description trust check (the step that makes this work)

**A description is a claim, not a fact.** Measured failure (2026-09-24): in a 26-part novel KB,
**24 of 26** descriptions read `Gutenberg front/back matter` while the parts actually contained
novel chapters — the librarian selected 2 parts instead of 7 and lost 2 of 7 key scenes.
A description-only librarian inherits every such error.

Before trusting a description, test it:

| Test | Untrustworthy if |
|---|---|
| **Boilerplate** | the same (or near-identical) description text repeats across many docs |
| **Content-free** | it names no specific subject/chapter/section/date/number of its own |
| **Contradiction** | its claimed range/section does not match the doc name or its siblings' spans |
| **Degenerate range** | an inverted or single-point span (e.g. `XV–I`, `XLVI–XLVI`) |
| **Broken part prefix** | a literal `【?/?·` placeholder — the ingest template never filled the part index (measured 156/322 catalog docs); part claims in this description are unreliable |

If untrusted → **downgrade the metadata signal and read the real content**:
```
kb_doc_read(kb_id, doc_path/doc_id, max_chars=600)   # verify from the opening text
```
Do not impose a fixed two-head-read budget in complete-recall mode. Read enough content to resolve the trust question, record `description_trust=untrusted`, and keep the document in the Jev candidate manifest when its shelf is `relevant` or `possible`.

## L4 — ⭐ Read every candidate segment (completeness first)

For each document/part in every kept shelf, use paginated `kb_doc_read` until the full readable body is covered. Build a JSON candidate manifest with one or more structure-aware segments per document. Segment boundaries should follow headings, paragraphs, lists, tables, fenced code, blockquotes, figures, or sentence boundaries; retain `doc_id`, `doc_path`, `part_index`, `section_path`, `start_line/end_line`, and `start_char/end_char`.

```text
for EVERY kept document part:
    read all pages with kb_doc_read(offset, limit, max_chars)
    scan the returned body into source-backed segments
    append EVERY segment to the Jev manifest
```

The reference implementation is `scripts/complete_recall.py`. It consumes an Archival-produced manifest and never calls MCP itself. Description matching only chooses `relevant/possible` shelves; pruning happens on real segment text after Jev. If pagination, service limits, or budgets leave a document/part unread, put its exact identity in `unscanned` and report it; never call the result exhaustive.

> **Interpreter**: Laya-judging paths (`complete_recall.py`, `jev_filter.py`) run under `backend/.venv/Scripts/python.exe` — the MinerU env hosting `laya` + GPU torch (Laya auto-selects CUDA). Bare `python` without `laya` fails closed (`JevUnavailable`).

**Budgeted catalog selection (script layer, `knowledgebase-hybrid/scripts/hybrid_search.py: catalog_lane`)** — when the lane runs under a read budget, selection order is: description-overlap hits → split-doc sibling completion (a picked `(part k of N)` brings its siblings, capped) → zero-overlap **round-robin across KBs** with `relevant/possible` shelves first (never drain in catalog-scan order — measured 2026-09-25: scan-order top-up silently favored the first KB and a 4th-KB gold was never read). With `--peek-heads`, every unpicked zero-overlap document still gets one cheap head read and its head is judged — the engine, not description vocabulary, decides its fate. This is the scripted form of "不要遗漏" under a budget.

## L5 — ⭐ Real Jev judgment and evidence aggregation

Write the manifest to JSON and invoke:

```bash
python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py \
  --engine laya --input candidates.json --output laya-result.json --require-real
# Use --engine jev only when remote Jev is intentionally selected.
```

The filter sends every candidate segment to the selected engine (default local Laya; explicit `engine=jev` for remote Jev) using the documented `noul` evidence/instance question. It returns one score record per candidate plus `result_list`, `survivors`, a deduplicated source-ordered `evidence_pack`, and provenance. Missing SDK/model/credentials, request errors, malformed/out-of-range scores, and rate-limit exhaustion are **fail-closed**: the affected candidate is not kept and the result is `unavailable`/`error`, never an implicit pass. Engines never silently fall back to one another.

- default engine `laya`; explicit `engine=jev` only when remote Jev is selected;
- every candidate gets a score record; `result_list` contains all kept candidates with source provenance;
- lookup/evidence query → `criterion=evidence`;
- enumeration/completeness query → `criterion=instance`;
- **keep EVERY yes-scored survivor — the engine verdict is final**: a segment scoring ≥ threshold is evidence, full stop. No doc-level retention cut, no top-K floor, no content rubric, no P0/P1 tiering after the gate (the relative cut and top-K floor remain options of the *hybrid* lane, not this one);
- aggregate by `{kb_id, doc_id/path, part_index, section, offset}` and merge duplicate/overlapping text without dropping provenance;
- answer from ALL scored survivors — every survivor is knowledge enhancement the answer must be able to draw on; the `evidence_pack` render is char-capped (default 20k) but `survivors`/`result_list` always carry every record, and `kb_doc_read` may re-read any survivor the pack truncated.

For offline preparation and tests, inject a score function into `complete_recall.run_manifest`; do not label that result as real Jev.
## L5.1 — Read survivors and preserve the evidence pack

This lane reaches the answer by navigating and reading, never by similarity search. The Archival agent may paginate `kb_doc_read` for survivors, but the final synthesis must use the selected engine's ordered `evidence_pack`, `result_list`, and `provenance` rather than a newly chosen top-k. Allowed reads:

```text
kb_doc_read(kb_id, doc_path/doc_id, offset=<line>, limit=100, max_chars=3000)
kb_get_documents(lightweight=True, kb_id)
fs_get_tree / fs_get_children
```

Forbidden here: `kb_search_vector`, `kb_search_two_stage`, and any embedding/BM25/hybrid ranking. If a document/part could not be fully read, report it under `unscanned`; do not silently switch to similarity.

Long documents must be judged on all manifest segments, not a single head/mid/tail sample. For `(part k of N)` files read the actual part and cite its concrete path/id.

## L6 — Handoff / answer from ALL survivors

Always finish the turn with the answer or the honest not-found report. There is no
verification step between the engine gate and the answer: the Jev/Laya yes is the
verdict, and **every survivor** — not a scored top tier — is the knowledge
enhancement the answer synthesizes from. The result must include:

- `Search Paths`: L0/L1/L2/L3/L4 counts and the `jev_filter.py` backend, criterion, and threshold;
- `Answer`: synthesized from the full survivor set (the engine's yes decides; no manual pruning afterwards);
- `Sources`: concrete KB + `doc_id`/`doc_path` + part/section/line or char offsets + Jev score;
- `Confidence`: grounded in coverage — how many survivors across how many documents/KBs at what threshold;
- `Blind Spots (Cross-Library Perspective)`: every unscanned or unavailable scope, including Jev unavailable/error status.

The only honest not-found is an engine-level one: when the real Jev/Laya gate returns zero survivors (or is `unavailable`/`error`), report exactly that — never resurrect discarded candidates by hand, and never invent a hit the engine did not score.

A partial catalog or partial segment scan must be labelled partial. It is never described as exhaustive.


## ⚠️ NEVER list

| ❌ Don't | Why | ✅ Do instead |
|---|---|---|
| Guess KBs by name without reading descriptions | The catalog read is the librarian's edge | L0 `kb_list(lightweight)` every time |
| Trust a description without the L3 check | Descriptions can be systematically wrong (measured 24/26) | Boilerplate/content-free tests → head read |
| Treat `(part k of N)` siblings as separate books | Part 1 ≠ the whole; counting inflates | Group by stem; read the hit part |
| Score a long doc from its head only | Evidence past the window is falsely discarded | chunk ∪ continuation reads |
| Search every KB when L1 found no plausible shelf | Brute force ≠ precision | Report the blind spot |
| **Call `kb_search_vector` / `kb_search_two_stage` here** | this lane's complete recall is catalog/read/Jev based | navigate with MCP, segment every body, then use `jev_filter.py`; hand off only when the caller explicitly chooses vector-first |
| Re-score, re-rank or prune Jev-yes survivors | The engine verdict is final; extra cuts recreate the recall loss this lane exists to prevent | Aggregate ALL survivors and answer from all of them |
| Answer from unscored text | Unscored = not evidence (fail-closed) | Honest engine-level not-found when zero survivors |

## Quick rule reference
1. **Catalog first** — read every KB description before judging (L0)
2. **High-recall shelf labels** — keep every `relevant` and `possible` KB in complete mode (L1)
3. **Read every doc description** in every kept shelf, part-aware, with doc IDs and paths (L2)
4. **Distrust descriptions** — boilerplate/content-free/degenerate → content read (L3)
5. **Read every candidate segment** and record exact offsets; no top-k or head-only pruning (L4)
6. **Real Jev only, and its yes is final** — every candidate scored, fail-closed; ≥ threshold = keep ALL (L5)
7. **Aggregate all survivors** by source/offset with provenance (L5.5)
8. **Answer from the full survivor set** or report engine-level blind spots; never fabricate (L6)
