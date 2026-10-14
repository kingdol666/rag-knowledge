#!/usr/bin/env python
"""exp12_partition_ablation.py — E-B: organization/partitioning ablation on the LIVE corpus.

PURPOSE
-------
Measure the retrieval cost/benefit of the paper's organization design — the
content-routed 5-library partition — without rebuilding or re-routing anything.
Everything below is READ-ONLY: query / search / read only. No create, update,
delete, move, re-index, re-tag, re-parse, graph build or meditation call.

PROTOCOL AS EXECUTED
--------------------
1. For each of the 10 questions of ``qa_quick10.json`` the gold document(s) are
   mapped, at paper (arXiv-id) granularity, to the live library that actually
   contains them, via ``kb_get_documents(lightweight=True)`` over the 5 domain
   libraries (same mapping helper E-A uses).

2. Four retrieval conditions per question. The first three are executed in ONE
   tool family — ``kb_search_vector`` — with byte-identical arguments except
   ``kb_id``, so search SCOPE is the only thing that differs:
     pinned-gold  kb_search_vector(query, kb_id=<gold's own library>,   top_k=10)
     pinned-other kb_search_vector(query, kb_id=<deterministic other lib>, top_k=10)
     flat         kb_search_vector(query, kb_id="",                     top_k=10)
     catalog-only kb_list + kb_get_documents(lightweight=True) across all 5
                  libraries, documents ranked by query<->description token
                  overlap (the discovery path the partition is meant to buy)
   ``score_threshold=0.0`` in all three vector conditions so that an empty
   result means "the scope genuinely has nothing", never "the threshold cut it".
   ``pinned-other`` picks the library that follows the gold library in a
   deterministic ordering of the five library NAMES (sorted by Unicode code
   point), wrapping around — i.e. the cost of a single routing mistake.

3. Per condition we record: raw chunk hits, document-level candidates,
   gold hit@5 / hit@10, gold rank (first rank at which ANY part of the gold
   arXiv id appears), latency, and the number of documents the content-
   verification gate (``kb_laya_judge``, threshold 0.5) keeps from that
   condition's candidate set.

4. Environment ground truth, each tied to the exact call that produced it:
     (a) naming convention inside the live libraries — do document names still
         carry the ``{domain}__`` topical prefix (a label leak), and how many
         carry the double ``.md`` artefact;
     (b) per-library document counts;
     (c) router assignment vs filename topical prefix, over the WHOLE corpus
         (all parts, far above the required sample of 30).

USAGE
-----
  python paper-kbs/experiments/exp12_partition_ablation.py \
      --out paper-kbs/experiments/results/exp12/<run-id>
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
for _p in (SUITE, SUITE / "experiments", SUITE / "scripts", str(Path(__file__).resolve().parent)):
    sys.path.insert(0, str(_p))

import lib as L  # noqa: E402  (benchmark-suite/scripts/lib.py)

# reuse E-A's primitives instead of re-implementing them
from exp11_gate_ablation import (  # noqa: E402
    DOMAIN_LIBS, LIB_BY_ID, basename, norm_path, tokenize,
)

QUESTIONS = SUITE / "data" / "papers" / "qa_quick10.json"
PAPERS_DIR = SUITE / "data" / "papers"
CANDIDATE_CAP = 12          # same gate-input cap as E-A
TOP_K = 10                  # 10 chunks/scope -> hit@5 / hit@10 are well defined
GATE_THRESHOLD = 0.5
GATE_CRITERION = "auto"
CONDITIONS = ("pinned-gold", "pinned-other", "flat", "catalog-only")
ARXIV_RE = re.compile(r"__(\d{4}\.\d{4,5})__")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def arxiv_of(path: str) -> str | None:
    m = ARXIV_RE.search(norm_path(path))
    return m.group(1) if m else None


def prefix_of(path: str) -> str | None:
    """Topical filename prefix, i.e. the token before the first ``__``."""
    b = basename(path)
    return b.split("__", 1)[0] if "__" in b else None


def lib_order() -> list:
    """Deterministic ordering of the five library names (Unicode code point)."""
    return sorted(DOMAIN_LIBS.keys())


def other_lib(gold_lib: str) -> str:
    order = lib_order()
    i = order.index(gold_lib)
    return order[(i + 1) % len(order)]


# ───────────────────────────── catalog (fetched once) ─────────────────────────────
def load_catalog(mc) -> dict:
    """Per-library document inventory + the library records themselves.

    Exact calls: kb_list(lightweight=True) once, then
                 kb_get_documents(kb_id=<lib>, lightweight=True) once per library.
    """
    t0 = time.time()
    libs = []
    raw = mc.call("kb_list", {"lightweight": True}, timeout=120)
    for k in (raw.get("catalog") or []):
        libs.append({"kb_id": k.get("kb_id"), "name": k.get("name"),
                     "description": k.get("description"),
                     "documentCount": k.get("documentCount")})
    per_lib, docs = {}, []
    for name, kid in DOMAIN_LIBS.items():
        r = mc.call("kb_get_documents", {"kb_id": kid, "lightweight": True}, timeout=180)
        cat = r.get("catalog") or []
        per_lib[name] = len(cat)
        for d in cat:
            dp = norm_path(d.get("doc_path"))
            if not dp:
                continue
            docs.append({
                "kb_id": kid, "library": name, "doc_path": dp,
                "name": str(d.get("name") or ""),
                "description": str(d.get("description") or ""),
                "arxiv_id": arxiv_of(dp), "prefix": prefix_of(dp),
                "double_md": basename(dp).count(".md") > 1,
                "prefix_leak": "__" in basename(dp),
            })
    return {"libs": libs, "per_lib_counts": per_lib, "docs": docs,
            "seconds": round(time.time() - t0, 1)}


# ───────────────────────────── retrieval conditions ─────────────────────────────
def vector_scope(mc, query: str, kb_id: str) -> dict:
    t0 = time.time()
    r = mc.call("kb_search_vector",
                {"query": query, "kb_id": kb_id, "top_k": TOP_K,
                 "score_threshold": 0.0, "slim": True}, timeout=300)
    hits = r.get("results") or []
    order, best = [], {}
    for h in hits:
        dp = norm_path(h.get("doc_path"))
        if not dp:
            continue
        if dp not in best:
            best[dp] = {"doc_path": dp, "kb_id": h.get("kb_id") or kb_id,
                        "score": float(h.get("score") or 0.0), "n_chunks": 0,
                        "chunks": []}
            order.append(dp)
        best[dp]["n_chunks"] += 1
        best[dp]["score"] = max(best[dp]["score"], float(h.get("score") or 0.0))
        best[dp]["chunks"].append(float(h.get("score") or 0.0))
    docs = [best[k] for k in order]          # server order = score order
    for i, d in enumerate(docs):
        d["rank"] = i + 1
    return {"condition": "vector", "kb_id": kb_id, "raw_chunk_hits": len(hits),
            "n_candidates": len(docs), "docs": docs,
            "seconds": round(time.time() - t0, 1),
            "error": r.get("error") if isinstance(r, dict) else None}


def catalog_rank(catalog: dict, query: str) -> dict:
    """Description-overlap ranking of documents, plus library-level routing rank."""
    t0 = time.time()
    q_terms = tokenize(query)
    rows = []
    for d in catalog["docs"]:
        ov = len(q_terms & tokenize(d["name"] + " " + d["description"]))
        rows.append({**d, "overlap": ov})
    rows.sort(key=lambda d: (-d["overlap"], d["doc_path"]))
    rows = [r for r in rows if r["overlap"] > 0]
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    # library-level routing: which library would the catalog point at?
    lib_scores = {}
    for lib in DOMAIN_LIBS:
        rec = next((x for x in catalog["libs"] if x["name"] == lib), {})
        lib_ov = len(q_terms & tokenize(f"{lib} {rec.get('description') or ''}"))
        doc_ov = max([r["overlap"] for r in rows if r["library"] == lib] or [0])
        lib_scores[lib] = {"lib_desc_overlap": lib_ov, "best_doc_overlap": doc_ov}
    order_desc = sorted(DOMAIN_LIBS, key=lambda x: -lib_scores[x]["lib_desc_overlap"])
    order_doc = sorted(DOMAIN_LIBS, key=lambda x: (-lib_scores[x]["best_doc_overlap"], x))
    return {"condition": "catalog-only", "n_candidates": len(rows), "docs": rows,
            "lib_routing": {"scores": lib_scores,
                            "order_by_lib_description": order_desc,
                            "order_by_best_doc_overlap": order_doc},
            "seconds": round(time.time() - t0, 1)}


def gate_keep(mc, query: str, docs) -> dict:
    """kb_laya_judge in reference mode over the condition's candidates (cap 12)."""
    t0 = time.time()
    refs = [{"kb_id": d["kb_id"], "doc_path": d["doc_path"]}
            for d in docs[:CANDIDATE_CAP]]
    if not refs:
        return {"status": "skipped", "reason": "no candidates",
                "candidate_docs": 0, "kept_docs": 0, "kept_refs": [],
                "seconds": 0.0}
    try:
        r = mc.call("kb_laya_judge",
                    {"query": query, "documents": json.dumps(refs),
                     "criterion": GATE_CRITERION, "threshold": GATE_THRESHOLD,
                     "max_evidence_chars": 4000, "include_text": False},
                    timeout=1800)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                "candidate_docs": len(refs), "kept_docs": None, "kept_refs": [],
                "seconds": round(time.time() - t0, 1)}
    kept, seen = [], set()
    for s in (r.get("survivors") or []):
        dp = norm_path(s.get("doc_path"))
        if dp in seen:
            continue
        seen.add(dp)
        kept.append(dp)
    return {"status": r.get("status"), "real_engine": r.get("real_engine"),
            "candidate_docs": len(refs), "scored_count": r.get("scored_count"),
            "survivor_count": r.get("survivor_count"),
            "docs_with_yes": r.get("docs_with_yes"),
            "kept_docs": len(kept), "kept_refs": kept,
            "fetch_errors": r.get("fetch_errors") or [],
            "errors": r.get("errors") or [],
            "seconds": round(time.time() - t0, 1)}


