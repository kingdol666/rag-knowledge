"""SOUL 路由校准脚本 (M3.6)

对 backend/app/data/router-test-queries.jsonl 测试集执行自动路由,
比对 choice==expected_soul 计算准确率,输出 per-SOUL 矩阵与 precision/recall,
结果写 reports/router-calibration-YYYYMMDD.md。阈值自动建议: 正确路由置信度
5% percentile,钳位 [0.4, 0.8]。

用法: python scripts/soul/calibrate.py [--backend http://127.0.0.1:8770] [--threshold 0.6]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
TEST_SET = ROOT / "backend" / "app" / "data" / "router-test-queries.jsonl"
OUT_DIR = ROOT / "reports"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="http://127.0.0.1:8770")
    ap.add_argument("--threshold", type=float, default=None)
    args = ap.parse_args()

    if not TEST_SET.exists():
        print(f"测试集缺失: {TEST_SET}")
        return 1

    cases = []
    for ln in TEST_SET.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            cases.append(json.loads(ln))
    if not cases:
        print("测试集为空")
        return 1

    async with httpx.AsyncClient() as client:
        per_soul = defaultdict(lambda: {"tp": 0, "total": 0, "predicted": 0})
        confidences = []
        rows = []
        for c in cases:
            r = await client.post(f"{args.backend}/api/v1/soul/router", json={
                "query": c["query"], "task_goal": c.get("task_goal", ""),
                "task_type": c.get("task_type", ""),
            }, timeout=60)
            data = r.json()
            top1 = data.get("top1")
            conf = data.get("route_confidence")
            if conf is not None:
                confidences.append(conf)
            expected = c["expected_soul"]
            hit = top1 == expected
            per_soul[expected]["total"] += 1
            per_soul[expected]["predicted"] += 1
            if hit:
                per_soul[expected]["tp"] += 1
            rows.append({
                "query": c["query"][:50], "expected": expected,
                "choice": top1, "confidence": conf, "hit": hit,
                "reason": (data.get("ranked") or [{}])[0].get("reason", "")[:40],
                "uncertain": data.get("route_uncertain"),
            })

    total = len(cases)
    correct = sum(1 for r in rows if r["hit"])
    accuracy = correct / total if total else 0.0

    # 阈值建议: 正确路由置信度 5% percentile,钳位 [0.4, 0.8]
    ok_conf = [r["confidence"] for r in rows if r["hit"] and r["confidence"] is not None]
    suggested = None
    if ok_conf:
        ok_conf.sort()
        suggested = max(0.4, min(0.8, ok_conf[max(0, int(len(ok_conf) * 0.05) - 1)]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"router-calibration-{datetime.now():%Y%m%d}.md"
    lines = [
        f"# 路由校准报告 {datetime.now():%Y%m%d}",
        "",
        f"- 测试集: {len(cases)} 条,准确率 **{accuracy:.1%}**({correct}/{total})",
        f"- 阈值建议: {suggested if suggested is not None else 'N/A(无命中样本)'}(当前 {args.threshold or 0.6})",
        "",
        "## Per-SOUL 矩阵",
        "",
        "| SOUL | 样本 | 命中 | 精确率 | 召回 | 备注 |",
        "|---|---|---|---|---|---|",
    ]
    for soul, st in sorted(per_soul.items()):
        precision = st["tp"] / st["predicted"] if st["predicted"] else 0.0
        recall = st["tp"] / st["total"] if st["total"] else 0.0
        note = "⚠ recall<60%: 审查 profile-summary 质量" if recall < 0.6 else ""
        lines.append(
            f"| {soul} | {st['total']} | {st['tp']} | {precision:.0%} | {recall:.0%} | {note} |")

    lines += ["", "## 明细", "", "| # | query | expected | choice | conf | hit | reason |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r['query']} | {r['expected']} | {r['choice']} | "
                     f"{r['confidence'] if r['confidence'] is not None else '-'} | "
                     f"{'✅' if r['hit'] else '❌'} | {r['reason']} |")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"准确率 {accuracy:.1%} ({correct}/{total});报告: {out_path}")
    print(f"阈值建议: {suggested if suggested is not None else 'N/A'}")
    return 0 if accuracy >= 0.8 else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
