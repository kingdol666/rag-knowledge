#!/usr/bin/env python3
"""入库归类基准 — 度量"内容入库后, 系统能否凭内容把文档归回正确的库".

模拟知识库整理场景: 把已知域归属的 golden 页面副本写入"未归类收件库"
(KB-Inbox-Organize), 再用两种纯生产 API 的归类策略为每份文档指派目标域库:

  retrieval_vote  跨库检索投票: 文档内容作 query 走生产 two-stage 全库检索,
                  过滤掉收件库自身的命中, 对剩余 top-3 命中所属域库多数投票
  perkb_scan      逐库扫描: 对每个域库做域内向量检索(文档内容为 query, top-1),
                  以余弦分 argmax 选库 — 即"查看全部文档库, 比对内容相似度"

另测入库保真 (round-trip): 用文档自身首句做检索, 金文档应被命中 —
"送入库里的内容检索得回来"是入库正确性的下界保证.

金标 = 语料划分协议的冻结域标签 (kb_assignments, 标题关键词分类器).
指标: Routing Acc@1 / top-3 投票 Acc / 混淆矩阵 / round-trip Hit@1·Hit@5.

用法:
  export RAG_BENCH_TOKEN=mcp-xxxx
  python run_ingest_routing.py --per-kb 3 --round 0    # 冒烟
  python run_ingest_routing.py --per-kb 15 --round 1   # 正式
  python run_ingest_routing.py --compare               # 双轮复现比对
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
SPLIT_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks" / "kb_split"
RESULTS_DIR = SCRIPTS_DIR.parent / "results" / "routing"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

WEB = os.environ.get("RAG_BENCH_WEB_URL", "http://localhost:6790").rstrip("/")
BACKEND = os.environ.get("RAG_BENCH_URL", "http://localhost:8771").rstrip("/")
TOKEN = os.environ.get("RAG_BENCH_TOKEN", "")
INBOX_KB = "KB-Inbox-Organize"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validate_base(base: str) -> str:
    p = urlparse(base)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https: {base}")
    host = (p.hostname or "").lower()
    if host not in _LOCAL_HOSTS:
        if os.environ.get("RAG_BENCH_ALLOW_REMOTE") != "1":
            raise ValueError(f"非本机目标 {host} 被拒绝: {base}")
        for ai in socket.getaddrinfo(host, None):
            addr = ipaddress.ip_address(ai[4][0])
            if addr.is_link_local or str(addr) == "169.254.169.254":
                raise ValueError(f"目标解析到受限地址: {base}")
    return base.rstrip("/")


WEB_B = validate_base(WEB)
BACKEND_B = validate_base(BACKEND)


def post_json(url: str, data: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def get_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {TOKEN}"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def with_retry(fn, tries: int = 5, base_delay: float = 2.0):
    last: Exception | None = None
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code in (401, 409, 429) or e.code >= 500:
                last = e
            else:
                raise
        except Exception as e:
            last = e
        time.sleep(base_delay * attempt)
    raise last  # type: ignore[misc]


def ensure_kb(name: str, description: str) -> str:
    try:
        r = with_retry(lambda: post_json(f"{WEB_B}/api/kb/create",
                                         {"name": name, "description": description}))
        return r["knowledgeBase"]["id"]
    except urllib.error.HTTPError as e:
        if e.code != 409:
            raise
    catalog = with_retry(lambda: get_json(f"{WEB_B}/api/kb/catalog"))
    kbs = catalog.get("knowledgeBases") or []
    for kb in kbs:
        if kb.get("name") == name or kb.get("path") == name:
            return kb.get("kbId") or kb.get("id")
    raise RuntimeError(f"KB {name} 409 但 catalog 找不到")


def load_catalog() -> dict[str, str]:
    """name -> uuid (仅 KB-* 域库)."""
    catalog = with_retry(lambda: get_json(f"{WEB_B}/api/kb/catalog"))
    out = {}
    for kb in catalog.get("knowledgeBases") or []:
        name = kb.get("name", "")
        if name.startswith("KB-") and name != INBOX_KB:
            out[name] = kb.get("kbId") or kb.get("id")
    return out


def sanitize_title(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]', "_", title).strip().rstrip(".")
    return safe or "untitled"


def pick_golden_pages(per_kb: int) -> dict[str, list[dict]]:
    """每域库从 shard 尾部取 golden 页(避开头部已用于 contentqa 的页)."""
    assignments = json.loads(
        (SPLIT_DIR / "kb_assignments.json").read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for shard in sorted(SPLIT_DIR.glob("pages_KB-*.jsonl")):
        kb = shard.stem.replace("pages_", "")
        golden = []
        for line in shard.open(encoding="utf-8"):
            page = json.loads(line)
            if assignments.get(page["title"]) == kb and page.get("content"):
                golden.append(page)
        out[kb] = golden[-per_kb:] if per_kb else golden
    return out


def first_sentence(content: str) -> str:
    for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", content):
        if 60 <= len(sent) <= 240 and "|" not in sent:
            return sent
    return content[:200]


def wait_vector_ready(kb_id: str, timeout_s: int = 180) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = post_json(f"{BACKEND_B}/api/v1/search/vector",
                          {"query": "probe", "kb_id": kb_id, "top_k": 1}, timeout=60)
            if r.get("results"):
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-kb", type=int, default=15)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--skip-ingest", action="store_true",
                    help="收件库已建好时跳过写入阶段")
    args = ap.parse_args()

    if not TOKEN:
        print("需要 RAG_BENCH_TOKEN", file=sys.stderr)
        return 2

    domain_kbs = load_catalog()
    print(f"domain KBs: {len(domain_kbs)} -> {sorted(domain_kbs)}")
    inbox_id = ensure_kb(INBOX_KB, "内容路由基准收件库 (benchmark artifact)")
    print(f"inbox kb_id={inbox_id}")

    # ---- 阶段 A: 写入收件库 ----
    pages_by_kb = pick_golden_pages(args.per_kb)
    planned = sum(len(v) for v in pages_by_kb.values())
    print(f"planned probe docs: {planned}")
    created = skipped = failed = 0
    docs: list[dict] = []
    if not args.skip_ingest:
        for kb in sorted(pages_by_kb):
            for page in pages_by_kb[kb]:
                doc_name = sanitize_title(page["title"]) + ".md"
                try:
                    with_retry(lambda: post_json(
                        f"{WEB_B}/api/kb/documents/create",
                        {"kbId": inbox_id, "name": doc_name,
                         "content": page["content"],
                         "description": f"routing probe: {page['title']}"}))
                    created += 1
                except urllib.error.HTTPError as e:
                    if e.code == 409:
                        skipped += 1
                    else:
                        failed += 1
                        print(f"  create failed {doc_name}: HTTP {e.code}")
                        continue
                except Exception as e:
                    failed += 1
                    print(f"  create failed {doc_name}: {e}")
                    continue
                docs.append({"title": page["title"], "doc_name": doc_name,
                             "gold_kb": page["kb"], "content": page["content"]})
            print(f"  {kb}: cumulative created={created} skipped={skipped} failed={failed}")
    else:
        for kb in sorted(pages_by_kb):
            for page in pages_by_kb[kb]:
                docs.append({"title": page["title"],
                             "doc_name": sanitize_title(page["title"]) + ".md",
                             "gold_kb": page["kb"], "content": page["content"]})
    print(f"ingest: created={created} skipped(exist)={skipped} failed={failed}")

    # ---- 阶段 B: 收件库向量索引 ----
    if created:
        paths = [d["doc_name"] for d in docs]
        for start in range(0, len(paths), 50):
            batch = paths[start:start + 50]
            r = with_retry(lambda: post_json(
                f"{BACKEND_B}/api/v1/search/batch-index",
                {"kb_id": inbox_id, "doc_paths": batch, "force": False}))
            print(f"  batch-index {start+len(batch)}/{len(paths)}: "
                  f"{len(r.get('indexed', []))} ok")
    if not wait_vector_ready(inbox_id):
        print("warn: inbox vector index not ready — 检索投票可能命中收件库自身")

    # ---- 阶段 C: 归类决策 ----
    confusion_vote: dict[str, Counter] = defaultdict(Counter)
    confusion_scan: dict[str, Counter] = defaultdict(Counter)
    roundtrip1 = roundtrip5 = 0
    records = []
    t_all = time.perf_counter()
    for idx, d in enumerate(docs):
        probe = d["content"][:1200]
        gold = d["gold_kb"]

        # 策略 1: 跨库检索投票 (two-stage, 过滤收件库命中)
        r = with_retry(lambda: post_json(
            f"{BACKEND_B}/api/v1/search/two-stage", {"query": probe, "kb_id": ""}))
        hits = (r.get("stage2") or {}).get("results") or []
        extern = [h for h in hits
                  if h.get("doc_path", "").replace("\\", "/").split("/", 1)[0] != INBOX_KB]
        pred_vote1 = (extern[0]["doc_path"].replace("\\", "/").split("/", 1)[0]
                      if extern else "")
        top3 = [h["doc_path"].replace("\\", "/").split("/", 1)[0] for h in extern[:3]]
        pred_vote3 = Counter(top3).most_common(1)[0][0] if top3 else ""

        # 策略 2: 逐库向量扫描 argmax
        best_kb, best_score = "", -1.0
        for name, uuid in domain_kbs.items():
            try:
                rv = with_retry(lambda: post_json(
                    f"{BACKEND_B}/api/v1/search/vector",
                    {"query": probe, "kb_id": uuid, "top_k": 1}), tries=3)
                score = rv["results"][0]["score"] if rv.get("results") else -1.0
            except Exception:
                score = -1.0
            if score > best_score:
                best_kb, best_score = name, score

        confusion_vote[gold][pred_vote1 or "(none)"] += 1
        confusion_scan[gold][best_kb or "(none)"] += 1

        # round-trip: 首句检索应取回原文档
        sent = first_sentence(d["content"])
        rr = with_retry(lambda: post_json(
            f"{BACKEND_B}/api/v1/search/two-stage", {"query": sent, "kb_id": ""}))
        rhits = (rr.get("stage2") or {}).get("results") or []
        basenames = [h.get("doc_path", "").replace("\\", "/").rsplit("/", 1)[-1]
                     for h in rhits]
        gold_name = sanitize_title(d["title"]) + ".md"
        rank = next((i + 1 for i, b in enumerate(basenames)
                     if b == gold_name or b.rsplit(" (part", 1)[0] == gold_name), None)
        roundtrip1 += rank == 1
        roundtrip5 += rank is not None and rank <= 5

        records.append({
            "title": d["title"], "gold_kb": gold,
            "pred_vote1": pred_vote1, "pred_vote3": pred_vote3,
            "pred_scan": best_kb, "scan_margin": round(best_score, 4),
            "roundtrip_rank": rank,
        })
        if (idx + 1) % 10 == 0:
            acc1 = sum(1 for r_ in records if r_["pred_vote1"] == r_["gold_kb"]) / len(records)
            print(f"  [{idx+1}/{len(docs)}] vote-acc@1 so far={acc1:.3f} "
                  f"elapsed={time.perf_counter()-t_all:.0f}s", flush=True)

    n = len(records)
    vote_acc1 = sum(1 for r in records if r["pred_vote1"] == r["gold_kb"]) / n if n else 0
    vote_acc3 = sum(1 for r in records if r["pred_vote3"] == r["gold_kb"]) / n if n else 0
    scan_acc1 = sum(1 for r in records if r["pred_scan"] == r["gold_kb"]) / n if n else 0
    per_domain = {}
    for gold in sorted(confusion_vote):
        total = sum(confusion_vote[gold].values())
        ok = confusion_vote[gold][gold]
        per_domain[gold] = {"n": total, "vote_acc1": ok / total if total else 0,
                            "scan_top_pred": confusion_scan[gold].most_common(1)[0][0]
                            if confusion_scan[gold] else ""}

    report = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "web": WEB_B, "backend": BACKEND_B,
            "inbox_kb": INBOX_KB, "per_kb": args.per_kb,
            "protocol": "inbox-copy routing; gold=frozen kb_assignments labels",
        },
        "ingest": {"planned": planned, "created": created,
                   "skipped_existing": skipped, "failed": failed},
        "summary": {
            "n_docs": n,
            "routing_vote_acc@1": round(vote_acc1, 4),
            "routing_vote_acc@top3": round(vote_acc3, 4),
            "routing_scan_acc@1": round(scan_acc1, 4),
            "roundtrip_hit@1": round(roundtrip1 / n, 4) if n else 0,
            "roundtrip_hit@5": round(roundtrip5 / n, 4) if n else 0,
        },
        "per_domain": per_domain,
        "confusion_vote": {g: dict(c) for g, c in sorted(confusion_vote.items())},
        "confusion_scan": {g: dict(c) for g, c in sorted(confusion_scan.items())},
        "records": records,
    }
    path = RESULTS_DIR / f"routing.r{args.round}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {path}")
    print("summary:", json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
