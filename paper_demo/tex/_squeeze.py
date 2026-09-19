#!/usr/bin/env python3
"""Round-5 squeeze pass: apply reviewed compressions. Raw strings only."""
import sys

def sub(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if old not in s:
            print(path, 'MISSING:', old[:70]); sys.exit(1)
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print(path, 'ok')

sub('sec2_system.tex', [
  (r"""where a candidate passes iff $s \ge 6$: topic scores subject relevance, scenario
aspect coverage, and evidence the presence of concrete facts, scored by a
rubric-prompted LLM judge. Unlike retrieve-then-generate
pipelines~\cite{rag-lewis}, the gate does not trust the ranker: passes exit
early; fails are demoted with their scores attached.""",
   r"""where a candidate passes iff $s \ge 6$: topic for subject relevance, scenario
for aspect coverage, evidence for concrete facts --- rubric-prompted LLM
scoring. Unlike retrieve-then-generate pipelines~\cite{rag-lewis}, the gate
does not trust the ranker: passes exit early, fails are demoted with scores
attached."""),
  (r"""If nothing passes, Phase~2 runs a librarian fallback: scan the shelves by document
list, re-search the most promising ones. Phase~3 emits a five-section cited
answer (search paths, answer, sources, confidence, blind spots) whose citations
name base, document, part, and section path --- or the failure contract fires:
a not-found report naming what was searched and why the shelves do not answer.""",
   r"""If nothing passes, Phase~2 runs a librarian fallback (shelf scan, then
targeted re-search). Phase~3 emits a five-section cited answer (search paths,
answer, sources, confidence, blind spots) citing base, document, part, and
section path --- or the failure contract fires: a not-found report naming what
was searched and why it does not answer."""),
  (r"""every part (165 of 165; \texttt{tag\_count=165} in \texttt{graph\_stats.json}). The relation graph reports
860 typed relations (730 shared-tag,
130 vector-similarity; the snapshot's total edge count also includes structural
edges), snapshot in \texttt{graph\_stats.json}.""",
   r"""every part (165 of 165; \texttt{tag\_count=165} in \texttt{graph\_stats.json}), whose
snapshot also reports 860 typed relations (730 shared-tag, 130
vector-similarity; the total edge count additionally includes structural
edges)."""),
  (r"""heuristic. \emph{(i)~Chunk windows:}
fixed-size windows scored top positions on abstracts and reference lists; the
part split with section headers, continuation reads, and librarian routing
removed both.""",
   r"""heuristic. \emph{(i)~Chunk windows:}
fixed-size windows scored abstracts and reference lists highest; the part
split, continuation reads, and librarian routing removed both failure modes."""),
  (r"""per-base on our 10-question check), so the protocol
contracts vector-first recall with cross-base balancing; repairing it under
duplication remains future work.""",
   r"""per-base on our 10-question check), so \S\ref{sec:retrieval} contracts
vector-first recall; repair under duplication remains future work."""),
  (r"""of the embedding space, so reading replaces scoring; category bases are induced
from content rather than declared, which shapes retrieval; and failure is a
first-class output of the retrieval layer, not generator prose.""",
   r"""of the embedding space, so reading replaces scoring; bases are induced from
content, not declared; and failure is a first-class retrieval output, not
generator prose."""),
])

sub('sec3_demo.tex', [
  (r"""Point proven: the administrator writes no rules, and re-filing is a logged operation
rather than a silent move.""",
   r"""Point proven: the administrator writes no rules, and re-filing is logged, not
silent."""),
])

sub('sec4_backmatter.tex', [
  (r"""\section{Conclusion}
\sys{} organizes documents by content and verifies every retrieval by
reading: one protocol (vector-first recall, a $0$--$8$ content gate, a
librarian fallback, an honest not-found contract) with one auditable trace
per query.""",
   r"""\section{Conclusion}
\sys{} organizes documents by content and verifies every retrieval by
reading: vector-first recall, a $0$--$8$ content gate, a librarian fallback,
an honest not-found contract --- one auditable trace per query."""),
])

sub('sec4_eval.tex', [
  (r"""Track~C is the fastest end-to-end track at 12.2\,s (0.59\,s of it retrieval): it
answered 8 of 10 and abstained on the other 2 --- the answer-bearing passage was
not among its two retrieved chunks, plausibly a chunking effect; chunk ranks
were not logged, and an internal top-10 packing run abstained 0/10, so the
count is sensitive to packing depth. Our harness logs no chunk-to-document
metadata (a reproduction limitation, not dense retrieval's), so C's hits cannot
be verified programmatically.""",
   r"""Track~C is the fastest end-to-end track at 12.2\,s (0.59\,s retrieval): 8 of 10
answered, 2 abstained --- the answer-bearing passage was not among its two
retrieved chunks, plausibly a chunking effect; chunk ranks were not logged, and
an internal top-10 packing run abstained 0/10, so the count is
packing-sensitive. Our harness logs no chunk-to-document metadata (a
reproduction limitation, not dense retrieval's), so C's hits cannot be verified
programmatically."""),
  (r"""Track~B produces the most detailed answers at 78.8\,s mean (35.5--165.3\,s); its
citations stop at self-reported file names, its single recorded agent call per
question asserting rather than demonstrating its file reads. On these canonical
papers every track may partly draw on the LLM's parametric knowledge ---
uncontrolled here; the comparison isolates provenance and auditability, not raw
accuracy.""",
   r"""Track~B produces the most detailed answers at 78.8\,s mean (35.5--165.3\,s); its
citations stop at self-reported file names, its single agent call per question
asserting rather than demonstrating file reads. On canonical papers every track
may partly draw on the LLM's parametric knowledge --- uncontrolled; the
comparison isolates provenance and auditability, not accuracy."""),
])
print('ALL DONE')
