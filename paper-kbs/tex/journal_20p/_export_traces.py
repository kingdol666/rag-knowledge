# -*- coding: utf-8 -*-
"""导出去内容化 per-question traces CSV（论文补充材料/Data availability 用）。

来源: review/experiment-redesign-20261101/artifacts/{final_bench,replication_bench_20261112}
输出: 本目录 supp_traces_frozen.csv / supp_traces_followup.csv / supp_traces_floor.csv
字段: run,arm,qid,gold_hit,is_refusal,refusal_ok,bytes_ingested,tool_seconds,calls,
      route_slug,route_correct,evidence_focus,first_hit_read_index
不含: 题面文本、金标串、证据包原文（去内容化；qid 对应公开题集）。
"""
import csv
import io
import json
from pathlib import Path

ART = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\experiment-redesign-20261101\artifacts")
OUTDIR = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal_20p")
FIELDS = ["run", "arm", "qid", "gold_hit", "is_refusal", "refusal_ok", "bytes_ingested",
          "tool_seconds", "calls", "route_slug", "route_correct", "evidence_focus",
          "first_hit_read_index"]


def to_row(run, arm, r):
    rk = r.get("refusal_ok")
    fc = r.get("route_correct")
    fh = r.get("first_hit_read_index")
    return {
        "run": run, "arm": arm, "qid": r.get("qid", ""),
        "gold_hit": bool(r.get("gold_hit")), "is_refusal": bool(r.get("is_refusal")),
        "refusal_ok": "" if rk is None else bool(rk),
        "bytes_ingested": r.get("bytes_ingested", ""),
        "tool_seconds": r.get("tool_seconds", ""),
        "calls": r.get("calls", ""),
        "route_slug": r.get("route_slug", ""),
        "route_correct": "" if fc is None else bool(fc),
        "evidence_focus": r.get("evidence_focus", ""),
        "first_hit_read_index": "" if fh is None else fh,
    }


def dump_csv(path, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    Path(path).write_text(buf.getvalue(), encoding="utf-8", newline="")
    return len(rows)


def main():
    frozen = json.loads((ART / "final_bench" / "s4_traces_final.json").read_text(encoding="utf-8"))
    follow = json.loads((ART / "replication_bench_20261112" / "s4_traces_r3_statsready.json").read_text(encoding="utf-8"))
    floor = json.loads((ART / "final_bench" / "s5_floor.json").read_text(encoding="utf-8"))

    rows = []
    for arm, lst in frozen.items():
        for r in lst:
            rows.append(to_row("frozen-20261111", arm, r))
    print("frozen rows:", dump_csv(OUTDIR / "supp_traces_frozen.csv", rows))

    rows = []
    for arm, lst in follow.items():
        for r in lst:
            rows.append(to_row("followup-20261112", arm, r))
    print("followup rows:", dump_csv(OUTDIR / "supp_traces_followup.csv", rows))

    rows = []
    for arm, lst in floor.items():
        for r in lst:
            rows.append({"run": "floor", "arm": arm, "qid": r.get("qid", ""),
                         "gold_hit": bool(r.get("gold_hit")), "is_refusal": False,
                         "refusal_ok": "", "bytes_ingested": r.get("bytes_ingested", ""),
                         "tool_seconds": r.get("tool_seconds", ""), "calls": r.get("calls", 1),
                         "route_slug": "", "route_correct": "",
                         "evidence_focus": r.get("evidence_focus", ""),
                         "first_hit_read_index": ""})
    print("floor rows:", dump_csv(OUTDIR / "supp_traces_floor.csv", rows))


if __name__ == "__main__":
    main()
