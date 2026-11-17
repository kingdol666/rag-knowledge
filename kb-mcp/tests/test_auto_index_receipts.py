"""Hermetic tests for parsed-save indexing receipts and background task outcomes."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import server
import task_registry
from kb_client.client import KbClient


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    monkeypatch.setattr(task_registry, "_persist", lambda record: None)
    monkeypatch.setattr(task_registry, "_records", {})
    monkeypatch.setattr(task_registry, "_handles", {})


async def finish(task_id):
    handle = task_registry._handles.get(task_id)
    if handle:
        await handle
    return task_registry.public_view(task_registry.get(task_id))


@pytest.mark.asyncio
@pytest.mark.parametrize("response,expected", [
    ({"success": False, "error": "HTTP request timed out", "status": 504,
      "error_kind": "timeout", "timeout_type": "ReadTimeout"}, "ReadTimeout"),
    ({"success": False, "error": "backend unavailable", "status": 503}, "503"),
    ({"success": True, "vector_index": {}}, "did not confirm vector chunks"),
    ({"success": True, "vector_index": {"collection": "kb_x", "total_chunks": 0}}, "did not confirm vector chunks"),
    (None, "index request failed"),
])
async def test_index_failure_has_error_registry_receipt(monkeypatch, response, expected):
    monkeypatch.setattr(server, "_client", lambda: SimpleNamespace(index_document=AsyncMock(return_value=response)))
    tid = task_registry.submit(server._auto_index_doc("kb", "kb/doc.md"), "auto-index")
    view = await finish(tid)
    assert view["status"] == "error"
    assert expected in view["error"]
    assert view["result"] is None


@pytest.mark.asyncio
async def test_index_exception_is_recorded(monkeypatch):
    monkeypatch.setattr(server, "_client", lambda: SimpleNamespace(index_document=AsyncMock(side_effect=ValueError("broken"))))
    tid = task_registry.submit(server._auto_index_doc("kb", "kb/doc.md"), "auto-index")
    view = await finish(tid)
    assert view["status"] == "error"
    assert "ValueError: broken" in view["error"]


@pytest.mark.asyncio
async def test_actual_http_timeout_surfaces_in_task(monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout("private detail", request=request)
    client = KbClient(backend_url="https://backend.invalid")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    monkeypatch.setattr(server, "_client", lambda: client)
    try:
        tid = task_registry.submit(server._auto_index_doc("kb", "kb/doc.md"), "auto-index")
        view = await finish(tid)
    finally:
        await client.aclose()
    assert view["status"] == "error"
    assert "ReadTimeout" in view["error"] and "504" in view["error"]
    assert "private detail" not in view["error"]


@pytest.mark.asyncio
async def test_partial_save_schedules_only_successful_new_files_once(monkeypatch):
    good = {"path": "kb/good.md"}
    bad = {"path": "kb/partial.md"}
    duplicate = {"path": "kb/existing.md", "deduped": True}
    receipt = {"success": False, "savedCount": 3, "failedCount": 1,
               "files": [good, bad, duplicate, {"path": "kb/unconfirmed.md"}],
               "items": [
                   {"success": True, "files": [good, {"path": "kb\\good.md"}, duplicate]},
                   {"success": False, "error": "metadata failed", "files": [bad]},
                   {"success": False, "error": "upload outcome uncertain", "files": []},
               ]}
    index_result = {"success": True, "vector_index": {"collection": "kb_x", "total_chunks": 2}}
    client = SimpleNamespace(save_parsed_files=AsyncMock(return_value=receipt),
                             index_document=AsyncMock(return_value=index_result))
    monkeypatch.setattr(server, "_client", lambda: client)
    response = json.loads(await server.kb_doc_save_parsed("kb", markdown="test", source_filename="source.pdf"))
    assert response["success"] is False and response["failedCount"] == 1
    assert [d["path"] for d in response["_auto_index"]["documents"]] == ["kb/good.md"]
    tid = response["_auto_index"]["documents"][0]["task_id"]
    assert (await finish(tid))["result"] == index_result
    assert task_registry.get(tid)["status"] == "done"
    client.index_document.assert_awaited_once_with("kb", "kb/good.md")
    server._auto_index_saved("kb", receipt)
    assert len(receipt["_auto_index"]["documents"]) == 1
    assert len(task_registry._records) == 1


@pytest.mark.asyncio
async def test_legacy_shape_and_failed_or_malformed_receipts(monkeypatch):
    response = {"success": True, "vector_index": {"collection": "kb_x", "total_chunks": 1}}
    client = SimpleNamespace(index_document=AsyncMock(return_value=response))
    monkeypatch.setattr(server, "_client", lambda: client)
    legacy = {"success": True, "files": [{"path": "kb/a.md"}, {"path": "kb/a.md"},
                                            {"path": "kb/old.md", "deduped": True}, {}, None]}
    server._auto_index_saved("kb", legacy)
    docs = legacy["_auto_index"]["documents"]
    assert [doc["path"] for doc in docs] == ["kb/a.md"]
    await finish(docs[0]["task_id"])
    for receipt in [
        {"success": False, "files": [{"path": "kb/uncertain.md"}]},
        {"success": True, "files": [{"path": "kb/uncertain.md"}], "items": None},
        {"success": True, "files": [{"path": "kb/uncertain.md"}], "items": [{"files": [{"path": "kb/uncertain.md"}]}]},
    ]:
        server._auto_index_saved("kb", receipt)
        assert "_auto_index" not in receipt
    client.index_document.assert_awaited_once_with("kb", "kb/a.md")


@pytest.mark.asyncio
async def test_batch_parse_save_indexes_successful_split_parts(monkeypatch):
    task = {"task_id": "parse", "kind": "parse_pdf_batch", "status": "done",
            "created_at": "now", "result": {"results": [
                {"success": True, "markdown": "one", "file": "one.pdf"},
                {"success": True, "markdown": "two", "file": "two.pdf"},
                {"success": False, "file": "failed.pdf"},
            ]}, "error": None}
    task_registry._records["parse"] = task
    receipt = {"success": False, "items": [
        {"success": True, "files": [{"path": "kb/part1.md"},
                                    {"path": "kb/part2.md"},
                                    {"path": "kb/existing.md", "deduped": True}]},
        {"success": False, "files": [{"path": "kb/incomplete.md"}]},
    ], "files": [{"path": "kb/incomplete.md"}]}
    index_result = {"success": True, "vector_index": {"collection": "kb_x", "total_chunks": 1}}
    client = SimpleNamespace(save_parsed_files=AsyncMock(return_value=receipt),
                             index_document=AsyncMock(return_value=index_result))
    monkeypatch.setattr(server, "_client", lambda: client)
    response = json.loads(await server.kb_doc_save_parsed("kb", task_id="parse"))
    assert response["success"] is False
    assert [d["path"] for d in response["_auto_index"]["documents"]] == ["kb/part1.md", "kb/part2.md"]
    assert len(client.save_parsed_files.await_args.args[1]) == 2
    for doc in response["_auto_index"]["documents"]:
        assert (await finish(doc["task_id"]))["status"] == "done"
    assert {call.args[1] for call in client.index_document.await_args_list} == {"kb/part1.md", "kb/part2.md"}


@pytest.mark.asyncio
async def test_conflicting_failed_item_excludes_path(monkeypatch):
    client = SimpleNamespace(index_document=AsyncMock())
    monkeypatch.setattr(server, "_client", lambda: client)
    result = {"success": False, "items": [
        {"success": True, "files": [{"path": "kb/same.md"}]},
        {"success": False, "files": [{"path": "kb\\same.md"}]},
    ]}
    server._auto_index_saved("kb", result)
    await asyncio.sleep(0)
    assert "_auto_index" not in result
    client.index_document.assert_not_awaited()


@pytest.mark.asyncio
async def test_web_batch_dedup_does_not_veto_successful_original(monkeypatch):
    original = {"id": "1", "name": "paper.md", "path": "kb/paper.md", "fileSize": 5, "imageCount": 0}
    duplicate = {**original, "path": "kb\\paper.md", "deduped": True}
    result = {"success": False, "savedCount": 2, "failedCount": 1,
              "files": [original, duplicate], "items": [
                  {"index": 0, "filename": "paper.pdf", "success": True,
                   "files": [original], "createdImages": []},
                  {"index": 1, "filename": "copy.pdf", "success": False,
                   "files": [duplicate], "createdImages": [],
                   "error": "Existing deduplicated document was not changed; save completeness is unknown"},
              ]}
    index_result = {"success": True, "vector_index": {"collection": "kb_x", "total_chunks": 1}}
    client = SimpleNamespace(index_document=AsyncMock(return_value=index_result))
    monkeypatch.setattr(server, "_client", lambda: client)
    server._auto_index_saved("kb", result)
    docs = result["_auto_index"]["documents"]
    assert [doc["path"] for doc in docs] == ["kb/paper.md"]
    assert (await finish(docs[0]["task_id"]))["status"] == "done"
    client.index_document.assert_awaited_once_with("kb", "kb/paper.md")


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [
    {"success": False, "files": [{"path": "kb\\same.md"}], "error": "metadata outcome uncertain"},
    {"success": False, "files": [{"path": "kb\\same.md", "deduped": False}], "recoveryReceipt": "secret"},
    {"files": [{"path": "kb\\same.md", "deduped": True}]},
])
async def test_failed_or_unknown_write_vetoes_matching_success(monkeypatch, failed):
    client = SimpleNamespace(index_document=AsyncMock())
    monkeypatch.setattr(server, "_client", lambda: client)
    result = {"success": False, "items": [
        {"success": True, "files": [{"path": "kb/same.md"}]}, failed,
    ]}
    server._auto_index_saved("kb", result)
    await asyncio.sleep(0)
    assert "_auto_index" not in result
    client.index_document.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("task_mode", [False, True])
async def test_single_recovery_retries_identical_web_result(monkeypatch, task_mode, caplog):
    token = "sensitive-single-capability"
    task_registry._records["single"] = {
        "task_id": "single", "kind": "parse_pdf", "status": "done", "created_at": "now",
        "result": {"markdown": "paper", "source_filename": "paper.pdf", "parse_method": "ocr"}, "error": None,
    }
    partial = {"id": "1", "path": "kb/paper.md", "fileSize": 5, "imageCount": 0}
    client = SimpleNamespace(index_document=AsyncMock(return_value={
        "success": True, "vector_index": {"collection": "kb_x", "total_chunks": 1}}))
    calls = []

    async def save(parent, results):
        calls.append((parent, [dict(item) for item in results]))
        if len(calls) == 1:
            return {"success": False, "savedCount": 1, "failedCount": 1, "files": [partial],
                    "items": [{"index": 0, "filename": "paper.pdf", "success": False,
                               "files": [partial], "createdImages": [], "error": "metadata failure",
                               "recoveryReceipt": token}]}
        assert results[0]["recoveryReceipt"] == token
        assert {k: v for k, v in results[0].items() if k != "recoveryReceipt"} == calls[0][1][0]
        return {"success": True, "savedCount": 1, "failedCount": 0, "files": [partial],
                "items": [{"index": 0, "filename": "paper.pdf", "success": True,
                           "files": [partial], "createdImages": []}]}

    client.save_parsed_files = AsyncMock(side_effect=save)
    monkeypatch.setattr(server, "_client", lambda: client)
    kwargs = ({"task_id": "single"} if task_mode else
              {"markdown": "paper", "source_filename": "paper.pdf", "parse_method": "ocr"})
    first = json.loads(await server.kb_doc_save_parsed("kb", description="description", **kwargs))
    assert "_auto_index" not in first
    retry = json.loads(await server.kb_doc_save_parsed(
        "kb", description="description", recovery_receipt=first["items"][0]["recoveryReceipt"], **kwargs))
    assert retry["success"] is True
    assert calls[0][0] == calls[1][0] == "kb"
    assert (await finish(retry["_auto_index"]["documents"][0]["task_id"]))["status"] == "done"
    client.index_document.assert_awaited_once_with("kb", "kb/paper.md")
    assert token not in caplog.text


@pytest.mark.asyncio
async def test_batch_recovery_only_retries_selected_original_indices(monkeypatch, caplog):
    tokens = ("secret-for-b", "secret-for-c")
    task_registry._records["batch"] = {
        "task_id": "batch", "kind": "parse_pdf_batch", "status": "done", "created_at": "now",
        "result": {"results": [
            {"success": False, "file": "parse-failed.pdf"},
            {"success": True, "markdown": "a", "file": "a.pdf"},
            {"success": True, "markdown": "b", "file": "b.pdf"},
            {"success": True, "markdown": "c", "file": "c.pdf"},
        ]}, "error": None,
    }
    client = SimpleNamespace(index_document=AsyncMock(return_value={
        "success": True, "vector_index": {"collection": "kb_x", "total_chunks": 1}}))
    calls = []
    c_attempts = 0

    async def save(parent, results):
        nonlocal c_attempts
        calls.append([dict(item) for item in results])
        if len(calls) == 1:
            files = [{"id": str(i), "path": f"kb/{name}.md"} for i, name in enumerate("abc")]
            return {"success": False, "savedCount": 3, "failedCount": 2, "files": files,
                    "items": [{"index": i, "filename": f"{name}.pdf", "success": i == 0,
                               "files": [files[i]], "createdImages": [],
                               **({"error": "metadata failure", "recoveryReceipt": tokens[i - 1]} if i else {})}
                              for i, name in enumerate("abc")]}
        assert parent == "kb"
        indices = (1, 2) if len(calls) == 2 else (2,)
        assert [item["source_filename"] for item in results] == [f"{'abc'[i]}.pdf" for i in indices]
        for item, index in zip(results, indices):
            assert item["recoveryReceipt"] == tokens[index - 1]
            assert {k: v for k, v in item.items() if k != "recoveryReceipt"} == calls[0][index]
        c_attempts += 1
        files = [{"id": str(i), "path": f"kb/{'abc'[i]}.md"} for i in indices]
        items = []
        for i, index in enumerate(indices):
            complete = index == 1 or c_attempts > 1
            items.append({"index": i, "filename": f"{'abc'[index]}.pdf", "success": complete,
                          "files": [files[i]], "createdImages": [],
                          **({} if complete else {"error": "still incomplete", "recoveryReceipt": tokens[1]})})
        return {"success": all(item["success"] for item in items), "savedCount": len(files),
                "failedCount": sum(not item["success"] for item in items), "files": files, "items": items}

    client.save_parsed_files = AsyncMock(side_effect=save)
    monkeypatch.setattr(server, "_client", lambda: client)
    first = json.loads(await server.kb_doc_save_parsed("kb", task_id="batch", description="same"))
    assert [doc["path"] for doc in first["_auto_index"]["documents"]] == ["kb/a.md"]
    retry = json.loads(await server.kb_doc_save_parsed("kb", task_id="batch", description="same",
        recovery_receipts={str(i): first["items"][i]["recoveryReceipt"] for i in (2, 1)}))
    assert retry["_recovery_batch_indices"] == [1, 2]
    assert retry["items"][1]["recoveryReceipt"] == tokens[1]
    assert [doc["path"] for doc in retry["_auto_index"]["documents"]] == ["kb/b.md"]
    original_index = retry["_recovery_batch_indices"][retry["items"][1]["index"]]
    final = json.loads(await server.kb_doc_save_parsed("kb", task_id="batch", description="same",
        recovery_receipts={str(original_index): retry["items"][1]["recoveryReceipt"]}))
    assert final["success"] is True and final["_recovery_batch_indices"] == [2]
    assert [doc["path"] for doc in final["_auto_index"]["documents"]] == ["kb/c.md"]
    for result in (first, retry, final):
        await finish(result["_auto_index"]["documents"][0]["task_id"])
    assert {call.args[1] for call in client.index_document.await_args_list} == {"kb/a.md", "kb/b.md", "kb/c.md"}
    assert all(token not in caplog.text for token in tokens)


@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs", [
    {"recovery_receipt": "a", "recovery_receipts": {"0": "b"}},
    {"recovery_receipts": {}},
    {"recovery_receipts": {"1": "secret"}},
    {"recovery_receipts": {"00": "secret"}},
    {"recovery_receipts": {"9" * 5000: "secret"}},
    {"recovery_receipts": {"0": ""}},
    {"recovery_receipt": "secret"},
])
async def test_batch_rejects_invalid_receipt_mapping_without_web_request(monkeypatch, kwargs):
    task_registry._records["batch"] = {
        "task_id": "batch", "kind": "parse_pdf_batch", "status": "done", "created_at": "now",
        "result": {"results": [{"success": True, "markdown": "a", "file": "a.pdf"}]}, "error": None,
    }
    client = SimpleNamespace(save_parsed_files=AsyncMock())
    monkeypatch.setattr(server, "_client", lambda: client)
    response = json.loads(await server.kb_doc_save_parsed("kb", task_id="batch", **kwargs))
    assert response["success"] is False
    assert "secret" not in json.dumps(response)
    client.save_parsed_files.assert_not_awaited()
