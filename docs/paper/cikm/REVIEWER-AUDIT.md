# CIKM Submission — Reviewer Audit

> Audit date: **2026-09-13** · Target: **CIKM (ACM sigconf, anonymous)**
> Scope: format compliance, factual integrity, content completeness, project
> defects that affect the paper's claims.
> Every finding below was verified against the repository or the live deployment —
> none is speculative. Items marked 🔴 **block submission**.

---

## Part 1 — Format compliance

### Verified CIKM 2026 requirements

Checked against the CIKM Skills compilation of the official 2026 pages
(verification date recorded there: 2026-07-08), **not** against this project's
own framework doc — which is out of date and self-contradictory.

| Track | Page limit | Notes |
|---|---|---|
| Full Research | **≤10 pages incl. tables, figures AND appendix, + ≤2 pp references** | double-blind |
| Short Research | ≤4 pages | |
| **Applied Research** | **≤7 pages**, requires deployment / data-release evidence | |
| Resource / Demo | ≤4 pages each | |

Mandatory, non-negotiable:
* GenAI Usage Disclosure section, **before the references**, covering research,
  code, data **and** writing.
* Double-blind: no author, institution, URL, acknowledgement, or repo link.
* **Appendices count toward the page limit** — "move it to the appendix" saves
  nothing.
* EasyChair form obligations: nominate an author as reviewer (**omission =
  desk reject**); declare any public non-anonymous version (e.g. arXiv).

### Findings

| # | Finding | Severity |
|---|---|---|
| F1 | **Track is undecided, and the page count depends on it.** The paper is **9 pages**. That is legal for Full (≤10) and **illegal for Applied (≤7)**. The project's `docs/paper/README.md` says Applied is the target; the paper is written as a systems/Full paper. **Decide the track before anything else.** | 🔴 |
| F2 | This project's own docs are wrong and mutually contradictory: `README.md` says "Applied, 7 pages"; `CIKM-WRITING-FRAMEWORK.md` says "Full, 9 pages"; the verified 2026 figures are Full ≤10 / Applied ≤7. Fix the docs or they will mislead the next run. | 🟠 |
| F3 | GenAI disclosure has been rewritten to cover writing / code / data / instrument-use separately, as required. | ✅ fixed |
| F4 | Anonymous ✓, no repo link ✓, references ≤2 pp ✓ (1 page), CCS + keywords ✓. | ✅ |
| F5 | No anonymous artefact link exists anywhere. Reviewers will ask. | 🟠 |

---

## Part 2 — Factual integrity (the most serious findings)

### F6 🔴 Two references contained fabricated metadata

Checked against the actual PDFs the project collected in `docs/paper/reference/`.

| Key | Was written as | Actually is |
|---|---|---|
| `huang2025hirag` | Title *"HiRAG: Enhancing RAG on Hierarchical Knowledge Graphs"*; 9 authors, **7 of them invented** | *"Retrieval-Augmented Generation with Hierarchical Knowledge"*, Findings of EMNLP 2025, pp. 6044–6060; Haoyu Huang, Yongfeng Huang, Junjie Yang, Zhenyu Pan, Yongqiang Chen, Kaili Ma, Hongzhi Chen, James Cheng |
| `ge2026mcppyserini` | *"MCP-Pyserini: Bridging IR Toolkits and Language Agents"*, "Ge, Jinyuan and others" | *"MCP Servers for Pyserini and RankLLM: Enabling Agentic RAG"*, **Yijun** Ge and **Zibo Guo** |

Both are now corrected. **This is the single most dangerous defect found**:
fabricated author lists are treated as research misconduct, not as a typo, and
they came from writing reference metadata from memory instead of from the PDFs
sitting in the repository.

**Rule going forward:** never write a BibTeX entry without opening the source.
The project already has 9 verified PDFs — use them.

### F7 🟠 Three directly relevant papers the project already owns were uncited

`AgenticRAG` (Suresh et al., Microsoft — enterprise KB retrieval), `AutoKB`
(Sahay et al., NAACL 2025 Industry), `DeepRead` (Li et al., 2026). All three
target the same industrial setting. A CIKM reviewer would ask why the closest
prior work is absent. Now cited in a new Related Work subsection.

### F8 🟠 No CIKM-native citations

`cikm-related-work` explicitly warns that CIKM submissions should cite the
venue's own milestones. Added TAGME (CIKM 2010) and BERT4Rec (CIKM 2019) as
hierarchical-organisation lineage.

### F9 🟠 The opening motivating example is unreproducible

"PET biaxial film stretching retrieves PP film literature at cosine 0.90"
appears **only** in `docs/paper/PAPER-FRAMEWORK.md`, the project's own design
notes — not in any benchmark artefact. It cannot be reproduced from recorded
data, and it was the paper's opening evidence. Softened to a possibility claim
and a red marker added demanding an artefact-backed replacement.

---

## Part 3 — Numeric consistency

### F10 🔴 The system-scale table mixed two different snapshots

