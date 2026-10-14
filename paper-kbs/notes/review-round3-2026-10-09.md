# Editorial Decision Letter — Round 3 (2026-10-09)

模拟 KBS (Knowledge-Based Systems, Elsevier) 返稿意见。评审团 5 席独立评审
（互不可见），编号对应本文件后半部分的分席报告全文。

- Manuscript: `tex/main.tex` (32 pp, elsarticle preprint)
- Panel: Journal-Fit Reviewer (EIC) / R1 Methodology / R2 Domain / R3 Perspective / DA (Devil's Advocate)
- Seat verdicts: EIC **Minor**; R1 **Major**; R2 **Major**; R3 **Major**; DA *"not publishable as framed; conditionally publishable after reframing"* (= Major)

---

## EDITORIAL DECISION: **MAJOR REVISION** (encouraged)

Dear Authors,

Your manuscript reports a deployed, verified multi-lane retrieval platform and a
quantified analysis of its verifier's failure mode. The panel is unanimous that
the measurement discipline is exceptional: every reviewer who recomputed numbers
from the released logs (R1: 25+ checks; DA: ~25 checks) found zero
discrepancies, and the negative-result honesty ("a measured open problem") is
exactly the register this journal values. The consensus view is that the paper
is **publishable in KBS after a revision that (a) repositions the core claim
inside the LLM-as-a-judge literature it currently ignores, (b) brings the
title/abstract claims down to what one 42-document case study can support, and
(c) repairs four specific methodological disclosures**. No reviewer requests new
hardware or a new corpus; the most common "strong revision" asks are writing and
disclosure work, plus one cheap offline addition (a second verification signal
on the already-logged pools) that we strongly encourage but do not require for
acceptance.

### Consensus findings (multi-reviewer corroboration)

| # | Finding | Seats | Severity |
|---|---------|-------|----------|
| C1 | Zero engagement with LLM-as-a-judge / verifiability / abstention literature; "same-domain inflation" framed as phenomenon-level novelty though it re-derives known judge miscalibration (score compression, self-preference) | EIC, R2 (CRITICAL), DA | CRITICAL |
| C2 | Claims exceed evidence: generic "enterprise knowledge bases" title vs one 42-doc corpus; BM25 saturates at 1.00 so the benchmark discriminates almost nothing; Q16 embeds the gold filename token (lexical win circular); "production" invites scale inference | EIC, R3, DA (CRITICAL 2) | CRITICAL |
| C3 | Fact-marker metric largely question-echo (12/16 markers occur verbatim in the question; Q4 bare scores 2/2 by restating the question; Q6 marker "5" matches any digit); the §6.1 "−8 °C" example reads as a marker but is not in the released set | R1 | MAJOR |
| C4 | Bare-arm prompt asymmetry undisclosed: bare arm receives an extra "answer from your own knowledge; if uncertain, say so" instruction while the text claims arms "differ only in retrieval affordance" (verified in `exp2_lanes.py`) | R1 | MAJOR |
| C5 | Derived-config provenance: §6.2 says "computed offline from the run's own logged pools" but `exp5_judge_filter.py` issues 16 fresh live calls (judged ordering coincides exactly → judge is deterministic; state this) | R1 | MAJOR |
| C6 | Margin-0.20 "repair" is in-sample calibration on the same 17 gold instances; must be labeled as such | R1, DA | MAJOR |
| C7 | Statistical reporting: no CIs (Wilson 95% on 0.4375, n=16 ≈ [0.23, 0.67]); MW variant unspecified; sign test is one of ~27 comparisons (multiplicity); "MRR" is MRR@5 | R1 | MAJOR |
| C8 | §6.2 "central lesson" sentence inverts the evidence (verification-as-re-ranker *hurt* ranked-list quality); replace with the explicit three-part testable model | R2, R3, DA | MAJOR |
| C9 | Agent-layer 12/12 headline omits that 6/12 runs answer from 1–2 document pinned libraries (body concedes, abstract doesn't) | DA, R3 | MAJOR |
| C10 | Single judge checkpoint (Laya) carries all generalization; no model card; no alternative verification signal (NLI / general-LLM judge / symbolic numeric check — Q6 is trivially rule-checkable) | R2, R3 | MAJOR |
| C11 | No consumer-side evidence for the honesty contract (who reads the not-found reports; does abstention help?) | R3 | MAJOR |
| C12 | Lane proliferation: Search lane occupies no distinct operating point in any reported run | R3 | MAJOR |

### Editor's required actions (must be addressed in revision)

1. **Reposition (C1).** Add the missing literature: Zheng et al. (NeurIPS 2023,
   MT-Bench), Sun et al. (EMNLP 2023 relevance judging; SIGIR 2024 RankGPT),
   Wang et al. (ACL 2024, evaluator bias), Panickssery et al. (NeurIPS 2024,
   self-preference), Liu et al. (EMNLP 2023 Findings, verifiability), Gao et al.
   (EMNLP 2023, citations), Yin et al. (ACL 2023 Findings), Feng et al. (ACL
   2024, abstention), a RAG survey, and the two industrial KG-RAG papers already
   in the bib but uncited (RRPDG TII 2024, CoMA-IKG TII 2026). Rewrite
   contribution 3 to claim *operational quantification and role-decomposition
   inside a deployed pipeline*, not discovery of the phenomenon. Add a
   RankGPT-style row to Table 1.
2. **Rescope (C2, C9).** Title/abstract/conclusion: "a deployed industrial case
   study"; correct the KB description (the workshop/telemetry library is
   manufacturing, not photovoltaic); abstract must carry the pinned-library
   caveat for the 12/12 grounding claim; reconcile "16 runs" vs "32 runs"
   phrasing; fix the §1 slogan the paper's own result falsifies; fix or delete
   the §6.2 inverted sentence and state the three-part model (filter safe iff
   judge gold-recall high; ordering safe iff pairwise separation beats the base
   ranker; threshold abstention needs OOD calibration).
3. **Methodological honesty (C3–C7).** Disclose the bare-arm prompt verbatim;
   downgrade fact-markers to corroborating (with the echo caveat) and fix the
   −8 °C sentence; restate derived-config provenance truthfully (fresh identical
   call; judged ordering reproduces logged run exactly); label margin 0.20 as
   in-sample; add Wilson CIs, name the MW implementation (tie-corrected,
   U=1726, p=0.257), mark the sign test as post-hoc/descriptive, relabel MRR@5,
   disclose in-process vs MCP latency measurement; name the round-2 11/12
   exception (hybrid-Q2) and the 600-character decontamination scope; note the
   refusal detector's 5/6 agreement with the manual audit.
4. **Discussion completeness (C8, C10–C12).** Add: judge-as-filter ≡ fusion-only
   identity + the +480 ms cost, said plainly in §7.1; single-judge limitation +
   roadmap for a second verification signal (NLI/LLM-judge/symbolic); consumer
   evidence as an explicit open item; an honest sentence on lane count; the
   untested two-stage+filter combination; consolidate the incident log into a
   failure-mode table (failure → detection signal → fix → residual risk).
5. **Presentation.** Abstract ≤200 words; fix Fig. 5(b) label collision;
   complete `highlights.tex` (currently empty; KBS requires 3–5 bullets ≤85
   characters); uncite `rrpdg`/`comaikg` or remove; expand the demo-vs-paper
   delta to 2–3 concrete bullets.

### Encouraged (not required)

- Run the shipped benchmark suite at even 2× scale, or add 16 paraphrased
  variants of the existing questions, to break the BM25 saturation.
- Replay §6.3 with one additional judge (a rubric-prompted general LLM and/or an
  NLI entailment model) over the already-logged 191 candidates, and a symbolic
  check for Q6's numeric watch clause.
- A graded probe family (covered / partial / unrelated) with per-level
  abstention targets.
- Any consumer-side evidence for abstention (operator telemetry, follow-up-query
  analysis).

---

## Seat reports (condensed to decision-relevant content)

### Seat 1 — Journal-Fit Reviewer (EIC). Verdict: Minor Revision
Strengths: load-bearing knowledge layer (ingestion quality gate, claims-not-facts
descriptions, experience store); quantified/dissected honest central finding;
abstract does not oversell; practitioner value density; presentation at KBS
level. Majors: no LLM-as-judge engagement; claims scope vs evidence (title
generic, "five industrial photovoltaic knowledge bases" imprecise). Minors:
shipped-default vs recommended filter mode; thin venue-skewed references; ~250-word
abstract; Fig. 5(b) label collision; 16-vs-32 run accounting. Desk notes: author
placeholders (known action); highlights empty; ORCID/funding placeholders;
declarations otherwise complete; two uncited bib entries.

### Seat 2 — Peer Reviewer 1 (Methodology). Verdict: Major Revision
Verified 25+ numbers against logs: **all MATCH** except (a) MW p=0.26 is the
no-tie-correction variant per R1's own recomputation (later settled by the
authors: scipy tie-corrected gives U=1726, p=0.257 ≈ 0.26 — implementation must
be named), (b) the "−8 °C" marker example does not exist in the released marker
set. Majors: fact-marker echo (C3); bare-arm prompt asymmetry (C4); derived-config
provenance (C5); in-sample margin calibration (C6); thin statistical reporting
(C7). Minors: MRR@5 relabel; refusal detector 5/6 agreement; in-process vs MCP
latency; round-2 16/16 is a ceiling effect (report informative-cells agreement,
name the 11/12 exception, add round-2 turn means); decontamination scope is
answer[:600]; judge checkpoint/temperature/seeds unspecified; `scored:14` for 12
candidates unexplained; timeout-attempt logs and the earlier 8-question round not
in results/.

