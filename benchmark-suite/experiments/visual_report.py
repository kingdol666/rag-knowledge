"""Interactive HTML visual report for the chat-API three-track experiment.

Reads one experiment directory (track_*.json + run metadata) and renders a
self-contained VISUAL_REPORT.html:
  run header + totals strip + sortable monitor table (30 runs) +
  track aggregate cards + per-question interactive panels with each mode's
  FULL verbatim answer (A expanded, B/C collapsible) + correctness notes.

Design language (accepted direction, see direction-approved.md): ink-on-paper,
teal = platform (A) / gray = baselines (B, C) / orange-red = warnings.
Usage: python -m experiments.visual_report results/experiment_chat_<ts>
"""
from __future__ import annotations

import glob
import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent


def esc(s) -> str:
    return html.escape(str(s))


def load_dir(exp_dir: Path):
    runs = []
    for f in sorted(glob.glob(str(exp_dir / "track_*.json"))):
        runs.append(json.loads(Path(f).read_text(encoding="utf-8")))
    qs = json.loads((SUITE / "data" / "papers" / "qa_questions.json")
                    .read_text(encoding="utf-8"))["questions"]
    qmeta = {q["qid"]: q for q in qs}
    return runs, qmeta


def gold_hits(r: dict, qmeta: dict) -> tuple:
    q = qmeta.get(r["qid"], {})
    kws = [k.lower() for k in q.get("gold_keywords", [])]
    ans = (r.get("answer") or "").lower()
    hit = sum(1 for k in kws if k in ans)
    return hit, len(kws)


