#!/usr/bin/env python3
"""基线复现 CLI — 在同一后端上跑 6 个检索 baseline，用同一 chat API 作答。

实现体在 experiments/baselines.py（runner 复用同一份代码）。

用法（在 benchmark-suite/ 下）
    python scripts/113_baselines.py --questions data/papers/qa_v2.json \
        --methods bm25,vector,rrf,rerank,crag,selfrag --limit 80
    python scripts/113_baselines.py --questions data/papers/qa_v2.json --methods bm25,vector
    python scripts/113_baselines.py --methods bm25 --question "..."      # 冒烟

输出：results/runs/<run_id>/baselines.json（含 env 指纹，不可原地覆盖）。
退出码：全部方法全部题都落盘 → 0；否则 1。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

import baselines as B  # noqa: E402
from lib import env_fingerprint, set_run  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="")
    ap.add_argument("--question", default="")
    ap.add_argument("--methods", default="bm25,vector,rrf,rerank,crag,selfrag")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--out", default="baselines.json")
    args = ap.parse_args()

    methods = [m.strip().lower() for m in args.methods.split(",") if m.strip()]
    bad = [m for m in methods if m not in B.METHODS]
    if bad:
        ap.error(f"unknown method(s) {bad}; choose from {B.METHODS}")

    if args.question:
        questions = [{"qid": "Q1", "question": args.question}]
    elif args.questions:
        raw = json.loads((SUITE / args.questions).read_text(encoding="utf-8"))
        questions = [{"qid": q.get("qid", f"Q{i}"), "question": q["question"]}
                     for i, q in enumerate(raw["questions"][: args.limit], 1)]
    else:
        ap.error("provide --question or --questions")

    out_dir = set_run()
    print(f"[run] {out_dir.name} · {len(questions)} questions × "
          f"{len(methods)} methods", flush=True)

    rows = B.run_all(questions, methods, progress=lambda s: print(s, flush=True))
    ok = sum(1 for r in rows if not r.get("error"))

    payload = {"run_id": out_dir.name, "env": env_fingerprint(),
               "questions_file": args.questions, "methods": methods,
               "n_questions": len(questions), "n_ok": ok, "n_rows": len(rows),
               "rows": rows}
    (out_dir / args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[baselines] {ok}/{len(rows)} rows ok → {out_dir / args.out}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
