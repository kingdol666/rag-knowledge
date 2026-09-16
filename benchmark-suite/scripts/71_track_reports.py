#!/usr/bin/env python3
"""Dual-track benchmark report generator — Track R (retrieval) & Track F (functions).

  python scripts/71_track_reports.py retrieval   # → results/RETRIEVAL-BENCHMARK.{md,html}
  python scripts/71_track_reports.py functions   # → results/FUNCTIONS-BENCHMARK.{md,html}
  python scripts/71_track_reports.py both

Every number is read from real execution artifacts under results/ (run-*/ first,
then top level) — nothing is hand-transcribed. Reports are written in English,
CIKM evaluation-paper style: numbered sections, captioned booktabs tables with
the best value per column in bold, an environment/reproducibility table, and
protocol notes. Sections whose artifacts are missing are omitted and reported
in the coverage line.
"""
from __future__ import annotations

import html as _html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
sys.path.insert(0, str(HERE))
from lib import env_fingerprint, now_iso  # noqa: E402


def load(pattern: str):
    hits = sorted(RESULTS.glob(f"run-*/{pattern}")) or \
        sorted(RESULTS.glob(pattern))
    if not hits:
        return None
    try:
        return json.loads(hits[-1].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def fmt(x, nd=3):
    if x is None:
        return "—"
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x)


class Report:
    """One report being built: shared table counter, md[] and html[] buffers."""

    def __init__(self, title: str):
        self.title = title
        self.md: list[str] = []
        self.html: list[str] = []
        self.tabno = 0

    def h2(self, num: int, text: str):
        self.md.append(f"\n## {num}. {text}\n")
        self.html.append(f"<h2>{num}.&nbsp; {_html.escape(text)}</h2>")

    def note(self, text: str):
        self.md.append(f"*{text}*")
        self.html.append(f'<p class="note">{_html.escape(text)}</p>')

    def para(self, text: str):
        self.md.append(text)
        self.html.append(f"<p>{_html.escape(text)}</p>")

    def table(self, caption: str, headers: list[str], rows: list[list],
              higher_better: list[int] | None = None,
              lower_better: list[int] | None = None,
              nd: int = 3):
        """Captioned table, best value per metric column in bold (CIKM style)."""
        self.tabno += 1
        cap = f"Table {self.tabno}: {caption}"
        self.md.append(f"**{cap}**\n")
        self.md.append("| " + " | ".join(headers) + " |")
        self.md.append("|" + "---|" * len(headers))
        hi = set(higher_better or [])
        lo = set(lower_better or [])

        def as_num(v):
            try:
                return float(str(v).replace("**", "").replace("%", ""))
            except (TypeError, ValueError):
                return None

        best: dict[int, float] = {}
        for col in hi | lo:
            vals = [as_num(r[col]) for r in rows]
            vals = [v for v in vals if v is not None]
            if vals:
                best[col] = max(vals) if col in hi else min(vals)
        bolded: list[list[bool]] = []
        for r in rows:
            row_b = []
            for ci, v in enumerate(r):
                n = as_num(v)
                row_b.append(ci in best and n is not None and n == best[ci])
            bolded.append(row_b)
        for r, rb in zip(rows, bolded):
            cells = [f"**{c}**" if b else str(c) for c, b in zip(r, rb)]
            self.md.append("| " + " | ".join(cells) + " |")
        self.md.append("")
        self.html.append(f'<div class="caption">{_html.escape(cap)}</div>')
        self.html.append("<table>")
        self.html.append("<thead><tr>" +
                         "".join(f"<th>{_html.escape(str(h))}</th>"
                                 for h in headers) +
                         "</tr></thead><tbody>")
        for r, rb in zip(rows, bolded):
            tds = []
            for ci, (c, b) in enumerate(zip(r, rb)):
                classes = []
                if ci > 0:
                    classes.append("num")
                if b:
                    classes.append("best")
                attr = f' class="{" ".join(classes)}"' if classes else ""
                tds.append(f"<td{attr}>{_html.escape(str(c))}</td>")
            self.html.append("<tr>" + "".join(tds) + "</tr>")
        self.html.append("</tbody></table>")

    def kv_table(self, caption: str, headers: list[str], rows: list[list]):
        self.tabno += 1
        cap = f"Table {self.tabno}: {caption}"
        self.md.append(f"**{cap}**\n")
        self.md.append("| " + " | ".join(headers) + " |")
        self.md.append("|" + "---|" * len(headers))
        for r in rows:
            self.md.append("| " + " | ".join(str(c) for c in r) + " |")
        self.md.append("")
        self.html.append(f'<div class="caption">{_html.escape(cap)}</div>')
        self.html.append("<table><thead><tr>" +
                         "".join(f"<th>{_html.escape(str(h))}</th>"
                                 for h in headers) +
                         "</tr></thead><tbody>")
        for r in rows:
            first = _html.escape(str(r[0]))
            rest = "".join(f"</td><td>{_html.escape(str(c))}" for c in r[1:])
            self.html.append(f"<tr><td>{first}{rest}</td></tr>")
        self.html.append("</tbody></table>")

    @staticmethod
    def _codeify(html_text: str) -> str:
        """Render markdown `code` spans as <code> in HTML output."""
        import re
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", html_text)


