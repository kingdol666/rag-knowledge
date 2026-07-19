# -*- coding: utf-8 -*-
"""Unit tests for project version/update helpers (no network, no real git pull)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import project_manager as pm


def test_project_version_prefers_ragctl_json():
    fake = {
        "success": True,
        "exit_code": 0,
        "stdout": json.dumps({
            "local": {"version": "2.2.0", "sha": "abc1234"},
            "remote": {"version": "2.2.0", "sha": "abc1234"},
            "update_available": False,
            "comparison": "equal",
        }),
        "stderr": "",
        "data": {
            "local": {"version": "2.2.0", "sha": "abc1234"},
            "remote": {"version": "2.2.0", "sha": "abc1234"},
            "update_available": False,
            "comparison": "equal",
        },
        "command": "node command/ragctl.js version --json",
    }
    with patch.object(pm, "_run_ragctl", return_value=fake):
        out = pm.project_version()
    assert out["success"] is True
    assert out["local"]["version"] == "2.2.0"
    assert out["update_available"] is False
    assert out["via"] == "ragctl"


def test_project_version_fallback_reads_version_file(tmp_path, monkeypatch):
    # Point PROJECT_ROOT at a temp dir with VERSION
    ver = tmp_path / "VERSION"
    ver.write_text("9.9.9\n", encoding="utf-8")
    monkeypatch.setattr(pm, "PROJECT_ROOT", tmp_path)
    with patch.object(pm, "_run_ragctl", return_value={"success": False, "error": "boom", "data": None}):
        out = pm.project_version(local_only=True)
    assert out["local"]["version"] == "9.9.9"
    assert out["via"] == "fallback"


def test_project_update_check_only_passes_flags():
    captured = {}

    def fake_run(args, timeout=180):
        captured["args"] = args
        captured["timeout"] = timeout
        return {
            "success": True,
            "exit_code": 0,
            "data": {
                "success": True,
                "updated": False,
                "dry_run": True,
                "reason": "up to date",
            },
            "stdout": "",
            "stderr": "",
            "command": "x",
        }

    with patch.object(pm, "_run_ragctl", side_effect=fake_run):
        out = pm.project_update(check_only=True, force=False, no_deps=True, restart=False)
    assert out["success"] is True
    assert out["check_only"] is True
    assert "--check" in captured["args"]
    assert "--json" in captured["args"]
    assert "--yes" in captured["args"]
    assert "--no-deps" in captured["args"]
    assert "--force" not in captured["args"]
    assert captured["timeout"] == 60  # check_only short timeout


def test_project_update_full_passes_restart_force():
    captured = {}

    def fake_run(args, timeout=180):
        captured["args"] = list(args)
        captured["timeout"] = timeout
        return {
            "success": True,
            "exit_code": 0,
            "data": {"success": True, "updated": True},
            "stdout": "",
            "stderr": "",
            "command": "x",
        }

    with patch.object(pm, "_run_ragctl", side_effect=fake_run):
        out = pm.project_update(check_only=False, force=True, no_deps=False, restart=True)
    assert out["updated"] is True
    assert "--force" in captured["args"]
    assert "--restart" in captured["args"]
    assert "--check" not in captured["args"]
    assert captured["timeout"] == 600


def test_run_ragctl_missing_js(monkeypatch, tmp_path):
    monkeypatch.setattr(pm, "PROJECT_ROOT", tmp_path)
    out = pm._run_ragctl(["version", "--json"])
    assert out["success"] is False
    assert "ragctl.js not found" in out["error"]


def test_extract_json_blob_from_mixed_output():
    mixed = (
        "\x1b[1mheader\x1b[0m\n"
        "  [INFO] Local : v2.2.0\n"
        '{\n  "success": true,\n  "updated": false,\n  "local": {"version": "2.2.0", "sha": "abc"}\n}\n'
    )
    data = pm._extract_json_blob(mixed)
    assert data is not None
    assert data["success"] is True
    assert data["local"]["version"] == "2.2.0"


def test_extract_json_blob_prefers_full_line():
    text = 'noise {not json}\n{"ok": true, "n": 1}\ntrail'
    data = pm._extract_json_blob(text)
    assert data == {"ok": True, "n": 1}
