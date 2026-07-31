"""Regression tests for the live E2E test defects fixed on 2026-07-31.

Hermetic (no live backend / neo4j / chroma / mineru) — monkeypatches the
minimal collaborators and asserts the *behaviour* that broke:

  F1. Concurrent create + auto-index writebacks lost documents from
      .knowledge-base.yml — cross-process RMW race between web (Nitro) and
      backend (FastAPI). Fix: shared lock-file protocol (file_lock.py /
      web file-lock.ts). Here: two independent lock owners must serialize.
  F1b. Concurrent vector_index writebacks must not lose entries.
  F2. kb_doc_move / auto-index built graph nodes without HAS_TAG edges —
      index_document now falls back to YAML tags when the caller passes none.
      (Covered indirectly by resolve/owner tests + route-level fallback helper.)
  F3a. Sub-KB docs' YAML writebacks must land in the sub-KB's own YAML —
      storage_reader.resolve_kb_path_for_doc (longest-prefix owner resolution).
  F4. two_stage search must NOT fall back to global vector noise when stage1
      (BM25) yields zero candidates for a query.
  F5. parse_doc must reject empty parse results instead of success-with-blank.
  F6. check_stale must clear needs_sync once an experience is fresh again.
"""
from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ──────────────────────────────────────────────────────────────────────────
# F1 — file lock serializes concurrent read-modify-write across owners
# ──────────────────────────────────────────────────────────────────────────

class TestFileLockCrossOwnerSerialization:
    def test_two_lock_owners_do_not_lose_updates(self, tmp_path: Path):
        """Two FileLock instances (as if two processes) incrementing a shared
        JSON counter concurrently must end at exactly N (no lost updates)."""
        from app.utils.file_lock import FileLock

        target = tmp_path / "counter.json"
        target.write_text(json.dumps({"n": 0}), encoding="utf-8")
        lock_path = tmp_path / "counter.json.lock"

        n_threads = 8
        increments_per_thread = 25

        def worker() -> None:
            for _ in range(increments_per_thread):
                # Owner A and owner B are *different* FileLock objects on the
                # same lock path — the cross-process scenario in one process.
                with FileLock(lock_path, timeout=30.0):
                    data = json.loads(target.read_text(encoding="utf-8"))
                    time.sleep(0.001)  # widen the RMW window
                    data["n"] += 1
                    target.write_text(json.dumps(data), encoding="utf-8")

        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            list(pool.map(lambda _: worker(), range(n_threads)))

        final = json.loads(target.read_text(encoding="utf-8"))
        assert final["n"] == n_threads * increments_per_thread, (
            f"lost updates: {final['n']} != {n_threads * increments_per_thread}"
        )

    def test_stale_lock_is_stealable(self, tmp_path: Path):
        """A lock file older than stale_after must be stolen, not deadlock."""
        from app.utils.file_lock import FileLock

        lock_path = tmp_path / "x.lock"
        lock_path.write_text("9999 0", encoding="utf-8")  # ancient PID/timestamp
        old = time.time() - 3600
        import os
        os.utime(lock_path, (old, old))

        with FileLock(lock_path, timeout=5.0, stale_after=30.0):
            assert lock_path.exists()
        assert not lock_path.exists(), "lock must be released after use"

    def test_lock_timeout_raises(self, tmp_path: Path):
        from app.utils.file_lock import FileLock, FileLockTimeoutError

        lock_path = tmp_path / "held.lock"
        lock_path.write_text("1 0", encoding="utf-8")  # fresh, not stale

        with pytest.raises(FileLockTimeoutError):
            with FileLock(lock_path, timeout=0.15, stale_after=3600):
                pass


# ──────────────────────────────────────────────────────────────────────────
# F1b — concurrent vector_index writebacks must not lose entries
# ──────────────────────────────────────────────────────────────────────────

def _make_tree(tmp_path: Path, kb_name: str = "KB", kb_id: str = "kb-uuid-1") -> None:
    tree = {
        "folders": [{
            "id": kb_id, "name": kb_name, "path": kb_name,
            "parentId": None, "isKnowledgeBase": True,
        }],
        "files": [],
    }
    (tmp_path / ".tree-fs.json").write_text(json.dumps(tree), encoding="utf-8")


