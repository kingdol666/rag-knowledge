# -*- coding: utf-8 -*-
"""金标准评测跑分器 — 全部改动前的守门仪表（plan 阶段 0）。

用法（仓库根目录）：
  python benchmark-suite/golden/run_eval.py --label baseline     # 首次基线入账
  python benchmark-suite/golden/run_eval.py --label after_p1     # 阶段守门（对比 baseline）
  python benchmark-suite/golden/run_eval.py --label x --no-judge # 跳过判卷维度（快速）

通道：一律走 127.0.0.1:8000 常驻 kb-mcp（scripts/mcp_call.py），与 agent 同路径。
守门指标：
  1. gold 召回：跨库向量 top-10 内命中 gold_docs（后缀匹配，克隆库算命中）——不得低于 baseline -3pp
  2. 负例误报：negatives 跨库向量命中小于 baseline+2 篇/题（期望 0）
  3. 判卷门：gold 文档过 Laya 判卷的存活率（--no-judge 可跳）
  4. 经验检索：experience 类问题 search_smart 召回
  5. 延迟记录（不设门槛，趋势观察）
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = REPO / "backend" / ".venv" / "Scripts" / "python.exe"
MCP_CALL = REPO / "scripts" / "mcp_call.py"
GOLDEN = Path(__file__).resolve().parent
VECTOR_THRESHOLD = 0.35
JUDGE_SAMPLE = 8          # 判卷维度抽样的 gold 题数（控制时长）
JUDGE_BATCH = 6


def mcp(tool: str, payload: dict, timeout: float = 300.0) -> dict:
    t0 = time.perf_counter()
    r = subprocess.run(
        [str(PY), str(MCP_CALL), tool, json.dumps(payload, ensure_ascii=False), "--raw"],
        capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(REPO),
    )
    dt = time.perf_counter() - t0
    out = (r.stdout or "").strip()
    if not out:
        raise RuntimeError(f"mcp_call {tool} empty (rc={r.returncode}) {r.stderr[:200]}")
    return json.loads(out), dt


def norm(p: str) -> str:
    return (p or "").replace("\\", "/")


def hit_gold(doc_path: str, gold_docs: list) -> bool:
    p = norm(doc_path).lower()
    return any(p.endswith(norm(g).lower()) for g in gold_docs)


def eval_vector(q: dict) -> dict:
    data, dt = mcp("kb_search_vector", {
        "query": q["query"], "top_k": 10, "score_threshold": VECTOR_THRESHOLD,
        "balance_kbs": True, "slim": True,
    })
    results = data.get("results", []) if data.get("success") else []
    ranks = [i + 1 for i, r in enumerate(results) if hit_gold(r.get("doc_path", ""), q.get("gold_docs", []))]
    return {
        "id": q["id"], "latency_s": round(dt, 3), "hits": len(results),
        "gold_hit": bool(ranks), "best_rank": min(ranks) if ranks else None,
        "top_score": round(results[0]["score"], 4) if results else None,
    }


def eval_two_stage(q: dict) -> dict:
    data, dt = mcp("kb_search_two_stage", {
        "query": q["query"], "stage1_top_k": 20, "stage2_top_k": 5,
        "enable_graph_expansion": False, "slim": True,
    })
    results = (data.get("stage2") or {}).get("results", []) if data.get("success") else []
    ranks = [i + 1 for i, r in enumerate(results) if hit_gold(r.get("doc_path", ""), q.get("gold_docs", []))]
    return {"id": q["id"], "latency_s": round(dt, 3), "gold_hit": bool(ranks), "best_rank": min(ranks) if ranks else None}


def eval_experience(q: dict) -> dict | None:
    if q.get("type") != "experience":
        return None
    data, dt = mcp("experience_search_global", {"query": q["query"], "top_k": 5})
    exps = data.get("experiences", []) or data.get("results", []) if isinstance(data, dict) else []
    gold_stems = {norm(g).lower().removesuffix(".md") for g in q.get("gold_docs", [])}
    ranks = []
    for i, e in enumerate(exps):
        cand = {norm(str(e.get(k, ""))).lower() for k in ("path", "doc_path", "id", "title")}
        if any(any(c.endswith(g) or g in c for g in gold_stems) for c in cand if c):
            ranks.append(i + 1)
    return {"id": q["id"], "latency_s": round(dt, 3), "gold_hit": bool(ranks), "best_rank": min(ranks) if ranks else None}


def eval_judge(q: dict) -> dict | None:
    """判卷维度：把 gold 文档（跨库找第一篇）送 Laya，要求存活。抽样控制时长。"""
    # 先用向量定位 gold 文档的实际 (kb_id, doc_path)
    data, _ = mcp("kb_search_vector", {
        "query": q["query"], "top_k": 30, "score_threshold": 0.0, "slim": True,
    })
    results = data.get("results", []) if data.get("success") else []
    refs, seen = [], set()
    for r in results:
        dp = norm(r.get("doc_path", ""))
        if hit_gold(dp, q.get("gold_docs", [])) and dp not in seen:
            seen.add(dp)
            refs.append({"kb_id": r.get("kb_id"), "doc_path": dp})
        if len(refs) >= 2:
            break
    if not refs:
        return {"id": q["id"], "status": "no_gold_located"}
    data, dt = mcp("kb_laya_judge", {
        "query": q["query"], "criterion": "evidence", "threshold": 0.5,
        "documents": json.dumps(refs, ensure_ascii=False),
    })
    surv = {norm(s.get("doc_path", "")) for s in data.get("survivors", [])}
    survived = any(hit_gold(s, q.get("gold_docs", [])) for s in surv)
    return {"id": q["id"], "status": data.get("status"), "real_engine": data.get("real_engine"),
            "survived": survived, "latency_s": round(dt, 2)}


def eval_hybrid(q: dict) -> dict | None:
    if q.get("type") == "negative":
        return None
    data, dt = mcp("kb_hybrid_search", {"query": q["query"]})
    if not data.get("success"):
        return {"id": q["id"], "error": str(data)[:120]}
    kept = data.get("cut", {}).get("kept", [])
    ranks = [i + 1 for i, k in enumerate(kept) if hit_gold(k.get("doc_path", ""), q.get("gold_docs", []))]
    return {"id": q["id"], "latency_s": round(dt, 2), "gold_hit": bool(ranks),
            "best_rank": min(ranks) if ranks else None, "kept_n": len(kept),
            "pre_filtered": (data.get("merge") or {}).get("pre_filtered")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--set", dest="set_file", default=str(GOLDEN / "golden_set.json"))
    args = ap.parse_args()

    questions = json.loads(Path(args.set_file).read_text(encoding="utf-8"))["questions"]
    gold_qs = [q for q in questions if q.get("gold_docs")]
    neg_qs = [q for q in questions if q.get("type") == "negative"]
    exp_qs = [q for q in questions if q.get("type") == "experience"]
    judge_qs = gold_qs[:JUDGE_SAMPLE] if not args.no_judge else []

    print(f"[golden] {len(questions)} 题（gold {len(gold_qs)} / neg {len(neg_qs)} / exp {len(exp_qs)}），judge 抽样 {len(judge_qs)}")

    rows = {"vector": [], "two_stage": [], "experience": [], "judge": [], "negative": [], "hybrid": []}
    for q in questions:
        r = eval_vector(q)
        rows["vector"].append(r)
        tag = "NEG" if q.get("type") == "negative" else ("ok " if r["gold_hit"] else "MISS")
        print(f"  vec {q['id']} {tag} rank={r['best_rank']} top={r['top_score']} {r['latency_s']}s")
        rows["two_stage"].append(eval_two_stage(q))
        h = eval_hybrid(q)
        if h:
            rows["hybrid"].append(h)
            print(f"  hyb {q['id']} {'ok ' if h.get('gold_hit') else 'MISS'} kept={h.get('kept_n')} {h.get('latency_s')}s")
        e = eval_experience(q)
        if e:
            rows["experience"].append(e)
            print(f"  exp {q['id']} {'ok ' if e['gold_hit'] else 'MISS'}")
    for q in neg_qs:
        vr = next(r for r in rows["vector"] if r["id"] == q["id"])
        rows["negative"].append({"id": q["id"], "hits": vr["hits"], "top_score": vr["top_score"]})
    for q in judge_qs:
        j = eval_judge(q)
        rows["judge"].append(j)
        print(f"  judge {q['id']} survived={j.get('survived')} ({j.get('latency_s')}s)")

    # 汇总
    vec_gold = [r for r in rows["vector"] if r["id"] in {q["id"] for q in gold_qs}]
    recall10 = sum(1 for r in vec_gold if r["gold_hit"]) / max(len(vec_gold), 1)
    mrr = sum(1.0 / r["best_rank"] for r in vec_gold if r["best_rank"]) / max(len(vec_gold), 1)
    neg_fp = sum(r["hits"] for r in rows["negative"]) / max(len(rows["negative"]), 1)
    exp_recall = (sum(1 for r in rows["experience"] if r["gold_hit"]) / max(len(rows["experience"]), 1)) if rows["experience"] else None
    judge_surv = (sum(1 for r in rows["judge"] if r.get("survived")) / max(len(rows["judge"]), 1)) if rows["judge"] else None
    p50 = sorted(r["latency_s"] for r in rows["vector"])[len(rows["vector"]) // 2]
    hyb = [r for r in rows["hybrid"] if "error" not in r]
    hyb_recall = (sum(1 for r in hyb if r["gold_hit"]) / max(len(hyb), 1)) if hyb else None
    hyb_p50 = sorted(r["latency_s"] for r in hyb)[len(hyb) // 2] if hyb else None

    summary = {
        "label": args.label, "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "recall@10": round(recall10, 4), "mrr": round(mrr, 4),
        "negative_fp_per_q": round(neg_fp, 2),
        "experience_recall": round(exp_recall, 4) if exp_recall is not None else None,
        "judge_survival": round(judge_surv, 4) if judge_surv is not None else None,
        "vector_p50_s": round(p50, 3),
        "hybrid_recall": round(hyb_recall, 4) if hyb_recall is not None else None,
        "hybrid_p50_s": round(hyb_p50, 2) if hyb_p50 is not None else None,
    }
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    out = GOLDEN / "results" / f"{args.label}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {out}")

    base_file = GOLDEN / "baseline.json"
    if args.label == "baseline":
        base_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[baseline 入账] {base_file}")
    elif base_file.exists():
        base = json.loads(base_file.read_text(encoding="utf-8"))
        gates = {
            "recall@10 不低于 baseline-3pp": summary["recall@10"] >= base["recall@10"] - 0.03,
            "负例误报不高于 baseline+2": summary["negative_fp_per_q"] <= base["negative_fp_per_q"] + 2,
        }
        if summary.get("judge_survival") is not None and base.get("judge_survival") is not None:
            gates["判卷存活率不低于 baseline-10pp"] = summary["judge_survival"] >= base["judge_survival"] - 0.10
        if summary.get("hybrid_recall") is not None and base.get("hybrid_recall") is not None:
            gates["hybrid kept 召回不低于 baseline-5pp"] = summary["hybrid_recall"] >= base["hybrid_recall"] - 0.05
        print("=== GATES ===")
        for k, ok in gates.items():
            print(f"  {'PASS' if ok else 'FAIL'}  {k}")
        return 0 if all(gates.values()) else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
