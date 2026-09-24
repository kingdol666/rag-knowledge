"""Experiment runner — agent tracks + reproducible baselines on one corpus.

Track names accepted by --tracks
--------------------------------
  Agent tracks (external chat API, harness=claude):
    a   platform kb_* tools + file tools   (cwd pinned to the corpus dir)
    a2  platform kb_* tools only           (leakage-free primary arm)
    b   bare agent, file tools only
    c   dense RAG, kb_search_vector only
  Retrieval baselines (local retrieval + the same chat API for answering):
    bm25 vector rrf rerank crag selfrag

Every answer — agent track or baseline — goes through the platform's external
POST /api/claude/chat. Baselines answer closed-book from their own evidence
pack, so the generation step is identical and only retrieval differs.

`execute()` is the reusable core (used by `benchmark-suite/exp.py`, the unified
launcher); `main()` is the CLI.

Usage (from benchmark-suite/)
  python -m experiments.runner --question "Which three ontologies subdivide the Gene Ontology?"
  python -m experiments.runner --questions data/papers/qa_questions.json --tracks a2,b,c
  python -m experiments.runner --questions data/papers/qa_questions.json --tracks bm25,vector,rrf,rerank --limit 5
  python -m experiments.runner --fast                      # 3 questions, a2,b,c, quick smoke
  python -m experiments.runner --list-tracks
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(SUITE / "scripts"))

RESULTS = SUITE / "results"

AGENT_TRACKS = ["a", "a2", "b", "c"]
DEFAULT_TRACKS = "a2,b,c"          # leakage-free, fair set (see chat_tracks docstring)
BASELINE_METHODS = ["bm25", "vector", "rrf", "rerank", "crag", "selfrag"]


def provenance() -> dict:
    try:
        from lib import config_hash, git_commit
        sha, cfg = git_commit(), config_hash()
    except Exception:  # noqa: BLE001
        sha, cfg = "", ""
    try:
        from chat_tracks import PROMPT_VERSION
        pv = PROMPT_VERSION
    except Exception:  # noqa: BLE001
        pv = ""
    return {"git_commit": sha, "config_hash": cfg, "prompt_version": pv,
            "started_utc": datetime.now(timezone.utc).isoformat()}


def run_chat(track: str, question: str, max_turns: int,
             selfheal: bool = True) -> dict:
    from chat_tracks import run_chat_track
    try:
        return run_chat_track(track, question, max_turns=max_turns)
    except Exception as first:  # noqa: BLE001 — nuxt dev can crash
        msg = f"{type(first).__name__}: {str(first)[:160]}"
        if not selfheal:
            raise
        print(f"[{track}] failed ({msg}) -> restarting WEB only (backend/KB "
              f"system stays untouched), retrying once ...", flush=True)
        subprocess.run([sys.executable,
                        str(SUITE.parent / "scripts" / "restart_web.py")],
                       check=False)
        probe = "http://127.0.0.1:6789/"
        for _ in range(30):
            time.sleep(6)
            try:
                import urllib.request
                from chat_tracks import OPENER, guard_url
                guard_url(probe)
                req = urllib.request.Request(probe)
                cand = SUITE.parent / "storage" / "loop-auth.json"
                if cand.exists():
                    tok = json.loads(cand.read_text(encoding="utf-8")).get("token")
                    if tok:
                        req.add_header("Authorization", f"Bearer {tok}")
                OPENER.open(req, timeout=8).read()
                break
            except Exception:  # noqa: BLE001
                continue
        r = run_chat_track(track, question, max_turns=max_turns)
        r["retried_after_restart"] = True
        r["first_error"] = msg
        return r


def question_order(tracks: list[str], qid: str, seed: int,
                   shuffle: bool) -> list[str]:
    """Randomise per-question track order to average out warm-up / cache order
    effects (a fixed a->b->c order can bias whoever runs first)."""
    if not shuffle:
        return list(tracks)
    rnd = random.Random(f"{seed}:{qid}")
    out = list(tracks)
    rnd.shuffle(out)
    return out


def new_run_dir() -> Path:
    """Canonical run directory: results/runs/<run>-<utc>-<sha>/."""
    try:
        from lib import new_run_dir as _n
        return _n()
    except Exception:  # noqa: BLE001
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        d = RESULTS / "runs" / f"run-{stamp}"
        d.mkdir(parents=True, exist_ok=True)
        return d


def execute(questions: list[dict], tracks: list[str], out_dir: Path, *,
            max_turns: int = 12, seed: int = 0, shuffle: bool = True,
            selfheal: bool = True, monitor_system: bool = False,
            dry_run: bool = False, quiet: bool = False) -> list[dict]:
    """Run every (question × track) and persist one JSON per cell.

    This is the single execution core shared by the CLI and `exp.py`.

    dry_run=True performs NO network call — it writes placeholder cells so the
    whole downstream chain (compare_report / 114 / 116 / HTML) can be exercised
    offline. Every dry-run cell is stamped `dry_run: true` and must never be
    reported as a real result.
    """
    agent_tracks = [t for t in tracks if t in AGENT_TRACKS]
    baseline_methods = [t for t in tracks if t in BASELINE_METHODS]
    prov = provenance()
    out_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        rows = []
        for q in questions:
            for t in tracks:
                r = {"qid": q["qid"], "question": q["question"], "track": t,
                     "method": t, "via": "dry-run", "dry_run": True,
                     "answer": "(dry-run placeholder — no API call made)",
                     "latency_s": 0.0, "tool_call_count": 0,
                     "tokens": {"input": 0, "output": 0},
                     "total_cost_usd": 0.0, "ranked": [], "evidence_sources": [],
                     "prompt_version": prov["prompt_version"]}
                rows.append(r)
                (out_dir / f"track_{t}_{q['qid']}.json").write_text(
                    json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        (out_dir / "run_manifest.json").write_text(
            json.dumps({**prov, "tracks": tracks, "questions": len(questions),
                        "seed": seed, "max_turns": max_turns, "shuffled": shuffle,
                        "selfheal": selfheal, "monitor_system": monitor_system,
                        "dry_run": True, "n_rows": len(rows),
                        "total_cost_usd": 0.0, "tokens_out_total": 0},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        if not quiet:
            print(f"[dry-run] {len(rows)} placeholder cells → {out_dir} "
                  f"(no API call made)")
        return rows

    bm25 = None
    if baseline_methods:
        import baselines
        bm25 = baselines.BM25(baselines.load_docs())

    mon = None
    if monitor_system:
        from monitor import SystemMonitor
        mon = SystemMonitor()

    rows: list[dict] = []
    for q in questions:
        order = question_order(agent_tracks + baseline_methods, q["qid"], seed,
                               shuffle)
        for t in order:
            if not quiet:
                print(f"[{q['qid']}/{t}] running ...", flush=True)
            if mon:
                mon.start()
            try:
                if t in BASELINE_METHODS:
                    import baselines
                    r = baselines.run_method(t, q["question"], q["qid"], bm25)
                else:
                    r = run_chat(t, q["question"], max_turns, selfheal=selfheal)
                r.update({"qid": q["qid"], "question": q["question"],
                          "via": "chat", "prompt_version": prov["prompt_version"],
                          "git_commit": prov["git_commit"],
                          "config_hash": prov["config_hash"],
                          "seed": seed, "max_turns": max_turns})
            except Exception as e:  # noqa: BLE001 — record and continue
                r = {"qid": q["qid"], "question": q["question"], "track": t,
                     "via": "chat",
                     "answer": f"(track failed: {type(e).__name__}: {str(e)[:200]})",
                     "latency_s": 0, "tool_call_count": 0, "error": True}
            if mon:
                r["system"] = mon.stop()
            rows.append(r)
            (out_dir / f"track_{t}_{q['qid']}.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
            if not quiet:
                tok = r.get("tokens") or {}
                print(f"[{q['qid']}/{t}] {r.get('latency_s')}s, "
                      f"{r.get('tool_call_count')} tools, "
                      f"tok in={tok.get('input')} out={tok.get('output')}",
                      flush=True)

    tot_cost = round(sum(r.get("total_cost_usd") or 0 for r in rows), 4)
    tot_out = sum((r.get("tokens") or {}).get("output") or 0 for r in rows)
    (out_dir / "run_manifest.json").write_text(
        json.dumps({**prov, "tracks": tracks, "questions": len(questions),
                    "seed": seed, "max_turns": max_turns,
                    "shuffled": shuffle, "selfheal": selfheal,
                    "monitor_system": monitor_system, "dry_run": False,
                    "n_rows": len(rows), "total_cost_usd": tot_cost,
                    "tokens_out_total": tot_out},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def summary(rows: list, tracks: list, questions: list, out_dir: Path) -> None:
    def _m(r: dict) -> str:
        # agent tracks carry `track`; baselines carry `method`
        return str(r.get("track") or r.get("method") or "?")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Three-Track Retrieval Experiment (chat, harness=claude)", "",
             f"Generated {now} · same corpus · questions: {len(questions)} · "
             f"tracks: {', '.join(tracks)}", "",
             "## Run monitor", "",
             "| QID | Track | Latency s | Tools | Tokens in | Tokens out | "
             "Cache read | Cost USD |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        tok = r.get("tokens") or {}
        lines.append(
            f"| {r.get('qid')} | {_m(r)} | {r.get('latency_s')} | "
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
        lines += [f"### [{_m(r)}] {r.get('qid')} — {r.get('latency_s')}s, "
                  f"{r.get('tool_call_count')} tool calls, "
                  f"tokens out {(r.get('tokens') or {}).get('output', '—')}", "",
                  f"**Q:** {r.get('question')}", "", r.get("answer", ""), ""]
    (out_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Three-track retrieval experiment")
    ap.add_argument("--question", help="single question text")
    ap.add_argument("--questions", help="questions JSON (questions[].question)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--tracks", default=DEFAULT_TRACKS,
                    help=f"comma list from {AGENT_TRACKS + BASELINE_METHODS}")
    ap.add_argument("--max-turns", type=int, default=12,
                    help="max agent turns per run (uniform across tracks)")
    ap.add_argument("--seed", type=int, default=0, help="order-randomisation seed")
    ap.add_argument("--no-shuffle", action="store_true",
                    help="keep a fixed track order (do not randomise)")
    ap.add_argument("--no-selfheal", action="store_true",
                    help="disable the web-restart retry during scored runs")
    ap.add_argument("--monitor-system", action="store_true",
                    help="sample process CPU/RSS (+GPU) around each run (needs psutil)")
    ap.add_argument("--dry-run", action="store_true",
                    help="wiring check: write placeholder cells, make NO API call")
    ap.add_argument("--fast", action="store_true",
                    help="quick smoke: 3 questions, tracks a2,b,c, --no-selfheal")
    ap.add_argument("--list-tracks", action="store_true")
    args = ap.parse_args()

    if args.list_tracks:
        print("agent tracks :", ", ".join(AGENT_TRACKS))
        print("baselines    :", ", ".join(BASELINE_METHODS))
        print("default      :", DEFAULT_TRACKS)
        return 0

    if args.fast:
        args.limit = 3
        if args.tracks == DEFAULT_TRACKS:
            args.tracks = "a2,b,c"
        args.no_selfheal = True

    if args.question:
        questions = [{"qid": "Q1", "question": args.question}]
    elif args.questions:
        raw = json.loads((SUITE / args.questions).read_text(encoding="utf-8"))
        questions = [dict(q, qid=q.get("qid", f"Q{i}"))
                     for i, q in enumerate(raw["questions"][: args.limit], 1)]
    else:
        ap.error("provide --question or --questions")

    tracks = [t.strip().lower() for t in args.tracks.split(",") if t.strip()]
    unknown = [t for t in tracks if t not in AGENT_TRACKS + BASELINE_METHODS]
    if unknown:
        ap.error(f"unknown track(s) {unknown}; "
                 f"choose from {AGENT_TRACKS + BASELINE_METHODS}")

    out_dir = new_run_dir()
    rows = execute(questions, tracks, out_dir, max_turns=args.max_turns,
                   seed=args.seed, shuffle=not args.no_shuffle,
                   selfheal=not args.no_selfheal,
                   monitor_system=args.monitor_system,
                   dry_run=args.dry_run)
    summary(rows, tracks, questions, out_dir)
    print(f"[done] {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
