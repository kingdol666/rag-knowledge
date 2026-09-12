#!/usr/bin/env python3
"""benchmark-suite 共享库: 本机 HTTP 客户端 + kb-mcp MCP stdio 客户端 + 指标工具.

边界: 所有 HTTP 仅允许本机回环目标(被测系统), 逐请求 fresh opener + 瞬态重试。
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SUITE = Path(__file__).resolve().parent.parent          # benchmark-suite/
REPO = SUITE.parent                                     # 仓库根
RESULTS = SUITE / "results"
RESULTS.mkdir(exist_ok=True)
DATA = SUITE / "data"

BACKEND = os.environ.get("RAG_BENCH_URL", "http://localhost:8771").rstrip("/")
WEB = os.environ.get("RAG_BENCH_WEB_URL", "http://localhost:6790").rstrip("/")
LOCAL = {"localhost", "127.0.0.1", "::1"}


def _token() -> str:
    if os.environ.get("RAG_BENCH_TOKEN"):
        return os.environ["RAG_BENCH_TOKEN"]
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("MCP_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("缺少 MCP_AUTH_TOKEN (环境变量或仓库 .env)")


def _check_local(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https: {url}")
    if (p.hostname or "").lower() not in LOCAL:
        raise ValueError(f"非本机目标被拒绝: {url}")
    return url


def _open_fresh(req, timeout: int):
    """每请求新建 opener — 规避本机连接栈负载下的 200+空体问题。"""
    return urllib.request.build_opener().open(req, timeout=timeout)


def http_post(url: str, payload: dict, timeout: int = 120, tries: int = 3) -> dict:
    url = _check_local(url)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {_token()}"}
    last: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers=headers, method="POST")
        try:
            with _open_fresh(req, timeout) as resp:
                raw = resp.read()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"null/empty body (len={len(raw)})")
            return parsed
        except urllib.error.HTTPError as e:
            if e.code in (401, 409, 429) or e.code >= 500:
                last = e          # 瞬态(409 交调用方判重时会再抛)
            else:
                raise
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 * (attempt + 1))
    raise last  # type: ignore[misc]


def http_get(url: str, timeout: int = 60, tries: int = 6) -> dict:
    url = _check_local(url)
    headers = {"Authorization": f"Bearer {_token()}"}
    last: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with _open_fresh(req, timeout) as resp:
                raw = resp.read()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"null/empty body (len={len(raw)})")
            return parsed
        except urllib.error.HTTPError as e:
            if e.code in (401, 429) or e.code >= 500:
                last = e
            else:
                raise
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(min(20, 3 * (attempt + 1)))
    raise last  # type: ignore[misc]


def http_delete(url: str, payload: dict, timeout: int = 300, tries: int = 3) -> dict:
    url = _check_local(url)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {_token()}"}
    last: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers=headers, method="DELETE")
        try:
            with _open_fresh(req, timeout) as resp:
                raw = resp.read()
            if not raw:
                return {"success": True}
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"null/empty body (len={len(raw)})")
            return parsed
        except urllib.error.HTTPError as e:
            if e.code in (401, 409, 429) or e.code >= 500:
                last = e
            else:
                raise
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 * (attempt + 1))
    raise last  # type: ignore[misc]


# ── kb-mcp MCP stdio 客户端(与仓库 .zcode/mcp.json 同款启动命令) ──
class McpClient:
    """最小 MCP stdio 客户端: initialize → tools/call。"""

    def __init__(self, repo_root: Path = REPO):
        env = dict(os.environ)
        env.setdefault("PYTHONUTF8", "1")
        if "MCP_AUTH_TOKEN" not in env:
            env["MCP_AUTH_TOKEN"] = _token()
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

    def _recv(self, want_id: int, timeout: float = 300.0) -> dict:
        assert self.proc.stdout
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
                               "clientInfo": {"name": "benchmark-suite", "version": "1.0"}}})
        self._recv(self._id)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, name: str, arguments: dict | None = None,
             timeout: float = 300.0) -> dict:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}}})
        result = self._recv(self._id, timeout)
        if result.get("isError"):
            raise RuntimeError(f"tool {name} error: {json.dumps(result)[:300]}")
        for block in result.get("content", []):
            if block.get("type") == "text":
                try:
                    return json.loads(block["text"])
                except json.JSONDecodeError:
                    return {"raw": block["text"]}
        return {}

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


# ── 通用工具 ──
THRESH = 0.35  # QDCVR Step2.5 硬阈值


def doc_basename(doc_path: str) -> str:
    """doc_path → 源文档基名: 去目录/.md, 递归去 part 与重名计数后缀。"""
    name = str(doc_path).replace("\\", "/").rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    prev = None
    while prev != name:
        prev = name
        name = re.sub(r" \((?:part \d+ of \d+|\d+)\)$", "", name)
    return name


def step25(results: list[dict], threshold: float = THRESH) -> list[dict]:
    """QDCVR Step2.5: 硬阈值丢弃 + 文档级去重(同文档留最高分)。"""
    best: dict[str, dict] = {}
    for r in results:
        if float(r.get("score", 0)) < threshold:
            continue
        dp = str(r.get("doc_path", ""))
        if dp not in best or float(r["score"]) > float(best[dp]["score"]):
            best[dp] = r
    return sorted(best.values(), key=lambda r: -float(r["score"]))


def eval_ranking(ranked_docs: list[str], golden: set[str],
                 k_list=(1, 3, 5)) -> dict:
    """命中率 Hit@k(任一金标进 top-k) / 召回率 Recall@k(金标覆盖) /
    准确率 Precision@5(top-5 中相关占比) / MRR。"""
    base = [norm_t(doc_basename(d)) for d in ranked_docs]
    hits = [1 if b in golden else 0 for b in base]
    out = {}
    for k in k_list:
        matched = len({b for b in base[:k] if b in golden})
        out[f"recall@{k}"] = matched / len(golden) if golden else 0.0
        out[f"hit@{k}"] = 1 if any(hits[:k]) else 0
    rel5 = sum(1 for b in base[:5] if b in golden)
    out["precision@5"] = rel5 / 5.0
    out["mrr"] = next((1.0 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    return out


def norm_t(t: str) -> str:
    return t.strip().lower()


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 4) if xs else None


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def env_fingerprint() -> dict:
    """环境指纹: 固定随机性说明+模型/库参数(写入每个结果 JSON)。"""
    return {
        "backend": BACKEND, "web": WEB,
        "embedding": "BAAI/bge-m3 (local GPU, normalize)",
        "vector_store": "ChromaDB (persistent)",
        "keyword_index": "jieba BM25",
        "randomness": "deterministic pipeline (no RNG); agent channel = mean of runs",
        "retrieval_defaults": {"vector_top_k": 10, "two_stage": {"stage1_top_k": 40, "stage2_top_k": 10},
                                "qdcvr_threshold": THRESH, "verification_reads": 3},
        "mcp_command": "uv run --directory kb-mcp python server.py (stdio)",
    }
