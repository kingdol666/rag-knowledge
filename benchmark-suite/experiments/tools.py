"""Tool implementations for the three experiment tracks.

Track A tools hit the platform's EXTERNAL HTTP APIs only (the same surface an
outside integrator would use): vector search on the backend, cross-KB keyword
search + offset-addressed document reads on the web server.
Track B tools are plain file operations confined to the exported corpus.
Track C tools expose real dense vector retrieval over Corpus-Chunks800 (the
agent executes the search itself and reads full chunk text on demand).

SSRF-hardened: every platform API call passes _guard(), which only allows
http://{127.0.0.1|localhost}:{8771|6789} with resolved-IP pinning and redirects
disabled.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import sys
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "algorithms"))

CORPUS_DIR = SUITE / "data" / "corpus_md"
BE = "http://127.0.0.1:8771"
WEB = "http://127.0.0.1:6789"
CATEGORY_KBS = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
                "工程与能源", "经济与社会"]


def _token() -> str:
    for cand in (SUITE.parent / "storage" / "loop-auth.json",):
        if cand.exists():
            return json.loads(cand.read_text(encoding="utf-8")).get("token", "")
    env = SUITE.parent / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
_ALLOWED_PORTS = {8771, 6789}


def _guard(url: str) -> None:
    """SSRF guard: this experiment only talks to the local platform APIs."""
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in _ALLOWED_HOSTS:
        raise ValueError(f"blocked non-loopback target: {url!r}")
    if p.port not in _ALLOWED_PORTS:
        raise ValueError(f"blocked port: {url!r}")
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError(f"DNS rebinding blocked: {url!r} -> {ip}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _http(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    _guard(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {_token()}")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    with _OPENER.open(req, data=data, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


# ── Track A: platform external API ──────────────────────────────────────────

def platform_vector_search(query: str, kb_id: str = "", top_k: int = 10,
                           score_threshold: float = 0.3) -> dict:
    """POST /api/v1/search/vector — dense retrieval over category KBs."""
    r = _http(f"{BE}/api/v1/search/vector", "POST",
              {"query": query, "kb_id": kb_id, "top_k": int(top_k),
               "score_threshold": float(score_threshold)})
    out = []
    for it in (r.get("results") or [])[:int(top_k)]:
        out.append({"doc_path": it.get("doc_path", ""), "score": round(
            float(it.get("score", 0)), 4),
            "excerpt": str(it.get("content", ""))[:350]})
    return {"count": len(out), "results": out, "known_kbs": CATEGORY_KBS}


def platform_keyword_search(query: str, top_k: int = 10) -> dict:
    """GET /api/kb/search — cross-KB keyword search."""
    r = _http(f"{WEB}/api/kb/search?query={quote(query)}&top_k={int(top_k)}")
    hits = r.get("hits") or []
    return {"count": len(hits), "hits": [
        {k: h.get(k) for k in ("name", "kb", "path", "score") if k in h}
        for h in hits[:int(top_k)]]}


def platform_doc_read(kb_id: str, doc_path: str, offset: int = 0,
                      limit: int = 200, max_chars: int = 3000) -> dict:
    """GET /api/kb/document — offset-addressed document read (continuation)."""
    q = (f"{WEB}/api/kb/document?kb_id={quote(str(kb_id))}"
         f"&doc_path={quote(str(doc_path))}&offset={int(offset)}"
         f"&limit={int(limit)}&max_chars={int(max_chars)}")
    r = _http(q)
    content = str(r.get("content", ""))
    return {"kb": r.get("kb", kb_id), "doc": r.get("doc", doc_path),
            "offset": offset, "chars": len(content),
            "truncated": r.get("truncated"), "content": content}


# ── Track B: bare file tools (corpus only) ──────────────────────────────────

def _safe_corpus_path(name: str) -> Path:
    p = (CORPUS_DIR / str(name)).resolve()
    if not str(p).startswith(str(CORPUS_DIR.resolve())):
        raise ValueError("path escapes corpus directory")
    return p


def bare_list_files() -> dict:
    files = sorted(p.name for p in CORPUS_DIR.glob("*.md"))
    return {"count": len(files), "files": files}


def bare_search_text(pattern: str, max_hits: int = 20) -> dict:
    rx = re.compile(pattern, re.I)
    hits = []
    for p in sorted(CORPUS_DIR.glob("*.md")):
        for i, line in enumerate(p.read_text(encoding="utf-8",
                                             errors="replace").splitlines(), 1):
            if rx.search(line):
                hits.append({"file": p.name, "line": i,
                             "text": line.strip()[:160]})
                if len(hits) >= int(max_hits):
                    return {"count": len(hits), "capped": True, "hits": hits}
    return {"count": len(hits), "hits": hits}


def bare_read_file(name: str, start_line: int = 1, max_lines: int = 120) -> dict:
    p = _safe_corpus_path(name)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    s = max(1, int(start_line))
    seg = lines[s - 1: s - 1 + int(max_lines)]
    return {"file": p.name, "total_lines": len(lines),
            "from_line": s, "lines_returned": len(seg),
            "content": "\n".join(seg)}


# ── Track C: dense RAG over Corpus-Chunks800 ────────────────────────────────

def rag_vector_search(query: str, top_k: int = 10) -> dict:
    """Real dense retrieval executed over the Corpus-Chunks800 vector index."""
    from lib import McpClient
    c = McpClient()
    try:
        r = c.call("kb_search_vector",
                   {"query": query, "kb_id": "Corpus-Chunks800",
                    "top_k": int(top_k), "score_threshold": 0.0}, timeout=300)
    finally:
        c.close()
    out = []
    for it in (r.get("results") or [])[:int(top_k)]:
        name = str(it.get("doc_path", "")).replace("\\", "/").rsplit("/", 1)[-1]
        out.append({"src": name, "score": round(float(it.get("score", 0)), 4),
                    "excerpt": str(it.get("content", ""))[:450]})
    return {"count": len(out),
            "index": "Corpus-Chunks800 (800/400-char chunks, 50 papers)",
            "results": out}


def rag_get_chunk(src: str) -> dict:
    """Full text of one retrieved chunk, by its file name (e.g. slug__k03.md)."""
    from index_kb import load_texts
    texts = load_texts("Corpus-Chunks800")
    want = str(src)
    for path, rec in texts.items():
        if path.replace("\\", "/").rsplit("/", 1)[-1] == want:
            return {"src": want, "chars": len(rec["text"]),
                    "content": rec["text"][:4000]}
    return {"error": f"chunk {want!r} not in index cache; call vector_search first"}


# ── registries ──────────────────────────────────────────────────────────────

from agent_loop import Tool  # noqa: E402


def track_a_tools() -> list:
    return [
        Tool("platform_vector_search",
             "Dense vector search over the platform's category KBs (semantic). "
             "kb_id may be empty (all KBs) or one of known_kbs.",
             {"query": "str", "kb_id": "str", "top_k": "int",
              "score_threshold": "float"}, platform_vector_search),
        Tool("platform_keyword_search",
             "Cross-KB keyword search over the platform.",
             {"query": "str", "top_k": "int"}, platform_keyword_search),
        Tool("platform_doc_read",
             "Read document text from the platform with continuation: pass "
             "offset=previous content length when truncated=true.",
             {"kb_id": "str", "doc_path": "str", "offset": "int",
              "limit": "int", "max_chars": "int"}, platform_doc_read),
    ]


def track_b_tools() -> list:
    return [
        Tool("list_files", "List the 50 corpus markdown filenames.",
             {}, bare_list_files),
        Tool("search_text",
             "Full-text search across all corpus files (case-insensitive "
             "regex); returns file, line number, line text.",
             {"pattern": "str", "max_hits": "int"}, bare_search_text),
        Tool("read_file",
             "Read a corpus file slice by line range (use search_text first "
             "to locate, then read around the hits).",
             {"name": "str", "start_line": "int", "max_lines": "int"},
             bare_read_file),
    ]


def track_c_tools() -> list:
    return [
        Tool("vector_search",
             "Execute dense vector retrieval over the Corpus-Chunks800 index "
             "(800-char chunks of the 50 papers). Returns ranked chunks with "
             "scores + excerpts.",
             {"query": "str", "top_k": "int"}, rag_vector_search),
        Tool("get_chunk",
             "Fetch the FULL text of one retrieved chunk by its src file name "
             "(from the last vector_search results).",
             {"src": "str"}, rag_get_chunk),
    ]
