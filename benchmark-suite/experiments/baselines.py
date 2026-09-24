"""Reproducible retrieval baselines over the SAME corpus and the SAME answer API.

Every method here retrieves with its own algorithm, packs an evidence bundle to
a fixed character budget, and then answers through
`chat_tracks.answer_closed_book` — the platform's external chat API with no
tools. Because the generation step is byte-identical across methods, any
difference in the final answer is attributable to the retrieval method, not to
the answering channel.

Methods
-------
  bm25     Okapi BM25 over the 100 corpus documents (doc-level, local index)
  vector   dense top-k via the platform's POST /api/v1/search/vector on
           kb_id="Corpus-Chunks800" (the same index track C uses)
  rrf      reciprocal-rank fusion of bm25 + vector (k=60)
  rerank   vector top-30 -> listwise LLM rerank -> top-10
           (the paper's CE-reranker stand-in; see REPRODUCTION-NOTES)
  crag     vector -> LLM retrieval evaluator (Correct/Incorrect/Ambiguous) ->
           keep Correct, and if nothing is Correct, rewrite + re-retrieve
           (CRAG-style, simplified)
  selfrag  vector -> LLM sufficiency reflection -> on-demand re-retrieval with
           a rewritten query (<=2 rounds) -> answer (Self-RAG-style, simplified)

Honesty note: `crag`/`selfrag` are simplified re-implementations of the
published corrective/reflective patterns, not the authors' original code. The
report must say so.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))   # experiments/
sys.path.insert(0, str(SUITE / "scripts"))                 # lib.py

from chat_tracks import answer_closed_book, chat_stream  # noqa: E402
from lib import doc_basename, http_post                  # noqa: E402

CORPUS_DIR = SUITE / "data" / "corpus_md"
# The dense baseline searches this KB by default. Override per run with
# RAG_BENCH_VECTOR_KB or run_method(kb=...) — hardwiring it meant the baselines
# silently searched the wrong KB (and abstained) on any other corpus.
VECTOR_KB = os.environ.get("RAG_BENCH_VECTOR_KB", "Corpus-Chunks800")
BACKEND = os.environ.get("RAG_BENCH_URL", "http://localhost:8771").rstrip("/")

EVIDENCE_BUDGET = int(os.environ.get("RAG_BENCH_EVIDENCE_BUDGET", "4000"))
UNIT_CHARS = int(os.environ.get("RAG_BENCH_UNIT_CHARS", "1200"))
TOP_K = 10
CANDIDATES = 30
RRF_K = 60

METHODS = ["bm25", "vector", "rrf", "rerank", "crag", "selfrag"]


# ── corpus + source-id normalisation ────────────────────────────────────────

def src_of(path: str) -> str:
    """'Corpus-Chunks800/climate-science__2409.13934__x__k21.md' -> '2409.13934'.

    Falls back to the file stem when the corpus naming convention is absent.
    """
    base = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    if base.endswith(".md"):
        base = base[:-3]
    parts = base.split("__")
    return parts[1] if len(parts) >= 2 and parts[1] else base


def load_docs() -> list[dict]:
    out = []
    for p in sorted(CORPUS_DIR.glob("*.md")):
        out.append({"src": src_of(p.name), "name": p.name,
                    "text": p.read_text(encoding="utf-8", errors="replace")})
    return out


# ── BM25 (doc-level, pure python — no external index needed) ────────────────

_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25:
    def __init__(self, docs: list[dict], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = docs
        self.tfs: list[dict] = []
        self.dl: list[int] = []
        df: dict[str, int] = {}
        for d in docs:
            toks = _tok(d["text"])
            tf: dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            self.tfs.append(tf)
            self.dl.append(len(toks))
            for t in tf:
                df[t] = df.get(t, 0) + 1
        n = len(docs)
        self.avgdl = (sum(self.dl) / n) if n else 0.0
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5))
                    for t, c in df.items()}

    def rank(self, query: str, top_k: int = TOP_K) -> list[dict]:
        q = _tok(query)
        scores = []
        for i, tf in enumerate(self.tfs):
            s = 0.0
            dl = self.dl[i] or 1
            for t in q:
                f = tf.get(t)
                if not f:
                    continue
                idf = self.idf.get(t, 0.0)
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
            if s > 0:
                scores.append((s, i))
        scores.sort(key=lambda x: -x[0])
        return [{"src": self.docs[i]["src"], "name": self.docs[i]["name"],
                 "score": round(s, 4), "text": self.docs[i]["text"]}
                for s, i in scores[:top_k]]


# ── dense retrieval via the platform API (same index as track C) ────────────

def vector_rank(query: str, top_k: int = TOP_K,
                candidates: int = CANDIDATES, kb: str | None = None) -> list[dict]:
    r = http_post(f"{BACKEND}/api/v1/search/vector",
                  {"query": query, "kb_id": kb or VECTOR_KB,
                   "top_k": int(candidates), "score_threshold": 0.0})
    best: dict[str, dict] = {}
    for it in (r.get("results") or []):
        dp = str(it.get("doc_path", ""))
        src = src_of(dp)
        sc = float(it.get("score", 0) or 0)
        cur = best.get(src)
        if cur is None or sc > cur["score"]:
            best[src] = {"src": src, "name": doc_basename(dp), "score": round(sc, 4),
                         "text": str(it.get("content", "") or "")}
    ranked = sorted(best.values(), key=lambda x: -x["score"])
    return ranked[:top_k]


# ── reciprocal-rank fusion ──────────────────────────────────────────────────

def rrf_rank(a: list[dict], b: list[dict], top_k: int = TOP_K) -> list[dict]:
    acc: dict[str, float] = {}
    store: dict[str, dict] = {}
    for lst in (a, b):
        for rank, item in enumerate(lst, 1):
            src = item["src"]
            acc[src] = acc.get(src, 0.0) + 1.0 / (RRF_K + rank)
            store.setdefault(src, item)
    out = []
    for src, s in sorted(acc.items(), key=lambda x: -x[1]):
        it = dict(store[src])
        it["score"] = round(s, 5)
        out.append(it)
    return out[:top_k]


# ── shared LLM helper (no tools; JSON out) ──────────────────────────────────

def _json_from(text: str):
    m = re.search(r"\[.*\]", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


def _llm_json(prompt: str, timeout_s: int = 240):
    r = chat_stream(prompt, str(CORPUS_DIR), allowed_tools=[], max_turns=1,
                    timeout_s=timeout_s)
    return _json_from(str(r.get("answer") or "")), r


def _excerpt(text: str, query: str, size: int = UNIT_CHARS) -> str:
    """Query-relevant window instead of a head slice.

    A doc-level baseline that packs only the head gets the title+abstract, which
    makes it abstain on questions whose answer lives in the body (observed
    2026-09-24: bm25/vector/rerank abstained 7-8/10 on qa_quick10). Slide a
    window and keep the densest one in query terms.
    """
    text = str(text or "")
    if len(text) <= size or not query:
        return text[:size]
    terms = set(_tok(query))
    if not terms:
        return text[:size]
    step = max(1, size // 2)
    best_i, best = 0, -1
    for i in range(0, len(text) - size + 1, step):
        w = text[i:i + size]
        s = sum(1 for t in _tok(w) if t in terms)
        if s > best:
            best, best_i = s, i
    return text[best_i:best_i + size]


def _pack(units: list[dict], budget: int = EVIDENCE_BUDGET,
          query: str = "") -> tuple[str, list[str]]:
    used, total, lines = [], 0, []
    for u in units:
        text = _excerpt(u.get("text"), query)
        line = f"[{u.get('src')}] {text}"
        if lines and total + len(line) > budget:
            break
        lines.append(line)
        used.append(str(u.get("src")))
        total += len(line) + 2
    return "\n\n".join(lines), used


# ── rerank / evaluator / reflection prompts ─────────────────────────────────

RERANK_PROMPT = """Rank the CANDIDATES below by how well they answer the QUESTION.
Reply ONLY a JSON array of candidate indices, best first, at most 10:
[<index>, <index>, ...]

