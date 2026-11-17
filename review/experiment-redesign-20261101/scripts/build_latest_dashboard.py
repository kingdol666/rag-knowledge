# -*- coding: utf-8 -*-
"""Build a self-contained HTML audit of the frozen and R3 HMRS runs.

Run from outside the artifact directories with: python -I -B <this file>.
The script reads only the two named JSON traces/statistics files and writes the
HTML dashboard to the named output path.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
BASE = ROOT / "review" / "experiment-redesign-20261101" / "artifacts"
FROZEN_TRACE = BASE / "final_bench" / "s4_traces_final.json"
R3_TRACE = BASE / "replication_bench_20261112" / "s4_traces_r3_statsready.json"
FROZEN_STATS = BASE / "final_bench" / "s6_stats.json"
R3_STATS = BASE / "replication_bench_20261112" / "s6_stats.json"
OUT = BASE / "replication_bench_20261112" / "latest_experiment_dashboard.html"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def gold_rows(trace: dict, arm: str):
    return [r for r in trace.get(arm, []) if not r.get("is_refusal")]


def summarize(trace: dict, stats: dict, arm: str):
    rows = gold_rows(trace, arm)
    st = stats.get("per_arm", {}).get(arm, {})
    return {
        "arm": arm,
        "n": len(rows),
        "hits": sum(bool(r.get("gold_hit")) for r in rows),
        "rate": (sum(bool(r.get("gold_hit")) for r in rows) / len(rows)) if rows else None,
        "route_hits": sum(bool(r.get("route_correct")) for r in rows if "route_correct" in r),
        "route_n": sum("route_correct" in r for r in rows),
        "bytes": st.get("avg_bytes_gold"),
        "seconds": st.get("avg_tool_s_gold"),
        "calls": sum((r.get("calls") or 0) for r in rows) if rows else None,
        "stats_p": stats.get("paired_mcnemar_vs_baseline", {}).get(arm, {}).get("p_exact_two_sided"),
    }


def pct(v):
    return "—" if v is None else f"{100*v:.1f}%"


def num(v):
    return "—" if v is None else f"{v:,.1f}"


def bar(v, maxv=1.0, cls="blue"):
    width = 0 if v is None else max(0, min(100, v / maxv * 100))
    return f'<span class="bar {cls}"><i style="width:{width:.1f}%"></i></span>'


def make():
    frozen_trace = load(FROZEN_TRACE)
    r3_trace = load(R3_TRACE)
    frozen_stats = load(FROZEN_STATS)
    r3_stats = load(R3_STATS)
    arms = ["A0", "A0f", "A0h", "PD", "A1b", "A2", "A3"]
    labels = {
        "A0": "Tiered baseline",
        "A0f": "Tiered + full window",
        "A0h": "Tiered + chunk union",
        "PD": "Precise, no navigation",
        "A1b": "Ten-library scoped union",
        "A2": "Tiered, no evidence gate",
        "A3": "Name-only route cards",
    }
    frozen = {a: summarize(frozen_trace, frozen_stats, a) for a in arms}
    r3 = {a: summarize(r3_trace, r3_stats, a) for a in arms}
    readall_frozen = summarize(frozen_trace, frozen_stats, "A1-readall")
    readall_r3 = summarize(r3_trace, r3_stats, "A1-readall")
    data = {"frozen": frozen, "r3": r3, "labels": labels,
            "readall_frozen": readall_frozen, "readall_r3": readall_r3}

    rows = []
    for arm in arms:
        f, r = frozen[arm], r3[arm]
        delta = None if r["rate"] is None else (r["rate"] - f["rate"]) * 100
        p = r["stats_p"]
        ptxt = "—" if p is None else ("<0.001" if p < .001 else f"{p:.4f}")
        status = "stable" if delta is not None and abs(delta) <= 2.8 else "sensitive"
        if arm == "A3":
            status = "route-card-sensitive"
        rows.append(
            "<tr>"
            f"<th>{html.escape(arm)}<small>{html.escape(labels[arm])}</small></th>"
            f"<td>{f['hits']}/{f['n']}<br><b>{pct(f['rate'])}</b></td>"
            f"<td>{r['hits']}/{r['n']}<br><b>{pct(r['rate'])}</b></td>"
            f"<td class=\"{'positive' if delta is not None and delta > 0 else 'negative' if delta is not None and delta < 0 else ''}\">{('+' if delta is not None and delta > 0 else '') if delta is not None else ''}{'—' if delta is None else f'{delta:.1f} pp'}</td>"
            f"<td>{ptxt}</td><td><span class=\"status {status}\">{status}</span></td></tr>"
        )

    metric_cards = []
    for arm in ["A0", "A0f", "A0h", "PD", "A1b", "A2"]:
        f, r = frozen[arm], r3[arm]
        metric_cards.append(
            f"<article class='metric'><h3>{html.escape(arm)} <small>{html.escape(labels[arm])}</small></h3>"
            f"<div class='metric-row'><span>Frozen</span><strong>{f['hits']}/{f['n']} · {pct(f['rate'])}</strong>{bar(f['rate'],1.0,'blue')}</div>"
            f"<div class='metric-row'><span>R3</span><strong>{r['hits']}/{r['n']} · {pct(r['rate'])}</strong>{bar(r['rate'],1.0,'orange')}</div>"
            f"<div class='metric-foot'>R3 bytes/q {num(r['bytes'])} · tool {num(r['seconds'])} s</div></article>"
        )

    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HMRS latest experiment audit</title>
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#dbe3ef;--bg:#f7f9fc;--blue:#2563eb;--orange:#f59e0b;--green:#087f5b;--red:#b42318}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}}main{{max-width:1240px;margin:0 auto;padding:38px 28px 60px}}h1{{font-size:34px;letter-spacing:-.03em;margin:0 0 8px}}h2{{font-size:22px;margin:34px 0 12px}}h3{{margin:0 0 12px;font-size:17px}}p{{max-width:930px}}.sub{{color:var(--muted);margin:0 0 22px}}.notice{{background:#fff8e6;border:1px solid #f3d28b;border-radius:14px;padding:16px 18px;margin:18px 0;color:#6b4a00}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}.metric,.panel{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:17px;box-shadow:0 3px 14px #1c3b6410}}.metric h3 small,th small{{display:block;color:var(--muted);font-weight:500;font-size:12px}}.metric-row{{display:grid;grid-template-columns:58px 1fr;gap:4px 10px;align-items:center;margin:9px 0}}.metric-row span{{color:var(--muted);font-size:12px}}.metric-row strong{{font-size:15px}}.bar{{grid-column:1/3;display:block;height:8px;border-radius:99px;background:#edf1f7;overflow:hidden}}.bar i{{display:block;height:100%;border-radius:99px}}.bar.blue i{{background:var(--blue)}}.bar.orange i{{background:var(--orange)}}.metric-foot{{border-top:1px solid #eef2f7;margin-top:12px;padding-top:10px;color:var(--muted);font-size:12px}}.table-wrap{{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:14px}}table{{width:100%;border-collapse:collapse;min-width:760px}}th,td{{padding:13px 14px;border-bottom:1px solid #eef2f7;text-align:left;vertical-align:middle}}thead th{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);background:#fbfcfe}}tbody tr:last-child th,tbody tr:last-child td{{border-bottom:0}}td b{{font-size:17px}}.positive{{color:var(--green);font-weight:700}}.negative{{color:#9a3412;font-weight:700}}.status{{font-size:11px;padding:4px 8px;border-radius:99px;font-weight:700;white-space:nowrap}}.status.stable{{background:#e7f7f0;color:var(--green)}}.status.sensitive,.status.route-card-sensitive{{background:#fff0e0;color:#9a3412}}.callout{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.callout .panel strong{{font-size:28px;display:block;margin:4px 0}}.blue-text{{color:var(--blue)}}.orange-text{{color:#b45309}}ul{{margin:8px 0 0 20px;padding:0}}code{{background:#eef2ff;border-radius:5px;padding:2px 5px}}footer{{margin-top:34px;color:var(--muted);font-size:12px}}@media(max-width:850px){{main{{padding:24px 14px}}.grid{{grid-template-columns:1fr 1fr}}.callout{{grid-template-columns:1fr}}}}@media(max-width:560px){{.grid{{grid-template-columns:1fr}}h1{{font-size:28px}}}}
</style></head><body><main>
<h1>HMRS experiment audit: frozen final vs R3</h1>
<p class="sub">Latest complete replication evidence from the frozen 2026-11-11 bench and the independent 2026-11-12 R3 run. Gold-string containment is a retrieval proxy, not semantic answer accuracy.</p>
<div class="notice"><b>Interpretation.</b> The latest complete R3 run supports the tiered chunk-window arm A0h as the best-performing complete arm: 51/72 (70.8%), above PD 45/72 (62.5%), A0f 44/72 (61.1%), A1b 39/72 (54.2%), A0 39/72 (54.2%) and A2 25/72 (34.7%). The R3 read-all arm is incomplete (3/76 rows), so it is not a latest-run comparator.</div>
<h2>Headline comparison</h2><div class="callout"><div class="panel"><span class="blue-text">Frozen A0h</span><strong>52/72 · 72.2%</strong><div>Exact paired comparison vs frozen A0: p = 0.000061.</div></div><div class="panel"><span class="orange-text">R3 A0h</span><strong>51/72 · 70.8%</strong><div>Exact paired comparison vs R3 A0: p = 0.000488.</div></div></div>
<h2>Arm-by-arm gold containment</h2><div class="table-wrap"><table><thead><tr><th>Arm</th><th>Frozen final</th><th>R3 latest complete</th><th>Change</th><th>R3 p vs A0</th><th>Stability</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Configuration details and cost</h2><div class="grid">{''.join(metric_cards)}</div>
<h2>Read-all is an upper-bound diagnostic</h2><div class="panel"><p><b>Frozen read-all:</b> 72/72 gold strings, 64,584 calls total, 897 calls/question, 24.3 MB/question, 253.7 s/question. It is a mechanical substring scan over 879 parts and generated no answers.</p><p><b>R3 read-all:</b> only 3 completed rows at the time of the frozen R3 report, all 3/3 hits, with the corpus expanded to 906 parts and about 25.5 MB/question. It must not replace the frozen read-all value until a complete run exists.</p></div>
<h2>What the evidence supports</h2><div class="panel"><ul><li><b>Supported:</b> A0h's latest complete R3 containment is highest among the complete tested content-layer arms, and its advantage over R3 A0 is statistically detectable in an exploratory paired test.</li><li><b>Supported:</b> A0h, PD and A0f reproduce their ordering and remain within 1.4 percentage points of frozen values.</li><li><b>Not supported:</b> a semantic answer-accuracy claim, a causal hierarchy claim isolated from all other components, or a comparison of A0h against a completed latest read-all run.</li><li><b>A3 caveat:</b> name-only route-card containment is numerically sensitive to route-card index health; use the stable qualitative conclusion that removing descriptions makes routing unreliable, not one A3 percentage as a universal constant.</li></ul></div>
<h2>Provenance</h2><div class="panel"><p>Frozen traces: <code>artifacts/final_bench/s4_traces_final.json</code>. Frozen statistics: <code>artifacts/final_bench/s6_stats.json</code>. R3 traces: <code>artifacts/replication_bench_20261112/s4_traces_r3_statsready.json</code>. R3 statistics: <code>artifacts/replication_bench_20261112/s6_stats.json</code>. Results narrative: <code>RESULTS-REPLICATION-20261112.md</code>.</p></div>
<footer>Generated from the named JSON artifacts without re-estimating or inventing missing R3 read-all rows.</footer>
<script>window.HMRS_AUDIT_DATA={json.dumps(data, ensure_ascii=False)};</script></main></body></html>"""
    OUT.write_text(html_doc, encoding="utf-8", newline="\n")
    print(OUT)


if __name__ == "__main__":
    make()
