# Editorial Decision Package — CIKM Full Research Submission

**Manuscript:** QDCVR — query-driven, content-adjudicated retrieval over heterogeneous, agent-operated knowledge bases (deployed MCP platform)
**Review round:** 1
**Panel:** 5 role-separated seats — Journal-Fit Reviewer (EIC), Peer Reviewer 1 (Methodology & Statistics), Peer Reviewer 2 (IR & KM), Peer Reviewer 3 (Cross-disciplinary & Impact), Devil's Advocate (fixed adversarial seat)

**Seat recommendations:** Major Revision ×4 (EIC, R2, R3, DA) · Reject ×1 (R1)
**Finding inventory transported from the five reports:** 66 findings — 9 CRITICAL (R1 ×5, R3 ×2, DA ×2), 34 MAJOR (EIC ×7, R1 ×7, R2 ×6, R3 ×7, DA ×7), 23 MINOR (EIC ×6, R1 ×4, R2 ×2, R3 ×8, DA ×3).

**Synthesis mode:** standard (no sprint contract in force) → the qualitative criteria and recommendation matrix of `references/editorial_decision_standards.md` govern; no dimension scoring matrix exists, so no `dimension_verdicts` line is emitted. No fabricated dimension arithmetic appears below.

## Panel Provenance and Calibration Boundary

- **Typed provenance artifact:** `[PROVENANCE-ARTIFACT-MISSING]` — the five seat reports reached this synthesis as text with no `review-panel-provenance/1.0` carrier. Per the invalid/unknown rule, every axis is rendered `unknown` rather than reconstructed.
- **Axes:** role_separated `unknown` · fresh_context `unknown` · blind_to_peer_outputs `unknown` · model_family_distinct `unknown` · provider_distinct `unknown` · human_distinct `unknown`.
- **Binary independence claim:** not computed. Five distinct personas establish only that five role labels were used; role separation is **not** independence, and no same-family correlated error can be excluded or confirmed from the material supplied.
- **Correlated-error disclosure:** family-unknown. The seats' *agreement* is therefore evidence of convergent reading, not of independent error processes — corroboration counts below are reported on that basis.
- **calibration_status:** `NOT_CALIBRATED`.

---

# Part 1 — Consensus Findings

**Counting rule applied:** consensus is computed over the **4 non-DA seats** (EIC, R1, R2, R3). The denominator is always 4; a silent seat is *not* agreement. The DA's agreement is reported separately and never inflates a consensus label. Because the assigning editor asked for a ≥3-seat threshold across the whole panel, the total-seat column is given as well — rows that reach 3 total only because the DA corroborates a 2/4 finding are labelled honestly as such rather than promoted to CONSENSUS-3.

## 1.1 Consensus at or above the bar

