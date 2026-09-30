#!/usr/bin/env python3
"""混合检索串行流程(S0-S6) ZCode 观察测试 — 每阶段打时间戳, 验证串行+去重合并.

不使用编排脚本; 逐阶段 MCP 工具调用(harness 等价物), 全程观察记录。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

QUERY = ("CoRoT 卫星的系外行星计划有哪些科学目标？它何时开始科学观测、任务延长到"
         "什么时候？截至 2010 年夏共收集了多少条光变曲线？为什么 CoRoT-7b 这类超级"
         "地球只能在较亮恒星的光变曲线中发现？")
SHELF = "自然科学与地球科学"
KB_ID = "1e6199ea-f380-44e2-94fc-d431f0f9bb6b"
log: list[dict] = []


def mark(phase: str, event: str, **kw) -> None:
    rec = {"t": round(time.perf_counter() - T0, 2), "phase": phase, "event": event}
    rec.update(kw)
    log.append(rec)
    print(f"[{rec['t']:7.2f}s] {phase} {event} " +
          " ".join(f"{k}={str(v)[:90]}" for k, v in kw.items()), flush=True)


def norm(kb_name_map: dict, kb_id: str, doc_path: str) -> tuple[str, str]:
    """(kb_id, doc_path) 归一化: 剥书架名前缀, 反斜杠→斜杠 (SKILL S3 规则)。"""
    p = str(doc_path).replace("\\", "/")
    for name in kb_name_map.values():
        pref = name + "/"
        if p.lower().startswith(pref.lower()):
            p = p[len(pref):]
            break
    return (str(kb_id), p)


T0 = time.perf_counter()
mc = McpClient()
kb_name_map: dict[str, str] = {KB_ID: SHELF}  # 向量命中 doc_path 带书架名前缀, S1 就要可剥
try:
    # ── S1 向量车道(先行, 只出 refs 不读内容) ──
    t1 = time.perf_counter()
    mark("S1", "start")
    res = mc.call("kb_search_vector", {"query": QUERY, "kb_id": KB_ID, "top_k": 30,
                                       "score_threshold": 0.35, "balance_kbs": True},
                  timeout=180)
    hits = res.get("result_list") or res.get("results") or res.get("hits") or []
    cand_a: dict[tuple[str, str], float] = {}
    for h in hits:
        kbn = str(h.get("kb_name") or "")
        if kbn:
            kb_name_map[str(h.get("kb_id") or KB_ID)] = kbn
        k = norm(kb_name_map, str(h.get("kb_id") or KB_ID),
                 str(h.get("doc_path") or h.get("path") or ""))
        sc = float(h.get("score") or 0)
        cand_a[k] = max(cand_a.get(k, 0.0), sc)
    s1_s = round(time.perf_counter() - t1, 2)
    mark("S1", "done", seconds=s1_s, raw_hits=len(hits), dedup_docs=len(cand_a),
         top=[f"{k[1].split('__')[-1][:40]}={round(v,3)}" for k, v in
              sorted(cand_a.items(), key=lambda x: -x[1])[:5]])

    # ── S2 内容车道(串行: S1 完成后才开始) ──
    t2 = time.perf_counter()
    mark("S2", "start")
    rows = mc.call("kb_get_documents", {"lightweight": True, "kb_id": KB_ID},
                   timeout=180).get("catalog") or []
    STOP = {"the", "and", "for", "with", "of", "to", "in", "on", "is", "are",
            "哪些", "多少", "为什么", "什么", "的", "了", "和"}
    import re as _re

    def terms(v: str) -> set:
        text = str(v or "").lower()
        latin = set()
        for run in _re.findall(r"[a-z0-9][a-z0-9_.\-]{1,}", text):
            for part in _re.split(r"[_.\-]+", run):
                part = part.strip(".'")
                if len(part) >= 3 and part not in STOP:
                    latin.add(part)
        return latin

    qterms = terms(QUERY) | {"corot", "exoplanet", "transit", "asteroseismology",
                             "light", "curves", "super-earth", "7b"}
    ranked = []
    for d in rows:
        blob = f"{d.get('name','')} {d.get('description','')}"
        ov = len(qterms & terms(blob))
        if ov > 0:
            ranked.append((ov, d))
    ranked.sort(key=lambda x: -x[0])
    cand_b: dict[tuple[str, str], dict] = {}
    budget = 6
    kb_name_map[KB_ID] = SHELF
    for ov, d in ranked[:budget]:
        r = mc.call("kb_doc_read", {"kb_id": KB_ID, "doc_path": d.get("doc_path"),
                                    "max_chars": 20000}, timeout=180)
        cand_b[norm(kb_name_map, KB_ID, str(d.get("doc_path")))] = {
            **d, "overlap": ov,
            "content": str(r.get("content") or ""), "truncated": bool(r.get("truncated"))}
    s2_s = round(time.perf_counter() - t2, 2)
    mark("S2", "done", seconds=s2_s, described=len(rows), overlap_docs=len(ranked),
         read=len(cand_b),
         picks=[f"{k[1].split('__')[-1][:40]}(ov={v['overlap']})" for k, v in cand_b.items()])

    # ── S3 去重合并 ──
    mark("S3", "start")
    merged: dict[tuple[str, str], dict] = {}
    for k, sc in cand_a.items():
        merged[k] = {"kb_id": k[0], "doc_path": k[1], "lane": "vector",
                     "vector_score": sc}
    for k, d in cand_b.items():
        if k in merged:
            merged[k]["lane"] = "both"
            merged[k]["content"] = d["content"]
            merged[k]["name"] = d.get("name")
            merged[k]["description"] = d.get("description")
        else:
            merged[k] = {"kb_id": k[0], "doc_path": k[1], "lane": "catalog",
                         "content": d["content"], "name": d.get("name"),
                         "description": d.get("description")}
    from_both = sum(1 for m in merged.values() if m["lane"] == "both")
    from_vec = sum(1 for m in merged.values() if m["lane"] == "vector")
    from_cat = sum(1 for m in merged.values() if m["lane"] == "catalog")
    mark("S3", "done", merged=len(merged), from_both=from_both,
         from_vector_only=from_vec, from_catalog_only=from_cat)

    # ── S4 LAYA 判卷: 先补读 vector-only, 再一次 kb_laya_judge ──
    mark("S4", "start")
    need_read = [m for m in merged.values()
                 if m["lane"] == "vector" and "content" not in m]
    for m in need_read:
        r = mc.call("kb_doc_read", {"kb_id": m["kb_id"], "doc_path": m["doc_path"],
                                    "max_chars": 20000}, timeout=180)
        m["content"] = str(r.get("content") or "")
    mark("S4", "vector_only_reread", docs=len(need_read))
    docs_payload = json.dumps([
        {"kb_id": m["kb_id"], "doc_path": m["doc_path"], "name": m.get("name") or "",
         "description": m.get("description") or "", "content": m.get("content") or ""}
        for m in merged.values()], ensure_ascii=False)
    verdict = mc.call("kb_laya_judge", {"query": QUERY, "documents": docs_payload,
                                        "criterion": "evidence", "threshold": 0.5,
                                        "max_evidence_chars": 40000}, timeout=900)
    v = json.loads(verdict) if isinstance(verdict, str) else verdict
    jev = v.get("jev") or {}
    doc_best: dict[str, float] = {}
    for s in v.get("survivors") or []:
        p = str(s.get("doc_path") or "")
        doc_best[p] = max(doc_best.get(p, 0.0), float(s.get("score") or 0))
    best = max(doc_best.values()) if doc_best else 0.0
    cut = best - 0.10
    kept = {p: sc for p, sc in doc_best.items() if sc >= cut}
    mark("S4", "done", real_engine=jev.get("real_engine"), status=jev.get("status"),
         criterion=jev.get("criterion"), scored=jev.get("scored_count"),
         survivors=len(v.get("survivors") or []), global_best=round(best, 4),
         cut=round(cut, 4), kept_docs=len(kept),
         kept=[f"{p.split('__')[-1][:40]}={round(sc,3)}" for p, sc in
               sorted(kept.items(), key=lambda x: -x[1])])
finally:
    mc.close()

# ── S5 完整读取检查(截断的分页补读) ──
mark("S5", "start")
trunc = [m for m in merged.values() if m["lane"] != "vector"
         and m.get("truncated") and m["doc_path"] in kept]
mark("S5", "done", truncated_needing_pagination=len(trunc))

# ── 落盘观察记录 ──
out = {"query": QUERY, "phases": log,
       "merge": {"from_both": from_both, "from_vector_only": from_vec,
                 "from_catalog_only": from_cat},
       "judge": {"real_engine": v.get("real_engine"), "criterion": v.get("criterion"),
                 "scored": v.get("scored_count"), "survivors": len(v.get("survivors") or []),
                 "global_best": round(best, 4), "cut": round(cut, 4), "kept": len(kept)},
       "kept_docs": kept}
(HERE / "serial-observation.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
print("\nserial-observation.json saved")