### Seat 3 — Peer Reviewer 2 (Domain). Verdict: Major Revision
Novelty assessment: the filter-vs-re-ranker decomposition with per-question
attribution and the repair statistic is genuinely new *inside a deployed
verified-retrieval system*; the inflation observation itself is an operational
instance of documented judge miscalibration. CRITICAL: phenomenon-novelty framing
without a single LLM-as-judge citation. Majors: single unscrutinized judge
(model card + second judge); §6.2 central-lesson inversion → three-part testable
model; missing verifiability/attribution/abstention literatures. Minors: Table 1
needs an LLM-judge-re-ranker row + neutral caption; uncited rrpdg/comaikg; demo
delta table; verify `singh-agentic-rag` turn-dominance claim, `deepread` claim,
Self-RAG "partial" basis.

### Seat 4 — Peer Reviewer 3 (Perspective). Verdict: Major Revision
Strengths: decomposed negative result on the paper's own centerpiece; abstention
evaluated at its enforcement point; MLOps-grade incident reporting; turn
economics measured; enforcement-not-prompt lane policy; artifact transparency.
Majors: missing no-verification grounded control at agent layer (or demote claim
to auditability); no consumer-side evidence for honesty contract; abstention
boundary sampled at n=1 (partial-coverage region); "production" vs n=42;
verification primitive never compared to NLI/LLM/symbolic; lane proliferation;
no deployment playbook or cost model. Minors: §6.2 self-contradicting sentence;
Windows-specific incident portability; lexical fragility under paraphrase;
missing cross-disciplinary anchors (IEC 61508 fail-safe, GRADE, FEVER/NLI, W3C
PROV, trust calibration). Three assumption challenges: (a) 42-doc "production" —
partially survives as honest pilot case study; (b) LLM judge as primitive — does
not survive as *justified* choice (survives as *studied* one); (c) three lanes —
does not fully survive (Hybrid + Librarian carry all evidence).

