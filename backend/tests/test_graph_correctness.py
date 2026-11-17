"""Hermetic graph correctness regression tests (no Neo4j or KB writes)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def graph_modules():
    from app.services import graph_service as service_module
    from app.services import storage_reader_service as storage_module

    return service_module, storage_module


def test_build_error_from_index_document_is_not_marked_and_is_retryable(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    storage.list_documents.return_value = [{"path": "KB/doc.md", "name": "doc.md", "tags": []}]
    monkeypatch.setattr(storage_module, "storage_reader", storage)

    service = service_module.GraphService()
    monkeypatch.setattr(service, "index_document", lambda **_: {"error": "Neo4j write failed", "graph_doc_id": "doc::KB/doc.md"})
    result = service._build_single_kb_docs("kb-1", "KB", force=False)

    assert result["docs_processed"] == 0
    assert result["errors"] == [{"doc_path": "KB/doc.md", "reason": "Neo4j write failed"}]
    storage.update_document_graph_index.assert_not_called()

    storage.update_document_graph_index.return_value = True
    monkeypatch.setattr(service, "index_document", lambda **_: {"graph_doc_id": "doc::KB/doc.md", "tag_count": 0})
    retry = service._build_single_kb_docs("kb-1", "KB", force=False)
    assert retry["docs_processed"] == 1
    assert retry["errors"] == []


def test_index_success_with_zero_relations_persists_marker(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    storage.list_documents.return_value = [{"path": "KB/alone.md", "name": "alone.md", "tags": []}]
    storage.update_document_graph_index.return_value = True
    monkeypatch.setattr(storage_module, "storage_reader", storage)

    service = service_module.GraphService()
    monkeypatch.setattr(service, "index_document", lambda **_: {
        "success": True,
        "graph_doc_id": "doc::KB/alone.md",
        "tag_count": 0,
        "vector_relations": 0,
        "agent_relations": 0,
        "shared_tag_relations": 0,
    })
    result = service._build_single_kb_docs("kb-1", "KB", force=False)

    assert result["docs_processed"] == 1
    assert result["errors"] == []
    assert result["total_relations"] == 0
    storage.update_document_graph_index.assert_called_once()


def test_marker_writeback_failure_is_reported_and_not_counted(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    storage.list_documents.return_value = [{"path": "KB/doc.md", "name": "doc.md", "tags": []}]
    storage.update_document_graph_index.return_value = False
    monkeypatch.setattr(storage_module, "storage_reader", storage)

    service = service_module.GraphService()
    monkeypatch.setattr(service, "index_document", lambda **_: {
        "success": True, "graph_doc_id": "doc::KB/doc.md", "tag_count": 0,
    })
    result = service._build_single_kb_docs("kb-1", "KB", force=False)

    assert result["docs_processed"] == 0
    assert "persist graph_index marker" in result["errors"][0]["reason"]


def test_bare_name_resolution_is_separator_normalized_and_rejects_collisions(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    storage.list_knowledge_bases.return_value = [
        {"kb_id": "1", "path": "First"},
        {"kb_id": "2", "path": "Second"},
    ]
    storage.list_documents.side_effect = [
        [{"path": r"First\doc.md", "name": "doc.md"}],
        [{"path": "Second/doc.md", "name": "doc.md"}],
    ]
    monkeypatch.setattr(storage_module, "storage_reader", storage)

    service = service_module.GraphService()
    with pytest.raises(service_module.AmbiguousDocumentPath, match="use a full path"):
        service._resolve_doc_path("doc.md")
    assert service._resolve_doc_path(r"First\doc.md") == "First/doc.md"


def test_document_graph_reports_missing_vs_existing_unrelated_document(monkeypatch, graph_modules):
    service_module, _ = graph_modules
    service = service_module.GraphService()

    class Record(dict):
        pass

    class FakeResult:
        def __init__(self, value):
            self.value = value

        def single(self):
            return self.value

        def __iter__(self):
            return iter(())

    class FakeSession:
        def __init__(self, exists):
            self.exists = exists

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def run(self, query, **kwargs):
            if "OPTIONAL MATCH" in query:
                return FakeResult(Record({"graph_doc_id": "doc::KB/alone.md", "path": "KB/alone.md", "tags": []}) if self.exists else None)
            return FakeResult(())

    class FakeDriver:
        def __init__(self, exists):
            self.exists = exists

        def session(self, **kwargs):
            return FakeSession(self.exists)

    service._driver = FakeDriver(True)
    existing = service.get_document_graph("KB/alone.md")
    service._driver = FakeDriver(False)
    missing = service.get_document_graph("KB/missing.md")

    assert existing["document_found"] is True
    assert existing["related_count"] == 0
    assert missing["document_found"] is False
    assert missing["related_count"] == 0


def test_kb_build_reports_document_failures(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    storage.get_kb_parent.return_value = None
    storage.list_sub_kbs.return_value = []
    monkeypatch.setattr(storage_module, "storage_reader", storage)
    service = service_module.GraphService()
    service._driver = MagicMock()
    service._driver.session.return_value.__enter__.return_value.run.return_value.single.return_value = {"cnt": 0}
    monkeypatch.setattr(service, "_resolve_kb_path", lambda _: "KB")
    monkeypatch.setattr(service, "_resolve_kb_id", lambda _: "kb-1")
    monkeypatch.setattr(service, "_ensure_schema", lambda _: None)
    monkeypatch.setattr(service, "_build_single_kb_docs", lambda *a: {
        "docs_processed": 0, "docs_skipped": 0, "total_relations": 0,
        "errors": [{"doc_path": "KB/doc.md", "reason": "write failed"}],
    })
    monkeypatch.setattr(service, "_relate_kbs_by_tags", lambda *a: None)
    monkeypatch.setattr(service, "_build_vector_similarity_edges", lambda **kw: {"errors": []})
    result = service.build_kb_graph("kb-1")
    assert result["success"] is False
    assert result["errors"][0]["reason"] == "write failed"


def test_force_failure_clears_marker_before_delete(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    doc = {"path": "KB/doc.md", "graph_index": {"graph_doc_id": "doc::KB/doc.md"}}
    storage.list_sub_kbs.return_value = []
    storage.list_documents.return_value = [doc]
    storage.update_document_graph_index.return_value = True
    monkeypatch.setattr(storage_module, "storage_reader", storage)
    service = service_module.GraphService()
    monkeypatch.setattr(service, "_resolve_kb_path", lambda _: "KB")
    monkeypatch.setattr(service, "_resolve_kb_id", lambda _: "kb-1")

    def failed_delete(_):
        storage.update_document_graph_index.assert_called_once_with("KB", "KB/doc.md", {})
        raise RuntimeError("delete failed")

    monkeypatch.setattr(service, "delete_kb_graph", failed_delete)
    result = service.build_kb_graph("kb-1", force=True)
    assert result["success"] is False
    assert "delete failed" in result["errors"][0]["reason"]


def test_graph_routes_report_status_and_ambiguous_paths(monkeypatch, graph_modules):
    import asyncio
    from fastapi import HTTPException
    from app.api.routes import graph as routes

    service_module, _ = graph_modules
    fake = MagicMock()
    monkeypatch.setattr(routes, "graph_service", fake)
    monkeypatch.setattr(routes, "_guard_graph_enabled", lambda: None)
    fake.build_kb_graph.return_value = {"success": False, "errors": [{"reason": "write failed"}]}
    fake.build_all_graphs.return_value = {"success": False}
    assert asyncio.run(routes.graph_build_kb(routes.BuildKbGraphRequest(kb_id="1")))["success"] is False
    assert asyncio.run(routes.graph_build_all(routes.BuildAllGraphsRequest()))["success"] is False
    fake.get_related_documents.return_value = []
    fake.document_exists.return_value = True
    response = asyncio.run(routes.graph_related_documents("KB/doc.md"))
    assert response["found"] is True and response["related"] == []
    fake.get_document_graph.side_effect = service_module.AmbiguousDocumentPath("doc.md", ["A/doc.md", "B/doc.md"])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.graph_for_document("doc.md"))
    assert exc.value.status_code == 409


def test_failed_marker_is_retried(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    doc = {"path": "KB/doc.md", "graph_index": {"error": "old failure"}}
    storage.list_documents.return_value = [doc]
    storage.update_document_graph_index.return_value = True
    monkeypatch.setattr(storage_module, "storage_reader", storage)
    service = service_module.GraphService()
    monkeypatch.setattr(service, "index_document", lambda **_: {"graph_doc_id": "doc::KB/doc.md", "tag_count": 0})
    result = service._build_single_kb_docs("kb-1", "KB", force=False)
    assert result["docs_processed"] == 1
    assert result["docs_skipped"] == 0
    assert storage.update_document_graph_index.call_args_list[0].args == ("KB", "KB/doc.md", {})


@pytest.fixture
def graph_build_harness(monkeypatch, graph_modules):
    service_module, storage_module = graph_modules
    storage = MagicMock()
    storage.list_knowledge_bases.return_value = [
        {"kb_id": "k1", "path": "First", "parent_id": None},
        {"kb_id": "child", "path": "First/Child", "parent_id": "k1"},
        {"kb_id": "k2", "path": "Second", "parent_id": None},
    ]
    storage.list_sub_kbs.side_effect = lambda kid: (
        [{"kb_id": "child", "path": "First/Child"}] if kid == "k1" else []
    )
    storage.get_kb_parent.return_value = None
    storage.list_documents.return_value = []
    monkeypatch.setattr(storage_module, "storage_reader", storage)
    service = service_module.GraphService()
    service._driver = MagicMock()
    service._driver.session.return_value.__enter__.return_value.run.return_value.single.return_value = {"cnt": 0}
    monkeypatch.setattr(service, "_resolve_kb_path", lambda kid: {"k1": "First", "k2": "Second"}[kid])
    monkeypatch.setattr(service, "_resolve_kb_id", lambda kid: kid)
    monkeypatch.setattr(service, "_ensure_schema", lambda _: None)
    monkeypatch.setattr(service, "delete_kb_graph", lambda _: None)
    events = []
    def build_docs(kid, path, force, parent_kb_id=""):
        events.append(("docs", kid))
        return {"docs_processed": 0, "docs_skipped": 0, "total_relations": 0, "errors": []}
    def build_vectors(*args, **kwargs):
        events.append(("vector", args, kwargs))
        return {"enabled": True, "total_edges": 0, "cross_kb_edges": 0, "errors": []}
    monkeypatch.setattr(service, "_build_single_kb_docs", build_docs)
    monkeypatch.setattr(service, "_build_vector_similarity_edges", build_vectors)
    monkeypatch.setattr(service, "_relate_kbs_by_tags", lambda *args: None)
    monkeypatch.setattr(service, "_relate_all_kbs_comprehensive", lambda: {})
    return service, events


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
def test_build_all_similarity_runs_once_globally_only_when_enabled(graph_build_harness, force, enabled):
    service, events = graph_build_harness
    result = service.build_all_graphs(force=force, enable_vector_similarity=enabled)
    vectors = [event for event in events if event[0] == "vector"]
    assert result["success"] is True
    assert [event[1] for event in events if event[0] == "docs"] == ["k1", "child", "k2"]
    if enabled:
        assert vectors == [("vector", (force,), {})]
        assert events[-1] == vectors[0]
    else:
        assert vectors == []
        assert result["phase2_vector_similarity"]["enabled"] is False


@pytest.mark.parametrize("force", [False, True])
def test_direct_kb_build_can_disable_similarity(graph_build_harness, force):
    service, events = graph_build_harness
    result = service.build_kb_graph("k1", force=force, enable_vector_similarity=False)
    assert result["success"] is True
    assert not [event for event in events if event[0] == "vector"]


@pytest.mark.parametrize("force", [False, True])
def test_direct_kb_build_runs_scoped_similarity_by_default(graph_build_harness, force):
    service, events = graph_build_harness
    result = service.build_kb_graph("k1", force=force)
    assert result["success"] is True
    assert [event for event in events if event[0] == "vector"] == [
        ("vector", (), {"force": force, "kb_id": "k1"})
    ]
