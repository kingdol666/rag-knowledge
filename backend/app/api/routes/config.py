"""
Configuration management router — read, update, and hot-reload all platform config.

Endpoints:
  GET  /api/v1/config         — read all config (config.yml + backend/config.yml + .env) with schema
  PUT  /api/v1/config         — save config to files and hot-reload in memory
  POST /api/v1/config/reload  — hot-reload config from files without saving
  GET  /api/v1/config/schema  — return the full config schema (field metadata)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import config
from app.utils.paths import CONFIG_PATH, SHARED_CONFIG_PATH, ENV_PATH, PROJECT_ROOT
from app.utils.atomic_io import atomic_write_text
from app.api.routes.config_schema import CONFIG_SCHEMA, ENV_SCHEMA
from app.api.deps.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])

# Sections stored in the shared config.yml (rag-knowledge/config.yml)
SHARED_SECTIONS = ("server", "storage", "vector", "embedding", "graph", "search", "experience_auto")
# Sections stored in backend/config.yml
BACKEND_SECTIONS = ("mineru",)


# ── Helpers ────────────────────────────────────────────────────────────

def _read_yaml(path: Path) -> dict:
    if not path or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, skipping comments and blanks."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip()
    return result

_SECRET_KEY_SUFFIXES = ("TOKEN", "PASSWORD", "SECRET", "KEY", "CREDENTIAL")


def _is_secret_env_key(key: str) -> bool:
    """True for env keys holding secrets (never safe to return verbatim on GET).

    Driven by ENV_SCHEMA (any field flagged type=password) plus a suffix guard
    (KB_AUTH_TOKEN, *_PASSWORD / *_SECRET / *_KEY / *_CREDENTIAL) so unknown
    future keys are also protected. The GET /api/v1/config endpoint is
    unauthenticated by design (local desktop console) — without redaction it
    leaked KB_AUTH_TOKEN / NEO4J_PASSWORD / any API keys to any caller.
    """
    if not key:
        return False
    field = ENV_SCHEMA.get("fields", {}).get(key)
    if isinstance(field, dict) and field.get("type") == "password":
        return True
    upper = key.upper()
    return any(upper.endswith(s) for s in _SECRET_KEY_SUFFIXES)


def _redact_env(env_data: dict[str, str]) -> dict[str, str]:
    """Return a copy of env_data with secret values masked (key preserved for UI)."""
    return {k: ("••••••" if v and _is_secret_env_key(k) else v) for k, v in env_data.items()}


def _yaml_scalar(val: Any) -> str:
    """Render a YAML scalar value with proper quoting."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return f'"{val}"'
    return str(val)


def _build_yaml(data: dict) -> str:
    """Build a clean YAML string from a dict with section comments."""
    lines: list[str] = [
        "# ============================================",
        "# RAG Knowledge Platform - Shared Configuration",
        "# ============================================",
        "# Single source of truth for ports and shared settings.",
        "# Env vars in .env override values here.",
        "# ============================================",
        "",
    ]

    def _dump_dict(d: dict, indent: int = 0) -> None:
        prefix = "  " * indent
        for key, val in d.items():
            if isinstance(val, dict):
                lines.append(f"{prefix}{key}:")
                _dump_dict(val, indent + 1)
            elif isinstance(val, list):
                lines.append(f"{prefix}{key}:")
                for item in val:
                    lines.append(f"{prefix}  - {_yaml_scalar(item)}")
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(val)}")

    section_comments = {
        "server": "# -- Server (ports, CORS, host) --",
        "storage": "# -- Storage (tree-file-system path) --",
        "vector": "# -- Vector Search (ChromaDB) --",
        "embedding": "# -- Embedding Model --",
        "graph": "# -- Knowledge Graph (Neo4j) --",
        "search": "# -- Two-Stage Search --",
    }

    for section in SHARED_SECTIONS:
        if section in data:
            comment = section_comments.get(section, "")
            if comment:
                lines.append(comment)
            _dump_dict({section: data[section]})
            lines.append("")

    return "\n".join(lines)


def _build_backend_yaml(data: dict) -> str:
    """Build backend/config.yml content."""
    lines: list[str] = [
        "# ============================================",
        "# MinerU OCR / PDF Engine Configuration",
        "# ============================================",
        "",
    ]

    def _dump_dict(d: dict, indent: int = 0) -> None:
        prefix = "  " * indent
        for key, val in d.items():
            if isinstance(val, dict):
                lines.append(f"{prefix}{key}:")
                _dump_dict(val, indent + 1)
            elif isinstance(val, list):
                lines.append(f"{prefix}{key}:")
                for item in val:
                    lines.append(f"{prefix}  - {_yaml_scalar(item)}")
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(val)}")

    for section in BACKEND_SECTIONS:
        if section in data:
            _dump_dict({section: data[section]})
            lines.append("")

    return "\n".join(lines)


def _build_env_file(env_data: dict[str, str]) -> str:
    """Build .env file content from a dict."""
    lines: list[str] = [
        "# ============================================",
        "# RAG Knowledge Platform - Environment Variables",
        "# ============================================",
        "# Env vars override config.yml values.",
        "# Modified via the web Settings page or manually.",
        "# ============================================",
        "",
    ]
    for key, val in env_data.items():
        if val == "":
            lines.append(f"# {key}=")
        else:
            lines.append(f"{key}={val}")
    lines.append("")
    return "\n".join(lines)


# ── Models ─────────────────────────────────────────────────────────────

class ConfigUpdateRequest(BaseModel):
    config: dict[str, Any] = {}
    env: dict[str, str] = {}


# ── Routes ─────────────────────────────────────────────────────────────

