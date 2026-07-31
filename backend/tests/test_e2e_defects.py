"""Regression tests for the four E2E-test-discovered defects.

These run hermetically (no live backend / neo4j / chroma) — each monkeypatches
the minimal collaborators to assert the *behaviour* the E2E test observed
breaking:

  1. EmbeddingService used to flip ``_available`` to False on the first
     transient CUDA load error and never recover; the service stayed
     "vector service not ready" until the process was restarted.
  2. ``experience_search_smart`` MCP tool filtered its backend results by
     ``kb_id`` substring, but the backend response only carried ``kb_path`` —
     so passing a UUID ``kb_id`` silently dropped every hit.
  3. ``triggerReindexAfterMove`` deletes old-path vector/graph nodes then
     re-indexes the new path. The deletion calls must use the *source* path
     and the reindex must use the *target* path, and a failure must not be
     swallowed into a non-observable empty result.
  4. Graph queries key off ``graph_doc_id = "doc::" + path``. Passing a bare
     filename (no KB prefix) produced a different id than the one written at
     ingest (full path) and silently returned an empty graph.
"""
from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


# Each test imports its target module lazily inside the test so monkeypatching
# the import-time singletons in app.services.* actually takes effect.


# ──────────────────────────────────────────────────────────────────────────
# 1. EmbeddingService — transient load failure must remain retryable
# ──────────────────────────────────────────────────────────────────────────

class TestEmbeddingRecovery:
    def test_transient_load_failure_stays_retryable(self, monkeypatch):
        # Force config to deterministic values so the test does not touch the
        from app import config as config_mod
        monkeypatch.setitem(config_mod.config._config, "embedding", {
            "model_name": "test-model",
            "cache_dir": "./models_cache",
            "device": "cpu",
            "normalize": True,
            "batch_size": 8,
        })

        # Reload embedding_service so the patched config + fresh class state is
        # used (the module-level `embedding_service` singleton holds state).
        if "app.services.embedding_service" in sys.modules:
            del sys.modules["app.services.embedding_service"]
        es_mod = importlib.import_module("app.services.embedding_service")

        # SentenceTransformer is imported inside get_model(); replace the module
        # so the first call raises (transient CUDA/meta-tensor-like error) and a
        # later call succeeds. This mirrors the real failure mode from the E2E
        # log: "Cannot copy out of meta tensor" once, then loads on retry.
        calls = {"n": 0}

        class _FakeST:
            def __init__(self, *a, **kw):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("Cannot copy out of meta tensor; no data!")
                # Second construction succeeds and behaves like an encoder.
                self.encode_calls = 0

            def encode(self, texts, **kw):
                self.encode_calls += 1
                # Real SentenceTransformer returns a tensor/numpy with .tolist()
                class _V:
                    def __init__(s, data): s._d = data
                    def tolist(s): return list(s._d)
                return _V([[0.0, 0.1] for _ in texts])

        st_mod = types_stub("sentence_transformers", SentenceTransformer=_FakeST)
        monkeypatch.setitem(sys.modules, "sentence_transformers", st_mod)

        # Use a private instance so we don't mutate shared global state across
        # the suite.
        EmbeddingService = es_mod.EmbeddingService
        EmbeddingService._model = None
        EmbeddingService._available = True
        svc = EmbeddingService()

        # First embed triggers the transient failure → empty list, *but* the
        # service must remain usable (not permanently disabled).
        first = svc.embed(["hello"])
        assert first == []
        # RED: current implementation flips _available=False forever here.
        assert svc.is_available() is True, (
            "transient embedding load failure must not permanently disable the service"
        )

        # Second embed retries the load and succeeds.
        second = svc.embed(["hello", "world"])
        assert len(second) == 2
        assert calls["n"] == 2, "get_model must retry after a transient failure"
    def test_permanent_degradation_only_after_retry_budget(self, monkeypatch):
        from app import config as config_mod
        monkeypatch.setitem(config_mod.config._config, "embedding", {
            "model_name": "test-model", "cache_dir": "./models_cache",
            "device": "cpu", "normalize": True, "batch_size": 8,
        })
        if "app.services.embedding_service" in sys.modules:
            del sys.modules["app.services.embedding_service"]
        es_mod = importlib.import_module("app.services.embedding_service")

        class _AlwaysFails:
            def __init__(self, *a, **kw):
                raise RuntimeError("persistent CUDA OOM")

        monkeypatch.setitem(sys.modules, "sentence_transformers",
                            types_stub("sentence_transformers", SentenceTransformer=_AlwaysFails))

        EmbeddingService = es_mod.EmbeddingService
        EmbeddingService._model = None
        EmbeddingService._available = True
        EmbeddingService._load_failures = 0
        svc = EmbeddingService()

        # Up to MAX (3) attempts stay retryable.
        for i in range(es_mod.EmbeddingService._MAX_LOAD_FAILURES - 1):
            svc.embed(["x"])
            assert svc.is_available() is True, f"disabled too early at attempt {i+1}"

        # The MAX-th consecutive failure permanently degrades.
        svc.embed(["x"])
        assert svc.is_available() is False, "must give up after the retry budget"


