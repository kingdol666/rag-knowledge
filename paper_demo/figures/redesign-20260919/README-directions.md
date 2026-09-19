# Fig.2 direction gate — 2026-09-19

These are three design drafts, not a paper replacement. Select A/B/C before producing a final figure.

- `gallery.html`: standalone local gallery, all three architecture SVGs inline; Chinese explanations and browser-only preference buttons.
- `direction-a.svg` / `.png`: horizontal academic process, two explicit decision gates.
- `direction-b.svg` / `.png`: offline/online swimlanes, one gate and explicit librarian-to-read retry loop.
- `direction-c.svg` / `.png`: numbered modules, central evidence store and vertical branching protocol.
- `generate.py`: deterministic SVG/HTML generator plus local Chromium rendering and browser checks.
- `verification.json`: fresh machine-readable test results.

Run from any directory: `python <this-directory>/generate.py`.
Requires Python and the installed Playwright Chromium runtime. No network access is needed during generation/rendering. Running the script overwrites only its own three SVGs, three PNGs, gallery, and verification report. Other collaborators' files are only read to discover available companion illustrations.

## Source and protocol notes
Read `../../tex/sec2_system.tex` and `../fig2_architecture_v2.html`. Corrected the old visual's misleading linear gate → fallback → answer sequence and all-clients-through-MCP wording. No metrics were copied. Initial evidence passing at ≥6 goes directly to a cited answer. Only no-pass initial retrieval invokes librarian shelf scan and targeted re-search; new candidates are read/rechecked before either answer or not-found. Not-found names scope, near miss and reason. Optional BM25/graph and lifecycle are outside the mandatory benchmark answer route.

## Print and visual notes
SVG width 1000, minimum text 14 px, typical body 16 px. Target full 178 mm double-column width: roughly 7.1 pt minimum / 8.1 pt body. Do not reuse the old 0.78 text-width scaling. Every diagram has accessible title/description and native editable text/shapes, no foreignObject or remote assets. All three revised drafts are landscape 1000 × 560 (height/width = 0.56), below the 0.62 limit. At 178 mm full width their figure height is 99.68 mm, excluding the paper caption. The old poster title, oversized access header, full rubric and answer-section lists have been removed from the figure; explanatory detail lives in gallery captions. Body text remains 16 px, never uniformly scaled down.

White page, fine strokes, restrained pink offline / pale yellow online groups in A/B. Document and cylinder glyphs are semantic objects, not raster illustrations. The reference description supplied by the user informed grouping; no claim is made to independently inspect the external DeepRead figure.

## Verification and learned constraints
Rendered actual standalone SVGs with local Playwright Chromium at 2× and visually inspected all three initial exports. Corrected text/connector interference in A, the B retry path and C's return-to-answer connector. Browser checks cover XML parsing, minimum font, canvas text bounds, absence of foreignObject, zero external requests, zero script errors, preference selection/persistence and mobile page overflow. These checks are not a full independent peer review or physical print proof. LSP tooling is unavailable; Python execution and browser checks are the relevant validation here.

Companion Fig.1/Fig.3 drafts are owned by another collaborator. Gallery links and available previews do not imply approval or selection of an architecture direction. No original paper files were edited by this work.

## Landscape reviewer correction
Rebuilt A as two horizontal bands, B as compact side-by-side swimlanes, and C as an evidence-centered numbered branching layout. Added native section/paragraph hierarchy glyphs. All three have compact access strips and offline/online panel labels, no visible QDCVR poster title. PNGs are 2000 × 1120. Font, canvas bounds, aspect ratio, local preferences and offline rendering checks rerun after the revision. No original paper or companion figure files changed.

## Companion figure source notice
Original Fig.3 mixed runs. Current BQ01 is 8/8 with parts 1/2 + 2/2; archived BQ01 is 7/8 with parts 11/26 + 25/26. Current drafts use the current run only; the source audit is separate. This notice reflects the source-audit context supplied by the user; this implementation pass does not independently re-audit benchmark artifacts.

Reference inspection status supplied by the review lane: DeepRead v3 is a preprint, not verified as a CIKM publication. AppAgent-Pro and CyberBOT are published CIKM 2025 works, inspected through author PDFs; the CyberBOT PDF is an extended 14-page version, not the camera-ready version. Local audit links: `../../review/figure-redesign-20260919/DESIGN-REVIEW.md` and `../../review/figure-redesign-20260919/PUBLISHED-REFERENCES.md`. No external imagery is used.
