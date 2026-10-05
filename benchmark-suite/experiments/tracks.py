"""Track definitions: same external corpus (50 exported papers), three agents.

Each track = a system prompt + a toolset. The SAME agent loop (agent_loop.ToolAgent)
executes every track, so any behavioral difference comes from the retrieval mode.
"""
from __future__ import annotations

from agent_loop import ToolAgent
from tools import track_a_tools, track_b_tools, track_c_tools

COMMON = """You are one track in a controlled retrieval experiment. Three agents answer
the same questions over the SAME 50-paper corpus; only your retrieval mode differs.
Rules:
1. Use ONLY your listed tools. Never invent content; answer strictly from tool outputs.
2. Answer in ENGLISH, 2-6 sentences, factual, with source references where available.
3. If your tools cannot find the answer, say so explicitly (honest not-found).
4. Be economical: at most {max_steps} tool steps."""

TRACK_A = COMMON + """
Your mode: PLATFORM KB SYSTEM (external API client). You are an outside integrator:
retrieve via the platform's HTTP APIs only (dense vector search over the category
knowledge bases, cross-KB keyword search, offset-addressed document reads).
Strategy hint: vector-search first; if truncated=true, continue reading with
offset = characters consumed so far."""

TRACK_B = COMMON + """
Your mode: BARE AGENT. You have NO index — just plain file tools over the corpus
directory. Locate papers by filename, search_text inside files, then read_file the
relevant line ranges. This is full-text reading and file search only."""

TRACK_C = COMMON + """
Your mode: DENSE RAG. You execute real dense vector retrieval yourself over the
Corpus-Chunks800 index (fixed 800-char chunks). Call vector_search (rephrase if the
first pass is weak), optionally get_chunk for full chunk text, then answer ONLY from
retrieved chunk text. If the chunks do not contain the answer, state that the
retrieved evidence is insufficient instead of guessing."""


def build(track: str, question: str, max_steps: int = 8) -> ToolAgent:
    track = track.lower()
    if track == "a":
        return ToolAgent("platform", TRACK_A.format(max_steps=max_steps),
                         track_a_tools(), stage="exp-a", max_steps=max_steps)
    if track == "b":
        return ToolAgent("bare", TRACK_B.format(max_steps=max_steps),
                         track_b_tools(), stage="exp-b", max_steps=max_steps)
    if track == "c":
        return ToolAgent("rag", TRACK_C.format(max_steps=max_steps),
                         track_c_tools(), stage="exp-c", max_steps=max_steps)
    raise ValueError(f"unknown track {track!r} (a/b/c)")
