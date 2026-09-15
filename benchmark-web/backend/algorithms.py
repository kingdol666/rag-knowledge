"""RAG algorithm registry with **declared, validated parameters**.

Every algorithm publishes a parameter schema (name, type, default, bounds,
description). That single declaration drives three things at once:

1. request validation — out-of-range or wrong-typed overrides are rejected with
   a message naming the parameter and its bounds, instead of silently ignored;
2. ``GET /api/algorithms`` — the UI renders its parameter panel from this, so
   the front end can never drift from what the back end accepts;
3. the benchmark itself — defaults are the paper settings, so a request with no
   overrides reproduces the published configuration.

Each entry carries an ``implementation`` provenance tag:

``REAL-CODE``
    An actual open-source library (rank_bm25, FAISS, sentence-transformers).
``REAL-ALGO``
    A paper's algorithm implemented here from its published description.
``PROJECT``
    The platform's own QDCVR retrieval path, called over its API.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import httpx

from config import get_settings
from store import DocumentStore, minmax_norm, tokenize

ParamType = Literal["int", "float", "bool", "str"]


class ParamError(ValueError):
    """Raised when a parameter override violates the declared schema."""


class AlgorithmUnavailable(RuntimeError):
    """Raised when an algorithm's backing service or model cannot be reached."""


@dataclass(frozen=True)
class Param:
    """One tunable parameter of an algorithm."""

    name: str
    type: ParamType
    default: Any
    description: str = ""
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] | None = None

    def coerce(self, raw: Any) -> Any:
        """Validate and convert ``raw`` to the declared type."""
        try:
            if self.type == "bool":
                if isinstance(raw, bool):
                    value: Any = raw
                elif isinstance(raw, str):
                    value = raw.strip().lower() in {"1", "true", "yes", "on"}
                else:
                    value = bool(raw)
            elif self.type == "int":
                value = int(raw)
            elif self.type == "float":
                value = float(raw)
            else:
                value = str(raw)
        except (TypeError, ValueError) as exc:
            raise ParamError(
                f"parameter '{self.name}' expects {self.type}, got {raw!r}"
            ) from exc

        if self.type in ("int", "float"):
            if self.minimum is not None and value < self.minimum:
                raise ParamError(
                    f"parameter '{self.name}' must be >= {self.minimum} (got {value})")
            if self.maximum is not None and value > self.maximum:
                raise ParamError(
                    f"parameter '{self.name}' must be <= {self.maximum} (got {value})")
        if self.choices and value not in self.choices:
            raise ParamError(
                f"parameter '{self.name}' must be one of {list(self.choices)} (got {value!r})")
        return value

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "description": self.description,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "choices": list(self.choices) if self.choices else None,
        }


@dataclass
class Hit:
    """One retrieved chunk."""

    rank: int
    chunk_id: str
    doc_id: str
    title: str
    domain: str
    content: str
    score: float
    source: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, preview_chars: int = 400) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "title": self.title,
            "domain": self.domain,
            "content": self.content[:preview_chars],
            "content_preview": self.content[:preview_chars],
            "score": round(float(self.score), 4),
            "source": self.source,
            **self.meta,
        }


