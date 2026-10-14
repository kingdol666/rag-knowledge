# KBS submission checklist — v2 manuscript (2026-10-12, post-restructure)

Build: `paper-kbs/tex/main2.tex` → `main2.pdf`, **72 pages**, 0 LaTeX errors, 0 undefined
references, 1 overfull box (1.09 pt, invisible), 25 floats all placed (none deferred past the
statements), 9 figures, 21 `table` environments (15 numbered in the body + 6 in the appendix),
16,210 body words (floats stripped), 59 references (unsrtnat), 3 `AUTHOR ACTION` markers.

Compile recipe: `pdflatex main2 && bibtex main2 && pdflatex main2 && pdflatex main2`
(Toolchain: `C:\texlive\2025\bin\windows\{pdflatex,bibtex}.exe`.)
Helper scripts: `paper-kbs/tex/_abs_count.py` (abstract cap), `paper-kbs/tex/_verify_compression.ps1`
(per-file word/number/citation/label diff against `paper-kbs/notes/precompress-20261012/`).

## 1. Form against the two measured KBS exemplars

| measure | bank-IRS (KBS 310, 2025) | SurveyAgent-HKA (KBS 2026) | ours (v2) |
|---|---|---|---|
| pages | 19 | 38 | 72 (12 pt preprint; ≈30 at 10 pt) |
| body words | 10,281 | 20,004 | 16,210 |
| words/page | 541 | 526 | 336 (12 pt) |
| figures | 6 | 12 | 9 |
| tables | 5 | 0 | 16 numbered (21 envs incl. appendix) |
| references | ~36 | 79 | 59 |
| sections | 8 | 7 | 11 + appendix |

Interpretation: at the exemplars' own type size the manuscript is ≈30 pages of text, i.e. within
the range KBS publishes for system papers; the remaining excess is table density (16 vs 0–5), not
length as such. Four of the original 19 tables were moved to appendix B (`Table B.*`), and the
component-ablation table added in §8.9 replaced none.

## 6. Adversarial self-review and its outcome (2026-10-12)

A review pass (subagent `5fa08f34-54d7-4490-8960-1124f5f97eee`) verified ~60 numbers against the
evidence base and the raw JSON artefacts: **no fabricated values, no dangling `\cite` key, no
uncited float, no duplicate label, no lost negative result, and no cross-lingual *retrieval*
number anywhere** (the H-1 ban held). Four attribution errors and five framing inconsistencies
were found and all were fixed in the same session:

1. **"21 papers failed to parse"** (eight sites: `n1_intro.tex`, `n4_acquisition.tex`,
   `n8b_eval.tex`, `n8c_eval.tex`, `n9_discussion.tex`, `n10_threats.tex`, `n11_conclusion.tex`)
   contradicted the paper's own §8.1 (`n8a_eval.tex`, which says the cause is unrecorded) and the
   `exp10_ingest_state.json` key set (no attempt/fail counters). All sites now say *never became
   retrievable, cause unrecorded*; contribution C2's 21 % figure was deleted; the Threats entry
   now states the cause may be either parsing or record keeping.
2. **§8.9 sold a null as a mechanism.** The gate ablation now leads with "returns a largely null
   result", states that the paired grades move on only 2 of 10 questions and are read as
   answering-model variance, that the pack shrank at all in a single cell (QK09, 12→4), and that
   the segment arm's loss tracks evidence packing rather than suppression. The abstract and
   contribution C4 were reframed accordingly: what is delivered is an auditable verdict record and
   routing coverage, not a recall gain.
3. **"8,031 chunks"** now carries its provenance ("the campaign record logs …"), and is no longer
   adjacent to the 800-character replica index (4,528 chunks) as if the same index.
4. **Confounded generality claim** in E6: "not the checkpoint, the domain, the language, or the
   corpus size" became an attribution to confuser density with an explicit statement that the
   second-corpus probe varied domain, language, scale and density jointly.
5. **"the five industrial libraries … were then absent from the live catalog"** now says the
   corporate deployment is air-gapped and the live snapshot is the research instance, so the
   headline corpora are frozen exports of that deployment.
