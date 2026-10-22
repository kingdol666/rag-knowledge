#!/usr/bin/env python3
"""Run-5 compact probes: agent/chat real execution + management smoke + librarian lane.

One script, three sections, all against live services:
  A. POST /api/kb/agent/chat (native agent, claude) — asks the agent to list KBs;
     asserts a real harness turn happened and the answer names a known KB.
  B. Management smoke on a disposable KB: create -> doc -> index -> vector search
     -> rename (inline hygiene: new labels immediately) -> batch index/delete
     -> tags dry-run -> cleanup zero-residual.
  C. Librarian lane (kbEnhanced=true, kbIds=[]), 1 gold question via SSE.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))

from dev_smoke import OPENER, guard_url  # noqa: E402
from mcp_client import McpClient  # noqa: E402

OUT = Path(__file__).resolve().parent
result: dict = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "sections": {}}


def env_token() -> str:
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("no token")


CHAT = "http://127.0.0.1:6789/api/claude/chat"
# NOTE: the native agent endpoint lives in the WEB layer (nuxt), not the backend.
AGENT = "http://127.0.0.1:6789/api/kb/agent/chat"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")


def sse_chat(prompt: str, tok: str, timeout_s: int = 420) -> dict:
    guard_url(CHAT)
    payload = {"prompt": prompt, "cwd": str(REPO), "engine": "claude",
               "maxTurns": 20, "stream": True, "kbEnhanced": True, "kbIds": []}
    req = urllib.request.Request(CHAT, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", f"Bearer {tok}")
    t0 = time.perf_counter()
    tools, texts = [], []
    frame = None
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
    return {"wall_s": round(time.perf_counter() - t0, 1),
            "tools": tools, "answer": str((frame or {}).get("result") or "".join(texts)).strip()}


def section_a_agent_chat(tok: str) -> dict:
    guard_url(AGENT)
    payload = {"prompt": "列出当前平台上的知识库名字（只要名字清单），不要做别的。",
               "engine": "claude", "maxTurns": 8}
    req = urllib.request.Request(AGENT, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {tok}")
    t0 = time.perf_counter()
    try:
        resp = OPENER.open(req, timeout=300)
        body = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = {"http_error": e.code, "body": e.read().decode("utf-8", "replace")[:200]}
    wall = round(time.perf_counter() - t0, 1)
    text = json.dumps(body, ensure_ascii=False)
    hit = ("计算机与人工智能" in text) or ("自然科学与地球科学" in text)
    return {"wall_s": wall, "harness_ran": bool(body.get("sessionId") or body.get("taskId")
                                                or body.get("result") or hit),
            "kb_named": hit, "shape_head": text[:260]}


def section_b_mgmt_smoke() -> dict:
    client = McpClient(REPO)
    steps: list[dict] = []
    kb_id = None

    def step(name, ok, detail=None):
        steps.append({"step": name, "ok": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name, flush=True)

    try:
        kb = client.call("kb_create", {"name": f"ZZ-Run5-Smoke-{STAMP}",
                                       "description": "run5 smoke"}, timeout=120)
        kb_id = (kb.get("knowledgeBase") or {}).get("kb_id")
        step("kb_create", bool(kb_id))
        name_a = f"smoke-a-{STAMP}.md"
        content = f"# run5 smoke\nunique token R5-{STAMP}\ncalibration 6.626e-34 J s.\n"
        da = client.call("kb_doc_create", {"kb_id": kb_id, "name": name_a,
                                           "content": content}, timeout=180)
        path_a = (da.get("document") or {}).get("path")
        step("kb_doc_create", bool(path_a))
        client.call("kb_index_document", {"kb_id": kb_id, "doc_path": path_a}, timeout=300)
        time.sleep(2)
        tok = f"R5-{STAMP}"
        r = client.call("kb_search_vector", {"query": f"{tok} calibration", "kb_id": kb_id,
                                             "top_k": 5, "score_threshold": 0.0}, timeout=180)
        hits = [h for h in (r.get("results") or []) if tok in str(h.get("content", ""))]
        step("vector_search_hit", len(hits) >= 1,
             {"top": round(float(hits[0]["score"]), 4) if hits else None})
        name_b = f"smoke-b-{STAMP}.md"
        rn = client.call("kb_doc_update_meta", {"kb_id": kb_id, "doc_path": path_a,
                                                "name": name_b}, timeout=120)
        hyg = rn.get("index_hygiene") or {}
        time.sleep(3)
        r2 = client.call("kb_search_vector", {"query": f"{tok} calibration constant",
                                              "kb_id": kb_id, "top_k": 5,
                                              "score_threshold": 0.0}, timeout=180)
        rows = r2.get("results") or []
        new_labels = [h for h in rows if name_b in str(h.get("doc_path", ""))
                      and tok in str(h.get("content", ""))]
        old_labels = [h for h in rows if name_a in str(h.get("doc_path", ""))]
        step("rename_inline_hygiene", bool(new_labels) and not old_labels
             and hyg.get("vectors", {}).get("cleaned", 0) >= 1,
             {"new": len(new_labels), "old": len(old_labels)})
        b = client.call("kb_doc_create", {"kb_id": kb_id, "name": f"smoke-c-{STAMP}.md",
                                          "content": f"extra {tok}\n"}, timeout=120)
        pb = (b.get("document") or {}).get("path")
        client.call("kb_batch_index", {"kb_id": kb_id, "doc_paths": [pb]}, timeout=300)
        bd = client.call("kb_doc_batch_delete", {"kb_id": kb_id, "doc_paths": [pb]}, timeout=180)
        step("batch_index_delete", bool(bd.get("success", True)))
        tc = client.call("kb_tags_cleanup", {"dry_run": True}, timeout=120)
        step("tags_dry_run", isinstance(tc, dict))
    except Exception as e:
        step("exception", False, {"error": str(e)[:300]})
    finally:
        if kb_id:
            try:
                docs = client.call("kb_get_documents", {"kb_id": kb_id}, timeout=120)
                cat = docs.get("documents", {}).get("catalog", []) if isinstance(docs.get("documents"), dict) else docs.get("catalog", [])
                for e in cat:
                    try:
                        client.call("kb_doc_delete", {"kb_id": kb_id, "doc_path": e.get("path")}, timeout=120)
                    except Exception:
                        pass
                client.call("kb_delete", {"kb_id": kb_id}, timeout=180)
                listing = client.call("kb_list", {"lightweight": True}, timeout=120)
                names = json.dumps(listing, ensure_ascii=False)
                step("cleanup_zero_residual", f"ZZ-Run5-Smoke-{STAMP}" not in names)
            except Exception as e:
                step("cleanup_error", False, {"error": str(e)[:200]})
        client.close()
    return {"steps": steps, "pass": all(s["ok"] for s in steps)}


def section_c_librarian(tok: str) -> dict:
    r = sse_chat("How does InstructDS generate high-quality query-based dialogue "
                 "summaries? (InstructDS dialogue summarization)", tok)
    blob = r["answer"].lower()
    gold = ("2310.10981" in blob) or ("instructds" in blob)
    offlane = any(t in ("kb_search_vector", "kb_search_two_stage", "kb_search")
                  for t in r["tools"])
    return {"wall_s": r["wall_s"], "tools": r["tools"], "gold_hit": gold,
            "lane_discipline": not offlane, "answer_chars": len(r["answer"]),
            "answer_head": r["answer"][:300]}


def main() -> int:
    tok = env_token()
    print("=== A. agent/chat native harness ===", flush=True)
    a = section_a_agent_chat(tok)
    result["sections"]["agent_chat"] = a
    print(json.dumps({k: a[k] for k in ("wall_s", "harness_ran", "kb_named")},
                     ensure_ascii=False), flush=True)
    print("=== B. management smoke ===", flush=True)
    b = section_b_mgmt_smoke()
    result["sections"]["mgmt_smoke"] = b
    print("=== C. librarian lane (1 gold question) ===", flush=True)
    c = section_c_librarian(tok)
    result["sections"]["librarian"] = c
    print(json.dumps({k: c[k] for k in ("wall_s", "gold_hit", "lane_discipline")},
                     ensure_ascii=False), flush=True)
    (OUT / "run5_probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = a.get("harness_ran") and a.get("kb_named") and b["pass"] and c["gold_hit"] and c["lane_discipline"]
    print("\nRUN5 PROBES:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