QUESTION: {q}

CANDIDATES:
{cands}"""

EVAL_PROMPT = """You are a retrieval evaluator. For each CANDIDATE, decide whether
it is CORRECT (contains information that answers the QUESTION), INCORRECT, or
AMBIGUOUS. Reply ONLY a JSON array:
[{{"i": <index>, "label": "CORRECT|INCORRECT|AMBIGUOUS"}}, ...]

QUESTION: {q}

CANDIDATES:
{cands}"""

REFLECT_PROMPT = """Decide whether the EVIDENCE below is sufficient to answer the
QUESTION. Reply ONLY a JSON object:
{{"sufficient": true|false, "rewritten_query": "<a better search query if not sufficient, else empty>"}}

QUESTION: {q}

EVIDENCE:
{ev}"""

REWRITE_PROMPT = """Rewrite the QUESTION into a short keyword search query that
would retrieve the passage answering it. Reply ONLY the query text.

QUESTION: {q}"""


def _cand_block(units: list[dict], limit: int = 12, chars: int = 400) -> str:
    return "\n\n".join(f"[{i}] ({u['src']}) {str(u.get('text') or '')[:chars]}"
                       for i, u in enumerate(units[:limit]))


def _rerank(units: list[dict], question: str) -> tuple[list[dict], dict]:
    parsed, _ = _llm_json(RERANK_PROMPT.format(q=question,
                                                cands=_cand_block(units, 20, 320)))
    if not isinstance(parsed, list):
        return units[:TOP_K], {"rerank_fallback": True}
    order, seen = [], set()
    for x in parsed:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(units) and i not in seen:
            order.append(i)
            seen.add(i)
    order += [i for i in range(len(units)) if i not in seen]
    return [units[i] for i in order[:TOP_K]], {"rerank_fallback": False}


def _crag(units: list[dict], question: str, top_k: int,
          kb: str | None = None) -> tuple[list[dict], dict]:
    parsed, _ = _llm_json(EVAL_PROMPT.format(q=question,
                                             cands=_cand_block(units, 10, 400)))
    labels, actions = {}, []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                try:
                    labels[int(item.get("i"))] = str(item.get("label", "")).upper()
                except (TypeError, ValueError):
                    pass
    keep = [u for i, u in enumerate(units[:10]) if labels.get(i) == "CORRECT"]
    actions.append(f"evaluator_keep={len(keep)}")
    if not keep:
        # corrective action: rewrite the query and re-retrieve once
        rw, _ = _llm_json(REWRITE_PROMPT.format(q=question))
        newq = rw.strip() if isinstance(rw, str) and rw.strip() else question
        keep = vector_rank(newq, top_k=top_k, candidates=CANDIDATES, kb=kb)
        actions.append("rewrite_retrieve")
    return keep[:top_k], {"crag_actions": actions, "labels": labels}


def _selfrag(units: list[dict], question: str, top_k: int,
             rounds: int = 2, kb: str | None = None) -> tuple[list[dict], dict]:
    seen = {u["src"]: u for u in units}
    trace = []
    cur = units
    for r in range(rounds):
        ev, _ = _pack(cur, budget=2500)
        parsed, _ = _llm_json(REFLECT_PROMPT.format(q=question, ev=ev))
        suff = bool(parsed.get("sufficient")) if isinstance(parsed, dict) else False
        trace.append({"round": r + 1, "sufficient": suff})
        if suff:
            break
        nq = ""
        if isinstance(parsed, dict):
            nq = str(parsed.get("rewritten_query") or "").strip()
        if not nq:
            rw, _ = _llm_json(REWRITE_PROMPT.format(q=question))
            nq = rw.strip() if isinstance(rw, str) else question
        for u in vector_rank(nq, top_k=top_k, candidates=CANDIDATES, kb=kb):
            seen.setdefault(u["src"], u)
        cur = list(seen.values())
    return cur[:top_k], {"selfrag_trace": trace}


# ── one method, one question ────────────────────────────────────────────────

def run_method(method: str, question: str, qid: str,
               bm25: BM25 | None = None, kb: str | None = None) -> dict:
    t0 = time.perf_counter()
    extra: dict = {}
    if method == "bm25":
        units = bm25.rank(question, top_k=TOP_K)
    elif method == "vector":
        units = vector_rank(question, top_k=TOP_K, kb=kb)
    elif method == "rrf":
        units = rrf_rank(bm25.rank(question, top_k=CANDIDATES),
                         vector_rank(question, top_k=CANDIDATES, kb=kb),
                         top_k=TOP_K)
    elif method == "rerank":
        units, extra = _rerank(vector_rank(question, top_k=CANDIDATES, kb=kb),
                               question)
    elif method == "crag":
        units, extra = _crag(vector_rank(question, top_k=TOP_K, kb=kb),
                             question, TOP_K, kb=kb)
    elif method == "selfrag":
        units, extra = _selfrag(vector_rank(question, top_k=TOP_K, kb=kb),
                                question, TOP_K, kb=kb)
    else:
        raise ValueError(f"unknown method {method!r} (expected one of {METHODS})")
    retrieval_s = round(time.perf_counter() - t0, 1)

    evidence, used = _pack(units, query=question)
    ans = answer_closed_book(question, evidence)
    tok = ans.get("tokens") or {}
    return {
        "qid": qid, "method": method, "question": question,
        "ranked": [u["src"] for u in units],
        "ranked_paths": [u.get("name", "") for u in units],
        "evidence_sources": used,
        "evidence_chars": len(evidence),
        "retrieval_s": retrieval_s,
        "latency_s": round(time.perf_counter() - t0, 1),
        "answer": ans.get("answer"),
        "is_error": ans.get("is_error"),
        "tool_call_count": 0,
        "tokens": tok,
        "total_cost_usd": ans.get("total_cost_usd"),
        "extra": extra,
    }


def run_all(questions: list[dict], methods: list[str],
            progress=None, kb: str | None = None) -> list[dict]:
    docs = load_docs()
    bm25 = BM25(docs)
    rows = []
    for q in questions:
        for m in methods:
            if progress:
                progress(f"[{q['qid']}/{m}] running ...")
            try:
                rows.append(run_method(m, q["question"], q["qid"], bm25, kb=kb))
            except Exception as e:  # noqa: BLE001 — record and continue
                rows.append({"qid": q["qid"], "method": m,
                             "question": q["question"],
                             "answer": f"(method failed: {type(e).__name__}: {str(e)[:180]})",
                             "error": True, "ranked": [], "latency_s": 0,
                             "tool_call_count": 0})
            if progress:
                r = rows[-1]
                progress(f"[{q['qid']}/{m}] {r.get('latency_s')}s "
                         f"ranked={len(r.get('ranked') or [])}")
    return rows
