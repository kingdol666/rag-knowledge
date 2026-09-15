"""QDCVR Benchmark API — backend for the paper-replication dashboard.

Ground rules this API follows
-----------------------------
* **Self-describing.** ``GET /`` lists every route; ``GET /api/algorithms``
  publishes each algorithm's parameter schema, so a client can render a
  complete UI — including per-algorithm controls — without hardcoding anything.
* **Failure is data.** A method that cannot run (platform API down, bad
  parameter) reports ``error`` on its own result and lets the other methods
  finish, instead of failing the whole request.
* **Honest metrics.** Real IR metrics (P@k, R@k, nDCG, MRR) are computed only
  when the caller supplies ground truth. Without it, the response carries
  observable quantities (latency, score spread, inter-method overlap) and marks
  the metrics as absent.

Provenance tags on every algorithm: ``REAL-CODE`` (open-source library),
``REAL-ALGO`` (paper algorithm implemented here), ``PROJECT`` (this platform).
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import loaders
import metrics as ir_metrics
from algorithms import (
    ALIASES,
    ALGORITHMS,
    DEFAULT_SELECTION,
    AlgorithmUnavailable,
    ParamError,
    get_algorithm,
    registry,
    resolve_id,
    run_algorithm,
)
from config import get_settings
from store import store

settings = get_settings()

app = FastAPI(
    title="QDCVR Benchmark API",
    version="5.0.0",
    description=__doc__,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────
class DocumentIn(BaseModel):
    """A document supplied as JSON."""

    content: str = Field(..., min_length=1, description="full document text")
    title: str = Field("", description="display title; defaults to the id")
    domain: str = Field("", description="grouping label used by the domain filter")
    id: str | None = Field(None, description="stable id; generated when omitted")


class SearchRequest(BaseModel):
    """Run one or more algorithms over the corpus."""

    query: str = Field(..., min_length=1)
    methods: list[str] | None = Field(
        None, description=f"algorithm ids; defaults to {list(DEFAULT_SELECTION)}")
    top_k: int = Field(5, ge=1, le=100,
                       description="applied to every method unless overridden in params")
    domain: str | None = Field(None, description="restrict the corpus to one domain")
    domains: list[str] | None = Field(None, description="restrict to several domains")
    params: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="per-algorithm parameter overrides, keyed by algorithm id. "
                    "See GET /api/algorithms for each algorithm's schema.")
    preview_chars: int = Field(400, ge=80, le=4000)
    relevant: list[str] | None = Field(
        None, description="ground-truth doc ids; when given, real IR metrics are computed")


class CompareRequest(SearchRequest):
    """Same as /api/search but always returns the cross-method comparison block."""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _scoped_domains(request: SearchRequest) -> list[str] | None:
    if request.domains:
        return request.domains
    if request.domain:
        return [request.domain]
    return None


def _run_all(request: SearchRequest) -> tuple[list, list[str]]:
    """Execute the requested algorithms; return the runs and the resolved ids."""
    names = request.methods or list(DEFAULT_SELECTION)
    if not names:
        raise HTTPException(status_code=422, detail="no algorithms selected")

    resolved: list[str] = []
    for name in names:
        try:
            resolved.append(get_algorithm(name).id)
        except ParamError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Preserve the caller's order while dropping duplicates.
    resolved = list(dict.fromkeys(resolved))

    domains = _scoped_domains(request)
    runs = []
    for method_id in resolved:
        overrides = dict(request.params.get(method_id) or {})
        # The top-level top_k is the default; an explicit override still wins.
        overrides.setdefault("top_k", request.top_k)
        # Aliases may have been used as the params key.
        for alias, canonical in ALIASES.items():
            if canonical == method_id and alias in request.params:
                overrides = {**request.params[alias], **overrides}
        runs.append(run_algorithm(method_id, request.query, overrides, store, domains))
    return runs, resolved


def _comparison(runs: list, relevant: list[str] | None) -> dict[str, Any]:
    """Build the cross-method comparison block."""
    per_method: dict[str, Any] = {}
    ranked_by_method: dict[str, list[str]] = {}

    for run in runs:
        payload = run.to_dict() if hasattr(run, "to_dict") else run
        entry: dict[str, Any] = {
            "label": payload["label"],
            "count": payload["count"],
            "latency_ms": payload["latency_ms"],
            "params": payload["params"],
            "error": payload["error"],
            **ir_metrics.score_summary(payload["results"]),
        }
        if relevant:
            entry["metrics"] = ir_metrics.evaluate(payload["results"], relevant)
        per_method[payload["method"]] = entry
        ranked_by_method[payload["method"]] = [
            str(r.get("doc_id") or r.get("chunk_id")) for r in payload["results"]]

    ids = list(ranked_by_method)
    overlap: dict[str, float] = {}
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            overlap[f"{left}|{right}"] = ir_metrics.jaccard(
                ranked_by_method[left], ranked_by_method[right])

    fastest = min((m for m in per_method if per_method[m]["latency_ms"]),
                  key=lambda m: per_method[m]["latency_ms"], default=None)
    return {
        "per_method": per_method,
        "overlap": overlap,
        "fastest_method": fastest,
        "metrics_available": bool(relevant),
        "metrics_note": (
            "IR metrics computed against the supplied ground truth."
            if relevant else
            "No ground truth supplied, so no precision/recall/nDCG is reported. "
            "Only latency, score distribution and inter-method overlap are shown."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Service description
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["meta"])
async def index() -> dict[str, Any]:
    """Self-describing API index."""
    return {
        "service": "QDCVR Benchmark API",
        "version": app.version,
        "docs": "/docs",
        "config": {
            "app_mode": settings.app_mode,
            "platform_api": settings.project_search_url,
            "embedding_model": settings.embedding_model,
            "config_file_loaded": settings.config_loaded,
        },
        "routes": {
            "meta": ["GET /", "GET /api/health", "GET /api/algorithms",
                     "GET /api/domains"],
            "corpus": ["POST /api/documents", "POST /api/documents/batch",
                       "POST /api/documents/upload", "GET /api/documents",
                       "GET /api/documents/{doc_id}", "DELETE /api/documents/{doc_id}",
                       "DELETE /api/documents"],
            "retrieval": ["POST /api/search", "POST /api/compare",
                          "POST /api/reindex"],
        },
        "algorithms": [a.id for a in ALGORITHMS.values()],
        "aliases": ALIASES,
    }


@app.get("/api/health", tags=["meta"])
async def health() -> dict[str, Any]:
    """Liveness plus corpus/index readiness."""
    return {
        "status": "healthy",
        "docs": len(store.documents),
        "doc_count": len(store.documents),
        "chunks": len(store.chunks),
        "domains": store.domains(),
        "index": store.stats(),
        "algorithms": {a.id: f"[{a.implementation}] {a.component}"
                       for a in ALGORITHMS.values()},
    }


@app.get("/api/algorithms", tags=["meta"])
async def list_algorithms() -> dict[str, Any]:
    """The algorithm catalogue, including each algorithm's parameter schema.

    This is the contract the UI renders its controls from: a client can build a
    fully parameterised request without knowing any algorithm in advance.
    """
    return {
        "count": len(ALGORITHMS),
        "aliases": ALIASES,
        "default_selection": list(DEFAULT_SELECTION),
        "algorithms": registry(),
    }


@app.get("/api/domains", tags=["meta"])
async def list_domains() -> dict[str, Any]:
    """Local corpus domains, plus the knowledge bases the platform exposes."""
    import httpx

    local = store.domains()
    counts: dict[str, int] = {}
    for document in store.documents:
        counts[document.domain or ""] = counts.get(document.domain or "", 0) + 1

    platform: list[dict[str, Any]] = []
    platform_error: str | None = None
    try:
        headers = ({"Authorization": f"Bearer {settings.auth_token}"}
                   if settings.auth_token else {})
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            response = client.get(f"{settings.web_url}/api/kb/catalog", headers=headers)
            response.raise_for_status()
            for item in response.json().get("knowledgeBases", []):
                platform.append({"kb_id": item.get("kbId"), "name": item.get("name"),
                                 "document_count": item.get("documentCount")})
    except Exception as exc:
        platform_error = f"{type(exc).__name__}: {exc}"

    return {"local": local, "local_document_counts": counts,
            "platform_knowledge_bases": platform, "platform_error": platform_error}


# ─────────────────────────────────────────────────────────────────────────────
# Corpus management
# ─────────────────────────────────────────────────────────────────────────────
def _ingest(content: str, title: str, domain: str, doc_id: str | None,
            source: str, kind: str, warnings: tuple[str, ...] = ()) -> dict[str, Any]:
    text = content.strip()
    if not text:
        raise HTTPException(status_code=422, detail="document has no text content")
    identifier = doc_id or f"doc-{uuid.uuid4().hex[:12]}"
    document = store.add_document(identifier, title or identifier, domain, text,
                                  source=source, kind=kind, warnings=warnings)
    return {"id": document.id, "title": document.title, "domain": document.domain,
            "chunks": document.n_chunks, "characters": document.char_count,
            "source": document.source, "warnings": document.warnings}


@app.post("/api/documents", status_code=201, tags=["corpus"])
async def add_document(payload: DocumentIn) -> dict[str, Any]:
    """Add or replace one document, re-chunking and re-indexing it."""
    return _ingest(payload.content, payload.title, payload.domain, payload.id,
                   "manual", "text")


@app.post("/api/documents/batch", status_code=201, tags=["corpus"])
async def add_documents(payload: list[DocumentIn]) -> dict[str, Any]:
    """Add several documents in one call."""
    if not payload:
        raise HTTPException(status_code=422, detail="empty document list")
    added = [_ingest(d.content, d.title, d.domain, d.id, "manual", "text")
             for d in payload]
    return {"added": len(added), "documents": added, **store.stats()}


@app.post("/api/documents/upload", status_code=201, tags=["corpus"])
async def upload_documents(
    files: list[UploadFile] = File(..., description="one or more files"),
    domain: str = Query("", description="domain applied to every uploaded file"),
    per_file_domain: bool = Query(
        True, description="when true, a file may override the domain via its form 'domain'"),
) -> dict[str, Any]:
    """Upload files and index them.

    Accepts `{extensions}`. Each file is parsed, chunked and indexed
    independently, so one bad file never discards the rest of the batch.
    """
    if not files:
        raise HTTPException(status_code=422, detail="no files supplied")

    results: list[dict[str, Any]] = []
    for upload in files:
        name = Path(upload.filename or "unnamed").name
        try:
            data = await upload.read()
        except Exception as exc:
            results.append({"filename": name, "ok": False,
                            "error": f"could not read upload: {exc}"})
            continue
        if not data:
            results.append({"filename": name, "ok": False, "error": "file is empty"})
            continue
        try:
            extracted = loaders.extract(name, data)
        except loaders.UnsupportedFileType as exc:
            results.append({"filename": name, "ok": False, "error": str(exc)})
            continue
        except Exception as exc:
            results.append({"filename": name, "ok": False,
                            "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not extracted.text.strip():
            results.append({"filename": name, "ok": False,
                            "error": "no extractable text found in this file"})
            continue
        try:
            record = _ingest(extracted.text, name, domain or "", None,
                             "upload", extracted.kind, extracted.warnings)
        except HTTPException as exc:
            results.append({"filename": name, "ok": False, "error": str(exc.detail)})
            continue
        results.append({"filename": name, "ok": True, "bytes": len(data),
                        "kind": extracted.kind, **record})

    ok = sum(1 for r in results if r["ok"])
    return {"uploaded": ok, "failed": len(results) - ok, "files": results,
            "accepted_extensions": loaders.SUPPORTED_EXTENSIONS, **store.stats()}


@app.get("/api/documents", tags=["corpus"])
async def list_documents(
    domain: str | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    include_content: bool = Query(False),
) -> dict[str, Any]:
    """List the corpus."""
    documents = store.documents
    if domain:
        documents = [d for d in documents if d.domain == domain]
    window = documents[offset:offset + limit]
    return {
        "total": len(documents),
        "count": len(window),
        "offset": offset,
        "limit": limit,
        "chunks": len(store.chunks),
        "documents": [
            {
                "id": d.id, "title": d.title, "domain": d.domain, "kind": d.kind,
                "source": d.source, "chunks": d.n_chunks, "characters": d.char_count,
                "created_at": d.created_at, "warnings": d.warnings,
                **({"content": d.content} if include_content else {}),
            }
            for d in window
        ],
    }


@app.get("/api/documents/{doc_id}", tags=["corpus"])
async def get_document(doc_id: str) -> dict[str, Any]:
    """Read one document together with the chunks it was split into."""
    document = store.get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"no document with id '{doc_id}'")
    chunks = [{"index": c.index, "chunk_id": c.id, "characters": len(c.content),
               "content": c.content}
              for c in store.chunks if c.doc_id == doc_id]
    return {"id": document.id, "title": document.title, "domain": document.domain,
            "kind": document.kind, "source": document.source,
            "characters": document.char_count, "content": document.content,
            "chunks": chunks}


@app.delete("/api/documents/{doc_id}", tags=["corpus"])
async def delete_document(doc_id: str) -> dict[str, Any]:
    """Delete one document and drop its chunks from both indices."""
    if not store.delete_document(doc_id):
        raise HTTPException(status_code=404, detail=f"no document with id '{doc_id}'")
    return {"deleted": doc_id, **store.stats()}


@app.delete("/api/documents", tags=["corpus"])
async def clear_documents() -> dict[str, Any]:
    """Empty the corpus."""
    removed = store.clear()
    return {"removed": removed, **store.stats()}


@app.post("/api/reindex", tags=["retrieval"])
async def reindex() -> dict[str, Any]:
    """Force a rebuild of the dense index (embedding model + FAISS)."""
    started = time.perf_counter()
    store._invalidate_dense()  # noqa: SLF001 - deliberate index maintenance
    try:
        store.ensure_dense()
    except Exception as exc:
        raise HTTPException(status_code=503,
                            detail=f"dense index build failed: {type(exc).__name__}: {exc}") from exc
    return {"status": "reindexed",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            **store.stats()}


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/search", tags=["retrieval"])
async def search(request: SearchRequest) -> dict[str, Any]:
    """Run the selected algorithms for one query.

    Each algorithm receives its own parameter set (``params[<algorithm id>]``);
    see ``GET /api/algorithms`` for the schema of each.
    """
    if not store.chunks:
        return JSONResponse(
            status_code=409,
            content={"detail": "corpus is empty — upload or add documents first",
                     "hint": "POST /api/documents/upload"},
        )
    started = time.perf_counter()
    runs, _ = _run_all(request)
    results = {r.method: r.to_dict(request.preview_chars) for r in runs}
    return {
        "query": request.query,
        "domain": request.domain,
        "domains": _scoped_domains(request),
        "top_k": request.top_k,
        "corpus": store.stats(),
        "results": results,
        "latencies": {r.method: r.latency_ms for r in runs},
        "errors": {r.method: r.error for r in runs if r.error},
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }


@app.post("/api/compare", tags=["retrieval"])
async def compare(request: CompareRequest) -> dict[str, Any]:
    """Run several algorithms over one query and return the comparison block.

    Supply ``relevant`` (ground-truth document ids) to get real P@k / R@k /
    nDCG@10 / MRR for every method; otherwise only latency, score distribution
    and inter-method overlap are reported.
    """
    if not store.chunks and not any(resolve_id(m).startswith("qdcvr")
                                    for m in (request.methods or list(DEFAULT_SELECTION))):
        return JSONResponse(
            status_code=409,
            content={"detail": "corpus is empty — upload or add documents first",
                     "hint": "POST /api/documents/upload"},
        )
    started = time.perf_counter()
    runs, resolved = _run_all(request)
    return {
        "query": request.query,
        "methods": resolved,
        "domains": _scoped_domains(request),
        "top_k": request.top_k,
        "results": {r.method: r.to_dict(request.preview_chars) for r in runs},
        "comparison": _comparison(runs, request.relevant),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Backwards-compatible aliases for the original dashboard
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/docs", tags=["compat"], include_in_schema=False)
async def legacy_list_docs() -> dict[str, Any]:
    listing = await list_documents()
    listing["documents"] = [{"id": d["id"], "title": d["title"], "domain": d["domain"]}
                            for d in listing["documents"]]
    return listing


@app.get("/api/documents/list", tags=["compat"], include_in_schema=False)
async def legacy_documents_list() -> dict[str, Any]:
    return await legacy_list_docs()


@app.post("/api/docs/add", status_code=201, tags=["compat"], include_in_schema=False)
async def legacy_add_doc(payload: DocumentIn) -> dict[str, Any]:
    return await add_document(payload)


@app.post("/api/docs/batch", status_code=201, tags=["compat"], include_in_schema=False)
async def legacy_add_batch(payload: list[DocumentIn]) -> dict[str, Any]:
    return await add_documents(payload)


@app.post("/api/documents/add", status_code=201, tags=["compat"], include_in_schema=False)
async def legacy_add_document(payload: DocumentIn) -> dict[str, Any]:
    return await add_document(payload)


@app.exception_handler(ParamError)
async def _param_error(_request, exc: ParamError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(AlgorithmUnavailable)
async def _unavailable(_request, exc: AlgorithmUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# `loaders.SUPPORTED_EXTENSIONS` is interpolated into the upload docstring above.
upload_documents.__doc__ = (upload_documents.__doc__ or "").format(
    extensions=", ".join(loaders.SUPPORTED_EXTENSIONS))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8800)
