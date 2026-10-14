#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 7 — a second verification signal on the logged pools (review C10).

Round-3 review: "all generalization rests on one judge". This replays the
191 logged (query, candidate) pairs -- and the four out-of-corpus probe
pools -- through an independent Chinese NLI model (Erlangshen-Roberta-330M,
entailment probability as an evidence score), plus a symbolic substring
check on Q6's numeric watch clause. No platform judging is involved.

Outputs (results/exp7_second_signal.json):
  per-question NLI ranking metrics vs Laya's logged ordering;
  gold vs non-gold NLI score separation (medians, Mann-Whitney, Cliff's delta);
  Spearman correlation between the two signals;
  symbolic Q6 check; OOD probe pools under the NLI signal.

Run with the backend venv (torch CUDA). Model downloads on first use.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ragproject\rag-knowledge")
EXP = REPO / "paper-kbs" / "experiments"
sys.path.insert(0, str(EXP))
from kbcommon import QUESTIONS, RESULTS  # noqa: E402

HYPOTHESIS = "这段文字包含直接回答该问题所需的具体证据信息。"
MAX_CHARS = 1600
BATCH = 16


def load_pairs():
    rows = json.loads((RESULTS / "exp1_retrieval.json").read_text(
        encoding="utf-8"))["rows"]
    docs = {d["doc_path"]: d["content"]
            for d in json.loads((RESULTS / "corpus_cache.json")
                                .read_text(encoding="utf-8"))}
    pairs = []  # (qid, path, laya_score, text, is_gold)
    for r in rows:
        if r.get("method") != "qdcvr_hybrid" or "judge_scores" not in r:
            continue
        q = next(qq for qq in QUESTIONS if qq["qid"] == r["qid"])
        subs = [g.lower() for g in q["gold_doc_substrings"]]
        for p, sc in r["judge_scores"]["all"].items():
            p = p.replace("\\", "/")
            pairs.append({"qid": r["qid"], "path": p, "laya": float(sc),
                          "text": docs.get(p, "")[:MAX_CHARS],
                          "gold": any(g in p.lower() for g in subs)})
    return pairs


def nli_scores(model, tok, device, queries: list[str], texts: list[str]) -> list[float]:
    import torch
    out = []
    for i in range(0, len(queries), BATCH):
        qs = queries[i:i + BATCH]
        ts = texts[i:i + BATCH]
        enc = tok([f"问题：{q}" for q in qs], ts,
                  padding=True, truncation=True, max_length=512,
                  return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1)
        # entailment = label whose name contains 'entail' (fallback: index 0)
        ent_idx = 0
        for idx, name in model.config.id2label.items():
            if "entail" in name.lower() or "蕴含" in name:
                ent_idx = idx
                break
        out.extend(probs[:, ent_idx].float().cpu().tolist())
    return out


def cliffs_delta(a: list[float], b: list[float]) -> float:
    import bisect
    b_sorted = sorted(b)
    gt = lt = 0
    for x in a:
        gt += len(b) - bisect.bisect_right(b_sorted, x)
        lt += bisect.bisect_left(b_sorted, x)
    n = len(a) * len(b)
    return (gt - lt) / n if n else 0.0


def _ranks(vals: list[float]) -> list[float]:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def mw_two_sided(a: list[float], b: list[float]) -> float:
    """Tie-corrected normal approximation, matching scipy.mannwhitneyu."""
    import math
    n1, n2 = len(a), len(b)
    allv = a + b
    ranks = _ranks(allv)
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    tie_sum = 0.0
    i = 0
    sv = sorted(allv)
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        t = j - i + 1
        tie_sum += t ** 3 - t
        i = j + 1
    n = n1 + n2
    sigma = (n1 * n2 / 12 * ((n + 1) - tie_sum / (n * (n - 1)))) ** 0.5
    if sigma == 0:
        return 1.0
    z = (u1 - mu) / sigma
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def spearman(a: list[float], b: list[float]) -> float:
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return num / (da * db) if da and db else 0.0


import math  # noqa: E402


def main() -> int:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    name = "IDEA-CCNL/Erlangshen-Roberta-330M-NLI"
    print("device:", device, "model:", name, flush=True)
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForSequenceClassification.from_pretrained(name).to(device).eval()
    print("labels:", model.config.id2label, flush=True)

    pairs = load_pairs()
    print(f"logged pairs: {len(pairs)}, gold: {sum(p['gold'] for p in pairs)}",
          flush=True)
    scores = nli_scores(model, tok, device,
                        [next(q["text"] for q in QUESTIONS if q["qid"] == p["qid"])
                         for p in pairs],
                        [p["text"] for p in pairs])
    for p, s in zip(pairs, scores):
        p["nli"] = round(float(s), 4)

    # per-question ranking metrics under each signal
    by_q = {}
    for p in pairs:
        by_q.setdefault(p["qid"], []).append(p)

    def metrics(qid, key):
        cands = sorted(by_q[qid], key=lambda x: -x[key])
        q = next(qq for qq in QUESTIONS if qq["qid"] == qid)
        subs = [g.lower() for g in q["gold_doc_substrings"]]
        hits, best = 0, None
        for i, c in enumerate(cands[:5], 1):
            if any(s in c["path"].lower() for s in subs):
                hits += 1
                best = best or i
        return hits > 0, (1.0 / best) if best else 0.0

    per_q = []
    for qid in sorted(by_q):
        l_hit, l_mrr = metrics(qid, "laya")
        n_hit, n_mrr = metrics(qid, "nli")
        per_q.append({"qid": qid, "laya_hit": l_hit, "laya_mrr": l_mrr,
                      "nli_hit": n_hit, "nli_mrr": n_mrr})
        print(f"{qid}: laya {l_hit}/{l_mrr:.2f}  nli {n_hit}/{n_mrr:.2f}",
              flush=True)

    golds = [p["nli"] for p in pairs if p["gold"]]
    nongs = [p["nli"] for p in pairs if not p["gold"]]
    rho = spearman([p["laya"] for p in pairs], [p["nli"] for p in pairs])
    summary = {
        "model": name, "n_pairs": len(pairs),
        "nli_hit5": sum(r["nli_hit"] for r in per_q) / len(per_q),
        "nli_mrr": sum(r["nli_mrr"] for r in per_q) / len(per_q),
        "laya_hit5": sum(r["laya_hit"] for r in per_q) / len(per_q),
        "laya_mrr": sum(r["laya_mrr"] for r in per_q) / len(per_q),
        "nli_gold_median": statistics.median(golds),
        "nli_nongold_median": statistics.median(nongs),
        "nli_gold_min": min(golds), "nli_nongold_max": max(nongs),
        "mw_p": mw_two_sided(golds, nongs),
        "cliffs_delta": cliffs_delta(golds, nongs),
        "spearman_rho": rho,
        "per_question": per_q,
        "pairs": pairs,
    }
    print(f"\nNLI  hit@5={summary['nli_hit5']:.2f} mrr={summary['nli_mrr']:.3f}")
    print(f"Laya hit@5={summary['laya_hit5']:.2f} mrr={summary['laya_mrr']:.3f}")
    print(f"NLI gold median={summary['nli_gold_median']:.3f} "
          f"min={summary['nli_gold_min']:.3f} | non-gold median="
          f"{summary['nli_nongold_median']:.3f} max={summary['nli_nongold_max']:.3f}")
    print(f"MW p={summary['mw_p']:.2e}  delta={summary['cliffs_delta']:.2f}  "
          f"spearman rho={summary['spearman_rho']:.3f}")

    # symbolic check on Q6's numeric watch clause
    docs = {d["doc_path"]: d["content"]
            for d in json.loads((RESULTS / "corpus_cache.json")
                                .read_text(encoding="utf-8"))}
    q6 = by_q["Q6"]
    symbolic = {p["path"]: ("31.35" in docs.get(p["path"], "")) for p in q6}
    golds_sym = [v for p, v in symbolic.items()
                 if any(g in p.lower() for g in
                        next(q for q in QUESTIONS if q["qid"] == "Q6")
                        ["gold_doc_substrings"])]
    nongs_sym = [v for p, v in symbolic.items() if p not in
                 [x for x in symbolic if any(
                     g in x.lower() for g in
                     next(q for q in QUESTIONS if q["qid"] == "Q6")
                     ["gold_doc_substrings"])]]
    summary["q6_symbolic"] = {
        "gold_contains_3135": sum(golds_sym), "gold_n": len(golds_sym),
        "nongold_contains_3135": sum(nongs_sym), "nongold_n": len(nongs_sym)}
    print(f"Q6 symbolic: gold {sum(golds_sym)}/{len(golds_sym)} contain 31.35; "
          f"non-gold {sum(nongs_sym)}/{len(nongs_sym)}")

    # OOD: full-corpus NLI scores under out-of-corpus topics
    print("\nscoring OOD topics over full corpus (4 x 42 pairs)...", flush=True)
    ood = []
    topics = {"O1": "锂电池热失控的处置流程", "O2": "儿童疫苗接种时间表",
              "O3": "Python并发编程的线程同步方法", "O4": "注塑模具排气槽的设计要点"}
    all_docs = [{"path": k, "text": v[:MAX_CHARS]} for k, v in docs.items()]
    qs, ts, meta = [], [], []
    for oid, topic in topics.items():
        for d in all_docs:
            qs.append(topic)
            ts.append(d["text"])
            meta.append((oid, d["path"]))
    ood_scores = nli_scores(model, tok, device, qs, ts)
    for (oid, path), s in zip(meta, ood_scores):
        ood.append({"qid": oid, "path": path, "nli": round(float(s), 4)})
    ood_summary = {}
    for oid in topics:
        vals = [o["nli"] for o in ood if o["qid"] == oid]
        ood_summary[oid] = {"max": max(vals), "median": statistics.median(vals),
                            "above_0.5": sum(v >= 0.5 for v in vals),
                            "above_0.8": sum(v >= 0.8 for v in vals)}
        print(f"OOD {oid}: max={max(vals):.3f} median={statistics.median(vals):.3f} "
              f"n>=0.5: {ood_summary[oid]['above_0.5']}/42 n>=0.8: "
              f"{ood_summary[oid]['above_0.8']}/42")
    summary["ood_full_corpus"] = {"per_doc": ood, "summary": ood_summary}

    out = RESULTS / "exp7_second_signal.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
