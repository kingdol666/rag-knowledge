"""Experiment runner: launch the three retrieval tracks on the same corpus.

Two execution modes:
  --via chat (default, harness=claude)
      Every track runs through the platform's EXTERNAL answer endpoint
      POST /api/claude/chat with engine:"claude" — the same surface an outside
      caller uses. Track A is unrestricted (the system's own QDCVR path);
      B locks allowedTools to Read/Grep/Glob over the corpus dir (bare agent);
      C locks allowedTools to the vector-search MCP tool (dense-RAG protocol).
      Monitored: full event timeline, tool calls, latency, SDK duration,
      tokens (input/output/cache) and total_cost_usd.
  --via toolloop (legacy, harness=omp)
      The in-process ToolAgent loop from agent_loop.py with per-track toolsets.

Usage (from benchmark-suite/):
  python -m experiments.runner --question "Which three ontologies subdivide the Gene Ontology?"
  python -m experiments.runner --questions data/papers/qa_questions.json --limit 3
  python -m experiments.runner --questions data/papers/qa_questions.json --tracks a,c
  python -m experiments.runner --question "..." --via toolloop --tracks b   # legacy omp loop
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

RESULTS = SUITE / "results"


def run_chat(track: str, question: str, max_steps: int) -> dict:
    from chat_tracks import run_chat_track, guard_url, OPENER
    try:
        return run_chat_track(track, question)
    except Exception as first:  # noqa: BLE001 — self-heal: nuxt dev can crash
        msg = f"{type(first).__name__}: {str(first)[:160]}"
        print(f"[{track}] failed ({msg}) -> restarting WEB only (backend/KB "
              f"system stays untouched), retrying once ...", flush=True)
        subprocess.run([sys.executable,
                        str(SUITE.parent / "scripts" / "restart_web.py")],
                       check=False)
        probe = "http://127.0.0.1:6789/"
        for _ in range(30):
            time.sleep(6)
            try:
                guard_url(probe)
                req = urllib.request.Request(probe)
                cand = SUITE.parent / "storage" / "loop-auth.json"
                if cand.exists():
                    tok = json.loads(cand.read_text(encoding="utf-8")).get("token")
                    if tok:
                        req.add_header("Authorization", f"Bearer {tok}")
                OPENER.open(req, timeout=8).read()
                break
            except Exception:
                continue
        r = run_chat_track(track, question)
        r["retried_after_restart"] = True
        r["first_error"] = msg
        return r


def run_toolloop(track: str, question: str, max_steps: int) -> dict:
    from tracks import build
    agent = build(track, question, max_steps=max_steps)
    return agent.run(question)


def main() -> int:
    ap = argparse.ArgumentParser(description="Three-track retrieval experiment")
    ap.add_argument("--question", help="single question text")
    ap.add_argument("--questions", help="questions JSON (questions[].question)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--tracks", default="a,b,c")
    ap.add_argument("--max-steps", type=int, default=8, help="toolloop mode only")
    ap.add_argument("--via", default="chat", choices=["chat", "toolloop"],
                    help="chat = external API, harness=claude (default)")
    args = ap.parse_args()

    if args.question:
        questions = [{"qid": "Q1", "question": args.question}]
    elif args.questions:
        raw = json.loads((SUITE / args.questions).read_text(encoding="utf-8"))
        questions = [{"qid": q.get("qid", f"Q{i}"), "question": q["question"]}
                     for i, q in enumerate(raw["questions"][: args.limit], 1)]
    else:
        ap.error("provide --question or --questions")

    tracks = [t.strip().lower() for t in args.tracks.split(",") if t.strip()]
    runner = run_chat if args.via == "chat" else run_toolloop
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = RESULTS / f"experiment_{args.via}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for q in questions:
        for t in tracks:
            print(f"[{q['qid']}/{t}] running ({args.via}) ...", flush=True)
            try:
                r = runner(t, q["question"], args.max_steps)
                r.update({"qid": q["qid"], "question": q["question"], "via": args.via})
            except Exception as e:  # noqa: BLE001 — record and continue
                r = {"qid": q["qid"], "question": q["question"], "track": t,
                     "via": args.via, "answer": f"(track failed: {type(e).__name__}:"
                                                f" {str(e)[:200]})",
                     "latency_s": 0, "tool_call_count": 0, "error": True}
            rows.append(r)
            (out_dir / f"track_{t}_{q['qid']}.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
            tok = r.get("tokens") or {}
            print(f"[{q['qid']}/{t}] {r.get('latency_s')}s, "
                  f"{r.get('tool_call_count')} tools, "
                  f"tok in={tok.get('input')} out={tok.get('output')}", flush=True)

    summary(rows, tracks, questions, out_dir, args.via)
    print(f"[done] {out_dir}")
    return 0


def summary(rows: list, tracks: list, questions: list, out_dir: Path, via: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Three-Track Retrieval Experiment ({via}, harness=claude)", "",
             f"Generated {now} · same 50-paper corpus · "
             f"questions: {len(questions)} · tracks: {', '.join(tracks)}", "",
             "## Run monitor", "",
             "| QID | Track | Latency s | Tools | Tokens in | Tokens out | "
             "Cache read | Cost USD |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        tok = r.get("tokens") or {}
        lines.append(
            f"| {r['qid']} | {r['track']} | {r.get('latency_s')} | "
            f"{r.get('tool_call_count')} | {tok.get('input', '—')} | "
            f"{tok.get('output', '—')} | {tok.get('cache_read', '—')} | "
            f"{r.get('total_cost_usd', '—')} |")
    tot_out = sum((r.get("tokens") or {}).get("output") or 0 for r in rows)
    tot_in = sum((r.get("tokens") or {}).get("input") or 0 for r in rows)
    tot_cost = sum(r.get("total_cost_usd") or 0 for r in rows)
    lat = [r.get("latency_s") or 0 for r in rows if r.get("latency_s")]
    lines += ["", f"**Totals**: latency avg "
              f"{round(sum(lat) / max(1, len(lat)), 1)}s · tokens in {tot_in} · "
              f"out {tot_out} · cost ${round(tot_cost, 4)}", "",
              "## Verbatim answers", ""]
    for r in rows:
        lines += [f"### [{r['track']}] {r['qid']} — {r.get('latency_s')}s, "
                  f"{r.get('tool_call_count')} tool calls, "
                  f"tokens out {(r.get('tokens') or {}).get('output', '—')}", "",
                  f"**Q:** {r['question']}", "", r.get("answer", ""), ""]
    (out_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
