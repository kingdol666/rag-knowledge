# Splice note (2026-09-21)

track_b_BQ06.json in this directory was replaced after the fact.
Original run returned "API Error: 402 Insufficient Balance" from the model
provider (infrastructure failure — b_BQ07..10 in the same session succeeded).
The replacement is a re-run of the identical question text on track b with
the same harness/model, produced in experiment_chat_20260921-120429.
The original artifact is preserved as track_b_BQ06.json.402-original.
Everything else in this run is untouched.

## Second splice attempt — REVERTED (2026-09-21)

track_a_BQ06.json originally produced a truncated answer (297 chars, cut
mid-sentence after fully successful retrieval — 9 tools, 0 denials;
substance correct as far as it goes). A re-run
(experiment_chat_20260921-120731) was tried as a replacement but itself hit
the intermittent tool-namespace allowlist denial (7 denials -> honest
refusal). The splice was REVERTED: track_a_BQ06.json is the original
in-run artifact, truncation documented here and in the comparison report.
The re-run refusal is preserved in experiment_chat_20260921-120731 as
further evidence that the alias-namespace denial is intermittent and
driven by the model's tool-name choice, not by uncertainty or absence of
the answer in the corpus.
