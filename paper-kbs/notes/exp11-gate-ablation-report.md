# E-A — Verification-gate ablation (end-to-end)

**Run id:** `exp11-20261012-full` · **n = 10 questions** (3 arms × 10 = 30 answered+graded cells)
**Script actually run:** `paper-kbs/experiments/exp11_gate_ablation.py`
**Aggregate JSON:** `paper-kbs/experiments/results/exp11_gate_ablation.json`
**Raw per-cell JSONs:** `paper-kbs/experiments/results/exp11/exp11-20261012-full/cell_QK01..QK10.json` (+ `cand_QK01..QK10.json`, `repairs.json`)
**Console transcript:** `paper-kbs/experiments/results/exp11/exp11-20261012-full.reproduce.console.log`
(see *Evidence provenance* at the end — this is a labelled reproduction pass, not the original stdout).

---

## (a) What was compared, and what was held constant

Three arms, all answered and graded by the **same** pipeline. Only the evidence that
reaches the closing model differs.

| Arm | Evidence given to the closing model |
|---|---|
| `C-nogate` | The **frozen shared candidate set**, in fusion order (cap 12 docs) — no verification gate. |
| `C-judge` | The `kb_laya_judge` **survivors** over that same frozen candidate set, in survivor order. |
| `C-judge-seg` | The judge's own returned **merged `evidence_pack`** (server-side content read), truncated to the same 4000-char budget. Diagnostic third arm. |

**Held constant across all three arms:**

- **Same 10 questions** — `benchmark-suite/data/papers/qa_quick10.json`, strata: 6× `single`, 1× `distractor` (QK07), 1× `crosskb` (QK08), 1× `unanswerable` (QK09), 1× `outofcorpus` (QK10).
- **Same corpus** — the live 100-paper / 322-part arXiv corpus, content-routed into 5 libraries (计算机与人工智能 b1199132-…, 自然科学与地球科学 1e6199ea-…, 生命科学与医学 b28f0a25-…, 工程与能源 8fa4db59-…, 经济与社会 f5770687-…).
- **Same frozen candidate set.** The recall/merge stage runs **once per question** and is written to `cand_<qid>.json`; both gated and ungated arms consume that identical list. The gate is the *only* difference between `C-nogate` and `C-judge`.
- **Same closing channel** — `chat_tracks.answer_closed_book` (platform chat API, `engine` pinned to `claude` at `chat_tracks.py:243`, `allowed_tools=[]`, `max_turns=1`, closed-book prompt, no tools).
- **Same evidence budget** — 4000 chars.
- **Same grader** — identical grader prompt for every arm, 0–5 against `gold_points` + `gold_keywords`, answer truncated to 4000 chars.
- **Same session** — both conditions ran in one process, one run dir, back to back.

**Warm-up:** executed before measurement (`--skip-warmup` not used). The gate is fail-closed, so warm-up used a **real** document path; it reported
`{"done": true, "real_doc": "economics__1911.06206__bayesian-state-space-modeling-for-analyzing (part 1 of 5).md", "seconds": 10.7, "judge_status": "ok", "judge_real_engine": true, "judge_engine": "laya", "judge_backend": "laya_sdk", "judge_errors": [], "judge_fetch_errors": []}`.
So the engine was live and real (`real_engine: true`) before any cell was measured — no cold-start contamination.

**Gate configuration:** `kb_laya_judge`, `criterion="auto"` **requested** (the server **resolved** it to `"evidence"` on all 10 questions — verified in every `cell_*.json → judge.criterion`), `threshold=0.5`, **reference mode** (`documents` passed as `{"kb_id","doc_path"}` refs so the server fetches bodies itself), `include_text=false`. Engine = **Laya SDK**. Judge calls were issued **serially**, one question at a time (a judge call spawns a GPU torch subprocess; concurrency previously exhausted machine commit).

---

## (b) Headline numbers — verbatim from the JSON

`aggregate.arms[*]`:

| arm | n_cells | mean_grade_all | mean_grade_gold | gold_survived | gold_rank_mean | mean_docs | mean_chars | mean_latency_s |
|---|---|---|---|---|---|---|---|---|
| `C-nogate` | 10 | **1.8** | **1.0** | 8/8 | 1.0 | **12.0** | 4000.0 | 6.92 |
| `C-judge` | 10 | **2.0** | **1.25** | 8/8 | 1.0 | **11.2** | 3880.6 | 7.65 |
| `C-judge-seg` | 10 | **1.3** | **0.375** | 8/8 | 1.0 | 11.2 | 4000.0 | 6.37 |

- `aggregate.paired_mean_delta` (**judge − nogate**) = **0.2**
- `aggregate.judge_failures` = **[]** (empty — all 10 gate calls returned `status:"ok"`, `real_engine:true`)
- `aggregate.total_answer_cost_usd` = **1.0015** · `total_answer_calls` = **30**

### Per-question raw values

`docs/rank/grade` — number of packed documents / gold rank within the packed order / grade 0–5. `None` = not applicable (gold absent from corpus).

