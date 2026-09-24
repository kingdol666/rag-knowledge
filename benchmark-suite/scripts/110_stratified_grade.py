#!/usr/bin/env python3
"""分层评分器 — 三轨实验的证据化评分（P0-1 / P0-4 / P1-11 的修法）。

相比 107_exp_grade.py 的三处升级：
  1. **分层**：按题目层（single / multihop / crosskb / distractor /
     unanswerable / outofcorpus）分别报数，而不是一个总的 pass rate。
     这样 FPR、not-found 正确率、误拒率才有 ground truth。
  2. **L2 judge 层**：用**外部**模型按答案要点打分，输出 correctness(0/1) 与
     quality(0-5)。judge 必须与被测系统解耦（禁止用本平台当 judge）。
     确定性层（L1）保留为回归层，不被替换。
  3. **L3 人工层**：载入人工标注，算 Cohen's κ 与 LLM-vs-human 一致率，
     把 "0-8 rubric 是未校准仪器" 变成可报告的校准证据。

用法
----
    # 只跑确定性层 + 分层（不需要外部依赖）
    python scripts/110_stratified_grade.py --run experiment_chat_20260922-211000 \
        --qfile data/papers/qa_questions_r2.json

    # 加 judge 层（外部 OpenAI 兼容端点，env 配置）
    export JUDGE_ENDPOINT=https://api.deepseek.com/v1/chat/completions
    export JUDGE_MODEL=deepseek-chat
    export JUDGE_API_KEY=...
    python scripts/110_stratified_grade.py --run <dir> --qfile <json> --judge

    # 加人工层
    python scripts/110_stratified_grade.py --run <dir> --qfile <json> \
        --human data/papers/human_labels.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"

# 题层定义：answerable 层期望"答对"，refusal 层期望"正确拒答"
ANSWERABLE = ("single", "multihop", "crosskb", "distractor")
REFUSAL = ("unanswerable", "outofcorpus")
ALL_STRATA = ANSWERABLE + REFUSAL

ABSTAIN_MARKERS = ("insufficient", "not found", "no evidence",
                   "does not contain", "cannot be answered",
                   "not present in", "outside the")


# --------------------------------------------------------------------------
# L1 — 确定性层（与 107_exp_grade.py 同口径，保留为回归层）
# --------------------------------------------------------------------------
def kw_hits(answer: str, kws: list) -> list:
    low = answer.lower()
    out = []
    for k in kws:
        core = re.escape(str(k).lower())
        if str(k).isdigit():
            core += r"(?:st|nd|rd|th)?"
        if re.search(r"(?<![a-z0-9])" + core + r"(?![a-z0-9])", low):
            out.append(k)
    return out


def gold_hit(q: dict, blob: str) -> bool:
    for key in ("arxiv_id", "gold_doc", "gold_slug"):
        gid = q.get(key)
        if not gid:
            continue
        gid = str(gid)
        if gid in blob or gid.replace("-", "/") in blob:
            return True
    for d in q.get("gold_docs", []) or []:
        if str(d) in blob:
            return True
    return False


def looks_abstained(answer: str, cited_gold: bool = False) -> bool:
    """拒答判定。

    不能只看关键词：2026-09-24 实测发现 A 轨的五段式回答在 "Blind Spots" 段里
    常写 "the evidence does not contain ..."，会被纯关键词检测器误判为拒答
    （旧启发式下 A 轨误拒率虚高到 3/10）。真实拒答的特征是**没有引用任何证据**，
    因此这里要求：出现拒答措辞 ∧ 未命中任何金标来源。
    """
    if cited_gold:
        return False
    low = answer.lower()
    return any(m in low for m in ABSTAIN_MARKERS)


# --------------------------------------------------------------------------
# L2 — judge 层（外部模型，与被测系统解耦）
# --------------------------------------------------------------------------
JUDGE_SYSTEM = (
    "You are a strict grader in a retrieval experiment. You are given a question, "
    "the reference answer points, and a system's answer. Decide whether the answer "
    "is CORRECT: it must affirmatively answer the question and be supported by the "
    "reference points. Do not reward hedging, partial restatement, or correct topic "
    "with wrong specifics. If the question has no answer in the corpus, the only "
    "correct behaviour is an explicit statement that the evidence is insufficient. "
    "Reply with JSON only: {\"correct\": 0|1, \"quality\": 0-5, \"reason\": \"<=25 words\"}."
)


def judge_one(question: str, points: list, answer: str) -> dict | None:
    ep = os.environ.get("JUDGE_ENDPOINT", "")
    key = os.environ.get("JUDGE_API_KEY", "")
    model = os.environ.get("JUDGE_MODEL", "")
    if not (ep and key and model):
        return None
    if ep.rstrip("/").endswith("chat/completions") and "127.0.0.1" in ep:
        # 硬约束：禁止用被测平台自身当 judge
        raise SystemExit("[judge] refusing to use the platform under test as judge")
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": json.dumps({
                "question": question,
                "reference_points": points,
                "answer": answer}, ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(ep, method="POST",
                                 data=json.dumps(body).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = json.loads(r.read().decode("utf-8"))
    txt = raw["choices"][0]["message"]["content"]
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0)) if m else None


# --------------------------------------------------------------------------
# L3 — 一致性
# --------------------------------------------------------------------------
def cohen_kappa(a: list, b: list) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    cats = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="")
    ap.add_argument("--qfile", default="data/papers/qa_questions_r2.json")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--human", default="")
    ap.add_argument("--out", default="stratified_grade.json")
    args = ap.parse_args()

    sys.path.insert(0, str(SUITE / "scripts"))
    from lib import resolve_run_dir
    run_dir = resolve_run_dir(args.run)
    qfile = SUITE / args.qfile
    gold = {q["qid"]: q for q in
            json.loads(qfile.read_text(encoding="utf-8"))["questions"]}

    files = sorted(run_dir.glob("track_*.json"))
    if not files:
        print(f"no track_*.json under {run_dir}")
        return 1

    human = {}
    if args.human:
        human = json.loads((SUITE / args.human).read_text(encoding="utf-8"))

    rows = []
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        q = gold.get(r.get("qid"), {})
        answer = str(r.get("answer") or "")
        trace = json.dumps(r.get("tool_calls") or [], ensure_ascii=False) + \
            "\n" + "\n".join(r.get("texts_full") or [])
        blob = answer + "\n" + trace
        kws = q.get("gold_keywords", []) or []
        hits = kw_hits(answer, kws)
        need = max(1, -(-len(kws) * 3 // 5))
        stratum = q.get("stratum") or "single"
        gh = gold_hit(q, blob)
        abst = looks_abstained(answer, cited_gold=gh)

        row = {
            "qid": r.get("qid"), "track": r.get("track"), "stratum": stratum,
            "gold_hit": gh, "kw": hits, "kw_ok": len(hits) >= need,
            "abstained": abst,
            "latency_s": r.get("latency_s"), "tools": r.get("tool_call_count"),
            "cost_usd": r.get("total_cost_usd"),
            "is_error": r.get("is_error"),
        }
        if args.judge:
            pts = q.get("gold_points") or kws
            j = judge_one(q.get("question", ""), pts, answer)
            row["judge_correct"] = (j or {}).get("correct")
            row["judge_quality"] = (j or {}).get("quality")
        rows.append(row)

    def has_judge(rows):
        return any(r.get("judge_correct") is not None for r in rows)

    # ---- 聚合 ----
    tracks = sorted({r["track"] for r in rows})
    out = {"run_dir": run_dir.name, "qfile": qfile.name,
           "judge_enabled": has_judge(rows), "per_track": {}}

    for t in tracks:
        tr = [r for r in rows if r["track"] == t]
        g = {"n": len(tr),
             "gold_hit": sum(r["gold_hit"] for r in tr),
             "kw_ok": sum(r["kw_ok"] for r in tr),
             "pass": sum(r["gold_hit"] and r["kw_ok"] for r in tr)}
        g["pass_rate"] = round(g["pass"] / len(tr), 3)
        # 诚实性两向指标
        refusal_rows = [r for r in tr if r["stratum"] in REFUSAL]
        answer_rows = [r for r in tr if r["stratum"] in ANSWERABLE]
        g["correct_refusal"] = sum(r["abstained"] for r in refusal_rows)
        g["refusal_n"] = len(refusal_rows)
        g["over_refusal"] = sum(r["abstained"] for r in answer_rows)
        g["answerable_n"] = len(answer_rows)
        g["notfound_accuracy"] = round(
            g["correct_refusal"] / len(refusal_rows), 3) if refusal_rows else None
        g["over_refusal_rate"] = round(
            g["over_refusal"] / len(answer_rows), 3) if answer_rows else None
        # judge
        if has_judge(tr):
            jr = [r for r in tr if r.get("judge_correct") is not None]
            g["judge_correct"] = sum(r["judge_correct"] for r in jr)
            g["judge_n"] = len(jr)
            g["judge_acc"] = round(sum(r["judge_correct"] for r in jr) / len(jr), 3)
            qs = [r["judge_quality"] for r in jr if r.get("judge_quality") is not None]
            g["judge_quality_mean"] = round(sum(qs) / len(qs), 2) if qs else None
        # 分层
        g["by_stratum"] = {}
        for s in ALL_STRATA:
            sr = [r for r in tr if r["stratum"] == s]
            if not sr:
                continue
            g["by_stratum"][s] = {
                "n": len(sr),
                "pass": sum(r["gold_hit"] and r["kw_ok"] for r in sr),
                "gold_hit": sum(r["gold_hit"] for r in sr),
                "abstained": sum(r["abstained"] for r in sr),
                "judge_correct": sum(1 for r in sr if r.get("judge_correct") == 1)
                if has_judge(sr) else None,
            }
        lat = [r["latency_s"] or 0 for r in tr]
        g["avg_latency_s"] = round(sum(lat) / len(tr), 1)
        g["avg_cost_usd"] = round(sum(r["cost_usd"] or 0 for r in tr) / len(tr), 4)
        out["per_track"][t] = g

    # ---- 一致性 ----
    if human:
        pairs = {}
        for r in rows:
            h = human.get(f"{r['track']}:{r['qid']}")
            if h is not None and r.get("judge_correct") is not None:
                pairs.setdefault(r["track"], ([], []))
                pairs[r["track"]][0].append(int(r["judge_correct"]))
                pairs[r["track"]][1].append(int(h))
        out["agreement"] = {
            t: {"cohen_kappa": cohen_kappa(a, b), "n": len(a)}
            for t, (a, b) in pairs.items()}

    (RESULTS / args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # 逐题结果落盘为 <run>/judge.json（供 115_stats / 116_report 消费）。
    # 只在 judge 层启用时写出——没有 judge 就没有主因变量。
    if has_judge(rows):
        jrows = [{"qid": r["qid"], "method": r["track"],
                  "correct": r.get("judge_correct"),
                  "quality": r.get("judge_quality"),
                  "stratum": r["stratum"], "abstained": r["abstained"]}
                 for r in rows]
        (run_dir / "judge.json").write_text(
            json.dumps({"run_id": run_dir.name, "judge_enabled": True,
                        "rows": jrows}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"[judge] rows → {run_dir / 'judge.json'}")

    # ---- 报告 ----
    L = ["# 分层评分报告", "",
         f"Run: `{run_dir.name}` · 题集: `{qfile.name}` · "
         f"judge: {'ON' if has_judge(rows) else 'OFF'}", "",
         "## 总表", "",
         "| 轨 | n | pass | gold | kw | 分层可答 n | 误拒 | 应拒答 n | 正确拒答 | 平均时延 s | 平均成本 $ |",
         "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for t in tracks:
        g = out["per_track"][t]
        L.append(f"| {str(t).upper()} | {g['n']} | {g['pass']} ({g['pass_rate']}) | "
                 f"{g['gold_hit']} | {g['kw_ok']} | {g['answerable_n']} | "
                 f"{g['over_refusal']} ({g['over_refusal_rate']}) | "
                 f"{g['refusal_n']} | {g['correct_refusal']} "
                 f"({g['notfound_accuracy']}) | {g['avg_latency_s']} | "
                 f"{g['avg_cost_usd']} |")
    if has_judge(rows):
        L += ["", "## Judge 层", "", "| 轨 | n | correct | acc | quality(0-5) |",
              "|---|---|---:|---:|---:|"]
        for t in tracks:
            g = out["per_track"][t]
            if g.get("judge_n"):
                L.append(f"| {str(t).upper()} | {g['judge_n']} | {g['judge_correct']} | "
                         f"{g['judge_acc']} | {g['judge_quality_mean']} |")
    L += ["", "## 分层明细", "",
          "| 轨 | 层 | n | pass | gold | 拒答 | judge correct |",
          "|---|---|---:|---:|---:|---:|---:|"]
    for t in tracks:
        for s, d in out["per_track"][t]["by_stratum"].items():
            L.append(f"| {str(t).upper()} | {s} | {d['n']} | {d['pass']} | "
                     f"{d['gold_hit']} | {d['abstained']} | {d['judge_correct']} |")
    if out.get("agreement"):
        L += ["", "## Judge vs 人工一致性", "", "| 轨 | n | Cohen's κ |", "|---|---:|---:|"]
        for t, a in out["agreement"].items():
            L.append(f"| {str(t).upper()} | {a['n']} | {a['cohen_kappa']} |")
    L += ["", "## 口径", "",
          "- `pass` = 金标可追溯 ∧ ≥60% 金标关键词（L1 确定性层，与 107 同口径，仅作回归）。",
          "- **主因变量是 judge correctness**，不是 pass。",
          "- `误拒` = 应可答题中却拒答的比例（越低越好）；`正确拒答` = 应拒答题中确实拒答的比例（越高越好）。",
          "- 两个方向必须同时报告——只报拒答正确率的规则，等价于「永远拒答」。", ""]
    (RESULTS / args.out.replace(".json", ".md")).write_text(
        "\n".join(L), encoding="utf-8")
    print(f"[stratified] → {RESULTS / args.out}")
    print(f"[report]     → {RESULTS / args.out.replace('.json', '.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
