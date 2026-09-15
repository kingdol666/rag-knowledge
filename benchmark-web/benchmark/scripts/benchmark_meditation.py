#!/usr/bin/env python3
"""模块 C — 冥想(经验自动总结)评测: 覆盖率 / 经验质量分 / 检索消融.

链路(全部真实系统):
  触发:  POST /api/v1/meditation/run {kb_id, trigger, harness}  → harness(omp) Agent
         从信号(聊天库 harvest / 文档综合)自动总结经验写入 KB 经验区
  覆盖:  meditation runs 成功率 + 每目标 KB 产出经验数 + 信号→经验转化
  质量:  结构完整性(title/scenario/category) + 检索接地(经验正文可在其 KB 中
         向量检索命中, 阈值 0.45) + 应用/评审链路可用
  消融:  对经验源问题: (a)经验层 /experience/global-search (QDCVR+内容验证)
         vs (b)纯向量 /search/vector — 经验层是否把"蒸馏后的答案"提前命中
         ΔReach = exp_hit@3 − kb_hit@3(同一问题)
用法:
  python benchmark_meditation.py --kbs KB-CrossLang-EN,KB-CrossLang-ZH --harness omp
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from bench_http import post_json, get_json, validated_url  # noqa: E402

RESULTS_DIR = SCRIPTS_DIR.parent / "results" / "benchmark"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

BACKEND = os.environ.get("RAG_BENCH_URL", "http://localhost:8771").rstrip("/")
WEB = os.environ.get("RAG_BENCH_WEB_URL", "http://localhost:6790").rstrip("/")
TOKEN = os.environ.get("RAG_BENCH_TOKEN", "")


def bpost(path: str, payload: dict, timeout: int = 900) -> dict:
    return post_json(validated_url(BACKEND), path, payload, token=TOKEN, timeout=timeout)


def norm(t: str) -> str:
    return str(t).replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".md")


def run_meditation(kb_id: str, harness: str) -> dict:
    return bpost("/api/v1/meditation/run",
                 {"kb_id": kb_id, "trigger": "benchmark", "harness": harness})


def list_experiences(kb_id: str) -> list[dict]:
    d = get_json(validated_url(BACKEND),
                 f"/api/v1/experience/{kb_id}", token=TOKEN, timeout=120)
    return d.get("experiences") or d.get("data") or d.get("items") or []


def quality(exp: dict, kb_id: str) -> dict:
    content = " ".join(str(exp.get(k) or "") for k in
                       ("title", "scenario", "content", "symptom", "resolution"))
    structural = sum(bool(exp.get(k)) for k in
                     ("title", "scenario", "category")) / 3.0
    grounded = None
    top1 = None
    if len(content) > 40:
        probe = re.sub(r"\s+", " ", content)[:300]
        try:
            r = bpost("/api/v1/search/vector",
                      {"query": probe, "kb_id": kb_id, "top_k": 1}, timeout=120)
            hits = r.get("results") or []
            top1 = float(hits[0]["score"]) if hits else 0.0
            grounded = top1 >= 0.45
        except Exception:
            pass
    return {"exp_id": exp.get("exp_id") or exp.get("id"),
            "structural": round(structural, 3),
            "grounded": grounded, "top1_score": top1,
            "content_len": len(content)}


def ablation(exp: dict) -> dict:
    """经验源场景问题: 经验层命中 vs 纯 KB 向量命中."""
    q = " ".join(str(exp.get(k) or "") for k in ("title", "scenario")).strip()
    if len(q) < 12:
        return {"skipped": True}
    out = {"skipped": False}
    try:
        r = bpost("/api/v1/experience/global-search",
                  {"query": q, "top_k": 3, "verify_content": True}, timeout=180)
        items = (r.get("experiences") or r.get("results") or r.get("items") or [])
        out["exp_hit3"] = int(bool(items))
    except Exception:
        out["exp_hit3"] = 0
    try:
        kb_id = exp.get("kb_id") or ""
        r = bpost("/api/v1/search/vector",
                  {"query": q, "kb_id": kb_id, "top_k": 3}, timeout=120)
        out["kb_top1_score"] = round(float((r.get("results") or [{}, ])[0]
                                           .get("score", 0)), 4)
    except Exception:
        out["kb_top1_score"] = None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kbs", default="KB-CrossLang-EN,KB-CrossLang-ZH")
    ap.add_argument("--harness", default="omp")
    ap.add_argument("--round", type=int, default=1)
    args = ap.parse_args()
    if not TOKEN:
        print("需要 RAG_BENCH_TOKEN", file=sys.stderr)
        return 2

    kbs = args.kbs.split(",")
    report: dict = {"meta": {
        "generated": datetime.now(timezone.utc).isoformat(),
        "harness": args.harness,
        "trigger": "POST /api/v1/meditation/run (真实 harness Agent)",
    }, "per_kb": {}}

    for kb_id in kbs:
        print(f"== {kb_id} ==", flush=True)
        run = {}
        try:
            run = run_meditation(kb_id, args.harness)
        except Exception as e:  # noqa: BLE001
            run = {"success": False, "error": str(e)[:200]}
        time.sleep(5)
        try:
            exps = list_experiences(kb_id)
        except Exception:
            exps = []

        quals = [quality(e, kb_id) for e in exps]
        grounded_vals = [q["grounded"] for q in quals if q["grounded"] is not None]
        ablations = [ablation(e) for e in exps[:10]]
        abl = [a for a in ablations if not a.get("skipped")]

        per_kb = {
            "run_success": bool(run.get("success", False)),
            "run_error": str(run.get("error", ""))[:120] or None,
            "n_experiences": len(exps),
            "coverage": 1 if exps else 0,
            "structural_mean": round(statistics.mean(q["structural"] for q in quals), 4)
            if quals else None,
            "grounded_ratio": round(statistics.mean(grounded_vals), 4)
            if grounded_vals else None,
            "ablation_exp_hit3": round(statistics.mean(
                a["exp_hit3"] for a in abl), 4) if abl else None,
            "ablation_kb_top1_mean": round(statistics.mean(
                a["kb_top1_score"] for a in abl if a.get("kb_top1_score") is not None), 4)
            if any(a.get("kb_top1_score") is not None for a in abl) else None,
        }
        report["per_kb"][kb_id] = per_kb
        report.setdefault("samples", {})[kb_id] = {
            "qualities": quals[:10], "ablations": abl[:10],
            "run": {k: run.get(k) for k in ("success", "error", "report")
                    if k in run},
        }
        print(f"  {json.dumps(per_kb, ensure_ascii=False)}", flush=True)

    covered = sum(1 for v in report["per_kb"].values() if v["coverage"])
    report["summary"] = {
        "n_kbs": len(kbs),
        "run_success_rate": round(sum(1 for v in report["per_kb"].values()
                                      if v["run_success"]) / len(kbs), 4),
        "kb_coverage": round(covered / len(kbs), 4),
        "total_experiences": sum(v["n_experiences"] for v in
                                 report["per_kb"].values()),
        "structural_mean": next((round(statistics.mean(
            v["structural_mean"] for v in report["per_kb"].values()
            if v["structural_mean"] is not None), 4)), None),
        "grounded_ratio_mean": next((round(statistics.mean(
            v["grounded_ratio"] for v in report["per_kb"].values()
            if v["grounded_ratio"] is not None), 4)), None),
        "ablation_exp_hit3_mean": next((round(statistics.mean(
            v["ablation_exp_hit3"] for v in report["per_kb"].values()
            if v["ablation_exp_hit3"] is not None), 4)), None),
    }
    out = RESULTS_DIR / f"benchmark_meditation_en_r{args.round}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (RESULTS_DIR / f"benchmark_meditation_en_{ts}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print("summary:", json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
