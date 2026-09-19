# Evidence audit for the demonstration revision

[OBJECTIVE] Independently reconcile the current local benchmark artifacts and scripts with the original evaluation claims, then bound Section 4 to operational demonstration evidence. Audit date: 2026-09-19. Only this audit and paper_demo/tex/sec4_eval.tex are owned by this task. No experiment, LLM call, package installation, or source-artifact modification was performed. Local JSON inspection and deterministic arithmetic/string matching used Node; no Python was executed (python_repl is unavailable). The audit is saved before the section edit. Main confirmed backup completion, and before/tex exists.

[DATA] Scope: current benchmark-suite/results files, ten questions, ten A answer records, ten B/C record pairs, and three probe records. The directory name is not a complete run manifest. BENCHMARK-30000chunk-20260918.md is a narrative with conflicting stages and stale aggregates; current skill_threeway_replication.md is generated 2026-09-19 09:20 UTC. Do not silently mix these with archive-20260917-10000chunk. No claim below means every factual answer has been independently validated against its full source paper.

## 1. Corpus and graph

[FINDING] The corpus inventory is supported at the aggregate level. [STAT:n] 50 papers; 5 category bases; 165 stored documents/parts; 3,798,446 parsed characters.
- results/ingest_survey.json: n=50, papers.length=50, sum(papers[].chars)=3,798,446.
- results/ingest_report.json: total=50, verified=50; catalog counts 18/15/10/5/2, graph values true for five bases. verified is an indexing probe result, not independent parse-fidelity validation.
- results/graph_stats.json: stats.doc_count=165, stats.kb_count=5. results/probe_evidence_raw.json:ooc_probes[0].phase2_librarian.shelf[].n_docs = 72/43/32/6/12, also totaling 165.
- The report calls this the 30,000-character ingestion configuration; there is no per-answer immutable run/config snapshot. Its 9 whole + 156 parts decomposition was not independently counted from the actual stored-document inventory in this audit; do not strengthen it to a new verified finding.

[FINDING] 860 is not the total edge count. [STAT:n] graph_stats.json: stats.edge_count=1671; stats.relation_by_reason.shared_tag=730 and vector_similar=130, summing to 860 typed relations. Preserve that qualifier. stats.tag_count=165 is a graph statistic, not sufficient alone to establish successful propagation to each of 165 parts; ingest_report.routed contains tag_ok=false records, so a later tagging-stage claim needs its own stage output.

## 2. Retrieval and regression versus answer correctness

[FINDING] A's saved first hit identifies the question's designated source in every case. [STAT:n] 10/10, computed by matching data/papers/qa_questions.json:questions[qid].arxiv_id against results/skill_track_evidence.json:[qid].hits[0].doc_path. This is paper-identity matching, not evidence-span entailment or answer accuracy.
- scripts/75_skill_track_phase1.py uses manually embedded REWRITES, five per-base searches, document-path deduplication, then candidate reads. Several rewrites contain expected-answer material (BQ03: 67.6; BQ06: precipitation efficiency; BQ07: 8B). Hence the source-match rate is not blind/unassisted retrieval efficacy.

[FINDING] The separate regression passes nine cases. [STAT:n] results/bench10_qa.json: total=10, passed=9; all rows[].doc_hit=true; BQ06 has kw_hit=[] and pass=false.
- scripts/72_bench10_verify.py: pass means designated paper among top three distinct document paths AND at least one literal gold keyword in concatenated retrieved content. It tests snippets, not final answers. It uses raw questions, unlike A's fixed rewritten queries.
- The absence of BQ06's keyword is verified; the narrative's precise chunk-boundary causal explanation is not established by this scorecard, which does not retain those snippets. Do not report that causal explanation as a measured fact.
- Original A/B 10/10 on-target and C 8/10 on-target claims are not independent accuracy judgments. A's BQ03 explicitly withholds the requested MedQA numeric score. C's eight non-abstentions are not eight demonstrated correct answers (BQ06 emphasizes the thermodynamic contribution rather than the literal gold factor). Remove the on-target scorecard.

