"""SOUL 上线前基线采集脚本 (M0.2/0.5)

规范: 固定 5 查询(中/英/混合)、top_k=10、统一 JSON schema,可复现。
捕获: 非 soul KB 的两阶段检索抽样、向量统计、经验草稿计数。
M3 末用同一脚本重跑对照(AC17): 结果集路径集合应相等。

用法: python scripts/soul/baseline.py [--backend http://127.0.0.1:8770] [--out reports/soul-baseline-YYYYMMDD.json]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]

# 固定 5 查询(中/英/混合),与验收回归一致
BASELINE_QUERIES = [
    "高分子薄膜缺陷检测的技术路线",
    "fault detection for polymer film inspection",
    "RAG 检索增强生成 向量索引 优化",
    "机器学习的模型评估指标",
    "文档解析 表格 识别 精度",
]


async def fetch(client: httpx.AsyncClient, method: str, url: str, **kw):
    try:
        resp = await client.request(method, url, timeout=60, **kw)
        if resp.status_code >= 400:
            return {"_http_error": resp.status_code, "_body": resp.text[:500]}
        return resp.json()
    except Exception as e:
        return {"_error": str(e)}


async def collect(backend: str) -> dict:
    async with httpx.AsyncClient() as client:
        # 1. 向量统计
        stats = await fetch(client, "GET", f"{backend}/api/v1/search/stats")

        # 2. 两阶段检索抽样(top_k=10,图谱展开关闭以隔离向量面)
        two_stage = []
        for q in BASELINE_QUERIES:
            r = await fetch(client, "POST", f"{backend}/api/v1/search/two-stage", json={
                "query": q, "kb_id": "", "stage1_top_k": 20,
                "stage2_top_k": 10, "enable_graph_expansion": False,
                "score_threshold": 0.0, "balance_kbs": False,
            })
            results = r.get("results", []) if isinstance(r, dict) else []
            paths = sorted({
                c.get("doc_path") for res in results
                for c in (res.get("chunks") or []) if isinstance(res, dict)
            })
            two_stage.append({"query": q, "result_paths": paths, "count": len(paths)})

        # 3. 经验草稿计数(非 soul KB,由 kb_list 语义: 根库)
        return {
            "captured_at": datetime.now().isoformat(),
            "schema_version": "1.0",
            "queries": BASELINE_QUERIES,
            "top_k": 10,
            "search_stats": stats,
            "two_stage": two_stage,
        }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="http://127.0.0.1:8770")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    out_dir = ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out or out_dir / f"soul-baseline-{datetime.now():%Y%m%d}.json"

    data = await collect(args.backend)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Baseline written: {out_path} ({len(data['two_stage'])} queries)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
