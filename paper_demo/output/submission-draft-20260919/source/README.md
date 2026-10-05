# Submission-oriented QDCVR draft

## Build

From `tex/`, run `pdflatex main.tex`, `bibtex main`, then `pdflatex main.tex` three times. On Windows, `BUILD-DRAFT.ps1` automates these steps. Tested with TeX Live 2025, pdfTeX, acmart v2.12. The standard `sigconf` body font, columns and margins are retained.

The supplied vector figure PDFs are sufficient to build; no Python, browser, image-generation API, or benchmark rerun is needed. Editable SVG originals are included in `figures/submission-20260919/`. Their source and assertions live in the working repository's figure build script; rerunning that script requires the audited repository artifacts and Python/Playwright, and is not necessary for paper compilation.

## Draft status

The scientific manuscript is a demonstration/operational-evidence draft, not a general performance benchmark. Recorded judgments, scripted examples, and independent measurements are distinguished. Do not restore retired accuracy, latency, automatic-enforcement or exhaustive-audit claims without new evidence.

The author metadata is explicitly a placeholder. Replace it with the agreed real names, affiliations, emails and author order; CIKM Demo is single-blind. Confirm disclosures, funding/acknowledgments, artifact rights and the required author reviewer nomination. Recompile and recheck the four-page body budget after these changes.

The repository's existing ~177-second video is linked, but its narration/screens must be synchronized with the revised scope, current score records and scripted-example provenance before submission. The paper does not establish video-content approval.

CIKM 2026's ordinary deadlines have passed as of 2026-09-19. Use only an authorized submission/revision route, or retarget to a later venue after checking that venue's rules. This package does not certify eligibility, acceptance, human review or camera-ready production metadata.
