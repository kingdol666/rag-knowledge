#!/usr/bin/env python3
"""八种检索方法 — DeepRead 论文对比集(Table 1)在本语料上的复现.

  qdcvr            本系统真链路: knowledgebase-search skill Step1-3(MCP 两阶段 +
                   0.35 阈值 + kb_doc_read 内容验证重排, content-overrides-vector)
  dense_rag        论文 Dense RAG: 定窗 800/400 分块, 稠密检索 top-10
  dense_rag_rerank : 稠密 top-30 → LLM listwise 重排 → top-10
                     (论文用 Qwen3-reranker-8b 交叉编码器; 本环境无该模型,
                      以 omp Agent listwise 重排替代, 见 REPRODUCTION-NOTES)
  raptor           Collapsed Tree 全节点检索 top-10(raptor.py 建树)
  itrg_refresh     ITRG 4 轮 × top-6, 每轮证据刷新(仅保留本轮)
  itrg_refine      ITRG 4 轮 × top-6, 证据跨轮累积
  search_o1        agentic 平铺检索: structure 分块(o0), 每轮 Search 返回 top-2,
                   ≤8 轮(论文上限 50, 但其 Table 3 实测均值 5.8-11.0 → cap 8)
  deepread         结构感知 locate-then-read: TOC 注入 + Retrieve(带 ±1 扫描窗)
                   + ReadSection(连续有序段落), ≤8 轮

证据输出统一为 {doc_rank, chunks, trace}; 作答阶段对全部方法用同一
omp Agent、同一 4000 字符证据预算(隔离检索质量的差异归因)。
"""
from __future__ import annotations

import re
import time

from corpus import load_corpus, parse_structure
from index_kb import (KB_FIXED, KB_PARA, KB_RAPTOR, KB_STRUCT,  # noqa: E402
                      load_texts, src_of)
from lib import doc_basename, step25  # noqa: E402
from omp_client import extract_json

BUDGET = 4000          # 统一作答证据预算(chars), 对所有方法对称
AGENTIC_CAP = 8        # agentic 轮数上限(论文 Table 3 实测均值区间 5.8-11.0)
KB_SCIFACT = "KB-SciFact"


def doc_cid(doc_path: str) -> str:
    """KB-SciFact 文档名 'Title [cid].md' → cid。"""
    b = doc_basename(doc_path)
    m = re.search(r"\[([^\[\]]+)\]\s*$", b)
    return m.group(1) if m else b


def pack(chunks: list[dict], budget: int = BUDGET) -> tuple[str, list[dict]]:
    """chunks → 证据文本(≤budget chars, 整块保留, 至少一块)。"""
    used, total = [], 0
    for c in chunks:
        t = f"[{c.get('src', '?')}] {c.get('text', '')}"
        if used and total + len(t) > budget:
            break
        used.append(c)
        total += len(t) + 2
    text = "\n\n".join(f"[{c.get('src', '?')}] {c.get('text', '')}" for c in used)
    return text, used


class Ctx:
    """方法共享上下文: MCP 客户端 / omp 工厂 / 分块文本 / 文档结构。"""

    def __init__(self, mc, rpc_factory, oneshot):
        self.mc = mc
        self.new_rpc = rpc_factory
        self.oneshot = oneshot
        self.texts = {kb: load_texts(kb)
                      for kb in (KB_FIXED, KB_STRUCT, KB_PARA, KB_RAPTOR)}
        self.tree: dict = {}
        self.corpus = {d["cid"]: d for d in load_corpus()}
        self.structure = {cid: parse_structure(d)
                          for cid, d in self.corpus.items()}

    # ── 稠密检索(指定 chunk 级 KB) ──
    def vector(self, kb: str, query: str, top_k: int) -> list[dict]:
        r = self.mc.call("kb_search_vector",
                         {"query": query, "kb_id": kb, "top_k": top_k},
                         timeout=300)
        out = []
        for h in r.get("results") or []:
            dp = str(h.get("doc_path", ""))
            out.append({"path": dp, "score": float(h.get("score", 0)),
                        "text": self.texts.get(kb, {}).get(dp, {}).get("text", "")})
        return out


# ── 1. QDCVR(真 skill 链路) ──────────────────────────────────────────────────

