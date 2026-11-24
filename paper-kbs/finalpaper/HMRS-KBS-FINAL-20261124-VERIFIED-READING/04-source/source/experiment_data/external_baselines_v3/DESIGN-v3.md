# External Baselines v3 — Design (fixed before any execution)

Extends the 2026-11-20 answer-quality bench (`review/baseline-quality-20261120/`)
with external research systems that the manuscript's Table 1 positions
qualitatively. Goal: same-question quantitative comparison on **retrieval /
answer quality**, not a re-implementation of any system.

## Systems

| Arm | System | Repo | Role |
|---|---|---|---|
| hmrs-agent | HMRS real tiered agent | this platform | reference (v2 rows reused) |
| bm25 / dense / rrf | classic baselines | v2 scripts | reference (v2 rows reused) |
| raptor | RAPTOR tree retrieval | parthsarthi03/raptor | retrieval-mode arm |
| graphrag | Microsoft GraphRAG (local search) | microsoft/graphrag | retrieval-mode arm |
| lightrag | LightRAG (mix mode) | HKUDS/LightRAG | retrieval-mode arm |
| deepread | DeepRead structure-aware agentic search | Zhanli-Li/DeepRead | native agentic arm (+retrieval mode only if the repo exposes the read sections) |
| eprag | EPRAG | no public implementation found (2026-11-21 search) | **excluded from runs**; stays qualitative in Table 1 |

## Fixed protocol (parity with v2)

1. Corpus: exactly the exported 100-paper corpus (328 parts / 9,504 chunks from
   `passages.jsonl`), questions BQ01–BQ10 unchanged.
2. Generation: retrieval-mode arms use the SAME one-shot prompt template, the
   SAME endpoint (`6789/api/claude/chat`), SAME engine/model
   (`ustc/deepseek-flash`), kbEnhanced=false, as v2 baselines.
3. Context budget: retrieval-mode arms capped to ≤12 units × 800 chars for the
   prompt. The raw retrieval payload size BEFORE capping is recorded per call
   and disclosed, so capping cannot silently shrink a system's evidence.
4. Embeddings: external systems use the SAME embedding model family as the
   dense baseline and platform — BGE-M3, served locally by `emb_shim.py`
   (OpenAI-compatible `/v1/embeddings`, loopback only) from the platform's own
   `models_cache` snapshot. No system uses a different retriever-side embedder.
5. Indexing-time LLM (RAPTOR summaries, GraphRAG entities/communities,
   LightRAG extraction, DeepRead parsing/agent): **ustc/deepseek-flash**
   (2026-11-21 user directive; original plan was a local model, pivoted BEFORE
   any metered indexing after the local LM Studio build was found to cap
   contexts at 8192 tokens). All systems now index AND generate with the same
   model the paper's other arms use. Credentials are read from cc Switch's
   local DB at runtime; no secret is stored in the repository.
6. DeepRead native arm: answers produced by its own pipeline (LLM identity as
   configured, disclosed). Its arm is marked generator-different in every table.
7. Judging: ONE blind pass over ALL arms (v2 rows merged with new rows;
   8 arms × 10 questions) with `03_judge.py` unchanged (same rubric, fresh
   random mapping, judge = local gpt-oss-20b temperature 0). Judge never sees
   arm names or system identity.
8. Deterministic metrics alongside judging: gold-id presence and gold-keyword
   coverage in the answer text (as v2), plus NEW retrieval-level
   gold-document containment: whether any pre-cap retrieved source belongs to
   the gold paper (matched by arXiv id in doc_path). For agent-style arms
   without a source list this is n/a and disclosed.
9. Per-call records: wall time, latency, answer text, cost, http status,
   errors preserved verbatim; failures stay failures.

## Cost gate

Before any metered full run: 1-question smoke per new arm; estimated total
cost printed and compared against the ustc channel budget. Calibrated from
cc Switch usage history (~$4/M input, ~$15/M output on this channel): the
full indexing + grid plan is estimated at roughly $35-45 total; GraphRAG runs
the official fast (NLP-extraction) variant first to cap cost. Indexing and
generation call volumes are logged per arm; the report itemizes measured
cost per arm from the recorded responses.

## Honesty rules

- No re-implementation of excluded systems; EPRAG is reported as "no public
  implementation" with the search date.
- Single run, ten questions, one judge model — same scope limits as v2,
  restated in the report.
- Report answers verbatim; no tuning of any system to favor HMRS; if an
  external system scores higher, that is the result and goes in the report.
- All raw artifacts (answers/judgments/mappings/indexing logs) are kept
  verbatim; nothing is post-edited.

## Addendum (2026-11-22): additional judge batches + uniform-corpus round

- **Batch 3 (v4)** and **Batch 4 (unified)**: single ZCode-subagent judge,
  same rubric anchors (byte-identical dimension definitions, verified by
  `adapters/verify_all.py`), fresh per-question letter mappings
  (seeds 20261122 / 20261124), per-dimension written justifications required.
  Both judged the SAME 80 answers in `answers-v3.jsonl` — enabling
  cross-judge agreement analysis on identical texts.
- **Scope disclosure stays attached to every number**: at answer-generation
  time RAPTOR/GraphRAG indexed a 30-part gold subset and DeepRead 23/96
  documents (favorable to externals); LightRAG and the four v2 arms ran on
  the full 328-part corpus. The table in report-v3.html (SCOPE_AT_GEN)
  carries the evidence per arm.
- **Uniform-corpus round (in flight)**: GraphRAG full-328 index rebuilt
  (18,551 entities / 2,077 text_units; the LanceDB dimension error at the
  final pipeline step is known and non-blocking for the entity-centric
  retrieval path); DeepRead re-parsed 96/96; RAPTOR full tree under rebuild
  on ustc/deepseek-flash summaries with escalating 429 backoff. The follow-up
  rerun writes `answers-v5-uniform.jsonl` (`run_arm_grid.py --out/--round-tag`),
  judged into `judgments-v5-sub.jsonl`, reported by `report_v5.py`.
- Reproduction manual: `PIPELINE.md`. One-shot integrity gate:
  `python -B adapters/verify_all.py` (17 checks).
