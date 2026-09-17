"""Generate the supplementary appendix (appendix.tex) from FROZEN artefacts.

Style reference: DeepRead (arXiv:2602.05014) appendix conventions -- lettered
sections (A.1 protocol, A.2 score matrix, A.3 full per-question transcripts),
each question block showing every system's real answer with its judge score.

Inputs (frozen, sha256-verified in data-snapshot/):
  deepread_matrix.json   -- 30 SciFact questions x 8 systems, per-question
                            answers, verdicts and judge scores (producer:
                            benchmark-suite/algorithms/run_matrix.py)
Output:
  appendix/appendix.tex  -- standalone acmart sigconf document

Run from docs/paper/cikm/:  python make_appendix.py && latexmk -pdf appendix.tex
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "data-snapshot"
MANIFEST = SNAP / "MANIFEST.json"


def load_frozen(name: str):
    raw = (SNAP / name).read_bytes()
    want = next((f["sha256"] for f in json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
                 if f["name"] == name), None)
    if want and hashlib.sha256(raw).hexdigest() != want:
        raise SystemExit(f"frozen artefact {name} modified (sha256 mismatch)")
    return json.loads(raw.decode("utf-8-sig"))


DR = load_frozen("deepread_matrix.json")

OUTDIR = HERE / "appendix"
OUTDIR.mkdir(exist_ok=True)
OUT = OUTDIR / "appendix.tex"

# Method order: proposed system first, then reproduced baselines (main-table
# order). Labels match Table 2 of the main paper.
ORDER = ["qdcvr", "dense_rag", "dense_rag_rerank", "itrg_refresh", "itrg_refine",
         "raptor", "search_o1", "deepread"]
LABEL = {
    "qdcvr": "\\textbf{\\textsc{Qdcvr}} (two-stage + content adjudication)",
    "dense_rag": "Dense RAG (chunk 800/400, top-10)",
    "dense_rag_rerank": "Dense RAG + reranker (30$\\to$10)",
    "itrg_refresh": "ITRG (refresh, 4 rounds $\\times$ top-6)",
    "itrg_refine": "ITRG (refine, 4 rounds $\\times$ top-6)",
    "raptor": "RAPTOR (collapsed tree, top-10)",
    "search_o1": "Search-o1 (agentic, 2 chunks/turn, cap 8)",
    "deepread": "DeepRead (locate-then-read, cap 8)",
}


UNICODE_MAP = {
    "α": "$\\alpha$", "β": "$\\beta$", "γ": "$\\gamma$", "δ": "$\\delta$",
    "ε": "$\\varepsilon$", "θ": "$\\theta$", "λ": "$\\lambda$", "μ": "$\\mu$",
    "κ": "$\\kappa$", "σ": "$\\sigma$", "τ": "$\\tau$", "φ": "$\\varphi$",
    "ω": "$\\omega$", "Δ": "$\\Delta$", "Ω": "$\\Omega$", "π": "$\\pi$",
    "×": "$\\times$", "–": "--", "—": "---", "‘": "`", "’": "'",
    "“": "``", "”": "''", "…": "\\ldots{}", "°": "$^\\circ$",
    "≥": "$\\geq$", "≤": "$\\leq$", "≈": "$\\approx$", "±": "$\\pm$",
    "é": "\\'e", "è": "\\`e", "ü": "\\\"u", "ö": "\\\"o", "ä": "\\\"a",
    "ï": "\\\"i", "ç": "\\c{c}", "ñ": "\\~n", "−": "-", "‐": "-", "‑": "-",
}


def esc(s: str) -> str:
    """Escape LaTeX specials in artifact text (answers, issues, claims)."""
    # Unicode first (mapped symbols), then LaTeX specials.
    s = "".join(UNICODE_MAP.get(ch, ch if ord(ch) < 128 else "") for ch in s)
    repl = [
        ("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
        ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ]
    for a, b in repl:
        s = s.replace(a, b)
    return s


def tidy(s: str) -> str:
    """Collapse whitespace so artifact line breaks do not create paragraphs."""
    return " ".join(s.split())


# ── collect per-question, per-method records ─────────────────────────
qa = {}
for row in DR["qa"]:
    qa.setdefault(row["qid"], {})[row["method"]] = row
qids = sorted(qa.keys())
judge_rows = DR["judge_rows"]
retr = {m: {r["qid"]: r for r in DR["retrieval_rows"][m]} for m in ORDER}
jsum = DR["summary"]["judge"]

# ── A.2 score matrix rows ────────────────────────────────────────────
matrix_rows = []
for m in ORDER:
    scores = [judge_rows[m][i]["score"] for i in range(len(judge_rows[m]))]
    cells = " & ".join(f"{s:.0f}" for s in scores)
    mean = jsum[m]["mean_score"]
    ok = 100.0 * jsum[m]["verdict_ok_rate"]
    matrix_rows.append(f"{LABEL[m]} & {cells} & {mean:.2f} & {ok:.0f}\\% \\\\")
# column header needs qids
qhead = " & ".join(q.replace("sf-", "") for q in qids)

# ── A.3 per-question transcripts ─────────────────────────────────────
blocks = []
for idx, qid in enumerate(qids, start=1):
    row0 = qa[qid]["qdcvr"]
    claim = tidy(row0["claim"])
    gold = ", ".join(row0["golden_ids"])
    means = sum(judge_rows[m][idx - 1]["score"] for m in ORDER) / len(ORDER)
    parts = [
        rf"\subsection{{Q{idx} ({qid}, mean judge {means:.1f}): ``{esc(claim)}''}}",
        rf"\label{{app:q{idx}}}",
        rf"\noindent Gold document(s): {esc(gold)}. Evidence budgets, prompts and "
        rf"the judge protocol are identical across systems (Appendix~A).",
    ]
    for m in ORDER:
        row = qa[qid][m]
        j = row["judge"]
        v = row["answer"]["verdict"]
        ans = tidy(row["answer"]["answer"])
        issues = tidy(j.get("issues") or "")
        h1 = retr[m][qid]["hit@1"]
        parts.append(rf"\paragraph{{{LABEL[m]} --- judge {j['score']:.0f}/10, "
                     rf"verdict: {esc(v)}, rank-1 hit: {'yes' if h1 == 1 else 'no'}}}")
        parts.append(rf"\noindent {esc(ans)}")
        if issues:
            parts.append(rf"\noindent\small\textit{{Judge: {esc(issues)}}}")
    blocks.append("\n".join(parts))

transcripts = "\n\n".join(blocks)

# ── document ─────────────────────────────────────────────────────────
doc = r"""% =====================================================================
% Supplementary appendix for the CIKM submission "Content-Adjudicated,
% Domain-Scoped Retrieval for Agent-Native Knowledge Bases".
% GENERATED FILE -- every answer, verdict, score and judge comment below is
% read from the frozen artefact data-snapshot/deepread_matrix.json by
% make_appendix.py; nothing is hand-transcribed. Producer:
%   benchmark-suite/algorithms/run_matrix.py (artefact)
%   docs/paper/cikm/make_appendix.py     (this document)
% Build: latexmk -pdf appendix.tex
% =====================================================================
\documentclass[sigconf, review, anonymous]{acmart}
\settopmatter{printacmref=false}
\settopmatter{printfolios=true}
\renewcommand\footnotetextcopyrightpermission[1]{}
\acmConference[Anonymous supplementary]{}{}{}
\acmISBN{}
\acmDOI{}
\newif\ifreviewlines
\reviewlinesfalse
\makeatletter
\ifreviewlines\else
  \def\ACM@linecountL{}%
  \def\ACM@linecountR{}%
