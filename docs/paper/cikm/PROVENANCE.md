# Provenance Record — what this paper can and cannot reproduce

> Created 2026-09-13 during the revision that followed the CIKM panel review
> (`EDITORIAL-DECISION.md`). Checked automatically by `provenance_audit.py`.
>
> **This document exists because the paper's original main results turned out to
> have no producing script.** The audit that found this is reproducible and the
> gate now fails the build if it recurs.

---

## 1. The finding

An earlier draft led with a 50-query benchmark reporting a false-positive rate
falling from `0.635` to `0.348`, the best P@1 (`0.457`), the best MRR (`0.477`)
and a significant advantage over a hybrid baseline (`p=0.001`). Two tables, one
figure and every headline number in the abstract came from it.

**That benchmark has no producer.** An exhaustive search over 417 code files for
any writer of `cikm_summary.json`, `figure1_comparison.json`, `table1_main.tex`,
`table3_ablation.tex` or `benchmark-web/backend/results/v4/benchmark_report.json`
returns **zero hits**. The only thing in that directory that renders them,
`make_benchmark_html.py`, reads them — it does not produce them.

The one benchmark runner present in that tree, `benchmark-web/backend/run_benchmark.py`,
is not the source either. It is a standalone script that:

* hard-codes ~30 synthetic document abstracts in Python (`add(...)` calls),
* declares itself *"Standalone benchmark runner — BM25 + QDCVR comparison. No
  BGE-M3 dependency. Uses rank_bm25 directly."*,
* computes **only BM25** (`bm25.get_scores`) — there is no vector index, no
  content adjudication and no LLM anywhere in it,
* defines relevance as *the query's expected domain label matching the returned
  document's domain label*,
* writes `results/aggregate.json`, not `cikm_summary.json`.

So the numbers that led the paper were neither produced by the deployed system
nor by the one script that resembles a benchmark.

## 2. Four compounding defects in the same artefact family

Found in the same audit, any one of which would independently block submission:

| # | Defect | Evidence |
|---|---|---|
| 1 | The component study ran on **8 queries**, not the 50 its caption implied | `docs/paper/benchmark/paper-tables/table3-ablation.tex`: *"Notes: 8 benchmark queries; top-k = 5"* |
| 2 | The reported significance was a paired *t*-test on **Recall@5**, and **all four *t*-statistics were negative** — a deficit presented in a column that read as an advantage | `results/v4/benchmark_report.json`: `"metric": "Recall@5"`, `n_paired: 46`, `t = −2.14 / −2.12 / −3.49 / −2.28`, `d = −0.32 … −0.51` |
| 3 | FPR is defined over **returned** documents, so a query returning nothing scores zero — abstention is rewarded without limit | metric definition; 22 empty result lists, all from the proposed configuration |
| 4 | One table statistic was a **hard-coded literal that mislabelled a mean as a median** | `make_assets.py` line 344 (`Median judge score & 3.5`); the actual median is `3.0` |

## 3. Verified provenance map

`provenance_audit.py` checks this table on every run and exits non-zero if a
producer disappears.

### Traceable — cited by the paper

| Artefact | Producer | Write site | Calls the live system? |
|---|---|---|---|
| `module_a_ingestion_r1.json` | `benchmark-suite/scripts/01_ingestion.py` | `RESULTS / …` | yes (MCP) |
| `module_a_std2_r1.json` | `benchmark-suite/scripts/21_std2_ingest.py` | `RESULTS / …` | yes (MCP) |
| `module_b_retrieval_r2.json` | `benchmark-suite/scripts/02_retrieval.py` | `RESULTS / f"module_b_retrieval{OUT_SUFFIX}_r{ROUND}.json"` | yes (`kb_search_two_stage`, `kb_search_vector`) |
| `module_b_std2_r2.json` | `benchmark-suite/scripts/22_std2_retrieval.py` | `RESULTS / f"module_b_std2_r{ROUND}{suffix}.json"` | yes (same tool layer) |
| `module_c_experience_r2.json` | `benchmark-suite/scripts/03_experience.py` | `RESULTS / …` | yes (MCP) |

Note: these scripts write via **computed** filenames, which is why a naive
exact-name grep finds nothing and why an earlier heuristic-based audit wrongly
reported "0 missing". The map above is hand-verified by reading each write site.

### Withheld — removed from the paper

| Artefact | Former use | Producer |
|---|---|---|
| `benchmark-web/backend/results/cikm/cikm_summary.json` | Table 4 (main), Figure 3 (FPR), Table 5 (ablation) | **none found** |
| `benchmark-web/backend/results/cikm/figure1_comparison.json` | Figure 3 source | **none found** |
| `benchmark-web/backend/results/cikm/table1_main.tex` | Table 4 pre-rendered | **none found** |
| `benchmark-web/backend/results/cikm/table3_ablation.tex` | Table 5 pre-rendered | **none found** |
| `benchmark-web/backend/results/v4/benchmark_report.json` | §7.2 statistics | **none found** |

