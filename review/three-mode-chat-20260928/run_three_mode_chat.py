#!/usr/bin/env python3
"""三模式(A/B/C)检索 × 平台 chat API 回答 — 3 道新设计问题, 全部真机.

协议(与 143_e2e_modes_baselines 同通道, 证据包按各模式设计预算):
  每模式各自真机检索(GPU Laya 判卷) → 该模式原生证据包(A 24k/B 40k/C 60k)
  → answer_closed_book(平台对外 chat API POST /api/claude/chat, 无工具)
产物(单 run 目录):
  arm_<m>-<qid>.json          检索原始输出(runner 原样)
  mode_<m>_<qid>_result.json  runner 摘要 + 验证门
  pack_<m>_<qid>.txt          喂给 chat API 的证据包原文
  cell_<m>_<qid>.json         chat API 完整真实输出(answer/tokens/cost/latency/timeline)
  MODES-CHAT.md               汇总报告
可断点续跑: 已存在的 cell 自动跳过.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SUITE = REPO / "benchmark-suite"
for p in (str(SUITE), str(SUITE / "experiments"), str(SUITE / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

RUN_DIR = Path(__file__).resolve().parent / ("run-" + datetime.now().strftime("%H%M%S"))

QUESTIONS = [
    {
        "qid": "Q1",
        "stratum": "single",
        "field": "large-language-models",
        "text": ("语言模型是如何逐步学会事实知识的？学习动力学呈现哪几个阶段、"
                 "性能平台期对应什么内部机制、数据分布不均衡有何影响，以及为什么用"
                 "微调向模型注入新知识会失败？(how language models learn facts "
                 "dynamics curricula hallucinations)"),
        "shelf_b": ["计算机与人工智能"],
        "gold_substrs": ["2503.21676"],
        "gold_docs": ["nlp__2503.21676__how-do-language-models-learn-facts-dynamics.md"],
        "gold_facts": [
            "三个学习阶段, 平台期后才获得精确事实知识",
            "平台期伴随基于注意力的回忆回路形成(attention patching)",
            "不均衡分布缩短平台期但导致过拟合; 数据课程可加速且缓解",
            "幻觉与知识同时出现; 微调注入新知识会快速破坏已有参数化记忆",
        ],
    },
    {
        "qid": "Q2",
        "stratum": "single",
        "field": "astronomy",
        "text": ("CoRoT 卫星的系外行星计划有哪些科学目标？它何时开始科学观测、"
                 "任务延长到什么时候？截至 2010 年夏共收集了多少条光变曲线？"
                 "为什么 CoRoT-7b 这类超级地球只能在较亮恒星的光变曲线中发现？"
                 "(CoRoT exoplanet program status results transit asteroseismology)"),
        "shelf_b": ["自然科学与地球科学"],
        "gold_substrs": ["1105.1887"],
        "gold_docs": ["astronomy__1105.1887__the-corot-exoplanet-program-status-results.md"],
        "gold_facts": [
            "两大科学目标: 凌星法探测系外行星 + 星震学(恒星内部研究)",
            "2007-02-02 开始科学观测; 初期 3 年, 延长 3 年至 2013-03",
            "截至 2010 年夏收集 129,326 条光变曲线",
            "超级地球(如 CoRoT-7b)只能在 R ≈ 14 以亮恒星的光变曲线中发现",
        ],
    },
    {
        "qid": "Q3",
        "stratum": "multi",
        "field": "chemistry",
        "text": ("在分子科学的机器学习中,Noé 等人的综述《Machine learning for "
                 "molecular simulation》与“深度空间学习 + 分子振动”数据增强方法"
                 "各自如何应对数据稀缺与建模挑战？后者在聚酰胺纳滤膜实验中把"
                 "相对误差和决定系数分别改善到多少？(machine learning molecular "
                 "simulation molecular vibration data augmentation nanofiltration)"),
        "shelf_b": ["自然科学与地球科学"],
        "gold_substrs": ["1911.02792", "2011.07200"],
        "gold_docs": ["chemistry__1911.02792__machine-learning-for-molecular-simulation.md",
                      "chemistry__2011.07200__deep-spatial-learning-with-molecular-vibrati.md"],
        "gold_facts": [
            "综述: ML 势函数/采样等视角(观点文章)",
            "振动增强: 物理合理扰动扩充分子 3D 坐标数据",
            "相对误差 16.34% → 6.71%",
            "决定系数 R² 0.16 → 0.75",
        ],
    },
]

MODES = ("A", "B", "C")
NATIVE_BUDGET = {"A": 24000, "B": 40000, "C": 60000}  # 各模式设计证据预算(143)


def main() -> int:
    from experiments.retrieval_modes import RUNNERS, ensure_laya_interpreter
    ensure_laya_interpreter()  # mode B 进程内 Laya 判卷需要; A/C 子进程自解析

    from chat_tracks import answer_closed_book
    from lib import McpClient

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[3mode] run={RUN_DIR.name} · {len(QUESTIONS)} 题 × {MODES}", flush=True)

    def spread_pack(docs: list, per_doc: int, budget: int) -> str:
        parts, total = [], 0
        for d in docs:
            if total >= budget:
                break
            piece = str(d.get("content") or "")[:per_doc]
            parts.append(piece)
            total += len(piece)
        return "\n\n".join(parts)[:budget]

    def mode_pack(out_path: Path, mode: str) -> tuple:
        """各模式原生证据包: A/B 用其检索器自产的 evidence_pack, C 用合并全文.
        仅按该模式设计预算截断 — 生成通道(chat API)对所有模式一致."""
        d = json.loads(out_path.read_text(encoding="utf-8"))
        budget = NATIVE_BUDGET.get(mode, 24000)
        if mode == "C":
            docs = d.get("docs") or []
            pack = "\n\n".join(
                f"[{r.get('doc_path', '')}]\n{r.get('content', '')}" for r in docs)
            return pack[:budget], [r.get("doc_path", "") for r in docs]
        if mode == "A":
            ordered = [r.get("doc_path", "") for r in (d.get("result_list") or [])]
        else:
            ordered = [s.get("doc_path", "") for s in (d.get("survivors") or [])]
        native = str(d.get("evidence_pack") or "")
        if native.strip():
            return native[:budget], ordered
        # 兜底: 无原生包时按判决序逐篇读头部(143 spread 策略)
        mc = McpClient()
        seen, docs = set(), []
        try:
            cat = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
            kb_of = {}
            for k in cat:
                kb_id = k.get("kb_id") or k.get("name")
                kb_of[str(k.get("name") or "").lower()] = kb_id
                kb_of[str(k.get("kb_id") or "").lower()] = kb_id
            for path in ordered:
                path = str(path).replace("\\", "/")
                key = path.lower()
                if not path or key in seen:
                    continue
                seen.add(key)
                kb_name = path.split("/")[0]
                kb_id = kb_of.get(kb_name.lower()) or kb_name
                r = mc.call("kb_doc_read", {"kb_id": kb_id,
                                            "doc_path": path.split("/", 1)[-1],
                                            "max_chars": 700}, timeout=120)
                docs.append({"doc_path": path, "content": str(r.get("content") or "")})
        finally:
            mc.close()
        return spread_pack(docs, 700, budget), [x["doc_path"] for x in docs]

    for m in MODES:
        for q in QUESTIONS:
            cell_path = RUN_DIR / f"cell_{m}_{q['qid']}.json"
            if cell_path.exists():
                print(f"[3mode] skip {m}×{q['qid']} (cell exists)", flush=True)
                continue
            arm_path = RUN_DIR / f"arm_{m}-{q['qid']}.json"
            t0 = time.time()
            qd = {"text": q["text"], "shelf_b": q["shelf_b"],
                  "gold_substr": q["gold_substrs"][0], "gold_name": ""}
            print(f"[3mode] mode {m} × {q['qid']} retrieving …", flush=True)
            try:
                summary = RUNNERS[m](qd, arm_path)
                (RUN_DIR / f"mode_{m}_{q['qid']}_result.json").write_text(
                    json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
                pack, ranked = mode_pack(arm_path, m)
                (RUN_DIR / f"pack_{m}_{q['qid']}.txt").write_text(pack, encoding="utf-8")
                ans = answer_closed_book(q["text"], pack, timeout_s=300)
                lat = round(time.time() - t0, 1)
                joined = " ".join(str(x).replace("\\", "/") for x in ranked).lower()
                gold_hits = {g: (g.lower() in joined) for g in q["gold_substrs"]}
                cell = {"qid": q["qid"], "mode": m, "question": q["text"],
                        "track": f"mode_{m}", "via": "retrieval-mode+closed-book-chat-api",
                        "retrieval": {k: summary.get(k) for k in
                                      ("ok", "real_engine", "status", "seconds", "wall_s",
                                       "n_result_docs", "judge")},
                        "gold_hit": all(gold_hits.values()), "gold_hits": gold_hits,
                        "ranked": ranked,
                        "pack_protocol": f"native:{NATIVE_BUDGET.get(m)}",
                        "evidence_chars": len(pack),
                        "answer": ans.get("answer"), "is_error": ans.get("is_error"),
                        "latency_total_s": lat, "answer_latency_s": ans.get("latency_s"),
                        "tokens": ans.get("tokens"),
                        "total_cost_usd": ans.get("total_cost_usd"),
                        "timeline_events": len(ans.get("timeline") or []),
                        "recorded_utc": datetime.now(timezone.utc).isoformat()}
            except Exception as e:  # noqa: BLE001
                cell = {"qid": q["qid"], "mode": m, "question": q["text"],
                        "track": f"mode_{m}", "via": "retrieval-mode",
                        "answer": f"(failed: {type(e).__name__}: {str(e)[:300]})",
                        "error": True, "latency_total_s": round(time.time() - t0, 1),
                        "gold_hit": False, "ranked": [], "recorded_utc":
                        datetime.now(timezone.utc).isoformat()}
            cell_path.write_text(json.dumps(cell, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
            print(f"[3mode]   → total {cell.get('latency_total_s')}s · "
                  f"gold_hit={cell.get('gold_hit')} · "
                  f"ans={len(str(cell.get('answer') or ''))}ch", flush=True)

    write_report(stamp)
    print(f"[3mode] done → {RUN_DIR / 'MODES-CHAT.md'}", flush=True)
    return 0


def write_report(stamp: str) -> None:
    L = ["# 三模式检索 × chat API 真机问答记录（3 题新设计）", "",
         f"- Run: `{RUN_DIR.name}` · 生成: {stamp}",
         "- 通道: 每模式真机检索(GPU Laya 判卷) → 各模式原生证据包"
         "(A 24k / B 40k / C 60k 设计预算) → 平台对外 chat API"
         "(`POST /api/claude/chat`, engine=claude, 无工具闭卷)",
         "- 问题: 本场次新设计, 金标事实均已在语料原文核实", ""]
    for q in QUESTIONS:
        L += [f"## {q['qid']} [{q['stratum']}] {q['field']}", "",
              f"- 问题: {q['text']}",
              f"- gold_docs: {q['gold_docs']}",
              f"- gold_facts: {'; '.join(q['gold_facts'])}", ""]
        for m in MODES:
            cell_p = RUN_DIR / f"cell_{m}_{q['qid']}.json"
            if not cell_p.exists():
                continue
            c = json.loads(cell_p.read_text(encoding="utf-8"))
            ret = c.get("retrieval") or {}
            judge = ret.get("judge") or {}
            L += [f"### 模式 {m}", "",
                  f"- 检索: ok={ret.get('ok')} real_engine={ret.get('real_engine')} "
                  f"engine={judge.get('engine') or judge.get('backend')} "
                  f"backend={judge.get('backend')} 检索耗时 {ret.get('seconds')}s "
                  f"保留文档 {ret.get('n_result_docs')} 篇",
                  f"- gold_hit: {c.get('gold_hit')} {c.get('gold_hits') or ''}",
                  f"- chat API: 总延迟 {c.get('latency_total_s')}s "
                  f"(回答 {c.get('answer_latency_s')}s) · tokens {c.get('tokens')} "
                  f"· cost ${c.get('total_cost_usd')}", "",
                  "```", str(c.get("answer") or ""), "```", ""]
    (RUN_DIR / "MODES-CHAT.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
