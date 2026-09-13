#!/usr/bin/env python3
"""端到端功能冒烟 — 每个模块单独调用一次，验证可用性（审稿实验前置闸门）."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import BACKEND, WEB, McpClient, http_get  # noqa: E402

ok: list[str] = []
bad: list[str] = []


def t(name: str, fn):
    try:
        r = fn()
        ok.append(name)
        print(f"  OK  {name}: {str(r)[:90]}", flush=True)
    except Exception as e:  # noqa: BLE001
        bad.append(name)
        print(f"  X   {name}: {str(e)[:90]}", flush=True)


def main() -> int:
    mc = McpClient()
    try:
        print("== MCP tool layer ==")
        kbs = mc.call("kb_list", {"lightweight": True}, timeout=60)
        n_kb = len(kbs.get("knowledge_bases") or kbs.get("items") or [])
        t("kb_list", lambda: f"n_kb={n_kb}")

        r = mc.call("kb_search_two_stage",
                    {"query": "Betz limit wind turbine", "kb_id": "",
                     "stage1_top_k": 20, "stage2_top_k": 5, "balance_kbs": True},
                    timeout=180)
        t("kb_search_two_stage",
          lambda: "s1={} s2={}".format(len((r.get("stage1") or {}).get("candidates") or []),
                                       len((r.get("stage2") or {}).get("results") or [])))

        rv = mc.call("kb_search_vector",
                     {"query": "photosynthesis Calvin cycle", "kb_id": "", "top_k": 5},
                     timeout=180)
        t("kb_search_vector", lambda: f"n={len(rv.get('results') or [])}")

        first_doc = ((rv.get("results") or [{}])[0]).get("doc_path", "")
        rd = mc.call("kb_doc_read", {"doc_path": first_doc, "max_chars": 500},
                     timeout=60)
        t("kb_doc_read", lambda: f"chars={len(str(rd.get('content') or ''))}")

        re_ = mc.call("experience_search_smart",
                      {"query": "wind turbine cut-out wind speed", "top_k": 5},
                      timeout=180)
        t("experience_search_smart",
          lambda: f"success={re_.get('success')} n={re_.get('count')}")

        rg = mc.call("experience_search_global",
                     {"query": "how to verify wind energy facts", "top_k": 5},
                     timeout=180)
        t("experience_search_global",
          lambda: f"success={rg.get('success')} n={rg.get('count')}")
    finally:
        mc.close()

    print("== REST API layer ==")
    t("GET /api/kb/catalog (web proxy)",
      lambda: "n_kb=" + str(len((http_get(WEB + "/api/kb/catalog",
                                         timeout=30) or {}).get("knowledgeBases") or [])))

    print()
    print("SMOKE:", "ALL OK" if not bad else f"FAILED: {bad}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
