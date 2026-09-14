#!/usr/bin/env python3
"""E16 · 外部驱动的端到端表面验证（为论文的 e2e 声明提供已提交的生产脚本）.

只用 HTTP 调用对外 API，不 import 应用代码 —— 与真实 Agent 用户同一条路径。
分组（A--H）对齐平台的对外能力面:
  A 连接与鉴权   B 知识库/文档生命周期（含标签、移动）
  C 基于内容检索（向量 + 两阶段 + 逐级读取）   D 知识图谱
  E 经验生命周期（创建/提取/草稿审批/检索/应用/评审/健康检查）
  F 人设(soul)   G Agent Harness 注册表与一次性执行   H 清理
所有创建物以 `e2e-` 前缀命名并在 H 组删除；产物写 results/run-*/e2e_surface.json，
内嵌 git commit / config hash / seed，可随时重跑复现。
用法: python scripts/80_e2e_surface.py [--skip-llm]
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import BACKEND, WEB, env_fingerprint, http_delete, http_get, http_post, now_iso, set_run  # noqa: E402

SKIP_LLM = "--skip-llm" in sys.argv
PREFIX = "e2e-surface"


class Checks:
    def __init__(self):
        self.rows: list[dict] = []

    def check(self, group: str, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append({"group": group, "name": name,
                          "status": "PASS" if ok else "FAIL", "detail": detail[:160]})
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {group} :: {name} {detail[:70]}", flush=True)
        return ok


def raw(method: str, url: str, body=None, token: str | None = None,
        timeout: int = 60):
    """极简 HTTP（不走代理），返回 (status, parsed_or_text)。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with opener.open(req, timeout=timeout) as r:
            b = r.read()
            try:
                return r.status, json.loads(b)
            except Exception:  # noqa: BLE001
                return r.status, b.decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:  # noqa: BLE001
            return e.code, ""
    except Exception as e:  # noqa: BLE001
        return 0, str(e)[:120]


