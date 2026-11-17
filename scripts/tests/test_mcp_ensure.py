"""Isolated regression tests for mcp_ensure; no project services are started."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "mcp_ensure.py"
spec = importlib.util.spec_from_file_location("mcp_ensure", SCRIPT)
assert spec and spec.loader
ensure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ensure)


class McpEnsureTests(unittest.TestCase):
    def test_handshake_with_mock_subprocess(self) -> None:
        program = (
            "import json,sys\n"
            "for line in sys.stdin:\n"
            " q=json.loads(line)\n"
            " if q.get('id'):\n"
            "  result={'tools':[{'name':'kb_list'}]} if q['id']==2 else {}\n"
            "  print(json.dumps({'jsonrpc':'2.0','id':q['id'],'result':result}),flush=True)\n"
        )
        result = ensure.check_stdio_server("mock", {"command": sys.executable, "args": ["-I", "-u", "-c", program]})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["sample"], ["kb_list"])

    def test_blocked_read_respects_per_phase_timeout(self) -> None:
        started = time.monotonic()
        with patch.object(ensure, "HANDSHAKE_TIMEOUT", 0.3):
            result = ensure.check_stdio_server("mock", {"command": sys.executable,
                                                       "args": ["-I", "-c", "import time; time.sleep(10)"]})
        self.assertFalse(result["ok"])
        self.assertIn("no response", result["error"])
        self.assertLess(time.monotonic() - started, 4)

    def test_stderr_diagnostics_never_return_secret(self) -> None:
        program = "import sys,time; print('MCP error SECRET_TEST_VALUE',file=sys.stderr,flush=True); time.sleep(2)"
        with patch.object(ensure, "HANDSHAKE_TIMEOUT", 0.3):
            result = ensure.check_stdio_server("mock", {"command": sys.executable, "args": ["-I", "-c", program]})
        self.assertIn("MCP connection failure", result.get("diagnostics", []))
        self.assertNotIn("SECRET_TEST_VALUE", repr(result))

    def test_config_read_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mcp.json"
            path.write_bytes(b"x" * (ensure.MAX_CONFIG_BYTES + 1))
            with self.assertRaises(ValueError):
                ensure._read_bounded_config(path)

    def test_process_env_precedes_dotenv_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.yml").write_text(
                "server:\n  dev:\n    backend_url: http://localhost:1000\n    frontend_port: 1001\n"
                "  prod:\n    backend_url: http://localhost:2000\n    frontend_port: 2001\n", encoding="utf-8")
            (root / ".env").write_text(
                "APP_MODE=dev\nBACKEND_URL=http://localhost:3000\nWEB_PORT=3001\n", encoding="utf-8")
            overrides = {"APP_MODE": "prod", "BACKEND_URL": "http://localhost:4000", "WEB_PORT": "4001"}
            with patch.object(ensure, "REPO", root), patch.dict(os.environ, overrides, clear=True):
                urls = ensure._configured_health_endpoints()
                self.assertEqual(urls["backend"], "http://localhost:4000/api/v1/health")
                self.assertEqual(urls["web"], "http://127.0.0.1:4001/")
            with patch.object(ensure, "REPO", root), patch.dict(os.environ, {"APP_MODE": "prod"}, clear=True):
                (root / ".env").write_text("APP_MODE=dev\n", encoding="utf-8")
                urls = ensure._configured_health_endpoints()
                self.assertEqual(urls["backend"], "http://localhost:2000/api/v1/health")
                self.assertEqual(urls["web"], "http://127.0.0.1:2001/")

    def test_endpoints_use_config_and_reject_remote_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.yml").write_text("server:\n  dev:\n    backend_url: http://localhost:1234\n    frontend_port: 5678\n", encoding="utf-8")
            with patch.object(ensure, "REPO", root), patch.dict(os.environ, {}, clear=True):
                urls = ensure._configured_health_endpoints()
                self.assertEqual(urls["backend"], "http://localhost:1234/api/v1/health")
                self.assertEqual(urls["web"], "http://127.0.0.1:5678/")
                (root / ".env").write_text("BACKEND_URL=http://example.com:9999\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    ensure._configured_health_endpoints()


if __name__ == "__main__":
    unittest.main()