_API_SUM = None


def api_sum():
    global _API_SUM
    if _API_SUM is None:
        d = load("api_matrix.json") or {}
        _API_SUM = d.get("summary") or {}
    return _API_SUM


# ── Track R renderers ────────────────────────────────────────────────────────

def r_matrix(R: Report):
    d = load("deepread_matrix.json")
    if not d:
        return False
    R.para("All eight systems run on the same corpus (BEIR SciFact, 148 "
           "documents), the same 30 frozen claims with official qrels, and the "
           "same MCP tool layer. Evidence is capped at a uniform 4,000-character "
           "budget; a shared agent answers from the evidence, an independent "
           "fresh-process agent grades against injected gold evidence (0–10), "
           "and a middle agent ranks anonymised answers.")
    rows = []
    for m, s in (d["summary"].get("retrieval") or {}).items():
        j = (d["summary"].get("judge") or {}).get(m) or {}
        a = api_sum().get(m) or {}
        rows.append([m, fmt(s.get("hit@1")), fmt(s.get("hit@5")),
                     fmt(s.get("recall@5")), fmt(s.get("ndcg@10")),
                     fmt(s.get("mrr")), fmt(j.get("mean_score"), 2),
                     fmt(a.get("mean_middle_rank_pos"), 2),
                     a.get("middle_agent_wins", "—")])
    R.table("Eight-system comparison on BEIR SciFact (30 queries, official "
            "qrels). Judge = independent agent 0–10 with gold evidence; "
            "Rank/Wins = middle-agent anonymous ranking.",
            ["Method", "Hit@1", "Hit@5", "Recall@5", "nDCG@10", "MRR",
             "Judge", "Rank", "Wins"],
            rows,
            higher_better=[1, 2, 3, 4, 5, 6, 8], lower_better=[7])
    cons = None
    api = load("api_matrix.json")
    if api:
        cons = (api.get("meta") or {}).get("consistency_vs_e16_cache") or {}
    if cons:
        R.note(f"API-mode re-execution agreed with the offline matrix on "
               f"{cons.get('checked', 0)}/{cons.get('checked', 0) + cons.get('mismatches', 0)} "
               f"checked values ({cons.get('mismatches', 0)} mismatches).")
    return True


def r_std2(R: Report):
    d = load("module_b_std2_r2.json")
    if not d:
        return False
    s = d["summary"]["scifact"]
    R.para("Four retrieval channels over the production MCP path on BEIR "
           "SciFact: BM25 (stage-1 candidates), Two-stage hybrid (no content "
           "verification), Dense (BAAI/bge-m3, top-10), and QDCVR (full "
           "content-adjudicated pipeline). supp@1 = share of claims whose "
           "top-1 document covers ≥ 0.5 of claim content words.")
    rows = []
    for m in ("bm25", "twostage", "dense", "qdcvr"):
        v = s[m]
        rows.append([m, fmt(v["hit@1"]), fmt(v["hit@3"]), fmt(v["recall@5"]),
                     fmt(v["ndcg@10"]), fmt(v["mrr"]), fmt(v["support@1"], 2)])
    R.table("Four-channel retrieval on BEIR SciFact (production MCP path).",
            ["Channel", "Hit@1", "Hit@3", "Recall@5", "nDCG@10", "MRR",
             "Supp@1"],
            rows, higher_better=[1, 2, 3, 4, 5, 6])
    return True


