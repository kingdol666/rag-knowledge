# Three-Track Experiment (deterministic regrade)

Run: `run-20261013T094350Z-5f9faac` · question set: `qa_questions.json` · 100-paper corpus

## Arm-level results

| Arm | Gold-ID coverage | Strict keyword | Alias-aware keyword | Strict pass | Alias-aware pass | Citation markers | Chunk markers | Mean wall s | Mean cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A2 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 9/10 | 5/10 | 52.6 | 0.7110 |
| B | 10/10 | 9/10 | 10/10 | 9/10 | 10/10 | 7/10 | 0/10 | 22.2 | 0.4867 |
| C | 10/10 | 9/10 | 10/10 | 9/10 | 10/10 | 2/10 | 7/10 | 24.5 | 0.5269 |

## Per-question grades

| QID | Arm | Gold-ID | Strict keywords | Alias-aware keywords | Citation marker | Strict pass | Alias-aware pass | Wall s | Tools |
|---|---|---|---:|---:|---|---|---|---:|---:|
| BQ01 | A2 | yes | 3/3 | 3/3 | yes (Table 1, part 1 of 2, §2) | yes | yes | 55.5 | 5 |
| BQ02 | A2 | yes | 2/2 | 2/2 | yes (part 1 of 3, part 1 of 4, §4.1) | yes | yes | 35.8 | 5 |
| BQ03 | A2 | yes | 2/2 | 2/2 | yes (Section 3.1.1, Table 4, part 1 of 8) | yes | yes | 75.3 | 10 |
| BQ04 | A2 | yes | 3/3 | 3/3 | yes (part 1 of 2) | yes | yes | 25.6 | 4 |
| BQ05 | A2 | yes | 1/1 | 1/1 | no | yes | yes | 35.6 | 5 |
| BQ06 | A2 | yes | 1/1 | 1/1 | yes (part 1 of 3, part 2 of 3, §3) | yes | yes | 97.4 | 10 |
| BQ07 | A2 | yes | 2/2 | 2/2 | yes (part 1 of 4) | yes | yes | 25.3 | 3 |
| BQ08 | A2 | yes | 2/2 | 2/2 | yes (part 1 of 2, part 2 of 2) | yes | yes | 77.0 | 6 |
| BQ09 | A2 | yes | 2/2 | 2/2 | yes (part 1 of 2, part 2 of 2) | yes | yes | 43.9 | 5 |
| BQ10 | A2 | yes | 2/2 | 2/2 | yes (part 1 of 3, part 2 of 3, part 3 of 3) | yes | yes | 54.7 | 7 |
| BQ01 | B | yes | 3/3 | 3/3 | no | yes | yes | 24.9 | 6 |
| BQ02 | B | yes | 2/2 | 2/2 | yes (§4.1, §4.2, §6.4) | yes | yes | 24.2 | 7 |
| BQ03 | B | yes | 2/2 | 2/2 | yes (Table 4) | yes | yes | 20.3 | 8 |
| BQ04 | B | yes | 3/3 | 3/3 | yes (Section 2) | yes | yes | 12.0 | 5 |
| BQ05 | B | yes | 1/1 | 1/1 | no | yes | yes | 19.6 | 4 |
| BQ06 | B | yes | 1/1 | 1/1 | yes (§2, §3, §4.1) | yes | yes | 29.9 | 10 |
| BQ07 | B | yes | 2/2 | 2/2 | yes (Section 1, Section 4) | yes | yes | 11.6 | 4 |
| BQ08 | B | yes | 2/2 | 2/2 | no | yes | yes | 20.2 | 4 |
| BQ09 | B | yes | 1/2 | 2/2 | yes (§I, §III-C, §III-D) | no | yes | 20.4 | 4 |
| BQ10 | B | yes | 2/2 | 2/2 | yes (Table 2, §1, §3.1) | yes | yes | 38.6 | 12 |
| BQ01 | C | yes | 3/3 | 3/3 | yes (Table 1, §3.2, §3.2.1) | yes | yes | 34.1 | 5 |
| BQ02 | C | yes | 2/2 | 2/2 | no | yes | yes | 21.4 | 2 |
| BQ03 | C | yes | 2/2 | 2/2 | yes (Table 4) | yes | yes | 18.6 | 2 |
| BQ04 | C | yes | 3/3 | 3/3 | no | yes | yes | 17.0 | 2 |
| BQ05 | C | yes | 1/1 | 1/1 | no | yes | yes | 30.0 | 4 |
| BQ06 | C | yes | 1/1 | 1/1 | no | yes | yes | 48.6 | 11 |
| BQ07 | C | yes | 2/2 | 2/2 | no | yes | yes | 11.2 | 2 |
| BQ08 | C | yes | 2/2 | 2/2 | no | yes | yes | 19.7 | 2 |
| BQ09 | C | yes | 2/2 | 2/2 | no | yes | yes | 23.3 | 3 |
| BQ10 | C | yes | 1/2 | 2/2 | no | no | yes | 21.3 | 4 |

## Scoring definitions

- Gold-ID coverage means the gold identifier occurs in the answer or recorded retrieval trace; it is provenance/document contact, not semantic grounding.
- Strict keyword coverage uses the original exact lexical keywords and the 60% threshold.
- Alias-aware keyword coverage additionally accepts the explicit aliases defined for BQ09 and BQ10; it remains lexical coverage, not a factuality score.
- Citation-marker hits are syntactic locator-pattern matches. They do not test whether a locator resolves or supports an answer claim.
- Chunk identifiers are counted separately and are not document citation markers.
  Citation regex: `part/section/table markers present: \bparts?\s+\d+\s+of\s+\d+ | \b(?:section|sections|table|tables|appendix|appendices)\s+(?:\d+(?:\.\d+)*(?:-[A-Z0-9]+)?|[IVXLCDM]+(?:-[A-Z0-9]+)?)\b | §\s*(?:\d+(?:\.\d+)*(?:-[A-Z0-9]+)?|[IVXLCDM]+(?:-[A-Z0-9]+)?)\b`
  Chunk regex: `dense chunk references (reported separately, NOT counted in the paper's cited numbers): \bchunk[_ ]?(?:index|id)?\s*\d+`
- This report regrades immutable saved answers and traces; raw run records are unchanged.

Verbatim answers and run monitoring are in `SUMMARY.md`.