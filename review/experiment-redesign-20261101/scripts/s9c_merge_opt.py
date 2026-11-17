# -*- coding: utf-8 -*-
"""优化轮 traces 合并（s6c 模式，落点 opt_bench —— 绝不触碰 final_bench 原件）。

1) 把 final_bench/s4_traces_final.json + s5_floor.json 复制进 opt_bench/（只读复制）；
2) 旧臂（A0/A1-readall/A1b/A2/A3）取自该副本，新臂（A0f/A0h/PD）取 opt_bench 顶层
   的 s4_traces_<ts>.json（按 mtime 升序合并，同臂后者覆盖）；
3) 写 opt_bench/s4_traces_merged.json，随后调用 s6_stats.py（基线 A0）——
   s6_stats 会把 s6_stats.json 写在输入旁（opt_bench），不污染 final_bench。

用法: python s9c_merge_opt.py [--run-stats]
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
EXP = BASE.parent
ART = EXP / "artifacts"
OPT = ART / "opt_bench"
FINAL = ART / "final_bench"
NEW_ARMS = {"A0f", "A0h", "PD"}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OPT.mkdir(parents=True, exist_ok=True)
    # 只读复制 final_bench 基线文件（不覆盖已存在副本，保住首份拷贝）
    for name in ("s4_traces_final.json", "s5_floor.json"):
        src, dst = FINAL / name, OPT / name
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"copied {name} -> opt_bench/ (read-only copy)")
    merged = {}
    old = json.loads((OPT / "s4_traces_final.json").read_text(encoding="utf-8"))
    for arm, rows in old.items():
        if arm not in NEW_ARMS and rows:
            merged[arm] = rows
            print(f"  {arm:<12s} <- final_bench copy ({len(rows)} traces)")
    # 新臂：opt_bench 顶层 s4_traces_*.json，mtime 升序；主跑 + 补跑分片含同臂部分行
    # → 按 qid 合并（同 qid 后传覆盖），最终每臂 76 行
    for p in sorted(OPT.glob("s4_traces_*.json"), key=lambda x: x.stat().st_mtime):
        if p.name in ("s4_traces_final.json", "s4_traces_merged.json"):
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for arm, rows in data.items():
            if rows and arm in NEW_ARMS:
                by_qid = {r["qid"]: r for r in merged.get(arm, [])}
                before = len(by_qid)
                for r in rows:
                    by_qid[r["qid"]] = r
                merged[arm] = list(by_qid.values())
                print(f"  {arm:<12s} <- {p.name} (+{len(by_qid)-before}/{len(rows)} rows -> {len(by_qid)})")
    out = OPT / "s4_traces_merged.json"
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"merged -> {out.name}")
    for arm, rows in sorted(merged.items()):
        gold = sum(1 for x in rows if x.get("gold_hit"))
        print(f"  {arm}: n={len(rows)} gold={gold}")
    if "--run-stats" in sys.argv:
        print("\nrunning s6_stats.py (baseline A0) from opt_bench ...")
        r = subprocess.run([sys.executable, str(BASE / "s6_stats.py"), str(out)],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout)
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
