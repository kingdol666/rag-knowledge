# KBS 20-page revision record — `paper-kbs/tex/journal_20p/`

Date: 2026-10-13 (revision session). Target: Knowledge-Based Systems (Elsevier,
ISSN 0950-7051), submission site `https://submit.elsevier.com/KNOSYS`,
Editorial Manager acronym `KNOSYS`, single-anonymized review, APC USD 3,240,
Impact Factor 8.0 (2025), CiteScore 13.7 (2025).

This note records what was changed in this revision and why. It is the durable
companion to the build; the paper itself is the artifact.

---

## 1. Structural repairs (the build was incomplete before this revision)

| # | Defect found | Repair |
|---|---|---|
| 1 | `n_back.tex` was **not `\input` by `main_20p.tex`**, so the appendix, all declarations and the mandated generative-AI statement never reached the PDF. | `\input{n_back}` added after `\input{n11_conclusion}` and before the bibliography block in `main_20p.tex`. |
| 2 | Four declarations (CRediT, competing interest, funding, data availability) existed **twice**, in `n11_conclusion.tex` and `n_back.tex`, with different wording and different placeholder author names. | Deleted from `n11_conclusion.tex`; `n_back.tex` rewritten as the single source of truth. |
| 3 | Declarations were in the wrong order for Elsevier. | `n_back.tex` reordered: CRediT → Declaration of competing interest → Funding → Ethics statement → Data availability → Acknowledgments → `\appendix` → per-question appendix → **Declaration of generative AI…** last, immediately before the reference list (KBS guide wording). |
| 4 | `tab_appendix_ranks.tex` **did not exist** in `journal_20p/`. The build died with `! LaTeX Error: File 'tab_appendix_ranks.tex' not found.` once `n_back` was wired. | Copied from `paper-kbs/tex/tab_appendix_ranks.tex`; in the copy the caption's backtick quoting became `\texttt{--}` and the float became `table*` (as a single-column float its 10-column tabular gave `Overfull \hbox (32.60803pt too wide)`). |
| 5 | None of the four appendix tables was cited in the text (KBS rule: "Cite all tables in the manuscript text"). | Intro paragraph of `n_appendix_tables.tex` rewritten to cite `tab:datamodel`, `tab:acq-crosslang`, `tab:questions`, `tab:org-ops` with their sections. |
| 6 | Three figure references had been mechanically stripped during an earlier compression pass, leaving the prose fragments `(the ablation)`, `(the ablationa)`, `(the ablationb)`. | Resolved in `n8c_eval.tex` — see §3. |

## 2. Dangling references

- `n8c_eval.tex`: `(Section~\ref{sec:discussion}, L6)` → `(Section~\ref{sec:discussion})`. `n9_discussion.tex` has no numbered lessons L1–L6, so `L6` was unresolvable.
- `n_back.tex` referenced `Fig.~\ref{fig:marginvariants}(b)`, a figure that no longer existed anywhere in the build. Resolved by restoring the figure (§3).
- `n8a_eval.tex` section roadmap listed "E1–E8 … eight groups" and **omitted E5b** (`sec:sysarms`), which exists in `n8c_eval.tex`. Roadmap rewritten as an accurate reading guide naming every subsection.
- Header comments in `n8c_eval.tex` pointed at `n11_conclusion.tex` for the data-availability text; retargeted to `n_back.tex`.

## 3. Garbled fragments — root cause and disposition

Root cause: during an earlier prose-compression pass, three `Figure~\ref{...}`
citations were deleted but their surrounding parentheses were left behind. The
generator source confirms the fragments are not abbreviations:

- line 434 `…actually binds (the ablation).` → parenthetical **deleted**.
- line 448 `(QK01 $0\to5$, QK03 $3\to0$; the ablationa; sign test $p = 1.0$, $n = 10$)` → **deleted**.
- line 464 `…yields surviving candidates (the ablationb), so…` → **deleted**.
- The fragment at 434 was deliberately **not** replaced by a `fig:marginvariants` citation: that panel shows the verdict-role attribution of E4, not the E8 gate/partition ablation, and citing it there would misrepresent it.

## 4. Evidence restored (9 figures, matching the fit-audit target)

Four figures existed in `figs/` but were referenced by no section:

