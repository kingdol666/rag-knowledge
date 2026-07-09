# -*- coding: utf-8 -*-
"""
VFCR (Vector-First Content-Verified Retrieval) 检索策略测试。

验证策略机制：
  1. 向量快速召回 (kb_search_two_stage) 正常工作
  2. 内容验证 (kb_doc_read) 能正确评分
  3. 早退机制 (评分≥6) 能触发
  4. 标签+描述扩展在向量未命中时启动
  5. 工具调用数和耗时在合理范围
  6. KB-scoped 检索能精确定位
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import os
from pathlib import Path

# Fix Windows GBK encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 确保能 import kb-mcp 模块
KB_MCP_DIR = Path(__file__).resolve().parent.parent / "kb-mcp"
sys.path.insert(0, str(KB_MCP_DIR))

# 设置 APP_MODE=dev 让 config 读到正确的端口
os.environ.setdefault("APP_MODE", "dev")

from kb_client.client import KbClient
from config import WEB_URL, BACKEND_URL

# ─── 测试辅助 ──────────────────────────────────────────────

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[96m[i]\033[0m"

passed = 0
failed = 0
warnings = 0


def check(condition: bool, name: str, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  {PASS} {name}" + (f" -- {detail}" if detail else ""))
    else:
        failed += 1
        print(f"  {FAIL} {name}" + (f" -- {detail}" if detail else ""))


def warn_check(condition: bool, name: str, detail: str = ""):
    global warnings
    if not condition:
        warnings += 1
        print(f"  {WARN} {name}" + (f" -- {detail}" if detail else ""))


def extract_content(result) -> str:
    """从 kb_doc_read 返回值中提取 content 字符串"""
    if isinstance(result, dict):
        return result.get("content", "")
    if isinstance(result, str):
        try:
            return json.loads(result).get("content", "")
        except Exception:
            return result
    return ""


def content_score(query: str, content: str) -> dict:
    """简化版 Agent 内容评分 (真实场景中 Agent 用 LLM 判断)"""
    q = query.lower()
    c = content.lower()
    words = [w for w in q.split() if len(w) > 2]
    topic_hits = sum(1 for w in words if w in c)
    topic = min(3, topic_hits)
    core = [w for w in words if len(w) > 3]
    scenario_hits = sum(1 for w in core if w in c[:1500])
    scenario = min(3, scenario_hits)
    has_data = any(ch.isdigit() for ch in content[:1000])
    potential = 2 if (len(content) > 500 and has_data) else (1 if len(content) > 200 else 0)
    total = topic + scenario + potential
    return {"total": total, "topic": topic, "scenario": scenario, "potential": potential}


# ─── VFCR 检索流程 ─────────────────────────────────────────

async def vfcr_search(client: KbClient, query: str, kb_id: str = "",
                      test_name: str = "") -> dict:
    """执行 VFCR 检索流程"""
    print(f"\n{'='*60}")
    print(f"  {test_name}")
    print(f"  Query: \"{query}\"" + (f"  KB: {kb_id}" if kb_id else "  (cross-KB)"))
    print(f"{'='*60}")

    result = {
        "query": query, "test_name": test_name, "kb_id": kb_id,
        "step1_count": 0, "step2_verified": [], "step2_max": 0,
        "early_exit": False, "step3_count": 0, "step4_verified": [],
        "final_docs": [], "tool_calls": 0, "elapsed": 0,
    }
    t0 = time.time()

    # Step 1: 向量快速召回
    print(f"\n  {INFO} Step 1: Vector recall (kb_search_two_stage)")
    try:
        ts = await client.two_stage_search(
            query=query, kb_id=kb_id, stage1_top_k=20, stage2_top_k=5)
        result["tool_calls"] += 1
    except Exception as e:
        print(f"  {FAIL} two_stage_search error: {e}")
        result["elapsed"] = time.time() - t0
        return result

    s2 = ts.get("stage2", {}).get("results", [])
    print(f"  {INFO} Stage2 chunks: {len(s2)}")

    # 提取 top 候选文档 (去重)
    seen = set()
    top_docs = []
    for r in s2:
        dp = r.get("doc_path", "")
        if dp and dp not in seen:
            seen.add(dp)
            top_docs.append({
                "doc_path": dp, "kb_id": r.get("kb_id", ""),
                "score": r.get("score", 0), "chunk": r.get("content", "")[:200],
            })
    result["step1_count"] = len(top_docs)

    check(len(top_docs) > 0, f"[{test_name}] Step1: vector recall returned candidates",
          f"count={len(top_docs)}")

    if top_docs:
        for i, d in enumerate(top_docs[:3]):
            print(f"    [{i+1}] vec={d['score']:.3f}  {d['doc_path'][:55]}...")

    # Step 2: 内容验证
    print(f"\n  {INFO} Step 2: Content verification (kb_doc_read x{min(3, len(top_docs))})")
    for doc in top_docs[:3]:
        try:
            raw = await client.kb_doc_read(
                kb_id=doc["kb_id"], doc_path=doc["doc_path"], max_chars=3000)
            result["tool_calls"] += 1
        except Exception as e:
            print(f"    {WARN} read error: {e}")
            continue

        content = extract_content(raw)
        sc = content_score(query, content)
        print(f"    {doc['doc_path'][:55]}...")
        print(f"      len={len(content)}  score={sc['total']}/8 (T={sc['topic']} S={sc['scenario']} P={sc['potential']})")

        v = {**doc, **sc, "content_len": len(content), "content": content[:200]}
        result["step2_verified"].append(v)

    if result["step2_verified"]:
        result["step2_max"] = max(v["total"] for v in result["step2_verified"])

    # Step 2-EARLY EXIT
    if result["step2_max"] >= 6:
        result["early_exit"] = True
        result["final_docs"] = [v for v in result["step2_verified"] if v["total"] >= 6]
        result["elapsed"] = time.time() - t0
        print(f"\n  {PASS} EARLY EXIT! score >= 6, skipping expansion")
        print(f"  {INFO} Time: {result['elapsed']:.2f}s  Calls: {result['tool_calls']}")
        return result

    # Step 3: 标签+描述扩展
    print(f"\n  {INFO} Step 3: Tag+Description expansion")
    try:
        tags_raw = await client.kb_tags_list()
        result["tool_calls"] += 1
    except Exception:
        tags_raw = {}

    tags = []
    if isinstance(tags_raw, dict):
        td = tags_raw.get("tags", [])
        tags = [t if isinstance(t, str) else t.get("name", str(t)) for t in td] if isinstance(td, list) else []

    q_lower = query.lower()
    matched = [t for t in tags if t.lower() in q_lower or
               any(w in t.lower() for w in q_lower.split() if len(w) > 2)]
    print(f"  {INFO} Tags matched: {matched}")

    expansion = []
    for tag in matched[:5]:
        try:
            tr = await client.kb_doc_get_by_tag(tag=tag, kb_id="")
            result["tool_calls"] += 1
        except Exception:
            continue
        docs = tr.get("documents", []) if isinstance(tr, dict) else (tr if isinstance(tr, list) else [])
        for d in docs:
            dp = d.get("path", d.get("doc_path", ""))
            if dp and dp not in seen:
                seen.add(dp)
                expansion.append({"doc_path": dp, "kb_id": d.get("kb_id", ""),
                                  "name": d.get("name", ""), "tag": tag})

    # 标签 API 返回 0 篇时的 fallback: 用 kb_search 做元数据搜索
    if len(expansion) == 0:
        print(f"  {INFO} Tag lookup returned 0, trying kb_search (metadata) as fallback")
        try:
            ms = await client.kb_search(query=query, top_k=5)
            result["tool_calls"] += 1
        except Exception:
            ms = {}
        hits = ms.get("hits", []) if isinstance(ms, dict) else (ms if isinstance(ms, list) else [])
        for h in hits:
            dp = h.get("path", "")
            if dp and dp not in seen:
                seen.add(dp)
                expansion.append({"doc_path": dp, "kb_id": h.get("kbId", ""),
                                  "name": h.get("docName", ""), "tag": "metadata-search"})

    result["step3_count"] = len(expansion)
    print(f"  {INFO} Expansion candidates: {len(expansion)}")

    # Step 4: 扩展内容验证
    print(f"\n  {INFO} Step 4: Expansion content verification")
    for doc in expansion[:3]:
        try:
            raw = await client.kb_doc_read(
                kb_id=doc["kb_id"], doc_path=doc["doc_path"], max_chars=3000)
            result["tool_calls"] += 1
        except Exception as e:
            print(f"    {WARN} read error: {e}")
            continue
        content = extract_content(raw)
        sc = content_score(query, content)
        print(f"    {doc['doc_path'][:55]}... (tag={doc.get('tag','')})")
        print(f"      len={len(content)}  score={sc['total']}/8")
        result["step4_verified"].append({**doc, **sc, "content_len": len(content)})

    # Step 5: 综合
    all_v = result["step2_verified"] + result["step4_verified"]
    all_v.sort(key=lambda x: x["total"], reverse=True)
    result["final_docs"] = [v for v in all_v if v["total"] >= 5]

    result["elapsed"] = time.time() - t0
    print(f"\n  {INFO} Final: P0+P1={len(result['final_docs'])}  "
          f"Time={result['elapsed']:.2f}s  Calls={result['tool_calls']}")
    return result


# ─── 主测试 ────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 60)
    print("  VFCR Search Strategy Test")
    print("  (Vector-First Content-Verified Retrieval)")
    print("=" * 60)
    print(f"  Backend: {BACKEND_URL}")
    print(f"  Web:     {WEB_URL}")

    client = KbClient(web_url=WEB_URL, backend_url=BACKEND_URL, timeout=60)

    # 健康检查
    print(f"\n--- Health Check ---")
    try:
        h = await client.health_check()
        check(h.get("backend", False), "Backend available")
        if not h.get("backend"):
            print(f"\n  {FAIL} Backend not available, aborting")
            return 1
    except Exception as e:
        print(f"  {FAIL} Health check failed: {e}")
        return 1

    # 向量索引检查
    try:
        stats = await client.search_stats()
        cols = stats.get("stats", {}).get("collections", [])
        total_chunks = sum(c.get("chunk_count", 0) for c in cols)
        check(total_chunks > 0, "Vector index has data",
              f"collections={len(cols)}, total_chunks={total_chunks}")
        print(f"  {INFO} {len(cols)} collections, {total_chunks} total chunks")
    except Exception:
        print(f"  {WARN} Could not get vector stats")

    # 获取 KB 列表 (用于 KB-scoped 测试)
    try:
        kb_list = await client.kb_list()
        kbs = kb_list.get("knowledgeBases", [])
        print(f"  {INFO} KBs: {len(kbs)}")
    except Exception:
        kbs = []

    # 找到 Energy-Batteries 和 Materials-Science 的 kb_id
    eb_kb_id = ""
    ms_kb_id = ""
    for kb in kbs:
        name = kb.get("name", "")
        kb_id = kb.get("id", kb.get("kb_id", ""))
        if "Energy" in name or "Batteries" in name:
            eb_kb_id = kb_id
        if "Materials-Science" in name:
            ms_kb_id = kb_id

    # ─── 测试用例 ─────────────────────────────────────────

    results = []

    # T1: 跨库向量检索 + 内容验证 + 早退
    r1 = await vfcr_search(client,
        query="battery thermal management phase change material cooling",
        test_name="T1: Cross-KB vector recall + content verify + early exit")
    results.append(r1)
    check(r1["step1_count"] > 0, "T1: Vector recall returned candidates")
    check(r1["step2_max"] > 0, "T1: Content verification produced scores")
    warn_check(r1["tool_calls"] <= 8, "T1: Tool calls reasonable", f"calls={r1['tool_calls']}")
    warn_check(r1["elapsed"] < 30, "T1: Time reasonable", f"{r1['elapsed']:.2f}s")

    # T2: KB-scoped 向量检索 (Energy-Batteries)
    if eb_kb_id:
        r2 = await vfcr_search(client,
            query="lithium ion battery design parameters full cell",
            kb_id=eb_kb_id,
            test_name="T2: KB-scoped search (Energy-Batteries)")
        results.append(r2)
        check(r2["step1_count"] > 0, "T2: KB-scoped recall returned candidates")
        check(any("battery" in v.get("doc_path","").lower() or
                   "lithium" in v.get("doc_path","").lower()
                   for v in r2["step2_verified"]),
              "T2: Found battery-related docs in Energy-Batteries KB")
    else:
        print(f"\n  {WARN} T2 skipped: Energy-Batteries KB not found")

    # T3: 跨库搜索 2D materials
    r3 = await vfcr_search(client,
        query="2D materials roadmap graphene MXene transition metal dichalcogenide",
        test_name="T3: Cross-KB search (2D materials)")
    results.append(r3)
    check(r3["step1_count"] > 0, "T3: Vector recall returned candidates")
    check(r3["early_exit"] or r3["step2_max"] >= 4,
          "T3: Content verification found relevant docs",
          f"max_score={r3['step2_max']}")

    # T4: KB-scoped 搜索 (Materials-Science)
    if ms_kb_id:
        r4 = await vfcr_search(client,
            query="graphene MXene flexible fabric electromagnetic shielding",
            kb_id=ms_kb_id,
            test_name="T4: KB-scoped search (Materials-Science)")
        results.append(r4)
        check(r4["step1_count"] > 0, "T4: KB-scoped recall returned candidates")
        check(any("graphene" in v.get("doc_path","").lower() or
                   "mxene" in v.get("doc_path","").lower()
                   for v in r4["step2_verified"]),
              "T4: Found graphene/MXene docs in Materials-Science KB")
    else:
        print(f"\n  {WARN} T4 skipped: Materials-Science KB not found")

    # T5: 向量未命中 → 标签/元数据扩展
    r5 = await vfcr_search(client,
        query="PVA polyvinyl alcohol biaxial stretching mechanical properties crystallization",
        test_name="T5: Cross-KB search (PVA - may need expansion)")
    results.append(r5)
    check(r5["step1_count"] > 0, "T5: Vector recall returned candidates")
    if r5["early_exit"]:
        check(True, "T5: Early exit triggered (vector hit)")
    else:
        check(r5["step3_count"] > 0 or r5["tool_calls"] > 3,
              "T5: Expansion was attempted",
              f"step3_count={r5['step3_count']}, calls={r5['tool_calls']}")

    # ─── 策略验证 ─────────────────────────────────────────

    print(f"\n\n{'='*60}")
    print(f"  VFCR Strategy Validation Report")
    print(f"{'='*60}")

    print(f"\n  Results: {PASS} {passed}  {FAIL} {failed}  {WARN} {warnings}")

    print(f"\n  Per-test summary:")
    print(f"  {'Test':<45} {'S1':>3} {'S2':>3} {'Max':>4} {'Exit':>5} {'Calls':>5} {'Time':>6}")
    print(f"  {'-'*72}")
    for r in results:
        tn = r["test_name"][:43]
        s1 = r["step1_count"]
        s2 = len(r["step2_verified"])
        mx = r["step2_max"]
        ex = "Y" if r["early_exit"] else "N"
        cl = r["tool_calls"]
        tm = f"{r['elapsed']:.2f}s"
        print(f"  {tn:<45} {s1:>3} {s2:>3} {mx:>4} {ex:>5} {cl:>5} {tm:>6}")

    # 策略指标
    early_exits = sum(1 for r in results if r["early_exit"])
    avg_calls = sum(r["tool_calls"] for r in results) / max(1, len(results))
    avg_time = sum(r["elapsed"] for r in results) / max(1, len(results))
    all_have_candidates = all(r["step1_count"] > 0 for r in results)
    all_verified = all(len(r["step2_verified"]) > 0 for r in results)

    print(f"\n  Strategy metrics:")
    print(f"    Early exit rate:    {early_exits}/{len(results)} ({early_exits*100//max(1,len(results))}%)")
    print(f"    Avg tool calls:     {avg_calls:.1f}/query (target: <=8)")
    print(f"    Avg time:           {avg_time:.2f}s/query (target: <30s)")
    print(f"    All had candidates: {all_have_candidates}")
    print(f"    All verified:       {all_verified}")

    print(f"\n  Strategy validation:")
    check(all_have_candidates, "All queries returned vector candidates")
    check(all_verified, "All queries had content verification")
    check(avg_calls <= 8, "Avg tool calls within target", f"{avg_calls:.1f}")
    warn_check(avg_time < 30, "Avg time within target", f"{avg_time:.2f}s")
    warn_check(early_exits > 0, "At least one early exit", f"{early_exits}/{len(results)}")

    print(f"\n  {'='*60}")
    if failed == 0:
        print(f"  ALL TESTS PASSED")
    else:
        print(f"  {failed} test(s) failed")
    print(f"  {'='*60}")

    await client.aclose()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
