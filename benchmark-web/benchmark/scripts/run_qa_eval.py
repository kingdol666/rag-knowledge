#!/usr/bin/env python3
"""端到端 QA 评测 — EM/F1（与 HiRAG Table 5 / Adaptive-RAG 直接可比协议）.

流程(每条查询):
  1. 系统检索: /search/two-stage 取 top-5 chunk 作为上下文
  2. 答案生成: OpenAI 兼容 API（RAG_QA_BASE_URL / RAG_QA_API_KEY / RAG_QA_MODEL）
     prompt 固定 → 提示词与温度写入结果文件（复现凭证）
  3. 评分: EM(归一化精确匹配) + token-F1（Rajpurhan 协议, 与 Adaptive-RAG 相同）
     Acc: golden answer 是否为预测答案子串（Adaptive-RAG 的 Acc 定义）

用法:
  export RAG_BENCH_TOKEN=mcp-xxxx
  export RAG_QA_BASE_URL=https://api.xxx/v1   # OpenAI 兼容端点
  export RAG_QA_API_KEY=sk-xxx
  export RAG_QA_MODEL=deepseek-v4-pro
  python run_qa_eval.py --dataset hotpotqa --limit 200
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import statistics
import string
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BENCH_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

BACKEND = os.environ.get("RAG_BENCH_URL", "http://localhost:8770").rstrip("/")
QA_URL = os.environ.get("RAG_QA_BASE_URL", "")
QA_KEY = os.environ.get("RAG_QA_API_KEY", "")
QA_MODEL = os.environ.get("RAG_QA_MODEL", "")

PROMPT_TEMPLATE = (
    "Answer the question using ONLY the context below. "
    "Be concise: reply with the answer only, no explanation.\n\n"
    "Context:\n{context}\n\nQuestion: {question}\nAnswer:")


def validate_url(base: str) -> str:
    """仅允许 https(远程)/http(回环), 禁止链路本地与云元数据地址。"""
    p = urlparse(base)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https: {base}")
    host = (p.hostname or "").lower()
    if p.scheme == "http" and host not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("http 仅限本机回环; 远程必须用 https")
    if p.scheme == "https" and host not in ("localhost", "127.0.0.1", "::1"):
        infos = {ai[4][0] for ai in socket.getaddrinfo(host, None)}
        for ip in infos:
            addr = ipaddress.ip_address(ip)
            if addr.is_link_local or str(addr) == "169.254.169.254":
                raise ValueError(f"目标解析到受限地址: {ip}")
    return base.rstrip("/")


def normalize_answer(s: str) -> str:
    """SQuAD 协议: 小写/去标点/去冠词/压空白"""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def f1_score(pred: str, golden: list[str]) -> float:
    return max(_f1(pred, g) for g in golden)


def _f1(pred: str, golden: str) -> float:
    pt, gt = normalize_answer(pred).split(), normalize_answer(golden).split()
    common = Counter(pt) & Counter(gt)
    num_same = sum(common.values())
    if len(pt) == 0 or len(gt) == 0:
        return float(pt == gt)
    if num_same == 0:
        return 0.0
    precision = num_same / len(pt)
    recall = num_same / len(gt)
    return 2 * precision * recall / (precision + recall)


def em_score(pred: str, golden: list[str]) -> float:
    return float(any(normalize_answer(pred) == normalize_answer(g) for g in golden))


def acc_score(pred: str, golden: list[str]) -> float:
    """Adaptive-RAG 的 Acc: golden 是否包含于预测(或预测包含 golden)"""
    np_, ng = normalize_answer(pred), [normalize_answer(g) for g in golden]
    return float(any(g in np_ or np_ in g for g in ng if g))


def retrieve(query: str, token: str, top_k: int = 5) -> list[dict]:
    req = urllib.request.Request(
        f"{BACKEND}/api/v1/search/two-stage",
        data=json.dumps({"query": query, "kb_id": "", "stage2_top_k": top_k,
                         "score_threshold": 0.0}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read()).get("results", [])


def generate(context: str, question: str) -> str:
    url = f"{validate_url(QA_URL)}/chat/completions"
    body = json.dumps({
        "model": QA_MODEL, "temperature": 0.0,
        "messages": [{"role": "user",
                      "content": PROMPT_TEMPLATE.format(context=context, question=question)}],
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {QA_KEY}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"].strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    token = os.environ.get("RAG_BENCH_TOKEN", "")
    if not token or not QA_URL or not QA_KEY or not QA_MODEL:
        print("❌ 需要 RAG_BENCH_TOKEN / RAG_QA_BASE_URL / RAG_QA_API_KEY / RAG_QA_MODEL")
        return 2

    samples = [json.loads(l) for l in
               (BENCH_DIR / f"{args.dataset}.jsonl").open(encoding="utf-8") if l.strip()]
    if args.limit:
        samples = samples[:args.limit]

    ems, f1s, accs, lats = [], [], [], []
    detail_path = RESULTS_DIR / f"qa-{args.dataset}-detail.jsonl"
    with detail_path.open("w", encoding="utf-8") as fd:
        for i, s in enumerate(samples):
            try:
                results = retrieve(s["question"], token, args.top_k)
                context = "\n\n".join(f"[{j+1}] {r.get('content','')[:800]}"
                                      for j, r in enumerate(results))
                t0 = time.perf_counter()
                answer = generate(context, s["question"]) if context.strip() else ""
                lats.append((time.perf_counter() - t0) * 1000)
            except Exception as e:  # 单条失败不终止评测, 记为 0
                print(f"  [{i}] error: {e}")
                answer = ""
            golden = s["golden_answers"]
            em, f1, acc = em_score(answer, golden), f1_score(answer, golden), acc_score(answer, golden)
            ems.append(em); f1s.append(f1); accs.append(acc)
            fd.write(json.dumps({"qid": s["qid"], "question": s["question"],
                                 "golden": golden, "prediction": answer,
                                 "em": em, "f1": round(f1, 4), "acc": acc},
                                ensure_ascii=False) + "\n")
            if (i + 1) % 25 == 0:
                print(f"  [{i+1}/{len(samples)}] EM={statistics.mean(ems):.3f} "
                      f"F1={statistics.mean(f1s):.3f}", flush=True)

    report = {
        "dataset": args.dataset, "n": len(samples), "model": QA_MODEL,
        "retrieval": "two-stage top-%d" % args.top_k,
        "temperature": 0.0, "prompt": PROMPT_TEMPLATE[:200],
        "EM": round(statistics.mean(ems), 4), "F1": round(statistics.mean(f1s), 4),
        "Acc": round(statistics.mean(accs), 4),
        "latency_ms": round(statistics.mean(lats), 1) if lats else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    out = RESULTS_DIR / f"qa-{args.dataset}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
