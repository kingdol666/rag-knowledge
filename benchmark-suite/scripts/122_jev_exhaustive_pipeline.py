#!/usr/bin/env python3
"""逐级检索增强：**穷尽召回 → Jev 判断剔除 → 只把真正有用的放进上下文作答**。

流程（对应 knowledgebase-librarian 的 L0–L7 + L5.5 Jev 层）：
  L0  kb_list(lightweight)                     读每个库的描述，定位书架
  L2  kb_get_documents(lightweight)            读该库**每篇文档**的描述
  L4  **穷尽召回**：kb_doc_read 每篇文档的头部（不做任何相似度筛选）
      → 候选 = 全部文档（不是 top-k）
  L5.5 ⭐ **Jev 判断层**：把每个候选文本 + 问题交给 Jev（noul 问句
      "这段文字是否包含能直接帮助回答该问题的具体证据？"）→ 只保留通过阈值的
  L5  对**保留下来**的文档做深读（更大窗口）
  L7  用保留的证据作答（同一 chat API）

用法（benchmark-suite/）：
    python scripts/122_jev_exhaustive_pipeline.py --question "..." [--kb Novel-PridePrejudice]
    python scripts/122_jev_exhaustive_pipeline.py --question "..." --threshold 0.5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

from chat_tracks import answer_closed_book  # noqa: E402
from jev_judge import available as jev_available, judge as jev_judge  # noqa: E402
from lib import McpClient  # noqa: E402

HEAD_CHARS = 1200      # window size for the judgment gate
DEEP_CHARS = 6000      # L5 deep-read window for survivors
N_WINDOWS = 3          # head / mid / tail sampling per document part
STOP = {"the", "and", "for", "with", "that", "this", "what", "does", "did", "was",
        "were", "are", "how", "why", "who", "when", "where", "which", "say", "said",
        "about", "into", "from", "her", "him", "his", "she", "they", "their", "you"}


def terms(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]{3,}", (s or "").lower()) if t not in STOP}


def desc_select(query: str, uniq: list[dict]) -> list[int]:
    """L2.5 — description-driven candidate selection, GENEROUS by design.

    'Possibly relevant' means ANY lexical overlap with the query — the whole point is
    completeness, so this must not behave like a top-k. Everything that overlaps is read;
    the JeV gate does the pruning afterwards (on content, not on descriptions).
    """
    q = terms(query)
    if not q:
        return list(range(len(uniq)))
    hits = []
    for i, p in enumerate(uniq):
        blob = f"{p.get('name','')} {p.get('desc','')}"
        n = len(q & terms(blob))
        if n:
            hits.append((n, i))
    hits.sort(key=lambda x: -x[0])
    return [i for _, i in hits]


def part_no(name: str) -> int:
    m = re.search(r"part (\d+) of \d+", name or "")
    return int(m.group(1)) if m else 0


def windows(text: str, size: int = HEAD_CHARS, n: int = N_WINDOWS) -> list[str]:
    """Sample n evenly-spaced windows. Judging a long part by its HEAD alone drops
    the parts whose evidence sits deeper — measured 2026-09-24: a head-only gate
    scored 25% scene recall vs 70% for vector top-k, because the gate never saw the
    answering passage. Sampling head/mid/tail fixes exactly that."""
    t = str(text or "")
    if len(t) <= size:
        return [t] if t.strip() else []
    step = (len(t) - size) / (n - 1) if n > 1 else 0
    return [t[int(i * step): int(i * step) + size] for i in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--kb", default="Novel-PridePrejudice")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--backend", default="auto", choices=["auto", "sdk", "http", "llm", "none"])
    ap.add_argument("--mode", default="desc", choices=["desc", "all", "union"],
                    help="desc=description-driven recall-all (default) · "
                         "all=read every doc · union=desc ∪ vector top-k (max completeness)")
    ap.add_argument("--out", default="results/JEV-EXHAUSTIVE-PIPELINE.md")
    args = ap.parse_args()

    t0 = time.perf_counter()
    log: dict = {"question": args.question, "kb": args.kb,
                 "jev_env": jev_available()}

    mc = McpClient()
    try:
        kbs = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
        kb_id = next((k.get("kb_id") for k in kbs if k.get("name") == args.kb), "")
        if not kb_id:
            print(f"[fatal] KB {args.kb!r} not found")
            return 1
        log["L0_kbs"] = len(kbs)

        docs = mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                       timeout=180).get("catalog") or []
        # Keep EVERY document entry — sub-split parts ("(part 1 of 2)") each hold
        # different content; deduping by part number silently drops half of them.
        uniq = [{"name": str(d.get("name") or ""), "path": str(d.get("doc_path") or ""),
                 "part": part_no(str(d.get("name") or "")),
                 "desc": str(d.get("description") or "")}
                for d in sorted(docs, key=lambda x: str(x.get("name")))]
        log["L2_parts"] = len(uniq)

        # ── L2.5 candidate selection (description-driven by default) ──
        if args.mode == "all":
            sel = list(range(len(uniq)))
        else:
            sel = desc_select(args.question, uniq)
        if args.mode in ("desc", "union") and len(sel) < 3:
            log["L2_5_broadened"] = True
            sel = list(range(len(uniq)))
        log["mode"] = args.mode
        log["L2_5_selected"] = len(sel)

        if args.mode == "union":
            # completeness: union with the vector lane — the two mechanisms miss
            # different parts (measured), so the union is strictly safer.
            v = mc.call("kb_search_vector", {"query": args.question, "kb_id": kb_id,
                                             "top_k": 10, "score_threshold": 0.0},
                        timeout=300)
            vpaths = {str(x.get("doc_path", "")).replace("\\", "/")
                      for x in (v.get("results") or [])}
            for i, p in enumerate(uniq):
                if p["path"].replace("\\", "/") in vpaths and i not in sel:
                    sel.append(i)
            log["L2_5_after_union"] = len(sel)

        # ── L4 exhaustive recall over the selected candidates ──
        cands = []
        for i in sel:
            p = uniq[i]
            r = mc.call("kb_doc_read", {"kb_id": kb_id, "doc_path": p["path"],
                                        "max_chars": 20000}, timeout=180)
            body = str(r.get("content") or "")
            cands.append({"part": p["part"], "name": p["name"], "path": p["path"],
                          "text": body, "windows": windows(body)})
        log["L4_candidates"] = len(cands)
        log["L4_windows"] = sum(len(c["windows"]) for c in cands)
    finally:
        mc.close()

    # ── L5.5 Jev judgment layer (WINDOW-level) ──
    # Judge every window, not every part: a part survives if ANY of its windows
    # carries answering evidence. Judging a whole part by one head window is the
    # failure mode measured on 2026-09-24.
    flat: list[str] = []
    owner: list[int] = []
    for ci, c in enumerate(cands):
        for w in c["windows"]:
            flat.append(w)
            owner.append(ci)
    t1 = time.perf_counter()
    verdict = jev_judge(args.question, flat, threshold=args.threshold, backend=args.backend)
    log["L5_5_jev"] = {k: v for k, v in verdict.items() if k != "results"}
    log["L5_5_jev"]["judge_seconds"] = round(time.perf_counter() - t1, 1)
    log["L5_5_jev"]["granularity"] = "window"
    log["L5_5_jev"]["windows"] = len(flat)

    kept_idx = sorted({owner[i] for i in verdict["kept_index"]})
    kept_parts = sorted({cands[i]["part"] for i in kept_idx if cands[i]["part"]})
    log["L5_5_kept_parts"] = kept_parts
    log["L5_5_kept_docs"] = len(kept_idx)

    # ── L5 deep-read the KEPT docs only ──
    mc = McpClient()
    units = []
    try:
        kb_id = next((k.get("kb_id") for k in
                      (mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or [])
                      if k.get("name") == args.kb), "")
        for i in kept_idx:
            c = cands[i]
            r = mc.call("kb_doc_read", {"kb_id": kb_id, "doc_path": c["path"],
                                        "max_chars": DEEP_CHARS}, timeout=180)
            units.append({"src": c["name"].replace(".md", ""),
                          "text": str(r.get("content") or "")})
    finally:
        mc.close()

    evidence = "\n\n".join(f"[{u['src']}] {u['text']}" for u in units)[:20000]
    ans = answer_closed_book(args.question, evidence)
    log["answer"] = ans.get("answer")
    log["answer_cost"] = ans.get("total_cost_usd")
    log["evidence_chars"] = len(evidence)
    log["total_seconds"] = round(time.perf_counter() - t0, 1)

    L = ["# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答", "",
         f"**问题**：{args.question}", "",
         f"**KB**：`{args.kb}` · 阈值 {args.threshold} · 判断后端 `{verdict['backend']}`", "",
         "## 管线轨迹", "",
         f"- **L0** 读库描述：{log['L0_kbs']} 个库",
         f"- **L2** 读文档描述：{log['L2_parts']} 篇",
         f"- **L2.5 候选选择**（mode `{args.mode}`）："
         f"{log.get('L2_5_selected', '?')}/{log['L2_parts']} 篇"
         + (f" → 并集后 {log.get('L2_5_after_union')}" if log.get("L2_5_after_union") else ""),
         f"- **L4 穷尽召回**：读全部 **{log['L4_candidates']}** 篇（无相似度筛选）",
         f"- **L5.5 Jev 判断**：后端 `{verdict['backend']}` · 模型 `{verdict.get('model')}` · "
         f"{log['L5_5_jev']['judge_seconds']}s → 保留 **{len(kept_parts)}** 篇：{kept_parts}",
         f"- **L5 深读**：{len(units)} 篇 × {DEEP_CHARS} 字符 → 证据 {log['evidence_chars']} 字符",
         f"- **L7 作答**：{log['total_seconds']}s · ${log['answer_cost']}", ""]
    if verdict.get("note"):
        L += [f"> ⚠️ {verdict['note']}", ""]
    L += ["## 每个窗口的判断分（窗口→所属 part）", "",
          "| 窗口 | 所属 part | 分 | 保留 |", "|---|---|---:|:--:|"]
    for r in verdict["results"]:
        ci = owner[r["index"]]
        L.append(f"| w{r['index']} | {cands[ci]['part']} | "
                 f"{'—' if r['score'] is None else round(r['score'], 3)} | "
                 f"{'✓' if r['kept'] else '✗'} |")
    L += ["", "## 作答（verbatim）", "", log["answer"] or "(空)", ""]

    out = SUITE / args.out
    out.write_text("\n".join(L), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(log, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print("\n".join(L[:22]))
    print(f"\n[jev] → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
