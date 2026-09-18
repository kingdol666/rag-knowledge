# YouTube upload sheet — QDCVR demo

Everything below is copy-paste ready. Two ways to use it:

- **Manual (2 minutes):** open <https://studio.youtube.com> → Create → Upload video,
  drop in `qdcvr-demo.mp4`, then paste the fields below and set the thumbnail to
  `thumbnail.png`.
- **API:** follow the setup at the top of `upload_youtube.py`, then
  `python upload_youtube.py --privacy unlisted` — it fills every field below
  automatically and prints the final URL.

> **Use `Unlisted`, not `Private`.** CIKM reviewers must be able to open the link
> without signing in to your account. `Unlisted` is viewable by anyone with the
> URL and does not appear in search or on your channel.

---

## Title

```
QDCVR: Content-Verified Retrieval for Knowledge-Base Management (CIKM Demo)
```

## Description

```
QDCVR is a deployable knowledge-base management platform that organizes
documents by what they say, and verifies every retrieval by reading it.

Documents are parsed to structured text and filed into a category base by
reading their content rather than their filename. Long papers are split into
parts that keep their section headers, and tags propagate from a paper to every
part. Retrieval then runs one query-driven protocol: vector-first recall, an
interpretable 0-8 content gate that scores the candidate text actually read, a
librarian fallback over the base shelves, and an explicit not-found contract
when no evidence passes. The platform is exposed to AI agents through 41 MCP
tools.

CHAPTERS
00:00 The problem: nobody can tell whether a retrieved passage answers the query
00:15 Content-based organization - 50 real papers, 5 category bases
00:47 Content-verified retrieval - the NISQ query, live
01:09 The 0-8 content gate and the five-section answer
01:36 The trap: a query for a paper that does not exist
01:54 The honest not-found report
02:19 Agent-native surface and benchmark evidence
02:46 Visit the booth

WHAT IS ON SCREEN
The console footage is a real recording of the running deployment. The NISQ
query returns quantum-physics__1801.00862 (part 1 of 3, 0.62 fused BM25+vector
similarity); the fabricated-paper query returns the BERT paper, which really
does contain the training-epoch strings described in the narration. The two
text cards reproduce, verbatim, a recorded benchmark answer and a recorded
not-found report. Nothing is mocked.

MEASURED (50 real papers, 3.8M characters, 165 indexed documents)
- gold document ranked first in 10/10 questions, 1.6 s mean vector recall
- final content-gate scores 6-8/8, with both librarian rescues succeeding
- three out-of-corpus probes scored 1/8, 1/8 and 0/8 - all returned not-found

Code and run artifacts: https://github.com/kingdol/rag-knowledge
```

## Tags

```
RAG, retrieval-augmented generation, knowledge base, content verification,
information retrieval, MCP, Model Context Protocol, document management,
CIKM demo, vector search, BM25, hallucination
```

## Settings

| Field | Value |
|---|---|
| Visibility | **Unlisted** |
| Category | Science & Technology |
| Language | English |
| Audience | *Not made for kids* |
| Thumbnail | `thumbnail.png` (1280×720, 398 KB — under the 2 MB limit) |
| Playlist | none needed |
| Comments | your choice; not required by CIKM |

## After uploading

Put the resulting URL (e.g. `https://youtu.be/XXXXXXXXXXX`) into all three places
in the paper, replacing the placeholder `https://example.org/qdcvr-demo`:

- `paper_demo/tex/sec0_abstract.tex` (last line of the abstract)
- `paper_demo/tex/sec3_demo.tex` (Demo setup paragraph)
- `paper_demo/tex/sec4_backmatter.tex` (Conclusion)

Then rebuild:

```bash
cd paper_demo/tex
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Sanity check that no placeholder survives anywhere:

```bash
grep -rn "example.org/qdcvr-demo" paper_demo/tex/     # should print nothing
```
