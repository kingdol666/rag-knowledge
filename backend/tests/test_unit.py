"""Fast, hermetic unit tests — no MinerU, no network, no slow subprocess.

Run with: ``uv run pytest`` (integration tests are auto-skipped).
Covers the pure-logic surfaces of the backend:
  * parse route helpers — _normalize_output_dirs (lenient pairing), _resolve_output_dir
  * MinerU manager — _pick_free_port avoids common ports; _base_url is derived
  * startup guard (main._port_in_use) — free vs actively-listening
  * SSE framing + MineruParseResult schema validation
"""
from __future__ import annotations

import json
import socket

import pytest

from app.api.routes.parse import (
    _DEFAULT_OUTPUT_ROOT,
    _normalize_output_dirs,
    _resolve_output_dir,
    _sse,
)
from app.models.schemas import MineruParseResult
from app.utils.paths import PROJECT_ROOT
from main import _port_in_use
from app.utils.mineru_manager import MineruApiManager


# ── _normalize_output_dirs: lenient positional pairing ───────────────────────
class TestNormalizeOutputDirs:
    def test_empty_list_all_none(self):
        assert _normalize_output_dirs([], 3) == [None, None, None]

    def test_short_list_padded_with_none(self):
        # The exact case requested: 2 files + 1 dir → file 2 falls back.
        assert _normalize_output_dirs(["D:/a"], 2) == ["D:/a", None]

    def test_empty_string_entry_becomes_none(self):
        assert _normalize_output_dirs(["a", "  ", "c"], 3) == ["a", None, "c"]

    def test_longer_list_truncated(self):
        assert _normalize_output_dirs(["a", "b", "c", "d"], 2) == ["a", "b"]

    def test_exact_length_passes_through(self):
        assert _normalize_output_dirs(["a", "b"], 2) == ["a", "b"]

    @pytest.mark.parametrize("n", [1, 5, 100])
    def test_never_raises_on_count_mismatch(self, n):
        # The point of the lenient rewrite — no ValueError, ever.
        result = _normalize_output_dirs(["only"], n)
        assert len(result) == n
        assert result[0] == "only"
        assert all(x is None for x in result[1:])


# ── _resolve_output_dir: abs / relative / uuid fallback ──────────────────────
class TestResolveOutputDir:
    def test_none_falls_back_to_uuid_dir(self):
        p = _resolve_output_dir(None)
        assert p.is_absolute()
        assert p.parent == _DEFAULT_OUTPUT_ROOT

    def test_absolute_path_used_verbatim(self):
        # P0 #7: 合法绝对路径（monorepo root 子树内）原样使用。
        legal = PROJECT_ROOT.parent / "test-output-legal"
        result = _resolve_output_dir(str(legal))
        assert result == legal.resolve()

    def test_absolute_path_outside_project_rejected(self, tmp_path):
        # P0 #7: 系统临时目录（monorepo 外）必须被 422 拒绝（防任意目录写）。
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _resolve_output_dir(str(tmp_path))
        assert exc.value.status_code == 422

    def test_relative_path_resolved_under_project_root(self):
        p = _resolve_output_dir("some/rel/path")
        assert p == (PROJECT_ROOT / "some/rel/path").resolve()


# ── MinerU manager: free-port picker + derived base_url ──────────────────────
class TestMineruApiManagerPort:
    def test_base_url_derived_from_port_never_drifts(self):
        m = MineruApiManager()
        m.port = None
        assert m._base_url == ""
        m.port = 12345
        assert m._base_url == "http://127.0.0.1:12345"
        m.port = 99
        assert m._base_url == "http://127.0.0.1:99"  # tracks instantly

    @pytest.mark.parametrize("iteration", range(15))
    def test_pick_free_port_avoids_common(self, iteration):
        m = MineruApiManager()
        assert m._pick_free_port() not in MineruApiManager._AVOID_PORTS

    def test_avoid_list_covers_project_and_common_ports(self):
        for must_avoid in (80, 443, 3000, 5432, 6379, 8000, 8080, 8764, 8765):
            assert must_avoid in MineruApiManager._AVOID_PORTS

    def test_pick_free_port_returns_valid_int(self):
        m = MineruApiManager()
        p = m._pick_free_port()
        assert isinstance(p, int)
        assert 1024 < p < 65536

    def test_manager_defaults_to_auto_port(self):
        m = MineruApiManager()
        assert m._requested_port is None
        assert m.port is None


# ── main startup guard: _port_in_use ─────────────────────────────────────────
class TestPortInUse:
    def test_free_port_is_not_in_use(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        assert _port_in_use("127.0.0.1", port) is False

    def test_active_listener_is_in_use(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen()
        port = srv.getsockname()[1]
        try:
            assert _port_in_use("127.0.0.1", port) is True
        finally:
            srv.close()


# ── SSE framing + schema validation ──────────────────────────────────────────
class TestSseFrame:
    def test_frame_format(self):
        frame = _sse({"type": "start", "total": 3})
        assert frame.startswith("data: ")
        assert frame.endswith("\n\n")
        assert json.loads(frame[len("data: "):].strip()) == {"type": "start", "total": 3}

    def test_frame_handles_unicode(self):
        frame = _sse({"msg": "中文 / émoji 🎉"})
        assert "中文" in frame and "🎉" in frame


class TestMineruParseResultSchema:
    def test_minimal_success(self):
        r = MineruParseResult(success=True, source_filename="a.pdf")
        assert r.success is True
        assert r.has_markdown is False
        assert r.image_count == 0
        assert r.metadata == {}

    def test_failure_with_error(self):
        r = MineruParseResult(success=False, source_filename="a.pdf", error="boom")
        assert r.success is False
        assert r.error == "boom"

    def test_success_is_required(self):
        with pytest.raises(Exception):
            MineruParseResult(source_filename="a.pdf")  # type: ignore[call-arg]

    def test_full_payload_roundtrip(self):
        r = MineruParseResult(
            success=True,
            output_dir="/out",
            markdown_path="/out/a.md",
            images_dir="/out/images",
            source_filename="a.pdf",
            image_count=5,
            has_markdown=True,
        )
        d = r.model_dump()
        assert d["image_count"] == 5
        # re-validate
        assert MineruParseResult(**d).success is True