## 3. Keyword scorecard is stale relative to current answer text

[FINDING] The saved scorecard does not reproduce against the current input answers. [STAT:n] track_a_kw_hit.json reports n=10, any_hit=10, all_hit=9, but current literal matching gives 8/10 any keyword and 5/10 all keywords across final_answer; all keywords in the Answer section gives 4/10, not 7/10.
- Exact sources: data/papers/qa_questions.json:questions[].gold_keywords; skill_track_answers.json:answers[].final_answer; scripts/80_track_a_kw_hit.py recursively collects every string except qid, lowercases and uses substring matching. Current gate strings add none of the missing gold terms, so matching the script's full-string scope yields the same 8/10 and 5/10.
- Current Answer-section all-keyword passes: BQ04, BQ05, BQ06, BQ07. Whole-answer all-keyword passes add BQ08, whose Sources title supplies cathode.
- Whole-answer misses: BQ01 recurrence; BQ02 error correction; BQ03 67.6; BQ09 dynamic and multilayer perceptron; BQ10 immune evasion and chemotherapy. BQ09/BQ10 have zero English gold substrings, despite Chinese related wording.
- Original 7/10 Answer-only, 9/10 with declarations, and 10/10 any-keyword counts are unsupported by current answers. Even the current corrected counts measure English literal occurrence, not semantic completeness in bilingual answers. Omit all keyword-answer counts from the paper rather than replace one misleading accuracy proxy with another.

## 4. Gates, two fallback traces, and scenario mismatches

[FINDING] Two records contain additional Phase-2 searches/reads, but only one current answer gate records a failure-triggered rescue. [STAT:n] skill_track_evidence.json phase2 exists for BQ06 and BQ10 (2/10); scripts/76_skill_track_phase2.py hard-codes those two QIDs instead of dynamically dispatching from stored gate scores.
- Current skill_track_answers.json answers[].gate.score sequence BQ01--BQ10: 8,8,7,8,7,5,8,7,8,7 (five 8s, four 7s, one 5). BQ06 gate.decision says 5 -> resolved 8/8; BQ10 says score=7, fast_exit (>=6), while its final_answer acknowledges supplementary Phase 2. Thus report two additional-read traces, NOT two rescues after initial 5/8s.
- BENCHMARK-30000chunk-20260918.md reports BQ01=7, BQ02=7, BQ06=5->7, BQ08=6, BQ09=7, BQ10=5->6 and final distribution 8x2/7x6/6x2. These conflict with current answer JSON. The original section's final 6--8/8 range is not a coherent extraction of current structured scores.
- NISQ/BQ02: evidence hits[0].vector_score=0.7090588808059692 and path names part 2 of 3. Those agree with Scenario 2's similarity/part, but current answer gate is 8/8, NOT the scenario/report's 7/8. BQ01 is also 8/8 in current JSON versus 7/8 in the narrative. Treat 8/8 as recorded self-assessment, never independent validation.
- BQ06 final_answer claims offset 0--12000 scanning; script 76 requests max_chars=6000 without offset and saves only head[:1500]. Additional unrecorded interaction cannot be ruled out, but the claimed exact read sequence is not demonstrated by this script.

## 5. Timing reconciliation and comparability

