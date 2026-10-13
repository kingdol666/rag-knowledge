#!/usr/bin/env python3
r"""QDCVR 论文终测总流水线 —— 一条命令跑完全部阶段并产出可写入论文的证据与可视化报告。

阶段（每阶段独立、可单独跑、fail-closed）
    S0 平台与语料体检   scripts/150_final_pipeline.py --check
                        （Gate0 平台/令牌 · Gate1 kb-mcp 工具面 · Gate2 语料+密索引探针 · Gate3 题集）
    S1 语料与密索引     scripts/106_exp_corpus_r2.py（必要时重建 100 篇 / 4528 chunk 副本索引）
    S2 三轨真实执行     scripts/150_final_pipeline.py（a2/b/c × BQ01–BQ10，写 results/runs/run-<ts>-<commit>/）
                        ⚠ 默认不跑（约 30 分钟、约 $17），必须显式加 --live
    S3 采集 + 自检      scripts/161_final_evidence.py（判分复算 + 论文级闸门 + 论文宏工单）
    S4 可视化 HTML      scripts/162_paper_report_html.py（单文件离线 dashboard）
    S5 稳定性套件       review/stability-multiround-20261013/run_stability.py（三任务 × 三车道 × 多轮）

用法
    python scripts/160_run_paper_pipeline.py --check          # 只体检（1 分钟内）
    python scripts/160_run_paper_pipeline.py                  # 用现有 run 出报告（快）
    python scripts/160_run_paper_pipeline.py --live           # 真跑一轮并出报告（约 30 分钟）
    python scripts/160_run_paper_pipeline.py --live --stability   # 连稳定性套件一起跑
    python scripts/160_run_paper_pipeline.py --stages S3,S4   # 只跑指定阶段
    python scripts/160_run_paper_pipeline.py --baselines bm25,vector,rrf

产物
    results/runs/run-<ts>-<commit>/     原始单元（每题每轨一个 JSON，含完整答案与工具轨迹）
    results/paper_report.json           采集+自检结果（报告的唯一数据源）
    results/PAPER-REPORT.html           单文件可视化报告（可直接附给评审）
    results/final-pipeline.json         本次流水线各阶段状态
退出码：0 = 全部执行的阶段通过；1 = 有阶段失败（报告仍然生成，失败项写在 verdict 里）
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
RESULTS = SUITE / "results"
PY = sys.executable or "python"
ALL_STAGES = ["S0", "S1", "S2", "S3", "S4", "S5"]


def run(cmd: list[str], cwd: Path, label: str, tail: int = 14) -> tuple[int, str]:
    print(f"\n$ {' '.join(cmd)}   ({label})", flush=True)
    t0 = time.time()
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    lines = [l for l in out.splitlines() if l.strip()]
    for l in lines[-tail:]:
        print("  " + l, flush=True)
    print(f"  → exit {p.returncode} · {time.time() - t0:.1f}s", flush=True)
    return p.returncode, out


def newest_run(min_cells: int = 10) -> Path | None:
    """最新「单元够多」的 run —— 避免选中还在跑、几乎没写盘的新目录。"""
    cands = [p for p in (RESULTS / "runs").glob("run-*") if p.is_dir()]
    if not cands:
        return None
    full = [p for p in cands if len(list(p.glob("track_*.json"))) >= min_cells]
    return max(full or cands, key=lambda p: p.stat().st_mtime)


def main() -> int:
    ap = argparse.ArgumentParser(description="QDCVR 论文终测总流水线")
    ap.add_argument("--stages", default="", help=f"逗号分隔子集，默认 {' '.join(ALL_STAGES)}")
    ap.add_argument("--live", action="store_true", help="真的执行三轨实验（S2，约 30 分钟 / ~$17）")
    ap.add_argument("--stability", action="store_true", help="跑稳定性套件（S5，约 30 分钟）")
    ap.add_argument("--check", action="store_true", help="只做 S0 体检")
    ap.add_argument("--rebuild-corpus", action="store_true",
                    help="S1 真的重建密索引（默认只做只读盘点）")
    ap.add_argument("--run", default="", help="指定 run 目录（S2 复用/断点续跑，S3 判分对象）")
    ap.add_argument("--questions", default="data/papers/qa_questions.json")
    ap.add_argument("--tracks", default="a2,b,c")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--baselines", default="", help="S3 附带基线对照：bm25,vector,rrf")
    args = ap.parse_args()

    stages = [s.strip().upper() for s in args.stages.split(",") if s.strip()] or list(ALL_STAGES)
    if args.check:
        stages = ["S0"]
    if not args.live and "S2" in stages:
        stages = [s for s in stages if s != "S2"]
        print("[info] 未加 --live → 跳过 S2（三轨真实执行）；用现有 run 出报告。"
              "要跑新的一轮请加 --live")
    if not args.stability and "S5" in stages:
        stages = [s for s in stages if s != "S5"]
    bad = [s for s in stages if s not in ALL_STAGES]
    if bad:
        print(f"[fail] 未知阶段 {bad}；可选 {ALL_STAGES}")
        return 2

    t0 = time.time()
    report: dict = {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "stages": [], "live": bool(args.live)}
    run_dir = Path(args.run) if args.run else None
    failed: list[str] = []

    def record(stage: str, ok: bool, detail: str, extra: dict | None = None) -> None:
        report["stages"].append({"stage": stage, "ok": ok, "detail": detail,
                                 **(extra or {})})
        if not ok:
            failed.append(stage)

    for s in stages:
        if s == "S0":
            rc, _ = run([PY, "scripts/150_final_pipeline.py", "--check"], SUITE, "S0 平台/语料体检")
            record("S0", rc == 0, "Gate0-3（平台·工具面·语料·题集）")
            if rc != 0:
                print("[stop] S0 未通过：先修 Gate，再跑后续阶段（报告仍会生成）")

        elif s == "S1":
            rc1, _ = run([PY, "scripts/106_exp_corpus_r2.py", "--dry-run"], SUITE,
                         "S1 语料只读盘点", tail=12)
            ok = rc1 == 0
            detail = "只读盘点"
            if args.rebuild_corpus:
                rc2, _ = run([PY, "scripts/106_exp_corpus_r2.py", "--reuse-export"], SUITE,
                             "S1 重建密索引（约 13 分钟）", tail=8)
                ok = ok and rc2 == 0
                detail += " + 重建密索引"
            elif rc1 != 0:
                # 106 的退出码会因历史遗留的 smoke 探针（探针论文不在 100 篇语料里）而
                # 非 0；以 151 的真实召回探针为准。
                rc1b, _ = run([PY, "scripts/151_smoke_probe.py"], SUITE, "S1 密索引召回实测",
                              tail=12)
                ok = rc1b == 0
                detail += "（106 dry-run 非 0，已用 151 实测复核）"
            record("S1", ok, detail)

        elif s == "S2":
            cmd = [PY, "scripts/150_final_pipeline.py",
                   "--questions", args.questions, "--tracks", args.tracks,
                   "--limit", str(args.limit), "--max-turns", str(args.max_turns)]
            if args.run:
                cmd += ["--run", args.run]
            rc, _ = run(cmd, SUITE, "S2 三轨真实执行（30 单元）", tail=24)
            record("S2", rc == 0, f"{args.tracks} × {args.limit} 题")
            run_dir = run_dir or newest_run()

        elif s == "S3":
            cmd = [PY, "scripts/161_final_evidence.py"]
            if run_dir:
                cmd += ["--run", str(run_dir)]
            if args.baselines:
                cmd += ["--baselines", args.baselines]
            rc, _ = run(cmd, SUITE, "S3 采集 + 自检 + 论文级闸门", tail=30)
            record("S3", rc == 0, "paper_report.json（判分复算 + 论文宏工单）")

        elif s == "S4":
            rc, _ = run([PY, "scripts/162_paper_report_html.py"], SUITE, "S4 可视化 HTML")
            html_path = RESULTS / "PAPER-REPORT.html"
            record("S4", rc == 0 and html_path.exists(),
                   f"{html_path} ({html_path.stat().st_size} B)"
                   if html_path.exists() else "未生成")

        elif s == "S5":
            rc, _ = run([PY, str(REPO / "review" / "stability-multiround-20261013"
                                 / "run_stability.py"), "r1", "r2", "r3",
                         "--out", "review/stability-multiround-20261013/results"],
                        REPO, "S5 稳定性套件（27 单元）", tail=12)
            record("S5", rc == 0, "27 单元（3 任务 × 3 车道 × 3 轮）")

    report["elapsed_s"] = round(time.time() - t0, 1)
    report["failed_stages"] = failed
    report["verdict"] = "pass" if not failed else "fail"
    report["run_dir"] = str(run_dir) if run_dir else None
    report["report_html"] = str(RESULTS / "PAPER-REPORT.html")
    out = RESULTS / "final-pipeline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 66)
    for st in report["stages"]:
        print(f"  {'✓' if st['ok'] else '✗'} {st['stage']}  {st['detail']}")
    print(f"  verdict: {report['verdict']} · {report['elapsed_s']}s")
    print(f"  报告: {report['report_html']}")
    print(f"  状态: {out}")
    print("=" * 66)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