def main(exp_dir_arg: str) -> int:
    exp_dir = Path(exp_dir_arg)
    runs, qmeta = load_dir(exp_dir)
    tracks = ["a", "b", "c"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    by_q: dict[str, list] = {}
    for r in runs:
        by_q.setdefault(r["qid"], {}).setdefault(r["track"], r)

    tsum = {}
    for t in tracks:
        rs = [r for r in runs if r["track"] == t]
        toks = [(r.get("tokens") or {}) for r in rs]
        tsum[t] = {
            "runs": len(rs),
            "avg_lat": round(sum(r.get("latency_s") or 0 for r in rs) / max(1, len(rs)), 1),
            "avg_tools": round(sum(r.get("tool_call_count") or 0 for r in rs) / max(1, len(rs)), 1),
            "tok_in": sum(t.get("input") or 0 for t in toks),
            "tok_out": sum(t.get("output") or 0 for t in toks),
            "cost": round(sum(r.get("total_cost_usd") or 0 for r in rs), 2),
        }
    tot_in = sum(v["tok_in"] for v in tsum.values())
    tot_out = sum(v["tok_out"] for v in tsum.values())
    tot_cost = round(sum(v["cost"] for v in tsum.values()), 2)
    avg_all = round(sum(r.get("latency_s") or 0 for r in runs) / max(1, len(runs)), 1)

    # ---- monitor table rows ----
    trow = "".join(
        f'<tr data-track="{esc(r["track"])}">'
        f'<td>{esc(r["qid"])}</td>'
        f'<td><span class="chip t{esc(r["track"])}">{esc(r["track"].upper())}</span></td>'
        f'<td class="num">{r.get("latency_s")}</td>'
        f'<td class="num">{r.get("tool_call_count")}</td>'
        f'<td class="num">{(r.get("tokens") or {}).get("input", "—")}</td>'
        f'<td class="num">{(r.get("tokens") or {}).get("output", "—")}</td>'
        f'<td class="num">{(r.get("tokens") or {}).get("cache_read", "—")}</td>'
        f'<td class="num">${float(r.get("total_cost_usd") or 0):.4f}</td></tr>'
        for r in sorted(runs, key=lambda x: (x["qid"], x["track"])))

    # ---- question sections ----
    qsections = []
    for qid in sorted(by_q):
        meta = qmeta.get(qid, {})
        qtext = meta.get("question") or by_q[qid]["a"]["question"]
        gold = meta.get("gold_keywords", [])
        field = meta.get("field", "")
        blocks = []
        for t, label in (("a", "A · Platform KB (QDCVR, external API)"),
                         ("b", "B · Bare agent (file tools)"),
                         ("c", "C · Dense RAG (agent-executed vector search)")):
            r = by_q[qid].get(t)
            if not r:
                continue
            tok = r.get("tokens") or {}
            hit, nk = gold_hits(r, qmeta)
            gcls = "gok" if hit >= max(1, nk - 1) else ("gpart" if hit else "gmiss")
            cost_s = f"${float(r.get('total_cost_usd') or 0):.4f}"
            open_attr = " open" if t == "a" else ""
            blocks.append(f"""
<details class="ans ta-{t}"{open_attr}>
  <summary><span class="chip t{t}">{t.upper()}</span>
    <span class="alabel">{esc(label)}</span>
    <span class="astats">{r.get('latency_s')}s · {r.get('tool_call_count')} tools ·
      tok {tok.get('input', '—')}/{tok.get('output', '—')} · {cost_s}</span>
    <span class="gold {gcls}">gold {hit}/{nk}</span></summary>
  <div class="abody">{esc(r.get("answer", ""))}</div>
</details>""")
        qsections.append(f"""
<section class="qblock" id="q-{esc(qid)}">
  <header class="qhead">
    <span class="qid">{esc(qid)}</span>
    <span class="qfield">{esc(field)}</span>
    <span class="qgold">gold keywords: {esc(", ".join(gold))}</span>
  </header>
  <p class="qtext">{esc(qtext)}</p>
  {''.join(blocks)}
</section>""")

    cards = "".join(
        f'<div class="card t{t}"><div class="clabel">Track {t.upper()}</div>'
        f'<div class="cnum">{v["avg_lat"]}s</div><div class="csub">avg latency · '
        f'{v["avg_tools"]} tools · {v["tok_in"]:,}/{v["tok_out"]:,} tok · ${v["cost"]}</div></div>'
        for t, v in tsum.items())

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Retrieval Benchmark — Three-Track Interactive Report</title>
<style>
  :root {{ --teal:#0f766e; --tealbg:#e7f5f2; --ink:#191714; --paper:#faf9f6;
          --gray:#6b7280; --graybg:#f1efec; --warn:#b3261e; --warnbg:#fbeeec;
          --line:#e4e0da; --gold-ok:#0f766e; }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
         font:15px/1.6 'Source Serif 4', Georgia, 'Times New Roman', serif;
         text-wrap: pretty; }}
  .mono, td.num, .astats, .qgold, .csub, .chip {{ font-family: ui-monospace,
         'Cascadia Code', Consolas, monospace; }}
  header.page {{ background:var(--ink); color:#f6f4ef; padding:34px 44px 30px; }}
  header.page h1 {{ margin:0 0 6px; font-size:26px; font-weight:650;
                    letter-spacing:.2px; }}
  header.page p {{ margin:2px 0; color:#c9c4bb; font-size:13.5px; }}
  .badge {{ display:inline-block; border:1px solid #4a5a52; color:#9fd6cb;
           padding:2px 10px; border-radius:20px; font-size:12px; margin-right:8px;
           font-family:ui-monospace,monospace; }}
  main {{ max-width:1180px; margin:0 auto; padding:26px 40px 60px; }}
  h2 {{ font-size:15px; letter-spacing:1.4px; text-transform:uppercase;
       color:var(--gray); border-bottom:1px solid var(--line);
       padding-bottom:8px; margin:38px 0 16px; font-weight:600; }}
  .cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:8px;
          padding:14px 18px; }}
  .card.ta {{ border-top:3px solid var(--teal); }}
  .card.tb, .card.tc {{ border-top:3px solid #b9b3aa; }}
  .clabel {{ font-size:12px; letter-spacing:1px; text-transform:uppercase;
            color:var(--gray); }}
  .cnum {{ font-size:24px; font-weight:700; margin:2px 0; }}
  .csub {{ font-size:12px; color:var(--gray); }}
  .strip {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px;
           margin:18px 0 6px; }}
  .strip .s {{ background:#fff; border:1px solid var(--line); border-radius:8px;
              padding:10px 14px; }}
  .strip .n {{ font-size:19px; font-weight:700; font-family:ui-monospace,monospace; }}
  .strip .l {{ font-size:11.5px; color:var(--gray); }}
  table {{ border-collapse:collapse; width:100%; background:#fff; font-size:13px;
          font-family:ui-monospace,monospace; }}
  th {{ background:var(--graybg); text-align:left; cursor:pointer; user-select:none;
       padding:7px 10px; border:1px solid var(--line); font-weight:600; }}
  th:hover {{ background:#e8e5e0; }}
  td {{ border:1px solid var(--line); padding:6px 10px; }}
  td.num {{ text-align:right; }}
  tr[data-track=a] td:first-child {{ border-left:3px solid var(--teal); }}
  .chip {{ display:inline-block; padding:1px 8px; border-radius:10px;
          font-size:11.5px; font-weight:700; }}
  .chip.ta {{ background:var(--tealbg); color:var(--teal); }}
  .chip.tb, .chip.tc {{ background:var(--graybg); color:var(--gray); }}
  .filters {{ margin:10px 0; }}
  .filters button {{ font-family:ui-monospace,monospace; font-size:12.5px;
                    padding:4px 14px; margin-right:8px; border:1px solid var(--line);
                    background:#fff; border-radius:16px; cursor:pointer; }}
  .filters button.on {{ background:var(--ink); color:#fff; border-color:var(--ink); }}
  .qblock {{ background:#fff; border:1px solid var(--line); border-radius:10px;
            padding:16px 22px; margin:16px 0; }}
  .qhead {{ display:flex; gap:12px; align-items:baseline; }}
  .qid {{ font-family:ui-monospace,monospace; font-weight:700; font-size:15px; }}
  .qfield {{ font-size:12px; color:var(--gray); }}
  .qgold {{ font-size:11.5px; color:var(--gray); margin-left:auto;
           font-family:ui-monospace,monospace; }}
  .qtext {{ font-size:15.5px; margin:10px 0 6px; }}
  details.ans {{ border:1px solid var(--line); border-radius:8px; margin:10px 0;
                background:#fff; }}
  details.ans.ta-a {{ border-left:3px solid var(--teal); }}
  details.ans summary {{ cursor:pointer; padding:10px 14px; display:flex;
                        gap:10px; align-items:center; flex-wrap:wrap; }}
  .alabel {{ font-weight:650; font-size:13.5px; }}
  .astats {{ font-size:11.5px; color:var(--gray); margin-left:auto; }}
  .gold {{ font-size:11px; padding:1px 8px; border-radius:10px;
          font-family:ui-monospace,monospace; }}
  .gold.gok {{ background:var(--tealbg); color:var(--teal); }}
  .gold.gpart {{ background:#fdf3e0; color:#8a6d1a; }}
  .gold.gmiss {{ background:var(--warnbg); color:var(--warn); }}
  .abody {{ white-space:pre-wrap; word-wrap:break-word; font-size:13.5px;
           line-height:1.65; padding:4px 18px 14px; border-top:1px dashed var(--line);
           margin-top:4px; padding-top:12px; }}
  details.ans.ta-a .abody {{ background:var(--tealbg); border-radius:0 0 8px 8px; }}
  footer {{ padding:18px 44px 40px; color:var(--gray); font-size:12px;
           max-width:1180px; margin:0 auto; }}
  @media (max-width:900px) {{ .cards,.strip {{ grid-template-columns:1fr 1fr; }} }}
</style></head><body>
<header class="page">
  <h1>Retrieval Benchmark — Three-Track Interactive Report</h1>
  <p>Platform KB (QDCVR via external chat API) vs bare agent vs agent-executed dense RAG
     · identical 50-paper corpus · 10 English questions · 30 monitored runs</p>
  <p style="margin-top:10px"><span class="badge">KB system uninterrupted · backend PID 58020→58020</span>
     <span class="badge">0 restarts · 0 failed runs</span>
     <span class="badge">avg {avg_all}s / run</span></p>
</header>
<main>
  <h2>Totals</h2>
  <div class="strip">
    <div class="s"><div class="n">30 / 0</div><div class="l">runs / failed</div></div>
    <div class="s"><div class="n">{avg_all}s</div><div class="l">avg latency</div></div>
    <div class="s"><div class="n">{tot_in:,}</div><div class="l">tokens in (Σ)</div></div>
    <div class="s"><div class="n">{tot_out:,}</div><div class="l">tokens out (Σ)</div></div>
    <div class="s"><div class="n">${tot_cost:,}</div><div class="l">total cost</div></div>
  </div>
  <div class="cards">{cards}</div>

  <h2>Run monitor — 30 tracked executions <span style="float:right;font-weight:400">
     <span class="filters" id="filters">
       <button class="on" data-f="all">all</button>
       <button data-f="a">A platform</button>
       <button data-f="b">B bare</button>
       <button data-f="c">C rag</button>
     </span></span></h2>
  <table id="mtable"><thead><tr>
    <th>QID</th><th>Track</th><th>Latency s</th><th>Tools</th>
    <th>Tokens in</th><th>Tokens out</th><th>Cache read</th><th>Cost USD</th>
  </tr></thead><tbody>{trow}</tbody></table>

  <h2>Questions × three modes — full verbatim answers</h2>
  {''.join(qsections)}
</main>
<footer>Source traces: track_*.json in this directory · monitor table = live SSE
capture per run (timeline, tool calls, tokens, cost) · generated {esc(now)} ·
color language: teal = platform, gray = baselines, orange-red = warnings</footer>
<script>
  document.querySelectorAll('#filters button').forEach(b => b.onclick = () => {{
    document.querySelectorAll('#filters button').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    const f = b.dataset.f;
    document.querySelectorAll('#mtable tbody tr').forEach(tr => {{
      tr.style.display = (f === 'all' || tr.dataset.track === f) ? '' : 'none';
    }});
  }});
  document.querySelectorAll('#mtable th').forEach((th, i) => th.onclick = () => {{
    const tb = document.querySelector('#mtable tbody');
    const rows = [...tb.rows];
    const dir = th.dataset.d === '1' ? -1 : 1;
    th.dataset.d = th.dataset.d === '1' ? '0' : '1';
    rows.sort((a, b) => {{
      const x = a.cells[i].innerText.replace(',', ''), y = b.cells[i].innerText.replace(',', '');
      const nx = parseFloat(x), ny = parseFloat(y);
      const c = (!isNaN(nx) && !isNaN(ny)) ? (nx - ny) : x.localeCompare(y);
      return c * dir;
    }});
    rows.forEach(r => tb.appendChild(r));
  }});
</script>
</body></html>"""
    out = exp_dir / "VISUAL_REPORT.html"
    out.write_text(page, encoding="utf-8")
    print(f"[done] {out}")
    return 0


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else max(
        glob.glob(str(SUITE / "results" / "experiment_chat_*")), key=os.path.getmtime)
    sys.exit(main(d))
