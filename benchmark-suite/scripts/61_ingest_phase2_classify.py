#!/usr/bin/env python3
"""Ingest Phase 2 (A3d+A5+A6+A6-V+A9) — 按 Archival 内容分类路由到 5 个门类库.

分类依据 = Phase 1 survey 的真实正文摘要(人工/AI 逐篇研读), 非文件名先验。
流程: 建 5 门类库 → 逐篇读 Inbox 全文 → kb_doc_create 路由入库 → 打内容标签
→ 删中转库 → batch-index → 逐篇 A6-V 探针 → 门类图谱 → A9 报告。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import BACKEND, McpClient, http_post  # noqa: E402

INBOX = "Papers-Inbox"

# ── A3d 分类判断工件 ────────────────────────────────────────────────────────
# 分类由 Archival(执行 Agent) 研读 Phase1 的 results/ingest_survey.json 后
# 产出 data/papers/classification.json(本脚本只消费, 不内嵌任何判断):
# {"categories": {"<门类库名>": "<描述>"}, "assign": {"<arxiv_id>":
#   {"kb": "<门类库名>", "tags": ["...", "..."]}}}
_clf_path = SUITE / "data" / "papers" / "classification.json"
_clf = json.loads(_clf_path.read_text(encoding="utf-8"))
KBS = _clf["categories"]
CLASSIFY = {k: (v["kb"], v["tags"]) for k, v in _clf["assign"].items()}
C = N = L = E = S = None  # 兼容旧引用(已不再使用字面量门类名)


def read_full(mc, doc_path: str) -> str:
    parts, offset = [], 0
    for _ in range(80):
        r = mc.call("kb_doc_read", {"kb_id": INBOX, "doc_path": doc_path,
                                    "offset": offset, "limit": 400,
                                    "max_chars": 40000}, timeout=120)
        c = (r or {}).get("content", "")
        parts.append(c)
        if not (r or {}).get("truncated"):
            break
        offset += c.count("\n") + 1
    return "\n".join(parts)


def main() -> int:
    survey = json.loads((SUITE / "results" / "ingest_survey.json")
                        .read_text(encoding="utf-8"))
    unclassified = [p for p in survey["papers"]
                    if p["arxiv_id"] not in CLASSIFY]
    if unclassified:
        raise RuntimeError(f"unclassified papers: "
                           f"{[p['arxiv_id'] for p in unclassified]}")

    mc = McpClient()
    # 建 5 门类库(已存在则复用)
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    have = {k.get("name") for k in cat.get("catalog") or []}
    for name, desc in KBS.items():
        if name not in have:
            mc.call("kb_create", {"name": name, "description": desc}, timeout=180)
            print(f"[kb] created {name}", flush=True)
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    kb_uuid = {k.get("name"): (k.get("kb_id") or k.get("name"))
               for k in cat.get("catalog") or []}

    # 路由: Inbox 全文 → 门类库 create + 标签
    docs = mc.call("kb_get_documents", {"kb_id": INBOX}, timeout=180)
    ds = docs.get("documents") or []
    t0 = time.perf_counter()
    routed = []
    for p in survey["papers"]:
        kb_name, tags = CLASSIFY[p["arxiv_id"]]
        match = next((d for d in ds
                      if str(d.get("name", "")).startswith(p["slug"])), None)
        if not match:
            raise RuntimeError(f"doc not found in Inbox: {p['slug']}")
        doc_name = str(match.get("name"))
        doc_path = match.get("path") or f"{INBOX}/{doc_name}"
        content = read_full(mc, doc_path)
        if len(content) < 200:
            raise RuntimeError(f"content too short for {p['slug']}: {len(content)}")
        created = mc.call("kb_doc_create",
                          {"kb_id": kb_name, "name": doc_name,
                           "content": content,
                           "description": p["title"][:160]}, timeout=180)
        if not (isinstance(created, dict) and created.get("success", True)):
            raise RuntimeError(f"create failed {p['slug']} -> {kb_name}: "
                               f"{str(created)[:200]}")
        tag_r = mc.call("kb_doc_update_tags",
                        {"kb_id": kb_name,
                         "doc_path": f"{kb_name}/{doc_name}",
                         "tags": [p["field"]] + tags}, timeout=120)
        routed.append({"slug": p["slug"], "field": p["field"],
                       "arxiv_id": p["arxiv_id"], "kb": kb_name,
                       "tags": [p["field"]] + tags,
                       "chars": len(content),
                       "tag_ok": bool((tag_r or {}).get("success", True))})
        print(f"[routed] {kb_name} <- {p['slug'][:48]} ({len(content)} ch)",
              flush=True)

    # 删中转库 → 显式重建各门类索引
    inbox_id = kb_uuid.get(INBOX)
    if inbox_id:
        mc.call("kb_delete", {"kb_id": inbox_id}, timeout=300)
        print("[A5] inbox removed", flush=True)
    n_indexed = 0
    for name in KBS:
        docs_list = mc.call("kb_get_documents", {"kb_id": name}, timeout=180)
        ds2 = docs_list.get("documents") or []
        paths = [d.get("path") or f"{name}/{d.get('name', '')}"
                 for d in ds2]
        for s in range(0, len(paths), 20):
            r = http_post(f"{BACKEND}/api/v1/search/batch-index",
                          {"kb_id": kb_uuid.get(name, name),
                           "doc_paths": paths[s:s + 20], "force": True},
                          timeout=900)
            n_indexed += len(r.get("indexed", []))
        print(f"[index] {name}: {len(paths)} docs", flush=True)
    print(f"[index] total {n_indexed} docs indexed", flush=True)

    # A6-V: 逐篇在“自己的门类库”内可检索
    deadline = time.time() + 600
    pending = {r_["slug"]: r_ for r_ in routed}
    while pending and time.time() < deadline:
        time.sleep(8)
        for slug in list(pending):
            r_ = pending[slug]
            pr = mc.call("kb_search_vector",
                         {"query": r_["slug"].replace("-", " ")[:60],
                          "kb_id": r_["kb"], "top_k": 3}, timeout=120)
            if any(str(h.get("doc_path", "")).startswith(r_["kb"] + "/")
                   for h in (pr.get("results") or [])):
                r_["verify_ok"] = True
                del pending[slug]
    for r_ in routed:
        r_.setdefault("verify_ok", False)

    # 图谱(每门类)
    graph = {}
    for name in KBS:
        g = mc.call("kb_graph_build", {"kb_id": name, "force": True}, timeout=300)
        graph[name] = bool((g or {}).get("success", True))
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    final = {k.get("name"): k for k in cat.get("catalog") or []}
    mc.close()

    per_kb: dict[str, int] = {}
    for r_ in routed:
        per_kb[r_["kb"]] = per_kb.get(r_["kb"], 0) + 1
    out = {"seconds": round(time.perf_counter() - t0, 1),
           "total": len(routed),
           "verified": sum(1 for r_ in routed if r_["verify_ok"]),
           "per_kb": per_kb, "graph": graph, "catalog": per_kb,
           "routed": routed}
    (SUITE / "results" / "ingest_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"total": out["total"], "verified": out["verified"],
                      "per_kb": per_kb, "graph": graph},
                     ensure_ascii=False, indent=1))
    return 0 if out["verified"] == out["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