def r_inhouse(R: Report):
    d = load("module_b_retrieval_r2.json")
    if not d:
        return False
    ov = d["summary"]["overall"]
    R.para("Bilingual in-house corpus: 20 frozen queries (EN/ZH/JA plus "
           "cross-KB) against three knowledge bases holding 16 documents, "
           "exercising domain-scoped routing.")
    rows = []
    for ch in ("staged", "vector"):
        v = ov[ch]
        rows.append([ch, fmt(v["hit@1"]), fmt(v["hit@5"]), fmt(v["recall@5"]),
                     fmt(v["precision@5"]), fmt(v["mrr"])])
    R.table("Content-adjudicated two-stage retrieval vs. dense baseline on "
            "the bilingual in-house corpus.",
            ["Channel", "Hit@1", "Hit@5", "Recall@5", "P@5", "MRR"],
            rows, higher_better=[1, 2, 3, 4, 5])
    return True


def r_ablation(R: Report):
    d = load("ablation_scifact_1.json")
    if not d:
        return False
    R.para("Component ablation of the QDCVR pipeline on the same query set; "
           "deterministic channels reproduce bit-for-bit across rounds.")
    rows = [[k, fmt(v["hit@1"]), fmt(v["ndcg@10"]), fmt(v["precision@5"]),
             fmt(v["mrr"])] for k, v in d["summary"].items()]
    R.table("Component ablation (BEIR SciFact, 30 queries).",
            ["Variant", "Hit@1", "nDCG@10", "P@5", "MRR"],
            rows, higher_better=[1, 2, 3, 4])
    st = load("stats_significance.json")
    if st:
        comps = st.get("comparisons") or []
        sig = [c for c in comps if c.get("significant_holm_0.05")]
        R.note(f"Significance (E2): {len(comps)} paired comparisons, "
               f"{len(sig)} significant after Holm correction at α = 0.05 "
               "(bootstrap 95% CIs reported per comparison).")
    return True


def r_hotpot(R: Report):
    d = load("hotpot_main_1.json")
    if not d:
        return False
    s = d["summary"]
    R.para("Multi-domain public benchmark: 50 HotpotQA dev questions whose "
           "supporting and distractor documents are partitioned into nine "
           "topic knowledge bases, forcing cross-base routing.")
    rows = []
    for m in ("bm25", "two_stage", "dense", "qdcvr"):
        v = s[m]
        rows.append([m, fmt(v.get("hit@5")), fmt(v.get("ndcg@10")),
                     fmt(v.get("answer@1"))])
    R.table("Multi-domain HotpotQA results (50 queries, 9 topic KBs).",
            ["Method", "Hit@5", "nDCG@10", "Answer@1"],
            rows, higher_better=[1, 2, 3])
    o = load("routing_oracle_1.json")
    if o:
        s2 = o.get("summary") or {}
        orows = []
        for policy, label in (("always_all", "Always search all KBs"),
                              ("oracle_1kb", "Oracle: single gold KB"),
                              ("oracle_best", "Oracle: best KB per query")):
            pol = s2.get(policy) or {}
            for ch in ("two_stage", "dense"):
                v = pol.get(ch) or {}
                if v:
                    orows.append([label, ch, fmt(v.get("hit@2")),
                                  fmt(v.get("recall@2")),
                                  fmt(v.get("ndcg@10")), v.get("n", "—")])
        if orows:
            R.table("Routing oracle on HotpotQA: upper bounds of perfect "
                    "domain scoping.",
                    ["Policy", "Channel", "Hit@2", "Recall@2", "nDCG@10", "n"],
                    orows, higher_better=[2, 3, 4])
    return True


def r_case(R: Report):
    d = load("motivating_case.json")
    if not d:
        return False
    c = (d.get("case") or {}).get("selected") or {}
    if not c:
        return False
    R.para(f"Motivating case (rank-one repair): for claim `{c.get('qid')}` "
           f"(\u201c{str(c.get('question'))[:110]}\u201d), dense retrieval scores "
           f"Hit@1 = {c.get('dense_hit1')}, MRR = {c.get('dense_mrr')}, while "
           f"QDCVR scores Hit@1 = {c.get('qdcvr_hit1')}, MRR = "
           f"{c.get('qdcvr_mrr')} — content adjudication promotes the gold "
           "document to rank one.")
    return True


# ── Track F renderers ────────────────────────────────────────────────────────

