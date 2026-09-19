## Verification Report

### Verdict
**Status**: FAIL
**Confidence**: high
**Blockers**: 4 repairable items before finalization: two P1 manuscript/figure corrections, one P2 contribution clarification, and one P2 venue-checklist correction. Author-supplied submission blockers are separate below.

Independent CONTENT-only review, September 19, 2026. This reviewer did not author or revise the manuscript, bibliography, figures, code, or results. The only file written is this report. Scope is a defensible scholarly initial draft—not conference acceptance, production readiness, human author attestation, or authority to submit after the deadline. No new LLM, retrieval, ingestion, or indexing experiments were run.

### Evidence
| Check | Result | Command/Source | Output |
|-------|--------|----------------|--------|
| Fresh artifact consistency tests | mixed | Read-only Python JSON/AST checks executed during this review | Five factual checks passed: 9/10 saved snippet outcomes; 50/5/165 census; BQ02 part/score/gate; C excerpt counts/2,854 characters; three NOT_FOUND records. Three stronger hypotheses failed, as described below; one affected sentence was concurrently corrected. |
| Types | N/A | No software edits; lsp_diagnostics_directory unavailable | Not a TypeScript/software verification pass. No clean-LSP claim. |
| Build | not independently rerun | Current main.log and current PDF inspected; pdftotext run by reviewer | Current log reports 5 pages, 596,596 bytes; remaining 1.152pt overfull vbox. Earlier 2.8831pt hbox disappeared during the concurrent update. Read-only restriction precluded a new compiler output set; this is not independent build approval. |
| Runtime | partial | Actual scripts, API handlers, MCP definitions, packaged skill, saved JSON, compiled PDF text, figure PDFs/proofs | Source-supported capabilities and saved examples checked; no new live arbitrary-query or attendee-upload validation. |
| Venue | verified discrepancy | Live GET of official CIKM demonstration CFP | Four-page body allowance, disclosure/reference exclusions, single-blind sigconf, three-minute video target, author reviewer nomination, and closed dates confirmed. Local venue checklist incorrectly says no duration specified. |
| Freshness | bounded | SHA-256 manifest at end | sec2_system, sec4_eval and main.pdf changed during review; changed sections and current PDF text were reread. Figures remained unchanged. Any subsequent edit invalidates blanket reuse of this verdict. |

Original local sources read: all seven requested TeX files, refs.bib, compiled main.pdf text, SYSTEM-AUDIT, EVIDENCE-AUDIT, REFERENCES-AUDIT and VENUE-REQUIREMENTS. Assertions were also checked against actual implementation/results rather than inherited from these audits. Figure proof images were visually inspected and their wording checked against text in the compiled PDF. No full video content/playback review is claimed.

