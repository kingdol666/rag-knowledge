# 图题、图注和表题（论文原文）

编号和页码来自本次双栏 PDF。以下保留原始 LaTeX 写法；插图、变量与引用以论文源文件为准。

## 图 1（第 6 页）

源文件：`n3_overview.tex`

```latex
Management levels and an illustrative catalogue-first query path. The levels maintain collections, documents and segments over shared state; the query path may use a subset of these tiers, and evidence judging is optional.
```

## 图 2（第 7 页）

源文件：`n3_overview.tex`

```latex
HMRS service architecture. The browser reaches the Nuxt server; agent tools access the MCP server, which calls service APIs and reads local state. The platform functions operate over files, registries and indices; the evidence gate is optional.
```

## 图 3（第 8 页）

源文件：`n3_overview.tex`

```latex
Ingestion and query workflows over shared state. An agent can select a collection from document content; indexing depends on the entry point. At query time, candidate gathering may be followed by optional segment scoring. A threshold-passing score does not guarantee support; execution failures are distinguished from a completed search without support.
```

## 图 4（第 13 页）

源文件：`n8a_eval.tex`

```latex
Paired scripted route audit (72 in-domain questions). (a) Gold-domain
choice: A0 72/72, A3 37/72 (Wilson 95\% intervals; McNemar
$p=5.82\times10^{-11}$). (b) Exact-string containment: A0/A3 Laya evidence
packs and A1 concatenated text from all 879 parts (37/72, 33/72, 72/72; Wilson
intervals; paired $p=0.4545$ for A0--A3 and $p=5.82\times10^{-11}$ for
A1--A0). (c) Trace-recorded text bytes on a symmetric-log axis linear through
1 KB, including 11 zero-byte A3 cases; (d) tool wall-clock on a log axis.
Boxes show IQR, whiskers 5th--95th percentiles, dots questions and diamonds
means. A0/A3 bytes sum candidate-snippet and evidence-pack text (possible
overlap); A1 sums document-read responses. Tool time excludes answer
generation. A1 is a script, not an answering agent; the A3 fallback is
unlogged. These are routing, substring and tool-cost diagnostics, not answer
quality or an isolated description effect.
```

## 图 5（第 15 页）

源文件：`n8a_eval.tex`

```latex
Content-layer optimisation arms on the 72 in-domain questions of the
ten-domain corpus. (a)~Blue circles and Wilson 95\% intervals show the
11 November frozen aggregate of gold-string containment; orange triangles
show later records on the same questions. The frozen aggregate combines runs
on different dates; A3 was added separately to the later record. Read-all is
incomplete in the later record. The dashed line is the frozen tiered baseline A0. A0f
(full-window judge) and A0h (plus a chunk-window union) improve on A0; PD
(precise per-document, no navigation) is the ladder-versus-precise contrast
(A0h vs PD: 7--1 discordant, McNemar $p=0.0703$); A0h vs the scoped flat union
A1b is 13--0 ($p=0.00024$). A1b, A2 (no gate) and A3 (name-only cards) are the
flat and ablated controls; read-all is a mechanical upper bound, not an agent
baseline. A1b uses a reference-mode judge and can use the gold domain in
reference resolution; A0h and PD differ in both routing and chunk union.
(b)~Frozen-aggregate mean total tool calls and trace-recorded kilobytes per
question; bytes can include overlapping text.
```

## 图 6（第 16 页）

源文件：`n8b_eval.tex`

```latex
Tool-layer retrieval quality on the two corpora of
Table~\ref{tab:retrieval}. (a)~The 42-document industrial demonstration corpus
over 16 gold-annotated questions: Hit@5, Recall@5 and MRR@5 for the seven
logged configurations. (b)~Hit@5 on the 79 retrievable arXiv papers over ten
questions. On the industrial corpus the evaluated, retired HMRS-Hybrid ordering is the
weakest configuration on all three metrics, while BM25 and RRF reach 1.00
Hit@5; on the arXiv corpus every configuration except Graph reaches 0.90.
The two derived replays (Judge-as-filter, RRF-fuse) are reported in
Table~\ref{tab:retrieval} and Fig.~S4 rather than
duplicated here. Values are read from the frozen result artefacts
(\protect\path{exp1\_summary.json}, \protect\path{exp10\_papers\_toollayer.json}).
```

## 图 7（第 19 页）

源文件：`n8c_eval.tex`

```latex
Recorded Laya scores for 191 candidates from sixteen hybrid runs:
17 in-pool golds and 174 non-golds. All recorded values exceed the dashed
0.5 threshold; one additional Q14 fusion candidate has no recorded score and
its status is unknown. Group medians (0.88 gold, 0.86 non-gold) are not
distinguishable by a two-sided Mann--Whitney test ($p=0.26$). Horizontal
jitter is for legibility.
```

## 表 1（第 5 页）

源文件：`n2_related.tex`

```latex
Positioning. Each strand addresses part of the path from stored
document to answer. HMRS studies a knowledge document management workflow
combining automatic collection assignment, content-informed acquisition,
server-side checks when invoked, and answer-layer reporting; the evaluation
measures selected components and boundaries in
Section~\ref{sec:eval}.
```

## 表 2（第 6 页）

源文件：`n3_overview.tex`

```latex
Management levels and the tiered access path. Each level names the
objects it maintains, the operations that write them, the state that describes
them, the tier that reads them, and the measurement that exercises it.
The selected access policy determines which tiers are visited; a pinned
search can bypass catalogue navigation.
```

## 表 3（第 7 页）

源文件：`n3_overview.tex`

```latex
Management functions, the enforcement or workflow check associated
with each, and the evaluation that exercises it. The table separates API/MCP
controls from agent procedures and campaign audits; semantic choices such as
which collection owns a document remain workflow decisions and are measured,
not enforced.
```

## 表 4（第 10 页）

源文件：`n6_retrieval.tex`

```latex
Access policies over the tiered path. Modes differ in how candidate collections and documents are selected.
The hybrid row describes an experimental composition.
```

## 表 5（第 17 页）

源文件：`n8b_eval.tex`

```latex
Tool-layer retrieval on the 42-document industrial demonstration corpus
(mean over 16 gold-annotated questions; top-5 document lists; latency per
call, warmed). The paraphrase column re-asks those sixteen questions in
different words (\protect\path{paper-kbs/experiments/results/exp6_paraphrase.json});
block~(b) repeats the Hit@5 measurement on a second corpus, the 79 retrievable
papers of the 100-paper arXiv ingestion, over ten questions.
```

## 表 6（第 17 页）

源文件：`n8c_eval.tex`

```latex
Answer quality per question and per interface in the original grid
(30 answer cells from \protect\path{run-20261013T094350Z-5f9faac}); the
controlled replication on a common substrate is reported in the text and adds
no column. Every answer passes the gold-ID
check, so coverage is 10/10 in each arm and the column is not repeated. Each
arm column gives strict keyword coverage (\yes\ or $\times$), alias-aware coverage,
and the number of recognised citation markers (m). Strict coverage is a
majority rule on the annotated terms, not an all-terms rule. The column m counts
markers; the prose's 9/10, 7/10 and 2/10 count answers with at least one.
Markers do not establish that a cited section exists or supports the sentence
citing it.
```
