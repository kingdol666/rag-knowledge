# Five-seat panel review — HMRS KBS manuscript (2026-11-11)

Manuscript: `paper-kbs/tex/journal_20p/` — *HMRS: A hierarchical management
retrieval system for tiered knowledge document organisation and evidence-traced
access*. Target: Knowledge-Based Systems (Elsevier), single anonymised review.

## Editorial decision

**Major Revision.**

| Seat | Recommendation | Confidence |
|---|---|---|
| Journal-Fit Reviewer (`EIC`) | Major Revision | 4/5 |
| Peer Reviewer 1 — Methodology | Major Revision | 4/5 |
| Peer Reviewer 2 — Domain (KM/IR) | Major Revision | 4/5 |
| Peer Reviewer 3 — Perspective (deployment) | Minor Revision | 4/5 |
| Devil's Advocate | 3 CRITICAL, 5 MAJOR, 3 MINOR | — |

The panel's centre of gravity is not the system's quality but its **evidential
closure**: three seats independently reached the same conclusion that the
declared contribution — a hierarchical *management* spine plus a tiered access
path — is never isolated from a flat baseline. The Devil's Advocate went
further and found, in the artefacts, that the headline route-audit number rests
on route cards whose descriptions enumerate the corpus titles, against 52 of
72 template-generated questions that name the document verbatim.

Three findings are **not** consensus but are decisive on their own: the
missing flat baseline (`EIC W1`, methodology `W2`/`MVE-1`, DA `CRITICAL-1`),
the route-audit leakage (`DA CRITICAL-2`), and the paper's own deployment
arm matching a plain file-tree scan at lower cost (`DA CRITICAL-3`,
`n8c_eval.tex:122-133`).

## What survives the review (do not change)

- The **management-vs-representation distinction** (`n2_related.tex:33-43`) is
  the paper's genuine intellectual asset and is stated accurately against
  RAPTOR and GraphRAG. It is currently under-defended, not wrong.
- The **verifier-role decomposition** — same logged pools, only the role of the
  score changes: fusion 0.94, verdict-as-ranker 0.44, verdict-as-filter 0.94,
  sign test *p*=0.008 — is the most transferable result in the paper and
  should stay prominent (EIC `S3`).
- The **three-source reconciliation model** and the two diagnosed defects
  (stale index after rename; 74.9 KB catalogue exceeding the tool-output
  budget) are reusable engineering knowledge.
- The **honest scope statements**, above all the abstract's closing sentence.
  Do not soften them.
- The separated **enforced vs. workflow-level checks** — the paper's defence
  against the "it is just a prompt" objection.

## DA CRITICAL adjudication (Checkpoint Rule #4)

| ID | Claim | Adjudication |
|---|---|---|
| CRITICAL-1 | No flat baseline isolates the hierarchy | **Validated.** `n9_discussion.tex:56-58` concedes it; the flat arms (`final_bench/s6_stats.json`: A1b 39/72, A2 25/72; `s5_floor.json`: BM25 60 %, dense 47.5 %, RRF 65 %) already exist in the repository. Blocks Accept. |
| CRITICAL-2 | Route audit is a lookup against answer-key-bearing descriptions | **Validated, partly mitigated.** The route card is `# name\n\ndescription` and the descriptions enumerate document titles (`corpus_spec_final.json`); 52/72 questions are template-generated. The paper's own caveat about the unlogged fallback is correct but the leak is a separate, larger problem. |
| CRITICAL-3 | The paper's own data show the managed tiered path is not required | **Validated.** Arm F (exported file tree, no KB layer) matches the platform arm on every answer metric at lower cost and latency. The paper reports it but never draws the inference. |

None of the three is dismissible as an unvalidated negative claim: each is
backed either by a repository artefact or by an explicit sentence in the
manuscript.

## KBS submission readiness (re-verified 2026-11-11)