### Acceptance Criteria
| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Human-readable administrator-to-demo story | VERIFIED | Abstract and Sections 1–3 coherently connect organizing a paper collection, inspecting answer evidence, and investigating a near miss. Audience and interaction surfaces are explicit. |
| 2 | Specific scholarly contribution differentiation | PARTIAL | Related work is acknowledged, but the three contribution bullets are generic capabilities; the integration challenge and boundary versus closest work remain implicit. P2-1. |
| 3 | Current services separated from agent obligations | PARTIAL | HTTP endpoints correctly distinguished from skill behavior; universal upload/tagging and append-only logging claims removed. However, the actual score-5 fallback branch is absent from the claimed skill policy and figures. P1-1. |
| 4 | Numerical claims correct and scoped | PARTIAL | 50/5/165, 9/10 snippet result, BQ02 0.709/8, and C two abstentions supported. Figure 3's apparent 165-document librarian inspection is stronger than retained scope evidence. P1-2. |
| 5 | No equal-baseline or efficacy claim | VERIFIED | Section 4 discloses answer-bearing rewrites, different windows/configurations, missing B read events, C logging loss, unknown per-answer models, cache uncertainty and unavailable A end-to-end time. No new accuracy or speed superiority claim found. |
| 6 | Abstract/demo promises match observed evidence | PARTIAL | Abstract's nine snippet passes and existence of three reports are sound. It does not promise guaranteed correctness. Saved probe reports nevertheless need explicit scripted/adjudicated provenance so they are not mistaken for observed autonomous online decisions. P1-2. |
| 7 | Figure PDFs and captions faithfully represent code/results | PARTIAL | Baseline budget, approximate token windows, selected BQ01 text and reconstructed section references are supported. Figures 1–2 omit an answer-permitted fallback branch; Figure 3 overcompresses scope/provenance. P1-1/P1-2. |
| 8 | References and venue format support an initial draft | PARTIAL | Eight references rendered; no unresolved citation markers found in inspected PDF. DeepRead's live primary abstract supports the locate/read comparison. Scientific text and Artifacts finish on page 4; page 5 contains references. Local venue record has a correctable video-rule error. |
| 9 | Independent final-build/live-demo verification | MISSING | No independent build or live harness test was run in this read-only content pass. Existing build artifacts are evidence of the writer's build, not this reviewer's fresh build. |
| 10 | Author-owned submission prerequisites identified | VERIFIED | Explicit placeholder author/affiliation/email remain. Submission eligibility, author consent, reviewer nomination and final responsibility are not supplied or attested by this review. |

### Gaps

**P1-1 — The depicted packaged skill has the wrong terminal decision boundary.** Risk: high. Locations: sec2_system.tex, final paragraph; main.tex Figures 1–2 captions/Descriptions; fig1-concept.pdf and fig2-architecture.pdf (and their editable sources/caption notes).

The initial >=6 fast-exit threshold is correct. It is not the only score that can support a final answer. The actual `.claude/skills/knowledgebase-search/SKILL.md:158–161,219–226,256` retains score 5 as a P1 backstop, permits adopting it with attribution, and expressly says to answer from that backstop if fallback produces nothing better. Total failure requires no usable P0/P1 evidence. Figure 2 routes “After fallback: none passes” from a diamond defined as “any >=6?” straight to Not found; Figure 1's footer/caption similarly presents >=6 as the sole pass condition. This suppresses a real weak-evidence answer branch. Disclaiming agent compliance does not repair an inaccurate statement of the instructions themselves.

Suggestion: distinguish the initial direct-answer criterion from post-fallback eligibility; show/describe a qualified score-5 backstop answer and reserve not-found for no usable P0/P1. Alternatively identify a genuinely different restricted demo policy, but do not call it the current packaged skill without supporting evidence. Synchronize PDF graphics, captions, accessible Descriptions, and Section 2. No new experiment is needed to correct the description.

**P1-2 — Saved probe judgments and librarian scope are presented too much like observed autonomous runtime outcomes.** Risk: high. Locations: sec4_eval.tex paragraph 2, sec3_demo.tex scenario 3, main.tex Figure 3 caption/Description, fig3-evidence.pdf lower row; abstract terminology should be reconciled with the clarified provenance.

`75_skill_track_phase1.py` collects evidence and leaves adjudication/composition to the executing agent. `76_skill_track_phase2.py:17–40` selects BQ06/BQ10 through a fixed QID table, not a runtime gate. `80_honest_probe_judge.py:29–77,94–116` contains predefined JUDGMENT and REPORT tables, a fixed absence finding, and an unconditional NOT_FOUND verdict. It serializes saved agent-authored judgments; it does not measure an online agent deciding whether to abstain. The result file labels the judgments as the executing agent's, which is compatible with agent authorship of these constants, but does not establish a fresh runtime decision event. “Self-assessment, not independent judgments” alone leaves this distinction unclear. The three reports exist; their existence is not three measured successful autonomous abstentions.

