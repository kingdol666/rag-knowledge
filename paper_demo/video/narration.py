#!/usr/bin/env python3
"""Narration script for the QDCVR demonstration video (CIKM Demo, ~3 minutes).

Every figure spoken here traces to benchmark-suite/results/ artifacts or to what
the recorded session shows on screen:

  BQ02 gate 7/8, vector recall 1.51 s   -> skill_track_evidence.json / BENCHMARK-30000chunk
  10/10 gold ranked first, 1.6 s mean   -> skill_track_evidence.json
  probes 1/8, 1/8, 0/8 all not-found    -> honest_failure_probe.json
  41 kb_* MCP tools                     -> kb-mcp/server.py
  50 papers / 3.8M chars / 5 bases      -> ingest_report.json, ingest_survey.json

`visual` is resolved by build_video.py:
  clip:<name>   an excerpt of the recorded browser session
  card:<name>   a generated card carrying real artifact text
  title / title_end
"""
from __future__ import annotations

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+18%"
PAUSE_AFTER_MS = 420          # silence appended to each segment

SEGMENTS = [
    dict(
        id="s1_opening", visual="title", min_seconds=15,
        text=(
            "Every organization sits on a pile of documents, and nobody can tell "
            "whether a retrieved passage actually answers the question. "
            "QDCVR is a deployable knowledge-base platform that organizes documents "
            "by what they say, and verifies every retrieval by reading it."
        ),
    ),
    dict(
        id="s2_organization", visual="clip:org", min_seconds=32,
        text=(
            "This is the live deployment. Fifty real research papers, three point "
            "eight million characters, filed into five category bases: computer "
            "science, natural sciences, life sciences, economics, and engineering. "
            "Nothing here was filed by filename. A classifier read each paper and "
            "decided. Three assignments deliberately overrode the filename: a paper "
            "labelled neuroscience is really a spiking neural-network algorithm, and "
            "it went to computer science. Long papers are split into parts that keep "
            "their section headers, and tags propagate from a paper to every part."
        ),
    ),
    dict(
        id="s3a_retrieval", visual="clip:search", min_seconds=22,
        text=(
            "Now the retrieval. We ask: what defines NISQ technology, and what is "
            "its central limitation? Phase one recalls candidates from all five "
            "bases and fuses BM25 with vector similarity. The NISQ paper comes back "
            "first, and the hit card tells us exactly where it lives: the natural "
            "sciences base, part one of three, with the similarity broken out by "
            "channel."
        ),
    ),
    dict(
        id="s3b_gate", visual="card:answer", min_seconds=26,
        text=(
            "The content gate then reads that part. It scores the candidate on a "
            "zero to eight rubric covering topic, scenario and evidence. Seven out "
            "of eight: a fast exit, and the search stops. What comes back is not a "
            "paragraph of prose. It is five sections, with the search path it took, "
            "the answer, its sources, a confidence level, and the blind spots it "
            "could not read. The citation names the base, the document, the part and "
            "the section, so you can open the cited fragment and check every claim."
        ),
    ),
    dict(
        id="s4a_trap", visual="clip:notfound", min_seconds=18,
        text=(
            "But a gate is only useful if it can say no. Here we ask about a paper "
            "that does not exist, Spectral Tuning for Low-Resource Odor Recognition. "
            "The trap is real. The top candidate is the BERT paper, and it genuinely "
            "contains training-epoch strings, so a similarity-ranked pipeline would "
            "happily quote them as the answer."
        ),
    ),
    dict(
        id="s4b_notfound", visual="card:notfound", min_seconds=24,
        text=(
            "The gate reads the text and scores it one out of eight. The librarian "
            "pass then scans the shelves and confirms the paper is not there. What "
            "the system returns is a not-found report: what it searched, the near "
            "miss it found, why that near miss does not answer the question, and what "
            "to do next. Three out-of-corpus probes scored one, one and zero out of "
            "eight, and all three returned not-found. Saying I don't know is a "
            "recorded output, not a failure."
        ),
    ),
    dict(
        id="s5_evidence", visual="clip:graph", min_seconds=25,
        text=(
            "The platform is agent-native as well: forty-one MCP tools expose the "
            "same operations to any AI agent. In the benchmark, the protocol placed "
            "the gold document first in all ten questions, at one point six seconds "
            "mean vector recall. A dense baseline was faster, but it cannot trace its "
            "answers to a source at all. And every decision, the classification, the "
            "gate score, the fallback and the not-found, is persisted as an artifact "
            "you can replay."
        ),
    ),
    dict(
        id="s6_close", visual="title_end", min_seconds=15,
        text=(
            "At the booth: bring a PDF, watch it classified, ask a question, inspect "
            "the score and the citation, and then try to make it lie. QDCVR. Content "
            "decides where documents live, and reading decides what answers."
        ),
    ),
]

