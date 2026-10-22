#!/usr/bin/env python3
"""Force-reindex the two drifted gate libraries and re-run the 15-probe suite (run-4 repair).

Repairs the live regression drift documented in regression_drift_diagnosis.json:
生命科学与医学 + 工程与能源 vector collections hold legacy backslash-label
generations and 2 probe golds lost their forward-slash generation.  The system's
own remedy (kb_reindex force) rebuilds both collections from the registry.
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

LIBS = ["生命科学与医学", "工程与能源"]
OUT = Path(__file__).resolve().parent / "reindex_repair_result.json"
result: dict = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "libraries": []}


def poll(client, task_id, tries=120, sleep_s=5):
    for _ in range(tries):
        st = client.call("kb_task_status", {"task_id": task_id}, timeout=60)
        s = str(st.get("status", "")).lower()
        if s in ("finished", "completed", "done", "success"):
            return True, st
        if s in ("failed", "error"):
            return False, st
        time.sleep(sleep_s)
    return False, {"status": "timeout"}


def main() -> int:
    client = McpClient(REPO)
    try:
        cat = client.call("kb_list", {"lightweight": True}, timeout=120)
        name2id = {i.get("name"): i.get("kb_id") for i in (cat.get("catalog") or [])}
        for lib in LIBS:
            kb_id = name2id[lib]
            t0 = time.perf_counter()
            ri = client.call("kb_reindex", {"kb_id": kb_id, "force": True}, timeout=120)
            ok, st = poll(client, ri.get("task_id"))
            wall = round(time.perf_counter() - t0, 1)
            entry = {"library": lib, "kb_id": kb_id, "reindex_ok": ok,
                     "wall_s": wall,
                     "result": json.dumps(st.get("result", {}), ensure_ascii=False)[:300]}
            print(f"{lib}: ok={ok} wall={wall}s {entry['result'][:120]}", flush=True)
            result["libraries"].append(entry)
    finally:
        client.close()
    (OUT).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    all_ok = all(e["reindex_ok"] for e in result["libraries"])
    print("REINDEX REPAIR:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
