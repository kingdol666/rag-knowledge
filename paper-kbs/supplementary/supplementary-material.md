---
title: "Supplementary Material: Complete Inventory of System and Retrieval Test Evidence"
subtitle: "Companion to the manuscript submitted to Knowledge-Based Systems"
---

# Supplementary Material: Complete Inventory of System and Retrieval Test Evidence

This document is the complete inventory of the functional, system-level and retrieval
evidence produced for this project. The manuscript reports its test campaigns in prose
and in a small number of summary tables; the material here is everything else: whole
campaigns that the manuscript only summarises in a sentence, the full retrieval
configuration matrix, and the campaigns whose results are negative, null or unmeasured.

**Provenance rule.** Every number below is copied from the artifact named beside it.
Nothing is rounded, re-derived, or "improved". Where an artifact is internally
inconsistent, the inconsistency is stated rather than resolved. Where the artifact
reports `null`, `NOT measured`, or a failed check, that is reproduced as such.

**Scope.** All results come from a single deployed instance on the authors' machine,
driven through the official harness API and the project's own MCP tool layer. The
counts of test cells are given per campaign so the reader can judge the weight of each
result. Section C states the limitations that apply across all of the evidence. Part D
carries the five appendix tables (S1-S5) that the manuscript cites: they moved here from
the manuscript appendix in the 2026-10-16 revision, and the manuscript's Data-availability
statement points at this document for them.

---

## Part A. System-level test campaigns

Each subsection states what was tested, at what scale, the headline result with the
actual numbers, and the artifact path.

### A.1 Eighteen-scenario end-to-end harness campaign (2026-10-12)

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

The A6 experience was created as `exp-d6f4d47ae3d6` and retrieved by local vector search
at score 0.711. Stage B (second engine) gave 52.4 s / 8 turns / $0.25 (retrieval),
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

**Artifact.** `review/fulltest-20261012/SUMMARY.md`

### A.2 Three-mode stability suite, 27 runs (2026-09-30)

**What was tested.** Three retrieval behaviours (vector-first, catalogue-first, hybrid)
crossed with three question types and repeated over three rounds, through the chat API
in its default non-streaming mode.

**Scale.** 3 tasks x 3 modes x 3 rounds = 27 runs. The three tasks were: a question whose
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

**Artifact.** `review/stability-multiround-20260930/REPORT.md` and the 27 run files
`review/stability-multiround-20260930/results/r{1,2,3}_{attention,seismology,pickles}_{A,B,C}.json`;
runner `review/stability-multiround-20260930/run_stability.py`.

### A.3 Concurrency and load campaign (2026-09-23)

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
p50 = 3743 ms (13.7x baseline) with only 159 of 270 requests completed in 30 s, so the
retrieval throughput ceiling is about 5.3 requests/s per instance - a capacity limit, not
a correctness failure. A 250 KB document (193 KB of UTF-8) indexed in 2.8 s; two real PDFs
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

**Artifact.** `review/stress-20260923/STRESS-REPORT.md`

### A.4 Paper acquisition campaign

**What was tested.** A batch acquisition of arXiv papers, from submission through parsing
to retrievability in the knowledge base.

**Scale.** 100 submitted papers; 26 distinct domain prefixes appear in the routed set.

**Headline result.** 100 papers were submitted; the state file records 91 names; 79 were
retrievable at evaluation time; 21 papers never became retrievable. The 91-versus-79 gap
is **not attributed** by any artifact: the state file has no per-paper parse status and
records no error text, so the campaign cannot say whether the nine papers missing
between submission and the recorded list failed or were never recorded. The failure modes
that were reported are formula-dense scanned papers, which the parser handled poorly, and
one crash of the tool layer during batch parsing that was restarted from a checkpoint.

**Artifact.** `paper-kbs/experiments/results/exp10_ingest_state.json` (knowledge base
`6a3c45f2-a1a1-4ce7-b64d-7a5a2f293bb5`, parse task `40f6fd42930d`, `parse_task_done`
true, 10 entries in `saved`, 91 entries in `saved_all`) and
`paper-kbs/experiments/results/exp10_papers_toollayer.json` (`n_docs` 79).

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

The routing run of the same campaign took 1,115.5 s at 16.3-40.4 s per paper, produced
202 tags, batch-indexed 50 documents and reported `all_probes_ok`; in that run 43 of the
50 documents carried `tag_ok: false` while `verify_ok` passed for all 50, so the
tag-quality check failed often without blocking ingestion. Two caveats attach to the
30,000-character tier: one stage re-ran because of inbox ordering, and more than 800
extracted images were not uploaded.

The single regression failure is instructive rather than a retrieval error: for the
precipitation-extremes question the gold document was hit at rank 1-3 in every round, but
the literal phrase checked for ("precipitation efficiency") fell outside the returned
chunk window because the answer sentence sits in a continuation paragraph cut by the
30,000-character boundary. This is a chunk-window effect, not a wrong-library retrieval.

**Artifacts.** `benchmark-suite/results/BENCHMARK-30000chunk-20260918.md`;
`paper-kbs/notes/functional-test-evidence-2026-10-12.md`;
`paper-kbs/tex/journal_20p/n8a_eval.tex`.

### A.6 Three-hundred-and-twenty-two-document reorganisation campaign

**What was tested.** The full reorganisation workflow over the combined arXiv corpus:
per-document content audit, description upgrade, tag de-duplication, batch re-indexing,
near-duplicate adjudication, three-source consistency and retrieval regression.

**Scale.** 322 documents across five libraries; 165 descriptions upgraded; 35
near-duplicate candidate groups.

**Headline result.**

- 322/322 metadata checks passed; the per-document content audit assertion passed 322/322.
- 165/165 descriptions were upgraded from the earlier "title; excerpt" form to the
  four-element two-layer form, with 165 OK / 0 bad on read-back.
