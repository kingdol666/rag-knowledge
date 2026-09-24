#!/usr/bin/env python3
"""exp.py — 实验平台统一入口（直接启动，同一问题对照项目 vs baseline）。

一条命令做三件事：
  1) 预检平台（后端 /health、Web、鉴权 token）；
  2) 在**同一个问题**上跑「项目（平台轨）+ 全部 baseline」，每次回答都真实
     经过被测系统的对外 API（POST /api/claude/chat）；
  3) 生成逐题并列对照 + 资源监控报告 COMPARE.md，并打印控制台对照表。

用法（在 benchmark-suite/ 下）
    python exp.py "Which three ontologies subdivide the Gene Ontology?"
    python exp.py --questions data/papers/qa_v2.json --limit 10
    python exp.py --fast                       # 1 题快速冒烟（项目 a2 + 4 baseline）
    python exp.py --full                       # 全轨：a,a2,b,c + 6 baseline
    python exp.py --project a --baselines bm25,vector,rerank
    python exp.py --report results/experiment_chat_<ts>   # 只重生成对照报告
    python exp.py --check                      # 只做预检
    python exp.py --list                       # 看可用方法

默认对照集（快）：项目 a2 + baseline bm25,vector,rrf,rerank（5 方法/题）
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

RESULTS = SUITE / "results"
PROJECT_ARMS = ["a", "a2", "b", "c"]
FAST_BASELINES = ["bm25", "vector", "rrf", "rerank"]
FULL_BASELINES = ["bm25", "vector", "rrf", "rerank", "crag", "selfrag"]
DEFAULT_BASELINES = FAST_BASELINES


def preflight(verbose: bool = True) -> dict:
    """检查平台是否可跑；返回 {ok, backend, web, token, token_state}。

    token 不只检查"存在"，而是打到需要鉴权的端点上验证；过期则用
    loop-auth.json 里的凭据自动重新登录（stale-token self-heal）。
    """
    from lib import BACKEND, WEB, check_token

    out = {"backend": False, "web": False, "token": False, "token_state": "?",
           "backend_url": BACKEND, "web_url": WEB}
    try:
        ok, state = check_token(WEB)
        out["token"], out["token_state"] = ok, state
    except Exception as e:  # noqa: BLE001
        out["token"], out["token_state"] = False, f"error:{type(e).__name__}"
    try:
        with urllib.request.urlopen(f"{BACKEND}/api/v1/health", timeout=6) as r:
            out["backend"] = r.status == 200
    except Exception:  # noqa: BLE001
        pass
    try:
        with urllib.request.urlopen(f"{WEB}/", timeout=6) as r:
            out["web"] = r.status < 500
    except Exception:  # noqa: BLE001
        pass
    out["ok"] = out["backend"] and out["web"] and out["token"]
    if verbose:
        print(f"[preflight] backend {BACKEND}: {'OK' if out['backend'] else 'DOWN'}")
        print(f"[preflight] web     {WEB}: {'OK' if out['web'] else 'DOWN'}")
        note = {"ok": "OK", "refreshed": "OK（已自动刷新过期 token）"}.get(
            out["token_state"], f"FAIL（{out['token_state']}）")
        print(f"[preflight] token: {note}")
        if not out["ok"]:
            print("[preflight] 平台未就绪 → 先 `ragctl up`（冷启动 ~20s）；"
                  "token 失效请检查 storage/loop-auth.json 的用户名/密码")
    return out


def _load_questions(args) -> list[dict]:
    if args.question:
        return [{"qid": "Q1", "question": args.question}]
    if args.questions:
        raw = json.loads((SUITE / args.questions).read_text(encoding="utf-8"))
        # keep the FULL question dict (gold_docs / arxiv_id / stratum) so the
        # comparison report can verify retrieval + citation gold hits.
        return [dict(q, qid=q.get("qid", f"Q{i}"))
                for i, q in enumerate(raw["questions"][: args.limit], 1)]
    raise SystemExit("provide a question text or --questions FILE")


def _console_table(payload: dict) -> None:
    pm = payload.get("per_method", {})
    print("\n方法            时延avg  时延med  tok_out  成本$   工具  检索命中  引用命中  弃答")
    print("-" * 82)
    for m, a in pm.items():
        rh = a.get("retrieval_gold_rate")
        ch = a.get("citation_gold_rate")
        print(f"{m:<14} {a['latency_avg_s']:>7} {a['latency_median_s']:>8} "
              f"{a['tokens_out_total']:>8} {a['cost_usd_total']:>7} "
              f"{a['tools_avg']:>5}  "
              f"{(f'{rh:.2f}' if rh is not None else '  — '):>7}  "
              f"{(f'{ch:.2f}' if ch is not None else '  — '):>7}  {a['abstentions']:>3}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Unified experiment launcher")
    ap.add_argument("question", nargs="?", default="", help="单个问题文本")
    ap.add_argument("--questions", default="")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--project", default="a2", choices=PROJECT_ARMS)
    ap.add_argument("--baselines", default=",".join(DEFAULT_BASELINES))
    ap.add_argument("--full", action="store_true", help="全轨 + 6 baseline")
    ap.add_argument("--fast", action="store_true", help="1 题快速冒烟")
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--monitor-system", action="store_true",
                    help="采样 CPU/RSS/GPU（需 psutil）")
    ap.add_argument("--report", default="", help="只对已有 run 目录重生成对照报告")
    ap.add_argument("--dry-run", action="store_true",
                    help="管线连通性检查：写占位结果，不调用任何 API")
    ap.add_argument("--no-html", action="store_true", help="不生成 COMPARE.html")
    ap.add_argument("--check", action="store_true", help="只做预检")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        print("project arms :", ", ".join(PROJECT_ARMS))
        print("baselines    :", ", ".join(FULL_BASELINES))
        print("default set  : project=a2 + baselines=" + ",".join(DEFAULT_BASELINES))
        return 0

    if args.check:
        return 0 if preflight()["ok"] else 1

    import compare_html
    import compare_report
    import runner

    def _emit(run_dir, questions):
        md, payload = compare_report.build(run_dir, questions)
        (run_dir / "COMPARE.md").write_text(md, encoding="utf-8")
        (run_dir / "monitor.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        if not args.no_html:
            (run_dir / "COMPARE.html").write_text(compare_html.render(payload),
                                                  encoding="utf-8")
        return payload

    if args.report:
        run = Path(args.report)
        run = run if run.is_absolute() else SUITE / args.report
        if not run.exists():
            print(f"[exp] run 目录不存在: {run}")
            return 1
        qfile = args.questions
        questions = (json.loads((SUITE / qfile).read_text(encoding="utf-8"))
                     if qfile else None)
        payload = _emit(run, questions)
        print(f"[exp] 对照报告 → {run / 'COMPARE.md'}")
        if not args.no_html:
            print(f"[exp] 可视化   → {run / 'COMPARE.html'}")
        _console_table(payload)
        return 0

    if args.fast:
        args.limit = 1

    if not args.dry_run:
        pf = preflight()
        if not pf["ok"]:
            print("[exp] 预检未通过：实验需要真实调用被测系统 API，请先启动平台。"
                  "（仅做管线检查可用 --dry-run）")
            return 1

    questions = _load_questions(args)
    baselines = FULL_BASELINES if args.full else \
        [b.strip() for b in args.baselines.split(",") if b.strip()]
    tracks = ([args.project] if not args.full else list(PROJECT_ARMS)) + baselines

    out_dir = runner.new_run_dir()
    print(f"[exp] run={out_dir.name} · {len(questions)} 题 × {len(tracks)} 方法 "
          f"= {len(questions) * len(tracks)} 次"
          + ("（dry-run，不调用 API）" if args.dry_run else "真实问答"))
    print(f"[exp] methods: {', '.join(tracks)}")

    rows = runner.execute(questions, tracks, out_dir,
                          max_turns=args.max_turns, seed=args.seed,
                          monitor_system=args.monitor_system,
                          dry_run=args.dry_run)
    runner.summary(rows, tracks, questions, out_dir)

    payload = _emit(out_dir, {"questions": questions})
    _console_table(payload)
    bad = [c for c in payload["self_checks"] if not c["ok"]]
    print(f"\n[exp] 自检 {len(payload['self_checks']) - len(bad)}/"
          f"{len(payload['self_checks'])} 通过"
          + (f" · 失败: {[c['check'] for c in bad]}" if bad else ""))
    print(f"[exp] 报告: {out_dir / 'COMPARE.md'}")
    if not args.no_html:
        print(f"[exp] 可视化: {out_dir / 'COMPARE.html'}")
    print(f"[exp] 监控: {out_dir / 'monitor.json'}")
    print(f"[exp] 逐题全文: {out_dir / 'SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