There is also a concrete retained-scope limit missed by the earlier audits: `79_honest_probe_e2e.py:63–73` counts all returned catalog entries but saves only the first 60 names per base, each truncated to 90 characters. Recounting all three raw probe records gives (count, retained names) = (72,60), (43,43), (32,32), (6,6), (12,12): 165 catalog entries, only 153 retained names. No per-document body reading of 165 items is evidenced. The librarian routine calls `kb_get_documents`, not a fresh per-document index-readiness check. Separate graph/corpus snapshots support the 165 collection count, not exhaustive semantic inspection or index verification by this step. Figure 3's “Librarian scan / 5 bases · 165 indexed docs” visually collapses these distinctions.

Suggestion: explicitly identify the probes as script-collected retrieval/catalog evidence plus recorded agent-authored rubric judgments and templated reports. Distinguish catalog census from retained inspection evidence, and label the figure count as collection/catalog scope, not exhaustive content checking. Keep not-found as a scoped recorded judgment, not proof of absence. State that arbitrary live queries are a planned skill-guided interaction, not validated by these serialization scripts. This is a provenance correction, not a request for new LLM experiments.

Concurrent correction acknowledged: the earlier Section 4 assertion “Track A follows the QDCVR protocol” became “Track A pairs tool-execution records with saved QDCVR answers” during review. The new version is materially better. Do not restore the old statement: BQ10 still has additional Phase 2 evidence despite its saved score-7 fast-exit label. That failed consistency hypothesis is not a new unresolved objection to the replacement sentence.

**P2-1 — Contribution differentiation needs one concrete integration argument.** Risk: medium. Location: sec1_intro.tex related-work paragraph and contribution list.

The narrative is readable, relevant to a demo track, and no longer makes an untenable new-retriever superiority claim. However, parsing/tagging, reusable skills, and saved retrieval records are capabilities rather than a precise explanation of the demonstrated technical contribution. The phrase “complements these approaches” does not identify the specific integration problem solved. DeepRead already makes document-native locate-then-read behavior central; retrieval judgment and adaptive processing are already credited to Self-RAG/CRAG. The case for this demo therefore needs to rest on the actual collection-management/evidence-inspection integration, not implied invention of those individual ideas.

Suggestion: make explicit which administrator operation and technical integration this system adds, and distinguish that scope from retrieval-controller methods, structural document navigation, and ontology-grounded domain verification. Tie it to the actual attendee action and stored artifacts. Do not claim competitors categorically lack these capabilities, firstness, new ranking theory, or effectiveness unsupported by the selected traces. No extra benchmark or blanket novelty guarantee is required.

**P2-2 — Correct the venue checklist before relying on it as final submission guidance.** Risk: medium. Location: VENUE-REQUIREMENTS.md, video bullet (supporting documentation, not a demonstrated manuscript failure).

The official demonstration CFP fetched during this review explicitly requests a three-minute demo video. VENUE-REQUIREMENTS says it does not specify a hard duration, while REFERENCES-AUDIT correctly records the three-minute target. Record the actual target without inventing an organizer tolerance. The earlier audit reports a 176.94-second video; this review did not remeasure or attest video content, and the rule discrepancy does not itself show that video violates the target. The official CFP submission link also differs from the local checklist link; use the current official destination rather than certifying either stale portal URL by inference. Only the report was changed here.

Primary sources consulted live: official CIKM 2026 Demonstration Papers page (host cikm2026.diag.uniroma1.it, path /demonstration-papers/), and DeepRead arXiv:2602.05014v3. Web search/open produced no usable page content; direct primary-source GET supplied the text.

**Author-supplied external blockers — not manuscript-edit failures.** Names, affiliations, email, author consent/responsibility, required author reviewer nomination, and any authorized submission/revision route require the authors. The official deadlines are May 30, 2026 (abstract), June 6, 2026 (full paper), August 7, 2026 (notification), and August 23, 2026 (camera-ready). They precede this September 19, 2026 review. An initial draft can be scholarly-ready while still ineligible for ordinary CIKM 2026 submission; do not imply a late-submission entitlement. Human authors must confirm disclosure accuracy, artifact rights and final presentation arrangements. No acceptance probability or guarantee is offered.

