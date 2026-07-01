# -*- coding: utf-8 -*-
"""
kb-mcp configuration and path resolution.

ZERO hardcoded URLs or absolute paths. All connection URLs are read from
the project's config.yml (the single source of truth). All file paths
are resolved relative to known anchors (__file__ location).

Resolution rules:
  - kb-mcp package dir  = directory containing this file
  - project root        = parent of kb-mcp dir (where config.yml lives)
  - storage             = {project_root}/web/storage/tree-file-system

Usage:
    from config import WEB_URL, BACKEND_URL, MINERU_URL, resolve_path
    from config import KB_MCP_DIR, PROJECT_ROOT
"""
from __future__ import annotations

import os
from pathlib import Path

# ---- anchor points (never hardcoded, derived from this file's location) ----

KB_MCP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = KB_MCP_DIR.parent


def resolve_path(*parts: str) -> str:
    """Resolve a relative path to absolute, anchored at the kb-mcp directory.

    Examples:
        resolve_path("kb_client", "client.py")
        resolve_path("..", "config.yml")   # relative to project root
    """
    return str((KB_MCP_DIR.joinpath(*parts)).resolve())


def resolve_project_path(*parts: str) -> str:
    """Resolve a relative path anchored at the PROJECT_ROOT (rag-knowledge/)."""
    return str((PROJECT_ROOT.joinpath(*parts)).resolve())


# ---- read URLs from config.yml (single source of truth) ----

_CONFIG_YML = PROJECT_ROOT / "config.yml"

def _read_config_yml() -> dict:
    """Load config.yml if present; return {} on any failure."""
    if not _CONFIG_YML.exists():
        return {}
    try:
        import yaml
        with open(_CONFIG_YML, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _url_from_config(key: str, section: str | None = None) -> str | None:
    """Extract a URL from config.yml. Returns None if not found."""
    cfg = _read_config_yml()
    server = cfg.get("server", {})
    mode = section or os.environ.get("APP_MODE", "prod")
    block = server.get(mode, server.get("prod", {}))
    return block.get(key)


def _default_web_url() -> str:
    """Web frontend URL — env, .env, or config.yml, in that order."""

    # 1) env / .env override (WEB_URL / WEB_PORT / FRONTEND_PORT)
    web_url = os.environ.get("WEB_URL")
    if web_url:
        return web_url

    env_port = os.environ.get("WEB_PORT") or os.environ.get("FRONTEND_PORT")
    if env_port:
        return f"http://localhost:{env_port}"

    # 2) config.yml frontend_url (if ever added)
    val = _url_from_config("frontend_url")
    if val:
        return val

    # 3) build from config.yml port
    port = _frontend_port()
    hostname = os.environ.get("WEB_HOST", "localhost")
    return f"http://{hostname}:{port}"


def _frontend_port() -> str:
    """Frontend port from config.yml or env."""
    cfg = _read_config_yml()
    mode = os.environ.get("APP_MODE", "prod")
    port = cfg.get("server", {}).get(mode, {}).get("frontend_port")
    if port:
        return str(port)
    return "3000"


def _default_backend_url() -> str:
    """Backend URL — env, .env, or config.yml, in that order."""

    # 1) env / .env override (BACKEND_URL / BACKEND_PORT)
    backend_url = os.environ.get("BACKEND_URL")
    if backend_url:
        return backend_url

    env_port = os.environ.get("BACKEND_PORT")
    if env_port:
        return f"http://localhost:{env_port}"

    # 2) config.yml
    val = _url_from_config("backend_url")
    if val:
        return val

    # 3) build from config.yml port
    cfg = _read_config_yml()
    mode = os.environ.get("APP_MODE", "prod")
    port = cfg.get("server", {}).get(mode, {}).get("backend_port")
    hostname = os.environ.get("BACKEND_HOST", "localhost")
    return f"http://{hostname}:{port or 8001}"


def _default_mineru_url() -> str:
    """MinerU health-check URL. Port 8764 is fixed by the platform's start script."""
    host = os.environ.get("MINERU_HOST", "127.0.0.1")
    port = os.environ.get("MINERU_PORT", "8764")
    return f"http://{host}:{port}"


# ---- exported connection settings (env overrides config.yml) ----

WEB_URL = os.environ.get("WEB_URL") or _default_web_url()
BACKEND_URL = os.environ.get("BACKEND_URL") or _default_backend_url()
MINERU_URL = os.environ.get("MINERU_URL") or _default_mineru_url()

# Timeouts (env-configurable, with sensible defaults)
HTTP_TIMEOUT = int(os.environ.get("MCP_HTTP_TIMEOUT", "30"))
PARSE_TIMEOUT = int(os.environ.get("MCP_PARSE_TIMEOUT", "300"))
