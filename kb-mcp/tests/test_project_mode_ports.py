"""Unit coverage for mode-specific service ports; no services are started."""
from unittest.mock import patch

import project_manager as pm


def test_prod_mode_override_uses_prod_ports_and_probe_urls(monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")
    monkeypatch.setenv("BACKEND_PORT", "8771")
    monkeypatch.setenv("WEB_PORT", "6789")
    config = {
        "dev": {"backend_port": 8765, "frontend_port": 6789},
        "prod": {"backend_port": 8001, "frontend_port": 3000},
    }
    with patch.object(pm, "_mode_config", side_effect=lambda mode: config[mode]):
        assert pm._ports("prod") == {"backend": 8001, "web": 3000}
        assert pm._backend_url("prod") == "http://localhost:8001"
        assert pm._web_url("prod") == "http://localhost:3000"
        assert pm._ports("dev") == {"backend": 8771, "web": 6789}


def test_start_project_probes_the_requested_mode(monkeypatch):
    monkeypatch.setenv("APP_MODE", "dev")
    monkeypatch.setenv("BACKEND_PORT", "8771")
    monkeypatch.setenv("WEB_PORT", "6789")
    config = {"prod": {"backend_port": 8001, "frontend_port": 3000}}
    probes = []
    launched = []
    with (
        patch.object(pm, "preflight", return_value={"ready_to_start": True}),
        patch.object(pm, "_mode_config", side_effect=lambda mode: config[mode]),
        patch.object(pm, "port_listening", side_effect=lambda port: probes.append(port) or False),
        patch.object(pm, "start_service", side_effect=lambda service, mode: launched.append((service, mode)) or {"success": True}),
        patch.object(pm, "project_status", side_effect=lambda mode: {"mode": mode}),
        patch.object(pm, "_wait_ready", side_effect=lambda timeout, mode: {"mode": mode}),
    ):
        result = pm.start_project(mode="prod", wait=True)
    assert probes == [8001, 3000]
    assert launched == [("backend", "prod"), ("web", "prod")]
    assert result["status"]["mode"] == "prod"
    assert result["wait"]["mode"] == "prod"