**Additional bounded checks / regression risks.** The universal automatic-upload, all-part tagging, immutable audit-log and equal-baseline claims are absent from the current prose. Actual `kb-mcp/server.py` AST count is 94 decorated tools / 41 kb_* tools. Search handlers return candidates without a rubric. The create wrapper's first-document-only tag/index behavior remains a reason to preserve the current per-part checking caveat. The dense implementation requests ten candidates, truncates each text to 1,400 characters, and packs a 4,000-character budget; saved rows pack two excerpts. BQ01's A part/section references are reconstructed evidence labels, not a verbatim final-answer citation; Figure 3 currently states that distinction correctly. Its B formula and C abstention/2,854-character labels match current records. Keep “C reports” and “Declared unread” qualifiers: these are not independent validation of unsaved context or actual reading behavior.

Avoid turning the 30,000-character part target into an exact hard bound including synthesized headings, or heading context into validated original-PDF coordinates. Live attendee ingestion can change the corpus: preserve the distinction between saved fixed-corpus examples and any new live query. After revisions, recheck all three rendered PDFs and Descriptions, page-4 body boundary, links, and current source/PDF hashes. The remaining small overfull vbox is a layout-owner follow-up, not newly classified here as a scientific-content blocker.

### Recommendation
REQUEST_CHANGES
The initial draft is substantially more readable and appropriately bounded than the prior audit targets, but the skill decision boundary, probe provenance/scope, and contribution explanation need correction before scholarly-initial-draft approval; final submission additionally requires author-owned prerequisites and an independent final build check.

Snapshot fingerprints (SHA-256; final read of this report's inspected files):

- `paper_demo/tex/main.tex`: `c63dea73377fd0902b4d29cd31402e02e67f5208a944f95e2d28106d49918dca`
- `paper_demo/tex/sec0_abstract.tex`: `86dec0ea1e94f80a30d9b1a2daa703a3bd18d56419a8f50a7ecdfe4a93384fea`
- `paper_demo/tex/sec1_intro.tex`: `697625f3e15f9a6b8d8d175eafe5cf303dbab26c79bd43226c216d82ed1efd3a`
- `paper_demo/tex/sec2_system.tex`: `0d6ea1600279562a112ec3e450a890c3c0b0ed5c98d8497e62b396d54ad6a800`
- `paper_demo/tex/sec3_demo.tex`: `ce6b6bd86e4436901af0c77b2f20696821cb99f4f2780f737f6f45cb6eba4be2`
- `paper_demo/tex/sec4_backmatter.tex`: `19a6c2ba5b6b4d413a31c83ddf687817f02e4fad83f3adca32aae4d2f63ac4e2`
- `paper_demo/tex/sec4_eval.tex`: `1dcfe647d6a11954395c0573189265ed440ab21e01f015a590b17825d5156a86`
- `paper_demo/tex/refs.bib`: `42f94fb3537283fe5d4fea0ceffb0f1c7e54ecb10c70a9c31f14dcfbbd4b9a47`
- `paper_demo/tex/main.pdf`: `272f8d422e924cbad65ce18a461ebcdfb9ac1510c61e2e28877fa6f93237b482`
- `paper_demo/figures/submission-20260919/fig1-concept.pdf`: `0b568f06b798769379e497566b9ad8f1d8dce68d5511e8d498d5509a73c77ab2`
- `paper_demo/figures/submission-20260919/fig2-architecture.pdf`: `2e3fa11410765a3c2e0e9d452a04b34047761067371b188b58b8a35f6373d541`
- `paper_demo/figures/submission-20260919/fig3-evidence.pdf`: `a3bc9d9999662360db6460b8baec15a2b12a3805f9344df5f3e2e068ebc18421`
