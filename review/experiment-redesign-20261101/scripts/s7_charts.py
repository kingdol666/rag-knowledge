# -*- coding: utf-8 -*-
"""Stage 7 可视化：消融/基线结果图表（PNG，供论文与汇报）。

色彩语言（项目惯例）：teal=本系统 A0 · 灰=对照/基线 · 橙红=警示/退化。
运行: uv run --no-sync --directory backend python .../s7_charts.py <traces.json> [floor.json]
产出: artifacts/viz/*.png
"""
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
VIZ = ART / "viz"
VIZ.mkdir(parents=True, exist_ok=True)

TEAL, GRAY, ORANGE, BLUE = "#0f766e", "#9ca3af", "#dc2626", "#3b82f6"
ARM_COLORS = {"A0": TEAL, "A1-readall": ORANGE, "A1b": GRAY, "A2": BLUE, "A3": BLUE,
              "A0f": "#0ea5e9", "A0h": "#7c3aed", "PD": "#f59e0b",
              "F-bm25": GRAY, "F-dense": GRAY, "F-rrf": GRAY}


def boot_ci(vals, resamples=5000, seed=7):
    import random
    if not vals:
        return (0.0, 0.0)
    rnd = random.Random(seed)
    n = len(vals)
    means = sorted(sum(rnd.choices(vals, k=n)) / n for _ in range(resamples))
    return (means[int(0.025 * resamples)], means[int(0.975 * resamples)])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    traces = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    arms = list(traces.keys())

    # ── 图 1：金标命中率 + 95% CI ──
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
    labels, rates, lo_s, hi_s, cols = [], [], [], [], []
    for a in arms:
        rows = traces[a]
        v = [1.0 if x.get("gold_hit") else 0.0 for x in rows]
        lo, hi = boot_ci(v)
        rates.append(sum(v) / len(v) * 100)
        lo_s.append((sum(v) / len(v) - lo) * 100)
        hi_s.append((hi - sum(v) / len(v)) * 100)
        labels.append(f"{a}\n(n={len(v)})")
        cols.append(ARM_COLORS.get(a, GRAY))
    bars = ax.bar(labels, rates, color=cols, width=0.55, yerr=[lo_s, hi_s], capsize=5)
    for b, r in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, r + 2, f"{r:.0f}%", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("金标证据命中率（%）")
    ax.set_title("消融/基线 · 金标证据命中率（bootstrap 95% CI）")
    ax.set_ylim(0, 108)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(VIZ / "chart1_gold_rate.png")

    # ── 图 2：拒答正确率（仅拒答探针题） ──
    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=150)
    labels, vals, cols = [], [], []
    for a in arms:
        rr = [x for x in traces[a] if x.get("is_refusal")]
        if not rr:
            continue
        ok = sum(1 for x in rr if x.get("refusal_ok"))
        labels.append(a)
        vals.append(ok / len(rr) * 100)
        cols.append(ARM_COLORS.get(a, GRAY))
    bars = ax.bar(labels, vals, color=cols, width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("域外拒答正确率（%）")
    ax.set_title("消融 · 域外拒答正确性（未入库领域探针）")
    ax.set_ylim(0, 108)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(VIZ / "chart2_refusal.png")

    # ── 图 3：每题读入字节（log）+ LLM 消化时间 ──
    fig, ax1 = plt.subplots(figsize=(7.6, 4.4), dpi=150)
    labels = arms
    avg_b = [sum(x.get("bytes_ingested", 0) for x in traces[a]) / len(traces[a]) / 1024 for a in arms]
    avg_d = [sum(x.get("llm_digest_seconds", 0) for x in traces[a]) / len(traces[a]) for a in arms]
    cols = [ARM_COLORS.get(a, GRAY) for a in arms]
    bars = ax1.bar(labels, avg_b, color=cols, width=0.55)
    ax1.set_ylabel("每题读入证据字节（KB）")
    ax1.set_yscale("log")
    for b, v in zip(bars, avg_b):
        ax1.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:,.0f}K", ha="center", fontsize=10)
    ax2 = ax1.twinx()
    ax2.plot(labels, avg_d, "o--", color=ORANGE, label="LLM 消化时间（模型值，右轴 s）")
    ax2.set_ylabel("LLM 消化时间（s）", color=ORANGE)
    ax2.tick_params(axis="y", colors=ORANGE)
    ax1.set_title("时间/成本口径：每题读入字节（对数轴）与模型消化时间")
    ax1.spines[["top"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(VIZ / "chart3_bytes_time.png")

    # ── 图 4：readall 首中位置分布（顺序成本，分桶直方图——位置跨全库时避免刻度粘连） ──
    rd = traces.get("A1-readall") or []
    hits = [x["first_hit_read_index"] for x in rd if x.get("first_hit_read_index")]
    if hits:
        import math
        mx = max(hits)
        nbins = max(8, min(20, int(math.sqrt(mx))))
        fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=150)
        ax.hist(hits, bins=nbins, color=ORANGE, edgecolor="white")
        med = sorted(hits)[len(hits) // 2]
        ax.axvline(med, color=TEAL, linestyle="--", linewidth=1.5,
                   label=f"中位首中位置 = {med}")
        ax.set_xlabel("逐篇通读首次命中金标的读入序号（分卷序，全库约 845 卷）")
        ax.set_ylabel("题数")
        ax.set_title(f"逐篇通读的顺序成本：首中位置分布（n={len(hits)}）")
        ax.legend(frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(VIZ / "chart4_first_hit.png")

    # ── 图 5：A0 描述路由正确率 ──
    a0 = traces.get("A0") or []
    rc = [x for x in a0 if x.get("route_correct") is not None]
    if rc:
        ok = sum(1 for x in rc if x["route_correct"])
        fig, ax = plt.subplots(figsize=(5.4, 3.6), dpi=150)
        ax.bar(["路由正确", "路由错误"], [ok, len(rc) - ok], color=[TEAL, ORANGE], width=0.45)
        for i, v in enumerate([ok, len(rc) - ok]):
            ax.text(i, v + 0.3, str(v), ha="center", fontsize=12, fontweight="bold")
        ax.set_title(f"A0 描述层路由质量：{ok}/{len(rc)}（{ok/len(rc)*100:.0f}%）")
        ax.set_ylim(0, max(ok, len(rc) - ok) * 1.3)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(VIZ / "chart5_route.png")

    print(f"charts → {VIZ}")
    for p in sorted(VIZ.glob("*.png")):
        print("  ", p.name)


if __name__ == "__main__":
    main()
