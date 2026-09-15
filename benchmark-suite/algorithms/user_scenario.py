#!/usr/bin/env python3
"""真实场景画像 — 把论文复现检索算法矩阵移植到任意用户上传文档.

与 E16 冻结矩阵(KB-SciFact + DR-*)完全解耦, 同一套算法实现换语料即用:
  生产 KB   kb_doc_create(平台真实用户路径: tree-fs + 后台向量/图索引) → qdcvr
  基线 KB   各论文自己的分块方案(suite 侧复现): Chunks800/Struct/Paras/Raptor
  问题      omp Agent 从文档内容生成(非人工挑选), 附逐字支持引文与期望答案
  作答      同一 omp Harness 同一模型, 统一证据预算(与 E16 对称)
  评审      独立 omp Agent(无检索参与), 注入问题生成时的逐字金标引文
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import index_kb
from index_kb import (CACHE, build_kb, dump_texts, items_fixed,  # noqa: E402
                      items_para, items_struct, load_texts)
import methods  # noqa: E402
from methods import Ctx, pack  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent


# ── 语料与指纹 ────────────────────────────────────────────────────────────────

def load_user_docs(paths: list[Path]) -> list[dict]:
    """本地文件 → [{cid, title, text, path}] — cid=文件名去扩展名。"""
    docs = []
    for p in paths:
        text = Path(p).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        title = ""
        if lines and lines[0].lstrip().startswith("#"):
            title = lines[0].lstrip().lstrip("#").strip()
        docs.append({"cid": Path(p).stem, "title": title or Path(p).stem,
                     "text": text, "path": Path(p).name})
    return docs


def fingerprint(docs: list[dict]) -> str:
    h = hashlib.sha256()
    for d in docs:
        h.update(d["cid"].encode())
        h.update(b"\x00")
        h.update(d["text"].encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()[:16]


# ── 生产 KB(平台真实用户路径) ────────────────────────────────────────────────

def _find_kb_id(mc, name: str) -> str:
    r = mc.call("kb_list", {"lightweight": True}, timeout=120)
    for k in r.get("catalog") or []:
        if k.get("name") == name:
            return k.get("kb_id") or name
    return ""


def ensure_production_kb(mc, kb_name: str, docs: list[dict],
                         wait_seconds: int = 300) -> dict:
    """删旧建新(确定性) + kb_doc_create 逐篇上传 + 轮询后台索引直至可查。

    kb_doc_create 是 web 层上传的底层契约: 文档落 tree-fs, 后台 fire-and-forget
    向量+图索引 — 因此必须轮询探针, 索引未完成时检索会静默为空。
    """
    t0 = time.perf_counter()
    old = _find_kb_id(mc, kb_name)
    if old:
        mc.call("kb_delete", {"kb_id": old}, timeout=300)
        time.sleep(2)
    mc.call("kb_create", {"name": kb_name,
                          "description": "real-scenario user-uploaded docs"},
            timeout=180)
    created = []
    for d in docs:
        r = mc.call("kb_doc_create",
                    {"kb_id": kb_name, "name": d["path"],
                     "content": d["text"],
                     "description": d["title"][:160]}, timeout=180)
        if not (isinstance(r, dict) and r.get("success")):
            raise RuntimeError(f"kb_doc_create failed for {d['path']}: "
                               f"{str(r)[:200]}")
        created.append(d["path"])

    # 轮询: 每篇文档都要能被向量检索命中(路径前缀必须归属本 KB)
    probes = {d["cid"]: _probe_term(d) for d in docs}
    pending = set(probes)
    deadline = time.time() + wait_seconds
    hits_by_doc: dict[str, int] = {}
    while pending and time.time() < deadline:
        time.sleep(5)
        for cid in list(pending):
            r = mc.call("kb_search_vector",
                        {"query": probes[cid], "kb_id": kb_name, "top_k": 3},
                        timeout=120)
            hits = [h for h in (r.get("results") or [])
                    if str(h.get("doc_path", "")).startswith(kb_name + "/")]
            if hits:
                hits_by_doc[cid] = len(hits)
                pending.discard(cid)
    if pending:
        raise RuntimeError(f"production KB background index not queryable "
                           f"after {wait_seconds}s for: {sorted(pending)}")
    return {"kb": kb_name, "docs": created, "probe_hits": hits_by_doc,
            "wait_seconds": round(time.perf_counter() - t0, 1)}


def _probe_term(d: dict) -> str:
    """文档专属探针词: 标题前 8 个词 + 正文一段切片, 避免与其他文档混淆。"""
    words = re.findall(r"[\w]{2,}", d["title"] or d["text"][:200])
    return " ".join(words[:8]) or d["text"][:60]


# ── 基线 KB(suite 侧按各论文分块方案复现) ────────────────────────────────────

def build_baseline_kbs(mc, docs: list[dict], prefix: str) -> dict:
    out = {}
    for name, fn in ((f"{prefix}-Chunks800", items_fixed),
                     (f"{prefix}-Struct", items_struct),
                     (f"{prefix}-Paras", items_para)):
        print(f"    [index] {name} ...", flush=True)
        out[name] = build_kb(mc, name, fn(docs, kb_prefix=name))
    return out


def build_user_raptor(mc, oneshot, docs: list[dict], prefix: str) -> dict:
    import raptor
    tree = raptor.build_tree(mc, oneshot, force=True,
                             kb=f"{prefix}-Raptor",
                             tree_path=CACHE / f"raptor_tree_{prefix}.json",
                             corpus_docs=docs)
    return {k: v for k, v in tree.items() if k != "nodes"} | {
        "n_nodes": len(tree.get("nodes", {}))}


# ── 方法画像激活(重绑 methods 模块级 KB 常量; 默认仍是 SciFact) ─────────────

def activate_profile(prefix: str, prod_kb: str) -> dict:
    """把 methods 的 KB 全局重绑到用户画像; 返回旧值便于恢复。"""
    old = {k: getattr(methods, k) for k in
           ("KB_SCIFACT", "KB_FIXED", "KB_STRUCT", "KB_PARA", "KB_RAPTOR")}
    methods.KB_SCIFACT = prod_kb
    methods.KB_FIXED = f"{prefix}-Chunks800"
    methods.KB_STRUCT = f"{prefix}-Struct"
    methods.KB_PARA = f"{prefix}-Paras"
    methods.KB_RAPTOR = f"{prefix}-Raptor"
    return old


def make_ctx_factory(mc_factory, docs: list[dict], prefix: str):
    """每线程独立 Ctx(独立 MCP 子进程 + 独立 oneshot), 与 api_server 同构。"""
    kb_names = (f"{prefix}-Chunks800", f"{prefix}-Struct",
                f"{prefix}-Paras", f"{prefix}-Raptor")
    import threading

    local = threading.local()

    def get() -> Ctx:
        ctx = getattr(local, "ctx", None)
        if ctx is None:
            from omp_client import OmpOneshot, OmpRpc
            ctx = Ctx(mc_factory(), lambda stage: OmpRpc(stage=stage,
                                                         timeout=420),
                      OmpOneshot(stage="aux", timeout=300),
                      kb_names=kb_names, corpus_docs=docs)
            tree_file = CACHE / f"raptor_tree_{prefix}.json"
            if tree_file.exists():
                ctx.tree = json.loads(tree_file.read_text(encoding="utf-8"))
            local.ctx = ctx
        return ctx

    return get


# ── 问题生成(omp Agent 从文档内容出题, 留 provenance) ────────────────────────

GEN_Q_PROMPT = """Read the DOCUMENT below and write {n} factual questions about it.
Rules:
- Each question MUST be answerable ONLY from this document, not from general knowledge.
- Write each question in the SAME LANGUAGE as the document.
- Include one short verbatim quote (<=200 chars, copied from the document) that
  supports the answer, and a short expected answer.
