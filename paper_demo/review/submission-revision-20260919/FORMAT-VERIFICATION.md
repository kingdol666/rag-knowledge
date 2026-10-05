# FORMAT VERIFICATION — CIKM 2026 Demo PDF

**Scope.** Independent final PDF/layout/format verification only. No manuscript content was edited. Source PDF checked: `tex/main.pdf` (SHA-256 recorded in `layout-check/machine-check.json`). Verification date: **September 19, 2026**.

## FINAL metadata-only refresh — September 19, 2026

**FORMAT PASS retained for the final PDF.** This section supersedes the earlier PDF identity below; earlier full visual inspection and isolated build results remain historical evidence for the pre-date-correction version, not claims that the new file was independently recompiled.

- Final `tex/main.pdf` SHA-256: **`05309a06454887a461a75245c57342f4df567f62ea0c15dbf4ed9943f3516182`**, independently computed and matching the supplied package target.
- File size: **600,973 bytes**; **5 pages**, each **612 × 792 PDF pt (US Letter)**.
- `main.tex` differs from the independently compiled source in exactly two lines: `acmConference` and `acmBooktitle` now use **November 9–11, 2026**, replacing November 9–13. The new date is present in the PDF ACM reference format and running conference headers. No old November 9–13 date remains in the inspected date lines.
- All scientific section files, bibliography, and three figure PDFs retain their previous SHA-256 values. Only `main.tex` and `main.pdf` changed among the frozen manuscript inputs.
- Body and artifact statement still finish on **page 4**. Page 5 still contains only GenAI disclosure continuation and references (apart from running headers/page number).
- Video link annotations on page 1 and public repository link on page 4 are unchanged and correctly embedded. This is a link-target check, not a new network availability test.
- Freshly read final build log reports **5 pages / 600,973 bytes**, one **1.452 pt overfull vbox**, three underfull vboxes, and no undefined-reference/citation or hbox warning. Thus “no other warning” should not be read as absence of the three underfull diagnostics. The final compile was performed by the writer; this refresh did **not** run another independent build.
- Re-read the corrected local `VENUE-REQUIREMENTS.md`: it now distinguishes main conference November 9–11 from tutorials November 7/workshops November 8, removes the unsupported two-paper reviewer threshold, and records the Demo CFP portal `my/conference?conf=cikm26`. This refresh verifies the local correction and PDF metadata, not a new independent live-policy audit. Reviewer nomination remains an author action; no two-paper threshold is imposed by this report.
- Author placeholders, author approval, and authorized submission status remain unresolved. No submission-readiness or acceptance guarantee is made.

Machine evidence: `layout-check/final-metadata-refresh.json`, including current hashes, source diff, page geometry, extracted date lines, links, page-4/5 text, and text-span geometry comparison. Original renders/build are preserved rather than relabeled as a new build. No manuscript file was edited during this refresh. Package copy itself has not been inspected; its hash must equal the final hash above.

---

## Bounded verdict

**FORMAT PASS (bounded).** The frozen five-page PDF is visually and geometrically clean for the requested ACM `sigconf` layout: US Letter, unchanged ACM margins, double-column body, three latest submission figures, selectable/vector figure content, embedded fonts, resolved citations, and body content confined to pages 1–4 with GenAI disclosure/references extending onto page 5. The 1.452 pt overfull vbox is a minor bottom-page balancing/fit condition and is not visibly harmful: no clipping, overlap, missing glyphs, or column collision was observed in the rendered five-page inspection.

This is **not** a submission-readiness or acceptance guarantee. The known author metadata/eligibility blockers remain below.

## Evidence

