#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 9 — span-level NLI and judge ensemble (Round-4 editor suggestion).

Round-4: the document-head NLI probe invites the strawman objection. This
replays the same 191 logged pairs with span-level scoring: each document is
cut into ~320-character spans (64-char stride, <=40 spans), every span is
scored by the same NLI model, and the document's score is the max span
score. Also computes a per-question rank-fusion ensemble (mean of ranks)
between the shipped judge and span-NLI.

Run with the backend venv (torch CUDA).
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

SPAN = 320
STRIDE = 64
MAX_SPANS = 40
BATCH = 24


def span_max_scores(model, tok, device, pairs):
    from exp7_second_signal import nli_scores  # reuse the scorer
    q_texts = {q["qid"]: q["text"] for q in QUESTIONS}
    queries, texts, meta = [], [], []
    for idx, p in enumerate(pairs):
        t = p["full_text"]
        if not t:
            p["nli_span"] = 0.0
            continue
        spans, pos = [], 0
        while pos < len(t) and len(spans) < MAX_SPANS:
            spans.append(t[pos:pos + SPAN])
            pos += STRIDE
        q = q_texts[p["qid"]]
        queries.extend([q] * len(spans))
        texts.extend(spans)
        meta.append((idx, len(spans)))
    print(f"span inferences: {len(texts)} over {len(meta)} docs", flush=True)
    scores = nli_scores(model, tok, device, queries, texts)
    out = [0.0] * len(pairs)
    cur = 0
    for idx, n in meta:
        out[idx] = max(scores[cur:cur + n])
        cur += n
    return out


def rank_fuse(per_q, key_a, key_b):
    hits = mrrs = 0
    for qid, cands in per_q.items():
        ra = {c["path"]: i + 1 for i, c in enumerate(
            sorted(cands, key=lambda x: -x[key_a]))}
        rb = {c["path"]: i + 1 for i, c in enumerate(
            sorted(cands, key=lambda x: -x[key_b]))}
        fused = sorted(cands, key=lambda c: (ra[c["path"]] + rb[c["path"]]) / 2)
        subs = next(q["gold_doc_substrings"] for q in QUESTIONS
                    if q["qid"] == qid)
        best = None
        for i, c in enumerate(fused[:5], 1):
            if any(s.lower() in c["path"].lower() for s in subs):
                best = i
                break
        hits += best is not None
        mrrs += (1.0 / best) if best else 0.0
    n = len(per_q)
    return hits / n, mrrs / n


def main() -> int:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from scipy.stats import mannwhitneyu

    device = "cuda" if torch.cuda.is_available() else "cpu"
    name = "IDEA-CCNL/Erlangshen-Roberta-330M-NLI"
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForSequenceClassification.from_pretrained(name).to(device).eval()

    docs = {d["doc_path"]: d["content"]
            for d in json.loads((RESULTS / "corpus_cache.json")
                                .read_text(encoding="utf-8"))}
    e7 = json.loads((RESULTS / "exp7_second_signal.json").read_text(
        encoding="utf-8"))
    pairs = []
    for p in e7["pairs"]:
        p = dict(p)
        p["full_text"] = docs.get(p["path"], "")
        pairs.append(p)
    print(f"pairs: {len(pairs)}", flush=True)

    span_scores = span_max_scores(model, tok, device, pairs)
    for p, s in zip(pairs, span_scores):
        p["nli_span"] = round(float(s), 4)

    per_q = {}
    for p in pairs:
        per_q.setdefault(p["qid"], []).append(p)

    def metrics(key):
        hits = mrrs = 0
        for qid, cands in per_q.items():
            subs = next(q["gold_doc_substrings"] for q in QUESTIONS
                        if q["qid"] == qid)
            best = None
            for i, c in enumerate(sorted(cands, key=lambda x: -x[key])[:5], 1):
                if any(s.lower() in c["path"].lower() for s in subs):
                    best = i
                    break
            hits += best is not None
            mrrs += (1.0 / best) if best else 0.0
        n = len(per_q)
        return hits / n, mrrs / n

    res = {}
    for key, label in (("laya", "laya"), ("nli", "nli_head"),
                       ("nli_span", "nli_span")):
        h, m = metrics(key)
        res[label] = {"hit5": h, "mrr": m}
        print(f"{label:<9} hit@5={h:.3f} mrr={m:.3f}", flush=True)
    eh, em = rank_fuse(per_q, "laya", "nli_span")
    res["ensemble_rank"] = {"hit5": eh, "mrr": em}
    print(f"ensemble  hit@5={eh:.3f} mrr={em:.3f}")

    golds = [p["nli_span"] for p in pairs if p["gold"]]
    nongs = [p["nli_span"] for p in pairs if not p["gold"]]
    res["span_separation"] = {
        "gold_median": statistics.median(golds),
        "nongold_median": statistics.median(nongs),
        "gold_min": min(golds), "nongold_max": max(nongs),
        "mw_p": mannwhitneyu(golds, nongs, alternative="two-sided").pvalue,
    }
    print(f"span separation: gold med={res['span_separation']['gold_median']:.4f} "
          f"min={res['span_separation']['gold_min']:.4f} | nongold "
          f"med={res['span_separation']['nongold_median']:.4f} "
          f"max={res['span_separation']['nongold_max']:.4f} "
          f"p={res['span_separation']['mw_p']:.2e}")

    out = RESULTS / "exp9_span_nli.json"
    out.write_text(json.dumps({"summary": res, "pairs": pairs},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
