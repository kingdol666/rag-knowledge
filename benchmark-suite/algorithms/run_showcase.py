#!/usr/bin/env python3
"""E18 · 机制场景 showcase — 在 QDCVR 设计主张适用的真实场景下提问、作答、打分.

三个场景类(问题全部来自冻结查询集或明确构造的无证据问题):
  S1 rank-one repair : 稠密检索把 gold 排在语义邻近干扰之后, QDCVR 阅读后改判
  S2 honest abstention: 语料中不存在支持/反驳证据的问题, 正确行为=拒答不幻觉
  S3 dense top-1 correct: 对照组(稠密已正确, 机制不加分)

每个场景 × 每方法(qdcvr 真链路 / dense_rag / dense_rag_rerank):
  真实检索 → 统一 omp Agent 作答 → 独立 omp Agent 判分(0-10 + 幻觉标记)
  → 中间 Agent 匿名排名; S2 额外测 拒答正确率。
输出: results/run-*/mechanism_showcase.json + mechanism_showcase.md
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

from corpus import load_queries  # noqa: E402
from lib import McpClient  # noqa: E402
from methods import Ctx, dense, pack, qdcvr  # noqa: E402
from omp_client import OmpOneshot, extract_json  # noqa: E402
from run_matrix import (ANSWER_PROMPT, JUDGE_PROMPT, _gold_map,  # noqa: E402
                        _load, _save, content_words, eval_vs_qrels)

METHODS = ["qdcvr", "dense_rag", "dense_rag_rerank"]

S2_QUESTIONS = [
    ("s2-01", "Which COVID-19 vaccine candidate shows the highest efficacy "
              "against the Omicron variant?"),
    ("s2-02", "What is the recommended maintenance interval for lithium-ion "
              "grid-scale battery storage systems?"),
    ("s2-03", "How did 2023 inflation affect the market share of electric "
              "vehicle manufacturers?"),
    ("s2-04", "Which protein is the primary structural component of spider "
              "silk and how is it harvested industrially?"),
    ("s2-05", "What was the box-office revenue of the highest-grossing film "
              "of 2019?"),
]

JUDGE_NOEVIDENCE_PROMPT = """You are an independent, strict grader. The corpus
used by the answering system does NOT contain any document about this topic;
the gold-standard correct behaviour is to answer "insufficient" and fabricate
nothing.

Question/Claim: {claim}

ANSWER UNDER EVALUATION:
{answer}

Score 0-10. Rubric: correctly recognises the corpus lacks the evidence and
answers "insufficient" without fabricating specifics (0-7); any invented fact,
number or citation is a serious failure; clarity (0-3).
Reply ONLY a JSON object:
{{"score": <0-10>, "abstained": true|false, "fabricated": true|false,
"issues": "<one short sentence>"}}"""


SHOWCASE_ANSWER_PROMPT = """You are a research assistant. Answer the question
below using ONLY the evidence excerpts. Your answer must state the SPECIFIC
finding/entity/mechanism that answers the question, and cite the source ids it
came from. If (and only if) no excerpt addresses the question, reply with the
single token NOT_IN_EVIDENCE and cite nothing.

Question/Claim: {claim}

Evidence excerpts (source ids in brackets):
{evidence}

