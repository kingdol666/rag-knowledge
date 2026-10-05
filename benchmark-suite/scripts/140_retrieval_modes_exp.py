#!/usr/bin/env python3
"""140 — 三模式检索实验启动器（A 向量优先 / B 图书管理员 / C 混合）.

把三种检索模式作为 exp 实验项目的一等公民臂：同一真库、同一问题、只换检索模式。
每个 (mode × question) 跑完立即落盘 + 打印一行结果（后台长任务友好）；
每个臂过硬验证门（exit/real_engine/证据/金标命中/延迟），失败 exit 2。

用法（在 benchmark-suite/ 下或仓库根均可）:
    python benchmark-suite/scripts/140_retrieval_modes_exp.py --mode A
    python benchmark-suite/scripts/140_retrieval_modes_exp.py --mode B --question q2
    python benchmark-suite/scripts/140_retrieval_modes_exp.py --mode C --question both
    python benchmark-suite/scripts/140_retrieval_modes_exp.py --mode A --mode B --mode C
    python benchmark-suite/scripts/140_retrieval_modes_exp.py --run-dir <已有目录>   # 续跑补臂
退出码: 全部门通过 → 0；任一臂验证失败 → 2。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

from experiments.retrieval_modes import (  # noqa: E402
    QUESTIONS, RUNNERS, ensure_laya_interpreter, verify_gate)


def default_run_dir() -> Path:
    from lib import new_run_dir
    return new_run_dir("retmodes")


def laya_env_snapshot() -> dict:
    """判决环境证据: Laya 宿主解释器的 torch 版本与 CUDA 可用性(写入 RUN.json)."""
    from experiments.retrieval_modes import resolve_laya_python
    py = resolve_laya_python()
    try:
        out = subprocess.run(
            [str(py), "-c",
             "import torch;print(torch.__version__, torch.cuda.is_available())"],
            capture_output=True, text=True, timeout=120)
        ver, _, cuda = out.stdout.strip().partition(" ")
        return {"python": str(py), "torch": ver, "cuda": cuda.strip() == "True"}
    except Exception as e:  # noqa: BLE001
        return {"python": str(py), "error": f"{type(e).__name__}: {str(e)[:120]}"}


def corpus_snapshot() -> dict:
    try:
        from lib import McpClient
        mc = McpClient()
        cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
        rows = cat.get("catalog") or []
        docs = sum(int(k.get("doc_count") or 0) for k in rows)
        mc.close()
        return {"kbs": len(rows), "docs": docs}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", action="append", choices=["A", "B", "C"],
                    help="检索模式臂，可重复（默认 A B C 全跑）")
    ap.add_argument("--question", choices=["q1", "q2", "both"], default="both")
    ap.add_argument("--run-dir", default="")
    args = ap.parse_args()

    ensure_laya_interpreter()

    modes = args.mode or ["A", "B", "C"]
    qids = ["q1", "q2"] if args.question == "both" else [args.question]
    run_dir = Path(args.run_dir) if args.run_dir else default_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)

    # 预检（后端/Web/token 自愈）——与 exp.py 同一门
    sys.path.insert(0, str(SUITE))
    import exp as expmod
    pf = expmod.preflight(verbose=True)
    if not pf.get("ok"):
        print("[140] 平台未就绪 → 终止（先 ragctl up）")
        return 2

    manifest_path = run_dir / "RUN.json"
    manifest = {"run_dir": str(run_dir),
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "modes": modes, "questions": qids,
                "corpus": corpus_snapshot(),
                "laya_env": laya_env_snapshot(),
                "interpreter": sys.executable,
                "arms": {}}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    print(f"[140] run_dir = {run_dir}")
    print(f"[140] corpus  = {manifest['corpus']}")

    n_fail = 0
    for mode in modes:
        runner = RUNNERS[mode]
        for qid in qids:
            q = QUESTIONS[qid]
            out_path = run_dir / f"arm_{mode}-{qid}.json"
            print(f"[140] ▶ mode {mode} × {qid} start {time.strftime('%H:%M:%S')} …", flush=True)
            t0 = time.time()
            try:
                arm = runner(q, out_path)
            except Exception as e:  # noqa: BLE001
                arm = {"mode": mode, "ok": False,
                       "error": f"{type(e).__name__}: {str(e)[:300]}",
                       "wall_s": round(time.time() - t0, 1)}
            gate = verify_gate(arm, q)
            arm["gate"] = gate
            arm["question"] = {"qid": qid, "text": q["text"], "gold_substr": q["gold_substr"],
                               "gold_name": q["gold_name"]}
            # 立即落盘（含 gate）——一个臂一文件，绝不攒到最后
            out_path.write_text(json.dumps(arm, ensure_ascii=False, indent=1),
                                encoding="utf-8")
            manifest["arms"][f"{mode}-{qid}"] = {
                "file": out_path.name, "ok": arm.get("ok"),
                "wall_s": arm.get("wall_s"), "gate_passed": gate["passed"]}
            manifest["updated_utc"] = datetime.now(timezone.utc).isoformat()
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
            status = "PASS" if gate["passed"] else "FAIL"
            fails = [k for k, v in gate["checks"].items() if not v]
            print(f"[140] ◼ mode {mode} × {qid} {status} {arm.get('wall_s')}s "
                  f"docs={arm.get('n_result_docs')} gold={arm.get('gold_hit')} "
                  f"real={arm.get('real_engine')}"
                  + (f" 失败项={fails}" if fails else ""), flush=True)
            if not gate["passed"]:
                n_fail += 1

    print(f"[140] 完成：{len(modes) * len(qids)} 臂，{n_fail} 个未过门 → {run_dir}")
    return 2 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
