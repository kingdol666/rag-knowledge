#!/usr/bin/env python3
"""157_lane_compliance — 从「已保存的会话轨迹」复算稳定性矩阵的车道契约。

为什么需要它：论文 sec4 断言「27/27 lane-contract compliance」，但稳定性矩阵的
结果文件（`review/stability-*/results/r{n}_{task}_{mode}.json`）只存了 HTTP 层
字段（http/success/turns/cost/wall_s/answer），**没有工具面**。于是「合规」只能靠
人工读 session trace —— 这正是审稿人会追问、而我们无法用脚本自证的一环。

本脚本不再重跑实验：chat.post.ts 把每轮消息落库到 `storage/claude-chat.db`
（表 messages.content = SDK 原始 JSON），会话 id 就在结果文件里。于是「这一格走了
哪条车道」可以在事后从数据库确定性复算。

车道定义（与 run_stability.py / knowledgebase-hybrid 的语义一致）：
  A 向量快车道 : 必须出现向量族工具（kb_search_vector / kb_search_two_stage /
                 kb_search_stats）
  B 逐级通道   : 必须走目录族（kb_list / kb_get_documents / kb_doc_read）且
                 **零向量调用**
  C 混合       : 允许两族并存，但必须真的发生过检索（零工具 = 该格无效）

用法：
    python scripts/157_lane_compliance.py \
        --results ../review/stability-multiround-20261013/results
输出：results/lane_compliance.json（含逐格证据 + 汇总）+ 控制台表格；exit 1 = 有违规。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
R = SUITE / "results"
DEFAULT_DB = REPO / "storage" / "claude-chat.db"

VECTOR_TOOLS = {"kb_search_vector", "kb_search_two_stage", "kb_search_stats"}
CATALOG_TOOLS = {"kb_list", "kb_get_documents", "kb_doc_read"}


def short(name: str) -> str:
    return str(name or "").split("__")[-1]


def session_tools(db: Path, sid: str) -> list[str]:
    """按落库顺序取出该会话所有 assistant.tool_use 的短工具名。"""
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute("select content from messages where session_id=?",
                           (sid,)).fetchall()
    finally:
        con.close()
    out: list[str] = []
    for (content,) in rows:
        try:
            msg = json.loads(content)
        except Exception:  # noqa: BLE001 — 非 JSON 行直接跳过
            continue
        if msg.get("type") != "assistant":
            continue
        for block in (msg.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                out.append(short(block.get("name")))
    return out


def judge(mode: str, tools: list[str]) -> dict:
    s = set(tools)
    zero = not s
    if mode == "A":
        ok = bool(s & VECTOR_TOOLS)
    elif mode == "B":
        ok = (not (s & VECTOR_TOOLS)) and bool(s & CATALOG_TOOLS)
    else:
        ok = not zero
    return {"mode": mode, "ok": bool(ok), "zero_tool": zero,
            "vector_used": sorted(s & VECTOR_TOOLS),
            "catalog_used": sorted(s & CATALOG_TOOLS),
            "tools": sorted(s), "n_calls": len(tools)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", required=True,
                    help="稳定性矩阵结果目录（含 r{n}_{task}_{mode}.json）")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--out", default=str(R / "lane_compliance.json"))
    args = ap.parse_args()

    res_dir, db = Path(args.results).resolve(), Path(args.db)
    if not res_dir.is_dir():
        raise SystemExit(f"[fatal] results dir not found: {res_dir}")
    if not db.exists():
        raise SystemExit(f"[fatal] chat db not found: {db}（无法复算车道证据）")

    cells, viol, no_sess, zero = [], [], [], []
    for f in sorted(res_dir.glob("r*_*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        sid = rec.get("session_id") or ""
        mode = str(rec.get("mode") or f.stem.split("_")[-1])
        tools = session_tools(db, sid) if sid else []
        verdict = judge(mode, tools)
        cell = {"cell": f.stem, "round": rec.get("round"), "task": rec.get("task"),
                "mode": mode, "session_id": sid, "http": rec.get("http"),
                "success": rec.get("success"), "turns": rec.get("turns"),
                "wall_s": rec.get("wall_s"), "cost_usd": rec.get("cost"),
                **verdict}
        cells.append(cell)
        if not sid:
            no_sess.append(f.stem)
        if verdict["zero_tool"]:
            zero.append(f.stem)
        if not verdict["ok"]:
            viol.append(f.stem)

    by_mode: dict[str, dict] = {}
    for m in ("A", "B", "C"):
        sub = [c for c in cells if c["mode"] == m]
        by_mode[m] = {
            "cells": len(sub),
            "compliant": sum(1 for c in sub if c["ok"]),
            "zero_tool": sum(1 for c in sub if c["zero_tool"]),
            "vector_calls_total": sum(len(c["vector_used"]) for c in sub),
            "median_wall_s": (sorted(c["wall_s"] for c in sub if c["wall_s"])[
                len(sub) // 2] if sub else None),
        }
    summary = {
        "results_dir": str(res_dir),
        "db": str(db),
        "cells": len(cells),
        "compliant": sum(1 for c in cells if c["ok"]),
        "violations": viol,
        "zero_tool_cells": zero,
        "cells_without_session": no_sess,
        "by_mode": by_mode,
        "verdict": "pass" if not viol and not zero else "fail",
    }
    out = Path(args.out)
    out.write_text(json.dumps({"summary": summary, "cells": cells},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    for c in cells:
        print(f"{'OK  ' if c['ok'] else 'VIOL'} {c['cell']:30s} n={c['n_calls']:2d} "
              f"vec={c['vector_used']} cat={c['catalog_used']}")
    print(f"\n[verdict] {summary['verdict']} — compliant "
          f"{summary['compliant']}/{summary['cells']} · zero-tool {len(zero)} · "
          f"missing-session {len(no_sess)}")
    print(f"[done] → {out}")
    return 0 if summary["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
