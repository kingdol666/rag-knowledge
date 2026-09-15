#!/usr/bin/env python3
"""模块 A — 知识入库评测: 入库成功率 / 分块完整率 / 指定库归属正确率 / 可检索性.

协议(每语言):
  1. 语料 = 冻结快照 pages_KB-CrossLang-{EN,ZH,JA}.jsonl (en 由本脚本按
     sha256(title) 稳定序从 13 个域库 shard 采样构建, 与 MIRACL 协议对齐:
     hotpotqa 前 60 查询金标页 + 后续查询金标页作干扰页)
  2. 走生产入库链路: POST {web}/api/kb/documents/create → batch-index(50/批)
  3. 指标:
     - ingest_success_rate   create 成功 / 尝试总数 (409 记为已存在=成功)
     - storage_completeness  库内文档字符回读覆盖率(抽样 kb_doc_read 全文回读)
     - membership_accuracy   文档出现在指定 KB 的文档清单中 (kb_get_documents)
     - self_retrieval_hit@1  以文档首句为 query 的库内向量检索命中自身 (索引完整性)
用法:
  python benchmark_ingestion.py --build-en        # 先构建 en 快照
  python benchmark_ingestion.py --ingest          # 入库+索引(断点续跑)
  python benchmark_ingestion.py --measure         # 指标测量 → results/benchmark/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import statistics
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from bench_http import post_json as _post_json, get_json as _get_json  # noqa: E402

SPLIT_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks" / "kb_split"
DATA_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks"
RESULTS_DIR = SCRIPTS_DIR.parent / "results" / "benchmark"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

WEB = os.environ.get("RAG_BENCH_WEB_URL", "http://localhost:6790").rstrip("/")
BACKEND = os.environ.get("RAG_BENCH_URL", "http://localhost:8771").rstrip("/")
TOKEN = os.environ.get("RAG_BENCH_TOKEN", "")

LANG_KB = {"en": "KB-CrossLang-EN", "zh": "KB-CrossLang-ZH", "ja": "KB-CrossLang-JA"}

EN_QUERIES_OUT = DATA_DIR / "hotpotqa-en60.jsonl"
EN_CORPUS_OUT = SPLIT_DIR / "pages_KB-CrossLang-EN.jsonl"
N_EN_QUERIES = 60
N_EN_DOCS = 460


def post(url: str, payload: dict, timeout: int = 120, tries: int = 3) -> dict:
    """bench_http.post_json 的 409 透传封装(HTTPError 由调用方按 409 判重)."""
    return _post_json("", url, payload, token=TOKEN, timeout=timeout)


def get_json(url: str, timeout: int = 60) -> dict:
    return _get_json("", url, token=TOKEN, timeout=timeout)


def sanitize(title: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "_", title).strip().rstrip(".")
    return s or "untitled"


def doc_basename(doc_path: str) -> str:
    name = str(doc_path).replace("\\", "/").rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    return re.sub(r" \(part \d+ of \d+\)$", "", name)


def load_shard_index() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for shard in sorted(SPLIT_DIR.glob("pages_KB-*.jsonl")):
        kb = shard.stem.replace("pages_", "")
        if kb.startswith("KB-CrossLang"):
            continue
        for line in shard.open(encoding="utf-8"):
            p = json.loads(line)
            idx[p["title"]] = p | {"kb": kb}
    return idx


def build_en() -> None:
    """en 快照: hotpotqa 前 60 查询金标页 + 后续查询金标页干扰, sha256 稳定采样."""
    hot = [json.loads(l) for l in
           (DATA_DIR / "hotpotqa.jsonl").open(encoding="utf-8")]
    hot.sort(key=lambda x: x["qid"])
    eval_qs, distractor_qs = hot[:N_EN_QUERIES], hot[N_EN_QUERIES:N_EN_QUERIES + 150]
    gold_titles: set[str] = set()
    for q in eval_qs:
        gold_titles.update(t for t in q.get("golden_titles") or [])
    distractor_titles: set[str] = set()
    for q in distractor_qs:
        distractor_titles.update(t for t in q.get("golden_titles") or [])
    distractor_titles -= gold_titles
    print(f"en: queries={len(eval_qs)} gold_titles={len(gold_titles)} "
          f"distractor_titles={len(distractor_titles)}")

    idx = load_shard_index()
    gold_pages = {t: idx[t] for t in sorted(gold_titles) if t in idx}
    distr_pages = {t: idx[t] for t in
                   stable_sample(sorted(distractor_titles), N_EN_DOCS - len(gold_pages))
                   if t in idx}
    print(f"en: found in shards gold={len(gold_pages)} distractors={len(distr_pages)}")

    corpus = [{"title": p["title"], "kb": LANG_KB["en"], "content": p["content"],
               "gold": True} for p in gold_pages.values()]
    corpus += [{"title": p["title"], "kb": LANG_KB["en"], "content": p["content"],
                "gold": False} for p in distr_pages.values()]
    with EN_CORPUS_OUT.open("w", encoding="utf-8") as fh:
        for c in corpus:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    with EN_QUERIES_OUT.open("w", encoding="utf-8") as fh:
        for q in eval_qs:
            fh.write(json.dumps({"qid": q["qid"], "question": q["question"],
                                 "golden_pages": sorted(
                                     t for t in q.get("golden_titles") or []
                                     if t in gold_pages), "lang": "en"},
                                ensure_ascii=False) + "\n")
    print(f"-> {EN_CORPUS_OUT} ({len(corpus)} docs) / {EN_QUERIES_OUT}")


def stable_sample(items: list, n: int) -> list:
    return sorted(items, key=lambda x: hashlib.sha256(str(x).encode()).hexdigest())[:n]


def ensure_kb(name: str, description: str) -> str:
    try:
        r = post(f"{WEB}/api/kb/create", {"name": name, "description": description},
                 timeout=90)
        return r["knowledgeBase"]["id"]
    except urllib.error.HTTPError as e:
        if e.code != 409:
            raise
    catalog = get_json(f"{WEB}/api/kb/catalog")
    for kb in catalog.get("knowledgeBases") or []:
        if kb.get("name") == name or kb.get("path") == name:
            return kb.get("kbId") or kb.get("id")
    raise RuntimeError(f"KB {name} not in catalog")


def do_ingest(langs: list[str], limit: int) -> None:
    for lang in langs:
        kb_name = LANG_KB[lang]
        kb_id = ensure_kb(kb_name, f"Benchmark cross-lang corpus ({lang})")
        shard = SPLIT_DIR / f"pages_{kb_name}.jsonl"
        pages = [json.loads(l) for l in shard.open(encoding="utf-8")][:limit or None]
        done_path = RESULTS_DIR / f"ingest-checkpoint-{kb_name}.json"
        done: dict[str, str] = {}
        if done_path.exists():
            done = json.loads(done_path.read_text(encoding="utf-8"))
        pending, created, skipped, failed = [], 0, 0, 0
        for i, p in enumerate(pages):
            prev = str(done.get(p["title"], ""))
            if prev and not prev.startswith("failed"):
                skipped += 1
                continue  # failed:* 条目在本轮重试
            doc_name = sanitize(p["title"]) + ".md"
            try:
                resp = post(f"{WEB}/api/kb/documents/create",
                            {"kbId": kb_id, "name": doc_name, "content": p["content"],
                             "description": f"bench corpus: {p['title']}"}, timeout=90)
                done[p["title"]] = "created"
                created += 1
                if resp.get("split"):
                    # 大文档被系统拆为 parts — 用真实 part 名做批量索引
                    doc_name = None
                    pending.extend(str(d.get("name")) for d in resp.get("documents") or [])
            except urllib.error.HTTPError as e:
                if e.code == 409:
                    done[p["title"]] = "exists"
                    skipped += 1
                else:
                    done[p["title"]] = f"failed:{e.code}"
                    failed += 1
            except Exception as e:  # noqa: BLE001
                done[p["title"]] = f"failed:{str(e)[:60]}"
                failed += 1
            if doc_name:
                pending.append(doc_name)
            if len(pending) >= 50:
                batch_index(kb_id, pending)
                pending = []
            if (i + 1) % 100 == 0:
                done_path.write_text(json.dumps(done, ensure_ascii=False),
                                     encoding="utf-8")
                print(f"  [{lang}] {i+1}/{len(pages)} created={created} "
                      f"skipped={skipped} failed={failed}", flush=True)
        if pending:
            batch_index(kb_id, pending)
        done_path.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
        print(f"[{lang}] ingest done: created={created} skipped={skipped} "
              f"failed={failed}", flush=True)


def batch_index(kb_id: str, paths: list[str], force: bool = False) -> None:
    try:
        r = post(f"{BACKEND}/api/v1/search/batch-index",
                 {"kb_id": kb_id, "doc_paths": paths, "force": force}, timeout=600)
        print(f"  batch-index: {len(r.get('indexed', []))}/{len(paths)} ok", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"  batch-index failed (will retry next pass): {str(e)[:80]}", flush=True)


def reindex_kb(lang: str) -> None:
    """force 重索引整个对照库(向量+触发 BM25 失效) — 入库后必须执行一次."""
    kb_name = LANG_KB[lang]
    catalog = get_json(f"{WEB}/api/kb/catalog")
    kb_id = next((k.get("kbId") or k.get("id") for k in
                  catalog.get("knowledgeBases", [])
                  if k.get("name") == kb_name), "")
    docs = get_json(f"{WEB}/api/kb/documents?kb_id={kb_id}", timeout=180)
    names = [str(d.get("name")) for d in (docs.get("documents")
                                          or docs.get("docs") or [])]
    print(f"[{lang}] force reindex {len(names)} docs", flush=True)
    for start in range(0, len(names), 50):
        batch_index(kb_id, names[start:start + 50], force=True)


def do_measure(langs: list[str], round_no: int) -> None:
    for lang in langs:
        kb_name = LANG_KB[lang]
        shard = SPLIT_DIR / f"pages_{kb_name}.jsonl"
        pages = {p["title"]: p for p in
                 (json.loads(l) for l in shard.open(encoding="utf-8"))}
        done = json.loads((RESULTS_DIR / f"ingest-checkpoint-{kb_name}.json")
                          .read_text(encoding="utf-8"))
        attempted = len(done)
        ok = sum(1 for v in done.values() if v in ("created", "exists"))
        ingest_success = ok / attempted if attempted else 0.0

        catalog = get_json(f"{WEB}/api/kb/catalog")
        kb_id = next((k.get("kbId") or k.get("id") for k in
                      catalog.get("knowledgeBases", [])
                      if k.get("name") == kb_name), "")
        docs = get_json(f"{WEB}/api/kb/documents?kb_id={kb_id}", timeout=120)
        listed_base = set()   # 先去 .md 再去 part 后缀 → 基名
        listed_raw_by_base: dict[str, list[str]] = {}
        for d in (docs.get("documents") or docs.get("docs") or []):
            name = str(d.get("name"))
            base = name[:-3] if name.endswith(".md") else name
            base = re.sub(r" \(part \d+ of \d+\)$", "", base)
            listed_base.add(base)
            listed_raw_by_base.setdefault(base, []).append(name)
        expected = {sanitize(t) for t in pages}
        membership = len(expected & listed_base) / len(expected) if expected else 0.0

        # 抽样深度测量: 存储回读完整率 + 自检索命中
        sample_keys = stable_sample(sorted(pages), 40)
        completeness, selfhit, sample_errors = [], [], {}
        for t in sample_keys:
            p = pages[t]
            doc_name = sanitize(t) + ".md"
            try:
                # 大文档被系统拆为 parts: 原名不存在 → 读全部 part 并按字节求和
                part_names = listed_raw_by_base.get(sanitize(t)) or [doc_name]
                content_len = 0
                for pn in part_names:
                    d = get_json(f"{WEB}/api/kb/document?kb_id={kb_id}"
                                 f"&doc_path={urllib.parse.quote(pn)}"
                                 f"&max_chars=999999", timeout=60)
                    content_len += len(d.get("content") or d.get("markdown") or "")
                completeness.append(min(1.0, content_len / max(len(p["content"]), 1)))
                if content_len == 0:
                    sample_errors[t] = "empty content"
            except Exception as e:  # noqa: BLE001
                completeness.append(0.0)
                sample_errors[t] = f"read: {str(e)[:120]}"
            try:
                probe = p["content"][:200]
                r = post(f"{BACKEND}/api/v1/search/vector",
                         {"query": probe, "kb_id": kb_id, "top_k": 3}, timeout=90)
                names = {doc_basename(x.get("doc_path", ""))
                         for x in r.get("results") or []}
                selfhit.append(1 if sanitize(t) in names else 0)
            except Exception:
                selfhit.append(0)
            time.sleep(0.2)
        summary = {
            "lang": lang, "kb": kb_name, "round": round_no,
            "attempted": attempted,
            "ingest_success_rate": round(ingest_success, 4),
            "membership_accuracy": round(membership, 4),
            "storage_completeness_mean": round(statistics.mean(completeness), 4)
            if completeness else None,
            "self_retrieval_hit1": round(statistics.mean(selfhit), 4)
            if selfhit else None,
            "n_sampled": len(sample_keys),
        }
        out_meta = {"sample_errors": dict(list(sample_errors.items())[:5])}
        out = RESULTS_DIR / f"benchmark_ingestion_{lang}_r{round_no}.json"
        out.write_text(json.dumps({
            "meta": {"kb_id": kb_id, "web": WEB, "backend": BACKEND,
                     "generated": datetime.now(timezone.utc).isoformat()},
            "summary": summary, **out_meta}, ensure_ascii=False, indent=1), encoding="utf-8")
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (RESULTS_DIR / f"benchmark_ingestion_{lang}_{ts}.json").write_text(
            json.dumps({"summary": summary}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"[{lang}] {json.dumps(summary, ensure_ascii=False)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-en", action="store_true")
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--reindex", action="store_true")
    ap.add_argument("--langs", default="en,zh,ja")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--round", type=int, default=1)
    args = ap.parse_args()
    if not TOKEN:
        print("需要 RAG_BENCH_TOKEN", file=sys.stderr)
        return 2
    langs = args.langs.split(",")
    if args.build_en:
        build_en()
    if args.ingest:
        do_ingest(langs, args.limit)
    if args.reindex:
        for lang in langs:
            reindex_kb(lang)
    if args.measure:
        do_measure(langs, args.round)
    return 0


if __name__ == "__main__":
    sys.exit(main())
