---
title: "Supplementary Material: Complete Inventory of System and Retrieval Test Evidence"
subtitle: "Companion to the Knowledge-Based Systems manuscript draft"
---

# Supplementary Material: Complete Inventory of System and Retrieval Test Evidence

**Reading note.** This inventory preserves campaign records and Tables S1--S8.
The older manuscript, appendix and supplement sources cited below are archival,
not the revised manuscript or its separate figure supplement
(Figures S1--S7 and Tables S9--S17). Section A.20 records the earlier route-card
protocol; the revised manuscript and figure supplement report the later
scoped configurations. The later runner could use the gold domain to resolve
candidate references for A0, A1b and A3, which limits their evidence-pack
comparisons. Neither set of records establishes a causal navigation benefit
or semantic answer accuracy.

This document is the complete inventory of the functional, system-level and retrieval
evidence produced for this project. The manuscript reports its test campaigns in prose
and in a small number of summary tables; the material here is everything else: whole
campaigns that the manuscript only summarises in a sentence, the full retrieval
configuration matrix, and the campaigns whose results are negative, null or unmeasured.

**Provenance rule.** Campaign numbers below are taken from the cited artifacts.
References such as A.7 / Src 1 resolve to exact paths and run identifiers in the
separate `supplementary-inventory-source-map.md` file. Where an explicitly identified
re-analysis or correction is provided, its scope is stated.
Where an artifact is internally inconsistent, the inconsistency is stated rather than
silently resolved. Where an artifact reports `null`, `NOT measured`, or a failed check,
that is reproduced as such.

**Naming key.** P/F/D denote the three answer interfaces (run tracks a2/b/c);
the revised manuscript calls the D chunk arm C. R1--R3 and S1--S3 are historical
retrieval-lane and deployment-arm labels used in the archived campaigns below; they
are not the current manuscript's experiment numbers. Archived tables that predate
this key retain their original A/B/C labels.

**Scope.** All results come from a single self-hosted instance on the authors' machine,
driven through the official harness API and the project's own MCP tool layer. The
counts of test cells are given per campaign so the reader can judge the weight of each
result. Part C states the limitations that apply across all of the evidence. Part D
contains supporting tables S1-S8 and later campaign records; the manuscript's
Data-availability statement points to this document for the campaign inventory,
per-question results, and lifecycle and ablation tables.

---

## Part A. System-level test campaigns

Each subsection states what was tested, at what scale, the headline result with the
actual numbers, and the artifact references.

### A.1 Eighteen-scenario end-to-end harness campaign

**What was tested.** The full agent surface, in three independent stages, against the
live deployment: Stage A drove the agent/chat surface with the platform's native engine
across 7 scenarios (retrieval, honest refusal, ingest, post-ingest recall, cross-library
retrieval, experience creation, second ingest plus graph); Stage B ran 5 scenarios plus
1 verification on a second engine; Stage C ran 5 scenarios on a third engine.

**Scale.** 18 scenarios in total. Every scenario was scored on three axes: gold-document
hit, answer correctness, and hallucination.

**Headline result.** 18/18 PASS, every gold document hit, zero hallucination.

Stage A (native engine, 7 scenarios), wall / engine seconds, turns, cost:

| Scenario | Wall (s) | Engine (s) | Turns | Cost (USD) |
|---|---:|---:|---:|---:|
| A1 retrieval | 140.1 | 137.4 | 4 | 1.77 |
| A2 honest refusal (K8s canary) | 105.9 | 104.1 | 3 | 1.25 |
| A3 ingest | 97.9 | 96.1 | 2 | 0.98 |
| A4 post-ingest recall | 53.8 | 51.9 | 9 | 1.18 |
| A5 cross-library (CoRoT) | 142.1 | 140.3 | 6 | 1.83 |
| A6 experience creation | 50.5 | 48.6 | 2 | 0.87 |
| A7 second ingest + graph | 175.9 | 173.9 | 2 | 1.80 |

The A6 case report states that experience `exp-d6f4d47ae3d6` was created and later
ranked first by global experience search. The successful raw response was not located,
so this is a report-level observation; it does not establish a local-vector score of
0.711 for that retrieval. Stage B (second engine) gave 52.4 s / 8 turns / $0.25 (retrieval),
40.3 s / 7 / $0.36 (cross-library), 45.9 s / 8 / $0.30 (refusal), 23.2 s / 5 / $0.13
(ingest, deduplicated: `true`), 30.5 s / 6 / $0.15 (second ingest, vector 0.747), and
25.0 s / 5 / $0.11 (verification). Stage C (third engine) gave 112.0 s wall (47.3 s
engine) / 3 turns / $0.065, 101.2 (48.0) / 6 / $0.042, 171.4 (82.7) / 9 / $0.058,
74.6 (41.9) / 5 / $0.040 (vector 0.834) and 33.5 (15.0) / 2 / $0.027.

Five findings are recorded by the campaign itself: (i) per-scenario cost differs by one
to two orders of magnitude between the three surfaces; (ii) on the third engine, wall
time is roughly twice engine time because of a 50-90 s harness cold start; (iii) the
streaming frames carry bare `data:` payloads with no event names; (iv) one document
ingested through the third engine had no graph node (graph overview reported
`doc_count` 2 where 3 documents existed); (v) diagnostic prompts trigger a six-skill
pre-check that was killed at 30 s, so production calls need an explicit timeout.

**Artifact.** Campaign summary (A.1 / Src 1).

### A.2 Archived three-lane stability suite, 27 runs

**What was tested.** Three retrieval behaviours (vector-first, catalogue-first, hybrid)
crossed with three question types and repeated over three rounds, through the chat API
in its default non-streaming mode.

**Scale.** 3 tasks x 3 stability lanes x 3 rounds = 27 runs. The three tasks were: a question whose
answer is fully in the corpus (attention formula), a question the corpus verifiably does
not cover (seismic-wave classification), and a question about something that plainly
does not exist (a pickles recipe).

**Headline result.** 27/27 HTTP 200; behaviour identical across rounds; tool paths
compliant in 27/27; no hallucination and no drift in any run.

- Answer-in-corpus task: 9/9 runs produced the correct formula
  `Attention(Q,K,V) = softmax(QK^T/sqrt(d_k)) * V`, with all three elements (softmax,
  `sqrt(d_k)` scaling, Q/K/V) present in 9/9.
- Not-covered task (verified by hand before the run: the corpus holds only two papers on
  supershear rupture and post-earthquake loss, and no textbook material on seismic-wave
  classification): 9/9 runs stated honestly that no systematic classification is in the
  corpus and named what the related in-corpus papers actually cover. Zero fabrication.
- Non-existent task: 9/9 runs refused honestly. The catalogue-first lane exited early at
  the description layer in every run rather than searching pointlessly.

Per-cell wall times in seconds (R1 / R2 / R3, median):

| Cell | R1 | R2 | R3 | Median |
|---|---:|---:|---:|---:|
| attention_A | 76.0 | 78.0 | 61.2 | 76 |
| attention_B | 54.8 | 72.7 | 42.1 | 55 |
| attention_C | 49.6 | 66.1 | 84.9 | 66 |
| seismology_A | 44.7 | 56.0 | 55.8 | 56 |
| seismology_B | 78.1 | 46.4 | 59.4 | 59 |
| seismology_C | 73.3 | 69.3 | 41.8 | 69 |
| pickles_A | 24.4 | 40.6 | 34.2 | 34 |
| pickles_B | 29.0 | 64.0 | 33.5 | 34 |
| pickles_C | 42.7 | 37.3 | 28.8 | 37 |

Round totals were 472.6 s / 527.1 s / 441.8 s for nine runs each, i.e. 49-59 s per run on
average. Cost ranged from $0.08 to $0.42 per run. Turn counts ranged from 3 to 17; the
17-turn outlier (R2 attention_B) was a parallel batch pull of several library
descriptions and remained compliant with its lane contract. All gaps of 20 s or more in
the session traces fall in the final answer-synthesis window (no cross-turn prompt cache
on the model route used) and not in tool execution; tool-side execution was within
1-33 s in every case.

**Artifacts.** Original report (A.2 / Src 1), 27 run files (A.2 / Src 2) and
runner (A.2 / Src 3).

**Historical rerun.** A later rerun of the same design (A.2 / Src 4): 27/27 HTTP 200,
27/27 lane-compliant, wall-clock 14.9--182.0 s. Its per-cell times differ from the
original table above; the success pattern is the same. The two tables are not pooled.

### A.3 Concurrency and load campaign

**What was tested.** Nine phases (S0-S8): endpoint baselines, write concurrency, large
single documents, parallel real PDF parses, streaming and background-task fan-out, a
six-minute soak, rate limiting, and resource footprint.

**Scale.** 41 checks in total, of which three are the explicitly concurrent write phases
below; the concurrency sweep itself issued 90 / 180 / 270 requests at 5 / 15 / 30
concurrent clients.

**Headline result.** 41 items = 41 PASS / 0 FAIL.

- **20 simultaneous document creations** completed in 0.8 s: 20/20 HTTP 200, the library
  list then reported exactly 20 documents, and no content was corrupted.
- **20 simultaneous index builds** completed in 4.1 s: 20/20 HTTP 200, and the collection
  held 620 chunks. A retrieval re-check after the burst returned 1 of 3 expected
  documents on the vector channel (top_k=3, a dilution effect of the test design) but 3
  of 3 on the lexical channel, so no data was lost.
- **10 simultaneous experience creations** completed in 1.6 s: 10/10 HTTP 200 and the
  experience list reported exactly 10.

Supporting numbers from the same campaign, given here because they bound the write results
above. Baseline p50 latency: health 0.9 ms, KB catalogue 19.1 ms, vector search 273.8 ms,
two-stage search 170.7 ms, graph stats 8.3 ms. The concurrency sweep at 5 / 15 / 30
clients gave p50 5.2 / 86.9 / 1577 ms and p99 31.4 / 2818 / 3080 ms with zero errors. A
health-only run at 30 clients held p50 = 1.5 ms, which rules out the auth middleware as
the cause of the slow path; a vector-only run at 30 clients and 9 requests/s gave
p50 = 3743 ms (13.7x baseline) with 159 of 270 requests completed in the 30 s
observation window. The observed completion rate was approximately 5.3 requests/s
(159/30), not an established throughput ceiling; the remaining 111 were unfinished
within that window and are not established timeout responses. This was a separate
vector-only probe, not the zero-error read-ladder sweep. A 250 KB document (193 KB of UTF-8) indexed in 2.8 s; two real PDFs
of 1.1 MB and 1.0 MB parsed in parallel in 29 s and 24 s (29 s wall against 41 s for a
single-file baseline). Five concurrent mock SSE sessions all terminated with five unique
session ids and zero cross-talk; 25 concurrent background tasks all completed. A
six-minute soak at 8 clients and 4 requests/s served 480 / 473 / 472 requests per window
at p50 858 / 1161 / 1159 ms with zero errors and no memory leak. A 50-thread burst issued
3952 requests in 12 s (about 329 requests/s): 200 x HTTP 416 and 429 x 3536, the
600-requests-per-60-s window enforced exactly, throttled responses at p50 81 ms, full
recovery after 70 s. Footprint after the campaign: backend worker RSS 981 MB and 705 s
CPU, BFF Node process RSS 103 MB. Post-test sanity checks 5/5; cleanup removed one library
and 23 documents.

