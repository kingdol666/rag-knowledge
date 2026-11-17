# -*- coding: utf-8 -*-
"""S5 附表（sanity 下限，非主表）：BM25 / dense / RRF 检索层对比——免 LLM 可执行。

定位声明：传统 RAG 检索器**不进主表**（用户裁定）；本脚本仅产出附表数据（trace schema
与 s4 一致、gold 判据同源），证明平台主通道相对"纯检索器"的增益可测。
主表内容认知基线（CRAG/Self-RAG/RAPTOR/HippoRAG/LightRAG）需要 OpenAI 兼容 LLM 端点
——当前环境缺失，按纪律如实记为阻塞性依赖（差一个端点即可跑，适配器已定义）。

用法: uv run --no-sync --directory backend python s5_floor.py [--limit 40]
产出: artifacts/s5_floor.json（arm: F-bm25 / F-dense / F-rrf）
"""
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"

TOKEN = ""
for line in (BASE.parents[2] / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
        break
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
WIN = 2000  # BM25 unit 粒度


def load_units():
    """(unit_id, text) 单元集：非 PDF 文档按 2000 字符窗口切分。"""
    spec = json.loads((ART / "corpus_spec_final.json").read_text(encoding="utf-8"))
    units = []
    for m in spec:
        for d in m["docs"]:
            p = CORPUS / d["file"]
            if not p.exists() or d["file"].lower().endswith(".pdf"):
                continue
            t = p.read_text(encoding="utf-8", errors="replace")
            for i in range(0, len(t), WIN):
                units.append((f"{d['file']}#w{i}", t[i:i + WIN]))
    return units


def tok(s):
    return re.findall(r"[\w\u4e00-\u9fff]+", s.lower())


def bm25_rank(query, docs, dfs, doc_tf, N, top_k=10):
    qt = tok(query)
    score = Counter()
    for i, tf in enumerate(doc_tf):
        dl = sum(tf.values())
        s = 0.0
        for w in qt:
            if w in tf:
                idf = math.log(1 + (N - dfs[w] + 0.5) / (dfs[w] + 0.5))
                s += idf * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * dl / 400))
        score[i] = s
    return [(docs[i][0], s, docs[i][1]) for i, s in
            sorted(score.items(), key=lambda kv: -kv[1])[:top_k] if s > 0]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    questions = [json.loads(l) for l in
                 (ART / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    questions = [q for q in questions if q.get("kind") == "gold" and not q.get("evidence_pending")]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 40
    questions = questions[:limit]
    docs = load_units()
    doc_tf = [Counter(tok(t)) for _, t in docs]
    dfs = Counter()
    for tf in doc_tf:
        for w in tf:
            dfs[w] += 1
    N = len(docs)
    corpus_bytes = sum(len(t.encode("utf-8")) for _, t in docs)
    print(f"floor arms on {len(questions)} golds over {N} units (~{corpus_bytes//1024}KB)")
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    out = {"F-bm25": [], "F-dense": [], "F-rrf": []}
    for q in questions:
        ev = q["gold_evidence"].lower()
        t0 = time.time()
        bm = bm25_rank(q["question"], docs, dfs, doc_tf, N)
        t_bm = round(time.time() - t0, 2)
        t0 = time.time()
        r = cli.post("http://127.0.0.1:8771/api/v1/search/vector",
                     json={"query": q["question"], "kb_id": "", "top_k": 30,
                           "score_threshold": 0.3, "balance_kbs": True})
        hits = r.json().get("results") or []
        t_dn = round(time.time() - t0, 2)
        seen, dense = set(), []
        for h in hits:
            dp = str(h.get("doc_path") or h.get("path") or "?").replace("\\", "/")
            if dp in seen:
                continue
            seen.add(dp)
            dense.append((dp, h.get("score", 0) or 0, str(h.get("content") or h.get("text") or "")))
            if len(dense) >= 10:
                break
        for arm, ranked, secs in (("F-bm25", bm, t_bm), ("F-dense", dense, t_dn)):
            joined = "\n".join(txt for _, _, txt in ranked)
            tr = dict(qid=q["id"], arm=arm, query=q["question"], is_refusal=False,
                      gold_hit=bool(ev) and ev in joined.lower(),
                      bytes_ingested=len(joined.encode("utf-8")),
                      evidence_focus=(len(joined.encode("utf-8")) / max(corpus_bytes, 1)),
                      top1=ranked[0][0] if ranked else "",
                      calls=1, tool_seconds=secs, llm_digest_seconds=None,
                      refusal_ok=None)
            out[arm].append(tr)
        rrf_join = "\n".join(t for _, _, t in bm[:5]) + "\n" + "\n".join(t for _, _, t in dense[:5])
        out["F-rrf"].append(dict(
            qid=q["id"], arm="F-rrf", query=q["question"], is_refusal=False,
            gold_hit=bool(ev) and ev in rrf_join.lower(),
            bytes_ingested=len(rrf_join.encode("utf-8")),
            evidence_focus=len(rrf_join.encode("utf-8")) / max(corpus_bytes, 1),
            top1=bm[0][0] if bm else (dense[0][0] if dense else ""),
            calls=2, tool_seconds=round(t_bm + t_dn, 2), llm_digest_seconds=None, refusal_ok=None))
    (ART / "s5_floor.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for arm, rows in out.items():
        g = sum(1 for x in rows if x.get("gold_hit"))
        print(f"=== {arm}: gold {g}/{len(rows)}")


if __name__ == "__main__":
    main()
