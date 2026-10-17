# KBS submission package

Generated from the canonical source `paper-kbs/tex/journal_20p/`. This is a flattened LaTeX source package for Editorial Manager; the local 20-page PDF is a review/layout preview, not evidence that the journal's preferred double-spaced manuscript length is met.

- manuscript source: `main_20p.tex` plus 15 included TeX files
- bibliography: `refs.bib`, `refs_new_verified.bib` plus generated `main_20p.bbl`
- figures used by the manuscript: `fig1_architecture.pdf`, `fig2_lanes.pdf`, `fig3_retrieval.pdf`, `fig6_margin_variants.pdf`, `fig11_three_arms.pdf`, `fig7_ood.pdf`, `fig4_inflation.pdf`, `fig8_anatomy.pdf`
- highlights: `highlights.docx` and `highlights.tex` (verify identical wording before upload)
- supplementary material: upload `paper-kbs/supplementary/supplementary-material.pdf` as a separate supplementary item (Part D of that document carries Tables S1-S5, the five appendix tables the manuscript cites; they moved out of the manuscript on 2026-10-16)
- Declaration of Interests: complete Elsevier's declarations tool and upload its generated Word document separately
- evaluation freeze: the corrected annotations, the pre-correction question set and the grader are pinned in `paper-kbs/tex/journal_20p/.frozen-experiment-sha256.txt` (verify with `sha256sum -c` from the repository root)
- page budget: measurements for both layouts (20-page camera-ready preview; 68-page double-spaced review format) and the compression plan are in `paper-kbs/notes/page-budget-2026-10-16.md`

## Author confirmation required before submission

1. Replace author names/order, corresponding-author email, affiliation and city/country in `main_20p.tex`.
2. Replace Author 1/Author 2 in CRediT with accurate names and roles.
3. Confirm the no-funding statement and acknowledgements.
4. Confirm the generative-AI declaration: it now names the two agent CLIs used on this project ("Anthropic Claude Code and ZCode command-line coding agents"); add versions only if the editors ask.
5. Supply the separate Declaration of Interests Word file from Elsevier's tool.
6. Confirm the CIKM demo author metadata and publication details when available.
7. Upload the supplementary PDF separately and verify it reflects the current manuscript.
8. Choose the manuscript layout: the two-column preview (`main_20p.tex`, 20 pages) or the double-spaced review source (`main_20p_review.tex`, 68 pages); KBS permits double-column LaTeX but describes 20 double-spaced pages as preferred (see the page-budget note).