def types_stub(name, **attrs):
    """Build a fake top-level module with the given attributes."""
    mod = SimpleNamespace()
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod
# ──────────────────────────────────────────────────────────────────────────
# 3. vector_service.delete_document — moved docs must not leave stale chunks
# ──────────────────────────────────────────────────────────────────────────

class TestMoveCleanupDeletesFromSource:
    def test_delete_resolves_path_form_to_uuid_collection(self, monkeypatch):
        """When move-cleanup calls delete_document(kb_id=<path>, doc_path),
        vector_service must resolve the path to its UUID collection and delete
        the chunks there (not silently no-op on a non-existent kb_<path>).

        This pins the BUG-3 contract: the web move path calls
        DELETE /search/document?kb_id=<source-path-or-uuid>&doc_path=<old>,
        and the backend must clean the right collection regardless of whether
        the caller passed a path or UUID.
        """
        from app.services import vector_service as vs_mod
        # vector_service resolves kb_id via a method-local import of
        # storage_reader_service.storage_reader, so patch the source module.
        from app.services import storage_reader_service as sr_mod
        fake_storage = MagicMock()
        fake_storage.list_knowledge_bases.return_value = [
            {"kb_id": "src-uuid-1234", "path": "SourceKB", "name": "SourceKB"},
        ]
        monkeypatch.setattr(sr_mod, "storage_reader", fake_storage)
        deleted = {}
        class _FakeCol:
            def __init__(self, name):
                self.name = name
                # Chroma stores chunks with an id + a metadata dict; the
                # doc_path filter keys off metadata, not the id.
                self._docs = {
                    "old/doc.md__chunk_0": {"doc_path": "old/doc.md"},
                }

            def get(self, where=None, **_kw):
                ids, metas = [], []
                want = (where or {}).get("doc_path")
                for _id, meta in self._docs.items():
                    if want is None or meta.get("doc_path") == want:
                        ids.append(_id)
                        metas.append(meta)
                return {"ids": ids, "metadatas": metas}

            def delete(self, ids=None):
                deleted.setdefault(self.name, [])
                deleted[self.name].extend(ids or [])
                for i in (ids or []):
                    self._docs.pop(i, None)

        class _FakeClient:
            def get_collection(self, name):
                if name.endswith("src-uuid-1234"):
                    return _FakeCol(name)
                raise Exception("not found")

            def get_or_create_collection(self, name, metadata=None):
                return _FakeCol(name)

            def list_collections(self):
                return []

        vs = vs_mod.VectorService()
        vs._client = _FakeClient()
        vs._ready = True

        # Caller passes a PATH kb_id (as the web move path does).
        vs.delete_document("SourceKB", "old/doc.md")

        # The delete must land on the UUID collection, not a kb_SourceKB one.
        assert "kb_src-uuid-1234" in deleted, (
            f"delete must target the UUID collection; got {list(deleted)}"
        )
        assert deleted["kb_src-uuid-1234"], "expected chunk ids to be deleted"


# ──────────────────────────────────────────────────────────────────────────
# 4. Graph doc path resolution — bare filename must resolve to full path
# ──────────────────────────────────────────────────────────────────────────

class TestGraphDocPathResolution:
    def test_bare_filename_resolves_to_full_path(self, monkeypatch):
        """BUG-4: graph lookups key on graph_doc_id = 'doc::' + path.
        Passing a bare filename ('doc.md') produces a different id than the
        one written at ingest ('KB/doc.md') and silently returns {}.
        The graph route must resolve a bare name to the full path first.
        """
        from app.services import graph_service as gs_mod
        from app.services import storage_reader_service as sr_mod

        # Fake storage_reader: list_documents returns one doc whose path
        # contains the bare filename.
        fake_storage = MagicMock()
        fake_storage.list_knowledge_bases.return_value = [
            {"kb_id": "k1", "path": "AI-ML-Research", "name": "AI-ML-Research"},
            {"kb_id": "k2", "path": "Materials-Science", "name": "Materials-Science"},
        ]
        fake_storage.list_documents.return_value = [
            {"path": "AI-ML-Research/doc.md", "name": "doc.md"},
        ]
        monkeypatch.setattr(sr_mod, "storage_reader", fake_storage)

        gs = gs_mod.GraphService()
        # The resolver helper must exist (added by the fix).
        assert hasattr(gs, "_resolve_doc_path"), (
            "graph_service must expose _resolve_doc_path to normalise bare names"
        )
        resolved = gs._resolve_doc_path("doc.md")
        assert resolved == "AI-ML-Research/doc.md", (
            f"bare filename must resolve to full kb-prefixed path; got {resolved!r}"
        )

    def test_full_path_passes_through_unchanged(self, monkeypatch):
        from app.services import graph_service as gs_mod
        from app.services import storage_reader_service as sr_mod
        fake_storage = MagicMock()
        monkeypatch.setattr(sr_mod, "storage_reader", fake_storage)
        gs = gs_mod.GraphService()
        full = "AI-ML-Research/doc.md"
        assert gs._resolve_doc_path(full) == full
        fake_storage.list_documents.assert_not_called()
