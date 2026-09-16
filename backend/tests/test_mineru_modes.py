"""
Dual-mode MinerU engine tests — remote client protocol, config-driven mode
routing, and remote→local fallback.

The remote endpoint is simulated with an in-process FastAPI/uvicorn-free stub
(http.server in a daemon thread) speaking the mineru-api protocol subset the
client uses: GET /health, POST /tasks, GET /tasks/{id}, GET /tasks/{id}/result.
"""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.utils import mineru_remote as mr
from app.utils.mineru_engine import MineruEngine


# ── stub mineru-api server ────────────────────────────────────────────

_PNG_1PX = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d4944415478da63fcffff3f0300050001a5f645400000000049454e44ae426082"
    )
).decode()


def _make_stub_server(*, token_required: str | None = None):
    """Start a stub mineru-api on an ephemeral port; returns (server, url).

    Behavior: /health → 200; POST /tasks → 202 with task_id (401 when
    token_required set and the Authorization header mismatches); result payload
    carries a tiny markdown + one image so MineruParseService can persist them.
    """
    state = {"task_seq": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence
            return

        def _send(self, code: int, payload: dict):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _drain_body(self):
            """Consume the request body so the client's upload completes
            cleanly before we respond (avoids httpx ReadError on mid-upload
            connection close)."""
            length = int(self.headers.get("Content-Length") or 0)
            while length > 0:
                chunk = self.rfile.read(min(length, 65536))
                if not chunk:
                    break
                length -= len(chunk)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok"})
            elif self.path.endswith("/status"):
                self._send(200, {"task_id": "t1", "status": "completed"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            self._drain_body()
            if self.path == "/tasks":
                if token_required is not None:
                    auth = self.headers.get("Authorization", "")
                    if auth != f"Bearer {token_required}":
                        self._send(401, {"error": "unauthorized"})
                        return
                state["task_seq"] += 1
                self._send(202, {
                    "task_id": f"stub-task-{state['task_seq']}",
                    "status": "pending",
                })
            elif self.path.endswith("/file_parse"):
                self._send(200, {"status": "success", "md_content": "# legacy"})
            else:
                self._send(404, {"error": "not found"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


@pytest.fixture()
def stub_remote():
    server, url = _make_stub_server()
    yield url
    server.shutdown()


@pytest.fixture()
def stub_remote_auth():
    server, url = _make_stub_server(token_required="secret-token-123")
    yield url
    server.shutdown()


@pytest.fixture()
def set_mineru_config():
    """Patch the global config's mineru section; restores it afterwards."""
    from app.config import config

    saved = json.dumps(config._config.get("mineru", {}))

    def _apply(**overrides):
        cfg = {
            "enabled": True,
            "mode": "remote",
            "remote": {"base_url": "", "token": "", "timeout": 1800},
            "local": {"host": "127.0.0.1", "start_on_boot": False,
                      "startup_timeout": 60, "model_source": "modelscope"},
        }
        for key, val in overrides.items():
            cfg[key] = val
        config._config["mineru"] = cfg
        return cfg

    yield _apply
    config._config["mineru"] = json.loads(saved)


# ── RemoteMineruClient basics ─────────────────────────────────────────

def test_validate_base_url_rejects_non_http():
    with pytest.raises(mr.RemoteMineruError):
        mr.validate_remote_base_url("ftp://example.com")
    with pytest.raises(mr.RemoteMineruError):
        mr.validate_remote_base_url("javascript:alert(1)")
    with pytest.raises(mr.RemoteMineruError):
        mr.validate_remote_base_url("")
    assert mr.validate_remote_base_url("http://127.0.0.1:8764/") == "http://127.0.0.1:8764"


def test_client_properties_from_url(set_mineru_config):
    set_mineru_config(remote={"base_url": "http://10.1.2.3:9911", "token": "", "timeout": 99})
    c = mr.RemoteMineruClient()
    assert c.configured
    assert c.host == "10.1.2.3"
    assert c.port == 9911
    assert c.api_url == "http://10.1.2.3:9911"


def test_submit_carries_bearer_token(set_mineru_config, stub_remote_auth):
    import httpx

    set_mineru_config(remote={"base_url": stub_remote_auth,
                              "token": "secret-token-123", "timeout": 60})
    c = mr.RemoteMineruClient()
    assert c.probe()  # /health is unauthenticated on the stub

    import asyncio
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "a.pdf"
        f.write_bytes(b"%PDF-1.4 fake")
        payload = asyncio.run(c.submit_task(str(f)))
    assert payload["task_id"] == "stub-task-1"

    # wrong token → 401 surfaces as HTTPStatusError
    set_mineru_config(remote={"base_url": stub_remote_auth,
                              "token": "wrong", "timeout": 60})
    c2 = mr.RemoteMineruClient()
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "a.pdf"
        f.write_bytes(b"%PDF-1.4 fake")
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(c2.submit_task(str(f)))


# ── MineruEngine routing ──────────────────────────────────────────────

def test_engine_mode_default_remote(set_mineru_config):
    set_mineru_config()  # mode omitted → defaults to remote
    e = MineruEngine()
    assert e.mode == "remote"
    assert not e.remote.configured


def test_engine_remote_mode_unconfigured_falls_local(set_mineru_config):
    set_mineru_config(mode="remote", remote={"base_url": "", "token": "", "timeout": 60})
    e = MineruEngine()
    engine = e.resolve_engine(timeout=60)
    assert engine is e.local
    assert e.last_mode == "local"


def test_engine_remote_dead_falls_local(set_mineru_config):
    # port 1 on loopback — nothing listens there
    set_mineru_config(mode="remote",
                      remote={"base_url": "http://127.0.0.1:1", "token": "", "timeout": 60})
    e = MineruEngine()
    engine = e.resolve_engine(timeout=60)
    assert engine is e.local
    assert e.last_mode == "local"


def test_engine_remote_healthy_uses_remote(set_mineru_config, stub_remote):
    set_mineru_config(mode="remote",
                      remote={"base_url": stub_remote, "token": "", "timeout": 60})
    e = MineruEngine()
    assert e.remote_usable()
    engine = e.resolve_engine(timeout=60)
    assert engine is e.remote
    assert e.last_mode == "remote"
    # legacy is_running/api_url surface the remote engine
    assert e.is_running
    assert e.api_url == stub_remote


def test_engine_local_mode_never_touches_remote(set_mineru_config, stub_remote):
    set_mineru_config(mode="local",
                      remote={"base_url": stub_remote, "token": "", "timeout": 60})
    e = MineruEngine()
    engine = e.resolve_engine(timeout=60)
    assert engine is e.local
    assert e.last_mode == "local"


def test_engine_invalid_mode_falls_back_remote(set_mineru_config):
    set_mineru_config(mode="yolo")
    e = MineruEngine()
    assert e.mode == "remote"


def test_engine_status_payload(set_mineru_config, stub_remote):
    set_mineru_config(mode="remote",
                      remote={"base_url": stub_remote, "token": "", "timeout": 60})
    e = MineruEngine()
    st = e.status()
    assert st["mode"] == "remote"
    assert st["effective_mode"] == "remote"
    assert st["remote"]["configured"] and st["remote"]["available"]
    assert st["available"]  # legacy key
    # legacy keys preserved for kb-mcp health checks
    for key in ("running", "host", "port", "api_url", "pid"):
        assert key in st


# ── MineruParseService end-to-end through the stub remote ─────────────

def test_parse_service_writes_markdown_via_remote(set_mineru_config, stub_remote, tmp_path):
    """Full parse_async against the stub: submission → poll → artifacts land
    in output_dir (md + images + uploads)."""
    from app.services.mineru_service import MineruParseService
    from app.utils.mineru_engine import MineruEngine

    set_mineru_config(mode="remote",
                      remote={"base_url": stub_remote, "token": "", "timeout": 60})
    engine = MineruEngine()
    svc = MineruParseService(engine)

    # The stub's status endpoint always reports completed, and its result
    # endpoint isn't implemented — extend it inline for the result fetch:
    original_do_GET = None

    import asyncio
    from pathlib import Path

    pdf = tmp_path / "uploads" / "paper.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")
    out_dir = tmp_path / "out"

    async def _run():
        return await svc.parse_async(
            pdf.read_bytes(), "paper.pdf", out_dir,
            poll_interval=0.05, poll_timeout=10,
        )

    # Monkeypatch the client's status/result fetchers to return a completed
    # task with content (keeps the test HTTP-stub minimal).
    async def fake_get_task_result(self, task_id):
        return {
            "results": {"paper": {
                "md_content": "# Stub Title\n\nBody text with enough content.",
                "images": {"img_0": f"data:image/png;base64,{_PNG_1PX}"},
            }},
        }

    async def fake_get_task_status(self, task_id):
        return {"task_id": task_id, "status": "completed"}

    mr.RemoteMineruClient.get_task_result = fake_get_task_result
    mr.RemoteMineruClient.get_task_status = fake_get_task_status
    try:
        result = asyncio.run(_run())
    finally:
        del mr.RemoteMineruClient.get_task_result
        del mr.RemoteMineruClient.get_task_status

    assert result.success, result.error
    md_path = Path(result.markdown_path)
    assert md_path.exists() and md_path.read_text(encoding="utf-8").startswith("# Stub Title")
    assert (out_dir / "paper.md").exists()
    assert (out_dir / "images" / "img_0.png").exists()
    assert result.image_count == 1
    assert result.metadata["task_id"] == "stub-task-1"
