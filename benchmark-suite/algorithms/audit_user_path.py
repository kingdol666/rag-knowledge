#!/usr/bin/env python3
"""用户文档路径审计 — 可复跑的回归检测(证据通道 + 修复对照).

检测 1: methods.Ctx.vector 是否丢弃后端返回的真实 chunk 文本
        (后端 kb_search_vector 一直返回 {content, chunk_index, doc_path})。
检测 2: methods.dense 的 [:1400] 截断在长文档上的证据覆盖率。
检测 3: A/B 对照 — 同一问题/同一模型/同一 prompt, 只换证据文本,
        验证"用真实 chunk content"能否恢复正确答案。

用法:
  python audit_user_path.py                       # 用内置测试文档
  python audit_user_path.py --doc <path> --question "<q>"
前置: 后端 8771 + omp 可用; 生产 KB/基线 KB 已由 ask_user_docs.py 建好。
退出码: 0 = 检测通过(无缺陷); 1 = 检出缺陷。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

import methods  # noqa: E402
import user_scenario as us  # noqa: E402
from index_kb import load_texts  # noqa: E402
from lib import McpClient  # noqa: E402
from omp_client import OmpOneshot  # noqa: E402

DEFAULT_DOC = HERE / "_verify_userdoc" / "orbital-debris-removal.md"
DEFAULT_Q = ("How does the ion-beam shepherd remove orbital debris, and what "
             "delta-v is required for a spent rocket upper stage?")
KB = "VerifyDemo-Chunks800"          # 单遍/ITRG 分支的索引(dense_rag 用)
ANSWER_CHARS = 1400                  # methods.dense 的截断长度


def vector_fixed(self, kb, query, top_k):
    """修复版 Ctx.vector: 用后端返回的真实 chunk content(chunk_index 去重)。"""
    r = self.mc.call("kb_search_vector",
                     {"query": query, "kb_id": kb, "top_k": top_k},
                     timeout=300)
    out, seen = [], set()
    for h in r.get("results") or []:
        dp = str(h.get("doc_path", ""))
        key = (dp, h.get("chunk_index"))
        if key in seen:
            continue
        seen.add(key)
        out.append({"path": dp, "score": float(h.get("score", 0)),
                    "text": str(h.get("content") or "")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=str(DEFAULT_DOC))
    ap.add_argument("--question", default=DEFAULT_Q)
    ap.add_argument("--prefix", default="VerifyDemo")
    ap.add_argument("--prod-kb", default="KB-VerifyDemo")
    ap.add_argument("--skip-ab", action="store_true", help="跳过 A/B LLM 对照")
    args = ap.parse_args()

    text = Path(args.doc).read_text(encoding="utf-8", errors="replace")
    print(f"[doc] {args.doc}  len={len(text)}")
    defective = False

    # ── 检测 1+2: 证据替换与截断 ──────────────────────────────────────────
    texts = load_texts(KB)
    mc = McpClient()
    try:
        hits = mc.call("kb_search_vector",
                       {"query": args.question, "kb_id": KB, "top_k": 3},
                       timeout=300).get("results") or []
    finally:
        mc.close()
    if not hits:
        print("[skip] 索引未就绪 — 先跑 ask_user_docs.py 建库")
        return 2

    top = hits[0]
    content = str(top.get("content") or "")
    dp = str(top.get("doc_path") or "")
    item = (texts.get(dp) or {}).get("text", "")
    substituted = item[:ANSWER_CHARS]

    print(f"\n=== 检测 1: 真实命中 chunk vs 复现层实际证据 ===")
    print(f"  后端 top-1: chunk_index={top.get('chunk_index')} "
          f"score={float(top.get('score', 0)):.4f} len={len(content)}")
    print(f"  后端返回 content 字段: {'有' if content else '无'}"
          f"  (methods.Ctx.vector 是否使用: 否 ← 缺陷点)")
    print(f"  复现层代之以 item 文本前 {ANSWER_CHARS} 字符: len={len(substituted)}")
    for probe in ("delta-v", "180 metres per second", "ion-beam shepherd"):
        in_c, in_s = probe in content, probe in substituted
        flag = "  <== 证据丢失" if (in_c and not in_s) else ""
        print(f"    {probe!r:<26} 真实chunk={in_c!s:<6} 实际证据={in_s!s:<6}{flag}")
        if in_c and not in_s:
            defective = True

    print(f"\n=== 检测 2: [:1400] 在长文档上的覆盖率 ===")
    for L in (1278, 3029, 15300):
        print(f"  item={L:>6} chars → {min(ANSWER_CHARS, L)/L:>6.1%}")
    if item:
        cov = min(ANSWER_CHARS, len(item)) / len(item)
        print(f"  本测试文档: {cov:.1%} (丢弃 {max(0, len(item)-ANSWER_CHARS)} 字符)")
        if cov < 0.99:
            defective = True

    # ── 检测 3: A/B 对照 ─────────────────────────────────────────────────
    if not args.skip_ab:
        docs = us.load_user_docs([Path(args.doc)])
        us.activate_profile(args.prefix, args.prod_kb)
        ctx_get = us.make_ctx_factory(McpClient, docs, args.prefix)
        oneshot = OmpOneshot(stage="answer", timeout=420)
        orig = methods.Ctx.__dict__["vector"]
        print(f"\n=== 检测 3: A/B 对照(仅证据文本不同) ===")
        for label, fn in (("A) 现状: item 文本 + [:1400]", orig),
                          ("B) 修复: 真实 chunk content", vector_fixed)):
            methods.Ctx.vector = fn
            ev = methods.dense(ctx_get(), args.question, rerank=False)
            ev_text, _ = methods.pack(ev.get("chunks") or [])
            covered = "delta-v" in ev_text
            ans = (us.answer_question(lambda s: oneshot, args.question, ev)
                   .get("parsed") or {}).get("answer", "")
            print(f"  {label}")
            print(f"    证据含 'delta-v': {covered}  chars={len(ev_text)}")
            print(f"    回答: {ans[:240]}")
            if not covered:
                defective = True
        methods.Ctx.vector = orig

    print(f"\n=== 结论: {'检出缺陷 (见上 <== 标记)' if defective else '通过'} ===")
    return 1 if defective else 0


if __name__ == "__main__":
    sys.exit(main())
