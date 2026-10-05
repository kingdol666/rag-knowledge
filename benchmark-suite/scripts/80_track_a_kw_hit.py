#!/usr/bin/env python3
# DEPRECATED 2026-09-20 — superseded by the experiments/ platform
# (python -m experiments.runner, chat API + harness=claude). Kept only to
# reproduce historical reports. Do not use for new retrieval testing.
"""Track A KW hit 离线实算 (PLAN 步骤②′b):
对 skill_track_answers.json 的 10 份五段式回答, 按 Table1 脚注口径
"≥1 个 gold 关键词子串命中" 实算, 落盘 results/track_a_kw_hit.json。
同时输出全关键词(严格)口径以供脚注对照。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent


def main() -> int:
    qs = {q["qid"]: q for q in json.loads(
        (SUITE / "data" / "papers" / "qa_questions.json")
        .read_text(encoding="utf-8"))["questions"]}
    ans = json.loads((SUITE / "results" / "skill_track_answers.json")
                     .read_text(encoding="utf-8"))
    rows_in = ans if isinstance(ans, list) else ans.get("rows") or ans.get("answers") or []
    rows = []
    any_hit_n = all_hit_n = 0
    for r in rows_in:
        qid = r.get("qid")
        if not qid:
            continue
        # 五段式回答全文 = 所有字符串字段拼接(含 raw/references 等)
        def collect(x):
            if isinstance(x, str):
                yield x
            elif isinstance(x, dict):
                for v in x.values():
                    yield from collect(v)
            elif isinstance(x, list):
                for v in x:
                    yield from collect(v)
        text = "\n".join(collect({k: v for k, v in r.items() if k != "qid"})).lower()
        gold = [k.lower() for k in qs[qid]["gold_keywords"]]
        hit_any = [k for k in gold if k in text]
        hit_all = len(hit_any) == len(gold)
        any_hit_n += bool(hit_any)
        all_hit_n += hit_all
        rows.append({"qid": qid, "kw_any": hit_any, "n_gold": len(gold),
                     "kw_all": hit_all})
        print(f"[{qid}] any={len(hit_any)}/{len(gold)} all={hit_all}", flush=True)
    out = {"rule": "hit = >=1 gold keyword substring occurs in the five-section answer",
           "n": len(rows), "any_hit": any_hit_n, "all_hit": all_hit_n, "rows": rows}
    (SUITE / "results" / "track_a_kw_hit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] Track A any-keyword {any_hit_n}/{len(rows)}, "
          f"all-keyword {all_hit_n}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
