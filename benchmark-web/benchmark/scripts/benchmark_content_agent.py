#!/usr/bin/env python3
"""模块 B-Agent — Agent(harness omp)+QDCVR Skill+MCP 真链路检索评测.

链路: omp CLI(cwd=仓库根, 加载 .omp/mcp.json → kb-mcp 工具) + QDCVR 规程提示词
      → Agent 自主逐级调用 MCP 工具(kb_list/kb_search_two_stage/kb_doc_read...)
      → 最终输出 FINAL_DOCS 行(引用的文档路径).
LLM 非确定性 → 每查询 R 次运行, 报 mean±std; 全部 transcript 存档可审计.

用法:
  python benchmark_content_agent.py --lang zh --n-queries 3 --runs 2
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[1]
DATA_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks"
OUT_DIR = SCRIPTS_DIR.parent / "results" / "benchmark" / "agent-transcripts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SKILL_BRIEF = """You are a knowledge-base retrieval agent. Follow the QDCVR protocol
(knowledgebase-search skill):
 Step1 kb_list to see available KBs; Step2 kb_search_two_stage(query, balance_kbs=true);
 Step2.5 drop score<0.35 and deduplicate by document; Step3 kb_doc_read on the top
 candidates (up to 3) and verify the content actually matches the question
 (content-overrides-vector); Step4 if verification fails, refine the query and search
 again (staged search). Work step by step. The answer must cite the SPECIFIC documents
 you verified.
QUESTION: {question}
OUTPUT CONTRACT (last line, mandatory):
 FINAL_DOCS: <doc_path_1>; <doc_path_2>; ...
"""


def norm(t: str) -> str:
    return str(t).replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".md")


def run_agent(question: str, timeout_s: int, tag: str) -> dict:
    prompt = SKILL_BRIEF.format(question=question)
    cmd = ["omp", "-p", prompt, "--auto-approve", "--no-session", "--max-time",
           str(timeout_s)]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout_s + 60)
        out = proc.stdout or ""
        err = proc.stderr or ""
        ok = proc.returncode == 0
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:150], "latency_s": 0}
    latency = time.perf_counter() - t0
    m = None
    for line in reversed(out.splitlines()):
        if "FINAL_DOCS:" in line:
            m = line
            break
    docs = [d.strip() for d in m.split("FINAL_DOCS:", 1)[1].split(";")
            if d.strip()] if m else []
    tool_calls = len(re.findall(r"kb_(?:list|search|doc_read|get_documents)"
                                r"|two_stage", out))
    (OUT_DIR / f"{tag}.txt").write_text(
        f"=== stdout ===\n{out}\n=== stderr ===\n{err[:4000]}", encoding="utf-8")
    return {"ok": ok, "final_docs": docs, "n_tool_calls": tool_calls,
            "latency_s": round(latency, 1), "transcript": str(OUT_DIR / f"{tag}.txt")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["en", "zh", "ja"])
    ap.add_argument("--queries", default="")
    ap.add_argument("--n-queries", type=int, default=3)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--round", type=int, default=1)
    args = ap.parse_args()

    qpath = Path(args.queries) if args.queries else (
        DATA_DIR / {"en": "hotpotqa-en60.jsonl", "zh": "miracl-zh-dev.jsonl",
                    "ja": "miracl-ja-dev.jsonl"}[args.lang])
    items = [json.loads(l) for l in qpath.open(encoding="utf-8")][: args.n_queries]

    rows = []
    for it in items:
        golden = {norm(t) for t in it.get("golden_pages")
                  or it.get("golden_titles") or []}
        for r in range(1, args.runs + 1):
            tag = f"{args.lang}-{it['qid']}-r{r}-{datetime.now().strftime('%H%M%S')}"
            print(f"  agent run {tag}...", flush=True)
            res = run_agent(it["question"], args.timeout, tag)
            cited = [norm(d) for d in res.get("final_docs") or []]
            hit1 = int(bool(cited) and cited[0] in golden)
            hitk = int(any(c in golden for c in cited))
            rows.append({"qid": it["qid"], "run": r,
                         "hit@1": hit1, "hit_any": hitk,
                         "n_cited": len(cited),
                         "n_tool_calls": res.get("n_tool_calls", 0),
                         "latency_s": res.get("latency_s"),
                         "ok": res.get("ok", False),
                         "transcript": res.get("transcript")})

    def ms(key):
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if not vals:
            return None, None
        return round(statistics.mean(vals), 4), round(statistics.pstdev(vals), 4)

    h1m, h1s = ms("hit@1")
    ham, has = ms("hit_any")
    summary = {
        "n_runs": len(rows), "lang": args.lang, "runs_per_query": args.runs,
        "hit@1_mean": h1m, "hit@1_std": h1s,
        "hit_any_mean": ham, "hit_any_std": has,
        "note": "Agent 链路含 LLM 非确定性 — 以 mean±std 报告, transcript 可审计",
    }
    out = OUT_DIR.parent / f"benchmark_content_agent_{args.lang}_r{args.round}.json"
    out.write_text(json.dumps({"meta": {
        "generated": datetime.now(timezone.utc).isoformat(),
        "chain": "omp CLI(+.omp/mcp.json→kb-mcp) + QDCVR skill prompt",
        "model": "omp profile (见 .omp/config; 固定版本)",
    }, "summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"-> {out}")
    print("summary:", json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
