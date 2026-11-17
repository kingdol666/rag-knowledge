"""Tests for MCP retrieval wait budgets and bounded supplements."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_MCP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_MCP_ROOT))
import server  # noqa: E402


class _FakeClient:
    def __init__(self, initial=None, supplement=None):
        self.initial = initial or {"success": True, "stage2": {"results": [
            {"doc_path": "kb/a", "kb_id": "one", "score": .9}]}, "total_results": 1}
        self.supplement = supplement or {"success": True, "count": 1, "results": []}
        self.two_stage_args = None
        self.supplement_args = None

    async def two_stage_search(self, *args, **kwargs):
        self.two_stage_args = (args, kwargs)
        return self.initial

    async def vector_search(self, *args, **kwargs):
        self.supplement_args = (args, kwargs)
        return self.supplement


@pytest.fixture
def patch_client(monkeypatch):
    async def exists(client, kb_id):
        return True
    monkeypatch.setattr(server, "_kb_exists", exists)
    return monkeypatch


@pytest.mark.asyncio
async def test_client_forwards_optional_budgets_in_http_body():
    from kb_client.client import KbClient
    client = KbClient()
    client._post_backend_json = AsyncMock(return_value={"success": True})
    await client.two_stage_search("q", graph_budget_ms=0, vector_budget_ms=25, timeout=.5)
    endpoint, body = client._post_backend_json.await_args.args
    assert endpoint == "/api/v1/search/two-stage"
    assert body["graph_budget_ms"] == 0 and body["vector_budget_ms"] == 25
    assert client._post_backend_json.await_args.kwargs["timeout"] == .5
    await client.vector_search("q", wait_budget_ms=15, timeout=.1)
    endpoint, body = client._post_backend_json.await_args.args
    assert endpoint == "/api/v1/search/vector" and body["wait_budget_ms"] == 15


@pytest.mark.asyncio
async def test_two_stage_exposes_backend_budgets_and_bounded_supplement(patch_client):
    client = _FakeClient()
    patch_client.setattr(server, "_client", lambda: client)
    out = json.loads(await server.kb_search_two_stage(
        "q", graph_budget_ms=220, vector_budget_ms=900,
        supplement_budget_ms=200, response_budget_ms=1200))
    assert client.two_stage_args[1]["graph_budget_ms"] == 220
    assert client.two_stage_args[1]["vector_budget_ms"] == 900
    assert 0 < client.two_stage_args[1]["timeout"] <= 1.201
    assert client.supplement_args is not None
    assert client.supplement_args[1]["timeout"] <= .2
    assert client.supplement_args[1]["wait_budget_ms"] <= 200
    assert out["_cross_kb_fallback"]["triggered"] is True


@pytest.mark.asyncio
async def test_expired_response_budget_skips_supplement(patch_client):
    client = _FakeClient()
    async def search(*args, **kwargs):
        await asyncio.sleep(.02)
        return client.initial
    client.two_stage_search = search
    patch_client.setattr(server, "_client", lambda: client)
    out = json.loads(await server.kb_search_two_stage(
        "q", supplement_budget_ms=0, response_budget_ms=1200))
    assert client.supplement_args is None
    assert out["_cross_kb_fallback"]["reason"] == "supplement_budget_exhausted"
    assert out["retrieval"]["degraded"] is True


@pytest.mark.asyncio
async def test_supplement_timeout_is_reported_degraded(patch_client):
    client = _FakeClient()
    async def slow_vector(*args, **kwargs):
        await asyncio.sleep(.2)
        return {"success": True, "count": 0}
    client.vector_search = slow_vector
    patch_client.setattr(server, "_client", lambda: client)
    out = json.loads(await server.kb_search_two_stage(
        "q", supplement_budget_ms=10, response_budget_ms=1200))
    assert out["_cross_kb_fallback"]["triggered"] is False
    assert out["_cross_kb_fallback"]["degraded"] is True


@pytest.mark.asyncio
async def test_backend_degraded_supplement_propagates(patch_client):
    client = _FakeClient(supplement={"success": True, "count": 0, "results": [],
        "retrieval": {"degraded": True, "degraded_reasons": ["vector_capacity_exhausted"]}})
    patch_client.setattr(server, "_client", lambda: client)
    out = json.loads(await server.kb_search_two_stage("q", response_budget_ms=1000))
    assert out["retrieval"]["degraded"] is True
    assert out["_cross_kb_fallback"]["reason"] == ["vector_capacity_exhausted"]


@pytest.mark.asyncio
async def test_primary_timeout_is_not_reported_as_no_results(patch_client):
    client = _FakeClient()
    async def slow(*args, **kwargs):
        await asyncio.sleep(.2)
        return client.initial
    client.two_stage_search = slow
    patch_client.setattr(server, "_client", lambda: client)
    out = json.loads(await server.kb_search_two_stage("q", response_budget_ms=10))
    assert out["success"] is False and out["status"] == 504
    assert out["degraded_reason"] == "two_stage_http_timeout"


@pytest.mark.asyncio
async def test_invalid_budgets_rejected(patch_client):
    client = _FakeClient()
    patch_client.setattr(server, "_client", lambda: client)
    out = json.loads(await server.kb_search_two_stage("q", vector_budget_ms=float("inf")))
    assert out["status"] == 400
    assert client.two_stage_args is None


@pytest.mark.asyncio
async def test_vector_tool_sends_bounded_backend_wait(patch_client):
    client = _FakeClient(supplement={"success": True, "count": 1, "results": []})
    patch_client.setattr(server, "_client", lambda: client)
    out = json.loads(await server.kb_search_vector("q", wait_budget_ms=125))
    assert out["success"] is True
    assert client.supplement_args[1]["wait_budget_ms"] == 125


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout_type", [
    "ConnectTimeout", "ReadTimeout", "WriteTimeout", "PoolTimeout",
])
async def test_kb_client_classifies_httpx_timeout_subclasses(timeout_type):
    import httpx
    from kb_client.client import KbClient

    exception_type = getattr(httpx, timeout_type)

    def raise_timeout(request):
        raise exception_type("simulated timeout", request=request)

    client = KbClient(backend_url="https://backend.invalid")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(raise_timeout))
    try:
        result = await client.two_stage_search("q", timeout=0.1)
    finally:
        await client.aclose()

    assert result["success"] is False
    assert result["status"] == 504
    assert result["error_kind"] == "timeout"
    assert result["timeout_type"] == timeout_type
    assert "simulated timeout" not in result["error"]


@pytest.mark.asyncio
async def test_actual_httpx_primary_timeout_returns_mcp_504(patch_client):
    import httpx
    from kb_client.client import KbClient

    def raise_timeout(request):
        raise httpx.ReadTimeout("simulated timeout", request=request)

    client = KbClient(backend_url="https://backend.invalid")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(raise_timeout))
    patch_client.setattr(server, "_client", lambda: client)
    try:
        out = json.loads(await server.kb_search_two_stage("q", response_budget_ms=1000))
    finally:
        await client.aclose()

    assert out["success"] is False
    assert out["status"] == 504
    assert out["error_kind"] == "timeout"
    assert out["degraded"] is True
    assert out["degraded_reason"] == "two_stage_http_timeout"
    assert out["timeout_type"] == "ReadTimeout"


@pytest.mark.asyncio
async def test_actual_httpx_supplement_timeout_is_reported_degraded(patch_client):
    import httpx
    from kb_client.client import KbClient

    def respond_then_timeout(request):
        if request.url.path.endswith("/two-stage"):
            return httpx.Response(200, json={
                "success": True,
                "stage2": {"results": [{"doc_path": "kb/a", "kb_id": "one", "score": .9}]},
                "total_results": 1,
            }, request=request)
        raise httpx.ReadTimeout("simulated timeout", request=request)

    client = KbClient(backend_url="https://backend.invalid")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(respond_then_timeout))
    patch_client.setattr(server, "_client", lambda: client)
    try:
        out = json.loads(await server.kb_search_two_stage(
            "q", supplement_budget_ms=500, response_budget_ms=1500))
    finally:
        await client.aclose()

    fallback = out["_cross_kb_fallback"]
    assert fallback["triggered"] is False
    assert fallback["degraded"] is True
    assert fallback["reason"] == "supplement_http_timeout"
    assert fallback["status"] == 504
    assert fallback["error_kind"] == "timeout"
    assert fallback["timeout_type"] == "ReadTimeout"
    assert out["retrieval"]["degraded"] is True
    assert "cross_kb_supplement_incomplete" in out["retrieval"]["degraded_reasons"]


@pytest.mark.asyncio
async def test_real_httpx_504_response_is_classified_without_claiming_timeout(patch_client):
    import httpx
    from kb_client.client import KbClient

    def respond_504(request):
        return httpx.Response(504, text="upstream gateway timeout", request=request)

    client = KbClient(backend_url="https://backend.invalid")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(respond_504))
    patch_client.setattr(server, "_client", lambda: client)
    try:
        out = json.loads(await server.kb_search_two_stage("q", response_budget_ms=1000))
    finally:
        await client.aclose()

    assert out["success"] is False
    assert out["status"] == 504
    assert out["error_kind"] == "timeout"
    assert out["error"] == "two-stage search returned HTTP 504"
    assert out["degraded_reason"] == "two_stage_http_timeout"
    assert out.get("timeout_type") is None
