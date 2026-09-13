#!/usr/bin/env python3
"""复现对比 — 逐项比较两次运行的 benchmark 结果.

用法:
  python scripts/compare_runs.py <baseline_dir> <candidate_dir>

容忍度（对齐 TEST-PLAN §7）:
  - 延迟字段（含 latency）           → 忽略
  - 模块 C 的 LLM 评分（judge*）     → 容忍 ±1.5
  - 其余数值字段                     → 逐位一致（浮点按 1e-9 容差）
退出码: 0 = 全部在容忍度内; 1 = 存在超差项。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKIP_KEY = ("latency", "generated", "timestamp")
LLM_TOL = 1.5
FLOAT_EPS = 1e-9


def is_skipped(path: str) -> bool:
    """计时/时间戳字段不参与复现判定."""
    p = path.lower()
    if any(s in p for s in SKIP_KEY):
        return True
    tail = p.rsplit(".", 1)[-1]
    return tail.endswith("_s")  # search_s / verify_s 等秒级计时


def section_of(path: str) -> str:
    """把字段归入 aggregate(汇总) 或 detail(逐查询明细) 或 other."""
    p = path
    if p.startswith("summary.") or p.startswith("meta.") or p.startswith("per_kb."):
        return "aggregate"
    if p.startswith("rows.") or p.startswith("samples."):
        return "detail"
    return "other"


def is_llm_score(path: str) -> bool:
    p = path.lower()
    return "judge" in p or "score" in p


def flat(obj, prefix=""):
    """把嵌套 dict/list 展平为 {dotted_path: leaf_value}."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flat(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flat(v, f"{prefix}{i}.")
    else:
        yield prefix.rstrip("."), obj


def cmp_leaf(path: str, a, b) -> tuple[str, str]:
    """返回 (verdict, detail). verdict ∈ {same, tolerant, diff, skip}."""
    if is_skipped(path):
        return "skip", f"baseline={a} candidate={b}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        if abs(a - b) <= FLOAT_EPS:
            return "same", f"{a}"
        if is_llm_score(path) and abs(a - b) <= LLM_TOL:
            return "tolerant", f"{a} → {b} (Δ{abs(a-b):.3f})"
        return "diff", f"{a} → {b} (Δ{abs(a-b):.4f})"
    if a == b:
        return "same", str(a)
    return "diff", f"{a!r} → {b!r}"


def compare_file(rel: str, base: Path, cand: Path) -> dict:
    fa, fb = base / rel, cand / rel
    if not fa.exists():
        return {"file": rel, "status": "MISSING_BASELINE"}
    if not fb.exists():
        return {"file": rel, "status": "MISSING_CANDIDATE"}
    try:
        a, b = json.loads(fa.read_text(encoding="utf-8")), json.loads(fb.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"file": rel, "status": f"PARSE_ERROR {e}"}
    da, db = dict(flat(a)), dict(flat(b))
    rows, counts = [], {"same": 0, "tolerant": 0, "diff": 0, "skip": 0}
    sec_diff = {"aggregate": 0, "detail": 0, "other": 0}
    # 只比较双方都有的叶子 + 缺失项
    for k in sorted(set(da) | set(db)):
        if k not in da or k not in db:
            counts["diff"] += 1
            sec_diff[section_of(k)] += 1
            rows.append({"path": k, "verdict": "diff", "section": section_of(k),
                         "detail": f"missing: {'baseline' if k not in da else 'candidate'}"})
            continue
        v, d = cmp_leaf(k, da[k], db[k])
        counts[v] += 1
        if v in ("diff", "tolerant"):
            sec_diff[section_of(k)] += 1
            rows.append({"path": k, "verdict": v, "section": section_of(k),
                         "detail": d})
    if counts["diff"] == 0:
        status = "PASS"
    elif sec_diff["aggregate"] == 0 and sec_diff["other"] == 0:
        status = "PASS_AGG"          # 汇总层一致，仅逐查询明细有差异
    else:
        status = "FAIL"
    return {"file": rel, "status": status, "counts": counts,
            "sections": sec_diff, "diffs": rows}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    base, cand = Path(sys.argv[1]), Path(sys.argv[2])
    files = sorted({p.name for p in cand.glob("module_*.json")} |
                   {p.name for p in base.glob("module_*.json")})
    results, n_fail = [], 0
    for rel in files:
        r = compare_file(rel, base, cand)
        results.append(r)
        mark = {"PASS": "PASS", "FAIL": "FAIL", "PASS_AGG": "PASS*"}.get(
            r.get("status"), r.get("status"))
        print(f"[{mark:5s}] {rel}", end="")
        if "counts" in r:
            c, s = r["counts"], r["sections"]
            print(f"  same={c['same']} diff={c['diff']} skipped={c['skip']} "
                  f"| agg_diff={s['aggregate']} detail_diff={s['detail']}")
            for d in r["diffs"]:
                if d["section"] == "aggregate" or r["status"] == "FAIL":
                    print(f"        {d['verdict']:8s} [{d['section']}] "
                          f"{d['path']}  {d['detail']}")
        else:
            print(f"  {r.get('status')}")
        if r.get("status") == "FAIL" or r.get("status") not in ("PASS", "PASS_AGG"):
            n_fail += 1
    out = Path(cand) / "_repro-compare.json"
    out.write_text(json.dumps({"baseline": str(base), "candidate": str(cand),
                               "files": results}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n{'='*64}")
    print("PASS  = 逐位一致 · PASS* = 汇总层一致(仅逐查询明细差异) · FAIL = 汇总层超差")
    print(f"{'REPRODUCIBLE (aggregate)' if n_fail == 0 else f'{n_fail} MODULE(S) WITH AGGREGATE FAIL'}"
          f" — 详情 {out}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