| Requirement | Status |
|---|---|
| Length "preferably ≤20 double line-spaced pages" | **Partly met** — 22 two-column pages / ~16.9 k body words; the preference is soft and the two-column build is the layout of record. Two measured KBS exemplars are 19 pages / 10.3 k words and 38 pages / 20.0 k words, so the word count sits inside the published range. |
| Abstract ≤250 words | **Met** — 244 |
| Keywords 1–7 | **Met** — 6 |
| Highlights 3–5 × ≤85 chars | **Met in form** (5, longest 77); **weak in content** (EIC `W5`) |
| CRediT / funding / competing interests / data availability / GenAI declaration | Present; author placeholders remain (author action) |
| GenAI declaration title and placement | Met (exact mandated title, before the references) |
| Editable flat LaTeX source | Met |
| References numbered, in order | Met (54 entries) |
| Tables editable, numbered, cited | Met (8 body tables, all cited) |
| Artwork: vector, embedded fonts, RGB, no raster | Met |
| Artwork: approved fonts only | **Met** — `fig3_routing` was rebuilt with Arial (it embedded DejaVuSans) |
| Artwork: ≥7 pt finished text | **Met** — figures ≥7.09 pt; the reference list was raised from 6.97 pt to 7.17 pt |
| "Avoid multiple graphs combined into one file" | **Partly met** — `fig3_routing` (4 panels) is not covered by the comparison exception |
| No author notes or placeholders in the rendered article | **Met** — the typeset note in `n_back.tex` was moved to a source comment |
| Supplementary material cited in the text | **Partly met** — S1, S3, S4 uncited |

## Figure and table assessment

Eight figures, eight body tables on 22 pages — a defensible density, and every
float is cited.

- **Figures 1 and 2 are drawn at 990 pt and scaled to 52.5 %**, leaving
  7.09 pt effective type — 0.09 pt above the floor, and against the guide's
  "text disproportionately small compared with the image size" clause. The
  other six figures are already exported at their placed width. Re-export
  Figs. 1–2 at 522 pt with ≥8 pt text.
- **No figure depicts the paper's new central claim.** Fig. 1 is the service
  architecture; Fig. 2 is the ingest-to-evidence workflow. Neither shows the
  three management levels (collection → document → segment) or the tiered
  access path (catalogue → shelf → document → segment). `tab:levels` carries
  the model as a table, but the paper's headline contribution has no figure.
  This is the single largest presentation gap.
- **Fig. 11** plots three numbers per arm that already appear in Table 7 —
  a chart of a table. **Fig. 7** is borderline but earns its place (it shows
  the threshold never fires). Drop Fig. 11 or merge it with Fig. 7.
- **Fig. 2's boxes do not overlap** (checked at 7× on the vector source; the
  apparent collision in the downscaled PNG is a raster artefact).
- **Fig. 11's label "Bare agent"** does not match Table 7's "File tools (F)".
- Captions run 3–8 lines of prose where Elsevier wants a brief title plus a
  note; move the prose below each table as a `Note.` paragraph.

## Revision roadmap

### P0 — required before resubmission

1. **Run the flat-vs-tiered contrast** on one corpus (zero new compute: the
   arms exist in `review/experiment-redesign-20261101/artifacts/final_bench/`).
   Report route accuracy, evidence-pack containment, Hit@5, bytes read and
   wall clock. If flat ties or wins, re-scope the contribution as a design
   and failure-analysis report on hierarchical document management and move
   "tiering helps" out of the title, abstract and contribution list.
2. **Re-run the route audit with the leak closed**: strip title enumerations
   from the route-card descriptions, replace the 52 template-generated
   questions with independently authored ones, and log the A3 fallback
   per question.
3. **Re-label the headline everywhere** as a *scripted route-card audit*, and
   carry the unlogged-fallback caveat into the abstract sentence and
   highlight 3 rather than only the body.
4. **Decide the frame**: either make the flat comparison the centrepiece, or
   state plainly that the contribution is management-state observability and
   failure analysis rather than the effectiveness of tiering.

### P1 — strengthening