**Artifact.** Stress report (A.3 / Src 1).

### A.4 Paper acquisition campaign

**What was tested.** A batch acquisition of arXiv papers, from submission through parsing
to retrievability in the knowledge base.

**Scale.** The campaign targeted 100 papers; 26 distinct domain prefixes appear in the routed set.

**Headline result.** Earlier artifacts record 91 names in an ingest-state list and 79
catalog records that the derived-library runner enumerated and attempted to read. These
are not matched target sets or stages of a 100-paper funnel, and the records do not establish a
reliable shared audit date. Neither a 21-paper failure count nor the individual
failure stages can be inferred from these counts. The state file has no per-paper parse
status or error text. Reports mention difficulty with formula-dense scanned papers and
a tool-layer crash followed by restart from a checkpoint; neither is a quantified
explanation of the difference. In a separate, later disk inventory, each of
the 100 targets had at least one stored part; that observation does not establish
complete paper coverage or retrieval quality.

**Artifacts.** Ingest state (A.4 / Src 1: `parse_task_done` true, 10 entries in `saved`,
91 entries in `saved_all`); tool-layer results (A.4 / Src 2: `n_docs` 79); and later disk
inventory (A.4 / Src 3).

### A.5 Fifty-paper / twenty-six-domain ingest and the 30,000-character tier

**What was tested.** A fully instrumented ingest of 50 real arXiv papers over 26 domains
(split 8 domains x 3 papers, 4 domains x 2, 14 domains x 1, with sha256 in the manifest),
followed by a 30,000-character chunking tier, batch indexing, per-document verification
probes, graph construction over the five target libraries, and a ten-question retrieval
regression.

**Scale.** 50 papers; 30,000-character chunks; 165 stored documents; 3,798,446
characters of body text.

**Headline result.**

| Item | Value |
|---|---|
| Parse | 50/50 parsed by the real parser, 8.3-50.3 s per paper, 2,672 s total |
| Body text | 3,798,446 characters |
| 30,000-char tier output | 165 stored documents = 9 whole documents + 156 `(part k of N)` |
| Comparison tier | the 2,000-character tier produced 2,713 parts on the same corpus |
| Index and probe | full batch index plus per-document probe 50/50 verified |
| Library graph | 5/5 graph builds returned `success=true` |
| Content tagging | 165/165 tagged OK, 0 failures, 48 s |
| Ten-question regression | 9/10 = 90% (threshold was >= 90%) |

The routing-run summary reports 1,115.5 s at 16.3-40.4 s per paper, 202 tags,
50 batch-indexed documents and `all_probes_ok`. In the raw ingest report, 41 of
50 records have `tag_ok: false`, while `verify_ok` passed for all 50. The
negative tag flags did not block ingestion. Two caveats attach to the
30,000-character tier: one stage re-ran because of inbox ordering, and more than 800
extracted images were not uploaded.

The single regression failure is instructive rather than a retrieval error: for the
precipitation-extremes question the gold document was hit at rank 1-3 in every round, but
the literal phrase checked for ("precipitation efficiency") fell outside the returned
chunk window because the answer sentence sits in a continuation paragraph cut by the
30,000-character boundary. This is a chunk-window effect, not a wrong-library retrieval.

**Artifacts.** Chunk-tier benchmark report (A.5 / Src 1); ingest report with per-record
tag and verification flags (A.5 / Src 2); campaign summary (A.5 / Src 3); and archived
manuscript evaluation (A.5 / Src 4).

### A.6 Three-hundred-and-twenty-two-part reorganisation campaign

**What was tested.** The full reorganisation workflow over the combined arXiv corpus:
per-part content audit, description upgrade, tag de-duplication, batch re-indexing,
near-duplicate adjudication, three-source consistency and retrieval regression.

**Scale.** 322 stored parts across five libraries; 165 descriptions upgraded; 35
near-duplicate candidate groups.

**Headline result.**

- 322/322 metadata checks passed; the per-part content audit assertion passed 322/322.
- 165/165 descriptions were upgraded from the earlier "title; excerpt" form to the
  four-element two-layer form, with 165 OK / 0 bad on read-back.
- Tag de-duplication: 4/4 duplicate tag sets resolved.
- All 322 stored parts were batch-indexed with `force`.
- 15/15 retrieval regression probes passed after reorganisation, i.e. zero degradation.
- 35 near-duplicate candidate groups (similarities 0.90-0.975) were adjudicated to
  **zero true duplicates**: every group was a set of adjacent parts of the same paper.
  No stored part was deleted.

Two honesty notes are recorded with the campaign. The three-source consistency spot check
sampled 33 of the 322 stored parts, so it is a sample and not a full pass. Sub-library
splitting and hierarchy creation were analysed but deliberately not executed pending user
confirmation, so this campaign is **not** evidence for hierarchical restructuring.

A scaling comparison ran alongside it. Against a fixed 50-question set over the first
corpus, doubling the corpus from 50 to 100 papers (163 to 322 stored parts) left
retrieval precision unchanged: pass rate 48/50 = 96%, MRR 0.98 and top-1 similarity 0.759
were identical before and after. After the description upgrade and forced re-index, the
same fixed set improved to 49/50 = 98% with MRR 1.00. The newly ingested 50 papers were
100% retrievable at the 100-paper scale on both channels (50/50, MRR 1.0).

**Artifacts.** Per-check counts and the two honesty notes (A.6 / Src 1); the before/after
scaling comparison (A.6 / Src 2); and archived manuscript evaluation (A.6 / Src 3).

### A.7 Cross-lingual ingestion campaign

**What was tested.** Whether the ingest gates hold without any language-specific tuning,
over Wikipedia pages in three languages, run twice.

**Scale.** 400 Wikipedia pages per language (English, Chinese, Japanese), two rounds.
Membership and ingestion success are computed over all 400 pages per language; storage
completeness and self-retrieval Hit@1 use a 40-page or 40-query sample per language.

**Headline result.** Round 2 reproduced round 1 bit-for-bit, so one column is shown.
This table is **Table S2** of this inventory (Part D), reproduced from the archived appendix.

| Language | Ingestion success | KB membership accuracy | Storage completeness | Self-retrieval Hit@1 |
|---|---:|---:|---:|---:|
| English (en) | 1.0 | 0.875 | 0.975 | 0.975 |
| Chinese (zh) | 1.0 | 1.0 | 0.9559 | 1.0 |
| Japanese (ja) | 1.0 | 1.0 | 0.9402 | 1.0 |

The English membership figure of 0.875 is the weakest cross-lingual number reported, and
it is an organisation defect rather than a parsing defect: the page was stored, but in
the wrong library roughly one time in eight. Membership is scored against the benchmark's
source category labels, not against any naming convention derived by the ingest agent, so
it is the one placement-correctness measurement in the manuscript that does not depend on
filename cues.

**Artifacts.** Archived Table S2 from the manuscript before revision (A.7 / Src 1),
archived evaluation (A.7 / Src 2) and acquisition section (A.7 / Src 3). The underlying
run outputs (A.7 / Src 4) are retained in the separate web-repository checkout, not in
this repository; the numbers above are therefore taken from the manuscript table that
reports them.

### A.8 Sixteen-skill lifecycle scenarios

**What was tested.** Every knowledge-base skill, exercised end to end through the
project's own stdio MCP client against a live backend and web instance, using two
disposable libraries that were created for the test and deleted afterwards.

**Scale.** 16 skills, 109 real tool calls. Two test libraries (A.8 / Src 3),
94 registered tools verified in this campaign (a later server version registered 95
after one tool was added). Pre-existing
libraries were read-only and the final listing showed the original 10 libraries
unchanged.

**Headline result.** **13 PASS, 2 PARTIAL, 1 FAIL**, plus one real defect class and three
secondary defects.

- The **FAIL** is `knowledgebase-update`: `kb_project_update(show_version=True)` returned
  `{"success": false, ..., "error": "ragctl version --json timed out after 30s",
  "via": "fallback"}`. The local version (2.3.0, matching the repository `VERSION` file)
  was retrieved but the remote comparison never completed, so the skill's version
  comparison could not run. A companion defect is that `kb_project_status` silently
  ignores a `show_version` argument: it was accepted without error and no version was
  returned.
- **PARTIAL #1** (`knowledgebase-experience-summarize`): the draft pool was empty
  (`{"count":0,"drafts":[]}`), so draft read and draft approve could not be exercised.
- **PARTIAL #2** (`soul-rag`): `soul_router` worked (top1 `aa0fec78-...`, route
  confidence 0.62, 27.7 s), but `soul_hmrs_ask` launched asynchronously (task
  `5765ea09e8d7`) and was still `status: "running"` at 353.2 s, so no final answer,
  citations or persona-alignment score were observed.
- **Real defect class D1 (stale vector chunks after rename + move).** After a rename, a
  move to a second library and a move back, the index reported `chunk_count = 18` for a
  library holding one 9-chunk document; vector search returned every chunk twice, once
  under the old path and once under the new path, with identical scores
  (`[0.8, 0.689, 0.641, 0.505, 0.172]` each); and duplicate detection flagged the document
  as a near-duplicate of its own pre-rename path at similarity 0.9738. Neither the
  automatic re-index after a move nor a forced batch index removed the stale chunks. Only
  an explicit force re-index repaired it, returning `chunk_count = 9`. The failure is
  invisible from the metadata alone.
- Two further defects: `kb_task_status` reported `status: "running"` together with a set
  `finished_at` and `success: true` for a completed task, and elapsed time that disagreed
  with the timestamp delta; and the keyword search channel returned unrelated documents
  for a generic-token query ("quality" matching "inequality") while a controlled re-test
  with a unique token returned the fixture at rank 1, so the weakness is tokenisation on
  generic terms and not a missing index.

**Artifacts.** Lifecycle report (A.8 / Src 1) and raw call log (A.8 / Src 2; 109 calls).

### A.9 Static skill and tool evidence chain

**What was tested.** Two static checks that do not require a running system: a structural
audit of every skill directory against the registered MCP tool surface, and a read-only
smoke pass calling at least one tool from each skill.

**Scale.** The smoke pass covered 16 skills in 22 calls; the structural audit covered the
registered tool surface and every skill directory.

**Headline result.**

- Smoke pass: **22 calls, 0 failures**, all read-only, 16 skills covered. Per-call latency
  ranged from 9 ms (`experience_list`) to 3751 ms; the slowest call was
  **`kb_find_duplicates` at 15828 ms (15.8 s)**, and the other outliers were the two
  `kb_project_status` calls at 3626 ms and 3751 ms. Typical search and listing calls sat
  between 300 ms and 560 ms.
- Structural audit: **0 FAIL, 0 WARN** over every skill directory, with line counts and
  tool-reference counts recorded per skill (`dot-skill` 1506 lines / 0 tool references is
  the largest, `knowledgebase-organize` 315 / 16 the most tool-dense).
- A separate standardisation result is recorded in the two-lane test artifact
  (Section A.14): **20/20 skills pass `skill-creator`'s `quick_validate.py`**, where the
  same check previously passed 0/20, because every skill's front-matter description had
  used a folded block scalar. The same artifact records
  `node scripts/validate_skills.cjs` PASS (8 checks, 0 warnings, 0 issues) and the
  118_skill_audit script reporting 0 FAIL / 0 WARN over 20 skills and 94 tools.

