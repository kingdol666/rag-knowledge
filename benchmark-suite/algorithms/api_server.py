#!/usr/bin/env python3
"""E16 实验 API — 通过 HTTP 选择检索算法, 对同一语料(KB-SciFact 148 篇)问答.

仅绑定 127.0.0.1(基准内部使用)。路由:
  GET  /health    → 存活 + 方法清单 + 语料/查询规模
  GET  /methods   → 8 个检索算法注册表(名称/论文对应/实现要点)
  GET  /questions → 30 条冻结查询(qid/claim/金标)
  POST /ask       → {"method","qid"|"question","judge":true}
                    = 检索(选算法) + omp Agent 统一作答 + 第三方 omp Agent 判分;
                      与 run_matrix 同一 prompt/缓存 → 结果逐字可复现
  POST /compare   → {"qid","methods":[缺省全 8],"rank":true}
                    = 同一问题多算法并答 + 中间 Agent(独立进程)对匿名答案
                      排名打分
缓存与 run_matrix 共享(algorithms/cache/), 证据/作答/判分逐(方法,查询)幂等。
"""
from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

from corpus import load_queries  # noqa: E402
from lib import McpClient  # noqa: E402
from methods import METHODS, pack  # noqa: E402
from omp_client import OmpOneshot, OmpRpc, extract_json  # noqa: E402
from run_matrix import (ANSWER_PROMPT, JUDGE_PROMPT, METHOD_ORDER,  # noqa: E402
                        _load, _save, content_words, eval_vs_qrels)

PORT = 8790
QUERIES = load_queries()
QUERY_BY_ID = {q["qid"]: q for q in QUERIES}
MAX_CONCURRENT = 3
_SEM = threading.Semaphore(MAX_CONCURRENT)
_MCP_LOCK = threading.Lock()  # 每线程独立 Ctx(独立 MCP 子进程), 锁保护首次构建


class _CtxFactory:
    def __init__(self, tree):
        self.tree = tree
        self._local = threading.local()

    def get(self):
        ctx = getattr(self._local, "ctx", None)
        if ctx is None:
            import methods
            mc = McpClient()
            ctx = methods.Ctx(mc, lambda stage: OmpRpc(stage=stage, timeout=420),
                              OmpOneshot(stage="aux", timeout=300))
            ctx.tree = self.tree
            self._local.ctx = ctx
        return ctx


FACTORY: _CtxFactory | None = None


def retrieve(method: str, question: str, qid: str | None) -> dict:
    import methods as m
    cache_key = f"{method}_{qid}" if qid else None
    if cache_key:
        cached = _load("ev", cache_key)
        if cached:
            return cached
    ctx = FACTORY.get()
    if method == "qdcvr":
        ev = m.qdcvr(ctx, question)
    else:
        ev = METHODS[method]["fn"](ctx, question)
    if cache_key:
        ev["qid"] = qid
        ev["method"] = method
        _save("ev", cache_key, ev)
    return ev


def answer(method: str, qid: str | None, question: str, ev: dict) -> dict:
    cache_key = f"{method}_{qid}" if qid else None
    if cache_key:
        cached = _load("ans", cache_key)
        if cached:
            return cached
    evidence, used = pack(ev.get("chunks") or [])
    oneshot = OmpOneshot(stage="answer", timeout=420)
    raw = oneshot(ANSWER_PROMPT.format(claim=question, evidence=evidence
                                       or "(no evidence retrieved)"))
    parsed = extract_json(raw)
    ans = {"raw": raw[:2000], "parsed": parsed if isinstance(parsed, dict) else {},
           "evidence_chars": len(evidence), "evidence_chunks": len(used),
           "sources": sorted({c.get("src", "") for c in used})}
    if cache_key:
        _save("ans", cache_key, ans)
    return ans