| qid | stratum | cands | segments scored | segments kept | `C-nogate` | `C-judge` | `C-judge-seg` |
|---|---|---|---|---|---|---|---|
| QK01 | single | 12 | 122 | 109 | 12/1/**0** | 12/1/**5** | 12/1/**0** |
| QK02 | single | 12 | 104 | 56 | 12/1/**0** | 12/1/**0** | 12/1/**0** |
| QK03 | single | 12 | 111 | 99 | 12/1/**3** | 12/1/**0** | 12/1/**0** |
| QK04 | single | 12 | 96 | 92 | 12/1/**0** | 12/1/**0** | 12/1/**0** |
| QK05 | single | 12 | 119 | 117 | 12/1/**0** | 12/1/**0** | 12/1/**0** |
| QK06 | single | 12 | 116 | 83 | 12/1/**0** | 12/1/**0** | 12/1/**3** |
| QK07 | distractor | 12 | 115 | 32 | 12/1/**5** | 12/1/**5** | 12/1/**0** |
| QK08 | crosskb | 12 | 106 | 91 | 12/1/**0** | 12/1/**0** | 12/1/**0** |
| QK09 | unanswerable | 12 | 127 | 7 | 12/None/**5** | **4**/None/**5** | **4**/None/**5** |
| QK10 | outofcorpus | 12 | 108 | 96 | 12/None/**5** | 12/None/**5** | 12/None/**5** |

Verdicts (`aggregate.arms[*].verdicts`):

- `C-nogate`: refusal×5 (QK01,02,04,06,08), partial×1 (QK03), wrong×1 (QK05), correct×3 (QK07,09,10)
- `C-judge`: correct×4 (QK01,07,09,10), refusal×5 (QK02,03,04,05,06), wrong×1 (QK08)
- `C-judge-seg`: correct×2 (QK09,10), refusal×7 (QK01,02,03,04,05,07,08), partial×1 (QK06)

Paired per-question deltas (judge − nogate), `aggregate.paired_primary`:
`QK01 +5`, `QK03 −3`, all others `0`.

---

## (c) Every null and unfavourable result — stated plainly

1. **The gate changed almost nothing about what the model saw.** For **9 of the 10 questions the judged arm's packed document set is identical to the ungated arm's** (verified by comparing `cell_*.json → arms[*].docs`). Only QK09 differs at all: 12 docs → 4 docs, 4000 chars → 2806 chars. Mean packed candidates moved only **12.0 → 11.2**.
2. **The gold document survived in ALL arms on all 8 matchable questions** (`gold_survived 8/8` for every arm) and its rank was **1.0** everywhere. **Retrieval was never the bottleneck in this run — the verification gate has no headroom to demonstrate a retrieval benefit, because the fusion-ranked candidate list already put gold first 8/8 times.**
3. **The paired grade delta is +0.2 at n = 10, and it is not a distribution — it is two questions.** QK01 gained +5; QK03 lost **−3**; the other eight are exactly 0. A one-question gain and a one-question loss. This is indistinguishable from answer-level generation noise at this n.
4. **The QK01 pair is the clearest evidence of that noise.** QK01 `C-nogate` and `C-judge` received the **same 12 documents, same 4000-char budget** (verified byte-identical packed doc list) — and graded **0 (refusal)** vs **5 (correct)**. For that question the gate's measurable contribution is zero; the 5-point swing is variance in the closing model or the grader.
5. **The diagnostic `C-judge-seg` arm is worse than no gate at all**: mean_grade_all **1.3 vs 1.8**, mean_grade_gold **0.375 vs 1.0**. Feeding the judge's own merged `evidence_pack` instead of per-document heads *reduced* answer quality. This arm is not the primary comparison, but it is an unfavourable result and is reported as such.
6. **2 of 30 cells errored and were repaired — do not read the repaired values as clean measurements.** `cell_QK09.json` originally recorded, for **both** gated arms: `"rationale": "HTTPError: HTTP Error 401: Unauthorized"`, `"grade": null`, `"verdict": "error"` (and for `C-judge-seg` the *answer itself* also failed: `"(failed: HTTPError: HTTP Error 401: Unauthorized)"`). Cause: the platform bearer token expired mid-run; `answer_closed_book` self-heals on the stream-open path but the **grader call was not covered**. These two cells were re-run through the new `--repair` path (which re-answers and re-grades from the frozen pack). The originals are preserved verbatim in `repairs.json` and in each cell's `original_failure`. **The three QK09 grades of 5 in the table above are repaired values, not first-pass values.** The pre-repair aggregate was `C-judge mean_grade_all = 1.667`, `C-judge-seg mean_grade_all = 0.889`.
7. **The unanswerable/out-of-corpus strata are the only place the gate visibly bit** (QK09: 12 → 4 docs) — and the grade did not change (5 before and after). One question is not evidence of an abstention benefit.
8. **Four of eight gold-matchable questions graded 0 in *every* arm** (QK02, QK04, QK05, QK08), and a fifth (QK03) scored 3 in one arm and 0 in the other two. The dominant failure mode in this run is the closing model refusing or failing to answer **from evidence that contains the gold document at rank 1** — not a retrieval or verification failure. Any claim that this experiment validates the content-verification component is unsupported by these numbers.

---

## (d) Protocol deviation — an explicit limitation, not a footnote

**The specified switch does not exist on the live platform.** The brief specified two retrieval conditions differing only by `kb_hybrid_search(enable_judge=true|false, candidate_cap=12)`. That tool is **not present** on the live kb-mcp: `tools/list` returns **95 tools**, `has_kb_hybrid_search: false`, and a repo-wide grep finds **zero definitions** of `kb_hybrid_search` in `kb-mcp/server.py` — it is referenced only by older experiment scripts (`paper-kbs/experiments/exp1_retrieval.py:173`, `exp3_abstention.py:48`, `exp5_judge_filter.py:33`, `exp5b_q2_anatomy.py:22`, `exp8_graded_probes.py:57`) and by `paper-kbs/tex/main.md` prose. It existed in an earlier era of the project and has since been removed/renamed. Modifying `kb-mcp` to restore it was forbidden by the brief's hard constraints.

**What was done instead** (fallback rule applied): the ablation was rebuilt around the live verification gate **`kb_laya_judge`**, applied to a **frozen shared candidate set** so that the gate remains the single difference between conditions. The cost of the gate is therefore measured honestly; the *un-gated* arm is defined as the fusion-ranked candidate order.

**Two consequences you must carry into the paper:**

- The ungated arm is **not** the historical `kb_hybrid_search(enable_judge=false)` output. It is `kb_search_vector(top_k=30, score_threshold=0.35, slim=True)` per-library + a `kb_list`/`kb_get_documents` description-overlap catalog lane, merged **agreed-first, then vector top-8, then catalog top-4, capped at 12**. The absolute grade levels are therefore not comparable to earlier `kb_hybrid_search`-era results; only the *within-run* gated-vs-ungated contrast is.
- The frozen-candidate design is **stronger** than the specified one for isolation (the two arms cannot diverge in recall), but it **cannot** show a benefit from the gate re-ranking or re-selecting documents that the fusion stage missed — by construction both arms draw from the same 12.

---

## (e) What this does NOT show

This experiment does **not** show that the content-verification component improves answer quality, and it does not show that it is useless — it shows that **on this corpus and this question set the gate had almost no work to do**. The fusion stage already ranked the gold document first on 8/8 matchable questions, and the gate kept essentially every document it was given (mean pack 12.0 → 11.2), so the two conditions delivered near-identical evidence and any difference is generation noise.

It does **not** establish a noise floor: no repeat-answering of a frozen pack was performed (the QK01 0-vs-5 swing is *consistent with* noise but was not itself measured as a distribution), so the +0.2 mean delta cannot be given a confidence interval, and a single-question ±5 swing is entirely uncontrolled.

It does **not** generalize beyond: **10 questions**, one of which is a distractor, one cross-library, and two unanswerable/out-of-corpus (so only **8 graded retrieval hits**); **100 papers / 322 parts** in **5 libraries** — a corpus small enough that a top-10 vector search over a library returns only **2–8 documents**, so the candidate cap of 12 was rarely binding and cross-library contamination had little room to appear; **one closing model** (`claude` via the platform chat API, pinned in `chat_tracks.py:243`) at one prompt version; **one grader** (an LLM rubric grader, itself unvalidated, and itself a source of the 0-vs-5 swing); **one gate configuration** (`criterion="auto"` → resolved `"evidence"`, `threshold=0.5`); and **one pass** with no repeats. Above all it does not test the gate where a gate matters — under an over-retrieving recall stage, on a large noisy corpus, or on questions whose gold document is *not* already rank 1. **The single most defensible reading is negative: the verification gate's end-to-end contribution was not observable here, and the experiment as designed cannot rule out that its true effect is smaller than this harness's noise.**

---

## Evidence provenance

- The **original measuring run's stdout was not tee'd.** The console file
  `exp11-20261012-full.reproduce.console.log` is a **verbatim transcript of a cached reproduction pass**
  (`python paper-kbs/experiments/exp11_gate_ablation.py --out paper-kbs/experiments/results/exp11/exp11-20261012-full`)
  in which **zero new LLM calls were made** — all 10 `cell_*.json` were reused as-is and the aggregate was recomputed
  from those frozen cells. The warm-up *is* re-executed and makes a real judge call. The file carries this
  provenance in its own header lines. The authoritative per-cell measurements are `cell_QK01..QK10.json`.
- Read-only with respect to knowledge-base content throughout: no document or library was created, updated, deleted, moved, re-indexed, re-tagged or re-parsed. Only `kb_search_vector`, `kb_list`, `kb_get_documents`, `kb_doc_read`, `kb_laya_judge` and the chat API were called. `kb-mcp/` and `.claude/skills/` were not modified.
- The judge is fail-closed and machine-wide serialized (`.laya_judge.lock`); calls were issued one question at a time.