class TestConcurrentVectorIndexWriteback:
    def test_parallel_writebacks_keep_both_docs(self, tmp_path: Path, monkeypatch):
        from app.services import storage_reader_service as sr_mod

        monkeypatch.setattr(sr_mod, "get_storage_root", lambda: tmp_path)
        kb = "KB"
        (tmp_path / kb).mkdir(parents=True)
        yml = tmp_path / kb / ".knowledge-base.yml"
        yml.write_text(
            "knowledge_base:\n  id: kb-uuid-1\n  path: KB\n  name: KB\n  total_documents: 2\n"
            "documents:\n"
            "  - id: d1\n    name: a.md\n    path: KB/a.md\n    file_type: md\n"
            "  - id: d2\n    name: b.md\n    path: KB/b.md\n    file_type: md\n",
            encoding="utf-8",
        )
        # Reset the singleton's tree cache so the tmp tree is picked up.
        sr_mod.storage_reader._tree_fs_cache = None
        sr_mod.storage_reader._tree_fs_mtime = None

        def write_one(doc: str) -> None:
            ok = sr_mod.storage_reader.update_document_vector_index(
                kb_path=kb, doc_path=f"KB/{doc}",
                vector_index={"collection": f"col-{doc}", "total_chunks": 3},
            )
            assert ok

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(write_one, ["a.md", "b.md"]))

        data = json.loads(
            json.dumps(__import__("yaml").safe_load(yml.read_text(encoding="utf-8")))
        )
        idx = {d["path"]: d.get("vector_index") for d in data["documents"]}
        assert idx.get("KB/a.md", {}).get("total_chunks") == 3, idx
        assert idx.get("KB/b.md", {}).get("total_chunks") == 3, idx


# ──────────────────────────────────────────────────────────────────────────
# F3a — resolve_kb_path_for_doc: sub-KB docs own their own YAML
# ──────────────────────────────────────────────────────────────────────────

class TestResolveKbPathForDoc:
    def _make_hierarchical_tree(self, tmp_path: Path):
        (tmp_path / "Parent" / "Child").mkdir(parents=True)
        tree = {
            "folders": [
                {"id": "p-uuid", "name": "Parent", "path": "Parent", "parentId": None, "isKnowledgeBase": True},
                {"id": "c-uuid", "name": "Child", "path": "Parent\\Child", "parentId": "p-uuid", "isKnowledgeBase": True},
            ],
            "files": [],
        }
        (tmp_path / ".tree-fs.json").write_text(json.dumps(tree), encoding="utf-8")

    def test_sub_kb_doc_resolves_to_sub_kb(self, tmp_path: Path, monkeypatch):
        from app.services import storage_reader_service as sr_mod
        monkeypatch.setattr(sr_mod, "get_storage_root", lambda: tmp_path)
        self._make_hierarchical_tree(tmp_path)
        sr_mod.storage_reader._tree_fs_cache = None
        sr_mod.storage_reader._tree_fs_mtime = None

        owner = sr_mod.storage_reader.resolve_kb_path_for_doc(
            "Parent/Child/doc.md", kb_id="p-uuid")
        assert owner == "Parent\\Child" or owner == "Parent/Child", owner

    def test_root_doc_resolves_to_root_kb(self, tmp_path: Path, monkeypatch):
        from app.services import storage_reader_service as sr_mod
        monkeypatch.setattr(sr_mod, "get_storage_root", lambda: tmp_path)
        self._make_hierarchical_tree(tmp_path)
        sr_mod.storage_reader._tree_fs_cache = None
        sr_mod.storage_reader._tree_fs_mtime = None

        owner = sr_mod.storage_reader.resolve_kb_path_for_doc(
            "Parent/doc.md", kb_id="p-uuid")
        assert owner.lower().replace("\\", "/") == "parent", owner

    def test_unknown_doc_falls_back_to_kb_id(self, tmp_path: Path, monkeypatch):
        from app.services import storage_reader_service as sr_mod
        monkeypatch.setattr(sr_mod, "get_storage_root", lambda: tmp_path)
        self._make_hierarchical_tree(tmp_path)
        sr_mod.storage_reader._tree_fs_cache = None
        sr_mod.storage_reader._tree_fs_mtime = None

        owner = sr_mod.storage_reader.resolve_kb_path_for_doc(
            "SomewhereElse/doc.md", kb_id="c-uuid")
        assert owner.lower().replace("\\", "/") == "parent/child", owner


# ──────────────────────────────────────────────────────────────────────────
# F4 — two-stage: no global vector fallback on empty stage1
# ──────────────────────────────────────────────────────────────────────────

