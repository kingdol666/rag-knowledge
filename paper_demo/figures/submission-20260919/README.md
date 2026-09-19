# Submission figure assets — 2026-09-19

All authored files are contained in this directory. Original drafts, manuscript TeX, source records, and other collaborators' files were not edited.

## Deliverables

- `fig1-concept.svg`, `.pdf`, `.png`: corrected reproduction configuration and unambiguous QDCVR-only outcome lane.
- `fig2-architecture.svg`, `.pdf`, `.png`: approved direction B with the audited separation between client surfaces, backend primitives, and agent-executed policy.
- `fig3-evidence.svg`, `.pdf`, `.png`: current saved BQ01 evidence and P2 rejection case, preserving paraphrase, provenance, and self-assessment caveats.
- `CAPTIONS.md`: proposed captions and integration caveats; no manuscript changes.
- `verification.json`: source assertions, frozen-input/audit fingerprints, runtime versions, text bounds, text overlaps, PDF geometry, embedded fonts, and vector checks.
- `*-pdf-proof.png`: rasterized **PDF** QA proofs, separate from the required PNG exports.
- `*-504pt-proof.png`: PDF previews rendered to 504-pixel width to inspect the intended print proportions (72-dpi preview; not the publication PNG).

## Rebuild

From the repository root:

```powershell
python paper_demo/figures/submission-20260919/build_figures.py
```

Dependencies: Python, `playwright` with its Chromium browser, and `PyMuPDF`; exact versions used are recorded in `verification.json`. No server, inference endpoint, or remote font is contacted. Calibri is used on this machine, with Carlito/sans-serif fallbacks. PDF fonts are embedded; an SVG rebuilt on another machine requires the same font for identical metrics. The script rejects text collisions/viewport clipping, unembedded PDF fonts, and raster PDF images.

`inputs/` contains frozen copies of the three approved drafts. These are reproducible source snapshots, **not corrected submission assets**: the old draft terminology is deliberately corrected by `build_figures.py`. Do not include the input snapshots in the paper. The build checks current source records and configuration defaults without executing benchmark code. Changes to the underlying evidence require a new audit, not merely a successful rendering.

## Geometry and readability

Each final SVG is 1000 × 590 px. Each PDF has one exactly trimmed 750 × 442.5 pt page. Include the PDF at 504 pt (approximately 178 mm), not at native width. At that scale, 14 px is 7.056 pt, 16 px is 8.064 pt, and 20 px is 10.08 pt. Figure 1 uses 14 px for compact branch labels and section glyphs; Figure 3 uses 14 px for section glyphs. Main prose is at least 16 px. Figure 2 is entirely at least 16 px. The publication PNGs are 2000 × 1180 px.

The required PDFs are browser-printed vector SVGs with selectable embedded-font text, **not PNG/screenshot wrappers**. SVGs include `role="img"`, title, and descriptive accessible text.

## Audit-driven corrections / integration learnings

1. Figure 1 now uses **≈800-token windows**, **pack 2 excerpts**, and **≤4,000-character evidence window**. The current script requests ten dense candidates; two excerpts are the saved packing result, not a top-2 retrieval setting. Source: `benchmark-suite/algorithms/corpus.py`, `methods.py`, `scripts/77_tracks_bc.py`, and the evidence audit.
2. Every Figure 1 gate outcome is inside the QDCVR lane. Initial ≥6 answers directly; initial 5 is retained as a P1 backstop, while ≤4 is discarded and fallback runs. Post-fallback branches explicitly distinguish P0 cited answers, usable P1 =5 attributed qualified answers, and no usable P0/P1 not-found reports. No arrow lands beneath the baseline.
3. Figure 2 explicitly labels **Agent-executed QDCVR skill**. Web HTTP and CLI setup/service management are not shown passing through MCP or through the gate. Agent routing/tag propagation is separated from deterministic split/index/store capabilities. Five bases are the demo configuration, not a fixed universal taxonomy.
4. Storage is **File tree + YAML metadata**, not an append-only audit log. No every-query logging claim, all-part tagging guarantee, or live-upload automatic-classification claim is made. The system audit reports a first-part-only MCP tagging/indexing issue; the diagram states the instructed agent workflow, not universal endpoint enforcement.
5. The diagram depicts the packaged skill's **0–8** rubric, **≥6 direct-answer** threshold, and **usable P1 =5 qualified-answer** option after fallback. The system audit's conflicting chat prompt threshold is not silently normalized into an implementation guarantee. Main should keep its distinction in the caption/body.
6. Figure 3 retains current BQ01 **8/8** and P2 **1/8**, current parts 1/2 (§3.2.3) and 2/2 (§7), declared unread positional formula/training details/benchmark scores, B's self-reported file source, and C's **2 chunks / 2,854 characters** with absent usable source metadata. These are selected saved-case records, not matched efficacy or independently judged accuracy.
7. No historical 7/8 case, 10/10 on-target scorecard, tag-count completeness assertion, invented UI, or new measurement is introduced.

Audit inputs: `paper_demo/review/submission-revision-20260919/EVIDENCE-AUDIT.md` and `SYSTEM-AUDIT.md`; prior case trace mapping: `paper_demo/figures/redesign-20260919/SOURCE-AUDIT.md`. The newer audits override the old manuscript/draft configuration wording. Rendering/source checks were performed locally; no independent reviewer approval or manuscript compilation is claimed.

## Independent content-review corrections

Applied the repairable figure findings in `paper_demo/review/submission-revision-20260919/CONTENT-REVIEW.md`, directly checking `.claude/skills/knowledgebase-search/SKILL.md` gate/tier/backstop clauses. Not-found now means **no usable P0/P1**, not merely no score ≥6. Figure 3 explicitly says **Tool records + agent-authored summaries; not an autonomous benchmark**, **Scripted probe record**, **Recorded: 1/8 / Agent judgment**, **Catalog census / 5 bases · 165 entries / 153 names retained**, and **Saved report: NOT_FOUND**. The predefined serializer judgment and retained census counts are checked from script AST and raw JSON without executing experiments. Captions and SVG descriptions preserve the difference between recorded judgments and autonomous decisions. No exhaustive document-body inspection or index-readiness verification is inferred from the catalog census. These edits address the figure findings but do not claim an independent re-review approval.