| figure | disposition |
|---|---|
| `fig4_inflation` | **Restored** into E6, `n8c_eval.tex`, immediately after the "Same-domain score inflation" paragraph and cited in it. |
| `fig6_margin_variants` | **Restored** into E4, `n8b_eval.tex`, at the foot of the file; cited twice (panel (b) in "The central result is the verdict's role", panel (a) in "Thresholds and margins"). |
| `fig5_e2e` | Not restored — its content duplicates `fig11_three_arms` panel (b). |
| `fig9_robustness` | Not restored — no current section discusses the paraphrase grid or NLI panels it carries. |

Both restored captions were written **from the generator source**
(`paper-kbs/figures/figures.py`), never from the stale caption text preserved at
`paper-kbs/tex/journal/n8b_eval.tex:282-289`, which describes a different
two-panel figure and would have mislabelled the plot.

`fig:ood` was defined but never cited; a `(Figure~\ref{fig:ood})` was added to
the sentence ending "the 0.5 threshold never fired as a refusal".

## 5. Story line (the core of the request)

- **`n1_intro.tex`** — the gap and the contributions were rewritten. New gap sentence: "No single stage owns the property the user actually needs---that the sentence being cited is supported by the document being cited---and so no stage is accountable for it." The three contracts are now a displayed `enumerate` with **named** items: *Content governs placement*, *Content governs admission*, *Absence is reported*. Contributions re-titled to lead with novelty.
- **`n2_related.tex`** — added `\subsection{Research gap}` (`sec:gap`) stating explicitly what is not a system today, and a new full-width `table*` `tab:positioning` (Strand / Representative work / What it optimizes / What it leaves to the deployment) with a final `QDCVR (this work)` row. Every cell is derived from citations already in the section; **no new reference was invented**. Column spec uses `>{\raggedright\arraybackslash}p{...}` to stop hyphenation of "Knowl-edge man-agement".
- **`n3_overview.tex`** — "Requirements and principles" replaced by `\subsection{Design principles: three enforceable contracts}`, naming the organising idea ("content, not metadata and not rank, is the governing object at every boundary a stored document crosses") and giving each contract's *Mechanism* and *Check*. The architecture subsection now says where the three contracts sit on the path.
- **`highlights.tex`** — "Today's tests separate…" (a deictic unfit for print) became "Deployment tests separate document recall from answer-level citation behavior" (77 chars, inside the 85-char ceiling).

## 6. Float fixes

- `fig:inflation` placed at `width=\columnwidth`, not the designed `0.5\textwidth`: `0.5\textwidth` evaluates to 261 pt in this two-column layout against a `\columnwidth` of about 252 pt, and produced `Overfull \hbox (9.0pt too wide)`.
- `fig:marginvariants` placed at `width=\textwidth` inside `figure*`.
- `tab:positioning`: justified `p`-columns were hyphenating across mid-word breaks; switched to ragged-right.

## 7. Build

The stale `main_20p.pdf` is locked by an external process (a PDF viewer), so the
build uses a separate jobname. From `paper-kbs/tex/journal_20p/`:

```
pdflatex -interaction=nonstopmode -jobname=qdcvr_kbs main_20p.tex
bibtex qdcvr_kbs
pdflatex -interaction=nonstopmode -jobname=qdcvr_kbs main_20p.tex
pdflatex -interaction=nonstopmode -jobname=qdcvr_kbs main_20p.tex
```

Do **not** use `-halt-on-error` while diagnosing: it aborts at the first error.
Toolchain: `C:\texlive\2025\bin\windows\{pdflatex,bibtex,pdftoppm,pdftotext}.exe`.

Final build: **22 pages, 0 Overfull \hbox, 0 undefined references, 0 undefined
citations, 0 LaTeX errors.** `qdcvr_kbs.pdf` is the build;
`final_20p.pdf` is a byte-identical copy under the older name. The stale
`main_20p.pdf` (821,299 B, 2026-10-13 18:01) could not be overwritten because it
is held open by a PDF viewer — close the viewer and re-run to restore the
canonical name.

## 8. Residual items from the static module sweep

`latex-paper-en` modules `check_figures.py`, `analyze_grammar.py`,
`check_pseudocode.py` and `deai_check.py` (default settings) return **no
findings**; `deai_check.py --analyze` ranks the abstract at 3.8 % and the
evaluation chapters at 2.6 %, both low.

Still open, in priority order:

