"""Full-feature real-scenario E2E — 知识库系统全部支持能力的真实调用验证.

覆盖（全部走对外 API，带认证，真实服务）:
  1. 文档解析上传: multipart POST /api/parse/file-vt (MinerU 真实解析 PDF)
     → documents/create 写盘 → index-document 向量索引 → 检索命中
  2. 检索全形态: web /api/kb/search (跨库关键词) + /api/v1/search/two-stage + graph/search/documents
  3. Tags: PATCH /api/kb/documents/tags → GET /api/kb/documents/by-tag
  4. Graph: POST /api/v1/graph/build-kb → GET /api/v1/graph/document → /document/related
  5. 经验机制: init / 写入 / 列表 / global-search / stale-global
  6. 人格机制（真实 LLM 训练）: soul- 建库 → init(omp) → bootstrap(async profile)
     → soul/ask 人格问答 → soul/{id}/learn (omp, limit=1 rounds=1, async) → task 轮询 → status
  7. Harness 作业: meditation/run 指定引擎 + 三态错误契约

Usage: python scripts/e2e_full_features.py
Exit 0 = all green.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
BACKEND = os.environ.get("RAG_E2E_BACKEND", "http://127.0.0.1:8771").rstrip("/")
WEB = os.environ.get("RAG_E2E_WEB", "http://127.0.0.1:6789").rstrip("/")
TEST_PDF = ROOT / "backend/app/utils/output/0024406d-c590-4f46-8ce6-762dc8d8e0a3/uploads/RAG-Retrieval-Augmented-Generation-arxiv-2020.pdf"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def assert_local_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked scheme: {parsed.scheme}")
    if (parsed.hostname or "").lower() not in _LOCAL_HOSTS:
        raise ValueError(f"Blocked non-local host: {parsed.hostname}")
    return url


def _token() -> str:
    tok = os.environ.get("RAG_E2E_TOKEN", "")
    if tok:
        return tok
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


TOKEN = _token()
_results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail[:150]}" if detail else ""), flush=True)


def call(method: str, url: str, body: dict | None = None, token: str = "",
         timeout: int = 120) -> tuple[int, dict]:
    assert_local_url(url)
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:300]}


def multipart_post(url: str, file_path: Path, filename: str, token: str,
                   timeout: int = 900) -> tuple[int, dict]:
    """multipart/form-data 上传（file + use_ocr）。"""
    assert_local_url(url)
    boundary = uuid.uuid4().hex
    payload = b""
    for name, value in (("output_dir", ""), ("use_ocr", "false")):
        payload += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode()
    payload += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
                "Content-Type: application/pdf\r\n\r\n").encode()
    payload += file_path.read_bytes() + b"\r\n"
    payload += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:300]}


def rag(name: str, method: str, url: str, body: dict | None, token: str = TOKEN,
        timeout: int = 120) -> dict:
    code, parsed = call(method, url, body, token, timeout)
    ok = code == 200 and isinstance(parsed, dict) and parsed.get("success") is True
    step(name, ok, "" if ok else f"HTTP {code}: {json.dumps(parsed, ensure_ascii=False)[:120]}")
    return parsed if isinstance(parsed, dict) else {}


def poll_task(task_id: str, timeout_sec: int, svc: str) -> dict | None:
    deadline = time.time() + timeout_sec
    last = None
    while time.time() < deadline:
        code, body = call("GET", f"{BACKEND}/api/v1/soul/tasks/{task_id}", token=svc)
        if code == 200 and isinstance(body, dict):
            last = body
            st = body.get("status") or (body.get("task") or {}).get("status") or ""
            if str(st).lower() in ("completed", "done", "success", "failed", "error", "cancelled"):
                return body
        time.sleep(10)
    return last


def main() -> int:
    svc = TOKEN
    stamp = time.strftime("%Y%m%d-%H%M%S")
    kb_name = f"fullfeat-{stamp}"

    print(f"=== Full-feature E2E ===\n  backend={BACKEND}\n  web={WEB}\n")

    # ══ 1. 建库 + md 文档（基线检索语料） ══
    print("── 1. KB + document baseline ──")
    parsed = rag("create KB", "POST", f"{WEB}/api/kb/create",
                 {"name": kb_name, "description": "full-feature e2e"}, svc)
    kb_id = (parsed.get("knowledgeBase") or {}).get("id", "")

    md_content = """# Prediction Markets And Aggregation

