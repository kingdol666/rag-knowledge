HMRS manuscript package for Overleaf (2026-11-17)
==================================================

Main document
-------------
Open/compile: main_20p.tex
Sequence: pdflatex -> bibtex -> pdflatex -> pdflatex (Overleaf runs this
automatically; the class is elsarticle, available in TeX Live).
Expected result: main_20p.pdf, 20 pages, no undefined references.

Supplementary material
----------------------
Compile separately: supplementary.tex (pdflatex twice).
Expected result: supplementary.pdf, 8 pages, figures S1-S5 and tables
S9-S17 with S-prefixed numbering.

supplementary-inventory.pdf is a static 42-page companion (campaign
inventories, its own tables S1-S8). It is referenced from the main text as
"the supplementary inventory"; its LaTeX source predates this package and is
archived outside it, so it ships as a finished PDF only.

Figures
-------
All included graphics are vector PDFs under figs/ with embedded fonts
(Arial subsets, fonttype 42). No absolute paths are used; the sources
reference them via \graphicspath{{figs/}}.

Data and provenance
-------------------
experiment_data/ carries the packaged trace CSVs (frozen 608 rows,
follow-up 532, floor 120; SHA256SUMS), the figure-source manifest, the
case-anatomy provenance record and the redraw summaries produced by
figure_scripts/build_results_20261116.py (kept in the repository, not required
for compilation).

Notes
-----
- Author names, affiliation, e-mail, CRediT, funding and acknowledgements
  remain author-confirmation fields in the source (see AUTHOR ACTION comments
  in main_20p.tex and n_back.tex); they must be completed before submission.
- This package is a double-column elsarticle review preview; final KBS
  layout remains subject to the journal's current author guide.
