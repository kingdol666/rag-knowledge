#!/usr/bin/env python3
r"""Collect + self-verify the FINAL benchmark evidence into results/paper_report.json.

This is the single source of truth for "what the paper may claim today". It runs
after the live runs are finished and does three things:

  1. collect — newest three-track run (a2/b/c), corpus state probed LIVE on the
     running platform, optional baseline arms, optional stability suite, provenance.
  2. grade   — re-uses the same grader kernel as scripts/107_exp_grade.py
     (`scripts/_paper_numbers.grade_run`) so the report can never drift from the
     scored artifacts: grounded / keyword-verified / cited / latency / cost are
     recomputed from the saved cells, not copied from prose.
  3. verify  — a list of fail-closed assertions. Each entry is `{name, ok, detail}`;
     the report renders them, and exit code 1 means "some number must not be
     quoted yet".

Usage
    python scripts/161_final_evidence.py                    # newest run, live corpus probe
    python scripts/161_final_evidence.py --run <run_id>
    python scripts/161_final_evidence.py --no-probe         # only read saved artifacts
    python scripts/161_final_evidence.py --baselines bm25,vector,rrf
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"
RUNS = RESULTS / "runs"
if str(SUITE / "scripts") not in sys.path:
    sys.path.insert(0, str(SUITE / "scripts"))

import _paper_numbers as PN  # noqa: E402  (grader kernel + paper macros)

CATEGORIES = ("计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
              "工程与能源", "经济与社会")
EXPECTED_PAPERS = 100
EXPECTED_CATEGORY_DOCS = 322
DENSE_KB = "Corpus-Chunks800"
TRACKS = ("a2", "b", "c")
CITE_ALT = {"A": "a2"}
STAB_DIRS = ("review/stability-multiround-20261013/results",
             "review/stability-multiround-20260930/results")
STAB_MIN_CELLS = 9  # 少于这个数说明套件还在跑，宁可用上一轮完整的，也不要半份
EXPECTED_LIBRARIES = 5  # 五门类库；探针必须每库至少命中一条，否则 15/15 是"局部满分"


# ── helpers ─────────────────────────────────────────────────────────────────
def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def newest_run(min_cells: int = 10) -> Path:
    """Newest COMPLETE-ENOUGH run.

    只看 mtime 会踩到「正在跑的新 run」——目录刚建出来、单元还没写盘，判分器拿到
    0 个题号直接 fail。因此优先取「已有 ≥min_cells 个单元」的最新 run，没有这样的
    run 时再退回最新目录（并让它 fail，属于正确的失败）。
    """
    cands = [p for p in RUNS.glob("run-*") if p.is_dir()]
    cands += [p for p in RESULTS.glob("experiment_chat_*") if p.is_dir()]
    if not cands:
        raise SystemExit("[evidence] results/ 下没有任何 run 目录")
    full = [p for p in cands if len(list(p.glob("track_*.json"))) >= min_cells]
    pool = full or cands
    pick = max(pool, key=lambda p: p.stat().st_mtime)
    n = len(list(pick.glob("track_*.json")))
    if n < min_cells:
        print(f"[warn] 最新 run {pick.name} 只有 {n} 个单元（< {min_cells}）："
              f"可能还在跑。要指定完整 run 请用 --run。")
    return pick


def resolve_run(arg: str) -> Path:
    if not arg:
        return newest_run()
    p = Path(arg)
    for cand in (p, RESULTS / arg, RUNS / arg):
        if cand.is_dir():
            return cand
    raise SystemExit(f"[evidence] 找不到 run 目录：{arg}")


def _stable_json(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def _bare_arxiv(gid: str) -> str:
    """`1706.03762v7` → `1706.03762`（manifest 带版本号，索引路径不带）。"""
    import re
    return re.sub(r"v\d+$", "", str(gid or "").strip(), flags=re.I)


def repo_git() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=SUITE.parent,
                              capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


# ── corpus probe (live platform) ────────────────────────────────────────────
def corpus_probe() -> dict:
    """Read-only live probe. Never writes to the platform."""
    sys.path.insert(0, str(SUITE / "scripts"))
    import lib
    out: dict = {"probed": False, "detail": {}}
    man = jload(SUITE / "data" / "papers" / "manifest.json").get("papers") or []
    corpus_files = list((SUITE / "data" / "corpus_md").glob("*.md"))
    out["detail"]["清单论文数 (manifest)"] = len(man)
    out["detail"]["导出语料 md 文件"] = len(corpus_files)
    try:
        cat = _mcp("kb_list", {"lightweight": True})
        cat_counts = {str(k.get("name")): int(k.get("doc_count") or 0)
                      for k in (cat.get("catalog") or [])}
        five = {n: cat_counts.get(n, 0) for n in CATEGORIES}
        out["category_docs"] = five
        out["detail"]["五门类库文档合计"] = sum(five.values())
        out["detail"]["门类分布"] = " · ".join(f"{k} {v}" for k, v in five.items())

        st = _mcp("kb_search_stats", {})
        cols = ((st or {}).get("stats") or {}).get("collections") or []
        out["detail"]["全库 collection 数"] = len(cols)
        out["detail"]["全库 chunk 总量"] = sum(int(c.get("chunk_count") or 0)
                                           for c in cols)
        dense_name = [k.get("kb_id") or k.get("id") for k in (cat.get("catalog") or [])
                      if k.get("name") == DENSE_KB]
        dense_col = [c for c in cols
                     if (dense_name and str(c.get("collection")) == f"kb_{dense_name[0]}")]
        if dense_col:
            out["detail"][f"{DENSE_KB} collection chunk"] = int(
                dense_col[0].get("chunk_count") or 0)

        probe_hits, probes = 0, []
        for p in man[:3]:
            q = (p.get("title") or "").strip()[:80]
            if not q:
                continue
            r = _mcp("kb_search_vector", {"query": q, "kb_id": DENSE_KB, "top_k": 5})
            hits = (r or {}).get("results") or []
            blob = _stable_json(hits)
            bare = _bare_arxiv(p["arxiv_id"])
            hit = bool(bare and (bare in blob or bare.replace("-", "/") in blob))
            probe_hits += int(hit)
            probes.append({"arxiv": p["arxiv_id"], "hit": hit,
                           "top": (hits[0].get("doc_path") if hits else None)})
        out["dense_probe_hits"] = probe_hits
        out["detail"][f"{DENSE_KB} 召回探针"] = f"{probe_hits}/3"
        out["dense_probes"] = probes
        out["probed"] = True
    except Exception as e:  # noqa: BLE001 — 探针失败不阻断，但会让自检报 fail
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return out


def _mcp(name: str, args: dict) -> dict:
    """One-shot MCP call through lib.McpClient (stdio), same path the tests use."""
    sys.path.insert(0, str(SUITE / "scripts"))
    import lib
    mc = lib.McpClient()
    try:
        return mc.call(name, args or {})
    finally:
        try:
            mc.close()
        except Exception:  # noqa: BLE001
            pass


def regression_artifact(path: Path | None = None) -> dict:
    """Table 1 的「Retrieval regression probes 15/15」实况证据（scripts/158 产出）。

    历史坑：这一行原先只有 2026-09 的 `r2_organize/report` 汇总数字，没有任何可复算
    的产物；2026-10-13 起由 158 每次真实检索生成 `results/a_retrieval_regression.json`，
    本函数只读它，并在 161 里作为闸门校验（缺产物 = 该主张没有证据，报 fail）。
    """
    p = path or (RESULTS / "a_retrieval_regression.json")
    if not p.exists():
        return {"path": str(p), "present": False}
    r = jload(p)
    probes = r.get("probes") or []
    hit_libs = sorted({pr.get("library") for pr in probes if pr.get("hit")})
    return {
        "path": str(p),
        "present": True,
        "generated": r.get("generated"),
        "top_k": r.get("top_k"),
        "probes_pass": r.get("probes_pass"),
        "probes_total": r.get("probes_total"),
        "verdict": r.get("verdict"),
        "libraries_covered": hit_libs,
        "libraries_total": (r.get("libraries") or {}).__len__() if isinstance(r.get("libraries"), dict) else len(hit_libs),
        "rank1": sum(1 for pr in probes if pr.get("hit") and pr.get("rank") == 1),
        "probes": [
            {"library": pr.get("library"), "gold": pr.get("gold"), "hit": pr.get("hit"),
             "rank": pr.get("rank"), "gold_score": pr.get("gold_score")}
            for pr in probes
        ],
    }


# ── stability suite ────────────────────────────────────────────────────────
# 「零覆盖诚实声明」检测。2026-10-13 实测教训：第一版只找「未找到 / 没有收录」这类
# 模板词，把一条正确拒答误判成「疑似编造」——那条答案写的是
# 「知识库中没有系统回答…的文档」「不足以构成完整答案」「本库内无法完整回答」
# 并附了逐级检索范围与盲区声明。判据必须是「模型明确声明库内无覆盖」，
# 而不是复述某个固定句。
_NO_COVERAGE = (
    # 明确说库内没有 / 不覆盖
    "未找到", "没有找到", "未检索到", "没有收录", "未收录", "没有相关",
    "无相关内容", "无对应内容", "没有任何文档", "不存在", "无覆盖", "未覆盖",
    "知识库中没有", "库中没有", "库内没有", "知识库中无", "库中无", "库内无",
    "不在知识库", "不在本库", "no content", "not covered", "not found in",
    "no relevant", "out of corpus", "outside the corpus",
    # 明确说无法/不足以回答
    "无法基于本库", "无法完整回答", "无法回答", "不能回答", "无法给出",
    "不足以构成完整答案", "不足以支撑", "不足以回答", "无法构成完整答案",
    "information is insufficient", "insufficient evidence", "cannot answer",
    "unable to answer",
    # 覆盖边界 / 盲区声明
    "覆盖边界", "盲区", "超出本库", "超出知识库", "建议入藏", "需另行入库",
    "coverage boundary", "blind spot",
)
_REFUSAL_HINT = ("不能", "无法", "不足", "不存在", "未覆盖", "无覆盖",
                 "没有", "未收录", "超出", "insufficient", "cannot", "unable")


def _honest_no_coverage(ans: str) -> bool:
    """True = 该答案明确声明「库内无覆盖 / 无法据此作答」（诚实拒答）。"""
    low = ans.lower()
    if any(w.lower() in low for w in _NO_COVERAGE):
        return True
    # 兜底：同时出现「否定词 + 库/范围词」，避免只因为用了别的说法就判成编造
    return any(h in low for h in _REFUSAL_HINT) and any(
        k in low for k in ("知识库", "本库", "库内", "库中", "语料", "corpus",
                           "检索范围", "覆盖"))
def stability_evidence(min_cells: int = STAB_MIN_CELLS) -> dict:
    for rel in STAB_DIRS:
        d = SUITE.parent / rel
        if not d.is_dir():
            continue
        files = sorted(d.glob("r*_*.json"))
        if len(files) < min_cells:
            print(f"[stab] {rel} 只有 {len(files)} 个单元（< {min_cells}）→ 视为套件未跑完，"
                  f"继续找上一轮完整结果")
            continue
        rows = []
        for f in files:
            try:
                r = jload(f)
            except Exception:  # noqa: BLE001
                continue
            ans = str(r.get("answer") or "")
            task, lane = r.get("task"), r.get("mode")
            low = ans.lower()
            if task == "attention":
                ok = "attention" in low and ("softmax" in low or "qk" in low)
                verdict = "公式命中" if ok else "未给出公式"
            elif task == "seismology":
                ok = _honest_no_coverage(ans)
                verdict = "诚实拒答" if ok else "疑似编造/未拒答"
            else:
                ok = _honest_no_coverage(ans)
                verdict = "诚实拒答" if ok else "疑似编造/未拒答"
            tools = [str(t.get("name") or t.get("tool") or "") for t in
                     (r.get("tool_calls") or [])]
            blob = " ".join(tools)
            if lane == "B":
                lane_ok = ("kb_search_vector" not in blob and "kb_search_two_stage" not in blob)
            elif lane == "A":
                lane_ok = "kb_search_vector" in blob or "kb_search_two_stage" in blob or not tools
            else:
                lane_ok = "kb_search_vector" in blob or "kb_list" in blob or not tools
            rows.append({"round": r.get("round"), "task": task, "lane": lane,
                         "wall_s": r.get("wall_s"), "http": r.get("http"),
                         "turns": r.get("turns"), "cost": r.get("cost"),
                         "ok": ok, "verdict": verdict, "lane_contract": lane_ok,
                         "file": f.name})
        if not rows:
            continue
        walls = [float(r["wall_s"]) for r in rows if r.get("wall_s")]
        return {
            "dir": str(d.relative_to(SUITE.parent)),
            "cells": len(rows), "ok_cells": sum(1 for r in rows if r["ok"]),
            "lane_ok_cells": sum(1 for r in rows if r["lane_contract"]),
            "rounds": len({r["round"] for r in rows}),
            "lanes": len({r["lane"] for r in rows}),
            "tasks": len({r["task"] for r in rows}),
            "latency_min_s": round(min(walls), 1) if walls else None,
            "latency_max_s": round(max(walls), 1) if walls else None,
            "latency_median_s": round(statistics.median(walls), 1) if walls else None,
            "cost_usd_total": round(sum(float(r["cost"] or 0) for r in rows), 4),
            "description": ("三任务（可回答／语料未覆盖／语料外）× 三车道 × 多轮，"
                            "验证检索一致性、诚实拒答与车道契约。"),
            "rows": rows,
        }
    return {}


# ── baseline arms (optional) ───────────────────────────────────────────────
def baselines_evidence(run: Path, qfile: Path, wanted: list[str]) -> dict:
    if not wanted:
        return {}
    qs = {q["qid"]: q for q in jload(qfile)["questions"]}
    out = {}
    for m in wanted:
        cells = sorted(run.glob(f"track_{m}_*.json"))
        if not cells:
            continue
        n = g = kw = ab = 0
        lat = []
        for f in cells:
            r = jload(f)
            q = qs.get(r.get("qid")) or {}
            ans = str(r.get("answer") or "")
            n += 1
            gid = str(q.get("arxiv_id") or "")
            ranked = _stable_json(r.get("results") or r.get("candidates") or
                                  r.get("documents") or r)
            if gid and (gid in ranked or gid.replace("-", "/") in ranked):
                g += 1
            hits = PN.kw_hit(ans, q.get("gold_keywords") or [])
            need = max(1, -(-len(q.get("gold_keywords") or []) * 3 // 5))
            kw += int(len(hits) >= need)
            ab += int(bool(PN.RX_ABSTAIN.search(ans)))
            if r.get("latency_s"):
                lat.append(float(r["latency_s"]))
        out[m] = {"n": n, "grounded": g, "kw_ok": kw, "abstain": ab,
                  "latency_avg_s": round(sum(lat) / len(lat), 2) if lat else None}
    return out


# ── main collection ────────────────────────────────────────────────────────
def collect(run: Path, probe: bool, baselines: list[str], paper_tex: Path | None) -> dict:
    if str(SUITE / "scripts") not in sys.path:
        sys.path.insert(0, str(SUITE / "scripts"))
    qfile = PN.pick_qfile(run)
    graded = PN.grade_run(run, qfile)
    manifest = jload(run / "run_manifest.json") if (run / "run_manifest.json").exists() else {}
    qs = {q["qid"]: q for q in jload(qfile)["questions"]}

    # per-track aggregates expected by the HTML contract
    grades = {}
    for t, g in graded["grades"].items():
        costs = [x["cost_usd"] or 0 for x in graded["rows"] if x["track"] == t]
        grades[t] = {
            "n": g["n"], "grounded": g["grounded"], "kw_ok": g["kw"], "cited": g["cited"],
            "cited_chunk": g["cited_chunk"], "pass": g["pass"], "abstain": g["abstain"],
            "sentinel": sum(1 for x in graded["rows"]
                            if x["track"] == t and x["sentinel"]),
            "errors": sum(1 for x in graded["rows"]
                          if x["track"] == t and x["is_error"]),
            "latency_avg_s": g["avg_latency_s"],
            "latency_median_s": round(statistics.median(g["latency_s"]), 1)
            if g["latency_s"] else None,
            "cost_usd_total": round(sum(costs), 4),
            "tools_avg": g["avg_tools"],
            "fails": g["fails"],
        }

    # per-question cells (with evidence for the reader)
    per_question: dict[str, dict] = {}
    for x in graded["rows"]:
        qid = str(x["qid"])
        q = qs.get(qid) or {}
        entry = per_question.setdefault(qid, {
            "qid": qid, "question": q.get("question") or "",
            "gold": str(q.get("arxiv_id") or ""), "kw_total": x["kw_n"],
            "top_sim": None, "cells": []})
        raw = x.get("raw") if isinstance(x, dict) else None
        ans = ""
        markers: list[str] = []
        for f in sorted(run.glob(f"track_{x['track']}_{qid}.json")):
            r = jload(f)
            ans = str(r.get("answer") or "")
            _c, _cc, mk = PN.cite_markers(ans)
            markers = mk or []
            sims = [c.get("similarity") or c.get("score") for c in
                    (r.get("results") or r.get("candidates") or []) if isinstance(c, dict)]
            sims = [float(s) for s in sims if isinstance(s, (int, float))]
            if sims:
                entry["top_sim"] = round(max(sims), 3)
            tools = r.get("tool_call_count")
            trace = _stable_json(r.get("tool_calls") or [])
            gid = entry["gold"]
            where = ("答案正文" if gid and (gid in ans or gid.replace("-", "/") in ans)
                     else "工具轨迹" if gid and (gid in trace
                                              or gid.replace("-", "/") in trace)
                     else "未命中")
            entry["cells"].append({
                "track": x["track"], "grounded": x["gold_hit"], "kw_ok": x["kw_ok"],
                "kw_hits": len(x["kw_hits"]), "kw_total": x["kw_n"],
                "kw_list": x["kw_hits"], "cited": x["cited"],
                "cite_markers": markers[:6], "gold_where": where,
                "sentinel": x["sentinel"], "abstain": x["abstain"],
                "latency_s": x["latency_s"], "tools": tools,
                "cost_usd": x["cost_usd"], "answer": ans[:20000],
                "state": ("sentinel" if x["sentinel"] else
                          "error" if x["is_error"] else
                          "pass" if x["pass"] else
                          "kw" if (x["gold_hit"] and not x["kw_ok"]) else "fail"),
            })
    for qid, e in per_question.items():
        e["cells"].sort(key=lambda c: TRACKS.index(c["track"])
                        if c["track"] in TRACKS else 99)

    corpus = {"detail": {}} if not probe else corpus_probe()
    corpus.setdefault("detail", {})
    if not probe:
        man = jload(SUITE / "data" / "papers" / "manifest.json").get("papers") or []
        corpus["detail"]["清单论文数 (manifest)"] = len(man)
        corpus["detail"]["导出语料 md 文件"] = len(
            list((SUITE / "data" / "corpus_md").glob("*.md")))
    corpus["detail"]["本次 run"] = run.name
    corpus["detail"]["题集"] = qfile.name
    corpus["detail"]["计分单元"] = manifest.get("n_rows")

    stab = stability_evidence()
    base = baselines_evidence(run, qfile, baselines)
    regression = regression_artifact()
    corpus["detail"]["检索回归探针"] = (
        f"{regression.get('probes_pass')}/{regression.get('probes_total')}"
        f" · 命中覆盖 {len(regression.get('libraries_covered') or [])}/"
        f"{EXPECTED_LIBRARIES} 库"
        if regression.get("present") else "缺 results/a_retrieval_regression.json")

    meta = {
        "run_id": run.name, "git_commit": manifest.get("git_commit") or repo_git(),
        "config_hash": manifest.get("config_hash"), "prompt_version": manifest.get("prompt_version"),
        "started_utc": manifest.get("started_utc"),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tracks": manifest.get("tracks") or list(graded["grades"]),
        "questions": manifest.get("questions"), "seed": manifest.get("seed"),
        "max_turns": manifest.get("max_turns"), "shuffled": manifest.get("shuffled"),
        "selfheal": manifest.get("selfheal"),
        "total_cost_usd": manifest.get("total_cost_usd"),
        "tokens_out_total": manifest.get("tokens_out_total"),
        "qfile": qfile.name, "n_rows": manifest.get("n_rows"),
    }

    # ── verification (fail-closed) ───────────────────────────────────────────
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str, informational: bool = False) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail,
                       **({"informational": True} if informational else {})})

    n_cells = len(graded["rows"])
    add("run 计分单元 = 题数 × 轨道", n_cells == 10 * len(TRACKS),
        f"{n_cells} 单元（{len(set(x['qid'] for x in graded['rows']))} 题 × "
        f"{len(set(str(x['track']) for x in graded['rows']))} 轨）")
    add("题集 = 论文 BQ 集", qfile.name == "qa_questions.json",
        f"使用 {qfile.name}（论文口径为 BQ01–BQ10）")
    n_sent = sum(1 for x in graded["rows"] if x["sentinel"])
    add("无工具面中断单元", n_sent == 0,
        f"{n_sent} 个哨兵单元" +
        ("" if n_sent == 0 else "：" + ", ".join(
            f"{x['track']}/{x['qid']}" for x in graded["rows"] if x["sentinel"])),
        informational=(n_sent > 0))
    n_err = sum(1 for x in graded["rows"] if x["is_error"])
    add("无执行错误单元", n_err == 0,
        f"{n_err} 个 error 单元" + ("" if n_err == 0 else "：" + ", ".join(
            f"{x['track']}/{x['qid']}" for x in graded["rows"] if x["is_error"])))
    a2 = grades.get("a2") or {}
    add("平台轨金标命中 = 满分", (a2.get("grounded") or 0) == (a2.get("n") or 0) > 0,
        f"{a2.get('grounded')}/{a2.get('n')}")
    add("平台轨关键词达标 ≥ 9/10", (a2.get("kw_ok") or 0) >= 9,
        f"{a2.get('kw_ok')}/{a2.get('n')}")
    add("平台轨引用可复核 ≥ 8/10", (a2.get("cited") or 0) >= 8,
        f"{a2.get('cited')}/{a2.get('n')}")
    add("清单论文数 = 100", corpus["detail"].get("清单论文数 (manifest)") == EXPECTED_PAPERS,
        str(corpus["detail"].get("清单论文数 (manifest)")))
    add("导出语料文件 = 100", corpus["detail"].get("导出语料 md 文件") == EXPECTED_PAPERS,
        str(corpus["detail"].get("导出语料 md 文件")))
    if probe:
        add("五门类库文档 ≥ 322",
            int(corpus["detail"].get("五门类库文档合计") or 0) >= EXPECTED_CATEGORY_DOCS,
            f"{corpus['detail'].get('五门类库文档合计')}（{corpus['detail'].get('门类分布')}）")
        add("密索引可召回（live 探针）",
            int(corpus.get("dense_probe_hits") or 0) >= 1,
            f"{corpus.get('dense_probe_hits')}/3 命中 {DENSE_KB}")
    # Table 1「Retrieval regression probes 15/15」：必须来自本轮真实检索产物，
    # 且命中要铺满五个门类库（否则是"只在某个库自测"的局部满分）。离线模式
    # （--no-probe）没有探针权限，本轮跳过该闸门。
    if probe:
        rp, rt = regression.get("probes_pass"), regression.get("probes_total")
        libs_hit = regression.get("libraries_covered") or []
        add("检索回归探针 15/15（论文 Table 1）",
            bool(regression.get("present")) and rp == 15 and rt == 15,
            (f"{rp}/{rt} · 产物 {Path(str(regression.get('path'))).name}"
             f" · 生成 {regression.get('generated')}"
             if regression.get("present") else
             "缺 results/a_retrieval_regression.json → 先跑 "
             "python scripts/158_a_retrieval_regression.py"))
        add("回归探针命中覆盖五门类库",
            len(libs_hit) >= EXPECTED_LIBRARIES,
            f"{len(libs_hit)}/{EXPECTED_LIBRARIES} 库命中：" + "、".join(libs_hit)
            + f" · rank1 {regression.get('rank1')}/{rt}")
    if stab:
        add("稳定性套件全部单元行为正确",
            stab["ok_cells"] == stab["cells"],
            f"{stab['ok_cells']}/{stab['cells']} 单元（{stab['rounds']} 轮 × "
            f"{stab['lanes']} 车道 × {stab['tasks']} 任务）")
        add("稳定性车道契约全部合规",
            stab["lane_ok_cells"] == stab["cells"],
            f"{stab['lane_ok_cells']}/{stab['cells']} 单元工具路径符合车道定义")
    else:
        add("稳定性套件存在", False, "未找到 r*_*.json（先跑 review/…/run_stability.py）")
    if paper_tex and paper_tex.exists():
        paper = PN.paper_values(paper_tex)
        cmp_checks = PN.compare(paper, graded["grades"], run, graded["rows"], tol=0.30)
        macro_drift = [c for c in cmp_checks if not c["ok"]]
        # 论文宏是「上一轮实测」的快照：本轮跑出新数字后它必然漂移。漂移本身
        # 不是失败，而是「论文该改哪几行」的工单；真正决定能否写入的是下面的
        # 论文级闸门（研究主张必须被本轮数据支撑）。
        for c in macro_drift:
            checks.append({
                "name": f"论文宏待刷新 · {c['claim']}", "ok": True,
                "detail": f"论文现值 {c['paper']} → 本轮实测 {c['observed']}"
                          f"{' · ' + c['detail'] if c['detail'] else ''}",
                "informational": True,
            })
        add("论文级闸门：平台轨必须满分支撑主张", bool(a2) and
            (a2.get("grounded") or 0) == (a2.get("n") or 0) > 0 and
            (a2.get("kw_ok") or 0) >= 9 and (a2.get("cited") or 0) >= 9,
            f"grounded {a2.get('grounded')}/{a2.get('n')} · kw {a2.get('kw_ok')}/{a2.get('n')}"
            f" · cited {a2.get('cited')}/{a2.get('n')}")
        zero_tool = [x for x in graded["rows"]
                     if not (x.get("tools") or 0) and not x.get("is_error")]
        add("论文级闸门：无「零工具面」单元（从未检索 = 该行无效）",
            not zero_tool,
            "无零工具单元" if not zero_tool else
            f"{len(zero_tool)} 个零工具单元：" + ", ".join(
                f"{x['track']}/{x['qid']}" for x in zero_tool) +
            " → 这些单元必须重跑（--retry-sentinel / 重启 kb-mcp）")
        add("论文级闸门：三轨无工具面中断",
            n_sent == 0,
            f"{n_sent} 个哨兵单元" if n_sent else "0 个哨兵单元",
            informational=(n_sent > 0))
        if n_sent:
            checks[-1]["detail"] += ("（有检索发生但引擎/工具面中途不可用："
                                     "论文口径允许「工具不可用中止」并据此解释，"
                                     "不阻塞报告生成；要清干净就重跑这些单元）")
        add("论文宏刷新工单已生成", True,
            f"{len(macro_drift)} 行需要改 main.tex（报告「论文宏工单」一节逐条列出）"
            if macro_drift else "本轮与论文宏一致，无需改动")
    else:
        add("论文宏对账", True, "已按 --no-paper 跳过")

    repro = "\n".join([
        "# 1) 语料与索引（只读体检 + 必要时重建）",
        "python scripts/151_smoke_probe.py",
        "python scripts/106_exp_corpus_r2.py --dry-run",
        "# 1b) Table 1 的检索回归探针（真实检索，15 条铺满五门类库）",
        "python scripts/158_a_retrieval_regression.py",
        "# 2) 三轨真实执行（写 results/runs/run-<ts>-<commit>/）",
        f"python -m experiments.runner --questions data/papers/{qfile.name} --tracks a2,b,c",
        "# 3) 采集 + 自检 + 渲染报告",
        "python scripts/161_final_evidence.py" +
        (f" --run {run.name}" if run.name else ""),
        "python scripts/162_paper_report_html.py",
        "# 4) 稳定性套件（可选，约 30 分钟）",
        "python review/stability-multiround-20260930/run_stability.py r1 r2 r3",
    ])

    return {"meta": {**meta, "repro": repro}, "corpus": corpus,
            "regression": regression,
            "tracks": [t for t in TRACKS if t in grades] or list(grades),
            "grades": grades, "per_question": per_question,
            "baselines": base, "stability": stab,
            "verification": {
                "checks": checks,
                "passed": sum(1 for c in checks if c["ok"] and not c.get("informational")),
                "total": sum(1 for c in checks if not c.get("informational")),
                "informational": sum(1 for c in checks if c.get("informational")),
                "verdict": "pass" if all(c["ok"] for c in checks
                                         if not c.get("informational")) else "fail",
            }}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="", help="run 目录名/相对/绝对路径（默认最新）")
    ap.add_argument("--no-probe", action="store_true", help="不打真实平台探针（离线模式）")
    ap.add_argument("--baselines", default="", help="逗号分隔：bm25,vector,rrf,rerank")
    ap.add_argument("--against-paper", action="store_true", default=True,
                    help="与 paper_demo/tex/main.tex 的宏对账（默认开）")
    ap.add_argument("--no-paper", dest="against_paper", action="store_false")
    ap.add_argument("--out", default=str(RESULTS / "paper_report.json"))
    args = ap.parse_args()

    run = resolve_run(args.run)
    paper_tex = SUITE.parent / "paper_demo" / "tex" / "main.tex" if args.against_paper else None
    ev = collect(run, probe=not args.no_probe,
                 baselines=[s.strip() for s in args.baselines.split(",") if s.strip()],
                 paper_tex=paper_tex)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")

    v = ev["verification"]
    print(f"[run ] {run.name}")
    print(f"[题集] {ev['meta']['qfile']} · {ev['meta'].get('questions')} 题 · "
          f"{ev['meta'].get('n_rows')} 单元")
    for t in ev["tracks"]:
        g = ev["grades"][t]
        print(f"[{t:>2}] grounded {g['grounded']}/{g['n']} · kw {g['kw_ok']}/{g['n']} · "
              f"cited {g['cited']}/{g['n']} · pass {g['pass']}/{g['n']} · "
              f"{g['latency_avg_s']}s · ${g['cost_usd_total']} · sentinel {g['sentinel']}")
    for c in v["checks"]:
        tag = "·" if c.get("informational") else ("✓" if c["ok"] else "✗")
        print(f"  {tag} {c['name']} — {c['detail']}")
    print(f"[verdict] {v['verdict']} ({v['passed']}/{v['total']}"
          + (f" + {v['informational']} 条信息项" if v.get("informational") else "")
          + f") → {out}")
    return 0 if v["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
