# Parallel merge protocol (design reference)

This document specifies the contracts behind `scripts/hybrid_search.py`. The
measured baseline for the design is the three-mode comparison harness in
`review/laya-three-mode-20260925/` (3 questions × A/B/C, real local Laya judge).

## 1. Lane contracts

### Lane A — vector (proposes, never reads)

```
kb_search_vector {query, kb_id: "", top_k, score_threshold, balance_kbs: true}
```

- Hard cut at `score_threshold` (default 0.35) on the **chunk** score.
- Dedup chunks → documents by `(kb_id, doc_path)`, keeping the best chunk score.
- Output: refs `{kb_id, doc_path, doc_id, name, vector_score, chunk_index, lane: "vector"}`.
- The lane performs **no** `kb_doc_read`: content arrives either from the catalog
  lane (shared docs) or from the unified reread (vector-only docs).

### Lane B — catalog (complete-recall scan with a budget)

```
kb_list {lightweight: true}
kb_get_documents {lightweight: true, kb_id}     # every kept shelf
kb_doc_read {kb_id, doc_path, max_chars}        # every picked doc
```

- Shelf selection: `doc_count > 0` (null counts kept — unknown, not empty) minus
  `--exclude-prefix` names. Recall beats a cheaper scan.
- Every document description is scanned; overlap = shared terms with the query
  **plus the agent's `--extra-terms`** (bilingual Phase-0 keywords — queries and
  descriptions often live in different languages; measured zero-overlap failure
  T1/T3 2026-09-25).
- Budgeted selection order (`pick_catalog_docs`):
  1. description-overlap hits, score desc;
  2. **stem completion** — siblings of any picked `(part k of N)` document, up to
     `--stem-max-parts` (a matched paper brings its experiments/appendix parts);
  3. zero-overlap top-up as a **round-robin across KBs**, `relevant`/`possible`
     shelves first (v1 drained in catalog-scan order, silently biasing toward the
     first-scanned KB — measured T3: the gold in the 4th KB was never read).
  Unread zero-overlap docs are counted in `zero_overlap_docs_unread`.
- **peek-heads** (`--peek-heads`, peek_chars default 700, peek_limit default 300):
  every unpicked zero-overlap doc gets one cheap head read and its head enters the
  judge like any segment. This removes the description-vocabulary blind spot by
  construction — measured T3 2026-09-25: without it, the librarian scanned 329
  descriptions, judged 30 docs in 307s, and the answer document was never opened.
- Each read document is segmented by `complete_recall.segment_document`
  (source-backed blocks + sentence fallback, char/line offsets preserved).

## 2. Merge

- Identity: `(kb_id, norm(doc_path))` where `norm` maps `\` → `/`. The same file
  in two KBs stays two documents.
- `lane` semantics: `both` (catalog content + vector score, judged once),
  `catalog`, `vector` (proposal until reread).
- Order stability: catalog docs insert first, so `lane=both` wins the record
  identity and the vector score is attached — no duplicate judge work.

## 3. Unified reread

- Targets: merged docs with empty content (= vector-only proposals).
- One `kb_doc_read` per target (default `max_chars=20000`), then segmentation.
- Read failure or empty content → doc moves to `unscanned` with the reason and is
  excluded from judging. A proposal is never judged on its description alone.

## 4. Decision-engine gate

- Engine: `laya` (default, local SDK) or `jev` (explicit remote). No fallback
  between engines; no keep-all on failure. Per-candidate fail-closed semantics
  are inherited from `jev_filter.filter_candidates`.
- Segments truncated to `--max-state-chars` (default 6000) for CPU throughput.
- Per-doc score = best segment score of that doc.
- Retention (shared `complete_recall.retain_docs`): `score ≥ threshold` **and**
  `score ≥ global_best − relative_margin` (defaults 0.5 / 0.10), plus a **top-K
  floor** (`--top-k-floor`, recommended 5) that keeps the global top-K docs
  whenever real evidence exists (`global_best ≥ threshold`). Rationale: the local
  Laya `noul` distribution on academic prose is top-heavy (measured median ≈0.88,
  min ≈0.55), so the absolute threshold alone is non-discriminating; the relative
  cut isolates the evidence-bearing tier; the floor protects question-critical
  mid-score docs (measured T1: an experiments section at 0.84 cut at 0.854).
  `abs_kept` reports the raw-threshold view.
- `--lane-agreement` (opt-in): `lane=both` documents scoring at or above the
  absolute threshold are kept without the relative cut. The hybrid's edge over
  either single lane is exactly the two-lane agreement signal, so it overrides
  the distribution-dependent adjustment. Measured rescue (2026-09-23, q2): gold
  MultiMedQA part 1 judged 0.868 was cut by a 0.879 relative threshold inflated
  by a lexically-attractive wrong dataset doc (0.979); the gold was lane=both
  (vector rank 2) and this rule retained it.
- `real_engine=false` (injected/offline scores) is always visible in the output;
  `--require-real` turns it into exit code 2.

## 5. Failure semantics

| Event | Behavior |
|---|---|
| One lane raises | `status=partial`, error in `lanes.<lane>.error`, the other lane still merges/judges |
| Both lanes raise | `status=error`, no judge work |
| Reread fails per doc | doc → `unscanned`, others continue |
| Engine unavailable | judge `status=unavailable`, `result_list` empty, nothing kept implicitly |
| CLI hard error | JSON with `status:error`, exit 1 |

## 6. Output schema

See SKILL.md "Output contract". Machine consumers should treat
`result_list` as the deduplicated answer-facing document set and
`judge.doc_scores` as the full scored audit trail (kept or not).

## 7. Test isolation

`run_hybrid` accepts `mcp_factory` and `score_fn` injections. Tests never spawn
MCP servers or load the real model; injected scores are labelled
`real_engine=false`. The real-model path is exercised by the CLI with
`--require-real` (see `review/hybrid-skill-20260923/` transcripts).
