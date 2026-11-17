# -*- coding: utf-8 -*-
"""s9h_build_html_report.py — 论文实验结果 HTML 报告生成器（终版 bench 专属）。

读取 artifacts/final_bench/（唯一可引用终版）：
  s6_stats.json / s4_traces_final.json / s5_floor.json / attribution_a0_misses.json
  viz/chart1-5.png
  responses/s4_responses_*.json（--capture-responses 复现跑的逐题回复原文，可选）

生成 artifacts/final_bench/report.html：数据+分析+可视化+逐题回复原文 同文件夹自包含。
回复原文策略：HTML 内嵌每题前 1500 字符预览；完整原文从 ./responses/*.json 相对路径
按需加载（文件夹整体拷贝/共享时可用；单独打开 HTML 时提示路径依赖）。

用法：
  backend/.venv/Scripts/python.exe scripts/s9h_build_html_report.py
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
FB = ART / "final_bench"
PREVIEW_CHARS = 1500


def _b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    stats = json.loads((FB / "s6_stats.json").read_text(encoding="utf-8"))
    traces = json.loads((FB / "s4_traces_final.json").read_text(encoding="utf-8"))
    floor = json.loads((FB / "s5_floor.json").read_text(encoding="utf-8"))
    attribution = json.loads((FB / "attribution_a0_misses.json").read_text(encoding="utf-8"))

    # ── 回复原文（复现跑 sidecar；取最新一份） ──────────────────────────
    resp_dir = FB / "responses"
    responses: dict = {}
    resp_files: list[str] = []
    if resp_dir.exists():
        for f in sorted(resp_dir.glob("*.json")):
            blob = json.loads(f.read_text(encoding="utf-8"))
            # s4_responses_<HHMMSS>.json = {arm: {qid: ...}}；<arm>.json = {qid: ...}
        if f.stem.startswith("s4_responses_"):
            for arm, rows in blob.items():
                dst = resp_dir / f"{arm}.json"
                dst.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
                responses.setdefault(arm, {}).update(rows)
        else:
            arm = f.stem
            responses.setdefault(arm, {}).update(blob)
        resp_files.append(f.name)

    # ── 金标证据（provenance 题集为权威源） ────────────────────────────
    gold_evidence: dict[str, str] = {}
    qsrc = ART / "provenance" / "questions.jsonl"
    if qsrc.exists():
        for line in qsrc.read_text(encoding="utf-8").splitlines():
            if line.strip():
                q = json.loads(line)
                gold_evidence[q["id"]] = q.get("gold_evidence", "")

    # ── 图表 base64 ────────────────────────────────────────────────
    charts = {}
    for png in sorted((FB / "viz").glob("chart*.png")):
        charts[png.stem] = _b64(png)

    # ── 逐题数据组装（合并指标 + 回复原文预览/全文标记） ─────────────
    arms = [a for a in ["A0h", "PD", "A0f", "A0", "A1b", "A2", "A1-readall"] if a in traces]
    questions: dict[str, dict] = {}
    for arm in arms:
        for r in traces[arm]:
            qid = r["qid"]
            slot = questions.setdefault(qid, {"qid": qid, "is_refusal": bool(r.get("is_refusal")),
                                              "question": r.get("query", ""), "arms": {}})
            resp = responses.get(arm, {}).get(qid, {})
            full_len = len(resp.get("response_text", ""))
            slot["arms"][arm] = {
                "gold_hit": bool(r.get("gold_hit")),
                "refusal_ok": r.get("refusal_ok"),
                "route_correct": r.get("route_correct"),
                "top1": r.get("top1", ""),
                "survivors": r.get("survivors", [])[:6],
                "bytes": r.get("bytes_ingested"),
                "tool_s": r.get("tool_seconds"),
                "preview": (resp.get("response_text", "")[:PREVIEW_CHARS]),
                "has_full": full_len > 0,
                "full_len": full_len,
                "response_note": resp.get("response_note", ""),
            }

    arm_stats = stats["per_arm"]
    paired = stats.get("paired_mcnemar_vs_baseline", {})
    floor_rows = floor.get("rows") or floor.get("results") or floor

    def _fmt_floor():
        if isinstance(floor_rows, dict):
            items = floor_rows.items()
        else:
            items = [(r.get("name", "?"), r) for r in floor_rows]
        out = []
        for k, v in items:
            if isinstance(v, dict):
                hits = v.get("hits", v.get("gold_hits"))
                n = v.get("n", v.get("total", 40))
                if hits is not None:
                    out.append((k, hits, n))
        return out

    data = {
        "arms": arms,
        "armStats": arm_stats,
        "paired": paired,
        "floor": _fmt_floor(),
        "charts": charts,
        "attribution": attribution if isinstance(attribution, list) else attribution.get("rows", []),
        "questions": dict(sorted(questions.items())),
        "goldEvidence": gold_evidence,
        "respFiles": resp_files,
        "notes": {
            "metric": stats.get("metric_note", ""),
            "ood": stats.get("ood_probe_note", ""),
            "scope": stats.get("scope_note", ""),
        },
    }

    tpl = Path(__file__).with_name("s9h_report_template.html")
    html = tpl.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False))
    out = FB / "report.html"
    out.write_text(html, encoding="utf-8")
    size_mb = out.stat().st_size / 1e6
    print(f"report.html written: {out} ({size_mb:.1f} MB, "
          f"{len(questions)} questions × {len(arms)} arms, responses files: {resp_files})")


if __name__ == "__main__":
    main()
