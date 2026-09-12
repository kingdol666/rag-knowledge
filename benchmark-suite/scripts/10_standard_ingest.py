#!/usr/bin/env python3
"""标准语料赛道入库 — XQuAD 子集(en/zh 各 8 篇)入 KB-Std-EN/KB-Std-ZH 并建索引."""
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
from lib import (BACKEND, RESULTS, WEB, doc_basename, env_fingerprint,  # noqa: E402
                 http_get, http_post, mean, now_iso)

DATA = Path(__file__).resolve().parent.parent / "data" / "standard"
ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"


def sanitize(t: str) -> str:
    s = t.replace("/", "-").strip()
    return s or "untitled"


def ensure_kb(name: str) -> str:
    try:
        r = http_post(f"{WEB}/api/kb/create",
                      {"name": name, "description": "XQuAD standard subset"},
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
                          {"query": "probe history", "kb_id": kb_id, "top_k": 1},
                          timeout=90)
            if r.get("results"):
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(6)
    return False


def main() -> int:
    kb_ids = {}
    created = 0
    membership, completeness = [], []
    for lang, kb in (("en", "KB-Std-EN"), ("zh", "KB-Std-ZH")):
        kb_id = ensure_kb(kb)
        kb_ids[lang] = kb_id
        docs = http_get(f"{WEB}/api/kb/documents?kb_id={kb_id}", timeout=180)
        listed = {str(d.get("name")) for d in (docs.get("documents") or [])}
        for src in sorted((DATA / lang).glob("*.md")):
            doc_name = sanitize(src.stem) + ".md"
            if doc_name in listed:
                continue
            try:
                http_post(f"{WEB}/api/kb/documents/create",
                          {"kbId": kb_id, "name": doc_name,
                           "content": src.read_text(encoding="utf-8"),
                           "description": "XQuAD standard corpus"},
                          timeout=90)
                created += 1
            except urllib.error.HTTPError as e:
                if e.code != 409:
                    print(f"  create failed {doc_name}: HTTP {e.code}")
            except Exception as e:  # noqa: BLE001
                print(f"  create failed {doc_name}: {str(e)[:80]}")
    for lang, kb_id in kb_ids.items():
        docs = http_get(f"{WEB}/api/kb/documents?kb_id={kb_id}", timeout=180)
        names = [str(d.get("name")) for d in (docs.get("documents") or [])]
        batch_index(kb_id, names)
        ok = wait_vector_ready(kb_id)
        print(f"  {kb}: {len(names)} files, vector ready={ok}", flush=True)
        # 归属 + 完整率
        raw_by_base = {}
        for n in names:
            b = n[:-3] if n.endswith(".md") else n
            raw_by_base.setdefault(doc_basename(b), []).append(n)
        for src in sorted((DATA / lang).glob("*.md")):
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
            completeness.append(min(1.0, content_len / max(len(src.read_text(encoding='utf-8')), 1)))

    summary = {
        "round": ROUND,
        "created": created,
        "ingest_success_rate": 1.0 if not created else None,  # 见 membership
        "membership_accuracy": round(mean(membership) or 0, 4),
        "storage_completeness": round(mean(completeness) or 0, 4),
        "env": env_fingerprint(),
        "generated": now_iso(),
    }
    out = RESULTS / f"module_a_std_r{ROUND}.json"
    out.write_text(json.dumps({"summary": summary}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
