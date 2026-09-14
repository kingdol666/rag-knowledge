#!/usr/bin/env python3
"""omp RPC 客户端 — benchmark-suite/algorithms 的唯一 Agent 通道.

协议(实测 omp 18.1.15 `--mode=rpc`): 行分隔 JSON、type 标签制(非 JSON-RPC):
  client → {"type":"prompt","message":"<text>"}
  server → {"type":"ready",...} → {"type":"response","command":"prompt","success":true}
         → agent_start/turn_start/message_start|message_end(role=user|assistant,
           content=[{type:"text",text}...]) → turn_end → agent_end(isTerminal)

设计:
  - OmpRpc      : 常驻 RPC 进程, 多回合共享会话历史 → agentic 方法
                  (search_o1/deepread) 的每查询循环走这里。
  - OmpOneshot  : 每次调用新起进程(无历史污染) → rerank/假设生成/作答/判分等
                  独立单回合调用; `omp -p --mode=json @file` 与平台 harness 同款。
  - 磁盘缓存: call() 以 (stage, prompt) 哈希缓存, 幂等重跑零成本。
所有超时/解析失败上抛, 由调用方决定降级 — 绝不静默造答案。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(stage: str, prompt: str) -> Path:
    h = hashlib.sha256(f"{stage}\x00{prompt}".encode("utf-8")).hexdigest()[:32]
    return CACHE_DIR / f"llm_{stage}_{h}.json"


class OmpError(RuntimeError):
    pass


class OmpBase:
    """共享: 模型/参数与磁盘缓存。缓存可经 DR_NO_LLM_CACHE=1 关闭。"""

    def __init__(self, stage: str = "call", timeout: float = 300.0):
        self.stage = stage
        self.timeout = timeout
        self.calls = 0            # 实际发起(未命中缓存)的调用数
        self.cache_hits = 0

    def _cached(self, prompt: str):
        if os.environ.get("DR_NO_LLM_CACHE") == "1":
            return None
        p = _cache_path(self.stage, prompt)
        if p.exists():
            try:
                self.cache_hits += 1
                return json.loads(p.read_text(encoding="utf-8"))["text"]
            except Exception:  # noqa: BLE001
                return None
        return None

    def _store(self, prompt: str, text: str) -> None:
        p = _cache_path(self.stage, prompt)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"text": text, "cached_at": time.time()},
                                  ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)


class OmpRpc(OmpBase):
    """常驻 omp RPC 会话; prompt() 追加到会话历史(多回合 agentic 用)。"""

    def __init__(self, stage: str = "rpc", timeout: float = 300.0):
        super().__init__(stage, timeout)
        self.proc = subprocess.Popen(
            ["omp", "--mode=rpc", "--no-session", "--no-tools", "--no-lsp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1)
        self._wait_ready()

    def _wait_ready(self) -> None:
        deadline = time.time() + 30
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                break
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if m.get("type") == "ready":
                return
        raise OmpError("omp RPC 未就绪(无 ready 事件)")

    def _drain_until_agent_end(self) -> str:
        text, saw_error = [], []
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:  # EOF
                raise OmpError("omp RPC 进程意外退出")
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = m.get("type")
            if t == "message_end" and (m.get("message") or {}).get("role") == "assistant":
                for b in m["message"].get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "text":
                        text.append(str(b.get("text", "")))
            elif t == "response" and m.get("success") is False:
                saw_error.append(str(m.get("error", ""))[:200])
            elif t == "agent_end":
                final = "".join(text).strip()
                if not final and saw_error:
                    raise OmpError(f"omp RPC 空回复: {saw_error[0]}")
                return final
        raise OmpError(f"omp RPC 超时(>{self.timeout}s, stage={self.stage})")

    def prompt(self, message: str, use_cache: bool = False) -> str:
        """发送一回合; use_cache 时以完整 message 哈希做磁盘缓存(仅无副作用调用)。"""
        if use_cache:
            hit = self._cached(message)
            if hit is not None:
                return hit
        send = {"type": "prompt", "message": message}
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps(send, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        self.calls += 1
        out = self._drain_until_agent_end()
        if use_cache:
            self._store(message, out)
        return out

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            self.proc.kill()


class OmpOneshot(OmpBase):
    """独立单回合调用: 每次新进程, 会话零污染(rerank/作答/判分/假设)。"""

    def __call__(self, prompt: str, system: str = "") -> str:
        hit = self._cached(prompt)
        if hit is not None:
            return hit
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="omp_prompt_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(prompt)
            argv = ["omp", "-p", "--mode=json", "--no-session", "--no-tools",
                    "--no-lsp", f"@{path}"]
            if system:
                argv += ["--append-system-prompt", system]
            t0 = time.perf_counter()
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  timeout=self.timeout,
                                  input="", cwd=str(Path.home()))
            self.calls += 1
            if proc.returncode != 0:
                raise OmpError(f"omp -p exit={proc.returncode}: "
                               f"{proc.stderr[-200:] if proc.stderr else ''}")
            text = self._parse_json_mode(proc.stdout)
            if not text.strip():
                raise OmpError("omp -p 空回复")
            self.last_latency = time.perf_counter() - t0
            self._store(prompt, text)
            return text
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    @staticmethod
    def _parse_json_mode(stdout: str) -> str:
        """`--mode=json` JSONL 事件流 → 聚合 assistant 文本(与平台解析同思路)。"""
        texts: list[str] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            # 兼容事件形 {type:"message_end",message:{role,content}} 与
            # 汇总形 {result|text|content}
            if isinstance(m, dict) and m.get("type") == "message_end":
                msg = m.get("message") or {}
                if msg.get("role") == "assistant":
                    for b in msg.get("content") or []:
                        if isinstance(b, dict) and b.get("type") == "text":
                            texts.append(str(b.get("text", "")))
            elif isinstance(m, dict) and m.get("role") == "assistant":
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "text":
                        texts.append(str(b.get("text", "")))
        return "".join(texts).strip()


def extract_json(text: str):
    """从回复中取第一个 JSON 值(容忍 ```json 围栏)。

    同时尝试 '{' 与 '[' 两种括号, 取出现更早且括号平衡解析成功者 —
    旧实现先扫 '{' 会把数组里的第一个元素当整体返回, 导致 rank 类
    数组输出被判失败。字符串内的括号/引号已做转义感知。
    """
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    body = fence.group(1) if fence else text
    candidates = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = body.find(open_ch)
        if start < 0:
            continue
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(body)):
            ch = body[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        candidates.append((start, i + 1))
                        break
    for start, end in sorted(candidates):
        try:
            return json.loads(body[start:end])
        except json.JSONDecodeError:
            continue
    return None