- Tag de-duplication: 4/4 duplicate tag sets resolved.
- All 322 documents were batch-indexed with `force`.
- 15/15 retrieval regression probes passed after reorganisation, i.e. zero degradation.
- 35 near-duplicate candidate groups (similarities 0.90-0.975) were adjudicated to
  **zero true duplicates**: every group was a set of adjacent parts of the same paper.
  No document was deleted.

Two honesty notes are recorded with the campaign. The three-source consistency spot check
sampled 33 of the 322 documents, so it is a sample and not a full pass. Sub-library
splitting and hierarchy creation were analysed but deliberately not executed pending user
confirmation, so this campaign is **not** evidence for hierarchical restructuring.

A scaling comparison ran alongside it. Against a fixed 50-question set over the first
corpus, doubling the corpus from 50 to 100 papers (163 to 322 stored documents) left
retrieval precision unchanged: pass rate 48/50 = 96%, MRR 0.98 and top-1 similarity 0.759
were identical before and after. After the description upgrade and forced re-index, the
same fixed set improved to 49/50 = 98% with MRR 1.00. The newly ingested 50 papers were
100% retrievable at the 100-paper scale on both channels (50/50, MRR 1.0).

**Artifacts.** `paper-kbs/notes/functional-test-evidence-2026-10-12.md` (the campaign's
per-check counts and its two honesty notes);
`benchmark-suite/results/R2-SCALING-20260921.md` (the before/after scaling comparison);
`paper-kbs/tex/journal_20p/n8a_eval.tex`.

### A.7 Cross-lingual ingestion campaign

**What was tested.** Whether the ingest gates hold without any language-specific tuning,
over Wikipedia pages in three languages, run twice.

**Scale.** 400 Wikipedia pages per language (English, Chinese, Japanese), two rounds.
Membership and ingestion success are computed over all 400 pages per language; storage
completeness and self-retrieval Hit@1 use a 40-page or 40-query sample per language.

**Headline result.** Round 2 reproduced round 1 bit-for-bit, so one column is shown.
This table is **Table S2** of the manuscript appendix (Part D).

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

**Artifacts.** `paper-kbs/tex/journal_20p/_appendix-archived/n_appendix_tables.tex`
(Table S2; manuscript source before the 2026-10-16 revision);
`paper-kbs/tex/journal_20p/n8a_eval.tex`;
`paper-kbs/tex/journal_20p/n4_acquisition.tex`. The underlying run outputs are retained under
`benchmark-web/benchmark/results/benchmark/`, which lives in the web-repository checkout
and not in this repository; the numbers above are therefore taken from the manuscript
table that reports them.

### A.8 Sixteen-skill lifecycle scenarios (2026-09-24)

**What was tested.** Every knowledge-base skill, exercised end to end through the
project's own stdio MCP client against a live backend and web instance, using two
disposable libraries that were created for the test and deleted afterwards.

**Scale.** 16 skills, 109 real tool calls. Two test libraries
(`E2E-SkillTest-1457` = `95f4e9a1-b24d-43c1-b94d-04c55d90b5d1`, `E2E-SkillTest-Dst-1457`
= `c2e2bf92-db86-48f5-96f8-7ac9b9931f67`), 94 registered tools verified. Pre-existing
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
  confidence 0.62, 27.7 s), but `soul_qdcvr_ask` launched asynchronously (task
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

**Artifacts.** `benchmark-suite/results/SKILL-E2E-REPORT.md`;
raw call log `.e2e/skilltest/calls.jsonl` (109 calls).

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

**Artifacts.** `benchmark-suite/results/SKILL-AUDIT.md`;
`benchmark-suite/results/SKILL-SMOKE.md`;
`benchmark-suite/results/SKILL-STANDARD-AND-CHAT-LANE-TEST.md`.

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

**Artifact.** `benchmark-suite/results/SKILL-E2E-REPORT.md`

### A.11 Three-channel retrieval end-to-end campaign (2026-10-12)

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
  questions) and six baseline cells all hit the gold document. Against the 2026-09-26
  baseline this is a large latency improvement: mode B 342 s / 234 s to 25.0 s / 10.2 s,
  mode C 1152 s / 1818 s to 37.3 s / 33.7 s. The four baselines (BM25, vector, RRF,
  rerank) each returned 10/10, 1/3, 10/10 and 10/10 documents for the two questions.

Channel 1 mean latencies were A = 47.0 s, B = 142.2 s, C = 51.2 s; the failing cell alone
was 353.5 s against 29.9-65.0 s for the other eight, and its engine time was 352.7 s. All
nine cells were otherwise PASS.

**Artifacts.** `review/retrieval-e2e-20261012/REPORT.md` and
`review/retrieval-e2e-20261012/channel1_summary.json`;
`benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/CHAT-MODES-COMPARE.md`;
`benchmark-suite/results/runs/run-20261012T062847Z-5f9faac/RETRIEVAL-COMPARE.md`.

Note the difference in external baseline tables between the two runs is a corpus
difference, not a contradiction: in `run-20261012T062847Z` the BM25 and RRF baselines
were scored on a 100-document markdown corpus and the vector baseline on the platform's
cross-library index, and the chat-mode run reports the system arms while the retrieval
run reports mode cells.

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

The run identifier is `experiment_chat_20260922-211000` using `qa_questions.json`. Two
things must be recorded with these numbers. First, `notfound_accuracy` is `null` and the
judge-derived "correct" field is `None` for every row, because the judge was not
configured; the only populated stratum is "single" at 10 of 10 per track, so the three
tracks are not actually stratified in this run. Second, the false-refusal rate of 0.0
across all three tracks is accompanied by zero should-refuse questions, and the report
itself notes that refusal-accuracy-only rules are equivalent to "always refuse", so both
directions must be reported together.

**Artifact.** `benchmark-suite/results/stratified_grade_smoke.md` and
`benchmark-suite/results/stratified_grade_smoke.json`

### A.13 Harness and honest-refusal campaign (2026-09-30)

**What was tested.** Two things: a three-mode system-arm comparison against fixed gates,
and a two-round harness reliability run over ten questions crossed with five methods.