| Check | Result | Command/source | Output/evidence |
|---|---|---|---|
| PDF page count and page geometry | PASS | PyMuPDF `fitz` machine check | 5 pages; every page `[0,0,612,792]` pt = US Letter. |
| Visual inspection | PASS | `fitz` render at 2x + manual inspection of `page-1.png` through `page-5.png` | No clipping, overlap, black boxes, broken glyphs, or column collisions. Figure captions and transitions are visible. Page 4 ends body prose and starts GenAI disclosure; page 5 continues disclosure and contains references. |
| ACM layout/margins | PASS | `tex/main.tex`, isolated compile `main.log` | `\documentclass[sigconf]`; geometry reports `paperwidth=614.295pt`, `paperheight=794.96999pt`, `textwidth=506.295pt`, `textheight=626pt`, horizontal parts `54/506.295/54pt`, vertical top `57pt`; no manual geometry/font/spacing override found. Render is visibly ACM double-column. |
| Body-page limit | PASS | Rendered pages + source section order | Scientific body occupies pages 1–4. GenAI disclosure begins at the end of page 4 and continues on page 5; references are page 5. This matches the supplied official CFP snapshot and venue requirements: body/appendices/acknowledgments ≤4 pages, with GenAI disclosure and references excluded. |
| Figures: latest source match | PASS | SHA-256 freeze check + embedded PDF inspection | All three included files are `figures/submission-20260919/fig1-concept.pdf`, `fig2-architecture.pdf`, and `fig3-evidence.pdf`; source hashes were unchanged during verification. Each appears once in the final PDF on pages 2–4. |
| Figure captions/descriptions | PASS | `main.tex` and `figures/submission-20260919/CAPTIONS.md` | Each figure has a caption and `\Description`; visible captions match the current figure content and explicitly bound claims (workflow/configuration, agent policy, recorded cases, non-benchmark limitations). |
| Figure text/vector quality | PASS | PyMuPDF page/resource inspection and visual render | Main PDF has zero raster images reported by `get_images()` on all pages; figures are included as PDF XObjects, with selectable text and vector drawing content. Source figure PDFs contain selectable text/drawings. No rasterized figure text was observed. |
| Font embedding | PASS | PyMuPDF `extract_font` over all referenced fonts | 19 font records; all extracted font streams have non-zero bytes. Includes ACM body fonts and embedded Calibri figure fonts. |
| Physical readability | PASS with minor note | 2x render inspection + text-span size inventory | Body text is visually readable. Figure labels are readable at full width. Smallest text is concentrated in references/metadata and approximately 6.9–7.0 pt; no figure label is clipped. This is acceptable for this format check, though authors may choose to enlarge tiny reference/figure annotations if desired. |
| Overfull/underfull behavior | PASS, non-blocking warning | Fresh isolated compile log | One `Overfull \\vbox (1.452pt too high)` and three `Underfull \\vbox` messages. The 1.452 pt condition is not visibly harmful: page 4/5 content remains inside the page, with no collision or clipping. No `Overfull \\hbox` warning. The warnings are disclosed, not hidden. |
| Independent isolated build | PASS | New isolated temp tree under `review/submission-revision-20260919/layout-check/isolated` | `pdflatex` pass 1 exit 0; `bibtex` exit 0; pdflatex passes 2–4 exit 0. Fresh rebuilt pages had identical pixmap samples to the frozen PDF for all five pages. Main files were not rewritten. |
| Citations/references | PASS | Fresh isolated build log + extracted PDF text | BibTeX exit 0; no undefined-citation/reference warning found in the fresh log; references are present on page 5 and readable. |
| Video/repository links | PASS | PyMuPDF PDF link extraction | Video link is embedded and resolves to the public repository path `github.com/kingdol666/rag-knowledge/blob/master/paper_demo/video/qdcvr-demo.mp4`; artifact repository link is embedded on page 4. Link presence was verified; live availability was not re-tested as part of this local layout pass. |
| Type/LSP diagnostics | N/A | No source-code/type-check change in this verification lane; no `lsp_diagnostics_directory` tool exposed in the current tool surface | LaTeX/BibTeX compile is the applicable independent build check. No claim of a codebase-wide LSP clean result is made. |

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Read and apply the official CFP snapshot and venue requirements. | VERIFIED | `official-cfp-snapshot.txt` and `VENUE-REQUIREMENTS.md` were read. Checks applied: ACM `sigconf`, non-anonymous/single-blind, ≤4 body pages, disclosure/references exclusion, video URL, artifact link. |
| 2 | Inspect all five rendered PDF pages independently. | VERIFIED | Rendered and manually inspected `page-1.png` through `page-5.png`; no harmful clipping/overlap or unreadable layout defect observed. |
| 3 | Confirm body/artifacts end within four pages; only GenAI disclosure and references extend. | VERIFIED | Page 4 contains the end of scientific body and starts disclosure; page 5 contains disclosure continuation and references only. Artifact statement is in body and ends on page 4. |
| 4 | Confirm latest three figures and caption/description alignment. | VERIFIED | All three `submission-20260919` PDFs are embedded, hash-stable, displayed once, and aligned with their current captions/descriptions. |
| 5 | Confirm readable physical font sizes, vector figure text, and embedded fonts. | VERIFIED | Visual inspection plus PyMuPDF resource checks: no raster page images; PDF XObjects/drawings for figures; 19 font streams embedded; smallest text is localized to references/metadata and remains readable. |
| 6 | Confirm ACM Letter/sigconf margins remain unchanged. | VERIFIED | Source uses `sigconf` with no geometry override; fresh log reports ACM Letter dimensions and 54 pt left/right text margins. |
| 7 | Resolve citations and verify links. | VERIFIED | Fresh BibTeX/LaTeX build exits 0 with no undefined-citation warnings; video and public repository links are present in the PDF. |
| 8 | Assess the 1.452 pt overfull vbox rather than hide it. | VERIFIED | Fresh log records it; rendered pages show no clipping/overlap. Classified non-harmful but retained as a disclosed warning. |
| 9 | Do not claim submitted-ready status despite known author blockers. | VERIFIED | This report gives only a bounded format PASS and lists unresolved author blockers below. |

