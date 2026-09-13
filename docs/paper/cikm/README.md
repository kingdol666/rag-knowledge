# CIKM Submission — Content-Adjudicated, Domain-Scoped Retrieval

> **Status: revised after panel review. Verdict was MAJOR REVISION.**
> The revision removed the paper's former main results because their producing
> script could not be found — see [`PROVENANCE.md`](PROVENANCE.md), which is now
> the single most important document in this directory.

## Build

```bash
python freeze_snapshot.py      # freeze cited artefacts (SHA-256) — run first
python make_assets.py          # emit only provenance-verified tables/figures
python provenance_audit.py     # GATE: exits 1 if a cited artefact has no producer
latexmk -pdf main.tex
```

Verified with TeX Live 2025. Current build: **11 pages = ~9.5 content + ~1.5
references** (CIKM Full Research allows ≤10 content + ≤2 references). No overfull
boxes, no undefined references.

## Read these in order

| # | File | Why |
|---|---|---|
| 1 | [`PROVENANCE.md`](PROVENANCE.md) | **Start here.** What was withdrawn and why. |
| 2 | [`EDITORIAL-DECISION.md`](EDITORIAL-DECISION.md) | Panel verdict, 8 validated CRITICAL findings, roadmap, author response |
| 3 | [`REVIEW-TODO.md`](REVIEW-TODO.md) | Every outstanding item with its acceptance criterion (TODO-1 … TODO-21) |
| 4 | [`REVIEWER-AUDIT.md`](REVIEWER-AUDIT.md) | Author-side audit: format compliance, reference integrity, numeric consistency |
| 5 | `main.pdf` | The paper |

## What changed in this revision

**Removed.** The former Table 4 (main results), Figure 3 (FPR) and Table 5
(ablation), together with every headline number in the abstract. Their artefacts
have **no producing script** — an exhaustive search over 417 code files found no
writer. The one benchmark runner in that directory is a standalone BM25 script
over ~30 synthetic document abstracts with no vector index, no adjudication and no
LLM.

**Rewritten around traceable evidence.** Abstract, C1, C2, §7.3 and §8 now rest
only on the five artefacts with committed producers: BEIR SciFact (30 official
queries, official qrels, four methods), the in-house bilingual corpus, ingestion
integrity, the experience module, and the 73-check end-to-end surface test.

**Added.** §7.4 reports the provenance failure as a first-class finding — every
table must name its producing script — and `provenance_audit.py` enforces it.

**Earlier in the same revision.** Two references with fabricated author metadata
corrected against the project's own PDFs; three relevant uncited papers added;
§3 expanded into a full architecture section with a figure; `Statistics` rewritten
to make no claim it cannot support.

## Provenance map

| Artefact | Producer | Status |
|---|---|---|
| `module_a_ingestion_r1.json` | `benchmark-suite/scripts/01_ingestion.py` | cited |
| `module_a_std2_r1.json` | `benchmark-suite/scripts/21_std2_ingest.py` | cited |
| `module_b_retrieval_r2.json` | `benchmark-suite/scripts/02_retrieval.py` | cited |
| `module_b_std2_r2.json` | `benchmark-suite/scripts/22_std2_retrieval.py` | cited |
| `module_c_experience_r2.json` | `benchmark-suite/scripts/03_experience.py` | cited |
| `cikm_summary.json` + 4 siblings | **none** | **withheld** |

## Compliance

| Requirement | Limit | Actual |
|---|---|---|
| Content + appendix | ≤10 pp | ~9.5 |
| References | ≤2 pp | ~1.5 |
| Template | ACM sigconf | ✅ |
| Anonymity | double-blind | ✅ |
| GenAI disclosure | before refs | ✅ |
| Red markers | must be 0 at submission | **19 — remove before submitting** |

## The one experiment that matters most

`TODO-18`: build a multi-domain benchmark from a public corpus (the project's own
`DATASETS-AND-EXPERIMENTS.md` documents the HotpotQA route) and run the **2×2
factorial** scoping × adjudication with its interaction term. That interaction
*is* the paper's central claim. Without it, either bound the claim in the abstract
or move to the applied/industry track.