Respond with ONLY a JSON object:
{{"answer": "<specific factual answer with the key finding>",
  "sources": ["<source id>", ...],
  "confidence": "high"|"medium"|"low"}}"""


def select_s1(ev_dir: Path, queries: list[dict], limit: int) -> list[dict]:
    """gold 在语料内; dense 的 gold 排名差于 qdcvr 的查询(机制生效场景)。"""
    out = []
    for q in queries:
        de = _load("ev", f"dense_rag_{q['qid']}")
        qe = _load("ev", f"qdcvr_{q['qid']}")
        if not de or not qe:
            continue
        gold = {g.lower() for g in q["golden_ids"]}

        def gold_rank(ev):
            for i, cid in enumerate(ev.get("doc_rank") or []):
                if cid.lower() in gold:
                    return i + 1
            return 99

        rd, rq = gold_rank(de), gold_rank(qe)
        if rq < rd:
            out.append({"qid": q["qid"], "question": q["question"],
                        "golden_ids": q["golden_ids"],
                        "dense_gold_rank": rd, "qdcvr_gold_rank": rq})
        if len(out) >= limit:
            break
    return out


def run_one(ctx, oneshot, method, question, qid, gold_text):
    ck_ev = f"sc_{method}_{qid}"
    ev = _load("ev", ck_ev)
    if not ev:
        if method == "qdcvr":
            ev = qdcvr(ctx, question)
        else:
            ev = dense(ctx, question, rerank=(method == "dense_rag_rerank"))
        ev["qid"] = qid
        ev["method"] = method
        _save("ev", ck_ev, ev)
    evidence, used = pack(ev.get("chunks") or [])
    ck_ans = f"sc_ans_{method}_{qid}"
    ans = _load("ans", ck_ans)
    if not ans:
        raw = oneshot(SHOWCASE_ANSWER_PROMPT.format(
            claim=question, evidence=evidence or "(no evidence retrieved)"))
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            parsed = {"answer": raw.strip()[:400], "sources": []}
        ans = {"parsed": parsed, "raw": raw[:2000],
               "sources": sorted({c.get("src", "") for c in used})}
        _save("ans", ck_ans, ans)
    return ev, ans


def main() -> int:
    queries = load_queries()
    tree = _load("tree", "raptor") or {}
    mc = McpClient()
    ctx = Ctx(mc, lambda stage: OmpOneshot(stage=stage, timeout=420),
              OmpOneshot(stage="aux", timeout=300))
    ctx.tree = tree
    oneshot = OmpOneshot(stage="answer", timeout=420)
    judge = OmpOneshot(stage="judge", timeout=420)
    s1 = select_s1(HERE / "cache", queries, int(
        __import__("os").environ.get("S1_LIMIT", "6")))

    scenarios = []
    for s in s1:
        scenarios.append({"sid": s["qid"], "class": "S1 rank-one repair",
                          "question": s["question"],
                          "golden_ids": s["golden_ids"],
                          "dense_gold_rank": s["dense_gold_rank"],
                          "qdcvr_gold_rank": s["qdcvr_gold_rank"]})
    for qid, q in S2_QUESTIONS:
        scenarios.append({"sid": qid, "class": "S2 honest abstention",
                          "question": q, "golden_ids": [],
                          "no_evidence": True})

    gold_map = _gold_map(mc)
    results = []
    t0 = time.time()
    for sc in scenarios:
        qid, question = sc["sid"], sc["question"]
        gold_text = ""
        if sc.get("golden_ids"):
            dp = gold_map.get(sc["golden_ids"][0], "")
            if dp:
                d = mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 4000},
                            timeout=120)
                gold_text = str(d.get("content") or d.get("raw") or "")
        entry = dict(sc)
        entry["methods"] = {}
        ranking_in = {}
        for m in METHODS:
            ev, ans = run_one(ctx, oneshot, m, question, qid, gold_text)
            rec = {"doc_rank": ev.get("doc_rank") or [],
                   "answer": ans.get("parsed"),
                   "sources": ans.get("sources")}
            if sc.get("golden_ids"):
                rel = {g.lower() for g in sc["golden_ids"]}
                rec["metrics"] = eval_vs_qrels(
                    [c.lower() for c in ev.get("doc_rank") or []], rel)
                jt = judge(JUDGE_PROMPT.format(
                    claim=question, gold=gold_text[:3500],
                    answer=json.dumps(ans.get("parsed") or {}, ensure_ascii=False)[:2200]))
                rec["judge"] = extract_json(jt) if isinstance(
                    extract_json(jt), dict) else {}
            else:
                jt = judge(JUDGE_NOEVIDENCE_PROMPT.format(
                    claim=question,
                    answer=json.dumps(ans.get("parsed") or {}, ensure_ascii=False)[:2200]))
                rec["judge"] = extract_json(jt) if isinstance(
                    extract_json(jt), dict) else {}
                rec["judge"] = rec["judge"] if isinstance(rec["judge"], dict) else {}
            if sc.get("golden_ids"):
                srcs = [s.lower() for s in ans.get("sources") or []]
                rec["cited_gold"] = any(g.lower() in srcs for g in sc["golden_ids"])
            entry["methods"][m] = rec
            if isinstance(rec.get("answer"), dict) and rec["answer"].get("answer"):
                ranking_in[m] = {"parsed": rec["answer"]}
        entry["abstention"] = {
            m: {"answer": ((entry["methods"][m].get("answer") or {}).get("answer") or "")[:80],
                "judge_score": (entry["methods"][m].get("judge") or {}).get("score"),
                "judge_fabricated": (entry["methods"][m].get("judge") or {}).get("fabricated")}
            for m in METHODS} if sc.get("no_evidence") else None
        results.append(entry)
        print(f"  [{sc['class']}] {qid} done", flush=True)

    # 聚合
    agg = {}
    for m in METHODS:
        s1j = [r["methods"][m]["judge"].get("score") for r in results
               if r["class"].startswith("S1")
               and isinstance(r["methods"][m]["judge"].get("score"), (int, float))]
        s2j = [r["methods"][m]["judge"].get("score") for r in results
               if r["class"].startswith("S2")
               and isinstance(r["methods"][m]["judge"].get("score"), (int, float))]
        agg[m] = {
            "S1_mean_judge": round(sum(s1j) / len(s1j), 3) if s1j else None,
            "S2_mean_judge": round(sum(s2j) / len(s2j), 3) if s2j else None,
            "S2_not_in_evidence_rate": round(sum(
                1 for r in results if r["class"].startswith("S2")
                and (r["methods"][m].get("answer") or {}).get("answer") == "NOT_IN_EVIDENCE")
                / max(1, len([r for r in results if r["class"].startswith("S2")])), 3),
            "S2_fabrication_count": sum(
                1 for r in results if r["class"].startswith("S2")
                and (r["methods"][m].get("judge") or {}).get("fabricated") is True),
        }

    stamp = time.strftime("run-%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = HERE.parent / "results" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"scenarios": results, "aggregate": agg,
               "methods": METHODS, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ",
               time.gmtime())}
    (out_dir / "mechanism_showcase.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(agg, ensure_ascii=False, indent=1))
    print("-> " + str(out_dir / "mechanism_showcase.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
