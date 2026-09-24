"""Render a run directory into a single-file HTML comparison dashboard.

Reads the same `monitor.json` that `compare_report.py` produces and emits a
self-contained `COMPARE.html` — no CDN, no build step, opens offline.

Sections: header + provenance chips · KPI cards · resource-monitoring table
(sortable) · functional-verification bars · per-question side-by-side panels
(filterable) · consistency self-checks. Light theme by default with a dark
toggle; project arms are teal, baselines slate, warnings amber.

Usage
  python -m experiments.compare_html --run results/runs/<run_id>
  python -m experiments.compare_html --run <dir> --questions data/papers/qa_v2.json
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(SUITE / "scripts"))

PROJECT_ARMS = {"a", "a2", "b", "c"}


def _e(x) -> str:
    return html.escape(str(x if x is not None else "—"))


def _is_project(m: str) -> bool:
    return m in PROJECT_ARMS


def _bar(rate: float | None, color: str) -> str:
    if rate is None:
        return '<span class="muted">—</span>'
    pct = max(0.0, min(1.0, float(rate))) * 100
    return (f'<div class="bar"><span style="width:{pct:.0f}%;background:{color}"></span>'
            f'<em>{pct:.0f}%</em></div>')


def render(payload: dict) -> str:
    manifest = payload.get("manifest") or {}
    methods = payload.get("methods") or []
    pm = payload.get("per_method") or {}
    per_q = payload.get("per_question") or {}
    checks = payload.get("self_checks") or []
    dry = bool(manifest.get("dry_run"))

    n_q = len(per_q)
    total_cost = sum((pm[m] or {}).get("cost_usd_total") or 0 for m in methods)
    lats = [(pm[m] or {}).get("latency_avg_s") or 0 for m in methods]
    avg_lat = round(sum(lats) / len(lats), 1) if lats else 0
    n_bad = sum(1 for c in checks if not c.get("ok"))

    # ── KPI cards ────────────────────────────────────────────────────────────
    kpis = [
        ("方法数", len(methods), "项目 + baseline"),
        ("问题数", n_q, "同一问题集"),
        ("总成本", f"${total_cost:.2f}", "全部方法合计"),
        ("平均时延", f"{avg_lat}s", "跨方法均值"),
        ("自检", f"{len(checks) - n_bad}/{len(checks)}",
         "全部通过" if n_bad == 0 else f"{n_bad} 项未通过"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-v">{_e(v)}</div>'
        f'<div class="kpi-k">{_e(k)}</div><div class="kpi-s">{_e(s)}</div></div>'
        for k, v, s in kpis)

    # ── monitoring table ─────────────────────────────────────────────────────
    rows = []
    for m in methods:
        a = pm.get(m) or {}
        sp = a.get("system_peak") or {}
        kind = ("项目" if _is_project(m) else "baseline")
        rows.append(
            f'<tr class="{"proj" if _is_project(m) else "base"}">'
            f'<td><span class="pill {"p-proj" if _is_project(m) else "p-base"}">{kind}</span> '
            f'<code>{_e(m)}</code></td>'
            f'<td data-v="{a.get("latency_avg_s") or 0}">{_e(a.get("latency_avg_s"))}</td>'
            f'<td data-v="{a.get("latency_median_s") or 0}">{_e(a.get("latency_median_s"))}</td>'
            f'<td data-v="{a.get("tokens_in_total") or 0}">{_e(a.get("tokens_in_total"))}</td>'
            f'<td data-v="{a.get("tokens_out_total") or 0}">{_e(a.get("tokens_out_total"))}</td>'
            f'<td data-v="{a.get("cost_usd_total") or 0}">{_e(a.get("cost_usd_total"))}</td>'
            f'<td data-v="{a.get("tools_avg") or 0}">{_e(a.get("tools_avg"))}</td>'
            f'<td data-v="{sp.get("cpu_pct_peak") or 0}">{_e(sp.get("cpu_pct_peak", "—"))}</td>'
            f'<td data-v="{sp.get("rss_mb_peak") or 0}">{_e(sp.get("rss_mb_peak", "—"))}</td>'
            f'</tr>')
    mon_table = "".join(rows)

    # ── functional verification ──────────────────────────────────────────────
    vrows = []
    for m in methods:
        a = pm.get(m) or {}
        vrows.append(
            f'<tr><td><code>{_e(m)}</code></td>'
            f'<td>{_bar(a.get("retrieval_gold_rate"), "#0F6E56" if _is_project(m) else "#888780")}</td>'
            f'<td>{_bar(a.get("citation_gold_rate"), "#0F6E56" if _is_project(m) else "#888780")}</td>'
            f'<td data-v="{a.get("abstentions") or 0}">{_e(a.get("abstentions"))}</td>'
            f'<td data-v="{a.get("errors") or 0}">{_e(a.get("errors"))}</td></tr>')
    verif_table = "".join(vrows)

    # ── per-question panels ──────────────────────────────────────────────────
    panels = []
    for qid in sorted(per_q, key=lambda x: (len(x), x)):
        cells = per_q[qid]
        blocks = []
        for m in methods:
            c = cells.get(m)
            if not c:
                continue
            rh = c.get("retrieval_hit")
            ch = c.get("citation_hit")
            def mark(v):
                return ('<span class="ok">✓</span>' if v is True else
                        '<span class="no">✗</span>' if v is False else
                        '<span class="muted">—</span>')
            blocks.append(
                f'<article class="cell {"proj" if _is_project(m) else "base"}">'
                f'<header><span class="pill {"p-proj" if _is_project(m) else "p-base"}>'
                f'{"项目" if _is_project(m) else "baseline"}</span> <code>{_e(m)}</code>'
                f'<span class="cell-meta">检索 {mark(rh)} · 引用 {mark(ch)} · '
                f'{_e(c.get("latency_s"))}s · {_e(c.get("cost_usd"))}$ · '
                f'工具 {_e(c.get("tools"))}</span></header>'
                f'<p>{_e(c.get("answer")) or "(空)"}</p></article>')
        panels.append(
            f'<section class="qcard" data-q="{_e(qid)}">'
            f'<h3>{_e(qid)}</h3>'
            f'<div class="cells">{"".join(blocks)}</div></section>')
    panels_html = "".join(panels) or '<p class="muted">无逐题数据</p>'

    # ── self checks ──────────────────────────────────────────────────────────
    chk = "".join(
        f'<li class="{"ok" if c.get("ok") else "no"}">'
        f'<b>{"✓" if c.get("ok") else "✗"}</b> {_e(c.get("check"))}'
        f'<span class="muted"> — {_e(c.get("detail"))}</span></li>' for c in checks)

    prov = " ".join(f'<span class="chip">{_e(k)}: <b>{_e(v)}</b></span>'
                    for k, v in manifest.items()
                    if k in ("git_commit", "config_hash", "prompt_version", "seed",
                             "max_turns", "shuffled", "monitor_system"))

    banner = ('<div class="banner">⚠️ DRY-RUN 数据 — 未调用任何 API，'
              '仅供管线连通性检查，<b>不得作为实验结果</b>。</div>' if dry else "")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>对照实验报告 — {_e(payload.get('run'))}</title>
<style>
:root{{--bg:#FBFAF7;--card:#FFFFFF;--bd:#E7E4DC;--tx:#2C2C2A;--mu:#6B6862;
--proj:#0F6E56;--projbg:#E1F5EE;--base:#5F5E5A;--basebg:#F1EFE8;--warn:#BA7517;
--gold:#9E7A38;--ok:#3B6D11;--no:#A32D2D}}
html[data-t=dark]{{--bg:#1B1B19;--card:#242422;--bd:#3A3A36;--tx:#EDEBE4;--mu:#A5A29A;
--projbg:#0B3B30;--basebg:#2E2E2B;--proj:#5DCAA5;--base:#B4B2A9}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);
font:15px/1.6 system-ui,-apple-system,"Segoe UI","Noto Sans SC",Roboto,sans-serif}}
.wrap{{max-width:1120px;margin:0 auto;padding:32px 20px 80px}}
header.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}}
h1{{font-size:24px;font-weight:600;margin:0 0 6px}}
.sub{{color:var(--mu);font-size:13px}}
.chip{{display:inline-block;background:var(--card);border:1px solid var(--bd);
border-radius:999px;padding:3px 10px;font-size:12px;color:var(--mu);margin:4px 6px 0 0}}
.chip b{{color:var(--tx);font-weight:600}}
button.toggle{{background:var(--card);border:1px solid var(--bd);color:var(--tx);
border-radius:10px;padding:8px 14px;cursor:pointer;font-size:13px}}
.banner{{margin:18px 0;padding:12px 16px;border-radius:12px;background:#FAEEDA;
border:1px solid #FAC775;color:#633806;font-size:13px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}}
.kpi{{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:16px}}
.kpi-v{{font-size:26px;font-weight:600;letter-spacing:-.02em}}
.kpi-k{{font-size:13px;color:var(--tx);margin-top:2px}}
.kpi-s{{font-size:12px;color:var(--mu);margin-top:2px}}
section.blk{{margin:34px 0}}
h2{{font-size:17px;font-weight:600;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid var(--bd)}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--bd);
border-radius:14px;overflow:hidden;font-size:13.5px}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--bd)}}
th{{font-weight:600;color:var(--mu);font-size:12.5px;cursor:pointer;user-select:none;white-space:nowrap}}
th:hover{{color:var(--tx)}}
tbody tr:last-child td{{border-bottom:0}}
tbody tr:hover{{background:var(--projbg)}}
td[data-v]{{font-variant-numeric:tabular-nums}}
code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}}
.pill{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;margin-right:6px}}
.p-proj{{background:var(--projbg);color:var(--proj)}}
.p-base{{background:var(--basebg);color:var(--base)}}
.bar{{position:relative;background:var(--basebg);border-radius:999px;height:18px;min-width:110px}}
.bar span{{display:block;height:100%;border-radius:999px}}
.bar em{{position:absolute;right:8px;top:0;font-size:11px;line-height:18px;font-style:normal;color:var(--tx)}}
.qcard{{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:18px;margin-bottom:16px}}
.qcard h3{{margin:0 0 14px;font-size:15px}}
.cells{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}
.cell{{border:1px solid var(--bd);border-radius:12px;padding:12px;background:var(--bg)}}
.cell.proj{{border-left:3px solid var(--proj)}}
.cell.base{{border-left:3px solid var(--base)}}
.cell header{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px}}
.cell-meta{{font-size:11.5px;color:var(--mu)}}
.cell p{{margin:0;font-size:13px;white-space:pre-wrap}}
.ok{{color:var(--ok);font-weight:600}} .no{{color:var(--no);font-weight:600}}
.muted{{color:var(--mu)}}
ul.checks{{list-style:none;padding:0;margin:0}}
ul.checks li{{padding:8px 12px;border-bottom:1px solid var(--bd);font-size:13.5px}}
ul.checks li.ok b{{color:var(--ok)}} ul.checks li.no b{{color:var(--no)}}
.toolbar{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}}
input.filter{{flex:1;min-width:200px;background:var(--card);border:1px solid var(--bd);
border-radius:10px;padding:9px 12px;color:var(--tx);font-size:13px}}
footer{{margin-top:48px;color:var(--mu);font-size:12px;border-top:1px solid var(--bd);padding-top:14px}}
</style></head><body><div class="wrap">
<header class="top">
<div>
<h1>对照实验报告</h1>
<div class="sub">run <code>{_e(payload.get('run'))}</code> · 项目 vs baseline · 同一问题集 · 资源监控</div>
<div>{prov}</div>
</div>
<button class="toggle" onclick="var h=document.documentElement;
h.dataset.t=h.dataset.t==='dark'?'light':'dark';this.textContent=h.dataset.t==='dark'?'☀ 浅色':'☾ 深色';">☾ 深色</button>
</header>
{banner}
<div class="kpis">{kpi_html}</div>

<section class="blk"><h2>资源监控</h2>
<table id="mon"><thead><tr>
<th onclick="sortT('mon',1,1)">方法</th><th onclick="sortT('mon',2,1)">时延 avg s</th>
<th onclick="sortT('mon',3,1)">时延 median s</th><th onclick="sortT('mon',4,1)">tokens in</th>
<th onclick="sortT('mon',5,1)">tokens out</th><th onclick="sortT('mon',6,1)">成本 $</th>
<th onclick="sortT('mon',7,1)">工具数</th><th onclick="sortT('mon',8,1)">CPU% peak</th>
<th onclick="sortT('mon',9,1)">RSS MB peak</th></tr></thead>
<tbody>{mon_table}</tbody></table></section>

<section class="blk"><h2>功能验证（检索命中 / 引用命中 / 弃答 / 错误）</h2>
<table><thead><tr><th>方法</th><th>检索金标命中率</th><th>引用金标命中率</th>
<th>弃答数</th><th>error 数</th></tr></thead><tbody>{verif_table}</tbody></table></section>

<section class="blk"><h2>逐题并列对照</h2>
<div class="toolbar"><input class="filter" id="f" placeholder="过滤 QID…"
oninput="var v=this.value.toLowerCase();
document.querySelectorAll('.qcard').forEach(function(c){{
c.style.display=c.dataset.q.toLowerCase().indexOf(v)<0?'none':'';}})"></div>
{panels_html}</section>

<section class="blk"><h2>一致性自检</h2><ul class="checks">{chk}</ul></section>

<footer>数字均来自本 run 目录工件；缺失显示 —。深/浅色可切换；表头可点击排序。</footer>
</div>
<script>
function sortT(id,col,desc){{
 var t=document.getElementById(id),b=t.tBodies[0],rs=[].slice.call(b.rows);
 var dir=t.dataset.c===col+':'+desc?-1:1;t.dataset.c=col+':'+desc;
 rs.sort(function(a,b){{var x=parseFloat(a.cells[col-1].dataset.v||a.cells[col-1].innerText)||0;
 var y=parseFloat(b.cells[col-1].dataset.v||b.cells[col-1].innerText)||0;return (x-y)*dir;}});
 rs.forEach(function(r){{b.appendChild(r);}});}}
</script>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--questions", default="")
    ap.add_argument("--out", default="COMPARE.html")
    args = ap.parse_args()

    from lib import resolve_run_dir
    run = resolve_run_dir(args.run)
    mon = run / "monitor.json"
    if not mon.exists():
        print(f"[html] 缺少 {mon}；先运行 compare_report / exp.py")
        return 1
    payload = json.loads(mon.read_text(encoding="utf-8"))
    (run / args.out).write_text(render(payload), encoding="utf-8")
    print(f"[html] → {run / args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
