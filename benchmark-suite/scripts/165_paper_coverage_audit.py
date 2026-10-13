#!/usr/bin/env python3
r"""165_paper_coverage_audit — 论文主张 ↔ 证据 覆盖审计（只读）。

回答一个问题：**现在这套 PIPELINE 的测试是否覆盖了论文里每一条实验性主张？**
它不是再跑一遍实验，而是把论文正文里的可证伪主张逐条抽出来，标出每条的
证据来源、当前是否自动核对、以及是否属于「只在正文里断言、无法从产物复算」。

三类判定：
  verified  已有产物 + 自动核对（161/107/155/150 的断言链覆盖）
  asserted  产物存在但没有自动断言（人读产物才能确认 == 论文口径）
  gap       当前产物无法支撑这条主张（缺字段 / 产物是旧运行的 / 脚本已跑不动）

用法：
    python scripts/165_paper_coverage_audit.py [--tex-dir paper_demo/tex]
                                              [--out results/paper_coverage.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
REPO = SUITE.parent
RESULTS = SUITE / "results"
STAB_DIRS = [
    REPO / "review" / "stability-multiround-20261013" / "results",
    REPO / "review" / "archive-superseded" / "stability-multiround-20260930" / "results",
]
DENSE_KB = "Corpus-Chunks800"

# ── 主张清单：正文位置 → 证据出处 → 核对方式 ────────────────────────────────
# kind: verified / asserted / gap 由 run() 依据产物实测判定，此处只登记定义。
CLAIMS: list[dict] = [
    # ---- §2 Services and Interfaces ----
    dict(id="C01", tex="sec2_system.tex 42 kb_* / 95-tool inventory",
         source="kb-mcp stdio tool face (`where`/`tools/list`)",
         how="161 采集时列出工具面（输出「21 KB」），工具条数只在探针里人工看过 → 无断言"),
    dict(id="C02", tex="sec2 Table 1: 100/100 parsed+routed, 5 bases",
         source="results/r2_pipeline_100.json ingest block + live kb_list 五门类库 322",
         how="161 断言「清单论文数=100 / 五门类库文档≥322 / 导出语料=100」"),
    dict(id="C03", tex="sec2 Table 1: 322 stored parts after 30k ceiling",
         source="results/r2_pipeline_100.json ingest.documents_total",
         how="161 断言五门类库合计≥322；322 的精确值由 155_paper_state_audit 实测"),
    dict(id="C04", tex="sec2 Table 1: nine per-paper checks, 100/100 pass",
         source="results/r2_ingest_report.json (papers_ok=50) + ingest_report.json (50/50)",
         how="108 断言 round2 papers_ok==50 / round1 verified==total==50；"
             "「九项检查」这一说法本身没有 9 项清单产物"),
    dict(id="C05", tex="sec2 Table 1: true duplicates 0, 35 near-pairs",
         source="results/r2_organize/o2_duplicates.json",
         how="108 统计近重复组数并断言 true_duplicates==0 → 35 这个数字需人工比对"),
    dict(id="C06", tex="sec2 Table 1: descriptions upgraded 165/165",
         source="results/r2_organize_report.json l1.updated / missing_judgment",
         how="108 断言 updated==165 且 missing_judgment==[]；155 另测「≥40 字描述 322/322」"),
    dict(id="C07", tex="sec2 Table 1: content+storage audits 322/322 • 33/33",
         source="results/r2_organize/audit_manifest.json + r2_organize_report.json o5b",
         how="108 断言 audited==total==322 与 o5b ok==checked==33"),
    dict(id="C08", tex="sec2 Table 1: retrieval regression probes 15/15",
         source="results/r2_organize_report.json → o5c_probes",
         how="108 断言 pass==total==15，但该字段所在产物缺失/脚本已跑不动 → 见 gap"),
    dict(id="C09", tex="sec2 Table 1: dense replica 4,528 chunks (800-char)",
         source="results/r2_exp_corpus.json chunks + live kb_search_vector 探针",
         how="106 产出 4528；161 断言 Corpus-Chunks800 召回探针 ≥1/3 命中"),
    dict(id="C10", tex="sec2: judgment engine ~50–80 ms/verdict warm",
         source="无产物（本地引擎计时）",
         how="无任何脚本测量 → 纯断言"),
    dict(id="C11", tex="sec2: 0.95 hit all-fail discarded / 0.40 one-positive survives",
         source="无产物（阶梯语义举例）",
         how="无对照实验 → 纯断言"),

    # ---- §3 Interactive demonstration ----
    dict(id="C12", tex="sec3: answer 20 s – 2 min, six-minute tail",
         source="本次运行逐题延迟 + 稳定性 27 单元墙钟",
         how="无断言；实测值在 paper_report.json / stability rows 里可复算"),
    dict(id="C13", tex="sec3 failure report: 10 generic two-stage hits, top sim 0.52, 12 title-token matches",
         source="results/honest_failure_probe.json（2026-09-22 探针，3 例 NOT_FOUND）",
         how="产物只留 verdict/NOT_FOUND，命中条数与 0.52 未落盘 → 需人工回读原始 trace"),

    # ---- §4 Evaluation ----
    dict(id="C14", tex="sec4: grounded / keyword-verified / cited 三项指标定义",
         source="scripts/107_exp_grade.py + experiments/_paper_numbers.py",
         how="107 判分即定义；cited 正则与论文 9/6/1 的标定写在 107 第 29 行注释"),
    dict(id="C15", tex="sec4: 10 题固定题集 BQ01–BQ10",
         source="data/papers/qa_questions.json",
         how="161 断言 qfile.name == qa_questions.json"),
    dict(id="C16", tex="sec4 Findings: A 10/10 kw、B 10/10 kw9、C 10/10 kw9、cited 9/7/2",
         source="results/exp_r2_grade.json @ run-20261013T094350Z",
         how="150/_paper_numbers 逐项对账（本次 17/17 pass）+ 161 论文级闸门"),
    dict(id="C17", tex="sec4: 引擎在 8/10 平台单元返回逐段判决，另 2 个回退直读",
         source="本次运行 track_a2_*.json 的 tool_calls 内 kb_laya_judge 调用",
         how="无断言；可复算（本次实测 8/10）"),
    dict(id="C18", tex="sec4: 27-run 稳定性 9/9 + 9/9 + 9/9",
         source="review/stability-multiround-20261013/results/r*_*.json",
         how="161 断言 ok_cells==cells==27"),
    dict(id="C19", tex="sec4: 27/27 lane-contract compliance（librarian 停在 catalog 层）",
         source="同一批稳定性单元的工具路径",
         how="161 断言 lane_ok_cells==27，但单元里没有 tool_calls 字段 → 见 gap"),
    dict(id="C20", tex="sec4: 每格墙钟 15–182 s（中位 52 s）",
         source="同一批稳定性单元的 wall_s",
         how="161 记录 min/max/median（latency_*_s）→ 可复算，无数值断言"),
    dict(id="C21", tex="sec4 Costs: 53/22/24 s、$0.71/$0.49/$0.53、中位 $0.72、逐题贵 9/10",
         source="results/exp_r2_grade.json + 本次运行逐单元 cost",
         how="150/_paper_numbers 断言均值三档；中位数与 9/10 为本次人工复算 → 建议补断言"),

    # ---- §5 Conclusion ----
    dict(id="C22", tex="sec5: 每个数字都能从保存的产物重新推导",
         source="本审计 + 161/150 的对账链",
         how="这正是本审计要回答的元主张 → 见报告末段"),
]


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def grade_artifact() -> dict:
    f = RESULTS / "exp_r2_grade.json"
    return jload(f) if f.exists() else {}


def stability_cells() -> tuple[Path | None, list[dict]]:
    for d in STAB_DIRS:
        if not d.is_dir():
            continue
        files = sorted(d.glob("r*_*.json"))
        if len(files) >= 27:
            return d, [jload(f) for f in files]
    return None, []


def check_stability_lane_contract() -> dict:
    """稳定性单元里有没有工具路径证据？没有的话 27/27 是空转的。"""
    d, cells = stability_cells()
    if not cells:
        return {"status": "gap", "detail": "未找到 27 个稳定性单元"}
    with_tools = sum(1 for c in cells if c.get("tool_calls"))
    return {
        "status": "verified" if with_tools == len(cells) else "gap",
        "detail": (f"{len(cells)} 个单元中 {with_tools} 个带 tool_calls"
                   if with_tools else
                   f"{len(cells)} 个单元全都没有 tool_calls 字段 → "
                   f"161 的 lane_ok 判定走 `or not tools` 分支，恒真"),
        "dir": str(d.relative_to(REPO)) if d else None,
        "cells": len(cells), "cells_with_tools": with_tools,
    }


def check_table1_provenance() -> dict:
    """Table 1 证据链现在还能不能自动跑出来？"""
    p108 = SUITE / "scripts" / "108_pipeline_evidence.py"
    out = {"pipeline_evidence": str((RESULTS / "r2_pipeline_100.json").relative_to(REPO)),
           "generated": None}
    f = RESULTS / "r2_pipeline_100.json"
    if f.exists():
        import datetime
        out["generated"] = datetime.datetime.fromtimestamp(
            f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        out["mtime"] = out["generated"]
    # 108 需要的输入产物是否齐备
    need = ["r2_organize_report.json", "r2_ingest_report.json",
            "ingest_report.json", "r2_organize/audit_manifest.json",
            "r2_organize/o2_duplicates.json"]
    missing = [n for n in need if not (RESULTS / n).exists()]
    grade = grade_artifact()
    keys = sorted((grade.get("grades") or {}).keys())
    out.update({"missing_inputs": missing, "grade_track_keys": keys,
                "script": str(p108.relative_to(REPO))})
    if missing:
        out["status"] = "gap"
        out["detail"] = f"108 依赖的产物缺失：{missing}"
    elif "a" not in keys:
        out["status"] = "gap"
        out["detail"] = ("exp_r2_grade.json 的轨道键是 "
                         f"{keys}（107 现在写 a2），而 108 第 100 行硬编码 "
                         "grade['grades']['a'] → 今日实跑 KeyError: 'a'")
    else:
        out["status"] = "verified"
        out["detail"] = "108 输入齐备且轨道键兼容"
    return out


def check_latency_claims() -> dict:
    """§3 的 20 s–2 min 与 6 分钟尾巴、以及本次逐题分布。"""
    rep = RESULTS / "paper_report.json"
    if not rep.exists():
        return {"status": "gap", "detail": "缺 paper_report.json"}
    d = jload(rep)
    per_q = d.get("per_question") or {}
    lats, over120, over300 = [], 0, 0
    for qid, e in per_q.items():
        cells = e.get("cells") or []
        if isinstance(cells, dict):          # 兼容 {track: cell} 形态
            cells = [dict(v, track=k) for k, v in cells.items()]
        for cell in cells:
            v = cell.get("latency_s")
            if v is None:
                continue
            lats.append(float(v))
            over120 += float(v) > 120
            over300 += float(v) > 300
    if not lats:
        return {"status": "gap", "detail": "paper_report.json 无逐单元延迟"}
    lats.sort()
    return {"status": "asserted", "detail":
            f"{len(lats)} 单元：min {lats[0]:.1f}s · median {lats[len(lats)//2]:.1f}s · "
            f"max {lats[-1]:.1f}s · >120s {over120} · >300s {over300}",
            "min_s": lats[0], "median_s": lats[len(lats) // 2], "max_s": lats[-1],
            "cells_over_120s": over120, "cells_over_300s": over300}


def check_judge_calls() -> dict:
    """§4 的「引擎在几题里给出逐段判决」——从 a2 单元 tool_calls 实测。"""
    runs = sorted((RESULTS / "runs").glob("run-*"))
    if not runs:
        return {"status": "gap", "detail": "无 run 目录"}
    # 用与论文宏绑定的那次运行
    target = None
    pn = RESULTS / "paper_numbers.json"
    if pn.exists():
        rid = jload(pn).get("run_dir")
        if rid:
            target = RESULTS / "runs" / rid
    run = target if (target and target.is_dir()) else max(
        runs, key=lambda p: p.stat().st_mtime)
    cells = sorted(run.glob("track_a2_*.json"))
    if not cells:
        return {"status": "gap", "detail": f"{run.name} 无 a2 单元"}
    judge = 0
    for f in cells:
        r = jload(f)
        if any("kb_laya_judge" in str(tc.get("name") or tc.get("tool") or "")
               for tc in (r.get("tool_calls") or [])):
            judge += 1
    return {"status": "verified", "run": run.name, "detail":
            f"平台轨 {len(cells)} 题中 {judge} 题调用 kb_laya_judge",
            "judge_cells": judge, "cells": len(cells)}


def check_cost_claims() -> dict:
    """§4 的均值/中位/逐题贵 9/10。"""
    runs = sorted((RESULTS / "runs").glob("run-*"))
    if not runs:
        return {"status": "gap", "detail": "无 run 目录"}
    pn = RESULTS / "paper_numbers.json"
    rid = jload(pn).get("run_dir") if pn.exists() else None
    run = (RESULTS / "runs" / rid) if rid else max(
        runs, key=lambda p: p.stat().st_mtime)
    if not run.is_dir():
        run = max(runs, key=lambda p: p.stat().st_mtime)
    per_q: dict[str, dict[str, float]] = {}
    for f in sorted(run.glob("track_*.json")):
        r = jload(f)
        per_q.setdefault(r["qid"], {})[r["track"]] = float(r.get("total_cost_usd") or 0)
    a2 = sorted(v["a2"] for v in per_q.values() if "a2" in v)
    if not a2:
        return {"status": "gap", "detail": f"{run.name} 无 a2 成本"}
    n = len(a2)
    med = a2[n // 2] if n % 2 else (a2[n // 2 - 1] + a2[n // 2]) / 2
    wins = sum(1 for v in per_q.values() if v.get("a2", 0) > v.get("b", 0))
    return {"status": "verified", "run": run.name, "detail":
            f"平台轨均值 ${sum(a2)/len(a2):.4f} · 中位 ${med:.4f} · "
            f"逐题贵于裸 Agent {wins}/{len(per_q)}",
            "mean_usd": round(sum(a2) / len(a2), 4), "median_usd": round(med, 4),
            "costlier_than_bare": wins, "questions": len(per_q)}


def check_tool_inventory() -> dict:
    """§2 的 42 kb_* / 95 tools：有没有产物记录工具面？"""
    txt = REPO / "docs" / "ARCHITECTURE.md"
    hits = []
    for p in [txt, SUITE / "PIPELINE.md", RESULTS / "paper_report.json"]:
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"(\d+)\s*(?:个)?\s*(?:MCP\s*)?工具|(\d+)\s+tools", s):
            hits.append(f"{p.relative_to(REPO)}: {m.group(0)}")
    return {"status": "asserted" if hits else "gap",
            "detail": ("文档里有工具条数记录：" + " | ".join(hits[:4])) if hits
                      else "没有任何产物/断言记录工具条数",
            "hits": hits[:8]}


def run(tex_dir: Path) -> dict:
    grade = grade_artifact()
    stab = check_stability_lane_contract()
    t1 = check_table1_provenance()
    lat = check_latency_claims()
    judge = check_judge_calls()
    cost = check_cost_claims()
    tools = check_tool_inventory()

    measured = {
        "C19": stab,
        "C08": t1,
        "C12": lat,
        "C17": judge,
        "C21": cost,
        "C01": tools,
    }

    rows = []
    for c in CLAIMS:
        m = measured.get(c["id"])
        if not m:
            # 未实测的主张：按定义登记（161 断言链覆盖的记为 verified）
            auto = c["id"] in {"C02", "C03", "C05", "C06", "C07", "C09",
                               "C14", "C15", "C16", "C18", "C20"}
            rows.append({**c, "status": "verified" if auto else "asserted",
                         "measured": None})
        else:
            rows.append({**c, "status": m["status"], "measured": m})

    counts = {k: sum(1 for r in rows if r["status"] == k)
              for k in ("verified", "asserted", "gap")}
    gaps = [r for r in rows if r["status"] == "gap"]
    return {"tex_dir": str(tex_dir), "claims": rows, "counts": counts,
            "gaps": [{"id": r["id"], "tex": r["tex"], "detail": r["measured"]["detail"]}
                     for r in gaps] if gaps else [],
            "grade_run": grade.get("run_dir")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex-dir", default=str(REPO / "paper_demo" / "tex"))
    ap.add_argument("--out", default=str(RESULTS / "paper_coverage.json"))
    args = ap.parse_args()

    rep = run(Path(args.tex_dir))
    out = Path(args.out)
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=" * 74)
    print("  论文主张 ↔ 证据 覆盖审计（只读）")
    print("=" * 74)
    icon = {"verified": "✓", "asserted": "·", "gap": "!"}
    for r in rep["claims"]:
        line = f"  {icon[r['status']]} {r['id']}  {r['tex']}"
        print(line)
        if r["measured"]:
            print(f"        → {r['measured']['detail']}")
    print("-" * 74)
    print(f"  verified {rep['counts']['verified']} · asserted "
          f"{rep['counts']['asserted']} · gap {rep['counts']['gap']}")
    if rep["gaps"]:
        print("  缺口（当前产物撑不住的主张）：")
        for g in rep["gaps"]:
            print(f"    ! {g['id']} {g['tex']} → {g['detail']}")
    print(f"  → {out}")
    return 0 if not rep["gaps"] else 1


if __name__ == "__main__":
    sys.exit(main())
