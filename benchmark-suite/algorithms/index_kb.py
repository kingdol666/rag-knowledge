#!/usr/bin/env python3
"""基线索引构建 — 用被测系统自己的嵌入服务(BAAI/bge-m3)为复现算法建分块级 KB.

四类索引(全部入库即度量, 指标进入 ingestion 块):
  DR-Chunks800 : 定窗滑块 800/400 tokens(single-pass / ITRG / RAPTOR 叶子)
  DR-Struct    : structure-based chunking, overlap 0(Search-o1)
  DR-Paras     : 段落级单元(DeepRead Retrieve)
  DR-Raptor    : RAPTOR Collapsed Tree 全节点(叶子+各层摘要; 由 raptor.py 填充)
KB 复用策略: 存在且 cache/<name>.json 指纹一致 → 复用; 否则删库重建。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from lib import McpClient  # noqa: E402

from corpus import (chunk_fixed, chunk_structure,  # noqa: E402
                    load_corpus, parse_structure)

ALGO = Path(__file__).resolve().parent
CACHE = ALGO / "cache"
CACHE.mkdir(exist_ok=True)

KB_FIXED = "DR-Chunks800"
KB_STRUCT = "DR-Struct"
KB_PARA = "DR-Paras"
KB_RAPTOR = "DR-Raptor"


def _cache_path(name: str) -> Path:
    return CACHE / f"index_{name}.json"


def _content_sha(items: list[dict]) -> str:
    import hashlib
    h = hashlib.sha256()
    for it in items:
        h.update(it["path"].encode())
        h.update(b"\x00")
        h.update(it["content"].encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()[:16]


def _delete_kb(mc: McpClient, kb_name: str) -> None:
    try:
        r = mc.call("kb_list", {"lightweight": True}, timeout=120)
        for k in r.get("catalog") or []:
            if k.get("name") == kb_name:
                mc.call("kb_delete", {"kb_id": k["kb_id"]}, timeout=300)
                time.sleep(2)
                return
    except Exception:  # noqa: BLE001
        pass


def build_kb(mc: McpClient, kb_name: str, items: list[dict],
             force: bool = False, batch: int = 25) -> dict:
    """items=[{path, content, meta}] → 索引级 KB; 返回构建/复用指标。

    逐条 kb_index_document(content 直传): 文档不落 tree-fs, 纯向量+BM25 索引,
    chunk 文本以 cache 指纹文件为准留档。批间 flush, 失败重试一次。
    """
    cpath = _cache_path(kb_name)
    sha = _content_sha(items)
    if not force and cpath.exists():
        try:
            meta = json.loads(cpath.read_text(encoding="utf-8"))
            if meta.get("content_sha") == sha and meta.get("items") == len(items):
                probe = mc.call("kb_search_vector",
                                {"query": "probe study", "kb_id": kb_name,
                                 "top_k": 1}, timeout=180)
                if probe.get("results"):
                    return {**meta, "reused": True}
        except Exception:  # noqa: BLE001
            pass

    t0 = time.perf_counter()
    last_err: Exception | None = None
    for attempt in (1, 2):  # 曾观测到并发代际切换吞集合 — 失败自动整轮重试一次
        try:
            return _build_kb_once(mc, kb_name, items, cpath, sha, t0, batch)
        except RuntimeError as e:
            last_err = e
            print(f"    [{kb_name}] build attempt {attempt} failed: {e}; retrying",
                  flush=True)
            time.sleep(5)
    raise last_err  # type: ignore[misc]


def _build_kb_once(mc: McpClient, kb_name: str, items: list[dict],
                   cpath: Path, sha: str, t0: float, batch: int) -> dict:
    _delete_kb(mc, kb_name)
    mc.call("kb_create", {"name": kb_name,
                          "description": "DeepRead baseline reproduction index"},
            timeout=180)
    ok, err = 0, []
    for i, it in enumerate(items):
        for attempt in (1, 2):
            try:
                mc.call("kb_index_document",
                        {"kb_id": kb_name, "doc_path": it["path"],
                         "doc_name": Path(it["path"]).name,
                         "description": str(it.get("meta", ""))[:180],
                         "content": it["content"]}, timeout=180)
                ok += 1
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    err.append(f"{it['path']}: {str(e)[:80]}")
                time.sleep(1.5)
        if (i + 1) % batch == 0:
            print(f"    [{kb_name}] {i+1}/{len(items)} indexed", flush=True)
    probe = {"results": []}
    try:
        probe = mc.call("kb_search_vector",
                        {"query": "probe study", "kb_id": kb_name, "top_k": 1},
                        timeout=180)
    except Exception:  # noqa: BLE001
        pass
    metrics = {"kb": kb_name, "items": len(items), "indexed_ok": ok,
               "errors": err[:10], "error_count": len(err),
               "vector_probe_hits": len(probe.get("results") or []),
               "content_sha": sha, "reused": False,
               "build_seconds": round(time.perf_counter() - t0, 1)}
    if metrics["vector_probe_hits"] == 0 and ok > 0:
        # 新建索引必须可查 — 静默空集合曾让 RAPTOR 聚类整层退化(已发生过)。
        raise RuntimeError(f"{kb_name}: indexed {ok} docs but vector probe "
                           f"returns 0 hits — collection not queryable")
    cpath.write_text(json.dumps(metrics, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    dump_texts(kb_name, items)
    return metrics


def dump_texts(kb_name: str, items: list[dict]) -> None:
    """chunk 文本留档: cache/texts_<KB>.json {path: {text, meta}} — 检索证据取用处."""
    (CACHE / f"texts_{kb_name}.json").write_text(
        json.dumps({it["path"]: {"text": it["content"], "meta": it.get("meta", "")}
                    for it in items}, ensure_ascii=False), encoding="utf-8")


def load_texts(kb_name: str) -> dict:
    p = CACHE / f"texts_{kb_name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ── 各索引的 item 生成 ────────────────────────────────────────────────────────

def items_fixed(corpus, kb_prefix=KB_FIXED):
    out = []
    for d in corpus:
        for j, ch in enumerate(chunk_fixed(d["text"])):
            out.append({"path": f"{kb_prefix}/{d['cid']}__k{j:02d}.md",
                        "content": ch, "meta": f"src={d['cid']} fixed800/400"})
    return out


def items_struct(corpus) -> list[dict]:
    out = []
    for d in corpus:
        for j, ch in enumerate(chunk_structure(d["text"])):
            out.append({"path": f"{KB_STRUCT}/{d['cid']}__s{j:02d}.md",
                        "content": ch, "meta": f"src={d['cid']} struct-o0"})
    return out


def items_para(corpus) -> list[dict]:
    out = []
    for d in corpus:
        for sec in parse_structure(d):
            for p in sec.paras:
                out.append({"path": f"{KB_PARA}/{d['cid']}__p{sec.sec:02d}{p.para:03d}.md",
                            "content": p.text,
                            "meta": f"src={p.doc} coords={p.coords}"})
    return out


def build_all(mc: McpClient, force: bool = False) -> dict:
    corpus = load_corpus()
    out = {}
    for name, fn in ((KB_FIXED, items_fixed), (KB_STRUCT, items_struct),
                     (KB_PARA, items_para)):
        print(f"[index] {name} ...", flush=True)
        out[name] = build_kb(mc, name, fn(corpus), force=force)
        print(f"    -> {out[name]}", flush=True)
    return out


def src_of(doc_path: str) -> str:
    """'DR-Chunks800/31715818__k00.md' → '31715818'."""
    base = str(doc_path).replace("\\", "/").rsplit("/", 1)[-1]
    return base.split("__")[0]


if __name__ == "__main__":
    mc = McpClient()
    try:
        print(json.dumps(build_all(mc, force=bool(os.environ.get("DR_REBUILD_KB"))),
                         ensure_ascii=False, indent=1))
    finally:
        mc.close()