@router.get("/schema")
async def get_schema() -> dict[str, Any]:
    """Return the full config schema with field metadata for UI rendering."""
    return {
        "success": True,
        "schema": CONFIG_SCHEMA,
        "env_schema": ENV_SCHEMA,
    }


@router.get("")
async def get_config() -> dict[str, Any]:
    """Read all configuration: config.yml + backend/config.yml + .env."""
    shared = _read_yaml(SHARED_CONFIG_PATH) if SHARED_CONFIG_PATH else {}
    backend_cfg = _read_yaml(CONFIG_PATH)
    env_data = _read_env_file(ENV_PATH)

    # Build the combined config
    combined: dict[str, Any] = {}
    for section in SHARED_SECTIONS:
        combined[section] = shared.get(section, {})
    for section in BACKEND_SECTIONS:
        combined[section] = backend_cfg.get(section, {})

    # Effective mode
    mode = config.app_mode

    # Effective values (after env override) for display
    effective = {
        "app_mode": mode,
        "backend_port": str(config.server_port),
        "frontend_port": config.frontend_port,
        "backend_url": os.environ.get("BACKEND_URL") or str(
            combined.get("server", {}).get(mode, {}).get("backend_url", "")
        ),
        "tree_storage_path": config.storage_tree_fs_root,
        "vector_enabled": config.vector_enabled,
        "graph_enabled": config.graph_enabled,
        "mineru_enabled": bool(combined.get("mineru", {}).get("enabled", False)),
    }

    return {
        "success": True,
        "config": combined,
        "env": _redact_env(env_data),
        "schema": CONFIG_SCHEMA,
        "env_schema": ENV_SCHEMA,
        "effective": effective,
    }


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


@router.put("", dependencies=[Depends(verify_token)])
async def update_config(req: ConfigUpdateRequest) -> dict[str, Any]:
    """Save configuration to files and hot-reload in memory.
    
    Merges incoming config with existing config to avoid data loss
    when only partial config is sent.
    """
    try:
        # 0. Read existing config for merge
        existing_shared = _read_yaml(SHARED_CONFIG_PATH) if SHARED_CONFIG_PATH else {}
        existing_backend = _read_yaml(CONFIG_PATH)

        # 1. Merge and write shared config.yml
        shared_data = {}
        for section in SHARED_SECTIONS:
            existing_sec = existing_shared.get(section, {})
            new_sec = req.config.get(section, {})
            shared_data[section] = _deep_merge(existing_sec, new_sec)

        if SHARED_CONFIG_PATH:
            yaml_content = _build_yaml(shared_data)
            atomic_write_text(SHARED_CONFIG_PATH, yaml_content)
            logger.info("Shared config.yml written to %s", SHARED_CONFIG_PATH)

        # 2. Merge and write backend/config.yml
        backend_data = {}
        for section in BACKEND_SECTIONS:
            existing_sec = existing_backend.get(section, {})
            new_sec = req.config.get(section, {})
            backend_data[section] = _deep_merge(existing_sec, new_sec)

        yaml_content = _build_backend_yaml(backend_data)
        atomic_write_text(CONFIG_PATH, yaml_content)
        logger.info("Backend config.yml written to %s", CONFIG_PATH)

        # 3. Write .env file
        if req.env:
            # Read existing .env to preserve unknown vars
            existing_env = _read_env_file(ENV_PATH)
            # Merge: update known vars, keep unknown ones
            merged_env: dict[str, str] = {}
            # First, write all keys from the request
            for key, val in req.env.items():
                merged_env[key] = val
            # Then, preserve existing keys not in the request
            for key, val in existing_env.items():
                if key not in merged_env:
                    merged_env[key] = val

            env_content = _build_env_file(merged_env)
            atomic_write_text(ENV_PATH, env_content)
            logger.info(".env written to %s", ENV_PATH)

            # Apply env vars to current process
            for key, val in req.env.items():
                if val:
                    os.environ[key] = val
                elif key in os.environ and key != "APP_MODE":
                    # Empty value = user cleared it in the UI → remove from the
                    # running process so it falls back to config.yml / default.
                    # The previous `pass` here was dead code: it claimed to clear
                    # optional vars but never did, so a UI clear never took effect
                    # until a full restart. APP_MODE is intentionally preserved
                    # (clearing it would flip the mode unexpectedly).
                    os.environ.pop(key, None)

        # 4. Hot-reload config in memory
        config.reload()
        logger.info("Configuration hot-reloaded successfully")

        # Notify meditation scheduler to pick up new interval/enabled state
        try:
            from app.services.experience_meditation_service import meditation_scheduler
            meditation_scheduler.notify_config_change()
        except Exception:
            pass  # scheduler not available — non-fatal

        # 5. Return updated config
        return await get_config()

    except Exception as e:
        logger.exception("Failed to update configuration")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.post("/reload", dependencies=[Depends(verify_token)])
async def reload_config() -> dict[str, Any]:
    """Hot-reload configuration from files without saving."""
    try:
        # Re-read .env
        env_data = _read_env_file(ENV_PATH)
        for key, val in env_data.items():
            os.environ[key] = val

        # Reload config
        config.reload()
        logger.info("Configuration reloaded from files")

        return {
            "success": True,
            "message": "Configuration reloaded successfully",
            "effective": {
                "app_mode": config.app_mode,
                "backend_port": str(config.server_port),
                "vector_enabled": config.vector_enabled,
                "graph_enabled": config.graph_enabled,
            },
        }
    except Exception as e:
        logger.exception("Failed to reload configuration")
        raise HTTPException(status_code=500, detail=f"Failed to reload: {e}")