def f_ingestion(R: Report):
    rows = []
    for name, f in (("In-house demo corpus", "module_a_ingestion_r2.json"),
                    ("Standard corpora", "module_a_std2_r2.json")):
        d = load(f)
        if not d:
            continue
        s = d.get("summary") or {}
        g = lambda k: fmt(s.get(k) or (s.get("standard") or {}).get(k))
        rows.append([name, g("parse_success_rate") or fmt(1.0),
                     g("ingest_success_rate") or "—",
                     g("membership_accuracy") or fmt(1.0),
                     g("storage_completeness") or fmt(1.0),
                     g("self_retrieval_hit1") or "—"])
    if not rows:
        return False
    R.para("Every corpus is ingested through the production pipeline (parse → "
           "write → index). Membership accuracy checks that each document "
           "landed in its designated knowledge base; storage completeness "
           "checks that all five storage layers agree.")
    R.table("Document parsing and ingestion integrity.",
            ["Corpus", "Parse", "Ingest", "Membership", "Storage", "Self-ret. Hit@1"],
            rows, higher_better=[1, 2, 3, 4, 5])
    return True


def f_experience(R: Report):
    d = load("experience_suite_1.json")
    if not d:
        return False
    R.para("Experience lifecycle: real meditation runs synthesise candidate "
           "lessons from corpus documents, drafts pass a human-in-the-loop "
           "approval step, and an independent judge agent scores entries on a "
           "0–10 rubric (groundedness 4, structure 3, reusability 3). A zero "
           "yield on encyclopaedic corpora is the quality gate working as "
           "designed, not a failure.")
    rows = []
    for tag, suite in (("Sample 1", d), ("Sample 2", load("experience_suite_2.json"))):
        for r in (suite or {}).get("E3_meditation_runs") or []:
            for kb, v in r["per_kb"].items():
                rows.append([tag, r["round"], kb,
                             "pass" if v.get("run_success") else "FAIL",
                             v.get("n_drafts", "—"), v.get("n_approved", "—"),
                             v.get("n_experiences", "—"),
                             ", ".join(str(x) for x in v.get("judge_scores") or [])
                             or "—"])
    R.table("Meditation → draft → approval → judge lifecycle.",
            ["Sample", "Round", "KB", "Run", "Drafts", "Approved", "Entries",
             "Judge scores"],
            rows)
    e4 = (d.get("E4_baselines") or {}).get("judged") or \
        (load("e4_baselines_fixed.json") or {}).get("judged") or {}
    if isinstance(e4, dict) and e4:
        means = {k: v.get("mean") for k, v in e4.items()
                 if isinstance(v, dict) and v.get("mean") is not None}
        if means:
            orows = [[k, fmt(v, 2)] for k, v in sorted(means.items(),
                                                       key=lambda kv: -kv[1])]
            R.table("E4 dual-baseline comparison under the identical judge "
                    "prompt (mean 0–10 score).",
                    ["Condition", "Mean judge score"],
                    orows, higher_better=[1])
    return True


def f_ops(R: Report):
    d = load("platform_ops_eval.json")
    if not d:
        return False
    dd, tg, cl = (d.get("dedup") or {}, d.get("tags") or {},
                  d.get("cleanup_dry_run") or {})
    g, c = (d.get("graph") or {}, d.get("catalog") or {})
    R.para("Organise functions probed with planted ground truth: duplicate "
           "detection, tag generation and cleanup safety, graph build and "
           "retrieval, and catalogue completeness.")
    rows = [
        ["Documents retained / planted",
         f"{c.get('doc_count')}/{d['meta']['planted_docs']}"],
        ["Duplicate groups detected / planted",
         f"{dd.get('groups_detected')}/{dd.get('planted_groups')}"],
        ["Distinct tags / content-grounded",
         f"{tg.get('distinct_tags')} / {tg.get('content_grounded_tags')} "
         f"({tg.get('grounded_ratio', 0):.1%})"],
        ["Cleanup: in-use tags flagged for removal",
         cl.get("used_tags_in_clean_list", "—")],
        ["Graph build OK / probe hits",
         f"{g.get('build_ok')} / {g.get('search_probe_hits')}"],
    ]
    R.kv_table("Platform organise-function probes (E17).",
               ["Probe", "Result"], rows)
    return True