- Vary the angles: one overview/concept, one concrete detail or number,
  one mechanism/relationship.
Reply ONLY a JSON array:
[{{"question": "...", "expected": "<short expected answer>",
   "quote": "<verbatim supporting quote from the document>"}}]

DOCUMENT — {title}:
{text}"""


def generate_questions(oneshot, docs: list[dict], per_doc: int = 3) -> tuple[list[dict], dict]:
    questions = []
    provenance = {"per_doc": per_doc, "docs": {}}
    for i, d in enumerate(docs):
        raw = oneshot(GEN_Q_PROMPT.format(n=per_doc, title=d["title"],
                                          text=d["text"][:12000]))
        from omp_client import extract_json
        arr = extract_json(raw)
        if not isinstance(arr, list):
            raise RuntimeError(f"question generation failed for {d['cid']}: "
                               f"{raw[:200]}")
        provenance["docs"][d["cid"]] = {"raw_prompt_sha": hashlib.sha256(
            raw.encode("utf-8")).hexdigest()[:12], "generated": len(arr)}
        for j, q in enumerate(arr[:per_doc]):
            if not isinstance(q, dict) or not q.get("question"):
                continue
            questions.append({
                "qid": f"U{i * per_doc + j + 1}",
                "doc": d["cid"],
                "question": str(q.get("question", "")).strip(),
                "expected": str(q.get("expected", "")).strip(),
                "gold_quote": str(q.get("quote", "")).strip()})
    return questions, provenance


# ── 作答 / 评审 / 中间 Agent 排名(与 E16 同构, 开放 QA 措辞) ─────────────────

SCEN_ANSWER_PROMPT = """You are a document-grounded QA assistant.
Question: {claim}

Evidence excerpts retrieved from the document collection (source id in brackets):
{evidence}

