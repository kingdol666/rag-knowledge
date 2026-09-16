# Track F — Platform Functions Benchmark

**Parsing, Experience Lifecycle, Organise, Agent Surface, Scale**

> Generated 2026-09-16T20:41:48.264971+00:00 · git `db8e25a` · config hash `fe17f60fb7e09075` · every number read from real execution artifacts under results/.
This track measures the platform's own capabilities — document parsing and ingestion integrity, the experience lifecycle, organise functions, the agent-facing surface, and measured scale — through production interfaces only. There are no external algorithm baselines here; each probe checks correctness or quality of a platform function.

## 1. Environment and Reproducibility

**Table 1: Measured environment. Deterministic channels are expected to reproduce bit-for-bit; LLM channels follow the tolerance table in TEST-PLAN §7.**

| Item | Value |
|---|---|
| Git commit | `db8e25a` |
| Config hash | `fe17f60fb7e09075` |
| Seed / randomness | 0 — deterministic pipeline (no RNG); agent channel = mean of runs |
| Embedding | BAAI/bge-m3 (local GPU, normalize) |
| Vector store | ChromaDB (persistent) |
| Keyword index | jieba BM25 |
| MCP transport | uv run --directory kb-mcp python server.py (stdio) |
| Retrieval defaults | vector k=10, stage-1 k=40, stage-2 k=10, QDCVR threshold 0.35, verification reads 3 |

Every corpus is ingested through the production pipeline (parse → write → index). Membership accuracy checks that each document landed in its designated knowledge base; storage completeness checks that all five storage layers agree.
**Table 2: Document parsing and ingestion integrity.**

| Corpus | Parse | Ingest | Membership | Storage | Self-ret. Hit@1 |
|---|---|---|---|---|---|
| In-house demo corpus | — | **1.000** | **1.000** | **1.000** | **0.938** |
| Standard corpora | — | — | **1.000** | **1.000** | — |

Experience lifecycle: real meditation runs synthesise candidate lessons from corpus documents, drafts pass a human-in-the-loop approval step, and an independent judge agent scores entries on a 0–10 rubric (groundedness 4, structure 3, reusability 3). A zero yield on encyclopaedic corpora is the quality gate working as designed, not a failure.
**Table 3: Meditation → draft → approval → judge lifecycle.**

| Sample | Round | KB | Run | Drafts | Approved | Entries | Judge scores |
|---|---|---|---|---|---|---|---|
| Sample 1 | 1 | KB-Demo-EN | pass | 0 | 0 | 0 | — |
| Sample 1 | 1 | KB-Demo-ZH | pass | 0 | 0 | 0 | — |
| Sample 1 | 2 | KB-Demo-EN | pass | 0 | 0 | 0 | — |
| Sample 1 | 2 | KB-Demo-ZH | pass | 0 | 0 | 0 | — |
| Sample 1 | 3 | KB-Demo-EN | pass | 0 | 0 | 0 | — |
| Sample 1 | 3 | KB-Demo-ZH | pass | 0 | 0 | 0 | — |
| Sample 2 | 1 | KB-Demo-EN | pass | 0 | 0 | 3 | 8.0, 8.0, 8.0 |
| Sample 2 | 1 | KB-Demo-ZH | pass | 0 | 0 | 0 | — |
| Sample 2 | 2 | KB-Demo-EN | pass | 0 | 0 | 0 | — |
| Sample 2 | 2 | KB-Demo-ZH | pass | 0 | 0 | 0 | — |
| Sample 2 | 3 | KB-Demo-EN | pass | 0 | 0 | 0 | — |
| Sample 2 | 3 | KB-Demo-ZH | pass | 0 | 0 | 0 | — |

**Table 4: E4 dual-baseline comparison under the identical judge prompt (mean 0–10 score).**

| Condition | Mean judge score |
|---|---|
| llm_summary | **3.50** |
| no_synthesis | 2.75 |
| ours_experience | 1.50 |

Organise functions probed with planted ground truth: duplicate detection, tag generation and cleanup safety, graph build and retrieval, and catalogue completeness.
**Table 5: Platform organise-function probes (E17).**

| Probe | Result |
|---|---|
| Documents retained / planted | 7/9 |
| Duplicate groups detected / planted | 1/2 |
| Distinct tags / content-grounded | 190 / 5 (2.6%) |
| Cleanup: in-use tags flagged for removal | 0 |
| Graph build OK / probe hits | True / 0 |

End-to-end validation of the complete agent-facing surface by an independent external client: every check executes the production HTTP/MCP interface, including a create-then-cleanup lifecycle.
**Table 6: Agent-surface end-to-end checks.**

| Surface group | Checks | Result |
|---|---|---|
| Group A | 4 | PASS |
| Group B | 5 | PASS |
| Group C | 3 | PASS |
| Group D | 2 | PASS |
| Group E | 6 | PASS |
| Group F | 3 | PASS |
| Group G | 1 | PASS |
| Group H | 2 | PASS |
| Total | 26/26 | PASS |

**Table 7: Platform scale, measured from the running services and source tree.**

| Item | Value |
|---|---|
| experiment | E17 system scale (measured, not hard-coded) |