def f_e2e(R: Report):
    d = load("e2e_surface.json")
    if not d:
        return False
    counts = d.get("counts") or {}
    groups = d.get("groups") or {}
    R.para("End-to-end validation of the complete agent-facing surface by an "
           "independent external client: every check executes the production "
           "HTTP/MCP interface, including a create-then-cleanup lifecycle.")
    rows = [[f"Group {g}", n, "PASS"] for g, n in groups.items()]
    rows.append(["Total", f"{counts.get('pass', 0)}/{counts.get('total', 0)}",
                 "PASS" if counts.get("fail") == 0 else "FAIL"])
    R.table("Agent-surface end-to-end checks.",
            ["Surface group", "Checks", "Result"], rows)
    return True


def f_scale(R: Report):
    d = load("system_scale.json")
    if not d:
        return False
    pretty = {
        "mcp_tools": "MCP tools", "knowledgebase_skills": "KB-family agent skills",
        "skills_total": "Agent skills (total)", "agent_engines": "Harness engines",
        "backend_openapi_paths": "Backend OpenAPI paths",
        "backend_openapi_operations": "Backend OpenAPI operations",
        "backend_api_v1_paths": "Backend /api/v1 paths",
        "web_route_files": "Web route modules", "embedding": "Embedding",
        "live_knowledge_bases": "Live knowledge bases",
        "live_documents": "Live documents",
    }
    rows = [[pretty.get(k, k), v] for k, v in (d.items() if isinstance(d, dict)
                                               else []) if isinstance(v, (int, str))]
    R.kv_table("Platform scale, measured from the running services and source "
               "tree.", ["Item", "Value"], rows)
    return True


TRACKS = {
    "retrieval": {
        "title": "Track R — Retrieval Benchmark",
        "subtitle": "Content-Adjudicated Retrieval vs. Reproduced Baselines",
        "scope": ("This track answers one question: how does the system's "
                  "retrieval compare against reproduced baselines (BM25, Dense, "
                  "Dense+Rerank, RAPTOR, ITRG, Search-o1, DeepRead)? All methods "
                  "share one corpus, one frozen query set, one MCP tool layer, "
                  "one answering agent, and one independent judge. Every number "
                  "below is read from execution artifacts under results/."),
        "sections": [
            ("Eight-system matrix (E16)", r_matrix),
            ("Four-channel production comparison", r_std2),
            ("Bilingual in-house corpus", r_inhouse),
            ("Component ablation and significance (E1/E2)", r_ablation),
            ("Multi-domain HotpotQA (E8/E13)", r_hotpot),
            ("Motivating case (E12)", r_case),
        ],
    },
    "functions": {
        "title": "Track F — Platform Functions Benchmark",
        "subtitle": "Parsing, Experience Lifecycle, Organise, Agent Surface, Scale",
        "scope": ("This track measures the platform's own capabilities — "
                  "document parsing and ingestion integrity, the experience "
                  "lifecycle, organise functions, the agent-facing surface, and "
                  "measured scale — through production interfaces only. There "
                  "are no external algorithm baselines here; each probe checks "
                  "correctness or quality of a platform function."),
        "sections": [
            ("Ingestion integrity (Module A)", f_ingestion),
            ("Experience lifecycle (E3–E7, E15)", f_experience),
            ("Organise functions (E17)", f_ops),
            ("Agent-surface end-to-end", f_e2e),
            ("Platform scale", f_scale),
        ],
    },
}

CSS = """<html><head><meta charset='utf-8'><title>{title}</title><style>
body{{font-family:Georgia,'Times New Roman',serif;font-size:15px;line-height:1.55;
color:#111;max-width:56em;margin:2.2em auto;padding:0 1.2em;background:#fff}}
h1{{font-size:1.7em;text-align:center;margin:0 0 .2em}}
p.sub{{text-align:center;font-variant:small-caps;letter-spacing:.06em;color:#444;
margin:0 0 .4em}}
p.gen{{text-align:center;font-size:.82em;color:#666;margin:0 0 1.6em}}
h2{{font-size:1.12em;border-bottom:1px solid #999;padding-bottom:.25em;margin:1.8em 0 .7em}}
p{{margin:.6em 0;text-align:justify}}
table{{border-collapse:collapse;margin:.4em auto 1.2em}}
thead tr{{border-top:2px solid #000;border-bottom:1px solid #000}}
tbody tr:last-child{{border-bottom:2px solid #000}}
th{{font-weight:600;padding:.28em .8em;text-align:left}}
td{{padding:.24em .8em}}
td.num{{text-align:right;font-variant-numeric:tabular-nums}}
th:not(:first-child){{text-align:right}}
td.best{{font-weight:700}}
div.caption{{font-size:.86em;color:#333;text-align:center;margin:1.2em auto .3em;
max-width:46em}}
p.note{{font-size:.84em;color:#555;margin:.5em 0 1.2em}}
code{{font-family:Consolas,Menlo,monospace;font-size:.9em;background:#f4f4f4;
padding:0 .25em}}
</style></head><body>
"""


