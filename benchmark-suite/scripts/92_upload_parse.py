#!/usr/bin/env python3
"""Step 2 — 文档解析上传测试: papers/ 全部 PDF 走官方链路入 Papers 库.

parse_doc(MinerU) → kb_doc_save_parsed → batch-index force → 逐篇向量探针,
外加目录/图谱两个简单功能检查。输出 results/upload_parse.json。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import BACKEND, McpClient, http_post  # noqa: E402

PAPERS = SUITE / "data" / "papers"
KB_NAME = "Papers"
PARSE_TIMEOUT = 900
INDEX_WAIT = 600


def poll_parse(mc, task_id: str) -> dict:
    # kb-mcp task_registry 状态词汇: running | done | error
    deadline = time.time() + PARSE_TIMEOUT
    while time.time() < deadline:
        r = mc.call("parse_task_status", {"task_id": task_id}, timeout=120)
        st = str((r or {}).get("status") or "").lower()
        if st in ("done", "success", "succeeded", "completed", "finished"):
            return r
        if st == "error":
            raise RuntimeError(f"parse failed: {str(r)[:300]}")
        time.sleep(8)
    raise RuntimeError(f"parse timeout after {PARSE_TIMEOUT}s")


def read_doc_full(mc, doc_path: str) -> str:
    parts, offset = [], 0
    for _ in range(60):
        r = mc.call("kb_doc_read", {"kb_id": KB_NAME, "doc_path": doc_path,
                                    "offset": offset, "limit": 400,
                                    "max_chars": 40000}, timeout=120)
        content = (r or {}).get("content", "")
        parts.append(content)
        if not (r or {}).get("truncated"):
            break
        offset += content.count("\n") + 1
    return "\n".join(parts)


def main() -> int:
    manifest = json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    mc = McpClient()

    # 删旧建新(确定性)
    r = mc.call("kb_list", {"lightweight": True}, timeout=120)
    for k in r.get("catalog") or []:
        if k.get("name") == KB_NAME:
            mc.call("kb_delete", {"kb_id": k.get("kb_id") or k.get("name")},
                    timeout=300)
            print(f"[reset] deleted {k.get('name')}", flush=True)
    mc.call("kb_create", {"name": KB_NAME,
                          "description": "multi-field real papers "
                          "(parse/upload benchmark)"}, timeout=180)

    # 逐篇: 官方解析链路入库
    records = []
    for p in manifest["papers"]:
        pdf = PAPERS / p["pdf"]
        slug = pdf.stem
        t1 = time.perf_counter()
        task = mc.call("parse_doc", {"file_path": str(pdf)}, timeout=300)
        task_id = (task or {}).get("task_id") or ""
        if not task_id:
            raise RuntimeError(f"parse_doc no task_id: {str(task)[:200]}")
        poll_parse(mc, task_id)
        saved = mc.call("kb_doc_save_parsed",
                        {"parent_id": KB_NAME, "task_id": task_id,
                         "source_filename": f"{slug}.md",
                         "description": p["title"][:160]}, timeout=300)
        if not (isinstance(saved, dict) and saved.get("success", True)):
            raise RuntimeError(f"save_parsed failed for {slug}: {str(saved)[:300]}")
        print(f"[parsed] {slug} in {time.perf_counter() - t1:.0f}s", flush=True)
        records.append({"slug": slug, "field": p["field"], "title": p["title"],
                        "parse_seconds": round(time.perf_counter() - t1, 1)})

    # 显式批量索引(确定性) + 目录核对
    docs_list = mc.call("kb_get_documents", {"kb_id": KB_NAME}, timeout=180)
    kb_docs = docs_list.get("documents") or []
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    kb_uuid = next((k.get("kb_id") for k in cat.get("catalog") or []
                    if k.get("name") == KB_NAME), KB_NAME)
    paths = [d.get("path") or f"{KB_NAME}/{d.get('name', '')}" for d in kb_docs]
    n_indexed = 0
    for s in range(0, len(paths), 20):
        r = http_post(f"{BACKEND}/api/v1/search/batch-index",
                      {"kb_id": kb_uuid, "doc_paths": paths[s:s + 20],
                       "force": True}, timeout=900)
        n_indexed += len(r.get("indexed", []))
    print(f"[index] batch-index {n_indexed} docs", flush=True)

    # 逐篇探针(标题词)
    deadline = time.time() + INDEX_WAIT
    pending = {rec["slug"] for rec in records}
    while pending and time.time() < deadline:
        time.sleep(8)
        for slug in list(pending):
            pr = mc.call("kb_search_vector",
                         {"query": slug.replace("-", " ")[:60],
                          "kb_id": KB_NAME, "top_k": 3}, timeout=120)
            if any(str(h.get("doc_path", "")).startswith(KB_NAME + "/")
                   for h in (pr.get("results") or [])):
                pending.discard(slug)
                print(f"[probe] {slug} ok", flush=True)
    if pending:
        raise RuntimeError(f"index not queryable: {sorted(pending)}")
    for rec in records:
        rec["probe_ok"] = True

    # 简单功能检查: 图谱构建 + 标签目录
    graph = mc.call("kb_graph_build", {"kb_id": KB_NAME, "force": True},
                    timeout=300)
    graph_ok = bool((graph or {}).get("success", True))
    tags = mc.call("kb_tags_list", {"kb_id": KB_NAME}, timeout=120)
    tags_n = len((tags or {}).get("tags") or (tags or {}).get("catalog") or [])

    mc.close()
    out = {"kb": KB_NAME, "seconds": round(time.perf_counter() - t0, 1),
           "papers_total": len(records), "papers_parsed": len(records),
           "docs_in_catalog": len(kb_docs), "batch_indexed": n_indexed,
           "all_probes_ok": not pending, "graph_build_ok": graph_ok,
           "tags_count": tags_n, "papers": records}
    (SUITE / "results" / "upload_parse.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] {len(records)}/{len(records)} parsed, catalog={len(kb_docs)}, "
          f"graph_ok={graph_ok}, tags={tags_n}, {out['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
