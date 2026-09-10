"""Harness Runner — 统一一次性回合作业执行通道（进程治理 + 错误即事件）。

职责与 agent_harness_manager 解耦：
- 所有引擎（mock/omp/claude/codex/dsh/gemini/copilot/cursor/crush/goose/qwen/pi/hermes/
  opencode）经 harness_specs.OneShotEngineSpec 驱动同一个 run_engine()；
- 进程治理: Windows Job Object KILL_ON_JOB_CLOSE + taskkill /T /F；POSIX 进程组；
  stdout/stderr → 独立 .out/.err 文件（绝不 PIPE，防大输出死锁）；
- 路径纪律: 日志文件名经清洗后锚定在 log_dir 内（resolve 后校验父目录防逃逸）；
  临时 prompt 文件用 mkstemp 独占创建（无 TOCTOU）；
- 调用约定: run_engine() 返回结构化结果，失败路径一律 error+detail（stderr 尾部优先）。
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
from app.services import harness_registry as hreg
from app.services import harness_specs as hspec


def safe_log_path(log_dir: Path, run_label: str, ext: str) -> Path:
    """日志路径安全构造：run_label 清洗为 [\\w-] 后锚定在 log_dir 内（防路径逃逸）。"""
    safe_label = re.sub(r"[^\w\-]", "", run_label)[:120] or "run"
    path = (log_dir / f"{safe_label}{ext}").resolve()
    if path.parent != log_dir.resolve():
        raise ValueError(f"log path escaped log dir: {path}")
    return path


def secure_tempfile(prefix: str, suffix: str = ".txt") -> Path:
    """安全临时文件（mkstemp 独占创建，无 TOCTOU 竞争）。"""
    fd, name = tempfile.mkstemp(prefix=re.sub(r"[^\w\-]", "", prefix)[:60], suffix=suffix)
    os.close(fd)
    return Path(name)


def read_log_tail(log_path: Path, n: int = 800) -> str:
    if not log_path.exists():
        return ""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        return content[-n:] if len(content) > n else content
    except Exception:
        return ""


def engine_tail(engine: dict, n: int = 800) -> str:
    """失败详情：stderr 优先、stdout 兜底的尾部（错误消息附 stderr 尾部）。"""
    parts = []
    for key in ("err_path", "out_path"):
        p = engine.get(key)
        if p:
            tail = read_log_tail(Path(p), n=n)
            if tail.strip():
                parts.append(f"--- {Path(p).name} ---\n{tail}")
    return "\n".join(parts)


# ── Windows Job Object（父进程退出收割子树，沿用 MinerU 模式） ─────────

def _create_kill_on_close_job() -> Any:
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
            ctypes.byref(info), ctypes.sizeof(info),
        ):
            logger.warning("SetInformationJobObject failed: %s", ctypes.get_last_error())
            kernel32.CloseHandle(hjob)
            return None
        return hjob
    except Exception:
        logger.warning("Failed to create Job Object (non-fatal)", exc_info=True)
        return None


def _assign_pid_to_job(job_handle: Any, pid: int) -> None:
    if sys.platform != "win32" or job_handle is None:
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
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


_JOB_HANDLE = _create_kill_on_close_job()
atexit.register(lambda: None)


def _terminate_process(proc: subprocess.Popen) -> None:
    """Cross-platform process + subtree kill."""
    if proc.poll() is not None:
        return
    pid = proc.pid
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            import signal
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(5)
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except Exception:
        logger.warning("Failed to terminate process %s", pid, exc_info=True)


async def _watch_process(proc: subprocess.Popen, timeout_sec: int) -> None:
    """Wait for process exit with hard timeout（超时由调用方收割）。"""

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
        _terminate_process(proc)


# ── 统一作业通道 ──────────────────────────────────────────────────────

async def run_engine(harness: str, prompt: str, cfg: dict, run_label: str,
                     log_dir: Optional[Path] = None) -> dict:
    """所有引擎共用的一次性回合作业执行通道（单一契约）。

    返回 {success, text, parsed, usage, exit_code, error, detail,
          out_path, err_path, elapsed}。错误即事件，绝不静默。
    """
    start = time.time()
    log_dir = log_dir or Path(PROJECT_ROOT.parent) / "backend" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    spec = hspec.get_spec(harness)
    timeout = int(cfg.get("timeout_sec", spec.timeout_default))

    _AUTH_KEYWORDS = ("auth", "api key", "apikey", "api_key", "login", "unauthorized",
                      "token", "credential", "sign in", "not found.*key", "401", "forbidden")

    def _fail(error: str, detail: str = "", exit_code: int | None = None,
              code: str | None = None, hint: str = "") -> dict:
        # 错误即事件：失败附带机器可读 error_code，凭据类失败附可读 hint
        error_code = code
        if error_code is None:
            if error == "timeout":
                error_code = "HARNESS_TIMEOUT"
            elif error.startswith("executable not found"):
                error_code = "HARNESS_NOT_INSTALLED"
            elif error.startswith("prompt_limit"):
                error_code = "HARNESS_PROMPT_TOO_LONG"
            elif error.startswith("cmd_build") or error.startswith("spawn"):
                error_code = "HARNESS_SPAWN_FAILED"
            elif error == "parse_failed" or error.startswith("acp_parse"):
                error_code = "HARNESS_NO_OUTPUT"
            elif error.startswith("exit_"):
                error_code = "HARNESS_EXIT_NONZERO"
                detail_full = detail or ""
                if any(k in detail_full.lower() for k in _AUTH_KEYWORDS):
                    error_code = "HARNESS_AUTH_OR_CONFIG"
            else:
                error_code = "HARNESS_ENGINE_FAILED"
        if not hint and error_code == "HARNESS_AUTH_OR_CONFIG":
            hint = ("Engine reported an authentication/configuration problem. "
                    "Set its required env vars (GET /api/v1/meditation/harnesses → "
                    "requires_env) or complete the engine's own login, then retry.")
        return {"success": False, "text": "", "parsed": None, "usage": None,
                "exit_code": exit_code, "error": error, "error_code": error_code,
                "hint": hint, "detail": (detail or "")[:2000],
                "out_path": None, "err_path": None,
                "elapsed": round(time.time() - start, 2)}

    # ── 进程内引擎（mock）──
    if spec.delivery == "inprocess":
        text = hspec.mock_respond(prompt, cfg.get("result_schema"))
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
        return {"success": True, "text": text, "parsed": parsed, "usage": None,
                "exit_code": 0, "error": None, "error_code": None, "hint": "",
                "detail": "inprocess",
                "out_path": None, "err_path": None,
                "elapsed": round(time.time() - start, 2)}

    # ── 协议内嵌引擎（dsh/hermes 的 ACP 单回合会话）──
    if spec.delivery == "embedded":
        err_log = safe_log_path(log_dir, run_label, ".err")
        try:
            with err_log.open("w", encoding="utf-8") as err_fp:
                state = await hspec.run_acp_oneshot(harness, cfg, prompt, stderr_fp=err_fp)
        except FileNotFoundError:
            return _fail(f"executable not found: {hreg.harness_command_name(harness)}")
        except Exception as e:
            return _fail(f"acp_spawn: {e}")
        text = (state.get("text") or "").strip()
        if state.get("error") and not text:
            return _fail(str(state["error"]), read_log_tail(err_log))
        if not text:
            return _fail("acp_parse_failed", read_log_tail(err_log))
        return {"success": True, "text": text, "parsed": None, "usage": None,
                "exit_code": 0, "error": None, "error_code": None, "hint": "",
                "detail": (f"stopReason={state.get('stop_reason', '')} "
                           f"unknown_events={state.get('unknown_events', 0)}"),
                "out_path": None, "err_path": err_log,
                "elapsed": round(time.time() - start, 2)}

    # ── CLI 一次性引擎（stdin / arg / argfile）──
    detail_note = ""
    if spec.delivery != "inprocess":
        resolved = hreg.resolve_command(harness) or ""
        # cmd shim 包装链拒绝引号参数 → 引擎经 .cmd/.bat 拉起时丢弃 --json-schema
        # （prompt 已内嵌输出格式模板，runner 从回复文本提取 JSON —— 显式降级，不静默）
        if resolved.lower().endswith((".cmd", ".bat")) and cfg.get("result_schema"):
            cfg = {**cfg, "result_schema": None}
            detail_note = ("cmd-shim engine: --json-schema dropped "
                           "(point harness.commands.<id> at a native bin to enable)")

    prompt_file: Path | None = None
    if spec.delivery == "argfile":
        prompt_file = secure_tempfile(prefix=f"{run_label}-prompt")
        prompt_file.write_text(prompt, encoding="utf-8")

    try:
        argv = hspec.build_engine_argv(harness, cfg, prompt, prompt_file)
    except ValueError as e:
        # 长度护栏：显式报错而非截断
        _cleanup_prompt_file(prompt_file)
        return _fail(f"prompt_limit: {e}")
    except Exception as e:
        _cleanup_prompt_file(prompt_file)
        return _fail(f"cmd_build: {e}")

    out_log = safe_log_path(log_dir, run_label, ".out")
    err_log = safe_log_path(log_dir, run_label, ".err")
    try:
        out_fp = out_log.open("w", encoding="utf-8")
        err_fp = err_log.open("w", encoding="utf-8")
    except Exception as e:
        _cleanup_prompt_file(prompt_file)
        return _fail(f"log_open: {e}")

    logger.info("[Engine:%s] label=%s argv0=%s", harness, run_label, argv[0])

    stdin_flag = subprocess.PIPE if spec.delivery == "stdin" else subprocess.DEVNULL
    try:
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            proc = subprocess.Popen(
                argv, cwd=str(PROJECT_ROOT.parent),
                stdin=stdin_flag, stdout=out_fp, stderr=err_fp,
                env={**hspec.engine_env_for(harness, cfg),
                     "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
                close_fds=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                startupinfo=si,
            )
        else:
            proc = subprocess.Popen(
                argv, cwd=str(PROJECT_ROOT.parent),
                stdin=stdin_flag, stdout=out_fp, stderr=err_fp,
                env={**hspec.engine_env_for(harness, cfg),
                     "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
                close_fds=True, start_new_session=True,
            )
    except FileNotFoundError:
        out_fp.close()
        err_fp.close()
        _cleanup_prompt_file(prompt_file)
        return _fail(f"executable not found: {argv[0]}")
    except Exception as e:
        out_fp.close()
        err_fp.close()
        _cleanup_prompt_file(prompt_file)
        return _fail(f"spawn: {e}")

    # Job Object：父进程退出时收割子树
    _assign_pid_to_job(_JOB_HANDLE, proc.pid)

    if spec.delivery == "stdin" and proc.stdin:
        try:
            proc.stdin.write(prompt.encode("utf-8"))
            proc.stdin.close()
        except Exception:
            pass

    try:
        await _watch_process(proc, timeout)
    except Exception as e:
        logger.warning("Process watch error: %s", e)

    _cleanup_prompt_file(prompt_file)
    out_fp.close()
    err_fp.close()
    exit_code = proc.poll()

    if exit_code is None:
        _terminate_process(proc)
        return _fail("timeout", engine_tail({"err_path": err_log, "out_path": out_log}))

    try:
        content = out_log.read_text(encoding="utf-8", errors="replace")
    except Exception:
        content = ""
    text, usage = spec.parse_output(content)

    if not text.strip():
        detail = engine_tail({"err_path": err_log, "out_path": out_log})
        return _fail("parse_failed" if exit_code == 0 else f"exit_{exit_code}",
                     detail, exit_code=exit_code)

    return {"success": True, "text": text, "parsed": None, "usage": usage,
            "exit_code": exit_code, "error": None, "error_code": None, "hint": "",
            "detail": detail_note,
            "out_path": out_log, "err_path": err_log,
            "elapsed": round(time.time() - start, 2)}


def _cleanup_prompt_file(prompt_file: Path | None) -> None:
    if prompt_file and prompt_file.exists():
        try:
            prompt_file.unlink(missing_ok=True)
        except Exception:
            pass


def _repair_embedded_quotes(raw: str) -> str | None:
    """宽松修复 JSON: 字符串值内未转义的成对英文引号替换为中文引号（LLM 输出常见毛病）。"""
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
                j = i + 1
                while j < n and raw[j] in " \t\n\r":
                    j += 1
                nxt = raw[j] if j < n else ""
                if nxt in ",}]:" or nxt == "":
                    out.append(ch)
                    in_str = False
                else:
                    k = j
                    while k < n:
                        if raw[k] == "\\":
                            k += 2
                            continue
                        if raw[k] == '"':
                            break
                        k += 1
                    if k < n:
                        out.append("\u201c")
                        out.append(raw[j:k])
                        out.append("\u201d")
                        i = k
                        changed = True
                    else:
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


def extract_json_block(text: str) -> Any | None:
    """提取首个平衡 JSON 值（dict/list）。处理 ```json 围栏与尾部叙述。

    优先围栏块；内嵌引号导致解析失败时宽松修复重试；未知形态返回 None。
    """
    search_text = text
    fence = re.search(r'```(?:json)?\s*\n?(.*?)```', search_text, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
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


def meditation_result_from_text(text: str) -> dict:
    """从引擎最终回复文本提取 meditation_result JSON（标准化结果）。"""
    if not text.strip():
        return {"success": False, "error": "empty_response"}
    mr = _find_meditation_result(text)
    if isinstance(mr, dict):
        return build_result(mr)
    return {"success": False, "error": "parse_failed", "log_tail": text[-500:]}


def _find_meditation_result(text: str) -> Optional[dict]:
    """提取 meditation_result：直接 JSON 块 / 围栏块 / 平衡括号扫描。"""
    block = extract_json_block(text)
    if isinstance(block, dict):
        mr = block.get("meditation_result")
        if isinstance(mr, dict):
            return mr
        if "experiences_created" in block or "drafts_created" in block:
            return block
    return None


def build_result(mr: dict) -> dict:
    """meditation_result → 标准化结果 dict。"""
    return {
        "success": True,
        "kb_id": mr.get("kb_id", ""),
        "experiences": mr.get("experiences_created", []),
        "drafts": mr.get("drafts_created", []),
        "skipped": mr.get("skipped", []),
        "total_signals_processed": mr.get("total_signals_processed", 0),
        "summary": mr.get("summary", ""),
    }
