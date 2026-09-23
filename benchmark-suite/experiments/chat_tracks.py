"""Claude-harness tracks via the platform's EXTERNAL chat API.

All three tracks run on harness=claude through the system's public answer
endpoint — POST /api/claude/chat with engine:"claude" — which is exactly how an
outside caller consumes the system. Only the retrieval protocol differs:

  a  platform  — no restrictions: the system answers through its own QDCVR skill
                 flow (cwd = repo root, full toolset)
  b  bare      — bare agent: cwd = the exported corpus dir, allowedTools locked
                 to Read/Grep/Glob (plain full-text reading + file search)
  c  rag       — dense-RAG protocol: allowedTools locked to the vector-search
                 MCP tool on Corpus-Chunks800; answer only from retrieved chunks

Monitoring (per run, all persisted): full event timeline, every tool call,
assistant texts, wall-clock latency, SDK duration_ms/num_turns, and the token
accounting from the SDK result (input / output / cache-read / cache-creation
tokens + total_cost_usd). Permission requests are auto-denied and counted —
retrieval experiments must stay read-only.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
sys.path.insert(0, str(REPO / "scripts"))
from dev_smoke import OPENER, guard_url  # noqa: E402  (loopback SSRF guard)

CHAT = "http://127.0.0.1:6789/api/claude/chat"
PERM = "http://127.0.0.1:6789/api/claude/permission"
CORPUS_DIR = REPO / "benchmark-suite" / "data" / "corpus_md"

A_PROMPT = ("Answer the following question using the knowledge base. Execute the "
            "retrieval yourself in THIS session with the kb_* tools — do NOT "
            "delegate to subagents or background tasks, and never end your turn "
            "while a retrieval is pending. Wait for every tool result, then give "
            "the final answer. Answer in English with source references.\n\n"
            "QUESTION: {q}")

B_PROMPT = """You are a BARE research agent in a retrieval experiment: you have NO
index and NO knowledge-base tools — only plain file tools (Read/Grep/Glob) over
the current directory, which holds 100 research-paper markdown files.
Workflow: Glob the file list, Grep inside files for relevant passages, Read
enough surrounding lines, then answer. Use ONLY what the files contain; if they
do not answer the question, say so explicitly. Answer in ENGLISH (2-6 sentences)
and name the file(s) you used.

QUESTION: {q}"""

C_PROMPT = """You are a DENSE-RAG pipeline in a retrieval experiment. Execute real
dense vector retrieval yourself with the kb_search_vector MCP tool on
kb_id="Corpus-Chunks800" (top_k 10, score_threshold 0) — this index holds fixed
800-character chunks of 100 papers. The tool is registered under one of these
names: `mcp__kb-mcp__kb_search_vector` or
`mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector` — use whichever exists in
your toolset (try the other only if the first is rejected). You may rephrase
and search again, but you must answer ONLY from the retrieved chunk text
(quote-level grounding). If the retrieved chunks do not contain the answer,
reply that the retrieved evidence is insufficient. Do not use any other tool.
Answer in ENGLISH (2-6 sentences) and cite the chunk file names you used.

QUESTION: {q}"""

# Track A = an outside integrator that has been granted READ access to the
# platform: kb-mcp read/search tools auto-approved via bare allowedTools
# entries (the SDK auto-approves bare names; canUseTool is not consulted for
# them). Write-side tools stay outside the list -> auto-denied + counted.
# Prefix drift fix (2026-09-23): the kb-mcp server registers under BOTH
# namespaces depending on install mode — project .mcp.json (`mcp__kb-mcp__*`)
# and the rag-knowledge plugin (`mcp__plugin_rag-knowledge_kb-mcp__*`). List
# both so the read surface auto-approves under either registration.
def _kb_read_tools(*names: str) -> list:
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

C_VECTOR_TOOLS = _kb_read_tools("kb_search_vector")

TRACKS = {
    "a": {"cwd": str(REPO), "allowed_tools": A_TOOLS, "prompt": A_PROMPT},
    "b": {"cwd": str(CORPUS_DIR), "allowed_tools": ["Read", "Grep", "Glob"],
          "prompt": B_PROMPT},
    "c": {"cwd": str(REPO),
          "allowed_tools": C_VECTOR_TOOLS, "prompt": C_PROMPT},
}


def _token() -> str:
    cand = REPO / "storage" / "loop-auth.json"
    if cand.exists():
        tok = json.loads(cand.read_text(encoding="utf-8")).get("token", "")
        if tok:
            return tok
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def run_chat_track(track: str, question: str, timeout_s: int = 420) -> dict:
    """One Q&A through the external chat API on harness=claude, fully monitored."""
    spec = TRACKS[track]
    token = _token()
    payload = {"prompt": spec["prompt"].format(q=question), "cwd": spec["cwd"],
               "engine": "claude", "maxTurns": 12}
    if spec["allowed_tools"] is not None:
        payload["allowedTools"] = spec["allowed_tools"]

    guard_url(CHAT)
    req = urllib.request.Request(CHAT, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", f"Bearer {token}")

    t0 = time.perf_counter()
    texts: list[str] = []
    tools: list[dict] = []
    timeline: list[dict] = []
    denied = 0
    result: dict = {}

    def mark(kind: str, detail: str = "") -> None:
        timeline.append({"t": round(time.perf_counter() - t0, 2), "event": kind,
                         "detail": str(detail)[:180]})

    with OPENER.open(req, timeout=timeout_s) as resp:
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
        "track": track, "question": question,
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