# ───────────────────────────── ground-truth observations ─────────────────────────────
def observe_naming(catalog: dict) -> dict:
    docs = catalog["docs"]
    n = len(docs)
    leak = sum(1 for d in docs if d["prefix_leak"])
    dbl = sum(1 for d in docs if d["double_md"])
    prefixes = collections.Counter(d["prefix"] for d in docs)
    by_lib = collections.Counter(d["library"] for d in docs if d["prefix_leak"])
    return {
        "exact_call": "kb_get_documents(kb_id=<each of 5 libraries>, lightweight=True)",
        "n_document_parts": n,
        "parts_with_domain_double_underscore_prefix": leak,
        "prefix_leak_fraction": round(leak / n, 4) if n else None,
        "parts_with_double_md_suffix": dbl,
        "double_md_examples": [d["doc_path"] for d in docs if d["double_md"]][:5],
        "distinct_prefixes": len(prefixes),
        "prefix_histogram": dict(prefixes.most_common()),
        "prefix_leak_per_library": dict(by_lib),
        "sample_doc_paths": [d["doc_path"] for d in docs[:8]],
    }


def observe_router(catalog: dict) -> dict:
    """Router assignment (live library) vs filename topical prefix, whole corpus."""
    papers = {}
    for d in catalog["docs"]:
        if not d["arxiv_id"]:
            continue
        p = papers.setdefault(d["arxiv_id"], {"prefix": d["prefix"],
                                              "libraries": set(), "parts": 0})
        p["libraries"].add(d["library"])
        p["parts"] += 1
    contingency = collections.defaultdict(collections.Counter)
    for d in catalog["docs"]:
        contingency[d["prefix"]][d["library"]] += 1

    multi = {pf: dict(c) for pf, c in contingency.items() if len(c) > 1}
    majority = {pf: c.most_common(1)[0][0] for pf, c in contingency.items()}
    paper_rows = [{"arxiv_id": a, "prefix": v["prefix"],
                   "libraries": sorted(v["libraries"]),
                   "n_parts": v["parts"],
                   "matches_majority": (len(v["libraries"]) == 1
                                        and v["libraries"] == {majority.get(v["prefix"])})}
                  for a, v in sorted(papers.items())]
    agree = sum(1 for r in paper_rows if r["matches_majority"])

    # independent cross-check: the routing domain encoded in the source PDF name
    disk = {}
    for p in sorted(PAPERS_DIR.glob("*.pdf")):
        stem = p.name[:-4]
        bits = stem.split("__")
        if len(bits) >= 2:
            disk[bits[1]] = {"disk_domain": bits[0], "file": p.name}
    disk_rows, disk_agree, disk_missing = [], 0, []
    for r in paper_rows:
        e = disk.get(r["arxiv_id"])
        if not e:
            disk_missing.append(r["arxiv_id"])
            continue
        # does the live library correspond 1:1 to the PDF's domain prefix?
        live_prefixes = sorted({x for x in r["libraries"]})
        expected = {majority.get(live_prefixes[0])} if live_prefixes else set()
        ok = bool(expected) and live_prefixes == [x for x in live_prefixes] \
            and r["libraries"] != [] and len(r["libraries"]) == 1
        disk_rows.append({"arxiv_id": r["arxiv_id"], "disk_domain": e["disk_domain"],
                          "live_prefix": r["prefix"], "live_library": r["libraries"],
                          "domain_matches_prefix": e["disk_domain"] == r["prefix"],
                          "single_library": len(r["libraries"]) == 1})
        disk_agree += 1 if (e["disk_domain"] == r["prefix"]
                            and len(r["libraries"]) == 1) else 0
    return {
        "exact_call": "kb_get_documents(kb_id=<each of 5 libraries>, lightweight=True)"
                      " + glob(benchmark-suite/data/papers/*.pdf)",
        "n_parts_sampled": len(catalog["docs"]),
        "n_papers": len(paper_rows),
        "prefix_to_library_contingency": {k: dict(v) for k, v in sorted(contingency.items())},
        "prefixes_spanning_multiple_libraries": multi,
        "papers_matching_majority_library": agree,
        "papers_total": len(paper_rows),
        "paper_agreement_fraction": round(agree / len(paper_rows), 4) if paper_rows else None,
        "disk_cross_check": {"checked": len(disk_rows), "agree": disk_agree,
                             "missing_on_disk": disk_missing,
                             "rows": disk_rows},
    }


