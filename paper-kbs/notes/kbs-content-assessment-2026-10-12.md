# Content-design assessment — is the system explained clearly? (2026-10-12)

Scope: `paper-kbs/tex/main2.tex` and its 17 `\input` files (11 sections + appendix),
judged against two questions the author asked: *is the content design excellent?*
and *does it explain the whole system clearly?*
Method: one read-only audit agent read every build file plus the evidence base and
the raw experiment artifacts (`paper-kbs/experiments/results/*.json`,
`benchmark-suite/results/*`, `review/*`), traced each claim to its source, and
returned a prioritised edit list. Findings were then verified line by line before
any edit was made (several claims were stale — see "claims checked and dismissed").

## Verdict

| dimension | verdict | basis |
|---|---|---|
| System architecture explained end to end | **yes, after today's fixes** | acquisition → organisation → retrieval → verification gate → agent lanes → experience → operations, each with a measured stage |
| Design decisions justified rather than asserted | **yes for the load-bearing ones** | the gate's placement, the two-stage tool's non-lane status, the honesty contract, free-form vs typed relations, the tree-vs-path governance choice |
| Evaluation completeness | **improving; now includes the newest campaign** | E1–E8 groups, with the 2026-10-12 three-channel campaign integrated today |
| Reproducibility of numbers | **yes** | every headline number carries an artifact path; two independent re-aggregations reproduced the retrieval table exactly |
| Honesty about limits | **unusually strong** | negative and null results are kept in the body, not buried: the gate ablation's null, the partitioning null, the unattributed 21-paper gap, the judge-inflation finding |

## What was genuinely unclear, and what was done today

1. **The BM25→dense two-stage tool had no home section.** It was named once and then
   denied a lane. Now: a subsection in §6 with its signature and stage budgets, why
   it is a scored configuration rather than a lane (stage 2 returns unverified chunk
   text), and its measured Hit@5 1.00 at 77 ms.
2. **"Nine configurations" was never defined.** The retrieval table now opens with all
   nine named and sourced, including the two derived rows that replay one logged run.
3. **The gate's acceptance threshold looked like a contradiction** (0.5 stated, a
   different rubric scored elsewhere). The rule now states its projection
   (0.5 general / 0.3 enumeration on the rubric's [0,1] scale) and concedes that on
   the evaluated corpus no threshold ever fired.
4. **"100/100 papers parsed" sat next to "21 never retrievable".** The acquisition
   table now shows the funnel (100 submitted → 100 parsed → 91 recorded → 79
   retrievable) and both the prose and caption say the gap is unattributed.
5. **A citation pointed at the wrong section** (`sec:system` → `sec:org-experience`).
6. **A dangling term** ("meditation") is now defined at first use, and the eval note
   that the experience evidence is one scenario rather than a scaled study is stated
   where the mechanism is described, not only where it is evaluated.
7. **The evidence-group count** ("seven") did not match the eight groups the paper
   actually reports; corrected in the introduction and the evaluation preamble.
8. **A path typo** (`.tree-fs.yml`) that a careful reader would have caught.

## Claims checked and dismissed (recorded so they are not re-investigated)

- `tab:appendixranks` is defined (`paper-kbs/tex/tab_appendix_ranks.tex:7`) and the
  built PDF contains no `??`.
- `tab:org-ops` has exactly one active definition; the older copy was superseded when
  the table moved to the appendix.
- The absent-tier latency triplet (73.3 / 113.5 / 47.9 s) **is** traceable to
  `paper-kbs/experiments/results/exp8b_absent_agent.json`; the audit's doubt was
  unfounded.

## Deliberate omissions (a decision, not an oversight)

- **No MCP interface table.** The 95 tools are described by group; a full signature
  table is the kind of material this journal's 20-page cap punishes. It is the first
  candidate for the supplementary document.
- **The data model stays in §3** rather than moving into §5; the move would have
  duplicated the table and cost a page.
- **Further compression of §8 was not applied.** Its 4.9k words exceed the internal
  3.0k budget, but every paragraph removed would delete evidence the review had just
  asked to keep. Length is handled by the review-variant measurement and by moving
  the full campaign matrix to the supplement.

## What a KBS reviewer will still ask for (honest list)

- Evidence on more than one deployed instance and more than one judge model.
- A second corpus in a different domain family (the current second corpus shares the
  first corpus's family).
- Merge/split, experience decay, crash durability and authentication: **no test
  evidence exists at all** for these, and the paper says so.
- The 21-paper acquisition gap attributed to a cause, which the artifacts cannot
  support today.