**Scale.** System arms 3 modes x 3 questions (one out-of-domain) = 9 cells; the
reliability run covered 10 questions x 5 methods x 2 rounds = 100 units, with a 50-unit
self-check.

**Headline result.**

- System arms: run `chatmodes-20260930T143945Z-3ec2174` **passed 9/9 gates** (exit code
  0). Mode A: cm1 85.5 s / 6 turns, cm2 83.6 / 5, cm3 76.1 / 5. Mode B: cm1 196.9 / 17,
  cm2 142.2 / 9, cm3 316.0 / 19 (before the fix described below). Mode C: cm1 99.1 / 7,
  cm2 89.9 / 8, cm3 72.0 / 5. The two gold papers were hit verbatim and the out-of-domain
  question was refused with zero fabrication in all three modes.
- Reliability run, round 1 (`run-20260930T165316Z`): gold 0.75, citation 0.75, mean
  41.5 s, 5.1 tools per question, over-refusal 0, errors 0, $3.75. Round 2
  (`run-20260930T170730Z`): **gold 1.00, citation 1.00**, mean 34.1 s, 5.2 tools per
  question, over-refusal 0, errors 0, $4.50. The self-check passed 6/6 in both rounds over
  50 units each (cost consistent, provenance complete).
- Four retrieval-only baselines (BM25, vector, RRF, rerank) achieved retrieval gold 1.0
  but closed-book over-refusal of 37.5-62.5%, which quantifies what the answer layer adds
  over raw retrieval.
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

**Artifact.** `benchmark-suite/results/PIPELINE-REPORT-20260930.md`

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

**Artifact.** `benchmark-suite/results/SKILL-STANDARD-AND-CHAT-LANE-TEST.md`

### A.15 Three-engine and three-channel cost campaign (2026-10-12)

**What was tested.** What the same kind of task costs when it is delivered three different
ways. First, three **engines** on one task set: the agent surface
(`/api/kb/agent/chat`), the Claude harness (`engine=claude`) and the OMP harness
(`engine=omp`). Second, the three **delivery channels** of the same day's three-channel
campaign run over the same three retrieval modes.

**Scale.** 18 runs in the engine campaign (7 agent-surface scenarios, 6 Claude-harness
scenarios, 5 OMP-harness scenarios); 9 runs each in channel 1 and channel 2 of the
three-channel campaign. The engine campaign's own verdict is 18 of 18 scenarios PASS, every
answer gold-hit, zero fabricated citations.

**Headline result.**

| Condition | Runs | Wall clock (s) | Turns | Cost per run |
|---|---:|---|---:|---|
| Agent surface (`/api/kb/agent/chat`) | 7 | 50.5-175.9 | 2-9 | $0.9-1.8 |
| Claude harness (`engine=claude`) | 6 | 23.2-52.4 | 5-8 | $0.11-0.36 |
| OMP harness (`engine=omp`) | 5 | 33.5-171.4 | 2-9 | $0.03-0.07 |
| Channel 1 (streaming harness, `engine=claude`; 8 of 9 gates) | 9 | 29.9-353.5 | 5-8 | $0.12-0.25 |
| Channel 2 (non-streaming chat API; 8 of 9 gates) | 9 | 25.7-100.0 | 4-11 | not metered |

The three engines separate by one to two orders of magnitude in cost at one quality tier
(the agent surface $0.9-1.8, the Claude harness $0.11-0.36, the OMP harness $0.03-0.07). The
OMP harness's wall clock is about twice its engine time because it pays a 50-90 s harness
cold start per call; the Claude harness's wall clock is approximately its engine time. The
third channel of the same campaign is pure retrieval with no LLM call at all: 12
method-question cells with the gold document present in all 12, 10.2-37.3 s against 0.0-0.1 s
for the lexical and vector baselines, at zero token cost.

**Artifacts.** `review/fulltest-20261012/SUMMARY.md` (the 18 engine runs, per scenario);
`review/retrieval-e2e-20261012/channel1_summary.json` and
`review/retrieval-e2e-20261012/REPORT.md` (channel 1);
`benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/CHAT-MODES-COMPARE.md`
(channel 2); `benchmark-suite/results/runs/run-20261012T062847Z-5f9faac/RETRIEVAL-COMPARE.md`
(channel 3, the pure-retrieval matrix);
`paper-kbs/notes/functional-test-evidence-2026-10-12.md` (reproduces the three-engine row
and cites the summary's line range); `paper-kbs/supplementary/supplementary-material.md` (this table; the
manuscript no longer carries it). The cost rows are **not** carried by any `exp8b*` artifact: the `paper-kbs/experiments/results/exp8b*.json`
glob resolves to exactly one file, `paper-kbs/experiments/results/exp8b_absent_agent.json`,
and that file carries the three absent-tier agent probes of B.7, not the cost table.


### A.17 The 30-cell answer grid: wall clock, tools and cost per cell

**What was tested.** The per-cell time, tool count and metered cost of the three-arm answer grid whose quality results the manuscript reports as Table 6 (gold-ID presence, strict keyword coverage, alias-aware coverage and citation-marker counts). The manuscript reports the quality cells and one sentence of arm means; the per-cell records live here.

**Scale.** 30 cells: ten questions (BQ01-BQ10) x three arms (P = platform read tools, F = file tools over the exported tree, D = dense index over the 800-character mirror).

**Headline result.** Arm means: P 52.6 s / 6.0 tools / $0.711; F 22.2 s / 6.4 tools / $0.487; D 24.5 s / 3.7 tools / $0.527. The platform arm is the slowest and most expensive in this single run; the manuscript reports this as an observation about this implementation, not an efficiency result.

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
| BQ01 | D (dense) | 34.1 | 5 | 0.610 |
| BQ02 | D (dense) | 21.4 | 2 | 0.483 |
| BQ03 | D (dense) | 18.6 | 2 | 0.454 |
| BQ04 | D (dense) | 17.0 | 2 | 0.442 |
| BQ05 | D (dense) | 30.0 | 4 | 0.581 |
| BQ06 | D (dense) | 48.6 | 11 | 0.801 |
| BQ07 | D (dense) | 11.2 | 2 | 0.412 |
| BQ08 | D (dense) | 19.7 | 2 | 0.468 |
| BQ09 | D (dense) | 23.3 | 3 | 0.516 |
| BQ10 | D (dense) | 21.3 | 4 | 0.503 |

