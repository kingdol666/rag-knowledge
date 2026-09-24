"""Claude-harness tracks via the platform's EXTERNAL chat API.

Every track answers through the platform's public answer endpoint —
POST /api/claude/chat with engine:"claude" — which is exactly how an outside
caller consumes the system. Only the retrieval affordance differs.

Tracks
------
  a   platform + file tools   kb_* tools AND Read/Grep/Glob. cwd is the CORPUS
                              directory, so the file tools can only ever see the
                              100 corpus markdown files — never the repository,
                              the question set, or the results (answer-key
                              isolation, see below).
  a2  platform only           kb_* tools, NO file tools. cwd = repo root is then
                              harmless (nothing can read it). This is the
                              leakage-free primary platform arm; (a - a2) is the
                              marginal value of the file tools.
  b   bare agent              plain file tools over the corpus dir only.
  c   dense RAG               kb_search_vector over Corpus-Chunks800 only.

Answer-key isolation (2026-09-24)
---------------------------------
The gold answers live under the repo (`data/papers/qa_questions*.json`,
`results/experiment_chat_*/SUMMARY.md`). Any track that can Read/Grep the repo
root can therefore read the key — an internal-validity defect, not a statistics
one. Fix: file-tool-bearing tracks are pinned to the corpus directory, and the
platform-only arm carries no file tools at all. `assert_no_repo_cwd()` enforces
this at import time.

Prompt neutrality (2026-09-24)
------------------------------
v1/v2 gave each track a different role framing ("You are a BARE agent…",
"You are a DENSE-RAG pipeline…"), so a difference could come from the framing
rather than the retrieval affordance. v3-neutral uses ONE task template with a
single slot for the affordance. Old runs keep their PROMPT_VERSION.

PROMPT_VERSION history
  v1       pre-2026-09-24 — B/C capped at "2-6 sentences", A uncapped (unfair)
  v2-fair  2026-09-24     — identical OUTPUT_CONTRACT, but per-track role prompts
  v3-neutral 2026-09-24   — single neutral template + sandboxed cwd (current)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
sys.path.insert(0, str(REPO / "scripts"))
from dev_smoke import OPENER, guard_url  # noqa: E402  (loopback SSRF guard)

CHAT = os.environ.get("RAG_BENCH_CHAT_URL",
                      "http://127.0.0.1:6789/api/claude/chat")
PERM = os.environ.get("RAG_BENCH_PERM_URL",
                      "http://127.0.0.1:6789/api/claude/permission")
CORPUS_DIR = SUITE / "data" / "corpus_md"

PROMPT_VERSION = "v3-neutral"

# ── shared output contract: byte-identical for every track ──────────────────
OUTPUT_CONTRACT = (
    "OUTPUT CONTRACT (identical for every track — do not exceed it):\n"
    "- Answer in ENGLISH.\n"
    "- At most 8 sentences, or one short paragraph plus a source list.\n"
    "- Name every source you actually used (document path / file name / chunk id).\n"
    "- If the evidence you retrieved does not answer the question, say so "
    "explicitly and stop — do NOT fall back on prior knowledge.\n"
    "- Do not pad. Length is not rewarded."
)

# ── one neutral template; only {affordance} changes between tracks ──────────
NEUTRAL_TASK = (
    "You are a retrieval-and-answer system in a controlled experiment.\n"
    "Answer the QUESTION using ONLY evidence you retrieve in THIS session. "
    "Retrieve first; never answer from prior knowledge.\n\n"
    + OUTPUT_CONTRACT +
    "\n\nYOUR RETRIEVAL AFFORDANCE:\n{affordance}\n\nQUESTION: {q}"
)

AFF_PLATFORM_FILES = (
    "The platform's knowledge-base tools are available to you "
    "(kb_search_vector, kb_search, kb_search_two_stage, kb_search_stats, "
    "kb_doc_read, kb_get_documents, kb_list, ...). Execute the retrieval "
    "yourself in THIS session — do not delegate to subagents or background "
    "tasks, and never end your turn while a retrieval is pending. You ALSO "
    "have plain file tools (Read/Grep/Glob) over the working directory, which "
    "holds the corpus markdown files."
)
AFF_PLATFORM = (
    "The platform's knowledge-base tools are available to you "
    "(kb_search_vector, kb_search, kb_search_two_stage, kb_search_stats, "
    "kb_doc_read, kb_get_documents, kb_list, ...). Execute the retrieval "
    "yourself in THIS session — do not delegate to subagents or background "
    "tasks, and never end your turn while a retrieval is pending. You have no "
    "file tools."
)
AFF_BARE = (
    "You have NO index and NO knowledge-base tools — only plain file tools "
    "(Read/Grep/Glob) over the working directory, which holds 100 research-"
    "paper markdown files. Glob the file list, Grep inside files for relevant "
    "passages, Read enough surrounding lines, then answer."
)
AFF_VECTOR = (
    "You have exactly one tool: dense vector search kb_search_vector over the "
    "index kb_id=\"Corpus-Chunks800\" (fixed 800-character chunks of the 100 "
    "papers; use top_k 10, score_threshold 0). You may rephrase and search "
    "again, but you must answer ONLY from the retrieved chunk text. Do not use "
    "any other tool."
)


def _kb_read_tools(*names: str) -> list:
    """Read-side kb tools, listed under both MCP registration namespaces."""
    out = []
    for n in names:
        out.append(f"mcp__kb-mcp__{n}")
        out.append(f"mcp__plugin_rag-knowledge_kb-mcp__{n}")
    return out


A_TOOLS = _kb_read_tools(
    "backend_status", "kb_list", "kb_search_vector", "kb_search",
    "kb_search_two_stage", "kb_search_stats", "kb_doc_read",
    "kb_get_documents", "kb_doc_get_by_tag", "kb_graph_stats",
    "kb_graph_search", "fs_get_tree", "fs_get_children",
) + ["Read", "Grep", "Glob"]

A2_TOOLS = [t for t in A_TOOLS if t not in ("Read", "Grep", "Glob")]

C_VECTOR_TOOLS = _kb_read_tools("kb_search_vector")

# ── track registry ──────────────────────────────────────────────────────────
# cwd policy: file-tool-bearing tracks are pinned to CORPUS_DIR (answer-key
# isolation). Tracks without file tools may use the repo root safely.
TRACKS = {
    "a": {"cwd": str(CORPUS_DIR), "allowed_tools": A_TOOLS,
          "affordance": AFF_PLATFORM_FILES, "prompt_version": PROMPT_VERSION},
    "a2": {"cwd": str(REPO), "allowed_tools": A2_TOOLS,
           "affordance": AFF_PLATFORM, "prompt_version": PROMPT_VERSION},
    "b": {"cwd": str(CORPUS_DIR), "allowed_tools": ["Read", "Grep", "Glob"],
          "affordance": AFF_BARE, "prompt_version": PROMPT_VERSION},
    "c": {"cwd": str(REPO), "allowed_tools": C_VECTOR_TOOLS,
          "affordance": AFF_VECTOR, "prompt_version": PROMPT_VERSION},
}

# Leakage guard: a track that has BOTH file tools and a repo-root cwd can read
# the gold answers. Refuse to construct such a track.
_FILE_TOOLS = {"Read", "Grep", "Glob", "Write", "Edit", "Bash", "Glob"}
for _name, _spec in TRACKS.items():
    _has_files = bool(set(_spec["allowed_tools"]) & _FILE_TOOLS)
    _at_repo = Path(_spec["cwd"]).resolve() == REPO.resolve()
    if _has_files and _at_repo:
        raise AssertionError(
            f"answer-key leak: track {_name!r} has file tools and cwd=repo root")


def build_prompt(track: str, question: str) -> str:
    spec = TRACKS[track]
    return NEUTRAL_TASK.format(affordance=spec["affordance"], q=question)


def _token() -> str:
    """Bearer token — shared resolver (loop-auth.json → env), with .env fallback."""
    try:
        from lib import auth_token
        t = auth_token()
        if t:
            return t
    except Exception:  # noqa: BLE001
        pass
    cand = REPO / "storage" / "loop-auth.json"
    if cand.exists():
        tok = json.loads(cand.read_text(encoding="utf-8")).get("token", "")
        if tok:
            return tok
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def _refresh() -> str:
    """Re-login and persist a fresh token (stale-token self-heal)."""
    try:
        from lib import login_refresh
        return login_refresh()
    except Exception:  # noqa: BLE001
        return ""


def _short_input(inp: dict | None) -> dict:
    inp = inp or {}
    keep = {}
    for k in ("query", "pattern", "path", "file_path", "kb_id", "cmd",
              "command", "doc_path"):
        if k in inp:
            keep[k] = str(inp[k])[:120]
    return keep


def _deny(token: str, session_id: str, tool_use_id: str) -> None:
    try:
        guard_url(PERM)
        req = urllib.request.Request(PERM, method="POST",
                                     data=json.dumps({
                                         "sessionId": session_id,
                                         "toolUseId": tool_use_id,
                                         "behavior": "deny",
                                         "message": "experiment read-only"}).encode("utf-8"))
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {token}")
        OPENER.open(req, timeout=20).read()
    except Exception:
        pass


def chat_stream(prompt: str, cwd: str, allowed_tools: list | None = None,
                max_turns: int = 12, timeout_s: int = 420) -> dict:
    """One monitored Q&A through the external chat API (SSE).

    This is the single choke point every track and every baseline answer goes
    through, so the generation channel is identical across the experiment.
    """
    token = _token()
    payload = {"prompt": prompt, "cwd": cwd, "engine": "claude",
               "maxTurns": int(max_turns)}
    if allowed_tools is not None:
        payload["allowedTools"] = allowed_tools

    guard_url(CHAT)

    def _build(tok: str) -> urllib.request.Request:
        r = urllib.request.Request(CHAT, method="POST",
                                   data=json.dumps(payload).encode("utf-8"))
        r.add_header("Content-Type", "application/json")
        r.add_header("Accept", "text/event-stream")
        r.add_header("Authorization", f"Bearer {tok}")
        return r

    req = _build(token)
    try:
        resp = OPENER.open(req, timeout=timeout_s)
    except urllib.error.HTTPError as e:
        # stale-token self-heal: re-login once and retry (else the whole run
        # would silently 401 — observed 2026-09-24)
        if e.code != 401:
            raise
        newtok = _refresh()
        if not newtok:
            raise
        resp = OPENER.open(_build(newtok), timeout=timeout_s)

    t0 = time.perf_counter()
    texts: list[str] = []
    tools: list[dict] = []
    timeline: list[dict] = []
    denied = 0
    result: dict = {}

    def mark(kind: str, detail: str = "") -> None:
        timeline.append({"t": round(time.perf_counter() - t0, 2), "event": kind,
                         "detail": str(detail)[:180]})

    with resp:
        cur = ""
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("event:"):
                cur = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            try:
                msg = json.loads(line[5:].strip())
            except Exception:
                continue
            if cur == "permission_request" or msg.get("type") == "permission_request":
                cur = ""
                denied += 1
                mark("permission_denied", str(msg.get("toolName")))
                _deny(token, msg.get("sessionId", msg.get("session_id", "")),
                      msg.get("toolUseId", ""))
                continue
            cur = ""
            mtype = msg.get("type")
            if mtype == "system" and msg.get("subtype") == "init":
                mark("init", str(msg.get("model")))
            elif mtype == "assistant":
                for blk in (msg.get("message") or {}).get("content", []):
                    if blk.get("type") == "tool_use":
                        tools.append({"tool": blk.get("name"),
                                      "input": _short_input(blk.get("input"))})
                        mark("tool_use", str(blk.get("name")))
                    elif blk.get("type") == "text" and (blk.get("text") or "").strip():
                        texts.append(blk["text"])
                        mark("text", len(blk["text"]))
            elif mtype == "result":
                result = msg
                mark("result", f"is_error={msg.get('is_error')}")
                break

    usage = result.get("usage") or {}
    answer = (texts[-1] if texts else str(result.get("result", "")))
    return {
        "answer": answer,
        "is_error": result.get("is_error"),
        "latency_s": round(time.perf_counter() - t0, 1),
        "sdk_duration_ms": result.get("duration_ms"),
        "num_turns": result.get("num_turns"),
        "tool_calls": tools,
        "tool_call_count": len(tools),
        "permission_denied": denied,
        "tokens": {"input": usage.get("input_tokens"),
                   "output": usage.get("output_tokens"),
                   "cache_read": usage.get("cache_read_input_tokens"),
                   "cache_creation": usage.get("cache_creation_input_tokens")},
        "total_cost_usd": result.get("total_cost_usd"),
        "timeline": timeline,
        "texts_full": texts,
    }


def run_chat_track(track: str, question: str, max_turns: int = 12,
                   timeout_s: int = 420) -> dict:
    """One Q&A through the external chat API on harness=claude, fully monitored."""
    spec = TRACKS[track]
    r = chat_stream(build_prompt(track, question), spec["cwd"],
                    spec["allowed_tools"], max_turns=max_turns,
                    timeout_s=timeout_s)
    r.update({"track": track, "question": question,
              "prompt_version": spec["prompt_version"],
              "cwd": spec["cwd"], "max_turns": int(max_turns)})
    return r


# ── closed-book answering channel (used by every retrieval-only baseline) ───
CLOSED_BOOK_PROMPT = (
    "You are a document-grounded QA assistant in a controlled experiment.\n"
    "Answer the QUESTION using ONLY the EVIDENCE below. If the evidence does "
    "not contain the answer, say the evidence is insufficient — do NOT use "
    "prior knowledge.\n\n"
    + OUTPUT_CONTRACT +
    "\n\nEVIDENCE:\n{evidence}\n\nQUESTION: {q}"
)


def answer_closed_book(question: str, evidence: str,
                       timeout_s: int = 300) -> dict:
    """Answer from a supplied evidence pack — same chat API, no tools.

    Retrieval-only baselines (BM25 / vector / RRF / rerank / CRAG / Self-RAG)
    all retrieve locally and then call THIS, so the generation step is
    byte-identical across methods and the only difference is the evidence.
    """
    prompt = CLOSED_BOOK_PROMPT.format(
        evidence=evidence or "(no evidence retrieved)", q=question)
    r = chat_stream(prompt, str(CORPUS_DIR), allowed_tools=[],
                    max_turns=1, timeout_s=timeout_s)
    r["channel"] = "closed-book"
    return r
