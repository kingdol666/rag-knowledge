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
import subprocess
import sys
import time
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
    """检查平台是否可跑；返回 {ok, backend, web, token, token_state, kbmcp}。

    token 不只检查"存在"，而是打到需要鉴权的端点上验证；过期则用
    loop-auth.json 里的凭据自动重新登录（stale-token self-heal）。
    2026-09-30 新增 kb-mcp 常驻 SSE(:8000) 探活——chat API 的 kbEnhanced
    车道全部经它取工具；挂了也能被服务端 ensureKbMcp 自动拉起，故只报
    状态不挡 ok。
    """
    from lib import BACKEND, WEB, check_token

    out = {"backend": False, "web": False, "token": False, "token_state": "?",
           "kbmcp": False, "backend_url": BACKEND, "web_url": WEB}
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
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/sse", timeout=5) as r:
            out["kbmcp"] = r.status == 200
    except Exception:  # noqa: BLE001
        pass
    out["ok"] = out["backend"] and out["web"] and out["token"]
    if verbose:
        print(f"[preflight] backend {BACKEND}: {'OK' if out['backend'] else 'DOWN'}")
        print(f"[preflight] web     {WEB}: {'OK' if out['web'] else 'DOWN'}")
        print(f"[preflight] kb-mcp  http://127.0.0.1:8000/sse: "
              f"{'OK' if out['kbmcp'] else 'DOWN（chat API ensureKbMcp 会自动拉起，不挡门）'}")
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


