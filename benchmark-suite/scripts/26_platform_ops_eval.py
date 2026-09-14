#!/usr/bin/env python3
"""E17 平台整理功能评价(精简驱动).

读 algorithms/ops_fixture.json(9 篇确定性文档, 2 组植入重复), 新建一次性 KB,
度量 kb_find_duplicates 检出 / 标签内容精确率 / cleanup dry-run 完整性 /
图谱构建与探针 / catalog 无幽灵条目。输出 results/run-*/platform_ops_eval.json
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
from lib import BACKEND, McpClient, WEB  # noqa: E402
from lib import env_fingerprint, http_get, http_post, now_iso  # noqa: E402

FIXTURE = json.loads((HERE.parent / "algorithms" / "ops_fixture.json")
                     .read_text(encoding="utf-8"))
DOCS = FIXTURE["docs"]
NAMES = [d["name"] for d in DOCS]


def group_of(name: str) -> int:
    if "kv-cache" in name:
        return 1
    if "fresh-reindex" in name:
        return 2
    return 0


def tag_text(t):
    if isinstance(t, dict):
        return str(t.get("tag") or t.get("name") or "")
    return str(t)


def main():
    mc = McpClient()
    started = time.perf_counter()
    try:
        stamp = datetime.now(timezone.utc).strftime("%H%M%S")
        kb_name = "KB-Ops-Eval-" + stamp
        create_url = WEB + "/api/kb/create"
        try:
            http_post(create_url, {"name": kb_name, "description": "E17"},
                      timeout=120)
        except urllib.error.HTTPError as err:
            if err.code != 409:
                raise
        catalog = http_get(WEB + "/api/kb/catalog", timeout=180)
        kb_id = ""
        for item in catalog.get("knowledgeBases") or []:
            if item.get("name") == kb_name:
                kb_id = str(item.get("kbId") or item.get("id"))
        if not kb_id:
            raise RuntimeError("KB create failed")

        doc_url = WEB + "/api/kb/documents/create"
        created = 0
        for doc in DOCS:
            try:
                http_post(doc_url, {"kbId": kb_id, "name": doc["name"],
                                    "content": doc["content"],
                                    "description": doc["description"]},
                          timeout=90)
                created += 1
            except urllib.error.HTTPError as err:
                if err.code != 409:
                    raise
        index_url = BACKEND + "/api/v1/search/batch-index"
        index_resp = http_post(index_url, {"kb_id": kb_id, "doc_paths": NAMES,
                                           "force": True}, timeout=600)

        dup = mc.call("kb_find_duplicates", {"kb_id": kb_id}, timeout=300)
        groups = dup.get("duplicate_groups") or dup.get("groups") or []
        valid_pairs, detected = [], set()
        for group in groups:
            members = group.get("documents") or group.get("members") or []
            gnames = [str(m.get("name") if isinstance(m, dict) else m)
                      for m in members]
            for i in range(len(gnames)):
                for j in range(len(gnames)):
                    if i != j and group_of(gnames[i]) > 0 \
                            and group_of(gnames[i]) == group_of(gnames[j]):
                        if group_of(gnames[i]) not in detected:
                            detected.add(group_of(gnames[i]))
                            valid_pairs.append([gnames[i], gnames[j]])

        tags = mc.call("kb_tags_list", {"kb_id": kb_id}, timeout=300)
        tag_items = tags.get("tags") or tags.get("items") or []
        corpus_text = " ".join(d["content"] for d in DOCS).lower()
        grounded = sum(1 for t in tag_items if tag_text(t).lower() in corpus_text)

        cleanup = mc.call("kb_tags_cleanup", {"kb_id": kb_id,
                                              "dry_run": True}, timeout=300)
        would_clean = cleanup.get("would_clean") or cleanup.get("orphans") or []
        used = set(tag_text(t) for t in tag_items)
        used_in_clean = sum(1 for x in would_clean if tag_text(x) in used)

        graph_build = mc.call("kb_graph_build", {"kb_id": kb_id}, timeout=600)
        graph_stats = mc.call("kb_graph_stats", {"kb_id": kb_id}, timeout=300)
        stats = graph_stats.get("stats") or graph_stats
        probe = mc.call("kb_graph_search",
                        {"keyword": "KV cache", "kb_id": kb_id,
                         "top_k": 3}, timeout=300)
        docs_url = WEB + "/api/kb/documents?kb_id=" + kb_id
        doc_count = len((http_get(docs_url, timeout=180)).get("documents") or [])

        result = {
            "meta": {"generated": now_iso(), "env": env_fingerprint(),
                     "kb": kb_name, "planted_docs": len(DOCS),
                     "planted_dup_groups": FIXTURE["planted_dup_groups"]},
            "ingestion": {"web_created": created,
                          "batch_indexed": len(index_resp.get("indexed") or [])},
            "dedup": {"valid_pairs": valid_pairs[:6],
                      "n_valid_pairs": len(valid_pairs),
                      "groups_detected": len(detected),
                      "planted_groups": FIXTURE["planted_dup_groups"],
                      "recall_groups": round(len(detected) /
                                             FIXTURE["planted_dup_groups"], 4)},
            "tags": {"distinct_tags": len(tag_items),
                     "content_grounded_tags": grounded,
                     "grounded_ratio": (round(grounded / len(tag_items), 4)
                                        if tag_items else 0)},
            "cleanup_dry_run": {"would_clean": len(would_clean),
                                "used_tags_in_clean_list": used_in_clean,
                                "integrity_ok": used_in_clean == 0},
            "graph": {"entities": stats.get("entities")
                      if isinstance(stats, dict) else None,
                      "relations": stats.get("relations")
                      if isinstance(stats, dict) else None,
                      "search_probe_hits": len(probe.get("results")
                                               or probe.get("nodes") or []),
                      "build_ok": bool(graph_build.get("success", True))},
            "catalog": {"doc_count": doc_count, "expected": len(DOCS),
                        "no_ghosts": doc_count == len(DOCS)},
            "latency_seconds": round(time.perf_counter() - started, 1),
        }
        run_stamp = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
        out_dir = HERE.parent / "results" / run_stamp
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "platform_ops_eval.json"
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=1))
        print("-> " + str(out_file))
        return 0
    finally:
        mc.close()


if __name__ == "__main__":
    sys.exit(main())
