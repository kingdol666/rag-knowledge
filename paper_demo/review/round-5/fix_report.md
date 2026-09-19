# Round 5 fix report (2026-09-19)

Input: round-5/R1–R4 reviews (all minor_revision). Every issue adjudicated below.
Verified-then-fixed discipline: DA/R2 factual claims were checked against artifacts
before editing; R2-2 was rejected as a misread.

## Fixed

| ID | Fix |
|---|---|
| R1-3 (major) | §3 Demo setup now opens with the intended-audience sentence: "The demo targets IR practitioners and research-data administrators evaluating alternatives to folder trees, and agent builders wanting auditable retrieval tools." |
| R1-4 (minor) | `\acmConference` → CIKM '26 / November 2026 / Rome, Italy (running heads updated). |
| R1-6 (minor) | §1 Evidence bullet reduced to one clause + forward pointer; duplicate statistic stack removed. |
| R2-1 (major) | Legibility pass: fig1 metric names/values 25/23→28/26px, chips 24→27px, fine-print + scope rows culled into the caption; fig2 box labels 29/31→31/33px, band subtitles 22→24px, legend 28px; fig3 badges 21→24px, metric text 23/25→25/27px, BQ01 strip 20/22/23→23/25/25px, latency strip 27/30px (done in earlier judge loop); include widths 0.68/0.76/0.70→0.72/0.78/0.72. Smallest tier now ≫ previous 2.9pt. |
| R2-3 (minor) | Fig1 chip "165 parts" → "165 docs". |
| R2-4 (minor) | Fig2 phase-card heights 214→224px + bottom padding; "dedup" no longer touches the border. |
| R2-5 (minor) | Fig1 caption now narrates the BENCHMARK RUN strip; Fig3 caption narrates latency strip + BQ01 three-fates strip. |
| R2-6 (minor) | Table 1 caption reworded — "(7/10; 9/10 with confidence/blind-spot declarations counted, miss BQ10)" + "``--'' = not applicable" legend. |
| R3-1 (major) | Ref [16] CRAG 4th author corrected to Zhen-Hua Ling (arXiv:2401.15884). |
| R3-2 (major) | Root cause found: `verify_refs.py` had the wrong survey ID (2401.11804, a copula paper). Corrected to 2309.01219, added CRAG/MinerU/Kamath; all 12 arXiv-indexed entries re-verified 12/12 OK; `refs_verified.json` regenerated one-record-per-ID; bib header claim made truthful. |
| R3-3 (minor) | BGE-M3 title restored to full "…Through Self-Knowledge Distillation". |
| R3-4 (minor) | Chen Xu inserted in [17] author list (canonical order). |
| R3-5 (minor) | Data availability: classification.json path corrected (data/papers/), "rationale notes on the overridden assignments". |
| R3-6 (minor) | BM25 now cited: Robertson & Zaragoza 2009, FnTIR 3(4) (new ref [14]). |
| R3-7 (minor) | {Wen-tau} braces protected; EMNLP/ACL/ICLR booktitles expanded to full proceedings names. |
| R3-8 (minor) | Data availability: ingest_report.json flagged as a pre-tagging snapshot; final tag coverage pointed to graph_stats.json. |
| R4-1 (major) | §4: Track B characterization now evidence-bounded — self-reported file names, single agent call per question asserting rather than demonstrating reads; parametric-knowledge confound owned ("every track may partly draw… uncontrolled; the comparison isolates provenance and auditability, not accuracy"). |
| R4-2 (major) | §4 Setup states top-2 (~2.8k chars) packing; Results hedge the mechanism ("plausibly a chunking effect; chunk ranks were not logged") and disclose the sensitivity ("an internal top-10 packing run abstained 0/10, so the count is packing-sensitive"). Verified against track_bc.json (evidence_chunks=2, mean 2831 chars) and results/ANALYSIS.md (top-10 run 10/10). |
| R4-3 (major) | Honesty checks: "On-target judgments are our readings of recorded answers against pre-written gold answers … neither is independent." Scenario 2's 7/8 flagged "(an execution-LLM self-assessment, Section 4)". |
| R4-4 (minor) | Verified against skill_track_answers.json (BQ01 keyword is in Confidence, Blind Spots paraphrases): caption and Results now say "confidence/blind-spot declarations … only outside the Answer section". |
| R4-5 (minor) | Conclusion: "its abstentions being the very evidence-check the protocol makes explicit". |
| R4-6 (minor) | Harness ownership: "Our harness logs no chunk-to-document metadata (a reproduction limitation, not dense retrieval's)" in §4, Table caption, and fig3 card. |
| R4-7 (minor) | Fig1 chip "(2/2 solved this run)"; fig3 Track A "0 — the 2 gate-fails (of 10) rescued by the librarian". |
| R4-8 (minor) | §2.1: "the rest were not independently adjudicated, and every rationale is inspectable." |
| R4-9 (minor) | Miss questions named per count (BQ06 scripted; BQ01/BQ03/BQ10 live) in caption + Results. |
| R4-10 (minor) | Self-assessment flag moved to first gate-score use (Scenario 2). |
| R4-11 (minor) | Honesty checks: "Track A's answer-authoring time is uninstrumented: its row is retrieval plus reads, not end-to-end." |

## Rejected

| ID | Reason |
|---|---|
| R2-2 ("20k characters" on p1) | Misread. `sec2_system.tex` line 18 reads "(30k characters here)"; no "20k" exists in any source. No change. |

## Author-side (cannot be fixed from the repo)

| ID | Item |
|---|---|
| R1-1 | Video URL 404 — record/commit/push `paper_demo/video/qdcvr-demo.mp4` to master so the URL in the paper resolves. |
| R1-2 | Real author names/affiliations (single-blind). |
| R1-5 / R2-7 | Acknowledgments/funding placeholder text. |

## Space compliance

The fixes added ~15 lines to a page that had ~2 lines of slack. Recovered via a
systematic compression pass (~20 lines: §1 ¶1–¶3, §2.1–§2.3, §3 scenarios,
§4 Results/Honesty, captions) with zero numbers or citations dropped, plus the
shrunken figure canvases (footers culled). Final build: body incl. Conclusion +
Acknowledgments ends on p4; p5 = GenAI disclosure (+ Data availability) +
References [1]–[18]; 0 overfull; figures on p2/p3/p4.
