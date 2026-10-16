# Industrial-corpus substitute recipe (2026-10-16)

Companion note for the KBS submission (`paper-kbs/tex/journal_20p/`). The
deployed industrial corpus used for Table 2 / Tab. 5 cannot be redistributed
for contractual reasons. This note records what can be released, what a
substitute corpus must reproduce for the reported effects to be re-testable,
and a small illustrative synthetic sample. Nothing here recovers the original
corpus text; the recipe is a construction plan for an independent analogue.

## 1. What is already released (no substitute needed)

Part of the same-pool diagnostic is re-derivable from released artifacts
alone, because it consumes logged results rather than the corpus text:

| artifact | contents | re-derives |
|---|---|---|
| `paper-kbs/experiments/results/exp1_retrieval.json` | 112 tool-layer rows; the 16 `qdcvr_hybrid` rows carry all candidate scores in `judge_scores.all` (191 recorded scores, Q14 has 11) and the post-judge `ranked_top5` | the judge-ordering row of Table 2 (Hit@5 0.4375, Recall@5 0.4062, MRR 0.2260) and the score census (every recorded score > 0.5, minimum 0.589) |
| `paper-kbs/experiments/kbcommon.py` (`QUESTIONS`) | the 16 gold questions with `gold_doc_substrings` and fact markers | gold/non-gold labels for every logged candidate |
| `paper-kbs/experiments/exp6_loo_margin.py` | relative-margin sweep over the same logged scores; makes no service calls | Fig. 6(a) |
| `paper-kbs/experiments/exp7_second_signal.py`, `exp9_span_nli.py` | independent NLI replays over the same 191 (query, candidate) pairs | the second-checkpoint failure |
| `paper-kbs/experiments/results/exp5_q2_anatomy.json` | the raw hybrid response for Q2, including the pre-judge fusion list (`merge.judged_candidates`) and the verdict scores (`cut.kept`) | the anatomy of Fig. 9: fusion order rank 1, judge order miss, filter order rank 1 |

Re-derivation of the judged row (repository root; reproduces 0.4375 on the
released artefact):

```python
import json, sys
sys.path.insert(0, 'paper-kbs/experiments')
from kbcommon import QUESTIONS, gold_hit, norm_path
rows = json.load(open('paper-kbs/experiments/results/exp1_retrieval.json'))['rows']
Q = {q['qid']: q for q in QUESTIONS}
ok = []
for r in rows:
    if r.get('method') != 'qdcvr_hybrid' or 'judge_scores' not in r:
        continue
    order = sorted(r['judge_scores']['all'], key=lambda p: -r['judge_scores']['all'][p])
    hits, _ = gold_hit([norm_path(p) for p in order], Q[r['qid']]['gold_doc_substrings'], 5)
    ok.append(hits > 0)
print(sum(ok) / len(ok))   # 0.4375
```

One caveat on `exp5_judge_filter.py`: the released script re-runs the hybrid
call against the live platform (`McpClient`) and only then derives the three
orderings, so it cannot be re-executed without the corpus and a running
service. The *fusion-order* rows (filter / fusion-only) therefore depend on
the logged pre-judge fusion lists, which are released for the anatomy query
above and retained per question in the campaign records and archive tarballs
for the remaining fifteen questions. The judged row, which carries the
headline number, needs none of that.

## 2. What a substitute corpus must reproduce

The published claim that needs a corpus is the *ordering* effect under
confuser density, so a substitute needs the confuser structure, not the
content. Construction parameters, taken from the manuscript's own description
of the deployed corpus:

1. **Scale.** 42 documents across five libraries; one library holds the
   confuser family of 20 equipment-telemetry reports.
2. **Family structure.** The 20 telemetry reports share a filename prefix,
   section skeleton, and vocabulary; their numeric fields differ in one or two
   values (temperature set-points, alarm limits, run identifiers). Target
   pairwise similarity in the 0.90--0.975 band reported for the near-duplicate
   candidate groups in the arXiv campaign.
3. **Gold placement.** The 20-member telemetry family carries four gold
   questions (the surviving telemetry cluster: the melt-temperature excursion
   verdict, the staircase excitation design, the FT regression after the P0
   optimization, and the multimodal diagnosis). A second confuser cluster of
   three near-duplicate incident reports carries one more (the
   post-compensation verification question).
4. **Questions.** 16 questions, each naming one or two gold documents by a
   *unique* filename fragment plus one to three fact markers; one question
   (Q16) deliberately includes a token also present in its gold filename, so a
   filename-ranking retriever can match it without reading content.
5. **Interface.** Ingest the substitute through the platform's own ingest
   path, then run the tool-layer configurations of Table 2 against it; the
   derived replays of Section 8.5 need only the logged pools and scores.

## 3. Illustrative synthetic sample

Three synthetic documents (English) showing the family structure; they are
fabricated for illustration and are not derived from any customer document.

```text
line-telemetry-run13-staircase.md   (gold: staircase excitation design)
line-telemetry-run14-step.md        (confuser)
line-telemetry-run15-ramp.md        (confuser)
```

```markdown
# Line 13 telemetry run 13 — staircase excitation

Section 1. Excitation design. The set-point was raised in six steps of
5 degC at 120 s intervals; the staircase was chosen over a single step to
separate the dead time from the rise time.

Section 2. Observations. Melt temperature settled within +/- 0.6 degC of each
plateau after two time constants; no overshoot exceeded 1.2 degC.

Section 3. Verdict. Dead-loop ruled out; the 206->180 degC excursion is
attributed to sensor lag on channel 2.
```

```markdown
# Line 13 telemetry run 14 — single step excitation

Section 1. Excitation design. The set-point was raised in one step of
15 degC and held for 720 s.

Section 2. Observations. Melt temperature settled within +/- 1.1 degC; one
overshoot of 2.4 degC was recorded at t+90 s.

Section 3. Verdict. Inconclusive; the single step cannot separate dead time
from rise time, so no root cause is assigned.
```

```markdown
# Line 13 telemetry run 15 — ramp excitation

Section 1. Excitation design. The set-point was ramped at 0.05 degC/s over
300 s.

Section 2. Observations. Melt temperature lagged the ramp by 18 s throughout;
no plateau exists in this run.

Section 3. Verdict. Dead-loop ruled out for this run; sensor lag not
assessed because the profile provides no plateau.
```

A substitute question set built on this family reproduces the failure mode of
Section 8.6: the confusers share the gold's prefix, section skeleton and
vocabulary, so a verifier that scores segments on topical overlap assigns them
scores in the same band as the gold, and using that score to reorder a fused
candidate list moves the gold out of the top-5 read window.

## 4. Limits of this recipe

- It reproduces *structure*, not the deployed numbers; agreement with the
  published Hit@5 values is not implied.
- The original candidate pools, per-candidate scores and gold labels are the
  release of record for the published numbers; this recipe only enables an
  independent end-to-end re-test on a de-identified analogue.
