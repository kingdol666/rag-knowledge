#!/usr/bin/env python3
"""内容问答检索评测 — 度量"检索到的内容里是否真的有答案"(content-grounded).

与 Track1 的文档级排序指标(P@5/MRR)互补: 这里以金答案串是否出现在检索命中的
chunk 正文为主指标, 直接回答"给定问题, 系统能否把含答案的内容检索回来".

方法组:
  two_stage    生产主检索: POST /api/v1/search/two-stage (服务端默认参数, 即前端同款)
  vector_flat  稠密锚点: POST /api/v1/search/vector 全库平面 top-10

指标 (对每条问题):
  AnswerRecall@k   top-k 命中 chunk 正文中包含任一金答案串(归一化) 的问题占比
  AnswerMRR        首个含答案 chunk 排名的倒数均值
  EvidenceHit@5    金文档(有 golden_titles 的数据集)出现在 top-5 文档中
  KBRoute@1        top-1 命中所库 == 金库 (仅 contentqa_corpus)
  延迟 mean/p95

数据集:
  contentqa  语料抽取式 cloze QA(build_content_qa.py 产物, 答案保证在库)
  hotpotqa / triviaqa / nq  公开真实问题(冻结子集, 含 golden_answers)

复现: 同参数重跑 --round 2, 再用 --compare 与 round1 逐字段比对.

用法:
  export RAG_BENCH_TOKEN=mcp-xxxx
  python run_content_qa.py --datasets contentqa --limit 50      # 冒烟
  python run_content_qa.py --datasets all --limit 300 --round 1 # 正式
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import random
import re
import socket
import statistics
import string
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
BENCH_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks"
SPLIT_DIR = BENCH_DIR / "kb_split"
OUT_DIR = SCRIPTS_DIR.parent / "results" / "contentqa"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BACKEND = os.environ.get("RAG_BENCH_URL", "http://localhost:8771").rstrip("/")
TOKEN = os.environ.get("RAG_BENCH_TOKEN", "")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
TOPK_EVAL = 10  # 取回并评分的深度


def validate_base_url(base: str) -> str:
    p = urlparse(base)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https: {base}")
    host = (p.hostname or "").lower()
    if host not in _LOCAL_HOSTS:
        if os.environ.get("RAG_BENCH_ALLOW_REMOTE") != "1":
            raise ValueError(f"非本机目标 {host} 被拒绝")
        for ai in socket.getaddrinfo(host, None):
            addr = ipaddress.ip_address(ai[4][0])
            if addr.is_link_local or str(addr) == "169.254.169.254":
                raise ValueError(f"目标解析到受限地址: {base}")
    return base.rstrip("/")


BASE = validate_base_url(BACKEND)


def api_post(path: str, data: dict, timeout: int = 120) -> dict:
    url = f"{BASE}{path}"
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


_PUNC_RE = re.compile(r"[{}]".format(re.escape(string.punctuation)))
_ARTICLE_RE = re.compile(r"\b(a|an|the)\b")
_SPACE_RE = re.compile(r"\s+")


def norm_answer(s: str) -> str:
    """SQuAD 协议归一化: 小写/去标点/去冠词/压空白."""
    s = s.lower()
    s = _PUNC_RE.sub(" ", s)
    s = _ARTICLE_RE.sub(" ", s)
    return _SPACE_RE.sub(" ", s).strip()


def doc_basename(doc_path: str) -> str:
    name = doc_path.replace("\\", "/").rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    name = re.sub(r" \(part \d+ of \d+\)$", "", name)  # 拆分 part 归并回原文档
    return name


def kb_of(doc_path: str) -> str:
    parts = doc_path.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 else ""


def score_item(answers: list[str], hits: list[dict], gold_title: str | None,
               gold_kb: str | None) -> dict:
    normed = [norm_answer(a) for a in answers if norm_answer(a)]
    scorable = any(len(a) >= 3 for a in normed)
    hit_rank = None
    if scorable:
        for idx, h in enumerate(hits, start=1):
            content = norm_answer(h.get("content") or "")
            if any(a in content for a in normed if len(a) >= 3):
                hit_rank = idx
                break
    ev_hit5 = None
    if gold_title:
        ev_hit5 = any(doc_basename(h.get("doc_path", "")) == gold_title
                      for h in hits[:5])
    route1 = None
    if gold_kb and hits:
        route1 = kb_of(hits[0].get("doc_path", "")) == gold_kb
    return {
        "hit_rank": hit_rank,
        "scorable": scorable,
        "evidence_hit5": ev_hit5,
        "kb_route1": route1,
        "n_hits": len(hits),
    }


def fetch_hits(method: str, question: str) -> tuple[list[dict], float]:
    t0 = time.perf_counter()
    # 批量索引并发时嵌入服务排队, 单查询可达数分钟 — 与 soul/嵌入等长窗口对齐取 600s
    if method == "two_stage":
        d = api_post("/api/v1/search/two-stage", {"query": question, "kb_id": ""},
                     timeout=600)
        hits = (d.get("stage2") or {}).get("results") or []
    elif method == "vector_flat":
        d = api_post("/api/v1/search/vector",
                     {"query": question, "kb_id": "", "top_k": TOPK_EVAL},
                     timeout=600)
        hits = d.get("results") or []
    else:
        raise ValueError(method)
    dt = time.perf_counter() - t0
    hits = sorted(hits, key=lambda x: x.get("score", 0), reverse=True)[:TOPK_EVAL]
    return hits, dt


def load_dataset(name: str, limit: int) -> list[dict]:
    if name == "contentqa":
        path = SPLIT_DIR / "contentqa_corpus.jsonl"
    else:
        path = BENCH_DIR / f"{name}.jsonl"
    items = [json.loads(line) for line in path.open(encoding="utf-8")]
    items.sort(key=lambda x: x.get("qid", ""))
    if limit and len(items) > limit:
        rng = random.Random(42)
        items = sorted(rng.sample(items, limit), key=lambda x: x.get("qid", ""))
    return items


def evaluate(dataset: str, method: str, limit: int, round_no: int,
             fail_gate: int) -> dict:
    items = load_dataset(dataset, limit)
    records = []
    latencies = []
    errors = 0
    for i, it in enumerate(items):
        q = it["question"]
        answers = it.get("golden_answers") or it.get("answers") or []
        gold_titles = it.get("golden_titles") or []
        gold_kb = it.get("gold_kb")
        try:
            hits, dt = fetch_hits(method, q)
        except Exception as exc:  # 单条失败不毁整轮, 记录后继续
            errors += 1
            if errors > fail_gate:
                raise RuntimeError(f"失败超过阈值 {fail_gate}, 中止") from exc
            records.append({"qid": it.get("qid"), "error": str(exc)[:200]})
            continue
        latencies.append(dt)
        gold_title = gold_titles[0] if gold_titles else None
        s = score_item(answers, hits, gold_title, gold_kb)
        s.update({"qid": it.get("qid"), "latency": round(dt, 4),
                  "pred_top1": hits[0].get("doc_path") if hits else ""})
        records.append(s)
        if (i + 1) % 25 == 0:
            print(f"  [{dataset}/{method}] {i+1}/{len(items)} "
                  f"recall@5 so far={_recall(records, 5):.3f}", flush=True)

    scorable = [r for r in records if r.get("scorable")]
    ev_pool = [r for r in records if r.get("evidence_hit5") is not None]
    route_pool = [r for r in records if r.get("kb_route1") is not None]

    def recall_at(k: int) -> float | None:
        if not scorable:
            return None
        return sum(1 for r in scorable if (r["hit_rank"] or 99) <= k) / len(scorable)

    mrr = (sum(1 / r["hit_rank"] for r in scorable if r["hit_rank"]) / len(scorable)
           if scorable else None)
    summary = {
        "dataset": dataset, "method": method, "round": round_no,
        "limit": limit, "n": len(items),
        "n_scorable": len(scorable), "n_errors": errors,
        "answer_recall@1": recall_at(1),
        "answer_recall@3": recall_at(3),
        "answer_recall@5": recall_at(5),
        "answer_recall@10": recall_at(10),
        "answer_mrr": mrr,
        "evidence_hit@5": (sum(1 for r in ev_pool if r["evidence_hit5"]) / len(ev_pool))
        if ev_pool else None,
        "kb_route@1": (sum(1 for r in route_pool if r["kb_route1"]) / len(route_pool))
        if route_pool else None,
        "latency_mean_s": round(statistics.mean(latencies), 4) if latencies else None,
        "latency_p95_s": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 4)
        if latencies else None,
    }
    return {"meta": {
        "backend": BASE, "generated": datetime.now(timezone.utc).isoformat(),
        "protocol": "content-grounded answer-in-retrieved-chunks (SQuAD norm)",
        "topk_eval": TOPK_EVAL,
    }, "summary": summary, "records": records}


def _recall(records: list[dict], k: int) -> float:
    sc = [r for r in records if r.get("scorable")]
    if not sc:
        return 0.0
    return sum(1 for r in sc if (r["hit_rank"] or 99) <= k) / len(sc)


def compare(path_a: str, path_b: str) -> bool:
    a = json.loads(Path(path_a).read_text(encoding="utf-8"))["summary"]
    b = json.loads(Path(path_b).read_text(encoding="utf-8"))["summary"]
    ignore = {"round", "latency_mean_s", "latency_p95_s"}
    diffs = {k: (a.get(k), b.get(k)) for k in a
             if k not in ignore and a.get(k) != b.get(k)}
    if diffs:
        print(f"REPRO FAIL {path_a} vs {path_b}: {diffs}")
        return False
    print(f"REPRO PASS {path_a} == {path_b} (metrics identical; latency ignored)")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="contentqa",
                    help="逗号组合: contentqa,hotpotqa,triviaqa,nq 或 all")
    ap.add_argument("--methods", default="two_stage,vector_flat")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--fail-gate", type=int, default=20)
    ap.add_argument("--compare", default="",
                    help="与既有结果文件比对复现: dataset,method 通配前后缀")
    args = ap.parse_args()

    if not TOKEN:
        print("需要 RAG_BENCH_TOKEN", file=sys.stderr)
        sys.exit(2)

    if args.compare:
        pattern = args.compare
        matches = sorted(OUT_DIR.glob("*.json"))
        ok = True
        for m in matches:
            if pattern in m.name and ".r1." in m.name:
                r2 = m.name.replace(".r1.", ".r2.")
                if (OUT_DIR / r2).exists():
                    ok &= compare(str(m), str(OUT_DIR / r2))
        sys.exit(0 if ok else 1)

    datasets = (["contentqa", "hotpotqa", "triviaqa", "nq"]
                if args.datasets == "all" else args.datasets.split(","))
    for dataset in datasets:
        for method in args.methods.split(","):
            print(f"== {dataset} x {method} (limit={args.limit}) ==")
            out = evaluate(dataset, method, args.limit, args.round, args.fail_gate)
            path = OUT_DIR / f"{dataset}.{method}.r{args.round}.json"
            path.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                            encoding="utf-8")
            print(f"-> {path}")
            print("   summary:", json.dumps(out["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
