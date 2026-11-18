HMRS manuscript sources (2026-11-19, 69 references)
==================================================

Open main_20p.tex as the root document. Compile with pdfLaTeX and BibTeX.
For example: latexmk -pdf -interaction=nonstopmode -halt-on-error main_20p.tex
Use main_20p_review.tex for a double-spaced length check from the same text
and figures. The double-column layout has 17 pages; the double-spaced layout
has 42, exceeding KBS's 20-page recommendation including figures and tables.

Compile supplementary.tex separately with pdfLaTeX (or latexmk -pdf).
The companion supplementary-inventory.pdf contains Tables S1-S8. The
editable inventory source and its Pandoc support files are included. To rebuild:
  pandoc supplementary-inventory.md -s --lua-filter=supplementary-inventory-paths.lua -H supplementary-inventory-header.tex --pdf-engine=pdflatex -o supplementary-inventory.pdf

The shareable CSVs include 532 arm/question records for the latest seven-arm
rerun (504 in-domain, 28 out-of-domain). The frozen, November 12 follow-up and
separate floor records are historical. Use python -I -B verify_archived_labels.py
for offline label recomputation; see README-archive-verification.md for limits.
The exports do not establish end-to-end replay or semantic answer validity.
The dated figure-redraw manifest documents historical assets. The Overleaf ZIP
root SHA256SUMS covers the actual package members except itself. The Editorial
Manager ZIP has a separate manifest because manuscript files are flattened.

Editorial Manager: identify editable manuscript sources (.tex, .bib, .bbl)
and standalone figure PDFs in the flat archive. Upload supplementary.pdf,
supplementary-inventory.pdf, shareable experiment_data files and the highlights
DOCX as separate items as appropriate. The single-column Word files are editable
companions; citations/references and figure numbering are not dynamically linked.

This is a draft with author placeholders, not an approved submission.
See SUBMISSION-FILL-IN.md for author details, funding, CRediT and disclosures,
including confirmation of provenance and journal eligibility of figure prototypes.

