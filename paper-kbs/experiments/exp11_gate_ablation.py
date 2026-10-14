#!/usr/bin/env python
"""exp11_gate_ablation.py — E-A: end-to-end ablation of the CONTENT-VERIFICATION gate.

PURPOSE
-------
Isolate the contribution of the platform's content-verification component (the
Laya evidence gate) with everything else held fixed, as the journal requires of
a knowledge-component ablation.

PROTOCOL AS ACTUALLY EXECUTED
-----------------------------
The paper's original plan was two server-side retrieval conditions differing only
by one flag: ``kb_hybrid_search(enable_judge=true|false, candidate_cap=12)``
(see ``paper-kbs/experiments/exp1_retrieval.py:162-183`` for that call shape).

**That tool no longer exists on the live server.** The live kb-mcp exposes 95
tools and ``kb_hybrid_search`` is not among them (verified by enumerating
``tools/list`` and by grepping ``kb-mcp/server.py``: zero matches). The
verification gate itself is still live and is exposed as the MCP tool
``kb_laya_judge`` (``kb-mcp/server.py:2725``).

Fallback (state explicitly in the report): the ablation is reconstructed so the
gate is the ONLY thing that differs, and it is applied to a FROZEN candidate set
so the two conditions are identical by construction rather than by re-running
retrieval twice:

  1. Candidate stage C(q) — executed ONCE per question, cached to disk:
       vector lane : kb_search_vector(query, kb_id=<each of the 5 domain
                     libraries>, top_k=30, score_threshold=0.35, slim=True),
                     merged doc-level by best cosine score
       catalog lane: kb_list + kb_get_documents(lightweight=True) over the same
                     5 libraries, ranked by query<->description token overlap
       fusion      : agreed-first, then vector-only top-8, then catalog-only
                     top-4, capped at 12
                     (this reproduces the fusion the retired server tool
                     described as "agreed-first, then vector top8, catalog
                     top4" — exp1_retrieval.py:165-168)
     Each candidate's 700-char head is fetched ONCE with kb_doc_read and stored,
     so both arms pack byte-identical source text.

  2. Two retrieval conditions per question, differing ONLY in the gate:
       C-nogate : the fusion-ranked candidate list is the retrieval output
       C-judge  : kb_laya_judge(query, documents=C(q) as {kb_id, doc_path}
                  references, criterion="auto", threshold=0.5) — content-read,
                  per-segment engine scored, relatively cut; the survivors are
                  the retrieval output

  3. A third, clearly-labelled arm records what the live pipeline actually
     hands the answerer (the gate's own segment-level evidence_pack):
       C-judge-seg : C-judge survivors' segment text as merged by the engine

  4. Identical downstream for every arm:
       evidence pack = spread_pack(docs in that arm's order, per_doc=700,
                                   budget=4000)
       (byte-identical to scripts/143_e2e_modes_baselines.py:92-101)
       answer        = chat_tracks.answer_closed_book(question, pack)
                       [platform chat API, engine pinned to "claude" by
                        chat_tracks.py:243, no tools, max_turns=1]
       grade         = same LLM grader prompt for every arm
                       (143_e2e_modes_baselines.py:223-233)

READ-ONLY: this script only queries/searches/reads/answers. It never creates,
updates, deletes, moves, re-indexes, re-tags or re-parses anything.

USAGE
-----
  python paper-kbs/experiments/exp11_gate_ablation.py \
      --out paper-kbs/experiments/results/exp11/<run-id>
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "benchmark-suite"
for _p in (SUITE, SUITE / "experiments", SUITE / "scripts"):
    sys.path.insert(0, str(_p))

import lib as L  # noqa: E402  (benchmark-suite/scripts/lib.py)
from chat_tracks import answer_closed_book  # noqa: E402

# ── the 5 content-routed libraries of the 100-paper / 322-part corpus ──
DOMAIN_LIBS = {
    "计算机与人工智能": "b1199132-e4d4-4305-8c2e-82dc1753b0ba",
    "自然科学与地球科学": "1e6199ea-f380-44e2-94fc-d431f0f9bb6b",
    "生命科学与医学": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28",
    "工程与能源": "8fa4db59-adde-4d6d-9fdb-2c375400e631",
    "经济与社会": "f5770687-6b05-4a8d-8645-af31686ca87e",
}
LIB_BY_ID = {v: k for k, v in DOMAIN_LIBS.items()}

QUESTIONS = SUITE / "data" / "papers" / "qa_quick10.json"
ANSWER_EVIDENCE_BUDGET = 4000  # unified budget, same as 143_e2e_modes_baselines.py:30
PER_DOC = 700                  # same per-doc head budget as 143 mode_pack
CANDIDATE_CAP = 12             # same candidate_cap the retired tool used
VECTOR_TOP8 = 8
CATALOG_TOP4 = 4
VEC_TOP_K = 30
VEC_THRESH = 0.35
JUDGE_THRESHOLD = 0.5
JUDGE_CRITERION = "auto"
ARMS = ("C-nogate", "C-judge", "C-judge-seg")
PRIMARY_PAIR = ("C-nogate", "C-judge")

GRADER_PROMPT = (
    "You are a strict QA grader. Grade the ANSWER against GOLD POINTS.\n"
    "score: 0=wrong or refusal on answerable, 3=partial, 5=complete&correct.\n"
    "Reply with ONLY a JSON object: "
    '{{"score": <0-5>, "verdict": "correct|partial|wrong|refusal", '
    '"rationale": "<one sentence>"}}\n\n'
    "QUESTION: {q}\n"
    "GOLD_POINTS: {gp}\n"
    "GOLD_KEYWORDS: {gk}\n"
    "STRATUM: {st}\n"
    "ANSWER: {ans}"
)


# ─────────────────────────── helpers ───────────────────────────
def norm_path(p) -> str:
    return str(p or "").replace("\\", "/")


def basename(p) -> str:
    return norm_path(p).rsplit("/", 1)[-1]


def tokenize(s) -> set:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9.\-]{1,}", str(s or "").lower())}


def spread_pack(docs, per_doc: int = PER_DOC,
                budget: int = ANSWER_EVIDENCE_BUDGET) -> str:
    """Byte-identical to scripts/143_e2e_modes_baselines.py:92-101.

    "按文档顺序逐篇头部摘录直到预算" — every arm packs with THIS function, so
    only the document ORDER/SET can differ between conditions.
    """
    parts, total = [], 0
    for d in docs:
        if total >= budget:
            break
        piece = str(d.get("content") or "")[:per_doc]
        parts.append(piece)
        total += len(piece)
    return "\n\n".join(parts)[:budget]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────── candidate stage (shared) ───────────────────────
def vector_lane(mc, query: str) -> tuple:
    """kb_search_vector over the 5 domain libraries, merged doc-level by score."""
    t0 = time.time()
    best: dict = {}
    order = []
    per_lib = {}
    for name, kid in DOMAIN_LIBS.items():
        r = mc.call("kb_search_vector",
                    {"query": query, "kb_id": kid, "top_k": VEC_TOP_K,
                     "score_threshold": VEC_THRESH, "slim": True}, timeout=300)
        hits = r.get("results") or []
        per_lib[name] = len(hits)
        for h in hits:
            dp = norm_path(h.get("doc_path"))
            if not dp:
                continue
            key = (kid, dp)
            sc = float(h.get("score") or 0.0)
            if key not in best:
                best[key] = {"kb_id": kid, "doc_path": dp, "vector_score": sc,
                             "n_chunks": 0}
                order.append(key)
            best[key]["n_chunks"] += 1
            best[key]["vector_score"] = max(best[key]["vector_score"], sc)
    docs = sorted(best.values(), key=lambda d: -d["vector_score"])
    for i, d in enumerate(docs):
        d["vector_rank"] = i + 1
    return docs, {"per_lib_hits": per_lib, "raw_hits": sum(per_lib.values()),
                  "doc_level": len(docs), "seconds": round(time.time() - t0, 1)}


def catalog_lane(mc, query: str) -> tuple:
    """kb_list + kb_get_documents(lightweight) → query<->description overlap rank."""
    t0 = time.time()
    q_terms = tokenize(query)
    rows = []
    per_lib = {}
    for name, kid in DOMAIN_LIBS.items():
        r = mc.call("kb_get_documents", {"kb_id": kid, "lightweight": True},
                    timeout=180)
        cat = r.get("catalog") or []
        per_lib[name] = len(cat)
        for d in cat:
            dp = norm_path(d.get("doc_path"))
            if not dp:
                continue
            desc = " ".join([str(d.get("name") or ""), str(d.get("description") or "")])
            rows.append({"kb_id": kid, "doc_path": dp,
                         "overlap": len(q_terms & tokenize(desc))})
    rows.sort(key=lambda d: (-d["overlap"], d["doc_path"]))
    positive = [r for r in rows if r["overlap"] > 0]
    for i, d in enumerate(positive):
        d["catalog_rank"] = i + 1
    return positive, {"per_lib_docs": per_lib, "catalog_size": len(rows),
                      "catalog_overlap_gt0": len(positive),
                      "seconds": round(time.time() - t0, 1)}


def fuse(vec_docs, cat_docs) -> tuple:
    """agreed-first, then vector top-8, then catalog top-4, capped at 12."""
    cat_by_key = {(d["kb_id"], d["doc_path"]): d for d in cat_docs}
    vec_by_key = {(d["kb_id"], d["doc_path"]): d for d in vec_docs}

    agreed, vec_only, cat_only = [], [], []
    for d in vec_docs:  # already score-sorted
        key = (d["kb_id"], d["doc_path"])
        if key in cat_by_key:
            agreed.append({"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                           "lane": "both", "vector_score": d["vector_score"],
                           "vector_rank": d.get("vector_rank"),
                           "catalog_rank": cat_by_key[key].get("catalog_rank")})
        else:
            vec_only.append({"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                             "lane": "vector", "vector_score": d["vector_score"],
                             "vector_rank": d.get("vector_rank")})
    for d in cat_docs:
        key = (d["kb_id"], d["doc_path"])
        if key not in vec_by_key:
            cat_only.append({"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                             "lane": "catalog", "overlap": d.get("overlap"),
                             "catalog_rank": d.get("catalog_rank")})

    fused = agreed + vec_only[:VECTOR_TOP8] + cat_only[:CATALOG_TOP4]
    fused = fused[:CANDIDATE_CAP]
    for i, d in enumerate(fused):
        d["fused_rank"] = i + 1
    trace = {"agreed": len(agreed), "vector_only_pool": len(vec_only),
             "catalog_only_pool": len(cat_only),
             "vector_only_taken": len(vec_only[:VECTOR_TOP8]),
             "catalog_only_taken": len(cat_only[:CATALOG_TOP4]),
             "fused_before_cap": len(agreed) + len(vec_only[:VECTOR_TOP8])
                                 + len(cat_only[:CATALOG_TOP4]),
             "fused_after_cap": len(fused), "candidate_cap": CANDIDATE_CAP}
    return fused, trace


def fetch_heads(mc, candidates) -> tuple:
    """kb_doc_read 700-char head per candidate — fetched ONCE, shared by all arms."""
    t0 = time.time()
    contents, errors = {}, []
    for c in candidates:
        key = (c["kb_id"], c["doc_path"])
        try:
            r = mc.call("kb_doc_read", {"kb_id": c["kb_id"],
                                        "doc_path": basename(c["doc_path"]),
                                        "max_chars": PER_DOC}, timeout=180)
            txt = str(r.get("content") or "")
            if not txt.strip():
                errors.append({"doc_path": c["doc_path"],
                               "error": str(r.get("error") or "empty content")[:200]})
            contents[key] = txt
        except Exception as exc:  # noqa: BLE001
            contents[key] = ""
            errors.append({"doc_path": c["doc_path"],
                           "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
    return contents, {"seconds": round(time.time() - t0, 1), "errors": errors}


def judge_candidates(mc, query, candidates) -> tuple:
    """kb_laya_judge in reference mode: server fetches every body itself."""
    t0 = time.time()
    refs = [{"kb_id": c["kb_id"], "doc_path": c["doc_path"]} for c in candidates]
    r = mc.call("kb_laya_judge",
                {"query": query, "documents": json.dumps(refs),
                 "criterion": JUDGE_CRITERION, "threshold": JUDGE_THRESHOLD,
                 "max_evidence_chars": ANSWER_EVIDENCE_BUDGET,
                 "include_text": False}, timeout=1800)
    surv = []
    seen = set()
    for s in (r.get("survivors") or []):
        dp = norm_path(s.get("doc_path"))
        kb = s.get("kb_id") or ""
        if not kb:  # engine may echo a KB-name-prefixed path only
            head = dp.split("/", 1)[0]
            kb = DOMAIN_LIBS.get(head, head)
        key = (kb, dp if "/" in dp else dp)
        if key in seen:
            continue
        seen.add(key)
        surv.append({"kb_id": kb, "doc_path": dp,
                     "score": s.get("score"), "segment": s.get("segment")
                     or s.get("segment_index")})
    meta = {"status": r.get("status"), "real_engine": r.get("real_engine"),
            "criterion": r.get("criterion"), "threshold": r.get("threshold"),
            "candidate_count": r.get("candidate_count"),
            "scored_count": r.get("scored_count"),
            "survivor_count": r.get("survivor_count"),
            "docs_with_yes": r.get("docs_with_yes"),
            "evidence_pack_chars": len(str(r.get("evidence_pack") or "")),
            "fetch_errors": r.get("fetch_errors") or [],
            "errors": r.get("errors") or [],
            "seconds": round(time.time() - t0, 1)}
    return surv, str(r.get("evidence_pack") or ""), meta


# ─────────────────────── gold-document resolution ───────────────────────
def gold_index() -> dict:
    """arxiv_id -> the set of live doc_paths (whole-paper level; parts collapse)."""
    q = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    idx = {}
    for item in q["questions"]:
        ids = [str(g) for g in (item.get("gold_docs") or [])]
        idx[item["qid"]] = ids
    return idx


def resolve_gold(mc, arxiv_ids) -> set:
    """Map gold arXiv ids to the live document paths that contain them.

    Documents are split into parts named
    ``{field}__{arxiv_id}__{slug} (part i of n).md``; a gold hit at paper level
    is ANY part of that arXiv id, so hits are reported at paper granularity.
    """
    want = {a.lower() for a in arxiv_ids}
    if not want:
        return set()
    patterns = set()
    for a in want:
        patterns.add("__" + a + "__")
        patterns.add("__" + a.replace("/", "-") + "__")
    out = set()
    for kid in DOMAIN_LIBS.values():
        r = mc.call("kb_get_documents", {"kb_id": kid, "lightweight": True},
                    timeout=180)
        for d in (r.get("catalog") or []):
            name = str(d.get("name") or "").lower()
            if any(p in name for p in patterns):
                out.add((kid, norm_path(d.get("doc_path"))))
    return out


def rank_of_gold(order_keys, gold_keys) -> int | None:
    for i, k in enumerate(order_keys):
        if k in gold_keys:
            return i + 1
    return None


# ─────────────────────────── generation + grading ───────────────────────────
def _call_with_token_retry(fn, *a, **kw):
    """Run fn; on an HTTP 401 refresh the platform token once and retry.

    The platform bearer token expires mid-run. ``answer_closed_book`` heals
    itself only on the stream-open path, so the GRADER call is not covered and
    two cells of run exp11-20261012-full died with
    ``HTTPError: HTTP Error 401: Unauthorized``. This wrapper covers both.
    """
    try:
        return fn(*a, **kw)
    except Exception as exc:  # noqa: BLE001
        if "401" not in str(exc) and "Unauthorized" not in str(exc):
            raise
        L.login_refresh()
        return fn(*a, **kw)


def answer(question: str, pack: str, timeout_s: int) -> dict:
    t0 = time.time()
    try:
        r = _call_with_token_retry(answer_closed_book, question, pack,
                                   timeout_s=timeout_s)
        return {"answer": r.get("answer"), "is_error": r.get("is_error"),
                "tokens": r.get("tokens") or {},
                "total_cost_usd": r.get("total_cost_usd"),
                "model": r.get("model") or r.get("engine"),
                "latency_s": round(time.time() - t0, 1), "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"answer": f"(failed: {type(exc).__name__}: {str(exc)[:300]})",
                "is_error": True, "tokens": {}, "total_cost_usd": None,
                "model": None, "latency_s": round(time.time() - t0, 1),
                "error": f"{type(exc).__name__}: {str(exc)[:400]}"}


def grade(item: dict, ans: str, timeout_s: int) -> dict:
    prompt = GRADER_PROMPT.format(
        q=item["question"],
        gp=json.dumps(item.get("gold_points") or [], ensure_ascii=False),
        gk=json.dumps(item.get("gold_keywords") or [], ensure_ascii=False),
        st=item.get("stratum", "single"), ans=str(ans or "")[:4000])
    t0 = time.time()
    try:
        r = _call_with_token_retry(answer_closed_book, prompt, "",
                                   timeout_s=timeout_s)
        txt = str(r.get("answer") or "")
        mt = re.search(r"\{.*\}", txt, re.S)
        j = (json.loads(mt.group(0)) if mt
             else {"score": None, "verdict": "unparsed", "rationale": txt[:120]})
    except Exception as exc:  # noqa: BLE001
        j = {"score": None, "verdict": "error",
             "rationale": f"{type(exc).__name__}: {str(exc)[:120]}"}
    j["grade_latency_s"] = round(time.time() - t0, 1)
    return j


def rebuild_packs(mc, cell, cand, question, need_seg=False):
    """Rebuild an arm's evidence pack byte-identically from frozen artifacts.

    Used by --repair / --noise-probe so a lost cell can be re-generated without
    re-running retrieval or the gate (the gate is re-called only when the
    segment arm's pack is actually needed — it is engine scoring, not an LLM).
    """
    fused = cand["fused"]
    heads = {tuple(k.split("||", 1)): v for k, v in cand["heads"].items()}
    cand_keys = [(c["kb_id"], c["doc_path"]) for c in fused]
    by_path = {p: k for k, p in cand_keys}
    surv_keys = [by_path[p] for p in
                 ((cell["arms"].get("C-judge") or {}).get("docs") or [])
                 if p in by_path]
    packs = {
        "C-nogate": spread_pack([{"content": heads.get(k, "")} for k in cand_keys]),
        "C-judge": spread_pack([{"content": heads.get(k, "")} for k in surv_keys]),
    }
    if need_seg:
        _, jpack, _ = judge_candidates(mc, question, fused)
        packs["C-judge-seg"] = jpack[:ANSWER_EVIDENCE_BUDGET]
    else:
        packs["C-judge-seg"] = ""
    return packs, {"n_nogate": len(cand_keys), "n_judge": len(surv_keys)}


def _repair_cells(out: Path, questions: list, args) -> list:
    """Re-run ONLY the arms whose answer or grade failed, in place."""
    mc = L.McpClient()
    repaired = []
    try:
        for item in questions:
            qid = item["qid"]
            cp = out / f"cell_{qid}.json"
            candp = out / f"cand_{qid}.json"
            if not (cp.exists() and candp.exists()):
                continue
            cell = json.loads(cp.read_text(encoding="utf-8"))
            cand = json.loads(candp.read_text(encoding="utf-8"))
            broken = [a for a in ARMS
                      if (cell["arms"].get(a) or {}).get("answer_error")
                      or (cell["arms"].get(a) or {}).get("grade") is None]
            if not broken:
                continue
            packs, _ = rebuild_packs(mc, cell, cand, item["question"],
                                     need_seg="C-judge-seg" in broken)
            for arm in broken:
                a = cell["arms"][arm]
                orig = {"answer_error": a.get("answer_error"),
                        "grade": a.get("grade"), "verdict": a.get("verdict"),
                        "rationale": a.get("rationale")}
                pack = packs[arm]
                if a.get("answer_error") or not a.get("answer"):
                    r = answer(item["question"], pack, args.timeout)
                    a.update({"answer": r.get("answer"),
                              "answer_error": r.get("error"),
                              "answer_latency_s": r.get("latency_s"),
                              "tokens": r.get("tokens"),
                              "total_cost_usd": r.get("total_cost_usd"),
                              "model": r.get("model")})
                g = grade(item, a.get("answer"), min(args.timeout, 300))
                a.update({"grade": g.get("score"), "verdict": g.get("verdict"),
                          "rationale": g.get("rationale"),
                          "grade_latency_s": g.get("grade_latency_s"),
                          "original_failure": orig, "repaired": now_iso()})
                repaired.append({"qid": qid, "arm": arm, "original": orig,
                                 "new_grade": a.get("grade")})
                print(f"[exp11] repaired {qid} {arm}: "
                      f"{orig['rationale']!r} -> grade={a.get('grade')}", flush=True)
            cell["summary"] = _summarize(cell)
            cp.write_text(json.dumps(cell, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    finally:
        mc.close()
    (out / "repairs.json").write_text(
        json.dumps({"repaired": repaired, "generated": now_iso()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return repaired


def _noise_probe(run_dir: Path, questions: list, n: int, args) -> int:
    """Re-answer + re-grade ONE frozen pack n times to measure the noise floor."""
    mc = L.McpClient()
    rows, total = [], 0.0
    try:
        for item in questions:
            qid = item["qid"]
            cp = run_dir / f"cell_{qid}.json"
            candp = run_dir / f"cand_{qid}.json"
            if not (cp.exists() and candp.exists()):
                continue
            cell = json.loads(cp.read_text(encoding="utf-8"))
            cand = json.loads(candp.read_text(encoding="utf-8"))
            packs, chk = rebuild_packs(mc, cell, cand, item["question"])
            pack = packs["C-nogate"]
            expected = (cell["arms"].get("C-nogate") or {}).get("evidence_chars")
            rep = []
            for i in range(n):
                a = answer(item["question"], pack, args.timeout)
                g = grade(item, a.get("answer"), min(args.timeout, 300))
                total += a.get("total_cost_usd") or 0.0
                rep.append({"i": i + 1, "grade": g.get("score"),
                            "verdict": g.get("verdict"),
                            "answer_chars": len(str(a.get("answer") or "")),
                            "answer_head": str(a.get("answer") or "")[:200],
                            "latency_s": a.get("latency_s"), "error": a.get("error")})
                print(f"[exp11] noise {qid} rep{i + 1}/{n}: "
                      f"grade={g.get('score')} {g.get('verdict')}", flush=True)
            rows.append({"qid": qid, "arm": "C-nogate", "pack_chars": len(pack),
                         "pack_sharable_with_original": len(pack) == expected,
                         "grades": [r["grade"] for r in rep], "repeats": rep})
    finally:
        mc.close()
    doc = {"run_dir": str(run_dir), "n_repeats": n, "arm": "C-nogate",
           "questions": rows, "total_cost_usd": round(total, 4),
           "generated": now_iso()}
    (run_dir / "noise_probe.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[exp11] noise probe -> {run_dir / 'noise_probe.json'} "
          f"(${doc['total_cost_usd']})", flush=True)
    return 0


# ─────────────────────────────── main ───────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--questions", default=str(QUESTIONS))
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--skip-warmup", action="store_true")
    ap.add_argument("--repair", default="",
                    help="run dir whose failed answer/grade cells to re-run in place")
    ap.add_argument("--noise-probe", type=int, default=0,
                    help="re-answer+re-grade one frozen pack N times (noise floor)")
    ap.add_argument("--from-run", default="", help="run dir for --noise-probe")
    args = ap.parse_args()

    qfile = Path(args.questions)
    data = json.loads(qfile.read_text(encoding="utf-8"))
    questions = data["questions"][:args.limit]

    if args.noise_probe:
        if not args.from_run:
            ap.error("--noise-probe requires --from-run <run-dir>")
        return _noise_probe(Path(args.from_run), questions, args.noise_probe, args)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"exp11-{stamp}"
    if args.repair:
        out = Path(args.repair)
    elif args.out:
        out = Path(args.out)
        if out.name in ("exp11", "results", ""):  # a parent dir was given
            out = out / run_id
    else:
        out = REPO / "paper-kbs" / "experiments" / "results" / "exp11" / run_id
    out.mkdir(parents=True, exist_ok=True)
    print(f"[exp11] run_dir={out}", flush=True)
    if args.repair:
        rep = _repair_cells(out, questions, args)
        print(f"[exp11] repaired {len(rep)} cell-arm(s)", flush=True)

    mc = L.McpClient()
    meta_env = {}
    try:
        meta_env = {
            "web_token_state": L.check_token()[1],
            "kb_list": [{"kb_id": k.get("kb_id"), "name": k.get("name"),
                         "documentCount": k.get("documentCount")}
                        for k in (mc.call("kb_list", {"lightweight": True},
                                          timeout=120).get("catalog") or [])],
            "mcp_tool_count": None,
        }
    except Exception as exc:  # noqa: BLE001
        meta_env["env_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"

    # ── warm-up: first-touch pays model load / resident-worker spin-up ──
    # NOTE: the gate is fail-closed — a reference to a non-existent document
    # makes it report status="unavailable", so the warm-up MUST use a real
    # document path or it would misreport the engine as down.
    warm = {"done": False, "real_doc": None}
    if not args.skip_warmup:
        t0 = time.time()
        try:
            probe_lib = DOMAIN_LIBS["经济与社会"]
            pc = mc.call("kb_get_documents", {"kb_id": probe_lib, "lightweight": True},
                         timeout=180).get("catalog") or []
            probe_doc = str((pc[0] or {}).get("name") or "") if pc else ""
            warm["real_doc"] = probe_doc
            mc.call("kb_search_vector",
                    {"query": "warmup probe", "kb_id": probe_lib,
                     "top_k": 3, "score_threshold": VEC_THRESH, "slim": True},
                    timeout=600)
            r = mc.call("kb_laya_judge",
                        {"query": "warmup probe",
                         "documents": json.dumps([{"kb_id": probe_lib,
                                                   "doc_path": probe_doc}]),
                         "criterion": "auto", "threshold": JUDGE_THRESHOLD,
                         "max_evidence_chars": 1000, "include_text": False},
                        timeout=1800)
            warm.update({"done": True, "seconds": round(time.time() - t0, 1),
                         "judge_status": r.get("status"),
                         "judge_real_engine": r.get("real_engine"),
                         "judge_engine": r.get("engine"),
                         "judge_backend": r.get("backend"),
                         "judge_errors": r.get("errors") or [],
                         "judge_fetch_errors": r.get("fetch_errors") or []})
        except Exception as exc:  # noqa: BLE001
            warm.update({"done": False, "seconds": round(time.time() - t0, 1),
                         "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
        print(f"[exp11] warmup {warm}", flush=True)

    gidx = gold_index()
    per_q, cells = [], {}

    for item in questions:
        qid = item["qid"]
        qtext = item["question"]
        print(f"[exp11] {qid} …", flush=True)
        cellpath = out / f"cell_{qid}.json"
        if cellpath.exists():
            cell = json.loads(cellpath.read_text(encoding="utf-8"))
            cells[qid] = cell
            per_q.append(cell.get("summary") or _summarize(cell))
            print(f"[exp11]   {qid} cached", flush=True)
            continue

        row = {"qid": qid, "question": qtext, "stratum": item.get("stratum"),
               "field": item.get("field"), "gold_docs": gidx.get(qid) or [],
               "started": now_iso()}
        t_start = time.time()
        try:
            # 1. shared candidate stage (executed ONCE)
            candpath = out / f"cand_{qid}.json"
            if candpath.exists():
                cand = json.loads(candpath.read_text(encoding="utf-8"))
                print(f"[exp11]   {qid} candidate set reused (frozen)", flush=True)
            else:
                vdocs, vtrace = vector_lane(mc, qtext)
                cdocs, ctrace = catalog_lane(mc, qtext)
                fused, ftrace = fuse(vdocs, cdocs)
                heads, htrace = fetch_heads(mc, fused)
                cand = {"qid": qid, "query": qtext, "fused": fused,
                        "fusion_trace": ftrace, "vector_trace": vtrace,
                        "catalog_trace": ctrace, "fetch_trace": htrace,
                        "heads": {"||".join(k): v for k, v in heads.items()},
                        "built": now_iso()}
                candpath.write_text(json.dumps(cand, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
            fused = cand["fused"]
            heads = {tuple(k.split("||", 1)): v for k, v in cand["heads"].items()}
            row["candidate_stage"] = {
                "n_fused": len(fused),
                "fusion_trace": cand["fusion_trace"],
                "vector_trace": cand["vector_trace"],
                "catalog_trace": cand["catalog_trace"],
                "fetch_errors": cand["fetch_trace"]["errors"],
                "candidate_order": [c["doc_path"] for c in fused],
            }

            # 2. resolve the gold document(s) at paper/part granularity
            gold_keys = resolve_gold(mc, gidx.get(qid) or [])
            row["gold_matchable"] = bool(gidx.get(qid))
            row["gold_parts_in_corpus"] = len(gold_keys)
            gold_parts = sorted(p for _, p in gold_keys)
            row["gold_doc_paths"] = gold_parts[:5]

            # 3. the gate
            survivors, judge_pack, jmeta = judge_candidates(mc, qtext, fused)
            row["judge"] = jmeta
            row["judge_survivors"] = [s["doc_path"] for s in survivors]

            # 4. arms
            cand_keys = [(c["kb_id"], c["doc_path"]) for c in fused]
            surv_keys, seen = [], set()
            for s in survivors:
                k = (s["kb_id"], s["doc_path"])
                if k in seen:
                    continue
                seen.add(k)
                if k not in dict.fromkeys(cand_keys):
                    # engine may echo a bare/other path form — try basename match
                    for ck in cand_keys:
                        if basename(ck[1]) == basename(s["doc_path"]):
                            k = ck
                            break
                surv_keys.append(k)

            arm_orders = {
                "C-nogate": cand_keys,
                "C-judge": surv_keys,
                "C-judge-seg": surv_keys,
            }
            arm_packs = {
                "C-nogate": spread_pack([{"content": heads.get(k, "")}
                                         for k in cand_keys]),
                "C-judge": spread_pack([{"content": heads.get(k, "")}
                                        for k in surv_keys]),
                "C-judge-seg": judge_pack[:ANSWER_EVIDENCE_BUDGET],
            }

            row["arms"] = {}
            for arm in ARMS:
                order = arm_orders[arm]
                pack = arm_packs[arm]
                a = answer(qtext, pack, args.timeout)
                g = grade(item, a.get("answer"), min(args.timeout, 300))
                row["arms"][arm] = {
                    "n_docs": len(order),
                    "docs": [p for _, p in order],
                    "gold_rank": (rank_of_gold(order, gold_keys)
                                  if row["gold_matchable"] else None),
                    "gold_survived": (any(k in gold_keys for k in order)
                                      if row["gold_matchable"] else None),
                    "evidence_chars": len(pack),
                    "answer": a.get("answer"),
                    "answer_error": a.get("error"),
                    "answer_latency_s": a.get("latency_s"),
                    "tokens": a.get("tokens"),
                    "total_cost_usd": a.get("total_cost_usd"),
                    "model": a.get("model"),
                    "grade": g.get("score"),
                    "verdict": g.get("verdict"),
                    "rationale": g.get("rationale"),
                    "grade_latency_s": g.get("grade_latency_s"),
                }
                print(f"[exp11]   {qid} {arm}: docs={len(order)} "
                      f"chars={len(pack)} grade={g.get('score')} "
                      f"{a.get('latency_s')}s", flush=True)

            row["wall_clock_s"] = round(time.time() - t_start, 1)
        except Exception as exc:  # noqa: BLE001
            import traceback
            row["fatal_error"] = f"{type(exc).__name__}: {str(exc)[:600]}"
            row["fatal_traceback"] = traceback.format_exc()[-1500:]
            row["wall_clock_s"] = round(time.time() - t_start, 1)
            print(f"[exp11]   {qid} FATAL {row['fatal_error']}", flush=True)

        row["summary"] = _summarize(row)
        cellpath.write_text(json.dumps(row, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        cells[qid] = row
        per_q.append(row["summary"])

    mc.close()

    agg = _aggregate(per_q, cells)
    stamp_doc = {
        "experiment": "E-A verification-gate ablation (end-to-end)",
        "run_id": out.name,
        "generated": now_iso(),
        "protocol": {
            "questions": str(qfile.relative_to(REPO)) if qfile.is_relative_to(REPO) else str(qfile),
            "n_questions": len(questions),
            "corpus": "live 100-paper / 322-part arXiv corpus in 5 content-routed libraries",
            "libraries": DOMAIN_LIBS,
            "candidate_cap": CANDIDATE_CAP,
            "vector_lane": {"tool": "kb_search_vector", "top_k": VEC_TOP_K,
                            "score_threshold": VEC_THRESH, "slim": True,
                            "per_library": True},
            "catalog_lane": {"tools": ["kb_list", "kb_get_documents"],
                             "rank": "query<->(name+description) token overlap"},
            "fusion": "agreed-first, then vector top-8, then catalog top-4, cap 12",
            "gate": {"tool": "kb_laya_judge", "criterion": JUDGE_CRITERION,
                     "threshold": JUDGE_THRESHOLD, "reference_mode": True,
                     "include_text": False},
            "arms": list(ARMS),
            "primary_pair": list(PRIMARY_PAIR),
            "evidence_pack": f"spread_pack(per_doc={PER_DOC}, budget={ANSWER_EVIDENCE_BUDGET})",
            "closing_channel": "chat_tracks.answer_closed_book (engine pinned 'claude' at chat_tracks.py:243, no tools, max_turns=1)",
            "grader": "same LLM grader prompt for all arms (143_e2e_modes_baselines.py:223-233)",
            "deviation_from_plan": ("kb_hybrid_search(enable_judge=...) no longer exists on the "
                                    "live kb-mcp (95 tools, zero matches in kb-mcp/server.py). "
                                    "The ablation was rebuilt around kb_laya_judge applied to a "
                                    "frozen shared candidate set, so the gate is still the only "
                                    "difference between conditions."),
        },
        "environment": meta_env,
        "warmup": warm,
        "aggregate": agg,
        "per_question": per_q,
    }
    aggpath = out / "exp11_gate_ablation.json"
    aggpath.write_text(json.dumps(stamp_doc, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    # brief requires the aggregate at a stable top-level path too
    top = REPO / "paper-kbs" / "experiments" / "results" / "exp11_gate_ablation.json"
    top.write_text(json.dumps(stamp_doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[exp11] wrote {aggpath}", flush=True)
    print(f"[exp11] wrote {top}", flush=True)
    _print_aggregate(agg)
    return 0


def _summarize(row: dict) -> dict:
    if row.get("fatal_error"):
        return {"qid": row["qid"], "fatal_error": row["fatal_error"]}
    s = {"qid": row["qid"], "stratum": row.get("stratum"),
         "gold_matchable": row.get("gold_matchable"),
         "n_candidates": row["candidate_stage"]["n_fused"],
         "n_kept": row["judge"].get("survivor_count"),
         "judge_status": row["judge"].get("status"),
         "judge_real_engine": row["judge"].get("real_engine"),
         "judge_scored": row["judge"].get("scored_count"),
         "gold_parts_in_corpus": row.get("gold_parts_in_corpus"),
         "arms": {}}
    for arm, a in (row.get("arms") or {}).items():
        s["arms"][arm] = {"n_docs": a["n_docs"], "gold_rank": a["gold_rank"],
                          "gold_survived": a["gold_survived"],
                          "chars": a["evidence_chars"], "grade": a["grade"],
                          "verdict": a["verdict"],
                          "latency_s": a["answer_latency_s"],
                          "cost_usd": a["total_cost_usd"]}
    return s


def _mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 3) if xs else None


def _aggregate(per_q: list, cells: dict) -> dict:
    ok = [r for r in per_q if not r.get("fatal_error")]
    agg = {"n_questions": len(per_q), "n_ok": len(ok),
           "n_fatal": len(per_q) - len(ok),
           "fatal_qids": [r["qid"] for r in per_q if r.get("fatal_error")],
           "judge_failures": [], "arms": {}}
    total_cost, total_calls = 0.0, 0
    for r in ok:
        if r.get("judge_status") != "ok" or not r.get("judge_real_engine"):
            agg["judge_failures"].append({"qid": r["qid"],
                                          "status": r.get("judge_status"),
                                          "real_engine": r.get("judge_real_engine")})
        for arm, a in (r.get("arms") or {}).items():
            agg["arms"].setdefault(arm, []).append({**a, "qid": r["qid"]})
            if isinstance(a.get("cost_usd"), (int, float)):
                total_cost += a["cost_usd"]
            total_calls += 1
    for arm, rows in agg["arms"].items():
        golds = [r for r in rows if r["gold_survived"] is not None]
        agg["arms"][arm] = {
            "n_cells": len(rows),
            "n_gold_matchable": len(golds),
            "mean_grade_all": _mean([r["grade"] for r in rows]),
            "mean_grade_gold": _mean([r["grade"] for r in golds]),
            "gold_survived_count": sum(1 for r in golds if r["gold_survived"]),
            "gold_rank_mean": _mean([r["gold_rank"] for r in golds]),
            "mean_docs": _mean([r["n_docs"] for r in rows]),
            "mean_chars": _mean([r["chars"] for r in rows]),
            "mean_latency_s": _mean([r["latency_s"] for r in rows]),
            "grades": {r["qid"]: r["grade"] for r in rows},
            "verdicts": {r["qid"]: r["verdict"] for r in rows},
        }
    # paired deltas on the primary pair
    paired = []
    for r in ok:
        a = (r.get("arms") or {}).get("C-nogate")
        b = (r.get("arms") or {}).get("C-judge")
        c = (r.get("arms") or {}).get("C-judge-seg")
        if a and b:
            paired.append({"qid": r["qid"], "nogate": a["grade"], "judge": b["grade"],
                           "judge_seg": (c or {}).get("grade"),
                           "delta": (None if a["grade"] is None or b["grade"] is None
                                     else b["grade"] - a["grade"])})
    agg["paired_primary"] = paired
    agg["paired_mean_delta"] = _mean([p["delta"] for p in paired])
    agg["total_answer_cost_usd"] = round(total_cost, 4)
    agg["total_answer_calls"] = total_calls
    return agg


def _print_aggregate(agg: dict) -> None:
    print("\n[exp11] ── aggregate ──", flush=True)
    for arm, a in agg["arms"].items():
        print(f"  {arm:14s} n={a['n_cells']:2d} mean_grade_all={a['mean_grade_all']} "
              f"mean_grade_gold={a['mean_grade_gold']} gold_survived="
              f"{a['gold_survived_count']}/{a['n_gold_matchable']} "
              f"gold_rank_mean={a['gold_rank_mean']} docs={a['mean_docs']} "
              f"chars={a['mean_chars']} lat={a['mean_latency_s']}s", flush=True)
    print(f"  paired mean delta (judge - nogate) = {agg['paired_mean_delta']}", flush=True)
    print(f"  judge failures: {agg['judge_failures']}", flush=True)
    print(f"  total answer cost usd = {agg['total_answer_cost_usd']}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