### Seat 5 — Devil's Advocate. Verdict: not publishable as framed; conditionally publishable after reframing
Strongest counter-argument: the verifier is the least trustworthy component of
its own pipeline (0/191 rejected; re-ranker halves Hit@5; judge-as-filter ≡
fusion-only on all 16 questions at +480 ms — identity verified from logs); the
platform's own two-stage service scores 1.00 at 77 ms and is never combined with
the gate; BM25 saturation + developer-authored questions + Q16 filename-token
circularity make the benchmark nearly non-discriminative; 6/12 agent runs answer
from 1–2 document libraries. Publish the failure analysis, not the title.
Attacks that FAIL (fairness): number-to-log fidelity (zero discrepancies);
abstention substance (6/6 explicit well-formed not-found reports, zero .md
citations); sign-test validity (controlled decomposition, sole regression Q7
3→5 as claimed); threshold-misdiagnosis attack (no threshold separates golds —
verified); tool-vs-agent-layer contradiction (decomposed and log-supported).
"So what?" verdict: the good negative result + attribution results + turn
economics + reproducible artifact merit publication **after reframing** (retitle
around what verification gates do and do not buy; run own benchmark at scale;
add one alternate judge). Observations: hybrid-Q4 transcript is the strongest
single artifact for the audit-trail value proposition; bare-Q7's unassisted
honest refusal cuts against L4's strong form and deserves engagement; judge
emits a saturated 1.0000 score (rubric clipping undiscussed); tool-layer
"pinned" Q2 still merged 43 from the 42-doc catalog (layer configs differ more
than §7.2 implies).

---

## Revision roadmap (immutable core)

