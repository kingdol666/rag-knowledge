# CIKM Demo-Track Figure / Table / Visual Style Guide

> Evidence base: 6 published CIKM demo papers (2025–2026) in `reference/`,
> 14 figure captions + 8 table captions. Derived by reading the plain-text
> extractions: captions, in-text references, table cells and section order are
> **directly stated**; colour, rule style, fonts and aspect ratio are **inferred**
> (text extractions cannot show them).

## 1. Per-paper exhibit inventory

| Paper | System type | Figs | Tbls | Exhibits |
|---|---|---|---|---|
| AppAgent-Pro (2508.18689) | Proactive GUI agent; Streamlit + mobile apps | 4 | 0 | F1 3-stage architecture (Comprehension/Execution/Integration) tracing "How to keep a cat"; F2 shallow-vs-deep execution; F3/F4 three-column Streamlit screenshots |
| JustEva (2509.12104) | LLM legal-fairness toolkit; Vue3+Python/Stata | 1 | 1 | F1 whole-system architecture; T1 3 LLMs × 5 fairness metrics |
| SearchLog (2606.05040) | Chromium extension + local Flask server | 3 | 2 | F1 client↔server workflow; F2 stored-data schema tree; F3 raw JSON event log; T1 feature matrix vs 6 tools (✓/–); T2 validation summary |
| SAFE-Cascade (2606.19646) | Cost-adaptive OCR/VLM router; Streamlit | 2 | 3 | F1 architecture + 5 UI panels + cost/latency; F2 threshold operating frontier; T1 main results (Acc/95% CI/VLM%/Cost); T2 router outcomes; T3 threshold sweep |
| PolyUQuest (2607.08269) | Structure-aware graph web-RAG | 2 | 1 | F1 framework overview (offline indexing + online retrieval); F2 UI composite: chat w/ citations (left), 3 mode traces (top), evidence panels (bottom right); T1 results + ablation w/ token costs |
| PrismaDV (2608.09376) | Compound-AI data-unit-test synthesis; web UI | 2 | 1 | F1 real Polars code + assumption graph + Deequ test + deployment pass/fail; F2 six-panel UI, callouts 1–6; T1 detection quality P/R/F1 |

*Caveat:* AppAgent-Pro's index comment claims 5 figures; only 4 captions survive extraction.

## 2. Figure archetypes

**A — Full-width architecture / pipeline (6/6, always Figure 1, top of p.2).**
Left→right named stage boxes, inputs left, artifact right, UI/deployment layer at
the bottom.

> "Figure 1: The architectural workflow of AppAgent-Pro, structured around a
> three-stage pipeline: Comprehension, Execution, and Integration."
> "Figure 1: SAFE-Cascade system architecture and processing workflow. The system
> exposes the same stages to users: chart/question input, OCR evidence, text-only
> answer, router decision, and final answer with estimated cost/latency."
> "Figure 1: Framework Overview of PolyUQuest"

**B — UI screenshot composite with numbered callouts (3/6).** PrismaDV 1–6;
PolyUQuest (1)(2)(3); AppAgent-Pro cropped Streamlit columns.