def qdcvr(ctx: Ctx, claim: str) -> dict:
    t0 = time.perf_counter()
    res = ctx.mc.call("kb_search_two_stage",
                      {"query": claim, "kb_id": KB_SCIFACT,
                       "stage1_top_k": 40, "stage2_top_k": 10,
                       "balance_kbs": False}, timeout=420)
    stage1 = [str(c.get("doc_path", ""))
              for c in (res.get("stage1") or {}).get("candidates") or []]
    fallback = False
    if not stage1:  # KB 限定 BM25 索引脏化兜底(套件已知陷阱④)
        res = ctx.mc.call("kb_search_two_stage",
                          {"query": claim, "kb_id": "",
                           "stage1_top_k": 40, "stage2_top_k": 10,
                           "balance_kbs": True}, timeout=420)
        stage1 = [str(c.get("doc_path", ""))
                  for c in (res.get("stage1") or {}).get("candidates") or []]
        fallback = True
    ranked = step25((res.get("stage2") or {}).get("results") or [])
    terms = [t.lower() for t in re.findall(r"[a-z]{3,}", claim)]
    verified: dict[str, int] = {}
    chars = 0
    for dp in [str(r.get("doc_path", "")) for r in ranked[:3]]:
        try:
            d = ctx.mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 3000},
                            timeout=120)
            content = str(d.get("content") or d.get("raw") or "")
            chars += len(content)
            verified[dp] = sum(1 for t in terms if t in content.lower())
        except Exception:  # noqa: BLE001
            verified[dp] = 0
    final = sorted((str(r.get("doc_path", "")) for r in ranked),
                   key=lambda dp: (0, -verified.get(dp, 0)) if dp in verified
                   else (1, 0))
    seen: set[str] = set()
    doc_rank = []
    for dp in final:
        cid = doc_cid(dp)
        if cid not in seen:
            seen.add(cid)
            doc_rank.append(cid)
    chunks = []
    for dp in final[:2]:
        try:
            d = ctx.mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 2100},
                            timeout=120)
            content = str(d.get("content") or d.get("raw") or "")
        except Exception:  # noqa: BLE001
            content = ""
        chunks.append({"src": doc_cid(dp), "text": content[:2100],
                       "meta": dp, "score": 1.0})
    return {"doc_rank": doc_rank, "chunks": chunks,
            "trace": {"fallback_global": fallback, "chars_read": chars,
                      "verify_pass": sum(1 for v in verified.values() if v > 0)},
            "latency": time.perf_counter() - t0, "llm_calls": 0}


# ── 2/3. Dense RAG ± reranker ───────────────────────────────────────────────

RERANK_PROMPT = """Rank the numbered passages by relevance to the claim.
Return ONLY a JSON array of passage numbers, best first, e.g. [3,1,7,2].
Claim: {claim}

{passages}"""


def dense(ctx: Ctx, claim: str, rerank: bool = False) -> dict:
    t0 = time.perf_counter()
    k = 30 if rerank else 10
    hits = ctx.vector(KB_FIXED, claim, k)
    llm_calls = 0
    rerank_fallback = False
    if rerank and hits:
        ptext = "\n\n".join(
            f"[{i+1}] (src {src_of(h['path'])}) {h['text'][:400]}"
            for i, h in enumerate(hits))
        try:
            raw = ctx.oneshot(RERANK_PROMPT.format(claim=claim, passages=ptext))
            llm_calls = 1
            order = extract_json(raw)
            if isinstance(order, list) and order:
                idx = [int(x) - 1 for x in order
                       if str(x).strip().lstrip("-").isdigit()]
                idx = [i for i in idx if 0 <= i < len(hits)]
                seen: set[int] = set()
                ordered = []
                for i in idx:
                    if i not in seen:
                        seen.add(i)
                        ordered.append(hits[i])
                ordered += [h for i, h in enumerate(hits) if i not in seen]
                hits = ordered[:10]
            else:
                rerank_fallback = True
        except Exception:  # noqa: BLE001
            rerank_fallback = True
        hits = hits[:10]
    chunks = [{"src": src_of(h["path"]), "text": h["text"][:1400],
               "meta": h["path"], "score": h["score"]} for h in hits]
    seen: set[str] = set()
    doc_rank = [s for h in hits
                for s in [src_of(h["path"])]
                if not (s in seen or seen.add(s))]
    return {"doc_rank": doc_rank, "chunks": chunks,
            "trace": {"rerank_fallback": rerank_fallback},
            "latency": time.perf_counter() - t0, "llm_calls": llm_calls}


