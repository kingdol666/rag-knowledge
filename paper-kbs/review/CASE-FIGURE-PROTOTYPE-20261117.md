# Case-figure prototypes: historical BQ04 and DeepSeek-R1 Q1

Status: visual design for author review; not inserted into the manuscript.

## Preferred comparison: historical BQ04

The same recorded question, “Which three independent ontologies subdivide the Gene Ontology?”, was answered by the platform agent (P), direct file tools (F) and a chunk-replica vector arm (C). Each recorded response names Molecular Function, Biological Process and Cellular Component. The platform response describes a Laya evidence check and cites a document part as well as retrieved chunks; the file response names Section 2, line 47 and the discussion at line 104; the chunk response identifies vector results in chunk indices 9 and 3. The chunk response provides source paths even though the study's document-style marker detector did not mark it as cited. Steps and paths in this illustration are reported by the answers; the arrows are schematic and should not be treated as a timestamped trace. The historical arms had different retrieval substrates. Their agreement on this one item does not establish a difference in accuracy or a causal benefit.

**Candidate caption.** Qualitative comparison of source access and answers for historical question BQ04. The platform-agent, file-tool and chunk-replica arms all named Molecular Function, Biological Process and Cellular Component and reported sources from *Primer on the Gene Ontology*. Displayed source paths and operations are summarized from the recorded answers; arrows are schematic rather than independently reconstructed tool-event sequences. The historical arms used different substrates, and this single example does not establish answer-quality superiority.

Primary record: `review/_exp_rerun_20261114/answers_historical_pfc.json`, object `BQ04`. This question and its answers were originally English; the DeepSeek-R1 Q1 alternative below translates and condenses Chinese responses.

## Evidence and wording

The directed demonstration asked (English translation): “What are DeepSeek-R1’s pass@1 scores on AIME 2024 and MATH-500?” Both recorded answers report 79.8% and 97.3%, respectively. Both cite Table 8 in part 3 and Table 3 in part 1 of the same paper; the latter also distinguishes R1-Zero's 77.9% and 95.9%. The abbreviated English answers in the prototype are translations/summaries of the Chinese responses, not original English quotations.

The two final answers describe query rewriting, vector search, Laya judging and reading source documents. The OMP answer reports 4 document parts, 52 segments scored and 40 retained; the Claude answer reports 5 parts, 62 segments scored and 58 retained. These are *answer-reported* counts and steps: the two Q1 JSON files are final-answer records rather than independent tool-event traces. The reported workflow is not proof of a catalogue-to-shelf traversal.

The prompt specified the knowledge base, the DeepSeek-R1 paper and arXiv identifier, and the sequence of tools. Both runs used retrieval; there is no no-retrieval control. This example illustrates directed retrieval and source-referenced responses, not autonomous collection selection or a causal improvement in answer accuracy. It is one qualitative case, not a statistical comparison between harnesses.

## Candidate caption for the manuscript

**Directed answer case for DeepSeek-R1 Q1.** Two harnesses received the same question, a named knowledge base and paper, and prescribed retrieval steps. Their recorded final answers describe query rewriting, vector retrieval, Laya evidence scoring and source reading, and both report pass@1 values of 79.8% for AIME 2024 and 97.3% for MATH-500. They reference Tables 8 and 3 in different parts of the same paper. The displayed answers are abbreviated English translations of Chinese responses; workflow steps and counts are taken from those responses, not independent tool-event logs. This qualitative example does not establish a retrieval-induced improvement in answer quality.

Suggested placement after the answer-level case-study paragraph in Section E6, subject to author approval and a fresh layout check. Adding a figure can change the manuscript's page count and float placement.

## Source records

- `review/experiment-redesign-20261101/artifacts/demo-20261112/qa_omp_Q1.json`
- `review/experiment-redesign-20261101/artifacts/demo-20261112/qa_claude_Q1.json`
- `review/experiment-redesign-20261101/artifacts/demo-20261112/run_pairs.py`, `QUESTIONS` and `TMPL`
- `review/experiment-redesign-20261101/artifacts/demo-20261112/QA-EVIDENCE-COMPENDIUM.md`, Part A Q1

Model-generated design prototypes can contain incorrect text; use only a separately checked vector rendering for manuscript integration.