**Artifacts.** `benchmark-suite/results/runs/run-20261013T094350Z-5f9faac/track_*.json` (one file per cell; `latency_s`, `tool_call_count`, `total_cost_usd`); arm aggregates recomputed here. The manuscript's Table 6 is graded from the same run by `benchmark-suite/results/exp_r2_grade_corrected.json`.

### A.16 Failure-mode catalogue

**What was tested.** Not an experiment. This entry documents the provenance of the
failure-mode catalogue (`tab:failures` in `paper-kbs/tex/n9_discussion.tex`), whose nine rows
are production incidents recorded during the campaigns plus the defects those campaigns
surfaced.

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
The catalogue is compiled from the incident logs held in `paper-kbs/notes/`, and those notes
in turn cite the campaign artifacts that recorded each incident. The four notes actually
found to carry it are:

- `paper-kbs/notes/review-round3-2026-10-09.md` — the request that produced the table
  (consolidate the incident log into failure -> detection signal -> fix -> residual risk) and
  the item tracking it.
- `paper-kbs/notes/review-2026-10-08.md` — the Windows driver-contention incident (the
  end-to-end regression from 68 s to 27 min).
- `paper-kbs/notes/restructure-plan-2026-10-12.md` — the out-of-memory indexing run that
  returned an empty payload in a success envelope.
- `paper-kbs/notes/functional-test-evidence-2026-10-12.md` — the campaign defects: the
  three-source check that found `chunk_count=18` where 9 chunks exist, the graph node that
  was not created, and the graph-build task left reporting `running`.

The campaign artifacts those notes cite are
`benchmark-suite/results/SKILL-E2E-REPORT.md`, `benchmark-suite/results/graph_stats.json`
and `benchmark-suite/results/tags_report.json`. Rows in the catalogue that no note in
`paper-kbs/notes/` traces to a recording artifact are reported here as carried only by the
chapter's own incident log, not as independently recorded.

**Artifacts.** No dedicated catalogue artifact; the carrier files are the four notes listed
above, with `benchmark-suite/results/SKILL-E2E-REPORT.md`,
`benchmark-suite/results/graph_stats.json` and `benchmark-suite/results/tags_report.json`
behind them.

---

## Part B. Retrieval evaluation matrix

Every retrieval configuration the project has measured, with its corpus, question count,
metrics and artifact path. Metrics are `hit@5 / recall@5 / MRR` unless a row states
otherwise. Rows are grouped by corpus and experiment, not by claim.

### B.1 Nine configurations on the 42-document corpus

Corpus: the live deployment's five libraries, 42 documents, 16 gold-annotated questions
(one library contains twenty near-duplicate equipment-telemetry reports). BM25 index
build took 0.61 s.

| Configuration | hit@5 | recall@5 | MRR | latency mean (s) | latency p50 (s) |
|---|---:|---:|---:|---:|---:|
| bm25 | 1.0 | 1.0 | 0.958333 | 0.001 | 0.001 |
| dense | 0.9375 | 0.9375 | 0.85625 | 0.018 | 0.017 |
| rrf | 1.0 | 1.0 | 0.927083 | 0.011 | 0.009 |
| graph | 0.5625 | 0.53125 | 0.5625 | 0.068 | 0.068 |
| twostage | 1.0 | 0.96875 | 0.927083 | 0.077 | 0.04 |
| fusion_only | 0.9375 | 0.9375 | 0.85625 | 0.062 | 0.066 |
| qdcvr_hybrid | 0.4375 | 0.40625 | 0.226042 | 0.542 | 0.581 |

**Artifact.** `paper-kbs/experiments/results/exp1_summary.json`

### B.2 Judged / as-filter / RRF-fuse decomposition on the same corpus

Same 42 documents and 16 questions. Each row reports `hit@5 / recall@5 / MRR`. `n_fusion`
was 12 candidates per question and `n_survivors` 12, except Q14 at 11.

| Configuration | hit@5 | recall@5 | MRR |
|---|---:|---:|---:|
| judged | 0.4375 | 0.40625 | 0.22604167 |
| filter_only | 0.9375 | 0.9375 | 0.85625 |
| rrf_fuse | 0.875 | 0.875 | 0.60625 |

Two remarks that the artifacts themselves support rather than conceal. First, `judged`
here reports the same values as `qdcvr_hybrid` in B.1 to five decimal places, so the two
names denote the same measurement and should not be counted twice. Second, `rrf` in B.1
(1.0 / 1.0 / 0.927083) and `rrf_fuse` here (0.875 / 0.875 / 0.60625) are different
configurations despite the similar name, and the difference is not explained by either
artifact.

**Artifacts.** `paper-kbs/experiments/results/exp5_judge_filter.json`;
`paper-kbs/experiments/results/exp1_summary.json`

### B.3 Threshold selection on the same corpus (leave-one-out)

The candidate-cut threshold was chosen by leave-one-out over the 16 questions on a grid
from 0.05 to 0.40 in steps of 0.01, using a smallest-margin rule on the 15 training
questions. Across 16 folds the leave-one-out gold survival was 0.9375 against 1.0 for a
fixed 0.20 cut, and the selected thresholds were 0.15 and 0.18.
Q11 is the only fold that selected 0.15, and it is the only fold whose holdout gold
document was not kept. Every fold kept the gold document at a fixed 0.20 cut, which is the
artifact's justification for not adopting the leave-one-out threshold.

**Artifact.** `paper-kbs/experiments/results/exp6_loo_margin.json`

### B.4 Same nine configurations on the paraphrase grid (16 paraphrases)

Each question was re-asked with 16 paraphrases.

