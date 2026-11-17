# CIKM Demo manuscript audit — 2026-11-04

## Status

The current PDF has five pages. The main paper ends with the conclusion on
page 4; the GenAI Usage Disclosure starts on page 4, continues on page 5, and
precedes the references. CIKM exempts the disclosure and references from the
four-page limit. The ACM sigconf build succeeds with no overfull boxes or
unresolved citations.

**This is a revised local draft, not a submission-ready CIKM 2026 paper.**
Author, affiliation, and email fields are placeholders. The linked
three-minute video shows an earlier 50-paper deployment using a legacy 0–8
gate, while the paper
describes a separate 100-paper ingest audit and a ten-domain evaluation. The
Demo submission deadline (June 6, 2026) and camera-ready deadline (August 23,
2026) have passed. See the [official Demo call](https://cikm2026.diag.uniroma1.it/demonstration-papers/)
and [important dates](https://cikm2026.diag.uniroma1.it/important-dates/).

## CIKM requirements

| Requirement | Status |
|---|---|
| ACM two-column sigconf | Included |
| Four-page main paper | Met; conclusion ends on page 4 |
| GenAI Usage Disclosure before references | Included; exempt from page cap |
| Three-minute video URL | Included; footage is from an older deployment |
| Single-blind author and affiliation information | Pending; placeholders remain |
| Audience, innovation, demo experience, functions, scenarios, interfaces | Covered in Sections 1–3 |
| State-of-the-art comparison | Related systems discussed; no matched dense baseline |
| Reviewer nominee | Author must nominate one in EasyChair |
| In-person presentation | Author or proxy required if accepted |

The [official rubric](https://cikm2026.diag.uniroma1.it/demonstration-papers/)
reviews novelty, R&D challenges, expected impact, timeliness, and CIKM
relevance. The revised conclusion states the operator-facing impact and its
relevance to agent workflows over shared corpora.

## Latest experiment

The paper uses the latest complete five-arm run in
review/experiment-redesign-20261101, with traces collected November 2–3,
2026: 380 traces, ten domains, 138 documents, and 879 parts. Each arm has 72
in-domain gold questions; four out-of-domain probes are separate. Gold hit is
exact-string containment in text delivered to the agent, not answer accuracy.

| Arm | Gold containment | Wilson 95% CI | Mean bytes/question | Exact McNemar p vs. A0 |
|---|---:|---:|---:|---:|
| A0: full ladder | 37/72 (51.4%) | [.401, .626] | 31.4 KB | — |
| A1: read all parts | 72/72 (100.0%) | [.949, 1.000] | 24.3 MB | <.0001 |
| A1b: global vector + gate | 42/72 (58.3%) | [.468, .690] | 28.2 KB | n/a† |
| A2: global vector, no gate | 35/72 (48.6%) | [.374, .599] | 1.6 KB | n/a† |
| A3: name-only cards + gate | 33/72 (45.8%) | [.348, .573] | 23.5 KB | .4545 |

A1 is a mechanical containment reference and makes no answer or abstention
decision. The OOD counts are evidence-gate rejections, not final-answer
abstentions: A0 returned no surviving candidates on 2/4 probes; A1b and A3
on 0/4; A1 and A2 have no applicable gate outcome. The ablation did not
generate answers. †A1b and A2 used an empty knowledge-base scope; their top-ranked
results include the A3 twin and other collections outside the evaluation
corpus. Their rates are exploratory and p-values are omitted as controlled
comparisons.

Description-based routing was correct for 72/72 questions; the name-only A3
condition was correct for 37/72. On qid-matched routing outcomes, 35 questions
were correct only with descriptions and none only without them (exact
McNemar p<.0001). This supports a routing-level effect on this test set, not
end-to-end retrieval superiority. A source-PDF audit found the exact anchors
for all 14 PDF-backed rows (whitespace-normalized); parsed/indexed part
provenance remains unaudited. The corpus is domain-skewed, and 52/72 gold
questions are automatically expanded. Source-PDF checks are recorded in
review/experiment-redesign-20261101/artifacts/pdf_anchor_audit_20261104.json;
they confirm the source strings, not the parsed/indexed part provenance.

The clean LLM-free floor is BM25 24/40 (60.0%); A0 is 23/40 (57.5%) on the
same subset. BM25 uses non-PDF 2,000-character windows, lowercase word/CJK
tokenization, Okapi k1=1.2 and b=0.75, average length 400 tokens, and top-10
packing. Dense/RRF floors are excluded because their global index returned
collections outside the evaluation corpus. Routing results are legacy cards
34/66 (52%), content summaries 72/72 (100%), and name-only cards 37/72 (51%).
Six sampled native-agent runs each included a base-targeting hint and are
described as illustrative, not unhinted routing estimates.

Metrics and the results figure are generated from saved traces by
build_fig3_experiment_results.py; the figure separates the 72 gold questions
from the four refusal probes. The corrected s6_stats.py uses gold-only
denominators, Wilson intervals, and qid-aligned pairs. A clean evaluation-
scoped dense baseline remains necessary before claiming a controlled vector
comparison.

## Corpus snapshots and demo

- **Ingest audit:** 100-paper collection, five bases, 322 parts. Content checks
  sample the first 1,000 characters per part; this is not a full semantic audit.
- **Retrieval evaluation:** ten-domain corpus, 138 documents, 879 parts.
- Three scenarios: document organization/checks; cited Gene Ontology retrieval;
  and a scoped not-found report for a fictitious paper.
- Figures 1–3: motivated failure example; architecture/workflow; experiment
  results.

## Independent review

**Independent verdict: Request changes before submission.** The author,
affiliation, and email fields remain placeholders. The newly documented
unscoped vector arms and pending PDF-anchor checks also need a clean rerun or
explicit scope-limited treatment in the final paper. Synchronizing the video
with the current demo remains a recommended improvement for any future
submission.
