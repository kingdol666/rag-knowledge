#!/usr/bin/env python3
"""下载标准 RAG 评测语料并确定性子集化 — BEIR SciFact + SQuAD v1.1 dev.

1. BEIR SciFact (检索基准, 带 qrels 相关性判定 — 支持标准 Recall/nDCG 指标):
   官方 zip (~5MB) → corpus.jsonl(5183 篇)/queries.jsonl(300)/qrels(test.tsv)
   子集: qid 排序后前 --n-queries 条查询, 金标 docs = 其 qrels 相关文档,
   干扰文档 = sha256 稳定序采样 → 每篇 corpus 文档写为一个 .md
2. SQuAD v1.1 dev (抽取式问答标准基准, 自包含 context):
   取 title 排序后前 --squad-articles 篇, 每篇合并 context 为一个 .md,
   每篇取前 --qs-per-article 个问题(含标准答案)

产出(全部冻结, manifest 记录 sha256):
  data/standard2/scifact/{md 文件, queries.jsonl, qrels.tsv}
  data/standard2/squad/{md 文件, queries.jsonl}
"""
from __future__ import annotations

import hashlib
import io
import ipaddress
import json
import socket
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

SUITE = Path(__file__).resolve().parent.parent
OUT = SUITE / "data" / "standard2"
OUT.mkdir(parents=True, exist_ok=True)

UA = "rag-knowledge-benchmark/1.0 (local research)"
SOURCES = {
    "scifact": "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip",
    "squad": "https://raw.githubusercontent.com/rajpurkar/SQuAD-explorer/master/dataset/dev-v1.1.json",
}
ALLOWED_HOSTS = frozenset({
    "public.ukp.informatik.tu-darmstadt.de",
    "raw.githubusercontent.com",
})