| Configuration | hit@5 | recall@5 | MRR |
|---|---:|---:|---:|
| bm25 | 0.875 | 0.875 | 0.7552083333333334 |
| dense | 0.9375 | 0.9375 | 0.8333333333333334 |
| rrf | 0.875 | 0.875 | 0.8125 |
| graph | 0.5625 | 0.5 | 0.5625 |
| twostage | 0.9375 | 0.90625 | 0.90625 |
| fusion_only | 0.9375 | 0.9375 | 0.8333333333333334 |
| judged | 0.5 | 0.46875 | 0.18854166666666666 |
| filter_only | 0.9375 | 0.9375 | 0.8333333333333334 |
| rrf_fuse | 0.875 | 0.84375 | 0.6291666666666667 |

The paraphrase grid costs every configuration except `dense`, `twostage` and
`fusion_only`, which hold their B.1 values. The judged configuration loses the most.

**Artifact.** `paper-kbs/experiments/results/exp6_paraphrase.json`

### B.5 Eight configurations on the second corpus (79 retrievable arXiv papers)

Corpus: 79 retrievable papers (Section A.4), 10 questions `BQ01`-`BQ10`. Values are
hit@5.

| Configuration | hit@5 |
|---|---:|
| bm25 | 0.9 |
| dense | 0.9 |
| rrf | 0.9 |
| graph | 0.2 |
| twostage | 0.9 |
| fusion_only | 0.9 |
| judged | 0.9 |
| filter_only | 0.9 |

`BQ03` was missed by **every** configuration. Per-question latency in seconds: BQ01
2.253, BQ02 0.621, BQ03 0.233, BQ04 0.187, BQ05 0.242, BQ06 0.185, BQ07 0.171, BQ08
0.178, BQ09 0.192, BQ10 0.206; candidate counts were 10-12 and kept counts 5-11.

**Artifact.** `paper-kbs/experiments/results/exp10_papers_toollayer.json`

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

**Artifacts.** `paper-kbs/experiments/results/exp2_lanes/summary.json`,
`.../summary_gen.json`, `.../run_{search,librarian,hybrid,bare}-Q{2,4,6,7}.json`;
`paper-kbs/experiments/results/exp2_lanes_rep2/summary.json` and its run files.

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

**Artifacts.** `paper-kbs/experiments/results/exp4_abstention/run_{hybrid,librarian,search}-O{1,2}.json`;
`paper-kbs/experiments/results/exp8b_absent_agent.json`

### B.8 Out-of-corpus probes at the tool layer

Four out-of-corpus questions were run through the tool layer alone (no LLM answer) to see
how many candidates survive the gate, out of 12.