| # | Item | Seats | Type | Status after this round's fixes |
|---|------|-------|------|-------------------------------|
| R1 | LLM-as-judge + verifiability + abstention literature; contribution-3 reframe; Table 1 row | C1 | writing+refs | **fixed** |
| R2 | Title/abstract rescope, KB precision, 16×2 runs, slogan fix, pinned-library caveat | C2,C9 | writing | **fixed** |
| R3 | §6.2 inverted sentence → three-part model | C8 | writing | **fixed** |
| R4 | Bare-arm prompt disclosure + affordance softening + bare 2/4 honesty engagement | C4 | disclosure | **fixed** |
| R5 | Fact-marker downgrade to corroborating + −8 °C fix | C3 | disclosure | **fixed** |
| R6 | Derived-config provenance truth + judge determinism | C5 | disclosure | **fixed** |
| R7 | In-sample margin labeling | C6 | wording | **fixed** |
| R8 | Wilson CIs + MW implementation + sign-test post-hoc + MRR@5 + latency footnote | C7 | stats | **fixed** |
| R9 | Round-2 exception named (hybrid-Q2), 600-char scope, round-2 turn means, refusal-detector agreement | R1 minors | disclosure | **fixed** |
| R10 | §7.1 identity-with-fusion + 480 ms cost said plainly; shipped-default recommendation wording | EIC/DA | writing | **fixed** |
| R11 | Failure-mode table (5 incidents → signal → fix → residual) | R3 | new table | **fixed** |
| R12 | Single-judge limitation + second-signal roadmap + two-stage×filter + graded probes + consumer evidence as open items | C10,C11 | limitations | **fixed (as limitations/roadmap)** |
| R13 | Fig. 5(b) label collision | EIC | figure | **fixed** |
| R14 | highlights.tex filled (5 bullets ≤85 chars) | EIC | submission | **fixed** |
| R15 | rrpdg/comaikg cited; demo delta bullets; Table 1 caption neutral; Self-RAG basis note | R2 | refs | **fixed** |
| R16 | Benchmark at 2× scale; paraphrase set; second judge replay; NLI/symbolic signals; user study | encouraged | future work | roadmap (not run) |

AUTHOR ACTION (unchanged, submission-blocking): real author names/affiliations/
ORCID, CRediT roles, funding or the no-funding statement, qdcvr-demo bib entry
authors.

---

## 修订执行记录 (同日)

- 编译: 37页 / 0错误 / 0未解析引用 / 0 "Appendix Appendix" / 唯一遗留 2.6pt 隐形超宽;
- 浮动体: 5个 [t] 表全部改 [!htbp] 后, Table 5→p29, Table A.1→p32, 无文末堆积;
- 视觉终审 7 页 (p7/14/17/20/23/25/29): 修复 "Appendix Appendix A" 后应全部 PASS;
- 新增 11 条文献 (zheng-llmjudge/rankgpt/sun-urara/panickssery/gao-ragsurvey/
  modular-rag/gao-citations/liu-verifiability/yin-knowwhat/feng-abstain/lightman-verify);
  wang-notfair 因作者列表不确定未收录(编辑时已撤引);
- 鼓励项(未执行, 列入 roadmap): 2倍规模benchmark、改述题集、第二判卷信号重放、
  NLI/符号校验、分级弃答探针、消费者侧证据。

## 补测数据轮 (同日晚间): R16 鼓励项执行

四个新实验全部真实执行, 脚本+原始JSON入库:
- **Exp6 LOO margin** (exp6_loo_margin.py): 最小margin规则在15训练题选出0.18,
  迁移留出题15/16存活(唯一失败=Q11, 与shipped 0.15同失), 0.20留出题16/16全存活
  → margin泛化验证完成, 回应R1#4 in-sample批评;
- **Exp6b 改述集** (exp6_paraphrase.py): 16题改述全工具层 — BM25 1.00→0.88
  (MRR 0.958→0.755, Q7/Q13丢失), Dense 0.94稳, judged 0.44→0.50仍坏,
  filter仍=fusion 0.94 → 证实词汇依赖+失效/修复对改述稳健, 回应C2/R3#10;
- **Exp7 第二信号** (exp7_second_signal.py, Erlangshen-330M NLI@CUDA):
  191对重放 hit@5 0.31/MRR 0.138(比Laya差), Spearman ρ=-0.134,
  gold中位0.011 vs 非gold 0.053 (p=0.12, δ=0.23), OOD全语料max 0.997
  → 通用NLI既排不好序也弃不了答; Q6符号检查 gold 1/1 vs 非gold 0/11完美
  → 论文核心结论(弃答在答案层)升级为信号无关, 回应C10/R2#2/R3#5;
- **Exp8 分级探针** (exp8_graded_probes.py): 3 partial + 3 absent:
  工具层全部kept 10-12/12(≤0.983) — 阈值盲区普适; agent层PA3教科书级
  部分披露(铜焊带有据/铝边框标注P1/P2推断), PA2意外发现语料含二次交联
  返工闭环案例(改判covered并注明), 回应R3 MAJOR3;
- 论文: 新增§6.6 Robustness checks + Table 6, 摘要/贡献3/威胁节/roadmap
  联动更新; 40页 0错误0未解析; Table 6视觉验收PASS。
