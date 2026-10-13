#!/usr/bin/env python3
"""Extended retrieval matrix — PIPELINE retmodes track scaled to 10 questions.
Questions: built-in q1/q2 + 8 Quick10 gold questions (QK01-QK08, each gold doc
verified in BOTH corpus_md and the live library before injection).
Methods: mode_A / mode_B / mode_C (scripted, no LLM answer) + bm25 / vector / rrf.
Run dir artifacts: arm_*.json, retmatrix.json, RETRIEVAL-COMPARE-10Q.md."""
import json, sys, time
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "benchmark-suite"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "experiments"))
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))

import runner as _runner  # noqa: E402
from experiments import retrieval_modes as rm  # noqa: E402
import baselines as bl  # noqa: E402

GROUND_TRUTH = """# Ground truth (verified 2026-10-13 before the run)

Every injected question's gold document was verified to exist in BOTH corpora:
- corpus_md 100-paper set (bm25/rrf substrate): `ls data/corpus_md | grep <id>` = 1
- live platform library (mode A/B/C substrate): kb_search metadata hit with KB attribution

| qid | gold arXiv id | live KB | question source |
|---|---|---|---|
| qk_QK01 | 1706.03762 | 计算机与人工智能 | Quick10 QK01 provenance |
| qk_QK02 | 1602.01876 | 生命科学与医学 | Quick10 QK02 cross-KB genomics |
| qk_QK03 | 1606.00335 | 工程与能源 | Quick10 QK03 materials/mechanism |
| qk_QK04 | 2209.15032 | 计算机与人工智能 | Quick10 QK04 numeric (94%) |
| qk_QK05 | 2508.05896 | 生命科学与医学 | Quick10 QK05 numeric (7-10%) |
| qk_QK06 | 1503.07557 | 自然科学与地球科学 | Quick10 QK06 chunk-window |
| qk_QK07 | 2608.05850 | 计算机与人工智能 | Quick10 QK07 distractor (multiple LM papers) |
| qk_QK08 | 2409.13934 | 自然科学与地球科学 | Quick10 QK08 cross-KB GAN/climate |

QK09 (unanswerable) / QK10 (out-of-corpus) are excluded here: the retrieval-layer
gate is gold-recall; their honesty behavior is covered by the chatmodes refusal
battery (cm5-cm9) at the system layer.
"""