# ── 4. RAPTOR collapsed tree ────────────────────────────────────────────────

def raptor(ctx: Ctx, claim: str) -> dict:
    t0 = time.perf_counter()
    hits = ctx.vector(KB_RAPTOR, claim, 10)
    doc_rank: list[str] = []
    seen: set[str] = set()
    chunks = []
    for h in hits:
        node = ctx.tree.get("nodes", {}).get(h["path"], {})
        srcs = node.get("src_cids") or ([src_of(h["path"])] if h["path"] else [])
        for c in srcs:
            if c not in seen:
                seen.add(c)
                doc_rank.append(c)
        chunks.append({"src": ",".join(srcs[:3]),
                       "text": (h.get("text") or node.get("text", ""))[:1500],
                       "meta": f"raptor L{node.get('level', '?')} {h['path']}",
                       "score": h["score"]})
    return {"doc_rank": doc_rank, "chunks": chunks,
            "trace": {"nodes_hit": len(hits)},
            "latency": time.perf_counter() - t0, "llm_calls": 0}


# ── 5/6. ITRG refresh / refine ──────────────────────────────────────────────

ITRG_HYP = """You are iteratively refining retrieval for a claim-verification task.
Claim: {claim}

Evidence retrieved so far (may be empty or insufficient):
{evidence}

Write ONE sentence that is your current best-guess answer to the claim.
Output ONLY that sentence (no preamble)."""


def itrg(ctx: Ctx, claim: str, variant: str) -> dict:
    t0 = time.perf_counter()
    llm_calls = 0
    hyps: list[str] = []
    queries: list[str] = []
    acc: dict[str, dict] = {}
    refreshed: list[dict] = []
    for rnd in range(1, 5):
        q = claim
        if rnd > 1:
            ev_text, _ = pack(list(acc.values())[:6], 2400)
            hyp = ctx.oneshot(ITRG_HYP.format(claim=claim, evidence=ev_text))
            hyp = " ".join(hyp.split())[:300]
            llm_calls += 1
            hyps.append(hyp)
            q = f"{claim} {hyp}"
        queries.append(q[:300])
        hits = ctx.vector(KB_FIXED, q, 6)
        refreshed = [{"src": src_of(h["path"]), "text": h["text"][:1400],
                      "meta": h["path"], "score": h["score"]} for h in hits]
        for c in refreshed:  # refine: 跨轮累积
            acc.setdefault(c["meta"], c)
    chunks = refreshed if variant == "refresh" else list(acc.values())[:24]
    seen: set[str] = set()
    doc_rank = [c["src"] for c in chunks
                if not (c["src"] in seen or seen.add(c["src"]))]
    return {"doc_rank": doc_rank, "chunks": chunks,
            "trace": {"variant": variant, "hypotheses": hyps, "queries": queries},
            "latency": time.perf_counter() - t0, "llm_calls": llm_calls}


# ── 7. Search-o1(agentic 平铺检索) ──────────────────────────────────────────

SEARCH_O1_BOOT = """You are verifying a scientific claim against a corpus of {n} research papers.
The corpus is a FLAT collection of text chunks (no structure exposed).
Each turn you must output EXACTLY ONE line, either:
Search: <a free-text search query>
Final Answer: <your verdict and justification>
After each Search you receive the top-2 chunks (source id in brackets). Use at most {cap} turns.

Claim: {claim}"""