def judge(method: str, qid: str | None, question: str, ans: dict,
          gold_text: str) -> dict:
    cache_key = f"{method}_{qid}" if qid else None
    if cache_key:
        cached = _load("judge", cache_key)
        if cached:
            return cached
    answer_text = json.dumps(ans.get("parsed") or {"raw": ans.get("raw", "")},
                             ensure_ascii=False)
    oneshot = OmpOneshot(stage="judge", timeout=420)
    prompt = JUDGE_PROMPT.format(claim=question, gold=gold_text[:3500],
                                 answer=answer_text[:2200])
    raw = oneshot(prompt)
    parsed = extract_json(raw)
    if not isinstance(parsed, dict) or "score" not in parsed:
        raw = oneshot(prompt + "\n\nIMPORTANT: reply with ONLY the JSON object "
                      '{"score": <0-10>, "verdict_ok": true|false, '
                      '"issues": "..."} — no other text.')
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            parsed = {}
    out = {"raw": raw[:1200], "parsed": parsed}
    if cache_key:
        _save("judge", cache_key, out)
    return out


RANK_PROMPT = """You are a neutral middle agent grading answers from N different
retrieval systems to the SAME question, using the ground-truth evidence.

Question/Claim: {claim}

GOLD EVIDENCE (ground-truth document):
{gold}

CANDIDATE ANSWERS (anonymized):
{answers}

Grade each candidate 0-10 (verdict correctness vs gold evidence 0-4; factual
grounding, no fabrication 0-4; clarity/completeness 0-2). Reply ONLY a JSON
array, best first: [{{"alias": "A", "score": <0-10>}}, ...] covering ALL aliases."""


