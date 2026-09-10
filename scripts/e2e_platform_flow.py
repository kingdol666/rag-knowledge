"""Platform end-to-end flow — 入库 → 检索 → 经验总结(mock) → 人格创建训练.

Prerequisites:
  - backend running (default http://127.0.0.1:8771, override with RAG_E2E_BACKEND)
  - web running     (default http://127.0.0.1:6789, override with RAG_E2E_WEB)
  - MCP service token present in .env (or RAG_E2E_TOKEN)

Usage: python scripts/e2e_platform_flow.py
Exit 0 = all green; 1 = failures.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent

BACKEND = os.environ.get("RAG_E2E_BACKEND", "http://127.0.0.1:8771").rstrip("/")
WEB = os.environ.get("RAG_E2E_WEB", "http://127.0.0.1:6789").rstrip("/")

# SSRF guard: this flow only ever talks to the local platform services.
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
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MCP_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


TOKEN = _token()

_results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail[:140]}" if detail else ""))


def http_json(method: str, url: str, body: dict | None = None,
              auth: bool = True, timeout: int = 120) -> tuple[int, dict | list | None]:
    assert_local_url(url)
    req = urllib.request.Request(url, method=method)
    if auth:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, None


DOC_CONTENT = """# Harness Integration Handbook

## Why one contract matters
Every execution engine implements the same job contract, so the scheduler,
API layer and frontend never branch on engine ids. Adding an engine means one
registry entry plus one spec — zero changes upstream.

## Probe before you integrate
Documentation drifts: versions remove flags (crush dropped --format json).
Write a probe script that spawns the real CLI and captures the first structured
event before writing the adapter. Same-family engines are NOT same-protocol:
qwen is a gemini fork yet uses a different output surface.

## Windows discipline
npm global CLIs are .cmd shims that CreateProcess cannot start directly — wrap
with a literal cmd.exe /d /s /c chain and validate every argument. Long prompts
go through stdin or @temp-file delivery, never argv.
"""


def main() -> int:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    kb_name = f"e2e-flow-{stamp}"

    print(f"=== Platform E2E flow ===\n  backend={BACKEND}\n  web={WEB}\n")

    # ── 0. health ──
    code, body = http_json("GET", f"{BACKEND}/api/v1/health", auth=False)
    step("backend health", code == 200 and "healthy" in json.dumps(body), str(body)[:80] if body else f"HTTP {code}")

    # ── 1. create KB (web tree-fs layer) ──
    code, body = http_json("POST", f"{WEB}/api/kb/create",
                           {"name": kb_name, "description": "E2E flow KB"})
    kb_id = ""
    if code == 200 and isinstance(body, dict) and body.get("success"):
        kb_id = (body.get("knowledgeBase") or {}).get("id", "")
    step("create KB", bool(kb_id), f"kb_id={kb_id}")

    # ── 2. create document ──
    doc_id = ""
    if kb_id:
        code, body = http_json("POST", f"{WEB}/api/kb/documents/create",
                               {"kbId": kb_id, "name": "harness-handbook.md",
                                "content": DOC_CONTENT,
                                "description": "integration handbook"})
        if code == 200 and isinstance(body, dict) and body.get("success"):
            doc_id = (body.get("document") or {}).get("id", "")
    step("create document", bool(doc_id), f"doc_id={doc_id}")

    # ── 3. index document (vector + graph) ──
    if doc_id:
        code, body = http_json("POST", f"{BACKEND}/api/v1/search/index-document",
                               {"doc_id": doc_id}, timeout=300)
        ok = code == 200 and isinstance(body, dict) and body.get("success", True)
        step("index document (vector+graph)", ok,
             f"chunks={body.get('chunks_indexed') if isinstance(body, dict) else code}")
    else:
        step("index document (vector+graph)", False, "no doc")

    time.sleep(1)

    # ── 4. retrieval ──
    code, body = http_json("POST", f"{BACKEND}/api/v1/search/two-stage",
                           {"query": "How do you integrate a new execution engine?",
                            "kb_id": kb_id, "stage1_top_k": 5, "stage2_top_k": 3,
                            "score_threshold": 0.1})
    hits = []
    if code == 200 and isinstance(body, dict):
        hits = (body.get("stage2") or {}).get("results") or body.get("results") or []
    step("two-stage retrieval", bool(hits), f"top1={hits[0].get('doc_path', '?') if hits else 'none'} score={hits[0].get('score') if hits else '-'}")

    # ── 5. meditation job with mock harness (knowledge-management job) ──
    if kb_id:
        code, body = http_json("POST", f"{BACKEND}/api/v1/meditation/run",
                               {"kb_id": kb_id, "trigger": "manual", "harness": "mock"},
                               timeout=180)
        ok = code == 200 and isinstance(body, dict) and body.get("success")
        drafts = len(body.get("drafts", [])) if isinstance(body, dict) else 0
        step("meditation run (mock harness, explicit job)", ok,
             f"drafts={drafts} harness={body.get('harness') if isinstance(body, dict) else code}")

    # ── 6. soul persona creation (template mode, mock harness) ──
    # 前端约定：先经 web 层创建 soul- 前缀的知识库，再 init/bootstrap。
    soul_name = f"soul-e2e-{stamp}"
    code, body = http_json("POST", f"{WEB}/api/kb/create",
                           {"name": soul_name, "description": "E2E soul persona"})
    kb_created = code == 200 and isinstance(body, dict) and body.get("success")
    step("create soul KB", kb_created, soul_name)
    code, body = http_json("POST", f"{BACKEND}/api/v1/soul/init",
                           {"soul_name": soul_name, "harness": "mock"}, timeout=600)
    ok = code == 200 and isinstance(body, dict) and (body.get("success") or body.get("soul_kb_id"))
    step("soul init (mock harness)", bool(ok),
         str(body.get("soul_kb_id") or body.get("error") if isinstance(body, dict) else code)[:80])

    # bootstrap completes config write + async profile generation
    code, body = http_json("POST", f"{BACKEND}/api/v1/soul/bootstrap",
                           {"soul_kb_id": soul_name, "harness": "mock", "async_mode": True})
    ok = code == 200 and isinstance(body, dict) and body.get("success", False)
    task_id = body.get("task_id") if isinstance(body, dict) else None
    step("soul bootstrap (async)", ok, f"task_id={task_id}")

    # poll the async task briefly (mock = fast)
    if task_id:
        final = None
        for _ in range(12):
            time.sleep(5)
            code, body = http_json("GET", f"{BACKEND}/api/v1/soul/tasks/{task_id}")
            if code == 200 and isinstance(body, dict):
                st = body.get("status") or (body.get("task") or {}).get("status")
                if st in ("completed", "done", "success", "failed", "error"):
                    final = body
                    break
        step("soul profile task finished", final is not None,
             json.dumps(final, ensure_ascii=False)[:120] if final else "timeout polling")

    # ── 7. soul list shows the persona ──
    code, body = http_json("GET", f"{BACKEND}/api/v1/soul/list")
    names = json.dumps(body, ensure_ascii=False)
    step("soul list contains persona", soul_name in names, soul_name)

    # ── summary ──
    failed = [r for r in _results if not r[1]]
    print(f"\n=== {len(_results) - len(failed)}/{len(_results)} steps passed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
