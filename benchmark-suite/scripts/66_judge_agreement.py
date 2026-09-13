#!/usr/bin/env python3
"""E15 + E4+ · 双 judge 一致性研究与经验基线扩展（响应评审 W3/W4）.

E15: 对同一批"经验合成材料"用两路独立 judge 评审
  Pass A  原始 judge 提示(与模块 C/E4 完全同款)
  Pass B  同 rubric 措辞扰动版(检验结论对提示措辞的稳健性)
报告逐条完全一致率(±0 分差)、Cohen's κ(二值化: score>=5 视为"可用")、
平均分差与 Pearson 相关。**如实标注: 这是 LLM–LLM 一致性, 不是人工 κ**;
人工 3 人×40-60 查询研究仍是 future work。
E4+: 基线查询从 4 条扩展到 8 条(同设计: no-synthesis / llm-summary / ours
三种材料、同一 Pass-A judge), 摘要 lessons 沿用冻结版本保持材料可比。
输出: results/run-*/judge_agreement.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (DATA, McpClient, REPO, RESULTS, WEB,  # noqa: E402
                 env_fingerprint, http_get, mean, now_iso, set_run)
from lib import step25  # noqa: E402

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
OPS_KB = "KB-Exp-Ops"

JUDGE_A = """You are a strict reviewer of an auto-generated "experience" entry
(distilled operational knowledge) for a knowledge-base system. Score it 0-10.
Rubric: grounded in real facts (not hallucinated) = up to 4 points; clear structure
(title/scenario/category present and coherent) = up to 3 points; reusable for
future retrieval tasks = up to 3 points. Reply with ONLY a JSON object:
{"score": <0-10>, "grounded": true/false, "issues": "<one short sentence>"}

EXPERIENCE:
{experience}
"""

JUDGE_B = """Act as an independent auditor rating a machine-written operational
"experience" record on a 0-10 scale. Award points for: factual grounding with no
fabrication (max 4); coherent structure covering title, scenario and category
(max 3); practical reusability for future retrieval tasks (max 3). Be strict.
Output only JSON: {"score": <0-10>, "grounded": true/false, "issues": "<one line>"}