def summarise(cell: dict) -> dict:
    gold = cell["gold_libraries"]
    out = {"qid": cell["qid"], "gold_arxiv": cell["gold_arxiv"],
          "gold_libraries": gold, "rows": {},
          "catalog_routing": cell.get("catalog_routing")}
    for cond in CONDITIONS:
        c = cell["conditions"].get(cond) or {}
        if not c:
            out["rows"][cond] = {"n_candidates": None, "raw_chunk_hits": None,
                                 "gold_rank": None, "hit@5": False, "hit@10": False,
                                 "kept_after_gate": None, "gate_status": "absent",
                                 "latency_s": None}
            continue
        g = c.get("gate") or {}
        docs = c.get("docs") or []
        if cond == "catalog-only":
            gold_keys = set()
            for lib in gold:
                gold_keys |= {d["doc_path"] for d in docs
                              if d["library"] == lib and d["arxiv_id"] in cell["gold_arxiv"]}
        else:
            gold_keys = {d["doc_path"] for d in docs
                         if d.get("arxiv_id") in cell["gold_arxiv"]}
        ranks = [d["rank"] for d in docs if d["doc_path"] in gold_keys]
        rank = min(ranks) if ranks else None
        out["rows"][cond] = {
            "n_candidates": c.get("n_candidates"),
            "raw_chunk_hits": c.get("raw_chunk_hits"),
            "gold_rank": rank,
            "hit@5": bool(rank is not None and rank <= 5),
            "hit@10": bool(rank is not None and rank <= 10),
            "kept_after_gate": g.get("kept_docs"),
            "gate_status": g.get("status"),
            "latency_s": c.get("seconds"),
        }
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def _rate(xs):
    return round(sum(1 for x in xs if x) / len(xs), 3) if xs else None


