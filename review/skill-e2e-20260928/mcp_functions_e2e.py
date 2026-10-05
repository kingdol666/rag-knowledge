#!/usr/bin/env python3
"""zcode-harness 全功能 E2E：用 MCP stdio 探针把知识库各 skill 的功能域各测一遍。

覆盖映射（skill → 探针步骤）：
  knowledgebase-list    → S2 kb_list / S3 kb_get_documents
  knowledgebase-ingest  → S4 kb_create + S5 kb_doc_create + S6 kb_index_document
  knowledgebase-search  → S7 kb_search_vector（新文档可检索=A6-V）+ S8 kb_search_two_stage
  knowledgebase-manage  → S9 kb_doc_update_meta（改描述）
  knowledgebase-batch   → S10 kb_batch_index（force 重建）
  knowledgebase-graph   → S11 kb_graph_build + S12 kb_graph_search
  knowledgebase-experience → S13 experience_create + S14 experience_search_smart
  knowledgebase-librarian/search judge → S15 kb_laya_judge
  knowledgebase-verify  → S16 kb_search_stats + S17 kb_find_duplicates
  knowledgebase-manage  → S18-S19 清理（kb_doc_delete + kb_delete）+ S20 确认删除

原则：全部写入只发生在自建测试 KB 内，结束即清理；真实库零改动。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parents[2])
KB_NAME = "zz-e2e-20260928b"
MARKER = "ZZE2E 灶台女王量子编织 unique-marker-7741"
DOC_NAME = "zz-e2e-probe-doc.md"
TAG = "zz-e2e-tag"

proc = None


def spawn_client(attempts: int = 3) -> None:
    """Spawn kb-mcp and complete the MCP handshake; retry with a fresh
    instance on failure (transient uv/lock contention seen under load)."""
    global proc
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        p = subprocess.Popen(
            ["uv", "run", "--no-sync", "--directory", "kb-mcp", "python", "server.py"],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
            env={**os.environ, "PYTHONUTF8": "1"})
        watch = threading.Timer(120, p.kill)
        watch.start()
        try:
            time.sleep(3)  # let uv exec the interpreter before first write
            send(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "e2e-probe", "version": "1.0"}}})
            recv(p, 1, 45)
            send(p, {"jsonrpc": "2.0", "method": "notifications/initialized"})
            proc = p
            print(f"[e2e] MCP handshake OK (attempt {attempt})")
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"[e2e] handshake attempt {attempt} failed: {exc}")
            watch.cancel()
            try:
                p.stdin.close()
                p.terminate()
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                p.kill()
            time.sleep(2)
    raise RuntimeError(f"handshake failed after {attempts} attempts: {last_err}")


def send(p: subprocess.Popen, o: dict) -> None:
    p.stdin.write(json.dumps(o, ensure_ascii=False) + "\n")
    p.stdin.flush()


def recv(p: subprocess.Popen, want: int, timeout: float = 120) -> dict:
    dl = time.time() + timeout
    while time.time() < dl:
        line = p.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if m.get("id") == want:
            return m
    raise TimeoutError(f"no response for id={want}")


def call(rid: int, name: str, args: dict, timeout: float = 120) -> dict:
    send(proc, {"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                "params": {"name": name, "arguments": args}})
    m = recv(proc, rid, timeout)
    if m.get("error"):
        raise RuntimeError(f"{name}: {json.dumps(m['error'])[:200]}")
    for b in (m.get("result") or {}).get("content", []):
        if b.get("type") == "text":
            try:
                d = json.loads(b["text"])
            except json.JSONDecodeError:
                d = {"raw": b["text"][:200]}
            return d
    return {}


def step(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"  {'✅' if ok else '❌'} {label} {('— ' + detail) if detail else ''}")


results: list[tuple[str, bool, str]] = []
spawn_client()
print("[e2e] proceeding with functional coverage")

rid = 10
# S2/S3 list
d = call(rid := rid + 1, "kb_list", {"lightweight": True})
kbs = d.get("catalog") or d.get("knowledgeBases") or []
step("list.kb_list", len(kbs) > 5, f"{len(kbs)} KBs")
d = call(rid := rid + 1, "kb_get_documents",
         {"lightweight": True, "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba"})
docs = d.get("catalog") or []
step("list.kb_get_documents", isinstance(docs, list) and len(docs) > 0, f"{len(docs)} docs in CS库")

# S4 ingest.kb_create（先清可能的历史残留）
d = call(rid := rid + 1, "kb_delete", {"kb_id": KB_NAME})
d = call(rid := rid + 1, "kb_create", {"name": KB_NAME, "description": "E2E probe KB (auto-deleted)"})
new_kb = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
step("ingest.kb_create", bool(new_kb), f"id={str(new_kb)[:12]}…")

# S5 ingest.kb_doc_create
content = f"# E2E Probe\n\n{MARKER}\n\n本文档用于 harness 全功能端到端探针，测完即删。\n"
d = call(rid := rid + 1, "kb_doc_create",
         {"kb_id": new_kb, "name": DOC_NAME, "content": content,
          "description": f"{MARKER} probe doc", "tags": [TAG]})
doc_path = d.get("doc_path") or d.get("path") or DOC_NAME
step("ingest.kb_doc_create", bool(d.get("doc_path") or d.get("path") or d.get("success", True)), f"path={doc_path}")

# S6 ingest.kb_index_document（显式索引）
d = call(rid := rid + 1, "kb_index_document",
         {"kb_id": new_kb, "doc_path": doc_path, "content": content,
          "doc_name": DOC_NAME, "description": f"{MARKER} probe doc"})
step("ingest.kb_index_document", "error" not in d or not d.get("error"), str(d)[:80])

# S7 search.kb_search_vector（A6-V：新文档可被向量检索到）
time.sleep(1)
d = call(rid := rid + 1, "kb_search_vector",
         {"query": MARKER, "kb_id": new_kb, "top_k": 5})
hits = d.get("results") or []
step("search.kb_search_vector(new doc)", len(hits) > 0, f"top score {hits[0].get('score') if hits else 'n/a'}")

# S8 search.kb_search_two_stage
d = call(rid := rid + 1, "kb_search_two_stage",
         {"query": MARKER, "kb_id": new_kb, "stage1_top_k": 5, "stage2_top_k": 3})
st2 = (d.get("stage2") or {}).get("results") or d.get("total_results")
step("search.kb_search_two_stage", bool(st2), str(st2)[:60])

# S9 manage.kb_doc_update_meta
d = call(rid := rid + 1, "kb_doc_update_meta",
         {"kb_id": new_kb, "doc_path": doc_path, "description": f"{MARKER} updated-desc"})
step("manage.kb_doc_update_meta", "error" not in d or not d.get("error"), str(d)[:60])

# S10 batch.kb_batch_index
d = call(rid := rid + 1, "kb_batch_index",
         {"kb_id": new_kb, "doc_paths": [doc_path], "force": True})
step("batch.kb_batch_index", "error" not in d or not d.get("error"), str(d)[:60])

# S11 graph.kb_graph_build
d = call(rid := rid + 1, "kb_graph_build", {"kb_id": new_kb, "force": True})
step("graph.kb_graph_build", "error" not in d or not d.get("error"), str(d)[:60])

# S12 graph.kb_graph_search
d = call(rid := rid + 1, "kb_graph_search", {"keyword": MARKER.split()[0], "limit": 5})
g = d.get("documents") or d.get("results") or []
step("graph.kb_graph_search", "error" not in d or not d.get("error"), str(d)[:60])

# S13 experience.experience_create
d = call(rid := rid + 1, "experience_create",
         {"kb_id": new_kb, "title": "E2E probe experience",
          "scenario": f"{MARKER} scenario", "problem": "how to verify e2e",
          "solution": "create → search → judge → cleanup", "category": "tip"})
exp_ok = ("error" not in d) or not d.get("error")
step("experience.experience_create", exp_ok, str(d)[:60])

# S14 experience.experience_search_smart
d = call(rid := rid + 1, "experience_search_smart", {"query": MARKER, "kb_id": new_kb})
exps = d.get("results") or d.get("experiences") or []
step("experience.experience_search_smart", "error" not in d or not d.get("error"), str(d)[:60])

# S15 librarian/search verify judge（真实引擎，小文档）
d = call(rid := rid + 1, "kb_laya_judge",
         {"query": "what is this probe document about",
          "documents": json.dumps([{"kb_id": new_kb, "doc_path": doc_path,
                                    "content": content}], ensure_ascii=False),
          "criterion": "evidence"}, timeout=240)
step("judge.kb_laya_judge", d.get("real_engine") is True,
     f"scored={d.get('scored_count')} survivors={d.get('survivor_count')} resp={len(json.dumps(d))}ch")

# S16 verify.kb_search_stats
d = call(rid := rid + 1, "kb_search_stats", {"kb_id": new_kb})
step("verify.kb_search_stats", "error" not in d or not d.get("error"), str(d)[:60])

# S17 verify.kb_find_duplicates
d = call(rid := rid + 1, "kb_find_duplicates", {"kb_id": new_kb, "threshold": 0.9})
step("verify.kb_find_duplicates", "error" not in d or not d.get("error"), str(d)[:60])

# S18 manage.kb_doc_delete
d = call(rid := rid + 1, "kb_doc_delete", {"kb_id": new_kb, "doc_path": doc_path})
step("manage.kb_doc_delete", "error" not in d or not d.get("error"), str(d)[:60])

# S19 manage.kb_delete
d = call(rid := rid + 1, "kb_delete", {"kb_id": KB_NAME})
step("manage.kb_delete", "error" not in d or not d.get("error"), str(d)[:60])

# S20 确认清理
d = call(rid := rid + 1, "kb_list", {"lightweight": True})
kbs2 = d.get("catalog") or d.get("knowledgeBases") or []
gone = all((k.get("name") != KB_NAME) for k in kbs2)
step("cleanup.verify_gone", gone, f"{len(kbs2)} KBs remain")

try:
    proc.stdin.close()
    proc.terminate()
    proc.wait(timeout=10)
except Exception:
    proc.kill()

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n[e2e] {passed}/{len(results)} steps passed")
sys.exit(0 if passed == len(results) else 1)
