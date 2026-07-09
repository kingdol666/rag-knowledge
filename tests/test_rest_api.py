"""REST API endpoint completeness test.

Tests all backend + Nuxt proxy endpoints to ensure they respond correctly.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
import yaml

KB_MCP_DIR = Path(__file__).parent.parent / "kb-mcp"
config_path = KB_MCP_DIR.parent / "config.yml"
with open(config_path, encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
mode = os.environ.get("APP_MODE", "dev")
server_cfg = cfg.get("server", {}).get(mode, cfg.get("server", {}).get("prod", {}))
WEB_URL = f"http://localhost:{server_cfg.get('frontend_port', 6789)}"
BACKEND_URL = server_cfg.get("backend_url", "http://localhost:8765")

results = {"pass": 0, "fail": 0, "errors": []}


async def api_test(label: str, method: str, url: str, expected_status: int = 200, **kwargs):
    """Test a REST API endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.request(method, url, **kwargs)

        if resp.status_code == expected_status or (expected_status == 200 and resp.status_code < 400):
            results["pass"] += 1
            ct = resp.headers.get("content-type", "")
            if "json" in ct:
                body = json.dumps(resp.json(), ensure_ascii=False)[:100]
            else:
                body = resp.text[:100]
            print(f"  + [{resp.status_code}] {label}: {body}")
        else:
            results["fail"] += 1
            results["errors"].append(f"FAIL {label}: expected {expected_status}, got {resp.status_code}")
            print(f"  X [{resp.status_code}] {label}: expected {expected_status}")
    except Exception as e:
        results["fail"] += 1
        results["errors"].append(f"FAIL {label}: {e}")
        print(f"  X {label}: {e}")


async def run_tests():
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("BACKEND REST API (FastAPI)")
    print("=" * 70)

    # Health
    await api_test("GET /api/v1/health", "GET", f"{BACKEND_URL}/api/v1/health")

    # MinerU status
    await api_test("GET /api/v1/mineru/status", "GET", f"{BACKEND_URL}/api/v1/mineru/status")

    # Search - vector
    await api_test("POST /api/v1/search/vector", "POST",
        f"{BACKEND_URL}/api/v1/search/vector",
        json={"query": "machine learning", "top_k": 3})

    # Search - two-stage
    await api_test("POST /api/v1/search/two-stage", "POST",
        f"{BACKEND_URL}/api/v1/search/two-stage",
        json={"query": "materials science", "stage2_top_k": 3})

    # Search - batch vector
    await api_test("POST /api/v1/search/batch-vector", "POST",
        f"{BACKEND_URL}/api/v1/search/batch-vector",
        json={"query_doc_paths": [], "top_k": 3})

    # Search - stats
    await api_test("GET /api/v1/search/stats", "GET",
        f"{BACKEND_URL}/api/v1/search/stats")

    # Search - debug paths
    await api_test("GET /api/v1/search/debug-paths", "GET",
        f"{BACKEND_URL}/api/v1/search/debug-paths")

    # Graph - search documents
    await api_test("GET /api/v1/graph/search/documents", "GET",
        f"{BACKEND_URL}/api/v1/graph/search/documents?keyword=test&limit=5")

    # Graph - stats
    await api_test("GET /api/v1/graph/stats", "GET",
        f"{BACKEND_URL}/api/v1/graph/stats")

    # Graph - health
    await api_test("GET /api/v1/graph/health", "GET",
        f"{BACKEND_URL}/api/v1/graph/health")

    # Graph - cross-kb
    await api_test("GET /api/v1/graph/cross-kb-documents", "GET",
        f"{BACKEND_URL}/api/v1/graph/cross-kb-documents?limit=5")

    # Experience - list (path is /{kb_id})
    await api_test("GET /api/v1/experience/{{kb_id}}", "GET",
        f"{BACKEND_URL}/api/v1/experience/test-kb")

    # Experience - summary
    await api_test("GET /api/v1/experience/summary", "GET",
        f"{BACKEND_URL}/api/v1/experience/summary?kb_id=test")

    # OpenAPI docs
    await api_test("GET /docs", "GET", f"{BACKEND_URL}/docs")

    # OpenAPI schema
    await api_test("GET /openapi.json", "GET", f"{BACKEND_URL}/openapi.json")

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("NUXT PROXY API (Web Layer)")
    print("=" * 70)

    # KB catalog
    await api_test("GET /api/kb/catalog", "GET", f"{WEB_URL}/api/kb/catalog")

    # KB search (keyword, via Nuxt)
    await api_test("GET /api/kb/search", "GET",
        f"{WEB_URL}/api/kb/search?query=material&top_k=3")

    # KB tags
    await api_test("GET /api/kb/tags", "GET", f"{WEB_URL}/api/kb/tags")

    # Filesystem - tree
    await api_test("GET /api/filesystem", "GET", f"{WEB_URL}/api/filesystem")

    # Filesystem - count (route doesn't exist on Nuxt, skip)
    # The count is handled by the MCP tool fs_get_count which calls a different path
    print("  - SKIP /api/filesystem/count (no Nuxt route)")

    # Graph - health (via Nuxt proxy)
    await api_test("GET /api/graph/health", "GET", f"{WEB_URL}/api/graph/health")

    # Graph - build all (via Nuxt proxy) - GET to check route exists
    # Don't actually POST build-all as it's expensive

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print(f"REST API SUMMARY: {results['pass']} passed, {results['fail']} failed")
    print("=" * 70)

    if results["errors"]:
        print("\nFailed tests:")
        for err in results["errors"]:
            print(f"  X {err}")

    total = results["pass"] + results["fail"]
    if total > 0:
        print(f"\nPass rate: {results['pass'] / total * 100:.1f}%")

    return results


if __name__ == "__main__":
    asyncio.run(run_tests())
