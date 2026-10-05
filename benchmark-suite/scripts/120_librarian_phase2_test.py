#!/usr/bin/env python3
"""图书馆员逐级检索对照测试（L0–L7）— 长篇小说长弧问题。

对照三条路径，同一 chat API、同一证据预算作答，再按关键情节覆盖逐条评分：
  P1 向量优先（kb_search_vector → 内容门控）
  P2 图书馆员（**只信描述**）：kb_list 库描述 → kb_get_documents 文档描述 → 按章节范围选 part
  P3 图书馆员 + **L3 描述信任检查**：检测样板化/无信息描述 → 不可信时不按描述选，
     改用**逐 beat 内容探针**（kb_search_two_stage 限定在该书架）→ 精读命中 part

用法（benchmark-suite/）：
    python scripts/120_librarian_phase2_test.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

from chat_tracks import answer_closed_book  # noqa: E402
from lib import McpClient  # noqa: E402

QUESTION = ("Trace how Elizabeth Bennet's opinion of Fitzwilliam Darcy changes across the whole "
            "novel — from the Meryton assembly to their final engagement. Which scenes are the "
            "turning points, and how does Darcy himself change?")

REWRITE = ("Elizabeth Bennet changing opinion of Darcy: first impressions at the Meryton assembly, "
           "Wickham's account, the first proposal at Hunsford and her refusal, Darcy's letter, "
           "the visit to Pemberley, the Lydia elopement, and the second proposal")

BEATS = [
    ("B1 assembly insult", 3,
     "Meryton assembly Darcy tolerable not handsome insult"),
    ("B2 Wickham's account", 16,
     "Wickham account of Darcy's ill treatment of him"),
    ("B3 first proposal + refusal", 34,
     "Hunsford first proposal Darcy in vain have I struggled Elizabeth refusal"),
    ("B4 Darcy's letter", 35,
     "Darcy letter delivered Elizabeth Georgiana explanation"),
    ("B5 Pemberley visit", 43,
     "Pemberley visit Elizabeth housekeeper Darcy's character"),
    ("B6 Lydia elopement", 46,
     "Lydia elopement Brighton Wickham news"),
    ("B7 second proposal", 58,
     "second proposal Elizabeth Darcy engaged aunt Lady Catherine"),
]

RANGE_RE = re.compile(r"Chapter\s+([IVXLC]+)\s*[–\-—]\s*([IVXLC]+)", re.I)
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}

# 关键情节的"真值 part"——由**内容核对**得出（不是描述），用于**与答案方差无关**的检索召回评估。
# 来源：子 Agent 的逐 part 内容核对（results/NOVEL-LONGTEXT-TEST.md）。
BEAT_TRUTH = {"B1": {2}, "B2": {6, 7}, "B3": {13}, "B4": {13, 14},
              "B5": {17}, "B6": {18}, "B7": {24}}


def beat_recall(parts) -> float:
    s = set(parts)
    return round(sum(1 for v in BEAT_TRUTH.values() if s & v) / len(BEAT_TRUTH), 3)


def roman(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s.upper().strip()):
        v = ROMAN.get(ch, 0)
        total += v if v >= prev else -v
        prev = max(prev, v)
    return total


def chapter_span(desc: str):
    m = RANGE_RE.search(desc or "")
    return (roman(m.group(1)), roman(m.group(2))) if m else None


def part_no(name: str) -> int:
    m = re.search(r"part (\d+) of \d+", name or "")
    return int(m.group(1)) if m else 0


def excerpt(text: str, query: str, size: int) -> str:
    text = str(text or "")
    if len(text) <= size:
        return text
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    step = max(1, size // 2)
    best_i, best = 0, -1
    for i in range(0, len(text) - size + 1, step):
        w = text[i:i + size]
        s = sum(1 for t in re.findall(r"[a-z0-9]+", w.lower()) if t in terms)
        if s > best:
            best, best_i = s, i
    return text[best_i:best_i + size]


def covered(ans: str) -> dict:
    low = (ans or "").lower()
    keys = {"B1": ["assembly", "insult", "meryton", "tolerable"],
            "B2": ["wickham"], "B3": ["hunsford", "first proposal", "refus"],
            "B4": ["letter", "never knew myself", "georgiana"],
            "B5": ["pemberley"], "B6": ["lydia", "elopement"],
            "B7": ["second proposal", "engaged", "engagement", "aunt"]}
    return {k: any(w in low for w in ws) for k, ws in keys.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default="Novel-PridePrejudice")
    ap.add_argument("--budget", type=int, default=12000)
    ap.add_argument("--out", default="results/LIBRARIAN-PHASE2-TEST.md")
    args = ap.parse_args()

    mc = McpClient()
    log: dict = {"question": QUESTION, "kb": args.kb}
    try:
        # L0 catalog
        kbs = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
        kb_id = next((k.get("kb_id") for k in kbs if k.get("name") == args.kb), "")
        if not kb_id:
            print(f"[fatal] KB {args.kb!r} not found")
            return 1
        log["L0_kbs"] = len(kbs)

        # P1 vector
        t0 = time.perf_counter()
        v = mc.call("kb_search_vector",
                    {"query": REWRITE, "kb_id": kb_id, "top_k": 10,
                     "score_threshold": 0.35, "balance_kbs": True}, timeout=300)
        p1_hits = [{"path": str(h.get("doc_path", "")).replace("\\", "/").rsplit("/", 1)[-1],
                    "score": round(float(h.get("score", 0)), 4),
                    "text": str(h.get("content", ""))} for h in (v.get("results") or [])]
        p1_parts = sorted({part_no(h["path"]) for h in p1_hits if part_no(h["path"])})
        log["P1"] = {"seconds": round(time.perf_counter() - t0, 1),
                     "parts": p1_parts,
                     "scores": [{"part": part_no(h["path"]), "s": h["score"]} for h in p1_hits]}

        # L2 shelf scan
        docs = mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                       timeout=180).get("catalog") or []
        uniq, seen = [], set()
        for d in sorted(docs, key=lambda x: str(x.get("name"))):
            pn = part_no(str(d.get("name") or ""))
            if not pn or pn in seen:
                continue
            seen.add(pn)
            uniq.append({"part": pn, "name": str(d.get("name") or ""),
                         "path": str(d.get("doc_path") or ""),
                         "span": chapter_span(str(d.get("description") or "")),
                         "desc": str(d.get("description") or "")})
        log["L2_parts"] = len(uniq)

        # ── L3 description trust check ──
        # Compare the *structural label* `【Part k/N · <label>】`, not the whole
        # description (each description also embeds unique body text, so a naive
        # full-text compare never detects boilerplate — measured 2026-09-24).
        LABEL_RE = re.compile(r"【([^】]+)】")
        CONTENT_FREE = ("front/back matter", "gutenberg")

        def label_of(desc: str) -> str:
            m = LABEL_RE.search(desc or "")
            return m.group(1).strip() if m else ""

        labels = Counter(label_of(p["desc"]) for p in uniq)
        boiler_labels = {l for l, c in labels.items() if l and c >= 3}
        content_free = {l for l in labels if any(w in l.lower() for w in CONTENT_FREE)}

        def untrusted_p(p) -> bool:
            l = label_of(p["desc"])
            return bool(l) and (l in boiler_labels or l in content_free)

        untrusted = [p for p in uniq if untrusted_p(p)]
        degenerate = [p for p in uniq if p["span"] and p["span"][0] >= p["span"][1]]
        trusted = [p for p in uniq if p not in untrusted]
        log["L3"] = {"label_groups": dict(labels),
                     "boilerplate_labels": sorted(boiler_labels),
                     "content_free_labels": sorted(content_free),
                     "untrusted_parts": len(untrusted),
                     "untrusted_ids": [p["part"] for p in untrusted],
                     "degenerate_spans": [p["part"] for p in degenerate],
                     "trusted_parts": len(trusted)}

        # ── P2: description-only selection (the naive librarian) ──
        picked2: dict[int, list[str]] = {}
        for label, ch, _ in BEATS:
            hit = next((p for p in uniq if p["span"] and p["span"][0] <= ch <= p["span"][1]), None)
            if hit:
                picked2.setdefault(hit["part"], []).append(label)
        log["P2_parts"] = sorted(picked2)

        # ── P3: L3-aware selection — descriptions untrusted → per-beat content probes ──
        picked3: dict[int, list[str]] = {}
        scores3: dict[int, float] = {}
        if len(untrusted) > len(uniq) * 0.5:
            log["P3_strategy"] = "content_probes (descriptions distrusted)"
            for label, ch, q in BEATS:
                r = mc.call("kb_search_two_stage",
                            {"query": q, "kb_id": kb_id, "stage1_top_k": 20,
                             "stage2_top_k": 5, "score_threshold": 0.30}, timeout=300)
                # kb_search_two_stage returns {stage1:{candidates}, stage2:{results}}
                hits = (r.get("stage2") or {}).get("results") or r.get("results") or []
                for c in hits:
                    pn = part_no(str(c.get("doc_path", "")))
                    if pn:
                        picked3.setdefault(pn, []).append(label)
                        scores3[pn] = max(scores3.get(pn, 0.0),
                                          float(c.get("score", 0) or 0))
            # ⭐ budget-aware shortlist cap: never select more parts than the
            # evidence budget can cover (≈2000 chars/part). Over-selection dilutes
            # every part's excerpt and *lowers* answer quality (measured).
            cap = max(3, args.budget // 2000)
            keep = sorted(picked3, key=lambda p: -scores3.get(p, 0))[:cap]
            log["P3_cap"] = {"cap": cap, "before": len(picked3), "after": len(keep)}
            picked3 = {p: picked3[p] for p in keep}
        else:
            log["P3_strategy"] = "description_mapping (descriptions trusted)"
            picked3 = picked2
        log["P3_parts"] = sorted(picked3)

        # L5 read the picked parts for both P2 and P3
        def read_parts(picked: dict) -> list[dict]:
            units, per = [], max(900, args.budget // max(1, len(picked)))
            for pn in sorted(picked):
                p = next(x for x in uniq if x["part"] == pn)
                r = mc.call("kb_doc_read", {"kb_id": kb_id, "doc_path": p["path"],
                                            "max_chars": 20000}, timeout=180)
                units.append({"src": f"part {pn}",
                              "text": excerpt(str(r.get("content") or ""), QUESTION, per)})
            return units

        u2 = read_parts(picked2)
        u3 = read_parts(picked3)
        log["L5_reads"] = {"P2": len(u2), "P3": len(u3)}
    finally:
        mc.close()

    ev1 = "\n\n".join(f"[{u['src']}] {u['text'][:1200]}" for u in
                      [{"src": f"part {part_no(h['path'])}", "text": h["text"]} for h in p1_hits]
                      )[:args.budget]
    ev2 = "\n\n".join(f"[{u['src']}] {u['text']}" for u in u2)[:args.budget]
    ev3 = "\n\n".join(f"[{u['src']}] {u['text']}" for u in u3)[:args.budget]

    a1 = answer_closed_book(QUESTION, ev1)
    a2 = answer_closed_book(QUESTION, ev2)
    a3 = answer_closed_book(QUESTION, ev3)
    c1, c2, c3 = (sum(covered(a1.get("answer") or "").values()),
                  sum(covered(a2.get("answer") or "").values()),
                  sum(covered(a3.get("answer") or "").values()))
    log["answers"] = {"P1": a1.get("answer"), "P2": a2.get("answer"), "P3": a3.get("answer")}
    log["covered"] = {"P1": covered(a1.get("answer") or ""),
                      "P2": covered(a2.get("answer") or ""),
                      "P3": covered(a3.get("answer") or "")}
    log["cost"] = {"P1": a1.get("total_cost_usd"), "P2": a2.get("total_cost_usd"),
                   "P3": a3.get("total_cost_usd")}

    L = ["# 图书馆员逐级检索测试（L0–L7）— 长篇小说长弧问题", "",
         f"**问题**：{QUESTION}", "",
         f"**KB**：`{args.kb}` · 证据预算 {args.budget} chars · 同一 chat API 作答", "",
         "## L0–L5 逐级轨迹", "",
         f"- **L0** 读库描述：{log['L0_kbs']} 个库",
         f"- **L2** 读文档描述：{log['L2_parts']} 个 part",
         f"- **L3 描述信任检查**：样板化标签 {log['L3']['boilerplate_labels']} · "
         f"无信息标签 {log['L3']['content_free_labels']} → "
         f"不可信 part **{log['L3']['untrusted_parts']}**/{log['L2_parts']}；"
         f"退化章节区间 {log['L3']['degenerate_spans']}",
         f"- **P3 选择策略**：{log['P3_strategy']}", "",
         "## 三路对照", "",
         "> **稳健指标 = 检索召回**：选中的 part 是否覆盖 7 个关键情节的**真值 part**"
         "（由内容核对得出，与答案措辞无关）。答案覆盖列受 LLM 单次运行方差影响，仅供参考。", "",
         "| 路径 | 选中 part | **检索召回(真值 part)** | 答案覆盖 | 成本 $ |",
         "|---|---|:--:|:--:|---:|",
         f"| P1 向量优先 | {p1_parts} | **{beat_recall(p1_parts)}** | {c1}/7 | {log['cost']['P1']} |",
         f"| P2 图书馆员（只信描述） | {sorted(picked2)} | **{beat_recall(picked2)}** | {c2}/7 | {log['cost']['P2']} |",
         f"| P3 图书馆员 + L3 信任检查 | {sorted(picked3)} | **{beat_recall(picked3)}** | {c3}/7 | {log['cost']['P3']} |",
         "", "## 逐 beat 覆盖（答案措辞）", "",
         "| beat | P1 | P2 | P3 |", "|---|:--:|:--:|:--:|"]
    for k in ("B1", "B2", "B3", "B4", "B5", "B6", "B7"):
        L.append(f"| {k} | {'✓' if log['covered']['P1'][k] else '✗'} | "
                 f"{'✓' if log['covered']['P2'][k] else '✗'} | "
                 f"{'✓' if log['covered']['P3'][k] else '✗'} |")
    for tag in ("P1", "P2", "P3"):
        L += ["", f"## {tag} 答案（verbatim）", "", log["answers"][tag] or "(空)", ""]

    out = SUITE / args.out
    out.write_text("\n".join(L), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(log, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print("\n".join(L[:20]))
    print(f"\n[test] P1 {c1}/7 · P2 {c2}/7 · P3 {c3}/7 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
