#!/usr/bin/env python3
"""Final compression pass — cut ~190 words across sections. Numbers untouched."""
import io

def sub(path, old, new):
    s = io.open(path, encoding="utf-8").read()
    if old not in s:
        print("MISS", path, repr(old[:50]))
        return
    io.open(path, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok", path, "-%d words" % (len(old.split()) - len(new.split())))

# 1) Abstract
sub("sec0_abstract.tex",
r"""Institutional document stores are indexed by filename and folder conventions, and
retrieval stacks chunk them into flat bags of passages, so nobody can tell whether
a retrieved passage actually answers a query. We present \sys{}, a deployable
knowledge-base management platform that organizes documents by their content and
verifies every retrieval by reading it. Ingestion parses documents into structured
text and files each one into a category base by reading its content rather than its
filename; long papers are split into parts that keep their section headers, and tags
propagate from a document to all of its parts. Retrieval runs one query-driven
protocol: vector-first recall, an interpretable $0$--$8$ content gate that scores the
candidate text actually read, a librarian fallback over the base shelves, and an
explicit not-found contract when no evidence passes. The platform is exposed to AI
agents through 41 \texttt{kb\_*} Model Context Protocol tools. On 50 real papers
organized into 5 category bases (165 indexed documents over 3.8\,M characters, all
50 parse-verified), a scripted 10-question keyword regression passes 9/10, and the
live skill run answers 10/10 on target with gate scores of 6--8/8, two librarian
rescues, and top-1 gold-document recall of 10/10 at $1.6$\,s mean vector recall;
three out-of-corpus probes return not-found reports instead of fabricated answers.
The demonstration lets attendees ingest, organize, query, and inspect every trace
live. Demo video:
\url{https://github.com/kingdol666/rag-knowledge/blob/master/paper_demo/video/qdcvr-demo.mp4}.""",
r"""Institutional document stores are indexed by filename and folder conventions, and
retrieval stacks chunk them into flat bags of passages, so nobody can tell whether a
retrieved passage actually answers a query. We present \sys{}, a deployable
knowledge-base management platform that organizes documents by content and verifies
every retrieval by reading it. Ingestion parses documents into structured text, files
each into a category base by content rather than filename, splits long papers into
parts that keep section headers, and propagates tags to every part. Retrieval runs
one query-driven protocol: vector-first recall, an interpretable $0$--$8$ content
gate that scores the candidate text actually read, a librarian fallback over the
base shelves, and an explicit not-found contract when no evidence passes. AI agents
operate the platform through 41 \texttt{kb\_*} Model Context Protocol tools. On 50
real papers in 5 category bases (165 indexed documents, 3.8\,M characters, all
parse-verified), a scripted 10-question keyword regression passes 9/10 and the live
skill run answers 10/10 on target with gate scores 6--8/8, two librarian rescues,
top-1 gold-document recall of 10/10 at $1.6$\,s mean recall; three out-of-corpus
probes return not-found reports instead of fabricated answers. The demonstration
lets attendees ingest, organize, query, and inspect every trace live. Demo video:
\url{https://github.com/kingdol666/rag-knowledge/blob/master/paper_demo/video/qdcvr-demo.mp4}.""")

# 2) §1 opener
sub("sec1_intro.tex",
r"""Consider a research group holding 50 PDFs: evaluation reports, survey papers,
hardware manuals. An administrator must decide which category each document belongs
to, which tags apply, and, when someone asks ``what does X conclude?'', how the
system proves it fetched the right text. Filename conventions and hand-built folder
trees answer none of this: a folder records where a file was saved, never what the
file says. Retrieval-augmented generation (RAG) promises answers over such stores
but inherits their disorganization.""",
r"""Consider a research group holding 50 PDFs: evaluation reports, surveys, manuals.
An administrator must decide which category each document belongs to, which tags
apply, and, when someone asks ``what does X conclude?'', how the system proves it
fetched the right text. Filename conventions and hand-built folder trees answer none
of this: a folder records where a file was saved, never what it says.
Retrieval-augmented generation (RAG) promises answers over such stores but inherits
their disorganization.""")

# 3) §2.3 压缩
sub("sec2_system.tex",
r"""The \texttt{kb-mcp} server exposes 41 \texttt{kb\_*} MCP tools~\cite{mcp} (94 in
total) covering CRUD, offset-addressed reads and writes, tags, search, graph
queries, and an experience lifecycle that distils resolved
question--answer logs into reusable entries. A packaged skill encodes
the protocol of \S\ref{sec:retrieval} so agents reproduce it step by step instead
of improvising a RAG loop; the benchmark's Track~A is that skill. Deployment is
one command (\texttt{ragctl}); embeddings and parsing run
locally, and answer generation uses any configured LLM
(${\sim}20$\,s cold start, excluding model downloads).""",
r"""The \texttt{kb-mcp} server exposes 41 \texttt{kb\_*} MCP tools~\cite{mcp} (94 in
total) covering CRUD, offset-addressed reads and writes, tags, search, graph
queries, and an experience lifecycle that distils resolved question--answer logs
into reusable entries. A packaged skill encodes the protocol of
\S\ref{sec:retrieval} so agents reproduce it step by step instead of improvising a
RAG loop; the benchmark's Track~A is that skill. Deployment is one command
(\texttt{ragctl}); embeddings and parsing run locally, and answer generation uses
any configured LLM (${\sim}20$\,s cold start, excluding model downloads).""")

# 4) §3 Scenario 1 压缩
sub("sec3_demo.tex",
r"""The attendee drops a PDF into the console upload panel. \sys{} parses it into
structured Markdown, splits the long document into parts that each carry their
section-path header, reads the text, and files it into the recommended category
base with tags propagated to every part --- no dialog asks the attendee to pick
a folder, define a schema, or author a routing rule. The console lists five
content-classified bases of 72, 43, 32, 12 and 6 indexed documents beside the
three reproduction indices built by chunking rather than by reading. Point
proven: the administrator writes no rules, and re-filing is a logged operation
rather than a silent move.""",
r"""The attendee drops a PDF into the console upload panel. \sys{} parses it into
structured Markdown, splits it into parts that carry their section-path header,
reads the text, and files it into the recommended category base with tags
propagated to every part --- no dialog asks the attendee to pick a folder, define
a schema, or author a routing rule. The console lists five content-classified
bases of 72, 43, 32, 12 and 6 documents beside three reproduction indices built
by chunking rather than reading. Point proven: the administrator writes no rules,
and re-filing is a logged operation, not a silent move.""")

# 5) §4 Setup 压缩
sub("sec4_eval.tex",
r"""Ten content-grounded questions are answered by three tracks over the same
ingested corpora: \emph{Track~A}, the \sys{} protocol of \S\ref{sec:retrieval}
executed end to end by its packaged skill; \emph{Track~B}, a bare agent with file
tools over the 50 exported markdown papers and no index, one fresh session per
question; and \emph{Track~C}, dense retrieval over 800-character fixed chunks
packed into a 4{,}000-character evidence window for a single LLM call.
Figure~\ref{fig:threeway} shows the per-track scorecards and latencies;
Table~\ref{tab:threeway} reports the aggregates. Every answer in every track is
recorded verbatim as a repository artifact.""",
r"""Ten content-grounded questions are answered by three tracks over the same
corpora: \emph{Track~A}, the \sys{} protocol of \S\ref{sec:retrieval} executed by
its packaged skill; \emph{Track~B}, a bare agent with file tools over the 50
exported markdown papers, no index, one fresh session per question; and
\emph{Track~C}, dense retrieval over 800-character fixed chunks packed into a
4{,}000-character evidence window for one LLM call. Figure~\ref{fig:threeway}
shows the scorecards and latencies; Table~\ref{tab:threeway} the aggregates.
Every answer in every track is recorded verbatim as a repository artifact.""")
print("done")