def run_retmodes(args) -> int:
    """检索任务矩阵: 三模式(A/B/C) + 检索类 baseline, 同题同库纯检索对照.

    - 模式跑在真库(18 KB, q1/q2 金标在库), B 臂书架标签取自内置 registry;
    - bm25/rrf 跑 corpus_md 100 篇(金标论文在集), vector 走平台跨库检索;
    - 全部纯检索(retrieval_only), 无 LLM 回答成本; 产出 RETRIEVAL-COMPARE.md.
    """
    from datetime import datetime, timezone
    import runner as _runner
    from experiments.retrieval_modes import (
        QUESTIONS, RUNNERS, ensure_laya_interpreter, resolve_laya_python,
        verify_gate)
    ensure_laya_interpreter()

    ret_baselines = [b.strip() for b in args.ret_baselines.split(",") if b.strip()]
    qids = list(QUESTIONS)
    out_dir = _runner.new_run_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    laya_py = resolve_laya_python()
    try:
        probe = subprocess.run(
            [str(laya_py), "-c",
             "import torch;print(torch.__version__, torch.cuda.is_available())"],
            capture_output=True, text=True, timeout=120)
        ver, _, cuda = probe.stdout.strip().partition(" ")
        laya_env = {"python": str(laya_py), "torch": ver, "cuda": cuda == "True"}
    except Exception as e:  # noqa: BLE001
        laya_env = {"error": str(e)[:120]}
    print(f"[exp:retmodes] run={out_dir.name} · questions={qids} · "
          f"modes=A/B/C · baselines={ret_baselines}")
    print(f"[exp:retmodes] laya_env={laya_env}")

    rows: list[dict] = []
    # 三模式臂
    for m in ("A", "B", "C"):
        for qid in qids:
            q = QUESTIONS[qid]
            print(f"[exp:retmodes] mode {m} × {qid} …", flush=True)
            t0 = time.time()
            try:
                arm = RUNNERS[m](q, out_dir / f"arm_{m}-{qid}.json")
            except Exception as e:  # noqa: BLE001
                arm = {"mode": m, "ok": False, "n_result_docs": 0,
                       "gold_hit": False, "kept_doc_paths": [],
                       "error": f"{type(e).__name__}: {str(e)[:200]}"}
            gate = verify_gate(arm, q)
            rows.append({
                "method": f"mode_{m}", "qid": qid, "question": q["text"],
                "latency_s": arm.get("wall_s"),
                "retrieval_gold": arm.get("gold_hit"),
                "n_docs": arm.get("n_result_docs"),
                "ranked": arm.get("kept_doc_paths") or [],
                "evidence_chars": arm.get("evidence_chars", 0),
                "real_engine": arm.get("real_engine"),
                "gate_passed": gate["passed"], "via": "retrieval-mode",
                "wall_overhead_s": round(time.time() - t0, 1),
            })
            print(f"[exp:retmodes]   → {arm.get('wall_s')}s gold={arm.get('gold_hit')} "
                  f"docs={arm.get('n_result_docs')}", flush=True)
            if m == "B":
                # B 臂在进程内持有一份 GPU Laya; 立即释放再进 C 子进程,
                # 否则两份副本叠加会顶爆显存, WDDM 换页拖慢 ~20x(实测 27min vs 68s)
                try:
                    import jev_filter as _jf
                    _jf.release_laya()
                    print("[exp:retmodes] released in-process Laya VRAM (post-B, pre-C)",
                          flush=True)
                except Exception as e:  # noqa: BLE001
                    print(f"[exp:retmodes] laya release skipped: {e}", flush=True)
    # baseline 臂(纯检索)
    import baselines as bl
    bm25 = bl.BM25(bl.load_docs())
    for b in ret_baselines:
        for qid in qids:
            q = QUESTIONS[qid]
            print(f"[exp:retmodes] baseline {b} × {qid} …", flush=True)
            try:
                r = bl.run_method(b, q["text"], qid, bm25=bm25, retrieval_only=True)
                blob = " ".join(str(p) for p in (r.get("ranked") or [])).lower()
                gold_src = (q["gold_substr"] in blob) or (q.get("gold_id", "") in blob)
                rows.append({
                    "method": b, "qid": qid, "question": q["text"],
                    "latency_s": r.get("latency_s"),
                    "retrieval_gold": gold_src,
                    "n_docs": len(r.get("ranked") or []),
                    "ranked": r.get("ranked") or [],
                    "evidence_chars": r.get("evidence_chars", 0),
                    "real_engine": None, "gate_passed": None,
                    "via": "baseline-retrieval-only",
                })
                print(f"[exp:retmodes]   → {r.get('latency_s')}s gold={gold_src} "
                      f"docs={len(r.get('ranked') or [])}", flush=True)
            except Exception as e:  # noqa: BLE001
                rows.append({"method": b, "qid": qid, "error": str(e)[:200]})
                print(f"[exp:retmodes]   → ERROR {str(e)[:120]}", flush=True)

    (out_dir / "retmatrix.json").write_text(
        json.dumps({"laya_env": laya_env, "rows": rows},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    # RETRIEVAL-COMPARE.md
    L = ["# 检索任务对照矩阵（三模式 + baseline, 纯检索无 LLM 回答）", "",
         f"- Run: `{out_dir.name}` · 生成: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
         f"- Laya 环境: {laya_env}（判决 GPU 化, C 与 A/B 同环境同通道）",
         "- 语料: 模式=真库(q1/q2 金标在库); bm25/rrf=corpus_md 100 篇(金标在集); vector=平台跨库", "",
         "| 方法 | q1 耗时 | q2 耗时 | q1 金标 | q2 金标 | q1 docs | q2 docs |",
         "|---|---:|---:|:--:|:--:|---:|---:|"]
    methods = [f"mode_{m}" for m in ("A", "B", "C")] + ret_baselines
    for meth in methods:
        rs = {r["qid"]: r for r in rows if r.get("method") == meth}
        if not rs:
            continue
        def _cell(qid, key):
            r = rs.get(qid)
            return "—" if not r else str(r.get(key))
        L.append(f"| {meth} | {_cell('q1','latency_s')}s | {_cell('q2','latency_s')}s "
                 f"| {'✅' if rs.get('q1',{}).get('retrieval_gold') else '❌'} "
                 f"| {'✅' if rs.get('q2',{}).get('retrieval_gold') else '❌'} "
                 f"| {_cell('q1','n_docs')} | {_cell('q2','n_docs')} |")
    L += ["", "> 全部为纯检索任务（无 LLM 回答）；模式臂经硬验证门（real_engine/金标/延迟），",
          "> baseline 臂为 retrieval_only（answer=None, 零 token 成本）。", ""]
    (out_dir / "RETRIEVAL-COMPARE.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[exp:retmodes] 报告 → {out_dir / 'RETRIEVAL-COMPARE.md'}")
    n_gold = sum(1 for r in rows if r.get("retrieval_gold"))
    print(f"[exp:retmodes] 金标命中 {n_gold}/{len(rows)}")
    return 0


def run_chatmodes(args) -> int:
    """Chat-API 三模式系统臂: 当前系统自身 A/B/C 执行流, 全部走官方 chat API。

    与 --retmodes 互补：retmodes 测检索脚本（子进程直跑、纯检索无 LLM），
    chatmodes 测**系统本体**——默认非流式 JSON、kbIds 钉库、服务端工具门禁、
    MCP 挂载、Laya 判卷、如实拒答，即外部调用方真实拿到的执行流程。
    题 = cm1/cm2（金标在库，答案金标词判定）+ cm3（域外，如实拒答判定）。
    """
    from experiments import chat_mode_arms as cma
    from lib import new_run_dir

    out_dir = new_run_dir("chatmodes")
    print(f"[exp:chatmodes] run={out_dir.name} · modes=A/B/C · "
          f"questions={list(cma.QUESTIONS)}", flush=True)
    res = cma.run_all(out_dir)
    return 0 if res["n_pass"] == len(res["rows"]) else 2


def main() -> int:
    ap = argparse.ArgumentParser(description="Unified experiment launcher")
    ap.add_argument("question", nargs="?", default="", help="单个问题文本")
    ap.add_argument("--questions", default="")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--project", default="a2", choices=PROJECT_ARMS)
    ap.add_argument("--baselines", default=",".join(DEFAULT_BASELINES))
    ap.add_argument("--full", action="store_true", help="全轨 + 6 baseline")
    ap.add_argument("--fast", action="store_true", help="1 题快速冒烟")
    ap.add_argument("--retmodes", action="store_true",
                    help="检索任务矩阵: 三模式(A/B/C)+检索类baseline 在内置 q1/q2 上"
                         "跑纯检索(无LLM回答), 产出 RETRIEVAL-COMPARE.md")
    ap.add_argument("--chatmodes", action="store_true",
                    help="Chat-API 三模式系统臂: 当前系统 A/B/C 执行流(默认非流式/"
                         "kbIds 钉库/服务端工具门禁) 在 cm1-cm3 上真实跑, "
                         "产出 CHAT-MODES-COMPARE.md")
    ap.add_argument("--ret-baselines", default="bm25,vector,rrf",
                    help="--retmodes 的 baseline 集(纯检索类; rerank 含 LLM 慎选)")
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
        print("retmodes     : 三模式(A/B/C)+检索baseline 纯检索矩阵 (--retmodes)")
        print("chatmodes    : Chat-API 三模式系统臂 (当前系统执行流, --chatmodes)")
        return 0

    if args.retmodes:
        import time  # noqa: F401 — run_retmodes 内部使用
        return run_retmodes(args)

    if args.chatmodes:
        return run_chatmodes(args)

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