def aggregate(per_q, catalog, naming, router) -> dict:
    # Questions whose gold document is NOT in the corpus at all (the
    # unanswerable / out-of-corpus strata) cannot be scored as retrieval hits
    # OR misses — they are excluded from the graded denominators and counted
    # separately, so the raw all-question rate is reported next to them.
    graded = [q for q in per_q if q["gold_libraries"]]
    ungraded = [q["qid"] for q in per_q if not q["gold_libraries"]]
    agg = {"n_questions": len(per_q),
           "n_graded_gold_in_corpus": len(graded),
           "n_excluded_gold_not_in_corpus": len(ungraded),
           "excluded_qids": ungraded,
           "conditions": {}}
    for cond in CONDITIONS:
        rows = [q["rows"][cond] for q in per_q]
        grows = [q["rows"][cond] for q in graded]
        agg["conditions"][cond] = {
            "n_all_questions": len(rows),
            "n_graded": len(grows),
            "hit@5_rate": _rate([r["hit@5"] for r in grows]),
            "hit@10_rate": _rate([r["hit@10"] for r in grows]),
            "hit@5_rate_all_questions_incl_ungraded_as_miss":
                _rate([r["hit@5"] for r in rows]),
            "hit@10_rate_all_questions_incl_ungraded_as_miss":
                _rate([r["hit@10"] for r in rows]),
            "gold_rank_mean": _mean([r["gold_rank"] for r in grows]),
            "gold_rank_per_question": {q["qid"]: q["rows"][cond]["gold_rank"]
                                       for q in per_q},
            "n_candidates_mean": _mean([r["n_candidates"] for r in rows]),
            "kept_after_gate_mean": _mean([r["kept_after_gate"] for r in rows]),
            "latency_s_mean": _mean([r["latency_s"] for r in rows]),
        }
    # routing accuracy of the catalog lane
    routes, routed_n = 0, 0
    for q in per_q:
        src = q.get("catalog_routing") or {}
        if not src:
            continue
        for g in q["gold_libraries"]:
            routed_n += 1
            if src["order_by_lib_description"][:1] == [g] or \
               src["order_by_best_doc_overlap"][:1] == [g]:
                routes += 1
    agg["catalog_library_top1_routing"] = {"hits": routes, "n": routed_n}
    agg["environment"] = {"naming": naming, "router": {
        k: v for k, v in router.items() if k != "prefix_to_library_contingency"},
        "per_lib_counts": catalog["per_lib_counts"]}
    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--questions", default=str(QUESTIONS))
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--skip-gate", action="store_true")
    ap.add_argument("--reaggregate", default="",
                    help="rebuild aggregate.json from frozen cell_*.json (no API calls)")
    args = ap.parse_args()

    data = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    questions = data["questions"][:args.limit]

    if args.reaggregate:
        out = Path(args.reaggregate)
        prev = json.loads((out / "aggregate.json").read_text(encoding="utf-8"))
        cells = []
        for item in questions:
            p = out / f"cell_{item['qid']}.json"
            if p.exists():
                cells.append(json.loads(p.read_text(encoding="utf-8")))
        per_q = [summarise(c) for c in cells]
        naming = json.loads((out / "env_naming.json").read_text(encoding="utf-8"))
        router = json.loads((out / "env_router_vs_prefix.json").read_text(encoding="utf-8"))
        agg = aggregate(per_q, {"per_lib_counts":
                                prev["environment"]["per_lib_counts"]}, naming, router)
        agg.update({"run_id": out.name, "started": prev.get("started"),
                    "reaggregated": now_iso(), "wall_clock_s": prev.get("wall_clock_s"),
                    "n_questions": len(questions), "per_question": per_q,
                    "protocol_deviations": prev.get("protocol_deviations") or [],
                    "failures": prev.get("failures") or []})
        (out / "aggregate.json").write_text(
            json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
        target = REPO / "paper-kbs" / "experiments" / "results" / \
            "exp12_partition_ablation.json"
        target.write_text(json.dumps(agg, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"[exp12] reaggregated {len(per_q)} cells -> {target}", flush=True)
        for cond in CONDITIONS:
            a = agg["conditions"][cond]
            print(f"  {cond:13s} n_graded={a['n_graded']} hit@5={a['hit@5_rate']} "
                  f"hit@10={a['hit@10_rate']} rank_mean={a['gold_rank_mean']} "
                  f"cands={a['n_candidates_mean']} kept={a['kept_after_gate_mean']} "
                  f"lat={a['latency_s_mean']}", flush=True)
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"exp12-{stamp}"
    out = Path(args.out) if args.out else (
        REPO / "paper-kbs" / "experiments" / "results" / "exp12" / run_id)
    if out.name in ("exp12", "results", ""):
        out = out / run_id
    out.mkdir(parents=True, exist_ok=True)
    print(f"[exp12] run_dir={out}", flush=True)

    mc = L.McpClient()
    rec = {"experiment": "E-B partition ablation", "run_id": run_id,
           "started": now_iso(), "n_questions": len(questions),
           "conditions": list(CONDITIONS), "top_k": TOP_K,
           "gate": {"tool": "kb_laya_judge", "threshold": GATE_THRESHOLD,
                    "criterion": GATE_CRITERION, "candidate_cap": CANDIDATE_CAP},
           "protocol_deviations": [], "failures": []}

    t_all = time.time()
    catalog = load_catalog(mc)
    rec["web_token_state"] = L.check_token()[1]
    rec["catalog_meta"] = {"per_lib_counts": catalog["per_lib_counts"],
                           "n_parts": len(catalog["docs"]),
                           "seconds": catalog["seconds"]}
    print(f"[exp12] catalog parts={len(catalog['docs'])} "
          f"per_lib={catalog['per_lib_counts']}", flush=True)

    naming = observe_naming(catalog)
    router = observe_router(catalog)
    rec["observation_a_naming"] = naming
    rec["observation_b_counts"] = {
        "exact_call": "kb_get_documents(kb_id=<lib>, lightweight=True)",
        **catalog["per_lib_counts"]}
    rec["observation_c_router_vs_prefix"] = {
        k: v for k, v in router.items() if k != "prefix_to_library_contingency"}
    (out / "env_naming.json").write_text(
        json.dumps(naming, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "env_router_vs_prefix.json").write_text(
        json.dumps(router, ensure_ascii=False, indent=2), encoding="utf-8")

    per_q = []
    for item in questions:
        qid = item["qid"]
        qtext = item["question"]
        gold_arxiv = {str(g).lower() for g in (item.get("gold_docs") or [])}
        libs = sorted({d["library"] for d in catalog["docs"]
                       if d["arxiv_id"] in gold_arxiv})
        cell = {"qid": qid, "question": qtext, "stratum": item.get("stratum"),
                "answerable": item.get("answerable"), "routed_kb": item.get("routed_kb"),
                "gold_arxiv": sorted(gold_arxiv), "gold_libraries": libs,
                "conditions": {}}

        if not libs:
            rec["failures"].append({"qid": qid, "where": "gold-resolution",
                                    "error": "gold arXiv id not found in any library"})
            print(f"[exp12] {qid} GOLD NOT FOUND {sorted(gold_arxiv)}", flush=True)
            cell["conditions"] = {}
            per_q.append(summarise(cell))
            (out / f"cell_{qid}.json").write_text(
                json.dumps(cell, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        gold_lib = libs[0]
        oth = other_lib(gold_lib)
        cell["pinned_other_library"] = oth
        cell["pinned_other_rule"] = ("library following the gold library in "
                                     "sorted(library names) order, wrapping around")

        scopes = {"pinned-gold": DOMAIN_LIBS[gold_lib],
                  "pinned-other": DOMAIN_LIBS[oth],
                  "flat": ""}
        for cond, kid in scopes.items():
            try:
                r = vector_scope(mc, qtext, kid)
            except Exception as exc:  # noqa: BLE001
                r = {"condition": "vector", "kb_id": kid, "raw_chunk_hits": None,
                     "n_candidates": None, "docs": [], "seconds": None,
                     "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
                rec["failures"].append({"qid": qid, "where": cond,
                                        "error": r["error"]})
            for d in r["docs"]:
                d["arxiv_id"] = arxiv_of(d["doc_path"])
                d["prefix"] = prefix_of(d["doc_path"])
            r["gate"] = ({"status": "skipped"} if args.skip_gate
                         else gate_keep(mc, qtext, r["docs"]))
            cell["conditions"][cond] = r

        cat = catalog_rank(catalog, qtext)
        cat["gate"] = ({"status": "skipped"} if args.skip_gate
                       else gate_keep(mc, qtext, cat["docs"]))
        cell["conditions"]["catalog-only"] = cat
        cell["catalog_routing"] = cat["lib_routing"]

        s = summarise(cell)
        per_q.append(s)
        (out / f"cell_{qid}.json").write_text(
            json.dumps(cell, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[exp12] {qid} gold_lib={gold_lib} other={oth} "
              + " ".join(f"{c}:{s['rows'][c]['gold_rank']}/{s['rows'][c]['kept_after_gate']}"
                         for c in CONDITIONS), flush=True)

    agg = aggregate(per_q, catalog, naming, router)
    agg.update({"run_id": run_id, "started": rec["started"],
                "finished": now_iso(), "wall_clock_s": round(time.time() - t_all, 1),
                "n_questions": len(questions), "per_question": per_q,
                "protocol_deviations": rec["protocol_deviations"],
                "failures": rec["failures"]})
    (out / "aggregate.json").write_text(
        json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    target = REPO / "paper-kbs" / "experiments" / "results" / "exp12_partition_ablation.json"
    target.write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[exp12] wrote {target} ({agg['wall_clock_s']}s)", flush=True)
    for cond in CONDITIONS:
        a = agg["conditions"][cond]
        print(f"  {cond:13s} n_graded={a['n_graded']} hit@5={a['hit@5_rate']} "
              f"hit@10={a['hit@10_rate']} "
              f"rank_mean={a['gold_rank_mean']} cands={a['n_candidates_mean']} "
              f"kept={a['kept_after_gate_mean']} lat={a['latency_s_mean']}s", flush=True)
    print(f"  router: papers_matching_majority="
          f"{agg['environment']['router'].get('paper_agreement_fraction')} "
          f"multi_lib_prefixes="
          f"{list(agg['environment']['router'].get('prefixes_spanning_multiple_libraries', {}))}",
          flush=True)
    print(f"  naming: prefix_leak_fraction="
          f"{naming['prefix_leak_fraction']} double_md={naming['parts_with_double_md_suffix']}",
          flush=True)
    print(f"  failures={len(rec['failures'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