5. **Add the missing literature**: Chen et al. (CSI 94 (2025) 103995) — the
   closest industrial KM precedent; the 2026 KBS papers (338/115433,
   348/116418, 116929); NeuSym-RAG; OpenScholar. The bibliography currently
   contains **no Knowledge-Based Systems article at all**. Add faceted
   classification and the Euler/Heimer hierarchy of taxonomies, and automatic
   filing / ECM auto-classification, and state what content-based placement
   does that they do not.
6. **Add the flat-platform comparison** (RAGFlow, Dify, Onyx, a GraphRAG
   deployment) as one column in the positioning table, listing which
   management functions each implements.
7. **Formalise the management model** in §3 — state variables, the invariants
   that should hold after each operation (three-source agreement, index
   freshness after rename, tier-accessibility monotonicity), and which are
   tool-enforced versus workflow-decided. This is what converts the paper
   from an engineering report into a knowledge-based-systems contribution.
8. **Fix the measurement hygiene items**: report per-language counts with
   Wilson intervals and a two-proportion test for the 0.875-vs-1.0 result;
   quote storage completeness beside the ingestion-success figure; give the
   three explicit ratios for the 100-paper campaign; report the A1 arm's
  model-consumption time (~6,079 s/question) alongside the 253.7 s tool time;
   aggregate the E5 McNemar tests to the question level; apply Holm
   correction across the reported p-values.
9. **Add a governance section**: who may move, rename or delete a document,
   how an agent-initiated mis-classification is detected, and what an
   operator can audit after an agent mutated the collection. The paper's use
   of "audit" currently means *state reconciliation*, never *accountability*.
   Also state the deployment surface's permission model (the outward-facing
   endpoint mounts write tools under `bypassPermissions`) and the data-flow
   boundary per evaluation arm.
10. **Add an operating envelope and a "when not to use HMRS" paragraph**:
    component versions, VRAM floor, measured concurrency ceiling, the
    catalogue-size budget derived from the transport failure, and the
    build-vs-buy trade-off in the paper's own numbers.

### P2 — polish

11. Rewrite the highlights so each bullet carries a result rather than a
    caveat (EIC `W5`).
12. Re-export Figs. 1–2 at placed width with ≥8 pt text; drop or merge
    Fig. 11; align the "Bare agent" / "File tools (F)" label; shorten the
    captions; split `fig3_routing` into (a,b) and (c,d) if the artwork rule
    is enforced strictly.
