#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""论文 Table 1（入库/整理半边）现场审计（只读）。

为什么需要：`150_final_pipeline.py` 只刷新论文的**检索**半边（a2/b/c 30 单元）。
论文 Table 1 里 "Papers parsed 100 · Stored parts 322 · Descriptions upgraded 165 ·
Content+storage audits 322/322 · Retrieval regression 15/15 · chunks800 4528" 这些
数字，出处是 `results/r2_pipeline_100.json`（由 `108_pipeline_evidence.py` 从历史
产物汇总）。本脚本不重跑入库，而是在**当前活动实例**上现场核对这批数字是否还成立，
输出可直接对照论文的结论，避免"表里一半数字来自三个月前的产物"这种复现风险。

做四件事（全部只读，不改任何 KB）：
  1. live catalog：五门类库列表、每库 doc 数、总数是否 322
  2. 逐库分页拉 `kb_get_documents`，统计：description 缺失/过短、part 命名、tags
  3. manifest ↔ 现场对账：100 篇 arXiv id 是否都能在五库里找到对应文档
  4. 密索引 `Corpus-Chunks800` live 探针（向量检索真命中，不看 doc_count）

用法:
    python scripts/155_paper_state_audit.py
    python scripts/155_paper_state_audit.py --json results/paper_state_audit.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

import lib  # noqa: E402

CATEGORIES = ("计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
              "工程与能源", "经济与社会")
PAPERS = 100
PARTS = 322
DESC_MIN = 40
PART_RE = re.compile(r"\(part\s+(\d+)\s+of\s+(\d+)\)", re.I)


def call(mc, name: str, args: dict, timeout: float = 120.0) -> dict:
    try:
        r = mc.call(name, args, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return {"_error": f"{type(e).__name__}: {e}"}
    if not isinstance(r, dict):
        return {}
    # kb-mcp wraps tool payloads as {"success":..., ...} or {"data": {...}}
    return r


def paged_docs(mc, kb_id: str, cap: int = 60) -> list[dict]:
    out: list[dict] = []
    page = 1
    while page <= cap:
        r = call(mc, "kb_get_documents",
                 {"kb_id": kb_id, "page": page, "page_size": 200})
        docs = r.get("catalog") or r.get("documents") or []
        if not docs:
            break
        out.extend(docs)
        if not r.get("has_more"):
            break
        page += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    manifest = json.loads((SUITE / "data" / "papers" / "manifest.json")
                          .read_text(encoding="utf-8"))["papers"]
    # Old-style ids (gr-qc/9805045, q-bio/0408016) and new-style
    # (2409.13934) both appear in corpus file names — compare on a
    # punctuation-free digest so neither form is missed.
    def _digest(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(s).lower())

    ids = {p["arxiv_id"]: _digest(p["arxiv_id"].split("v")[0]) for p in manifest}

    mc = lib.McpClient()
    try:
        cat = call(mc, "kb_list", {"lightweight": True})
        kbs = cat.get("catalog") or cat.get("kbs") or cat.get("knowledge_bases") or []
        by_name = {k.get("name"): k for k in kbs}
        print(f"[catalog] {len(kbs)} KBs · "
              f"{'5 门类库齐全' if all(c in by_name for c in CATEGORIES) else '缺门类库!'}")

        total = 0
        per_kb: dict[str, dict] = {}
        for name in CATEGORIES:
            k = by_name.get(name)
            if not k:
                per_kb[name] = {"missing": True}
                continue
            docs = paged_docs(mc, k.get("kb_id") or k.get("id") or name)
            desc_ok = sum(1 for d in docs
                          if len(str(d.get("description") or "").strip()) >= DESC_MIN)
            parts = [d for d in docs
                     if PART_RE.search(str(d.get("path") or d.get("name") or ""))]
            total += len(docs)
            per_kb[name] = {"docs": len(docs), "desc_ok": desc_ok,
                            "desc_missing": len(docs) - desc_ok,
                            "part_named": len(parts)}
            print(f"  {name:<12} docs={len(docs):<4} desc≥{DESC_MIN}字={desc_ok:<4} "
                  f"缺描述={len(docs) - desc_ok:<4} part命名={len(parts)}")

        found: set[str] = set()
        for name in CATEGORIES:
            if per_kb[name].get("missing"):
                continue
            k = by_name[name]
            for d in paged_docs(mc, k.get("kb_id") or k.get("id") or name):
                blob = _digest(f"{d.get('path', '')} {d.get('name', '')}")
                for i, dig in ids.items():
                    if dig in blob:
                        found.add(i)
        miss = sorted(set(ids) - found)

        probe_ok = 0
        probes = [("how does the Transformer compute attention", "1706.03762"),
                  ("GAN-based downscaling of climate model output", "2409.13934")]
        for q, gold in probes:
            r = call(mc, "kb_search_vector",
                     {"query": q, "kb_id": "Corpus-Chunks800", "top_k": 5})
            hits = r.get("results") or []
            rank = next((i + 1 for i, h in enumerate(hits)
                         if gold in json.dumps(h)), 0)
            probe_ok += 1 if rank else 0
            print(f"[chunks800] {gold}: hit_rank={rank or 'MISS'} "
                  f"(hits={len(hits)})")
    finally:
        try:
            mc.close()
        except Exception:  # noqa: BLE001
            pass

    checks = [
        ("五门类库齐全", all(not per_kb[c].get("missing") for c in CATEGORIES)),
        (f"门类库文档总数={PARTS}", total == PARTS),
        (f"密索引可检索（{probe_ok}/{len(probes)} 探针命中）", probe_ok == len(probes)),
        (f"manifest {PAPERS} 篇全在库里", not miss and len(ids) == PAPERS),
    ]
    print("\n[结论]")
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    if miss:
        print(f"  缺: {miss[:8]}{' …' if len(miss) > 8 else ''}")

    out = {"categories": per_kb, "total_docs": total, "manifest_found": len(found),
           "manifest_ids": len(ids), "missing": miss, "chunks800_probe_hits": probe_ok,
           "checks": [{"claim": n, "ok": ok} for n, ok in checks]}
    if a.json:
        p = Path(a.json)
        if not p.is_absolute():
            p = SUITE / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n→ {p}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
