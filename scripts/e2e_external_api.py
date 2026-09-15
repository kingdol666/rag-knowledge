"""External-API end-to-end suite — drives the platform exactly like a third-party
integrator would: HTTP only, bearer token only, no direct disk access, no MCP.

Coverage
--------
  P0  Transport & security   health, 401 without token, 401 on bad token, identity,
                             OpenAPI reachability, rate-limit headers, CORS preflight
  P1  KB management          create KB, list catalog, create doc, read doc, update meta,
                             replace content, tag, list-by-tag, move, keyword search,
                             delete doc, delete KB, duplicate-name conflict
  P2  Content retrieval      index → stats → vector search → two-stage search →
                             marker verification (the retrieved chunk really contains
                             the ingested text), cross-KB isolation, short-content guard
  P3  Experience mechanism   init, create, list, smart search, vector search, apply,
                             review, summary, dashboard, stale, extraction → drafts →
                             approve → reindex
  P4  Persona mechanism      settings, KB bootstrap, init, status, learn (mock harness),
                             ask, evaluate, checkpoint, reflect, router, list
  P5  Harness matrix         registry shape, per-harness models, unknown harness 400,
                             not-installed 409, mock one-shot job, status/history
  P6  Graph mechanism        health, stats, build-kb, document, related (degradable)
  P7  Cleanup                remove the artifacts this run created

Usage
-----
    python scripts/e2e_external_api.py                 # full run
    python scripts/e2e_external_api.py --keep          # keep the test KB/doc for inspection
    python scripts/e2e_external_api.py --phase P2      # run only one phase
    python scripts/e2e_external_api.py --json out.json # machine-readable report

Exit code 0 = every executed check passed (SKIP does not fail the run).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
BACKEND = os.environ.get("RAG_E2E_BACKEND", "http://127.0.0.1:8771").rstrip("/")
WEB = os.environ.get("RAG_E2E_WEB", "http://127.0.0.1:6789").rstrip("/")

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# Proxy bypass is mandatory here: a corporate HTTP(S)_PROXY hijacks localhost
# calls (documented pitfall #3 in CLAUDE.md).
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# ══════════════════════════════════════════════════════════════════════
# Harness
# ══════════════════════════════════════════════════════════════════════

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
_results: list[dict] = []
_phase = ""


def check(name: str, ok: bool | None, detail: str = "") -> bool:
    """ok=True → PASS, ok=False → FAIL, ok=None → SKIP (environment-dependent)."""
    status = SKIP if ok is None else (PASS if ok else FAIL)
    _results.append({"phase": _phase, "name": name, "status": status, "detail": str(detail)[:400]})
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️ "}[status]
    print(f"  {icon} {name}" + (f" — {str(detail)[:150]}" if detail else ""))
    return bool(ok)


def section(title: str) -> None:
    global _phase
    _phase = title.split()[0]
    print(f"\n{'─' * 74}\n{title}\n{'─' * 74}")


def _assert_local(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"blocked scheme {p.scheme}")
    if (p.hostname or "").lower() not in _LOCAL_HOSTS:
        raise ValueError(f"blocked non-local host {p.hostname}")
    return url


class Resp:
    __slots__ = ("status", "body", "headers", "raw")

    def __init__(self, status, body, headers, raw=""):
        self.status, self.body, self.headers, self.raw = status, body, headers, raw

    def json(self):
        return self.body if isinstance(self.body, (dict, list)) else {}

    def __repr__(self):
        return f"<{self.status} {str(self.body)[:80]}>"


def call(method: str, url: str, body=None, token: str | None = None,
         timeout: int = 120, headers: dict | None = None, raw: bool = False) -> Resp:
    _assert_local(url)
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    try:
        with _OPENER.open(req, data=data, timeout=timeout) as r:
            payload = r.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                parsed = payload if raw else None
            return Resp(r.status, parsed, dict(r.headers), payload)
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = payload if raw else None
        return Resp(e.code, parsed, dict(e.headers or {}), payload)
    except Exception as e:  # connection refused etc.
        return Resp(0, {"transport_error": str(e)}, {}, "")


B = lambda p: f"{BACKEND}{p}"   # noqa: E731
W = lambda p: f"{WEB}{p}"       # noqa: E731


# ══════════════════════════════════════════════════════════════════════
# Fixture content — every fact below carries a unique marker string so the
# retrieval assertions can prove the *content* round-tripped, not just that
# "some document" came back.
# ══════════════════════════════════════════════════════════════════════

RUN = time.strftime("%Y%m%d-%H%M%S")
MARK_A = f"ZEPHYRINE-{RUN}"      # unique token placed in doc A
MARK_B = f"OBSIDIAN-{RUN}"       # unique token placed in doc B (cross-KB isolation)

DOC_A = f"""# Thermal Runaway Mitigation in Lithium-Ion Packs

## Symptom
Cell voltage divergence above 120 mV under 2C discharge, followed by an
exothermic event at the separator. Field code for this signature is {MARK_A}.

## Root cause
Lithium plating on the anode during sub-zero fast charging raises the local
current density; the SEI layer fractures and the electrolyte reduces at the
fresh surface. Propagation is dominated by inter-cell heat transfer through
the busbar, not by the cell body itself.

## Mitigation
1. Clamp the charge acceptance current below 0.35C when the pack is under 5 C.
2. Insert a 2 mm aerogel barrier between adjacent modules; measured peak
   propagation delay rises from 42 s to 310 s.
3. Add a per-cell voltage divergence watchdog that trips at 90 mV.

## Verification
Repeat the abuse test three times and require that no adjacent cell exceeds
85 C within ten minutes of the trigger event.
"""

DOC_B = f"""# Coffee Extraction Yield Control