class TestTwoStageNoVectorNoiseFallback:
    def test_gibberish_query_returns_empty(self, monkeypatch):
        from app import config as config_mod
        from app.services import two_stage_search_service as tss_mod

        # Deterministic config: graph off, small top-k.
        monkeypatch.setitem(config_mod.config._config, "two_stage", {
            "stage1_top_k": 20, "stage2_top_k": 5,
            "stage1_keyword_weight": 0.5, "stage1_graph_weight": 0.5,
            "min_candidates": 3,
        })
        monkeypatch.setitem(config_mod.config._config, "graph", {"enabled": False})

        svc = tss_mod.two_stage_search_service
        svc._keyword_built = True  # skip BM25 build
        monkeypatch.setattr(tss_mod.keyword_index_service, "search",
                            lambda *a, **k: [])

        def _boom(*a, **k):
            raise AssertionError("global vector fallback must not run for empty stage1")

        monkeypatch.setattr(tss_mod.vector_service, "search", _boom)
        monkeypatch.setattr(tss_mod.vector_service, "search_in_documents", _boom)

        result = svc.search("qzxvklm123", kb_id="SomeKB")
        assert result["total_results"] == 0
        assert result["stage1"]["candidate_count"] == 0

    def test_one_candidate_still_broadens_via_vector(self, monkeypatch):
        """1–2 BM25 candidates should still get the (legit) global vector
        broadening — only the zero-candidate path is gated."""
        from app import config as config_mod
        from app.services import two_stage_search_service as tss_mod

        monkeypatch.setitem(config_mod.config._config, "two_stage", {
            "stage1_top_k": 20, "stage2_top_k": 5,
            "stage1_keyword_weight": 0.5, "stage1_graph_weight": 0.5,
            "min_candidates": 3,
        })
        monkeypatch.setitem(config_mod.config._config, "graph", {"enabled": False})

        svc = tss_mod.two_stage_search_service
        svc._keyword_built = True
        monkeypatch.setattr(
            tss_mod.keyword_index_service, "search",
            lambda *a, **k: [{"doc_path": "KB/only.md", "score": 8.0,
                              "name": "only", "source": "keyword"}])

        seen = {}
        def fake_search(query, kb_id=None, top_k=5, score_threshold=None, balance_kbs=False):
            seen["called"] = True
            return [{"content": "hit", "doc_path": "KB/only.md", "score": 0.7,
                     "chunk_index": 0, "kb_id": kb_id}]
        monkeypatch.setattr(tss_mod.vector_service, "search", fake_search)

        result = svc.search("legit query", kb_id="KB")
        assert seen.get("called") is True
        assert result["total_results"] >= 1


# ──────────────────────────────────────────────────────────────────────────
# F5 — empty parse results are rejected
# ──────────────────────────────────────────────────────────────────────────

class TestMineruEmptyParseRejected:
    def test_blank_payload_fails_instead_of_succeeding(self, tmp_path: Path):
        from unittest.mock import AsyncMock
        from app.services.mineru_service import MineruParseService

        manager = AsyncMock()
        manager.submit_task.return_value = {"task_id": "t-empty"}
        manager.wait_for_task.return_value = {
            "results": {"blank": {"md_content": "", "images": {}}},
        }

        svc = MineruParseService(manager)
        result = asyncio.run(svc.parse_async(
            b"fake", "blank.png", tmp_path / "out", poll_interval=0.01, poll_timeout=5.0,
        ))
        assert result.success is False
        assert "Empty parse result" in (result.error or "")

    def test_whitespace_only_payload_fails(self, tmp_path: Path):
        from unittest.mock import AsyncMock
        from app.services.mineru_service import MineruParseService

        manager = AsyncMock()
        manager.submit_task.return_value = {"task_id": "t-ws"}
        manager.wait_for_task.return_value = {
            "results": {"blank": {"md_content": "   \n\t  ", "images": {}}},
        }

        svc = MineruParseService(manager)
        result = asyncio.run(svc.parse_async(
            b"fake", "blank.pdf", tmp_path / "out", poll_interval=0.01, poll_timeout=5.0,
        ))
        assert result.success is False
        assert "Empty parse result" in (result.error or "")


# ──────────────────────────────────────────────────────────────────────────
# F3c-2 — vector collection must follow the DOC's owning KB (R3 regression)
# ──────────────────────────────────────────────────────────────────────────

