# E-B — Organization / partitioning ablation (live corpus)

**Run id:** `exp12-20261012-full` · **n = 10 questions** (4 conditions × 10 = 40 retrieval cells, **no LLM calls**)
**Script actually run:** `paper-kbs/experiments/exp12_partition_ablation.py`
**Aggregate JSON:** `paper-kbs/experiments/results/exp12_partition_ablation.json` (10-question version — this is the reportable one)
**Superseded n = 2 file, kept as a record:** `paper-kbs/experiments/results/exp12_partition_ablation_n2.json`
**Raw per-cell JSONs:** `paper-kbs/experiments/results/exp12/exp12-20261012-full/cell_QK01..QK10.json` + `env_naming.json`, `env_router_vs_prefix.json`
**Console transcript:** `paper-kbs/experiments/results/exp12/exp12-20261012-full.console.log` (3476 bytes, the real measuring run)

---

## (a) What was compared, and what was held constant

The partition is what is under test: all four conditions run in the **same tool family** (`kb_search_vector`) and differ **only in search scope**.

| Condition | Scope |
|---|---|
| `pinned-gold` | Restricted to the gold document's own library — `kb_search_vector(query, kb_id=<gold's library>)`. The "routing was correct" case. |
| `pinned-other` | Restricted to **one deterministically chosen other** library — the alphabetically-next library name among the five, excluding the gold's own. This is the **cost of a routing mistake**. |
| `flat` | **No `kb_id` restriction** — cross-library, i.e. what a single flat library would give. |
| `catalog-only` | The **catalog/description lane**: `kb_list` + `kb_get_documents` (names + descriptions only, no content search), ranked by query↔description token overlap. What the partition buys on the discovery path. |

**Held constant:** same 10 questions, same live corpus, same retrieval tool and parameters (`kb_search_vector`, `top_k=10`, **`score_threshold=0.0`**, `slim=True`), and the **same gate applied identically to every candidate list** (`kb_laya_judge`, `criterion="auto"` → server-resolved `"evidence"`, `threshold=0.5`) so that "kept after gate" is comparable across conditions.

**Why `score_threshold=0.0` and not the platform default 0.35:** a non-zero threshold would make an empty result ambiguous between "this scope genuinely contains nothing" and "the threshold cut everything". At 0.0 every returned document was returned on merit, so `pinned-other` scoring 0.0 hit@5 is a real routing-miss result rather than a threshold artefact. The consequence is that candidate counts here are **not** directly comparable to E-A's vector lane, which did use `score_threshold=0.35`.

**Denominators (as requested):** QK09 (`unanswerable`) and QK10 (`outofcorpus`) have **no gold document in the corpus** — QK09's and QK10's gold lists are empty and gold resolution failed with `"gold arXiv id not found in any library"`. **They are excluded from all hit/rank denominators** rather than counted as misses (`n_graded_gold_in_corpus = 8`, `excluded_qids = ["QK09","QK10"]`). The all-10 rate that would count them as misses is reported alongside, explicitly labelled.

`pinned-other` assignment (deterministic, alphabetical next library): QK01→工程与能源, QK02→经济与社会, QK03→生命科学与医学, QK04→工程与能源, QK05→经济与社会, QK06→计算机与人工智能, QK07→工程与能源, QK08→计算机与人工智能.

---

## (b) Headline numbers — verbatim from the JSON

`aggregate.conditions[*]`, **n_graded = 8** (gold present in corpus):

| condition | hit@5 | hit@10 | gold_rank_mean | n_candidates_mean | kept_after_gate_mean | latency_s_mean |
|---|---|---|---|---|---|---|
| `pinned-gold` | **1.0** | **1.0** | **1.0** | **2.75** | **2.75** | **0.462** |
| `pinned-other` | **0.0** | **0.0** | **null** | **7.125** | **6.875** | **0.487** |
| `flat` | **1.0** | **1.0** | **1.0** | **2.5** | **2.5** | **0.3** |
| `catalog-only` | **1.0** | **1.0** | **1.75** | **235.75** | **11.375** | **0.0** |

All-10 rate, counting the two gold-absent questions as **misses** (reported for completeness, **not** the headline):
`pinned-gold` hit@5 = 0.8 · `pinned-other` hit@5 = 0.0 · `flat` hit@5 = 0.8 · `catalog-only` hit@5 = 0.8 (hit@10 identical in every condition).

Other aggregate fields: `n_questions = 10`, `n_graded_gold_in_corpus = 8`, `n_excluded_gold_not_in_corpus = 2`, `wall_clock_s = 394.0`, `catalog_library_top1_routing = {"hits": 6, "n": 8}`.

### Per-question gold ranks

| qid | gold arxiv | gold library | `pinned-gold` | `pinned-other` | `flat` | `catalog-only` |
|---|---|---|---|---|---|---|
| QK01 | 1706.03762 | 计算机与人工智能 | 1 | null | 1 | 2 |
| QK02 | 1602.01876 | 生命科学与医学 | 1 | null | 1 | 1 |
| QK03 | 1606.00335 | 工程与能源 | 1 | null | 1 | 1 |
| QK04 | 2209.15032 | 计算机与人工智能 | 1 | null | 1 | 2 |
| QK05 | 2508.05896 | 生命科学与医学 | 1 | null | 1 | 2 |
| QK06 | 1503.07557 | 自然科学与地球科学 | 1 | null | 1 | 1 |
| QK07 | 2608.05850 | 计算机与人工智能 | 1 | null | 1 | 2 |
| QK08 | 2409.13934 | 自然科学与地球科学 | 1 | null | 1 | 3 |
| QK09 | — (none) | — | null | null | null | null |
| QK10 | — (none) | — | null | null | null | null |

Per-question candidate counts / kept-after-gate (all four conditions) are in `aggregate.per_question[*].rows[*].n_candidates` / `.kept_after_gate`.

---

## (c) Every null and unfavourable result — stated plainly

1. **`pinned-other` scored 0.0 hit@5 and 0.0 hit@10 on all 8 graded questions.** A routing mistake never recovered the gold document. That is the intended "cost of a mistake" result, and it is absolute here.
2. **The partition bought nothing measurable on the retrieval path: `flat` (no `kb_id` restriction, cross-library) is exactly as good as `pinned-gold`** — hit@5 1.0, hit@10 1.0, gold_rank_mean 1.0 on every question. Gold rank 1 in both. **On this corpus, scoping the search to the correct library is not what makes the gold document rank first.**
3. **`flat` returned *fewer* candidates than `pinned-gold`** (2.5 vs 2.75 mean) — cross-library search did not even add distractor documents. With `top_k=10` chunks the hits collapse onto 2–3 documents, so the candidate cap of 12 was never binding in either condition. **This experiment cannot show a partition cost on the retrieval path because the retrieval path never over-retrieved in the first place.**
4. **`catalog-only` reaches the same hit@5/hit@10 (1.0/1.0) as the content-search conditions — but only by ranking 235.75 candidates on average, ~86× more than `pinned-gold`'s 2.75,** and it ranks the gold worse (gold_rank_mean **1.75** vs **1.0**; gold at rank 2 or 3 on 5 of 8 questions). Its `kept_after_gate_mean` of 11.375 is an artefact of the 12-document cap, not of gate selectivity.
5. **`catalog_library_top1_routing = {"hits": 6, "n": 8}`** — ranking the five library *descriptions* against the query puts the correct library first only **6 out of 8** times. The discovery path misroutes 25% of the time on gold-bearing questions; `pinned-other` shows the penalty for that.
6. **The gate kept essentially everything in every condition.** `kept_after_gate` ≈ `n_candidates` throughout (`pinned-gold` 2.75→2.75, `flat` 2.5→2.5, `pinned-other` 7.125→6.875). The verification gate is not doing scoping work here — consistent with the E-A finding.
7. **Two questions yielded no gold whatsoever** — QK09 (`unanswerable`) and QK10 (`outofcorpus`), both `"gold arXiv id not found in any library"` (`aggregate.failures`). All four conditions returned `null` for every metric on them. They are not evidence about partitioning; they are recorded as excluded, not as successes.
8. **Latency differences are within noise and favour no condition**: 0.462 s (`pinned-gold`) vs 0.487 s (`pinned-other`) vs 0.3 s (`flat`) vs ~0.0 s (`catalog-only`, which does no vector search at all).

### Environment observations (each with its exact call)

**(a) Document naming convention — the topical prefix IS still present. This is a label leak.**
Call: `kb_get_documents(kb_id=<each of the 5 libraries>, lightweight=True)`
- `n_document_parts = 322`, and **`parts_with_domain_double_underscore_prefix = 322`** → `prefix_leak_fraction = 1.0`.
- Every stored part name still carries the full `{domain}__{arxiv_id}__{slug}` prefix, e.g. `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md`.
- **165 of 322 parts carry a doubled `.md` suffix** (`...conte.md.md`, `...need.md (part 1 of 2).md`), e.g. `计算机与人工智能/artificial-intelligence__2504.16021__navigating-the-state-of-cognitive-flow-conte.md.md`.
- `distinct_prefixes = 26`. Histogram: large-language-models 32, mathematics 30, quantum-physics 20, nlp 19, genomics 19, economics 19, artificial-intelligence 17, databases 17, clinical-medicine 17, statistics 14, chemistry 14, climate-science 12, neuroscience 10, robotics 9, medical-imaging 9, materials 9, speech 8, astronomy 7, seismology 7, power-systems 7, social-networks 5, oceanography 5, finance 5, immunology 4, agriculture 4, gravitational-physics 3.

**(b) Per-library document counts** (`environment.per_lib_counts`; matches the brief's figures): 计算机与人工智能 **131** · 自然科学与地球科学 **75** · 生命科学与医学 **53** · 工程与能源 **39** · 经济与社会 **24** = **322 parts**.

**(c) Router assignment vs filename topical prefix — 95/96 papers agree.**
Call: `kb_get_documents(kb_id=<each of the 5 libraries>, lightweight=True) + glob(benchmark-suite/data/papers/*.pdf)`
- `n_parts_sampled = 322`, `n_papers = 96`, **`papers_matching_majority_library = 95` / `papers_total = 96`, `paper_agreement_fraction = 0.9896`** (sample size exceeds the requested ≥30).
- **Only one topical prefix spans more than one library**: `mathematics` → 自然科学与地球科学 7, 工程与能源 23. Every other prefix maps to exactly one library.
- Disk cross-check: `checked = 96`, `agree = 96`, `missing_on_disk = []` — the arXiv id's disk filename prefix always equals the live stored prefix.
- **Caveat that must travel with this number (as requested): the topical prefix is a leak — it is embedded in the document name, so the stored prefix is not an independent signal of what the router decided.** The count above only shows that the *stored name* still carries the filename's domain and that the library assignment is consistent with it 95/96 times; it does **not** demonstrate that the router independently inferred the domain. Agreement between two copies of the same leaked label is not evidence of routing skill.

---

## (d) Protocol deviations and limitations

- **No deviations were recorded by the run itself:** `protocol_deviations = []`. In particular, no `kb_id` filter failed or was ignored, and the two gold-resolution failures were recorded in `failures` rather than silently dropped.
- **Tool substitution relative to the brief (stated explicitly):** the brief allowed `kb_search_two_stage` **or** `kb_search_vector` for the pinned conditions and `flat`. This run used **`kb_search_vector`** in all four conditions, deliberately, so that the *only* variable is search scope. `kb_search_two_stage` adds a BM25 stage-1 whose cross-library behaviour differs from its single-library behaviour, which would have confounded scope with tool. The cost is that these numbers describe the **vector lane**, not the two-stage lane.
- **The E-A deviation does not apply here** — E-B never referenced `kb_hybrid_search`.
- **`flat` is defined as `kb_search_vector(kb_id="")`.** This is *not* a genuinely flat single library: the live platform holds **20 KBs**, of which only the five corpus libraries are the 100-paper corpus (the rest include unrelated content such as `aw-industrial`, 29 docs). `flat` therefore searches the five corpus libraries *and* 15 unrelated ones. Since it still scored 1.0/1.0, this only strengthens the finding that cross-library search did not hurt.
- **Aggregation provenance:** `exp12_partition_ablation.json` was rebuilt from the frozen `cell_QK01..QK10.json` via `python paper-kbs/experiments/exp12_partition_ablation.py --reaggregate paper-kbs/experiments/results/exp12/exp12-20261012-full` (**no API calls**) to add the gold-only denominators. The retrieval measurements themselves are the original run's, unmodified; only the aggregation changed.

---

## (e) What this does NOT show

It does **not** show that the partition *helps* retrieval, and it does not show that it *hurts*: `flat` matched `pinned-gold` on every metric. It shows only that **the retrieval path never over-retrieved**, so there was no cost for the partition to remove.

It does **not** validate the router. The 0.9896 agreement figure is computed against a **label that leaks into the document name**, so it is a consistency check, not an accuracy measurement — see the caveat in (c). The only *independent* routing signal reported here is `catalog_library_top1_routing = 6/8`, which is worse than the leak-based figure and rests on 8 questions.

It does **not** generalize beyond: **8 graded questions + 2 excluded**, **one query per question** (no paraphrase or query-rewrite robustness), **one retrieval tool** (`kb_search_vector`, `top_k=10`, `score_threshold=0.0`) at **one parameter setting**, **one deterministic `pinned-other` rule** (alphabetical next — a different rule may misroute to a topically adjacent library, which is the more realistic failure and is *not* what was measured), and a **100-paper / 322-part corpus small enough that a top-10 vector search returns only 2–8 documents per library**, which is precisely why the partition's cost could not appear. A larger corpus, a higher `top_k`, or a recall stage that actually over-retrieves is required before any cost/benefit claim about the 5-library partition can be made.

---

## Evidence provenance

- The console file `exp12-20261012-full.console.log` is the **verbatim stdout of the original measuring run** (394.0 s, all 10 questions, retrieval only). Its final summary lines still use the **pre-reaggregation** denominators (`n=10`, `hit@5=0.8`, i.e. counting the two gold-absent questions as misses) because it predates the `--reaggregate` pass; the per-question lines above them are the raw measurements and are unchanged. **Only the denominators and the reported rates changed in the aggregate** — no retrieval measurement was recomputed, and no LLM call was ever made in this experiment.
- Read-only with respect to knowledge-base content throughout: no document or library was created, updated, deleted, moved, re-indexed, re-tagged or re-parsed. Only `kb_list`, `kb_get_documents`, `kb_search_vector` and `kb_laya_judge` were called.
- `env_naming.json` and `env_router_vs_prefix.json` hold the raw observation payloads (including the full 96-row disk cross-check) behind observation (c).
