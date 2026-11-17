#!/usr/bin/env python3
"""Live demo @ master: batch-parse ingest vs direct ingest vs RAG queries.

Three real arXiv PDFs go through the TRUE batch SSE parse endpoint
(POST /batch/parse/file/vt/stream, concurrent MinerU tasks), two real
repository markdown docs are ingested directly WITHOUT parsing, then three
retrieval-augmented queries run against the combined knowledge base via the
web chat SSE (kbEnhanced). The demo KB is kept for browsing.

Usage: python review/e2e-master-20261117/batch_demo.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))

from dev_smoke import OPENER, load_token  # noqa: E402
from mcp_client import McpClient  # noqa: E402

TOKEN = load_token()
BACKEND = "http://127.0.0.1:8770"
WEB = "http://127.0.0.1:6789"
SCI = REPO / "corpus" / "multi-domain-docs-20261101" / "science-en"
PDFS = [SCI / "attention_is_all_you_need.pdf",
        SCI / "rag_lewis2020.pdf",
        SCI / "llama.pdf"]
DIRECT_DOCS = [
    (REPO / "docs" / "ARCHITECTURE.md", "平台架构说明-ARCHITECTURE.md"),
    (REPO / "README.md", "平台总览-README.md"),
]
OUT = Path(__file__).resolve().parent
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
KB_NAME = f"实机演示-多路入库-{STAMP}"

RESULTS: list[tuple[str, bool, str]] = []
DETAIL: dict = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "steps": {}}


def step(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f" -- {detail}" if detail else ""), flush=True)


def jkey(obj, *names, default=None):
    for n in names:
        if isinstance(obj, dict) and obj.get(n) not in (None, "", []):
            return obj[n]
    return default


def batch_parse() -> dict:
    """True batch endpoint: concurrent MinerU tasks, SSE progress stream."""
    boundary = "----batchdemo" + uuid.uuid4().hex
    body = bytearray()

    def field(name, value):
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())

    import mimetypes
    out_dir = f"backend/output/batch-demo-{STAMP}"
    for pdf in PDFS:
        ctype = mimetypes.guess_type(pdf.name)[0] or "application/pdf"
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{pdf.name}\"\r\n"
                    f"Content-Type: {ctype}\r\n\r\n".encode())
        body.extend(pdf.read_bytes())
        body.extend(b"\r\n")
    for _ in PDFS:
        field("output_dirs", out_dir)
    field("default_output", out_dir)
    field("use_ocr", "true")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(f"{BACKEND}/batch/parse/file/vt/stream", method="POST",
                                 data=bytes(body))
    # route is mounted under /api/v1 — corrected below if needed
    req.full_url = f"{BACKEND}/api/v1/batch/parse/file/vt/stream"
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    t0 = time.perf_counter()
    events: list[dict] = []
    complete = None
    try:
        resp = OPENER.open(req, timeout=900)
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                msg = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            events.append(msg)
            if msg.get("type") == "complete":
                complete = msg
                break
    except urllib.error.HTTPError as e:
        return {"ok": False, "wall_s": round(time.perf_counter() - t0, 1),
                "error": f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"}
    wall = round(time.perf_counter() - t0, 1)
    if not complete:
        return {"ok": False, "wall_s": wall, "error": f"no complete frame; events={len(events)}"}
    summ = complete.get("summary") or {}
    results = []
    for r in summ.get("results") or []:
        res = r.get("result") or {}
        results.append({"filename": r.get("filename"), "success": bool(r.get("success")),
                        "markdown_path": jkey(res, "markdown_path"),
                        "chars": len(jkey(res, "markdown") or ""),
                        "image_count": res.get("image_count", 0)})
    ok = summ.get("successful") == len(PDFS) and all(r["markdown_path"] for r in results)
    return {"ok": ok, "wall_s": wall, "total": summ.get("total"),
            "successful": summ.get("successful"), "failed": summ.get("failed"),
            "results": results, "event_count": len(events)}


def sse_chat(prompt: str, kb_ids: list, timeout_s: int = 480) -> dict:
    payload = {"prompt": prompt, "cwd": str(REPO), "engine": "claude",
               "maxTurns": 14, "stream": True, "kbEnhanced": True, "kbIds": kb_ids}
    req = urllib.request.Request(f"{WEB}/api/claude/chat", method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    t0 = time.perf_counter()
    tools: list[str] = []
    texts: list[str] = []
    frame = None
    try:
        resp = OPENER.open(req, timeout=timeout_s)
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                msg = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "assistant":
                for b in (msg.get("message") or {}).get("content", []):
                    if b.get("type") == "tool_use":
                        tools.append(b.get("name"))
                    elif b.get("type") == "text" and b.get("text"):
                        texts.append(str(b["text"]))
            elif msg.get("type") == "result":
                frame = msg
    except Exception as e:  # noqa: BLE001
        return {"wall_s": round(time.perf_counter() - t0, 1), "error": str(e),
                "tools": tools, "answer": "".join(texts).strip()}
    return {"wall_s": round(time.perf_counter() - t0, 1), "tools": tools,
            "answer": str((frame or {}).get("result") or "".join(texts)).strip()}


def search_top(kb_id: str, query: str) -> tuple[str, float]:
    s = client.call("kb_search_vector", {"kb_id": kb_id, "query": query, "top_k": 2},
                    timeout=300)
    r = (s.get("results") or [{}])[0]
    return (r.get("doc_path") or ""), (r.get("score") or 0)


client = McpClient(REPO)


def main() -> int:
    # ---- 1. demo KB ----
    kb = client.call("kb_create", {"name": KB_NAME,
                                   "description": "实机演示：3 篇真实论文批量解析入库 + 2 个真实仓库文档直接入库 + 检索增强查询"},
                     timeout=120)
    kb_id = jkey(jkey(kb, "knowledgeBase", default={}), "kb_id") or jkey(kb, "kb_id")
    step("kb_create", bool(kb_id), f"kb_id={kb_id}")
    DETAIL["steps"]["kb"] = {"kb_id": kb_id, "name": KB_NAME}

    # ---- 2. batch parse (true SSE batch endpoint) ----
    b = batch_parse()
    md_by_file = {r["filename"]: r["markdown_path"] for r in b.get("results", [])}
    step("BE batch parse SSE (3 PDFs concurrent)", b["ok"],
         f"wall={b['wall_s']}s successful={b.get('successful')}/{b.get('total')} "
         f"events={b.get('event_count')}")
    for r in b.get("results", []):
        print(f"       {r['filename']}: chars={r['chars']} images={r['image_count']}", flush=True)
    DETAIL["steps"]["batch_parse"] = b
    if not b["ok"]:
        print(json.dumps({k: v for k, v in b.items() if k != 'results'}, ensure_ascii=False)[:400])
        return finish()

    # ---- 3. ingest parsed docs (A5: save_parsed per file) ----
    parsed_paths = {}
    for pdf, r in zip(PDFS, b["results"]):
        md = md_by_file.get(pdf.name) or ""
        md_abs = str((REPO / md).resolve()) if md and not Path(md).is_absolute() else md
        saved = client.call("kb_doc_save_parsed",
                            {"parent_id": kb_id, "markdown_path": md_abs,
                             "images_dir": "", "source_filename": pdf.name}, timeout=600)
        dp = None
        for f in saved.get("files") or []:
            dp = jkey(f, "path", "doc_path", "name") or dp
        for it in saved.get("items") or []:
            for f in it.get("files") or []:
                dp = jkey(f, "path", "doc_path", "name") or dp
        parsed_paths[pdf.name] = dp
        step(f"save_parsed {pdf.name}", bool(saved.get("success")) and bool(dp),
             f"path={dp}")

    # ---- 4. per-doc retrieval verification (parsed path) ----
    probes = [
        ("attention_is_all_you_need.pdf", "scaled dot-product attention multi-head"),
        ("rag_lewis2020.pdf", "non-parametric memory retrieval augmented generation"),
        ("llama.pdf", "LLaMA open foundation model training tokens"),
    ]
    for fname, q in probes:
        dp, score = search_top(kb_id, q)
        want = fname.replace(".pdf", "").split("_")[0].lower()
        hit = want in dp.lower() or dp.startswith(kb_id) is False and bool(dp)
        dp_ok = bool(dp)
        step(f"retrieve parsed doc: {fname}", dp_ok and want in dp.lower(),
             f"top1={dp[:70]!r} score={round(score, 3)}")

    # ---- 5. direct ingest WITHOUT parsing (kb_doc_create, real repo docs) ----
    direct_paths = {}
    for src, name in DIRECT_DOCS:
        content = src.read_text(encoding="utf-8", errors="replace")
        made = client.call("kb_doc_create", {"kb_id": kb_id, "name": name,
                                             "content": content}, timeout=300)
        dp = jkey(jkey(made, "document", default={}), "path") or jkey(made, "path")
        direct_paths[name] = dp
        step(f"direct ingest {src.name} ({len(content)} chars, no parsing)",
             bool(dp), f"path={dp}")
    DETAIL["steps"]["direct"] = direct_paths

    direct_probes = [
        ("平台架构说明-ARCHITECTURE.md", "平台三服务架构 FastAPI Nuxt MCP"),
        ("平台总览-README.md", "知识库 树索引 knowledge-base 配置"),
    ]
    for name, q in direct_probes:
        dp, score = search_top(kb_id, q)
        step(f"retrieve direct doc: {name}", name in (dp or ""),
             f"top1={dp[:70]!r} score={round(score, 3)}")

    stats = client.call("kb_search_stats", {"kb_id": kb_id}, timeout=120)
    chunk_count = jkey(jkey(stats, "stats", default={}), "chunk_count")
    step("KB totals (kb_search_stats)", bool(chunk_count), f"chunk_count={chunk_count}")
    DETAIL["steps"]["stats"] = jkey(stats, "stats")

    # ---- 6. retrieval-augmented queries (web chat SSE, kbEnhanced) ----
    queries = [
        ("RAG-EN", "According to the knowledge base: what memory types does Retrieval-Augmented Generation (Lewis et al. 2020) combine, and what are the two RAG variants? Cite the document.",
         ["retrieval", "non-parametric", "parametric", "RAG-Sequence", "RAG-Token"]),
        ("ARCH-ZH", "根据知识库回答：本平台由哪几个服务组成？各自负责什么、使用什么端口？请给出依据文档名。",
         ["服务", "8770", "6789", "8000", "backend", "web", "MCP", "架构"]),
        ("CROSS", "综合知识库内容回答：Transformer 的自注意力机制与检索增强生成中的检索机制，各自解决什么问题？一句话对比后分别给出依据文档。",
         ["注意力", "attention", "检索", "retrieval"]),
    ]
    for tag, prompt, markers in queries:
        ans = sse_chat(prompt, [kb_id])
        hit = any(m.lower() in ans.get("answer", "").lower() for m in markers)
        step(f"RAG query {tag}", bool(ans.get("answer")) and hit,
             f"wall={ans.get('wall_s')}s tools={len(ans.get('tools', []))} "
             f"answer_head={ans.get('answer', '')[:110]!r}")
        DETAIL["steps"][f"rag_{tag}"] = ans

    return finish()


def finish() -> int:
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n==== demo summary: {len(RESULTS) - failed} passed, {failed} failed ====", flush=True)
    DETAIL["summary"] = {"passed": len(RESULTS) - failed, "failed": failed,
                         "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in RESULTS]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "batch_demo_results.json").write_text(json.dumps(DETAIL, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    if DETAIL["steps"].get("kb"):
        print(f"LIVE DEMO KB kept: {DETAIL['steps']['kb']['name']} "
              f"(kb_id={DETAIL['steps']['kb']['kb_id']}) — http://127.0.0.1:6789")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
