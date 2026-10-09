#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 10a — ingest the 10 gold arXiv papers as a second-corpus KB.

Pipeline: kb_create -> parse_doc_batch (MinerU, async task) -> poll ->
kb_doc_save_parsed per paper -> REST reindex. Idempotent-ish: reuses the
existing "benchmark-papers" KB if present.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import RESULTS, McpClient  # noqa: E402

PDF_DIR = REPO_PDF = Path(r"D:\codes\ragproject\rag-knowledge"
                          r"\benchmark-suite\data\papers\pdf")
STATE = RESULTS / "exp10_ingest_state.json"
API = "http://127.0.0.1:8770"


def api_post(path: str, payload: dict) -> dict:
    from kbcommon import get_token
    req = urllib.request.Request(API + path, method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    token = get_token()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    mc = McpClient()
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    print(f"pdfs: {len(pdfs)}", flush=True)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}

    kb_id = state.get("kb_id")
    if not kb_id:
        cat = mc.call("kb_list", {"lightweight": True}, timeout=60)
        existing = next((k for k in cat["catalog"]
                         if k.get("name") == "benchmark-papers"), None)
        kb_id = existing["kb_id"] if existing else None
        if not kb_id:
            r = mc.call("kb_create", {
                "name": "benchmark-papers",
                "description": "Ten gold arXiv papers from the "
                               "benchmark-suite question set (second-corpus "
                               "scaling probe for the KBS submission)."},
                timeout=120)
            kb_id = r.get("kb_id") or (r.get("data") or {}).get("kb_id")
        state["kb_id"] = kb_id
    print("kb_id:", kb_id, flush=True)

    if not state.get("parse_task_done"):
        task = mc.call("parse_doc_batch",
                       {"file_paths": [str(p) for p in pdfs],
                        "use_ocr": True}, timeout=600)
        tid = task.get("task_id") or (task.get("data") or {}).get("task_id")
        print("parse task:", tid, flush=True)
        for i in range(240):  # up to 40 min
            time.sleep(10)
            st = mc.call("parse_task_status", {"task_id": tid}, timeout=120)
            s = json.dumps(st, ensure_ascii=False)
            status = st.get("status") or (st.get("data") or {}).get("status")
            done = st.get("done", status in ("completed", "success", "finished"))
            if i % 6 == 0 or done:
                print(f"  [{i*10}s] status={status} {s[:200]}", flush=True)
            if done:
                break
        state["parse_task_done"] = True
        state["parse_status"] = st
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    saved = state.get("saved", [])
    for p in pdfs:
        if p.name in saved:
            continue
        r = mc.call("kb_doc_save_parsed", {
            "parent_id": kb_id, "source_filename": p.name,
            "task_id": state.get("parse_task_id", ""),
            "description": f"arXiv gold paper {p.stem}"}, timeout=600)
        s = json.dumps(r, ensure_ascii=False)
        ok = r.get("success", True)
        print(("saved " if ok else "SAVE-FAIL ") + p.name + " " + s[:150],
              flush=True)
        saved.append(p.name)
        state["saved"] = saved
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    print("reindex...", flush=True)
    rr = api_post("/api/v1/search/reindex", {"kb_id": kb_id, "force": True})
    print("reindex:", json.dumps(rr, ensure_ascii=False)[:200], flush=True)
    smoke = mc.call("kb_search_vector",
                    {"query": "transformer attention mechanism",
                     "kb_id": kb_id, "top_k": 3, "score_threshold": 0.0},
                    timeout=120)
    print("smoke:", json.dumps(smoke, ensure_ascii=False)[:300], flush=True)
    print("DONE. kb_id =", kb_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
