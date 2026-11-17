# HMRS — Knowledge-Based Systems submission package (Overleaf-ready)

Self-contained LaTeX project: `main.tex` (23 double-column pages) plus
`supplementary.tex` (3 pages, redundant/extra figures & tables), with the
`elsarticle` class + `.bst`, all figures, and both `.bib` files bundled.
Compiles on Overleaf without external dependencies.

## Contents
- `main.tex` — entry point; inputs `n1_intro`…`n11_conclusion`, `n_back`.
- `n*.tex`, `highlights.tex` — sections + highlights (3–5 bullets, ≤85 chars).
- `refs.bib`, `refs_new_verified.bib` — numbered bibliography (elsarticle-num).
- `elsarticle.cls`, `elsarticle-num.bst` — bundled Elsevier class + style.
- `figs/` — design figures (GPT-2.6, cropped + upscaled to 314 dpi at full width):
  `fig_analogy.png`, `fig_architecture.png`, `fig_workflow_demo.png`,
  `fig_software_design.png`; experimental figures as vector PDFs (Origin-style):
  `fig_ladder_optimization.pdf`, `fig_retrieval_comparison.pdf`, `fig3_routing.pdf`,
  `fig4_inflation.pdf`, `fig6_margin_variants.pdf`, `fig7_ood.pdf`,
  `fig8_anatomy.pdf`, `fig11_three_arms.pdf`.
- Pseudocode: Algorithm 1 (tiered access + optional evidence gate) in `n6_retrieval.tex`
  (`algorithm`/`algpseudocode`, vector).

## Import to Overleaf
1. Zip this folder as-is (keep `figs/`, `elsarticle.cls`).
2. Overleaf → New Project → Upload Project.
3. Menu → Main document = `main.tex`; Compiler = pdfLaTeX; TeX Live default.
4. Recompile (auto pdflatex→bibtex→pdflatex) → `main.pdf` (23 pages, 0 errors).
   For the supplement, set main document to `supplementary.tex` and recompile (3 pages).

## Local build
```
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

## Before submission (author actions)
- Fill real authors/affiliations/corresponding e-mail (frontmatter), CRediT
  (`n_back.tex`), and the `hmrs-demo` bib entry.
- Upload figures separately if required (TIFF/EPS/PDF ≥300 dpi); the vector PDFs
  and 314-dpi PNGs here satisfy Elsevier artwork rules.
- Add cover letter; keep `highlights.tex`.

## Compliance snapshot
- 27 double-column pages (KBS has no hard double-column limit; the ≤20 guidance
  refers to double-spaced single-column manuscript pages). Complete experimental
  design + results in main text.
- 0 LaTeX errors / 0 undefined references / 0 overfull boxes; every figure/table
  cited; every citation resolves; abstract 247 words.
- Design figures full-width (figure*) at 314 dpi; experimental figures vector,
  colour-blind-safe, ≥7 pt (superscripts ≥6 pt). All figures double-column where
  multi-panel, per KBS placement practice.