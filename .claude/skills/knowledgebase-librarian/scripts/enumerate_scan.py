#!/usr/bin/env python3
"""enumerate_scan — 枚举/字面提及类问题的召回层（librarian 快速通道第一步判定前扫描）。

语义判卷引擎（Laya/Jev）对"哪些文档字面提到 X"类穷尽题实测欠召回
（PridePrejudice 28 part 提 Pemberley 真值 9，instance 判据 0.3/0.5 阈值均仅召回 3），
因为引擎按语义相关性打分，会压低"顺带提及"的段落。本脚本补上确定性的字面匹配层：

    kb_get_documents 的 docid 清单 → 逐篇 kb_doc_read（MCP，机侧消化）→
    字面/正则匹配 → 命中 docid + 命中窗口（供 kb_doc_read 精读与回答引用）

治理边界：所有内容访问都经 scripts/mcp_call.py → kb-mcp MCP 服务完成，
本脚本不自取 token、不直连 backend/web。正文在机侧组装判定载荷，不进
LLM 上下文——这是它不拖慢作业的根本原因（28 篇 ≈ 15-20s，0 个 LLM 轮次）。

用法（在仓库根目录）：
  python .claude/skills/knowledgebase-librarian/scripts/enumerate_scan.py \
      --kb-id <uuid> --terms "Pemberley" [--terms "彭伯利"] \
      [--docs-json kb_docs.json] [--regex] [--max-doc-chars 30000] [--window 80]

  --docs-json 省略时自动调 mcp_call kb_get_documents --raw 获取。
输出（stdout，JSON）：{"kb_id","terms","scanned","hit_count",
  "hits":[{"doc_id","doc_path","count","windows":["…命中±window…"]}]}
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]          # .claude/skills/<name>/scripts → repo root
MCP_CALL = REPO / "scripts" / "mcp_call.py"


def mcp(tool: str, payload: dict, timeout: float = 120.0) -> dict:
    """单次 MCP 工具调用：@file 传参（doc_path 反斜杠不经过 shell argv）。"""
    pf = Path("_scan_payload.json")
    pf.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    cmd = [sys.executable, str(MCP_CALL), tool, f"@{pf.name}", "--raw"]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", cwd=str(REPO), timeout=timeout)
    try:
        pf.unlink()
    except OSError:
        pass
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        raise RuntimeError(f"mcp_call {tool} failed rc={r.returncode}: {(r.stderr or out)[:200]}")
    return json.loads(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Literal-term enumeration scan over one KB (via MCP)")
    ap.add_argument("--kb-id", required=True)
    ap.add_argument("--terms", action="append", required=True,
                    help="字面词/短语，可重复；多词为 OR")
    ap.add_argument("--docs-json", default="", help="kb_get_documents --raw 的输出文件（省略则自动拉取）")
    ap.add_argument("--regex", action="store_true", help="terms 按正则解释（默认字面）")
    ap.add_argument("--max-doc-chars", type=int, default=30000)
    ap.add_argument("--window", type=int, default=80, help="命中窗口半径（字符）")
    ap.add_argument("--max-windows", type=int, default=3, help="每篇最多返回的窗口数")
    args = ap.parse_args()

    if args.docs_json:
        listing = json.loads(Path(args.docs_json).read_text(encoding="utf-8"))
    else:
        listing = mcp("kb_get_documents", {"kb_id": args.kb_id, "lightweight": True})
    if not listing.get("success"):
        print(json.dumps({"success": False, "error": listing.get("error", "kb_get_documents failed")},
                         ensure_ascii=False))
        return 1
    docs = listing.get("catalog") or []

    flags = 0 if args.regex else re.IGNORECASE
    patterns = [re.compile(t if args.regex else re.escape(t), flags) for t in args.terms]

    hits, scanned, t0 = [], 0, time.time()
    for d in docs:
        doc_path = d.get("doc_path") or ""
        try:
            body = mcp("kb_doc_read", {"kb_id": args.kb_id, "doc_path": doc_path,
                                       "max_chars": args.max_doc_chars},
                       timeout=180.0)
        except Exception as exc:  # noqa: BLE001 — 单篇失败不阻断整扫，如实记入输出
            hits.append({"doc_id": d.get("doc_id"), "doc_path": doc_path,
                         "error": str(exc)[:160]})
            scanned += 1
            continue
        scanned += 1
        content = body.get("content") or ""
        if not content:
            continue
        spans = sorted({m.span() for p in patterns for m in p.finditer(content)})
        if not spans:
            continue
        windows = []
        for s, e in spans[: args.max_windows]:
            lo, hi = max(0, s - args.window), min(len(content), e + args.window)
            windows.append(content[lo:hi].replace("\n", " ").strip())
        hits.append({"doc_id": d.get("doc_id"), "doc_path": doc_path,
                     "count": len(spans), "windows": windows})

    real_hits = [h for h in hits if h.get("count")]
    print(json.dumps({"kb_id": args.kb_id, "terms": args.terms,
                      "scanned": scanned, "hit_count": len(real_hits),
                      "elapsed_s": round(time.time() - t0, 1),
                      "hits": hits}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
