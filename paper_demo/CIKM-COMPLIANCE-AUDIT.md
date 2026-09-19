# CIKM Demo compliance & style audit — QDCVR

Audited build: `tex/main.pdf`, 5 pages = **body 4 pp** (Abstract → §5 Conclusion +
Acknowledgments, per CFP "4 pages including appendices and acknowledgments") +
p. 5 carries only the GenAI Usage Disclosure (with the Data-availability paragraph)
and references — the two categories the CFP allows to overflow.
Reference set: the six CIKM demo papers in `reference/`; distilled rules in
[`FIGURE-STYLE-GUIDE.md`](FIGURE-STYLE-GUIDE.md).
Review loop: rounds 1–4 (3-reviewer loop, converged accept) + rounds 5–6
(4-seat panel: EIC / figures / citations-integrity / devil's advocate → fixes →
fresh 3-reviewer re-review). Round-6 verdicts: **R1 accept, R2 accept-with-minors
(all minors fixed), R3 accept**. See `review/round-5/` and `review/round-6/`.

## 1. Hard requirements (CIKM 2026 Call for Demo Papers)

| Requirement | Status | Evidence |
|---|---|---|
| ≤ 4 pages incl. appendices **and acknowledgments** | ✅ | §5 Conclusion + Acknowledgments end on p4; only GenAI disclosure + references on p5 |
| Unlimited references | ✅ | p5, [1]–[18] (BM25 added in round 5) |
| GenAI Usage Disclosure **before** references, outside the page budget | ✅ | `sec4_backmatter.tex`; Data Availability lives inside this block as "Data availability." paragraph (the reviewers' recommended reading of the CFP, which names only GenAI + references as exempt) |
| ACM **sigconf**, two column | ✅ | `\documentclass[sigconf]{acmart}` |
| CCS concepts + keywords | ✅ | p1, three CCS concepts + 6 keywords |
| **Single-blind** — real names required | ⚠️ | `Author Name` / `Affiliation` are placeholders; **must be filled before submission** |
| 3-minute demo video, URL in the paper | ✅ | URL present (abstract + Data availability); video re-cut to 176.9 s and **pushed to master — URL verified HTTP 200 (2026-09-19)** |
| Funding + competing-interest disclosure | ⚠️ | "Competing interests: none declared." written; funding line is still a placeholder |
| Intended audience | ✅ | §1 last paragraph |
| Innovative aspects | ✅ | §2.3 three named contracts (reading replaces scoring; content-induced bases; failure as first-class output) |
| Contribution to SOTA | ✅ | §4 + Fig. 3 three-track comparison |
| What attendees will experience | ✅ | §3, first sentence of each scenario |
| Functionality & user scenarios | ✅ | §3 Scenarios 1–3 |
| Interface / interaction options | ✅ | §2.1 three entry surfaces (web console / CLI / MCP), §3 demo setup; console walkthrough live in the video |
| Comparison with existing systems | ✅ | §1 related work + Fig. 1/Fig. 3 measured comparisons |
| **R&D challenges** (review criterion) | ✅ | §2.3 three operational failures → contracts |

## 2. Layout — one figure per page (user-required, 2026-09-19 build)

| Page | Content |
|---|---|
| p1 | Title, abstract, CCS, keywords, §1 + contribution bullets, §2 opening |
| p2 | **Fig. 1** (teaser: dense RAG vs. QDCVR, scope-labeled latency strip) + §2.1–§2.3 |
| p3 | **Fig. 2** (architecture + live query trace) + §2.3 tail, §3 Scenarios 1–3, §4 opening |
| p4 | **Fig. 3** (three answering tracks) + Table 1 + §4 + §5 Conclusion + Acknowledgments |
| p5 | GenAI Usage Disclosure (+ Data availability) + References |

Mechanics: a `figure*` is eligible only from the page **after** the one being
typeset when LaTeX meets it. Fig. 1's block sits after `\input{sec1_intro}`,
Fig. 2's block deliberately mid-§2.2 in `sec2_system.tex`, Fig. 3's block after
`\input{sec3_demo}`. Moving source blocks moves the figure; do not cluster them.

Caption discipline follows the six reference papers: full-sentence captions,
every panel and callout explained, scope notes ("scopes differ") inside the
figures, `Figure N:` never abbreviated.

## 3. Figure aesthetics (post-review fixes)

- **Fig. 1**: bottom scoreboard now has one scope line per metric — latency
  annotated "dense: end-to-end · KB: retrieval + evidence reads" (2.4 s, rounded
  from 2.38), abstentions annotated "dense: 2 abstentions · KB: 2 gate-fails
  rescued" so the fallback column cannot be misread as rescuing the baseline's
  drops (round-4 R1/R2 issues). Footer enlarged.
- **Fig. 2**: layer-label chips sit above the wires (no more line through
  "AGENT & PROTOCOL LAYER"); legend/footnote enlarged to 28 px.
- **Fig. 3**: LATENCY PER QUESTION strip labels/values enlarged to 27–30 px —
  an acceptance-pass judge initially misread the 24 px rows, so legibility was
  fixed rather than argued; footer condensed and enlarged; "2.4 s" everywhere.
- All three figures re-renderable: `capture_*.py` → HTML → `shot.py` (now always
  appends `#static` so animation particles never freeze into the PNG).

## 4. Outstanding before submission

1. ~~Push the repo so the video URL resolves~~ **done 2026-09-19** — video live on
   master, `blob` and `raw` URLs return HTTP 200; closing-card repo URL inside the
   video also corrected (was `kingdol/…`, a 404) and duration re-cut to 176.9 s.
2. **Author names and affiliations** — single-blind, placeholders must go.
3. **Acknowledgments / funding** — placeholder text on p4 (fits; replacing the
   bracket line with real text of similar length is safe, longer text needs a
   recompile check).
4. **`\acmConference`** — running head now reads CIKM '26 / November 2026 /
   Rome, Italy; confirm exact dates at camera-ready and re-enable the ACM
   reference/ISBN/DOI block.

## 5. Round-5/6 content hardening (devil's-advocate-driven)

- Track B characterized by what traces support: self-reported file names, one
  agent call per question, reads asserted not demonstrated; uncontrolled
  parametric-knowledge confound owned for all tracks.
- Track C: top-2 packing stated, abstention mechanism hedged ("plausibly a
  chunking effect; chunk ranks were not logged"), top-10 packing sensitivity
  disclosed (internal run: 0/10 abstentions); missing chunk metadata owned as a
  harness limitation.
- Honesty checks extended: on-target judgments are author readings against
  pre-written gold keywords (not an independent judge); Track A's
  answer-authoring time uninstrumented (its row is retrieval + reads).
- BQ01/BQ03 keyword location corrected to confidence/blind-spot declarations;
  all 12 arXiv-indexed references re-verified via arXiv API (one wrong survey ID
  and one fabricated-looking author caught and fixed); classification.json path
  and ingest_report.json pre-tagging snapshot noted in Data availability.

## 6. Verdict

| Aspect | Verdict |
|---|---|
| Hard CIKM 2026 demo requirements | **passes**, modulo the author-side placeholders (names, funding, video push) |
| Page budget | **passes** — body incl. conclusion + acknowledgments = 4 pp; p5 = GenAI disclosure + references only |
| One figure per page (p2/p3/p4) | **passes** |
| Content completeness | system functions, architecture, protocol, scenarios, evaluation, honesty checks all present and artifact-sourced; all headline numbers re-verified against `benchmark-suite/results/` (B: 35.5–165.3 s mean 78.8; C: 5.8–28.6 s mean 12.2, retrieval 0.59) |
| Typesetting | 0 overfull boxes, 0 undefined references, 0 LaTeX errors; underfull glue only in the p5 file-name paragraph (backmatter, cosmetic) |
| Visual acceptance | judge pass on all 5 rendered pages (p4 re-verified after latency-strip fix) |