**Note on a count discrepancy.** The structural audit's own header states *19* skill
directories and 94 registered tools, and its table lists exactly 19 skills (the 20th,
`soul-rag`, is absent from the table because it is a sibling of the skills counted);
the standardisation artifact states 20 skills. This document reports both numbers as
they stand in their respective artifacts rather than reconciling them.

**Artifacts.** Structural audit (A.9 / Src 1), smoke report (A.9 / Src 2) and
standardisation and chat-lane report (A.9 / Src 3).

### A.10 Isolated-environment ingest and index probe

**What was tested.** A minimal ingest-and-index path in a disposable environment: two
libraries were created, a 2,942-character document was written with a distinctive
measurable fact (a `ZQ-7731` resonator with quality factor `8,314,159` at `42.7 K`), the
document was indexed, and retrieval was probed.

**Scale.** 2 libraries, 1 document, 9 chunks, 5 retrieval probes.

**Headline result.** Indexing produced `collection = kb_95f4e9a1-...`, `total_chunks = 9`
under embedding model `bge-m3`. The A6-V probe (top_k 5, threshold 0.0) returned the fact
chunk at **score 0.7778**, `chunk_index` 2. With the platform's default threshold of 0.35
the top hit scored 0.7525. The two-stage probe returned the document from stage 1 at
1.899 and a stage-2 score of **0.6549**. The lexical channel returned only unrelated
documents for a "quality factor" query, and a controlled re-test with a unique token
returned the fixture at rank 1 with score 10, so the lexical weakness is tokenisation and
not index absence.

**Caveat, stated by the artifact.** `parse_doc` and `kb_doc_save_parsed` were **not
exercised**; consequently the parse-quality gate, the split gate and the parsed-document
save path were not exercised either. All ingest testing in this probe used the direct
document-creation path.

**Artifact.** Lifecycle report (A.10 / Src 1).

### A.11 Three-channel retrieval end-to-end campaign

**What was tested.** The same three questions through three independent channels, so that
the retrieval result and the answering surface can be separated:

1. the harness's official streaming API (`POST /api/claude/chat`, `engine=claude`,
   `kbEnhanced=true`), with a per-tool SSE timeline;
2. a non-streaming system-arm comparison through the same chat API;
3. a pure retrieval matrix with no LLM call at all.

**Scale.** Three questions (a dialogue-summarisation paper as an in-corpus retrieval task,
a stroke-prediction paper as a second in-corpus task, and an out-of-domain collider
question that must be refused), three retrieval modes (A pinned-library vector, B
hierarchical all-library, C hybrid), three channels.

**Headline result.**

- **Channel 1: 8/9 gates.** The single failure is cell B x cm1, a **false refusal**: the
  answer asserted that the library contained nothing on the topic although the gold
  document was present. The tool timeline shows the cause: a single `kb_search_vector`
  call consumed **300.0 s** (`t+21.5s` to `t+321.5s`), making the whole scenario 353.5 s.
  Channel-1 end-to-end means: A = 47.0 s, B = 142.2 s, C = 51.2 s.
- **Channel 2: 8/9 gates** under the same corrected refusal criterion, failing on the
  same cell B x cm1, independently reproduced. Non-streaming means: A = 48.0 s,
  B = 66.4 s, C = 68.9 s. Per-cell: A 53.0 / 65.3 / 25.7 s, B 41.4 / 91.9 / 66.0 s,
  C 58.3 / 100.0 / 48.3 s (cm1 / cm2 / cm3).
- **Channel 3: 12/12 gold cells.** Six scripted arm cells (3 modes x 2 in-corpus
  questions) and six scripted baseline cells all hit the gold document. Against the earlier
  baseline (A.11 / Src 5) this is a large latency improvement: mode B 342 s / 234 s to 25.0 s / 10.2 s,
  mode C 1152 s / 1818 s to 37.3 s / 33.7 s. The lexical BM25 baseline returned 10/10
  documents for the two questions.

Channel 1 mean latencies were A = 47.0 s, B = 142.2 s, C = 51.2 s; the failing cell alone
was 353.5 s against 29.9-65.0 s for the other eight, and its engine time was 352.7 s. All
nine cells were otherwise PASS.

**Artifacts.** Campaign report (A.11 / Src 1), streaming summary (A.11 / Src 2),
chat-mode comparison (A.11 / Src 3) and retrieval comparison (A.11 / Src 4).

Note the difference in external baseline tables between the two runs is a corpus
difference, not a contradiction: in the retrieval comparison (A.11 / Src 4) the BM25
baseline was scored on a 100-document markdown corpus, and the chat-mode run reports the
system arms while the retrieval run reports mode cells.

### A.12 Stratified three-track run with the judge switched off

**What was tested.** A stratified three-track evaluation (track A, B, C over the same
question set) with the evaluator deliberately left unconfigured.

**Scale.** 10 questions per track, 30 cells.

**Headline result.**

