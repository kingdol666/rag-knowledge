# Three-Track Experiment (deterministic regrade)

Run: `rerun5-20261017` · question set: `qa_questions_e5_corrected.json` · 100-paper corpus

## Arm-level results

| Arm | Gold-ID coverage | Strict keyword | Alias-aware keyword | Strict pass | Alias-aware pass | Citation markers | Chunk markers | Mean wall s | Mean cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A2 | 10/10 | 7/10 | 9/10 | 7/10 | 9/10 | 9/10 | 8/10 | 37.7 | 0.6721 |
| B | 10/10 | 7/10 | 9/10 | 7/10 | 9/10 | 9/10 | 0/10 | 15.2 | 0.3767 |
| C | 10/10 | 8/10 | 10/10 | 8/10 | 10/10 | 9/10 | 8/10 | 19.6 | 0.5236 |

## Per-question grades

| QID | Arm | Gold-ID | Strict keywords | Alias-aware keywords | Citation marker | Strict pass | Alias-aware pass | Wall s | Tools |
|---|---|---|---:|---:|---|---|---|---:|---:|
| BQ01 | A2 | yes | 3/3 | 3/3 | yes (Table 1, part 1 of 2, part 2 of 2) | yes | yes | 42.5 | 8 |
| BQ02 | A2 | yes | 2/2 | 2/2 | yes (part 1 of 3, part 1 of 4) | yes | yes | 48.8 | 8 |
| BQ03 | A2 | yes | 2/2 | 2/2 | yes (Table 1, Table 4, part 1 of 8) | yes | yes | 37.7 | 8 |
| BQ04 | A2 | yes | 3/3 | 3/3 | yes (part 1 of 2) | yes | yes | 32.7 | 8 |
| BQ05 | A2 | yes | 1/1 | 1/1 | no | yes | yes | 19.8 | 7 |
| BQ06 | A2 | yes | 1/2 | 2/2 | yes (part 1 of 3) | no | yes | 42.3 | 7 |
| BQ07 | A2 | yes | 2/2 | 2/2 | yes (Section 5, part 1 of 4) | yes | yes | 40.7 | 9 |
| BQ08 | A2 | yes | 1/2 | 1/2 | yes (Section 4, Tables 1, part 1 of 2) | no | no | 40.7 | 9 |
| BQ09 | A2 | yes | 1/2 | 2/2 | yes (Sections I, Tables II, part 1 of 2) | no | yes | 25.0 | 8 |
| BQ10 | A2 | yes | 2/2 | 2/2 | yes (Section 3.3, Sections 3.1, part 1 of 3) | yes | yes | 46.7 | 10 |
| BQ01 | B | yes | 3/3 | 3/3 | yes (Section 1, Section 3.2, Section 3.2.1) | yes | yes | 21.0 | 8 |
| BQ02 | B | yes | 2/2 | 2/2 | yes (part 1 of 3, part 2 of 3, §4.1) | yes | yes | 12.5 | 6 |
| BQ03 | B | yes | 2/2 | 2/2 | yes (Table 1, Table 4, Table 6) | yes | yes | 11.5 | 5 |
| BQ04 | B | yes | 3/3 | 3/3 | yes (part 1 of 2) | yes | yes | 11.4 | 5 |
| BQ05 | B | yes | 1/1 | 1/1 | no | yes | yes | 16.9 | 4 |
| BQ06 | B | yes | 1/2 | 2/2 | yes (part 1 of 3, part 2 of 3, §3) | no | yes | 14.6 | 7 |
| BQ07 | B | yes | 2/2 | 2/2 | yes (Section 5, part 1 of 4) | yes | yes | 12.6 | 6 |
| BQ08 | B | yes | 1/2 | 1/2 | yes (part 1 of 2, part 2 of 2, §1) | no | no | 13.2 | 4 |
| BQ09 | B | yes | 1/2 | 2/2 | yes (Tables II, part 1 of 2, part 2 of 2) | no | yes | 11.3 | 4 |
| BQ10 | B | yes | 2/2 | 2/2 | yes (Table 2, part 1 of 3, part 2 of 3) | yes | yes | 27.1 | 10 |
| BQ01 | C | yes | 3/3 | 3/3 | yes (part 1 of 2, part 2 of 2) | yes | yes | 22.8 | 6 |
| BQ02 | C | yes | 2/2 | 2/2 | yes (part 1 of 3, part 1 of 4) | yes | yes | 16.6 | 5 |
| BQ03 | C | yes | 2/2 | 2/2 | yes (part 1 of 8, part 2 of 8) | yes | yes | 17.2 | 5 |
| BQ04 | C | yes | 3/3 | 3/3 | yes (part 1 of 2) | yes | yes | 13.8 | 5 |
| BQ05 | C | yes | 1/1 | 1/1 | no | yes | yes | 19.6 | 5 |
| BQ06 | C | yes | 1/2 | 2/2 | yes (part 1 of 3, part 2 of 3) | no | yes | 17.0 | 5 |
| BQ07 | C | yes | 2/2 | 2/2 | yes (part 1 of 4) | yes | yes | 16.4 | 5 |
| BQ08 | C | yes | 2/2 | 2/2 | yes (part 1 of 2, part 2 of 2) | yes | yes | 25.0 | 7 |
| BQ09 | C | yes | 2/2 | 2/2 | yes (part 1 of 2, part 2 of 2) | yes | yes | 22.6 | 7 |
| BQ10 | C | yes | 1/2 | 2/2 | yes (part 1 of 3, part 2 of 3, part 3 of 3) | no | yes | 25.2 | 8 |

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