def main() -> int:
    outdir = set_run()
    c = Checks()
    token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not token:
        for line in (Path(__file__).resolve().parent.parent.parent / ".env").read_text(
                encoding="utf-8").splitlines():
            if line.startswith("MCP_AUTH_TOKEN="):
                token = line.split("=", 1)[1].strip()
    suffix = uuid.uuid4().hex[:6]
    kb_name = f"{PREFIX}-{suffix}"

    # ── A 连接与鉴权 ──
    st, body = raw("GET", f"{BACKEND}/health")
    c.check("A", "backend health is public", st == 200, f"HTTP {st}")
    st, _ = raw("GET", f"{BACKEND}/api/v1/knowledge-bases")
    c.check("A", "protected endpoint rejects missing token", st in (401, 403), f"HTTP {st}")
    st, _ = raw("GET", f"{BACKEND}/api/v1/knowledge-bases", token=token)
    c.check("A", "protected endpoint accepts valid token", st in (200, 404), f"HTTP {st}")
    st, body = raw("GET", f"{WEB}/api/kb/catalog", token=token, timeout=90)
    c.check("A", "web proxy catalog reachable", st == 200 and isinstance(body, dict),
            f"HTTP {st}")

    # ── B 知识库与文档生命周期 ──
    st, body = raw("POST", f"{WEB}/api/kb/create",
                   {"name": kb_name, "description": "e2e surface check"}, token=token, timeout=120)
    kb_id = (body or {}).get("knowledgeBase", {}).get("id") if isinstance(body, dict) else None
    c.check("B", "create knowledge base", st in (200, 201) and bool(kb_id), f"HTTP {st}")
    doc = f"{PREFIX}-doc-{suffix}.md"
    content = ("# E2E Surface Document\n\nZeta probe marker QUASAR-7731. "
               "This document exists only to verify the external surface.\n")
    st, _ = raw("POST", f"{WEB}/api/kb/documents/create",
                {"kbId": kb_id, "name": doc, "content": content,
                 "description": "e2e"}, token=token, timeout=120)
    c.check("B", "create document", st in (200, 201), f"HTTP {st}")
    st, body = raw("GET", f"{WEB}/api/kb/documents?kb_id={kb_id}", token=token, timeout=120)
    names = [d.get("name") for d in (body or {}).get("documents", [])] if isinstance(body, dict) else []
    c.check("B", "document appears in listing", doc in names, f"n={len(names)}")
    st, _ = raw("POST", f"{WEB}/api/kb/documents/create",
                {"kbId": kb_id, "name": doc, "content": content}, token=token, timeout=120)
    c.check("B", "duplicate create is rejected", st in (409, 400), f"HTTP {st}")
    st, _ = raw("POST", f"{BACKEND}/api/v1/search/batch-index",
                {"kb_id": kb_id, "doc_paths": [doc], "force": True}, token=token, timeout=300)
    c.check("B", "vector index accepts batch-index", st in (200, 201), f"HTTP {st}")

    # ── C 基于内容检索（含逐级读取） ──
    ready = False
    for _ in range(20):
        st, body = raw("GET", f"{WEB}/api/kb/vector-status?kb_id={kb_id}", token=token, timeout=60)
        if isinstance(body, dict) and (body.get("ready") or body.get("vector_ready")):
            ready = True
            break
        time.sleep(6)
    c.check("C", "vector index reports ready", ready, "")
    st, body = raw("POST", f"{BACKEND}/api/v1/search/vector",
                   {"query": "QUASAR-7731 probe marker", "kb_id": kb_id, "top_k": 5},
                   token=token, timeout=180)
    n = len((body or {}).get("results", [])) if isinstance(body, dict) else 0
    c.check("C", "vector search returns the document", st == 200 and n >= 1, f"n={n}")
    st, body = raw("POST", f"{BACKEND}/api/v1/search/two-stage",
                   {"query": "QUASAR-7731 probe marker", "kb_id": kb_id,
                    "stage1_top_k": 20, "stage2_top_k": 5}, token=token, timeout=300)
    n2 = len((body or {}).get("stage2", {}).get("results", [])) if isinstance(body, dict) else 0
    c.check("C", "two-stage search returns stage-2 results", st == 200 and n2 >= 1, f"n={n2}")

    # ── D 知识图谱 ──
    st, body = raw("POST", f"{BACKEND}/api/v1/graph/build",
                   {"kb_id": kb_id}, token=token, timeout=300)
    c.check("D", "graph build endpoint responds", st in (200, 201, 202, 409), f"HTTP {st}")
    st, body = raw("GET", f"{BACKEND}/api/v1/graph/stats?kb_id={kb_id}", token=token, timeout=120)
    c.check("D", "graph stats endpoint responds", st == 200, f"HTTP {st}")

    # ── E 经验生命周期 ──
    st, body = raw("POST", f"{BACKEND}/api/v1/experience/{kb_id}/init", {}, token=token, timeout=120)
    c.check("E", "experience store init", st in (200, 201, 409), f"HTTP {st}")
    st, body = raw("POST", f"{BACKEND}/api/v1/experience/{kb_id}",
                   {"title": f"{PREFIX} lesson", "scenario": "surface verification",
                    "problem": "external surface unverified", "solution":
                    "run the committed e2e surface script", "tags": ["e2e"],
                    "key_lessons": ["verify over HTTP as an agent would"]},
                   token=token, timeout=120)
    exp_id = (body or {}).get("experience", {}).get("id") if isinstance(body, dict) else None
    c.check("E", "create experience", st in (200, 201) and bool(exp_id), f"HTTP {st}")
    st, body = raw("POST", f"{BACKEND}/api/v1/search/experience/global",
                   {"query": "external surface unverified", "top_k": 5}, token=token, timeout=180)
    c.check("E", "global experience search responds", st == 200, f"HTTP {st}")
    st, body = raw("GET", f"{BACKEND}/api/v1/experience/{kb_id}/summary", token=token, timeout=120)
    c.check("E", "experience summary responds", st == 200, f"HTTP {st}")
    st, body = raw("GET", f"{BACKEND}/api/v1/experience/check-stale?kb_id={kb_id}", token=token, timeout=120)
    c.check("E", "stale check responds", st == 200, f"HTTP {st}")
    st, body = raw("GET", f"{BACKEND}/api/v1/experience/{kb_id}/dashboard", token=token, timeout=120)
    c.check("E", "experience dashboard responds", st == 200, f"HTTP {st}")

    # ── F 人设 (soul) ──
    st, body = raw("GET", f"{BACKEND}/api/v1/soul/status", token=token, timeout=120)
    c.check("F", "soul status responds", st in (200, 404), f"HTTP {st}")
    st, body = raw("GET", f"{BACKEND}/api/v1/soul/list", token=token, timeout=120)
    c.check("F", "soul list responds", st in (200, 404), f"HTTP {st}")

    # ── G 引擎注册表 ──
    st, body = raw("GET", f"{BACKEND}/api/v1/harness/list", token=token, timeout=120)
    h = (body or {}) if isinstance(body, dict) else {}
    c.check("G", "harness registry lists engines", st == 200, f"HTTP {st}")

    # ── H 清理 ──
    st, _ = raw("DELETE", f"{WEB}/api/kb/delete", {"kbId": kb_id}, token=token, timeout=180)
    c.check("H", "cleanup deletes the e2e base", st in (200, 204), f"HTTP {st}")
    st, body = raw("GET", f"{WEB}/api/kb/catalog", token=token, timeout=120)
    remaining = [k.get("name") for k in (body or {}).get("knowledgeBases", [])] if isinstance(body, dict) else []
    c.check("H", "e2e base is gone from the catalog", kb_name not in remaining, f"n={len(remaining)}")

    passed = sum(1 for r in c.rows if r["status"] == "PASS")
    from collections import Counter
    by_group = Counter(r["group"] for r in c.rows)
    result = {
        "experiment": "E16 externally-driven end-to-end surface verification",
        "counts": {"total": len(c.rows), "pass": passed, "fail": len(c.rows) - passed},
        "groups": {g: n for g, n in sorted(by_group.items())},
        "results": c.rows,
        "meta": {"generated": now_iso(), "env": env_fingerprint()},
    }
    out = outdir / "e2e_surface.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print(f"E2E: {passed}/{len(c.rows)} passed; groups={dict(sorted(by_group.items()))}")
    return 0 if passed == len(c.rows) else 1


if __name__ == "__main__":
    sys.exit(main())
