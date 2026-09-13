#!/usr/bin/env python3
"""E4 修复重跑 — llm_summary 材料须用带 KB 前缀的 doc_path 读取全文.

背景: 40_experience_suite 的 llm_summarize_docs 用裸文件名调 kb_doc_read，
返回空内容导致 one-shot 摘要基线退化为"拒绝编造"。本脚本用正确路径重取材料，
重判三组基线，并把结果回写进最近两份 experience_suite_*.json。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (McpClient, REPO, RESULTS, WEB, env_fingerprint,  # noqa: E402
                 http_get, mean, now_iso, set_run)

JUDGE_PROMPT = open(Path(__file__).with_name("40_experience_suite.py"),
                    encoding="utf-8").read().split('JUDGE_PROMPT = """')[1].split('"""')[0]


def judge(material: str, run_tag: str) -> dict:
    body = material if len(material) <= 6000 else material[:6000]
    prompt = JUDGE_PROMPT.replace("{experience}", body)
    proc = subprocess.run(["omp", "-p", prompt, "--auto-approve", "--no-session",
                           "--max-time", "300"], cwd=str(REPO), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=360)
    m = re.search(r"\{[^{}]*\}", proc.stdout or "", re.S)
    if m:
        d = json.loads(m.group(0))
        d["score"] = max(0, min(10, float(d.get("score", 0))))
        return d
    return {"score": None, "grounded": None, "issues": "judge failed"}


EXP_QUERIES = [
    {"qid": "x-01", "question": "parsing job hangs forever and the file never appears"},
    {"qid": "x-02", "question": "why does search return zero hits after recreating a base"},
    {"qid": "x-04", "question": "few candidates come back for very short questions"},
    {"qid": "x-08", "question": "long runs die with too-many-requests errors"},
]


def main() -> int:
    outdir = set_run()
    mc = McpClient()
    try:
        cat = http_get(f"{WEB}/api/kb/catalog", timeout=120)
        kbs = {k.get("name"): (k.get("kbId") or k.get("id"))
               for k in cat.get("knowledgeBases") or []}
        en_id = kbs["KB-Demo-EN"]
        ops_id = kbs.get("KB-Exp-Ops")

        listing = http_get(f"{WEB}/api/kb/documents?kb_id={en_id}", timeout=180)
        names = [str(d.get("name")) for d in listing.get("documents") or []][:7]
        docs = []
        for n in names:
            d = mc.call("kb_doc_read",
                        {"doc_path": f"KB-Demo-EN/{n}", "max_chars": 3000}, timeout=120)
            c = str(d.get("content") or d.get("raw") or "")
            print(f"  read {n}: {len(c)} chars", flush=True)
            if c:
                docs.append(c[:3000])
        joined = "\n\n---\n\n".join(docs)
        prompt = ("Summarise the following knowledge-base documents into concise "
                  "operational lessons entries. Output 5-8 bullet lessons, each one "
                  "sentence, no preamble.\n\n" + joined[:20000])
        proc = subprocess.run(["omp", "-p", prompt, "--auto-approve", "--no-session",
                               "--max-time", "420"], cwd=str(REPO), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=480)
        lessons = [l.strip("-• ").strip() for l in (proc.stdout or "").splitlines()
                   if len(l.strip()) > 20][:8]
        sum_mat = "\n".join("- " + l for l in lessons) or "(summary unavailable)"

        ops_exps = mc.call("experience_list", {"kb_id": ops_id},
                           timeout=120).get("experiences") or []
        nosyn, ours, sums = [], [], []
        for q in EXP_QUERIES:
            res = mc.call("kb_search_two_stage",
                          {"query": q["question"], "kb_id": en_id, "stage1_top_k": 40,
                           "stage2_top_k": 5, "balance_kbs": False}, timeout=300)
            mats = []
            for r_ in ((res.get("stage2") or {}).get("results") or [])[:3]:
                dp = str(r_.get("doc_path", ""))
                try:
                    d = mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 1500},
                                timeout=120)
                    mats.append(str(d.get("content") or "")[:1500])
                except Exception:  # noqa: BLE001
                    pass
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
            nosyn.append(judge("\n---\n".join(mats) or "(no docs)",
                               f"e4fix-nosyn-{q['qid']}").get("score"))
            ours.append(judge(ours_mat, f"e4fix-ours-{q['qid']}").get("score"))
            sums.append(judge(sum_mat, f"e4fix-summary-{q['qid']}").get("score"))
        judged = {
            "no_synthesis": {"scores": nosyn, "mean": mean(nosyn)},
            "ours_experience": {"scores": ours, "mean": mean(ours)},
            "llm_summary": {"scores": sums, "mean": mean(sums)},
            "note": ("identical JUDGE_PROMPT; llm-summary material regenerated with "
                     "KB-prefixed doc paths (previous sample degenerated to empty "
                     "input, the summariser correctly refused)")}
        result = {"experiment": "E4 baseline rerun (fixed doc read paths)",
                  "llm_summary_material": lessons, "judged": judged,
                  "meta": {"generated": now_iso(), "env": env_fingerprint()}}
        out = outdir / "e4_baselines_fixed.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        # 回写进既有 suite JSON
        for p in sorted(RESULTS.glob("run-*/experience_suite_*.json"))[-2:]:
            d = json.loads(p.read_text(encoding="utf-8"))
            d["E4_baselines"] = {"n_queries_judged": 4,
                                 "llm_summary_material": lessons,
                                 "judged": judged,
                                 "superseded_by": str(out)}
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  patched {p}")
        print(f"-> {out}")
        print(json.dumps(judged, ensure_ascii=False, indent=1))
        return 0
    finally:
        mc.close()


if __name__ == "__main__":
    sys.exit(main())