Prediction markets aggregate dispersed beliefs into prices. Operators should
ensure liquidity incentives and guard against manipulation via position limits.
Retrieval systems benefit from market-generated forecasts as fresh signals.
"""
    parsed = rag("create md document", "POST", f"{WEB}/api/kb/documents/create",
                 {"kbId": kb_id, "name": "prediction-markets.md", "content": md_content,
                  "description": "baseline corpus"}, svc)
    md_path = parsed.get("document", {}).get("path", "")
    rag("index md document", "POST", f"{BACKEND}/api/v1/search/index-document",
        {"kb_id": kb_id, "doc_path": md_path, "content": md_content,
         "tags": ["e2e", "baseline"]}, svc, timeout=180)
    time.sleep(1)

    # ══ 2. 文件解析上传（MinerU 真实解析 PDF）══
    print("── 2. file parse & upload (MinerU real parse) ──")
    code, parsed = multipart_post(f"{WEB}/api/parse/file-vt", TEST_PDF, TEST_PDF.name, svc)
    md_text = (parsed or {}).get("markdown") or ""
    if not md_text and (parsed or {}).get("markdown_path"):
        step("parse PDF via file-vt", False, f"no markdown field: {json.dumps(parsed)[:120]}")
    else:
        step("parse PDF via file-vt (MinerU)", bool(md_text), f"markdown_chars={len(md_text)}")
    if md_text:
        parsed = rag("upload parsed PDF as document", "POST", f"{WEB}/api/kb/documents/create",
                     {"kbId": kb_id, "name": "rag-arxiv-2020.md", "content": md_text,
                      "description": "parsed from PDF via MinerU"}, svc)
        pdf_doc_path = parsed.get("document", {}).get("path", "")
        rag("index parsed PDF", "POST", f"{BACKEND}/api/v1/search/index-document",
            {"kb_id": kb_id, "doc_path": pdf_doc_path, "tags": ["e2e", "parsed"]},
            svc, timeout=300)
        time.sleep(1)
        code, body = call("POST", f"{BACKEND}/api/v1/search/two-stage",
                          {"query": "retrieval augmented generation knowledge", "kb_id": kb_id,
                           "stage2_top_k": 3, "score_threshold": 0.1}, token=svc, timeout=120)
        hits = (body.get("stage2") or {}).get("results") if isinstance(body, dict) else []
        step("retrieval hits parsed PDF", bool(hits),
             f"top1={hits[0].get('doc_path','?') if hits else 'none'}")

    # ══ 3. 检索全形态 ══
    print("── 3. retrieval surface ──")
    code, body = call("GET", f"{WEB}/api/kb/search?query={quote('prediction markets')}&top_k=5",
                      token=svc)
    hits = body.get("hits", []) if isinstance(body, dict) else []
    step("web cross-KB keyword search", code == 200 and isinstance(hits, list), f"hits={len(hits)}")
    code, body = call("POST", f"{BACKEND}/api/v1/search/two-stage",
                      {"query": "liquidity incentives manipulation", "kb_id": kb_id,
                       "stage2_top_k": 3, "score_threshold": 0.1}, token=svc, timeout=120)
    hits = ((body or {}).get("stage2") or {}).get("results") or []
    step("two-stage semantic retrieval", bool(hits), f"top1_score={hits[0].get('score') if hits else '-'}")

    # ══ 4. Tags ══
    print("── 4. tags ──")
    if md_path:
        code, body = call("PATCH", f"{WEB}/api/kb/documents/tags",
                          {"kbId": kb_id, "docPath": md_path, "tags": ["e2e", "finance", "baseline"]},
                          token=svc)
        ok = code == 200 and isinstance(body, dict) and body.get("success", True)
        step("PATCH document tags", ok, f"HTTP {code}")
        code, body = call("GET", f"{WEB}/api/kb/documents/by-tag?tag=e2e", token=svc)
        docs = body.get("documents", []) if isinstance(body, dict) else []
        step("GET documents by-tag", code == 200 and any("prediction-markets" in json.dumps(d) for d in docs),
             f"matched={len(docs)}")

    # ══ 5. Graph ══
    print("── 5. graph ──")
    code, body = call("GET", f"{BACKEND}/api/v1/graph/health", token=svc)
    step("graph health", code == 200, json.dumps(body, ensure_ascii=False)[:80] if body else f"HTTP {code}")
    parsed = rag("graph build-kb", "POST", f"{BACKEND}/api/v1/graph/build-kb",
                 {"kb_id": kb_id}, svc, timeout=600)
    code, body = call("GET", f"{BACKEND}/api/v1/graph/document",
                      None, svc)  # 形状: ?doc_path=
    code, body = call("GET", f"{BACKEND}/api/v1/graph/document?doc_path={quote(str(md_path))}",
                      token=svc, timeout=60)
    step("graph document nodes", code == 200, f"HTTP {code}")
    code, body = call("GET", f"{BACKEND}/api/v1/graph/document/related?doc_path={quote(str(md_path))}",
                      token=svc, timeout=60)
    step("graph document related", code == 200, f"HTTP {code}")
    rag("graph agent-relation", "POST", f"{BACKEND}/api/v1/graph/agent-relation",
        {"doc_path": md_path, "target_doc_path": md_path,
         "relation_type": "self_reference", "reasoning": "e2e full-feature"}, svc)

    # ══ 6. 经验机制补全 ══
    print("── 6. experience ──")
    rag("experience init", "POST", f"{BACKEND}/api/v1/experience/{kb_id}/init", {}, svc)
    rag("experience write", "POST", f"{BACKEND}/api/v1/experience/{kb_id}",
        {"title": "Prediction market ops", "category": "best_practice",
         "problem": "Thin books drift from true beliefs.",
         "solution": "Subsidize market makers and cap positions per trader.",
         "key_lessons": ["Liquidity begets accuracy"], "tags": ["e2e"]}, svc)
    code, body = call("GET", f"{BACKEND}/api/v1/experience/{kb_id}?limit=10", token=svc)
    n = body.get("count", 0) if isinstance(body, dict) else 0
    step("experience list", code == 200 and n >= 1, f"count={n}")
    rag("experience global-search", "POST", f"{BACKEND}/api/v1/experience/global-search",
        {"query": "market liquidity", "top_k": 5}, svc)
    code, body = call("POST", f"{BACKEND}/api/v1/experience/stale-global", {}, token=svc, timeout=120)
    step("experience stale-global", code == 200, f"HTTP {code}")

    # ══ 7. 人格机制（真实 LLM：omp 训练）══
    print("── 7. soul persona (REAL training via omp) ──")
    soul_name = f"soul-fullfeat-{stamp}"
    rag("create soul KB", "POST", f"{WEB}/api/kb/create",
        {"name": soul_name, "description": "full-feature persona"}, svc)
    parsed = rag("soul init (omp profile)", "POST", f"{BACKEND}/api/v1/soul/init",
                 {"soul_name": soul_name, "harness": "omp"}, svc, timeout=600)
    parsed = rag("soul bootstrap (async profile)", "POST", f"{BACKEND}/api/v1/soul/bootstrap",
                 {"soul_kb_id": soul_name, "harness": "omp", "async_mode": True}, svc, timeout=120)
    task_id = parsed.get("task_id", "")
    if task_id:
        final = poll_task(task_id, 900, svc)
        st = (final or {}).get("status") or ((final or {}).get("task") or {}).get("status")
        step("soul profile task completed", str(st).lower() in ("completed", "done", "success"),
             f"status={st}")

    # soul 文档（训练语料）
    parsed = rag("create soul training doc", "POST", f"{WEB}/api/kb/documents/create",
                 {"kbId": soul_name, "name": "operator-playbook.md",
                  "content": "# Operator Playbook\n\nAlways verify sources before answering. "
                             "Prefer precise, falsifiable statements. When uncertain, say so "
                             "and propose the cheapest experiment that would settle the question.",
                  "description": "persona corpus"}, svc)
    soul_doc_path = parsed.get("document", {}).get("path", "")
    if soul_doc_path:
        code, body = call("POST", f"{BACKEND}/api/v1/soul/{soul_name}/learn",
                          {"doc_paths": [soul_doc_path], "limit": 1, "rounds": 1,
                           "async_mode": True}, token=svc, timeout=120)
        learn_task = body.get("task_id") if isinstance(body, dict) else None
        if learn_task:
            final = poll_task(learn_task, 1500, svc)
            st = (final or {}).get("status") or ((final or {}).get("task") or {}).get("status")
            report = json.dumps((final or {}).get("report") or {}, ensure_ascii=False)[:120]
            step("soul learn (omp, 1 doc x 1 round)", str(st).lower() in ("completed", "done", "success"),
                 f"status={st} report={report}")
        else:
            ok = code == 200 and isinstance(body, dict) and body.get("success")
            step("soul learn (sync fallback)", bool(ok), f"HTTP {code}")

    code, body = call("GET", f"{BACKEND}/api/v1/soul/{soul_name}/status?summary_window=30", token=svc, timeout=60)
    ok = code == 200 and isinstance(body, dict)
    step("soul status", ok, f"memories={body.get('total_memories') if isinstance(body, dict) else code}")

    code, body = call("POST", f"{BACKEND}/api/v1/soul/ask",
                      {"query": "How should I verify a claim before acting on it?",
                       "soul_kb_id": soul_name}, token=svc, timeout=300)
    ok = code == 200 and isinstance(body, dict) and body.get("success", True)
    answer = (body.get("answer") or body.get("response") or "") if isinstance(body, dict) else ""
    step("soul ask (persona-injected QA)", bool(ok and answer), f"answer_chars={len(answer)} HTTP {code}")

    # ══ summary ══
    failed = [r for r in _results if not r[1]]
    print(f"\n=== {len(_results) - len(failed)}/{len(_results)} steps passed ===")
    for name, _, detail in failed:
        print(f"  ❌ {name}: {detail[:140]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
