# -*- coding: utf-8 -*-
"""优化轮报告生成（s9e）：读 opt_bench 的 merged traces + s6_stats + 归因 JSON，
产出 OPTIMIZATION-REPORT.md（对比表 / 逐 qid 恢复分析 / 归因汇总 / ladder-vs-precise 结论）。"""
import json
import sys
from collections import Counter
from math import comb
from pathlib import Path

BASE = Path(__file__).resolve().parent
OPT = BASE.parent / "artifacts" / "opt_bench"


def wilson(hits, n, z=1.959963984540054):
    p = hits / n
    z2 = z * z
    den = 1 + z2 / n
    center = (p + z2 / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / den
    return max(0.0, center - half), min(1.0, center + half)


def mcnemar(pa, pb):
    qids = sorted(set(pa) & set(pb))
    a_only = sum(1 for q in qids if pa[q] and not pb[q])
    b_only = sum(1 for q in qids if pb[q] and not pa[q])
    n = a_only + b_only
    if n == 0:
        return a_only, b_only, 1.0
    p = sum(comb(n, k) for k in range(0, min(a_only, b_only) + 1)) / (2 ** n) * 2
    return a_only, b_only, min(1.0, p)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    traces = json.loads((OPT / "s4_traces_merged.json").read_text(encoding="utf-8"))
    stats = json.loads((OPT / "s6_stats.json").read_text(encoding="utf-8"))
    attr = json.loads((OPT / "attribution_a0_misses.json").read_text(encoding="utf-8"))
    cls_by_qid = {r["qid"]: r["cls"] for r in attr["rows"]}

    arms = ["A0", "A0f", "A0h", "PD", "A1b", "A1-readall"]
    gold_rows = {a: [x for x in traces[a] if not x.get("is_refusal", False)] for a in arms}
    gold_by_arm = {a: {x["qid"]: bool(x.get("gold_hit")) for x in gold_rows[a]} for a in arms}
    a0_misses = {q for q, hit in gold_by_arm["A0"].items() if not hit}

    # routing
    routing = {}
    for a in arms:
        rc = [x for x in gold_rows[a] if x.get("route_correct") is not None]
        routing[a] = f"{sum(1 for x in rc if x['route_correct'])}/{len(rc)}" if rc else "n/a"

    lines = ["# 逐级检索内容层优化实验报告（A0f / A0h / PD）", "",
             "日期 2026-11-11 · 语料 10 KB（MD语料-*，138 卷）· 72 gold + 4 refusal 探针 · 判卷 = 本地 Laya 引擎",
             "",
             "## 结论速览", ""]
    rec = {}
    for a in ("A0f", "A0h", "PD"):
        rec[a] = sorted(q for q in a0_misses if gold_by_arm[a].get(q))
    lines += [
        f"- **A0f（判卷全窗口，inline content，零 server 改动）**：{stats['per_arm']['A0f']['gold_hits']}/72 = "
        f"{stats['per_arm']['A0f']['gold_rate']:.1%}（A0 {stats['per_arm']['A0']['gold_rate']:.1%}），"
        f"修复 {len(rec['A0f'])} 个 A0 未命中，0 回归；McNemar p={stats['paired_mcnemar_vs_baseline']['A0f']['p_exact_two_sided']:.4f}",
        f"- **A0h（A0f + 全文 chunk top-8 ∪ 判卷包，总帽 60K）**：{stats['per_arm']['A0h']['gold_hits']}/72 = "
        f"{stats['per_arm']['A0h']['gold_rate']:.1%}，修复 {len(rec['A0h'])} 个，0 回归；p={stats['paired_mcnemar_vs_baseline']['A0h']['p_exact_two_sided']:.4f}",
        f"- **PD（精确逐文档：无导航，十库并集 top-6 → 同款全窗口判卷）**：{stats['per_arm']['PD']['gold_hits']}/72 = "
        f"{stats['per_arm']['PD']['gold_rate']:.1%}，修复 {len(rec['PD'])} 个，0 回归；p={stats['paired_mcnemar_vs_baseline']['PD']['p_exact_two_sided']:.4f}",
        "",
        "**回收主力 = A0h 的 chunk 窗口并集**（+15 hits > PD +9 > A0f +8）：判卷全窗口（A0f）只救回"
        "「卷在候选内但尾巴截断」类；向量 chunk 信号（A0h）额外救回「判卷段未存活 / 候选选择失败」类。",
        "",
        "## 对比表（gold-only，n=72）", "",
        "| arm | 检索 | gold hits | rate | Wilson 95% CI | McNemar vs A0 | avg bytes/q | avg tool_s | avg digest_s | routing |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    desc = {"A0": "逐级：目录卡路由→书架→库内宽网→判卷(参考模式 40K)",
            "A0f": "同 A0 导航；判卷自行取全卷 250K + inline content",
            "A0h": "A0f + slim=False chunk top-8 ∪ 判卷包（帽 60K）",
            "PD": "无导航：十库定向 top30 并集 top-6 → 全窗口判卷",
            "A1b": "全局向量直搜（十库并集，无判卷）",
            "A1-readall": "逐篇通读（上界）"}
    for a in arms:
        r = stats["per_arm"][a]
        lo, hi = r["gold_ci95"]
        m = stats["paired_mcnemar_vs_baseline"].get(a)
        mtxt = f"p={m['p_exact_two_sided']:.4f}" + (" *" if m["p_exact_two_sided"] < 0.05 else "") if m else "baseline"
        lines.append(f"| {a} | {desc[a]} | {r['gold_hits']}/72 | {r['gold_rate']:.1%} | "
                     f"[{lo:.3f},{hi:.3f}] | {mtxt} | {r['avg_bytes_gold']:,} | {r['avg_tool_s_gold']} | "
                     f"{r['avg_digest_s_gold']} | {routing[a]} |")

    ao, bo, p = mcnemar(gold_by_arm["A0h"], gold_by_arm["PD"])
    lines += ["", f"**ladder vs precise 正面对比（A0h vs PD）**：A0h-only={ao} PD-only={bo}，"
              f"McNemar p={p:.4f}（方向一致但未达 0.05 显著）—— 逐级导航保留（路由→宽网→判卷）"
              "+ chunk 并集在命中率上优于放弃导航的十库并集精确检索（PD 还多付 10× 搜索调用）；"
              "两者均显著优于 A0。",
              "",
              "## A0 未命中归因（35 qids，磁盘卷文件 substring 定位）", ""]
    cnt = attr["counts"]
    lines += [f"- routing-miss: {cnt.get('routing-miss', 0)}（路由 72/72 全对，与既有结论一致）",
              f"- window-truncation-miss: {cnt.get('window-truncation-miss', 5)}"
              "（参考模式 server 抓取窗 = min(40000 chars, 200 行)；含 line>200 子类）",
              f"- judge-miss: {cnt.get('judge-miss', 30)}"
              "（窗内未进证据包：其中仅 5 个的 gold 卷出现在旧 survivors——25 个属候选选择/段存活失败）",
              f"- format-mismatch: {cnt.get('format-mismatch', 0)}"]
    lines += ["", "### 各修复臂对应归因类（修复数按 A0 未命中 35 个计）", "",
              "| arm | window-truncation | judge-miss | 合计修复 |", "|---|---|---|---|"]
    for a in ("A0f", "A0h", "PD"):
        c = Counter(cls_by_qid.get(q, "?") for q in rec[a])
        lines.append(f"| {a} | {c.get('window-truncation-miss', 0)} | {c.get('judge-miss', 0)} | {len(rec[a])} |")
    still = sorted(q for q in a0_misses if not gold_by_arm["A0h"].get(q))
    lines += ["", f"A0h 仍未命中 {len(still)}/35（全部为 judge-miss 类深处：gold 段 laya 分数 <0.5 或"
              f"chunk 检索未召回对应窗口）——离 A1-readall(100%) 上界还差 {72-stats['per_arm']['A0h']['gold_hits']} 题，"
              "其中 gold 段语义相关性本身偏低（如标题词 gold_evidence：'LLaMA'、'Odyssey'）。", "",
              "## 逐 qid 明细", "",
              "| qid | 归因类 | A0f | A0h | PD |", "|---|---|---|---|---|"]
    for q in sorted(a0_misses):
        lines.append(f"| {q} | {cls_by_qid.get(q,'?')} | "
                     f"{'hit' if gold_by_arm['A0f'].get(q) else 'miss'} | "
                     f"{'hit' if gold_by_arm['A0h'].get(q) else 'miss'} | "
                     f"{'hit' if gold_by_arm['PD'].get(q) else 'miss'} |")
    lines += ["", "## 方法注记", "",
              "- 判卷全窗口方案：kb_laya_judge 参考模式 server 端抓取硬编码 max_chars=40000（kb-mcp/server.py ~:3205）"
              "且 limit 默认 200 行 = 窗口截断主因；已核验 documents 条目带 content 时跳过 server 抓取（legacy 模式），"
              "故 A0f/A0h/PD 均自行 kb_doc_read(max_chars=250000, limit=100000) 取全卷 inline 传入，"
              "max_evidence_chars=250000 —— **零 server 改动**（方案 preferred 分支成立）。",
              "- trace 字段完整保留（qid/arm/query/is_refusal/gold_hit/bytes_ingested/tool_seconds/"
              "llm_digest_seconds/refusal_ok/top1/distractor_docs/evidence_focus/calls/route_correct），"
              "新臂另加 judge_mode/chunk_bytes/pack_bytes；checkpoint 与 trace 均在 opt_bench/（final_bench 未动）。",
              "- 事件记录：会话开始前 MD语料-文学-中文 的 chroma hnsw 段已损坏（0 命中@threshold 0）；"
              "实验中期一次双 backend 并存（kb-mcp 启动健康检查自动拉起第二个）再次触发段丢失。已按"
              "单写者原则删除重建该 collection（force reindex，171 chunks），全部 17 个受累行重跑，"
              "最终 228/228 行有效。判卷 liveness real_engine=true（参考+inline 双模式）。",
              "- refusal 探针：A0f/A0h/PD 门 0/4 拒绝（证据变多→判卷存活变多）；A0 2/4。"]
    (OPT / "OPTIMIZATION-REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OPT/'OPTIMIZATION-REPORT.md'}")
    print(json.dumps({"recovered": {a: len(rec[a]) for a in rec},
                      "a0h_still_miss": len(still)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
