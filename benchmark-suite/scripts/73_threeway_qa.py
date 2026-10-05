#!/usr/bin/env python3
# DEPRECATED 2026-09-20 — superseded by the experiments/ platform
# (python -m experiments.runner, chat API + harness=claude). Kept only to
# reproduce historical reports. Do not use for new retrieval testing.
"""三轨对照 QA — 10 道内容强相关题目 × 3 种检索方式 × 同一 Harness(omp) 作答.

Track A  kb_system   — 平台知识库检索: MCP two_stage 全库 → 文档级去重 → top-3
                       chunk 证据(4000 字符预算) → 统一作答 prompt
Track B  bare_agent  — 裸 Agent: omp RPC 保留文件工具, cwd=data/corpus_md/,
                       自行 grep/read 定位并作答
Track C  dense_rag   — RAG 复刻算法: methods.dense(Corpus-Chunks800) → 同一
                       4000 字符预算 → 同一统一作答 prompt
A/C 证据与作答 prompt 完全一致, 差异只在检索来源; B 无预算限制(自己读文件)。
输出: results/threeway_qa.json + results/threeway_qa.md(分轨汇整)。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "algorithms"))

from lib import McpClient  # noqa: E402
from methods import Ctx, dense, pack  # noqa: E402
from omp_client import OmpRpc, OmpOneshot, extract_json  # noqa: E402
from user_scenario import SCEN_ANSWER_PROMPT, activate_profile, \
    load_user_docs  # noqa: E402

CORPUS_DIR = SUITE / "data" / "corpus_md"
BARE_TIMEOUT = 360.0
BARE_PROMPT = """You are a research assistant sitting INSIDE a directory of
research-paper files (plain markdown). Nobody built any index for you.

