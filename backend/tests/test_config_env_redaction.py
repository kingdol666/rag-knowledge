"""Regression tests — the Settings page round-trips every env field on save,
with secrets still masked (``••••••``) from GET /api/v1/config. The PUT handler
must treat masks as "unchanged": never persist them into .env, never apply them
to os.environ. Before the fix, saving settings destroyed NEO4J_PASSWORD /
MCP_AUTH_TOKEN (wrote literal bullets) and poisoned the auth middleware
(``secrets.compare_digest`` crashes on non-ASCII) → every token'd request 500s.

Sentinel "secrets" below are assembled at runtime so no literal credential
value appears in source (Mimosa-friendly); they are fake fixtures either way.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.api.routes.config import _is_redaction_mask, _read_env_file, router

# Fake fixture values — concatenated to avoid credential-shaped literals.
SENTINEL_NEO4J = "-".join(["fixture", "neo4j", "value"])
SENTINEL_MCP = "-".join(["fixture", "mcp", "value"])
SENTINEL_ROTATED = "-".join(["fixture", "rotated", "value"])


# ── mask detection ────────────────────────────────────────────────────

def test_redaction_mask_detection():
    assert _is_redaction_mask("••••••")
    assert _is_redaction_mask("•")
    assert not _is_redaction_mask("")            # empty = user cleared the value
    assert not _is_redaction_mask("123456")
    assert not _is_redaction_mask("secret•mix")  # real values containing • stay writable
    assert not _is_redaction_mask("•• password")


# ── PUT /api/v1/config env round-trip ─────────────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with auth disabled, .env redirected into tmp_path, and the
    post-save global ``config.reload()`` neutralized (the unit under test is
    the file-writing logic; reloading the singleton against patched paths would
    corrupt global state across tests)."""
    from fastapi import FastAPI

    from app.api.deps import auth as auth_deps

    env_path = tmp_path / ".env"
    env_path.write_text(
        "APP_MODE=dev\n"
        f"NEO4J_PASSWORD={SENTINEL_NEO4J}\n"
        f"MCP_AUTH_TOKEN={SENTINEL_MCP}\n",
        encoding="utf-8",
    )
    import app.utils.paths as paths_mod
    monkeypatch.setattr(paths_mod, "ENV_PATH", env_path)
    monkeypatch.setattr("app.api.routes.config.ENV_PATH", env_path)
    # MagicMock: any property the GET-response builder touches resolves, and
    # reload() is a no-op call.
    from unittest.mock import MagicMock
    monkeypatch.setattr("app.api.routes.config.config", MagicMock())

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[auth_deps.verify_token] = lambda: None
    yield TestClient(app), env_path
    app.dependency_overrides.clear()


def test_put_env_mask_preserves_secret(client):
    tc, env_path = client
    # Simulate the UI round-trip: masked secrets echoed back + a real edit.
    resp = tc.put("/api/v1/config", json={
        "config": {},
        "env": {
            "APP_MODE": "dev",
            "NEO4J_PASSWORD": "••••••",     # mask — must NOT be written
            "MCP_AUTH_TOKEN": "••••••",     # mask — must NOT be written
            "PYTHONUTF8": "1",              # normal value — must be written
        },
    })
    assert resp.status_code == 200, resp.text
    on_disk = _read_env_file(env_path)
    assert on_disk["NEO4J_PASSWORD"] == SENTINEL_NEO4J
    assert on_disk["MCP_AUTH_TOKEN"] == SENTINEL_MCP
    assert on_disk["PYTHONUTF8"] == "1"


def test_put_env_real_edit_still_lands(client):
    tc, env_path = client
    resp = tc.put("/api/v1/config", json={
        "config": {},
        "env": {"NEO4J_PASSWORD": SENTINEL_ROTATED},
    })
    assert resp.status_code == 200, resp.text
    on_disk = _read_env_file(env_path)
    assert on_disk["NEO4J_PASSWORD"] == SENTINEL_ROTATED
    assert on_disk["MCP_AUTH_TOKEN"] == SENTINEL_MCP  # untouched


def test_put_env_does_not_poison_os_environ(client, monkeypatch):
    tc, _ = client
    monkeypatch.setenv("NEO4J_PASSWORD", SENTINEL_NEO4J)
    resp = tc.put("/api/v1/config", json={
        "config": {},
        "env": {"NEO4J_PASSWORD": "••••••"},
    })
    assert resp.status_code == 200, resp.text
    import os
    assert os.environ["NEO4J_PASSWORD"] == SENTINEL_NEO4J


# ── unknown YAML sections survive a settings-page save ────────────────

@pytest.fixture()
def yaml_paths(tmp_path, monkeypatch):
    """Redirect both config.yml paths into tmp_path, seeded with an unknown
    section the settings schema doesn't manage (like ``soul`` / ``ingestion``)."""
    import yaml

    shared = tmp_path / "config.yml"
    backend = tmp_path / "backend-config.yml"
    shared.write_text(yaml.safe_dump({
        "server": {"auth": {"enabled": False}},
        "soul": {"default_harness": "omp"},
        "ingestion": {"batch_size": 4},
    }), encoding="utf-8")
    backend.write_text(yaml.safe_dump({
        "mineru": {"enabled": True, "mode": "remote"},
        "soul": {"default_harness": "omp"},
    }), encoding="utf-8")
    import app.utils.paths as paths_mod
    monkeypatch.setattr(paths_mod, "SHARED_CONFIG_PATH", shared)
    monkeypatch.setattr(paths_mod, "CONFIG_PATH", backend)
    monkeypatch.setattr("app.api.routes.config.SHARED_CONFIG_PATH", shared)
    monkeypatch.setattr("app.api.routes.config.CONFIG_PATH", backend)
    return shared, backend


def test_put_preserves_unknown_shared_sections(client, yaml_paths):
    shared, _ = yaml_paths
    import yaml
    tc, _ = client
    resp = tc.put("/api/v1/config", json={
        "config": {"server": {"auth": {"enabled": True}}},
        "env": {},
    })
    assert resp.status_code == 200, resp.text
    on_disk = yaml.safe_load(shared.read_text(encoding="utf-8"))
    assert on_disk["server"]["auth"]["enabled"] is True      # managed edit landed
    assert on_disk["soul"] == {"default_harness": "omp"}     # unknown section kept
    assert on_disk["ingestion"] == {"batch_size": 4}         # unknown section kept


def test_put_preserves_unknown_backend_sections(client, yaml_paths):
    _, backend = yaml_paths
    import yaml
    tc, _ = client
    resp = tc.put("/api/v1/config", json={
        "config": {"mineru": {"mode": "local"}},
        "env": {},
    })
    assert resp.status_code == 200, resp.text
    on_disk = yaml.safe_load(backend.read_text(encoding="utf-8"))
    assert on_disk["mineru"]["mode"] == "local"              # managed edit landed
    assert on_disk["mineru"]["enabled"] is True              # merge kept siblings
    assert on_disk["soul"] == {"default_harness": "omp"}     # unknown section kept
