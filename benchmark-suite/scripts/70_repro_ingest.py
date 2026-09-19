#!/usr/bin/env python3
"""RAG 算法复现项目: md 文档入库.

1) 导出: 5 门类库中的 50 篇论文按篇读回(部分 part 拼接) → data/corpus_md/*.md
2) 清理: 删除复现项目旧库(LitQA-*/Corpus-* 前缀)
3) 入库: 复现项目自有分块方案(index_kb.items_fixed/struct/para) 建
   Corpus-Chunks800 / Corpus-Struct / Corpus-Paras(自带删旧重建+探针)
4) 冒烟: methods.dense 在 Corpus-Chunks800 上真实检索一次
输出 results/repro_ingest.json。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "algorithms"))

from lib import McpClient  # noqa: E402
from user_scenario import build_baseline_kbs, load_user_docs  # noqa: E402

KB_CATEGORIES = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
                 "工程与能源", "经济与社会"]
OUT_DIR = SUITE / "data" / "corpus_md"
PREFIX = "Corpus"
STALE_PREFIXES = ("LitQA-", "Corpus-")


def read_full(mc, kb: str, doc_path: str) -> str:
    parts, offset = [], 0
    for _ in range(80):
        r = mc.call("kb_doc_read", {"kb_id": kb, "doc_path": doc_path,
                                    "offset": offset, "limit": 400,
                                    "max_chars": 40000}, timeout=120)
        c = (r or {}).get("content", "")
        parts.append(c)
        if not (r or {}).get("truncated"):
            break
        offset += c.count("\n") + 1
    return "\n".join(parts)


def export_corpus(mc) -> list[dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SUITE / "data" / "papers" / "manifest.json")
                          .read_text(encoding="utf-8"))
    slugs = {Path(p["pdf"]).stem: {"field": p["field"], "title": p["title"]}
             for p in manifest["papers"]}
    out = []
    for kb in KB_CATEGORIES:
        docs = mc.call("kb_get_documents", {"kb_id": kb}, timeout=180)
        ds = docs.get("documents") or []
        by_slug: dict[str, list[dict]] = {}
        for d in ds:
            name = str(d.get("name", ""))
            slug = next((s for s in slugs if name.startswith(s)), None)
            if slug:
                by_slug.setdefault(slug, []).append(d)
        for slug, parts in by_slug.items():
            if slug in {o["slug"] for o in out}:
                continue  # A0: 跨门类重复论文只保留首见
            parts.sort(key=lambda d: d.get("name", ""))
            texts = []
            for d in parts:
                path = d.get("path") or f"{kb}/{d.get('name', '')}"
                texts.append(read_full(mc, kb, path))
            merged = "\n\n".join(texts)
            (OUT_DIR / f"{slug}.md").write_text(merged, encoding="utf-8")
            out.append({"slug": slug, "kb": kb, "parts": len(parts),
                        "chars": len(merged), **slugs[slug]})
            print(f"[export] {slug[:50]} parts={len(parts)} chars={len(merged)}",
                  flush=True)
    missing = [s for s in slugs if s not in {o["slug"] for o in out}]
    if missing:
        raise RuntimeError(f"papers missing from category KBs: {missing[:3]}")
    return out


def clean_stale_kbs(mc) -> list[str]:
    cat = mc.call("kb_list", {"lightweight": True}, timeout=120)
    removed = []
    for k in cat.get("catalog") or []:
        name = str(k.get("name", ""))
        if name.startswith(STALE_PREFIXES):
            mc.call("kb_delete", {"kb_id": k.get("kb_id") or name}, timeout=300)
            removed.append(name)
            print(f"[clean] deleted {name}", flush=True)
    return removed


def main() -> int:
    t0 = time.perf_counter()
    mc = McpClient()
    corpus = export_corpus(mc)
    removed = clean_stale_kbs(mc)
    mc.close()

    docs = load_user_docs(sorted(OUT_DIR.glob("*.md")))
    mc = McpClient()
    baselines = build_baseline_kbs(mc, docs, PREFIX)
    mc.close()

    # dense 冒烟由 71_repro_smoke.py 负责(需先 activate_profile 重绑
    # methods 模块 KB 常量, 本脚本不做以避免误判)
    out = {"seconds": round(time.perf_counter() - t0, 1),
           "exported": len(corpus), "stale_kbs_removed": removed,
           "baselines": {k: v.get("items") for k, v in baselines.items()}}
    (SUITE / "results" / "repro_ingest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["exported"] == 50 else 1


if __name__ == "__main__":
    sys.exit(main())