## Remaining author blockers / non-format blockers

- **Author identity metadata remains placeholder text:** `Author Name`, `Affiliation`, `City, Country`, and `author@example.com` are still present in `main.tex`. This is incompatible with a real non-anonymous submission until replaced and author consent/ownership is confirmed.
- **Reviewer-volunteer requirement remains unverified:** the venue record requires at least one author to nominate/volunteer as reviewer; eligibility and nomination were not verified here.
- **Submission timing/status is unresolved:** the local venue record states the June 6, 2026 full-paper deadline and August 23, 2026 camera-ready deadline have passed as of September 19, 2026. Authors must establish whether this is an authorized revision, already-submitted/accepted work, or a future-venue draft; no late-submission eligibility is inferred.
- **Scientific/content acceptance is outside this pass:** figure/source factual synchronization, claim correctness, reproducibility, and venue acceptance remain subject to the content reviewer and authors.
- **The 1.452 pt overfull vbox is non-blocking visually but remains a log warning.** If a warning-free build is required, authors should make a small layout adjustment and rerun this independent check; do not alter the frozen PDF solely to conceal the warning.

## Files produced

- `review/submission-revision-20260919/layout-check/page-1.png` through `page-5.png`
- `review/submission-revision-20260919/layout-check/machine-check.json`
- `review/submission-revision-20260919/layout-check/isolated/` (independent compile workspace and logs)

**Overall verification verdict: FORMAT PASS, bounded to PDF/layout/format evidence. No acceptance guarantee and not submitted-ready until the author blockers are resolved.**

## Quantitative follow-up (same frozen inputs)

`layout-check/comparison-results.json` records these additional independent results:

- Embedded figure content streams are **byte-for-byte equal** to the content streams of the current source figure PDFs, for all three figures. This is stronger than matching filenames or modification times.
- At the actual full-column-span placement, minimum figure text sizes are **7.062 PDF pt (Figure 1), 8.071 PDF pt (Figure 2), and 7.062 PDF pt (Figure 3)**. These meet the local editorial target of approximately 7 pt; this is not a venue-specified figure-font minimum.
- The installed `acmart.cls` selects **9 TeX pt** for sigconf. This corresponds to approximately **8.966 PDF pt** before font-expansion transforms. The body span inventory clusters near that value (approximately 8.876–9.056 PDF pt with microtypographic transforms); there is no source body-font reduction.
- Last-page reference/disclosure text bottoms are **291.506 PDF pt in the left column and 270.783 PDF pt in the right column** (coordinates measured from the top). Both lie far above the footer near 718 PDF pt. The final columns are not exactly equal-height; their 20.723 pt visible bottom difference does not create overlap, clipping, or a page-limit issue. The **1.452 TeX pt overfull vbox** is about **1.447 PDF pt**, not a page-edge overflow. Its exact internal TeX box cause was not instrumented; visual/geometric safety, not an assertion that the columns are perfectly balanced, is the basis of the bounded PASS.
- All five rebuilt page rasters are exactly equal to the frozen main PDF at the comparison rendering scale. All frozen main TeX/Bib/PDF and three figure-PDF SHA-256 hashes remain unchanged.
- Manual rendered-text inspection and the source placeholder search found only the already-known author metadata placeholders; no additional visible TODO/TBD, fake DOI/ISBN, credential-like string, or unresolved citation marker was observed. This is a bounded manuscript inspection, not a repository-wide secret/security audit.

**Regression risk:** replacing author metadata, adding acknowledgments, or revising captions/prose can reflow the page-4 boundary. Repeat the full compile and page-4/5 checks after any such edit. Current content-review approval and video-claim synchronization remain outside this lane.
