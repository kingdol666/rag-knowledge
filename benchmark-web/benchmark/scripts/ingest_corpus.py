#!/usr/bin/env python3
"""语料入库 runner — 把 pages_KB-*.jsonl 写入系统并建立向量索引（可断点续跑）.

流程（每 KB）:
  1. POST {web}/api/kb/create            → 幂等: 已存在同名 KB 则从 catalog 取 uuid
  2. POST {web}/api/kb/documents/create  → 每页一个 .md 文档（name="{title}.md"）
  3. POST {backend}/api/v1/search/batch-index → 每 50 doc 一批建立向量索引
  4. POST {backend}/api/v1/search/vector (kb_id=本KB) → 验证索引非空
断点续跑: results/checkpoint-{KB}.jsonl 记录已入库 title; 重跑自动跳过。

用法:
  export RAG_BENCH_TOKEN=mcp-xxxx
  python ingest_corpus.py                               # 全部 KB
  python ingest_corpus.py --kbs KB-Film-TV --limit 100  # 冒烟: 单 KB 前 100 页
"""
from __future__ import annotations

import argparse
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
KB_SPLIT_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks" / "kb_split"
RESULTS_DIR = SCRIPTS_DIR.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
BATCH_SIZE = 50
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validated_url(url: str, extra_hosts: set[str] | None = None) -> str:
    """发请求前校验: 仅 http(s); 默认仅允许本机回环目标（本基准的合法靶机）,
    远程目标需显式设 RAG_BENCH_ALLOW_REMOTE=1 且禁止解析到链路本地/云元数据地址。"""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https: {url}")
    host = (p.hostname or "").lower()
    allow = _LOCAL_HOSTS | (extra_hosts or set())
    if host not in allow:
        if os.environ.get("RAG_BENCH_ALLOW_REMOTE") != "1":
            raise ValueError(f"非白名单目标被拒绝: {host} (白名单={sorted(allow)})")
        for ai in socket.getaddrinfo(host, None):
            addr = ipaddress.ip_address(ai[4][0])
            if addr.is_link_local or str(addr) == "169.254.169.254":
                raise ValueError(f"目标解析到受限地址: {url}")
    return url


def _web_base() -> str:
    return validated_url(os.environ.get("RAG_BENCH_WEB_URL", "http://localhost:6789")).rstrip("/")


def _backend_base() -> str:
    return validated_url(os.environ.get("RAG_BENCH_URL", "http://localhost:8770")).rstrip("/")


def request(url: str, data: dict, token: str, timeout: int = 300) -> dict:
    """POST with retry — long ingest runs must survive transient timeouts
    (batch-index of 50 pages can exceed short timeouts under load)."""
    url = validated_url(url)
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            wait = 5 * attempt
            print(f"    request retry {attempt}/3 after {wait}s: {e}")
            time.sleep(wait)
    raise last_err  # type: ignore[misc]


def get_json(url: str, token: str, timeout: int = 120) -> dict:
    url = validated_url(url)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def batch_index_with_recovery(backend: str, kb_name: str, kb_id: str,
                              paths: list[str], token: str) -> None:
    """batch-index, 失败批次写入 recovery 文件供后续补索引（入库不死）。"""
    recovery = RESULTS_DIR / ("index-retry-" + kb_name + ".txt")
    batch_url = backend + "/api/v1/search/batch-index"
    payload = {"kb_id": kb_id, "doc_paths": paths, "force": False}
    try:
        r = request(batch_url, payload, token)
        ok = len(r.get("indexed", []))
        if ok < len(paths):
            print("  batch-index: %d/%d ok" % (ok, len(paths)))
            indexed_set = set(r.get("indexed", []))
            missed = [p for p in paths if p not in indexed_set]
            with open(recovery, "a", encoding="utf-8") as f:
                f.write("\n".join(missed) + "\n")
    except Exception as e:
        print("  batch-index failed (%s) — %d paths -> %s" % (e, len(paths), recovery.name))
        with open(recovery, "a", encoding="utf-8") as f:
            f.write("\n".join(paths) + "\n")


def ensure_kb(name: str, description: str, token: str) -> str:
    """创建 KB（幂等），返回 kb uuid。"""
    web = _web_base()
    try:
        r = request(f"{web}/api/kb/create", {"name": name, "description": description}, token)
        return r["knowledgeBase"]["id"]
    except urllib.error.HTTPError as e:
        if e.code == 409:  # 已存在 → 从 catalog 取 uuid
            catalog = get_json(f"{web}/api/kb/catalog", token)
            kbs = (catalog if isinstance(catalog, list)
                   else catalog.get("knowledgeBases") or catalog.get("kbs") or [])
            for kb in kbs:
                if kb.get("name") == name or kb.get("path") == name:
                    return kb.get("kbId") or kb.get("id") or kb.get("kb_id")
            raise RuntimeError(f"KB {name} 返回 409 但 catalog 中找不到")
        raise