Using ONLY the evidence above, respond with ONLY a JSON object:
{{"answer": "<2-4 sentence factual answer in the question's language; say the evidence is insufficient if the excerpts do not contain it>",
  "evidence_used": ["<source id>", ...]}}"""

SCEN_JUDGE_PROMPT = """You are an independent, strict grader. You did not retrieve
anything yourself and have no stake in any retrieval method. Grade the ANSWER below
against the GOLD EVIDENCE quoted verbatim from the ground-truth document.

Question: {claim}

GOLD EVIDENCE (verbatim from the ground-truth document):
{gold}

ANSWER UNDER EVALUATION:
{answer}

Score 0-10. Rubric: factual correctness vs the gold evidence (0-5); grounding in the
gold evidence with no fabrication (0-4); clarity and completeness (0-1).
Reply ONLY a JSON object:
{{"score": <0-10>, "verdict_ok": true|false, "issues": "<one short sentence>"}}"""

SCEN_RANK_PROMPT = """You are a neutral middle agent grading answers from N different
retrieval systems to the SAME question, using the ground-truth evidence.

Question: {claim}

GOLD EVIDENCE (verbatim from the ground-truth document):
{gold}

CANDIDATE ANSWERS (anonymized):
{answers}

Grade each candidate 0-10 (factual correctness vs gold evidence 0-5; grounding,
no fabrication 0-4; clarity/completeness 0-1). Reply ONLY a JSON array, best first:
[{{"alias": "A", "score": <0-10>}}, ...] covering ALL aliases."""


def norm_cid(cid: str) -> str:
    # 平台对大文档按 "(part N of M)" 拆分入库(kb_doc_create 生产路径),
    # doc 级命中须把部件后缀归一到源文档; 同时去 .md 与大小写差异。
    c = str(cid).strip().removesuffix(".md").strip()
    c = re.sub(r"\s*\(\s*part\s+\d+\s+of\s+\d+\s*\)\s*$", "", c, flags=re.I)
    return c.lower()


def parse_answer_fallback(raw: str) -> dict | None:
    """严格 JSON 解析失败后的字段级回退。

    中文回答常含未转义 ASCII 引号(如 构造"向量高分但内容不符"的样本),
    balanced-parse 会整体失败但字段内容完好 — 用非贪婪字段捕获恢复。
    """
    m = re.search(r'"answer"\s*:\s*"(.*?)"\s*,\s*"evidence_used"', raw, re.S)
    if not m:
        return None
    ev: list[str] = []
    m2 = re.search(r'"evidence_used"\s*:\s*\[(.*?)\]', raw, re.S)
    if m2:
        ev = [e.strip().strip("\"'") for e in m2.group(1).split(",")
              if e.strip()]
    return {"answer": m.group(1).strip(), "evidence_used": ev}


def doc_hits(doc_rank: list[str], gold_cid: str) -> dict:
    rank = [norm_cid(c) for c in doc_rank]
    g = norm_cid(gold_cid)
    hit1 = 1 if rank[:1] == [g] else 0
    hit3 = 1 if g in rank[:3] else 0
    return {"gold": gold_cid, "rank_position": (rank.index(g) + 1)
            if g in rank else 0, "hit@1": hit1, "hit@3": hit3,
            "n_docs_returned": len(rank)}


def answer_question(oneshot_factory, question: str, ev: dict) -> dict:
    from omp_client import extract_json
    evidence, used = pack(ev.get("chunks") or [])
    oneshot = oneshot_factory("answer")
    raw = oneshot(SCEN_ANSWER_PROMPT.format(
        claim=question, evidence=evidence or "(no evidence retrieved)"))
    parsed = extract_json(raw)
    return {"raw": raw[:2000], "parsed": parsed if isinstance(parsed, dict) else {},
            "evidence_chars": len(evidence), "evidence_chunks": len(used),
            "sources": sorted({c.get("src", "") for c in used})}


def judge_answer(oneshot_factory, question: str, gold_quote: str,
                 ans: dict) -> dict:
    from omp_client import extract_json
    answer_text = json.dumps(ans.get("parsed") or {"raw": ans.get("raw", "")},
                             ensure_ascii=False)
    oneshot = oneshot_factory("judge")
    prompt = SCEN_JUDGE_PROMPT.format(claim=question, gold=gold_quote[:1500],
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
    return {"raw": raw[:1200], "parsed": parsed}


def middle_agent_rank(oneshot_factory, question: str, gold_quote: str,
                      answers: dict) -> list[dict]:
    from omp_client import extract_json
    aliases, lines = {}, []
    for i, (method, ans) in enumerate(sorted(answers.items())):
        alias = chr(ord("A") + i)
        aliases[alias] = method
        text = json.dumps(ans.get("parsed") or {"raw": ans.get("raw", "")},
                          ensure_ascii=False)
        lines.append(f"[{alias}] ({method}) {text[:500]}")
    oneshot = oneshot_factory("rank")
    raw = oneshot(SCEN_RANK_PROMPT.format(claim=question,
                                          gold=gold_quote[:1500],
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