class TestVectorOwnerResolution:
    def test_parent_kb_id_indexes_sub_kb_doc_into_sub_kb_collection(self, monkeypatch):
        """R3 finding: kb_doc_update_content(kb_id=<parent>, doc in sub-KB)
        wrote new chunks into the PARENT collection while old chunks stayed in
        the sub-KB collection (split vectors). The route must resolve the
        vector kb_id from the doc's actual owning KB, not the caller's kb_id.
        """
        from app.api.routes import search as search_mod
        from app.models.search_models import IndexDocumentRequest

        class FakeStorage:
            def resolve_kb_path_for_doc(self, doc_path, kb_id=""):
                return "Parent\\Child"

            def resolve_kb_uuid_for_path(self, kb_path):
                assert kb_path == "Parent\\Child", kb_path
                return "child-uuid-1234"

            def get_document_metadata(self, kb_path, doc_path):
                return {"tags": ["t1"]}

            def read_document_content(self, doc_path):
                return "# content"

            def list_knowledge_bases(self):
                return [{"kb_id": "parent-uuid", "path": "Parent"}]

            def update_document_vector_index(self, kb_path, doc_path, vector_index):
                return True

            def update_document_graph_index(self, kb_path, doc_path, graph_index):
                return True

        seen = {}

        class FakeVS:
            def index_document(self, kb_id, doc_path, content, metadata=None):
                seen["kb_id"] = kb_id
                seen["doc_path"] = doc_path
                return {"collection": f"kb_{kb_id}", "total_chunks": 1}

        monkeypatch.setattr(search_mod, "storage_reader", FakeStorage())
        monkeypatch.setattr(search_mod, "_get_vs", lambda: FakeVS())
        monkeypatch.setitem(search_mod.config._config, "graph", {"enabled": False})

        req = IndexDocumentRequest(
            kb_id="parent-uuid", doc_path="Parent/Child/doc.md")
        asyncio.run(search_mod.index_document(req))

        assert seen["kb_id"] == "child-uuid-1234", seen
        assert seen["doc_path"] == "Parent/Child/doc.md", seen

    def test_batch_index_uses_owner_collection_per_doc(self, monkeypatch):
        from app.api.routes import search as search_mod
        from app.models.search_models import BatchIndexDocumentRequest

        class FakeStorage:
            def resolve_kb_path_for_doc(self, doc_path, kb_id=""):
                return "Parent\\Child"

            def resolve_kb_uuid_for_path(self, kb_path):
                return "child-uuid-1234"

            def get_document_metadata(self, kb_path, doc_path):
                return {"vector_index": None}

            def read_document_content(self, doc_path):
                return "# batch content"

            def list_knowledge_bases(self):
                return [{"kb_id": "parent-uuid", "path": "Parent"}]

        seen = {}

        class FakeVS:
            def index_document(self, kb_id, doc_path, content, metadata=None):
                seen["kb_id"] = kb_id
                return {"collection": f"kb_{kb_id}", "total_chunks": 1}

        monkeypatch.setattr(search_mod, "storage_reader", FakeStorage())
        monkeypatch.setattr(search_mod, "_get_vs", lambda: FakeVS())

        req = BatchIndexDocumentRequest(
            kb_id="parent-uuid",
            doc_paths=["Parent/Child/doc-a.md", "Parent/Child/doc-b.md"],
        )
        asyncio.run(search_mod.batch_index_documents(req))

        assert seen["kb_id"] == "child-uuid-1234", seen


# ──────────────────────────────────────────────────────────────────────────
# F8 — delete_kb must drop BOTH UUID and path-named collections
# ──────────────────────────────────────────────────────────────────────────

