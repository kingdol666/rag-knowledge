# KBS Figure Redesign — QA Report

## Scope

- Staging directory only: `paper-kbs/figures/figure-redesign-20261112/`
- Canonical paper figures and LaTeX source were not replaced.
- GPT Image 2.6 outputs are visual-direction boards only; no generated bitmap is used as a scientific figure.

## Automated checks

- Six candidates built: 3 figures × 2 styles.
- Authoritative denominator asserted: gold n=72 for every arm.
- Asserted hits: A0/A0f/A0h/PD/A1b/A2/A3/read-all = 37/45/52/46/39/25/33/72.
- Recomputed per-arm trace rows: 72 gold rows per arm.
- Recomputed costs from `s4_traces_final.json` and matched `s6_stats.json` within tolerance.
- PDF: one page per candidate; full-width staging canvas; selectable text; Type-42-compatible font output; vector drawings present.
- PDF: zero raster image XObjects in all six candidates.
- SVG: native `<text>` retained; no `<image>` elements.
- QA artifact: `qa/vector_audit.json`.

## Visual acceptance status

- Figure A (design overview): PASS after separating the query ladder from the service/state columns; no label/arrow overlap at staging scale.
- Figure B (ingest-to-evidence): PASS; two swimlanes and three terminal states remain visually distinct.
- Figure C (latest results): PASS after moving the A0h–PD annotation inside the quality panel; direct hit labels, Wilson intervals, units, and proxy caveat remain visible.
- Contact sheet: `contact_sheet.png`.

## KBS recommendation

- **Preferred submission style:** Style 1 (clean editorial vector): stronger contrast, more conservative KBS/Elsevier appearance, safest for print and grayscale.
- **Alternative:** Style 2 (warm study-style vector): suitable for graphical abstract, presentation, or a more editorial front-page treatment. It is still native vector and semantically identical.
- Before replacing a formal manuscript figure, compile a staging manuscript copy and run the journal's final page-flow, caption, cross-reference, and overfull-box checks. This staging task intentionally did not edit the paper source.

## Known deliberate limitations

- Figure A intentionally uses no hardcoded port or tool-count claim because repository documentation and runtime configuration have drifted historically.
- Figure C intentionally uses authoritative `s6_stats.json` and `s4_traces_final.json`, not auxiliary `final_bench/viz` charts that mix n=76 probes or rounded byte displays.
- The retrieval-comparison and routing figures were not selected for this new three-figure core set: they rely on older/heterogeneous artifacts and have more severe logged-vs-derived or metric-conflation issues. They should be redesigned separately if retained in the final manuscript.
