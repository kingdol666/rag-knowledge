#!/usr/bin/env python3
"""标准 RAG 语料赛道 — 从 XQuAD(标准跨语言问答基准) 确定性抽取子集.

XQuAD: google-deepmind/xquad, 每语言 1190 问, 自包含 context+question+answers,
en/zh/ja 三语对齐(同一段落集合的专业翻译) — 标准基准且零外部页面依赖。

子集协议(确定性): 每语言取 title 排序后的前 --n-articles 篇文章, 每篇最多
--qs-per-article 问 → 语料 md = 该文章全部 context 拼接, 查询金标 = 文章 title,
答案 = answers[0].text(用于内容级答案命中指标)。

产出: data/standard/{lang}/*.md + data/standard/queries-std.jsonl + manifest.json
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SUITE = Path(__file__).resolve().parent.parent
OUT = SUITE / "data" / "standard"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://raw.githubusercontent.com/google-deepmind/xquad/master"
# XQuAD 无 ja 文件(11 语言) — 标准赛道覆盖 en/zh; ja 由自建 demo 赛道覆盖
LANGS = {"en": "KB-Std-EN", "zh": "KB-Std-ZH"}
UA = "rag-knowledge-benchmark/1.0 (local research)"

# SSRF 边界: 仅 https + 字面域名白名单 + 解析结果非私网/回环/元数据
ALLOWED_HOSTS = frozenset({"raw.githubusercontent.com"})


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


def http_get(url: str, timeout: int = 90, retries: int = 4) -> bytes:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(check_target(url),
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * attempt)
    raise last  # type: ignore[misc]


def main() -> int:
    all_queries = []
    manifest = {}
    for lang, kb in LANGS.items():
        raw = http_get(f"{BASE}/xquad.{lang}.json")
        data = json.loads(raw)["data"]
        articles = sorted(data, key=lambda d: d["title"])[:8]
        lang_dir = OUT / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        for old in lang_dir.glob("*.md"):
            old.unlink()
        queries = []
        for art in articles:
            title = art["title"]
            paras = art.get("paragraphs") or []
            body = "\n\n".join(p["context"] for p in paras)
            safe = title.replace("/", "-")
            (lang_dir / f"{safe}.md").write_text(
                f"# {title}\n\n{body}\n", encoding="utf-8")
            qas = [qa for p in paras for qa in (p.get("qas") or [])]
            for qa in qas[:2]:
                answers = [a["text"] for a in qa.get("answers") or []]
                queries.append({
                    "qid": f"xq-{lang}-{hashlib.sha1(qa['id'].encode()).hexdigest()[:8]}",
                    "lang": lang, "question": qa["question"],
                    "golden_pages": [title], "answers": answers, "kb": kb,
                })
        all_queries.extend(queries)
        digest = hashlib.sha256(
            json.dumps(articles, ensure_ascii=False).encode()).hexdigest()[:16]
        manifest[lang] = {"kb": kb, "articles": len(articles),
                          "queries": len(queries), "source": f"xquad.{lang}.json",
                          "subset_sha256_16": digest}
        print(f"[{lang}] articles={len(articles)} queries={len(queries)}",
              flush=True)

    qpath = OUT / "queries-std.jsonl"
    with qpath.open("w", encoding="utf-8") as fh:
        for q in all_queries:
            fh.write(json.dumps(q, ensure_ascii=False) + "\n")
    (OUT / "manifest.json").write_text(
        json.dumps({"source": "XQuAD (CC BY-SA), subset", "langs": manifest,
                    "fetched": time.strftime("%Y-%m-%d"),
                    "total_queries": len(all_queries)},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total queries={len(all_queries)} -> {qpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
