#!/usr/bin/env python3
"""共享 kb-mcp stdio 客户端 + QDCVR Step2.5 工具 — 供基准脚本复用.

链路: 本客户端 → MCP stdio (uv run --directory kb-mcp python server.py) → KbClient → backend。
这是 Agent 实际使用的工具层(与 .zcode/mcp.json 同款启动命令)。
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

THRESHOLD = 0.35  # skill Step 2.5 硬阈值


class McpClient:
    """最小 MCP stdio 客户端: initialize → tools/list → tools/call."""

    def __init__(self, repo_root: Path):
        env = dict(os.environ)
        env.setdefault("PYTHONUTF8", "1")
        token_path = repo_root / ".env"
        if "MCP_AUTH_TOKEN" not in env and token_path.exists():
            for line in token_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("MCP_AUTH_TOKEN="):
                    env["MCP_AUTH_TOKEN"] = line.split("=", 1)[1].strip()
        self.proc = subprocess.Popen(
            ["uv", "run", "--directory", "kb-mcp", "python", "server.py"],
            cwd=str(repo_root), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1)
        self._id = 0
        self._initialize()

    def _send(self, obj: dict) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _recv(self, want_id: int, timeout: float = 120.0) -> dict:
        assert self.proc.stdout
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id:
                if "error" in msg:
                    raise RuntimeError(f"MCP error: {msg['error']}")
                return msg["result"]
        raise TimeoutError(f"MCP 响应超时 (id={want_id})")

    def _initialize(self) -> None:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "qdcvr-bench", "version": "1.0"}}})
        self._recv(self._id)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def list_tools(self) -> list[dict]:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": "tools/list"})
        return self._recv(self._id).get("tools", [])

    def call(self, name: str, arguments: dict | None = None, timeout: float = 120.0) -> dict:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}}})
        result = self._recv(self._id, timeout)
        if result.get("isError"):
            raise RuntimeError(f"tool {name} error: {json.dumps(result)[:300]}")
        for block in result.get("content", []):
            if block.get("type") == "text":
                text = block["text"]
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw": text}
        return {}

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def step25_dedup_threshold(results: list[dict], threshold: float = THRESHOLD) -> list[dict]:
    """skill Step 2.5: 硬阈值丢弃 + 文档级去重(同文档留最高分)。"""
    best_by_doc: dict[str, dict] = {}
    for r in results:
        if float(r.get("score", 0)) < threshold:
            continue
        dp = str(r.get("doc_path", ""))
        if dp not in best_by_doc or float(r["score"]) > float(best_by_doc[dp]["score"]):
            best_by_doc[dp] = r
    return sorted(best_by_doc.values(), key=lambda r: -float(r["score"]))
