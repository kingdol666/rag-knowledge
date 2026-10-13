#!/usr/bin/env python3
r"""_paper_numbers.py — 论文实验数字 ↔ benchmark 运行产物的对账内核.

论文（`paper_demo/tex/main.tex`）把实验数字集中定义成 15 个 `\\NUM*` 宏，
正文（sec0/sec4）只引用宏名。本模块：

  1. `paper_values()`  从 `paper_demo/tex/main.tex` 解析当前宏值（论文是唯一真源）；
  2. `grade_run()`     用与 `scripts/107_exp_grade.py` **完全一致**的确定性口径
                       判分一个 run 目录（gold 证据 / ≥60% 关键词 / 引用标记 /
                       哨兵失败分类），并额外算出论文需要的"引用数"；
  3. `compare()`       逐条对账（计数类要求精确相等；时延/成本允许 1% 容差）。

引用口径（此前只存在于 main.tex 注释里的一段临时正则，2026-10-13 固化到
`scripts/107_exp_grade.py`，本模块直接复用其常量，避免两处定义漂移）
----------------------------------------------------------------------------
论文 Metrics 原文：`cited (part/section/table markers present)`：

  * **A 族 part/section/table**（论文口径，也是 `\\NUMcite*` 的来源）
    `part k of N` / `section(s)|table(s)|appendix|appendices <num|letter>` / `§<num>`
  * **B 族 chunk 引用**（稠密轨按提示词要求引用的 `<file>#chunk_index N`）

实测校准（run-20260930T150453Z-3ec2174，论文 \NUMciteA/B/C = 9/6/1）：
A 族 a2=9 · b=6 · c=1 —— 与论文三个宏**逐一吻合**；
B 族 a2=6 · b=1 · c=7 —— 即稠密轨 7 次 chunk 引用并未计入论文数字。
因此 A 族是 `\\NUMcite*` 的定义，B 族只作附注（`cited_chunk`）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
PAPER_TEX = SUITE.parent / "paper_demo" / "tex" / "main.tex"

from importlib import import_module  # noqa: E402

import sys  # noqa: E402

if str(SUITE / "scripts") not in sys.path:
    sys.path.insert(0, str(SUITE / "scripts"))
_g107 = import_module("107_exp_grade")

RX_CITE = _g107.RX_CITE
RX_CITE_DENSE = _g107.RX_CITE_DENSE
cite_markers = _g107.cite_markers
CITE_DEF = _g107.CITE_DEF
CITE_DEF_DENSE = _g107.CITE_DEF_DENSE
RX_ABSTAIN = re.compile(
    r"retrieved evidence is insufficient|insufficient evidence|unable to answer|"
    r"could not answer|not[- ]found report|i am not giving", re.I)

# 论文宏名 → 用途（真源 = main.tex，此处只做缺失时报错）
EXPECTED_MACROS = [
    "NUMgroundedA", "NUMgroundedB", "NUMgroundedC",
    "NUMkwA", "NUMkwB", "NUMkwC",
    "NUMciteA", "NUMciteB", "NUMciteC",
    "NUMlatA", "NUMlatB", "NUMlatC",
    "NUMcostA", "NUMcostB", "NUMcostC",
]


# ── 1. 论文真源 ─────────────────────────────────────────────────────────────
def paper_values(tex: Path = PAPER_TEX) -> dict:
    txt = tex.read_text(encoding="utf-8")
    macros = dict(re.findall(r"\\newcommand\{\\(NUM\w+)\}\{([^}]*)\}", txt))
    missing = [m for m in EXPECTED_MACROS if m not in macros]
    if missing:
        raise SystemExit(f"[paper_numbers] main.tex 缺宏: {missing}")
    # 正文里的硬编码数字（尚无宏）——发现即报，供投稿前收敛
    hard = []
    for pat, label in ((r"(?<![\d,])4,?528(?![\d])", "chunks800 (Table 1)"),
                       (r"run-20260930T150453Z-3ec2174", "canonical run id 注释")):
        if re.search(pat, txt) or any(re.search(pat, p.read_text(encoding="utf-8"))
                                      for p in tex.parent.glob("sec*.tex")):
            hard.append(label)

    def num(name: str) -> float:
        v = re.sub(r"[^0-9.]", "", macros[name].replace("\\,", ""))
        return float(v or 0)

    return {"tex": str(tex), "raw": {k: macros[k] for k in EXPECTED_MACROS},
            "hardcoded": hard,
            # 论文口径：10 道固定题 BQ01–BQ10（sec4_eval.tex Setup）
            "n_questions": 10,
            "grounded": {t: num(f"NUMgrounded{t}") for t in "ABC"},
            "kw": {t: num(f"NUMkw{t}") for t in "ABC"},
            "cite": {t: num(f"NUMcite{t}") for t in "ABC"},
            "lat": {t: num(f"NUMlat{t}") for t in "ABC"},
            "cost": {t: num(f"NUMcost{t}") for t in "ABC"}}


# ── 2. 判分（与 107_exp_grade.py 同口径 + 引用/哨兵） ───────────────────────
def _pick_run_file(run_dir: Path) -> str:
    """运行器写盘的「发现文件」：agent 轨 = track_*.json；老式检索臂 = arm_*.json。"""
    if list(run_dir.glob("track_*.json")):
        return "track"
    if list(run_dir.glob("arm_*.json")):
        return "arm"
    return ""


def _iter_run_rows(run_dir: Path):
    """产出归一化后的行：{qid, track, answer, tool_calls, texts_full}。

    两种载体：
      * `track_<track>_<qid>.json`（experiments/runner.py）——论文三轨的载体；
      * `arm_<A|B|C>-<qid>.json`（老式检索臂，A/B/C 映射到 a2/b/c）。
    """
    kind = _pick_run_file(run_dir)
    if kind == "track":
        for f in sorted(run_dir.glob("track_*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            yield {"qid": r.get("qid"), "track": r.get("track"),
                   "answer": str(r.get("answer") or ""),
                   "tool_calls": r.get("tool_calls") or [],
                   "texts_full": r.get("texts_full") or [], "raw": r}
    elif kind == "arm":
        amap = {"A": "a2", "B": "b", "C": "c", "A2": "a2"}
        for f in sorted(run_dir.glob("arm_*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            m = re.match(r"arm_([A-Za-z0-9]+)-(.+)\.json$", f.name)
            if not m:
                continue
            raw_t, qid = m.group(1).upper(), m.group(2)
            yield {"qid": qid, "track": amap.get(raw_t, raw_t.lower()),
                   "answer": str(r.get("answer") or ""),
                   "tool_calls": r.get("tool_calls") or [],
                   "texts_full": r.get("texts_full") or [], "raw": r}


def run_qids(run_dir: Path) -> list[str]:
    return sorted({str(x["qid"]) for x in _iter_run_rows(run_dir) if x["qid"]})


def qfile_candidates() -> list[Path]:
    return [SUITE / "data" / "papers" / n for n in
            ("qa_questions.json", "qa_questions_r2.json", "qa_quick10.json")]


def pick_qfile(run_dir: Path) -> Path:
    """挑与 run 题号重合度最高的题集（对不上就 fail-closed，绝不拿错金标判分）。"""
    qids = set(run_qids(run_dir))
    best, best_n = None, 0
    for p in qfile_candidates():
        if not p.exists():
            continue
        ids = {str(q.get("qid")) for q in
               json.loads(p.read_text(encoding="utf-8"))["questions"]}
        n = len(qids & ids)
        if n > best_n:
            best, best_n = p, n
    if best is None or best_n == 0:
        raise SystemExit(
            f"[paper_numbers] {run_dir.name} 的题号 {sorted(qids)[:4]}… 与任何题集都不匹配"
            "（既不是论文 BQ 集，也不是 R2/quick10）——不能对账")
    return best


def kw_hit(answer: str, kws: list[str]) -> list[str]:
    low = answer.lower()
    hits = []
    for k in kws:
        core = re.escape(k.lower())
        if k.isdigit():
            core += r"(?:st|nd|rd|th)?"
        if re.search(r"(?<![a-z0-9])" + core + r"(?![a-z0-9])", low):
            hits.append(k)
    return hits


def grade_run(run_dir: Path, qfile: Path) -> dict:
    gold = {q["qid"]: q for q in
            json.loads(qfile.read_text(encoding="utf-8"))["questions"]}
    rows = []
    unmatched = 0
    for x in _iter_run_rows(run_dir):
        r, ans = x["raw"], x["answer"]
        q = gold.get(x["qid"])
        if q is None:
            unmatched += 1
        q = q or {}
        gid = str(q.get("arxiv_id") or "")
        qid = x["qid"]
        trace = json.dumps(x["tool_calls"], ensure_ascii=False) + \
            "\n" + "\n".join(x["texts_full"])
        blob = ans + "\n" + trace
        kws = q.get("gold_keywords") or []
        hits = kw_hit(ans, kws)
        need = max(1, -(-len(kws) * 3 // 5))
        sentinel = any(s in ans for s in ("KB_TOOLS_NOT_READY", "KB_NO_RETRIEVAL"))
        cited, cited_chunk, _mk = cite_markers(ans)
        rows.append({
            "qid": qid, "track": x["track"],
            "grounded_by_question_set": q is not None,
            "gold_hit": bool(gid and (gid in blob or gid.replace("-", "/") in blob)),
            "kw_hits": hits, "kw_n": len(kws), "kw_ok": len(hits) >= need,
            "cited": cited, "cited_chunk": cited_chunk,
            "abstain": bool(RX_ABSTAIN.search(ans)),
            "sentinel": sentinel,
            "is_error": bool(r.get("error") or r.get("is_error")),
            "latency_s": r.get("latency_s"), "tools": r.get("tool_call_count"),
            "cost_usd": r.get("total_cost_usd"),
            "tokens_out": (r.get("tokens") or {}).get("output"),
        })
    for x in rows:
        x["pass"] = bool(x["gold_hit"] and x["kw_ok"] and not x["sentinel"])

    grades = {}
    for t in sorted({str(x["track"]) for x in rows}):
        tr = [x for x in rows if x["track"] == t]
        grades[t] = {
            "n": len(tr),
            "grounded": sum(x["gold_hit"] for x in tr),
            "kw": sum(x["kw_ok"] for x in tr),
            "cited": sum(x["cited"] for x in tr),
            "cited_chunk": sum(x["cited_chunk"] for x in tr),
            "pass": sum(x["pass"] for x in tr),
            "abstain": sum(x["abstain"] for x in tr),
            "latency_s": [round(x["latency_s"] or 0, 1) for x in tr],
            "avg_latency_s": round(sum(x["latency_s"] or 0 for x in tr) / len(tr), 1),
            "avg_cost_usd": round(sum(x["cost_usd"] or 0 for x in tr) / len(tr), 4),
            "avg_tools": round(sum(x["tools"] or 0 for x in tr) / len(tr), 1),
            "fails": [f"{x['qid']}"
                      f"{'(sentinel)' if x['sentinel'] else ''}"
                      f"{'(kw)' if not x['kw_ok'] else ''}"
                      f"{'(gold)' if not x['gold_hit'] else ''}"
                      for x in tr if not x["pass"]],
        }
    return {"run_dir": run_dir.name, "qfile": qfile.name, "unmatched": unmatched,
            "rows": rows, "grades": grades}


# ── 3. 对账 ─────────────────────────────────────────────────────────────────
def track_map(run_dir: Path | None = None) -> dict:
    """论文 A/B/C → 运行臂名。论文三轨（BQ 题集）= a2/b/c；
    老式检索臂 run（arm_*.json）= a2/b/c 由 `_iter_run_rows` 归一化而来。"""
    return {"A": "a2", "B": "b", "C": "c"}


def compare(paper: dict, grades: dict, run_dir: Path, rows: list | None = None,
            tol: float = 0.01) -> list[dict]:
    tm = track_map(run_dir)
    checks: list[dict] = []
    expected_n = paper.get("n_questions") or 10
    rows_by_track: dict[str, list] = {}
    for x in (rows or []):
        rows_by_track.setdefault(str(x.get("track")), []).append(x)

    def add(claim: str, p, o, ok: bool, detail: str = "") -> None:
        if isinstance(p, float) and p.is_integer():
            p = int(p)
        checks.append({"claim": claim, "paper": p, "observed": o,
                       "ok": bool(ok), "detail": detail})

    for t, tk in tm.items():
        g = grades.get(tk)
        if not g:
            add(f"track {tk} 存在", "有", "缺失", False, "run 里没有该轨")
            continue
        same_n = g["n"] == expected_n
        note = "" if same_n else f"（本轮 n={g['n']}≠{expected_n}，按实测 n 计）"
        # 计数类：n 相同就必须与论文宏精确相等；n 不同则只核对内部一致
        for key, macro in (("grounded", "grounded"), ("kw", "kw"), ("cited", "cite")):
            pv = paper[macro][t]
            ov = g[key]
            if same_n:
                ok = ov == pv
            else:
                ok = True
            add(f"{key}{tk.upper()}", pv, ov, ok, f"/{g['n']} {note}".strip())
        # 时延：论文宏是整秒；容差 max(1s, 1%)
        pl, ol = paper["lat"][t], g["avg_latency_s"]
        add(f"lat{tk.upper()}", f"{pl:g}s", f"{ol}s",
            abs(ol - pl) <= max(1.0, tol * pl), "avg/question")
        pc, oc = paper["cost"][t], g["avg_cost_usd"]
        add(f"cost{tk.upper()}", f"${pc:g}", f"${oc}",
            abs(oc - pc) <= max(0.01, tol * pc), "avg/question")
        # 失败单元：论文口径允许两类——① 工具面失败（sentinel，论文明确写
        # "both dense grounding misses were tool-availability aborts"）；
        # ② 关键词未达 60%（论文明确写 grading is conservative：裸 Agent 的
        # 复数 "cathodes" 被词边界判定判掉）。除此之外的失败都不能解释。
        if g["fails"]:
            explainable = all(("(sentinel)" in f) or ("(kw)" in f) for f in g["fails"])
            n_sent = sum(1 for f in g["fails"] if "(sentinel)" in f)
            add(f"fails{tk.upper()}", "0", f"{len(g['fails'])}: {', '.join(g['fails'])}",
                explainable,
                # 只在真出现工具面中止时才提它，否则会误导读者以为本轮的失败
                # 也是中止造成的（2026-10-13 轮 0 哨兵，失败全是词边界假阴性）。
                ("sentinel=工具面失败(论文的 tool-availability abort)；"
                 if n_sent else "本轮无工具面中止；")
                + "(kw)=保守词边界判分（论文已声明）")
        # 论文对 dense 轨的专门声明：2026-10-13 之前写的是「两次 grounding miss
        # 都是工具不可用中止」。该句只在 C 轨真的缺题时才成立，所以判据变成
        # 「正文是否还在这么写」——还在写却对不上，就是必须改的红旗。
        if tk == "c" and same_n:
            misses = [x for x in rows_by_track.get(tk, [])
                      if not x["gold_hit"]]
            aborts = [x for x in misses if x["sentinel"]]
            body = "\n".join(p.read_text(encoding="utf-8")
                             for p in PAPER_TEX.parent.glob("sec*.tex"))
            claimed = bool(re.search(r"dense grounding misses were tool-availability",
                                     body))
            if claimed:
                add("dense_aborts", f"{len(misses)} 次缺→全部为工具不可用",
                    f"{len(misses)} 次缺 · 其中哨兵 {len(aborts)}",
                    bool(misses) and len(aborts) == len(misses),
                    "论文 sec4 仍声明「both dense grounding misses were "
                    "tool-availability aborts」")
            else:
                add("dense_aborts", "论文不再声明「缺题=中止」",
                    f"C 轨缺 {len(misses)} 次 · 其中哨兵 {len(aborts)} · "
                    f"正文已无该句", True, "2026-10-13 口径：该句已删除")
    return checks
