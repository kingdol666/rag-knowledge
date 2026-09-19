#!/usr/bin/env python3
"""Track B (裸 Agent 直搜) + Track C (RAG 复刻 dense) 重跑 — 全程计时+原始回答.

B: omp RPC 保留文件工具, cwd=data/corpus_md/, 每题独立会话, 原始 JSON 回答原样记录。
C: activate_profile → methods.dense(Corpus-Chunks800) → pack(4000) →
   SCEN_ANSWER_PROMPT(omp oneshot), 与 Track A 完全不同的检索来源。
输出 results/track_bc.json。
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
    def __init__(self, cwd: Path, timeout: float = BARE_TIMEOUT):
        super(OmpRpc, self).__init__("bare2", timeout)
        self.proc = subprocess.Popen(
            ["omp", "--mode=rpc", "--no-session", "--no-lsp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
            cwd=str(cwd))
        self._wait_ready()


def run_bare(cwd: Path, q: str) -> dict:
    t0 = time.perf_counter()
    agent = BareAgentRpc(cwd)
    try:
        raw = agent.prompt(BARE_PROMPT.format(q=q))
        steps = agent.calls
    finally:
        agent.close()
    t_answer = time.perf_counter() - t0
    parsed = extract_json(raw)
    if not isinstance(parsed, dict) or not parsed.get("answer"):
        m = re.search(r'"answer"\s*:\s*"(.*?)"', raw, re.S)
        parsed = {"answer": (m.group(1).strip() if m else raw.strip()[:1500]),
                  "files_used": []}
    return {"raw_answer": parsed.get("answer", ""), "files_used":
            parsed.get("files_used", []), "raw_model_output": raw[:2400],
            "omp_calls": steps, "latency": round(t_answer, 1)}


def run_dense(mc, ctx, oneshot, q: str) -> dict:
    t0 = time.perf_counter()
    ev = dense(ctx, q)
    t_retrieval = time.perf_counter() - t0
    chunks = ev.get("chunks") or []
    evidence, used = pack(chunks)
    t1 = time.perf_counter()
    raw = oneshot(SCEN_ANSWER_PROMPT.format(
        claim=q, evidence=evidence or "(no evidence retrieved)"))
    t_answer = time.perf_counter() - t1
    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        parsed = {"answer": raw.strip()[:1500]}
    return {"raw_answer": parsed.get("answer", ""), "evidence_docs": sorted(
        {c.get("doc_path", "")[:56] for c in chunks if c.get("doc_path")}),
        "evidence_chunks": len(used), "evidence_chars": len(evidence),
        "raw_model_output": raw[:2400], "latency_retrieval": round(t_retrieval, 2),
        "latency_answer": round(t_answer, 1),
        "latency_total": round(time.perf_counter() - t0, 1)}


def main() -> int:
    qs = json.loads((SUITE / "data" / "papers" / "qa_questions.json")
                    .read_text(encoding="utf-8"))["questions"]
    docs = load_user_docs(sorted(CORPUS_DIR.glob("*.md")))
    activate_profile("Corpus", "Corpus-Chunks800")
    out = []
    mc = McpClient()
    ctx = Ctx(mc, None, None,
              kb_names=("Corpus-Chunks800", "Corpus-Struct", "Corpus-Paras", ""),
              corpus_docs=docs)
    for q in qs:
        print(f"[{q['qid']}] running B + C ...", flush=True)
        b = run_bare(CORPUS_DIR, q["question"])
        oneshot = OmpOneshot(stage="bc-answer", timeout=420)
        c = run_dense(mc, ctx, oneshot, q["question"])
        out.append({"qid": q["qid"], "field": q["field"], "paper": q["paper"],
                    "question": q["question"], "track_b_bare_agent": b,
                    "track_c_dense_rag": c})
        print(f"    B:{b['latency']}s ({len(b['files_used'])} files) "
              f"C:{c['latency_total']}s ({c['evidence_chunks']} chunks)",
              flush=True)
    mc.close()
    (SUITE / "results" / "track_bc.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[done] results/track_bc.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