[FINDING] Original timing means do not match current rows. [STAT:n] ten records per track; deterministic means of existing rounded fields, not new timed measurements.
- skill_track_evidence.json: mean(timings.phase1_vector_search)=1.718 s; mean(phase1_doc_reads)=0.787 s; sum=2.505 s. Original 1.57+0.81=2.38 s is stale.
- Phase-2 times are additional: BQ06 targeted_search=0.96, continuation_reads=0.53 s; BQ10 0.34 and 0.53 s. A's answer authoring, gate judgments, and query construction are not timed end to end. Even a phase-1 sum is not whole-protocol latency.
- track_bc.json: mean(track_b_bare_agent.latency)=29.44 s, range 17.2--37.6; mean(track_c_dense_rag.latency_total)=18.99 s, range 0.8--67.3; mean(C.latency_retrieval)=0.812 s. Original B 78.8 (35.5--165.3), C 12.2 (5.8--28.6), retrieval 0.59 are not current.
- scripts/77_tracks_bc.py times B process creation/prompt/close, whereas C includes retrieval/pack/answer wrapper with different setup boundaries. algorithms/omp_client.py: OmpOneshot.__call__ permits cache returns; cache key uses stage+prompt, NOT model/config. C BQ05 latency_answer=0.0, total=0.8, retrieval=0.77; this is compatible with cache use, but cache-hit status was not logged. Do not certify all C timings as fresh generation calls.
- Archive comparison also does not recover old paper means: archived A retrieval/read means 1.935/0.801, B/C 55.46/23.19 s. Do not attribute stale values to that archive without evidence.
- Decision: omit latency numbers from the compact section and explicitly preserve the unavailable A end-to-end / non-comparability limitation.

## 6. B/C configuration and provenance

[FINDING] C abstains explicitly on two saved answers and lacks usable source-document metadata in all saved rows. [STAT:n] BQ01 and BQ04 abstain; 10/10 track_c_dense_rag.evidence_docs=[]; 10/10 evidence_chunks=2. No independent eight-answer correctness claim follows.
- algorithms/corpus.py: chunk_fixed(max_tokens=800, overlap_tokens=400), CHARS_PER_TOKEN=4 => approximately 3200-character windows, 1600-character overlap. index_kb.py:items_fixed calls these defaults; user_scenario.py builds Corpus-Chunks800 with items_fixed. Original '800-character fixed chunks' is incorrect for the current implementation; the name denotes approximate token windows, not characters.
- methods.py:dense requests top_k=10 (no reranker), truncates each text to 1400 characters, returns chunks with src/text/meta/score. pack uses BUDGET=4000, preserving whole packed chunks. Two were packed per saved row; it is not a top-2 retrieval configuration.
- scripts/77_tracks_bc.py:run_dense incorrectly looks for chunk.doc_path when constructing evidence_docs, whereas methods.dense emits meta. It does not serialize evidence text, ordered chunk paths, or scores. Raw model evidence_used values often identify only a field (e.g., artificial-intelligence), not a document. This is a logging/adapter limitation of this reproduction, NOT an inherent dense-RAG inability to expose provenance.
- B files_used is model-supplied JSON. omp_calls=1 for all ten records counts prompt submissions, not file-tool actions. omp_client.py drains text events without retaining a full file-tool event trace. Therefore neither actual read order nor gold-first retrieval is verified from B's file list; one prompt does not prove the absence of tool use either.
- scripts/77_tracks_bc.py invokes external omp; algorithms/omp_client.py has no explicit model/provider/temperature/seed selection and does not save a resolved configuration alongside each answer. algorithms/README.md describes local omp configuration (reported provider=ustc, model=deepseek-flash); REPRODUCTION-NOTES.md repeats that identity for an ITRG configuration with default temperature. This is documentation, NOT a per-run attestation for current A/B/C outputs. A's executing agent/model is not identified in its answer artifact. Do not claim model matching or a particular model generated these answers without archived resolved configuration.

## 7. Probe evidence and scope of inference

[FINDING] Three saved probe reports explicitly return NOT_FOUND. [STAT:n] honest_failure_probe.json:probes[].verdict=NOT_FOUND for P1/P2/P3; gate.score=1/8,1/8,0/8. Reports state search scope and near misses; P2 is the fabricated-paper scenario.
- probe_evidence_raw.json contains retrieval/read excerpts and shelf scans. scripts/80_honest_probe_judge.py serializes executing-agent judgments through predefined score/report logic; this is not an independent blinded judging experiment.
[LIMITATION] These are selected operational traces (n=10 plus 3 probes), not a representative test population. No repetitions, randomization, independent raters, model-matched controls, or causal ablations establish general efficacy, superiority, or state of the art. Parametric knowledge, answer-bearing rewrites, evidence-window differences, cache state, and incomplete provenance are uncontrolled. No inferential confidence interval is presented because there is no defensible random-sampling basis here.