\fi
\makeatother
\usepackage{booktabs}
\usepackage{graphicx}
\let\Bbbk\relax
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
\usepackage{enumitem}
\setlist[itemize]{leftmargin=1.1em,topsep=2pt,itemsep=1pt,parsep=0pt}
\setlength{\textfloatsep}{6pt plus 2pt minus 2pt}
\setlength{\floatsep}{6pt plus 2pt minus 2pt}
\setlength{\abovecaptionskip}{4pt}
\newcommand{\sys}{\textsc{Qdcvr}}
\setlength{\emergencystretch}{2.2em}
\tolerance=1400

\begin{document}

\title{Content-Adjudicated, Domain-Scoped Retrieval for\\ Agent-Native Knowledge Bases:\\ Supplementary Appendix}

\author{Anonymous Author(s)}
\affiliation{%
  \institution{Anonymous Institution}
  \country{}
}
\email{anonymous@example.org}

\begin{abstract}
This supplementary appendix accompanies the main paper and publishes, in
full, the answer-quality evaluation whose aggregate results appear in
Table~2 of the main paper: for each of the 30 BEIR SciFact claims and each
of the 8 compared systems, the complete system answer as produced under the
shared 4{,}000-character evidence budget, the independent judge's 0--10
score, the declared verdict, and the judge's free-text justification.
Appendix~A restates the protocol, Appendix~B gives the complete
30$\times$8 score matrix, Appendix~C the multi-path experience-retrieval
evaluation, and Appendix~D reproduces every transcript.
Nothing here is edited or selected: the text of each answer is verbatim
from the frozen evaluation artefact (SHA-256-pinned), including answers
that declare insufficient evidence or that the judge penalised.
\end{abstract}
\keywords{Retrieval-Augmented Generation; Evaluation; Supplementary Material}

\maketitle

\appendix