CAPTIONS = {
    "s1_opening": "QDCVR \u2014 a deployable knowledge-base platform",
    "s2_organization": "50 real papers \u00b7 3.8M characters \u00b7 5 content-classified bases",
    "s3a_retrieval": "BM25 + vector recall over all five bases",
    "s3b_gate": "0\u20138 content gate \u2192 five-section answer with base \u00b7 doc \u00b7 part \u00b7 section",
    "s4a_trap": "A query for a paper that does not exist",
    "s4b_notfound": "Gate 1/8 \u2192 not-found report, not a fabricated answer",
    "s5_evidence": "41 MCP tools \u00b7 gold ranked first 10/10 \u00b7 every decision persisted",
    "s6_close": "Content decides where documents live. Reading decides what answers.",
}

# ── Card content: real artifact text, trimmed for legibility ─────────────────
CARD_ANSWER = dict(
    kicker="QDCVR protocol \u00b7 Track A \u00b7 recorded benchmark answer",
    title="BQ02 \u2014 What defines NISQ technology and what is its central limitation?",
    badge="content gate 7/8 \u00b7 fast exit",
    body=[
        ("Search Paths",
         "Phase 1 vector search \u2192 gold doc top-1 (0.709), parts 1/3 and 2/3 both "
         "retrieved \u2192 gate read: title/intro of part 1 and \u00a76.4 of part 2 \u2192 fast exit."),
        ("Answer",
         "NISQ stands for \u201cNoisy Intermediate-Scale Quantum\u201d. Its central limitation: "
         "these devices run without quantum error correction \u2014 the overhead of QEC is what "
         "keeps near-term devices limited to using noisy qubits directly."),
        ("Sources",
         "[P0] quantum-physics__1801.00862 (part 1/3 title+intro; part 2/3 \u00a76.4) "
         "@ \u987e\u81ea\u7136\u79d1\u5b66\u4e0e\u5730\u7403\u79d1\u5b66 \u2014 definition framing and the no-QEC-overhead limitation quote."),
        ("Confidence",
         "High on the without-error-correction limitation (\u00a76.4 verbatim) and the NISQ naming."),
        ("Blind Spots",
         "The exact qubit-count sentence in \u00a71 was only partially inside the 3000-char head "
         "window; quote the precise range only after re-reading \u00a71."),
    ],
)

CARD_NOTFOUND = dict(
    kicker="QDCVR protocol \u00b7 honest-failure probe P2",
    title="\u201cWhat did \u2018Spectral Tuning for Low-Resource Odor Recognition\u2019 "
          "report about training epochs?\u201d",
    badge="content gate 1/8 \u00b7 NOT FOUND",
    body=[
        ("Verdict", "NOT_FOUND \u2014 the paper is not in the corpus."),
        ("Why the near miss is not an answer",
         "The top candidate is the BERT pre-training paper, which does contain "
         "training-epoch strings. On reading, the gate scored it 1/8: those epochs belong "
         "to that paper\u2019s own pre-training recipe, not to any paper of the requested title."),
        ("Librarian shelf scan",
         "5 category bases, 50 papers, 165 indexed documents. No NAACL odor-recognition "
         "paper is present; the nearest language-model neighbour is unrelated."),
        ("Report excerpt",
         "\u201cI could not verify this paper in the knowledge base, and I will not fabricate "
         "its findings. \u2026 Quoting the near-miss would have been a fabrication.\u201d"),
    ],
)
