---
name: knowledgebase-hybrid
description: "Parallel hybrid retrieval that runs both recall lanes at the same time on separate MCP connections: the vector lane (kb_search_vector, hard threshold, doc-level dedup) and the complete-recall catalog lane (every KB and document description, description-overlap ranking, budget top-up, full reads). Merges and deduplicates the two candidate sets by (kb_id, doc_path), re-reads only documents one lane found, segments every merged document, sends every segment to the real Laya (default) or Jev decision engine, applies the absolute threshold plus relative cut, and returns a deduplicated result_list with lane provenance for knowledge-enhanced answering. Use for 并行检索, 混合检索, 双通道检索, parallel hybrid, dual-lane retrieval, vector+catalog, both retrieval modes, dedup retrieval, when vector recall alone is not trusted or the catalog scan alone is too slow, or when the fastest recall and the most complete recall must be combined."
---
## ⭐ Related Skills
- **Vector + Jev-gate lane** → `skill://knowledgebase-search` — lane A alone (fast semantic proposal + engine verify gate)
- **Complete-recall lane** → `skill://knowledgebase-librarian` — lane B alone (catalog/read/Jev, exhaustive)
- Document ingest → `skill://knowledgebase-ingest` — produces the descriptions both lanes rely on
- Decision layer → `knowledgebase-librarian/scripts/jev_filter.py` (shared, not duplicated here)

## When to use this skill

| Situation | Use hybrid? |
|---|---|
| You want the **speed of vector recall** and the **coverage of the catalog scan** together | **Yes** — this skill's whole point |
| Vector search alone may miss paraphrased/mis-described evidence | **Yes** — the catalog lane is vector-independent |
| You only know the KB and ask a simple fact question | No — `knowledgebase-search` alone is cheaper |
| An explicit "read everything" request with no latency constraint | No — pure `knowledgebase-librarian` (no budget top-up) |
| Both lanes are unaffordable | Pick one lane; do not fake parallelism |

## The One Picture

```
query ──┬─ lane A · vector      kb_search_vector(top_k, threshold, balance_kbs)
        │   (own MCP conn)      → hard threshold → dedup by (kb_id, doc_path)
        │                       → refs only, NO reads           ┐
        │                                                        ├─ threads
        └─ lane B · catalog    kb_list → select shelves → EVERY doc description
            (own MCP conn)     → description-overlap ranking + budget top-up
                               → kb_doc_read every pick → structure segments ┘
                                   │
                      MERGE on (kb_id, normalized doc_path)
                      lane = both | vector | catalog   (shared docs never re-read)
                                   │
                      UNIFIED REREAD  vector-only proposals (one kb_doc_read each)
                                   │
                      SEGMENT        complete_recall.segment_document (source-backed)
                                   │
                      ⭐ REAL ENGINE GATE  every segment → Laya (default) / Jev
                      per-doc best score; keep abs ≥ threshold AND rel ≥ best−margin
                                   │
                      RESULT LIST    deduplicated doc metadata + lane + scores
                      → re-read survivors → answer from ALL kept docs (engine verdict is final)
```

## Division of labor

**The script does the parallel work** — the agent cannot issue two MCP calls at once,
so `scripts/hybrid_search.py` owns both threads, the merge, the reread, and the engine gate:

> **Interpreter**: run with `backend/.venv/Scripts/python.exe` — the MinerU env hosting `laya` + GPU torch (Laya auto-selects CUDA). Bare `python` without `laya` fails closed (`JevUnavailable`).

```bash
python .claude/skills/knowledgebase-hybrid/scripts/hybrid_search.py \
  --query "How does InstructDS generate high-quality query-based dialogue summaries?" \
  --engine laya --output hybrid-result.json --require-real \
  --extra-terms "instructds 对话摘要 数据集 baselines experiments" \
  --peek-heads --top-k-floor 5 --lane-agreement
# optional: --vector-top-k 10 --vector-threshold 0.35 --doc-budget 30
#           --exclude-prefix Corpus --relative-margin 0.10 --peek-limit 300
```

**Supply `--extra-terms` yourself (Phase 0, mandatory for cross-lingual corpora).** The
catalog descriptions and the query often live in different languages (measured: an
English question against Chinese descriptions shares ZERO terms — T3/T1 2026-09-25).
Write the query's subject × attribute × constraints as bilingual keywords and pass them;
they are merged into the description match. `--peek-heads` is the second, engine-based
net: every unpicked zero-overlap document gets one cheap head read (default 700 chars)
and its head is judged like any other segment — the decision engine, not description
vocabulary, decides its fate, so the scan has no blind spot by construction.

**The agent does the answering** — read `result_list`/`evidence_pack` from the JSON,
re-read survivors with `kb_doc_read` when the 2,500-char heads are not enough,
then answer from ALL kept documents. The engine gate is the single verdict —
same contract as `knowledgebase-search`/`knowledgebase-librarian`: no LLM
0-8 rubric, no re-scoring, no post-gate pruning; zero kept docs means an
honest not-found report.

## Output contract (`hybrid-result.json`)

