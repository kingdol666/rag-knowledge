# -*- coding: utf-8 -*-
"""Stage 4b: explicit kb_index_document (library-relative, forward slashes)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
STORAGE = REPO / "storage" / "tree-file-system"
OUT = REPO / "review" / "_exp_rerun_20261114"
PDF_DIR = REPO / "benchmark-suite" / "data" / "papers"

sys.path.insert(0, str(REPO / "review" / "experiment-redesign-20261101" / "scripts"))
from run100_lib import LIBS  # noqa: E402
from run100_stage2 import mcp  # noqa: E402
from run100_stage3 import probe_once  # noqa: E402


def main() -> int:
    data = json.loads((OUT / "probe3_reindexed.json").read_text(encoding="utf-8"))
    still = data["still"]
    fixed, unresolved = [], []
    for i, r in enumerate(still, 1):
        lib = r["lib"]
        lib_id = LIBS.get(lib, "")
        stem_id = r["arxiv"].replace("-", "_")
        lib_dir = STORAGE / lib
        parts = sorted(lib_dir.glob(f"**/*{stem_id}*"))
        if not parts:
            parts = sorted(lib_dir.glob(f"**/*{r['arxiv']}*"))
        idx_ok, errs = 0, []
        for part in parts:
            rel = part.relative_to(lib_dir).as_posix()
            rr = mcp("kb_index_document",
                     {"kb_id": lib_id, "doc_path": rel}, timeout=180)
            txt = json.dumps(rr, ensure_ascii=False)[:200]
            ok = (rr.get("success") is True) and not rr.get("error")
            if ok:
                idx_ok += 1
            else:
                errs.append(txt)
        hit, names = probe_once(r["arxiv"], lib_id, r["query"], 10)
        entry = dict(r)
        entry.update({"parts_found": len(parts), "index_calls_ok": idx_ok,
                      "index_errors": errs[:2], "post_index_hit": hit,
                      "post_names": names[:5]})
        (fixed if hit else unresolved).append(entry)
        print(f"[{i:02d}] parts={len(parts)} idx_ok={idx_ok} "
              f"{'HIT' if hit else 'STILL'} {r['domain']:22s} {r['arxiv']}",
              flush=True)
        if errs:
            print("      err:", errs[0][:160], flush=True)
    (OUT / "probe4_indexed.json").write_text(
        json.dumps({"fixed": fixed, "unresolved": unresolved},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSTAGE4b SUMMARY: fixed={len(fixed)} unresolved={len(unresolved)}",
          flush=True)
    for u in unresolved:
        print("  UNRESOLVED:", u["domain"], u["arxiv"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