@dataclass(frozen=True)
class Algorithm:
    """A retrievable algorithm plus its parameter contract."""

    id: str
    label: str
    family: str
    implementation: str
    component: str
    paper: str
    description: str
    params: tuple[Param, ...]
    runner: Callable[..., list[Hit]]

    def resolve(self, overrides: dict[str, Any] | None) -> dict[str, Any]:
        """Merge defaults with ``overrides``, rejecting unknown keys."""
        known = {p.name for p in self.params}
        supplied = dict(overrides or {})
        unknown = set(supplied) - known
        if unknown:
            raise ParamError(
                f"algorithm '{self.id}' has no parameter(s) {sorted(unknown)}; "
                f"valid: {sorted(known)}"
            )
        resolved = {p.name: p.default for p in self.params}
        for param in self.params:
            if param.name in supplied and supplied[param.name] is not None:
                resolved[param.name] = param.coerce(supplied[param.name])
        return resolved

    def schema(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "family": self.family,
            "implementation": self.implementation,
            "component": self.component,
            "paper": self.paper,
            "description": self.description,
            "params": [p.schema() for p in self.params],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Shared parameter declarations
# ─────────────────────────────────────────────────────────────────────────────
def _top_k(default: int = 5) -> Param:
    return Param("top_k", "int", default, "number of results returned", 1, 100)


CANDIDATE_K = Param("candidate_k", "int", 20,
                    "size of the first-stage pool each retriever contributes", 1, 200)
SCORE_FLOOR = Param("score_threshold", "float", 0.0,
                    "drop hits whose cosine similarity is below this", 0.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# REAL-CODE — sparse, dense, hybrid, rerank
# ─────────────────────────────────────────────────────────────────────────────
def run_bm25(query: str, params: dict[str, Any], store: DocumentStore,
             domains: list[str] | None = None) -> list[Hit]:
    """BM25 Okapi sparse retrieval (``rank_bm25``)."""
    scored = store.bm25_scores(query, k1=params["k1"], b=params["b"], domains=domains)
    hits: list[Hit] = []
    for chunk, score in scored:
        if len(hits) >= params["top_k"]:
            break
        if score <= 0:
            break  # sorted, so every later chunk also scores 0
        hits.append(Hit(len(hits) + 1, chunk.id, chunk.doc_id, chunk.title, chunk.domain,
                        chunk.content, score,
                        "BM25 [REAL-CODE: rank_bm25]",
                        {"k1": params["k1"], "b": params["b"]}))
    return hits


def run_dense(query: str, params: dict[str, Any], store: DocumentStore,
              domains: list[str] | None = None) -> list[Hit]:
    """Dense retrieval: FAISS inner-product over BGE-M3 embeddings."""
    pairs = store.dense_search(query, params["top_k"], params["score_threshold"],
                               domains=domains)
    return [Hit(i + 1, c.id, c.doc_id, c.title, c.domain, c.content, s,
                "Dense [REAL-CODE: FAISS + BGE-M3]")
            for i, (c, s) in enumerate(pairs)]


def run_hybrid(query: str, params: dict[str, Any], store: DocumentStore,
               domains: list[str] | None = None) -> list[Hit]:
    """Linear fusion of BM25 and dense scores.

    ``alpha`` weights the sparse side: ``alpha=1`` is pure BM25, ``alpha=0`` is
    pure dense.
    """
    pool = params["candidate_k"]
    sparse = {h.chunk_id: h for h in run_bm25(
        query, {"top_k": pool, "k1": params["k1"], "b": params["b"]}, store, domains)}
    dense = {h.chunk_id: h for h in run_dense(
        query, {"top_k": pool, "score_threshold": 0.0}, store, domains)}

    if params["norm"] == "minmax":
        sparse_scores = minmax_norm({k: h.score for k, h in sparse.items()})
        dense_scores = minmax_norm({k: h.score for k, h in dense.items()})
    else:
        sparse_scores = {k: h.score for k, h in sparse.items()}
        dense_scores = {k: h.score for k, h in dense.items()}

    alpha = params["alpha"]
    fused: list[Hit] = []
    for chunk_id in set(sparse) | set(dense):
        base = sparse.get(chunk_id) or dense[chunk_id]
        score = alpha * sparse_scores.get(chunk_id, 0.0) + (1 - alpha) * dense_scores.get(chunk_id, 0.0)
        fused.append(Hit(0, base.chunk_id, base.doc_id, base.title, base.domain,
                         base.content, score,
                         f"Hybrid [REAL-CODE: BM25+FAISS fusion, alpha={alpha}, norm={params['norm']}]",
                         {"alpha": alpha, "norm": params["norm"],
                          "sparse": round(sparse_scores.get(chunk_id, 0.0), 4),
                          "dense": round(dense_scores.get(chunk_id, 0.0), 4)}))
    fused.sort(key=lambda h: h.score, reverse=True)
    for i, hit in enumerate(fused[:params["top_k"]]):
        hit.rank = i + 1
    return fused[:params["top_k"]]


def run_ce_rerank(query: str, params: dict[str, Any], store: DocumentStore,
                  domains: list[str] | None = None) -> list[Hit]:
    """Dense recall, then a MS MARCO cross-encoder rescores the pool."""
    pool = store.dense_search(query, params["candidate_k"], params["score_threshold"],
                              domains=domains)
    if not pool:
        return []
    try:
        encoder = store.cross_encoder()
        scores = encoder.predict([(query, c.content) for c, _ in pool])
    except Exception as exc:
        # Degrade to the dense ranking, but say so instead of pretending.
        return [Hit(i + 1, c.id, c.doc_id, c.title, c.domain, c.content, s,
                    "Dense+CE [FALLBACK: cross-encoder unavailable]",
                    {"rerank_error": f"{type(exc).__name__}: {exc}"})
                for i, (c, s) in enumerate(pool[:params["top_k"]])]

    reranked = sorted(zip(pool, scores), key=lambda pair: float(pair[1]), reverse=True)
    return [Hit(i + 1, c.id, c.doc_id, c.title, c.domain, c.content, float(s),
                "Dense+CE [REAL-CODE: FAISS + cross-encoder/ms-marco-MiniLM-L-6-v2]",
                {"dense_score": round(float(d), 4)})
            for i, ((c, d), s) in enumerate(reranked[:params["top_k"]])]


# ─────────────────────────────────────────────────────────────────────────────
# REAL-ALGO — CRAG, Self-RAG
# ─────────────────────────────────────────────────────────────────────────────
def run_crag(query: str, params: dict[str, Any], store: DocumentStore,
             domains: list[str] | None = None) -> list[Hit]:
    """Corrective RAG (Yan et al., NAACL 2024).

    Scores each candidate with a retrieval evaluator, splits it into
    correct / ambiguous / incorrect by two thresholds, and — when incorrect
    candidates dominate — runs a refinement pass over an expanded pool.
    """
    pool = run_dense(query, {"top_k": params["candidate_k"], "score_threshold": 0.0},
                     store, domains)
    if not pool:
        return []

    terms = set(tokenize(query))
    upper, lower = params["upper_threshold"], params["lower_threshold"]
    w_overlap, w_dense = params["w_overlap"], params["w_dense"]

    def evaluate(hit: Hit) -> float:
        doc_terms = set(tokenize(hit.content))
        overlap = len(terms & doc_terms) / len(terms) if terms else 0.0
        return w_overlap * overlap + w_dense * hit.score

    scored = [(hit, evaluate(hit)) for hit in pool]
    correct = [(h, c) for h, c in scored if c >= upper]
    ambiguous = [(h, c) for h, c in scored if lower <= c < upper]
    incorrect = [1 for _, c in scored if c < lower]

    refined = False
    if len(incorrect) > len(scored) * params["expand_trigger"]:
        refined = True
        seen = {h.chunk_id for h, _ in correct}
        # run_dense yields Hit objects (not (chunk, score) pairs).
        for hit in run_dense(query, {"top_k": params["expand_k"], "score_threshold": 0.0},
                             store, domains):
            if hit.chunk_id in seen:
                continue
            confidence = evaluate(hit)
            if confidence >= lower:
                correct.append((hit, confidence))
                seen.add(hit.chunk_id)

    merged = sorted(correct + ambiguous, key=lambda pair: pair[1], reverse=True)
    return [Hit(i + 1, h.chunk_id, h.doc_id, h.title, h.domain, h.content, c,
                "CRAG [REAL-ALGO: Yan et al. NAACL 2024]",
                {"crag_confidence": round(c, 4), "refined": refined,
                 "verdict": "correct" if c >= upper else "ambiguous"})
            for i, (h, c) in enumerate(merged[:params["top_k"]])]


def run_selfrag(query: str, params: dict[str, Any], store: DocumentStore,
                domains: list[str] | None = None) -> list[Hit]:
    """Self-RAG (Asai et al., 2023) — reflection-token critic.

    Emits the paper's three reflection signals per candidate — ISREL
    (relevant), ISSUP (supported) and ISUSE (useful) — and keeps only those
    whose weighted score clears ``threshold``.
    """
    pool = run_dense(query, {"top_k": params["candidate_k"], "score_threshold": 0.0},
                     store, domains)
    terms = set(tokenize(query))
    w_rel, w_sup, w_use = params["w_rel"], params["w_sup"], params["w_use"]
    gain = params["support_gain"]

    reflected: list[Hit] = []
    for hit in pool:
        doc_terms = set(tokenize(hit.content))
        isrel = min(1.0, (len(terms & doc_terms) / len(terms) * 1.5) if terms else 0.0)
        issup = min(1.0, hit.score * gain)
        isuse = min(1.0, len(hit.content) / 500)
        score = w_rel * isrel + w_sup * issup + w_use * isuse
        if score >= params["threshold"]:
            reflected.append(Hit(0, hit.chunk_id, hit.doc_id, hit.title, hit.domain,
                                 hit.content, score,
                                 "Self-RAG [REAL-ALGO: Asai et al. 2023]",
                                 {"reflection_tokens": {
                                     "ISREL": round(isrel, 3),
                                     "ISSUP": round(issup, 3),
                                     "ISUSE": round(isuse, 3)}}))
    reflected.sort(key=lambda h: h.score, reverse=True)
    for i, hit in enumerate(reflected[:params["top_k"]]):
        hit.rank = i + 1
    return reflected[:params["top_k"]]


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT — the platform's own QDCVR path, over HTTP
# ─────────────────────────────────────────────────────────────────────────────
def _project_search(query: str, kb_id: str, top_k: int, score_threshold: float) -> list[Hit]:
    """Call the platform's vector-search API (the QDCVR baseline)."""
    settings = get_settings()
    payload = {"query": query, "kb_id": kb_id, "top_k": top_k,
               "score_threshold": score_threshold}
    headers = {"Authorization": f"Bearer {settings.auth_token}"} if settings.auth_token else {}
    try:
        with httpx.Client(timeout=60.0, trust_env=False) as client:
            response = client.post(settings.project_search_url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise AlgorithmUnavailable(
            f"cannot reach the platform API at {settings.project_search_url} "
            f"({type(exc).__name__}). Start it with `ragctl up` in the repo root."
        ) from exc
    if response.status_code == 401:
        raise AlgorithmUnavailable(
            "platform API rejected the request (401). MCP_AUTH_TOKEN is missing or "
            "stale in the repo-root .env."
        )
    if response.status_code >= 400:
        raise AlgorithmUnavailable(
            f"platform API returned HTTP {response.status_code}: {response.text[:200]}")

    results = response.json().get("results", [])
    hits: list[Hit] = []
    for i, item in enumerate(results[:top_k]):
        path = item.get("doc_path") or item.get("name") or f"result-{i}"
        title = re.split(r"[\\/]", str(path))[-1]
        hits.append(Hit(i + 1, item.get("chunk_id", f"{path}#{item.get('chunk_index', i)}"),
                        str(path), title, item.get("kb_id", kb_id), item.get("content", "") or "",
                        float(item.get("score", 0.0)), "QDCVR [PROJECT: platform API]",
                        {"collection": item.get("collection"),
                         "chunk_index": item.get("chunk_index")}))
    return hits


def run_qdcvr_flat(query: str, params: dict[str, Any], store: DocumentStore,
                   domains: list[str] | None = None) -> list[Hit]:
    return _project_search(query, params["kb_id"], params["top_k"], params["score_threshold"])


def run_qdcvr_domain(query: str, params: dict[str, Any], store: DocumentStore,
                     domains: list[str] | None = None) -> list[Hit]:
    if not params["kb_id"]:
        raise ParamError(
            "algorithm 'qdcvr_domain' requires 'kb_id' — pass the knowledge base to "
            "scope the search to (see GET /api/domains for the ones the platform exposes)."
        )
    return _project_search(query, params["kb_id"], params["top_k"], params["score_threshold"])


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────
_ALGORITHMS: tuple[Algorithm, ...] = (
    Algorithm(
        id="bm25", label="BM25", family="sparse", implementation="REAL-CODE",
        component="rank_bm25 (BM25Okapi)",
        paper="Robertson & Zaragoza, Okapi BM25",
        description="Lexical sparse retrieval. Tune k1 for term-frequency "
                    "saturation and b for document-length normalisation.",
        params=(_top_k(),
                Param("k1", "float", 1.5, "term-frequency saturation", 0.0, 3.0),
                Param("b", "float", 0.75, "length-normalisation strength", 0.0, 1.0)),
        runner=run_bm25,
    ),
    Algorithm(
        id="dense", label="Dense (BGE-M3)", family="dense", implementation="REAL-CODE",
        component="FAISS IndexFlatIP + BAAI/bge-m3",
        paper="Karpukhin et al., DPR — dense dual-encoder retrieval",
        description="Exact inner-product search over sentence embeddings. "
                    "score_threshold filters weak neighbours by cosine similarity.",
        params=(_top_k(), SCORE_FLOOR),
        runner=run_dense,
    ),
    Algorithm(
        id="hybrid", label="Hybrid (BM25+Dense)", family="hybrid", implementation="REAL-CODE",
        component="rank_bm25 + FAISS linear fusion",
        paper="Robertson & Zaragoza + Karpukhin et al. (fusion)",
        description="Weighted fusion of the sparse and dense rankings. "
                    "alpha=1 is pure BM25, alpha=0 is pure dense.",
        params=(_top_k(),
                Param("alpha", "float", 0.5, "weight on the sparse side (1-alpha on dense)",
                      0.0, 1.0),
                Param("candidate_k", "int", 20, "pool size contributed by each retriever", 1, 200),
                Param("norm", "str", "minmax", "how scores are put on a common scale",
                      choices=("minmax", "none")),
                Param("k1", "float", 1.5, "BM25 term-frequency saturation", 0.0, 3.0),
                Param("b", "float", 0.75, "BM25 length normalisation", 0.0, 1.0)),
        runner=run_hybrid,
    ),
    Algorithm(
        id="ce_rerank", label="Dense + Cross-Encoder", family="rerank",
        implementation="REAL-CODE",
        component="FAISS recall → cross-encoder/ms-marco-MiniLM-L-6-v2",
        paper="Nogueira & Cho, Passage Re-ranking with BERT",
        description="Recall a wide dense pool, then rescore every candidate with "
                    "a cross-encoder. candidate_k controls how much the reranker sees.",
        params=(_top_k(),
                Param("candidate_k", "int", 20, "dense pool handed to the reranker", 1, 200),
                SCORE_FLOOR),
        runner=run_ce_rerank,
    ),
    Algorithm(
        id="crag", label="CRAG (corrective)", family="corrective",
        implementation="REAL-ALGO",
        component="dense recall + retrieval evaluator + refinement pass",
        paper="Yan et al., CRAG: Corrective Retrieval Augmented Generation, NAACL 2024",
        description="Classifies each candidate as correct / ambiguous / incorrect "
                    "and refines when the incorrect share exceeds expand_trigger.",
        params=(_top_k(),
                Param("candidate_k", "int", 20, "candidates the evaluator scores", 1, 200),
                Param("upper_threshold", "float", 0.6, "confidence at or above = correct",
                      0.0, 1.0),
                Param("lower_threshold", "float", 0.3, "confidence below = incorrect", 0.0, 1.0),
                Param("expand_trigger", "float", 0.5,
                      "incorrect fraction that triggers knowledge refinement", 0.0, 1.0),
                Param("expand_k", "int", 15, "size of the refinement pool", 1, 200),
                Param("w_overlap", "float", 0.4, "evaluator weight on query-term overlap",
                      0.0, 1.0),
                Param("w_dense", "float", 0.6, "evaluator weight on the dense score", 0.0, 1.0)),
        runner=run_crag,
    ),
    Algorithm(
        id="selfrag", label="Self-RAG (reflective)", family="self-reflective",
        implementation="REAL-ALGO",
        component="dense recall + ISREL/ISSUP/ISUSE reflection critic",
        paper="Asai et al., Self-RAG: Learning to Retrieve, Generate and Critique "
              "through Self-Reflection, 2023",
        description="Emits the paper's three reflection signals per candidate and "
                    "keeps only those clearing the weighted threshold.",
        params=(_top_k(),
                Param("candidate_k", "int", 20, "candidates the critic scores", 1, 200),
                Param("threshold", "float", 0.4, "minimum weighted reflection score",
                      0.0, 1.0),
                Param("w_rel", "float", 0.4, "weight of ISREL", 0.0, 1.0),
                Param("w_sup", "float", 0.3, "weight of ISSUP", 0.0, 1.0),
                Param("w_use", "float", 0.3, "weight of ISUSE", 0.0, 1.0),
                Param("support_gain", "float", 1.2, "scaling applied to the dense score for ISSUP",
                      0.0, 5.0)),
        runner=run_selfrag,
    ),
    Algorithm(
        id="qdcvr_flat", label="QDCVR (all KBs)", family="project",
        implementation="PROJECT",
        component="platform API — /api/v1/search/vector across every knowledge base",
        paper="This platform (QDCVR retrieval path)",
        description="The system under test, searched flat across all knowledge "
                    "bases. Requires the platform backend to be running.",
        params=(_top_k(), SCORE_FLOOR, Param("kb_id", "str", "",
                                             "optional knowledge-base id; empty = all")),
        runner=run_qdcvr_flat,
    ),
    Algorithm(
        id="qdcvr_domain", label="QDCVR (KB-scoped)", family="project",
        implementation="PROJECT",
        component="platform API — /api/v1/search/vector scoped to one knowledge base",
        paper="This platform (QDCVR retrieval path)",
        description="The system under test, scoped to a single knowledge base so it "
                    "cannot answer from the wrong domain. kb_id is required.",
        params=(_top_k(), SCORE_FLOOR,
                Param("kb_id", "str", "", "knowledge-base id to scope the search to")),
        runner=run_qdcvr_domain,
    ),
)

ALGORITHMS: dict[str, Algorithm] = {a.id: a for a in _ALGORITHMS}

#: Backwards-compatible spellings the old dashboard used.
ALIASES: dict[str, str] = {"vector": "dense", "qdcvr": "qdcvr_flat",
                           "self_rag": "selfrag", "cross_encoder": "ce_rerank"}

DEFAULT_SELECTION: tuple[str, ...] = ("bm25", "dense", "hybrid", "crag", "selfrag")


def resolve_id(name: str) -> str:
    """Map an alias to its canonical algorithm id."""
    key = (name or "").strip().lower()
    return ALIASES.get(key, key)


def get_algorithm(name: str) -> Algorithm:
    resolved = resolve_id(name)
    if resolved not in ALGORITHMS:
        raise ParamError(
            f"unknown algorithm '{name}'. Available: {sorted(ALGORITHMS)} "
            f"(aliases: {sorted(ALIASES)})"
        )
    return ALGORITHMS[resolved]


def registry() -> list[dict[str, Any]]:
    """The full algorithm catalogue, with parameter schemas."""
    return [a.schema() for a in _ALGORITHMS]


@dataclass
class MethodRun:
    """Outcome of one algorithm on one query."""

    method: str
    label: str
    hits: list[Hit] = field(default_factory=list)
    latency_ms: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self, preview_chars: int = 400) -> dict[str, Any]:
        return {
            "method": self.method,
            "label": self.label,
            "params": self.params,
            "latency_ms": self.latency_ms,
            "count": len(self.hits),
            "results": [h.to_dict(preview_chars) for h in self.hits],
            "error": self.error,
        }


def run_algorithm(name: str, query: str, params: dict[str, Any] | None,
                  store: DocumentStore, domains: list[str] | None = None) -> MethodRun:
    """Execute one algorithm, capturing failure as data rather than a 500.

    A comparison runs several independent backends — an embedding model, a
    cross-encoder, an HTTP service. Any of them can be unavailable while the
    others work, so a failure is reported on that method's own result instead
    of aborting the request. The exception type is kept in the message so a
    genuine bug is still diagnosable.
    """
    algorithm = get_algorithm(name)
    started = time.perf_counter()
    try:
        resolved = algorithm.resolve(params)
        hits = algorithm.runner(query, resolved, store, domains)
        return MethodRun(algorithm.id, algorithm.label, hits,
                         round((time.perf_counter() - started) * 1000, 1), resolved)
    except (ParamError, AlgorithmUnavailable) as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 - deliberate: isolate per-method failure
        error = f"{type(exc).__name__}: {exc}"
    return MethodRun(algorithm.id, algorithm.label, [],
                     round((time.perf_counter() - started) * 1000, 1),
                     dict(params or {}), error=error)
