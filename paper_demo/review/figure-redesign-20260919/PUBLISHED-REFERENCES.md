# Published CIKM references: visual evidence and redesign guidance

Research date: 2026-09-19. Findings persisted from the completed read-only investigation; no additional research performed. Actual PDF pages were rendered and visually inspected, not inferred from abstracts. Recommendations below are design judgments, not venue requirements.

## Publication evidence and version caveats

Official sources:
- Accepted papers: https://cikm2025.org/program/accepted-papers
- Proceedings: https://cikm2025.org/program/proceedings
- Awards: https://cikm2025.org/program/awards

**CyberBOT: Ontology-Grounded Retrieval Augmented Generation for Reliable Cybersecurity Education**
- Official accepted-list entry **de5994**; official proceedings link to https://doi.org/10.1145/3746252.3761478 ; official awards page names it **Best Demo Paper**.
- Inspected PDF: https://arxiv.org/pdf/2504.00389 ; record: https://arxiv.org/abs/2504.00389 (v2, 2025-09-03).
- IMPORTANT: ACM PDF access returned HTTP 403. The inspected author PDF is **14 pages**, titled “CyberBOT: Towards Reliable Cybersecurity Education via Ontology-Grounded Retrieval Augmented Generation.” Its record states CIKM 2025 acceptance and links the published DOI. Publication is independently verified, but figure identity and pagination against the ACM camera-ready were NOT verified. Treat its visuals as author-version examples, not evidence of CIKM page-budget/layout conventions.

**AppAgent-Pro: A Proactive GUI Agent System for Multidomain Information Integration and User Assistance**
- Official accepted-list entry **de4922**; official proceedings link to https://doi.org/10.1145/3746252.3761473 .
- Inspected PDF: https://arxiv.org/pdf/2508.18689 ; local copy: `reference/cikm-demo__2508.18689__appagent-pro-a-proactive-gui-agent-syste.pdf`.
- The five-page author PDF bears the CIKM ’25 running header. Publication was independently verified; this was not a byte-for-byte comparison with the ACM version of record.

**DeepRead is not a verified CIKM exemplar.** The retrieved https://arxiv.org/abs/2602.05014 record identifies v3 (2026-02-12); the PDF describes the work as preview/in progress. These retrieved sources do not establish a confirmed conference venue. Do not infer CIKM publication from ACM-like typography. Detailed DeepRead inspection was handed back to the user; the side task concentrated on the two verified CIKM works above.

## Actual visual observations

### AppAgent-Pro: rendered PDF pages 2–4

- **Figure 1, p2:** full-width landscape architecture at page top. Concrete cat-care query and direct/proactive answers on the left; two horizontal sequences of actual phone screenshots on the right. Short stage labels: Comprehension, Execution, Integration. Pale-blue connectors and an explicit return path bring results back to integration. Grey grouping backgrounds, yellow answer areas, blue modules, cartoon icons, and screenshots coexist: not monochrome.
- **Figure 2, p3:** two stacked dashed-outline lanes, Shallow Execution and Deep Execution, start with the same guitar-learning query. Shallow is nearly linear; deep branches into three searches and has a feedback loop. Red outlines mark selected screenshots. Workflow topology, rather than only evaluative prose, conveys the contrast.
- **Figures 3–4, p4:** single-column real-interface composites. Red boxes and arrow labels identify running log, answer, execution state, query information, and proactive answer. Captions explain left/middle/right panel geometry.

Source: https://arxiv.org/pdf/2508.18689

### CyberBOT: rendered author-PDF pages 2, 3, 11

- **Figure 1, p2:** compact functional loop on white, with small colored component icons. UI, Intent Interpreter, Retriever, Knowledge Base, Generative Model, Ontology Verifier, and Learning Record are explicitly named. Edges identify Query, Search, Retrieve, Prompt, Raw Answer, Validated Answer, and Summarize & Store. Generation and validation are distinct; validated output returns to the UI.
- **Figure 2, p3:** five worked-example text panels in two columns: Student, Intent Interpreter, Retriever, Generative AI, Ontology Verifier. Thin colored borders and faint diagonal hatching distinguish roles. Concrete original/rephrased questions, passages, generated answer, and verification record appear. The verifier exposes `validation_result`, `confidence_score`, and `reasoning`, rather than only a checkmark.
- **Figure 4, p11:** light-blue composite with numbered setup, web-UI, and learning-log areas. Callouts identify history, multi-turn interaction, and validation behavior. A real JSON/log response occupies the lower portion. This links visible interaction to backend records. Its full-page footprint belongs to the extended author version and is not a four-page-demo layout precedent.

Source: https://arxiv.org/pdf/2504.00389

## Recommendations tied to the current local figures

Visually inspected: `figures/fig1_protocols.png`, `figures/fig2_architecture_v2.png`, `figures/fig3_answers.png`.

1. **Figure 2 first: fix control-flow readability.** The current linear gate → fallback chain implies fallback always runs. Show pass → cited answer; fail → fallback → re-verification; exhausted search → NOT_FOUND. Attach the floating storage-access arrow to actual endpoints. Label edges with transmitted artifacts (candidate passages, read evidence, gate result, answer + citations, trace record), borrowing CyberBOT’s explicit edge semantics. Keep offline/online grouping; move long explanations and benchmark counts to caption/body. Show trace persistence as a connected output.
2. **Figure 3: distinguish evidence from commentary.** Separate recorded output from author interpretation. Use short verbatim excerpts and explicit provenance/gate fields; do not present summaries as quotations. Add one real UI/trace crop with numbered callouts. Compress the failure case to query → near miss + gate → recorded verdict. CyberBOT’s structured verification panel and AppAgent-Pro’s annotated screenshots are useful precedents.
3. **Figure 1: show the mechanism, not only the conclusion.** Fill or remove the large gap between pipeline boxes and outputs. Show a compact chunk/evidence object in each lane and connect it to the answer. Prefer “Dense-RAG baseline used in this demo” over a universal claim about conventional RAG. Mark the left answer as illustrative unless replaced by a recorded excerpt. Reduce slogans; retain the shared-question framing. AppAgent-Pro Figure 2 demonstrates comparison through branching and iteration.

## Limits on inference

- No palette overhaul is justified: pastel regions, icons, colorful screenshots, and callouts are observed author choices, not mandated CIKM style.
- Do not derive universal rules such as “Figure 1 must be architecture,” “all figures are full-width,” or “one figure per page” from this small sample.
- The local `FIGURE-STYLE-GUIDE.md` is not venue policy; its evidence labels require publication/version checks. Local filenames calling later preprints “CIKM demos” do not establish publication.
- Priority: correct Figure 2 semantics → expose Figure 3 evidence → simplify Figure 1. Keep readable labels, redundant role naming, and inspect the final printed-size PDF.