def check_target(url: str) -> str:
    p = urlparse(url)
    if p.scheme != "https":
        raise ValueError(f"仅允许 https: {url}")
    host = (p.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"非白名单域名被拒绝: {host}")
    try:
        for ai in socket.getaddrinfo(host, None):
            addr = ipaddress.ip_address(ai[4][0])
            if (addr.is_loopback or addr.is_private or addr.is_link_local
                    or addr.is_reserved or addr.is_multicast):
                raise ValueError(f"目标解析到受限地址: {host} -> {addr}")
    except socket.gaierror:
        if not any(os.environ.get(k) for k in
                   ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY")):
            raise ValueError(f"DNS 解析失败且未配置出站代理: {host}")
    return url


def http_get(url: str, timeout: int = 180, retries: int = 4) -> bytes:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(check_target(url), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * attempt)
    raise last  # type: ignore[misc]


def stable_sample(items, n: int) -> list:
    return sorted(items, key=lambda x: hashlib.sha256(
        str(x).encode()).hexdigest())[:n]


def scifact(n_queries: int, n_distractors: int) -> None:
    out = OUT / "scifact"
    out.mkdir(parents=True, exist_ok=True)
    zip_path = OUT / "scifact.zip"
    if not zip_path.exists():
        print("downloading BEIR scifact.zip (~5MB)...", flush=True)
        zip_path.write_bytes(http_get(SOURCES["scifact"], timeout=300))
    with zipfile.ZipFile(io.BytesIO(zip_path.read_bytes())) as z:
        names = z.namelist()
        corpus_name = next(n for n in names if n.endswith("corpus.jsonl"))
        queries_name = next(n for n in names if n.endswith("queries.jsonl"))
        qrels_name = next(n for n in names if "qrels" in n and n.endswith(".tsv"))
        corpus_raw = z.read(corpus_name).decode("utf-8")
        queries_raw = z.read(queries_name).decode("utf-8")
        qrels_raw = z.read(qrels_name).decode("utf-8")

    corpus = {json.loads(l)["_id"]: json.loads(l)
              for l in corpus_raw.splitlines() if l.strip()}
    queries = [json.loads(l) for l in queries_raw.splitlines() if l.strip()]
    queries.sort(key=lambda q: q["_id"])
    qrels: dict[str, set[str]] = {}
    for line in qrels_raw.splitlines():
        parts = line.split("\t") if "\t" in line else line.split()
        # BEIR 格式: 表头 query-id\tcorpus-id\tscore, 数据行 3 列 score>0 为相关
        if len(parts) >= 3 and parts[0] != "query-id":
            try:
                if int(parts[2]) > 0:
                    qrels.setdefault(parts[0], set()).add(parts[1])
            except ValueError:
                continue

    eval_qs = [q for q in queries if q["_id"] in qrels][:n_queries]
    gold_ids: set[str] = set()
    kept = []
    for q in eval_qs:
        rel = qrels.get(q["_id"], set()) & set(corpus)
        if not rel:
            continue
        gold_ids |= rel
        kept.append(q)
    distractors = {cid for cid in stable_sample(
        sorted(set(corpus) - gold_ids), n_distractors)}
    print(f"[scifact] queries={len(kept)} gold_docs={len(gold_ids)} "
          f"distractors={len(distractors)}")

    for old in out.glob("*.md"):
        old.unlink()
    qrows = []
    for i, q in enumerate(kept, start=1):
        qid = f"sf-{i:03d}"
        qrows.append({"qid": qid, "question": q["text"],
                      "golden_ids": sorted(qrels.get(q["_id"], set())),
                      "kb": "KB-SciFact"})
    (out / "queries.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in qrows) + "\n",
        encoding="utf-8")
    (out / "qrels.tsv").write_text(qrels_raw, encoding="utf-8")

    n_md = 0
    for cid in sorted(gold_ids | distractors):
        doc = corpus[cid]
        title = doc.get("title") or cid
        text = doc.get("text") or ""
        if len(text) < 100:
            continue
        safe = re_sub(title)
        (out / f"{safe} [{cid}].md").write_text(
            f"# {title}\n\n{text}\n", encoding="utf-8")
        n_md += 1
    digest = hashlib.sha256(
        "\n".join(sorted(gold_ids | distractors)).encode()).hexdigest()[:16]
    (OUT / "manifest-scifact.json").write_text(json.dumps({
        "source": SOURCES["scifact"], "n_queries": len(kept),
        "n_docs_md": n_md, "gold_docs": len(gold_ids),
        "subset_sha256_16": digest,
        "fetched": time.strftime("%Y-%m-%d"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[scifact] md docs={n_md} -> {out} (sha256_16={digest})", flush=True)


def re_sub(title: str) -> str:
    import re
    s = re.sub(r'[\\/:*?"<>|]', "_", title).strip().rstrip(".")
    return (s or "untitled")[:80]


def squad(articles_n: int, qs_per_article: int) -> None:
    out = OUT / "squad"
    out.mkdir(parents=True, exist_ok=True)
    raw = http_get(SOURCES["squad"], timeout=300)
    data = json.loads(raw)["data"]
    articles = sorted(data, key=lambda a: a["title"])[:articles_n]
    for old in out.glob("*.md"):
        old.unlink()
    qrows = []
    for art in articles:
        title = art["title"]
        contexts = [p["context"] for p in art.get("paragraphs") or []]
        body = "\n\n".join(contexts)
        safe = re_sub(title)
        (out / f"{safe}.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        qas = [qa for p in art.get("paragraphs") or [] for qa in p.get("qas") or []]
        for qa in qas[:qs_per_article]:
            answers = [a["text"] for a in qa.get("answers") or []]
            if not answers:
                continue
            qrows.append({
                "qid": f"squad-{hashlib.sha1(qa['id'].encode()).hexdigest()[:8]}",
                "question": qa["question"], "golden_pages": [title],
                "answers": answers, "kb": "KB-SQuAD"})
    (out / "queries-squad.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in qrows) + "\n",
        encoding="utf-8")
    digest = hashlib.sha256(
        json.dumps(articles, ensure_ascii=False).encode()).hexdigest()[:16]
    (OUT / "manifest-squad.json").write_text(json.dumps({
        "source": SOURCES["squad"], "articles": len(articles),
        "queries": len(qrows), "subset_sha256_16": digest,
        "fetched": time.strftime("%Y-%m-%d"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[squad] articles={len(articles)} queries={len(qrows)} -> {out}",
          flush=True)


def main() -> int:
    scifact(n_queries=30, n_distractors=120)
    squad(articles_n=8, qs_per_article=2)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
