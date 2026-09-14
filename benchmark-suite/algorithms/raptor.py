#!/usr/bin/env python3
"""RAPTOR (Sarthi et al. 2024) Collapsed Tree 复现 — 论文 §4.2 设置.

  node ≤800 tokens(3200 chars), 5 层, cluster top-5, 检索取 top-10 节点。
聚类: 论文用 GMM 软分配; 本复现以互为 top-5 相似 UNION-FIND 近似(嵌入同源
bge-m3, 经被测系统 kb_search_vector 取相似度), 偏差记录于 REPRODUCTION-NOTES。
摘要: 每 cluster 由 omp Agent 生成 ≤150 词摘要 — 这是树的 LLM 成本所在,
tree 落盘 cache/raptor_tree.json, 重建需 DR_REBUILD_KB=1。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from corpus import load_corpus, tokens
from index_kb import (CACHE, KB_FIXED, KB_RAPTOR, build_kb,  # noqa: E402
                      dump_texts, items_fixed)
from omp_client import OmpOneshot

TREE_PATH = CACHE / "raptor_tree.json"
MAX_NODE_CHARS = 800 * 4
MAX_LEVELS = 5
TOPK_CLUSTER = 5
LEAF_K = 6  # 聚类时每个 seed 取的近邻查询宽度(自排除后取 5)


def _summarize(oneshot: OmpOneshot, text: str) -> str:
    prompt = ("Summarize the following scientific text in at most 150 words. "
              "Preserve key facts, entities, numbers and findings. Output ONLY "
              f"the summary.\n\nTEXT:\n{text[:MAX_NODE_CHARS]}")
    out = oneshot(prompt).strip()
    return out or text[:1200]


def build_tree(mc, oneshot: OmpOneshot, force: bool = False) -> dict:
    if not force and TREE_PATH.exists():
        tree = json.loads(TREE_PATH.read_text(encoding="utf-8"))
        probe = mc.call("kb_search_vector",
                        {"query": "probe study", "kb_id": KB_RAPTOR, "top_k": 1},
                        timeout=180)
        if probe.get("results") and len(tree.get("nodes", {})) > 10:
            tree["reused"] = True
            return tree

    t0 = time.perf_counter()
    corpus = load_corpus()
    # 叶子路径必须带 DR-Raptor 前缀(后端按 doc_path 首段解析所属 KB,
    # 复用 DR-Chunks800 前缀会把写入路由到别的集合 — 已实测发生)
    leaves = items_fixed(corpus, kb_prefix=KB_RAPTOR)
    leaf_metrics = build_kb(mc, KB_RAPTOR, leaves, force=True)

    nodes: dict[str, dict] = {}
    for it in leaves:
        nodes[it["path"]] = {"level": 0, "text": it["content"],
                             "src_cids": [it["meta"].split("src=")[1].split()[0]],
                             "children": []}
    level_sizes = [len(leaves)]
    summarize_calls = 0
    current = list(nodes.keys())

    for level in range(1, MAX_LEVELS + 1):
        if len(current) <= 1:
            break
        remaining = sorted(current)
        clusters: list[list[str]] = []
        while remaining:
            seed = remaining[0]
            try:
                r = mc.call("kb_search_vector",
                            {"query": nodes[seed]["text"][:2000],
                             "kb_id": KB_RAPTOR, "top_k": LEAF_K + 1},
                            timeout=180)
            except Exception:  # noqa: BLE001
                r = {}
            nbrs = []
            for hit in r.get("results") or []:
                dp = str(hit.get("doc_path", ""))
                if dp in nodes and dp in remaining and dp != seed and dp not in nbrs:
                    nbrs.append(dp)
                if len(nbrs) >= TOPK_CLUSTER:
                    break
            group = [seed] + nbrs
            clusters.append(group)
            remaining = [p for p in remaining if p not in group]
        if len(clusters) >= len(current):  # 无法合并 → 停止
            break

        new_nodes: list[str] = []
        for i, group in enumerate(clusters):
            text = "\n\n".join(nodes[p]["text"] for p in group)
            src_cids = sorted({c for p in group for c in nodes[p]["src_cids"]})
            summary = _summarize(oneshot, text)
            summarize_calls += 1
            path = f"{KB_RAPTOR}/L{level}_{i:03d}.md"
            nodes[path] = {"level": level, "text": summary,
                           "src_cids": src_cids, "children": group}
            new_nodes.append(path)
        # 摘要节点入同一 KB(collapsed tree: 叶子与摘要同索引可检索)
        for p in new_nodes:
            for attempt in (1, 2):
                try:
                    mc.call("kb_index_document",
                            {"kb_id": KB_RAPTOR, "doc_path": p,
                             "doc_name": Path(p).name,
                             "description": f"raptor L{level}",
                             "content": nodes[p]["text"]}, timeout=180)
                    break
                except Exception:  # noqa: BLE001
                    if attempt == 2:
                        raise
                    time.sleep(1.5)
        current = new_nodes
        level_sizes.append(len(new_nodes))
        print(f"  [raptor] level {level}: {len(clusters)} clusters", flush=True)

    tree = {"nodes": nodes, "levels": level_sizes,
            "summarize_calls": summarize_calls,
            "build_seconds": round(time.perf_counter() - t0, 1),
            "leaf_index": leaf_metrics, "reused": False}
    if len(level_sizes) <= 1 and len(current) > 1:
        raise RuntimeError("RAPTOR clustering merged nothing — similarity "
                           "search over the node KB returned no neighbors")
    TREE_PATH.write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")
    dump_texts(KB_RAPTOR, [{"path": p, "content": n["text"],
                            "meta": f"L{n['level']} src={','.join(n['src_cids'][:8])}"}
                           for p, n in nodes.items()])
    return tree


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from lib import McpClient
    mc = McpClient()
    oneshot = OmpOneshot(stage="raptor", timeout=300)
    try:
        t = build_tree(mc, oneshot, force=bool(os.environ.get("DR_REBUILD_KB")))
        print(json.dumps({k: v for k, v in t.items() if k != "nodes"},
                         ensure_ascii=False, indent=1))
        print(f"nodes={len(t['nodes'])} omp_calls={oneshot.calls} "
              f"cache_hits={oneshot.cache_hits}")
    finally:
        mc.close()