class TestDeleteKbCleansBothForms:
    def test_stale_path_cache_does_not_leave_ghost_collection(self, monkeypatch):
        """Bug: _canonical_kb_id caches path→UUID; after the KB is deleted the
        cache still resolves the path to the (now gone) UUID collection, so
        delete_kb('path') kept deleting the UUID collection and left the
        path-named ghost (kb_E2E-Integration-Test) behind forever.
        """
        from unittest.mock import MagicMock
        from app.services import vector_service as vs_mod

        vs = vs_mod.VectorService()
        # stale cache: path resolved before the KB was deleted
        vs._kb_id_cache = {"E2E-Integration-Test": "1eb3a7d9-5d05-4992-9ea1-d1198f94cc9c"}
        deleted = []
        fake_client = MagicMock()
        fake_client.delete_collection.side_effect = lambda name: deleted.append(name)
        vs._client = fake_client

        vs.delete_kb("E2E-Integration-Test")

        assert "kb_E2E-Integration-Test" in deleted, deleted
        assert any("1eb3a7d9" in n for n in deleted), deleted

    def test_uuid_form_also_drops_cached_path_collection(self, monkeypatch):
        from unittest.mock import MagicMock
        from app.services import vector_service as vs_mod

        vs = vs_mod.VectorService()
        vs._kb_id_cache = {"Old-Name": "abc-1234"}
        deleted = []
        fake_client = MagicMock()
        fake_client.delete_collection.side_effect = lambda name: deleted.append(name)
        vs._client = fake_client

        vs.delete_kb("abc-1234")

        assert "kb_Old-Name" in deleted, deleted
        assert "kb_abc-1234" in deleted, deleted


# ──────────────────────────────────────────────────────────────────────────
# F6 — check_stale clears needs_sync when fresh
# ──────────────────────────────────────────────────────────────────────────

class TestNeedsSyncClearedOnFresh:
    def test_resolved_experience_loses_needs_sync(self, tmp_path: Path, monkeypatch):
        from app.services import experience_service as exp_mod
        monkeypatch.setattr(exp_mod, "get_storage_root", lambda: tmp_path)

        kb_name = "KB"
        (tmp_path / kb_name / "experience").mkdir(parents=True)
        (tmp_path / ".tree-fs.json").write_text(json.dumps({
            "folders": [{"id": "kb-uuid", "name": kb_name, "path": kb_name,
                         "parentId": None, "isKnowledgeBase": True}],
            "files": [],
        }), encoding="utf-8")

        # related doc with OLD mtime → experience is fresh (not stale)
        doc = tmp_path / kb_name / "doc.md"
        doc.write_text("# doc", encoding="utf-8")
        old = time.time() - 86400
        import os
        os.utime(doc, (old, old))

        index_path = tmp_path / kb_name / "experience" / ".experience-index.yml"
        index_path.write_text(
            "experiences:\n"
            "  - id: exp-1\n"
            "    title: t\n"
            "    updated_at: '2026-07-31T00:00:00+00:00'\n"
            "    related_docs:\n"
            "      - KB/doc.md\n"
            "    needs_sync: true\n"
            "    sync_requested_at: '2026-07-31T00:00:00+00:00'\n",
            encoding="utf-8",
        )

        svc = exp_mod.ExperienceService()
        result = asyncio.run(svc.check_stale(kb_name))
        assert result["fresh"] == 1, result
        assert result["stale"] == 0, result

        # needs_sync must have been cleared in the persisted index
        import yaml
        data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        exp = data["experiences"][0]
        assert exp.get("needs_sync") is False, exp
        assert "sync_requested_at" not in exp, exp

    def test_stale_experience_keeps_needs_sync(self, tmp_path: Path, monkeypatch):
        from app.services import experience_service as exp_mod
        monkeypatch.setattr(exp_mod, "get_storage_root", lambda: tmp_path)

        kb_name = "KB"
        (tmp_path / kb_name / "experience").mkdir(parents=True)
        (tmp_path / ".tree-fs.json").write_text(json.dumps({
            "folders": [{"id": "kb-uuid", "name": kb_name, "path": kb_name,
                         "parentId": None, "isKnowledgeBase": True}],
            "files": [],
        }), encoding="utf-8")

        # related doc with NEW mtime → experience stays stale → keep needs_sync
        doc = tmp_path / kb_name / "doc.md"
        doc.write_text("# doc", encoding="utf-8")

        index_path = tmp_path / kb_name / "experience" / ".experience-index.yml"
        index_path.write_text(
            "experiences:\n"
            "  - id: exp-1\n"
            "    title: t\n"
            "    updated_at: '2026-07-30T00:00:00+00:00'\n"
            "    related_docs:\n"
            "      - KB/doc.md\n"
            "    needs_sync: true\n",
            encoding="utf-8",
        )

        svc = exp_mod.ExperienceService()
        result = asyncio.run(svc.check_stale(kb_name))
        assert result["stale"] == 1, result

        import yaml
        data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        assert data["experiences"][0].get("needs_sync") is True
