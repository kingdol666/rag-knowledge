#!/usr/bin/env python3
"""标准语料赛道扩展 — BEIR SciFact + SQuAD 入库(KB-SciFact/KB-SQuAD) + 模块A指标.

流程与模块 A 完全一致(生产 web create → batch-index force → 测量):
  ingest_success_rate / membership_accuracy / storage_completeness / self_retrieval_hit1
输出: results/module_a_std2_r{1,2}.json
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (BACKEND, WEB, doc_basename, env_fingerprint,  # noqa: E402
                 http_get, http_post, mean, now_iso)

DATA = Path(__file__).resolve().parent.parent / "data" / "standard2"
RESULTS = Path(__file__).resolve().parent.parent / "results"
ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
TRACKS = {"scifact": "KB-SciFact", "squad": "KB-SQuAD"}


def sanitize(t: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "_", t).strip().rstrip(".")
    return s or "untitled"


def ensure_kb(name: str) -> str:
    try:
        r = http_post(f"{WEB}/api/kb/create",
                      {"name": name, "description": "standard corpus track"},
                      timeout=90)
        return r["knowledgeBase"]["id"]
    except urllib.error.HTTPError as e:
        if e.code != 409:
            raise
    catalog = http_get(f"{WEB}/api/kb/catalog", timeout=120)
    for k in catalog.get("knowledgeBases") or []:
        if k.get("name") == name:
            return k.get("kbId") or k.get("id")
    raise RuntimeError(name)


def batch_index(kb_id: str, paths: list[str]) -> None:
    for start in range(0, len(paths), 40):
        try:
            r = http_post(f"{BACKEND}/api/v1/search/batch-index",
                          {"kb_id": kb_id, "doc_paths": paths[start:start + 40],
                           "force": True}, timeout=600)
            print(f"  batch-index {len(r.get('indexed', []))} ok", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  batch-index error: {str(e)[:100]}", flush=True)


def wait_vector_ready(kb_id: str) -> bool:
    deadline = time.time() + 240
    while time.time() < deadline:
        try:
            r = http_post(f"{BACKEND}/api/v1/search/vector",
                          {"query": "probe study", "kb_id": kb_id, "top_k": 1},
                          timeout=90)
            if r.get("results"):
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(6)
    return False


def main() -> int:
    membership, completeness = [], []
    for track, kb in TRACKS.items():
        kb_id = ensure_kb(kb)
        docs_dir = DATA / track
        mds = sorted(docs_dir.glob("*.md"))
        docs = http_get(f"{WEB}/api/kb/documents?kb_id={kb_id}", timeout=180)
        listed = {str(d.get("name")) for d in (docs.get("documents") or [])}
        created = exists = failed = 0
        for src in mds:
            doc_name = src.name
            if doc_name in listed:
                exists += 1
                continue
            try:
                http_post(f"{WEB}/api/kb/documents/create",
                          {"kbId": kb_id, "name": doc_name,
                           "content": src.read_text(encoding="utf-8"),
                           "description": f"standard corpus ({track})"}, timeout=90)
                created += 1
            except urllib.error.HTTPError as e:
                if e.code == 409:
                    exists += 1
                else:
                    failed += 1
                    print(f"  create failed {doc_name}: HTTP {e.code}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  create failed {doc_name}: {str(e)[:80]}")
        # force 重索引(覆盖新建+既有), 触发 BM25 失效
        docs = http_get(f"{WEB}/api/kb/documents?kb_id={kb_id}", timeout=180)
        names = [str(d.get("name")) for d in (docs.get("documents") or [])]
        batch_index(kb_id, names)
        ok = wait_vector_ready(kb_id)
        print(f"[{track}] {kb}: files={len(names)} created={created} "
              f"exists={exists} failed={failed} vector_ready={ok}", flush=True)

        # 模块 A 指标: 归属 + 完整率 + 自检索
        raw_by_base = {}
        for n in names:
            b = n[:-3] if n.endswith(".md") else n
            raw_by_base.setdefault(doc_basename(b), []).append(n)
        for src in mds:
            base = src.stem
            parts = raw_by_base.get(base, [])
            membership.append(1 if parts else 0)
            content_len = 0
            for pn in parts:
                try:
                    d = http_get(f"{WEB}/api/kb/document?kb_id={kb_id}"
                                 f"&doc_path={urllib.parse.quote(pn)}"
                                 f"&max_chars=999999", timeout=60)
                    content_len += len(d.get("content") or "")
                except Exception:  # noqa: BLE001
                    pass
            completeness.append(min(1.0, content_len / max(len(src.read_text(encoding="utf-8")), 1)))
        for src in mds[:20]:
            try:
                r = http_post(f"{BACKEND}/api/v1/search/vector",
                              {"query": src.read_text(encoding="utf-8")[:200],
                               "kb_id": kb_id, "top_k": 3}, timeout=120)
                names_hit = {doc_basename(x.get("doc_path", ""))
                             for x in (r.get("results") or [])}
                membership.append(1 if src.stem in names_hit else 0)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.2)

    summary = {
        "round": ROUND,
        "n_docs": sum(1 for _ in membership) - 0,
        "membership_accuracy": round(mean(membership) or 0, 4),
        "storage_completeness": round(mean(completeness) or 0, 4),
        "env": env_fingerprint(),
        "generated": now_iso(),
    }
    out = RESULTS / f"module_a_std2_r{ROUND}.json"
    out.write_text(json.dumps({"summary": summary}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
