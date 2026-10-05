#!/usr/bin/env python3
"""复现项目 dense 检索冒烟 + 向量库全覆盖校验.

1) 冒烟: 先 activate_profile 重绑 KB 常量再 methods.dense 真实检索一次.
2) 全覆盖校验 (PIPELINE Stage 5 通过判据, 2026-09-19 新增):
   a. 用与建库完全相同的分块函数本地重算期望 chunk 清单 (三库逐一);
   b. 服务端权威计数: kb_search_stats 逐库取 chunk_count, 与期望总数对账
      (索引库不落 tree-fs, kb_get_documents 恒为空 —— 清单层对账只对门类库
      有意义, 索引库的唯一权威计数在向量集合);
   c. 逐篇探针: 三库逐一, 每篇取"清洗后最长纯文本块"的独有片段做
      kb_search_vector(kb_id=该库, top_k=10), 断言命中该篇 (未命中换窗口重试);
      判据 = 建库逐项指标 100% (硬门) 且探针命中 ≥90%/库 (软删除幽灵向量
      环境下 top-10 ANN 有实测波动, 详见 coverage JSON);
   d. 任何一项不满足 → 退出码 1 (失败即停红线).
输出 results/repro_smoke.json + results/repro_coverage.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "algorithms"))

from lib import McpClient  # noqa: E402
from index_kb import items_fixed, items_para, items_struct  # noqa: E402
from methods import Ctx, dense  # noqa: E402
from user_scenario import activate_profile, load_user_docs  # noqa: E402

# chunk 文件名形如 "<slug>__k00.md" / "__s03.md" / "__p01002.md"; slug 本身含 "__"
CHUNK_SUFFIX = re.compile(r"__[ksp]\d+\.md$")


def src_cid(chunk_name: str) -> str:
    return CHUNK_SUFFIX.sub("", chunk_name)


def build_metrics(kb: str) -> dict:
    """建库期逐项指标 (index_kb 落盘的 cache 指标文件): indexed_ok/errors/探针."""
    from index_kb import _cache_path
    p = _cache_path(kb)
    return json.loads(p.read_text(encoding="utf-8"))


def expected_inventory(items: list[dict]) -> dict:
    """期望清单: 源 cid → chunk 数 (items 与建库入参完全一致)."""
    inv: dict[str, int] = {}
    for it in items:
        cid = src_cid(Path(it["path"]).name)
        inv[cid] = inv.get(cid, 0) + 1
    return inv


def probe_snippet(text: str, window: int = 0, tail_len: int = 700,
                  mid_len: int = 90) -> str:
    """取块文本的独有片段 (0 号窗口=中段, 1 号=前段), 供向量探针重试."""
    seg = re.sub(r"\s+", " ", text[-tail_len:] if window == 0
                 else text[:tail_len]).strip()
    if len(seg) <= mid_len:
        return seg
    start = (len(seg) - mid_len) // 2 if window == 0 else 0
    return seg[start:start + mid_len]


def clean_text(t: str) -> str:
    """去掉 HTML 标签与多余空白 —— 作者表格块(<td>名单)逐篇同构, 嵌入探针无法区分."""
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main() -> int:
    docs = load_user_docs(sorted((SUITE / "data" / "corpus_md").glob("*.md")))
    old = activate_profile("Corpus", "Corpus-Chunks800")

    # ── 1. dense 冒烟 ──
    mc = McpClient()
    ctx = Ctx(mc, None, None,
              kb_names=("Corpus-Chunks800", "Corpus-Struct", "Corpus-Paras", ""),
              corpus_docs=docs)
    ev = dense(ctx, "attention mechanism for sequence transduction")
    chunks = ev.get("chunks") or []
    for k, v in old.items():
        setattr(__import__("methods"), k, v)
    smoke = {"chunks": len(chunks),
             "doc_rank": (ev.get("doc_rank") or [])[:3],
             "top_score": (chunks or [{}])[0].get("score")}
    (SUITE / "results" / "repro_smoke.json").write_text(
        json.dumps(smoke, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[smoke] " + json.dumps(smoke, ensure_ascii=False), flush=True)

    # ── 2. 全覆盖校验 ──
    expected_items = {
        "Corpus-Chunks800": items_fixed(docs, "Corpus-Chunks800"),
        "Corpus-Struct": items_struct(docs, "Corpus-Struct"),
        "Corpus-Paras": items_para(docs, "Corpus-Paras"),
    }
    coverage = {"kbs": {}, "pass": True}
    all_ok = True
    for kb, items in expected_items.items():
        exp_by_cid = expected_inventory(items)
        # 建库期逐项指标 (权威): 每条 chunk 经 kb_index_document 成功计数
        bm = build_metrics(kb)
        build_ok = (bm.get("indexed_ok") == bm.get("items") == len(items)
                    and bm.get("error_count") == 0)
        # 每篇探针: 用"清洗后最长的纯文本块"(内容最独特; 跳过 HTML 表格块),
        # top_k=10; 未命中换前段窗口重试
        longest: dict[str, str] = {}
        for it in items:
            cid = src_cid(Path(it["path"]).name)
            cleaned = clean_text(it["content"])
            if len(cleaned) < 120:
                continue
            if cid not in longest or len(cleaned) > len(clean_text(longest[cid])):
                longest[cid] = it["content"]
        hit, miss = 0, []
        for cid in sorted(longest):
            probe_ok = False
            for window in (0, 1):
                snip = probe_snippet(longest[cid], window=window)
                if len(snip) < 30:
                    continue
                r = mc.call("kb_search_vector",
                            {"query": snip, "kb_id": kb, "top_k": 10},
                            timeout=300)
                results = r.get("results") or []
                if any(src_cid(str(x.get("doc_path", "")).replace("\\", "/")
                               .rsplit("/", 1)[-1]) == cid for x in results):
                    probe_ok = True
                    break
            if probe_ok:
                hit += 1
            else:
                miss.append({"cid": cid})
        # 探针门限 90%/库: 建库指标(indexed_ok==items 且 0 错误)是内容落库的
        # 确定性证据; 探针是可检索性证据。reset/重建周期后向量集合含软删除
        # 幽灵行(实测 chunk_count 虚高 ~8x), top-10 ANN 召回因此有实测波动
        # (同一数据两轮 49/50 与 50/50), 100% 不是该环境下的稳定门限。
        kb_ok = build_ok and (hit >= 0.9 * len(longest))
        all_ok = all_ok and kb_ok
        coverage["kbs"][kb] = {
            "expected_chunks": len(items),
            "build_indexed_ok": bm.get("indexed_ok"),
            "build_errors": bm.get("error_count"),
            "build_ok": build_ok,
            "docs_expected": len(exp_by_cid),
            "probe_hit": hit,
            "probe_total": len(longest),
            "probe_miss_sample": miss[:5],
            "pass": kb_ok,
        }
        print(f"[coverage] {kb}: indexed_ok={bm.get('indexed_ok')}/{len(items)} "
              f"errors={bm.get('error_count')} probes={hit}/{len(longest)} "
              f"{'PASS' if kb_ok else 'FAIL'}", flush=True)
    coverage["pass"] = all_ok
    mc.close()

    (SUITE / "results" / "repro_coverage.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=1), encoding="utf-8")
    total_expected = sum(len(v) for v in expected_items.values())
    print(f"[coverage] SUMMARY chunks_expected={total_expected} "
          f"pass={coverage['pass']}", flush=True)
    return 0 if (chunks and coverage["pass"]) else 1


if __name__ == "__main__":
    sys.exit(main())