RECORD:
{experience}
"""

QUERIES = [
    {"qid": "x-01", "question": "parsing job hangs forever and the file never appears"},
    {"qid": "x-02", "question": "why does search return zero hits after recreating a base"},
    {"qid": "x-03", "question": "suddenly every request says unauthorized"},
    {"qid": "x-04", "question": "few candidates come back for very short questions"},
    {"qid": "x-05", "question": "one big base dominates the merged ranking"},
    {"qid": "x-06", "question": "metric comes out above one, ranking looks duplicated"},
    {"qid": "x-07", "question": "distillation step yields an empty draft list"},
    {"qid": "x-08", "question": "long runs die with too-many-requests errors"},
]


def run_judge(prompt_template: str, material: str, tag: str) -> dict:
    body = material if len(material) <= 6000 else material[:6000]
    prompt = prompt_template.replace("{experience}", body)
    proc = subprocess.run(["omp", "-p", prompt, "--auto-approve", "--no-session",
                           "--max-time", "300"], cwd=str(REPO), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=360)
    m = re.search(r"\{[^{}]*\}", proc.stdout or "", re.S)
    if m:
        d = json.loads(m.group(0))
        d["score"] = max(0.0, min(10.0, float(d.get("score", 0))))
        return d
    (RESULTS / f"judge-{tag}.txt").write_text(
        (proc.stdout or "")[:2000] + (proc.stderr or "")[:500], encoding="utf-8")
    return {"score": None, "grounded": None, "issues": "judge failed"}


def cohens_kappa(pairs) -> float:
    """κ over binary 'usable' = score >= 5."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    a_yes = sum(1 for a, b in pairs if a >= 5)
    b_yes = sum(1 for a, b in pairs if b >= 5)
    both = sum(1 for a, b in pairs if a >= 5 and b >= 5)
    po = sum(1 for a, b in pairs if (a >= 5) == (b >= 5)) / n
    pe = (a_yes / n) * (b_yes / n) + ((n - a_yes) / n) * ((n - b_yes) / n)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def main() -> int:
    outdir = set_run()
    mc = McpClient()
    try:
        cat = http_get(f"{WEB}/api/kb/catalog", timeout=120)
        kbs = {k.get("name"): (k.get("kbId") or k.get("id"))
               for k in cat.get("knowledgeBases") or []}
        en_id = kbs["KB-Demo-EN"]
        ops_id = kbs[OPS_KB]

        # 冻结的 llm-summary 材料(与 42_e4_fix 一致, 保证可比)
        prev = sorted(RESULTS.glob("run-*/e4_baselines_fixed.json"))
        lessons = json.loads(prev[-1].read_text(encoding="utf-8"))["llm_summary_material"] \
            if prev else []
        sum_mat = "\n".join("- " + l for l in lessons) or "(summary unavailable)"
        ops_exps = mc.call("experience_list", {"kb_id": ops_id},
                           timeout=120).get("experiences") or []

        records = []
        for q in QUERIES:
            # 材料 1: no-synthesis (确定性检索+读取)
            res = mc.call("kb_search_two_stage",
                          {"query": q["question"], "kb_id": en_id, "stage1_top_k": 40,
                           "stage2_top_k": 5, "balance_kbs": False}, timeout=300)
            mats = []
            for r in ((res.get("stage2") or {}).get("results") or [])[:3]:
                dp = str(r.get("doc_path", ""))
                try:
                    d = mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 1500},
                                timeout=120)
                    mats.append(str(d.get("content") or "")[:1500])
                except Exception:  # noqa: BLE001
                    pass
            nosyn_mat = "\n---\n".join(mats) or "(no docs)"
            # 材料 2: ours (经验库检索)
            try:
                er = mc.call("experience_search_smart",
                             {"query": q["question"], "top_k": 3, "kb_id": ops_id},
                             timeout=180)
                hit = er.get("experiences") or []
            except Exception:  # noqa: BLE001
                hit = []
            ours_mat = "\n".join(
                json.dumps({k: e.get(k) for k in ("title", "scenario", "problem",
                                                  "solution", "key_lessons")},
                           ensure_ascii=False)
                for e in (hit or ops_exps[:3])) or "(none)"

            for mat_name, material in (("no_synthesis", nosyn_mat),
                                       ("ours_experience", ours_mat),
                                       ("llm_summary", sum_mat)):
                a = run_judge(JUDGE_A, material,
                              f"e15-A-{ROUND}-{q['qid']}-{mat_name}")
                b = run_judge(JUDGE_B, material,
                              f"e15-B-{ROUND}-{q['qid']}-{mat_name}")
                records.append({"qid": q["qid"], "material": mat_name,
                                "score_a": a.get("score"), "score_b": b.get("score"),
                                "grounded_a": a.get("grounded"),
                                "grounded_b": b.get("grounded")})
            print(f"  [{q['qid']}] 3 materials x 2 judges done", flush=True)

        pairs = [(r["score_a"], r["score_b"]) for r in records
                 if r["score_a"] is not None and r["score_b"] is not None]
        import statistics
        agreement = {
            "n_materials": len(records), "n_scored_pairs": len(pairs),
            "exact_agreement": round(sum(1 for a, b in pairs if abs(a - b) < 0.5)
                                     / len(pairs), 4) if pairs else None,
            "within_1": round(sum(1 for a, b in pairs if abs(a - b) <= 1.0)
                              / len(pairs), 4) if pairs else None,
            "mean_abs_delta": round(mean([abs(a - b) for a, b in pairs]), 3)
                              if pairs else None,
            "pearson_r": round(statistics.correlation([a for a, _ in pairs],
                                                      [b for _, b in pairs]), 3)
                         if len(pairs) > 2 else None,
            "cohens_kappa_usable_ge5": cohens_kappa(pairs),
            "honest_label": "LLM-LLM agreement (two independent judge prompts over "
                            "identical materials), NOT human inter-annotator kappa; "
                            "a 3-annotator human study remains future work"}
        by_material = {}
        for m in ("no_synthesis", "ours_experience", "llm_summary"):
            sub = [r for r in records if r["material"] == m]
            by_material[m] = {
                "scores_a": [r["score_a"] for r in sub],
                "scores_b": [r["score_b"] for r in sub],
                "mean_a": round(mean([r["score_a"] for r in sub]), 2),
                "mean_b": round(mean([r["score_b"] for r in sub]), 2)}
        result = {"experiment": "E15 dual-judge agreement + E4 extension to 8 queries",
                  "round": ROUND, "agreement": agreement,
                  "by_material": by_material, "records": records,
                  "meta": {"generated": now_iso(), "env": env_fingerprint()}}
        out = outdir / f"judge_agreement_{ROUND}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {out}")
        print(json.dumps({"agreement": agreement, "by_material": by_material},
                         ensure_ascii=False, indent=1))
        return 0
    finally:
        mc.close()


if __name__ == "__main__":
    sys.exit(main())