def load_checkpoint(kb_name: str) -> tuple[set[str], object]:
    cp = RESULTS_DIR / f"checkpoint-{kb_name}.jsonl"
    done = set()
    if cp.exists():
        for line in cp.open(encoding="utf-8"):
            if line.strip():
                done.add(json.loads(line)["title"])
    return done, cp.open("a", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kbs", default="", help="逗号分隔的 KB 名过滤, 空=全部")
    ap.add_argument("--limit", type=int, default=0, help="每 KB 最多入库页数(冒烟)")
    args = ap.parse_args()

    token = os.environ.get("RAG_BENCH_TOKEN", "")
    if not token:
        print("❌ 缺少 RAG_BENCH_TOKEN 环境变量")
        return 2

    shards = sorted(KB_SPLIT_DIR.glob("pages_KB-*.jsonl"))
    if args.kbs:
        wanted = {k.strip() for k in args.kbs.split(",")}
        shards = [s for s in shards if s.stem[len("pages_"):] in wanted]
    if not shards:
        print(f"❌ 未找到分片: {KB_SPLIT_DIR}/pages_KB-*.jsonl — 先运行 split_corpus_to_kbs.py")
        return 2

    report: dict = {"kbs": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    for shard in shards:
        kb_name = shard.stem[len("pages_"):]
        pages = [json.loads(l) for l in shard.open(encoding="utf-8") if l.strip()]
        if args.limit:
            pages = pages[:args.limit]
        print(f"\n=== {kb_name}: {len(pages)} pages ===", flush=True)

        kb_id = ensure_kb(kb_name,
                          f"Benchmark 主题库 {kb_name} (wiki18 拆分, 见 BENCHMARK-EXECUTION-PLAN)",
                          token)
        done, cp = load_checkpoint(kb_name)
        pending_paths: list[str] = []
        created = skipped = failed = 0
        t0 = time.perf_counter()
        web = _web_base()
        backend = _backend_base()

        for i, page in enumerate(pages):
            title = page["title"]
            if title in done:
                skipped += 1
                continue
            # Windows 文件名净化: wiki 标题含 : ? * 等非法字符会让 web 建目录 ENOENT。
            # 确定性替换 → 同一标题总是得到同一文件名, 断点续跑的 done 集合保持一致。
            safe_title = re.sub(r'[\\/:*?"<>|]', "_", title).strip().rstrip(".") or "untitled"
            doc_name = f"{safe_title}.md"
            try:
                request(f"{web}/api/kb/documents/create",
                        {"kbId": kb_id, "name": doc_name,
                         "content": page["content"], "description": f"wiki18 页面: {title}"},
                        token)
                cp.write(json.dumps({"title": title}, ensure_ascii=False) + "\n")
                pending_paths.append(doc_name)
                created += 1
            except urllib.error.HTTPError as e:
                if e.code == 409:  # 名称冲突 = 自动去重语义, 视为已存在
                    cp.write(json.dumps({"title": title, "dup": True}, ensure_ascii=False) + "\n")
                    skipped += 1
                else:
                    failed += 1
                    detail = e.read().decode(errors="replace")[:150]
                    print(f"  [{i}] create failed {doc_name}: HTTP {e.code} {detail}")
            except Exception as e:
                failed += 1
                print(f"  [{i}] create failed {doc_name}: {e}")

            if len(pending_paths) >= BATCH_SIZE:
                batch_index_with_recovery(backend, kb_name, kb_id, pending_paths, token)
                pending_paths = []
            if (i + 1) % 200 == 0:
                rate = created / max(time.perf_counter() - t0, 1)
                print(f"  [{i+1}/{len(pages)}] created={created} skipped={skipped} "
                      f"failed={failed} ({rate:.1f} doc/s)", flush=True)
        cp.close()

        if pending_paths:
            batch_index_with_recovery(backend, kb_name, kb_id, pending_paths, token)

        # 索引验证: KB 内向量检索必须能返回结果
        verify = request(f"{backend}/api/v1/search/vector",
                         {"query": "history", "kb_id": kb_id, "top_k": 3,
                          "score_threshold": 0.0, "balance_kbs": False}, token)
        n_results = len(verify.get("results", []))
        report["kbs"][kb_name] = {
            "kb_id": kb_id, "pages_in_shard": len(pages), "created": created,
            "skipped": skipped, "failed": failed,
            "index_verify_results": n_results,
            "status": "OK" if n_results > 0 else "INDEX_EMPTY",
        }
        print(f"  -> {report['kbs'][kb_name]}")

    out = RESULTS_DIR / "corpus-ingest-report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ {out} — 全部 KB INDEX_EMPTY 时请检查 batch-index 的 errors 字段")
    return 0


if __name__ == "__main__":
    sys.exit(main())
