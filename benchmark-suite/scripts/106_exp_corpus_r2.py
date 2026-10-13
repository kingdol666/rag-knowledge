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
    sys.modules[name] = mod  # 必须注册：否则第二次 _load 会造出**新模块对象**，
    spec.loader.exec_module(mod)  # patch70 打的补丁就落不到这个对象上
    return mod


def patch70(mod70=None) -> None:
    """让 70 的语料导出对平台分页/改名鲁棒（2026-10-13 实测破坏点）.

    2026-10-13 实测：`kb_get_documents` 的返回键是 **`catalog`**（不是 `documents`），
    且分批返回（响应里有 `page/page_count/page_size/has_more/total`）。旧代码读
    `documents` → 恒空 → `by_slug` 恒空 → `export_corpus` 抛
    `RuntimeError: papers missing from category KBs: [...]`，导致 106 在"重建密索引"
    第一步就死掉（而密索引为空正是它要修的问题）。

    同时平台已把 100 篇论文按 part 拆分（如
    `artificial-intelligence__1706.03762__attention-is-all-you-need (part 1 of 5).md`），
    旧代码 `name.startswith(slug)` 匹配不到带后缀的名字。这里统一改成
    「去后缀 + 前缀匹配」，因为 read_full 按 doc_path 读回的是**整篇**文本。
    """
    if mod70 is None:
        mod70 = _load("repro70", "scripts/70_repro_ingest.py")

    def _docs(mc, kb: str) -> list[dict]:
        out, page = [], 1
        for _ in range(60):  # 分页上限，防死循环
            r = mc.call("kb_get_documents",
                        {"kb_id": kb, "page": page, "page_size": 200},
                        timeout=300) or {}
            batch = r.get("catalog") or r.get("documents") or []
            out.extend(batch)
            if not r.get("has_more") or not batch:
                break
            page += 1
        return out

    def export_corpus(mc, reuse: bool = False) -> list[dict]:
        OUT_DIR = mod70.OUT_DIR
        man = json.loads((SUITE / "data" / "papers" / "manifest.json")
                         .read_text(encoding="utf-8"))
        slugs = {Path(p["pdf"]).stem: {"field": p["field"], "title": p["title"]}
                 for p in man["papers"]}
        if reuse and all((OUT_DIR / f"{s}.md").exists() for s in slugs):
            print(f"[export] reuse: {len(slugs)} 篇已存在于 {OUT_DIR}", flush=True)
            return [{"slug": s, "kb": "reuse", "parts": 0,
                     "chars": (OUT_DIR / f"{s}.md").stat().st_size, **slugs[s]}
                    for s in slugs]
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = []
        for kb in mod70.KB_CATEGORIES:
            ds = _docs(mc, kb)
            by_slug: dict[str, list[dict]] = {}
            for d in ds:
                nm = str(d.get("name", ""))
                core = nm.split(" (part ")[0]
                slug = next((s for s in slugs if core.startswith(s)), None)
                if slug:
                    by_slug.setdefault(slug, []).append(d)
            for slug, parts in by_slug.items():
                if slug in {o["slug"] for o in out}:
                    continue  # A0: 跨门类重复论文只保留首见
                parts.sort(key=lambda d: d.get("name", ""))
                texts = []
                for d in parts:
                    path = d.get("path") or f"{kb}/{d.get('name', '')}"
                    texts.append(mod70.read_full(mc, kb, path))
                merged = "\n\n".join(texts)
                (OUT_DIR / f"{slug}.md").write_text(merged, encoding="utf-8")
                out.append({"slug": slug, "kb": kb, "parts": len(parts),
                            "chars": len(merged), **slugs[slug]})
        missing = [s for s in slugs if s not in {o["slug"] for o in out}]
        # 只有真读回整篇（≥1000 字）才算导出成功，防"空壳 md"冒充语料
        thin = [o["slug"] for o in out if o["chars"] < 1000]
        if reuse is False and (missing or thin):
            print(f"[export] 警告：缺 {len(missing)} 篇 / 疑似空壳 {len(thin)} 篇；"
                  f"已有 corpus_md 不会被删，可加 --reuse-export 复用旧导出",
                  flush=True)
        return out

    mod70.export_corpus = export_corpus