The withheld files are retained in `data-snapshot/` under `"withheld"` in
`MANIFEST.json` — kept as evidence of what was withdrawn, not cited.

## 4. What changed in the paper

* Abstract and contributions **C1/C2 rewritten** to rest only on traceable
  evidence. C1 no longer claims a false-positive-rate improvement.
* **§7.3 (main results) replaced** with the two traceable benchmarks (BEIR
  SciFact, in-house corpus) and an explicit statement that the two jointly support
  only "verification re-orders the top of the list".
* **§7.5 added**: a first-class account of the provenance failure, because it is
  the most transferable thing in the paper.
* **No significance claim anywhere.** `Statistics` now states that no test
  statistic, *p*-value or confidence interval is quoted because none was computed
  on a reproducible protocol.
* **Discussion** rewritten: the distractor hypothesis is stated as a hypothesis
  with no traceable support, and the provenance failure is reported as a finding.
* `make_assets.py` **trimmed** so it cannot re-emit the withheld assets.

## 5. The gate

```bash
python provenance_audit.py     # exit 1 if any cited artefact loses its producer
python make_assets.py          # emits only provenance-verified assets
latexmk -pdf main.tex
```

**Rule going forward:** if you cannot name the script that wrote a table, you do
not have the table. Every benchmark run should write to a uniquely named,
immutable directory and record the git commit, configuration hash and seed inside
the result file.

## 6. What this costs the paper

The paper is weaker in headline numbers and sound. What remains measurable:

* ingestion integrity — membership and completeness `1.000` across two corpora
  and five storage layers;
* content adjudication's *cost* — $13\times$ latency in-house, mean characters
  read per query;
* its *mixed* ranking effect — Hit@1 up on the public benchmark, P@5 up
  in-house, Hit@1/Recall@5/MRR down in-house and nDCG down on the public set;
* the agent surface — 26/26 checks passing from the committed external client
  `benchmark-suite/scripts/80_e2e_surface.py` (the earlier 73/88-check figure had
  no committed producer and is no longer cited);
* the multi-domain benchmark — HotpotQA partitioned into nine topic bases, where
  adjudication is significantly *worse* than its own recall stage on full ranking
  but best on answer@1;
* a negative and unstable result on experience synthesis — heuristic-extraction
  mean `3.5/10`; the generative path produces entries in 3 of 9 state-reset
  rounds, and is judged `7`–`9/10` when it produces.

The central claim — that domain scoping plus content adjudication reduces false
positives in heterogeneous corpora — is **not** among them, and `TODO-18` records
the single experiment (a $2\times2$ scoping × adjudication factorial on a
public multi-domain corpus) that would decide it.

## 2026-09-15-a snapshot update (Stage D / E16-E17)

Added to the frozen snapshot, each with a committed producer:

| Artefact | Producer |
|---|---|
| `deepread_matrix.json` | `benchmark-suite/algorithms/run_matrix.py` (E16: 8-system matrix, 30 SciFact queries, retrieval metrics + omp-RPC answers + independent judge) |
| `api_matrix.json` | `benchmark-suite/scripts/27_api_flow_test.py` + `algorithms/api_server.py` (E16b: HTTP-driven rerun, 480/480 byte-identical consistency checks, middle-agent anonymised ranking) |
| `platform_ops_eval.json` | `benchmark-suite/scripts/26_platform_ops_eval.py` (E17: organise functions, planted-truth probe) |
| `deepread_matrix_replay.json` | cache-replay rerun of run_matrix (summary layer identical to `deepread_matrix.json`) |

Deviations from the reproduced paper's settings are enumerated in
`benchmark-suite/algorithms/REPRODUCTION-NOTES.md`.

---

## Snapshot 2026-09-16-a (post-freeze re-execution audit)

2026-09-16 的全轨重跑复现审计（F/R 两轨按 committed pipeline 重跑 + 逐项机器
对比）之后，快照升级为 `2026-09-16-a`：

* 2026-09-15-a 的全部引用字节**原样再冻结**（module_b_retrieval_r2 的 live
  文件在后续重跑中漂移至 0.75/0.90，论文引用的冻结值 0.80/0.90 以快照字节
  为准 —— 这正是本快照机制存在的理由）。
* 新增引用产物：
  - `hotpot_main_2.json`（run-20260914T053707Z）— tab-multidomain 之源，
    producer: `60_hotpot_build.py` + `61_hotpot_eval.py`；
  - `real_scenario_run1.json` / `real_scenario_run2.json`（E19 真实场景两次
    全量运行，producer: `29_real_scenario_test.py`）；
  - `real_scenario_comparison.json`（47/48 检索位置一致、judge mean |Δ|=0.417，
    producer: `32_real_scenario_report.py --compare`）。
* 审计结论（论文 §Reproducibility "Post-freeze re-execution audit" 段）：
  E16 矩阵 9,837/9,837 字段逐位一致；功能轨聚合层 0 差异；E19 两次运行
  97.9% 检索位置一致。E8 绝对值依赖向量库构建时状态（chromadb 段损坏缺陷，
  触发器与规避已文档化），排序结论在每次健康重跑中复现。
