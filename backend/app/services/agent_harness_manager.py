"""Agent Harness Manager — spawn Claude Code / OMP as subprocesses for LLM synthesis.

Design mirrors MinerU manager:
- Windows: Job Object KILL_ON_JOB_CLOSE (no orphans)
- Linux: prctl(PR_SET_PDEATHSIG)
- stdout/stderr → log file (never PIPE)
- Hard timeout + budget cap
- Global concurrency semaphore
"""
from __future__ import annotations

import asyncio
import atexit
import ctypes
import json
import logging
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from app.utils.paths import PROJECT_ROOT

# ── Log directory ──
_LOG_DIR = PROJECT_ROOT.parent / "backend" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── MCP config path (project root .mcp.json) ──
_MCP_CONFIG_PATH = PROJECT_ROOT.parent / ".mcp.json"


def _repair_embedded_quotes(raw: str) -> str | None:
    """宽松修复 JSON: 把字符串值内未转义的成对英文引号替换为中文引号。

    LLM 输出常在 alignment_notes/q_text 等字段内嵌引用(如 开篇即\"先结论后论证\")
    而忘记转义,导致 json.loads 失败。修复策略: 在 JSON 字符串值内部,把
    "成对出现"的英文引号替换为中文引号 \u201c \u201d(成对 = 字符串值内
    除边界外剩余的引号数量为偶数时,逐对替换)。
    """
    out = []
    in_str = False
    escape = False
    i = 0
    n = len(raw)
    changed = False
    while i < n:
        ch = raw[i]
        if in_str:
            if escape:
                out.append(ch)
                escape = False
            elif ch == "\\":
                out.append(ch)
                escape = True
            elif ch == '"':
                # 判断这是值边界还是内嵌引号: 向前看本字符串内是否还有未闭合引号
                # 简单启发: 若下一个非空白字符不是 , } ] : 且当前位置之后
                # 到行尾/逗号前还有偶数个引号,则视为内嵌引号对的开头或中间
                j = i + 1
                while j < n and raw[j] in " \t\n\r":
                    j += 1
                nxt = raw[j] if j < n else ""
                if nxt in ",}]:" or nxt == "":
                    out.append(ch)
                    in_str = False
                else:
                    # 内嵌引号: 找它的配对(下一个未转义引号)
                    k = j
                    while k < n:
                        if raw[k] == "\\":
                            k += 2
                            continue
                        if raw[k] == '"':
                            break
                        k += 1
                    if k < n:
                        # 配对存在 → 替换为中文引号对
                        out.append("\u201c")
                        # 复制中间内容
                        out.append(raw[j:k])
                        out.append("\u201d")
                        i = k
                        changed = True
                    else:
                        # 无配对 → 视为值边界
                        out.append(ch)
                        in_str = False
            else:
                out.append(ch)
        else:
            if ch == '"':
                in_str = True
                out.append(ch)
            else:
                out.append(ch)
        i += 1
    return "".join(out) if changed else None


# ── System prompt path ──
_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "meditation_agent_system.txt"

# ── Result JSON Schema (for claude --json-schema) ──
RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "meditation_result": {
            "type": "object",
            "properties": {
                "kb_id": {"type": "string"},
                "experiences_created": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "exp_id": {"type": "string"},
                            "scenario": {"type": "string"},
                            "quality_score": {"type": "number"}
                        }
                    }
                },
                "drafts_created": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "draft_id": {"type": "string"},
                            "quality_score": {"type": "number"}
                        }
                    }
                },
                "skipped": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "reason": {"type": "string"}
                        }
                    }
                },
                "total_signals_processed": {"type": "integer"},
                "summary": {"type": "string"}
            },
            "required": ["total_signals_processed", "experiences_created", "drafts_created"]
        }
    },
    "required": ["meditation_result"]
}

# ── Harness command configurations ──
HARNESS_CONFIG: dict[str, dict] = {
    "omp": {
        "exe": "omp",
        "build_args": lambda cfg, prompt_file: [
            "-p",
            "--auto-approve",
            "--no-session",
            "--mode=json",
            "--max-time", str(cfg.get("timeout_sec", 600)),
            # Use model from KB config; empty = OMP uses its own default (e.g. deepseek-v4-pro)
        ] + ([
            "--model", cfg["model"]
        ] if cfg.get("model") else []) + [
            f"@{prompt_file}",
        ],
        # NOTE: --cwd is NOT used here because OMP mangles the path.
        # Working directory is set via subprocess.Popen(cwd=...) instead.
        "stdin_needed": False,
    },
    "claude": {
        "exe": "claude",
        "build_args": lambda cfg, prompt_file: [
            "-p",
            "--output-format", "json",
            # Use model from KB config; fall back to sonnet
            "--model", cfg.get("model") or "claude-sonnet-4-20250514",
            "--max-budget-usd", str(cfg.get("max_budget_usd", 0.05)),
            "--dangerously-skip-permissions",
            "--no-session-persistence",
            "--bare",
            "--mcp-config", str(_MCP_CONFIG_PATH),
            "--add-dir", str(PROJECT_ROOT.parent),
            "--system-prompt-file", str(_SYSTEM_PROMPT_PATH),
            "--json-schema", json.dumps(RESULT_SCHEMA),
        ],
        "stdin_needed": True,
    },
}


# ── Windows Job Object helpers (reuse MinerU pattern) ──

def _create_kill_on_close_job() -> Any:
    """Create a Windows Job Object that kills children when this process exits."""
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        hjob = kernel32.CreateJobObjectW(None, None)
        if not hjob:
            logger.warning("CreateJobObjectW failed: %s", ctypes.get_last_error())
            return None

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        JobObjectExtendedLimitInformation = 9

        if not kernel32.SetInformationJobObject(
            hjob, JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info)
        ):
            logger.warning("SetInformationJobObject failed: %s", ctypes.get_last_error())
            kernel32.CloseHandle(hjob)
            return None

        return hjob
    except Exception:
        logger.warning("Failed to create Job Object (non-fatal)", exc_info=True)
        return None


def _assign_pid_to_job(job_handle: Any, pid: int) -> None:
    """Assign a process to the job object."""
    if sys.platform != "win32" or job_handle is None:
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        import ctypes.wintypes
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_TERMINATE = 0x0001
        hproc = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
        if not hproc:
            return
        kernel32.AssignProcessToJobObject(job_handle, hproc)
        kernel32.CloseHandle(hproc)
    except Exception:
        pass


