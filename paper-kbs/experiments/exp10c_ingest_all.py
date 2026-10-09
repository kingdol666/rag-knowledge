#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 10c — ingest ALL benchmark-suite papers into the benchmark-papers KB.

Batches of 20: parse_doc_batch -> poll to status=done -> kb_doc_save_parsed.
Resumable via exp10_ingest_state.json ("saved_all" list). Then reindex.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import RESULTS, McpClient  # noqa: E402

PDF_DIR = Path(r"D:\codes\ragproject\rag-knowledge"
               r"\benchmark-suite\data\papers\pdf")
STATE = RESULTS / "exp10_ingest_state.json"
BATCH = 20


def main() -> int:
    mc = McpClient()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    kb_id = state["kb_id"]
    saved = set(state.get("saved_all", []))
    pdfs = [p for p in sorted(PDF_DIR.glob("*.pdf"))
            if p.stat().st_size > 100_000 and p.name not in saved]
    print(f"to ingest: {len(pdfs)} (already saved: {len(saved)})", flush=True)
    if not pdfs:
        print("nothing to do")
        return 0

    for i in range(0, len(pdfs), BATCH):
        chunk = pdfs[i:i + BATCH]
        task = mc.call("parse_doc_batch",
                       {"file_paths": [str(p) for p in chunk],
                        "use_ocr": True}, timeout=600)
        tid = task.get("task_id") or (task.get("data") or {}).get("task_id")
        print(f"[batch {i//BATCH+1}] task={tid} n={len(chunk)}", flush=True)
        status = None
        for _ in range(400):
            time.sleep(10)
            st = mc.call("parse_task_status", {"task_id": tid}, timeout=120)
            status = st.get("status")
            if status == "done":
                break
        print(f"[batch {i//BATCH+1}] status={status}", flush=True)
        for p in chunk:
            r = mc.call("kb_doc_save_parsed", {
                "parent_id": kb_id, "source_filename": p.name,
                "task_id": tid,
                "description": f"arXiv paper {p.stem}"}, timeout=600)
            ok = r.get("success", True)
            if ok:
                saved.add(p.name)
            print(("saved " if ok else "SAVE-FAIL ") + p.name, flush=True)
        state["saved_all"] = sorted(saved)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    print("reindex...", flush=True)
    from kbcommon import get_token
    import urllib.request
    req = urllib.request.Request(
        "http://127.0.0.1:8770/api/v1/search/reindex", method="POST",
        data=json.dumps({"kb_id": kb_id, "force": True}).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    token = get_token()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=1800) as r:
        rr = json.loads(r.read().decode("utf-8"))
    print("reindex:", json.dumps(rr, ensure_ascii=False)[:200], flush=True)
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
