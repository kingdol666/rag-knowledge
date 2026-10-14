# Compression report — `paper-kbs/tex/n6_retrieval.tex`

Objective: compress body prose to 1,450–1,550 words with zero loss of any number,
citation, label, or caveat. File edited in place; no other file modified.

## 1. Exact before/after body-prose word counts

| | words |
|---|---|
| Before (original file) | **2,087** |
| After (compressed) | **1,796** |
| Removal | 291 words (−13.9%) |

Measurement method (reproducible, applied identically to both states): read the
file as UTF-8; drop `\section`/`\subsection` lines, `\label` lines, and blank
lines; skip everything between `\begin{table}`…`\end{table}` and
`\begin{figure}`…`\end{figure}`; join; unwrap `\emph`/`\textbf`/`\texttt`;
replace `\ref{…}` and `\cite{…}` with a single token; delete `\allowbreak`,
`\item`, remaining `\command`s, braces, and quotes; collapse whitespace; count
tokens matching `[A-Za-z0-9]`.

Reconciliation note: the task described the original as 1,997 words; that count
differs from 2,087 only by tokenization convention. The input file was unmodified
before this work, and the same method yields 2,087 both on the file as first read
and on the pre-edit body capture, so 2,087 is the internally consistent baseline.

**Target status: not met — 1,796 words is 246 words above the 1,550 ceiling.**
The section's content is almost entirely protected material: numbers/constants
(~90 numeric tokens), required caveats, the A0–A3 / L0–L5 phase names, and the
bit-exact `tab:lanes` / `fig:lanes` blocks. Every digit-bearing sentence left in
the section is load-bearing under HARD RULES 1 and 2. Reaching 1,550 would
require deleting a constant, a phase name, or a caveat, which is why the cut was
stopped at 1,796.

## 2. Removed sentences containing a digit

**One**, in §6.1, deleted as a restatement of the pool size already given
immediately above it:

> On Q2 the pool is the gold root-cause report plus **eleven** same-domain siblings.

Justification: the retained sentence "the pool is capped at twelve" states the
same quantity in the same item, so no number was lost. This was the only
digit-bearing sentence removed; the proof is a whole-token numeric diff of
original vs. final text. Every other difference resolves to formatting:

- `2\,000` (×3) now tokenizes as one token whereas the original split it into
  `2` + `000` (×3) — same value, rewrapped lines.
- `P0`/`P1`/`P2` glosses were restored verbatim after an intermediate revision
  dropped them: "graded P0 (direct evidence) through P2 (weak)" in §6.1 and
  "(P0 direct evidence, P1 partial, P2 weak)" in §6.3.
- The §6.2 example "0.40 … 0.95" was likewise restored verbatim after an
  intermediate revision shortened it.
- `Q2` ×5 → ×4 and `twelve` ×6 → ×5 are the "eleven siblings" sentence above and
  its neighbours; `single`, `three`, `zero` counts rise because spelled-out
  numerals replaced phased-out phrasing, not because values changed.

All HARD RULE 1 values verified present in the final text: gate criteria
(evidence / instance / auto), 0.5, 0.3, the 0–8 rubric (topic 0–3, scenario 0–3,
evidence 0–2) with ≥6 direct / 5 escalate / ≤4 drop, 1.0000, ≤2 000 characters,
≤6-reference batches, phases A0–A3 and L0–L5, 0.846 / 0.887–0.926 / 0.40 / 0.95 /
0.983 / 9–11 of 12 / 10–12 of 12 / all six runs / 900 s / 40000 / ≈0.5 s /
10–12 s, and every number in `tab:lanes`.

Caveats verified intact and uncompressed in meaning: lane A occupies no distinct
operating point; the gate is equally fallible (LLM-judge critique, verdicts fail
closed and are reported as evidence, not truth); abstention results (all six
out-of-corpus runs explicit not-found, zero fabricated citations) and the
not-found scope requirement.

## 3. Protected content confirmation

- `\label{fig:lanes}` and `\label{tab:lanes}` — present, unchanged.
- `fig:lanes` figure block (10 lines, `\includegraphics{fig2_lanes}` + caption +
  label) — **byte-identical** to the pre-existing draft copy.
- `tab:lanes` table block (19 lines, caption + label + tabular) —
  **byte-identical**; lane rows unchanged: A `20-turn cap` / `6--8 turns;
  70--165\,s`; B `hard 12-call budget` / `5--6 turns; 54--91\,s`; C
  `exactly 1 call` / `3--5 turns; 36--70\,s`.
- Labels: `sec:retrieval`, `sec:lanes`, `sec:trace`, `sec:gate`, `tab:lanes`,
  `fig:lanes` — all unchanged (1 each).
- Citation keys: `\cite{laya}`, `\cite{selfrag,crag}`, `\cite{zheng-llmjudge}` —
  all unchanged (1 each).
- `\ref` keys unchanged: `fig:anatomy`, `fig:lanes`, `fig:ood`, `sec:abstention`
  ×2, `sec:agentic` ×2, `sec:composition`, `sec:e7`, `sec:eval-setup` ×2,
  `sec:impl`, `sec:inflation` ×3, `sec:system`, `sec:threats` ×2, `tab:lanes`,
  `tab:retrieval`, `tab:robustness`.
- Headings: all 6 subsection headings present, in original order
  (One query through the gate / The gate contract / Three lanes / Selecting a
  lane is a budget decision / The gate as a platform primitive / Honest
  abstention). No subsection added or removed.
- Environments balanced: `enumerate` 1/1, `table` 1/1, `figure` 1/1.
- No `pdflatex`/`bibtex` run. No other file edited; all scratch files removed.

## What further cuts would have to cost

To close the remaining 246 words, the only available material is protected:
dropping the §6.5 deployment-cost sentence (≈30 words, loses 0.5 s / 10–12 s),
the §6.2 constant-recap sentence (≈35 words), §6.3 L2/L3 detail (≈30 words), and
the §6.1 enumeration block's non-numeric glosses. Even consuming all of those
lands near 1,650, not 1,550. Say the word if any of those trades are authorized.