def _close_job_handle(job_handle: Any) -> None:
    """Close the job object handle."""
    if sys.platform != "win32" or job_handle is None:
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle(job_handle)
    except Exception:
        pass


def _run_silent_kwargs() -> dict:
    """Extra kwargs for subprocess.run so probes never flash a console window."""
    if sys.platform != "win32":
        return {}
    flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flags |= subprocess.CREATE_NO_WINDOW
    si = subprocess.STARTUPINFO()
    si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    si.wShowWindow = 0
    return {"creationflags": flags, "startupinfo": si}


class AgentHarnessManager:
    """Spawn Claude Code / OMP as subprocesses for LLM synthesis.

    Design:
    - Windows: Job Object KILL_ON_JOB_CLOSE (no orphans)
    - stdout/stderr → log file (never PIPE)
    - Hard timeout + global concurrency semaphore
    - Circuit breaker after 3 consecutive failures
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # 训练并行度: 默认 4(配置可调), 支持并行批处理 Actor 管道
        try:
            from app.config import config
            _concurrency = config.soul_train_concurrency
        except Exception:
            _concurrency = 4
        self._semaphore = asyncio.Semaphore(_concurrency)
        self._job_handle = _create_kill_on_close_job()
        self._circuit_open: dict[str, float] = {}  # harness → tripped_until timestamp
        self._consecutive_failures: dict[str, int] = {}
        self._harness_available: dict[str, dict] = {}
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        _close_job_handle(self._job_handle)
        self._job_handle = None

    # ── Health Check ───────────────────────────────────────────────────

    async def probe_harness(self, harness: str) -> dict:
        """Probe whether a harness is installed and ready. Cached after first call."""
        if harness in self._harness_available:
            return self._harness_available[harness]

        if harness not in HARNESS_CONFIG:
            return {"installed": False, "error": f"Unknown harness: {harness}"}

        cfg = HARNESS_CONFIG[harness]
        exe = cfg["exe"]

        # Check if executable is findable
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [exe, "--version"],
                    capture_output=True, timeout=15,
                    **_run_silent_kwargs(),
                )
            )
            installed = result.returncode == 0
            version = result.stdout.decode("utf-8", errors="replace").strip()
        except Exception as e:
            installed = False
            version = ""
            logger.debug("Harness probe for %s failed: %s", harness, e)

        # Additional checks per harness
        extra = {}
        if harness == "claude":
            extra["api_key_configured"] = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
            if not extra["api_key_configured"]:
                installed = False  # claude --bare mode requires API key

        info = {
            "installed": installed,
            "version": version,
            **extra,
        }
        self._harness_available[harness] = info
        return info

    async def get_all_harness_status(self) -> dict:
        """Get status for all harnesses + circuit breaker state."""
        status = {}
        for name in HARNESS_CONFIG:
            status[name] = await self.probe_harness(name)

        return {
            "harnesses": status,
            "circuit_breaker": {
                harp: {
                    "tripped": harp in self._circuit_open and self._circuit_open[harp] > time.time(),
                    "until": self._circuit_open.get(harp),
                    "consecutive_failures": self._consecutive_failures.get(harp, 0),
                }
                for harp in HARNESS_CONFIG
            }
        }

    def _check_circuit(self, harness: str) -> str | None:
        """Check if circuit breaker is open. Returns error message or None."""
        if harness not in self._circuit_open:
            return None
        until = self._circuit_open[harness]
        if until > time.time():
            remaining = int(until - time.time())
            return f"Circuit breaker open for {harness} — {remaining}s remaining (consecutive failures: {self._consecutive_failures.get(harness, 0)})"
        # Circuit expired, reset
        del self._circuit_open[harness]
        return None

    def _record_failure(self, harness: str) -> None:
        self._consecutive_failures[harness] = self._consecutive_failures.get(harness, 0) + 1
        if self._consecutive_failures[harness] >= 3:
            self._circuit_open[harness] = time.time() + 86400  # 24h
            logger.warning("Circuit breaker OPEN for %s (3 consecutive failures)", harness)

    def _record_success(self, harness: str) -> None:
        self._consecutive_failures[harness] = 0
        self._circuit_open.pop(harness, None)

    # ── Synthesis ──────────────────────────────────────────────────────

    async def synthesize_experiences(
        self,
        kb_path: str,
        kb_id: str,
        signals: list[dict],
        kb_config: dict,
        trigger: str = "scheduled",
    ) -> dict:
        """Spawn agent to synthesize experiences from signals.

        Returns {"success": bool, "experiences": [...], "drafts": [...], "error": ...}
        """
        harness = kb_config.get("harness", "omp")

        # Heuristic is always available (no subprocess needed)
        if harness == "heuristic":
            logger.info("Using heuristic harness for KB %s", kb_path)
            return await self._heuristic_fallback(kb_path, kb_id, signals, kb_config, trigger)

        # Check circuit breaker
        breaker_msg = self._check_circuit(harness)
        if breaker_msg:
            logger.warning("Circuit breaker: %s", breaker_msg)
            if trigger == "manual":
                # Manual trigger should not silently produce low-quality heuristic output.
                return {"success": False,
                        "error": f"Agent harness '{harness}' circuit breaker tripped: {breaker_msg}. "
                                 f"Wait or reset the breaker, then retry.",
                        "harness": harness, "trigger": trigger}
            return await self._heuristic_fallback(kb_path, kb_id, signals, kb_config, trigger)

        # Check harness availability
        probe = await self.probe_harness(harness)
        if not probe.get("installed", False):
            logger.info("Harness %s not available", harness)
            if trigger == "manual":
                # Manual trigger: tell user the agent isn't ready, don't silently
                # produce placeholder experiences.
                missing = []
                if not probe.get("installed"):
                    missing.append(f"executable '{harness}' not found on PATH")
                if harness == "claude" and not probe.get("api_key_configured"):
                    missing.append("ANTHROPIC_API_KEY not set")
                return {"success": False,
                        "error": f"Agent harness '{harness}' is not available for real LLM synthesis. "
                                 f"Issues: {'; '.join(missing)}. "
                                 f"Install/configure the harness, then retry meditation.",
                        "harness": harness, "probe": probe, "trigger": trigger}
            # Scheduled/incremental: silent fallback is acceptable
            return await self._heuristic_fallback(kb_path, kb_id, signals, kb_config, trigger)

        # Build task prompt
        task_prompt = self._build_task_prompt(kb_path, kb_id, signals, kb_config, trigger)

        # Spawn agent under semaphore
        async with self._semaphore:
            return await self._spawn_agent(harness, kb_path, kb_id, signals, kb_config, trigger, task_prompt)

    def _build_task_prompt(
        self, kb_path: str, kb_id: str, signals: list[dict],
        kb_config: dict, trigger: str
    ) -> str:
        """Build the task prompt with signal data for the agent."""
        kb_name = kb_path.rsplit("/", 1)[-1] if "/" in kb_path else kb_path
        lookback_days = kb_config.get("interval_hours", 24) // 24 or 7
        max_drafts = kb_config.get("max_drafts_per_run", 3)
        auto_publish = kb_config.get("auto_publish", False)

        # Prepend system prompt so BOTH harnesses (claude via --system-prompt-file,
        # omp via @prompt_file) get the quality standards and doc-reading instructions.
        sys_prompt = ""
        try:
            sys_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
        except Exception:
            pass

        lines = [
            sys_prompt,
            "",
            "---",
            "",
            "## 本次冥想任务",
            "",
            f"目标知识库: {kb_name} (id={kb_id}, path={kb_path})",
            f"触发器: {trigger}",
            f"信号窗口: 最近 {lookback_days} 天",
            f"待处理信号: {len(signals)} 条",
            f"最大产出: {max_drafts} 条经验",
            f"自动发布: quality>=7 且 auto_publish={auto_publish}",
            "",
            "## 待处理问题信号",
        ]

        for i, sig in enumerate(signals[:20], 1):  # Cap at 20 to avoid prompt bloat
            lines.append(f"### 信号 {i}")
            lines.append(f"问题: {sig.get('question_text', '')[:300]}")
            answer = sig.get("assistant_answer", "")
            if answer:
                lines.append(f"回答摘要: {answer[:300]}")
            docs = sig.get("retrieved_docs", "[]")
            try:
                docs_list = json.loads(docs) if isinstance(docs, str) else docs
            except Exception:
                docs_list = []
            if docs_list:
                lines.append("相关检索文档（请用 kb_doc_read 读取全文验证）:")
                for doc in docs_list[:3]:
                    if isinstance(doc, dict):
                        lines.append(f"  - path={doc.get('path', '?')}, score={doc.get('score', '?')}")
                    else:
                        lines.append(f"  - {doc}")
            lines.append("")

        lines.append("## ⚠️ 输出格式要求（必须严格遵守）")
        lines.append("")
        lines.append("你的最后一条消息必须且仅包含以下 JSON 格式的 meditation_result，")
        lines.append("不要添加任何 markdown 表格、解释说明、或其他格式的文字。")
        lines.append("")
        lines.append('```json')
        lines.append('{')
        lines.append('  "meditation_result": {')
        lines.append('    "kb_id": "' + kb_id + '",')
        lines.append('    "experiences_created": [],')
        lines.append('    "drafts_created": [],')
        lines.append('    "skipped": [],')
        lines.append('    "total_signals_processed": 0,')
        lines.append('    "summary": "..."')
        lines.append('  }')
        lines.append('}')
        lines.append('```')
        lines.append("")
        lines.append("所有经验必须通过 kb_doc_read 验证文档后再创建。")
        lines.append("如果信号不足以支撑高质量经验，返回空列表而不是编造。")
        return "\n".join(lines)

    async def _spawn_agent(
        self, harness: str, kb_path: str, kb_id: str,
        signals: list[dict], kb_config: dict, trigger: str,
        task_prompt: str,
    ) -> dict:
        """Spawn agent subprocess and wait for completion."""
        from app.services.meditation_db import create_run, finish_run

        cfg = HARNESS_CONFIG[harness]
        run_id = create_run(kb_id, harness, trigger)

        log_path = _LOG_DIR / f"meditation-agent-{run_id}.log"

        # Write task prompt to temp file (for omp @ref; claude uses stdin)
        prompt_file = None
        try:
            prompt_file = Path(tempfile.mktemp(suffix=".txt"))
            prompt_file.write_text(task_prompt, encoding="utf-8")
        except Exception:
            prompt_file = _LOG_DIR / f"meditation-prompt-{run_id}.txt"
            prompt_file.write_text(task_prompt, encoding="utf-8")

        try:
            cmd = [cfg["exe"]] + cfg["build_args"](kb_config, str(prompt_file))
        except Exception as e:
            finish_run(run_id, status="failed", error=f"cmd_build: {e}")
            if prompt_file and prompt_file.exists():
                prompt_file.unlink(missing_ok=True)
            return {"success": False, "error": f"Failed to build command: {e}", "run_id": run_id}

        # Resolve executable path on Windows
        if sys.platform == "win32" and not cfg["exe"].endswith(".exe"):
            # Check common locations
            candidates = [
                Path(os.path.expandvars(f"%USERPROFILE%\\.local\\bin\\{cfg['exe']}.exe")),
                Path(os.path.expandvars(f"%USERPROFILE%\\.bun\\bin\\{cfg['exe']}.exe")),
                Path(f"C:\\Users\\{os.environ.get('USERNAME', '')}\\.local\\bin\\{cfg['exe']}.exe"),
                Path(f"C:\\Users\\{os.environ.get('USERNAME', '')}\\.bun\\bin\\{cfg['exe']}.exe"),
            ]
            for candidate in candidates:
                if candidate.exists():
                    cmd[0] = str(candidate)
                    break

        logger.info("[Meditation] kb=%s harness=%s run_id=%s cmd=%s",
                    kb_path, harness, run_id, cmd[0])

        # Open log file
        try:
            log_fp = open(str(log_path), "a", encoding="utf-8")
        except Exception as e:
            finish_run(run_id, status="failed", error=f"log_open: {e}")
            if prompt_file and prompt_file.exists():
                prompt_file.unlink(missing_ok=True)
            return {"success": False, "error": f"Cannot open log: {e}", "run_id": run_id}

        log_fp.write(f"=== Meditation Run {run_id} ===\n")
        log_fp.write(f"KB: {kb_path}\nHarness: {harness}\nTrigger: {trigger}\n")
        log_fp.write(f"Started: {datetime.now(timezone.utc).isoformat()}\n")
        log_fp.write(f"Signals: {len(signals)}\n")
        log_fp.write(f"Command: {' '.join(cmd)}\n\n")

        # Build popen kwargs
        popen_kwargs: dict = dict(
            cwd=str(PROJECT_ROOT.parent),
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
            close_fds=True,
        )

        if cfg["stdin_needed"]:
            popen_kwargs["stdin"] = subprocess.PIPE
        else:
            popen_kwargs["stdin"] = subprocess.DEVNULL

        if sys.platform == "win32":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            popen_kwargs["startupinfo"] = si
        else:
            popen_kwargs["start_new_session"] = True

        # Spawn
        try:
            proc = subprocess.Popen(cmd, **popen_kwargs)
        except FileNotFoundError:
            log_fp.close()
            finish_run(run_id, status="failed", error=f"executable not found: {cfg['exe']}")
            self._record_failure(harness)
            if prompt_file.exists():
                prompt_file.unlink(missing_ok=True)
            return {"success": False, "error": f"Executable not found: {cfg['exe']}", "run_id": run_id}

        # Assign to job object
        _assign_pid_to_job(self._job_handle, proc.pid)

        # Write task prompt to stdin for claude
        if cfg["stdin_needed"] and proc.stdin:
            try:
                proc.stdin.write(task_prompt.encode("utf-8"))
                proc.stdin.close()
            except Exception:
                pass

        # Wait with timeout
        timeout = kb_config.get("timeout_sec", 600)
        try:
            await self._watch_process(proc, log_path, timeout)
        except Exception as e:
            logger.warning("Process watch error: %s", e)

        # Clean up temp file
        if prompt_file.exists():
            prompt_file.unlink(missing_ok=True)

        # Read log and parse result
        log_fp.close()
        exit_code = proc.poll()

        if exit_code is None:
            self._terminate_process(proc)
            finish_run(run_id, status="timeout", error="timeout")
            self._record_failure(harness)
            return {"success": False, "error": "timeout", "run_id": run_id}

        # Parse result from log
        result = self._parse_result_log(log_path, harness)

        if result.get("success"):
            self._record_success(harness)
            finish_run(
                run_id,
                status="completed",
                experiences_created=len(result.get("experiences", [])),
                drafts_created=len(result.get("drafts", [])),
                signals_processed=len(signals),
                exit_code=exit_code,
                report_json=json.dumps(result, ensure_ascii=False),
            )
            # Mark signals as derived
            try:
                from app.services.meditation_db import mark_signals_derived
                signal_ids = [s.get("id") for s in signals if s.get("id")]
                if signal_ids:
                    mark_signals_derived(signal_ids)
            except Exception as e:
                logger.warning("Failed to mark signals derived: %s", e)
            # Update KB meditation config
            try:
                from app.services.kb_meditation_config import update_meditation_config
                update_meditation_config(kb_id, {
                    "last_run_at": datetime.now(timezone.utc).isoformat(),
                    "last_run_status": "success",
                    "total_runs": kb_config.get("total_runs", 0) + 1,
                    "total_experiences_generated": kb_config.get("total_experiences_generated", 0) + len(result.get("experiences", [])) + len(result.get("drafts", [])),
                })
            except Exception as e:
                logger.warning("Failed to update KB meditation config: %s", e)
        else:
            self._record_failure(harness)
            finish_run(
                run_id,
                status="failed",
                error=result.get("error", "parse_failed"),
                exit_code=exit_code,
                agent_stdout_tail=self._read_log_tail(log_path),
            )

        result["run_id"] = run_id
        return result

    async def _watch_process(self, proc: subprocess.Popen, log_path: Path, timeout_sec: int) -> None:
        """Wait for process with timeout."""

        def _wait():
            try:
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                pass

        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _wait),
                timeout=timeout_sec + 10,
            )
        except asyncio.TimeoutError:
            self._terminate_process(proc)

    def _terminate_process(self, proc: subprocess.Popen) -> None:
        """Cross-platform process + subtree kill."""
        if proc.poll() is not None:
            return
        pid = proc.pid
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, timeout=10,
                    **_run_silent_kwargs(),
                )
            else:
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)
                    time.sleep(5)
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except Exception:
            logger.warning("Failed to terminate process %s", pid, exc_info=True)

    def _parse_result_log(self, log_path: Path, harness: str) -> dict:
        """Parse agent output from log file, extracting the result JSON."""
        if not log_path.exists():
            return {"success": False, "error": "log_missing"}

        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return {"success": False, "error": "log_read_failed"}

        # Strategy 0: OMP streaming JSON (line-delimited JSON events)
        if harness == "omp":
            for line in content.split("\n"):
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # OMP puts final response in message_end, agent_end, or turn_end
                if event.get("type") in ("agent_end", "turn_end", "message_end"):
                    msg_data = event.get("message") or event.get("messages", [])
                    if isinstance(msg_data, dict):
                        msg_list = [msg_data]
                    else:
                        msg_list = msg_data
                    assistant_msgs = [m for m in msg_list if isinstance(m, dict) and m.get("role") == "assistant"]
                    if assistant_msgs:
                        last_msg = assistant_msgs[-1]
                        content_blocks = last_msg.get("content", [])
                        text_blocks = [b for b in content_blocks if b.get("type") == "text"]
                        assistant_text = "\n".join(b.get("text", "") for b in text_blocks)
                        # Try to find meditation_result JSON
                        # First try direct search in raw text
                        mr_match = re.search(r'\{\s*"meditation_result"\s*:\s*\{', assistant_text, re.DOTALL)
                        # Strip leading/trailing ``` fences (not inline ones)
                        search_text = assistant_text
                        if search_text.lstrip().startswith("```"):
                            first_nl = search_text.find("\n")
                            if first_nl > 0:
                                search_text = search_text[first_nl+1:]
                        if search_text.rstrip().endswith("```"):
                            search_text = search_text[:search_text.rfind("```")].rstrip()
                        mr_match = re.search(r'\{\s*"meditation_result"\s*:\s*\{', search_text, re.DOTALL)
                        if mr_match:
                            assistant_text = search_text
                            start = mr_match.start()
                            depth = 0
                            end = start
                            for i in range(start, len(assistant_text)):
                                if assistant_text[i] == '{':
                                    depth += 1
                                elif assistant_text[i] == '}':
                                    depth -= 1
                                    if depth == 0:
                                        end = i + 1
                                        break
                            if end > start:
                                try:
                                    parsed = json.loads(assistant_text[start:end])
                                    mr = parsed.get("meditation_result", {})
                                    return self._build_result(mr)
                                except (json.JSONDecodeError, Exception):
                                    mr = self._regex_extract_result(assistant_text[start:end])
                                    if mr and (mr.get("experiences_created") or mr.get("drafts_created") or mr.get("skipped")):
                                        return self._build_result(mr)
            # Fall through to other strategies if OMP parsing failed

        # Strategy 1: Find meditation_result JSON block
        # Look for {"meditation_result" or {\n"meditation_result" ...} pattern
        match = re.search(r'\{\s*"meditation_result"\s*:\s*\{', content, re.DOTALL)
        if match:
            # Find the closing brace by counting
            start = match.start()
            depth = 0
            end = start
            for i in range(start, len(content)):
                if content[i] == '{':
                    depth += 1
                elif content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > start:
                try:
                    parsed = json.loads(content[start:end])
                    mr = parsed.get("meditation_result", {})
                    return self._build_result(mr)
                except json.JSONDecodeError:
                    pass

        # Strategy 2: Look for any JSON object containing "experiences_created"
        matches = list(re.finditer(r'\{[^{}]*"experiences_created"[^{}]*\}', content))
        if matches:
            for m in reversed(matches):
                try:
                    mr = json.loads(m.group())
                    return self._build_result(mr)
                except json.JSONDecodeError:
                    continue

        # Strategy 3: Look for the last complete JSON block
        json_blocks = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content))
        for m in reversed(json_blocks):
            try:
                parsed = json.loads(m.group())
                if isinstance(parsed, dict) and "meditation_result" in parsed:
                    return self._build_result(parsed["meditation_result"])
            except json.JSONDecodeError:
                continue

        return {"success": False, "error": "parse_failed", "log_tail": self._read_log_tail(log_path)}

    @staticmethod
    def _build_result(mr: dict) -> dict:
        """Build standardized result dict from meditation_result."""
        return {
            "success": True,
            "kb_id": mr.get("kb_id", ""),
            "experiences": mr.get("experiences_created", []),
            "drafts": mr.get("drafts_created", []),
            "skipped": mr.get("skipped", []),
            "total_signals_processed": mr.get("total_signals_processed", 0),
            "summary": mr.get("summary", ""),
        }

    @staticmethod
    def _regex_extract_result(text: str) -> dict | None:
        """Fallback: extract meditation_result fields via regex when JSON is malformed."""
        import re as _re
        result: dict = {"experiences_created": [], "drafts_created": [], "skipped": [], "total_signals_processed": 0, "summary": ""}
        # Extract experiences_created count
        exp_match = _re.search(r'"experiences_created"\s*:\s*\[', text)
        if exp_match:
            # Count items in the array
            arr_start = exp_match.end() - 1
            depth = 0; arr_end = arr_start
            for i in range(arr_start, len(text)):
                if text[i] == '[': depth += 1
                elif text[i] == ']':
                    depth -= 1
                    if depth == 0: arr_end = i+1; break
            # Count non-empty items
            arr_content = text[arr_start:arr_end]
            items = _re.findall(r'"title"\s*:', arr_content)
            result["experiences_created"] = [{} for _ in items]
        # Extract drafts_created count
        draft_match = _re.search(r'"drafts_created"\s*:\s*\[', text)
        if draft_match:
            arr_start = draft_match.end() - 1
            depth = 0
            for i in range(arr_start, len(text)):
                if text[i] == '[': depth += 1
                elif text[i] == ']':
                    depth -= 1
                    if depth == 0: break
            arr_content = text[arr_start:i+1] if depth == 0 else text[arr_start:]
            items = _re.findall(r'"title"\s*:', arr_content)
            result["drafts_created"] = [{} for _ in items]
        # Extract skipped count
        skip_match = _re.search(r'"skipped"\s*:\s*\[', text)
        if skip_match:
            arr_start = skip_match.end() - 1
            depth = 0; arr_end = arr_start
            for i in range(arr_start, len(text)):
                if text[i] == '[': depth += 1
                elif text[i] == ']':
                    depth -= 1
                    if depth == 0: arr_end = i+1; break
            # Count string items in skipped array
            skipped_text = text[arr_start:arr_end]
            # Count quoted strings
            str_items = _re.findall(r'"([^"]*(?:\\.[^"]*)*)"', skipped_text)
            result["skipped"] = str_items
        # Extract total_signals_processed
        tsp = _re.search(r'"total_signals_processed"\s*:\s*(\d+)', text)
        if tsp: result["total_signals_processed"] = int(tsp.group(1))
        # Extract summary
        sum_match = _re.search(r'"summary"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text, _re.DOTALL)
        if sum_match: result["summary"] = sum_match.group(1)[:500]
        result["kb_id"] = ""
        return result
    def _read_log_tail(self, log_path: Path, n: int = 500) -> str:
        """Read last n characters of log file."""
        if not log_path.exists():
            return ""
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
            return content[-n:] if len(content) > n else content
        except Exception:
            return ""

    # ── Generic Completion (SOUL) ──────────────────────────────────────

    # Rough per-1k-token cost estimate (fixed rates, budget accounting only)
    _TOKEN_COST_PER_1K: dict[str, float] = {"claude": 0.005, "omp": 0.001}
    # Rough synthesis-time estimate: seconds per token (sync-timeout estimation)
    _TOKENS_PER_SEC: dict[str, float] = {"claude": 0.02, "omp": 0.015}

    async def complete(
        self,
        prompt: str,
        kb_config: dict | None = None,
        result_schema: dict | None = None,
        system_prompt_path: str | Path | None = None,
        timeout_sec: int = 120,
        max_budget_usd: float | None = None,
        expected_output_tokens: int = 512,
    ) -> dict:
        """Generic single-shot LLM completion via the claude/omp harness.

        Fully independent of the meditation pipeline: the caller supplies the
        prompt, an optional JSON schema (claude branch), and an optional system
        prompt file. Reuses only the spawn / semaphore / circuit-breaker /
        timeout / process-cleanup machinery of this manager.

        NOTE: caller-owned call counting and budget check-and-deduct live in the
        SOUL run context (see soul_learn/soul_service); this method is stateless
        and returns token/cost estimates for the caller to accumulate.

        Args:
            prompt: The full user prompt (system content should be wrapped in
                <USER_CONTENT>...</USER_CONTENT> tags per SOUL injection-defense
                convention).
            kb_config: harness/model/timeout settings (same keys as meditation
                config: harness, model, timeout_sec, max_budget_usd).
            result_schema: JSON schema for claude --json-schema; when provided,
                ``parsed`` is populated from the validated JSON. For omp, the
                schema is embedded in the prompt instead and parsed best-effort.
            system_prompt_path: optional system prompt file (claude
                --system-prompt-file; omp gets it prepended to the prompt).
            timeout_sec: per-call hard timeout (default 120).
            max_budget_usd: claude --max-budget-usd override.
            expected_output_tokens: used for the sync-time estimate.

        Returns:
            {"success": bool, "text": str, "parsed": dict|list|None,
             "harness": str, "error": str|None, "elapsed": float,
             "token_estimate": int, "cost_estimate": float,
             "estimated_seconds": float}
        """
        cfg = kb_config or {}
        harness = cfg.get("harness", "omp")
        start = time.time()

        if harness not in HARNESS_CONFIG:
            return self._complete_error(
                f"Unknown harness: {harness}", harness, start)

        # Circuit breaker
        breaker_msg = self._check_circuit(harness)
        if breaker_msg:
            return self._complete_error(
                f"Harness '{harness}' circuit breaker tripped: {breaker_msg}",
                harness, start)

        # Probe availability
        probe = await self.probe_harness(harness)
        if not probe.get("installed", False):
            missing = [f"executable '{harness}' not found on PATH"]
            if harness == "claude" and not probe.get("api_key_configured"):
                missing.append("ANTHROPIC_API_KEY not set")
            return self._complete_error(
                f"Harness '{harness}' unavailable: {'; '.join(missing)}",
                harness, start, probe=probe)

        # System prompt (omp branch: --system-prompt override; claude: --system-prompt-file)
        sys_text = ""
        if system_prompt_path:
            try:
                sys_text = Path(system_prompt_path).read_text(encoding="utf-8").strip()
            except Exception:
                sys_text = ""

        final_prompt = prompt
        if harness == "omp" and sys_text:
            # omp 默认注入 coding-assistant 系统提示词,会把单次补全跑成全 agent;
            # 用 --system-prompt 覆盖为调用方指定的角色(纯文本补全、快且可控)。
            final_prompt = prompt

        # Write prompt to temp file (omp @ref; claude reads from stdin)
        prompt_file = None
        try:
            prompt_file = Path(tempfile.mktemp(suffix=".txt"))
            prompt_file.write_text(final_prompt, encoding="utf-8")
        except Exception as e:
            return self._complete_error(f"prompt_write: {e}", harness, start)

        # Build CLI args (bypass module-level globals RESULT_SCHEMA / _SYSTEM_PROMPT_PATH)
        timeout = cfg.get("timeout_sec", timeout_sec)
        budget = max_budget_usd or cfg.get("max_budget_usd", 0.05)
        model = cfg.get("model", "")
        if harness == "omp":
            cmd = [HARNESS_CONFIG["omp"]["exe"], "-p", "--auto-approve",
                   "--no-session", "--mode=json", "--no-tools", "--max-time", str(timeout)]
            if sys_text:
                cmd += ["--system-prompt", sys_text]
            if model:
                cmd += ["--model", model]
            cmd += [f"@{prompt_file}"]
            stdin_needed = False
        else:  # claude
            cmd = [HARNESS_CONFIG["claude"]["exe"], "-p", "--output-format", "json",
                   "--model", model or "claude-sonnet-4-20250514",
                   "--max-budget-usd", str(budget),
                   "--dangerously-skip-permissions", "--no-session-persistence",
                   "--bare", "--mcp-config", str(_MCP_CONFIG_PATH),
                   "--add-dir", str(PROJECT_ROOT.parent)]
            if system_prompt_path:
                cmd += ["--system-prompt-file", str(system_prompt_path)]
            if result_schema:
                cmd += ["--json-schema", json.dumps(result_schema)]
            stdin_needed = True

        run_id = f"soul-{int(time.time_ns()):x}"
        log_path = _LOG_DIR / f"soul-complete-{run_id}.log"
        logger.info("[Soul-complete] harness=%s run_id=%s", harness, run_id)

        try:
            log_fp = open(str(log_path), "a", encoding="utf-8")
        except Exception as e:
            self._cleanup_prompt_file(prompt_file)
            return self._complete_error(f"log_open: {e}", harness, start)

        log_fp.write(f"=== Soul Complete {run_id} ===\n")
        log_fp.write(f"Harness: {harness}\nCommand: {' '.join(cmd)}\n\n")

        popen_kwargs: dict = dict(
            cwd=str(PROJECT_ROOT.parent),
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
            close_fds=True,
        )
        popen_kwargs["stdin"] = subprocess.PIPE if stdin_needed else subprocess.DEVNULL
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            popen_kwargs["startupinfo"] = si
        else:
            popen_kwargs["start_new_session"] = True

        try:
            proc = subprocess.Popen(cmd, **popen_kwargs)
        except FileNotFoundError:
            log_fp.close()
            self._cleanup_prompt_file(prompt_file)
            self._record_failure(harness)
            return self._complete_error(
                f"Executable not found: {HARNESS_CONFIG[harness]['exe']}",
                harness, start)

        _assign_pid_to_job(self._job_handle, proc.pid)

        if stdin_needed and proc.stdin:
            try:
                proc.stdin.write(final_prompt.encode("utf-8"))
                proc.stdin.close()
            except Exception:
                pass

        try:
            await self._watch_process(proc, log_path, timeout)
        except Exception as e:
            logger.warning("Soul-complete watch error: %s", e)

        self._cleanup_prompt_file(prompt_file)
        log_fp.close()
        exit_code = proc.poll()

        if exit_code is None:
            self._terminate_process(proc)
            self._record_failure(harness)
            return self._complete_error("timeout", harness, start)

        text, parsed = self._parse_complete_log(log_path, harness, result_schema)
        if not text and parsed is None:
            self._record_failure(harness)
            return self._complete_error(
                "parse_failed", harness, start,
                detail=self._read_log_tail(log_path))

        self._record_success(harness)
        token_estimate = max(1, (len(prompt) + len(text)) // 4)
        rate = self._TOKEN_COST_PER_1K.get(harness, 0.001)
        cost_estimate = round(token_estimate / 1000 * rate, 6)
        est_sec = (token_estimate + expected_output_tokens) * \
            self._TOKENS_PER_SEC.get(harness, 0.015)

        return {
            "success": True,
            "text": text,
            "parsed": parsed,
            "harness": harness,
            "error": None,
            "elapsed": round(time.time() - start, 2),
            "token_estimate": token_estimate,
            "cost_estimate": cost_estimate,
            "estimated_seconds": round(est_sec, 1),
        }

    @staticmethod
    def _cleanup_prompt_file(prompt_file: Path | None) -> None:
        if prompt_file and prompt_file.exists():
            try:
                prompt_file.unlink(missing_ok=True)
            except Exception:
                pass

    def _complete_error(
        self, error: str, harness: str, start: float,
        probe: dict | None = None, detail: str = "",
    ) -> dict:
        return {
            "success": False,
            "text": "",
            "parsed": None,
            "harness": harness,
            "error": error,
            "probe": probe,
            "detail": detail[:2000] if detail else "",
            "elapsed": round(time.time() - start, 2),
            "token_estimate": 0,
            "cost_estimate": 0.0,
            "estimated_seconds": 0.0,
        }

    def _parse_complete_log(
        self, log_path: Path, harness: str, result_schema: dict | None
    ) -> tuple[str, Any]:
        """Extract (text, parsed) from a soul-complete log.

        - omp: line-delimited JSON events → last assistant text → JSON block
        - claude: --output-format json → last JSON object; ``result`` field is
          the final message (string JSON when --json-schema was used)
        """
        if not log_path.exists():
            return "", None
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "", None

        text = ""
        if harness == "omp":
            # Strategy: line-delimited JSON events (agent_end/turn_end/message_end)
            for line in content.split("\n"):
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") in ("agent_end", "turn_end", "message_end"):
                    msg_data = event.get("message") or event.get("messages", [])
                    msg_list = [msg_data] if isinstance(msg_data, dict) else msg_data
                    assistant_msgs = [
                        m for m in msg_list
                        if isinstance(m, dict) and m.get("role") == "assistant"
                    ]
                    if assistant_msgs:
                        blocks = assistant_msgs[-1].get("content", [])
                        text = "\n".join(
                            b.get("text", "") for b in blocks if b.get("type") == "text"
                        )
                        if text.strip():
                            break
        else:  # claude
            # --output-format json: single JSON object with a "result" field
            candidates = []
            for line in content.split("\n"):
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    candidates.append(obj)
            if candidates:
                obj = candidates[-1]
                result = obj.get("result")
                if isinstance(result, str):
                    text = result
                elif isinstance(result, (dict, list)):
                    return "", result
                elif obj.get("type") == "error":
                    return "", None

        if not text.strip():
            # Fallback: brace-counted JSON block anywhere in the log
            block = self._extract_json_block(content)
            if block is not None:
                if isinstance(block, str):
                    text = block
                else:
                    return "", block
            if not text.strip():
                return "", None

        parsed = None
        if result_schema is not None or text.lstrip().startswith(("{", "[")):
            block = self._extract_json_block(text)
            if block is not None and not isinstance(block, str):
                parsed = block
        return text.strip(), parsed

    @staticmethod
    def _extract_json_block(text: str) -> Any | None:
        """Extract the first balanced JSON value (dict/list) from text.

        Handles ```json fences and trailing prose. Returns None when no valid
        JSON object/array is found.
        """
        search_text = text
        # 优先找 ```json 围栏块(即使有叙述前缀,如 "基于文档内容生成...")
        fence = re.search(r'```(?:json)?\s*\n?(.*?)```', search_text, re.DOTALL)
        if fence:
            raw = fence.group(1).strip()
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                # 宽松修复: 中文引号内嵌(如 "回应"更原创"这一发现")
                # 用状态机把字符串值内部未转义的 " 替换为 ' 后重试
                repaired = _repair_embedded_quotes(raw)
                if repaired is not None:
                    try:
                        return json.loads(repaired)
                    except (json.JSONDecodeError, TypeError):
                        pass

        if search_text.lstrip().startswith("```"):
            first_nl = search_text.find("\n")
            if first_nl > 0:
                search_text = search_text[first_nl + 1:]
        if search_text.rstrip().endswith("```"):
            search_text = search_text[:search_text.rfind("```")].rstrip()

        # Direct parse first
        try:
            return json.loads(search_text.strip())
        except (json.JSONDecodeError, TypeError):
            pass

        for start in re.finditer(r'[{\[]', search_text):
            s = start.start()
            depth = 0
            in_str = False
            escape = False
            for i in range(s, len(search_text)):
                ch = search_text[i]
                if in_str:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch in "{[":
                    depth += 1
                elif ch in "}]":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(search_text[s:i + 1])
                        except json.JSONDecodeError:
                            break
        return None

    # ── Heuristic Fallback ─────────────────────────────────────────────

    @staticmethod
    def _extract_structured_qa(question: str, answer: str, retrieved_docs: list) -> dict:
        """Structured extraction from a Q&A pair — no placeholder dumping.
        Returns None if the signal lacks actionable content (quality gate)."""
        import re as _re

        if not answer or len(answer.strip()) < 50:
            return None  # Quality gate: answer too short to be actionable

        # ── Extract key_lessons from list items or causal sentences ──
        lessons: list[str] = []
        # Bullet/numbered list items (strongest signal)
        list_items = _re.findall(r'(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+(.+?)(?=\n|$)', answer)
        for item in list_items[:5]:
            t = item.strip().rstrip('.')
            if len(t) >= 20:
                lessons.append(t)
        # Causal sentences (because/therefore/thus/so/导致/因此/从而)
        if len(lessons) < 2:
            causal = _re.findall(
                r'[^.\n]*(?:therefore|thus|hence|so that|导致|因此|从而|使得|说明)[^.\n]*[.]?',
                answer, _re.IGNORECASE,
            )
            for c in causal[:3]:
                t = c.strip()
                if len(t) >= 20 and t not in '; '.join(lessons):
                    lessons.append(t)
        # Fallback: first 2 sentences of the answer (>=30 chars each)
        if not lessons:
            sents = [s.strip() for s in _re.split(r'[.!?。！？]', answer) if len(s.strip()) >= 30]
            lessons = sents[:3]
        if not lessons:
            return None  # No extractable knowledge

        # ── Extract actionable solution sentences ──
        # Imperative/specific patterns: "use X", "set Y to Z", numbers, config keys
        action_words = (
            r'use|using|set|configure|install|run|apply|enable|disable|'
            r'使用|设置|配置|安装|运行|应用|启用|禁用|需要|建议|推荐'
        )
        action_sents = [
            s.strip() for s in _re.split(r'(?<=[.!?。！？])\s+', answer)
            if len(s.strip()) >= 25 and _re.search(action_words, s, _re.IGNORECASE)
        ]
        if not action_sents:
            # Take the longest sentence as the best-available solution
            all_sents = [s.strip() for s in _re.split(r'(?<=[.!?。！？])\s+', answer) if len(s.strip()) >= 25]
            action_sents = sorted(all_sents, key=len, reverse=True)[:2]
        if not action_sents:
            return None
        solution = ' '.join(action_sents[:3])

        # ── Extract domain tags from the question ──
        # Stopwords to filter
        _stop = {
            'the','a','an','is','are','how','to','what','why','when','where',
            'of','in','on','for','with','and','or','not','can','do','does',
            '的','了','是','在','和','与','如何','什么','为什么','怎么','吗','呢','吧',
        }
        # English words (2+ chars) + CJK runs
        tokens = _re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{1,}', question)  # 2+ char latin tokens
        cjk = _re.findall(r'[\u4e00-\u9fff]{2,}', question)
        candidates = [t.lower() for t in tokens if t.lower() not in _stop and len(t) >= 2] + cjk
        # Dedup + take top 4 by frequency proxy (longer = more specific)
        seen, tags = set(), []
        for t in sorted(candidates, key=len, reverse=True):
            k = t.lower()
            if k not in seen:
                seen.add(k)
                tags.append(t)
            if len(tags) >= 4:
                break
        if not tags:
            tags = ['auto-extracted']

        # ── Confidence based on structural richness ──
        score = 0.0
        score += min(0.2, len(lessons) / 5 * 0.2)            # up to 0.2 for lessons
        score += min(0.2, len(action_sents) / 3 * 0.2)       # up to 0.2 for actionable sents
        score += min(0.15, len(tags) / 4 * 0.15)             # up to 0.15 for tags
        score += min(0.15, min(len(answer), 2000) / 2000 * 0.15)  # up to 0.15 for length
        score += 0.2 if retrieved_docs else 0.0               # 0.2 if backed by docs
        score += 0.1 if list_items else 0.0                   # 0.1 bonus for structured lists
        confidence = round(min(0.75, score), 3)  # heuristic caps at 0.75 (LLM path can reach 1.0)

        # ── Title: question core (strip filler) ──
        title_core = question.strip().rstrip('?？.。!！')[:55]
        title = title_core if title_core else 'Auto-extracted experience'

        # ── Category heuristic ──
        q_lower = question.lower()
        if any(w in q_lower for w in ['error', 'fail', '报错', '失败', 'connect', 'crash', 'bug', '异常']):
            category = 'troubleshooting'
            severity = 'important'
        elif any(w in q_lower for w in ['optimize', 'best', 'tune', '优化', '最佳', '调优']):
            category = 'optimization'
            severity = 'normal'
        elif any(w in q_lower for w in ['how to', '怎么做', '如何', '步骤', '流程']):
            category = 'workflow'
            severity = 'normal'
        else:
            category = 'best_practice'
            severity = 'normal'

        return {
            'title': title,
            'problem': question.strip()[:500],
            'solution': solution[:1200],
            'key_lessons': lessons[:5],
            'tags': tags,
            'category': category,
            'severity': severity,
            'related_docs': [d.get('path', '') if isinstance(d, dict) else str(d)
                             for d in (retrieved_docs or [])][:3],
            'confidence': confidence,
            'extraction_method': 'heuristic-structured',
            'auto_extracted': True,
            'harness': 'heuristic',
            'vetted': False,
        }

    async def _heuristic_fallback(
        self, kb_path: str, kb_id: str, signals: list[dict],
        kb_config: dict, trigger: str,
    ) -> dict:
        """Structured heuristic extraction when the LLM agent is unavailable.
        Quality-gated: signals without actionable content are skipped, not placeholdered."""
        from app.services.meditation_db import create_run, finish_run
        from app.services.experience_service import experience_service

        run_id = create_run(kb_id, "heuristic", trigger)
        drafts = []
        skipped = []

        try:
            max_drafts = kb_config.get("max_drafts_per_run", 3)
            created = 0
            for sig in signals:
                if created >= max_drafts:
                    break
                question = sig.get("question_text", "")
                if not question or len(question) < 10:
                    continue
                answer = sig.get("assistant_answer", "")
                # Parse retrieved_docs JSON
                docs_raw = sig.get("retrieved_docs", "[]")
                try:
                    retrieved_docs = json.loads(docs_raw) if isinstance(docs_raw, str) else (docs_raw or [])
                except Exception:
                    retrieved_docs = []

                extracted = self._extract_structured_qa(question, answer, retrieved_docs)
                if not extracted:
                    skipped.append({
                        "question": question[:80],
                        "reason": "No actionable content (answer <50 chars or no extractable lessons)",
                    })
                    continue  # Quality gate: skip, don't placeholder

                extracted["scenario"] = f"heuristic-{created}"
                r = await experience_service.save_draft(kb_id, extracted)
                if r.get("success"):
                    drafts.append({
                        "title": extracted["title"],
                        "draft_id": r.get("draft_id"),
                        "confidence": extracted["confidence"],
                    })
                    created += 1

            finish_run(
                run_id,
                status="completed",
                drafts_created=len(drafts),
                signals_processed=len(signals),
                report_json=json.dumps({"drafts": drafts, "skipped": skipped}, ensure_ascii=False),
            )
            # Update KB meditation config with run stats
            try:
                from app.services.kb_meditation_config import update_meditation_config
                update_meditation_config(kb_id, {
                    "last_run_at": datetime.now(timezone.utc).isoformat(),
                    "last_run_status": "success",
                    "total_runs": kb_config.get("total_runs", 0) + 1,
                    "total_experiences_generated": kb_config.get("total_experiences_generated", 0) + len(drafts),
                })
            except Exception as e:
                logger.warning("Failed to update KB meditation config: %s", e)
            # Mark signals as derived
            try:
                from app.services.meditation_db import mark_signals_derived
                signal_ids = [s.get("id") for s in signals if s.get("id")]
                if signal_ids:
                    mark_signals_derived(signal_ids)
            except Exception as e:
                logger.warning("Failed to mark signals derived: %s", e)
            return {"success": True, "experiences": [], "drafts": drafts, "skipped": skipped,
                    "run_id": run_id, "harness": "heuristic",
                    "note": "Structured heuristic extraction (quality-gated)"}

        except Exception as e:
            logger.exception("Heuristic fallback failed")
            finish_run(run_id, status="failed", error=str(e))
            return {"success": False, "error": str(e), "run_id": run_id}


# Singleton
agent_harness = AgentHarnessManager()