The draft reported "13 KBs, **184 documents**, **13,709 chunks**, 179 nodes /
2,502 edges" in one column. But:
* 13,709 chunks + 179/2,502 graph + **154 documents** = the 2026-07-29 run;
* **184 documents** = the 2026-09-13 run.

The 184/13,709 pairing never existed. Table 1 now reports **both snapshots on
separate dated rows**, with `--` where a run did not measure a value.

### F11 🟠 The live deployment no longer matches the paper's testbed

Measured today: **5 top-level knowledge bases and 5 vector collections**, not the
13 the paper describes. The testbed has been mutated by test runs. Either
re-create the documented testbed, or state that the 13-base figures refer to a
recorded snapshot no longer resident in the live deployment. **A reviewer who
asks for the artefact must be able to rebuild it.**

### F12 🔴 Ablation and main results are on different scales

| Table | P@5 range |
|---|---|
| Main results (Table 5) | 0.117 – 0.200 |
| Ablation (Table 6) | **0.723 – 0.875** |

A 4–7× gap. Both come from the same `cikm_summary.json`, so they were run on
different query sets or different relevance definitions. **The two tables cannot
be read together.** Red marker added: re-run the ablation on the same 50-query
set, or state the differing protocol explicitly.

### F13 🟠 Reported confidence intervals are not per-comparison

`cikm_summary.json` records the identical `ci: [0.43, 0.57]` for all four
baselines, which strongly suggests one shared interval rather than
per-comparison intervals. Flagged in the new Statistics paragraph.

### F14 🟠 p-values are uncorrected for multiplicity

Four baselines are compared; only the Hybrid-RRF comparison survives a
Holm–Bonferroni correction. The paper now says so instead of reporting only the
favourable value.

### F15 🟠 The XQuAD result contradicts the project's own summary of it

Recorded: staged **P@5 = 0.275** vs vector **P@5 = 0.831** — vector is 3× better.
`benchmark-report.html` describes this as "near-ceiling scores for both methods",
which the numbers do not support. Not cited in the paper, and deliberately
excluded from the frozen snapshot, but **the project's HTML report needs
correcting** or it will mislead the next author.

---

## Part 4 — Reproducibility

### F16 🔴 Benchmark artefacts are mutated in place and have no run identity

`benchmark-suite/results/*.json` are overwritten by every re-run.

**This actually happened during this session**: `module_c_experience_r2.json`
changed from `judge_score_mean = 3.5, total_experiences = 10` (archived 21:48) to
`judge_score_mean = null, total_experiences = 0` (live, 22:56). A paper citing the
live path would have cited numbers that no longer exist.

Fixed by freezing the exact bytes the paper uses:
* `data-snapshot/` holds immutable copies + `MANIFEST.json` with SHA-256 digests;
* `make_assets.py` reads **only** from the snapshot and verifies every digest,
  aborting if a frozen file changes;
* `freeze_snapshot.py` documents the snapshot history.

**Still to fix in the project**: give every benchmark run a unique immutable
output directory (`archive-<timestamp>` already exists as a manual convention —
make it the default), and record git commit + config hash + seed inside each
result file.

### F17 🟠 The experience module is not reproducible across runs

See F16. The same module produced 10 judged entries and then 0. The most likely
cause is that the second run found a populated experience store and the
deduplication guard suppressed every candidate — i.e. **the benchmark does not
reset state between runs**. Red marker added; the paper must not present one
favourable run of a module that yields a different answer on re-execution.

---

## Part 5 — Content completeness (non-Experience sections)

| Section | State after this revision |
|---|---|
| **Introduction** | Four-part structure (scene → problem → gap → method → contributions). Motivating case de-risked (F9). **Adequate.** |
| **Related Work** | Now covers 5 axes + enterprise/agentic KBs + CIKM-native lineage + capability table. **Adequate.** |
| **System Overview** | Five-layer model, write–read asymmetry, hierarchy. Scale table no longer mixes snapshots. **Adequate**, but see F11. |
| **Method (QDCVR)** | 7 stages, 2 equations, pipeline figure, algorithm, rubric table. Domain scoping and content adjudication are each given a mechanism-level explanation. **Adequate.** |
| **Agent interface** | 94 tools / 14 skills, verified by count. **Adequate but thin** — one paragraph. If the track is Applied, expand: the deployment evidence is precisely what Applied rewards. |
| **Evaluation** | Statistics paragraph added; ablation inconsistency flagged; author-evaluation bias added to threats. **Structurally adequate, evidentially incomplete** (see below). |
| **Discussion / Limitations** | Honest, specific, includes the strongest threat. **Adequate.** |
| **GenAI disclosure** | Rewritten to the required four-way coverage. **Compliant.** |

### What the Evaluation still lacks (red-marked in the paper)

1. **Multi-run reporting.** One run per configuration. CIKM convention is ≥5 with
   standard deviation.
2. **The exact statistical test**, and whether its assumptions were checked.
3. **Per-metric confidence intervals** (F13).
4. **Baseline implementation details** — BM25 `k1`/`b`, BGE-M3 version/revision,
   ChromaDB HNSW parameters (`M`, `ef_construction`), jieba dictionary version.
   Without these the baselines are not reproducible.
