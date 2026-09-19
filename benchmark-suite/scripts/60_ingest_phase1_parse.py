#!/usr/bin/env python3
"""Ingest Phase 1 (A2+A1) — 50 篇 PDF 经官方链路解析入中转库 Papers-Inbox,
并导出调研材料 survey.json(每篇标题+正文前 1400 字) 供 A3d 内容驱动分类。

分类(Archival)在 Phase 2 前基于本文件的真实正文完成。
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
KB = "Papers-Inbox"
PARSE_TIMEOUT = 900
INDEX_WAIT = 600


def poll_parse(mc, task_id: str) -> None:
    deadline = time.time() + PARSE_TIMEOUT
    while time.time() < deadline:
        r = mc.call("parse_task_status", {"task_id": task_id}, timeout=120)
        st = str((r or {}).get("status") or "").lower()
        if st in ("done", "success", "succeeded", "completed", "finished"):
            # status=done 不代表解析成功（MinerU 提交失败也以 done 收场，
            # 失败详情在 result.success/error）——失败必须在此即停。
            result = (r or {}).get("result") or {}
            if isinstance(result, dict) and result.get("success") is False:
                raise RuntimeError(f"parse failed (task done but result.success=false): "
                                   f"{str(result.get('error'))[:260]}")
            return
        if st == "error":
            raise RuntimeError(f"parse failed: {str(r)[:300]}")
        time.sleep(8)
    raise RuntimeError(f"parse timeout {PARSE_TIMEOUT}s")


def read_head(mc, doc_path: str, limit: int = 400, max_chars: int = 40000) -> str:
    parts, offset = [], 0
    for _ in range(60):
        r = mc.call("kb_doc_read", {"kb_id": KB, "doc_path": doc_path,
                                    "offset": offset, "limit": limit,
                                    "max_chars": max_chars}, timeout=120)
        content = (r or {}).get("content", "")
        parts.append(content)
        if not (r or {}).get("truncated"):
            break
        offset += content.count("\n") + 1
    return "\n".join(parts)


def main() -> int:
    manifest = json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
    # A0 去重: 同一 arXiv id 只入一次
    seen_ids: set[str] = set()
    papers = []
    for p in manifest["papers"]:
        aid = p["arxiv_id"].split("v")[0]
        if aid in seen_ids:
            print(f"[A0] duplicate id skipped: {aid} ({p['field']})", flush=True)
            continue
        seen_ids.add(aid)
        papers.append(p)
    print(f"[A0] {len(papers)} unique papers", flush=True)

    mc = McpClient()
    r = mc.call("kb_list", {"lightweight": True}, timeout=120)
    for k in r.get("catalog") or []:
        if k.get("name") == KB:
            mc.call("kb_delete", {"kb_id": k.get("kb_id") or k.get("name")},
                    timeout=300)
            print(f"[reset] deleted {k.get('name')}", flush=True)
    mc.call("kb_create", {"name": KB,
                          "description": "staging inbox for content-driven "
                          "classification (A1 survey)"}, timeout=180)

    t0 = time.perf_counter()
    done = []
    for p in papers:
        pdf = PAPERS / p["pdf"]
        slug = pdf.stem
        t1 = time.perf_counter()
        task = mc.call("parse_doc", {"file_path": str(pdf)}, timeout=300)
        task_id = (task or {}).get("task_id") or ""
        if not task_id:
            raise RuntimeError(f"parse_doc no task_id: {str(task)[:200]}")
        poll_parse(mc, task_id)
        saved = mc.call("kb_doc_save_parsed",
                        {"parent_id": KB, "task_id": task_id,
                         "source_filename": f"{slug}.md",
                         "description": p["title"][:160]}, timeout=300)
        if not (isinstance(saved, dict) and saved.get("success", True)):
            raise RuntimeError(f"save_parsed failed {slug}: {str(saved)[:200]}")
        done.append({"slug": slug, "field": p["field"], "arxiv_id": aid_of(p),
                     "title": p["title"], "parse_seconds":
                         round(time.perf_counter() - t1, 1)})
        print(f"[parsed] {len(done)}/{len(papers)} {slug[:52]} "
              f"{done[-1]['parse_seconds']}s", flush=True)

    # 索引(供后续 A6-V 与 kb_doc_read 稳定读取)
    docs_list = mc.call("kb_get_documents", {"kb_id": KB}, timeout=180)
    kb_docs = docs_list.get("documents") or []
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    kb_uuid = next((k.get("kb_id") for k in cat.get("catalog") or []
                    if k.get("name") == KB), KB)
    paths = [d.get("path") or f"{KB}/{d.get('name', '')}" for d in kb_docs]
    n = 0
    for s in range(0, len(paths), 20):
        r = http_post(f"{BACKEND}/api/v1/search/batch-index",
                      {"kb_id": kb_uuid, "doc_paths": paths[s:s + 20],
                       "force": True}, timeout=900)
        n += len(r.get("indexed", []))
    print(f"[index] {n} docs", flush=True)
    deadline = time.time() + INDEX_WAIT
    pending = {d["slug"] for d in done}
    while pending and time.time() < deadline:
        time.sleep(8)
        for slug in list(pending):
            pr = mc.call("kb_search_vector",
                         {"query": slug.replace("-", " ")[:60],
                          "kb_id": KB, "top_k": 2}, timeout=120)
            if any(str(h.get("doc_path", "")).startswith(KB + "/")
                   for h in (pr.get("results") or [])):
                pending.discard(slug)
    if pending:
        raise RuntimeError(f"not queryable: {sorted(pending)}")

    # A1 调研材料: 每篇正文前 1400 字
    # 坑: save_parsed 会给 source_filename 再补一个 .md, 实际名是 xxx.md.md —
    # 必须用 kb_get_documents 返回的真实名匹配, 不能拼 slug+'.md'
    for d in done:
        match = next((x for x in kb_docs
                      if str(x.get("name", "")).startswith(d["slug"])), None)
        if not match:
            raise RuntimeError(f"doc not found in {KB}: {d['slug']}")
        head = read_head(mc, match.get("path") or f"{KB}/{match.get('name')}")
        d["chars"] = len(head)
        d["excerpt"] = head[:1400]
    mc.close()
    (SUITE / "results" / "ingest_survey.json").write_text(
        json.dumps({"kb": KB, "n": len(done), "papers": done},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] survey for {len(done)} papers, "
          f"{time.perf_counter() - t0:.0f}s total", flush=True)
    return 0


def aid_of(p: dict) -> str:
    return p["arxiv_id"].split("v")[0]


if __name__ == "__main__":
    sys.exit(main())