def search_o1(ctx: Ctx, claim: str) -> dict:
    t0 = time.perf_counter()
    rpc = ctx.new_rpc("search_o1")
    gathered: dict[str, dict] = {}
    commands: list[str] = []
    final_answer = ""
    try:
        msg = SEARCH_O1_BOOT.format(n=len(ctx.corpus), cap=AGENTIC_CAP, claim=claim)
        for turn in range(AGENTIC_CAP):
            out = rpc.prompt(msg)
            line = next((l.strip() for l in out.splitlines()
                         if l.strip()), "")
            m_search = re.match(r"(?i)^search\s*[:：]\s*(.+)$", line)
            m_final = re.match(r"(?i)^final\s*answer\s*[:：]\s*(.+)$", line)
            if m_final:
                final_answer = m_final.group(1).strip()
                commands.append("final")
                break
            if not m_search:
                msg = ("Invalid command. Output exactly one line: "
                       "'Search: <query>' or 'Final Answer: <answer>'.")
                commands.append("invalid")
                continue
            q = m_search.group(1).strip()[:400]
            commands.append(f"search:{q[:80]}")
            hits = ctx.vector(KB_STRUCT, q, 2)
            parts = [f"[{src_of(h['path'])}] {h['text'][:1200]}" for h in hits]
            for h in hits:
                gathered.setdefault(h["path"],
                                    {"src": src_of(h["path"]),
                                     "text": h["text"][:1400],
                                     "meta": h["path"], "score": h["score"]})
            msg = ("Search results:\n" + "\n---\n".join(parts)
                   + "\n\nContinue. Output exactly one line: "
                     "'Search: <query>' or 'Final Answer: <answer>'.")
        else:
            commands.append("cap_reached")
    finally:
        rpc.close()
    chunks = list(gathered.values())
    seen: set[str] = set()
    doc_rank = [c["src"] for c in chunks
                if not (c["src"] in seen or seen.add(c["src"]))]
    return {"doc_rank": doc_rank, "chunks": chunks,
            "trace": {"turns": len(commands), "commands": commands,
                      "own_final_answer": final_answer[:600]},
            "latency": time.perf_counter() - t0,
            "llm_calls": len([c for c in commands if c != "invalid"])}


# ── 8. DeepRead(TOC + Retrieve 扫描窗 + ReadSection) ────────────────────────

DEEPREAD_BOOT = """You are verifying a scientific claim against a corpus of {n} research papers.
Document structure (TOC). Format: [doc_id] title | sec <i>: <heading> (<p> paras, ~<c> chars)
{toc}

Tools — output EXACTLY ONE line per turn:
Retrieve: <free-text query>          # semantic scan over paragraphs; returns top-2
                                     # hits with ±1 neighboring paragraphs and coordinates
ReadSection: <doc_id> | <sec> | <start> | <end>   # read a contiguous paragraph span
Final Answer: <your verdict and justification>
Use at most {cap} turns. Locate first, then read.

Claim: {claim}"""


def _deepread_toc(ctx: Ctx) -> str:
    lines = []
    for cid, sections in ctx.structure.items():
        title = ctx.corpus[cid]["title"][:70]
        lines.append(f"[{cid}] {title}")
        for s in sections:
            lines.append(f"    sec {s.sec}: {s.heading[:60]} "
                         f"({len(s.paras)} paras, ~{s.n_chars} chars)")
    return "\n".join(lines)


def _para_lookup(ctx: Ctx, cid: str, sec: int, para: int) -> str:
    try:
        return ctx.structure[cid][sec].paras[para].text
    except Exception:  # noqa: BLE001
        return ""