6. Low-severity fixes: Fig. 9 panel (d) caption de-duplicated from `tab:robustness`; the
   `main2.tex` float comment corrected ("twenty-one table environments (six in the appendix)");
   the appendix rank-table sentence now reads "eight questions … plus Q16"; the graded-probe
   caption states the two sample sizes (tool layer n=6, agent layer n=3 from `exp8b`); the PA2
   reclassification is marked post-hoc; the `laya` bib entry states the checkpoint ships with the
   platform artefacts; cross-lingual and margin-sweep artefact pointers added.


## 2. Mandatory inclusions (KBS/Elsevier) — status

| requirement | where | status |
|---|---|---|
| Data availability statement | `n_back.tex` | present (points at logged runs, not a repository DOI) |
| Ethics declaration | `n_back.tex` `\section*{Ethics statement}` | present |
| Generative-AI use declaration | `n_back.tex` | present |
| Competing-interest statement | `n_back.tex` | present |
| CRediT author contributions | `n_back.tex` | present but names still `AUTHOR ACTION` |
| Funding acknowledgment | `n_back.tex` | present ("no specific grant") |
| Author names, affiliations, ORCID, corresponding author | `main2.tex:35-41` | **`AUTHOR ACTION` — blocks submission** |
| Highlights ≤ 85 characters | `highlights.tex` | 5 items, max 76 chars |
| Abstract ≤ 250 words | `main2.tex` | 246 words |
| Keywords | `main2.tex` | 6 |
| Figures as separate hi-res files < 10 MB | `paper-kbs/tex/figs/*.pdf` + `paper-kbs/figures/*.png` | present (vector PDF + 300 dpi PNG; all < 1 MB) |
| Reproducibility support | `n_back.tex` data availability, `paper-kbs/experiments/`, `benchmark-suite/` | present as run logs; no public archive yet |
| Suggested / opposed reviewers | — | **not prepared** |
| Cover letter | — | **not prepared** |

## 3. KBS desk-reject risks and how the manuscript answers them

1. *Generic model applied to a dataset* — answered: the contribution is a system of enforced
   contracts over a knowledge layer (nine subsystems, 95 MCP tools), not a model.
2. *Applied-X-to-Y with no methodological advance* — the advance claimed is the contract set plus
   the verifier-role decomposition (verdict as filter vs ranker), measured in §8.5/§8.7.
3. *Results without an ablation that isolates the knowledge component* — now answered by two
   matched ablations added in §8.9 (`sec:e8`): the verification gate (three arms, frozen candidate
   set) and content-routed search scope (four scopes). Both are reported as bounds, and the gate
   ablation's headline is negative (no measurable effect; the reading step is the constraint).
4. *Scope drift toward an applications venue* — mitigated by framing the knowledge layer as the
   object of study (§3–§7) and by keeping the negative result as the centrepiece.

## 4. Number discipline (what an evidence audit may check)

Every quantitative claim in `n1…n11` is traceable to one of:
`paper-kbs/notes/functional-test-evidence-2026-10-12.md`,
`paper-kbs/notes/exp11-gate-ablation-report.md` (+ JSON + cells),
`paper-kbs/notes/exp12-partition-ablation-report.md` (+ JSON + cells),
`paper-kbs/experiments/results/*.json` (the QDCVR suite),
`review/fulltest-20261012/SUMMARY.md`, `benchmark-suite/results/*`, `paper_demo/tex/*`.
Cross-lingual numbers are ingestion only (Module A); all cross-lingual retrieval numbers are
banned because the underlying suite is incomplete (recorded in Threats).

## 5. Remaining work before submission

1. **Author metadata** (`main2.tex:35-41`, `n_back.tex:33,37`): names, affiliations, ORCID,
   corresponding e-mail, CRediT roles, funding text. Also `refs.bib` key `qdcvr-demo` carries the
   placeholder author `Author Name`.
2. **Cover letter** + **suggested reviewers** (Editorial Manager, `editorialmanager.com/knosys`).
3. Optional: further compress §8 (≈4.9k words vs the plan's 3.0k budget) if a 13k-word target is
   kept — this requires dropping an evidence group, not rewording; the compression agents have
   certified that every remaining number and caveat in §5/§6/§8/§10 is load-bearing.
4. Optional: replace the two uncited `refs.bib` entries (`comaikg`, `rrpdg`) or leave them (they
   never appear in the reference list because nothing cites them).
5. Optional: split Figure 2 (lane flow, dense) or drop `tab:lanes`, since both describe the same
   lane structure.
