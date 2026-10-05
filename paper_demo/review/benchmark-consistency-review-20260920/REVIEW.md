# Review — QDCVR CIKM 2026 Demo Submission (consistency-audited round)

- **Reviewer role**: independent reviewer pass (Agent-executed), 2026-09-20
- **Manuscript**: `paper_demo/tex/main.pdf` (5 pages: body pp.1–4 + GenAI-disclosure tail & references p.5), figures `figures/submission-20260919/fig{1,2,3}*.pdf`
- **Audit basis**: fresh full PIPELINE run committed at `7bb45ad` (2026-09-19 evening round): 50/50 parsed, 50/50 routed, 13,970/13,970 RAG chunks verified, bench10 9/10, three-track 10-Q English QA, all artifacts in `benchmark-suite/results/`
- **Method**: every checkable claim in abstract/sec2/sec3/sec4 and every number rendered in the three figures was cross-checked against the fresh run's saved artifacts (`skill_track_evidence.json`, `skill_track_answers.json`, `track_bc.json`, `bench10_qa.json`, `repro_coverage.json`, build assertions in `figures/submission-20260919/build_figures.py`).

---

## 1. Consistency audit — paper ↔ fresh benchmark ↔ figures

**Verdict: 15 of 17 checkable items match exactly; 1 real drift; 1 unit-terminology inaccuracy.**

| # | Paper / figure claim | Fresh-run artifact value | Verdict |
|---|---|---|---|
| 1 | 50 papers, five bases, 165 stored docs+parts (abstract, sec3, sec4) | 50 / 5 / 165 (`ingest_report`, `tags_report`) | ✅ |
| 2 | Regression passes 9/10; BQ06 retrieves its paper but lacks the keyword (abstract, sec4) | 9/10; BQ06 `doc_hit=True, kw=[]` | ✅ exact |
| 3 | C explicitly abstains in two of ten saved answers (sec4) | abstains at BQ01 and BQ04 | ✅ exact |
| 4 | BQ02 demo trace: first hit = part 2 of 3, similarity ≈ 0.71, gate 8/8 direct (sec3) | top-1 = part 2/3 §6.4, score 0.709, gate 8, fast-exit | ✅ exact |
| 5 | fig3 BQ01 track A evidence: parts 1/2 §3.2.3 + 2/2 §7 | identical parts/sections in `skill_track_evidence` | ✅ exact |
| 6 | **fig3 BQ01 track A: "Gate: 8/8 · fast exit"** | **current run gate = 7** (same evidence, agent-rubric run variance; earlier round = 8) | ⚠️ **DRIFT** |
| 7 | fig3 BQ01 track C: abstains; 2 chunks · 2,854 characters; chunk/source metadata not logged | `evidence_chunks=2, evidence_chars=2854, evidence_docs=[]` | ✅ exact (deterministic) |
| 8 | fig3 BQ01 track B: self-reported filename; softmax(QKᵀ/√dₖ)V | fresh B answer cites the formula and self-reports the file | ✅ |
| 9 | fig3 P2 probe: BERT near miss, Recorded 1/8, census 5 bases · 165 entries · 153 names, NOT_FOUND | scripted-probe artifacts unchanged (not re-run this round; framed as scripted in text) | ✅ |
| 10 | C evidence budget 4,000 characters (sec4) | `BUDGET=4000` (asserted at figure build) | ✅ |
| 11 | Dense pack yields 2 excerpts (fig1) | all 10 questions pack exactly 2 chunks (~2.83k chars) | ✅ behavior match |
| 12 | A records retrieval+read times only; end-to-end latency unavailable (sec4) | fresh A: 1.62 s retrieval + 0.83 s reads per Q; no authoring time | ✅ |
| 13 | Gate policy ≥6 direct / =5 P1 backstop / ≤4 discard (sec2, fig1, fig2) | fresh gates 7–8, all fast-exit; policy followed | ✅ |
| 14 | 41 `kb_*` tools within a 94-tool inventory (sec2) | fresh `tools/list`: 94 tools, 41 `kb_*` | ✅ exact |
| 15 | Split ceiling 30,000 characters (sec2) | `split_large_doc` maxChars=30000 | ✅ |
| 16 | **fig1: "≈800-token windows"** for the dense reproduction | chunker is **800/400 characters** (`chunk_fixed` defaults [800,400]); the 4,000 budget is also character-based | ⚠️ **UNIT ERROR** |
| 17 | "mutable file-tree metadata is not an append-only per-query audit log" (sec2) | true of current storage design | ✅ honest |

Additional cross-check: `build_figures.py` runs hard source assertions before rendering (BQ01 gate == 8, P2 == '1/8' + NOT_FOUND, C == (2, 2854, []), chunker defaults [800,400], BUDGET == 4000, evidence parts contain §3.2.3 / §7). Against the **current** results tree, **the rebuild would fail at the BQ01==8 assertion** — the committed figure still renders the archived round.

---

## 2. Overall assessment

**Recommendation: Accept with minor revisions (demo-track score 4.5 / 5** on the strong artifact-claim discipline and verified reproducibility; the two flagged items are cheap to fix**).**

This is an unusually honest demo paper. Nearly every sentence in the evidence section is scoped to what a saved trace can support, the limitations section pre-empts the obvious attacks (gate ≠ correctness, fixed rewrites preclude retrieval comparison, self-reported file reads, C metadata loss, uncontrolled cache/parametric knowledge), and the figures carry "not an autonomous benchmark" / "agent judgments, not accuracy" footers. The fresh full-pipeline run reproduces every deterministic quantity bit-for-bit (chunk counts 2366/1385/10219; C pack = 2 chunks / 2,854 chars; bench10 9/10 with the same BQ06 signature for the third consecutive run) and every stochastic quantity within stated variance (0.709 vs "≈0.71"; gate scores 7–8).