| Track | n | Pass | Pass rate | Gold hits | Keyword hits | False refusals | Should-refuse | Correct refusals | Mean latency (s) | Mean cost (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 10 | 9 | 0.9 | 9 | 9 | 0.0 | 0 | 0 (None) | 113.0 | 0.4911 |
| B | 10 | 6 | 0.6 | 10 | 6 | 0.0 | 0 | 0 (None) | 42.7 | 0.1631 |
| C | 10 | 5 | 0.5 | 9 | 6 | 0.0 | 0 | 0 (None) | 48.0 | 0.1803 |

The run (A.12 / Src 2) used the archived question file (A.12 / Src 3). Two
things must be recorded with these numbers. First, `notfound_accuracy` is `null` and the
judge-derived "correct" field is `None` for every row, because the judge was not
configured; the only populated stratum is "single" at 10 of 10 per track, so the three
tracks are not actually stratified in this run. Second, the false-refusal rate of 0.0
across all three tracks is accompanied by zero should-refuse questions, and the report
itself notes that refusal-accuracy-only rules are equivalent to "always refuse", so both
directions must be reported together.

**Artifacts.** Smoke report (A.12 / Src 1) and structured results (A.12 / Src 2).

### A.13 Harness and honest-refusal campaign

**What was tested.** Two things: a three-mode system-arm comparison against fixed gates,
and a two-round harness reliability run over ten questions crossed with five methods.

**Scale.** System arms 3 modes x 3 questions (one out-of-domain) = 9 cells; the
reliability run covered 10 questions x 5 methods x 2 rounds = 100 units, with a 50-unit
self-check.

**Headline result.**

- System arms: run (A.13 / Src 2) **passed 9/9 gates** (exit code
  0). Mode A: cm1 85.5 s / 6 turns, cm2 83.6 / 5, cm3 76.1 / 5. Mode B: cm1 196.9 / 17,
  cm2 142.2 / 9, cm3 316.0 / 19 (before the fix described below). Mode C: cm1 99.1 / 7,
  cm2 89.9 / 8, cm3 72.0 / 5. The two gold papers were hit verbatim and the out-of-domain
  question was refused with zero fabrication in all three modes.
- Reliability run, round 1 (A.13 / Src 3): gold 0.75, citation 0.75, mean
  41.5 s, 5.1 tools per question, over-refusal 0, errors 0, $3.75. Round 2
  (A.13 / Src 4): **gold 1.00, citation 1.00**, mean 34.1 s, 5.2 tools per
  question, over-refusal 0, errors 0, $4.50. The self-check passed 6/6 in both rounds over
  50 units each (cost consistent, provenance complete).
- Retrieval-only baseline cells (including a lexical BM25 baseline) achieved retrieval
  gold 1.0 but closed-book over-refusal of 37.5-62.5%, which quantifies what the answer
  layer adds over raw retrieval.
- **Three real defects were found and fixed during this campaign.** (1) A session MCP
  mount race: sessions mounted with an allow-list only failed on short prompts roughly
  half the time, and the model answered from memory (one question emitted the attention
  formula from parametric knowledge). The fix was a stdio mount plus a
  `KB_TOOLS_NOT_READY` sentinel, forcing zero-tool sessions to `success=false`
  (`code=KB_TOOLS_NOT_READY` / `KB_NO_RETRIEVAL`) and retrying three times; a residual
  honest-failure rate of about 2 in 10 per round remains under parallel load because of
  cold start. (2) A lane-B instruction self-contradiction: one instruction forbade
  spawning a sub-agent while another told the model to do exactly that. (3) Lane-B
  refusal had no budget: the refusal scenario took 316 s, and after the fix it took
  **20.3 s (a 15.6x reduction, 6 turns)**, while cm1 fell from 196.9 s to 57.5 s
  (12 turns) with zero regression.
- **Not measured, stated by the report itself:** the L2 external judge
  (`JUDGE_ENDPOINT`/`JUDGE_KEY` unset), qrels, and significance testing. No significance
  claim is made from this campaign.

**Artifact.** Pipeline report (A.13 / Src 1).

### A.14 Two-lane isolation test

**What was tested.** Whether a chat lane with the vector and two-stage tools removed can
still answer, and whether the tool removal is actually enforced at the call level.

**Scale.** 4 questions x 2 lanes through one chat API. Lane A had 26 knowledge-base tools
including `kb_search_vector` and `kb_search_two_stage`; lane B had 20 tools with the
vector, two-stage and vector-stats tools removed. The environment was backend 8771, web
6789, Neo4j 7687, MinerU up; the capability probe returned 10 libraries and 364
documents, `permission_denied` 0, `is_error` false.

**Headline result.**

- **Lane A: 4/4 correct**, complete answers with part-file citations. Latencies and tool
  counts: 132.9 s / 13, 58.3 / 9, 55.8 / 8, 43.4 / 7.
- **Lane B, first round: 0/4.** All four runs returned process narration rather than an
  answer and did not converge within the session. Latencies and tool counts: 75.2 / 12,
  59.3 / 15, 50.0 / 12, 59.1 / 19.
- **Isolation verified.** Lane B made **zero vector-tool calls** in all four questions,
  confirmed from the call traces; denied-tool counts were 0 in every run.
- **Lane B retest with an explicit final-answer instruction: 11 tool calls, 12 turns
  (limit 30, ended naturally), 106 s, fully correct verbatim answer.**

The artifact states plainly what this test cannot show: no quality ranking between lane A
and lane B (the retest is n=1 and variance is high), and no efficiency conclusion for lane
B (12-19 tools against 7-13 for lane A). It also records that 24 poor novel descriptions
remained unfixed at the time of the run.

**Artifact.** Standardisation and chat-lane report (A.14 / Src 1).

### A.15 Three-engine and three-channel cost campaign

**What was tested.** What the same kind of task costs when it is delivered three different
ways. First, three **engines** on one task set: the agent surface
(`/api/kb/agent/chat`), the Claude harness (`engine=claude`) and the OMP harness
(`engine=omp`). Second, the three **delivery channels** of the contemporaneous three-channel
campaign (A.11), run over the same three retrieval modes.

**Scale.** 18 runs in the engine campaign (7 agent-surface scenarios, 6 Claude-harness
scenarios, 5 OMP-harness scenarios); 9 runs each in channel 1 and channel 2 of the
three-channel campaign. The engine campaign's own verdict is 18 of 18 scenarios PASS, every
answer gold-hit, zero fabricated citations.

**Headline result.**

| Condition | Runs | Wall clock (s) | Turns | Cost per run |
|---|---:|---|---:|---|
| Agent surface | 7 | 50.5-175.9 | 2-9 | $0.9-1.8 |
| Claude harness | 6 | 23.2-52.4 | 5-8 | $0.11-0.36 |
| OMP harness | 5 | 33.5-171.4 | 2-9 | $0.03-0.07 |
| Channel 1 (streaming; 8 of 9 gates) | 9 | 29.9-353.5 | 5-8 | $0.12-0.25 |
| Channel 2 (non-streaming; 8 of 9 gates) | 9 | 25.7-100.0 | 4-11 | not metered |

The three engines separate by one to two orders of magnitude in cost at one quality tier
(the agent surface $0.9-1.8, the Claude harness $0.11-0.36, the OMP harness $0.03-0.07). The
OMP harness's wall clock is about twice its engine time because it pays a 50-90 s harness
cold start per call; the Claude harness's wall clock is approximately its engine time. The
third channel of the same campaign is pure retrieval with no LLM call at all: 12
method-question cells with the gold document present in all 12, 10.2-37.3 s against
millisecond in-process calls for the lexical baseline, at zero token cost.

**Artifacts.** Per-scenario summary for the 18 engine runs (A.15 / Src 1); channel 1
summary and report (A.15 / Src 2 and A.15 / Src 3); channel 2 comparison (A.15 / Src 4);
channel 3 pure-retrieval matrix (A.15 / Src 5); the campaign note that reproduces the
three-engine row and cites the summary's line range (A.15 / Src 6); and the earlier
supplementary inventory containing the cost table (A.15 / Src 7). The `exp8b*` file
pattern (A.15 / Src 8) resolves to exactly one file: it carries the three absent-tier
agent probes of B.7, not the cost table.

### A.16 The 30-cell answer grid: wall clock, tools and cost per cell

**What was tested.** Per-cell time, tool count and cost for the original three-arm answer grid. Supplementary Figure S6 and Tables S14--S15 preserve the marker, answer and runtime checks. The later platform-only run in E6 is not part of this grid.

**Scale.** 30 cells: ten questions (BQ01-BQ10) x three arms (P = platform read tools, F = file tools over the exported tree, C = chunk index over the 800-character mirror; the archived run tracks are a2, b and c respectively).

**Headline result.** Arm means: P 52.6 s / 6.0 tools / $0.711; F 22.2 s / 6.4 tools / $0.487; C 24.5 s / 3.7 tools / $0.527. The platform arm is the slowest and most expensive in this single run; the manuscript reports this as an observation about this implementation, not an efficiency result.

| Q | arm | wall (s) | tools | cost (USD) |
|---|---|---:|---:|---:|
| BQ01 | P (platform) | 55.5 | 5 | 0.772 |
| BQ02 | P (platform) | 35.8 | 5 | 0.595 |
| BQ03 | P (platform) | 75.3 | 10 | 0.782 |
| BQ04 | P (platform) | 25.6 | 4 | 0.511 |
| BQ05 | P (platform) | 35.6 | 5 | 0.638 |
| BQ06 | P (platform) | 97.4 | 10 | 1.032 |
| BQ07 | P (platform) | 25.3 | 3 | 0.487 |
| BQ08 | P (platform) | 77.0 | 6 | 0.836 |
| BQ09 | P (platform) | 43.9 | 5 | 0.729 |
| BQ10 | P (platform) | 54.7 | 7 | 0.728 |
| BQ01 | F (file tools) | 24.9 | 6 | 0.420 |
| BQ02 | F (file tools) | 24.2 | 7 | 0.492 |
| BQ03 | F (file tools) | 20.3 | 8 | 0.487 |
| BQ04 | F (file tools) | 12.0 | 5 | 0.375 |
| BQ05 | F (file tools) | 19.6 | 4 | 0.439 |
| BQ06 | F (file tools) | 29.9 | 10 | 0.641 |
| BQ07 | F (file tools) | 11.6 | 4 | 0.377 |
| BQ08 | F (file tools) | 20.2 | 4 | 0.444 |
| BQ09 | F (file tools) | 20.4 | 4 | 0.418 |
| BQ10 | F (file tools) | 38.6 | 12 | 0.773 |
| BQ01 | C (chunk) | 34.1 | 5 | 0.610 |
| BQ02 | C (chunk) | 21.4 | 2 | 0.483 |
| BQ03 | C (chunk) | 18.6 | 2 | 0.454 |
| BQ04 | C (chunk) | 17.0 | 2 | 0.442 |
| BQ05 | C (chunk) | 30.0 | 4 | 0.581 |
| BQ06 | C (chunk) | 48.6 | 11 | 0.801 |
| BQ07 | C (chunk) | 11.2 | 2 | 0.412 |
| BQ08 | C (chunk) | 19.7 | 2 | 0.468 |
| BQ09 | C (chunk) | 23.3 | 3 | 0.516 |
| BQ10 | C (chunk) | 21.3 | 4 | 0.503 |

**Artifacts.** Original grid records (A.16 / Src 1; one file per cell; `latency_s`,
`tool_call_count`, `total_cost_usd`); arm aggregates recomputed here. The question-level
checks in Table S14 use the corrected grades for the same run (A.16 / Src 2).

### A.17 Deployment-layer system arms (three questions)

**What was tested.** Whether the public chat API delivers the same contracts when invoked as an external caller would. Three questions (an English methodology question, a Chinese clinical question, one out-of-corpus probe) crossed three deployment arms: S1 pinned the target shelf, S2 left the library unpinned, S3 pinned it with a hybrid directive.

**Scale.** Nine cells in the streaming channel, replicated in a non-streaming channel; both channels returned 8 of 9 gates. Wall-clock seconds are shown; a passing in-corpus cell returned the gold identifier, and an out-of-corpus cell passes by abstaining.

| Arm | cm1 (EN, CS shelf) | cm2 (ZH, life shelf) | cm3 (out-of-corpus) |
|---|---|---|---|
| S1 pinned vector | 55.7 s, pass | 48.8 s, pass | 36.4 s, abstain |
| S2 all-KB librarian | 353.5 s, fail | 43.2 s, pass | 29.9 s, abstain |
| S3 hybrid | 43.1 s, pass | 45.6 s, pass | 65.0 s, abstain |

**Artifact.** The historical campaign archive (A.17 / Src 1) records S2's oversized-catalog
transport failure. The revised manuscript's E7 (Section 8.8) notes that truncation case
but reports separate, later deployment checks.

### A.18 Failure-mode catalogue

**What was tested.** Not an experiment. This entry documents the provenance of the
failure-mode catalogue from the earlier manuscript (A.18 / Src 1). Its nine rows cover recorded production
incidents and defects surfaced by the campaigns.

**Scale.** Nine failure modes. The chapter names three early production incidents (a
corrupted index segment that made one library silently un-retrievable across lanes, an
out-of-memory indexing run that returned success with an empty payload, and judge failures
that had to reject candidates rather than pass them) and states that the catalogue is that
incident log "extended with the three defects the organization and functional campaigns
surfaced". The rows are: corrupted index segment (silent loss); out-of-memory during
indexing; driver contention on Windows (embedding latency 68 s against 27 min); judge
worker cold start (first judge batch stalls 10-12 s); un-whitelisted harness tools (14-170 s
detours per run); judge or engine errors; rename without re-index (chunk count 18 where 9
exist); graph node not created (a library reports two of three documents); and a task record
that outlives its task (a finished build still reports `running`).

**Headline result, stated as a provenance limit.** No single catalogue artifact exists.
The catalogue is compiled from the incident notes, and those notes
in turn cite the campaign artifacts that recorded each incident. The four notes actually
found to carry it are:

- A.18 / Src 2 — the request that produced the table
  (consolidate the incident log into failure -> detection signal -> fix -> residual risk) and
  the item tracking it.
- A.18 / Src 3 — the Windows driver-contention incident (the
  end-to-end regression from 68 s to 27 min).
- A.18 / Src 4 — the out-of-memory indexing run that
  returned an empty payload in a success envelope.
- A.18 / Src 5 — the campaign defects: the
  three-source check that found `chunk_count=18` where 9 chunks exist, the graph node that
  was not created, and the graph-build task left reporting `running`.

The campaign artifacts those notes cite are the lifecycle report (A.18 / Src 6),
graph statistics (A.18 / Src 7) and tag report (A.18 / Src 8). Rows in the catalogue that
no note traces to a recording artifact are reported here as carried only by the chapter's
own incident log, not as independently recorded.

**Artifacts.** No dedicated catalogue artifact; the carrier files are the four notes listed
above, with the cited campaign artifacts behind them.

---

## Part B. Retrieval evaluation matrix

Every retrieval configuration the project has measured, with its corpus, question count,
metrics and artifact references. Metrics are `hit@5 / recall@5 / MRR` unless a row states
otherwise. Rows are grouped by corpus and experiment, not by claim.

### B.1 Five configurations on the 42-document corpus

Corpus: the live deployment's five libraries, 42 documents, 16 gold-annotated questions
(one library contains twenty near-duplicate equipment-telemetry reports). BM25 index
build took 0.61 s.

| Configuration | hit@5 | recall@5 | MRR | latency mean (s) | latency p50 (s) |
|---|---:|---:|---:|---:|---:|
| bm25 | 1.0 | 1.0 | 0.958333 | 0.001 | 0.001 |
| graph | 0.5625 | 0.53125 | 0.5625 | 0.068 | 0.068 |
| twostage | 1.0 | 0.96875 | 0.927083 | 0.077 | 0.04 |
| fusion_only | 0.9375 | 0.9375 | 0.85625 | 0.062 | 0.066 |
| hmrs_hybrid | 0.4375 | 0.40625 | 0.226042 | 0.542 | 0.581 |

**Artifact.** Retrieval summary (B.1 / Src 1).

### B.2 Judged / as-filter / judge-fuse decomposition on the same corpus

Same 42 documents and 16 questions. Each row reports `hit@5 / recall@5 / MRR`. `n_fusion`
was 12 candidates per question and `n_survivors` 12, except Q14 at 11. The fuse replay
(artifact key `rrf_fuse`) fuses the fusion ranking with the judge-score ranking by
reciprocal-rank fusion; the name is the artifact key, not a separate retrieval lane.

| Configuration | hit@5 | recall@5 | MRR |
|---|---:|---:|---:|
| judged | 0.4375 | 0.40625 | 0.22604167 |
| filter_only | 0.9375 | 0.9375 | 0.85625 |
| judge_fuse | 0.875 | 0.875 | 0.60625 |

One remark that the artifacts themselves support rather than conceal: `judged`
here reports the same values as `hmrs_hybrid` in B.1 to five decimal places, so the two
names denote the same measurement and should not be counted twice.

**Artifacts.** Judge-filter replay (B.2 / Src 1) and retrieval summary (B.2 / Src 2).

### B.3 Threshold selection on the same corpus (leave-one-out)

The candidate-cut threshold was chosen by leave-one-out over the 16 questions on a grid
from 0.05 to 0.40 in steps of 0.01, using a smallest-margin rule on the 15 training
questions. Across 16 folds the leave-one-out gold survival was 0.9375 against 1.0 for a
fixed 0.20 cut, and the selected thresholds were 0.15 and 0.18.
Q11 is the only fold that selected 0.15, and it is the only fold whose holdout gold
document was not kept. Every fold kept the gold document at a fixed 0.20 cut, which is the
artifact's justification for not adopting the leave-one-out threshold.

**Artifact.** Leave-one-out margin results (B.3 / Src 1).

### B.4 Same configurations on the paraphrase grid (16 questions, one paraphrase each)

Each of the 16 questions was re-asked once in different words.

| Configuration | hit@5 | recall@5 | MRR |
|---|---:|---:|---:|
| bm25 | 0.875 | 0.875 | 0.7552083333333334 |
| graph | 0.5625 | 0.5 | 0.5625 |
| twostage | 0.9375 | 0.90625 | 0.90625 |
| fusion_only | 0.9375 | 0.9375 | 0.8333333333333334 |
| judged | 0.5 | 0.46875 | 0.18854166666666666 |
| filter_only | 0.9375 | 0.9375 | 0.8333333333333334 |
| judge_fuse | 0.875 | 0.84375 | 0.6291666666666667 |

Under rewording `fusion_only` and `filter_only` hold their B.1 hit@5 while BM25 and the
two-stage lane lose ground; the judged configuration's MRR falls furthest (0.226 to 0.189).

**Artifact.** Paraphrase results (B.4 / Src 1).

### B.5 Six configurations on the derived library (79 document records)

Corpus: 79 derived-library document records and ten questions (`BQ01`-`BQ10`).
The runner counted entries in the derived library's catalog after issuing a read
for each (Section A.4). This is not a count of distinct target papers or of
successful retrievals. Values are hit@5.

| Configuration | hit@5 |
|---|---:|
| bm25 | 0.9 |
| graph | 0.2 |
| twostage | 0.9 |
| fusion_only | 0.9 |
| judged | 0.9 |
| filter_only | 0.9 |

No configuration logged a top-five gold hit for `BQ03` in this run. Its gold ID
appears in the answer or trace in all arms of the separate A.19 grid. Per-question latency in seconds: BQ01
2.253, BQ02 0.621, BQ03 0.233, BQ04 0.187, BQ05 0.242, BQ06 0.185, BQ07 0.171, BQ08
0.178, BQ09 0.192, BQ10 0.206; candidate counts were 10-12 and kept counts 5-11.

**Artifact.** Derived-library tool-layer results (B.5 / Src 1).

### B.6 Four-lane agentic grid

Four agentic lanes (search, librarian, hybrid, bare) over four questions, run twice. The
`bare` lane has no retrieval tools at all and is the closed-book control.

| Lane | n | Document hit | Fact markers | Mean wall (s) | Mean turns | Refusals |
|---|---:|---:|---:|---:|---:|---:|
| search (round 1) | 4 | 1.0 | 1.0 | 61.3 | 5.5 | 0 |
| librarian (round 1) | 4 | 1.0 | 1.0 | 71.3 | 5.5 | 0 |
| hybrid (round 1) | 4 | 1.0 | 1.0 | 56.7 | 3.8 | 1 |
| bare (round 1) | 4 | 0.0 | 0.5 | 57.2 | 1 | 2 |
| search (round 2) | 4 | 1.0 | 1.0 | 95.0 | 7.2 | 0 |
| librarian (round 2) | 4 | 1.0 | 1.0 | 74.0 | 7.8 | 0 |
| hybrid (round 2) | 4 | 1.0 | 1.0 | 73.8 | 5.0 | 0 |
| bare (round 2) | 4 | 0.0 | 0.3 | 58.8 | 1 | 1 |

The generated summary adds seconds per turn (11.671666666666667 / 12.800833333333333 /
15.26125 / 57.2 for search / librarian / hybrid / bare) and zero timeouts in every lane. The bare lane never
cites a document (citation 0.0) and its fact-marker rate falls from 0.5 to 0.3 between
rounds, i.e. the closed-book control is unstable as well as inaccurate. Individual run
records exist for every cell.

**Artifacts.** First-round summary (B.6 / Src 1), generated summary (B.6 / Src 2) and
first-round run files (B.6 / Src 3); second-round summary and run files (B.6 / Src 4).

### B.7 Abstention runs

Six agent runs over two out-of-corpus questions (lithium-battery thermal runaway; the
childhood vaccination schedule), three lanes each.

| Run | Wall (s) | Turns | Answer chars | Refusal opening | Honest marker anywhere |
|---|---:|---:|---:|:--:|:--:|
| hybrid O1 | 75.3 | 4 | 463 | false | false |
| hybrid O2 | 36.2 | 3 | 299 | true | true |
| librarian O1 | 68.4 | 4 | 539 | true | true |
| librarian O2 | 57.3 | 3 | 411 | true | true |
| search O1 | 82.9 | 7 | 708 | true | true |
| search O2 | 37.8 | 3 | 433 | true | true |

The script's own marker rule flags five of six runs. The sixth (hybrid O1) is flagged
`false` on both fields, but its answer text does state that the knowledge base contains no
corresponding content and lists the searches performed; the miss is in the script's marker
list, not in the behaviour, and it is recorded here rather than corrected.

Three further absent-tier **agent** runs (the corpus contains nothing on the asked topic)
are recorded separately: wall times **73.3 s, 113.5 s and 47.9 s**, answer lengths 536,
640 and 494 characters, turn counts `null`. All three are explicit not-found reports. The
third reports its own search arithmetic for a run **assembled from separate tool calls** —
a vector lane over 16 documents, a catalogue lane over 42 candidates, 43 merged with 15
overlap, 12 documents judged through `kb_laya_judge` of which 11 survived, and the top three
read — rather than performed by a single hybrid tool; the answer text times that pair of
lanes at **1.67 s**. The vector and experience channels are recorded as unavailable in the
*first* of the three runs, not the third.

**Artifacts.** Six agent-run records (B.7 / Src 1) and the separate absent-tier agent
records (B.7 / Src 2).

### B.8 Out-of-corpus probes at the tool layer

Four out-of-corpus questions were run through the tool layer alone (no LLM answer) to see
how many candidates survive the gate, out of 12.

O1--O4 concern lithium battery thermal runaway, child vaccination schedules,
Python multiprocessing versus threading, and injection-mould vent design, respectively.

| Probe | Vector top score | Candidates above 0.35 | Merged | Kept of 12 | Reads | Latency (s) |
|---|---:|---:|---:|---:|---:|---:|
| O1 | 0.596 | 4 | 43 | 11 | 5 | 0.7 |
| O2 | 0.397 | 8 | 42 | 11 | 5 | 0.15 |
| O3 | 0.511 | 10 | 43 | 9 | 5 | 0.16 |
| O4 | 0.538 | 7 | 43 | 11 | 5 | 0.16 |

The same artifact replays the candidate cut on the in-corpus question set, reporting how
many of the 17 gold documents survive at each threshold: 8 at cut 0.05, 14 at 0.10, 16 at
0.15, and 17 at every cut from 0.20 to 0.35.

**Artifact.** Tool-layer abstention results (B.8 / Src 1).

### B.9 Graded probes on a partially-answerable set

Six tool-layer probes on questions graded partial-answerable (PA) or absent (AB), plus
three agent-layer probes on the same partial-answerable questions. Retained candidates are
out of 12.

| Probe | Kind | Merged | Kept | Max score | Min kept score | Latency (s) |
|---|---|---:|---:|---:|---:|---:|
| PA1 | partial | 12 | 12 | 0.954 | 0.666 | 7.83 |
| PA2 | partial | 12 | 12 | 0.876 | 0.511 | 1.44 |
| PA3 | partial | 12 | 11 | 0.965 | 0.550 | 0.68 |
| AB1 | absent | 12 | 10 | 0.983 | 0.500 | 0.67 |
| AB2 | absent | 12 | 11 | 0.968 | 0.813 | 0.64 |
| AB3 | absent | 12 | 11 | 0.944 | 0.592 | 0.79 |

Every tool-layer probe retains 10-12 of 12 candidates and top scores reach 0.983 on a
question the corpus cannot answer, which is the clearest single demonstration in this
project that a high vector score is not evidence of an answer. The agent layer on the
same partial questions is much slower and gives no turn counts: 47.9 s / 724 characters,
65.9 s / 840 characters, 155.7 s / 774 characters.

**Artifact.** Graded-probe results (B.9 / Src 1).

### B.10 NLI second signal (first replay)

A local NLI model (`IDEA-CCNL/Erlangshen-Roberta-330M-NLI`) was replayed as a second
scoring signal over the same candidate pairs as the platform gate, n = 191 pairs.

| Quantity | Value |
|---|---:|
| NLI hit@5 / MRR | 0.3125 / 0.1375 |
| Platform gate hit@5 / MRR (same pairs) | 0.4375 / 0.22604 |
| NLI score, gold median | 0.0113 |
| NLI score, non-gold median | 0.05285 |
| NLI score, gold minimum | 0.0001 |
| NLI score, non-gold maximum | 0.9992 |
| Mann-Whitney p | 0.12024 |
| Cliff's delta | 0.22853 |
| Spearman rho | -0.13421 |

The direction is wrong: the non-gold median is higher than the gold median, the
correlation with gold rank is negative, and the separation is not significant at
p = 0.12024. One symbolic sub-check is also recorded: for Q6, gold documents containing
the literal string `3135` were 1 of 1 while non-gold documents containing it were 0 of 11.
The artifact additionally carries a full out-of-corpus replay over the corpus documents.

**Artifact.** Document-level NLI replay (B.10 / Src 1).

### B.11 Span-level NLI (second replay)

The same idea applied at span level rather than document level, over the same 191 pairs.

| Signal | hit@5 | MRR |
|---|---:|---:|
| platform gate | 0.4375 | 0.22604 |
| NLI, head | 0.3125 | 0.1375 |
| NLI, span | 0.1875 | 0.09375 |
| rank ensemble | 0.3125 | 0.11146 |

Span separation: gold median 0.4728 against non-gold median 0.91855 (gold minimum
0.0002, non-gold maximum 0.999), Mann-Whitney p = 0.007414975017999724. The separation is
significant and in the wrong direction, and span-level scoring is worse than head-level
scoring as a ranker. Neither NLI replay improves on the platform gate.

**Artifact.** Span-level NLI replay (B.11 / Src 1).

### B.12 Five-track by ten-question matrix

The run (B.12 / Src 1) crossed five tracks (`a2`, `bm25`, `vector`, `rrf`,
`rerank`) with ten questions, producing 50 rows. The run manifest records `n_rows` 50,
total cost $8.6161, 22,300 output tokens, `prompt_version` v4-neutral, seed 0,
`max_turns` 12, shuffled questions, `selfheal` true.

**The run's own report does not report IR metrics.** Its main table carries only track
`a2` and marks every retrieval and judge column as `null` / NOT measured:

| Field (track a2, n=10) | Value |
|---|---:|
| judge accuracy | null (NOT measured) |
| quality | null (NOT measured) |
| P@5 | null (NOT measured) |
| R@10 | null (NOT measured) |
| nDCG@10 | null (NOT measured) |
| MRR | null (NOT measured) |
| mean latency | 48.630 s |
| cost | $0.689 |
| tools per question | 6.400 |

Three artifacts that would carry those metrics are absent: `judge.json` (L2 evaluation),
`qrels_scores.json` (IR metrics) and `stats.json` (significance). Per-question records for
all five tracks are available in B.12 / Src 1. The summary table leaves the unmeasured
metrics blank rather than substituting other results.

**Artifact.** The five-track run archive (B.12 / Src 1) contains the reports, run manifest
and per-question records.

### B.13 Verification-gate ablation, ten questions

Three arms over one ten-question set and one **frozen shared candidate set**: `C-nogate`,
the ungated control; `C-judge`, the gate applied to those frozen candidates; and
`C-judge-seg`, the same gate with evidence taken at segment granularity. Because the
candidate set is frozen before the arms diverge, the gate is the only difference between
conditions. An earlier protocol built around `kb_hybrid_search(enable_judge=...)` was
superseded and is **not** reported here.

**Scale.** Ten questions (`QK01`-`QK10`) from the archived question set (B.13 / Src 4)
against the live five-library corpus, candidate cap 12, gate threshold 0.5 with criterion
`auto` and `reference_mode` true, evidence pack budget 4000 characters. Thirty answer
cells (three arms x ten questions), 30 answer calls, $1.0015 of metered answer cost. Eight
of the ten questions are gold-answerable; `QK09` is unanswerable and `QK10` is out of
corpus, and both are excluded from the gold-level means.

| Arm | Mean grade, all ten | Mean grade, eight gold-answerable | Gold docs surviving | Mean documents per cell | Mean latency (s) |
|---|---:|---:|---:|---:|---:|
| `C-nogate` | 1.8 | 1.0 | 8 of 8 | 12.0 | 6.92 |
| `C-judge` | 2.0 | 1.25 | 8 of 8 | 11.2 | 7.65 |
| `C-judge-seg` | 1.3 | 0.375 | 8 of 8 | 11.2 | 6.37 |

- **The gate moved two of ten answers and left eight unchanged.** Paired against the
  control, `QK01` rose **0 to 5** and `QK03` fell **3 to 0**; the other eight questions are
  identical between the two arms. The paired mean delta is +0.2. Segment granularity moves
  a third: relative to the control, `C-judge-seg` keeps a partial answer on `QK06` (grade 3)
  while `QK01` and `QK03` both sit at 0.
- **The gate lost no gold document.** Gold-document survival is **8 of 8** in every arm, and
  the mean gold rank is 1.0 wherever the gold is in the corpus. On this question set the
  gate is not the agent that drops the needed documents.
- **The packed document set is identical between arms on nine of the ten questions.** The
  single exception is `QK09`, where the control packs **12 documents** and both judged arms
  pack **4**; that is the whole of the difference in mean documents per cell (12.0 against
  11.2).
- **Segment granularity is the weakest arm.** Its mean grade over the eight gold-answerable
  questions is 0.375 against 1.25 for the document-level gate over the same candidates.
- **Two of the thirty cells failed mid-run and were repaired.** Both were `QK09` (arms
  `C-judge` and `C-judge-seg`) and both failed with `HTTPError: HTTP Error 401:
  Unauthorized`. They were rerun through the artifact's `--repair` path, both to grade 5,
  and the pre-repair originals are retained in `repairs.json`.

**Protocol deviation recorded in the artifact.** The planned gate,
`kb_hybrid_search(enable_judge=...)`, was not registered in the test
environment, so the ablation used `kb_laya_judge` on a frozen shared candidate set. The
consequence for reading these numbers is stated in the artifact and repeated here: only
the within-run contrast between the three arms is comparable to anything, and no number in
this entry is comparable to a run of the superseded protocol.

**Artifacts.** Aggregate results (B.13 / Src 1); per-cell, candidate and repair records
(B.13 / Src 2); and the ablation report (B.13 / Src 3).

### B.14 Library-partition ablation

Four conditions x ten questions = 40 retrieval cells, no LLM calls. The
gold-pinned, wrong-library and catalog diagnostics use the five-library
evaluation corpus; the `flat` condition used `kb_id=""` and searched all 20
live libraries, including 15 outside that corpus. Thus, the flat and pinned
conditions did not have a controlled, matched search scope. Both
`score_threshold` and the gate were held identical across conditions
(`top_k=10`, `score_threshold=0.0`, gate threshold 0.5) so that an empty
result cannot be an artifact of the threshold.

| Condition      | Hit@5 | Hit@10 | Gold rank | Candidates | Kept | Time (s) |
|----------------|------:|-------:|----------:|-----------:|-----:|---------:|
| Gold library   | 1.0   | 1.0    | 1.0       | 2.75       | 2.75 | 0.462    |
| Other library  | 0.0   | 0.0    | null      | 7.125      | 6.875| 0.487    |
| Unscoped       | 1.0   | 1.0    | 1.0       | 2.5        | 2.5  | 0.3      |
| Catalogue only | 1.0   | 1.0    | 1.75      | 235.75     | 11.375| ~0.0    |

Gold rank, candidate count, retained count and time are means.

Denominators: `QK09` (unanswerable) and `QK10` (out of corpus) have no gold document in
the corpus and are excluded from the hit and rank denominators
(`n_graded_gold_in_corpus` 8, `excluded_qids` `["QK09","QK10"]`); the all-ten rate that
would count them as misses is reported alongside in the artifact and is not used here.

Environment measurements from the same run: 322 of 322 document names carry the topical
prefix (a label leak, `prefix_leak_fraction` 1.0); per-library document counts are 131,
75, 53, 39 and 24 for a total of 322 parts; routing agreement between the router's
assignment and the filename prefix is 95 of 96 papers (0.9896); and ranking the five
library descriptions against the query puts the correct library first only **6 of 8**
times (`catalog_library_top1_routing` `{"hits": 6, "n": 8}`).

The observed results are bounded to this diagnostic: a routing mistake never
recovered the gold document (0.0 hit@5 and hit@10 on all 8 graded questions);
`flat` and `pinned-gold` both scored 1.0, but the unscoped arm searched 15
additional libraries and therefore does not establish equivalence or show
that partitioning has no retrieval benefit. The catalog-only condition also
used filename prefixes that leak domain labels. The gate kept essentially
everything in every condition, so it did not provide scoping in this run. The
n = 2 version of this experiment is retained separately as a superseded
record.

**Artifacts.** Reportable ten-question aggregate (B.14 / Src 1); superseded record
(B.14 / Src 2); per-cell records (B.14 / Src 3); and the ablation report (B.14 / Src 4).

### B.15 The sixteen-question gold set

**What was tested.** This entry documents the sixteen-question industrial set used
for the tool-layer runs in B.1 and B.2. The questions are listed in **Table S3**
of this inventory (Part D).

**Scale.** Sixteen questions, `Q1`-`Q16`, defined once in the `QUESTIONS` list
(B.15 / Src 1, lines 195-292). Each entry carries
`qid`, `kb`, `text`, `gloss`, `gold_doc_substrings`, `fact_markers` and an `exp2` flag
marking the four questions included in the agentic end-to-end experiment (`Q2`, `Q4`, `Q6`,
`Q7`). The set is materialised in the artifacts that consume it:
the retrieval results (B.15 / Src 2) hold 16 question ids x 7 methods = 112 rows over a
42-document corpus (`corpus_docs`), and the judge-filter results (B.15 / Src 3) hold 16
rows keyed `Q1`-`Q16`.

**Headline result (provenance).** The questions are **author-written**, in Chinese, over the
five demonstration knowledge bases, for a PV-module manufacturing and process-engineering
domain; they are **not drawn from any public benchmark**. Their design intents, as recorded
in **Table S3** (Part D), span multi-gold questions (Q1), incident-to-root-cause questions (Q2),
mechanism questions (Q3), cross-material questions (Q4), synonym gaps (Q5), numeric
exactness (Q6), confuser density among near-duplicate documents (Q7), plain factual recall
(Q8, Q12), the PV operations family (Q9-Q11), and the telemetry cluster (Q13-Q16). The gold
answers are unique filename fragments (`gold_doc_substrings`) rather than corpus-wide
judgements.

**Inconsistency carried rather than resolved.** The comment block above the list
(B.15 / Src 1, line 190) still reads "Gold question set: 8 domain questions
over the 5 production KBs" while the list itself defines sixteen. The set of record is the
list; the stale comment is reported here as it stands.

**Artifacts.** Question definitions (B.15 / Src 1); retrieval and judge-filter results
(B.15 / Src 2 and B.15 / Src 3); and archived Table S3 from the manuscript before
revision (B.15 / Src 4).

### B.16 Per-question rank table and its generator

**What was tested.** The provenance of **Table S4** of this inventory (Part D), the
per-question best-gold-rank grid for the five reported tool-layer pipelines and two derived
configurations. The generator also emits Dense and RRF columns from the same frozen
artefact; those columns are not reproduced in this document.

**Scale.** One generated table: 16 question rows x 6 method columns (BM25, Graph,
2-stage, Fusion, Hybrid, Filter). Each cell is the best gold rank inside the top-5
window, or `--` where the gold document was not in that window.

**Headline result (generator and inputs).** The generator (B.16 / Src 1) reads exactly
two result inputs: the retrieval artifact (B.16 / Src 3) for the seven tool-layer pipelines
(`bm25`, `dense`, `rrf`, `graph`, `twostage`, `fusion_only`, `hmrs_hybrid`) and the
judge-filter artifact (B.16 / Src 4) for the two derived configurations (`filter_only`,
`rrf_fuse`) replayed over the same logged pools. Question order comes from `QUESTIONS`
(B.16 / Src 2), and the script asserts the input shapes it depends on: 7 x 16 rows in the
first file and 16 rows in the second. Its output (B.16 / Src 5) is marked
`Auto-generated ... do not edit` and is reproduced as Table S4 in Part D.

---

## Part C. Limitations of this evidence

**One deployment, one machine.** Every campaign in this document was run against a single
self-hosted instance on the authors' machine, with the tool layer, the parsers, the graph
store and the vector store all local. Nothing here establishes behaviour under a different
hardware profile, a different index size, a shared deployment, or multi-tenant load. The
concurrency observations in A.3 in particular are properties of one host: 159 of 270
requests completed within the vector-only probe's 30 s window, about 5.3 completions/s
in that window. This observation does not establish an instance throughput ceiling.

**Single-shot and n=2 campaigns.** Several campaigns are single-shot or smoke-scale and
support no variance claim. The isolated-environment probe (A.10) is one document and five
retrieval probes. The two-lane test (A.14) is four questions, and its own retest is n=1.
The abstention runs (B.7) are two questions per lane. The gate ablation (B.13) is ten
questions across three arms but only eight gold-answerable ones, and it was run once, so it
carries no variance estimate either; the retrieval-mode ablation recorded at n=2
(B.14 / Src 2) is retained only as a superseded record and
**supports no claim at all**. Where a campaign ran multiple rounds (A.2, A.13) the rounds
agree, but agreement across two or three rounds on one machine is not a reliability
result.

**Shared pipeline between corpora.** The B.5 run counted 79 document records
in a derived library, not 79 distinct papers. Its arXiv inputs share the ingestion
pipeline used elsewhere in the evaluation. This is not an independent replication:
parser, chunker or router failure modes may be shared.

**A single local judge.** The evaluator used throughout is one local model. In the
stratified run (A.12) it was not configured at all, which is why `notfound_accuracy` is
`null`; in the gate ablation (B.13) one grader prompt scored all three arms, so the arms are
comparable to each other while the grades remain that grader's, and the two cells that
failed with an HTTP 401 mid-run could not be scored at all until they were re-run through
the artifact's repair path. No human adjudication was performed on any
of the answer-quality numbers, and no inter-annotator agreement exists for any of them.
The final reliability round (A.13) is self-checked by the same pipeline, not by an
independent evaluator, and its report explicitly marks the external L2 judge, qrels and
significance testing as not measured.

**Counting and observability gaps that constrain what can be claimed.** The acquisition
campaign (A.4) has an ingest-state list of 91 names and a derived-library count of
79 catalog records. These records are not matched target sets or
funnel stages; neither their difference nor subtraction from 100 identifies failures.
Per-paper parse status, error text and a reliable shared audit date are unavailable. The
five-track matrix (B.12) has no IR metrics at all: P@5, R@10, nDCG@10 and MRR are marked
NOT measured in its own report. The skill-catalogue count is inconsistent across artifacts
19 against 20, tools 94 against 95, and this document reports both rather than choosing.
The 322-part reorganisation campaign's three-source check is a 33-part sample,
not a full pass.

**Coverage limits for selected features.** The available checks range from
limited fixture tests to operations not exercised in the evaluation:

- **Library merge and split.** Sub-library splitting and hierarchy creation were analysed
  but not executed in the 322-part reorganisation (A.6). No controlled test of merge or
  split is reported.
- **Sub-library hierarchy.** The separate three-level fixture (E2, Table S9) passed
  creation, parent-to-child document moves, listing, reading and judging. The
  parent-scope probe (C / Src 1) found a child
  document. Neither check tests library re-parenting or generalises to all nested retrieval.
- **Experience decay and meditation.** The decay cycle, the meditation induction, and the
  `apply_decay` path were never exercised end to end. The sixteen-skill campaign (A.8)
  created experiences and read the dashboard; it did not run review, apply, review-driven
  decay, or meditation. The 50-paper and 322-part campaigns mention automatic
  meditation only as an unrelated background process.
- **Crash durability.** The stress campaign (A.3) measured throughput, latency, rate
  limiting and one soak window; it did not kill the process mid-write and verify
  recovery. The only crash recorded anywhere near this evidence is the tool-layer crash
  during batch parsing in A.4, which was restarted from a checkpoint and is not a
  durability test. Recovery after an unclean shutdown is untested.
- **Authentication on the knowledge-base side.** The only authentication-related result
  is the negative observation that a health-only run at 30 concurrent clients held p50 =
  1.5 ms, which rules out auth middleware as the cause of the slow path (A.3). No test
  exercises login, session expiry, per-user authorisation, rate limiting per identity, or
  denial of an unauthorised knowledge-base operation.

**What the reader should take from this inventory.** The system-level evidence is broad
but shallow in places: many campaigns, mostly thin per campaign, all on one machine, all
scored by one local evaluator. The retrieval matrix is the most useful part of this
document because it is the largest body of repeated measurement the project has, and its
main results are negative: BM25 matches or beats the more elaborate pipelines on both
corpora, the verification gate in the ablation where it was measured kept every gold
document yet moved only two of ten answers (one up, one down) while adding latency,
the unscoped flat partition diagnostic matched the pinned score while searching 15 extra
libraries, so it does not identify a partition effect, although a wrong-library scope missed
the gold document in that setup; and neither NLI replay improved on the platform gate.
Those results are reported here at the scale at which they were
measured.

---

## Part D. Supporting tables and later campaign records

Tables S1-S5 provide store, cross-lingual, question-set, rank and lifecycle
detail. Their older LaTeX sources are the archived appendix (D / Src 1; S1, S2,
S3, S5) and generated rank table (D / Src 2; S4); every value is copied from
its source. S6-S8 report verifier-threshold
and source-presence audits.

### Table S1. Stores and their principal contents

This historical table records the field names used by the implementation and
its audit tools. See A.6 for the archived three-source consistency check and
E2 (Section 8.3) of the revised manuscript for the separate lifecycle check.

| Store | Contents |
|---|---|
| Tree registry (`.tree-fs.json`) | version, root identifier and name, timestamps, node counter and aggregate statistics; per node: identifier, name, type, parent, path, children, metadata map, timestamps. Authoritative structure of the collection. |
| Library metadata (`.knowledge-base.yml`) | library identifier, name, description, timestamps, per-library configuration; per document: path, name, description, tags, content hash, file size, vector-index metadata. The retrieval index read by catalog search. |
| Document files | Markdown body per document or per split part, plus an image directory for figures extracted during parsing. |
| Vector store | one collection per library (cosine space, 1024-dimensional embeddings, HNSW index), holding segment embeddings of 500 characters with 50-character overlap. |
| Graph store | nodes for documents, libraries, tags, folders and entities; edges for membership, tagging, relatedness, identity and containment. |
| Task and session databases | pollable task records for parsing, indexing, graph builds and distillation; chat sessions; distillation signals. |

### Table S2. Cross-lingual ingestion

The cross-lingual results are in Section A.7 above (400 Wikipedia pages per
language, first round; the second reproduced these values bit-for-bit, so one
column is shown). The table retains its number from the archived appendix.

### Table S3. Gold-annotated questions over the five demonstration knowledge bases

"Gold" lists unique filename fragments of the ground-truth documents. All
sixteen were used in the historical tool-layer runs (B.1 and B.2); Q2, Q4, Q6
and Q7 were also used in the archived four-lane grid (B.6). The revised
manuscript discusses the historical ordering diagnostic in E8 (Section 8.9).

| # | Question (abridged, translated) | Gold document(s) | Design intent |
|---|---|---|---|
| Q1 | EVA encapsulation film lamination: how to set the temperature, pressure and time window; how to control cure degree | EVA process essentials; EVA hydro-thermal aging mechanism | multi-gold |
| Q2 | EL inspection shows edge delamination: root cause and corrective actions | EL delamination RCA report (S3 / Src 1) | incident to RCA |
| Q3 | Why does humid aging of EVA generate acetic acid and corrode ribbons; moisture transport mechanism | EVA hydro-thermal aging mechanism | mechanism |
| Q4 | Moisture-barrier behavior of POE encapsulant; lamination differences vs. EVA | POE process essentials | cross-material |
| Q5 | Summer power drop at a PV plant: systematic troubleshooting order | Power-drop troubleshooting manual; O&M lessons | synonym gap ("drop" vs. "plunge") |
| Q6 | Trigger condition, nominal value and tolerance of the line-1027 part weight alarm | Watch-clause document (31.35 g ± 0.05 g, 5 min) | numeric exactness |
| Q7 | Melt temperature fell 206 to 180 °C on extruder line 1: final root-cause verdict | TC0 dead-loop RCA revision (among 20 telemetry dups) | confuser density |
| Q8 | PET biaxial stretching process flow and critical temperature ranges | PET process regulation | plain factual |
| Q9 | Frequent inverter alarm trips: handling steps | Inverter alarm handling manual | PV O&M family |
| Q10 | Hot-spot acceptance criteria and disposal | Hot-spot detection and disposal procedure | PV O&M family |
| Q11 | String mismatch causes; IV-curve diagnosis | String mismatch analysis method | PV O&M family |
| Q12 | PP cast-film extrusion parameters; chill-roll temperature | PP cast film process regulation | plain factual |
| Q13 | Weight closed-loop run1: staircase excitation design | Weight optimization staircase record | telemetry cluster |
| Q14 | FT full-function regression after P0 optimization | FT regression test record | telemetry cluster |
| Q15 | Multimodal diagnosis: fusing scalar, vector and image signals | Three-modality closed-loop record | telemetry cluster |
| Q16 | Post-compensation recovery verification of the heatdecay092 event | heatdecay092 compensation verification (among 3 near-dup incident docs) | confuser density |

### Table S4. Per-question best gold rank (top-5 window)

Best gold rank for the five tool-layer pipelines (logged runs) and the two
derived configurations (offline replay of the same logged HMRS-Hybrid pools).
Fusion = fusion-only (no judge); Hybrid = the judged ordering in the historical
HMRS-Hybrid wrapper; Filter = judge-as-filter. `--` = gold absent from the top-5 window.
Generated by the script in B.16 / Src 1; question texts in Table S3.

| Q | BM25 | Graph | 2-stage | Fusion | Hybrid | Filter |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 1 | 1 | 4 | 1 |
| 2 | 1 | -- | 1 | 1 | -- | 1 |
| 3 | 1 | -- | 1 | 1 | 1 | 1 |
| 4 | 1 | -- | 1 | 1 | -- | 1 |
| 5 | 1 | 1 | 1 | 1 | -- | 1 |
| 6 | 1 | 1 | 1 | 1 | -- | 1 |
| 7 | 3 | -- | 3 | 5 | 3 | 5 |
| 8 | 1 | 1 | 1 | 1 | -- | 1 |
| 9 | 1 | 1 | 1 | 1 | -- | 1 |
| 10 | 1 | 1 | 1 | 1 | 3 | 1 |
| 11 | 1 | 1 | 1 | 2 | -- | 2 |
| 12 | 1 | 1 | 1 | 1 | -- | 1 |
| 13 | 1 | -- | 1 | 1 | 2 | 1 |
| 14 | 1 | 1 | 1 | 1 | 1 | 1 |
| 15 | 1 | -- | 1 | 1 | 5 | 1 |
| 16 | 1 | -- | 2 | -- | -- | -- |

\Needspace{9\baselineskip}

### Table S5. Lifecycle operations exercised on disposable test libraries

Merge and split were analysed but never executed.

| Operation | Observed outcome |
|---|---|
| Create | Pass, document indexed and retrievable |
| Rename | Pass, stale chunks remained until forced re-index (18 recorded, 9 expected) |
| Move | Pass, source 1 to 0 to 1, target 0 to 1 to 0 |
| Delete | Pass, batch delete 1/1; both test libraries removed |
| Re-index | Automatic and batch paths did not purge; pass with `force=true` (18 to 9) |
| Merge, split | Not evaluated |
| Task status | Fail, reports `running` after `finished_at` is set |
| Update check | Fail, `ragctl version` timed out after 30 s |



### A.19 Controlled replication on a common substrate

**What was tested.** The 30-cell answer grid was repeated with every arm restricted to the same five domain libraries (322 stored parts), using different access interfaces. The platform and chunk arms query the libraries' vector collections (500-character segments); the file arm reads the same parts in full. P, F and D are the run tracks a2, b and c; D denotes the chunk arm called C in the revised manuscript. BQ06 was worded differently in the two grids, and the access substrates also changed; the comparison does not isolate an interface, substrate or wording effect.

**Scale.** Ten questions (BQ01-BQ10) x three arms x one run per arm = 30 cells. Same model as the original grid (recorded as claude-opus-4-8[1m]), seed 0, 12-turn configuration; run archived as A.19 / Src 1.

**Headline result.** Gold-identifier coverage 10/10 in every arm; strict keyword coverage 7/7/8; alias-aware coverage 9/9/10; answers with at least one document-style marker 9/9/9 versus 9/7/2 originally (Supplementary Figure S6 and Tables S14--S15). E6 (Section 8.7 of the revised manuscript) reports the separate, later platform-only run.

| Q | Arm | Gold-ID | Strict | Alias | Markers (count) |
|---|---|---|---|---|---|
| BQ01 | D | yes | yes | yes | 2 |
| BQ01 | F | yes | yes | yes | 10 |
| BQ01 | P | yes | yes | yes | 3 |
| BQ02 | D | yes | yes | yes | 2 |
| BQ02 | F | yes | yes | yes | 4 |
| BQ02 | P | yes | yes | yes | 2 |
| BQ03 | D | yes | yes | yes | 2 |
| BQ03 | F | yes | yes | yes | 8 |
| BQ03 | P | yes | yes | yes | 7 |
| BQ04 | D | yes | yes | yes | 1 |
| BQ04 | F | yes | yes | yes | 1 |
| BQ04 | P | yes | yes | yes | 1 |
| BQ05 | D | yes | yes | yes | 0 |
| BQ05 | F | yes | yes | yes | 0 |
| BQ05 | P | yes | yes | yes | 0 |
| BQ06 | D | yes | no | yes | 2 |
| BQ06 | F | yes | no | yes | 5 |
| BQ06 | P | yes | no | yes | 1 |
| BQ07 | D | yes | yes | yes | 1 |
| BQ07 | F | yes | yes | yes | 2 |
| BQ07 | P | yes | yes | yes | 2 |
| BQ08 | D | yes | yes | yes | 2 |
| BQ08 | F | yes | no | no | 6 |
| BQ08 | P | yes | no | no | 4 |
| BQ09 | D | yes | yes | yes | 2 |
| BQ09 | F | yes | no | yes | 5 |
| BQ09 | P | yes | no | yes | 4 |
| BQ10 | D | yes | no | yes | 3 |
| BQ10 | F | yes | yes | yes | 8 |
| BQ10 | P | yes | yes | yes | 5 |

The manuscript's 9/10 per arm is the number of answers with at least one marker;
the Markers column above is the count within an answer, so its column sum is not
the 9/10 figure. BQ03's gold ID appears in the answer or trace in every arm;
the B.5 run on 79 derived-library records logged no top-five gold hit for BQ03.

**Identifier-matched agreement.** The archived comparison joins grids by question identifier and arm (30 cells), but BQ06 has different wording in the two grids; its three cells are therefore not same-question pairs. The table retains the historical identifier-joined counts and exact two-sided McNemar calculations, not a valid fully matched 30-cell comparison or causal test. Both grids also changed access substrates. The original answers were rescored using revised BQ06 annotations. For each binary check the table gives both / original only / replication only / neither and raw agreement (both plus neither). Marker presence means at least one recognized document-style marker; marker counts differ in 24 of 30 identifier-joined cells.

| Measure | Paired counts (both / orig. / repl. / neither) | Agree | p (exact) |
|---|---:|---:|---:|
| Gold ID | 30 / 0 / 0 / 0 | 30/30 | — |
| Alias | 28 / 2 / 0 / 0 | 28/30 | 0.500 |
| Strict | 22 / 5 / 0 / 3 | 25/30 | 0.0625 |
| Marker | 18 / 0 / 9 / 3 | 21/30 | 0.0039 |

All five strict disagreements favour the original grid and all nine marker disagreements favour the common-substrate grid; alias coverage loses BQ08 in the P and F arms in the replication. Excluding BQ06 leaves 27 same-wording, same-arm pairs. In the same order (both / original only / replication only / neither), their counts are gold ID 27 / 0 / 0 / 0; alias 25 / 2 / 0 / 0; strict 22 / 3 / 0 / 2; and marker presence 16 / 0 / 8 / 3. These are descriptive single-run comparisons across different substrates, not evidence of semantic support or a causal effect. The historical script (A.19 / Src 4) joins all 30 cells by identifier and writes the agreement results (A.19 / Src 5); it does not exclude the changed BQ06 wording.

**Arm means.** Wall clock and cost: P 37.7 s / $0.672; F 15.2 s / $0.377; D 19.6 s / $0.524. These are single-run means.

**Artifacts.** Per-cell records (A.19 / Src 1), grades (A.19 / Src 2) and runner
(A.19 / Src 3; `RAG_BENCH_PIN_KB`, `RAG_BENCH_CORPUS_DIR`).

### A.20 Paired route-card audit

**Question.** How do two configured route-card probes differ before document
retrieval and answer generation? This is not an isolated description
treatment, an LLM-agent route-selection test or a QA-accuracy test.

**Corpus and arms.** Ten domain knowledge bases contain 138 documents and 879
stored parts. The paired in-domain set contains 72 gold-domain questions; each
arm also includes four out-of-domain probes, with two cross-placeholder probes
excluded. A0 retains collection descriptions and A3 removes them. The set is
unbalanced: 52/72 questions were automatically expanded, and 47/72 belong to
three English domains (literature 18, medicine 15, science 14).

**Route result.** A0 returned the gold-domain knowledge base for 72/72
questions (100%; Wilson 95% CI [0.949, 1.000]); the nominal name-only A3
condition returned it for 37/72 (51.4%; CI [0.401, 0.626]). The runner queried
a route-card vector index and, on a miss, fell back to a deterministic matcher
over the full catalog. A3 route cards were created without descriptions, but
this fallback could still read original descriptions; traces do not record
whether it ran. The observed contrast therefore does not isolate the causal
effect of description removal. The paired outcomes are:

| A0 outcome | A3 correct | A3 wrong | Total |
|---|---:|---:|---:|
| Correct | 37 | 35 | 72 |
| Wrong | 0 | 0 | 0 |

The exact two-sided McNemar test gives `p = 5.82e-11` (35 A0-only correct
routes, no A3-only correct routes).

**Evidence containment and full-read ablation.** Exact-string containment in
the Laya evidence pack is 37/72 for A0 and 33/72 for A3 (paired
`p = 0.4545`). A1-readall enumerated and read all 879 stored parts, concatenated
the returned text and checked for the same exact strings; it found 72/72
(`p = 5.82e-11` paired with A0). Mean trace-recorded text volume and tool
wall-clock time were 24.3 MB and 253.7 s per question for A1, compared with
31.4 KB and 16.3 s for A0; A3 averaged 23.5 KB and 7.8 s. A0 averaged four
tool calls per question and A1 897. For A0/A3, the byte counter sums the
returned top-ranked candidate snippets and evidence-pack text, which may
overlap. For A1 it sums UTF-8 text returned by document-read calls. These are
not network-traffic totals or measured LLM context. Tool time spans the tool
calls and excludes answer generation. The A1 script made no LLM call and
generated no answer; its result is a mechanical containment upper bound, not
evidence that a model or person can carefully read the corpus and answer
correctly. It measures substring presence, not semantic support or citation
correctness. An audit found exact strings for 14 anchors in the original source
PDFs, but did not verify their survival in parser output or indexed parts. A
real-agent full-read arm remains pending in the experiment checklist.

**Comparison limits.** In the earlier five-arm run, A1b and A2 used an
unscoped global search and returned collections outside the ten evaluation
libraries. The later scoped rerun and its reference-mode judge are described
in the revised manuscript; it remains subject to the gold-domain fallback
limitation stated above. Four out-of-domain probes per arm
are too few for a stable abstention estimate. Empty evidence survivors in a
probe do not demonstrate that the final assistant correctly abstained.

**Artifacts.** Audit report (A.20 / Src 1), traces (A.20 / Src 2), paired statistics
(A.20 / Src 3) and PDF anchor audit (A.20 / Src 4).
Figure 5(a) of the revised manuscript shows this historical routing result alongside
the later scoped follow-up and rerun.

\Needspace{11\baselineskip}

### Table S6. Verdict-score threshold sweep (16 hybrid runs, 191 recorded scores)

Each row re-reads the recorded per-candidate scores and counts survivors at that cut. Gold means the candidate document is an in-pool gold (17 instances); one Q14 candidate has no recorded score and is not counted. This is a score-level sweep: it shows where the verifier would begin to filter, and it does not measure answer quality at a higher cut.

| Cut | Survivors (of 191) | Survivors (%) | Golds kept (of 17) | Non-golds kept (%) |
|---:|---:|---:|---:|---:|
| 0.50 | 191 | 100.0 | 17 | 100.0 |
| 0.60 | 189 | 99.0 | 17 | 98.9 |
| 0.65 | 185 | 96.9 | 17 | 96.6 |
| 0.70 | 182 | 95.3 | 17 | 94.8 |
| 0.75 | 169 | 88.5 | 16 | 87.9 |
| 0.80 | 151 | 79.1 | 16 | 77.6 |
| 0.85 | 114 | 59.7 | 13 | 58.0 |
| 0.88 | 77 | 40.3 | 7 | 40.2 |
| 0.90 | 49 | 25.7 | 4 | 25.9 |
| 0.92 | 29 | 15.2 | 2 | 15.5 |

**Artifacts.** Retrieval results (S6 / Src 1; `judge_scores.all` on the sixteen
`hmrs_hybrid` rows) and question definitions (S6 / Src 2; `QUESTIONS` for the gold
substrings).

### Table S7. Source-presence audit of matched facts (30 answer cells)

For every cell, the audit looks for annotated strict keywords both in the answer and in the separately selected gold document. It does not inspect which source the answer cites, resolve citation markers, verify provenance, or establish that a cited passage supports a claim; keyword co-occurrence is not entailment. Only cells with at least one matched keyword are counted as passing.

| Arm | Cells with at least one matched keyword | Cells where every matched keyword occurs in the gold document |
|---|---:|---:|
| P (platform) | 9 | 9 |
| F (file tools) | 10 | 10 |
| C (chunk) | 10 | 10 |

Across all 30 cells, 29 satisfy the check; the remaining cell (BQ06 in arm P) matched no keyword because its answer is in Chinese.

**Artifacts.** Original grid answers (S7 / Src 1), keywords (S7 / Src 2) and gold
documents (S7 / Src 3).

### Table S8. Source-presence audit of the replication grid (30 answer cells)

Same lexical co-occurrence check as Table S7, run on the common-substrate replication grid (A.19). Every strict keyword matched by an answer occurs in the separately selected gold document in all 30 cells, including the BQ08 cells whose alias coverage fails. The audit does not check that the gold document was cited or that any cited source supports the answer.

| Arm | Cells with at least one matched keyword | Cells where every matched keyword occurs in the gold document |
|---|---:|---:|
| P (platform) | 10 | 10 |
| F (file tools) | 10 | 10 |
| C (chunk) | 10 | 10 |

Across all 30 cells, 30 satisfy the check.

**Artifacts.** Replication grid answers (S8 / Src 1), keywords (S8 / Src 2), gold
documents (S8 / Src 3) and audit script (S8 / Src 4).

### Release checksum manifest

Use the `SHA256SUMS` manifest at the root of the extracted Overleaf release
archive. From that directory, run `sha256sum -c SHA256SUMS`. This checks the
listed package files against their recorded SHA-256 digests; it does not
prevent later changes or reproduce the evaluation. The earlier experiment
freeze list is a historical record, not the verification manifest for this
release.
