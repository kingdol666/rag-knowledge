#!/usr/bin/env python3
"""124 — 模式 C(并行重定义): A ∥ B 并行 → 去重合并 → 完整文档读取 → 知识增强包.

语义(2026-09-27 用户定义):
  1. 并行调用模式 A(vector_jev_search 宽网+逐段判决)与模式 B(图书管理员
     complete_recall 全目录+逐段判决), 各自作为独立子进程(脚本内执行, 不占
     主对话上下文);
  2. 先执行完的等待后者(threading join), 然后按 doc_path 去重合并 ——
     双模式共识文档优先, 其余按最佳得分排序;
  3. 对合并后的文档逐篇 kb_doc_read **完整正文**(truncated 自动 offset 续读);
  4. 产出: 最终 JSON = 合并溯源 + 每篇完整内容(知识增强包)。
主对话只消费最终产物中的完整文档内容, 中间过程全部留在子进程/临时文件里。

用法:
  python scripts/124_mode_c_parallel.py --query "..." [--shelves 计算机与人工智能] \
      [--max-docs 12] [--doc-chars 24000] [--out result.json]
  python scripts/124_mode_c_parallel.py --worker-b --query "..." --out b.json --shelves ...
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT_A = REPO / ".claude/skills/knowledgebase-search/scripts/vector_jev_search.py"


def resolve_laya_python() -> Path:
    import os
    env = os.environ.get("RAG_LAYA_PYTHON", "").strip()
    if env:
        return Path(env)
    for rel in ("backend/.venv/Scripts/python.exe", "backend/.venv/bin/python"):
        cand = REPO / rel
        if cand.exists():
            return cand
    return Path(sys.executable)


def norm(path: str) -> str:
    return str(path or "").replace("\\", "/").lower()


# ────────────────────────── worker B(图书管理员整链) ──────────────────────────

def worker_b(query: str, out_path: Path, shelves: list[str],
             budget: int = 35, head_budget: int = 20) -> dict:
    sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
    sys.path.insert(0, str(REPO / ".claude" / "skills" / "knowledgebase-librarian" / "scripts"))
    import re as _re
    from lib import McpClient
    import complete_recall as cr

    t0 = time.time()
    mc = McpClient()
    manifest_docs: list[dict] = []
    docs_all: list[dict] = []
    trace: dict = {}
    try:
        kbs = (mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or [])
        sel = [k for k in kbs if not shelves or str(k.get("name") or "") in set(shelves)]
        for k in sel:
            kb_id = k.get("kb_id") or k.get("name")
            rows = (mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                            timeout=180).get("catalog") or [])
            for d in rows:
                docs_all.append({**d, "kb_id": kb_id, "kb_name": k.get("name")})
        trace["l2_docs"] = len(docs_all)

        qterms = cr._terms(query)
        sibs: dict[str, list[str]] = {}
        for d in docs_all:
            sibs.setdefault(str(d.get("kb_id")), []).append(str(d.get("description") or ""))
        for d in docs_all:
            blob = f"{d.get('name', '')} {d.get('description', '')}"
            d["overlap"] = len(qterms & cr._terms(blob)) if qterms else 0
            trusted, reasons = cr._metadata_trust(str(d.get("description") or ""),
                                                  sibs[str(d.get("kb_id"))])
            d["description_trust"] = "trusted" if trusted else "untrusted"

        picked: set = set()

        def full_read(d: dict) -> None:
            key = (str(d.get("kb_id")), str(d.get("doc_path")))
            if key in picked or len(manifest_docs) >= budget:
                return
            picked.add(key)
            r = mc.call("kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": 20000}, timeout=180)
            manifest_docs.append({**d, "content": str(r.get("content") or ""),
                                  "truncated": bool(r.get("truncated")), "read_kind": "full"})

        def head_read(d: dict) -> None:
            key = (str(d.get("kb_id")), str(d.get("doc_path")))
            if key in picked or len(manifest_docs) >= budget + head_budget:
                return
            picked.add(key)
            r = mc.call("kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": 600}, timeout=120)
            manifest_docs.append({**d, "content": str(r.get("content") or ""),
                                  "truncated": bool(r.get("truncated")), "read_kind": "trust_head"})

        def stem_of(p: str):
            m = _re.search(r"^(.*) \(part \d+ of \d+\)", str(p or "").replace("\\", "/"))
            return m.group(1) if m else None

        for d in sorted((d for d in docs_all if d["overlap"] > 0), key=lambda x: -x["overlap"]):
            if len(manifest_docs) >= budget:
                break
            full_read(d)
        stems = {stem_of(d["doc_path"]) for d in manifest_docs} - {None}
        for d in docs_all:
            if len(manifest_docs) >= budget:
                break
            if stem_of(d.get("doc_path")) in stems:
                full_read(d)
        for d in docs_all:
            if d["description_trust"] == "untrusted":
                head_read(d)
    finally:
        mc.close()

    manifest = {"query": query, "engine": "laya", "threshold": 0.5,
                "max_segment_chars": 3000, "max_evidence_chars": 40_000,
                "documents": manifest_docs}
    run = cr.run_manifest(manifest)  # real Laya, fail-closed
    jev = run["jev"]
    survivors = jev.get("survivors") or []
    result = {"worker": "B", "seconds": round(time.time() - t0, 1),
              "real_engine": jev.get("real_engine"),
              "scored": jev.get("scored_count"),
              "docs": sorted({str(s.get("doc_path", "")).replace("\\", "/")
                              for s in survivors}),
              "survivor_segments": len(survivors),
              "best_score": max([float(s.get("score") or 0) for s in survivors], default=0.0),
              "trace": {k: trace.get(k) for k in ("l2_docs",)}}
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


# ────────────────────────── parent: A ∥ B → merge → full reads ──────────────────────────

def run_parallel_c(query: str, out_path: Path, shelves: list[str], max_docs: int,
                   doc_chars: int, total_chars_cap: int) -> dict:
    t0 = time.time()
    laya_py = str(resolve_laya_python())
    tmp = out_path.parent
    out_a, out_b = tmp / "c-worker-A.json", tmp / "c-worker-B.json"
    results: dict = {}

    def run_a():
        st = time.time()
        p = subprocess.run([laya_py, str(SCRIPT_A), "--query", query, "--top-k", "30",
                            "--require-real", "--output", str(out_a)],
                           capture_output=True, text=True, timeout=1800, cwd=str(REPO))
        d = json.loads(out_a.read_text(encoding="utf-8")) if out_a.exists() else {}
        results["A"] = {
            "worker": "A", "seconds": d.get("seconds"),
            "real_engine": d.get("real_engine"),
            "scored": ((d.get("judge") or {}).get("scored")),
            "docs": sorted({str(r.get("doc_path", "")).replace("\\", "/")
                            for r in (d.get("result_list") or [])}),
            "rc": p.returncode,
            "interpreter": laya_py,
            "start": round(st - t0, 2), "end": round(time.time() - t0, 2)}

    def run_b():
        st = time.time()
        p = subprocess.run([laya_py, str(Path(__file__).resolve()), "--worker-b",
                            "--query", query, "--out", str(out_b),
                            "--shelves", ",".join(shelves)],
                           capture_output=True, text=True, timeout=1800, cwd=str(REPO))
        d = json.loads(out_b.read_text(encoding="utf-8")) if out_b.exists() else {}
        results["B"] = {**d, "rc": p.returncode,
                        "interpreter": laya_py,
                        "start": round(st - t0, 2), "end": round(time.time() - t0, 2)}

    ta = threading.Thread(target=run_a)
    tb = threading.Thread(target=run_b)
    ta.start(); tb.start()
    ta.join()  # 先完成的一方在此等待另一方
    tb.join()
    merge_s = round(time.time() - t0, 1)

    # ── 去重合并: 共识优先, 其余按来源 ──
    docs_a = set(results.get("A", {}).get("docs") or [])
    docs_b = set(results.get("B", {}).get("docs") or [])
    consensus = sorted(docs_a & docs_b)
    only_a = sorted(docs_a - docs_b)
    only_b = sorted(docs_b - docs_a)
    merged = consensus + only_a + only_b[: max(0, max_docs - len(consensus) - len(only_a))]
    merged = merged[:max_docs]

    # ── 完整文档读取(truncated 自动续读) ──
    mc = __import__("benchmark-suite.scripts.lib", fromlist=["McpClient"]) if False else None
    sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
    from lib import McpClient
    mc = McpClient()
    reads: list[dict] = []
    total = 0
    try:
        cat = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
        kb_of = {}
        for k in cat:
            kb_id = k.get("kb_id") or k.get("name")
            kb_of[str(k.get("name") or "").replace("\\", "/").lower()] = kb_id
            kb_of[norm(k.get("kb_id"))] = kb_id
        for path in merged:
            kb_name = path.split("/")[0]
            kb_id = kb_of.get(kb_name.lower()) or kb_name
            content, offset, truncated, reads_n = "", 0, True, 0
            while truncated and reads_n < 8 and total < total_chars_cap:
                r = mc.call("kb_doc_read",
                            {"kb_id": kb_id, "doc_path": path.split("/", 1)[-1]
                             if "/" in path else path,
                             "offset": offset, "max_chars": doc_chars}, timeout=180)
                piece = str(r.get("content") or "")
                if not piece:
                    break
                content += piece
                total += len(piece)
                reads_n += 1
                truncated = bool(r.get("truncated"))
                offset += piece.count("\n") + 1
            reads.append({"doc_path": path, "chars": len(content),
                          "reads": reads_n, "capped": truncated,
                          "in_consensus": path in docs_a and path in docs_b,
                          "from_a": path in docs_a, "from_b": path in docs_b,
                          "content": content})
    finally:
        mc.close()

    wa, wb = results.get("A", {}), results.get("B", {})
    a0, a1 = float(wa.get("start") or 0), float(wa.get("end") or 0)
    b0, b1 = float(wb.get("start") or 0), float(wb.get("end") or 0)
    # 区间相交判定(0.0 是合法起点, 不可用 or-默认值吞掉)
    overlap = a1 > b0 and b1 > a0
    out = {"query": query, "worker_wall_s": merge_s,
           "parallelism": {"workers_overlapped": bool(overlap),
                           "A": [wa.get("start"), wa.get("end")],
                           "B": [wb.get("start"), wb.get("end")]},
           "total_s": round(time.time() - t0, 1),
           "workers": {k: {kk: vv for kk, vv in v.items() if kk != "trace"}
                       for k, v in results.items()},
           "merge": {"a_docs": len(docs_a), "b_docs": len(docs_b),
                     "consensus": len(consensus), "merged": len(merged)},
           "reads_summary": [{k: v for k, v in r.items() if k != "content"} for r in reads],
           "total_chars": total,
           "docs": reads}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"mode": "C-parallel", "out": str(out_path),
                      "merge_s": merge_s, "total_s": out["total_s"],
                      "merge": out["merge"], "docs": len(reads),
                      "chars": total}, ensure_ascii=False))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker-b", action="store_true", help="内部: 以 B 工作者模式运行")
    ap.add_argument("--query", default="")
    ap.add_argument("--shelves", default="", help="B 臂 L1 书架标签(逗号分隔; 空=全部 KB)")
    ap.add_argument("--out", default="")
    ap.add_argument("--max-docs", type=int, default=12)
    ap.add_argument("--doc-chars", type=int, default=24000)
    ap.add_argument("--total-chars-cap", type=int, default=160_000)
    args = ap.parse_args()
    shelves = [s.strip() for s in args.shelves.split(",") if s.strip()]
    if args.worker_b:
        r = worker_b(args.query, Path(args.out), shelves)
        print(json.dumps({"worker": "B", "seconds": r["seconds"],
                          "docs": len(r["docs"]), "scored": r["scored"]},
                         ensure_ascii=False))
        return 0
    if not args.query or not args.out:
        print("usage: --query ... --out ... [--shelves ...]")
        return 1
    run_parallel_c(args.query, Path(args.out), shelves,
                   args.max_docs, args.doc_chars, args.total_chars_cap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