### Strengths
1. **Claim–evidence discipline is exemplary for a demo track.** The one-claimed-number-per-trace style (BQ02: part 2/3, ≈0.71, 8/8) is fully verified by the fresh run.
2. **Reproducibility is real, not rhetorical.** Deterministic layers (parsing, routing, chunking, pack) reproduce exactly; stochastic layers (LLM latency, gate scores) are labeled as such, and three full runs now exist for comparison.
3. **Figure build pipeline with source assertions** (`build_figures.py`) — figures cannot silently drift from data without breaking the build; automated font/bounds/overlap checks; per-figure desc + footer qualifiers.
4. **Failure reporting is a first-class demo object** (P2 scripted probe: near-miss BERT at 1/8 → NOT_FOUND with census scope), which distinguishes this from generic RAG demos.
5. Compliance hygiene: GenAI disclosure present; artifacts and video linked; page composition currently body pp.1–4 + refs on p.5.

### Weaknesses and required changes

- **[R1 — Required] Stabilize figure↔trace coupling (the BQ01 8/8 vs 7/8 drift).**
  fig3 renders "Gate: 8/8 · fast exit" from an archived run, while the current committed run judges the same evidence at 7/8, and `build_figures.py:242` asserts `gate == 8` against a **mutable** results file — a rebuild today breaks. Because gate scores are agent-authored rubric judgments, any future run can invalidate the figure again. Required fix (choose one, (a) preferred):
  (a) snapshot the referenced traces (e.g., `benchmark-suite/results/snapshots/20260919a/…`), point `build_figures.py` at the snapshot, and add a trace id to the fig3 footer + caption ("recorded trace: run 2026-09-19a");
  (b) soften the label to the policy outcome ("Gate ≥ 6 · fast exit (recorded 7–8 across runs)") — but (a) is cleaner and keeps the number.
  Add one sentence to sec4 acknowledging run-to-run gate variance (BQ01 8 vs 7 on identical evidence; BQ06 5+fallback vs 7 fast-exit across runs).

- **[R2 — Required] fig1 unit error: "≈800-token windows" → "≈800-character windows".**
  The reproduction chunker is 800/400 **characters** (`chunk_fixed` defaults [800, 400]); the evidence budget in the same figure is already "4,000-character". Update the label and the corresponding assert (`'800-char' not in source` was presumably added to force vaguer wording — it should assert the correct unit instead, not ban it).

- **[R3 — Recommended] C-pack under-fill.**
  All ten questions pack exactly 2 excerpts (~2.83k of the 4k budget). The paper presents "pack 2 excerpts" as the reproduction's behavior (correct), but a one-line cause (doc-level dedup in `methods.dense` / pack stop rule) would preempt the reviewer question "why doesn't dense fill its window?", and it is the main reason C abstains twice. Worth one sentence in sec4; optionally fix the pack to fill the budget in the next artifact round.

- **[R4 — Recommended] Compliance check on p.5.**
  Body text (GenAI disclosure tail) spills onto page 5 together with references. If the CFP counts the disclosure inside the 4-page body, ~0.2 page must be trimmed (the disclosure can likely be tightened by 2–3 lines); if disclosures are excluded, current composition is fine. Verify against the CFP text.

- **[R5 — Minor] "Author Name" placeholder remains in running headers** — must be filled before submission (also page-1 author block).

- **[R6 — Minor] sec4 "retains 153 document names" is cryptic** — add a parenthetical explaining the census counts 165 parts but 153 unique names (deterministic part splitting / naming), otherwise reviewers may read it as an inconsistency.

- **[R7 — Minor] fig1 left panel and sec4 describe the same budget in different granularities** ("pack 2 excerpts" vs "4,000-character budget"); consider "(2 excerpts, ≤4,000 characters)" in fig1 for self-containment.

### Section-level remarks
- **Abstract**: numbers verifiable; "nine cases" matches. Fine.
- **sec2**: the s = s_topic + s_scenario + s_evidence rubric box is clear; the disclaimer "prompted relevance assessment, not guaranteed correctness" is exactly right. The "not an append-only audit log" honesty is unusual and good.
- **sec3**: demo scenarios 2–3 map 1:1 onto fig3 and the saved traces; scenario 1 (organize) honestly offers a prepared example if live parsing is slow.
- **sec4**: the strongest section of the paper. The audit found nothing overstated.
- **Figures**: all three are legible at print size, ≥14px min font asserted at build, no overlaps; color semantics (neutral boxes, red reserved for not-found/warning) are consistent; fig2's dashed "Indexed evidence → recall" boundary correctly signals that ordinary HTTP search bypasses the gate.

---

## 3. Actionable fix list (ordered)

1. Snapshot referenced traces; repoint `build_figures.py` asserts; add trace id to fig3 footer/caption; extend sec4 with one gate-variance sentence. *(R1)*
2. fig1 "≈800-token" → "≈800-character"; fix the assert. *(R2)*
3. One sentence on C-pack under-fill cause in sec4. *(R3)*
4. Confirm CFP treatment of the GenAI disclosure; trim if counted. *(R4)*
5. Fill author placeholders. *(R5)*
6. Parenthetical for 165/153. *(R6)*
7. fig1 budget self-containment. *(R7)*

*Reviewer's conflict note: this review was executed by the same agent family that operates the platform under review; the consistency audit is artifact-based and reproducible (commands and artifact hashes in `benchmark-suite/results/`), but scores should be weighed accordingly.*