Answer the QUESTION using ONLY the files in your current working directory.
Workflow: list the files, grep/read the relevant passages, read enough context,
then answer. Reply with ONLY a JSON object (no other text):
{{"answer": "<2-5 sentence factual answer; say the files do not contain the
answer if they do not>", "files_used": ["<filename>", ...]}}

QUESTION: {q}"""


class BareAgentRpc(OmpRpc):
    """裸 Agent: omp RPC 保留文件工具, cwd=纯文献目录(继承 OmpRpc 排水/关闭)."""

    def __init__(self, cwd: Path, timeout: float = BARE_TIMEOUT):
        OmpBase = super(OmpRpc, self)  # noqa: N806 (MRO 跳过 OmpRpc 孵化)
        OmpBase.__init__("bare", timeout)
        self.proc = subprocess.Popen(
            ["omp", "--mode=rpc", "--no-session", "--no-lsp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
            cwd=str(cwd))
        self._wait_ready()


def two_stage_chunks(mc, question: str) -> list[dict]:
    r = mc.call("kb_search_two_stage",
                {"query": question, "kb_id": "", "stage1_top_k": 20,
                 "stage2_top_k": 5, "score_threshold": 0.30,
                 "balance_kbs": True}, timeout=300)
    results = (r or {}).get("stage2", {}).get("results") or []
    best: dict[str, dict] = {}
    for it in results:
        dp = str(it.get("doc_path", "")).replace("\\", "/")
        if dp and (dp not in best or it.get("score", 0) > best[dp]["score"]):
            best[dp] = it
    top = sorted(best.values(), key=lambda x: -x.get("score", 0))[:3]
    return [{"src": d["doc_path"].split("/")[-1][:60], "text": d.get("content", ""),
             "score": d.get("score", 0), "doc_path": d["doc_path"]}
            for d in top]


def run_track_a(mc, oneshot_factory, q: str) -> dict:
    t0 = time.perf_counter()
    chunks = two_stage_chunks(mc, q)
    ans = _answer_evidence(oneshot_factory, q, chunks)
    ans["latency"] = round(time.perf_counter() - t0, 1)
    ans["evidence_docs"] = sorted({c["doc_path"].split("/")[-1][:50]
                                   for c in chunks})
    return ans


def run_track_c(mc, ctx, oneshot_factory, q: str) -> dict:
    t0 = time.perf_counter()
    ev = dense(ctx, q)
    chunks = ev.get("chunks") or []
    ans = _answer_evidence(oneshot_factory, q, chunks)
    ans["latency"] = round(time.perf_counter() - t0, 1)
    ans["evidence_docs"] = sorted({c.get("doc_path", "")[:50]
                                   for c in chunks if c.get("doc_path")})
    return ans


def _answer_evidence(oneshot_factory, q: str, chunks: list[dict]) -> dict:
    evidence, used = pack(chunks)
    oneshot = oneshot_factory("answer")
    raw = oneshot(SCEN_ANSWER_PROMPT.format(
        claim=q, evidence=evidence or "(no evidence retrieved)"))
    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        parsed = {"answer": raw.strip()[:1500]}
    return {"parsed": parsed, "raw": raw[:1800],
            "evidence_chars": len(evidence), "evidence_chunks": len(used)}


def run_track_b(cwd: Path, q: str) -> dict:
    t0 = time.perf_counter()
    agent = BareAgentRpc(cwd)
    try:
        raw = agent.prompt(BARE_PROMPT.format(q=q))
    finally:
        agent.close()
    parsed = extract_json(raw)
    if not isinstance(parsed, dict) or not parsed.get("answer"):
        m = re.search(r'"answer"\s*:\s*"(.*?)"', raw, re.S)
        parsed = {"answer": (m.group(1).strip() if m else raw.strip()[:1500]),
                  "files_used": []}
    return {"parsed": parsed, "raw": raw[:1800],
            "latency": round(time.perf_counter() - t0, 1)}


def gold_check(ans_text: str, keywords: list[str]) -> list[str]:
    low = ans_text.lower()
    return [k for k in keywords if k.lower() in low]


def main() -> int:
    qs = json.loads((SUITE / "data" / "papers" / "qa_questions.json")
                    .read_text(encoding="utf-8"))["questions"]
    docs = load_user_docs(sorted(CORPUS_DIR.glob("*.md")))
    activate_profile("Corpus", "Corpus-Chunks800")

    def oneshot_factory(stage: str):
        return OmpOneshot(stage=f"tw-{stage}", timeout=420)

    mc = McpClient()
    ctx = Ctx(mc, None, None,
              kb_names=("Corpus-Chunks800", "Corpus-Struct", "Corpus-Paras", ""),
              corpus_docs=docs)
    out = []
    for q in qs:
        print(f"[{q['qid']}] {q['question'][:60]}", flush=True)
        a = run_track_a(mc, oneshot_factory, q["question"])
        c = run_track_c(mc, ctx, oneshot_factory, q["question"])
        b = run_track_b(CORPUS_DIR, q["question"])
        row = {"qid": q["qid"], "field": q["field"], "paper": q["paper"],
               "question": q["question"],
               "gold_keywords": q["gold_keywords"],
               "track_a_kb_system": {**a, "gold_kw_hit": gold_check(
                   str(a["parsed"].get("answer", "")), q["gold_keywords"])},
               "track_b_bare_agent": {**b, "gold_kw_hit": gold_check(
                   str(b["parsed"].get("answer", "")), q["gold_keywords"])},
               "track_c_dense_rag": {**c, "gold_kw_hit": gold_check(
                   str(c["parsed"].get("answer", "")), q["gold_keywords"])}}
        out.append(row)
        print(f"    A:{row['track_a_kb_system']['latency']}s "
              f"B:{row['track_b_bare_agent']['latency']}s "
              f"C:{row['track_c_dense_rag']['latency']}s", flush=True)
    mc.close()
    (SUITE / "results" / "threeway_qa.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[done] results/threeway_qa.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