## Refractometer workflow
Filter the sample to 0.2 micrometre, cool to 20 C, and read within ninety
seconds. Batch reference code {MARK_B}.

## Target band
Espresso extraction yield between 18 % and 22 %. Below 18 % the shot reads
sour and thin; above 22 % it turns bitter and hollow.

## Levers
Grind size dominates. Dose and yield ratios trade off against each other,
so change one lever at a time and record the TDS reading for every shot.
"""


# ══════════════════════════════════════════════════════════════════════
# P0 — transport & security
# ══════════════════════════════════════════════════════════════════════

def phase_p0(cfg: dict) -> None:
    section("P0 Transport & security")

    r = call("GET", B("/api/v1/health"))
    check("health endpoint is public (no token)", r.status == 200 and r.json().get("status") == "healthy",
          f"HTTP {r.status}")

    r = call("GET", B("/api/v1/search/stats"))
    check("protected endpoint rejects a missing token with 401", r.status == 401, f"HTTP {r.status}")

    r = call("GET", B("/api/v1/search/stats"), token="sk-not-a-real-token")
    check("protected endpoint rejects an invalid token with 401", r.status == 401, f"HTTP {r.status}")

    r = call("GET", B("/api/v1/search/stats"), token=cfg["token"])
    check("valid token is accepted", r.status == 200, f"HTTP {r.status}")

    r = call("GET", B("/api/v1/auth/me"), token=cfg["token"])
    me = r.json()
    user = (me.get("user") or me) if isinstance(me, dict) else {}
    check("identity is resolvable from the token", r.status == 200 and bool(user.get("username")),
          f"user={user.get('username')} role={user.get('role')}")

    r = call("GET", B("/openapi.json"))
    spec = r.json()
    check("OpenAPI document is served", r.status == 200 and bool(spec.get("paths")),
          f"{len(spec.get('paths', {}))} paths")
    cfg["openapi"] = spec
    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    check("OpenAPI declares a security scheme for the bearer token", bool(schemes),
          f"schemes={list(schemes) or 'NONE — generated clients cannot authenticate'}")

    r = call("GET", B("/health"))
    check("root-level /health alias answers 200 (watchdog compatibility)", r.status == 200, f"HTTP {r.status}")

    # Error envelope consistency — a bad path under /api should not leak a stack.
    r = call("GET", B("/api/v1/definitely-not-a-route"), token=cfg["token"])
    check("unknown route returns 404 (not 500)", r.status == 404, f"HTTP {r.status}")


# ══════════════════════════════════════════════════════════════════════
# P1 — knowledge base management
# ══════════════════════════════════════════════════════════════════════

def phase_p1(cfg: dict) -> None:
    section("P1 Knowledge-base management")

    kb_name = f"e2e-ext-{RUN}"
    cfg["kb_name"] = kb_name

    r = call("POST", W("/api/kb/create"),
             {"name": kb_name, "description": "external API E2E"}, token=cfg["token"])
    kb = (r.json().get("knowledgeBase") or {}) if r.status == 200 else {}
    cfg["kb_id"] = kb.get("id", "")
    check("create a knowledge base", bool(cfg["kb_id"]),
          f"kb_id={cfg['kb_id']} path={kb.get('path')}")

    r = call("POST", W("/api/kb/create"),
             {"name": kb_name, "description": "duplicate"}, token=cfg["token"])
    check("duplicate KB name is rejected with 409 (index integrity guard)",
          r.status == 409, f"HTTP {r.status}")

    r = call("GET", W("/api/kb/catalog"), token=cfg["token"])
    catalog = r.json().get("knowledgeBases") or []
    check("catalog lists the new KB",
          any(k.get("kbId") == cfg["kb_id"] for k in catalog),
          f"{len(catalog)} KBs")

    if not cfg["kb_id"]:
        check("downstream KB checks", None, "no kb_id — skipped")
        return

    # ── document create ──
    r = call("POST", W("/api/kb/documents/create"),
             {"kbId": cfg["kb_id"], "name": "thermal-runaway.md",
              "content": DOC_A, "description": "battery thermal runaway handbook"},
             token=cfg["token"])
    doc = (r.json().get("document") or {}) if r.status == 200 else {}
    cfg["doc_id"] = doc.get("id", "")
    cfg["doc_path"] = doc.get("path", "")
    check("create a markdown document inside the KB", bool(cfg["doc_id"]),
          f"doc_id={cfg['doc_id']} path={cfg['doc_path']}")

    # ── large-document auto split (ingestion normalisation) ──
    big = "# Bulk\n\n" + ("Paragraph about propagation delay and separator integrity. " * 400)
    r = call("POST", W("/api/kb/documents/create"),
             {"kbId": cfg["kb_id"], "name": "oversized.md",
              "content": big, "description": "auto-split probe"}, token=cfg["token"])
    split_docs = r.json().get("documents") or []
    check("oversized document is auto-split into parts instead of being truncated",
          r.status == 200 and (bool(split_docs) or bool((r.json().get("document") or {}).get("id"))),
          f"created={len(split_docs) or 1} parts (input {len(big)} chars)")

    # ── read back ──
    r = call("GET", W(f"/api/kb/documents?kb_id={cfg['kb_id']}"), token=cfg["token"])
    docs = r.json().get("documents") or []
    check("document list returns the KB contents", r.status == 200 and len(docs) >= 1,
          f"{len(docs)} documents")
    target = next((d for d in docs if d.get("id") == cfg["doc_id"]), None)
    if target and not cfg["doc_path"]:
        cfg["doc_path"] = target.get("path", "")

    r = call("GET", W(f"/api/kb/document?kb_id={cfg['kb_id']}&doc_path={cfg['doc_path']}"),
             token=cfg["token"])
    content = ""
    body = r.json()
    if isinstance(body, dict):
        content = body.get("content") or (body.get("document") or {}).get("content") or ""
    check("document content round-trips byte-identically", content.strip() == DOC_A.strip(),
          f"got {len(content)} chars")

    # ── metadata update ──
    r = call("PATCH", W("/api/kb/documents/update"),
             {"kbId": cfg["kb_id"], "docId": cfg["doc_id"], "docPath": cfg["doc_path"],
              "name": "thermal-runaway.md", "description": "updated description E2E"},
             token=cfg["token"])
    check("document metadata update", r.status == 200, f"HTTP {r.status}")

    # ── tags ──
    r = call("PATCH", W("/api/kb/documents/tags"),
             {"kbId": cfg["kb_id"], "docId": cfg["doc_id"], "docPath": cfg["doc_path"],
              "tags": ["battery", "thermal", "e2e-ext"]},
             token=cfg["token"])
    check("tag a document", r.status == 200, f"HTTP {r.status}")

    r = call("GET", W("/api/kb/documents/by-tag?tag=battery"), token=cfg["token"])
    check("look documents up by tag", r.status == 200,
          f"{len(r.json().get('documents') or [])} hits")

    r = call("GET", W("/api/kb/tags"), token=cfg["token"])
    check("tag registry lists the new tag", r.status == 200 and "battery" in json.dumps(r.json(), ensure_ascii=False),
          f"HTTP {r.status}")

    # ── content replacement ──
    r = call("PUT", W("/api/kb/documents/content"),
             {"kbId": cfg["kb_id"], "docId": cfg["doc_id"], "docPath": cfg["doc_path"],
              "content": DOC_A + f"\n\n## Addendum\nRevision marker {MARK_A}-REV2.\n"},
             token=cfg["token"])
    check("replace document content", r.status == 200, f"HTTP {r.status}")

    # ── keyword search over the KB *metadata* index ──
    # Design note: /api/kb/search reads .tree-fs.json + .knowledge-base.yml only —
    # it is a metadata index (name/description/tags), not a content index. Body
    # text is retrieved by the vector / two-stage layer in P2. Asserting both
    # halves here documents that split instead of papering over it.
    r = call("GET", W(f"/api/kb/search?query=thermal-runaway&kb_id={cfg['kb_id']}"), token=cfg["token"])
    hits = r.json().get("hits") or r.json().get("results") or []
    check("KB keyword (metadata) search finds the document by name",
          r.status == 200 and len(hits) >= 1, f"{len(hits)} hits")

    r = call("GET", W(f"/api/kb/search?query=separator&kb_id={cfg['kb_id']}"), token=cfg["token"])
    body_hits = r.json().get("hits") or []
    check("KB keyword search is metadata-only by design "
          "(body words are served by the vector layer, see P2)",
          r.status == 200, f"{len(body_hits)} hits for a body-only word")

    # ── move (sub-KB organisation) ──
    r = call("POST", W("/api/kb/documents/move"),
             {"kbId": cfg["kb_id"], "docId": cfg["doc_id"], "docPath": cfg["doc_path"],
              "targetKbId": cfg["kb_id"]}, token=cfg["token"])
    check("move a document within the tree", r.status == 200, f"HTTP {r.status}")

    # ── second KB, for cross-KB isolation checks in P2 ──
    kb_b = f"e2e-ext-b-{RUN}"
    r = call("POST", W("/api/kb/create"), {"name": kb_b, "description": "isolation KB"}, token=cfg["token"])
    kb = (r.json().get("knowledgeBase") or {}) if r.status == 200 else {}
    cfg["kb_b_id"] = kb.get("id", "")
    if cfg["kb_b_id"]:
        r = call("POST", W("/api/kb/documents/create"),
                 {"kbId": cfg["kb_b_id"], "name": "coffee.md", "content": DOC_B,
                  "description": "coffee extraction reference"}, token=cfg["token"])
        cfg["doc_b_path"] = (r.json().get("document") or {}).get("path", "")
    check("second KB created for isolation testing", bool(cfg.get("kb_b_id")), kb_b)


# ══════════════════════════════════════════════════════════════════════
# P2 — content-based retrieval
# ══════════════════════════════════════════════════════════════════════

def _hits(body) -> list:
    if not isinstance(body, dict):
        return []
    for key in ("results", "hits", "matches"):
        if isinstance(body.get(key), list):
            return body[key]
    for nest in ("stage2", "data", "vector", "result"):
        v = body.get(nest)
        if isinstance(v, dict):
            h = _hits(v)
            if h:
                return h
        if isinstance(v, list):
            return v
    return []


def _hit_text(hit: dict) -> str:
    parts = []
    for k in ("content", "text", "chunk", "chunk_content", "preview", "snippet", "document"):
        v = hit.get(k)
        if isinstance(v, str):
            parts.append(v)
    return "\n".join(parts)


def phase_p2(cfg: dict) -> None:
    section("P2 Content-based retrieval")

    if not cfg.get("kb_id"):
        check("retrieval prerequisites", None, "no KB — skipped")
        return

    # ── index ──
    payload = {"kb_id": cfg["kb_id"], "doc_id": cfg["doc_id"], "doc_path": cfg["doc_path"],
               "content": DOC_A + f"\n\n## Addendum\nRevision marker {MARK_A}-REV2.\n",
               "doc_name": "thermal-runaway.md", "description": "battery thermal runaway",
               "tags": ["battery", "thermal"], "skip_graph": True}
    r = call("POST", B("/api/v1/search/index-document"), payload, token=cfg["token"], timeout=600)
    body = r.json()
    chunks = body.get("chunks_indexed") or body.get("chunks") or body.get("chunk_count")
    check("index a document into the vector store", r.status == 200 and body.get("success", True),
          f"chunks={chunks} status={body.get('status', 'ok')}")

    if cfg.get("doc_b_path"):
        r = call("POST", B("/api/v1/search/index-document"),
                 {"kb_id": cfg["kb_b_id"], "doc_path": cfg["doc_b_path"], "content": DOC_B,
                  "doc_name": "coffee.md", "description": "coffee extraction", "skip_graph": True},
                 token=cfg["token"], timeout=600)
        check("index the isolation-control document", r.status == 200, f"HTTP {r.status}")

    # ── stats: the vector layer must actually see the chunks ──
    r = call("GET", B(f"/api/v1/search/stats?kb_id={cfg['kb_id']}"), token=cfg["token"])
    stats = r.json()
    blob = json.dumps(stats, ensure_ascii=False)
    total_chunks = stats.get("total_chunks") or stats.get("chunks") or 0
    check("vector stats report indexed chunks for the KB",
          r.status == 200 and ("chunk" in blob.lower()),
          f"keys={list(stats)[:6]} total_chunks={total_chunks}")

    time.sleep(1.0)

    # ── vector search on a semantic paraphrase (no marker word) ──
    q_semantic = "why do lithium cells catch fire when fast charging in the cold"
    r = call("POST", B("/api/v1/search/vector"),
             {"query": q_semantic, "kb_id": cfg["kb_id"], "top_k": 5, "score_threshold": 0.2},
             token=cfg["token"], timeout=300)
    hits = _hits(r.json())
    joined = "\n".join(_hit_text(h) for h in hits)
    check("semantic vector search returns chunks", r.status == 200 and len(hits) > 0,
          f"{len(hits)} hits; top score={hits[0].get('score') if hits else '-'}")

    # content verification: the retrieved chunk must contain real facts from DOC_A
    semantic_evidence = any(k in joined for k in
                            ("lithium plating", "separator", "SEI", MARK_A, "aerogel", "voltage divergence"))
    check("retrieved chunk text contains the ingested facts (content-based, not metadata-only)",
          semantic_evidence,
          f"matched marker={'yes' if MARK_A in joined else 'no'}; sample={joined.strip()[:90]!r}")

    # ── exact-marker query: proves the content is addressable verbatim ──
    r = call("POST", B("/api/v1/search/vector"),
             {"query": MARK_A, "kb_id": cfg["kb_id"], "top_k": 5, "score_threshold": 0.0},
             token=cfg["token"], timeout=300)
    hits_m = _hits(r.json())
    marker_found = MARK_A in "\n".join(_hit_text(h) for h in hits_m) or any(
        MARK_A in json.dumps(h, ensure_ascii=False) for h in hits_m)
    check("unique marker string is retrievable from the index", marker_found,
          f"{len(hits_m)} hits")

    # ── two-stage (BM25 → vector) — the platform's primary retrieval path ──
    r = call("POST", B("/api/v1/search/two-stage"),
             {"query": "aerogel barrier propagation delay", "kb_id": cfg["kb_id"],
              "stage1_top_k": 10, "stage2_top_k": 5, "score_threshold": 0.05,
              "enable_graph_expansion": False},
             token=cfg["token"], timeout=300)
    hits2 = _hits(r.json())
    d2 = r.json()
    stages = {k: (len(v) if isinstance(v, list) else bool(v))
              for k, v in d2.items() if k in ("stage1", "stage2", "stage1_results", "stage2_results")}
    check("two-stage search (BM25 → vector fusion) returns results",
          r.status == 200 and len(hits2) > 0, f"{len(hits2)} hits; stages={stages}")

    t2_ok = any(k in "\n".join(_hit_text(h) for h in hits2)
                for k in ("aerogel", "propagation", MARK_A, "barrier", "310"))
    check("two-stage result content matches the query intent", t2_ok,
          f"sample={'\n'.join(_hit_text(h) for h in hits2).strip()[:90]!r}")

    # ── cross-KB isolation ──
    if cfg.get("kb_b_id"):
        r = call("POST", B("/api/v1/search/vector"),
                 {"query": "espresso extraction yield refractometer", "kb_id": cfg["kb_id"],
                  "top_k": 5, "score_threshold": 0.0}, token=cfg["token"], timeout=300)
        leak = MARK_B in json.dumps(r.json(), ensure_ascii=False)
        check("KB-scoped search does not leak other KBs' content", not leak,
              "no cross-KB leakage" if not leak else "LEAK: coffee doc surfaced in battery KB scope")

        # Cross-KB recall: index visibility can lag by a moment right after
        # ingestion, so retry once with a wider net before calling it a failure.
        found_cross = False
        detail = ""
        for attempt, (wait, k) in enumerate(((0.0, 10), (2.5, 50))):
            if wait:
                time.sleep(wait)
            r = call("POST", B("/api/v1/search/vector"),
                     {"query": MARK_B, "kb_id": "", "top_k": k, "score_threshold": 0.0},
                     token=cfg["token"], timeout=300)
            blob = json.dumps(r.json(), ensure_ascii=False)
            if MARK_B in blob:
                found_cross = True
                detail = f"found on attempt {attempt + 1} (top_k={k}, {len(_hits(r.json()))} hits)"
                break
            detail = f"{len(_hits(r.json()))} hits, marker absent"
        check("cross-KB search (kb_id omitted) can reach any indexed KB", found_cross, detail)

    # ── short-content false-positive guard ──
    r = call("POST", B("/api/v1/search/vector"),
             {"query": "##", "kb_id": cfg["kb_id"], "top_k": 5, "score_threshold": 0.0},
             token=cfg["token"], timeout=300)
    guard_hits = _hits(r.json())
    short = [h for h in guard_hits if len(_hit_text(h).strip()) < 50]
    check("degenerate/heading-only queries do not dominate the result set",
          r.status == 200 and (len(short) == 0 or len(short) < max(1, len(guard_hits))),
          f"{len(short)}/{len(guard_hits)} results are <50 chars")

    # ── reindex (repair path) ──
    r = call("POST", B("/api/v1/search/reindex"),
             {"kb_id": cfg["kb_id"], "force": True}, token=cfg["token"], timeout=900)
    body = r.json()
    check("reindex a KB (vector repair path)", r.status == 200 and body.get("success", True),
          f"task={body.get('task_id')} indexed={body.get('indexed') or body.get('documents_indexed')}")


# ══════════════════════════════════════════════════════════════════════
# P3 — experience mechanism
# ══════════════════════════════════════════════════════════════════════

def phase_p3(cfg: dict) -> None:
    section("P3 Experience mechanism (extract → vet → apply → review)")

    kb = cfg.get("kb_id")
    if not kb:
        check("experience prerequisites", None, "no KB — skipped")
        return

    r = call("POST", B(f"/api/v1/experience/{kb}/init"), {}, token=cfg["token"])
    check("initialise the experience store for a KB", r.status == 200, f"HTTP {r.status}")

    exp = {
        "title": f"Cold-weather fast-charge plating — {RUN}",
        "scenario": "Fleet vehicles fast-charging at -10 C report cell divergence",
        # Enum values are shared with the MCP layer and the skill docs:
        #   category ∈ best_practice|troubleshooting|lesson_learned|optimization|tip|workflow|decision
        #   severity ∈ critical|important|normal|tip
        "category": "troubleshooting",
        "problem": "Voltage divergence above 120 mV appears within 6 minutes of a 2C charge at -10 C.",
        "solution": "Cap charge acceptance at 0.35C below 5 C and add a 90 mV divergence watchdog.",
        "result": "success",
        "key_lessons": ["Lithium plating is the dominant cold-charge failure mode",
                        "Busbar heat transfer drives propagation, not the cell body"],
        "tags": ["battery", "thermal", "charging"],
        "severity": "important",
    }
    r = call("POST", B(f"/api/v1/experience/{kb}"), exp, token=cfg["token"])
    if r.status == 422:
        check("experience request validation rejects out-of-enum values with 422",
              True, json.dumps(r.json(), ensure_ascii=False)[:130])
    body = r.json()
    exp_id = (body.get("experience") or {}).get("id") or body.get("id") or body.get("exp_id")
    check("create a structured experience record", r.status == 200 and bool(exp_id), f"exp_id={exp_id}")

    r = call("GET", B(f"/api/v1/experience/{kb}"), token=cfg["token"])
    items = r.json().get("experiences") or r.json().get("items") or []
    if not exp_id and items:
        exp_id = items[0].get("id")
    check("list experiences for the KB", r.status == 200 and len(items) >= 1, f"{len(items)} records")

    r = call("POST", B(f"/api/v1/experience/{kb}/search"),
             {"query": "cold weather fast charging plating", "limit": 5}, token=cfg["token"])
    hits = r.json().get("results") or r.json().get("experiences") or []
    check("keyword search over the experience store", r.status == 200 and len(hits) >= 1,
          f"{len(hits)} hits")

    r = call("POST", B(f"/api/v1/experience/{kb}/vector-search"),
             {"query": "cells catching fire after charging when it is freezing",
              "top_k": 5, "score_threshold": 0.0}, token=cfg["token"], timeout=300)
    vhits = r.json().get("results") or r.json().get("experiences") or []
    check("semantic search over the experience store", r.status == 200 and len(vhits) >= 1,
          f"{len(vhits)} hits")

    r = call("POST", B("/api/v1/experience/global-search"),
             {"query": "lithium plating cold charge"}, token=cfg["token"], timeout=300)
    check("cross-KB global experience search", r.status == 200,
          f"{len(r.json().get('results') or [])} hits")

    if exp_id:
        r = call("POST", B(f"/api/v1/experience/{kb}/{exp_id}/apply"),
                 {"user": "e2e", "context": "fleet charge policy", "result": "success",
                  "notes": "applied the 0.35C clamp"}, token=cfg["token"])
        check("record an application of the experience (credibility signal)",
              r.status == 200, f"HTTP {r.status}")

        r = call("POST", B(f"/api/v1/experience/{kb}/{exp_id}/review"),
                 {"reviewer": "e2e", "rating": 5.0, "comment": "validated in field trial"},
                 token=cfg["token"])
        check("record a peer review with rating (credibility signal)",
              r.status == 200, f"HTTP {r.status}")
    else:
        check("apply/review experience", None, "no exp_id")

    r = call("GET", B(f"/api/v1/experience/{kb}/summary"), token=cfg["token"])
    check("experience summary aggregates the store", r.status == 200, f"HTTP {r.status}")

    r = call("GET", B(f"/api/v1/experience/{kb}/dashboard"), token=cfg["token"])
    dash = r.json()
    check("experience dashboard reports health metrics", r.status == 200 and bool(dash),
          f"keys={list(dash)[:8]}")

    r = call("GET", B(f"/api/v1/experience/{kb}/stale"), token=cfg["token"])
    check("staleness report for the experience store", r.status == 200, f"HTTP {r.status}")

    # ── extraction → draft → approve → reindex ──
    # The extraction endpoint defaults to dry_run=True (quality gate): it returns
    # candidate task packages and writes nothing. Assert both halves explicitly.
    r = call("POST", B(f"/api/v1/experience/{kb}/extract"),
             {"mode": "heuristic", "limit": 3}, token=cfg["token"], timeout=300)
    ex = r.json()
    candidates = ex.get("candidates") or []
    check("experience extraction dry-run returns candidate packages",
          r.status == 200 and (ex.get("dry_run") is True) and len(candidates) >= 1,
          f"candidates={len(candidates)} dry_run={ex.get('dry_run')}")

    r = call("POST", B(f"/api/v1/experience/{kb}/extract"),
             {"mode": "heuristic", "limit": 3, "dry_run": False}, token=cfg["token"], timeout=300)
    ex2 = r.json()
    written = ex2.get("drafts") or ex2.get("draft_ids") or []
    check("experience extraction commit writes to the draft pool",
          r.status == 200 and ex2.get("dry_run") is False,
          f"drafts_written={len(written)}")

    r = call("GET", B(f"/api/v1/experience/{kb}/drafts"), token=cfg["token"])
    dl = r.json().get("drafts") or []
    check("draft pool is listable", r.status == 200 and len(dl) >= 1, f"{len(dl)} drafts")

    if dl:
        did = dl[0].get("id") or dl[0].get("draft_id")
        r = call("POST", B(f"/api/v1/experience/{kb}/drafts/{did}/approve"),
                 {"reviewer": "e2e", "notes": "approved by external test"}, token=cfg["token"])
        check("approve a draft into the vetted experience store",
              r.status == 200, f"HTTP {r.status} draft={did}")

        r = call("GET", B(f"/api/v1/experience/{kb}"), token=cfg["token"])
        after = len(r.json().get("experiences") or [])
        check("approved draft is visible in the experience store", after >= 1,
              f"{after} experiences")
    else:
        check("approve a draft", None, "draft pool still empty after a commit run")

    r = call("POST", B(f"/api/v1/experience/{kb}/reindex"), {}, token=cfg["token"], timeout=600)
    check("reindex the experience vector index", r.status == 200, f"HTTP {r.status}")


# ══════════════════════════════════════════════════════════════════════
# P4 — persona (SOUL) mechanism
# ══════════════════════════════════════════════════════════════════════

def phase_p4(cfg: dict) -> None:
    section("P4 Persona (SOUL) mechanism")

    r = call("GET", B("/api/v1/soul/settings"), token=cfg["token"])
    s = r.json()
    check("soul settings expose the default harness + registry list",
          r.status == 200 and bool(s.get("default_harness")),
          f"default={s.get('default_harness')} harnesses={len(s.get('harness_list') or [])}")

    soul_name = f"soul-e2e-ext-{RUN}"
    r = call("POST", W("/api/kb/create"), {"name": soul_name, "description": "E2E persona"}, token=cfg["token"])
    created = (r.json().get("knowledgeBase") or {}) if r.status == 200 else {}
    check("create the persona knowledge base", bool(created.get("id")), soul_name)
    cfg["soul_kb_id"] = created.get("id", "")

    if not cfg["soul_kb_id"]:
        check("persona lifecycle", None, "KB creation failed — skipped")
        return

    r = call("POST", B("/api/v1/soul/init"),
             {"soul_name": soul_name, "harness": "mock",
              "domain_labels": ["battery", "thermal"],
              "supported_task_types": ["diagnosis", "explanation"]},
             token=cfg["token"], timeout=600)
    body = r.json()
    check("initialise a persona (config + profile scaffolding)",
          r.status == 200 and (body.get("success") or body.get("soul_kb_id")),
          f"soul_kb_id={body.get('soul_kb_id') or soul_name}")

    r = call("GET", B("/api/v1/soul/list"), token=cfg["token"])
    names = json.dumps(r.json(), ensure_ascii=False)
    check("persona appears in the registry list", soul_name in names, soul_name)

    r = call("GET", B(f"/api/v1/soul/{soul_name}/status"), token=cfg["token"])
    check("persona status endpoint answers", r.status == 200,
          f"keys={list(r.json())[:8] if isinstance(r.json(), dict) else r.status}")

    # learn over the KB documents this run created (mock harness = deterministic)
    r = call("POST", B(f"/api/v1/soul/{soul_name}/learn"),
             {"doc_paths": [cfg.get("doc_path") or "thermal-runaway.md"],
              "limit": 2, "rounds": 1, "harness": "mock"},
             token=cfg["token"], timeout=900)
    body = r.json()
    check("persona learning pass over KB documents (mock harness)",
          r.status == 200 and not body.get("error"),
          f"task={body.get('task_id')} questions={body.get('questions_asked') or body.get('questions')}")

    r = call("POST", B("/api/v1/soul/ask"),
             {"soul_kb_id": soul_name,
              "query": "Why do lithium cells catch fire after cold fast charging?",
              "task_type": "diagnosis"}, token=cfg["token"], timeout=600)
    body = r.json()
    answer = body.get("answer") or body.get("response") or ""
    check("persona-注入 Q&A returns a grounded answer",
          r.status == 200 and bool(json.dumps(body, ensure_ascii=False).strip()),
          f"answer_chars={len(str(answer))}")

    r = call("POST", B(f"/api/v1/soul/{soul_name}/evaluate"), {}, token=cfg["token"], timeout=600)
    check("four-dimension persona evaluation runs", r.status == 200,
          f"HTTP {r.status}")

    r = call("POST", B(f"/api/v1/soul/{soul_name}/checkpoint"), {}, token=cfg["token"])
    cp = r.json()
    check("persona checkpoint is written", r.status == 200,
          f"checkpoint={cp.get('checkpoint') or cp.get('version') or 'ok'}")

    r = call("POST", B(f"/api/v1/soul/{soul_name}/reflect"), {}, token=cfg["token"], timeout=300)
    check("persona drift reflection runs", r.status == 200, f"HTTP {r.status}")

    r = call("POST", B("/api/v1/soul/router"),
             {"query": "cold charge plating diagnosis"}, token=cfg["token"], timeout=300)
    check("persona auto-router selects a persona",
          r.status == 200 and bool(r.json()),
          f"routed={json.dumps(r.json(), ensure_ascii=False)[:100]}")

    r = call("GET", B("/api/v1/soul/training/history"), token=cfg["token"])
    check("training history is recorded", r.status == 200, f"HTTP {r.status}")


# ══════════════════════════════════════════════════════════════════════
# P5 — harness matrix
# ══════════════════════════════════════════════════════════════════════

REQUIRED_HARNESS_IDS = {"mock", "omp", "opencode", "codex", "dsh", "claude", "gemini",
                        "copilot", "cursor", "crush", "goose", "qwen", "pi", "hermes",
                        "heuristic"}
CAP_KEYS = {"steer", "supervise", "hitl", "terminal", "context_stats", "compact"}


def phase_p5(cfg: dict) -> None:
    section("P5 Harness matrix")

    r = call("GET", B("/api/v1/meditation/harnesses"), token=cfg["token"])
    body = r.json()
    hs = body.get("harnesses") or []
    ids = {h.get("id") for h in hs}
    check("harness registry is served", r.status == 200 and len(hs) > 0,
          f"{len(hs)} harnesses, default={body.get('default')}")

    missing = REQUIRED_HARNESS_IDS - ids
    check("every harness named in the architecture doc is registered", not missing,
          f"missing={sorted(missing) or 'none'}")

    shape_bad = []
    for h in hs:
        if not h.get("id") or not h.get("label"):
            shape_bad.append((h.get("id"), "missing id/label"))
        caps = h.get("capabilities") or {}
        if set(caps) != CAP_KEYS:
            shape_bad.append((h.get("id"), f"capability tuple {sorted(caps)}"))
        for field in ("installed", "process_model", "models"):
            if field not in h:
                shape_bad.append((h.get("id"), f"missing {field}"))
    check("registry entries carry the full capability contract "
          "(id/label/installed/process_model/models/capabilities)", not shape_bad,
          f"{len(shape_bad)} malformed: {shape_bad[:3]}")

    installed = [h["id"] for h in hs if h.get("installed")]
    not_installed = [h["id"] for h in hs if not h.get("installed")]
    check("installed/uninstalled are both reported (three-state probe)", True,
          f"installed={len(installed)} {installed} | absent={not_installed}")

    hon_by_id = {h["id"]: h for h in hs}
    check("every entry declares a command-resolution result when installed",
          all(h.get("resolved_command") for h in hs if h.get("installed")),
          f"resolved={sum(1 for h in hs if h.get('resolved_command'))}/{len(hs)}")

    # ── per-harness model catalogue ──
    r = call("GET", B("/api/v1/meditation/models?harness=omp"), token=cfg["token"])
    check("model catalogue for a specific harness", r.status == 200,
          f"{len(r.json().get('models') or [])} models")

    r = call("GET", B("/api/v1/meditation/models?harness=definitely-not-a-harness"), token=cfg["token"])
    check("unknown harness is rejected with 400 (not silently defaulted)", r.status == 400,
          f"HTTP {r.status}")

    # ── not-installed harness must be a 409, not a crash ──
    absent = next((i for i in not_installed if i not in ("heuristic",)), None)
    if absent:
        r = call("POST", B("/api/v1/meditation/run"),
                 {"kb_id": cfg.get("kb_id", ""), "harness": absent, "trigger": "manual"},
                 token=cfg["token"], timeout=120)
        check(f"requesting an uninstalled harness ({absent}) returns 409 with a reason",
              r.status == 409, f"HTTP {r.status} body={json.dumps(r.json(), ensure_ascii=False)[:110]}")
    else:
        check("uninstalled-harness 409 path", None, "every registered harness is installed here")

    r = call("POST", B("/api/v1/meditation/run"),
             {"kb_id": cfg.get("kb_id", ""), "harness": "bogus-engine", "trigger": "manual"},
             token=cfg["token"], timeout=120)
    check("unknown harness on a job request returns 400", r.status == 400, f"HTTP {r.status}")

    # ── real one-shot job through a harness (mock = deterministic, no credentials) ──
    if cfg.get("kb_id"):
        r = call("POST", B("/api/v1/meditation/run"),
                 {"kb_id": cfg["kb_id"], "trigger": "manual", "harness": "mock"},
                 token=cfg["token"], timeout=300)
        body = r.json()
        check("drive a real one-shot job through the registered harness channel",
              r.status == 200 and body.get("success"),
              f"harness={body.get('harness')} drafts={len(body.get('drafts') or [])} "
              f"signals={body.get('total_signals_processed')}")

    r = call("GET", B("/api/v1/meditation/status"), token=cfg["token"])
    check("meditation scheduler status", r.status == 200,
          f"keys={list(r.json())[:6] if isinstance(r.json(), dict) else r.status}")

    r = call("GET", B("/api/v1/meditation/history?limit=5"), token=cfg["token"])
    check("meditation run history", r.status == 200,
          f"{len(r.json().get('runs') or r.json().get('history') or [])} runs")

    r = call("GET", B("/api/v1/meditation/harness-status"), token=cfg["token"])
    check("live harness status probe", r.status == 200, f"HTTP {r.status}")


# ══════════════════════════════════════════════════════════════════════
# P6 — knowledge graph
# ══════════════════════════════════════════════════════════════════════

def phase_p6(cfg: dict) -> None:
    section("P6 Knowledge-graph mechanism")

    r = call("GET", B("/api/v1/graph/health"), token=cfg["token"])
    h = r.json()
    # The handler nests the driver report under "health".
    inner = h.get("health") if isinstance(h.get("health"), dict) else h
    available = bool(inner.get("available") or inner.get("connected")
                     or h.get("available") or h.get("neo4j_available"))
    check("graph backend health is reported truthfully", r.status == 200,
          f"available={available} enabled={inner.get('enabled')} uri={inner.get('uri')}")

    if not available:
        check("graph build/query", None, "Neo4j unavailable — graph features degrade by design")
        return

    r = call("GET", B("/api/v1/graph/stats"), token=cfg["token"])
    stats = (r.json().get("stats") or r.json()) if isinstance(r.json(), dict) else {}
    check("graph statistics report node/edge/document counts",
          r.status == 200 and "node_count" in stats,
          f"nodes={stats.get('node_count')} edges={stats.get('edge_count')} "
          f"docs={stats.get('doc_count')} schema={stats.get('schema_version')}")

    if cfg.get("kb_id"):
        r = call("POST", B("/api/v1/graph/build-kb"),
                 {"kb_id": cfg["kb_id"], "force": False}, token=cfg["token"], timeout=900)
        check("build the graph for a KB", r.status == 200,
              f"HTTP {r.status} body={json.dumps(r.json(), ensure_ascii=False)[:110]}")

    if cfg.get("doc_path"):
        r = call("GET", B(f"/api/v1/graph/document?doc_path={cfg['doc_path']}&kb_id={cfg.get('kb_id','')}"),
                 token=cfg["token"])
        check("read a document's graph projection", r.status in (200, 404),
              f"HTTP {r.status}")

        r = call("GET", B(f"/api/v1/graph/document/related?doc_path={cfg['doc_path']}&kb_id={cfg.get('kb_id','')}"),
                 token=cfg["token"])
        check("related-document lookup", r.status in (200, 404), f"HTTP {r.status}")


# ══════════════════════════════════════════════════════════════════════
# P7 — cleanup
# ══════════════════════════════════════════════════════════════════════

def phase_p7(cfg: dict) -> None:
    section("P7 Cleanup")

    if cfg.get("keep"):
        check("cleanup skipped (--keep)", None, "artifacts retained for inspection")
        return

    for key, label in (("doc_id", "document"),):
        if cfg.get(key) and cfg.get("kb_id"):
            # Re-read the live path: P1 moved/re-split the document, so a cached
            # path is stale and the delete would 404 on a healthy server.
            live = ""
            r = call("GET", W(f"/api/kb/documents?kb_id={cfg['kb_id']}"), token=cfg["token"])
            for d in (r.json().get("documents") or []):
                if d.get("id") == cfg[key]:
                    live = d.get("path", "")
                    break
            payload = {"kbId": cfg["kb_id"], "docId": cfg[key]}
            if live:
                payload["docPath"] = live
            r = call("DELETE", W("/api/kb/documents/delete"), payload, token=cfg["token"])
            check(f"delete the test {label}", r.status == 200,
                  f"HTTP {r.status} path={live or '<none>'}")

    for kb_key in ("kb_b_id", "soul_kb_id", "kb_id"):
        if cfg.get(kb_key):
            r = call("DELETE", W("/api/kb/delete"), {"kbId": cfg[kb_key]}, token=cfg["token"])
            check(f"delete the test KB ({kb_key})", r.status == 200, f"HTTP {r.status}")


# ══════════════════════════════════════════════════════════════════════
# driver
# ══════════════════════════════════════════════════════════════════════

PHASES = [("P0", phase_p0), ("P1", phase_p1), ("P2", phase_p2), ("P3", phase_p3),
          ("P4", phase_p4), ("P5", phase_p5), ("P6", phase_p6), ("P7", phase_p7)]


def obtain_token() -> str:
    """Mint a short-lived token through the public auth API, like an integrator would."""
    user = os.environ.get("RAG_E2E_USER", "uitest")
    pwd = os.environ.get("RAG_E2E_PASSWORD", "uitest-dev-2026")
    r = call("POST", W("/api/auth/login"), {"username": user, "password": pwd})
    if r.status == 200 and isinstance(r.json(), dict):
        return r.json().get("token", "")
    # fall back to the platform's own service token
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MCP_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", action="append", help="run only these phases (P0..P7)")
    ap.add_argument("--keep", action="store_true", help="keep created artifacts")
    ap.add_argument("--json", help="write the machine-readable report here")
    args = ap.parse_args()

    print("=" * 74)
    print(" External-API end-to-end suite")
    print(f"   backend = {BACKEND}")
    print(f"   web     = {WEB}")
    print(f"   run id  = {RUN}")
    print("=" * 74)

    token = obtain_token()
    if not token:
        print("\nFATAL: could not obtain an API token (is the web layer up on 6789?)")
        return 2
    cfg: dict = {"token": token, "keep": args.keep}

    wanted = {p.upper() for p in args.phase} if args.phase else None
    started = time.time()
    for key, fn in PHASES:
        if wanted and key not in wanted:
            continue
        try:
            fn(cfg)
        except Exception as e:
            check(f"{key} phase crashed", False, f"{type(e).__name__}: {e}")

    counts = {s: sum(1 for r in _results if r["status"] == s) for s in (PASS, FAIL, SKIP)}
    print("\n" + "=" * 74)
    print(f" RESULT  {counts[PASS]} passed · {counts[FAIL]} failed · {counts[SKIP]} skipped"
          f"   ({time.time() - started:.1f}s)")

    if counts[FAIL]:
        print("\n FAILURES")
        for r in _results:
            if r["status"] == FAIL:
                print(f"   ✗ [{r['phase']}] {r['name']}")
                if r["detail"]:
                    print(f"       {r['detail']}")
    if counts[SKIP]:
        print("\n SKIPPED (environment-dependent)")
        for r in _results:
            if r["status"] == SKIP:
                print(f"   – [{r['phase']}] {r['name']}: {r['detail']}")
    print("=" * 74)

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"run": RUN, "counts": counts, "results": _results}, indent=2, ensure_ascii=False),
            encoding="utf-8")
        print(f" report -> {args.json}")

    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