| ID | Finding (deduplicated, with the seats' own anchors) | Non-DA seats | Canonical label | DA | Total seats | Severity |
|----|---------------------------------------------------|--------------|-----------------|----|-------------|----------|
| C1 | **The ablation and the main comparison are not the same experiment, and the ablation's scale is arithmetically impossible under the main table's relevance definition.** Table 4 reports P@5 0.117–0.200 / FPR 0.348; the "ablation on the held-out benchmark" reports P@5 0.723–0.875 / FPR 0.025 — a 4–7× gap and a **sign flip** on the central mechanism (removing adjudication *raises* FPR in the ablation; the adjudicating-but-unscoped configuration has the *worst* FPR in the main table). §8 concedes the two "cannot be read together"; the abstract and C2 nonetheless quote the ablation as positive evidence. | EIC-4, R1-M4, R2-07, R3-M1 | **[CONSENSUS-4]** | DA-1 corroborates and specifies the protocol (8 queries, stage-1 k=20, top-k=5) | **5/5** | CRITICAL (R1) / MAJOR (EIC, R2, R3, DA) |
| C2 | **Prose numbers contradict the generated tables and the frozen artefacts in at least six places.** Dense SciFact nDCG@10 0.830 vs table 0.834; BM25 MRR 0.838 vs 0.839; in-house "QDCVR raises Recall@5 (0.908 vs 0.892)" vs the table's 0.917 (the claim reverses sign); MRR 0.867/0.910 vs 0.8625/0.9306; SQuAD "answer@1 0.938 for every method" vs BM25 0.875; Table 8 "median 3.5" where the sampled median is 3.0 and 3.5 is the mean; latency 1.69/0.126 s vs 1.3364/0.0656 s; characters 3,639/4,292 vs 3,938.8/4,265.6. | EIC-10, R1-M12 (+M5), R2-08, R3-m1/m2 | **[CONSENSUS-4]** | DA-4, DA-9, DA-10, DA-11 corroborate | **5/5** | MAJOR (R1, DA) / MINOR (EIC, R2, R3) |
| C3 | **The submission is unfinished by its own admission and asks to be judged as complete.** 10–12 inline red `[TODO-n]` markers in the review copy, including on the opening motivating example, the headline ablation (TODO-9) and the experience module (TODO-5/6); the README's "8 pages / ≤9" contradicts the audit's 9 and the compiled 10. | EIC-13, R1-M16, R2-07, R3-m6 | **[CONSENSUS-4]** | DA cites TODO-9/TODO-12 as admissions | **5/5** | MAJOR (R2) / MINOR (EIC, R1, R3) |
| C4 | **The "every number is generated from frozen artefacts / cannot silently change" guarantee does not hold as stated, and nothing is linkable.** §7.8 claims digest verification, but Figure 5's coordinates are hand-written in `main.tex`, Table 8's median and the SciFact article count are string literals in `make_assets.py`, `load()` passes any file absent from the manifest, verification runs at generation time (a stale PDF passes), no prose number is tied to the snapshot, the snapshot contains **no query list, no qrels, no per-query scores** for the primary benchmark, no judge prompt and no E2E JSON, and there is **no anonymous artefact link**. | EIC-7, R1-M5, R3-m6 | **[CONSENSUS-3]** — R2 silent | DA-11 corroborates the sub-claim about §7.8's wording | **4/5** | CRITICAL (R1) / MAJOR (EIC) / MINOR (R3) |
| C5 | **XQuAD is announced in the setup and withheld, and its omission is justified by a ceiling claim the authors' own record contradicts.** §7.2 lists a 32-question XQuAD subset and §8 calls it "at or near ceiling", but no XQuAD result appears anywhere; the project's own audit records staged P@5 0.275 vs vector 0.831 (vector ~3× better) and flags the ceiling language as unsupported. | EIC-6, R1-M9, R3-m6 | **[CONSENSUS-3]** — R2 silent | DA-8 corroborates with the latency pair (1.42 s vs 0.085 s) | **4/5** | MAJOR (EIC, R1, DA) / MINOR (R3) |
| C6 | **The adjudicator is an unvalidated instrument.** Judge model, version, prompt and decoding are never stated; no human κ and no LLM-vs-human agreement exist; the accept ≥6 / supplement =5 / discard ≤4 cuts, τ = 0.35, the ≤3-base routing budget and the 30-day decay are asserted with no tuning protocol and no sensitivity analysis; there is no rubric-structure ablation (3-dimension 0–8 vs scalar LLM judge vs binary filter vs cross-encoder vs pointwise LLM re-ranker), so it is untested whether the named dimensions do any work. | R1-M10, R2-02, R3-M6 | **[CONSENSUS-3]** — EIC silent | DA-7 corroborates (the "− adjudication" row bundles four design choices and is not attributable to the rubric) | **4/5** | MAJOR ×4 |
| C7 | **Every multi-domain result is author-constructed; every public benchmark is single-domain; the abstract and C1 never disclose this.** The paper says so in §8 only. The authors' own docs already record a public route (HotpotQA supporting documents partitioned into 8–12 topic KBs); BRIGHT sits uncited in `refs.bib`. | EIC-12, R2-06, R3-C1 | **[CONSENSUS-3]** — R1 silent | DA-12 corroborates | **4/5** | CRITICAL (R3) / MAJOR (EIC, R2) / MINOR (DA) |
| C8 | **§7.2 describes a corpus that never existed: 13 KBs + 184 documents + 13,709 chunks mixes two mutually exclusive snapshots** (2026-07-29 = 13 KBs/154 docs/13,709 chunks; 2026-09-13 = 12 KBs/184 docs), which Table 2's own caption calls "not sound"; "11 domains" is claimed but eight are named; Figure 2 annotates 13,709 chunks against the evaluation snapshot. | EIC-5, R1-M8, R3-m6/m4 | **[CONSENSUS-3]** — R2 silent | — | **3/5** | MAJOR (EIC, R1) / MINOR (R3) |
| C9 | **The KM-distinctive component (C3, the 11-stage experience lifecycle) is a design document, and the KM-flavoured ablation effect is unexplained.** No baseline, no ablation of the five retrieval paths, an empty baseline slot printed in the PDF (TODO-6), and the second-largest ablation effect (−0.118 P@5) receives one clause and no mechanism while the module producing those entries is scored 3.5/10 by the same paper. "Experience archiving" and "cross-KB balancing" are ablated but never defined in §4 or Algorithm 1; the L5 graph layer is a Stage-2 fusion term with no ablation row. | EIC-2, R2-03 (+R2-07), R3-m6 | **[CONSENSUS-3]** — R1 silent | — | **3/5** | MAJOR (EIC, R2) / MINOR (R3) |
| C10 | **The five-layer "one logical transaction" guarantee is stated as a design fact, verified by the write path itself, and never failure-injected.** The 1.000 membership/completeness figures come from the same ingestion module that performs the write (not an independent oracle), cover 16 documents, and the implementation uses per-file atomic writes with best-effort, non-fatal graph/vector synchronisation; the audit records vector metadata missing after indexing until `kb_reindex(force=true)`. | EIC (summary + EIC-1), R1-M11, R3-M5 | **[CONSENSUS-3]** — R2 silent | — | **3/5** | MAJOR (R1, R3) |
| C11 | **The headline p-values are computed on Recall@5 — the metric where the proposed system trails — and are printed in a column headed only "p" with no metric, sign or n.** The generating artefact is titled "Paired t-test on Recall@5" with a "95% CI (Recall@5)" column, n_paired = 46, negative t/Cohen's d (vs Hybrid-RRF t = −3.49, d = −0.51), MoE 0.500 vs Hybrid-RRF 0.783; so the one comparison surviving Holm–Bonferroni is a **significant deficit**, while the abstract and C1 present p=0.001 as a routing win. The CI [0.43, 0.57] is identical across four different effect sizes. | R1-M1, R3-M1/m3 | corroborated (2/4) — EIC explicitly defers statistics to R1, R2 silent | DA-3 corroborates | **3/5** | CRITICAL (R1) / MAJOR (R3, DA) |
| C12 | **An entire language subgroup is inside Table 7's Overall row and absent from its per-language rows.** Archived `by_lang` has en (n=10), zh (n=6) and **ja (n=4)**; the generator emits only en/zh, so the omission is structural. Japanese is where the method is weakest (dense vs staged Hit@1 1.000 vs 0.750, MRR 1.000 vs 0.750, verify_pass_rate 0.0) — and the paper calls the corpus "bilingual". | R1-M8, R3-M2 | corroborated (2/4) — EIC, R2 silent | DA-8 corroborates | **3/5** | MAJOR (R1, R3, DA) |
| C13 | **The strongest measured result (KB-granularity routing) has neither prior-art positioning nor any baseline, oracle or size-matched control.** Claiming routing "is not the axis prior routing work optimises" while citing no distributed/federated-IR resource-selection work and no LLM/MoE query-routing work; the 0.62 accuracy over 13 bases has no always-search-all, BM25-over-catalogue, size-prior or oracle comparison, and no random-pool or candidate-matched control — so descriptor similarity and mere pool shrinkage (13,709 chunks → ~538) are confounded. | EIC-1, R2-01 (+R2-05, R2-06) | corroborated (2/4) — R1, R3 silent | DA-6 corroborates | **3/5** | MAJOR ×3 |
| C14 | **The headline FPR reduction may be substantially an abstention artefact, and no coverage figure is reported anywhere.** All 22 empty result lists in the archived per-query record belong to QDCVR-MoE, which returned nothing on ~19 of the 46 scored queries; FPR is defined over *returned* documents, so abstention scores 0 by construction. QDCVR-MoE: FPR 0.348, R@5 0.500, P@5 0.200 vs Hybrid-RRF FPR 0.543, R@5 0.783, P@5 0.191 — a coverage/precision trade presented as a discrimination win. | R1-M2, R3-C2 | corroborated (2/4) — EIC, R2 silent | DA-2/DA-3 corroborate the underlying fact | **3/5** | **CRITICAL ×2** |
| C15 | **The abstract's "neutral" understates a consistent loss, while the title and system name centre the mechanism the data does not support.** Dense wins SciFact Hit@3/R@5/nDCG@10, in-house Hit@1 and MRR; adjudication also carries an order-of-magnitude latency cost. §4.5's "this is the stage that distinguishes QDCVR" and the title's "Content-Adjudicated" promise X and deliver Y; "halves the false-positive rate" is a 45% cut. | EIC-8, R2-08 | corroborated (2/4) — R1 and R3 praise §7.5's candour but do not join this finding | DA-5 corroborates | **3/5** | MINOR (EIC, R2) / MAJOR (DA) |

## 1.2 Below the consensus bar but decision-bearing (corroborated, 2 seats — retained, not discarded)

| ID | Finding | Seats | Note |
|----|---------|-------|------|
| B1 | **Latency is unattributed.** Identical 1.58 s for BM25, two-stage and QDCVR on SciFact, and 1.53 s for all four methods on SQuAD, indicate a harness-dominated measurement; the 12× scoped/unscoped gap (117 ms vs 1,411 ms) has no stated mechanism, and adjudication cost is reported in characters rather than documents read. | R3-M3, DA-9 (+DA-5) | 2/5 seats. Blocking for the practical recommendation, not for the retrieval claim. |
| B2 | **C4 is not a research contribution.** A tool count (94) and a pass rate (73/73) are numbered as a contribution and lead the title, while RQ1–RQ6 depend on neither; coverage of the 94 tools by the 73 checks is never stated, the E2E JSON is unfrozen, and "the platform is cross-platform" is asserted with no OS/hardware matrix. | EIC-3, R1-M11 | 2/5 seats; EIC also supplies the page-reallocation remedy. |
| B3 | **Run discipline is not established.** One run per configuration while §7.2 asserts "repeated runs are bit-identical"; the project's own two-run comparison differs in 83 fields for the in-house retrieval module and 42 for SciFact/SQuAD; §7.5's prose reports the superseded run while Tables 6–7 report the re-run; the experience module produced 10, 8 and 0 entries with judge means 3.5, 4.375 and null. | R1-M6, DA-4 | 2/5 seats. R2 discloses the ±1.5 tolerance as a virtue; that credit stands while the determinism claim does not. |
| B4 | **Sample sizes cannot resolve the reported deltas.** n = 20/46/30/16 imply minimum detectable effects of ≈0.05–0.17 on P@5/R@5, so the ablation's MEDIUM/LOW rows and much of Table 4's P@5 ordering sit inside the noise band; "50 queries" is 46 scored queries throughout (4 unjudged). | R1-M7, R1-M13 | 1 seat (methodology owner), expertise-weighted; DA and R3 flag related scale problems. |
| B5 | **The agent-operated write surface has no trust or failure model, and the credibility model has unaddressed failure modes.** Nine of the 94 tools are destructive; Stage 4 loads raw candidate text into an LLM and Stage 0 rewrites the query, crossing the same trust boundary twice; Eq. 3 is manipulable by whoever supplies ratings, and `experience_review` is agent-callable. | R3-M4, R3-M7, R3-m8 | 1 seat. Accepted in **scope-reduced** form (see Disagreement D6). |

---

# Part 2 — Disagreements and Arbitration

**D1 — Disposition: Reject vs Major Revision.** *(recommendation split)*
- **R1 (Reject):** the measurement architecture does not support the claims; M1–M5 are correctness defects, not missing extras.
- **EIC, R2, R3, DA (Major Revision):** the contribution survives, the gaps are concrete and largely closable with infrastructure the authors already hold; DA states explicitly that this is why it stops short of Reject.
- **Type:** severity/existence disagreement on disposition.
- **Editor's resolution: Major Revision (last chance).** The decision matrix row `[Major | Major | Major | Reject] → Major Revision (last chance)` applies with the seats permuted.
- **Rationale:** R1's CRITICALs are upheld on substance — each is corroborated (M1 by C11, M2 by C14, M4 by C1, M5 by C4, M3 by the adversarial reconciliation) — but "reject" is the disposition for defects that revision cannot repair, and here the per-query record, the re-run harness and the generator already exist. **R1 is not overruled on substance, only on disposition, and only conditionally:** if the revision cannot produce the metric-correct tests, the coverage-aware FPR, a same-protocol ablation and the per-query artefact, Reject is the correct outcome at re-review. This paper is on its last round, not its first.

**D2 — What is actually wrong with the ablation.** *(action/severity conflict)*
- **EIC-4, R2-07:** a coherence and captioning failure — the two tables "cannot be read together"; remedy is to relabel and stop quoting incomparable numbers.
- **R1-M4:** relabelling is inadequate — a P@5 of 0.875 is unreachable under Table 4's qrels, so the relevance definition or denominator must differ, not merely the query set.
- **DA-1:** it is an 8-query ablation at stage-1 k=20, never disclosed as such.
- **Editor's resolution:** the deeper diagnosis governs. Caption-only repair is **rejected as insufficient**; the ablation must be re-run on the main protocol or the −0.152 ΔP@5 claim must leave the abstract and C2.
- **Rationale:** expertise-first — methodology issues defer to R1, and EIC explicitly ceded the statistical reading ("the statistical treatment is Reviewer 1's remit"). DA-1's protocol detail is consistent with R1's arithmetic and with every other seat's inference; the exact n must be confirmed by the authors, but the caption's silence is the defect regardless of its value.

**D3 — Does the headline routing/FPR result survive?** *(direction conflict — unresolved)*
- **R2 (summary):** KB-granularity routing "halves the false-positive rate … a large, cheap, significant win". **R3 (summary):** the core contribution "survives scrutiny".
- **R1-M1/M2, DA-2/DA-3:** the significance was tested on Recall@5 where the system trails, and the FPR advantage is substantially abstention.
- **Editor's resolution:** **the claim cannot be accepted as printed, and it is not declared null either — recorded as unresolved dissent requiring author response.** R2's and R3's endorsements rest on numbers the paper does not print; R3's own C2 concedes the identical figures that refute the reading.
- **Rationale:** evidence-first. The panel does not average this into "partially true". The effect is decidable only after the coverage-matched, metric-correct re-analysis (roadmap M1–M2); the authors must supply it, and the abstract's current sentence must be withdrawn meanwhile.

**D4 — Severity of the routing-novelty gap.** *(severity/direction conflict)*
- **EIC-1:** an unstated gap, repairable with one Related Work paragraph, three cheap baselines, an oracle and a "modest but true" restatement.
- **R2-01:** the claim as written is indefensible; KB-granularity routing is the decades-old collection/resource-selection problem, and its absence makes the headline contribution read as an independent invention of a solved problem.
- **Editor's resolution:** both hold; the remedies merge. Delete the sentence, add the literature, restate narrowly, and add the baselines and the size-matched control.
- **Rationale:** R2 owns the IR literature dimension; EIC owns positioning and remedy cost. R2's severity governs the *claim*; EIC's governs the *repair*.

**D5 — How far does the honesty breakdown extend?** *(existence conflict)*
- **EIC-6:** "one apparent exception" — the XQuAD omission — in an otherwise candid paper.
- **R1-M3/M6, R2-08, DA-2/DA-4/DA-5:** at least four more (the misattributed 0.0% adversarial rate with the true full-system value absent; the reversed in-house Recall@5 claim; prose drawn from a discarded run; "neutral" for a consistent loss).
- **Editor's resolution:** EIC's characterisation is **too generous; the breakdown is systematic in the number layer, not the narrative layer.**
- **Rationale:** R1 and DA reconstruct from artefacts; EIC's evidence is the authors' own audit note. The distinction matters for the revision: the *narrative* candour is a genuine asset to preserve intact, while the *number pipeline* must be rebuilt and re-verified rather than merely corrected in the places that were noticed.

**D6 — The scope of Peer Reviewer 3's new demands.** *(perspective difference)*
- **R3-M4/M7/m8** demand a threat model, a reputation-system failure analysis and an accountability/recourse discussion for a 94-tool agent-operated surface.
- No other seat raises these; EIC-3 treats §6 as a paragraph to compress rather than expand.
- **Editor's resolution:** **accepted in scope-reduced form.** Retain provenance of ingested content, one adversarial-ingestion test, a confirmation policy for the destructive tools, and rollback of a partially applied multi-layer write; retain a short credibility-failure-modes paragraph (self-review prohibition, reviewer cap, cold-start exit rule) and a short accountability paragraph. Do **not** mount a security evaluation — the paper makes no security claim, and one seat's demand does not set the scope.
- **Rationale:** the surface is load-bearing for the paper's own framing ("agent-native" leads the title), so silence is not defensible; but a full threat model belongs to a different paper, and the panel will not require work no criterion demands. EIC-3's compression and R3's content requirement are jointly satisfiable: demote C4's *contribution status*, keep the surface as a subsection, and spend the space on the trust model.

**D7 — Panel-internal conflict on the adversarial numbers (unresolved; referred to the authors).**
R1-M3 cites the archived per-intent breakdown as adversarial FPR 0.10 for QDCVR-MoE over **n = 10**; DA-2 cites the CIKM artefact as QDCVR-MoE 27.8%, QDCVR-Flat 73.0%, Hybrid-RRF 62.4% over **n = 8**. Both agree the printed "0.0%" is not the full system's number and that the true value is non-zero. The panel cannot resolve which archived value is authoritative from the material supplied; the authors must publish the subset and settle it (roadmap M4). This discrepancy is **not** treated as evidence against either seat — it is recorded as an open item the revision must close.

**D8 — Determinism: virtue or defect.** *(severity conflict)*
- **R2** credits the ±1.5 judge tolerance disclosure as an honesty signal most papers omit; **R1-M6** shows the project's own two-run comparison falsifies the "bit-identical" claim (83 differing fields; hit@3 1→0; recall@3 0.5→0.0).
- **Editor's resolution:** the credit stands, the claim does not. Withdraw or restrict the determinism claim; keep the tolerance disclosure and evidence it.

---

# Part 3 — Devil's Advocate CRITICAL Adjudication

Both DA CRITICALs are adjudicated below. **Neither is rejected; both are VALIDATED and therefore block any favourable decision.**

### DA-1 — "The single experiment establishing that content adjudication pays is an 8-query ablation that the paper never discloses as such." → **VALIDATED**

- **DA's argument:** the project's own pre-existing table for this study records "8 benchmark queries … top-k = 5" and "Stage-1 k = 20"; the paper's Table 6 caption says only "Ablation on the held-out benchmark", immediately after that benchmark was defined as 50 queries; the abstract then imports the 8-query delta as the positive evidence for the central mechanism.
- **Corroborated by:** R1-M4 (independently concludes from arithmetic that the relevance definition or denominator must differ, not merely the query set), EIC-4 (4–7× scale gap on "nominally the same benchmark"), R2-07 (TODO-9 concedes the mismatch), R3-M1 — i.e. **C1, a CONSENSUS-4 item with DA corroboration.**
- **Adjudication: VALIDATED.** The caption's silence is a disclosure defect independently of the exact n, and an 8-query point estimate cannot carry contribution C2 or an abstract sentence under any reading.
- **Required author response:** disclose the exact protocol and n in the caption; re-run on the 50-query/qrels/metric protocol, or remove ΔP@5 = −0.152 from the abstract and C2 entirely. A caption-only fix does not discharge this item (see D2).

### DA-2 — "The headline adversarial result (76.9% → 0.0%) is traceable to a separate 8-query domain-only experiment, while the full system records 27.8% FPR on adversarial queries — a number that appears nowhere in the submission." → **VALIDATED**

- **DA's argument:** the 0.0% comes from an experiment labelled *Domain* (scoping only, no adjudication), yet it is presented in the system's name; the flat baseline is printed as 76.9% rather than the artefact's 73.0%; the full system's 27.8% is suppressed.
- **Corroborated by:** R1-M3 — the 76.9% and the 50.0% "describe the same set", neither has a stated n or metric definition, neither appears in the frozen snapshot, and the archived per-intent breakdown contradicts 0.0%. **C5 (CONSENSUS-3) and C14 (CRITICAL ×2) both bear on this.**
- **Adjudication: VALIDATED.** The defect is twofold and both halves are anchored: a number produced by one configuration is attributed to another, and an adverse number for the actual system is absent. Both directly contradict the paper's own completeness claim ("a paper that hid them would be describing a different system from the one we measured").
- **Required author response:** attribute each figure to its exact configuration and n, report the full system's adversarial FPR, define the metric and denominator, reconcile 76.9% with 50.0%, and delete every "0.0%" attributed to content-adjudicated search. The n = 8 vs n = 10 and 0.278 vs 0.10 conflicts (D7) must be settled from the artefact.

**Emitted adjudication line:** `da_critical_adjudications: [DA-1=VALIDATED, DA-2=VALIDATED]` · `editorial_decision=major_revision`
No `[DA-CRITICAL-VS-ACCEPT]` marker applies: the decision is not Accept, and no DA adjudication was REJECTED, so no rejection rationale line is emitted.

### DA MAJOR findings — handling
DA-3 (p-values on Recall@5), DA-6 (no size-matched control; 0.62-accuracy ceiling), DA-7 (bundled ablation row), DA-8 (XQuAD + Japanese), DA-9 (latency attribution), DA-4/DA-5 (in-house Recall@5; "neutral"), DA-10/DA-11 (SQuAD answer@1; provenance wording), DA-12 (claim scope) are not CRITICAL under the panel's own tagging, but they are **not** dropped: each corroborates a live consensus or corroborated finding and each generates roadmap work (M1, M4, M6, M7, M9, M10, M12, M13, S4, S6).

**Panel-internal note:** the DA's summary header states "2 CRITICAL and 9 MAJOR findings", while its ID list contains 2 CRITICAL, 7 MAJOR (DA-3…DA-9) and 3 MINOR (DA-10…DA-12). The counts in this letter are taken from the tagged IDs, not the header. This does not affect any adjudication.

---

# Part 4 — Editorial Decision

## Decision: **MAJOR REVISION** — Full Research track, final round

*(Matrix basis: `Major | Major | Major | Reject → Major Revision (last chance)`. Vote 4–1.)*

**Justification.** CIKM is the right home for this work and the current manuscript is not yet a CIKM Full Research paper. The topic genuinely spans CIKM's three communities — retrieval (BM25→vector cascade, KB routing, adjudication), knowledge organisation (experience lifecycle, credibility tiers, decay, nested KBs) and agent-facing infrastructure (a 94-tool MCP surface) — and no better venue exists among IR/DM/KM: as a SIGIR/ECIR paper the IR content is too thin and half of it negative, and as a KDD/VLDB paper it offers no mining, learning or storage-engine contribution. The problem the panel identifies is **allocation of effort, not of topic**: roughly a page of the nine content pages is platform inventory while the evaluation is the thinnest part of the paper. What stands between the manuscript and acceptance is neither dishonesty nor a dead idea — the negative results are real, mechanism-explained, and better reported than most submissions — but a **claim layer that outruns its measurement layer**. Five defect clusters are corroborated across seats and two DA CRITICALs are validated: the ablation that carries C2 is a different experiment from the table it is read against (CONSENSUS-4, DA-1 VALIDATED); the headline significance was tested on Recall@5, where the system trails, and the headline FPR rewards abstention over discrimination (C11, C14, DA-3); the multi-domain claim rests entirely on author-built data while every public benchmark is single-domain (C7); the "frozen artefacts" guarantee is contradicted inside its own section and nothing is linkable (C2, C4); and the submitted PDF still carries ten red TODO markers (C3). Each is repairable with infrastructure the authors already hold — the per-query record exists, the generator exists, the public multi-domain routes are documented in their own notes — which is why the panel stops short of Reject, and why R1's Reject is recorded as a **judgment on the manuscript as submitted that the revision must answer rather than as an error to be overruled**. The revised manuscript will be re-reviewed, and if the metric-correct tests, coverage-aware FPR, same-protocol ablation and per-query artefact do not appear, Reject is the appropriate outcome.

**CIKM-track reasoning.** Full Research at CIKM expects an isolated research claim that survives its own threats-to-validity section. Two branch conditions apply. *(i)* If a public multi-domain split is produced (BRIGHT, BEIR partitioned into topic bases, or the HotpotQA route the authors' own `DATASETS-AND-EXPERIMENTS.md` records), the Full Research claim stands, bounded to what was measured. *(ii)* If independent multi-domain evidence cannot be produced, the honest destination is **CIKM's applied/industry track with the claim explicitly bounded to the in-house corpus and stated as such in the abstract and C1** — a respectable outcome and better than over-claiming on the Full Research track. The one combination the panel will not accept is the current one: Full Research framing carrying a multi-domain claim supported only by author-constructed data. Venue-fit details reinforce this: the two CIKM-native citations are decorative (TAGME and BERT4Rec in a closing sentence, with BERT4Rec mischaracterised), and the one CIKM-literate reader will ask for the resource-selection lineage and the artefact before anything else.

---

# Part 5 — Revision Roadmap

> **Ordering note.** Items are sequenced by blocking dependency for readability at the authors' request. This sequence is *not* an obligation ranking and does not pre-empt author triage: each item carries its own transported severity, and `cost_scope` is the contract field. Effort bands are the synthesizer's estimates, not a venue deadline. Authors choose `will_address` / `wont_address` / `not_on_point` explicitly later.

## 5.1 Blocking issues (the three that currently block acceptance)

| Ref | Blocking issue | Source seats | Evidence anchor | Resolving items |
|-----|----------------|--------------|-----------------|-----------------|
| B-1 | The C2 evidence base is a different experiment from the table it is compared against, at undisclosed n | EIC-4, R1-M4, R2-07, R3-M1, DA-1 | table: Table 4 vs Table 5/6 — P@5 0.117–0.200 vs 0.723–0.875 | M3, M13 |
| B-2 | The two headline claims are measured on axes that do not support them (significance on Recall@5; FPR over returned documents only) | R1-M1, R1-M2, R3-C2, DA-2, DA-3 | artefact: paired t-test on Recall@5, n=46, negative d; 22 empty result lists, all QDCVR-MoE | M1, M2, M4 |
| B-3 | Nothing is verifiable: no anonymous artefact, no qrels/per-query scores/judge prompt in the snapshot, corpus described from two incompatible snapshots | EIC-5, EIC-7, R1-M5, R3-m6 | file: `data-snapshot/MANIFEST.json`; §7.2 vs Table 2 | M5, M8 |

## 5.2 Must fix

| # | Requirement | Demanded by | New experiments or writing | Effort (est.) | Severity |
|---|-------------|-------------|---------------------------|---------------|----------|
| M1 | Name the test, metric, sign and n in §7.2 and in the Table 4 caption; print Holm-adjusted values; run exact McNemar/permutation for P@1 and a paired bootstrap for the FPR difference; demote the Recall@5 test to a secondary result reported with its true sign; recompute or delete the single shared CI [0.43, 0.57]. Withdraw the abstract's significance sentence until this is done. | R1-M1, R3-M1/m3, DA-3 | Re-analysis of the existing per-query records (no new runs strictly required) | 2–4 days | CRITICAL |
| M2 | Report per method: share of queries returning zero documents; FPR over returned documents **and** per query; coverage and precision-on-answered; and one metric abstention cannot game (α-nDCG or answer-with-support). Reframe the claim as a coverage/precision trade with its measured cost, or replace the metric. | R1-M2, R3-C2 | Re-analysis of archived per-query records | 3–5 days | CRITICAL |
| M3 | Re-run the ablation on the identical query set, qrels, metric unit and scale as the main table; put the full-system row in both tables; state query set, n, relevance definition and protocol in every caption; add the 2×2 scoping × adjudication factorial with its interaction term — the direct test of the "complementary, neither sufficient alone" claim. | EIC-4, R1-M4, R2-07, R3-M1, DA-1 | **New experiments** | 1–2 weeks | CRITICAL |
| M4 | Attribute every adversarial figure to its configuration and n; publish the subset with query texts, gold documents and the metric definition; report the full system's adversarial FPR; reconcile 76.9% with 50.0%; resolve n=8 vs n=10 and 0.278 vs 0.10; delete "0.0%" for content-adjudicated search. | R1-M3, DA-2 | Re-analysis + writing; small re-run if the set is n=8 | 3–5 days | CRITICAL |
| M5 | Ship an anonymous artefact containing the frozen snapshot with MANIFEST, `make_assets.py`, the 50 queries with qrels, per-query per-method score vectors, the real SciFact/SQuAD ids, the judge prompt with model/version/decoding, the adversarial subset and the 73-check E2E JSON; make `load()` fail on any unmanifested file; restore run identity (git commit, config hash, seed); cite the link from §7.8. | EIC-7, R1-M5, R3-m6, DA-11 | Engineering + writing | 3–5 days | CRITICAL |
| M6 | One run per number: regenerate the prose from the frozen run; report ≥5 runs with SD for every stochastic channel and median+IQR latency; withdraw or restrict the "bit-identical" claim; correct in-house R@5 to 0.908 vs 0.917 (QDCVR **loses**), SciFact nDCG 0.830→0.834 and MRR 0.838→0.839, SQuAD answer@1 (BM25 0.875), Table 8's median (3.0, or relabel as mean over 8), and the latency/character figures. | R1-M6, R1-M12, R2-08, R3-m1/m2, DA-4/5/9/10/11, EIC-10 | **New runs** for the SD claim; the rest is re-derivation from existing artefacts | 1–2 weeks | MAJOR (CRITICAL-adjacent) |
| M7 | Report XQuAD with the same framing used for SciFact (vector ≈3× P@5; 0.275 vs 0.831) — or remove the set and the "at or near ceiling" sentence; add the Japanese row (n=4) or a labelled exclusion note; correct "bilingual" to trilingual. | EIC-6, R1-M9/M8, R3-m6/m2, DA-8 | Writing (the record already exists) | 1–2 days | MAJOR |
| M8 | Restate §7.2 with one dated snapshot per experiment, matching Table 2 row-for-row; resolve the 12-vs-13 KB conflict; list all eleven domains or delete the count; relabel Figure 2's corpus annotation; state where the snapshot can be rebuilt. | EIC-5, R1-M8, R3-m6/m4 | Writing | 1–2 days | MAJOR |
| M9 | Add a Related Work paragraph on federated/distributed-IR collection and resource selection and on LLM/MoE query routing; delete "not the axis prior work optimises"; restate the claim narrowly (administrator-authored descriptions, administrative partitions, FPR-reduction objective). Add baselines: always-search-all, BM25-over-catalogue, size prior, oracle router, and a size-matched/random-pool control; report selection precision@3, the ceiling implied by 0.62 accuracy, and behaviour at N ∈ {13, 50, 200}. | EIC-1/EIC-11, R2-01/05/06, DA-6 | **New experiments** + writing | 1–2 weeks | MAJOR |
| M10 | Validate the instrument: judge model/version/prompt in the snapshot; 3-annotator κ on ≥40 items plus per-dimension agreement; threshold provenance and a sensitivity sweep over τ and the 6/5/4 cuts; the rubric-structure ablation (0–8 rubric vs scalar 0–10 judge vs binary filter vs cross-encoder vs pointwise LLM re-ranker) under one decision rule; decompose the "− adjudication" row so its delta is attributable. | R1-M10, R2-02, R3-M6, DA-7 | **New experiments** + annotation | 2–3 weeks | MAJOR |
| M11 | Supply the TODO-6 experience baseline (no-synthesis and one-shot LLM summary under the identical judge prompt) and the TODO-4 leave-one-out over the five retrieval paths; add a "− graph expansion" row; state what "− experience archiving" removes and how it can move document-level P@5 — or demote C3 to system design. | EIC-2, R2-03/07, R3-m6 | **New experiments**; the demotion route is writing-only | ~1 week (or ~1 day) | MAJOR |
| M12 | Add one public multi-domain evaluation (BRIGHT / BEIR partitioned into topic bases / the HotpotQA route already in the project's notes) — **or** bound the multi-domain claim in the abstract and C1, not only in §8, and remove the two uncited bib entries. | EIC-12, R2-06, R3-C1, DA-12 | **New experiments**; the bounded fallback is writing-only | 2–4 weeks (or ~1 day) | CRITICAL (R3) |
| M13 | Retitle so the research claim leads and conditional adjudication reads as the instrument under test; rename QDCVR-MoE → QDCVR-Scoped in `make_assets.py` and regenerate Table 4, Figure 3 and Figure 6; move domain scoping to the front of the abstract and C1; "halves" → "cuts by 45%"; "neutral" → a directional per-metric statement. | EIC-8/EIC-9, R2-08, DA-5 | Writing + asset regeneration | 2–3 days | MAJOR |
| M14 | Demote C4 to a system subsection (keep the two contract defects as a short observation); state how many of the 94 tools the 73 checks cover; delete or measure "cross-platform"; compress §3 and §6 and Table 2's structural rows, drop the figure duplicating a table, and free ~1.5–2 pages for M3/M9/M10/M12; trim the abstract to ~200 words. | EIC-3/EIC-13, R1-M11/M16, R2-07, R3-m6 | Writing | 3–5 days | MAJOR |
| M15 | Remove every red `[TODO-n]` marker and reconcile the page count with the README and the audit. | R1-M16, R2-07, R3-m6, EIC-13 | Writing | hours | MAJOR |

## 5.3 Should fix / consider

| # | Requirement | Demanded by | Type | Effort | Severity |
|---|-------------|-------------|------|--------|----------|
| S1 | Restate the five-layer consistency guarantee as a measured bound; name the self-check as self-verification by the write path; define the agreement metric and its granularity; state what is uncovered (concurrent writers, crash mid-write, partial index failure); or implement real transactional semantics. | EIC, R1-M11, R3-M5 | Writing (+ optional engineering) | 2 days | MAJOR |
| S2 | Add a scope-reduced trust/failure subsection: ingestion provenance and untrusted-content handling, one adversarial-ingestion test, which destructive tools require confirmation, audit records, rollback of a partial multi-layer write; add credibility failure modes (self-review prohibition, distinct-reviewer requirement, reviewer cap, cold-start exit rule, decay from last independent verification) and a short accountability paragraph. | R3-M4/M7/m8 | Writing + one test | ~1 week | MAJOR |
| S3 | Scale SciFact to the full 300 queries or a documented random sample with real ids; state n and the minimum detectable effect in every table; void sub-threshold comparisons and replace IMPACT adjectives with measured statements; add a hyper-parameter provenance table (BM25 k1/b, jieba dict, BGE-M3 revision, HNSW M/ef, hardware, latency protocol) and reconcile §4.3's and §7.2's two different fusion descriptions. | R1-M7/M13/M14 | **New experiments** + writing | 1–2 weeks | MAJOR |
| S4 | Add a per-stage latency decomposition with candidate and document counts entering adjudication, explain the 12× scoped/unscoped gap, state that the SciFact latencies are harness-dominated, and report adjudication cost in documents as well as characters. | R3-M3, DA-9 | Instrumentation + re-run | ~1 week | MINOR (R3) / MAJOR (DA) |
| S5 | Report the content-coverage metrics that favour QDCVR (claim_evidence 0.5126 vs 0.4726; support@1 0.600 vs 0.567) with their caveats and their non-standard instrument definition; downgrade §6's "no privileged path" generalisation to a structural statement; clarify that SQuAD's gold is author-constructed while SciFact's qrels are official. | R3-m7/m6 | Writing | 1 day | MINOR |
| S6 | Bold the SciFact column bests or fix the caption; reword §7.8 to "verifies each digest on every regeneration"; delete or cite the unused bib entries; replace the decorative TAGME/BERT4Rec sentence with load-bearing CIKM-native citations. | EIC-11, R2-05/06, DA-11 | Writing | hours | MINOR |
| S7 | Fix the snapshot's mixed run provenance (`module_b` from the live results directory, `module_c` from `archive-20260913-214859`). | R1-M5 | Engineering | 1 day | CRITICAL-adjacent |

## 5.4 Source-traceability checklist

- [ ] M1 — `must_fix`: metric-correct significance testing (R1-M1, R3-M1, DA-3)
- [ ] M2 — `must_fix`: coverage and abstention-aware FPR (R1-M2, R3-C2)
- [ ] M3 — `must_fix`: one-protocol ablation + factorial interaction (EIC-4, R1-M4, R2-07, R3-M1, DA-1)
- [ ] M4 — `must_fix`: adversarial number reconciliation and attribution (R1-M3, DA-2)
- [ ] M5 — `must_fix`: anonymous artefact and complete snapshot (EIC-7, R1-M5, R3-m6)
- [ ] M6 — `must_fix`: one run per number; determinism claim withdrawn (R1-M6/M12, R2-08, R3-m1/m2, DA-4/5/9/10/11, EIC-10)
- [ ] M7 — `must_fix`: XQuAD reported or removed; Japanese subgroup disclosed (EIC-6, R1-M8/M9, R3-M2/m6, DA-8)
- [ ] M8 — `must_fix`: one dated snapshot in §7.2 (EIC-5, R1-M8, R3-m6)
- [ ] M9 — `must_fix`: resource-selection literature, baselines, oracle and size-matched control (EIC-1/11, R2-01/05/06, DA-6)
- [ ] M10 — `must_fix`: adjudicator validation and rubric-structure ablation (R1-M10, R2-02, R3-M6, DA-7)
- [ ] M11 — `must_fix`: experience baseline and multi-path ablation, or C3 demoted (EIC-2, R2-03/07, R3-m6)
- [ ] M12 — `must_fix`: public multi-domain evidence, or the claim bounded in the abstract (EIC-12, R2-06, R3-C1, DA-12)
- [ ] M13 — `must_fix`: reframing, retitling, asset regeneration (EIC-8/9, R2-08, DA-5)
- [ ] M14 — `must_fix`: C4 demoted, page budget reallocated (EIC-3/13, R1-M11/M16, R2-07, R3-m6)
- [ ] M15 — `must_fix`: markers removed, page count reconciled (R1-M16, R2-07, R3-m6, EIC-13)
- [ ] S1 — `should_fix`: consistency claim restated (EIC, R1-M11, R3-M5)
- [ ] S2 — `should_fix`: trust/failure model and credibility failure modes (R3-M4/M7/m8)
- [ ] S3 — `should_fix`: scale, power and hyper-parameter provenance (R1-M7/M13/M14)
- [ ] S4 — `consider`: latency decomposition (R3-M3, DA-9)
- [ ] S5 — `consider`: favourable content-coverage metrics reported with caveats (R3-m7)
- [ ] S6 — `consider`: presentation, citation and provenance wording (EIC-11, R2-05/06, DA-11)
- [ ] S7 — `consider`: snapshot run provenance (R1-M5)

---

# Part 6 — Do Not Change

Every item below is anchored in at least one seat's strength list. These are the assets the revision must carry through intact — several of them are the reason the panel chose Major Revision over Reject.

1. **The bounded claim in §8 and the abstract's refusal of uniform superiority.** "We report this boundary explicitly rather than claiming uniform superiority"; "The claim we explicitly decline to make is that content adjudication improves retrieval in general. Our own SciFact and SQuAD results refute that reading." *(EIC strengths 1–2, R2 strength 1, R3 strength 1, DA strength 3.)* Keep this section verbatim in substance; only widen the boundary to cover the multi-domain data provenance.
2. **Mechanism-level explanation of the negative results, not just their confession.** §7.4's account of *why* adjudication fails on SciFact (corpus homogeneity, the Stage-3 τ dropping gold documents, 4,292 characters read per query with only ~3.0 passing) and §7.6's architectural diagnosis (metadata with empty payloads). *(EIC strength 1, R2 strength 1, R3 strength 1.)*
3. **The 3.5/10 experience result reported with the judge's own verbatim criticisms** ("empty shell", "no content body or verifiable facts") and the refusal to equate quarantine with quality. *(All five seats.)* This is the single most cited strength in the panel; it is also, per R3-m5, **worse than the paper admits** — fix the statistic, do not soften the finding.
4. **The refusal to claim the two-stage cascade as a contribution, evidenced by its own losing number** (Hit@3 0.833 vs dense 0.900). *(R1 strength 5, R2 strength 5, DA strength 5.)* Apply the same standard to the routing and adjudication claims — do not withdraw the standard.
5. **The hash-pinned snapshot and the generator that aborts on digest mismatch** — including the archived copy of a result a later run had overwritten. *(EIC strength 4, R1 strength 3, R2 strength 3, R3 strength 5, DA strength 4.)* Fix the *coverage* of the practice (M5, S7); never trade the practice away for convenience.
6. **The independently written external E2E client and the two real contract defects it found** — read endpoints accepting only one of two documented parameter spellings, and two engine-registry entries whose declared env-var requirements contradicted the engines' docs and made working engines unselectable — together with the self-report that an earlier run's four failures were harness artefacts. *(EIC strength 3, R1 strength 4, R3 strength 6.)* This is a genuine empirical observation about agent-facing API contracts and should survive as a short subsection after C4 is demoted.
7. **Method specification detailed enough to attack and re-implement.** Algorithm 1, the three-dimension rubric with ranges, the tier and decay equations with numeric thresholds, the full parameter list, and the honest disclosure that the benchmark used k = 40/10 while the platform default is 20/5 (recorded in the manifest). *(R1 strength 5, R2 strength 4.)* Add the missing provenance table; do not simplify away the specificity.
8. **One shared index and tool layer for all methods, so the comparison isolates the ranking stage.** *(R2 strength 4.)*
9. **The multiplicity disclosure and its arithmetic** — "the single result that survives it is the comparison against Hybrid-RRF … We state this rather than reporting only the favourable number." *(R1 strength 2, R2 strength 2.)* The disclosure is the right instinct; M1 corrects the metric it applies to, and R1 has independently confirmed the Holm arithmetic is correct.
10. **§5.4's symptom-vs-topic observation** ("a user searching for 'why did the run fail' shares no vocabulary with an entry titled 'pulse self-heating window violation', but shares its scenario and tags"). *(R3 strength 3.)* The most transferable idea in the paper; add the TODO-4 measurement rather than cutting it.
11. **The write–read asymmetry as a quantified cost insight** (§3.3; 117 ms scoped vs 1,411 ms unscoped). *(R3 strength 4.)* Keep it, and make the mechanism explicit (B1/S4).
12. **The agentic/enterprise-KB related-work paragraph** (AgenticRAG, AutoKB, DeepRead): closest industrial prior art named, the axis of difference localised to "where the judgement lives", and the unevaluated combination conceded. *(R2 strength 3.)* This is the model the rest of §2 should be rewritten to match.
13. **Author-evaluation bias named as the strongest threat** ("every benchmark in this paper was designed, run and scored by the authors"). *(EIC strength 1, DA strength 3.)* Do not trim it when the multi-domain items land.
14. **Venue-compliance basics:** anonymous sigconf, review option, no institution or URL, GenAI disclosure covering writing/code/data/instrument separately and placed before the bibliography, CCS concepts and keywords. *(EIC strength 4.)*
15. **The low-impact ablation rows reported as low-impact** (blind-spot guard ΔP@5 0.000 / ΔFPR 0.000; query rewriting −0.028) rather than spun upward. *(R3 strength 2, DA strength 1.)*
16. **Per-metric reporting granularity.** Hit@3, R@5, nDCG@10, MRR and P@5 are all printed, including where the method loses, and the figure/table pair is generated. Fix the digits and the unit consistency; do not respond to C2 by deleting per-metric detail in favour of a single headline number.

*Manuscript not modified: this document is a separate review artifact. No file of the submission was edited.*


---

# Part 7 — Author Response and Independent Verification

*Appended by the authors after the panel returned. The panel's text above is
unmodified; this part records what was independently re-checked and what changed.*

## 7.1 Verification of the CRITICAL findings

The authors re-checked six of the eight CRITICAL findings directly against the
repository rather than accepting them on the panel's word. **All six were
confirmed true**, including three defects the authors had introduced during the
previous revision round.

| Finding | Claim | Verified against | Result |
|---|---|---|---|
| R1-M1 | The p-values test Recall@5, not P@1, and are negative | `benchmark-web/backend/results/v4/benchmark_report.json` | **TRUE.** Four records, all `"metric": "Recall@5"`, `n_paired: 46`, t = −2.14 / −2.12 / −3.49 / −2.28, d = −0.32 to −0.51 |
| R1-M4 / DA-1 | The ablation is an 8-query study | `docs/paper/benchmark/paper-tables/table3-ablation.tex` | **TRUE.** "Notes: **8 benchmark queries**; embedding = BGE-M3; top-k = 5 … Stage-1 k = 20" |
| R1-M5 | A table statistic is hard-coded and mislabelled | `make_assets.py` line 344 | **TRUE.** `Median judge score & 3.5` was a literal; the actual median of the eight judged entries is **3.0** and 3.5 is the *mean* |
| DA-2 | The real full-system adversarial FPR is 27.8%, not 0.0% | `benchmark-web/backend/results/cikm/table4_fpr.tex` | **TRUE.** `QDCVR-MoE (Ours) & 34.8% & 27.8%`; `QDCVR-Flat` is `73.0%` |
| R1-M5 | `load()` passes silently on unmanifested files | `make_assets.py` | **TRUE.** Guard was `if want and digest != want` |
| R1-M5 | "148 articles" is hard-coded | `make_assets.py` line 194 | **TRUE** |

**No CRITICAL was rejected.** The authors accept all eight.

## 7.2 What changed in this revision round

Addressed (verified in the rebuilt PDF):

| Item | Status | What was done |
|---|---|---|
| **M1** | ✅ done | §7.2 and the Table 4 caption now name the metric (`Recall@5`), the sign, and `n=46`; Holm-adjusted values printed; the abstract and C1 rewritten to state the recall-for-precision trade instead of a significance win |
| **M4** | ✅ partly | §1 and §7.5 now attribute `76.9% → 0.0%` to the domain-scoping-only 8-query probe, report the true full-system `73.0% → 27.8%`, and state that 0.0% on eight queries has no useful denominator. The `50.0%` figure was removed. Reconciling `n=8 vs n=10` and `0.278 vs 0.10` still needs the per-query record |
| **M6** | ✅ partly | Median and mean both computed from the snapshot, and the bimodality disclosed; SciFact nDCG `0.830 → 0.834` and MRR `0.838 → 0.839` corrected; `median → 3.0` with the mean labelled as such |
| **M8** | ✅ done | §7.2 rewritten so each corpus is pinned to one dated snapshot, matching Table 2 row-for-row; `11 domains → eight domains`; the `184 documents` / `13,709 chunks` chimera removed |
| **M9** | 🟡 partial | "not the axis prior work optimises" retained but now carries an explicit TODO for the resource-selection lineage and baselines. **Baselines are still missing** |
| **M13** | ✅ partly | `QDCVR-MoE → QDCVR-Scoped` throughout prose and regenerated assets (no mixture-of-experts mechanism exists); `halves → cuts by 45%`; domain scoping moved to lead the abstract; decorative CIKM-native citations removed. **Retitling still open** |
| **M15** | 🟡 partial | Markers compressed from ~2 pp to ~0.65 pp and re-pointed at `REVIEW-TODO.md`; they still must be deleted before submission |
| **S7** | ✅ done | Snapshot provenance recorded per file in `MANIFEST.json`, with `module_c` explicitly sourced from `archive-20260913-214859` |
| — | ✅ done | Two references with **fabricated author metadata** corrected against the project's own PDFs; three relevant uncited papers added |
| — | ✅ done | §3 expanded into a full architecture section with a system figure; §1 gained a "What is new here" novelty paragraph |

Not addressed (needs new experiments or new annotation — cannot be written):

`M2` (coverage/abstention metric), `M3` (single-protocol ablation + 2×2 factorial),
`M5` (anonymous artefact with qrels/per-query scores), `M7` (XQuAD), `M9`
baselines, `M10` (judge validation + κ), `M11` (experience baselines), `M12`
(public multi-domain), `S3`, `S4`, `S5`, `S6`. Each is enumerated with its
acceptance criterion in `REVIEW-TODO.md`.

## 7.3 Author position on the two branch conditions

The panel's §"CIKM-track reasoning" offers two acceptable branches. The authors
**select branch (ii) as the fallback and intend branch (i) as the target**:
produce the public multi-domain split via the HotpotQA route already documented in
`docs/paper/DATASETS-AND-EXPERIMENTS.md` (supporting documents clustered into 8–12
topic knowledge bases). If that cannot be completed, the multi-domain claim will
be bounded in the abstract and C1, and the submission moves to the applied/industry
track rather than over-claiming on Full Research.

## 7.4 One correction to the panel record

The panel's Part 5 opens by citing "ten red TODO markers". The count at review
time was **15 marker commands**, of which two were the macro definitions in the
preamble and thirteen were live markers in the body. The substantive point —
that a submitted PDF must carry none — stands unchanged.
