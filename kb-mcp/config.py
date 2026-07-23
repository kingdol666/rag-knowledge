# -*- coding: utf-8 -*-
"""
kb-mcp configuration and path resolution.

ZERO hardcoded URLs or absolute paths. All connection URLs are read from
the project's config.yml (the single source of truth). All file paths
are resolved relative to known anchors (__file__ location).

Resolution rules:
  - kb-mcp package dir  = directory containing this file
  - project root        = parent of kb-mcp dir (where config.yml lives)
  - storage             = {project_root}/storage/tree-file-system  (config.yml / TREE_STORAGE_PATH)

Usage:
    from config import WEB_URL, BACKEND_URL, MINERU_URL, resolve_path
    from config import KB_MCP_DIR, PROJECT_ROOT
"""
from __future__ import annotations

import os
from pathlib import Path

# ---- anchor points (never hardcoded, derived from this file's location) ----

KB_MCP_DIR = Path(__file__).resolve().parent

# ⭐ RAG_PROJECT_ROOT env var allows running kb-mcp as a standalone MCP server
# outside of the rag-knowledge project directory. Set it to the absolute path
# of the rag-knowledge repo (or any directory containing config.yml + storage).
# When not set, PROJECT_ROOT defaults to kb-mcp's parent directory.
_RAG_ROOT = os.environ.get("RAG_PROJECT_ROOT")
if _RAG_ROOT:
    PROJECT_ROOT = Path(_RAG_ROOT).resolve()
else:
    PROJECT_ROOT = KB_MCP_DIR.parent

# ---- load .env into os.environ (before URL resolution) ----
# Priority: existing env vars (shell / .mcp.json) > .env > config.yml.
# Using setdefault so .env only fills in vars not already in the environment.

def _load_dotenv() -> None:
    """Load `.env` from PROJECT_ROOT into os.environ (setdefault — env wins over .env)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("\"'")
                if key:
                    os.environ.setdefault(key, val)
    except Exception:
        pass  # .env is best-effort; config.yml still works as fallback

_load_dotenv()


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
    mode = section or os.environ.get("APP_MODE", "dev")
    block = server.get(mode, server.get("dev", {}))
    return block.get(key)


def _default_web_url() -> str:
    """Web frontend URL — env, .env, or config.yml, in that order."""

    # 1) env / .env override (WEB_URL / WEB_PORT + WEB_HOST / FRONTEND_PORT)
    web_url = os.environ.get("WEB_URL")
    if web_url:
        return web_url

    env_port = os.environ.get("WEB_PORT") or os.environ.get("FRONTEND_PORT")
    if env_port:
        hostname = os.environ.get("WEB_HOST", "localhost")
        return f"http://{hostname}:{env_port}"

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
    mode = os.environ.get("APP_MODE", "dev")
    port = cfg.get("server", {}).get(mode, {}).get("frontend_port")
    if port:
        return str(port)
    return "6789"


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
    mode = os.environ.get("APP_MODE", "dev")
    port = cfg.get("server", {}).get(mode, {}).get("backend_port")
    hostname = os.environ.get("BACKEND_HOST", "localhost")
    return f"http://{hostname}:{port or 8765}"


def _default_mineru_url() -> str:
    """MinerU health-check URL (legacy fallback, rarely used directly).

    The MinerU port is ephemeral (auto-picked by the backend's MineruApiManager).
    This constant is only used when MINERU_URL is explicitly set via env.
    The primary health-check path goes through the backend's
    /api/v1/mineru/status endpoint, not this URL.
    """
    host = os.environ.get("MINERU_HOST", "127.0.0.1")
    port = os.environ.get("MINERU_PORT", "8764")
    return f"http://{host}:{port}"


# ---- exported connection settings (env overrides config.yml) ----

WEB_URL = os.environ.get("WEB_URL") or _default_web_url()
BACKEND_URL = os.environ.get("BACKEND_URL") or _default_backend_url()
MINERU_URL = os.environ.get("MINERU_URL") or _default_mineru_url()

# Shared auth token — when set, all HTTP requests carry `Authorization: Bearer <token>`.
# Set KB_AUTH_TOKEN in .env (or environment) to match server.auth.enabled=true on backend/web.
AUTH_TOKEN = os.environ.get("KB_AUTH_TOKEN", "")

# NOTE: HTTP_TIMEOUT / PARSE_TIMEOUT live in kb_client/client.py (the single
# source of truth — they are consumed there by KbClient). Do NOT re-declare
# them here: the previous duplicate diverged (config had 300, client had 5000).