## 8. Handoff: other sections/captions (not edited)

- sec0_abstract.tex: reconcile/remove 10/10 on-target, gates 6--8/8, two rescues, and 1.6 s; retain 9/10 only as the scripted snippet regression, 10/10 only as designated-paper first-hit matching.
- sec1_intro.tex Evidence contribution: remove the unsupported 10/10 on-target efficacy framing.
- sec2_system.tex and architecture caption: 860 typed relations is consistent; 860 total edges is not. tag_count=165 alone does not verify tagging of each part. 'all parse-verified' should not conflate indexing probes with parse fidelity.
- sec3_demo.tex Scenario 2 and any NISQ screenshot/caption: current BQ02 gate=8/8, not 7/8; part 2/3 and 0.71 remain supported. Scenario 3(a)'s tumor 5->6 two-rescue story conflicts with current BQ10=7 fast-exit; use a clearly labeled illustrative scenario or reconcile it to a specific frozen trace. BQ06 is the current failed-gate fallback example, with textual resolved score=8/8.
- Three-way figure/caption: verify text against current records rather than the September 18 narrative; avoid calling all eight non-abstentions correct, avoid 800-character chunking and top-2 retrieval, and label C's lost metadata as a reproduction limitation.
- Keep original section/table labels for cross-reference compatibility. Main owns compilation/page-budget/figure layout checks. This task does not inspect CFP or revise submission-policy text.

## Snapshot fingerprints

These hashes bind this audit to the files actually inspected; differing later files require reconciliation, not reuse of old counts.

- benchmark-suite/results/bench10_qa.json — SHA-256 b0e1cc62b5431e67850c4a2efb38c06269c936c0b69a7e8c897eb9e08c147efc
- benchmark-suite/results/skill_track_evidence.json — SHA-256 729d1537a7284c9389cda1f2657586c20257cf835332e998cd6bfb20016694e4
- benchmark-suite/results/skill_track_answers.json — SHA-256 c13bae49d11183eabe264cf0e782b645b051f7f3b40c2bb73974e8e8d1b1564b
- benchmark-suite/results/track_a_kw_hit.json — SHA-256 21b76c96b2182d9f63d38afd6b19a9bbf2189e3ce68e44b82d771d05c38e4a01
- benchmark-suite/results/track_bc.json — SHA-256 a2806db32ea24e35b83b56cbd8f9a4d710ca52b71c7e49ab243f0092cad95823
- benchmark-suite/results/honest_failure_probe.json — SHA-256 c0090f75d6552f78273e7c98c02e60e2bb646bca72ec6780b4362f5f12f2caee
- benchmark-suite/results/graph_stats.json — SHA-256 966a931e6078f3f99eedeaca6682e4bd3859aef697e9c3d325ecd3a5f198c778
- benchmark-suite/results/ingest_survey.json — SHA-256 2fb860cd1cd78ed3e1942312802c8b25306a25650eb665dc5a20ac46ac5cb6ed
- benchmark-suite/results/ingest_report.json — SHA-256 37d095bcbc7823efd917742b29c453eca25deaf9b95f6045778f9c376f256663
- benchmark-suite/data/papers/qa_questions.json — SHA-256 cbe1c2ae2c86fc9484a59e32ce8b582789de5a42e7a50edbd00517aabac70805

## Authoring verification

Section saved only after this audit and main backup confirmation. Revised title: Demonstration Evidence and Limitations. Five data rows; approximately 383 text words including table/caption (simple TeX-stripped token count). Existing sec:eval and tab:threeway labels retained. Static brace check and git diff --check passed; source fingerprints remained unchanged at verification. No LaTeX build was run, to avoid producing files outside the two-file ownership boundary; main should compile and check page fit.
