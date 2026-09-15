"""LLM channel for answer generation.

Uses **omp** in one-shot JSON mode — the same channel and invocation the paper's
benchmark suite uses (`benchmark-suite/algorithms/omp_client.py`), so an answer
produced here is generated under the same protocol as the published results:

    omp -p --mode=json --no-session --no-tools --no-lsp @<prompt file>

Each call is a fresh process with an empty session *and no tools*, which matters
for a benchmark: the model cannot go and fetch anything itself, so the answer can
only come from the evidence the chosen retrieval method supplied. That is what
makes the comparison attributable to retrieval rather than to the model's prior
knowledge.

The prompt travels in a file (`@path`) rather than on argv to avoid Windows
command-line length limits on long evidence blocks.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

#: `--mode=json` emits one JSON event per line; the assistant text arrives in
#: `message_end` events. Same aggregation the platform harness performs.
_TEXT_BLOCK = "text"


class LlmUnavailable(RuntimeError):
    """Raised when the omp CLI is missing, fails, or returns nothing usable."""


@dataclass
class LlmResult:
    """One completed generation."""

    text: str
    latency_s: float


@lru_cache(maxsize=1)
def available() -> tuple[bool, str]:
    """Is the LLM channel usable? Returns ``(ok, detail)``."""
    try:
        proc = subprocess.run(["omp", "--version"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60,
                              input="", cwd=str(Path.home()))
    except FileNotFoundError:
        return False, ("the 'omp' CLI was not found on PATH — install oh-my-pi "
                       "(or set up another harness) to enable answer generation")
    except Exception as exc:  # noqa: BLE001
        return False, f"could not run 'omp --version': {type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        return False, f"'omp --version' exited {proc.returncode}"
    banner = (proc.stdout or proc.stderr or "").strip().splitlines()
    return True, banner[0] if banner else "omp ready"


def _aggregate(stdout: str) -> str:
    """Collapse an ``--mode=json`` event stream into the assistant's text."""
    pieces: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "message_end":
            message = event.get("message") or {}
            if message.get("role") == "assistant":
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == _TEXT_BLOCK:
                        pieces.append(str(block.get("text", "")))
        elif event.get("role") == "assistant":  # aggregated form
            for block in event.get("content") or []:
                if isinstance(block, dict) and block.get("type") == _TEXT_BLOCK:
                    pieces.append(str(block.get("text", "")))
    return "".join(pieces).strip()


def complete(prompt: str, system: str = "", timeout: float = 300.0) -> LlmResult:
    """Run one stateless generation.

    Raises :class:`LlmUnavailable` on any failure — a caller must never be
    handed a fabricated or empty answer in place of an error.
    """
    ok, detail = available()
    if not ok:
        raise LlmUnavailable(detail)

    handle, path = tempfile.mkstemp(suffix=".txt", prefix="bench_answer_")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(prompt)
        argv = ["omp", "-p", "--mode=json", "--no-session", "--no-tools",
                "--no-lsp", f"@{path}"]
        if system:
            argv += ["--append-system-prompt", system]
        started = time.perf_counter()
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  timeout=timeout, input="", cwd=str(Path.home()))
        except subprocess.TimeoutExpired as exc:
            raise LlmUnavailable(
                f"the model did not finish within {timeout:.0f}s — retry, or lower "
                "the evidence budget / choose a cheaper method"
            ) from exc
        elapsed = time.perf_counter() - started
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise LlmUnavailable(
            f"omp exited {proc.returncode}"
            + (f": {stderr[-240:]}" if stderr else " (no stderr)")
        )
    text = _aggregate(proc.stdout)
    if not text:
        raise LlmUnavailable("omp returned an empty response")
    return LlmResult(text=text, latency_s=round(elapsed, 2))


def extract_json(text: str):
    """Pull the first balanced JSON value out of a model reply.

    Tolerates ```json fences and leading prose. Compares ``{`` and ``[`` starts
    and returns whichever parses, so an array answer is not mistaken for its
    first element (the bug the paper suite fixed in its own helper).
    """
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    body = fence.group(1) if fence else text

    spans: list[tuple[int, int]] = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = body.find(open_ch)
        if start < 0:
            continue
        depth, in_string, escaped = 0, False, False
        for i in range(start, len(body)):
            ch = body[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    spans.append((start, i + 1))
                    break

    for start, end in sorted(spans):
        try:
            return json.loads(body[start:end])
        except json.JSONDecodeError:
            continue
    return None
