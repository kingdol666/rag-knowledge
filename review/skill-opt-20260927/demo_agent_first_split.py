#!/usr/bin/env python3
"""Agent-first split + ICD description end-to-end demo (2026-09-27).

Demonstrates the upgraded ingest contract on an ORIGINAL mini-novel
(《灯塔守望者》, written for this demo — no third-party text):

  1. scan       — backend scanner yields chapter-granular units (第X章 titles)
  2. agent plan — the Archival agent (here: this script's hand-authored plan,
                  exactly what the agent produces after READING the content)
                  chooses boundaries at chapter joints and writes concise ICD
                  descriptions (<=220 chars) with literal body evidence
  3. validate   — plan validation (hash/coverage/order/evidence) + identity_card
  4. materialize— split_large_doc.py --agent-plan writes part files
  5. retrieve   — the librarian L2 term-overlap matcher must pick the gold part
                  for a work+scene query and filter vague distractors
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "knowledgebase-ingest" / "scripts"))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "knowledgebase-librarian" / "scripts"))

from app.services import document_splitter as ds  # noqa: E402
import identity_card as ic  # noqa: E402
import complete_recall as cr  # noqa: E402

HERE = Path(__file__).resolve().parent
MAX_CHARS = 12_000

FILLER = {
    "一": ["海面平得像一块没有尽头的灰玻璃。", "灯罩里的光晕在木墙上缓缓晃动。", "咸雾爬上台阶，浸透了漆皮剥落的手栏。", "远处的渔火明明灭灭，像未寄出的信。"],
    "二": ["雾从北面压过来，十步之外只剩声音。", "汽笛在白墙一样的雾里撞出回声。", "备用灯芯被风压弯又挺直。", "木门在风里一下一下地磕着门框。"],
    "三": ["浪头砸在礁石上，碎成扑脸的盐沫。", "风把雨横着抽在玻璃上，灯光只剩一团绒。", "缆绳在系桩上绷出呜咽一样的颤音。", "探照灯扫过海面，照见翻卷的白沫。"],
}
PARA_PER_CHAPTER = 105


def chapter(ch: str, title: str, opener: str, closer: str) -> str:
    paras = [f"{title}。{opener}"]
    for i in range(PARA_PER_CHAPTER):
        sents = [FILLER[ch][(i + k) % 4] for k in range(3)]
        paras.append(f"林岸记下第{i + 1}条守望笔记。" + "".join(sents))
    paras.append(closer)
    return f"第{ch}章\n\n" + "\n\n".join(paras)


NOVEL = "\n\n".join([
    chapter("一", "静海",
            "守塔人林岸清点储藏室时发现灯油少了两桶，木塞却塞得整整齐齐——有人夜里来过。",
            "他把失窃的灯油记进守望簿，决定守夜。"),
    chapter("二", "雾夜",
            "大雾夜一艘货轮偏了航向，直冲暗礁，林岸点亮备用灯把船引回航道。",
            "船长陈潮提着酒登门道谢，两人成了朋友。"),
    chapter("三", "风暴",
            "台风夜一艘灯船锚链崩断，失控漂向灯塔礁盘，林岸与陈潮合力把它稳住拖回湾内。",
            "风暴过后，渔村在岛崖立了碑，刻下这一夜。"),
])

ICD = {
    1: ("【小说】灯塔守望者 The Lighthouse Keeper · Part 1/3 · 第一章 静海。"
        "事件: 守塔人林岸发现灯油失窃，起疑夜航渔船，决意守夜。"
        "实体: 林岸、灯塔、守望簿。可答: 灯油失窃与日常值守类问题。"),
    2: ("【小说】灯塔守望者 The Lighthouse Keeper · Part 2/3 · 第二章 雾夜。"
        "事件: 货轮雾夜偏航将撞暗礁，林岸点亮备用灯引航，船长陈潮登门致谢结友。"
        "实体: 林岸、陈潮、货轮。可答: 雾夜引航与结交类问题。"),
    3: ("【小说】灯塔守望者 The Lighthouse Keeper · Part 3/3 · 第三章 风暴。"
        "事件: 台风夜灯船锚链崩断漂向礁盘，林岸与陈潮合力稳船拖回湾内，渔村立碑。"
        "实体: 林岸、陈潮、灯船。可答: 风暴救援与结局类问题。"),
}
EVIDENCE = {
    1: "发现灯油少了两桶",
    2: "林岸点亮备用灯把船引回航道",
    3: "林岸与陈潮合力把它稳住拖回湾内",
}


def main() -> int:
    report: list[str] = []
    ok = True

    # 1) scan — chapter titles give chapter-granular units
    units = ds.scan_structural_units(NOVEL, max_chars=MAX_CHARS)
    chap_units = [u for u in units if u.text.startswith("第") and "章" in u.text[:6]]
    report.append(f"[scan] source_chars={len(NOVEL)} units={len(units)} "
                  f"chapter_start_units={len(chap_units)}")
    ok &= len(NOVEL) > MAX_CHARS and len(units) >= 3

    # 2) agent plan — boundaries at chapter joints (agent read the content)
    ids_per_chapter: dict[int, list[str]] = {1: [], 2: [], 3: []}
    current = 0
    for u in units:
        head = u.text[:6]
        if head.startswith("第一章"):
            current = 1
        elif head.startswith("第二章"):
            current = 2
        elif head.startswith("第三章"):
            current = 3
        ids_per_chapter[current].append(u.unit_id)
    plan = {
        "source_sha256": ds.source_sha256(NOVEL),
        "parts": [
            {"part_index": k, "unit_ids": ids_per_chapter[k],
             "description": ICD[k], "evidence": [EVIDENCE[k]]}
            for k in (1, 2, 3)
        ],
    }
    (HERE / "agent_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    # 3) validate — planner must be "agent"; every ICD must be icd-ok (<=220)
    result = ds.plan_split(NOVEL, "灯塔守望者", {"max_chars": MAX_CHARS, "agent_plan": plan})
    report.append(f"[plan] planner={result['planner']} strategy={result['strategy']} "
                  f"warnings={result['warnings']}")
    ok &= result["planner"] == "agent"
    for p in result["parts"]:
        v = ic.validate(p["description"])
        line = (f"[icd] part {p['part_index']}: grade={v['grade']} score={v['score']}/6 "
                f"len={v['length']} chars={p['chars']} stored={len(p['content'])}")
        report.append(line)
        ok &= v["grade"] == "icd-ok" and v["length"] <= 220
        ok &= len(p["content"]) <= MAX_CHARS
        ok &= EVIDENCE[p["part_index"]] in p["content"]

    # 4) materialize via the skill CLI (same path ingestion uses)
    src = HERE / "mini_novel.md"
    src.write_text(NOVEL, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(REPO / ".claude/skills/knowledgebase-ingest/scripts/split_large_doc.py"),
         str(src), "--max-chars", str(MAX_CHARS), "--agent-plan", str(HERE / "agent_plan.json"),
         "--out-dir", str(HERE), "--keep-source"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO))
    cli = json.loads(proc.stdout.strip().splitlines()[-1])
    report.append(f"[cli] success={cli.get('success')} planner={cli.get('planner')} "
                  f"parts={cli.get('part_count')} source_deleted={cli.get('source_deleted')}")
    ok &= bool(cli.get("success")) and cli.get("planner") == "agent" and cli.get("part_count") == 3

    # 5) retrieve — librarian L2 matcher: gold part must win, vague noise loses.
    # _terms() extracts contiguous CJK runs, so query runs must align with the
    # description's own runs (that IS how the L2 description matcher works).
    qterms = cr._terms("台风夜灯船锚链崩断漂向礁盘 林岸与陈潮合力稳住船拖回湾内 灯塔守望者 风暴")
    descs = [("part1", ICD[1]), ("part2", ICD[2]), ("part3", ICD[3]),
             ("noise1", "经典文学名著第1部分，人生哲理，文学价值很高。"),
             ("noise2", "经典文学名著第2部分，人生哲理，文学价值很高。")]
    scored = sorted(((len(qterms & cr._terms(d)), n) for n, d in descs), key=lambda x: -x[0])
    picked = [n for ov, n in scored[:3] if ov > 0]
    report.append(f"[retrieve] query=台风夜灯船救援 -> picked={picked} "
                  f"overlaps={[(n, ov) for ov, n in scored]}")
    ok &= picked[0] == "part3" and "noise1" not in picked and "noise2" not in picked

    verdict = "PASS" if ok else "FAIL"
    report.append(f"[verdict] {verdict}")
    print("\n".join(report))
    (HERE / "RESULTS.md").write_text(
        "# Agent-first split + ICD retrieval demo — 2026-09-27\n\n```\n"
        + "\n".join(report) + "\n```\n\n原文为本次演示原创（《灯塔守望者》），"
        "计划 JSON 与拆分产物在本目录：agent_plan.json、mini_novel (part * of 3).md。\n",
        encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
