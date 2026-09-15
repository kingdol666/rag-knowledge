"""Shared document store: chunking, BM25 index, dense index, persistence.

Every algorithm in :mod:`algorithms` reads from this one store so that
differences in the benchmark come from the retrieval strategy, never from the
corpus, the chunking or the embedding model.

Design notes
------------
* **Chunking is character-based.** The previous implementation split on
  whitespace, which collapses any CJK document into a single "chunk" because
  Chinese/Japanese text has no spaces. Character windows with sentence-boundary
  preference work for both scripts.
* **Both indices are invalidated together.** Adding or deleting a document
  marks the dense index dirty; ``ensure_dense()`` rebuilds it on the next
  search. BM25 is cheap and rebuilt eagerly.
* **The corpus is persisted** to ``backend/data/corpus.json`` so a restart does
  not silently empty the benchmark.
"""
from __future__ import annotations

import json
import math
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from config import get_settings

#: Sentence-ish boundaries, CJK included. Used to avoid cutting mid-sentence.
_BREAK_CHARS = "\n。！？!?.;；"
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")


def tokenize(text: str) -> list[str]:
    """Tokenize for BM25 over mixed Latin/CJK text.

    Latin runs become lowercased words; CJK runs become character bigrams,
    which is the standard cheap approximation of Chinese word segmentation and
    keeps recall reasonable without pulling in a segmenter.
    """
    tokens: list[str] = []
    for chunk in re.findall(r"[A-Za-z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", text):
        if _CJK.match(chunk):
            if len(chunk) == 1:
                tokens.append(chunk)
            else:
                tokens.extend(chunk[i:i + 2] for i in range(len(chunk) - 1))
        else:
            tokens.append(chunk.lower())
    return tokens


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split ``text`` into ~``size``-character windows overlapping by ``overlap``.

    The window is nudged forward/back to the nearest sentence boundary when one
    is close, so chunks stay readable.
    """
    text = text.strip()
    if not text:
        return []
    size = max(50, int(size))
    overlap = max(0, min(int(overlap), size - 1))
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            # Prefer the last sentence break in the final 30% of the window.
            floor = int(size * 0.7)
            best = max((window.rfind(ch, floor) for ch in _BREAK_CHARS), default=-1)
            if best > 0:
                end = start + best + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


@dataclass
class Document:
    """One ingested source document."""

    id: str
    title: str
    domain: str
    content: str
    source: str = "manual"
    kind: str = "text"
    created_at: float = field(default_factory=time.time)
    n_chunks: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        return len(self.content)


@dataclass
class Chunk:
    """A retrieval unit cut from one document."""

    id: str
    doc_id: str
    content: str
    title: str
    domain: str
    index: int


class DocumentStore:
    """Thread-safe corpus + index holder."""

    def __init__(self, persist: bool = True) -> None:
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.data_file = settings.data_dir / "corpus.json"
        self.persist = persist

        self._lock = threading.RLock()
        self._documents: dict[str, Document] = {}
        self._chunks: list[Chunk] = []

        self._bm25 = None
        self._bm25_params: tuple[float, float] | None = None
        self._bm25_tokenized: list[list[str]] = []

        self._dense_ready = False
        self._embedder = None
        self._faiss_index = None
        self._dense_ids: list[str] = []

        self._cross_encoder = None
        self._dense_error: str | None = None

        if persist:
            self._load()

    # ── corpus mutation ────────────────────────────────────────────────────
    def add_document(self, doc_id: str, title: str, domain: str, content: str,
                     source: str = "manual", kind: str = "text",
                     warnings: Iterable[str] = ()) -> Document:
        """Add or replace a document and re-chunk it."""
        with self._lock:
            self._remove_chunks(doc_id)
            pieces = chunk_text(content, self.chunk_size, self.chunk_overlap)
            document = Document(
                id=doc_id, title=title or doc_id, domain=domain or "",
                content=content, source=source, kind=kind,
                n_chunks=len(pieces), warnings=list(warnings),
            )
            self._documents[doc_id] = document
            for i, piece in enumerate(pieces):
                self._chunks.append(Chunk(id=f"{doc_id}::c{i}", doc_id=doc_id,
                                          content=piece, title=document.title,
                                          domain=document.domain, index=i))
            self._rebuild_bm25()
            self._invalidate_dense()
            self._save()
            return document

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id not in self._documents:
                return False
            del self._documents[doc_id]
            self._remove_chunks(doc_id)
            self._rebuild_bm25()
            self._invalidate_dense()
            self._save()
            return True

    def clear(self) -> int:
        with self._lock:
            removed = len(self._documents)
            self._documents.clear()
            self._chunks.clear()
            self._rebuild_bm25()
            self._invalidate_dense()
            self._save()
            return removed

    def _remove_chunks(self, doc_id: str) -> None:
        self._chunks = [c for c in self._chunks if c.doc_id != doc_id]

    # ── reads ──────────────────────────────────────────────────────────────
    @property
    def documents(self) -> list[Document]:
        with self._lock:
            return sorted(self._documents.values(), key=lambda d: d.created_at, reverse=True)

    @property
    def chunks(self) -> list[Chunk]:
        with self._lock:
            return list(self._chunks)

    def get_document(self, doc_id: str) -> Document | None:
        return self._documents.get(doc_id)

    def domains(self) -> list[str]:
        with self._lock:
            return sorted({d.domain for d in self._documents.values() if d.domain})

    def chunks_in(self, domains: Iterable[str] | None) -> list[Chunk]:
        """Return the chunks belonging to ``domains`` (all chunks when falsy).

        Filtering happens *after* scoring and *before* truncation, so a
        domain-scoped query still returns ``top_k`` hits instead of whatever
        survives a post-hoc cut of an already-truncated list.
        """
        with self._lock:
            if not domains:
                return list(self._chunks)
            wanted = set(domains)
            return [c for c in self._chunks if c.domain in wanted]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total_chars = sum(len(d.content) for d in self._documents.values())
            return {
                "documents": len(self._documents),
                "chunks": len(self._chunks),
                "domains": len({d.domain for d in self._documents.values() if d.domain}),
                "characters": total_chars,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "bm25_ready": self._bm25 is not None,
                "dense_ready": self._dense_ready,
                "dense_error": self._dense_error,
                "cross_encoder_ready": self._cross_encoder is not None,
            }

    # ── BM25 ───────────────────────────────────────────────────────────────
    def _rebuild_bm25(self) -> None:
        self._bm25 = None
        self._bm25_params = None
        self._bm25_tokenized = [tokenize(c.content) for c in self._chunks]

    def bm25(self, k1: float = 1.5, b: float = 0.75):
        """Return a BM25 index for the requested hyper-parameters.

        ``BM25Okapi`` bakes ``k1``/``b`` into its precomputed statistics, so the
        index is cached per parameter pair rather than rebuilt on every query.
        """
        from rank_bm25 import BM25Okapi

        if not self._bm25_tokenized:
            return None
        key = (round(float(k1), 4), round(float(b), 4))
        if self._bm25 is not None and self._bm25_params == key:
            return self._bm25
        self._bm25 = BM25Okapi(self._bm25_tokenized, k1=key[0], b=key[1])
        self._bm25_params = key
        return self._bm25

    def bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75,
                    domains: Iterable[str] | None = None) -> list[tuple[Chunk, float]]:
        """Score every in-scope chunk, best first.

        The Okapi index itself is global and cached; the domain filter is a
        mask over its output, so scoping never rebuilds the index.
        """
        index = self.bm25(k1=k1, b=b)
        if index is None:
            return []
        scores = index.get_scores(tokenize(query))
        allowed = None if not domains else {c.id for c in self.chunks_in(domains)}
        scored = [(chunk, float(score)) for chunk, score in zip(self.chunks, scores)
                  if allowed is None or chunk.id in allowed]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    # ── dense ──────────────────────────────────────────────────────────────
    def _invalidate_dense(self) -> None:
        self._dense_ready = False
        self._faiss_index = None
        self._dense_ids = []
        self._dense_error = None

    def ensure_dense(self) -> None:
        """Lazily build the embedding model + FAISS index for the whole corpus."""
        with self._lock:
            if self._dense_ready:
                return
            if not self._chunks:
                self._dense_ready = True
                return
            try:
                import faiss
                import numpy as np
                from sentence_transformers import SentenceTransformer

                if self._embedder is None:
                    settings = get_settings()
                    self._embedder = SentenceTransformer(
                        settings.embedding_model,
                        cache_folder=str(settings.hf_cache_dir)
                        if settings.hf_cache_dir.is_dir() else None,
                    )
                embeddings = self._embedder.encode(
                    [c.content for c in self._chunks],
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    batch_size=32,
                )
                matrix = np.asarray(embeddings, dtype="float32")
                index = faiss.IndexFlatIP(matrix.shape[1])
                index.add(matrix)
                self._faiss_index = index
                self._dense_ids = [c.id for c in self._chunks]
                self._dense_ready = True
                self._dense_error = None
            except Exception as exc:  # surface the reason through /api/health
                self._dense_error = f"{type(exc).__name__}: {exc}"
                self._dense_ready = False
                raise

    def encode_query(self, query: str):
        """Embed a query with the same model used for the corpus."""
        self.ensure_dense()
        if self._embedder is None:
            return None
        import numpy as np

        return np.asarray(self._embedder.encode([query], normalize_embeddings=True),
                          dtype="float32")

    def dense_search(self, query: str, top_k: int, score_threshold: float = 0.0,
                     domains: Iterable[str] | None = None):
        """Return ``[(chunk, score), ...]`` by cosine similarity.

        With a domain filter the FAISS search is widened before filtering, so
        the caller still gets up to ``top_k`` in-scope hits when out-of-scope
        neighbours would otherwise occupy the top of the ranking.
        """
        self.ensure_dense()
        if self._faiss_index is None:
            return []
        allowed = None if not domains else {c.id for c in self.chunks_in(domains)}
        if allowed is not None and not allowed:
            return []
        seek = top_k if allowed is None else min(len(self._dense_ids),
                                                 max(top_k * 20, 200))
        vector = self.encode_query(query)
        if vector is None:
            return []
        scores, indices = self._faiss_index.search(vector, seek)
        by_id = {c.id: c for c in self._chunks}
        hits = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            chunk = by_id.get(self._dense_ids[idx])
            if chunk is None:
                continue
            if allowed is not None and chunk.id not in allowed:
                continue
            value = float(score)
            if value < score_threshold:
                continue
            hits.append((chunk, value))
            if len(hits) >= top_k:
                break
        return hits

    def cross_encoder(self):
        """Lazily load the MS MARCO cross-encoder reranker."""
        with self._lock:
            if self._cross_encoder is None:
                from sentence_transformers import CrossEncoder

                self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            return self._cross_encoder

    # ── persistence ────────────────────────────────────────────────────────
    def _save(self) -> None:
        if not self.persist:
            return
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "saved_at": time.time(),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "documents": [asdict(d) for d in self._documents.values()],
        }
        tmp = self.data_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.data_file)

    def _load(self) -> None:
        if not self.data_file.is_file():
            return
        try:
            payload = json.loads(self.data_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for raw in payload.get("documents", []):
            try:
                document = Document(**raw)
            except TypeError:
                continue
            self._documents[document.id] = document
            for i, piece in enumerate(chunk_text(document.content, self.chunk_size,
                                                 self.chunk_overlap)):
                self._chunks.append(Chunk(id=f"{document.id}::c{i}", doc_id=document.id,
                                          content=piece, title=document.title,
                                          domain=document.domain, index=i))
        self._rebuild_bm25()


def minmax_norm(values: dict[str, float]) -> dict[str, float]:
    """Min-max normalise a score map into ``[0, 1]`` (a flat map maps to 1.0)."""
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if math.isclose(high, low):
        return {k: 1.0 for k in values}
    return {k: (v - low) / (high - low) for k, v in values.items()}


#: Process-wide store used by the FastAPI app.
store = DocumentStore()
