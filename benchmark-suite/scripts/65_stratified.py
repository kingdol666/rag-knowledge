#!/usr/bin/env python3
"""E14 · 词汇重叠分层分析（响应评审 Q2: 按重叠触发裁决能否消除负效应）.

对 SciFact(30 查询) 与 HotpotQA(50 查询) 的逐查询结果按
"查询内容词在金标文档(标题)中的覆盖率"分为 高/低 两层(以中位数为界),
逐层比较 qdcvr vs two_stage 的 Hit@1 与 nDCG@10 —— 检验论文的
"词汇重叠边界"主张, 并估算"按重叠触发裁决"策略的潜在收益。
纯分析: 使用已冻结的逐查询 JSON + 查询/文档标题, 无新检索调用。
输出: results/run-*/stratified_adjudication.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DATA, RESULTS, doc_basename, mean, now_iso, set_run  # noqa: E402

STOP = set("""the a an of in on for to and or is are was were be been being with as
by at from that this these those it its we our their they he she his her you your
i not no do does did can could may might will would should shall than then so such
which who whom whose what when where why how""".split())


def content_words(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{2,}", text.lower()) if t not in STOP]


def gold_title_of(q: dict, dataset: str) -> str:
    if dataset == "hotpotqa":
        return " ".join(q["golden_titles"])
    # scifact: golden_ids -> 标题在文件名中
    docs = DATA / "standard2" / "scifact" / "docs"
    titles = []
    for gid in q["golden_ids"]:
        for f in docs.glob(f"*[{gid}].md"):
            titles.append(f.name.split(" [")[0])
    return " ".join(titles)


def stratify(per_query: list[dict], qs: dict, dataset: str):
    rows = []
    for r in per_query:
        q = qs[r["qid"]]
        qwords = set(content_words(q["question"]))
        gwords = set(content_words(gold_title_of(q, dataset)))
        cov = (len(qwords & gwords) / len(qwords)) if qwords else 0.0
        rows.append({**r, "_cov": cov})
    rows.sort(key=lambda r: r["_cov"])
    med = rows[len(rows) // 2]["_cov"]
    low = [r for r in rows if r["_cov"] <= med]
    high = [r for r in rows if r["_cov"] > med]
    return {"low": low, "high": high, "median_cov": round(med, 4)}


def agg(rows, method_field_prefix=""):
    out = {}
    for m in ("two_stage", "qdcvr"):
        sub = rows
        out[m] = {
            "hit@1": round(mean(r["hit@1"] for r in sub), 4),
            "ndcg@10": round(mean(r["ndcg@10"] for r in sub), 4),
            "n": len(sub)}
    out["delta_hit1"] = round(out["qdcvr"]["hit@1"] - out["two_stage"]["hit@1"], 4)
    out["delta_ndcg"] = round(out["qdcvr"]["ndcg@10"] - out["two_stage"]["ndcg@10"], 4)
    return out


def main() -> int:
    outdir = set_run()
    result = {"experiment": "E14 overlap-stratified adjudication (review Q2)",
              "datasets": {}}

    # ── HotpotQA ──
    hot_files = sorted(RESULTS.glob("run-*/hotpot_main_1.json"))
    if hot_files:
        d = json.loads(hot_files[-1].read_text(encoding="utf-8"))
        qs = {q["qid"]: q for q in
              (json.loads(l) for l in
               (DATA / "hotpotqa" / "queries.jsonl").open(encoding="utf-8"))}
        paired = {}
        for m in ("two_stage", "qdcvr"):
            for r in d["rows"][m]:
                paired.setdefault(r["qid"], {})[m] = r
        per_query = []
        for qid, pr in paired.items():
            merged = {"qid": qid}
            for m in ("two_stage", "qdcvr"):
                for k in ("hit@1", "ndcg@10"):
                    merged[f"{m}_{k}"] = pr[m][k]
            per_query.append(merged)
        # 改造 stratify 输入: 直接用 two_stage 行携带 golden 覆盖
        rows = []
        for r in d["rows"]["two_stage"]:
            q = qs[r["qid"]]
            qwords = set(content_words(q["question"]))
            gwords = set(content_words(" ".join(q["golden_titles"])))
            cov = (len(qwords & gwords) / len(qwords)) if qwords else 0.0
            qrow = next(x for x in d["rows"]["qdcvr"] if x["qid"] == r["qid"])
            rows.append({"qid": r["qid"], "cov": cov,
                         "ts_hit1": r["hit@1"], "ts_ndcg": r["ndcg@10"],
                         "qd_hit1": qrow["hit@1"], "qd_ndcg": qrow["ndcg@10"]})
        def build_strata(rows):
            rows = sorted(rows, key=lambda r: r["cov"])
            n = len(rows)
            med = rows[n // 2]["cov"]
            out = {}
            for name, filt in (("low_overlap", lambda r: r["cov"] <= med),
                               ("high_overlap", lambda r: r["cov"] > med)):
                sub = [r for r in rows if filt(r)]
                if not sub:
                    continue
                out[name] = {
                    "n": len(sub), "median_cov": round(med, 4),
                    "two_stage_hit1": round(mean(r["ts_hit1"] for r in sub), 4),
                    "qdcvr_hit1": round(mean(r["qd_hit1"] for r in sub), 4),
                    "two_stage_ndcg": round(mean(r["ts_ndcg"] for r in sub), 4),
                    "qdcvr_ndcg": round(mean(r["qd_ndcg"] for r in sub), 4)}
                out[name]["delta_hit1"] = round(
                    out[name]["qdcvr_hit1"] - out[name]["two_stage_hit1"], 4)
                out[name]["delta_ndcg"] = round(
                    out[name]["qdcvr_ndcg"] - out[name]["two_stage_ndcg"], 4)
            if len(out) == 2:
                mix_hit1 = (out["high_overlap"]["qdcvr_hit1"] * out["high_overlap"]["n"]
                            + out["low_overlap"]["two_stage_hit1"]
                            * out["low_overlap"]["n"]) / n
                mix_ndcg = (out["high_overlap"]["qdcvr_ndcg"] * out["high_overlap"]["n"]
                            + out["low_overlap"]["two_stage_ndcg"]
                            * out["low_overlap"]["n"]) / n
                out["overlap_conditioned_mix"] = {
                    "hit@1": round(mix_hit1, 4), "ndcg@10": round(mix_ndcg, 4),
                    "note": "route to qdcvr when query-gold-title overlap > median, "
                            "else two_stage (oracle router on the boundary variable)"}
            return out

        strata = build_strata(rows)
        result["datasets"]["hotpotqa"] = strata

    # ── SciFact ──
    sf_files = sorted(RESULTS.glob("run-*/../../module_b_std2_r1.json"))
    sf_file = RESULTS / "module_b_std2_r1.json"
    if sf_file.exists():
        d = json.loads(sf_file.read_text(encoding="utf-8"))
        qs = {q["qid"]: q for q in
              (json.loads(l) for l in
               (DATA / "standard2" / "scifact" / "queries.jsonl").open(encoding="utf-8"))}
        rows = []
        for r in d["rows"]["scifact"]["twostage"]:
            q = qs[r["qid"]]
            qwords = set(content_words(q["question"]))
            gwords = set(content_words(gold_title_of(q, "scifact")))
            cov = (len(qwords & gwords) / len(qwords)) if qwords else 0.0
            qrow = next(x for x in d["rows"]["scifact"]["qdcvr"]
                        if x["qid"] == r["qid"])
            rows.append({"qid": r["qid"], "cov": cov,
                         "ts_hit1": r["hit@1"], "ts_ndcg": r["ndcg@10"],
                         "qd_hit1": qrow["hit@1"], "qd_ndcg": qrow["ndcg@10"]})
        strata = build_strata(rows)
        result["datasets"]["scifact"] = strata

    result["meta"] = {"generated": now_iso(),
                      "note": "overlap = share of query content words (stopwords "
                              "removed) present in gold document title(s); strata "
                              "split at the median. Pure analysis of frozen "
                              "per-query artefacts."}
    out = outdir / "stratified_adjudication.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print(json.dumps(result["datasets"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
