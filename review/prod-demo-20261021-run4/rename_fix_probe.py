#!/usr/bin/env python3
"""Rename→vector-label defect probe (ralph run 4, US-306).

Runs the rename path end-to-end on a disposable KB and records, at each
stage, exactly which doc_path labels the vector store returns:

  1. index fixture under path A  -> labels must be A
  2. rename A -> B (kb_doc_update_meta)
  3. search immediately          -> run3 defect: labels stay A (no hygiene)
                                    after fix: labels B (inline hygiene)
  4. force reindex               -> does a rebuild alone repair labels?
  5. description-only update    -> must not change anything (no-hygiene gate)

Usage: python rename_fix_probe.py <phase-tag>   (tag: before|after)
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))

from mcp_client import McpClient  # noqa: E402

PHASE = sys.argv[1] if len(sys.argv) > 1 else "before"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
KB = f"ZZ-RenFix-{PHASE}-{STAMP}"
TOKEN = f"RENFIX-{PHASE}-{STAMP}"
OUT = Path(__file__).resolve().parent / f"rename_probe_{PHASE}.json"

result: dict = {"phase": PHASE, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "kb": KB, "token": TOKEN, "stages": []}


def search_paths(client, kb_id, query):
    r = client.call("kb_search_vector", {"query": query, "kb_id": kb_id,
                                         "top_k": 10, "score_threshold": 0.0},
                    timeout=180)
    rows = r.get("results", []) if isinstance(r, dict) else []
    return [{"doc_path": str(h.get("doc_path")), "score": round(float(h.get("score", 0)), 4),
             "has_token": TOKEN in str(h.get("content", ""))}
            for h in rows if TOKEN in str(h.get("content", "")) or TOKEN in str(h.get("doc_path", ""))]


def stage(name, detail):
    result["stages"].append({"stage": name, **detail})
    print(f"[{name}] " + json.dumps(detail, ensure_ascii=False)[:400], flush=True)


def poll_task(client, task_id, tries=30, sleep_s=3):
    for _ in range(tries):
        st = client.call("kb_task_status", {"task_id": task_id}, timeout=60)
        s = str(st.get("status", "")).lower()
        if s in ("finished", "completed", "done", "success"):
            return st
        if s in ("failed", "error"):
            return st
        time.sleep(sleep_s)
    return {"status": "timeout"}


def main() -> int:
    client = McpClient(REPO)
    kb_id = None
    try:
        kb = client.call("kb_create", {"name": KB, "description": "rename probe"}, timeout=120)
        kb_id = (kb.get("knowledgeBase") or {}).get("kb_id")
        name_a = f"renfix-a-{STAMP}.md"
        content = (f"# rename probe\nunique token {TOKEN}\n"
                   "calibration constant 42.195 km.\n")
        da = client.call("kb_doc_create", {"kb_id": kb_id, "name": name_a,
                                           "content": content, "description": TOKEN},
                         timeout=180)
        path_a = (da.get("document") or {}).get("path")
        client.call("kb_index_document", {"kb_id": kb_id, "doc_path": path_a}, timeout=300)
        time.sleep(2)

        # Cache-busting: vector_service.search caches identical (query, kb_id, ...)
        # rows for 30s, so every stage probes with a DISTINCT query string.
        s1 = search_paths(client, kb_id, f"{TOKEN} calibration")
        stage("index_at_A", {"path_a": path_a, "hits": s1})

        name_b = f"renfix-b-{STAMP}.md"
        rn = client.call("kb_doc_update_meta", {"kb_id": kb_id, "doc_path": path_a,
                                                "name": name_b}, timeout=120)
        time.sleep(3)
        s2 = search_paths(client, kb_id, f"{TOKEN} calibration constant")
        new_labels = [h["doc_path"] for h in s2 if name_b in h["doc_path"]]
        old_labels = [h["doc_path"] for h in s2 if name_a in h["doc_path"]]
        stage("after_rename", {"rename_ok": bool(rn.get("success", True)),
                               "index_hygiene": rn.get("index_hygiene"),
                               "new_label_hits": len(new_labels),
                               "old_label_hits": len(old_labels),
                               "hits": s2})
        result["verdict_inline_hygiene"] = bool(new_labels) and not old_labels

        try:
            rd_old = client.call("kb_doc_read", {"kb_id": kb_id,
                                                 "doc_path": f"{KB}/{name_a}",
                                                 "max_chars": 120}, timeout=120)
            old_readable = TOKEN in json.dumps(rd_old)
        except Exception:
            old_readable = False
        rd_new = client.call("kb_doc_read", {"kb_id": kb_id,
                                             "doc_path": f"{KB}/{name_b}",
                                             "max_chars": 120}, timeout=120)
        stage("registry_sanity", {"old_path_readable": old_readable,
                                  "new_path_readable": TOKEN in json.dumps(rd_new)})

        ri = client.call("kb_reindex", {"kb_id": kb_id, "force": True}, timeout=120)
        st = poll_task(client, ri.get("task_id")) if ri.get("task_id") else {"status": "no-task"}
        time.sleep(2)
        s3 = search_paths(client, kb_id, f"{TOKEN} calibration constant km")
        new_labels3 = [h["doc_path"] for h in s3 if name_b in h["doc_path"]]
        old_labels3 = [h["doc_path"] for h in s3 if name_a in h["doc_path"]]
        stage("after_force_reindex", {"task_status": st.get("status"),
                                      "task_result": json.dumps(st.get("result", {}), ensure_ascii=False)[:400],
                                      "new_label_hits": len(new_labels3),
                                      "old_label_hits": len(old_labels3),
                                      "hits": s3})
        result["verdict_reindex_repairs"] = bool(new_labels3) and not old_labels3

        up = client.call("kb_doc_update_meta", {"kb_id": kb_id, "doc_path": f"{KB}/{name_b}",
                                                "description": f"desc-only {TOKEN}"}, timeout=120)
        time.sleep(1)
        s4 = search_paths(client, kb_id, f"{TOKEN} calibration constant km distance")
        stage("desc_only_update", {"update_ok": bool(up.get("success", True)),
                                   "labels_unchanged": sorted(set(h["doc_path"] for h in s4)) ==
                                                       sorted(set(h["doc_path"] for h in s3)),
                                   "hits": len(s4)})

        rd = client.call("kb_doc_read", {"kb_id": kb_id, "doc_path": f"{KB}/{name_b}",
                                         "max_chars": 200}, timeout=120)
        result["final_content_readable"] = TOKEN in json.dumps(rd)
    except Exception as e:
        stage("exception", {"error": str(e)[:600]})
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
                dk = client.call("kb_delete", {"kb_id": kb_id}, timeout=180)
                listing = client.call("kb_list", {"lightweight": True}, timeout=120)
                names = [k.get("name") for k in listing.get("catalog", [])] if isinstance(listing, dict) else []
                stage("cleanup", {"kb_delete_ok": bool(dk.get("success", True)),
                                  "residual": KB in names})
            except Exception as e:
                stage("cleanup_error", {"error": str(e)[:300]})
        client.close()

    (OUT).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RESULT saved:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
