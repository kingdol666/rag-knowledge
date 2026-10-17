# Page budget under the KBS submission formats (2026-10-16)

Measurement record for the 2026-10-16 assessment
(`review/KBS-PAPER-ASSESSMENT-2026-10-16.md`, recommendation P0-1). The KBS
Guide for Authors asks for "preferably no more than **20 double line-spaced
manuscript pages** (including tables and figures)". Two builds were measured.

| build | source | class options | pages | notes |
|---|---|---|---|---|
| camera-ready preview (layout of record) | `paper-kbs/tex/journal_20p/main_20p.tex` | `[final,5p,times,twocolumn]` | **20** | all `_postcheck.ps1` gates pass: 0 overfull, 0 undefined, every float cited, figures ≥ 7 pt effective |
| review format (Elsevier double-spaced) | `paper-kbs/tex/journal_20p/main_20p_review.tex` | `[review,12pt]` | **68** | 0 errors; 6 "Overfull \hbox" warnings: four are the wide float tables tuned for the two-column measure (the lane table, the management-functions table, the answer-quality table and Table 3's block (b)), and two are sub-12 pt line overflows from the same tables. They remain legible and the build has no errors; see the file header |

Rebuild commands:

```bash
# camera-ready preview + gates (PowerShell, TeX Live on PATH)
powershell -ExecutionPolicy Bypass -File paper-kbs/tex/journal_20p/_postcheck.ps1

# review format (page-count measurement only)
cd paper-kbs/tex/journal_20p
pdflatex -jobname=main_20p_review main_20p_review.tex && bibtex main_20p_review
pdflatex -jobname=main_20p_review main_20p_review.tex   # twice
```

## Measured content

- words: **14{,}361** total, **12{,}892** excluding the reference list
  (`pdftotext` on `main_20p.pdf`, after the 2026-10-17 restructure)
- references: 54 entries (`refs.bib` 35 + `refs_new_verified.bib` 19)
- floats: 8 figures, 7 body tables; 5 further tables moved to the supplement on
  2026-10-16 (Part D, Tables S1-S5); Figure 10 was removed on 2026-10-17
  because Table 5 carries the same six methods
- abstract 235 words; highlights 5 × ≤ 85 characters

## What the numbers mean

The double-spaced page holds roughly 230-260 words at 12 pt with the elsarticle
`review` spacing, so a 20-page target corresponds to about **5,000 words**.
Reaching it from the current 11,800 body words would require deleting or
relocating more than half of the evaluation. That is not a compression task;
it is a different paper.

Three options, in the order this project should prefer them:

1. **Submit the two-column build as the manuscript.** KBS permits
   double-column LaTeX; the 20-page limit is stated as a preference, and the
   camera-ready build is exactly 20 pages. This is what `submission-20p/`
   packages today. Risk: an editorial "please shorten" request.
2. **Submit the `review` build (68 pages) with a short cover-letter note** that
   the evaluation is a deployment case study whose evidence is carried by the
   tables and by the supplementary material, and offer the compression plan
   below on request. Risk: the same request, later.
3. **Compress toward 20 double-spaced pages only if asked**, using the plan
   below; it buys on the order of 10-12 double-spaced pages, not 48.

## Compression plan (if the editor asks)

Ordered by words saved per unit of damage to the argument. Items 1-3 preserve
every headline claim; each names where the evidence still lives.

1. **Move E2's operation-by-operation detail to the supplement** (~450 words):
   the lifecycle-scenario walk-through and the tag-registry paragraph reduce to
   a two-sentence summary plus Table S5. Evidence stays in Part A/B of the
   supplementary material.
2. **Compress E5b** (~400 words): keep the transport failure, the repair and
   the honesty battery headline (18 arms, zero fabricated citations, both
   honest behaviours); move the per-arm transcript forensics (2 KB preview,
   74.9 KB catalog, shelf-size boundaries) to the supplement, which already
   carries the campaign.
3. **Move the E6 second-signal replay to the supplement** (~350 words): keep
   one sentence ("an independent NLI checkpoint fails on the same pools,
   Hit@5 0.3125") and cite Part B.10/B.11; the same-pool verdicts are
   unchanged.
4. **Collapse Figures 6 and 10** (~1 page): Figure 10 (six-method matrix) can
   be a table row set; Figure 6(b) restates Table 2's derived rows.
5. **Trim E4's paraphrase and margin paragraphs** (~300 words) to the numbers
   and the conclusion; the sweeps stay in the supplement (B.3, B.4).
6. **Shorten Section 3** (~250 words): the data-model paragraph duplicates
   Table S1.

Items 1-6 total roughly 1,750 words plus one float page, i.e. about 7-9
double-spaced pages. Reaching 20 would additionally require cutting Section 2
to a third, dropping E3 and E8 entirely, and reducing the evaluation to
headline tables only — a materially weaker paper, which is why option 1 or 2
is recommended instead.
