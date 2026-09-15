"""OpenAPI contract enrichment.

The service authenticates with a bearer token enforced by `AuthMiddleware`,
but that is invisible to the generated schema: without it, `/docs` shows no
Authorize button, generated SDKs cannot attach credentials, and clients have
no declared error contract to code against.

This module patches the auto-generated document (it does not change runtime
behaviour) so the published contract matches what the middleware actually does:

  * declares the `bearerAuth` HTTP security scheme
  * applies it to every protected operation, leaving the whitelist public
  * documents the shared error envelope on 401 / 403 / 404 / 422 / 500
  * attaches the operation `tags` used by the sidebar, plus a description
"""
from __future__ import annotations

from typing import Any, Iterable

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# Endpoints served without a token (must mirror AuthMiddleware.WHITELIST_EXACT).
PUBLIC_PATHS = {
    "/",
    "/health",
    "/api/v1/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/verify",
}

# Documented response codes. The runtime envelope for errors raised by the
# middleware / route handlers is {"error": true, "error_type": str, "message": str}.
ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "error": {"type": "boolean", "example": True},
        "error_type": {"type": "string", "example": "unauthorized"},
        "message": {"type": "string"},
        "hint": {"type": "string"},
    },
    "required": ["error"],
}

ERROR_RESPONSES: dict[str, Any] = {
    "401": {"description": "Missing, invalid, revoked or expired token",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}},
    "403": {"description": "Authenticated but not permitted (e.g. scope check)",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}},
    "404": {"description": "Resource not found",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}},
    "409": {"description": "Conflict with current state (duplicate, harness not installed, "
                           "index already exists)",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}},
    "429": {"description": "Rate limit exceeded",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}},
    "500": {"description": "Unhandled server error",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}},
}

_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")

SECURITY_SCHEME = {
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "opaque",
        "description": (
            "Bearer token in the `Authorization` header.\n\n"
            "Three credential kinds are accepted:\n"
            "* **user API token** — `sk-…`, minted by `POST /api/v1/auth/tokens` "
            "(or `POST /api/auth/tokens` through the web proxy)\n"
            "* **MCP service token** — the platform's own service credential "
            "(`MCP_AUTH_TOKEN` in `.env`)\n"
            "* **legacy shared token** — `KB_AUTH_TOKEN`, kept for compatibility\n\n"
            "Health and the auth-bootstrap endpoints are public."
        ),
    }
}


def _tag_descriptions() -> dict[str, str]:
    return {
        "Health": "Liveness and readiness probes.",
        "Auth": "Registration, login, identity and API-token lifecycle.",
        "PDF Conversion": "Parse PDF/DOCX/XLSX/PPTX/images into markdown via MinerU.",
        "MinerU Engine": "Inspect and restart the MinerU parsing engine.",
        "Search": "Content retrieval: vector, BM25→vector two-stage, indexing and repair.",
        "Graph": "Neo4j knowledge graph: build, traverse, relate and audit.",
        "Experience": "Experience lifecycle: extract, vet, apply, review, decay.",
        "Meditation": "Scheduled agent jobs that synthesise experience from Q&A signals.",
        "soul": "SOUL personas: distillation, training, evaluation and retrieval-augmented Q&A.",
        "Configuration": "Runtime configuration read/update/reload.",
        "System Maintenance": "Disk and cache housekeeping.",
        "Documents": "Document-level helpers (splitting large inputs).",
    }


def install_openapi(app: FastAPI, *, title: str, version: str, description: str) -> None:
    """Replace `app.openapi` with a contract-accurate generator."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=title,
            version=version,
            description=description,
            routes=app.routes,
        )
        components = schema.setdefault("components", {})
        components.setdefault("schemas", {})["ApiError"] = ERROR_SCHEMA
        components["securitySchemes"] = SECURITY_SCHEME

        for path, item in schema.get("paths", {}).items():
            is_public = path in PUBLIC_PATHS
            for method, op in item.items():
                if method not in _METHODS or not isinstance(op, dict):
                    continue
                op["tags"] = op.get("tags") or ["Uncategorised"]
                if is_public:
                    op["security"] = []          # explicitly public
                    continue
                op["security"] = [{"bearerAuth": []}]
                responses = op.setdefault("responses", {})
                for code, spec in ERROR_RESPONSES.items():
                    if code == "422" or code in responses:
                        continue
                    responses[code] = spec
                # Surface the async/long-running shape where it exists.
                if "text/event-stream" in str(op.get("responses", {})):
                    op["description"] = (op.get("description") or "") + \
                        "\n\n_Streams Server-Sent Events._"

        schema["tags"] = [{"name": name, "description": desc}
                          for name, desc in _tag_descriptions().items()]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
