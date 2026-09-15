#!/usr/bin/env python3
"""拉取 MIRACL zh/ja 跨语言评测语料 — 冻结查询集 + Wikipedia 页面快照.

协议(确定性):
  1. 下载 MIRACL v1.0 dev topics+qrels (HF, <200KB/语言) 缓存到 data/miracl/
  2. dev 查询按 qid 排序取前 N_Q 条 → 金标页 = 其 qrels positives 的 pageid
     干扰页 = 后续 [N_Q, N_Q+N_DQ) 条查询的金标页 (同域、与金标集去重),
     按 sha256(title) 稳定序采样 → 与英文语料协议一致
  3. Wikipedia API (prop=extracts, explaintext) 按 pageid 批量拉正文,
     快照写 data/benchmarks/kb_split/pages_KB-CrossLang-{ZH,JA}.jsonl
  4. 查询集写 data/benchmarks/miracl-{zh,ja}-dev.jsonl
     {qid, question, golden_pages:[titles], lang}
  5. MANIFEST 记录 sha256/来源/时间 → 复现凭证

用法: python fetch_crosslang_corpus.py [--n-queries 60] [--n-distractors 400]
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks"
MIRACL_DIR = SCRIPTS_DIR.parent / "data" / "miracl"
SPLIT_DIR = DATA_DIR / "kb_split"
MIRACL_DIR.mkdir(parents=True, exist_ok=True)

HF_BASE = "https://huggingface.co/datasets/miracl/miracl/resolve/main"
LANGS = {
    "en": {"wiki": "https://en.wikipedia.org/w/api.php", "kb": "KB-CrossLang-EN"},
    "zh": {"wiki": "https://zh.wikipedia.org/w/api.php", "kb": "KB-CrossLang-ZH"},
    "ja": {"wiki": "https://ja.wikipedia.org/w/api.php", "kb": "KB-CrossLang-JA"},
}
UA = "rag-knowledge-benchmark/1.0 (local research; contact: local)"

# ── SSRF 边界(本脚本唯一出口 http_get): 仅 https + 字面域名白名单,
#    且解析出的 IP 不得为回环/私网/链路本地/云元数据 —— 防 DNS rebinding. ──
ALLOWED_HOSTS = frozenset({"datasets-server.huggingface.co", "huggingface.co", "en.wikipedia.org",
                           "zh.wikipedia.org", "ja.wikipedia.org"})


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
                    or addr.is_reserved or addr.is_multicast
                    or str(addr) in ("169.254.169.254", "0.0.0.0")):
                raise ValueError(f"目标解析到受限地址: {host} -> {addr}")
    except socket.gaierror:
        # 本机 DNS 无法解析白名单域(由出站代理负责解析与 TLS);
        # 白名单校验已通过, 此处放行由代理解析。
        if not (os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
                or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")):
            raise ValueError(f"DNS 解析失败且未配置出站代理: {host}")
    return url


def http_get(url: str, timeout: int = 60, retries: int = 4) -> bytes:
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


def fetch_miracl(lang: str) -> tuple[list[dict], dict[str, list[str]], str, str]:
    """返回 (queries sorted by qid, {qid: [docid...]}, topics_url, qrels_url) — 缓存本地."""
    tsv_url = f"{HF_BASE}/miracl-v1.0-{lang}/topics/topics.miracl-v1.0-{lang}-dev.tsv"
    qr_url = f"{HF_BASE}/miracl-v1.0-{lang}/qrels/qrels.miracl-v1.0-{lang}-dev.tsv"
    tsv_path = MIRACL_DIR / f"topics.miracl-v1.0-{lang}-dev.tsv"
    qr_path = MIRACL_DIR / f"qrels.miracl-v1.0-{lang}-dev.tsv"
    if not tsv_path.exists():
        tsv_path.write_bytes(http_get(tsv_url))
    if not qr_path.exists():
        qr_path.write_bytes(http_get(qr_url))

    queries = []
    for line in tsv_path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2:
            queries.append({"qid": parts[0], "question": parts[1]})
    queries.sort(key=lambda x: x["qid"])
    qrels: dict[str, list[str]] = {}
    for line in qr_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[3].strip() == "1":
            qrels.setdefault(parts[0], []).append(parts[2])
    return queries, qrels, tsv_url, qr_url


def wiki_rows(lang: str, n_pages: int = 400, length: int = 100) -> list[dict]:
    """datasets-server /rows 顺序取页 — 每语言 3-4 次请求, 无 429 风险.

    返回 [{pageid, title, extract}]; 文本过短(<200)的跳过.
    """
    cfg = f"20231101.{lang}"
    out = []
    offset = 0
    while len(out) < n_pages:
        q = ("https://datasets-server.huggingface.co/rows?dataset=wikimedia%2Fwikipedia"
             f"&config={cfg}&split=train&offset={offset}&length={length}")
        data = None
        for attempt in range(4):
            try:
                data = json.loads(http_get(q, timeout=90))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  rows offset={offset}: {str(e)[:60]}, retry", flush=True)
                time.sleep(20)
        if not data or "rows" not in data:
            print(f"  rows offset={offset}: unavailable, stop at {len(out)}", flush=True)
            break
        rows_list = data["rows"] if isinstance(data["rows"], list)             else data["rows"].get("rows") or []
        for r in rows_list:
            text = r.get("row", {}).get("text") or ""
            if len(text) >= 200:
                out.append({"pageid": str(r.get("row", {}).get("id")),
                            "title": r.get("row", {}).get("title", ""),
                            "extract": text})
            if len(out) >= n_pages:
                break
        offset += length
        if offset > 5000:  # 安全上限
            break
    return out


# ── 多语言 cloze 查询构建(与英文 CorpusClozeQA 同协议) ──
_YEAR_RE = re.compile(r"\b(1[5-9][0-9]{2}|20[0-2][0-9])\b")
_SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


def cloze_queries(pages: list[dict], kb: str, lang: str,
                  per_page: int = 1, max_items: int = 40) -> list[dict]:
    """确定性抽取式 cloze 查询: 金答案 span 保证存在于页面正文."""
    section_words = ("参见", "參見", "参考文献", "參考文獻", "注释", "註釋",
                     "外部链接", "外部連結", "参考书目", "延伸阅读", "関連項目",
                     "脚注", "注釋", "出典", "外部リンク", "Notes", "References",
                     "See also", "External links", "Bibliography")
    items = []
    for p in pages:
        content = p["extract"].replace("\n", " ")
        for sentence in _SENT_SPLIT.split(content):
            if not (60 <= len(sentence) <= 300):
                continue
            if any(ch in sentence for ch in "|\n\t"):
                continue
            if any(w in sentence[:14] for w in section_words):
                continue  # 导航/注释段
            if lang in ("zh", "ja") and sentence.count(" ") > 10:
                continue  # 条目名罗列非叙述句
            if lang in ("zh", "ja") and not re.search(r"[，。、；：「」『』（）！？]", sentence):
                continue  # 书目/ISBN 条目无 CJK 标点
            m = _YEAR_RE.search(sentence)
            if m and not sentence.startswith(m.group(1)):
                span = m.group(1)
                masked = sentence.replace(span, "____", 1)
                items.append({"qid": f"mqa-{lang}-{len(items)+1:03d}",
                              "question": masked, "answers": [span],
                              "golden_pages": [p["title"]], "lang": lang})
                break
        if len(items) >= max_items:
            break
    return items


def docid_to_pageid(docid: str) -> str:
    return docid.split("#", 1)[0]


def wiki_page_via_datasets_server(lang: str, pageid: str) -> dict | None:
    """datasets-server /filter 按 pageid 取页(id 字段=pageid) — 绕开 Wikipedia 429."""
    cfg = f"20231101.{lang}"
    q = (f"https://datasets-server.huggingface.co/filter?dataset=wikimedia%2Fwikipedia"
         f"&config={cfg}&split=train&where=%22id%22%3D%27{pageid}%27&length=5")
    for attempt in range(4):
        try:
            data = json.loads(http_get(q, timeout=60))
            if "rows" in data:
                best = None
                for row in data["rows"].get("rows") or data["rows"] or []:
                    if str(row.get("id")) == pageid and len(row.get("text") or "") >= 200:
                        best = row
                        break
                if best:
                    return {"title": best.get("title", ""),
                            "extract": best.get("text", "")}
                return None
            # 索引未就绪等场景
            time.sleep(30)
        except Exception:  # noqa: BLE001
            time.sleep(15)
    return None


def wiki_extract_batch(api: str, pageids: list[str], cache_path: Path,
                       lang: str = "zh") -> dict[str, dict]:
    """一批 pageid → {pageid: {title, extract}}; 429 长退避 + 磁盘缓存断点续拉."""
    out: dict[str, dict] = {}
    if cache_path.exists():
        out = json.loads(cache_path.read_text(encoding="utf-8"))
        out = {k: v for k, v in out.items() if len(v.get("extract") or "") >= 200}
    todo = [p for p in pageids if p not in out]
    print(f"  cached={len(out)} todo={len(todo)}", flush=True)
    # 主源: datasets-server 按页取(无 429); 后备: Wikipedia API 批量
    for idx, pid in enumerate(todo):
        row = wiki_page_via_datasets_server(lang, pid)
        if row:
            out[pid] = row
        if (idx + 1) % 10 == 0:
            cache_path.write_text(json.dumps(out, ensure_ascii=False),
                                  encoding="utf-8")
            print(f"  progress: {len(out)}/{len(pageids)}", flush=True)
    cache_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    if len(todo) > 0:
        print(f"  datasets-server got {len(out)}/{len(pageids)}; "
              f"fallback Wikipedia API for {len(pageids)-len(out)}", flush=True)
    todo = [p for p in pageids if p not in out]
    batch = 10
    for start in range(0, len(todo), batch):
        chunk = todo[start:start + batch]
        q = (f"{api}?action=query&prop=extracts&explaintext=1&redirects=1"
             f"&format=json&formatversion=2&pageids={'|'.join(chunk)}")
        data = None
        for attempt in range(1, 7):  # 429: 60→120→240→480s 指数退避
            try:
                data = json.loads(http_get(q, timeout=90))
                break
            except urllib.error.HTTPError as e:
                wait = min(480, 60 * attempt) if e.code == 429 else 15 * attempt
                print(f"  batch {start//batch+1}: HTTP {e.code}, wait {wait}s "
                      f"(attempt {attempt}/6)", flush=True)
                time.sleep(wait)
            except Exception as e:  # noqa: BLE001
                print(f"  batch {start//batch+1}: {e}, wait 20s", flush=True)
                time.sleep(20)
        if data is None:
            continue  # 该批放弃(计入 coverage 报告)
        for page in (data.get("query") or {}).get("pages") or []:
            extract = page.get("extract") or ""
            if page.get("missing") or len(extract) < 200:
                continue
            out[str(page["pageid"])] = {"title": page.get("title", ""),
                                        "extract": extract}
        cache_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"  progress: {len(out)}/{len(pageids)}", flush=True)
        time.sleep(8)  # 礼貌限速
    return out


def stable_sample(items: list, n: int) -> list:
    return sorted(items, key=lambda x: hashlib.sha256(str(x).encode()).hexdigest())[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-pages", type=int, default=400,
                    help="每语言入库页数(datasets-server /rows 顺序取)")
    ap.add_argument("--n-queries", type=int, default=40,
                    help="每语言 cloze 查询数上限")
    args = ap.parse_args()

    for lang, cfg in LANGS.items():
        print(f"[{lang}] fetching {args.n_pages} pages via datasets-server /rows",
              flush=True)
        pages = wiki_rows(lang, n_pages=args.n_pages)
        print(f"[{lang}] got {len(pages)} usable pages", flush=True)

        queries = cloze_queries(pages, cfg["kb"], lang,
                                max_items=args.n_queries)
        print(f"[{lang}] cloze queries={len(queries)}", flush=True)

        qpath = DATA_DIR / f"cloze-{lang}-dev.jsonl"
        with qpath.open("w", encoding="utf-8") as fh:
            for item in queries:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

        corpus = [{"title": p["title"], "kb": cfg["kb"], "content": p["extract"],
                   "pageid": p["pageid"], "gold": True}
                  for p in pages]
        cpath = SPLIT_DIR / f"pages_{cfg['kb']}.jsonl"
        with cpath.open("w", encoding="utf-8") as fh:
            for item in corpus:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        digest = hashlib.sha256(cpath.read_bytes()).hexdigest()[:16]
        qdigest = hashlib.sha256(qpath.read_bytes()).hexdigest()[:16]
        print(f"[{lang}] corpus={len(corpus)} pages -> {cpath} "
              f"(sha256_16={digest})", flush=True)

        manifest_path = SPLIT_DIR / f"crosslang-manifest-{lang}.json"
        manifest_path.write_text(json.dumps({
            "lang": lang, "kb": cfg["kb"],
            "source": ("wikimedia/wikipedia 20231101 via datasets-server /rows, "
                       "offset=0 顺序取样; 查询=确定性 cloze 协议(年份 span)"),
            "rows_url": ("https://datasets-server.huggingface.co/rows"
                         "?dataset=wikimedia%2Fwikipedia"),
            "n_queries": len(queries), "n_pages": len(corpus),
            "corpus_sha256_16": digest,
            "queries_sha256_16": qdigest,
            "fetched": time.strftime("%Y-%m-%d"),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
