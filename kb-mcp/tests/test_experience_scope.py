"""Regression test for the ``experience_search_smart`` KB-scope filter.

The E2E test passed a UUID ``kb_id`` but the backend's experience search
response only carried ``kb_path`` (a human path like ``"AI-ML-Research"``).
The MCP-layer filter compared the UUID against ``kb_path`` with ``in`` and
silently dropped every hit, while the transparency metadata still claimed
``tier_counts.P1 == N`` — a self-contradictory response.

This test stubs ``server._client()`` so no HTTP is performed, feeds the
*real* backend-shaped payload through the MCP tool, and asserts that:

  * the experiences are returned when ``kb_id`` matches by UUID, path, or
    name (the resolver must recognise all three forms), and
  * ``count`` stays consistent with ``len(experiences)``.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# kb-mcp is a sibling of backend; import server.py directly off disk.
_KB_MCP = Path(__file__).resolve().parent.parent / "kb-mcp"
sys.path.insert(0, str(_KB_MCP))


@pytest.fixture
def patched_server(monkeypatch):
    import server as srv

    # The backend payload mirrors experience_service.search_experiences_global
    # exactly: each hit carries ``kb_path`` but NO ``kb_id`` (the field the
    # MCP filter keyed on). Two hits from two different KBs.
    backend_payload = {
        "success": True,
        "query": "向量服务故障",
        "count": 2,
        "experiences": [
            {"id": "exp-aaa", "title": "向量服务恢复", "kb_path": "AI-ML-Research",
             "scenario": "recovery", "tags": ["向量"], "vector_score": 0.77},
            {"id": "exp-bbb", "title": "其他库经验", "kb_path": "Materials-Science",
             "scenario": "other", "tags": ["材料"], "vector_score": 0.60},
        ],
        "tier_counts": {"P0": 0, "P1": 2, "P2": 0, "discarded": 0},
        "threshold": 0.55,
        "query_type": "troubleshooting",
        "rounds": 1,
        "degraded": False,
        "message": "向量2召回 → 返回2 (P0:0 P1:2 P2:0)",
    }

    # Fake storage aliases so the resolver can map UUID↔path. Mirrors the real
    # storage_reader.list_knowledge_bases() shape.
    kb_catalog = [
        {"kb_id": "11111111-1111-1111-1111-111111111111", "path": "AI-ML-Research",
         "name": "AI-ML-Research"},
        {"kb_id": "22222222-2222-2222-2222-222222222222", "path": "Materials-Science",
         "name": "Materials-Science"},
    ]

    fake_client = MagicMock()
    fake_client.experience_search_global = AsyncMock(return_value=backend_payload)
    # Inject the catalog onto the client so _resolve_kb_aliases can resolve
    # UUID↔path without a network kb_list() call.
    fake_client._kb_aliases = kb_catalog

    monkeypatch.setattr(srv, "_client", lambda: fake_client)
    return srv, backend_payload


async def _run(srv, **kw):
    raw = await srv.experience_search_smart(**kw)
    return json.loads(raw)


async def test_scope_filter_keeps_matches_by_uuid(patched_server):
    srv, payload = patched_server
    kb_uuid = "11111111-1111-1111-1111-111111111111"

    out = await _run(srv, query="向量服务故障", kb_id=kb_uuid, top_k=5)

    # RED today: count==0 / experiences==[] despite backend returning 2 hits.
    assert out["count"] == 1, out
    assert [e["id"] for e in out["experiences"]] == ["exp-aaa"]
    # Consistency invariant the E2E report caught being violated.
    assert out["count"] == len(out["experiences"])


async def test_scope_filter_keeps_matches_by_path(patched_server):
    srv, _ = patched_server
    out = await _run(srv, query="向量服务故障", kb_id="AI-ML-Research", top_k=5)
    assert out["count"] == 1 and out["experiences"][0]["id"] == "exp-aaa"


async def test_scope_filter_no_kb_id_returns_all(patched_server):
    srv, _ = patched_server
    out = await _run(srv, query="向量服务故障", top_k=5)
    assert out["count"] == 2, out