| Field | Meaning |
|---|---|
| `status` | `ok` both lanes · `partial` one lane failed (reported, never hidden) · `error` both failed |
| `lanes.vector` | raw hits, dedup docs, seconds |
| `lanes.catalog` | shelves/descriptions scanned, overlap docs, budget top-up, docs read, seconds |
| `merge` | `from_both` / `from_vector_only` / `from_catalog_only` counts |
| `reread` | how many vector-only proposals were read; per-doc read errors |
| `judge` | engine/backend/real_engine, abs threshold, `relative_cut`, `global_best`, per-doc `doc_scores` |
| `result_list` | kept docs: `kb_id, doc_id, doc_path, name, lane, vector_score, judge_score` |
| `evidence_pack` | source-ordered pack from kept docs, lane-tagged headers |
| `unscanned` | merged docs with no readable content and why — never silently dropped |

## Merge and dedup rules

1. Identity is `(kb_id, normalized doc_path)` — backslashes and slashes are the same path.
2. A document found by both lanes is kept **once** with `lane=both`; it inherits the
   catalog lane's content and the vector lane's score. No duplicate reads, no duplicate judge work.
3. Vector-only documents are proposals until the unified reread succeeds; a failed reread
   moves the doc to `unscanned`, it is never judged on its description alone.
4. Catalog-lane budget top-up (zero-overlap docs filling the remaining budget) is reported
   in `lanes.catalog.zero_overlap_docs_unread` — partial scans are labelled partial.

## Engine gate (fail-closed)

- Default engine `laya` (local SDK, repo-local `model/laya` checkpoint; see
  `knowledgebase-librarian/references/laya-sdk.md`). Pass `--engine jev` only when remote
  Jev is intentionally selected. Engines never silently fall back to one another.
- Every segment gets a score record; missing SDK/model/score or out-of-range score is
  **fail-closed** (candidate rejected, `unavailable`/`error` status), never an implicit pass.
- Retention = `score ≥ threshold` **and** `score ≥ global_best − relative_margin`,
  plus a global **top-K floor** (`--top-k-floor`, recommended 5): when real evidence
  exists, the top-K docs always survive the cut. The relative cut exists because the
  local Laya distribution on prose is top-heavy (measured median ≈0.88, min ≈0.55);
  the floor protects question-critical mid-score documents (measured: an experiments
  section scoring 0.84 was cut at 0.854 — T1 2026-09-25). `abs_kept` preserves the
  raw-threshold view for audit.
- **Split-doc sibling completion** (default on): picking any `(part k of N)` document
  auto-includes its siblings (up to `--stem-max-parts`) — a matched paper brings its
  experiments/appendix parts that the question actually targets (measured: T4 kept
  part 1 while the hallucination section lived in part 2).
- **Post-judge stem expansion** (default on, `--no-stem-expansion` to disable): after
  the engine keeps a split document, its sibling parts are full-read and judged in a
  second pass (score memoization makes the repeat pass free). This is what saves
  enumeration questions whose answer sections sit outside both the description picks
  and the peeked heads (measured T1: the experiments part scored 0.83 from its head;
  full content scores it into the kept set). Bounded by `--expansion-cap` 40.
- `--lane-agreement` (opt-in): a document recalled by **both** independent lanes and
  scored at or above the absolute threshold is kept without the relative cut — two
  agreeing signals replace the distribution-dependent adjustment. Use it when the
  merged pool contains lexically-attractive distractors that inflate `global_best`
  (measured q2: a wrong dataset doc at 0.979 cut the gold at 0.868; the gold was
  lane=both and rescued by this rule).
- `--require-real` makes the CLI exit 2 unless `real_engine=true`; offline/injected
  scores are always labelled as such.

## ⚠️ NEVER list

| ❌ Don't | Why | ✅ Do instead |
|---|---|---|
| Run the lanes sequentially and call it parallel | Loses the latency win | `hybrid_search.py` (threads, separate MCP connections) |
| Dedup on `doc_path` alone | Same path can exist in two KBs | Key on `(kb_id, doc_path)` |
| Read a `lane=both` document again | Wasted I/O, duplicate work | Merge first; reread only `lane=vector` proposals |
| Judge a document that never got content | Description ≠ evidence | `unscanned` + honest report |
| Keep docs because the lane found them | Lanes propose, the engine disposes | Every segment through the real engine gate |
| Hide a failed lane | Partial coverage looks like full coverage | `status=partial` + `lanes.*.error` |
| Answer from unscored text or re-score kept docs | The engine verdict is final | Answer from ALL kept docs; zero kept = honest not-found |

## Quick rule reference
1. **Both lanes in parallel**, each with its own MCP connection (the script does this)
2. **Vector lane proposes, catalog lane reads** — no reads in the vector lane
3. **Merge on (kb_id, doc_path)**; `both` docs survive once with both scores
4. **One unified reread** for vector-only proposals before judging
5. **Every segment through the real engine** — fail-closed, relative cut on top of absolute
6. **Result list = deduplicated metadata** with lane provenance and both scores
7. **Answer from ALL kept docs only** — the engine gate is the verdict; report blind spots
