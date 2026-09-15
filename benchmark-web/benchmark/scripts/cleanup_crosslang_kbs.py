#!/usr/bin/env python3
"""清理三个跨语言对照库(级联删除向量/图谱), 供基准重建前执行."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))
from bench_http import post_json, get_json  # noqa: E402

TOKEN = os.environ.get("RAG_BENCH_TOKEN", "")
WEB = os.environ.get("RAG_BENCH_WEB_URL", "http://localhost:6790").rstrip("/")
NAMES = {"KB-CrossLang-EN", "KB-CrossLang-ZH", "KB-CrossLang-JA"}


def main() -> int:
    catalog = get_json(WEB, "/api/kb/catalog", token=TOKEN, timeout=120)
    for k in catalog.get("knowledgeBases", []):
        if k.get("name") in NAMES:
            try:
                # delete 级联清理时响应体可能为空 — 空 body 视为成功
                import json as _json
                import urllib.request as _u
                req = _u.Request(f"{WEB}/api/kb/delete",
                                 data=_json.dumps({"kbId": k["kbId"]}).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {TOKEN}"},
                                 method="DELETE")
                with _u.urlopen(req, timeout=600) as resp:
                    resp.read()
                print("deleted", k["name"])
            except Exception as e:  # noqa: BLE001
                print("delete failed", k["name"], str(e)[:100])
    print("cleanup done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
