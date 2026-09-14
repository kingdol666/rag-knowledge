#!/usr/bin/env python3
"""98 · 全量复现对比 — 归档 vs 新跑（指标层严格比对，LLM 通道单独标注）.

用法: python scripts/98_compare_archive.py <archive_dir> <new_results_dir>

分类:
  deterministic  指标必须逐位一致（module A/B、ablation、hotpot、oracle、stratified）
  llm            LLM 通道（module C 冥想、经验套件、judge）→ 报告差异并标注为已知方差
忽略: 计时字段、时间戳、run_id、git/config 指纹
输出: stdout 表格 + <new>/repro_compare_full.json
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

TIMING = re.compile(r"(latency|generated|timestamp|run_id|search_s|verify_s|elapsed|duration)", re.I)
LLM_FAMILY = re.compile(r"(module_c_|experience_suite|judge_agreement|e4_baselines)", re.I)


def flat(o, pre=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("env", "meta"):
                continue
            yield from flat(v, f"{pre}{k}.")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flat(v, f"{pre}{i}.")
    else:
        yield pre.rstrip("."), o


def cmp_pair(a: Path, b: Path):
    da = dict(flat(json.loads(a.read_text(encoding="utf-8"))))
    db = dict(flat(json.loads(b.read_text(encoding="utf-8"))))
    diffs = []
    for k in sorted(set(da) | set(db)):
        if TIMING.search(k):
            continue
        x, y = da.get(k, "<absent>"), db.get(k, "<absent>")
        if x != y:
            diffs.append((k, x, y))
    return diffs


def main() -> int:
    arch = Path(sys.argv[1])
    new = Path(sys.argv[2])
    # 结果家族: 根目录 module_*.json + run-*/ 下的各实验 JSON
    pairs: list[tuple[str, Path, Path]] = []
    for f in sorted(arch.glob("module_*.json")):
        cand = new / f.name
        if cand.exists():
            pairs.append((f.name, f, cand))
    for fam in ("ablation_scifact_*.json", "hotpot_main_*.json", "routing_oracle_*.json",
                "stratified_adjudication.json", "experience_suite_*.json",
                "judge_agreement_*.json", "e4_baselines_fixed.json"):
        # 每个家族取"最新"一份配对（归档里可能同时存在被修复前的旧运行）
        afiles = list(arch.glob(f"run-*/{fam}"))
        bfiles = [p for p in new.glob(f"run-*/{fam}")
                  if not any("archive" in part.lower() for part in p.parts)]
        # 排除更早的 run 目录: 只保留 mtime 最新的
        if afiles and bfiles:
            a = max(afiles, key=lambda p: p.stat().st_mtime)
            b = max(bfiles, key=lambda p: p.stat().st_mtime)
            pairs.append((a.name, a, b))

    results = []
    n_fail = 0
    print(f"{'file':42s} {'class':6s} {'verdict':10s} diffs")
    print("-" * 78)
    for name, a, b in pairs:
        cls = "llm" if LLM_FAMILY.search(name) else "det"
        diffs = cmp_pair(a, b)
        if cls == "det":
            verdict = "IDENTICAL" if not diffs else f"DIFF({len(diffs)})"
            if diffs:
                n_fail += 1
        else:
            verdict = "VARIANCE" if diffs else "IDENTICAL"
        print(f"{name:42s} {cls:6s} {verdict:10s} {len(diffs)}")
        for k, x, y in diffs[:4]:
            print(f"      {k}: {x} -> {y}")
        results.append({"file": name, "class": cls, "verdict": verdict,
                        "n_diffs": len(diffs), "diffs": diffs[:40]})

    out = new / "repro_compare_full.json"
    out.write_text(json.dumps({"archive": str(arch), "new": str(new),
                               "deterministic_failures": n_fail,
                               "files": results}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("-" * 78)
    print(f"确定性家族: {'ALL IDENTICAL' if n_fail == 0 else str(n_fail) + ' FILE(S) DIFFER'} "
          f"(LLM 通道差异按已知方差报告)")
    print(f"-> {out}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