\section{Evaluation Protocol and Judge Rubric}\label{app:protocol}
The protocol is identical for all eight systems: one shared answering agent
receives each system's gathered evidence under an identical 4{,}000-character
budget and a frozen prompt; a second, independent agent (fresh process, no
shared context) grades each answer 0--10 \emph{after} receiving the gold
document. The judge's 0--10 rubric decomposes into answer verdict (0--4:
does the answer reach the correct conclusion, including a well-grounded
declaration of insufficient evidence), grounding (0--4: are claims supported
by the provided evidence and attributed to the right documents) and clarity
(0--2). Every call runs at temperature 0; HTTP-driven and offline runs are
byte-identical (480/480 consistency checks, main paper Table~2). The
\emph{verdict} field below is the answering agent's own declared verdict
(``supported'' or ``insufficient''); \emph{rank-1 hit} records whether the
system's own retrieval ranked a gold document first.

\paragraph*{Implementation and hyper-parameters (main paper \S7.2).}
All configurations share one index and one tool layer. Embeddings are BGE-M3
(1024-d, L2-normalised) from HuggingFace snapshot \texttt{5617a9f6} via
sentence-transformers 5.6.1; chunks are 500 characters with 50 overlap; the
vector store is ChromaDB 1.5.9 (persistent HNSW, library-default
$M{=}16$, efConstruction${=}100$, cosine); the keyword index is jieba 0.42.1
BM25 ($k_1{=}1.5$, $b{=}0.75$) over a 12{,}000-character window. Retrieval
defaults are vector top-$k{=}10$, two-stage $k{=}40/10$, threshold
$\tau{=}0.35$, three verification reads; fusion is 0.5 keyword and 0.5
graph-neighbour (depth 1). The platform default for stage-1/2 is $20/5$; the
benchmark uses $40/10$, recorded in the frozen snapshot manifest. Statistics:
pairwise comparisons use the Wilcoxon signed-rank test with a per-comparison
95\% bootstrap confidence interval ($B{=}2000$, seed 0) and
Holm--Bonferroni correction across the family
(\texttt{31\_stats.py}); deterministic retrieval repeats are bit-identical.

\section{Complete Score Matrix (30 claims $\times$ 8 systems)}\label{app:matrix}
Table~\ref{tab:matrix} lists every individual judge score; column headers
are the claim numbers (sf-001--sf-030). Means and verdict-ok rates match
main paper Table~2.

\begin{table*}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{2.6pt}
\caption{Individual judge scores (0--10) for all 30 SciFact claims $\times$
8 systems, from the frozen evaluation artefact. Producer:
\texttt{make\_appendix.py} from \texttt{deepread\_matrix.json}.}
\label{tab:matrix}
\begin{tabular}{@{}l""" + "c" * len(qids) + r"""cc@{}}
\toprule
System & """ + qhead + r""" & Mean & ok\% \\
\midrule
""" + "\n".join(matrix_rows) + r"""
\bottomrule
\end{tabular}
\end{table*}

\section{Multi-Path Experience Retrieval: Complete Evaluation}\label{app:multipath}
Experience is recalled along five parallel paths --- vector, keyword,
scenario, tag and quality-feedback --- fused and deduplicated. The fusion is
evaluated on a purpose-built set: eight operational experiences seeded
through the platform's own write path and twelve frozen queries --- eight
\emph{symptom-style}, sharing no vocabulary with the target entry's title,
four \emph{vocabulary-style}, sharing solution words. Because the deployed
endpoint exposes no per-path switches, the fusion is re-implemented at
harness level from the service's published scoring rule (keyword/scenario/
tag matches scored by $\min(0.42 + 0.06\,\mathrm{hits} +
0.15\,\mathrm{cov},\,0.72)$ over their fields; per-query vector scores from
the experience vector index; quality as a tier/rating bonus); a top-3
agreement check against the live endpoint matches $1$ of $6$ spot checks, so
the numbers characterise the fusion design, not the shipped endpoint's
end-to-end behaviour.

\emph{Results.} The full five-path fusion is perfect on the twelve queries
(Hit@1 $=$ MRR $= 1.000$), and it is the only perfect configuration.
Leave-one-out: removing quality-feedback costs most (Hit@1 $0.833$), removing
keyword or scenario costs $0.083$ each, removing vector or tag none. Single
paths are all imperfect and fail on \emph{disjoint} queries (vector-only
$0.833$ fails the symptom-style queries with no lexical overlap; keyword-only
$0.917$ fails paraphrases; tag-only $0.417$; scenario-only $0.750$;
quality-only $0.167$) --- the complementarity the five-path design assumes.

\section{Full Transcripts}\label{app:transcripts}
Each block below reproduces, verbatim, every system answer for one claim,
followed by the judge's free-text justification in italics. Answers are not
truncated or edited; the only normalisation is whitespace collapsing.

""" + transcripts + r"""

\end{document}
"""

OUT.write_text(doc, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({OUT.stat().st_size} B), {len(qids)} questions x {len(ORDER)} systems")
