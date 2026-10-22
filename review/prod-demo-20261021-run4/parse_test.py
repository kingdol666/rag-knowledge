#!/usr/bin/env python3
"""Acquisition entry live test (run 4): real MinerU PDF parse -> KB -> index -> retrieve.

Closes gap G-P: the parse path driven end-to-end on a real 26 KB paper PDF
(.bench_backup_20260917/data/en/wind-energy.pdf), parse_doc (MinerU spawns on
demand), saves via the preferred kb_doc_save_parsed task_id mode, indexes and
retrieves.  Disposable KB, full cleanup, MCP stdio only.
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

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
KB = f"ZZ-Parse-Test-{STAMP}"
PDF = (REPO / ".bench_backup_20260917" / "data" / "en" / "wind-energy.pdf").resolve()

OUT = Path(__file__).resolve().parent
result: dict = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "kb": KB, "pdf": str(PDF), "steps": []}


def step(name, ok, detail=None, note=""):
    result["steps"].append({"step": name, "ok": bool(ok), "note": note, "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f"  [{note}]" if note else ""), flush=True)


def poll(client, task_id, kind="parse", tries=90, sleep_s=5):
    tool = "parse_task_status" if kind == "parse" else "kb_task_status"
    for _ in range(tries):
        st = client.call(tool, {"task_id": task_id}, timeout=60)
        s = str(st.get("status", "")).lower()
        if s in ("finished", "completed", "done", "success"):
            return True, st
        if s in ("failed", "error"):
            return False, st
        time.sleep(sleep_s)
    return False, {"status": "timeout"}


def main() -> int:
    client = McpClient(REPO)
    kb_id = None
    try:
        kb = client.call("kb_create", {"name": KB, "description": "parse path live test"},
                         timeout=120)
        kb_id = (kb.get("knowledgeBase") or {}).get("kb_id")
        step("kb_create", bool(kb_id), {"kb_id": kb_id})

        pr = client.call("parse_doc", {"file_path": str(PDF), "use_ocr": True}, timeout=180)
        task_id = pr.get("task_id") if isinstance(pr, dict) else None
        step("parse_doc_submitted", bool(task_id),
             {"task_id": task_id, "head": json.dumps(pr, ensure_ascii=False)[:200]},
             note="MinerU spawns on demand; cold start 1-2 min")
        if not task_id:
            raise RuntimeError("no parse task id")
        ok, st = poll(client, task_id, "parse", tries=90, sleep_s=5)
        detail = {k: str(st.get(k))[:120] for k in ("status", "markdown_path", "images_dir",
                                                    "source_filename", "error") if k in st}
        step("parse_finished", ok, detail)
        if not ok:
            raise RuntimeError(f"parse failed: {json.dumps(st)[:300]}")

        sp = client.call("kb_doc_save_parsed", {"parent_id": kb_id, "task_id": task_id,
                                                "description": "wind energy paper (parsed live)"},
                         timeout=300)
        # Response shape is batch-style: {savedCount, files:[{path,...}]}
        doc_path = None
        if isinstance(sp, dict):
            files = sp.get("files") or []
            if files and isinstance(files[0], dict):
                doc_path = files[0].get("path")
            if not doc_path:
                doc_path = (sp.get("document") or {}).get("path")
        step("kb_doc_save_parsed", bool(doc_path), {"path": doc_path,
                                                    "head": json.dumps(sp, ensure_ascii=False)[:200]})

        idx = client.call("kb_index_document", {"kb_id": kb_id, "doc_path": doc_path},
                          timeout=600)
        chunks = (idx.get("vector_index") or {}).get("total_chunks")
        step("kb_index_document", bool(idx.get("success")) and (chunks or 0) >= 1,
             {"total_chunks": chunks})

        time.sleep(2)
        sr = client.call("kb_search_vector", {"query": "wind energy turbine power generation",
                                              "kb_id": kb_id, "top_k": 3,
                                              "score_threshold": 0.0}, timeout=180)
        hits = sr.get("results", []) if isinstance(sr, dict) else []
        step("retrieval_after_parse", len(hits) >= 1,
             {"hits": len(hits), "top_score": hits[0].get("score") if hits else None,
              "head": str(hits[0].get("content", ""))[:150] if hits else ""})

        rd = client.call("kb_doc_read", {"kb_id": kb_id, "doc_path": doc_path,
                                         "max_chars": 600}, timeout=120)
        rb = json.dumps(rd, ensure_ascii=False)
        step("doc_read_markdown", ("wind" in rb.lower()) and len(rb) > 300,
             {"chars": len(rb)})

    except Exception as e:
        step("exception", False, {"error": str(e)[:800]})
    finally:
        if kb_id:
            try:
                docs = client.call("kb_get_documents", {"kb_id": kb_id}, timeout=120)
                cat = docs.get("documents", {}).get("catalog", []) if isinstance(docs.get("documents"), dict) else docs.get("catalog", [])
                for e in cat:
                    client.call("kb_doc_delete", {"kb_id": kb_id, "doc_path": e.get("path")}, timeout=120)
                dk = client.call("kb_delete", {"kb_id": kb_id}, timeout=180)
                step("cleanup", bool(dk.get("success", True)), {})
            except Exception as e:
                step("cleanup", False, {"error": str(e)[:200]})
        client.close()

    result["pass"] = all(s["ok"] for s in result["steps"])
    (OUT / "parse_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nRESULT:", "PASS" if result["pass"] else "FAIL")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
