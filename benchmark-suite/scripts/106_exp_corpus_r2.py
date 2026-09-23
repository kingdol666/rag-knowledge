#!/usr/bin/env python3
"""Exp 语料扩展到 100 篇 — 为三轨实验准备同源外部语料.

1) 导出: 复用 70.export_corpus, 5 门类库 100 篇(两轮)按篇读回拼接 part
   → data/corpus_md/*.md(100 文件)
2) 清理: 删除 Corpus-* 旧复刻库(当前为空壳)
3) 重建: 仅 Corpus-Chunks800(items_fixed 800 字符分块, Track C 密索引;
   Corpus-Struct/Paras 本轮实验不用, 不建)
4) 冒烟: kb_search_vector 在 Corpus-Chunks800 上以第二轮论文问题探针,
   须命中第二轮论文 chunk
输出 results/r2_exp_corpus.json。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "algorithms"))

from lib import McpClient  # noqa: E402


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, SUITE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    t0 = time.perf_counter()
    mod70 = _load("repro70", "scripts/70_repro_ingest.py")
    import user_scenario as us
    import index_kb

    mc = McpClient()
    corpus = mod70.export_corpus(mc)          # 100 篇导出
    removed = mod70.clean_stale_kbs(mc)       # 删 Corpus-* 空壳
    docs = us.load_user_docs(sorted(mod70.OUT_DIR.glob("*.md")))
    print(f"[corpus] {len(docs)} md docs loaded", flush=True)
    items = us.items_fixed(docs, kb_prefix="Corpus-Chunks800")
    print(f"[chunks] {len(items)} fixed-800 chunks", flush=True)
    built = index_kb.build_kb(mc, "Corpus-Chunks800", items)
    mc.close()

    # 冒烟: 第二轮论文问题必须命中第二轮论文 chunk
    mc = McpClient()
    probes = [
        ("2203.02155", "How does InstructGPT align language models with human intent via reinforcement learning from human feedback?"),
        ("2409.13934", "GAN downscaling precipitation extremes warmer climates extrapolation"),
        ("q-bio-0408016", "influenza vaccine epitope antigenic drift statistical mechanics"),
    ]
    smoke = []
    for aid, q in probes:
        r = mc.call("kb_search_vector",
                    {"query": q, "kb_id": "Corpus-Chunks800", "top_k": 5,
                     "score_threshold": 0.0}, timeout=300)
        hits = [str(x.get("doc_path", "")).replace("\\", "/")
                for x in (r.get("results") or [])]
        hit = any(aid in h for h in hits)
        smoke.append({"aid": aid, "hit": hit, "top": hits[:2]})
        print(f"[smoke] {aid}: {'HIT' if hit else 'MISS'}", flush=True)
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    kb = next((k for k in cat.get("catalog") or []
               if k.get("name") == "Corpus-Chunks800"), {})
    mc.close()

    out = {"seconds": round(time.perf_counter() - t0, 1),
           "exported": len(corpus), "corpus_files": len(docs),
           "chunks": built.get("items"), "stale_kbs_removed": removed,
           "kb_doc_count": kb.get("doc_count"), "smoke": smoke}
    (SUITE / "results" / "r2_exp_corpus.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "smoke"},
                     ensure_ascii=False), flush=True)
    ok = (len(corpus) == 100 and len(docs) == 100
          and all(s["hit"] for s in smoke))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
