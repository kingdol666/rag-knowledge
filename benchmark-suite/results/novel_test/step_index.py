#!/usr/bin/env python3
"""List docs, force batch-index, probe, and verify (real MCP calls)."""
from __future__ import annotations
import json, sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
from lib import McpClient  # noqa: E402

OUT = Path(__file__).resolve().parent
KB_ID = "b4c48237-6937-440a-9696-cc1e66bed5c1"


def main():
    c = McpClient()
    try:
        docs = c.call("kb_get_documents", {"kb_id": KB_ID}, timeout=180)
        items = docs.get("documents") or docs.get("items") or []
        print(f"### kb_get_documents -> {len(items)} docs")
        paths = []
        for d in items:
            p = d.get("path") or d.get("docPath") or d.get("name")
            paths.append(p)
            print("  -", p)
        (OUT / "documents.json").write_text(
            json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")

        idx = c.call("kb_batch_index", {"kb_id": KB_ID, "doc_paths": paths,
                                        "force": True}, timeout=900)
        print("\n### kb_batch_index")
        print(json.dumps({k: v for k, v in idx.items() if k != "indexed"},
                         ensure_ascii=False)[:800])
        print("total_indexed", idx.get("total_indexed"),
              "errors", len(idx.get("errors") or []),
              "skipped", len(idx.get("skipped") or []))
        (OUT / "batch_index.json").write_text(
            json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")

        stats = c.call("kb_search_stats", {"kb_id": KB_ID}, timeout=120)
        print("\n### kb_search_stats")
        print(json.dumps(stats, ensure_ascii=False)[:600])

        for q in ["Pemberley", "Wickham", "Darcy first proposal rejected"]:
            r = c.call("kb_search_vector", {"query": q, "kb_id": KB_ID,
                                            "top_k": 5, "score_threshold": 0.35,
                                            "balance_kbs": False}, timeout=300)
            res = r.get("results", [])
            print(f"\n### probe '{q}' -> {len(res)} hits")
            for h in res[:5]:
                print(f"   score={h.get('score'):.4f} path={h.get('doc_path')} "
                      f"chunk={h.get('chunk_index')} :: {str(h.get('content'))[:90]!r}")
    finally:
        c.close()


if __name__ == "__main__":
    main()
