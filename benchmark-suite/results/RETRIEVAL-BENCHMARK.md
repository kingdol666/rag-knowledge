# Track R — Retrieval Benchmark

**Content-Adjudicated Retrieval vs. Reproduced Baselines**

> Generated 2026-09-16T22:04:11.494894+00:00 · git `db8e25a` · config hash `fe17f60fb7e09075` · every number read from real execution artifacts under results/.
This track answers one question: how does the system's retrieval compare against reproduced baselines (BM25, Dense, Dense+Rerank, RAPTOR, ITRG, Search-o1, DeepRead)? All methods share one corpus, one frozen query set, one MCP tool layer, one answering agent, and one independent judge. Every number below is read from execution artifacts under results/.

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

All eight systems run on the same corpus (BEIR SciFact, 148 documents), the same 30 frozen claims with official qrels, and the same MCP tool layer. Evidence is capped at a uniform 4,000-character budget; a shared agent answers from the evidence, an independent fresh-process agent grades against injected gold evidence (0–10), and a middle agent ranks anonymised answers.
**Table 2: Eight-system comparison on BEIR SciFact (30 queries, official qrels). Judge = independent agent 0–10 with gold evidence; Rank/Wins = middle-agent anonymous ranking.**

| Method | Hit@1 | Hit@5 | Recall@5 | nDCG@10 | MRR | Judge | Rank | Wins |
|---|---|---|---|---|---|---|---|---|
| qdcvr | 0.700 | 0.833 | 0.833 | 0.784 | 0.767 | 7.70 | — | **0** |
| dense_rag | 0.733 | 0.900 | 0.900 | 0.834 | 0.811 | **8.93** | — | **0** |
| dense_rag_rerank | **0.900** | **0.933** | **0.933** | **0.921** | **0.917** | 8.67 | — | **0** |
| raptor | 0.733 | 0.867 | 0.856 | 0.817 | 0.800 | 8.37 | — | **0** |
| itrg_refresh | 0.833 | **0.933** | **0.933** | 0.896 | 0.883 | 8.30 | — | **0** |
| itrg_refine | 0.733 | 0.900 | 0.900 | 0.845 | 0.816 | 8.53 | — | **0** |
| search_o1 | 0.800 | 0.900 | 0.844 | 0.811 | 0.839 | 8.70 | — | **0** |
| deepread | 0.567 | 0.733 | 0.694 | 0.635 | 0.639 | 8.13 | — | **0** |

*API-mode re-execution agreed with the offline matrix on 480/480 checked values (0 mismatches).*
Four retrieval channels over the production MCP path on BEIR SciFact: BM25 (stage-1 candidates), Two-stage hybrid (no content verification), Dense (BAAI/bge-m3, top-10), and QDCVR (full content-adjudicated pipeline). supp@1 = share of claims whose top-1 document covers ≥ 0.5 of claim content words.
**Table 3: Four-channel retrieval on BEIR SciFact (production MCP path).**

| Channel | Hit@1 | Hit@3 | Recall@5 | nDCG@10 | MRR | Supp@1 |
|---|---|---|---|---|---|---|
| bm25 | **0.833** | 0.833 | 0.800 | 0.808 | **0.838** | **0.67** |
| twostage | 0.733 | 0.833 | 0.867 | 0.811 | 0.792 | 0.57 |
| dense | 0.733 | **0.900** | **0.900** | **0.834** | 0.811 | 0.57 |
| qdcvr | 0.767 | 0.833 | 0.867 | 0.823 | 0.808 | 0.60 |

Bilingual in-house corpus: 20 frozen queries (EN/ZH/JA plus cross-KB) against three knowledge bases holding 16 documents, exercising domain-scoped routing.
**Table 4: Content-adjudicated two-stage retrieval vs. dense baseline on the bilingual in-house corpus.**

| Channel | Hit@1 | Hit@5 | Recall@5 | P@5 | MRR |
|---|---|---|---|---|---|
| staged | 0.800 | **0.950** | 0.908 | **0.210** | 0.860 |
| vector | **0.900** | **0.950** | **0.917** | 0.200 | **0.925** |

Component ablation of the QDCVR pipeline on the same query set; deterministic channels reproduce bit-for-bit across rounds.
**Table 5: Component ablation (BEIR SciFact, 30 queries).**

| Variant | Hit@1 | nDCG@10 | P@5 | MRR |
|---|---|---|---|---|
| qdcvr_full | **0.767** | 0.809 | **0.213** | 0.800 |
| verify_k1 | 0.733 | 0.796 | **0.213** | 0.783 |
| verify_k5 | **0.767** | 0.809 | **0.213** | 0.800 |
| no_verify | 0.733 | 0.796 | **0.213** | 0.783 |
| no_dedup | **0.767** | 0.809 | **0.213** | 0.800 |
| deep_t_0.20 | **0.767** | **0.832** | **0.213** | **0.810** |
| deep_t_0.35 | **0.767** | **0.832** | **0.213** | **0.810** |
| deep_t_0.50 | **0.767** | 0.821 | **0.213** | 0.806 |
| deep_t_off | **0.767** | **0.832** | **0.213** | **0.810** |

*Significance (E2): 48 paired comparisons, 0 significant after Holm correction at α = 0.05 (bootstrap 95% CIs reported per comparison).*
Multi-domain public benchmark: 50 HotpotQA dev questions whose supporting and distractor documents are partitioned into nine topic knowledge bases, forcing cross-base routing.
**Table 6: Multi-domain HotpotQA results (50 queries, 9 topic KBs).**

| Method | Hit@5 | nDCG@10 | Answer@1 |
|---|---|---|---|
| bm25 | 0.860 | 0.530 | 0.520 |
| two_stage | 0.960 | 0.825 | 0.500 |
| dense | **1.000** | **0.859** | 0.480 |
| qdcvr | 0.960 | 0.759 | **0.560** |

**Table 7: Routing oracle on HotpotQA: upper bounds of perfect domain scoping.**

| Policy | Channel | Hit@2 | Recall@2 | nDCG@10 | n |
|---|---|---|---|---|---|
| Always search all KBs | two_stage | 0.960 | 0.700 | 0.825 | 50 |
| Always search all KBs | dense | **0.980** | **0.730** | **0.859** | 50 |
| Oracle: single gold KB | two_stage | 0.940 | 0.670 | 0.772 | 50 |
| Oracle: single gold KB | dense | 0.940 | 0.670 | 0.761 | 50 |
| Oracle: best KB per query | two_stage | **0.980** | 0.690 | 0.795 | 50 |
| Oracle: best KB per query | dense | **0.980** | 0.690 | 0.784 | 50 |

Motivating case (rank-one repair): for claim `sf-002` (“4-PBA treatment decreases endoplasmic reticulum stress in response to general endoplasmic reticulum stress mar”), dense retrieval scores Hit@1 = 0, MRR = 0.5, while QDCVR scores Hit@1 = 1, MRR = 1.0 — content adjudication promotes the gold document to rank one.