def corpus_completeness() -> dict:
    """导出目录是否与 manifest 逐篇对齐（Track B/C 的证据面就建在这 100 个文件上）."""
    man = json.loads((SUITE / "data" / "papers" / "manifest.json")
                     .read_text(encoding="utf-8"))
    slugs = {Path(p["pdf"]).stem for p in man["papers"]}
    OUT = SUITE / "data" / "corpus_md"
    sizes = {s: (OUT / f"{s}.md").stat().st_size
             for s in slugs if (OUT / f"{s}.md").exists()}
    thin = sorted(s for s, n in sizes.items() if n < 1000)
    return {"manifest": len(slugs), "exported": len(sizes),
            "missing": sorted(slugs - set(sizes))[:5], "thin": thin[:5],
            "min_bytes": min(sizes.values()) if sizes else 0,
            "total_bytes": sum(sizes.values())}


def dry_run() -> int:
    """只读盘点：要删哪些库、要建多少 chunk、密索引当前是否可用。

    为什么需要：106 会 kb_delete 掉所有 Corpus-* 库再重建（`clean_stale_kbs`
    按前缀删）。修密索引前先跑这个，确认删除面只有空壳、语料导出不残缺。
    """
    import user_scenario as us
    from index_kb import _cache_path, _content_sha

    man = json.loads((SUITE / "data" / "papers" / "manifest.json")
                     .read_text(encoding="utf-8"))
    slugs = {Path(p["pdf"]).stem for p in man["papers"]}
    md = sorted((SUITE / "data" / "corpus_md").glob("*.md"))
    docs = us.load_user_docs(md)
    items = us.items_fixed(docs, kb_prefix="Corpus-Chunks800")
    cpath = _cache_path("Corpus-Chunks800")
    cached = None
    if cpath.exists():
        try:
            meta = json.loads(cpath.read_text(encoding="utf-8"))
            cached = {"items": meta.get("items"),
                      "content_sha_match": meta.get("content_sha") == _content_sha(items),
                      "vector_probe_hits": meta.get("vector_probe_hits")}
        except Exception as e:  # noqa: BLE001
            cached = {"error": f"{type(e).__name__}: {e}"}

    mc = McpClient()
    cat = mc.call("kb_list", {"lightweight": True}, timeout=180).get("catalog") or []
    stale = [str(k.get("name")) for k in cat
             if str(k.get("name", "")).startswith(("LitQA-", "Corpus-"))]
    probe = mc.call("kb_search_vector",
                    {"query": "probe study", "kb_id": "Corpus-Chunks800", "top_k": 3},
                    timeout=300)
    live_hits = len(probe.get("results") or [])
    exported = {o.stem for o in md}
    mc.close()

    print(json.dumps({
        "mode": "dry-run（未执行任何写操作）",
        "corpus_md_files": len(md),
        "manifest_papers": len(slugs),
        "manifest_papers_missing_export": sorted(slugs - exported)[:5],
        "chunks_would_index": len(items),
        "cache": cached,
        "kb_to_delete_before_rebuild": stale,
        "chunks800_live_probe_hits": live_hits,
        "verdict": ("密索引可用（无需修复）" if live_hits else
                    "密索引为空 → c 臂/baseline 拿不到证据，需要重建 106"),
    }, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    t0 = time.perf_counter()
    mod70 = _load("repro70", "scripts/70_repro_ingest.py")
    patch70(mod70)
    import user_scenario as us
    import index_kb

    mc = McpClient()
    # 语料导出：平台分页/改名会让重导出失败；已有 100 篇完整导出时用
    # --reuse-export 复用（字节级不变），否则按 manifest 完整性自检后再决定。
    comp = corpus_completeness()
    reuse = ("--reuse-export" in sys.argv) or (
        comp["exported"] == comp["manifest"] and not comp["thin"]
        and comp["min_bytes"] >= 1000)
    print(f"[corpus] 完整性 {comp['exported']}/{comp['manifest']} 篇 · "
          f"最小 {comp['min_bytes']}B · reuse_export={reuse}", flush=True)
    corpus = mod70.export_corpus(mc, reuse=reuse)
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
    if "--dry-run" in sys.argv:
        sys.exit(dry_run())
    sys.exit(main())