def main() -> int:
    rm.ensure_laya_interpreter()
    laya_py = rm.resolve_laya_python()

    quick = json.loads((REPO / "benchmark-suite/data/papers/qa_quick10.json")
                       .read_text(encoding="utf-8"))["questions"]
    KB = {"1706.03762": "计算机与人工智能", "1602.01876": "生命科学与医学",
          "1606.00335": "工程与能源", "2209.15032": "计算机与人工智能",
          "2508.05896": "生命科学与医学", "1503.07557": "自然科学与地球科学",
          "2608.05850": "计算机与人工智能", "2409.13934": "自然科学与地球科学"}
    injected = []
    for q in quick:
        golds = q.get("gold_docs") or []
        if not golds:
            continue  # QK09/QK10: no gold (unanswerable/out-of-corpus) — system layer covers them
        gid = golds[0]
        if gid not in KB:
            continue
        qid = f"qk_{q['qid']}"
        rm.QUESTIONS[qid] = {"qid": qid, "lang": "en", "text": q["question"],
                             "shelf_b": [KB[gid]], "gold_substr": gid,
                             "gold_id": gid, "gold_name": q.get("paper", "")}
        injected.append(qid)
    qids = list(rm.QUESTIONS)
    out_dir = _runner.new_run_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "GROUND-TRUTH.md").write_text(GROUND_TRUTH, encoding="utf-8")
    print(f"[ret10q] run={out_dir.name} · questions={qids}", flush=True)

    rows = []
    for m in ("A", "B", "C"):
        for qid in qids:
            q = rm.QUESTIONS[qid]
            print(f"[ret10q] mode {m} × {qid} …", flush=True)
            t0 = time.time()
            try:
                arm = rm.RUNNERS[m](q, out_dir / f"arm_{m}-{qid}.json")
            except Exception as e:  # noqa: BLE001
                arm = {"mode": m, "ok": False, "n_result_docs": 0, "gold_hit": False,
                       "kept_doc_paths": [], "error": f"{type(e).__name__}: {str(e)[:200]}"}
            gate = rm.verify_gate(arm, q)
            rows.append({"method": f"mode_{m}", "qid": qid, "question": q["text"],
                         "latency_s": arm.get("wall_s"), "retrieval_gold": arm.get("gold_hit"),
                         "n_docs": arm.get("n_result_docs"),
                         "ranked": arm.get("kept_doc_paths") or [],
                         "evidence_chars": arm.get("evidence_chars", 0),
                         "real_engine": arm.get("real_engine"),
                         "gate_passed": gate["passed"], "via": "retrieval-mode",
                         "wall_overhead_s": round(time.time() - t0, 1),
                         **({"error": arm["error"]} if arm.get("error") else {})})
            print(f"[ret10q]   → {arm.get('wall_s')}s gold={arm.get('gold_hit')} "
                  f"docs={arm.get('n_result_docs')}", flush=True)
            if m == "B":
                try:
                    import jev_filter as _jf
                    _jf.release_laya()
                except Exception:
                    pass

    ret_baselines = ["bm25", "vector", "rrf"]
    bm25 = bl.BM25(bl.load_docs())
    for b in ret_baselines:
        for qid in qids:
            q = rm.QUESTIONS[qid]
            print(f"[ret10q] baseline {b} × {qid} …", flush=True)
            try:
                r = bl.run_method(b, q["text"], qid, bm25=bm25, retrieval_only=True)
                blob = " ".join(str(p) for p in (r.get("ranked") or [])).lower()
                gold_src = (q["gold_substr"] in blob) or (q.get("gold_id", "") in blob)
                rows.append({"method": b, "qid": qid, "question": q["text"],
                             "latency_s": r.get("latency_s"), "retrieval_gold": gold_src,
                             "n_docs": len(r.get("ranked") or []),
                             "ranked": r.get("ranked") or [],
                             "evidence_chars": r.get("evidence_chars", 0),
                             "real_engine": None, "gate_passed": None,
                             "via": "baseline-retrieval-only"})
            except Exception as e:  # noqa: BLE001
                rows.append({"method": b, "qid": qid, "error": str(e)[:200]})
                print(f"[ret10q]   → ERROR {str(e)[:120]}", flush=True)

    (out_dir / "retmatrix.json").write_text(
        json.dumps({"questions": qids, "rows": rows}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # extended report: per-method per-question gold matrix + averages
    methods = [f"mode_{m}" for m in ("A", "B", "C")] + ret_baselines
    L = ["# 检索任务对照矩阵（三模式 + baseline × 10 题, 纯检索无 LLM 回答）", "",
         f"- Run: `{out_dir.name}` · 生成: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
         "- 题: 内置 q1/q2 + Quick10 QK01-QK08（金标双库预验证, 见 GROUND-TRUTH.md）",
         "- 语料: 模式=真库; bm25/rrf=corpus_md 100 篇; vector=平台跨库", "",
         "| 方法 | " + " | ".join(qids) + " | gold率 | 延迟均值s |",
         "|---|" + "---:|" * (len(qids) + 2)]
    for meth in methods:
        rs = {r["qid"]: r for r in rows if r.get("method") == meth}
        if not rs:
            continue
        cells, golds, lats = [], 0, []
        for qid in qids:
            r = rs.get(qid)
            if not r:
                cells.append("—")
                continue
            hit = bool(r.get("retrieval_gold"))
            golds += hit
            lat = r.get("latency_s")
            if isinstance(lat, (int, float)):
                lats.append(lat)
            cells.append(("✅" if hit else "❌") + (f" {lat:.0f}s" if isinstance(lat, (int, float)) else ""))
        rate = f"{golds}/{len(qids)}"
        avg = f"{sum(lats)/len(lats):.1f}" if lats else "—"
        L.append(f"| {meth} | " + " | ".join(cells) + f" | {rate} | {avg} |")
    L += ["", "> 模式臂经硬验证门（real_engine/金标/延迟）; baseline 臂 retrieval_only 零 token。", ""]
    (out_dir / "RETRIEVAL-COMPARE-10Q.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[ret10q] 报告 → {out_dir / 'RETRIEVAL-COMPARE-10Q.md'}", flush=True)

    n_pass = sum(1 for r in rows if r.get("method", "").startswith("mode_") and r.get("gate_passed"))
    n_mode = sum(1 for r in rows if r.get("method", "").startswith("mode_"))
    print(f"[ret10q] mode gates {n_pass}/{n_mode}", flush=True)
    for meth in methods:
        rs = [r for r in rows if r.get("method") == meth]
        golds = sum(1 for r in rs if r.get("retrieval_gold"))
        print(f"  {meth}: gold {golds}/{len(rs)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