def deepread(ctx: Ctx, claim: str) -> dict:
    t0 = time.perf_counter()
    rpc = ctx.new_rpc("deepread")
    gathered: dict[str, dict] = {}
    commands: list[str] = []

    def remember(cid: str, text: str, meta: str, score: float) -> None:
        gathered.setdefault(meta, {"src": cid, "text": text[:1400],
                                   "meta": meta, "score": score})

    try:
        msg = DEEPREAD_BOOT.format(n=len(ctx.corpus),
                                   toc=_deepread_toc(ctx)[:6000],
                                   cap=AGENTIC_CAP, claim=claim)
        for turn in range(AGENTIC_CAP):
            out = rpc.prompt(msg)
            line = next((l.strip() for l in out.splitlines() if l.strip()), "")
            m_final = re.match(r"(?i)^final\s*answer\s*[:：]\s*(.+)$", line)
            m_read = re.match(r"(?i)^readsection\s*[:：]\s*(.+)$", line)
            m_ret = re.match(r"(?i)^retrieve\s*[:：]\s*(.+)$", line)
            if m_final:
                commands.append("final")
                break
            if m_read:
                parts = [p.strip() for p in m_read.group(1).split("|")]
                commands.append(f"read:{m_read.group(1)[:80]}")
                if len(parts) != 4:
                    msg = ("Malformed ReadSection. Use: "
                           "ReadSection: <doc_id> | <sec> | <start> | <end>")
                    continue
                cid = parts[0]
                try:
                    sec, start, end = (int(parts[1]), int(parts[2]), int(parts[3]))
                except ValueError:
                    msg = "sec/start/end must be integers."
                    continue
                sections = ctx.structure.get(cid)
                if not sections or sec < 0 or sec >= len(sections):
                    msg = f"Unknown doc/section: {cid} sec {sec}. Use the TOC."
                    continue
                sec_obj = sections[sec]
                s = max(0, start)
                e = min(len(sec_obj.paras) - 1, end)
                span = [(cid, sec, p) for p in range(s, e + 1)]
                body = "\n---\n".join(
                    f"[{pc} sec {psec} para {pp}] {_para_lookup(ctx, pc, psec, pp)}"
                    for (pc, psec, pp) in span)
                for (pc, psec, pp) in span:
                    t = _para_lookup(ctx, pc, psec, pp)
                    if t:
                        remember(pc, t, f"{pc}#s{psec}p{pp}", 1.0)
                msg = (f"ReadSection result ({len(span)} paragraphs):\n{body[:2600]}"
                       "\n\nContinue. One line: Retrieve: / ReadSection: / Final Answer:")
            elif m_ret:
                q = m_ret.group(1).strip()[:400]
                commands.append(f"retrieve:{q[:80]}")
                hits = ctx.vector(KB_PARA, q, 2)
                shown: set[tuple] = set()
                body_parts = []
                for h in hits:
                    dp = h["path"]
                    base = dp.rsplit("/", 1)[-1]
                    try:
                        cid = base.split("__")[0]
                        tail = base.split("__")[1]
                        sec = int(tail[1:3])
                        para = int(tail[3:6])
                    except (IndexError, ValueError):
                        continue
                    for pp in (para - 1, para, para + 1):  # 扫描窗 ω=(1,1)
                        coord = (cid, sec, pp)
                        if pp < 0 or coord in shown:
                            continue
                        t = _para_lookup(ctx, cid, sec, pp)
                        if not t:
                            continue
                        shown.add(coord)
                        tag = "HIT" if pp == para else "ctx"
                        body_parts.append(
                            f"[{tag} {cid} sec {sec} para {pp}] {t[:800]}")
                        remember(cid, t, f"{cid}#s{sec}p{pp}", h["score"])
                msg = ("Retrieve results:\n" + ("\n---\n".join(body_parts) or "(no hit)")
                       + "\n\nContinue. One line: Retrieve: / ReadSection: / Final Answer:")
            else:
                commands.append("invalid")
                msg = ("Invalid command. Output exactly one line: "
                       "'Retrieve: <query>' | 'ReadSection: <doc> | <sec> | <start> | <end>' | "
                       "'Final Answer: <answer>'.")
        else:
            commands.append("cap_reached")
    finally:
        rpc.close()
    chunks = list(gathered.values())
    seen: set[str] = set()
    doc_rank = [c["src"] for c in chunks
                if not (c["src"] in seen or seen.add(c["src"]))]
    return {"doc_rank": doc_rank, "chunks": chunks,
            "trace": {"turns": len(commands), "commands": commands},
            "latency": time.perf_counter() - t0,
            "llm_calls": len([c for c in commands if c != "invalid"])}


METHODS = {
    "qdcvr": {"fn": lambda ctx, q: qdcvr(ctx, q),
              "paper": "this system (knowledgebase-search skill QDCVR)"},
    "dense_rag": {"fn": lambda ctx, q: dense(ctx, q, rerank=False),
                  "paper": "Dense RAG (chunk 800/400, top-10)"},
    "dense_rag_rerank": {"fn": lambda ctx, q: dense(ctx, q, rerank=True),
                         "paper": "Dense RAG w/ Reranker (30→rerank→10)"},
    "raptor": {"fn": lambda ctx, q: raptor(ctx, q),
               "paper": "RAPTOR Collapsed Tree (≤800 tok/node, 5 layers, "
                        "cluster top-5, top-10 nodes)"},
    "itrg_refresh": {"fn": lambda ctx, q: itrg(ctx, q, "refresh"),
                     "paper": "ITRG (refresh), 4 rounds × top-6"},
    "itrg_refine": {"fn": lambda ctx, q: itrg(ctx, q, "refine"),
                    "paper": "ITRG (refine), 4 rounds × top-6"},
    "search_o1": {"fn": lambda ctx, q: search_o1(ctx, q),
                  "paper": "Search-o1 agentic search (struct chunks o0, "
                           "2 chunks/call, cap 8)"},
    "deepread": {"fn": lambda ctx, q: deepread(ctx, q),
                 "paper": "DeepRead locate-then-read (TOC + Retrieve ω=(1,1) "
                          "+ ReadSection, cap 8)"},
}
