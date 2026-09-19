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
SVG width 1000, minimum text 14 px, typical body 16 px. Target full 178 mm double-column width: roughly 7.1 pt minimum / 8.1 pt body. Do not reuse the old 0.78 text-width scaling. Every diagram has accessible title/description and native editable text/shapes, no foreignObject or remote assets. The three tall drafts prioritize protocol legibility; the selected direction can be compacted later to fit the paper's final height budget.

White page, fine strokes, restrained pink offline / pale yellow online groups in A/B. Document and cylinder glyphs are semantic objects, not raster illustrations. The reference description supplied by the user informed grouping; no claim is made to independently inspect the external DeepRead figure.

## Verification and learned constraints
Rendered actual inline SVGs with local Playwright Chromium at 2× and visually inspected all three initial exports. Corrected text/connector interference in A, the B retry path and C's return-to-answer connector. Browser checks cover XML parsing, minimum font, canvas text bounds, absence of foreignObject, zero external requests, zero script errors, preference selection/persistence and mobile page overflow. These checks are not a full independent peer review or physical print proof. LSP tooling is unavailable; Python execution and browser checks are the relevant validation here.

Companion Fig.1/Fig.3 drafts are owned by another collaborator. Gallery links and available previews do not imply approval or selection of an architecture direction. No original paper files were edited by this work.