1. **Em-dash density.** 90 `---` in the sources, but 80 of them are in the
   three evaluation files (`n8c_eval.tex` 43, `n8b_eval.tex` 21,
   `n8a_eval.tex` 16). The Introduction, Related work, System overview, back
   matter and Conclusion between them carry 8. Most instances are being used
   where a colon, semicolon or comma is the conventional academic choice.
   Not converted in this revision: each instance needs a judgement call
   (many sit after a complete clause and take a colon; some introduce a
   coordinated clause and take a comma), and a mechanical substitution would
   damage the prose. Recommended as a separate focused pass.
2. **Long sentences.** 88 module hits, concentrated at `n8c_eval.tex:417` and
   `n8c_eval.tex:443` (E8 ablation prose, up to 127 words). Four of the 88 are
   measurement artifacts, not prose: they are `tabular` blocks
   (`n2_related.tex:93`, `n8c_eval.tex:33`, `n8c_eval.tex:158`,
   `tab_appendix_ranks.tex:8`).
3. **Decimal precision in three tables** (`tab:e4-matrix`, `tab:e5-cost`,
   `tab:acq-crosslang`). Cosmetic; forcing uniform precision would destroy real
   information (0.9559 and 0.9402 need four places where 1.0 needs one).
4. **Six uncited bibliography entries** — `comaikg`, `jieba`, `rrpdg` in
   `refs.bib`; `ji-kg-survey-2022`, `wang-kg-embedding-2017`, `xu-spfresh-2023`
   in `refs_new_verified.bib`. BibTeX already omits them from the `.bbl`;
   removing them is hygiene only.

### Module findings assessed as tool artifacts, not paper defects

- `analyze_logic.py` and `analyze_literature.py` both report **Major / P1 "no
  research gap at the end of Related Work"** anchored at `n2_related.tex:98-108`.
  Both are wrong: the gap subsection exists at `n2_related.tex:60-81`, but the
  `table*` float for `tab:positioning` was appended after it in the source, so
  the file *ends* with a table. The rendered PDF reads correctly (Research gap,
  then Section 3, with Table 1 floated to the top of page 3). Reordering the
  float above the gap subsection would silence the check at no reader benefit.
- `verify_bib.py` reports `@dpr: Missing required field 'author'` — the field is
  present at `refs.bib:14`; the parser chokes on the `{\u{g}}` escape.
- `analyze_experiment.py` reports a **Critical / P0** "guarantee-style claim" at
  `n7_implementation.tex:35`; the sentence is "…but does not establish privacy,
  access-control or multi-host deployment guarantees", i.e. it *denies* the
  guarantee. Its "Major / P1 performance claim lacks a baseline" at
  `n7_implementation.tex:33` points at a hardware description.
- `analyze_abstract.py` reports Background and Conclusion as MISSING on a
  248-word abstract that contains both, and assigns Methods and Results to the
  same sentence. The word-limit check passes.
- `optimize_title.py` moved from 85/100 to 90/100 after the title was expanded;
  its one remaining note is the `QDCVR:` acronym, which is the system's name.

## 9. Open items (cannot be automated)

KBS requires, and only the authors can supply:

1. Author names, affiliations, full postal addresses, corresponding author and published e-mail.
2. ORCID iDs.
3. CRediT roles attributed to real authors (currently `Author Name` / `Co-author Name` placeholders).
4. Funding: the mandated no-grant sentence is in place; replace if a grant exists.
5. Declaration of competing interests **exported from the Elsevier declarations tool** as `.doc/.docx` and uploaded separately — the in-text statement is not a substitute.
6. Cover letter and suggested reviewers.
7. Separate high-resolution figure files for upload (the `figs/` PDFs and 300 dpi PNGs are prepared but must be uploaded individually).
8. `paper-kbs/notes/kbs-requirements-compliance-2026-10-12.md` needs the corrections found by the live re-verification of 2026-10-12 (highlights are "encouraged" not required; the generative-AI section title is the recommended form, not byte-exact; the LaTeX Manuscript item type covers nine extensions and "no subfolders" is unverified; the 10 MB/7 MB figure limit is Elsevier-wide advice with no KBS-specific number; `doubleblind` is an inference from single-anonymized review, not a quoted prohibition; the artwork numeric specs have moved to the `/about/policies-and-standards/author/artwork-and-media-instructions/` pages).
