#!/usr/bin/env python3
"""优化版逐级检索 vs 旧 mode B — 同 3 题真机对比 + chat API 回答 + 相关性审计.

对每题: run_tiered(优化逐级检索) → 内容驱动证据包 → answer_closed_book(平台 chat API)
产出: run-<HHMMSS>/cell_opt_B_<qid>.json + pack + trace.jsonl + OPT-COMPARE.md
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SUITE = REPO / "benchmark-suite"
for p in (str(SUITE), str(SUITE / "experiments"), str(SUITE / "scripts"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.retrieval_modes import ensure_laya_interpreter  # noqa: E402
ensure_laya_interpreter()  # L5 进程内 Laya 判卷需要 GPU env; 幂等

from chat_tracks import answer_closed_book  # noqa: E402
from librarian_opt import run_tiered  # noqa: E402

OLD_RUN = REPO / "review" / "three-mode-chat-20260928" / "run-004648"

QUESTIONS = [
    {"qid": "Q1", "shelf_b": ["计算机与人工智能"], "gold_substrs": ["2503.21676"],
     "text": ("语言模型是如何逐步学会事实知识的？学习动力学呈现哪几个阶段、"
              "性能平台期对应什么内部机制、数据分布不均衡有何影响，以及为什么用"
              "微调向模型注入新知识会失败？(how language models learn facts "
              "dynamics curricula hallucinations)")},
    {"qid": "Q2", "shelf_b": ["自然科学与地球科学"], "gold_substrs": ["1105.1887"],
     "text": ("CoRoT 卫星的系外行星计划有哪些科学目标？它何时开始科学观测、"
              "任务延长到什么时候？截至 2010 年夏共收集了多少条光变曲线？"
              "为什么 CoRoT-7b 这类超级地球只能在较亮恒星的光变曲线中发现？"
              "(CoRoT exoplanet program status results transit asteroseismology)")},
    {"qid": "Q3", "shelf_b": ["自然科学与地球科学"],
     "gold_substrs": ["1911.02792", "2011.07200"],
     "text": ("在分子科学的机器学习中,Noé 等人的综述《Machine learning for "
              "molecular simulation》与“深度空间学习 + 分子振动”数据增强方法"
              "各自如何应对数据稀缺与建模挑战？后者在聚酰胺纳滤膜实验中把"
              "相对误差和决定系数分别改善到多少？(machine learning molecular "
              "simulation molecular vibration data augmentation nanofiltration)")},
]

RUN_DIR = HERE / ("run-" + datetime.now().strftime("%H%M%S"))


def old_cell(qid: str) -> dict:
    p = OLD_RUN / f"cell_B_{qid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[optB] run={RUN_DIR.name} · {len(QUESTIONS)} 题", flush=True)
    for q in QUESTIONS:
        qdir = RUN_DIR / q["qid"]
        t0 = time.time()
        print(f"[optB] {q['qid']} tiered retrieval …", flush=True)
        r = run_tiered(q["text"], q["shelf_b"], qdir)
        pack = r["pack"]
        ph = r["phase_s"]
        total = round(sum(ph.values()), 2)
        joined = json.dumps(r["pack_rows"], ensure_ascii=False).lower()
        gold_hits = {g: (g.lower() in joined) for g in q["gold_substrs"]}
        print(f"[optB] {q['qid']} retrieval {total}s "
              f"(L4 reads {ph['L4']}s · L5 judge {ph['L5']}s · L5b peek {ph['L5b_peek_read']}+{ph['L5b_judge']}s) · "
              f"retained {r['tier_counts']['retained_docs']} docs · "
              f"pack {r['tier_counts']['pack_blocks']} blocks/{r['tier_counts']['pack_chars']}ch · "
              f"gold_in_pack={all(gold_hits.values())}", flush=True)
        ans = answer_closed_book(q["text"], pack, timeout_s=300)
        cell = {"qid": q["qid"], "question": q["text"], "mode": "opt_B",
                "retrieval": {"phase_s": r["phase_s"], "phase_total_s": total,
                              "tier_counts": r["tier_counts"],
                              "real_engine": r["real_engine"], "status": r["status"],
                              "criterion": r["criterion"], "retention": r["retention"],
                              "evicted": r["evicted"]},
                "gold_in_pack": gold_hits,
                "pack_docs": sorted({row["doc_path"] for row in r["pack_rows"]}),
                "answer": ans.get("answer"), "is_error": ans.get("is_error"),
                "answer_latency_s": ans.get("latency_s"),
                "tokens": ans.get("tokens"), "total_cost_usd": ans.get("total_cost_usd"),
                "total_s": round(time.time() - t0, 1),
                "recorded_utc": datetime.now(timezone.utc).isoformat()}
        (RUN_DIR / f"cell_opt_B_{q['qid']}.json").write_text(
            json.dumps(cell, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[optB] {q['qid']} answer {ans.get('latency_s')}s · "
              f"len={len(str(ans.get('answer') or ''))}ch", flush=True)
    write_compare(stamp)
    print(f"[optB] done → {RUN_DIR / 'OPT-COMPARE.md'}", flush=True)
    return 0


def write_compare(stamp: str) -> None:
    L = ["# 优化版逐级检索(opt_B) vs 旧 mode B — 同题真机对比", "",
         f"- Run: `{RUN_DIR.name}` · 生成: {stamp}",
         "- 变化: ①L4 并行读取(窗口8) ②内容驱动保留(retain_docs 相对截断 best-0.05"
         "+overlap 契合+top3 地板) ③分数降序打包(旧=路径字典序) ④全链路 trace.jsonl",
         "- 判卷契约不变: Laya 逐段 fail-closed, yes 全收(段级)", ""]
    for q in QUESTIONS:
        new = json.loads((RUN_DIR / f"cell_opt_B_{q['qid']}.json").read_text(encoding="utf-8"))
        old = old_cell(q["qid"])
        old_ret = old.get("retrieval") or {}
        L += [f"## {q['qid']}", "",
              f"- 检索: 旧 {old_ret.get('seconds')}s → 新 {new['retrieval']['phase_total_s']}s "
              f"(L4 读 {new['retrieval']['phase_s']['L4']}s, L5 判 {new['retrieval']['phase_s']['L5']}s, "
              f"L5b peek {new['retrieval']['phase_s']['L5b_peek_read']}+{new['retrieval']['phase_s']['L5b_judge']}s)"
              f" · 旧题总 {old.get('latency_total_s')}s → 新题总 {new['total_s']}s",
              f"- 层次: 列表 {new['retrieval']['tier_counts']['docs_listed']} → 读 "
              f"{new['retrieval']['tier_counts']['docs_read']} → 判 "
              f"{new['retrieval']['tier_counts']['scored']} 段 → yes 全收 "
              f"{new['retrieval']['tier_counts']['survivors_all_yes']} 段 → 保留 "
              f"{new['retrieval']['tier_counts']['retained_docs']} 篇 → 包 "
              f"{new['retrieval']['tier_counts']['pack_blocks']} 块",
              f"- gold_in_pack: {new['gold_in_pack']} (旧 gold_hit: {old.get('gold_hit')})",
              f"- 包内文档 {len(new['pack_docs'])} 篇: "
              + "; ".join(str(p).split('/')[-1][:52] for p in new["pack_docs"]), "",
              "### 优化版回答(chat API 原样输出)", "",
              "```", str(new.get("answer") or ""), "```", ""]
        if old.get("answer"):
            L += ["### 旧版回答(对照)", "", "```", str(old.get("answer"))[:1200], "```", ""]
    (RUN_DIR / "OPT-COMPARE.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
