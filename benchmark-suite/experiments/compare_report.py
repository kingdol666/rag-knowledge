"""Side-by-side comparison report — project vs baselines on the same question.

Reads a run directory (`results/experiment_chat_*/`) and produces:
  COMPARE.md   per-question side-by-side answers + resource monitoring + self-checks
  monitor.json machine-readable version of the same

Design goals (PIPELINE V4/V8):
  * same question, every method, one table — so the project's output is directly
    comparable with each baseline;
  * resource monitoring per method (latency, tokens, cost, tool calls, and
    optional system CPU/RSS/GPU peaks);
  * functional verification is visible: retrieval gold-hit and answer-level gold
    citation per method, plus abstention counts;
  * logical self-consistency: totals are checked against the sum of parts and
    missing cells / errors are surfaced instead of hidden.

Usage
  python -m experiments.compare_report --run results/experiment_chat_<ts>
  python -m experiments.compare_report --run <dir> --questions data/papers/qa_v2.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(SUITE / "scripts"))

from baselines import src_of  # noqa: E402

ABSTAIN_MARKERS = ("insufficient", "not found", "no evidence", "does not contain",
                   "does not answer", "cannot be answered", "cannot answer",
                   "unable to answer", "not answerable", "not present in",
                   "outside the", "will not answer", "could not find",
                   "no source in the retrieved", "nothing in the knowledge base")

ANSWERABLE_STRATA = ("single", "multihop", "crosskb", "distractor")
REFUSAL_STRATA = ("unanswerable", "outofcorpus")


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def method_of(row: dict) -> str:
    return str(row.get("method") or row.get("track") or "?")


_ARXIV = re.compile(r"\b\d{4}\.\d{4,5}\b")
_SLUG = re.compile(r"[A-Za-z0-9_\-]+__[A-Za-z0-9\.\-]+__[^\s\"'\)\]，。]+")


def extract_ranked(row: dict) -> list[str]:
    """Ranked source ids for one cell.

    Baselines expose `ranked` directly. Agent tracks must be recovered from the
    tool-call trace AND the agent's own narration (all assistant text blocks
    EXCEPT the final answer) — a `kb_search_vector` call carries no document id,
    so the trace alone under-reports retrieval and produced false "retrieval
    miss" verdicts (observed 2026-09-24: a2 scored 0.625 while its answers
    correctly cited the gold paper). The final answer is excluded on purpose so
    retrieval_hit stays distinct from citation_hit.
    """
    if row.get("ranked"):
        return [str(x) for x in row["ranked"]]
    out: list[str] = []
    seen: set[str] = set()

    def add(v: str) -> None:
        s = src_of(v)
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    for call in (row.get("tool_calls") or []):
        inp = call.get("input") or {}
        for key in ("doc_path", "path", "file_path", "kb_id"):
            v = inp.get(key)
            if isinstance(v, str) and v.strip():
                add(v)

    texts = [str(t) for t in (row.get("texts_full") or [])]
    narration = "\n".join(texts[:-1])          # exclude the final answer block
    for m in _SLUG.finditer(narration):
        add(m.group(0))
    for m in _ARXIV.finditer(narration):
        add(m.group(0))
    return out


def _gold_ids(q: dict) -> list[str]:
    ids = list(q.get("gold_docs") or [])
    if q.get("arxiv_id"):
        ids.append(q["arxiv_id"])
    return [str(x) for x in ids]


def _abstained(answer: str) -> bool:
    low = str(answer or "").lower()
    return any(m in low for m in ABSTAIN_MARKERS)


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    return round(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2, 1)


def _avg(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 4) if xs else 0.0


def build(run: Path, questions: dict | None = None) -> tuple[str, dict]:
    rows: list[dict] = []
    b = _load(run / "baselines.json")
    if b:
        rows += [r for r in b.get("rows", []) if r.get("method") or r.get("track")]
    for f in sorted(run.glob("track_*.json")):
        d = _load(f)
        if isinstance(d, dict) and (d.get("track") or d.get("method")):
            rows.append(d)
    manifest = _load(run / "run_manifest.json") or {}

    qmeta = {q["qid"]: q for q in (questions or {}).get("questions", [])}
    qids = sorted({str(r.get("qid")) for r in rows})
    methods = sorted({method_of(r) for r in rows})

    # index rows by (qid, method)
    cell: dict[tuple, dict] = {}
    dupes = []
    for r in rows:
        k = (str(r.get("qid")), method_of(r))
        if k in cell:
            dupes.append(k)
        cell[k] = r

    per_q: dict[str, dict[str, dict]] = defaultdict(dict)
    for (qid, m), r in cell.items():
        gold = _gold_ids(qmeta.get(qid, {}))
        ranked = extract_ranked(r)
        ans = str(r.get("answer") or "")
        ev = " ".join(str(x) for x in (r.get("evidence_sources") or []))
        # Baselines expose a real ranked list → retrieval is directly observable.
        # Agent tracks do not (the SSE trace carries tool *inputs*, and a
        # kb_search_vector call has no doc id), so retrieval can only be inferred
        # from the trace ∪ the answer. Label the basis instead of silently
        # reporting a false "retrieval miss" (observed 2026-09-24).
        is_agent = not r.get("ranked")
        retr_blob = " ".join(ranked) if not is_agent else \
            " ".join(ranked) + " " + ans + " " + ev
        stratum = str((qmeta.get(qid) or {}).get("stratum") or "single")
        per_q[qid][m] = {
            "answer": ans,
            "stratum": stratum,
            "latency_s": r.get("latency_s"),
            "retrieval_s": r.get("retrieval_s"),
            "tokens_in": (r.get("tokens") or {}).get("input"),
            "tokens_out": (r.get("tokens") or {}).get("output"),
            "cost_usd": r.get("total_cost_usd"),
            "tools": r.get("tool_call_count"),
            "ranked": ranked,
            "gold": gold,
            "retrieval_basis": "ranked" if not is_agent else "trace+answer",
            "retrieval_hit": (any(g in retr_blob for g in gold) if gold else None),
            "citation_hit": (any(g in (ans + " " + ev) for g in gold) if gold else None),
            "abstained": _abstained(ans),
            "error": bool(r.get("error") or r.get("is_error")),
            "system": r.get("system"),
        }

    # ── per-method aggregates ────────────────────────────────────────────────
    agg = {}
    for m in methods:
        cells = [per_q[q][m] for q in qids if m in per_q[q]]
        lat = [c["latency_s"] for c in cells if isinstance(c["latency_s"], (int, float))]
        tin = [c["tokens_in"] for c in cells if isinstance(c["tokens_in"], (int, float))]
        tout = [c["tokens_out"] for c in cells if isinstance(c["tokens_out"], (int, float))]
        cost = [c["cost_usd"] for c in cells if isinstance(c["cost_usd"], (int, float))]
        tools = [c["tools"] for c in cells if isinstance(c["tools"], (int, float))]
        rh = [c["retrieval_hit"] for c in cells if c["retrieval_hit"] is not None]
        ch = [c["citation_hit"] for c in cells if c["citation_hit"] is not None]
        sys_peak = {}
        for c in cells:
            s = c.get("system") or {}
            for k, v in s.items():
                if k.endswith("_peak") and isinstance(v, (int, float)):
                    sys_peak[k] = max(sys_peak.get(k, 0), v)
        agg[m] = {
            "n": len(cells),
            "latency_avg_s": _avg(lat), "latency_median_s": _median(lat),
            "tokens_in_total": sum(tin), "tokens_out_total": sum(tout),
            "cost_usd_total": round(sum(cost), 4), "cost_usd_avg": _avg(cost),
            "tools_avg": _avg(tools),
            "retrieval_gold_rate": (round(sum(rh) / len(rh), 3) if rh else None),
            "citation_gold_rate": (round(sum(ch) / len(ch), 3) if ch else None),
            "abstentions": sum(1 for c in cells if c["abstained"]),
            "errors": sum(1 for c in cells if c["error"]),
            "system_peak": sys_peak or None,
        }
        # two-way honesty metric: a rule that always refuses looks perfect on
        # "correct refusal" alone — report over-refusal too.
        ref = [c for c in cells if c.get("stratum") in REFUSAL_STRATA]
        answ = [c for c in cells if c.get("stratum") in ANSWERABLE_STRATA]
        cr = sum(1 for c in ref if c["abstained"])
        orf = sum(1 for c in answ if c["abstained"])
        agg[m].update({
            "correct_refusal": cr, "refusal_n": len(ref),
            "notfound_accuracy": round(cr / len(ref), 3) if ref else None,
            "over_refusal": orf, "answerable_n": len(answ),
            "over_refusal_rate": round(orf / len(answ), 3) if answ else None,
        })

    # ── self-consistency checks ──────────────────────────────────────────────
    checks = []
    missing = [f"{q}/{m}" for q in qids for m in methods if m not in per_q[q]]
    checks.append({"check": "每 (qid,method) 都有结果", "ok": not missing,
                   "detail": f"{len(missing)} 缺失" + (f": {missing[:5]}" if missing else "")})
    checks.append({"check": "无重复单元", "ok": not dupes,
                   "detail": f"{len(dupes)} 重复" if dupes else "ok"})
    err = sum(a["errors"] for a in agg.values())
    checks.append({"check": "无 error 单元", "ok": err == 0, "detail": f"{err} 个 error"})
    manifest_cost = manifest.get("total_cost_usd")
    sum_cost = round(sum(a["cost_usd_total"] for a in agg.values()), 4)
    cost_ok = (manifest_cost is None) or (abs(float(manifest_cost) - sum_cost) < 0.01)
    checks.append({"check": "成本合计 = 各方法之和", "ok": cost_ok,
                   "detail": f"sum(method)={sum_cost}"
                             + (f" · manifest={manifest_cost}" if manifest_cost is not None
                                else " · manifest 未记总额")})
    n_rows = manifest.get("n_rows")
    checks.append({"check": "单元数 = 题数 × 方法数",
                   "ok": (n_rows is None) or (n_rows == len(qids) * len(methods)),
                   "detail": f"rows={n_rows} vs {len(qids)}×{len(methods)}"
                             f"={len(qids) * len(methods)}"})
    checks.append({"check": "provenance 完整",
                   "ok": all(manifest.get(k) is not None
                             for k in ("prompt_version", "seed", "max_turns")),
                   "detail": f"prompt_version={manifest.get('prompt_version')} "
                             f"seed={manifest.get('seed')}"})

    # ── markdown ─────────────────────────────────────────────────────────────
    L = [f"# 对照实验报告 — `{run.name}`", "",
         f"同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。",
         f"生成时间 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
         "", "## 方法清单", "",
         "| method | 类型 | n |", "|---|---|---:|"]
    for m in methods:
        kind = "项目（平台）" if m in ("a", "a2", "b", "c") else "baseline"
        L.append(f"| `{m}` | {kind} | {agg[m]['n']} |")

    L += ["", "## 资源监控总表", "",
          "| method | 时延 avg s | 时延 median s | tokens in | tokens out | "
          "成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m in methods:
        a = agg[m]
        sp = a["system_peak"] or {}
        L.append(f"| `{m}` | {a['latency_avg_s']} | {a['latency_median_s']} | "
                 f"{a['tokens_in_total']} | {a['tokens_out_total']} | "
                 f"{a['cost_usd_total']} | {a['cost_usd_avg']} | {a['tools_avg']} | "
                 f"{sp.get('cpu_pct_peak', '—')} | {sp.get('rss_mb_peak', '—')} |")

    L += ["", "## 功能验证（检索命中 / 引用命中 / 诚实性双向）", "",
          "| method | 检索金标命中率 | 引用金标命中率 | 正确拒答(应拒答层) | 误拒(可答层) | error 数 |",
          "|---|---:|---:|---:|---:|---:|"]
    for m in methods:
        a = agg[m]
        nf, orr = a.get("notfound_accuracy"), a.get("over_refusal_rate")
        L.append(
            f"| `{m}` | {a['retrieval_gold_rate'] if a['retrieval_gold_rate'] is not None else '—'} | "
            f"{a['citation_gold_rate'] if a['citation_gold_rate'] is not None else '—'} | "
            f"{a.get('correct_refusal')}/{a.get('refusal_n')}"
            + (f" ({nf})" if nf is not None else "") + " | "
            f"{a.get('over_refusal')}/{a.get('answerable_n')}"
            + (f" ({orr})" if orr is not None else "") + " | "
            f"{a['errors']} |")
    if not qmeta:
        L.append("")
        L.append("> 未提供题集（`--questions`），检索/引用命中率显示 `—`；"
                 "传入题集可启用金标核对。")
    if any((per_q[q].get(m) or {}).get("retrieval_basis") == "trace+answer"
           for q in qids for m in methods):
        L += ["", "> **口径说明**：baseline 的「检索命中」基于其真实 ranked 列表（可直接观测）；"
                  "agent 轨（a/a2/b/c）的 SSE 轨迹只含工具**入参**、不含检索结果文档 id，"
                  "故其检索命中由 trace ∪ 答案推断（`retrieval_basis=trace+answer`）。"
                  "**agent 轨请以「引用命中率」为可靠功能信号。**"]

    for qid in qids:
        q = qmeta.get(qid, {})
        L += ["", f"## {qid}" + (f" — `{q.get('stratum','')}`" if q.get("stratum") else ""), ""]
        if q.get("question"):
            L += [f"**Q:** {q['question']}", ""]
        if q.get("gold_docs") or q.get("arxiv_id"):
            L += [f"**gold:** {', '.join(_gold_ids(q))}", ""]
        L += ["| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |",
              "|---|:--:|:--:|---:|---:|---:|---:|:--:|---|"]
        for m in methods:
            c = per_q[qid].get(m)
            if not c:
                L.append(f"| `{m}` | — | — | — | — | — | — | — | (缺失) |")
                continue
            summary = re.sub(r"\s+", " ", c["answer"]).strip()[:150]
            rh = "✓" if c["retrieval_hit"] else ("✗" if c["retrieval_hit"] is False else "—")
            ch = "✓" if c["citation_hit"] else ("✗" if c["citation_hit"] is False else "—")
            L.append(f"| `{m}` | {rh} | {ch} | {c['latency_s']} | {c['tokens_out']} | "
                     f"{c['cost_usd']} | {c['tools']} | {'是' if c['abstained'] else '否'} | "
                     f"{summary or '(空)'} |")
        # full verbatim answers
        L += ["", "<details><summary>逐字答案全文</summary>", ""]
        for m in methods:
            c = per_q[qid].get(m)
            if c:
                L += [f"**[{m}]**", "", c["answer"] or "(空)", ""]
        L += ["</details>", ""]

    L += ["## 一致性自检", "", "| 检查 | 结果 | 详情 |", "|---|---|---|"]
    for c in checks:
        L.append(f"| {c['check']} | {'✅' if c['ok'] else '❌'} | {c['detail']} |")
    L += ["", "---", "",
          "*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*"]

    payload = {"run": run.name, "manifest": manifest, "methods": methods,
               "per_method": agg, "self_checks": checks,
               "per_question": {q: {m: {k: v for k, v in c.items() if k != "answer"}
                                    for m, c in per_q[q].items()} for q in qids}}
    return "\n".join(L), payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--questions", default="", help="题集 JSON（启用金标核对）")
    ap.add_argument("--out", default="COMPARE.md")
    args = ap.parse_args()

    run = Path(args.run)
    run = run if run.is_absolute() else SUITE / args.run
    if not run.exists():
        print(f"[compare] 目录不存在: {run}")
        return 1
    questions = None
    if args.questions:
        questions = json.loads((SUITE / args.questions).read_text(encoding="utf-8"))
    md, payload = build(run, questions)
    (run / args.out).write_text(md, encoding="utf-8")
    (run / "monitor.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"[compare] → {run / args.out}")
    bad = [c for c in payload["self_checks"] if not c["ok"]]
    print(f"[compare] 自检: {len(payload['self_checks']) - len(bad)}/"
          f"{len(payload['self_checks'])} 通过"
          + (f" · 失败: {[c['check'] for c in bad]}" if bad else ""))
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
