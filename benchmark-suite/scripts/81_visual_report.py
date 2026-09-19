#!/usr/bin/env python3
"""Benchmark visual report generator — self-contained HTML (no external deps).

Reads every pipeline artifact from results/ and renders:
  pipeline funnel cards · vector-store coverage · retrieval regression bars ·
  three-track per-question latency/keyword comparison · per-question verbatim
  answers (QDCVR skill flow / bare agent / dense RAG baseline).

Color language (project convention): teal = platform system (Track A),
gray = baseline tracks (B/C), orange-red = warnings/failures.
Output: results/benchmark_visual_report.html
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"


def load(name: str):
    p = RESULTS / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def esc(s) -> str:
    return html.escape(str(s))


def main() -> int:
    survey = load("ingest_survey.json") or {}
    ingest = load("ingest_report.json") or {}
    tags = load("tags_report.json") or {}
    repro = load("repro_ingest.json") or {}
    cov = load("repro_coverage.json") or {}
    bench = load("bench10_qa.json") or {}
    ev = load("skill_track_evidence.json") or []
    ans = load("skill_track_answers.json") or {}
    bc = load("track_bc.json") or []

    answers = {a.get("qid"): a for a in (ans.get("answers") or [])}
    bcmap = {r.get("qid"): r for r in bc}
    baselines = repro.get("baselines") or {}
    cov_kbs = cov.get("kbs") or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ---- derived numbers ----
    parsed = survey.get("n", 0)
    papers_total = len(survey.get("papers", [])) or 50
    routed = ingest.get("verified", "?")
    routed_total = ingest.get("total", 50)
    chunks800 = baselines.get("Corpus-Chunks800", "?")
    cov_probe = "/".join(
        f"{(cov_kbs.get(k) or {}).get('probe_hit', '?')}/{(cov_kbs.get(k) or {}).get('probe_total', '?')}"
        for k in ("Corpus-Chunks800", "Corpus-Struct", "Corpus-Paras"))
    bench_passed = bench.get("passed", "?")

    track_a_latency = {}
    for e in ev:
        t = e.get("timings") or {}
        total = sum(v for k, v in t.items() if isinstance(v, (int, float)))
        p2 = (e.get("phase2") or {}).get("timings") or {}
        total += sum(v for v in p2.values() if isinstance(v, (int, float)))
        track_a_latency[e["qid"]] = round(total, 1)

    cards = [
        ("Papers on disk", papers_total, "gray"),
        ("Parsed → staging KB", f"{parsed}/{papers_total}",
         "ok" if parsed == papers_total else "warn"),
        ("Routed & probe-verified", f"{routed}/{routed_total}",
         "ok" if routed == routed_total else "warn"),
        ("Tags applied", f"ok {tags.get('ok', '?')} / fail {tags.get('fail', '?')}",
         "ok" if tags.get("fail") == 0 else "warn"),
        ("RAG chunks indexed", f"{chunks800} + "
         f"{baselines.get('Corpus-Struct', '?')} + {baselines.get('Corpus-Paras', '?')}",
         "gray"),
        ("Vector coverage (3 KBs)",
         f"{sum((cov_kbs.get(k) or {}).get('build_indexed_ok', 0) for k in ('Corpus-Chunks800', 'Corpus-Struct', 'Corpus-Paras'))}/"
         f"{sum((cov_kbs.get(k) or {}).get('expected_chunks', 0) for k in ('Corpus-Chunks800', 'Corpus-Struct', 'Corpus-Paras'))}"
         f" indexed · probes {cov_probe}",
         "ok" if (cov.get("pass")) else "warn"),
        ("Retrieval regression", f"{bench_passed}/{bench.get('total', 10)}",
         "ok" if (isinstance(bench_passed, int) and bench_passed >= 9) else "warn"),
    ]
    card_html = "\n".join(
        f'<div class="card {cls}"><div class="num">{esc(v)}</div>'
        f'<div class="lbl">{esc(k)}</div></div>'
        for k, v, cls in cards)

    # bench10 bars
    bench_rows = ""
    for r in (bench.get("rows") or []):
        cls = "pass" if r.get("pass") else "fail"
        kws = ", ".join(r.get("kw_hit") or []) or "—"
        bench_rows += (
            f'<tr class="{cls}"><td>{esc(r["qid"])}</td><td>{esc(r["field"])}</td>'
            f'<td>{"✓" if r.get("doc_hit") else "✗"}</td>'
            f'<td>{esc(kws)}</td><td>{esc((r.get("kb") or "—")[:18])}</td>'
            f'<td>{"PASS" if r.get("pass") else "FAIL"}</td></tr>')

    # three-track latency groups (per question)
    lat_rows = ""
    max_lat = 1.0
    per_q = []
    for r in bc:
        qid = r["qid"]
        a_lat = track_a_latency.get(qid)
        b_lat = (r.get("track_b_bare_agent") or {}).get("latency", 0)
        c_lat = (r.get("track_c_dense_rag") or {}).get("latency_total", 0)
        per_q.append((qid, a_lat, b_lat, c_lat))
        max_lat = max(max_lat, a_lat or 0, b_lat or 0, c_lat or 0)

    def bar(cls, qid, lat, label):
        if lat is None:
            return (f'<div class="barrow"><span class="blabel">{label}</span>'
                    f'<span class="bspace">not decomposed (agent-composed answer)</span></div>')
        w = max(2, int(lat / max_lat * 560))
        return (f'<div class="barrow"><span class="blabel">{label}</span>'
                f'<div class="btrack"><div class="bfill {cls}" style="width:{w}px">'
                f'</div><span class="bval">{lat}s</span></div></div>')

    for qid, a_lat, b_lat, c_lat in per_q:
        lat_rows += f'<div class="qblock"><div class="qid">{esc(qid)}</div>'
        lat_rows += bar("teal", qid, a_lat, "A · Platform KB (QDCVR)")
        lat_rows += bar("grayb", qid, b_lat, "B · Bare agent")
        lat_rows += bar("grayb", qid, c_lat, "C · Dense RAG")
        lat_rows += "</div>"

    # per-question verbatim answers
    qa_html = ""
    for r in bc:
        qid = r["qid"]
        q = r["question"]
        a = answers.get(qid) or {}
        b = (r.get("track_b_bare_agent") or {})
        c = (r.get("track_c_dense_rag") or {})
        gate = (a.get("gate") or {})
        qa_html += f'<details class="qa"><summary>{esc(qid)} — {esc(r.get("paper", ""))[:70]}</summary>'
        qa_html += f'<div class="q">{esc(q)}</div>'
        qa_html += ('<div class="answer a-track"><h4>Track A · Platform KB (QDCVR v2 skill flow) '
                    f'— gate {esc(gate.get("score", "?"))}/8 · {esc(gate.get("decision", ""))}</h4>'
                    f'<pre>{esc(a.get("final_answer", "(no answer recorded)"))}</pre></div>')
        qa_html += ('<div class="answer b-track"><h4>Track B · Bare agent — '
                    f'{esc(b.get("latency", "?"))}s · files: '
                    f'{esc(", ".join(b.get("files_used") or []) or "—")}</h4>'
                    f'<pre>{esc(b.get("raw_answer", ""))}</pre></div>')
        qa_html += ('<div class="answer c-track"><h4>Track C · Dense RAG — retrieval '
                    f'{esc(c.get("latency_retrieval", "?"))}s · {esc(c.get("evidence_chunks", "?"))} chunks</h4>'
                    f'<pre>{esc(c.get("raw_answer", ""))}</pre></div>')
        qa_html += "</details>"

    avg = lambda xs: round(sum(x for x in xs if x is not None) / max(1, len([x for x in xs if x is not None])), 1)
    a_avg = avg([track_a_latency.get(r["qid"]) for r in bc])
    b_avg = avg([(r.get("track_b_bare_agent") or {}).get("latency") for r in bc])
    c_avg = avg([(r.get("track_c_dense_rag") or {}).get("latency_total") for r in bc])

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Three-Track Benchmark — Visual Report</title>
<style>
  :root {{ --teal:#0f766e; --tealbg:#ccfbf1; --gray:#6b7280; --graybg:#f3f4f6;
          --warn:#b91c1c; --warnbg:#fee2e2; --ink:#111827; --line:#e5e7eb; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; color: var(--ink);
         margin: 0; background: #fafaf9; }}
  header {{ background: var(--ink); color: #fff; padding: 28px 40px; }}
  header h1 {{ margin: 0 0 6px; font-size: 22px; }}
  header p {{ margin: 0; color: #d1d5db; font-size: 13px; }}
  main {{ padding: 28px 40px; max-width: 1200px; margin: 0 auto; }}
  h2 {{ font-size: 16px; margin: 34px 0 12px; border-left: 4px solid var(--teal);
       padding-left: 10px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
           gap: 12px; }}
  .card {{ background: #fff; border: 1px solid var(--line); border-radius: 10px;
          padding: 14px 16px; }}
  .card.ok {{ border-top: 3px solid var(--teal); }}
  .card.warn {{ border-top: 3px solid var(--warn); background: var(--warnbg); }}
  .card.gray {{ border-top: 3px solid var(--gray); }}
  .card .num {{ font-size: 20px; font-weight: 700; }}
  .card .lbl {{ font-size: 12px; color: var(--gray); margin-top: 4px; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff;
          font-size: 13px; }}
  th, td {{ border: 1px solid var(--line); padding: 6px 10px; text-align: left; }}
  th {{ background: var(--graybg); }}
  tr.pass td:last-child {{ color: var(--teal); font-weight: 700; }}
  tr.fail td:last-child {{ color: var(--warn); font-weight: 700; }}
  tr.fail {{ background: var(--warnbg); }}
  .qblock {{ display: inline-block; vertical-align: top; margin: 8px 18px 8px 0; }}
  .qid {{ font-weight: 700; font-size: 12px; margin-bottom: 4px; color: var(--gray); }}
  .barrow {{ display: flex; align-items: center; margin: 3px 0; }}
  .blabel {{ width: 150px; font-size: 11px; color: var(--gray); }}
  .btrack {{ display: flex; align-items: center; gap: 6px; }}
  .bfill {{ height: 12px; border-radius: 3px; }}
  .bfill.teal {{ background: var(--teal); }}
  .bfill.grayb {{ background: #9ca3af; }}
  .bval {{ font-size: 11px; color: var(--ink); }}
  .bspace {{ font-size: 10px; color: var(--gray); font-style: italic; }}
  details.qa {{ background: #fff; border: 1px solid var(--line); border-radius: 8px;
               margin: 10px 0; padding: 10px 16px; }}
  details.qa summary {{ cursor: pointer; font-weight: 600; font-size: 14px; }}
  .q {{ margin: 10px 0; padding: 10px 14px; background: var(--graybg);
       border-radius: 6px; font-size: 13px; }}
  .answer {{ margin: 10px 0; }}
  .answer h4 {{ margin: 0 0 6px; font-size: 12.5px; }}
  .answer pre {{ white-space: pre-wrap; word-wrap: break-word; font-size: 12.5px;
                margin: 0; padding: 12px 14px; border-radius: 6px;
                font-family: inherit; line-height: 1.55; }}
  .a-track h4 {{ color: var(--teal); }}
  .a-track pre {{ background: var(--tealbg); border: 1px solid #99f6e4; }}
  .b-track pre, .c-track pre {{ background: var(--graybg); border: 1px solid var(--line); }}
  .b-track h4, .c-track h4 {{ color: var(--gray); }}
  footer {{ padding: 20px 40px; color: var(--gray); font-size: 12px; }}
  .legend span {{ display: inline-block; padding: 2px 10px; border-radius: 4px;
                 font-size: 12px; margin-right: 10px; }}
  .legend .t {{ background: var(--tealbg); color: var(--teal); }}
  .legend .g {{ background: var(--graybg); color: var(--gray); }}
  .legend .w {{ background: var(--warnbg); color: var(--warn); }}
</style></head><body>
<header>
  <h1>Three-Track Benchmark — Visual Report</h1>
  <p>QDCVR platform KB retrieval vs bare agent vs dense RAG reproduction ·
     50 real papers · 10 English questions · generated {esc(now)}</p>
</header>
<main>
  <h2>1 · Pipeline execution &amp; corpus coverage</h2>
  <div class="cards">{card_html}</div>

  <h2>2 · Retrieval regression — 10 questions, `kb_search_vector` over 5 category KBs</h2>
  <table><thead><tr><th>QID</th><th>Field</th><th>Gold doc in top-3</th>
  <th>Gold keywords echoed</th><th>Top KB</th><th>Verdict</th></tr></thead>
  <tbody>{bench_rows}</tbody></table>

  <h2>3 · Three-track latency per question (seconds)</h2>
  <p class="legend"><span class="t">teal = Track A · platform system</span>
  <span class="g">gray = Track B/C · baselines</span>
  <span class="w">orange-red = failed/warn</span></p>
  <p style="font-size:12px;color:{'var(--gray)'}">Track A bars measure the scripted
  retrieval pipeline only (query rewrite → vector search → content-gate reads
  [+ librarian fallback]); answer composition is done by the executing agent and is
  not part of the bar. Averages — A: {a_avg}s · B: {b_avg}s · C: {c_avg}s.</p>
  {lat_rows}

  <h2>4 · Per-question verbatim answers (all three systems, full text)</h2>
  {qa_html}
</main>
<footer>Raw records: ingest_survey.json · ingest_report.json · tags_report.json ·
repro_ingest.json · repro_coverage.json · bench10_qa.json ·
skill_track_evidence.json · skill_track_answers.json · track_bc.json ·
full markdown transcript: skill_threeway_replication.md</footer>
</body></html>"""
    out = RESULTS / "benchmark_visual_report.html"
    out.write_text(page, encoding="utf-8")
    print(f"[done] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