5. **Public-benchmark scale.** SciFact 30 queries, SQuAD 16, XQuAD 32. SQuAD and
   XQuAD are at ceiling and therefore uninformative about method differences.
6. **Human agreement (κ) on the 0–8 rubric.** The rubric is an LLM judgement with
   no inter-annotator study. This is the most likely single reviewer objection.
7. **A multi-domain public benchmark.** Every multi-domain result is
   author-constructed; every public result is single-domain. The paper's central
   claim — adjudication pays under cross-domain distraction — therefore rests
   entirely on self-built data. **This is the deepest weakness in the paper.**

---

## Part 6 — Project-side issues to watch during testing

These are real defects or hazards in the repository, not paper problems.

| # | Issue | Impact |
|---|---|---|
| P1 | **Benchmark results are overwritten in place** (F16). | Paper numbers rot silently. Highest-priority project fix. |
| P2 | **Benchmarks do not reset KB state between runs** (F17). Re-running a module on a populated store gives a different answer. | Results are not comparable across runs; the experience module already demonstrated this. |
| P3 | **Concurrent agent sessions share this working tree.** During this session another session overwrote benchmark results and had earlier edited `harness_registry.py`, `main.py`, `openapi.py` and added scripts under `.ui-audit/`. | Two writers to one artefact directory = unreproducible experiments. Isolate benchmark runs per session or serialise them. |
| P4 | **The live testbed has drifted** (F11): 5 KBs today vs 13 in the paper. Test runs create and delete KBs without a documented reset. | Documented setup cannot be rebuilt from the paper. |
| P5 | **Vector-index warning noise**: `"Error creating hnsw segment reader: Nothing found on disk"` appears for several collections during search. | Queries against those collections silently return nothing; if a benchmark hits one, a method looks worse for an infrastructure reason. Check before every measured run. |
| P6 | **`config.yml` disagrees with the running services**: file says backend `8770` / frontend `6789`, but the backend actually runs on **8771** and the frontend on both **6789 and 6790**. | Benchmarks can silently measure a different instance than intended; the recorded `"web": "http://localhost:6790"` in the result files is not the port the paper's own deployment uses. |
| P7 | **`docs/paper/README.md` is stale**: it links `APPLIED-PAPER-FRAMEWORK.md`, `FINAL-TEST-PLAN.md`, `FINAL-POTENTIAL-ASSESSMENT.md`, `AGENT-TEST-PROMPTS.md`, `PUBLISHABLE-STANCE.md` — **none of which exist**. | The next author follows dead links and re-derives decisions already made. |
| P8 | **Document-count drift is systematic**, not a one-off: the project's own records contain 154 (Jul), 184 (Sep, std2), 15+1 (Sep, ingestion) and "47 KB" (DATASETS doc) for the same platform. | Any paper number about corpus size needs an explicit dated snapshot or it is unfalsifiable. |

---

## Prioritised action list

**Before any further writing** 🔴
1. Choose the track (Full ≤10 pp vs Applied ≤7 pp) — F1. The current draft is
   9 pages and therefore only viable as Full, or must be cut by ~2 pages.
2. Re-run the ablation on the main 50-query set, or document the differing
   protocol — F12.
3. Resolve the experience module's 10 → 0 instability and report ≥3 runs — F17.

**Before submission** 🟠
4. Measure inter-annotator agreement (κ) on the 0–8 rubric.
5. Add a multi-domain public benchmark, or explicitly bound the central claim to
   the in-house corpus.
6. Add ≥5-run reporting, the named statistical test, and per-metric CIs.
7. Document baseline hyper-parameters.
8. Create an anonymous artefact repository and link it.
9. Remove every red marker — a submitted PDF must contain no red text.

**Project hygiene** (protects all future papers)
10. Immutable, timestamped, self-describing benchmark output dirs (P1).
11. State reset between benchmark runs (P2).
12. Serialise or isolate benchmark runs across concurrent sessions (P3).
13. Rebuild the documented 13-base testbed, or restate the paper's setup (P4).
14. Fix `docs/paper/README.md` dead links (P7).
15. Reconcile `config.yml` ports with the running services (P6).

---

## Verdict

**Format:** compliant for **Full Research** (9 pp ≤ 10, double-blind, GenAI
disclosure present). **Not compliant for Applied** (9 pp > 7). The track decision
is the gate.

**Content outside Experience:** structurally complete and now factually
consistent. Introduction, Related Work, System, Method and Discussion meet the
bar. The Evaluation is the weak section — not in structure, but in evidence: one
run per configuration, no κ, and a central claim resting entirely on
author-built data.

**Experience:** the architecture is described, but the section is currently a
design document. It has **no baseline comparison** and **no ablation**, and its
headline result is not reproducible. Five red markers specify exactly what is
missing. As it stands, a reviewer would accept the negative result as honest but
would not accept the section as a contribution.