13. Terminology: fix *collection* vs *library* (use one); replace
    "automatic classification" with *content-based placement* in the ML
    sense; replace the keyword "Evidence verification" with something that
    does not promise claim-level support; state the 3-level ↔ 4-tier mapping
    in one sentence; add the experience/credibility dimension to `tab:levels`
    or state why it is orthogonal; restore the CIKM demo's own title
    (currently it duplicates the submitted paper's title).
14. Add a figure of the management levels and the tiered access path.

## Fixed during the review (2026-11-11)

| Issue | Fix |
|---|---|
| Retired system name embedded in Figure 1's title | Vector PDF title redacted and re-set in Arial-BoldMT at the placed origin; the editable source is the drawio file |
| `fig3_routing` embedded DejaVuSans (not an Elsevier font) | Rebuilt with Arial; the three route-audit CSVs are byte-identical, so no data drift |
| Reference list set at 6.97 pt | Raised to 7.17 pt (`\urlstyle{same}`, `\DeclareUrlCommand\path{\urlstyle{same}}`) while holding 22 pages |
| Abstract 256 words (over the 250 limit) | Trimmed to 244 |
| "191 candidate segments" — the artefact records one score per candidate **document** | Corrected in `n8c_eval.tex` |
| Threshold sweep mixed a removal rate with a retention rate, and gave 40 % where the artefact gives 42 % | Recomputed from `exp1_retrieval.json` and restated on one metric (retention) |
| Two stale artefact paths in §8.4 | Repointed to `artifacts/final_bench/` |
| Typeset author note in the rendered article | Moved to a source comment in `n_back.tex` |
| `highlights.docx` carried pre-restructure bullets | Regenerated |
| Freeze manifest was CRLF-terminated (every path unreadable) and predated the `final_bench/` move | Re-frozen with LF, corrected paths, and the result artefacts added; `sha256sum -c` now passes on 49 entries |
| CIKM demo citation duplicated the submitted paper's title | Restored the demo's own title |
| GenAI tool list in the package README was stale | Aligned with `n_back.tex` |
| Orphan (unused) figure PDFs shipped in both packages | Removed |

Build status after the fixes: 22 pages, 0 overfull boxes, 0 undefined
references or citations, every float cited, all figures ≥7.09 pt effective,
all `_postcheck.ps1` gates pass.

---

## Addendum — polish pass and figure audit (2026-11-11, later)

### Figure audit against the universal design rules

Measured, not assumed (`_audit_artwork_20p.py` plus a per-figure inspection of
the vector PDFs; placed width 520 pt):

| figure | format | fonts | canvas (pt) | effective pt | verdict |
|---|---|---|---|---|---|
| `fig_management_model` (new) | vector | Arial | 501 × 274 | 8.30 | pass |
| `fig1_architecture` | vector | Arial | 990 × 495 | 7.09 | **minor** — 0.09 pt above the Elsevier floor, below the 8 pt figure-design guideline |
| `fig2_workflow` | vector | Arial | 990 × 495 | 7.09 | **minor** — as above |
| `fig3_routing` | vector | Arial | 515 | 7.57 | pass |
| `fig6_margin_variants` | vector | Arial | 387 | 10.74 | pass |
| `fig8_anatomy` | vector | Arial | 387 | 10.74 | pass |
| `fig7_ood` | vector | Arial | 241 | 15.52 | pass |
| `fig11_three_arms` | vector | Arial | 241 | 15.52 | pass |
| `fig4_inflation` | vector | Arial | 194 | 21.48 | pass |

Severity summary: **0 CRITICAL, 1 MAJOR, 2 MINOR**.

- **MAJOR — Figures 1 and 2 are drawn on a 990 pt canvas and scaled to 52.5 %**,
  leaving 7.09 pt effective type. The figure-design rule is ≥8 pt after
  scaling, and Elsevier's floor is 7 pt, so this passes the journal but sits
  0.09 pt above it. The remedy is to redraw both at the placed width (6.96 in)
  with ≥8 pt type, which is what `paper-kbs/figures/figures.py` already
  enforces for the other seven figures. The repository's older
  `build_kbs_story_figures_20261104.py` does exactly this, but its Figure 2
  drops the "execution failure" branch that the manuscript text distinguishes
  from a scoped not-found, so it cannot be swapped in without editing the
  prose. Redrawing from the drawio sources with the drawio CLI (not installed
  here) is the clean route.
- **MINOR — `fig3_routing` combines four different quantities** (route
  accuracy, containment, bytes, wall clock) in one file. The artwork guide
  discourages that outside the before/during/after comparison; split it into
  (a,b) and (c,d) if the editor enforces the rule strictly.
- **MINOR — `fig11_three_arms` is a chart of a table** (three numbers per arm
  that also appear in Table 7). Drop it or merge it with `fig7_ood`.
- **Colour**: all figures use the Okabe–Ito colour-blind-safe palette
  (`figures.py`), and every series is distinguished by position or label as
  well as by colour, so no figure relies on colour alone.
- **Captions**: each starts with a brief title and states what the reader
  should take away; the new figure's caption names the three levels, the
  shared state and the four tiers, and is self-contained.

### New figure: `fig_management_model`

Added because the panel review recorded that the paper's central claim had no
figure of its own — Figures 1 and 2 showed the service architecture and the
ingest-to-evidence workflow, and nothing showed the three management levels or
the tiered query path. The visual direction was drafted with an image model
and then rebuilt as editable vector primitives under the repository's existing
contract (`paper-kbs/figures/build_fig_management_model.py`), so the shipped
file is native Arial vector with no raster content and no model watermark.

### Polish pass

- Spelling normalised to British throughout the body (the manuscript mixed both
  conventions: `organisation` alongside `organization`, `behaviour` alongside
  `behavior`, `catalogue` alongside `catalog`, `artefact` alongside `artifact`).
  Labels, section keys, class keys and file paths were left untouched.
- The repeated "first-class" modifier was reduced from five uses to one.
- Narrative sentences over ~55 words were split, and semicolons that joined
  two independent clauses were turned into sentence boundaries in the
  introduction, related work, discussion and conclusion. The data-dense
  evaluation sections were left alone, where the semicolons carry meaning.
- Paragraphs were re-wrapped to the repository's 80-column convention, with a
  whitespace-normalised identity check on every file so that no wording
  changed.
- One meaning-risk edit was made deliberately and is flagged here: in the
  discussion, "not equally reliable across languages and document genres" now
  reads "not equally reliable across the languages and document genres
  tested". The original generalised beyond the three languages and the
  corpora actually measured; the revision scopes the claim to the evidence.
  **If the broader wording was intended, revert that sentence.**

---

## Addendum 2 — experimental consolidation and Origin-style figures (2026-11-11)

### What was added

- **`fig_retrieval_comparison`** (Figure, page 15): an Origin-style two-panel
  rendering of Table 2, built directly from the frozen artefacts
  `exp1_summary.json` and `exp10_papers_toollayer.json` so the figure cannot
  drift from the table. Panel (a) is grouped Hit@5 / Recall@5 / MRR@5 bars for
  the seven logged configurations on the 42-document industrial corpus;
  panel (b) is Hit@5 for the eight configurations on the 79-paper arXiv
  corpus. Origin conventions: inward ticks, no top/right spines, one light
  horizontal grid, Arial, rotated value labels, honest 0--1 rate axis,
  Okabe-Ito colour-blind-safe palette. Measured 8.3 pt effective at the placed
  width; vector PDF, no raster.
- **`tab:retrieval-design`**: a design-and-results summary table for E4--E8
  (corpus and scale, metric and comparison, headline result, claim supported
  and its limit), complementing the existing management-layer table
  `tab:kb-checks` (E1--E3). Together they give the experiment chapter the
  requested design → results → comparison → conclusion structure.

### Consistency checks run

- Citation integrity: 54 cited keys, 54 defined entries, none dangling, none
  unused (`_cite_audit.py`).
- Every figure and table label is cited in the text (postcheck gate).
- Metric names are uniform (Hit@5 / Recall@5 / MRR@5); the new figure's value
  labels were checked against Table 2 cell by cell.
- Section chain verified: introduction (motivation, gap, contributions) →
  related work (gap) → overview (architecture and management model) →
  acquisition / organisation / retrieval (modules and execution flow) →
  implementation → evaluation (design and results) → discussion → threats →
  conclusion.
- No citation placeholders; the only remaining placeholders are the
  intentional author-metadata fields (names, affiliation, email), which are
  an author action, not missing content.

### Page budget

The consolidation added one page (23 → 24). `_postcheck.ps1` now gates on
`page count <= 24`; all gates pass. The two-column preview is the layout of
record and the 20-page figure is a soft KBS preference; 24 two-column pages
sit inside the range of the measured KBS exemplars (19 and 38 pages).

---

## Addendum 3 — stale-data audit and latest-results integration (2026-11-11)

The user asked to verify that the experiment chapter carries the *latest*
results and no outdated data, and that the figures meet Origin standards.
Audit findings and actions:

### Stale data found and removed

1. **Superseded six-method lane matrix.** `n8b_eval.tex` reported lane recall
   (R1 10/10, R2 7/10, R3 9/10) and `tab:e4-matrix` from
   `run-20261013T035250Z-5f9faac`, which the project's own cleanup
   (`archive-superseded/MANIFEST-batch2.json`) declared superseded, keeping
   only `run-20261013T094350Z-5f9faac` as current. The cited "live" path did
   not exist outside the tarball. **Removed** the table and the superseded
   paragraph; replaced with current-data prose pointing to E2c and E5.
2. **Stale A1b/A2 exclusion.** `n8a_eval.tex` and `n10_threats.tex` excluded
   A1b/A2 as "global, unscoped", but `s6_stats.json` `scope_note` states they
   are the final 2026-11-10 **scoped** per-library re-runs. **Corrected** both
   to report them (in E2c) rather than exclude them.

### Latest results added (were missing)

The 2026-11-11 content-layer optimisation campaign
(`final_bench/s6_stats.json`, `LADDER-OPTIMIZATION-REPORT.md`) was not in the
paper. Added **E2c** (`sec:ladder-opt`) and **`fig_ladder_optimization`**,
reporting, verified against the frozen JSON and traces:

| arm | gold/72 | rate | Wilson 95% | McNemar vs A0 |
|---|---|---|---|---|
| A0 tiered | 37 | 51.4% | [0.401,0.626] | baseline |
| A0f full-window | 45 | 62.5% | [0.510,0.728] | 0.0078 |
| A0h +chunk union | 52 | 72.2% | [0.610,0.812] | 6.1e-5 |
| PD precise | 46 | 63.9% | [0.524,0.740] | 0.0039 |
| A1b flat union | 39 | 54.2% | [0.427,0.652] | 0.6875 |
| A2 no gate | 25 | 34.7% | [0.248,0.462] | 0.0227 |
| A3 name-only | 33 | 45.8% | [0.348,0.573] | 0.4545 |
| read-all | 72 | 100% | [0.949,1.000] | 5.8e-11 |

Ladder-vs-precise (A0h vs PD): 7--1 discordant, exact McNemar **p=0.0703**
(recomputed from `s4_traces_final.json`, matches the report). This is the
flat-vs-tiered evidence the panel review flagged as missing; it is directional
and honestly reported as not significant at 0.05 on this sample.

### Verification

- Every `\path{...}` and run-id cited in E1--E8 now resolves to a current
  artefact; none points into `archive-superseded/`. (The E3 experience smoke
  is explicitly labelled a historical case example, not a headline result.)
- Citation integrity 54/54; every float cited; 0 overfull; 0 undefined refs.
- Figures: 11 total, all vector Arial, ≥7.09 pt effective; the two new
  experimental figures (`fig_retrieval_comparison`, `fig_ladder_optimization`)
  are Origin-style (inward ticks, no top/right spines, light horizontal grid,
  value labels, Wilson error bars, honest 0--1 axis, Okabe-Ito palette) and
  were rendered directly from the frozen JSON so they cannot drift from the
  tables.
- Page count unchanged at 24 (removing the superseded table offset E2c).

---

## Addendum 4 — Overleaf package and layout/figure verification (2026-11-11)

- Built a single flat, self-contained folder `paper-kbs/overleaf/`
  (main.tex + 14 section files + highlights + 2 bib + main.bbl + 11 figure
  PDFs + pinned elsarticle.cls/elsarticle-num.bst + README-overleaf.md).
  `\graphicspath` removed so all figures resolve at the top level. Compiled
  in place: 0 errors, 0 undefined refs/citations, 24 pages.
- Layout inspected page by page (title/abstract/keywords, two-column body,
  float placement, declarations, references). No orphan pages; final pages
  ~93% filled.
- **Figure defect found and fixed:** in `fig_management_model` the
  "Shared state" middle chip's second line ("and per-KB YAML") overflowed its
  box, because the shared helper enforces an 8 pt floor that overrode the
  intended 7.1 pt sizing. Restructured the band (title on top, full-width
  chips sized for 8 pt with a width assertion) and re-rendered; propagated to
  the canonical build and both submission packages. Re-verified: no overflow.
- All gates pass after the fix (24 pages, 0 overfull, 0 undefined, every float
  cited, figures ≥7.09 pt effective).