def middle_agent_rank(question: str, gold_text: str,
                      answers: dict) -> list[dict]:
    aliases = {}
    lines = []
    for i, (method, ans) in enumerate(sorted(answers.items())):
        alias = chr(ord("A") + i)
        aliases[alias] = method
        text = json.dumps(ans.get("parsed") or {"raw": ans.get("raw", "")},
                          ensure_ascii=False)
        lines.append(f"[{alias}] ({method}) {text[:500]}")
    oneshot = OmpOneshot(stage="rank", timeout=420)
    raw = oneshot(RANK_PROMPT.format(claim=question, gold=gold_text[:3000],
                                     answers="\n\n".join(lines)))
    parsed = extract_json(raw)
    out = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict) and item.get("alias") in aliases:
                try:
                    score = float(item.get("score"))
                except (TypeError, ValueError):
                    score = None
                out.append({"alias": item.get("alias"),
                            "method": aliases[item.get("alias")],
                            "score": score})
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: A002
        sys.stderr.write("[api] " + fmt % args + "\n")

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/health":
            self._send({"status": "ok", "port": PORT,
                        "methods": METHOD_ORDER,
                        "queries": len(QUERIES),
                        "corpus": "KB-SciFact (148 docs, frozen)"})
        elif path == "/methods":
            self._send({"methods": METHOD_ORDER,
                        "paper_mapping": {m: METHODS[m]["paper"]
                                          for m in METHOD_ORDER}})
        elif path == "/questions":
            self._send({"queries": [{"qid": q["qid"],
                                     "question": q["question"],
                                     "golden_ids": q["golden_ids"]}
                                    for q in QUERIES]})
        else:
            self._send({"error": f"unknown path {path}"}, 404)

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send({"error": "invalid json"}, 400)
            return
        if path == "/ask":
            self._send(self._ask(body))
        elif path == "/compare":
            self._send(self._compare(body))
        else:
            self._send({"error": f"unknown path {path}"}, 404)

    def _resolve_question(self, body: dict):
        qid = str(body.get("qid") or "")
        question = str(body.get("question") or "")
        if qid:
            q = QUERY_BY_ID.get(qid)
            if not q:
                raise ValueError(f"unknown qid {qid}")
            return q["question"], qid, q["golden_ids"]
        if question:
            return question, None, []
        raise ValueError("qid 或 question 必填其一")

    def _ask(self, body: dict) -> dict:
        method = str(body.get("method") or "")
        if method not in METHOD_ORDER:
            return {"error": f"unknown method {method}",
                    "methods": METHOD_ORDER}
        want_judge = body.get("judge", True)
        try:
            question, qid, golden = self._resolve_question(body)
        except ValueError as e:
            return {"error": str(e)}
        with _SEM:
            t0 = time.perf_counter()
            ev = retrieve(method, question, qid)
            retrieval = {"doc_rank": ev.get("doc_rank") or [],
                         "n_chunks": len(ev.get("chunks") or [])}
            if qid and golden:
                relevant = {g.lower() for g in golden}
                retrieval["metrics"] = eval_vs_qrels(
                    [c.lower() for c in ev.get("doc_rank") or []], relevant)
            ans = answer(method, qid, question, ev)
            judge_out = None
            if want_judge and qid and golden:
                gold = _GOLD.get(golden[0], "")
                judge_out = judge(method, qid, question, ans, gold).get("parsed")
            return {"method": method, "qid": qid, "question": question,
                    "retrieval": retrieval,
                    "metrics": retrieval.get("metrics"),
                    "evidence_sources": ans.get("sources"),
                    "answer": ans.get("parsed"),
                    "judge": judge_out,
                    "latency_seconds": round(time.perf_counter() - t0, 2)}

    def _compare(self, body: dict) -> dict:
        try:
            question, qid, golden = self._resolve_question(body)
        except ValueError as e:
            return {"error": str(e)}
        methods_want = body.get("methods") or METHOD_ORDER
        bad = [m for m in methods_want if m not in METHOD_ORDER]
        if bad:
            return {"error": f"unknown methods {bad}", "methods": METHOD_ORDER}
        gold = ""
        if golden:
            gold = _GOLD.get(golden[0], "")
        results = {}
        for m in methods_want:
            with _SEM:
                t0 = time.perf_counter()
                ev = retrieve(m, question, qid)
                metrics = None
                if qid and golden:
                    metrics = eval_vs_qrels(
                        [c.lower() for c in ev.get("doc_rank") or []],
                        {g.lower() for g in golden})
                ans = answer(m, qid, question, ev)
                jd = None
                if qid and golden:
                    jd = judge(m, qid, question, ans, gold).get("parsed")
                results[m] = {"metrics": metrics,
                              "evidence_sources": ans.get("sources"),
                              "answer": ans.get("parsed"),
                              "judge": jd,
                              "latency_seconds": round(
                                  time.perf_counter() - t0, 2)}
        ranking = None
        if body.get("rank", False) and gold:
            answers = {m: {"parsed": r["answer"], "raw": ""}
                       for m, r in results.items()}
            ranking = middle_agent_rank(question, gold, answers)
        return {"qid": qid, "question": question, "golden_ids": golden,
                "results": results, "middle_agent_ranking": ranking}


_GOLD: dict[str, str] = {}


def load_gold() -> int:
    """KB-SciFact 金标文档全文(cid → text), 供判分/中间 Agent 注入。"""
    import re
    ctx = FACTORY.get()
    docs = ctx.mc.call("kb_get_documents", {"kb_id": "KB-SciFact"}, timeout=600)
    n = 0
    for d in docs.get("documents") or []:
        name = str(d.get("name") or d.get("path") or "")
        m = re.search(r"\[([^\[\]]+)\]\s*\.md$", name)
        if not m:
            continue
        read = ctx.mc.call("kb_doc_read",
                           {"doc_path": f"KB-SciFact/{name}", "max_chars": 4000},
                           timeout=120)
        _GOLD[m.group(1)] = str(read.get("content") or read.get("raw") or "")
        n += 1
    return n


def main() -> int:
    global FACTORY
    tree = _load("tree", "raptor") or {}
    tp = HERE / "cache" / "raptor_tree.json"
    if not tree and tp.exists():
        tree = json.loads(tp.read_text(encoding="utf-8"))
    FACTORY = _CtxFactory(tree)
    n_gold = load_gold()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"E16 API on http://127.0.0.1:{PORT} — methods={len(METHOD_ORDER)} "
          f"queries={len(QUERIES)} gold_docs={n_gold}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
