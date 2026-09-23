"""P3 ingestion E2E: real PDF via MinerU + real markdown docs, A6-V index gate.

SSRF-hardened: guard_url allows loopback 8771/6789 only. Token from .env.
Local file access goes through pathlib with explicit repo-root containment
checks (os.path.abspath + startswith) before any read.
Usage: python review/e2e-full-stack-20260922/p3_ingest.py [--skip-parse]
"""
import ipaddress
import json
import os
import posixpath
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HERE = Path(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {8771, 6789}


def read_bytes(*parts: str) -> bytes:
    target = os.path.abspath(str(ROOT.joinpath(*parts)))
    if not target.startswith(os.path.abspath(str(ROOT))):
        raise ValueError("path escapes repo root: " + target)
    return Path(target).read_bytes()


def read_text(path_arg: str) -> str:
    target = os.path.abspath(path_arg)
    allowed = (os.path.abspath(str(ROOT)), os.path.abspath(str(ROOT.joinpath("backend", "output"))))
    if not target.startswith(allowed):
        raise ValueError("path outside allowed roots: " + target)
    return Path(target).read_text(encoding="utf-8", errors="replace")


def save_state(state: dict) -> None:
    target = os.path.abspath(str(HERE.joinpath("p3_state.json")))
    if not target.startswith(os.path.abspath(str(HERE))):
        raise ValueError("path escapes review dir: " + target)
    Path(target).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def guard_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked target: " + repr(url))
    if p.port not in ALLOWED_PORTS:
        raise ValueError("blocked target: " + repr(url))
    ip = socket.gethostbyname(p.hostname)
    if ipaddress.ip_address(ip) != ipaddress.ip_address("127.0.0.1"):
        raise ValueError("DNS rebinding blocked: " + url)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def load_token() -> str:
    for line in ROOT.joinpath(".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


TOKEN = load_token()
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("[PASS] " if cond else "[FAIL] ") + name + ("  -- " + detail if detail else ""), flush=True)


def call_json(method, url, body=None, token=TOKEN, timeout=120):
    guard_url(url)
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    with OPENER.open(req, data=data, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


def call_multipart(url, fields, token=TOKEN, timeout=1200):
    guard_url(url)
    boundary = "----e2eboundary" + uuid.uuid4().hex
    buf = b""
    for name, val in fields.items():
        if isinstance(val, tuple):
            fname, ctype, data = val
            buf += ("--" + boundary + "\r\n").encode()
            buf += ('Content-Disposition: form-data; name="' + name + '"; filename="' + fname + '"\r\n').encode()
            buf += ("Content-Type: " + ctype + "\r\n\r\n").encode()
            buf += data + b"\r\n"
        else:
            buf += ("--" + boundary + "\r\n").encode()
            buf += ('Content-Disposition: form-data; name="' + name + '"\r\n\r\n' + val + "\r\n").encode()
    buf += ("--" + boundary + "--\r\n").encode()
    req = urllib.request.Request(url, data=buf, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with OPENER.open(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


WEB = "http://127.0.0.1:6789"
BE = "http://127.0.0.1:8771"
stamp = time.strftime("%m%d-%H%M%S")
KB_NAME = "e2e-demo-" + stamp

# ---- Stage 1: create test KB ----
s, j = call_json("POST", WEB + "/api/kb/create", {"name": KB_NAME, "description": "E2E full-stack test KB (2026-09-22): real-doc ingestion, retrieval, experience, persona integration"})
kb = j.get("knowledgeBase") or {}
kb_folder_id = kb.get("id") or kb.get("folderId") or ""
check("kb create", s == 200 and j.get("success") and bool(kb_folder_id), "folder_id=" + kb_folder_id + " path=" + str(kb.get("path")))

s, j = call_json("GET", WEB + "/api/kb/catalog")
kb_uuid = ""
kb_path = ""
for k in j.get("knowledgeBases") or []:
    if k.get("name") == KB_NAME:
        kb_uuid = k.get("kbId") or ""
        kb_path = k.get("path") or ""
        break
check("kb visible in catalog", bool(kb_uuid), "kbId=" + kb_uuid + " path=" + kb_path)

state = {"kb_name": KB_NAME, "kb_folder_id": kb_folder_id, "kb_uuid": kb_uuid, "kb_path": kb_path, "stamp": stamp}
save_state(state)

# ---- Track B: markdown docs (real repo content) ----
md_sources = [
    (("docs", "ARCHITECTURE.md"), "平台架构总览",
     "Three services + MCP layer architecture: FastAPI backend, Nuxt 3 BFF, kb-mcp tools, MinerU OCR, tree storage model"),
    (("docs", "agentworkshop-integration.md"), "AgentWorkShop 集成指南",
     "External agent workshop integration: kb_agent chat API sync/async contract, native-search QDCVR pipeline, auth channels"),
]
md_docs = []
for rel_parts, title, desc in md_sources:
    content = read_bytes(*rel_parts).decode("utf-8", "replace")
    md_docs.append((title, desc, content))
    s, j = call_json("POST", WEB + "/api/kb/documents/create",
                     {"kbId": kb_uuid, "name": title + ".md", "content": content,
                      "description": desc, "tags": ["e2e", "architecture"]})
    check("doc create [" + title + "]", s == 200 and j.get("success"), "status=" + str(s) + " chars=" + str(len(content)))

# ---- A6-V gate: explicit index + verify chunks >= 1 ----
for title, desc, content in md_docs:
    doc_path = posixpath.join(KB_NAME, title + ".md")
    s, j = call_json("POST", BE + "/api/v1/search/index-document",
                     {"kb_id": kb_uuid, "doc_path": doc_path, "doc_name": title,
                      "description": desc, "content": content, "skip_graph": False}, timeout=300)
    ok = s == 200 and j.get("success") and (j.get("vector_index") or {}).get("success", True)
    check("index-document [" + title + "]", ok, json.dumps(j, ensure_ascii=False)[:160])

s, j = call_json("GET", BE + "/api/v1/search/stats", token=TOKEN, timeout=60)
coll = [c for c in (j.get("stats", {}).get("collections") or []) if kb_uuid in str(c.get("collection", ""))]
chunks = sum(int(c.get("chunk_count") or 0) for c in coll)
check("A6-V stats: test KB collection chunks >= 1", chunks >= 1, "collections=" + json.dumps(coll, ensure_ascii=False) + " chunks=" + str(chunks))

# ---- Track A: real PDF via MinerU ----
if "--skip-parse" not in sys.argv:
    t0 = time.time()
    pdf_bytes = read_bytes("docs", "paper", "benchmark", "datasets", "arxiv-benchmark", "global-rag-benchmark.pdf")
    print("[i] parsing real PDF (" + str(len(pdf_bytes)) + " bytes) via MinerU (local engine cold start possible)...", flush=True)
    try:
        s, j = call_multipart(WEB + "/api/parse/file-vt",
                              {"file": ("global-rag-benchmark.pdf", "application/pdf", pdf_bytes), "use_ocr": "true"},
                              timeout=1500)
        dur = time.time() - t0
        md_path = j.get("markdown_path") or ""
        check("PDF parse via MinerU", s == 200 and j.get("success") and j.get("has_markdown", True),
              " dur=" + str(int(dur)) + "s markdown_path=" + md_path + " images=" + str(j.get("image_count")))
        state["parse_result"] = j
        save_state(state)
        # ---- save parsed result into KB ----
        s, j = call_json("POST", WEB + "/api/parse/save-parsed-files",
                         {"parentId": kb_folder_id, "results": [j]}, timeout=300)
        check("save-parsed-files into KB", s == 200 and j.get("success", True),
              "status=" + str(s) + " body=" + json.dumps(j, ensure_ascii=False)[:200])
        # ---- index parsed doc ----
        src_name = j.get("source_filename") or "global-rag-benchmark"
        doc_title = os.path.splitext(src_name)[0]
        md_content = ""
        mp = j.get("markdown_path") or ""
        if mp and os.path.exists(mp):
            md_content = read_text(mp)
        s, j = call_json("POST", BE + "/api/v1/search/index-document",
                         {"kb_id": kb_uuid, "doc_path": posixpath.join(KB_NAME, doc_title + ".md"),
                          "doc_name": doc_title,
                          "description": "Real arXiv paper: global RAG benchmark (parsed by MinerU OCR)",
                          "content": md_content, "skip_graph": False}, timeout=300)
        check("index parsed PDF doc", s == 200 and j.get("success"), json.dumps(j, ensure_ascii=False)[:160])
        s, j = call_json("GET", BE + "/api/v1/search/stats", token=TOKEN, timeout=60)
        coll = [c for c in (j.get("stats", {}).get("collections") or []) if kb_uuid in str(c.get("collection", ""))]
        chunks = sum(int(c.get("chunk_count") or 0) for c in coll)
        check("A6-V stats after PDF ingest: chunks >= 1", chunks >= 1, "chunks=" + str(chunks))
        state["chunks_total"] = chunks
        save_state(state)
    except Exception as e:  # noqa: BLE001 — any parse failure is recorded as a FAIL line
        check("PDF parse via MinerU", False, "exception after " + str(int(time.time() - t0)) + "s: " + repr(e))

# ---- metadata closure: documents read-back ----
s, j = call_json("GET", WEB + "/api/kb/documents?kbId=" + kb_uuid)
docs = j.get("documents") or j.get("docs") or []
check("documents list in KB", s == 200 and len(docs) >= 2, "count=" + str(len(docs)))

print()
failed = [n for n, ok, _ in results if not ok]
print("==== P3 ingestion summary: " + str(len(results) - len(failed)) + "/" + str(len(results)) + " passed ====")
sys.exit(1 if failed else 0)