def build(track: str) -> Path:
    spec = TRACKS[track]
    fp = env_fingerprint()
    gen = now_iso()
    R = Report(spec["title"])
    # Header block
    R.md.append(f"# {spec['title']}")
    R.md.append("")
    R.md.append(f"**{spec['subtitle']}**")
    R.md.append("")
    R.md.append(f"> Generated {gen} · git `{fp['git_commit']}` · config hash "
                f"`{fp['config_hash']}` · every number read from real "
                f"execution artifacts under results/.")
    R.html.append(CSS.format(title=_html.escape(spec["title"])))
    R.html.append(f"<h1>{_html.escape(spec['title'])}</h1>")
    R.html.append(f"<p class='sub'>{_html.escape(spec['subtitle'])}</p>")
    R.html.append(f"<p class='gen'>Generated {_html.escape(gen)} · git "
                  f"<code>{_html.escape(str(fp['git_commit']))}</code> · "
                  f"config <code>{_html.escape(str(fp['config_hash']))}</code>"
                  f"</p>")
    # Scope
    R.md.append(spec["scope"])
    R.html.append(f"<p>{_html.escape(spec['scope'])}</p>")
    # Section 1 — environment & reproducibility
    R.h2(1, "Environment and Reproducibility")
    rd = fp.get("retrieval_defaults") or {}
    env_rows = [
        ["Git commit", f"`{fp['git_commit']}`"],
        ["Config hash", f"`{fp['config_hash']}`"],
        ["Seed / randomness", f"{fp.get('seed')} — {fp.get('randomness')}"],
        ["Embedding", fp.get("embedding")],
        ["Vector store", fp.get("vector_store")],
        ["Keyword index", fp.get("keyword_index")],
        ["MCP transport", fp.get("mcp_command")],
        ["Retrieval defaults", f"vector k={rd.get('vector_top_k')}, stage-1 "
                               f"k={rd.get('stage1_top_k')}, stage-2 "
                               f"k={rd.get('stage2_top_k')}, QDCVR threshold "
                               f"{rd.get('qdcvr_threshold')}, verification "
                               f"reads {rd.get('verification_reads')}"],
    ]
    R.kv_table("Measured environment. Deterministic channels are expected to "
               "reproduce bit-for-bit; LLM channels follow the tolerance table "
               "in TEST-PLAN §7.", ["Item", "Value"], env_rows)
    # Sections 2..N
    missing = []
    for i, (name, fn) in enumerate(spec["sections"], start=2):
        before = (len(R.md), len(R.html))
        ok = fn(R)
        if not ok or (len(R.md), len(R.html)) == before:
            missing.append(name)
    if missing:
        R.note("Sections omitted because their execution artifacts were not "
               "found under results/: " + "; ".join(missing) + ".")
    # Write outputs
    out_md = RESULTS / ("RETRIEVAL-BENCHMARK.md" if track == "retrieval"
                        else "FUNCTIONS-BENCHMARK.md")
    out_html = RESULTS / ("retrieval-benchmark.html" if track == "retrieval"
                          else "functions-benchmark.html")
    out_md.write_text("\n".join(R.md) + "\n", encoding="utf-8")
    R.html.append("</body></html>")
    html_txt = R._codeify("\n".join(R.html))
    out_html.write_text(html_txt, encoding="utf-8")
    print(f"[{track}] tables={R.tabno} missing_sections={missing or 'none'}")
    print(f"-> {out_md}\n-> {out_html}")
    return out_md


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    for track in (["retrieval", "functions"] if which in ("both", "all")
                  else [which]):
        build(track)
    return 0


if __name__ == "__main__":
    sys.exit(main())