| Probe | Topic | Vector top score | Candidates above 0.35 | Merged | Kept of 12 | Reads | Latency (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| O1 | lithium battery thermal runaway | 0.596 | 4 | 43 | 11 | 5 | 0.7 |
| O2 | child vaccination schedule | 0.397 | 8 | 42 | 11 | 5 | 0.15 |
| O3 | Python multiprocessing vs threading | 0.511 | 10 | 43 | 9 | 5 | 0.16 |
| O4 | injection-mould vent design | 0.538 | 7 | 43 | 11 | 5 | 0.16 |

The same artifact replays the candidate cut on the in-corpus question set, reporting how
many of the 17 gold documents survive at each threshold: 8 at cut 0.05, 14 at 0.10, 16 at
0.15, and 17 at every cut from 0.20 to 0.35.

**Artifact.** `paper-kbs/experiments/results/exp3_abstention.json`

### B.9 Graded probes on a partially-answerable set

Six tool-layer probes on questions graded partial-answerable (PA) or absent (AB), plus
three agent-layer probes on the same partial-answerable questions. Retained candidates are
out of 12.

| Probe | Kind | Merged | Kept | Top score | Span of kept scores | Latency (s) |
|---|---|---:|---:|---:|---|---:|
| PA1 | partial | 12 | 12 | 0.954 | 0.954 down to 0.666 | 7.83 |
| PA2 | partial | 12 | 12 | 0.876 | 0.876 down to 0.511 | 1.44 |
| PA3 | partial | 12 | 11 | 0.965 | 0.965 down to 0.55 | 0.68 |
| AB1 | absent | 12 | 10 | 0.983 | 0.983 down to 0.5 | 0.67 |
| AB2 | absent | 12 | 11 | 0.968 | 0.968 down to 0.813 | 0.64 |
| AB3 | absent | 12 | 11 | 0.944 | 0.944 down to 0.592 | 0.79 |

Every tool-layer probe retains 10-12 of 12 candidates and top scores reach 0.983 on a
question the corpus cannot answer, which is the clearest single demonstration in this
project that a high vector score is not evidence of an answer. The agent layer on the
same partial questions is much slower and gives no turn counts: 47.9 s / 724 characters,
65.9 s / 840 characters, 155.7 s / 774 characters.

**Artifact.** `paper-kbs/experiments/results/exp8_graded_probes.json`

### B.10 NLI second signal (first replay)

A local NLI model (`IDEA-CCNL/Erlangshen-Roberta-330M-NLI`) was replayed as a second
scoring signal over the same candidate pairs as the platform gate, n = 191 pairs.

| Quantity | Value |
|---|---:|
| NLI hit@5 / MRR | 0.3125 / 0.1375 |
| Platform gate hit@5 / MRR (same pairs) | 0.4375 / 0.22604166666666667 |
| NLI score, gold median | 0.0113 |
| NLI score, non-gold median | 0.05285 |
| NLI score, gold minimum | 0.0001 |
| NLI score, non-gold maximum | 0.9992 |
| Mann-Whitney p | 0.120243225159967 |
| Cliff's delta | 0.22853279242731575 |
| Spearman rho | -0.13420631455001675 |

The direction is wrong: the non-gold median is higher than the gold median, the
correlation with gold rank is negative, and the separation is not significant at
p = 0.12024. One symbolic sub-check is also recorded: for Q6, gold documents containing
the literal string `3135` were 1 of 1 while non-gold documents containing it were 0 of 11.
The artifact additionally carries a full out-of-corpus replay over the corpus documents.

**Artifact.** `paper-kbs/experiments/results/exp7_second_signal.json`

### B.11 Span-level NLI (second replay)

The same idea applied at span level rather than document level, over the same 191 pairs.

| Signal | hit@5 | MRR |
|---|---:|---:|
| platform gate | 0.4375 | 0.22604166666666667 |
| NLI, head | 0.3125 | 0.1375 |
| NLI, span | 0.1875 | 0.09375 |
| rank ensemble | 0.3125 | 0.11145833333333333 |

Span separation: gold median 0.4728 against non-gold median 0.91855 (gold minimum
0.0002, non-gold maximum 0.999), Mann-Whitney p = 0.007414975017999724. The separation is
significant and in the wrong direction, and span-level scoring is worse than head-level
scoring as a ranker. Neither NLI replay improves on the platform gate.

**Artifact.** `paper-kbs/experiments/results/exp9_span_nli.json`

### B.12 Five-track by ten-question matrix

Run `run-20260930T174948Z-3ec2174` crossed five tracks (`a2`, `bm25`, `vector`, `rrf`,
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
all five tracks exist as `track_{a2,bm25,vector,rrf,rerank}_QK01..QK10.json`, so the raw
material is present even though the summary table is not populated. This document records
the absence of the metrics rather than substituting anything for them.

**Artifact.** `benchmark-suite/results/runs/run-20260930T174948Z-3ec2174/`
(`REPORT.md`, `report.json`, `run_manifest.json`, `track_*_QK*.json`)

### B.13 Verification-gate ablation, ten questions (2026-10-12)

Three arms over one ten-question set and one **frozen shared candidate set**: `C-nogate`,
the ungated control; `C-judge`, the gate applied to those frozen candidates; and
`C-judge-seg`, the same gate with evidence taken at segment granularity. Because the
candidate set is frozen before the arms diverge, the gate is the only difference between
conditions. An earlier protocol built around `kb_hybrid_search(enable_judge=...)` was
superseded and is **not** reported here.

**Scale.** Ten questions (`QK01`-`QK10`) from `benchmark-suite/data/papers/qa_quick10.json`
against the live five-library corpus, candidate cap 12, gate threshold 0.5 with criterion
`auto` and `reference_mode` true, evidence pack budget 4000 characters. Thirty answer
cells (three arms x ten questions), 30 answer calls, $1.0015 of metered answer cost. Eight
of the ten questions are gold-answerable; `QK09` is unanswerable and `QK10` is out of
corpus, and both are excluded from the gold-level means.

| Arm | Mean grade, all ten | Mean grade, eight gold-answerable | Gold docs surviving | Mean documents per cell | Mean latency (s) |
|---|---:|---:|---:|---:|---:|
| C-nogate (ungated control) | 1.8 | 1.0 | 8 of 8 | 12.0 | 6.92 |
| C-judge (gate on frozen candidates) | 2.0 | 1.25 | 8 of 8 | 11.2 | 7.65 |
| C-judge-seg (segment-granular evidence) | 1.3 | 0.375 | 8 of 8 | 11.2 | 6.37 |

**Headline result.**

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
`kb_hybrid_search(enable_judge=...)`, is not registered on the shipped tool layer, so the
ablation was rebuilt around `kb_laya_judge` applied to a frozen shared candidate set. The
consequence for reading these numbers is stated in the artifact and repeated here: only
the within-run contrast between the three arms is comparable to anything, and no number in
this entry is comparable to a run of the superseded protocol.

**Artifacts.** `paper-kbs/experiments/results/exp11_gate_ablation.json`;
`paper-kbs/experiments/results/exp11/exp11-20261012-full/` (`cell_QK01..QK10.json`,
`cand_QK01..QK10.json`, `repairs.json`);
`paper-kbs/notes/exp11-gate-ablation-report.md`

### B.14 Library-partition ablation

Four conditions x ten questions = 40 retrieval cells, no LLM calls, over the live
five-library corpus. Both `score_threshold` and the gate were held identical across
conditions (`top_k=10`, `score_threshold=0.0`, gate threshold 0.5) so that an empty
result cannot be an artifact of the threshold.

| Condition | hit@5 | hit@10 | Mean gold rank | Mean candidates | Mean kept after gate | Mean latency (s) |
|---|---:|---:|---:|---:|---:|---:|
| pinned-gold (correct library) | 1.0 | 1.0 | 1.0 | 2.75 | 2.75 | 0.462 |
| pinned-other (routing mistake) | 0.0 | 0.0 | null | 7.125 | 6.875 | 0.487 |
| flat (no library restriction) | 1.0 | 1.0 | 1.0 | 2.5 | 2.5 | 0.3 |
| catalog-only (descriptions only) | 1.0 | 1.0 | 1.75 | 235.75 | 11.375 | ~0.0 |

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

Three of the artifact's own conclusions are load-bearing and are reproduced: a routing
mistake never recovered the gold document (0.0 hit@5 and hit@10 on all 8 graded
questions); the partition bought **nothing measurable** on the retrieval path, because
`flat` scored exactly as well as `pinned-gold` and even returned fewer candidates; and the
gate kept essentially everything in every condition, so it is not doing scoping work here.
The n = 2 version of this experiment is retained separately as a superseded record.

**Artifacts.** `paper-kbs/experiments/results/exp12_partition_ablation.json` (the
reportable ten-question aggregate);
`paper-kbs/experiments/results/exp12_partition_ablation_n2.json` (superseded);
`paper-kbs/experiments/results/exp12/exp12-20261012-full/cell_QK01..QK10.json`;
`paper-kbs/notes/exp12-partition-ablation-report.md`

### B.15 The sixteen-question gold set

**What was tested.** This entry documents the question set that is the denominator of every
retrieval table in Part B and of **Table S3** of the manuscript appendix (Part D).

**Scale.** Sixteen questions, `Q1`-`Q16`, defined once in
`paper-kbs/experiments/kbcommon.py` (the `QUESTIONS` list, lines 195-292). Each entry carries
`qid`, `kb`, `text`, `gloss`, `gold_doc_substrings`, `fact_markers` and an `exp2` flag
marking the four questions included in the agentic end-to-end experiment (`Q2`, `Q4`, `Q6`,
`Q7`). The set is materialised in the artifacts that consume it:
`paper-kbs/experiments/results/exp1_retrieval.json` holds 16 question ids x 7 methods = 112
rows over a 42-document corpus (`corpus_docs`), and
`paper-kbs/experiments/results/exp5_judge_filter.json` holds 16 rows keyed `Q1`-`Q16`.

**Headline result (provenance).** The questions are **author-written**, in Chinese, over the
five production knowledge bases, for a PV-module manufacturing and process-engineering
domain; they are **not drawn from any public benchmark**. Their design intents, as recorded
in **Table S3** (Part D), span multi-gold questions (Q1), incident-to-root-cause questions (Q2),
mechanism questions (Q3), cross-material questions (Q4), synonym gaps (Q5), numeric
exactness (Q6), confuser density among near-duplicate documents (Q7), plain factual recall
(Q8, Q12), the PV operations family (Q9-Q11), and the telemetry cluster (Q13-Q16). The gold
answers are unique filename fragments (`gold_doc_substrings`) rather than corpus-wide
judgements.

**Inconsistency carried rather than resolved.** The comment block above the list
(`paper-kbs/experiments/kbcommon.py`:190) still reads "Gold question set: 8 domain questions
over the 5 production KBs" while the list itself defines sixteen. The set of record is the
list; the stale comment is reported here as it stands.

**Artifacts.** `paper-kbs/experiments/kbcommon.py` (the definitions);
`paper-kbs/experiments/results/exp1_retrieval.json`;
`paper-kbs/experiments/results/exp5_judge_filter.json`;
`paper-kbs/tex/journal_20p/_appendix-archived/n_appendix_tables.tex`
(Table S3; manuscript source before the 2026-10-16 revision).

### B.16 Per-question rank table and its generator

**What was tested.** The provenance of **Table S4** of the manuscript appendix (Part D), the
per-question best-gold-rank grid for all nine retrieval pipelines.

**Scale.** One generated table: 16 question rows x 9 method columns (BM25, Dense, RRF, Graph,
2-stage, Fusion, Hybrid, Filter, RRF-fuse). Each cell is the best gold rank inside the top-5
window, or `--` where the gold document was not in that window.

**Headline result (generator and inputs).** The table is produced by
`paper-kbs/experiments/derive_appendix.py`, which reads exactly two inputs:
`paper-kbs/experiments/results/exp1_retrieval.json` for the seven tool-layer pipelines
(`bm25`, `dense`, `rrf`, `graph`, `twostage`, `fusion_only`, `qdcvr_hybrid`) and
`paper-kbs/experiments/results/exp5_judge_filter.json` for the two derived configurations
(`filter_only`, `rrf_fuse`) replayed over the same logged pools. Question order comes from
`QUESTIONS` in `paper-kbs/experiments/kbcommon.py`, and the script asserts the input shapes
it depends on: 7 x 16 rows in the first file and 16 rows in the second. Its output is written
to `paper-kbs/tex/journal_20p/_appendix-archived/tab_appendix_ranks.tex`, marked
`Auto-generated ... do not edit`, and is reproduced as Table S4 in Part D.

**Artifacts.** `paper-kbs/experiments/derive_appendix.py`;
`paper-kbs/experiments/kbcommon.py`;
`paper-kbs/experiments/results/exp1_retrieval.json`;
`paper-kbs/experiments/results/exp5_judge_filter.json`;
`paper-kbs/tex/journal_20p/_appendix-archived/tab_appendix_ranks.tex`

---

## Part C. Limitations of this evidence

**One deployment, one machine.** Every campaign in this document was run against a single
deployed instance on the authors' machine, with the tool layer, the parsers, the graph
store and the vector store all local. Nothing here establishes behaviour under a different
hardware profile, a different index size, a shared deployment, or multi-tenant load. The
concurrency numbers in A.3 in particular are properties of one host: the retrieval ceiling
of about 5.3 requests/s per instance is a measurement of that instance.

**Single-shot and n=2 campaigns.** Several campaigns are single-shot or smoke-scale and
support no variance claim. The isolated-environment probe (A.10) is one document and five
retrieval probes. The two-lane test (A.14) is four questions, and its own retest is n=1.
The abstention runs (B.7) are two questions per lane. The gate ablation (B.13) is ten
questions across three arms but only eight gold-answerable ones, and it was run once, so it
carries no variance estimate either; the retrieval-mode ablation recorded at n=2
(`exp12_partition_ablation_n2.json`) is retained only as a superseded record and
**supports no claim at all**. Where a campaign ran multiple rounds (A.2, A.13) the rounds
agree, but agreement across two or three rounds on one machine is not a reliability
result.

**Shared domain family between corpora.** The second corpus of 79 arXiv papers
(Section B.5) shares the first corpus's domain family and was ingested through the same
pipeline into the same five libraries. It is not an independent replication: a shared
failure mode in the parser, the chunker or the router would appear in both corpora.

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
campaign (A.4) cannot attribute the 91-versus-79 gap because no artifact records per-paper
parse status or error text, so 21 of 100 submitted papers are simply unaccounted for and
the nine-paper difference between submission and the recorded list is unexplained. The
five-track matrix (B.12) has no IR metrics at all: P@5, R@10, nDCG@10 and MRR are marked
NOT measured in its own report. The skill-catalogue count is inconsistent across artifacts
19 against 20, tools 94 against 95, and this document reports both rather than choosing.
The 322-document reorganisation campaign's three-source check is a 33-document sample,
not a full pass.

**Features with no test evidence at all.** The following capabilities have **no** test
evidence in this project, and this document reports none:

- **Library merge and split.** Sub-library splitting and hierarchy creation were analysed
  but deliberately not executed (A.6). No merge or split has ever been run against a
  corpus, and no correctness property of either operation is established.
- **Parent-KB hierarchy creation.** The hierarchical parent library exists as a structure
  and is used by the hierarchical search mode, but no campaign tests hierarchy creation,
  re-parenting, or nested retrieval correctness as an operation.
- **Experience decay and meditation.** The decay cycle, the meditation induction, and the
  `apply_decay` path were never exercised end to end. The sixteen-skill campaign (A.8)
  created experiences and read the dashboard; it did not run review, apply, review-driven
  decay, or meditation. The 50-paper and 322-document campaigns mention automatic
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
library partitioning bought nothing measurable on the
retrieval path although a routing mistake was fatal, and neither NLI replay improved on
the platform gate. Those results are reported here at the scale at which they were
measured.

---

## Part D. Manuscript appendix tables (S1-S5)

These five tables are cited from the manuscript's appendix
(`paper-kbs/tex/journal_20p/n_back.tex`) as Tables S1-S5. They were part of the
manuscript appendix until the 2026-10-16 revision moved them here; their LaTeX
sources are archived at
`paper-kbs/tex/journal_20p/_appendix-archived/n_appendix_tables.tex` (S1, S2, S3,
S5) and `paper-kbs/tex/journal_20p/_appendix-archived/tab_appendix_ranks.tex`
(S4). Every value is copied from those sources.

### Table S1. Stores and their principal contents

Field names are the ones used by the implementation and by the audit tools
(three-source consistency checks of the manuscript's Section 8.3).

| Store | Contents |
|---|---|
| Tree registry (`.tree-fs.json`) | version, root identifier and name, timestamps, node counter and aggregate statistics; per node: identifier, name, type, parent, path, children, metadata map, timestamps. Authoritative structure of the collection. |
| Library metadata (`.knowledge-base.yml`) | library identifier, name, description, timestamps, per-library configuration; per document: path, name, description, tags, content hash, file size, vector-index metadata. The retrieval index read by catalog search. |
| Document files | Markdown body per document or per split part, plus an image directory for figures extracted during parsing. |
| Vector store | one collection per library (cosine space, 1024-dimensional embeddings, HNSW index), holding segment embeddings of 500 characters with 50-character overlap. |
| Graph store | nodes for documents, libraries, tags, folders and entities; edges for membership, tagging, relatedness, identity and containment. |
| Task and session databases | pollable task records for parsing, indexing, graph builds and distillation; chat sessions; distillation signals. |

### Table S2. Cross-lingual ingestion

The manuscript cites the cross-lingual table as **Table S2**; it is the table in
Section A.7 above (400 Wikipedia pages per language, first round; the second
round reproduced these values bit-for-bit, so one column is shown).

### Table S3. Gold-annotated questions over the five production knowledge bases

"Gold" lists unique filename fragments of the ground-truth documents. All
sixteen serve the tool-layer experiment (manuscript Section 8.5); Q2, Q4, Q6 and
Q7 also served the archived lane grid of Section 8.6.

| # | Question (abridged, translated) | Gold document(s) | Design intent |
|---|---|---|---|
| Q1 | EVA encapsulation film lamination: how to set the temperature, pressure and time window; how to control cure degree | EVA process essentials; EVA hydro-thermal aging mechanism | multi-gold |
| Q2 | EL inspection shows edge delamination: root cause and corrective actions | EL-2025-0317 delamination RCA report | incident to RCA |
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

Best gold rank for the seven tool-layer pipelines (logged runs) and the two
derived configurations (offline replay of the same logged QDCVR-Hybrid pools).
Fusion = fusion-only (no judge); Hybrid = the shipped QDCVR-Hybrid judged
ordering; Filter = judge-as-filter. `--` = gold absent from the top-5 window.
Generated by `paper-kbs/experiments/derive_appendix.py`; question texts in
Table S3.

| Q | BM25 | Dense | RRF | Graph | 2-stage | Fusion | Hybrid | Filter | RRF-fuse |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 1 | 1 | 1 | 1 | 4 | 1 | 1 |
| 2 | 1 | 1 | 1 | -- | 1 | 1 | -- | 1 | 1 |
| 3 | 1 | 1 | 1 | -- | 1 | 1 | 1 | 1 | 1 |
| 4 | 1 | 1 | 1 | -- | 1 | 1 | -- | 1 | 1 |
| 5 | 1 | 1 | 1 | 1 | 1 | 1 | -- | 1 | 2 |
| 6 | 1 | 1 | 1 | 1 | 1 | 1 | -- | 1 | -- |
| 7 | 3 | 5 | 3 | -- | 3 | 5 | 3 | 5 | 3 |
| 8 | 1 | 1 | 1 | 1 | 1 | 1 | -- | 1 | 2 |
| 9 | 1 | 1 | 1 | 1 | 1 | 1 | -- | 1 | 3 |
| 10 | 1 | 1 | 1 | 1 | 1 | 1 | 3 | 1 | 1 |
| 11 | 1 | 2 | 1 | 1 | 1 | 2 | -- | 2 | 5 |
| 12 | 1 | 1 | 1 | 1 | 1 | 1 | -- | 1 | 3 |
| 13 | 1 | 1 | 1 | -- | 1 | 1 | 2 | 1 | 1 |
| 14 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 15 | 1 | 1 | 1 | -- | 1 | 1 | 5 | 1 | 2 |
| 16 | 1 | -- | 2 | -- | 2 | -- | -- | -- | -- |

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

### Freeze manifest for the manuscript's evaluation

From the 2026-10-16 revision, the corrected E5 annotations, the pre-correction
question set and the deterministic grader are pinned together with the
manuscript's evaluation text in
`paper-kbs/tex/journal_20p/.frozen-experiment-sha256.txt`, so the two-grade
disclosure of the manuscript's Section 8.7 cannot drift after review. Verify
with `sha256sum -c paper-kbs/tex/journal_20p/.frozen-experiment-sha256.txt`
from the repository root.
