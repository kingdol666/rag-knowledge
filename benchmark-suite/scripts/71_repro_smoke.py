#!/usr/bin/env python3
"""复现项目 dense 检索冒烟(修正版): 先 activate_profile 重绑 KB 常量再检索."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "algorithms"))

from lib import McpClient  # noqa: E402
from methods import Ctx, dense  # noqa: E402
from user_scenario import activate_profile, load_user_docs  # noqa: E402

def main() -> int:
    docs = load_user_docs(sorted((SUITE / "data" / "corpus_md").glob("*.md")))
    old = activate_profile("Corpus", "Corpus-Chunks800")
    mc = McpClient()
    ctx = Ctx(mc, None, None,
              kb_names=("Corpus-Chunks800", "Corpus-Struct", "Corpus-Paras", ""),
              corpus_docs=docs)
    ev = dense(ctx, "attention mechanism for sequence transduction")
    mc.close()
    for k, v in old.items():
        setattr(__import__("methods"), k, v)
    chunks = ev.get("chunks") or []
    out = {"chunks": len(chunks),
           "doc_rank": (ev.get("doc_rank") or [])[:3],
           "top_score": (chunks or [{}])[0].get("score")}
    (SUITE / "results" / "repro_smoke.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if chunks else 1


if __name__ == "__main__":
    sys.exit(main())
