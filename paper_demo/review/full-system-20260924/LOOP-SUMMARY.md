# Full-System Review Loop — 2026-09-24 (3 rounds, converged)

Paper: paper_demo/tex/main.pdf (CIKM 2026 Demo, sigconf). Monitored run:
experiment_chat_20260922-211000. Fact sheet: FACTSHEET.md (all numbers
artifact-locked). Reviewer JSONs in this directory.

## Round 1 — four seats (R1 systems 8.3 / R2 demo 7.5 / R3 methods 7.5 / DA audit 8.5, all minor)
3 P1 + 11 P2. Key catches:
- DA-1 (P1): Fig3 timeline boxes misstated traces in 5 places (e.g. BQ06-A
  claimed two-stage search that never happened; "kb_doc_read x3" vs real 2).
- R3-1/R3-2 (P1): BQ06 caption "matched no key facts" is an orthographic
  artifact — bare agent wrote hyphenated "precipitation-efficiency"; abstract
  9-vs-6 lacked the conservatism qualifier.
- R1-1 (P1): §4 called the 322 units "stored documents", colliding with the
  paper's own address space (parts).
- R2-1 (P1): demo video still shows the OLD 50-paper census on screen
  (50 papers / 165 documents / 8 KBs / 91 tools) — USER ACTION: re-record or
  slate. Not fixable in-paper.
- R1-5 (P2): Fig2 banner claimed "nine-point" while listing 7 items.

## Fixes applied after Round 1
Fig3 timelines fully counted from traces + builder gate upgraded from
non-empty assertion to exact count partition; fig2 banner count dropped then
re-annotated; §4 parts terminology; abstract qualifier + cost comparator;
score-5 flow clarified in §2.3 (verified against knowledgebase-search
SKILL.md); §3 points to Section 1's decisions + video pointer; "about three
minutes" latency bound; citation-metric + audit-granularity disclosure;
caption-pixel agreement fixes.

## Round 2 — four fresh seats (R4 AC 7.5 / R5 visual 7.5 / R6 line-editor 7.5 / DA2 delta 8.5, all minor)
- R4-1/R5-1/R6-1/DA2-1 (P0, unanimous): Round-1 additions pushed §4 body onto
  page 5, violating the <=4-page body rule. FIXED: ~15 lines reclaimed
  (caption trims, conservatism sentences merged, redundancy cuts,
  Fig3 0.92->0.885\textwidth); body ends p4, p5 = GenAI + refs only.
- DA2: 8/8 delta checks PASSED (Fig3 counts exact vs traces; grader regex
  provably fails across the hyphen; 7-4-1 invariant to the "table" branch;
  gate flow matches SKILL.md; no regressions).
- R5-2 (P1): 8 vs 9 check-count mismatch on p3 -> banner now lists 9
  countable recordings ("vector probe (×2)").
- R5-3 (P1): Fig3 strip columns unlabeled -> in-banner labels
  "A Platform · B Bare agent · C Dense".
- R6: 34 line edits applied (sentence splits, terminology, parallelism,
  articles, ties).
- R5-6 rejected: fully-bold captions ARE stock acmart (LinLibertineTB class
  default) — do not override.

## Round 3 — three fresh seats (V1 AC 8.5 ACCEPT / V3 verification 9.0 ACCEPT 9/9 / V2 visual 7.9 minor)
- V3: all 9 fix-verification checks passed, zero issues, no regressions.
- V1: acceptance-ready apart from user-pending author placeholders.
- V2-1 (P1): Fig3 smallest text tier ~5-6.5pt at 0.885\textwidth. RESOLVED AS
  DOCUMENTED TRADE-OFF: growing the figure back re-breaks the hard <=4-page
  body limit (the P0 four seats flagged); V2's own option (c) accepts
  screen-first legibility for the demo track. Revisit only if content is cut.
- V2-2 (P2): Fig1 caption enumerated "rewrite, cross-base recall" not shown
  in panels -> caption trimmed to match pixels. FIXED (final build).

## Final build state (2026-09-24)
- 5 pages: p1 abstract/§1, p2 Fig1+§2.2-2.3+§3, p3 Fig2+Table1+§4 start,
  p4 Fig3+§4 end, p5 GenAI+refs. 0 visible Overfull (one 1.327pt vbox on p5
  refs column, invisible). Figure gates all green (min fonts, no overlap/
  overflow/border-cross, vector PDFs, fonts embedded).
- All headline numbers re-verified against artifacts by two independent
  audit seats (DA + DA2) plus V1/V3 spot checks.

## Open items (user)
1. Author/affiliation/email placeholders (single-blind: real names required).
2. Demo video re-record against the 100-paper instance (on-screen census is
   stale), or add a slate; video README's own checklist anticipated this.

---

# Session 2 — Compact-figure build re-review (2026-09-24 02:xx, 2 rounds, converged)

Trigger: figures 2-3 compacted, body expanded, new §5 Conclusion added after the
first converged loop. Fresh panel on the new build.

## Round A — four fresh seats (F1 full 9.0 accept / F2 visual 7.5 / F3 methods 7.5 / F4 delta audit 9.0 accept 8/8)
- F2 P1s: Markdown·YAML chip 2px from band border (my redesign bug); fig3
  \Description claimed "295 kelvin" that the shortened excerpt no longer shows;
  fig2 legend wording fix had NOT been rebuilt into the PDF (caught).
- F3 P1s: §2.2 named read-back instead of BASE FIT as the misroute witness;
  §5 librarian sentence dropped the re-assessed cited-answer exit;
  "every number this paper reports" falsified by config constants
  (41 tools / 30k ceiling are repo facts, not run artifacts).
- All 13 fixes applied (incl. latency floor 10s→"about fifteen seconds" vs
  measured 13.8s; README quick-start reproduction pointer — verified README.md
  has a Quick start section; abstract baselines compressed; tool-call counts
  moved to the Costs paragraph; fig2 chips/alignment/legend rebuilt;
  fig3 quote typography normalized to curly+ellipsis wrapping).

## Round B — three fresh seats (G1 9.0 accept / G2 9.2 accept / G3 9.0 accept 10/10)
- G2 pixel-verified all five figure fixes (chip padding 27px symmetric, chain
  left-aligned x=55-56, legend wording, quote typography, badge uniformity
  52px×3 with even gaps).
- G3 verified all 13 text fixes against artifacts (C4_kb at 103_final_check.py:
  79; latency min 13.8s/max 174.0s; README Quick start; strip numbers
  re-derived; layout: body ends p4, p5 = GenAI + refs, 0 visible Overfull).
- G2-1 (P2, rejected-with-reason): inner straight quotes inside verbatim
  excerpts are part of the saved answers — normalizing them would break the
  verbatim-substring gates; reviewer concurs "safe to ship as-is".

## Verdict
All seats accept. Loop converged in 2 rounds (cap 4). User-pending items
unchanged: author placeholders; demo video re-record (stale 50-paper census).