**C — Query traced inside the figure (3/6).** A real query string printed in the
diagram ("How to keep a cat"; "What subjects are in the AIDA secondary major for
BEng Mechanical Engineering?").

**D — Schema / data-structure tree (1/6).** SearchLog F2.

**E — Raw code / JSON listing as a figure (2/6).** SearchLog F3 (6-word caption);
PrismaDV F1 embeds Deequ code.

**F — Trade-off curve (1/6)** — the only quantitative figure (SAFE-Cascade F2).

## 3. Caption conventions

`Figure N: <3–7-word noun-phrase title>.` + 1–4 present-tense sentences. Never
"Fig."; colon and terminal period always. **Bimodal length**: 90–125 words for
architecture/UI figures, 5–10 words for schema/code figures. Structure first,
then mechanism, reusing the body's exact stage nouns. Composite geometry is
narrated explicitly; **every callout number is explained**. Result figures state
a takeaway.

> "The left column presents the reasoning process and execution log; the middle
> column shows the integrated output…; the right column displays the real-time
> mobile phone screen."
> "The selected configuration θ = 0.3 achieves 69.1% accuracy with 73.1% VLM
> invocation."

Figure captions sit **below** figures; table captions **above** tables (all 8).

## 4. Table conventions

Row entity = compared method; baselines first, **proposed system last among the
compared rows**, directly above ablations. Cost/latency columns are
near-mandatory, with ↓ arrows. Caption = title + scope/N + legend + takeaway.

> "Table 1: Main results and ablation on PolyU-Web (300 questions). Q. Tok.:
> average LLM tokens per query; B. Tok.: total offline build tokens; '–': no
> offline build phase."
> "Table 1: Detection quality… Best F1 score in bold, second best underlined.
> PrismaDV outperforms all baselines by a large margin of more than 20 points."

Precision discipline: 1 decimal for %, 3 decimals for normalised scores, comma
thousands. Every abbreviation defined (in caption *and* prose). Booktabs =
[INFERENCE].

## 5. Section structure template

Unnumbered Abstract (~150–200 w) → CCS Concepts → Keywords → ACM Reference Format
→ numbered body (5 pp typical; ~1 p references).

1. **Introduction** 0.7–1 p, ends with contribution bullets or bold run-in leads.
2. **Related Work / Positioning** 0.3–0.5 p — present in only 3/6; the rest fold
   it into the Introduction.
3. **System** 1.5–2 p, 2–4 subsections, naming exact models/APIs.
4. **Demonstration** 1–1.5 p, always scenario-shaped (3 scenarios or 3 stages).
5. **Conclusion** in 4/6 (SearchLog "Final Remarks"; PrismaDV none).

Back matter: GenAI Usage Disclosure 5/6, Acknowledgments 3/6, repo/demo-video URL 6/6.

## 6. Actionable design rules

1. Figure 1 = full-width architecture at top of p.2. **[EVIDENCE 6/6]**
2. Box labels reuse the body's stage nouns. **[EVIDENCE]**
3. Trace one real query verbatim through the diagram. **[EVIDENCE]**
4. Show the produced artifact (JSON / answer) inside the figure. **[EVIDENCE]**
5. Number UI panes 1…N, explain each in the caption, re-cite in prose. **[EVIDENCE]**
6. One accent colour per semantic role, always with a redundant label. **[EVIDENCE]**
7. Narrate composite geometry in the caption. **[EVIDENCE]**
8. Caption pattern + bimodal length. **[EVIDENCE]**
9. Takeaway number in result-figure captions. **[EVIDENCE]**
10. Table caption = scope + N + legend + takeaway. **[EVIDENCE]**
11. Proposed row last among compared, above ablations. **[EVIDENCE]**
12. Cost/token column with ↓ arrows. **[EVIDENCE]**
13. State and apply the bold/underline convention. **[EVIDENCE]**
14. 95% CI column; no significance claim when CIs overlap. **[EVIDENCE]**
15. One threshold/trade-off curve with the chosen operating point annotated. **[EVIDENCE]**
16. Target 2–3 exhibits/paper, ~1 per content page. **[INFERENCE]**
17. ~2:1–3:1 landscape, wide boxes, short labels, one dominant arrow direction. **[INFERENCE]**
18. Near-monochrome palette, greyscale-print-safe. **[INFERENCE]**

## 7. Do-not list

1. Never an exhibit without an in-text reference (all 22 are cited).
2. No standalone results bar/line charts in the body — charts live inside the toolkit UI.
3. No colour-only encoding.
4. No "Fig." abbreviation, no untitled caption, no missing final period.
5. No undefined symbol/abbreviation in a table.
6. No unhedged performance claim.
7. No full-desktop/full-browser screenshots — crop to panels/columns. **[INFERENCE]**
8. No vertical rules / dense gridlines; no two tables answering the same question. **[INFERENCE]**
