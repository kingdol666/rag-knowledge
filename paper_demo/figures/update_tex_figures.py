"""Synchronize manuscript captions, alt text, and the table with the
vector figures and the filtered 72-question result analysis.
"""
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "tex" / "main.tex"


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + replacement + text[b:]


text = PAPER.read_text(encoding="utf-8")
text = replace_section(
    text, r"\Description{Two storyboard rows", r"\label{fig:teaser}",
    r"""\Description{The query asks which training epochs were used in the
fictitious paper Spectral Tuning for Low-Resource Odor Recognition. One
card identifies BERT fine-tuning recipes as a near-miss, not evidence
about that paper. Separately, the trace records a top vector similarity
of 0.52. The second card shows the scoped not-found outcome, with ten
generic two-stage hits, twelve weak title-token matches, and no relevant
segment for the judgment engine to grade. No epoch value is returned.}
""",
)
text = replace_section(
    text, r"\caption{Platform operations", r"\label{fig:arch}",
    r"""\caption{The platform keeps collection management and retrieval on
one inspectable address model. The diagram connects its interfaces and
shared stores to the gated organize workflow and layered, fail-closed
retrieval.}
\Description{The top row links the web console, ragctl CLI, MCP agents,
and packaged skills to a hierarchical knowledge base addressed as base,
document, part, and section. Markdown content and tree and metadata
registries share ChromaDB BGE-M3 vectors and an optional Neo4j document
graph. Supported operations include base and document CRUD, tags, search,
graphs, experiences, and SOUL personas. The lower organize lane parses
and checks source files, deduplicates and splits them, routes them by
content, adds tags and five-dimension descriptions, then verifies indexes
with checks C1--C9. The retrieve lane rewrites a query, navigates catalogs
and descriptions, recalls candidates with vector search or exact scans,
retains evidence segments that pass the local Laya gate at 0.5 or above,
reads them by address, and returns a cited answer or scoped not-found.}
""",
)
text = replace_section(
    text, r"\caption{Five-arm ablation", r"\label{fig:ablation}",
    r"""\caption{Full-corpus reading contains all 72 gold strings, but
reads about 775$\times$ as much text per question as the platform lane.
(a) Exact-string containment on 72 in-domain questions with Wilson 95\%
confidence intervals; labels show mean bytes read. (b) Routing accuracy
for legacy, content-summarized, and name-only catalog cards. (c) Correct
refusals on four out-of-domain probes; the mechanical full-read arm makes
no answer decision.}
\Description{Three panels. Panel (a) compares five arms on 72 in-domain
gold questions: the platform ladder gets 37/72 (51.4 percent), faithful
full reading gets 72/72 (100 percent), global vector recall gets 42/72
(58.3 percent), no evidence gate gets 35/72 (48.6 percent), and no
descriptions gets 33/72 (45.8 percent). Whiskers show Wilson 95 percent
confidence intervals; labels below bars show mean bytes read per gold
question: 31.4 KB, 24.3 MB, 28.2 KB, 1.6 KB, and 23.5 KB. Panel (b)
shows routing accuracy: legacy cards 34/66 (52 percent),
content-summarized cards 72/72 (100 percent), and name-only cards 37/72
(51 percent). Panel (c) shows correct non-answers on four out-of-domain
probes: the platform ladder 2/4; full reading is not applicable because
it makes no answer decision; global vector, no gate, and no descriptions
each score 0/4.}
""",
)
table_start = r"\begin{table}[t]" + chr(10) + r"\caption{Five-arm ablation"
table = r"""\begin{table}[t]
\caption{Five-arm ablation on 72 in-domain gold questions, with four
out-of-domain refusal probes reported separately. Gold hit means exact
containment of the gold string in packed text, not answer correctness.}
\label{tab:ablation}
\footnotesize
\setlength{\tabcolsep}{2.7pt}
\begin{tabular}{@{}lccccc@{}}
\toprule
\textbf{Arm} & \textbf{Hit/72} & \textbf{Wilson CI} & \textbf{Refus./4} &
\textbf{Read/q} & \textbf{$p$} \\
\midrule
A0 ladder          & 51.4\% (37) & [.401,.626] & 2/4 & 31.4\,KB    & --- \\
A1 full-read       & 100.0\% (72) & [.949,1.000] & n/a & 24.3\,MB & $<$.0001 \\
A1b global vector  & 58.3\% (42) & [.468,.690] & 0/4 & 28.2\,KB    & .267 \\
A2 no gate         & 48.6\% (35) & [.374,.599] & 0/4 & 1.6\,KB     & .851 \\
A3 no descriptions & 45.8\% (33) & [.348,.573] & 0/4 & 23.5\,KB    & .455 \\
\midrule
BM25 floor$^\dagger$ & 60.0\% (24/40) & n/a & n/a & --- & n/a \\
\bottomrule
\end{tabular}
\\[-2pt]\parbox{\columnwidth}{\scriptsize $p$: exact paired McNemar
test vs. A0 on the 72 gold questions, uncorrected. $^\dagger$BM25 uses a
40-question subset; A0 scores 23/40 on that subset. Dense/RRF floors are
omitted because their global index included non-evaluation collections.}
\end{table}
"""
text = replace_section(text, table_start, r"\input{sec4_eval}", table)
PAPER.write_text(text, encoding="utf-8", newline="")
print(f"Updated {PAPER}")
