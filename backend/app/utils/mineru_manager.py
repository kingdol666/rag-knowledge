"""
MinerU API Manager -- manages mineru-api as a hidden, lifecycle-bound subprocess.
GPU is available: CUDA-capable PyTorch (torch 2.8.0+cu128) is installed,
so mineru-api runs with GPU acceleration via the hybrid-engine backend.

``start()`` spawns the venv's own ``mineru-api.exe`` directly with ``cwd`` set
runs directly from the shared backend venv (``backend/.venv/``), running::

    mineru-api --host {host} --port {port}

**Hidden + lifecycle-bound design (important).** The subprocess is launched with
``CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`` — so it runs **silently in the
background with no console window** — and its combined stdout/stderr is
redirected to ``{project}/logs/mineru-api.log`` (append, **never a ``PIPE``**).

The process is assigned to a Windows **Job Object** with
``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE``:

  * When the backend process exits — *for any reason*: graceful lifespan
    shutdown, Ctrl-C, an unhandled crash, or ``taskkill /F`` — the kernel
    closes the job handle and kills mineru-api (and its whole worker subtree).
    No orphaned mineru-api is ever left running in the background.
  * Writing OCR log lines to a file never blocks. (A closed/full pipe on
    Windows surfaces as ``[Errno 22] Invalid argument`` and fails the parse
    task — redirecting to a file eliminates that failure mode entirely, while
    the Job Object — not pipe ownership — carries the lifecycle guarantee.)

If mineru-api is already healthy on the port when ``start()`` is called (e.g.
reused from a prior session), it is best-effort *adopted* into the job so it
shares this backend's lifecycle too.

**Lazy auto-start.** ``ensure_running()`` / ``ensure_running_async()`` check
health and start mineru-api if it's down; ``parse_file`` and ``submit_task``
call them, so any MinerU API call auto-starts the engine when it isn't already
running. Concurrent callers serialize on a lock — only one spawns.

A background daemon thread tails the log file into the backend console
(prefixed ``[mineru-api]``) so live output stays visible; that tail is purely
cosmetic. ``stop()`` kills by port and closes the job (defensive — the job's
kill-on-close already covers the crash case).
"""
import asyncio
import atexit
import ctypes
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_MINERU_ENV_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _MINERU_ENV_DIR.parents[1] if _MINERU_ENV_DIR.name == 'utils' else _MINERU_ENV_DIR.parent  # now the sole venv lives at backend/.venv
# backend/logs/ — created on demand by start(). mineru-api's combined
# stdout/stderr is redirected here so it never depends on a parent-owned pipe.
_LOG_DIR = _BACKEND_DIR / "logs"
_MINERU_LOG = _LOG_DIR / "mineru-api.log"


def _run_silent_kwargs() -> dict:
    """Extra kwargs for ``subprocess.run`` so status/cleanup probes
    (``netstat`` / ``lsof`` / ``taskkill``) never flash a console window.

    Windows-only effect: ``CREATE_NO_WINDOW`` + a hidden ``STARTUPINFO``.
    POSIX returns ``{}`` (no console-window concern there).
    """
    if sys.platform != "win32":
        return {}
    flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flags |= subprocess.CREATE_NO_WINDOW
    si = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
    si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    si.wShowWindow = 0  # SW_HIDE
    return {"creationflags": flags, "startupinfo": si}


# ── Windows Job Object: bind mineru-api to THIS process so it dies the moment
#    the backend exits — graceful shutdown OR hard crash. With
#    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, when the last handle to the job
#    closes (i.e. this process dies for any reason), the kernel kills every
#    process in the job (mineru-api + its worker subtree). No orphans.
#    stdout still goes to a log file (never a pipe), so the historical
#    [Errno 22] pipe-closure crash does not recur.
if sys.platform == "win32":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _IO_COUNTERS(ctypes.Structure):
        # Must match the Windows IO_COUNTERS struct — 6 ULONG64 fields (48 B).
        # An undersized struct makes SetInformationJobObject fail with
        # ERROR_BAD_LENGTH (WinError 24).
        _fields_ = [
            (n, ctypes.c_ulonglong)
            for n in (
                "ReadOperationCount", "WriteOperationCount",
                "OtherOperationCount", "ReadTransferCount",
                "WriteTransferCount", "OtherTransferCount",
            )
        ]

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
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

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    _JobObjectExtendedLimitInformation = 9
    _PROCESS_SET_QUOTA = 0x0100
    _PROCESS_TERMINATE = 0x0001

    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
    ]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def _create_kill_on_close_job() -> int:
        """Create a Job Object whose members die when its handle is closed."""
        job = _kernel32.CreateJobObjectW(None, None)
        if not job:
            raise ctypes.WinError(ctypes.get_last_error())
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not _kernel32.SetInformationJobObject(
            job, _JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info),
        ):
            err = ctypes.get_last_error()
            _kernel32.CloseHandle(job)
            raise ctypes.WinError(err)
        return job  # type: ignore[return-value]

    def _assign_pid_to_job(job: int, pid: int) -> bool:
        """Best-effort: open ``pid`` and assign it to the kill-on-close job."""
        if not job:
            return False
        h = _kernel32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid)
        if not h:
            return False
        try:
            return bool(_kernel32.AssignProcessToJobObject(job, h))
        finally:
            _kernel32.CloseHandle(h)

    def _close_job_handle(job: Optional[int]) -> None:
        if job:
            _kernel32.CloseHandle(job)

    def _linux_set_pdeathsig() -> None:
        """preexec_fn stub (Windows): no-op, always defined for import-safety.
        Real implementation lives in the non-Windows branch."""
        return

else:  # non-Windows fallbacks (project is Windows-targeted, but stay import-safe)
    def _create_kill_on_close_job() -> int:
        return 0

    def _assign_pid_to_job(job: int, pid: int) -> bool:
        return False

    def _close_job_handle(job: Optional[int]) -> None:
        return None

    def _linux_set_pdeathsig() -> None:
        """preexec_fn: fork 后 exec 前调 prctl，让内核在父进程死亡（含 SIGKILL/OOM）时给子进程发 SIGKILL。
        Linux-only；macOS 不支持 PR_SET_PDEATHSIG，直接 return（退回进程组+atexit）。"""
        if sys.platform != "linux":
            return
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6", use_last_error=True)
            PR_SET_PDEATHSIG = 1
            libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0)
        except Exception:
            pass  # 最佳努力，失败退回进程组清理


class MineruApiManager:
    """Manages the mineru-api lifecycle, launching it as a subprocess."""

    def __init__(self, host: str = "127.0.0.1", port: Optional[int] = None):
        """``port=None`` (default) → pick a free ephemeral port at start time
        (avoids common dev/service ports). A fixed ``port`` is used as-is.
        """
        self.host = host
        self._requested_port = port  # None = auto-pick on start()
        self.port: Optional[int] = port  # the REAL port mineru-api runs on
        self._process: Optional[subprocess.Popen] = None
        # Windows Job Object handle — mineru-api is assigned to this so it is
        # killed by the kernel when this process dies. Created lazily in start().
        self._job_handle: Optional[int] = None
        # Serializes concurrent ensure_running()/start() calls so that N
        # parallel API requests only spawn mineru-api once.
        self._spawn_lock = threading.Lock()
        self._atexit_registered = False

    @property
    def _base_url(self) -> str:
        """The mineru-api base URL — **always derived from the actual
        ``self.port``**, so it can never drift from the port mineru-api is
        really running on. Empty until ``start()`` has resolved a port."""
        if self.port is None:
            return ""
        return f"http://{self.host}:{self.port}"

    def _ensure_atexit(self) -> None:
        """Register stop() to run on interpreter exit (Unix graceful cleanup;
        on Windows the Job Object already covers crashes — this is extra)."""
        if not self._atexit_registered:
            atexit.register(self.stop)
            self._atexit_registered = True

    @property
    def api_url(self) -> str:
        return self._base_url

    @property
    def is_running(self) -> bool:
        """True when the mineru-api health endpoint responds."""
        return self._health_ok()

    # -- internal helpers ------------------------------------------------

    def _health_ok(self) -> bool:
        if not self._base_url:
            return False
        try:
            resp = httpx.get(f"{self._base_url}/health", timeout=2.0, trust_env=False)
            return resp.status_code == 200
        except Exception:
            return False

    # Ports we refuse to land on even if the OS momentarily offers them, so
    # MinerU never collides with common dev tools / DBs / this project's own
    # backend (8765) / the legacy fixed MinerU port (8764).
    _AVOID_PORTS = frozenset({
        22, 80, 443,                        # system
        3000, 3306, 4200, 5173, 5432,       # web frontends / dbs
        5678, 6379, 6789, 7860,             # debuggers / redis / gradio
        8000, 8001, 8080, 8443, 8764, 8765, # backends / legacy mineru / this backend
        8888, 9000, 9090, 9200,             # misc services
    })

    def _pick_free_port(self) -> int:
        """Return a free TCP port on ``self.host``, avoiding common/dev ports.

        Asks the OS for an ephemeral port (``bind((host, 0))``) and rejects any
        that fall in :data:`_AVOID_PORTS`. There is an inherent TOCTOU window
        between the probe socket closing and mineru-api binding; ``start()``
        retries on a fresh port if mineru-api fails to come up.
        """
        last: Optional[int] = None
        for _ in range(64):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind((self.host, 0))
                last = sock.getsockname()[1]
            finally:
                sock.close()
            if last not in self._AVOID_PORTS:
                return last
        if last is None:
            raise RuntimeError("Could not allocate a free port for mineru-api")
        return last

    def _exe_path(self) -> Path:
        """Resolve the venv's ``mineru-api`` executable — now shared with
        the backend at ``backend/.venv/`` (not the old mineru_module/.venv)."""
        venv = _BACKEND_DIR / ".venv"
        if sys.platform == "win32":
            return venv / "Scripts" / "mineru-api.exe"
        return venv / "bin" / "mineru-api"

    def _find_pid_on_port(self) -> Optional[str]:
        """Return the PID listening on ``self.port`` (string), or ``None``.
        Cross-platform: ``netstat -ano`` on Windows, ``lsof -ti`` on Unix.
        """
        if self.port is None:
            return None
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["netstat", "-ano"], capture_output=True, text=True, timeout=10,
                    **_run_silent_kwargs(),
                )
                for line in result.stdout.splitlines():
                    if f":{self.port}" in line and "LISTENING" in line.upper():
                        pid = line.split()[-1]
                        if pid and pid != "0":
                            return pid
            else:
                result = subprocess.run(
                    ["lsof", "-ti", f":{self.port}"],
                    capture_output=True, text=True, timeout=10,
                )
                pids = [p for p in result.stdout.split() if p]
                if pids:
                    return pids[0]
        except Exception:
            logger.debug("Could not resolve PID on port %s", self.port, exc_info=True)
        return None

    def _adopt_running_into_job(self) -> None:
        """Best-effort: bind an *already-running* mineru-api into our job so
        it shares the backend's lifecycle. Used when ``start()`` finds a
        healthy mineru-api it did not spawn itself (e.g. reused from a prior
        session). Silently skips on any failure.
        """
        if not self._job_handle:
            try:
                self._job_handle = _create_kill_on_close_job()
            except Exception:
                logger.exception("Could not create lifecycle job (non-fatal)")
                return
        pid_str = self._find_pid_on_port()
        if not pid_str:
            return
        try:
            pid = int(pid_str)
        except ValueError:
            return
        if _assign_pid_to_job(self._job_handle, pid):
            logger.info(
                "Adopted running mineru-api (pid %s) into the lifecycle job", pid
            )

    # -- public API ------------------------------------------------------

    def start(self, timeout: float = 30.0) -> bool:
        """Launch ``mineru-api`` as a **hidden, lifecycle-bound** background
        subprocess and wait for it to be healthy. Cross-platform (Win/Linux/macOS).

        * **Port**: if ``port`` was not given (default), a free ephemeral port
          is picked at runtime, avoiding common dev/service ports. ``start()``
          retries on a few distinct ports to dodge the ephemeral-port TOCTOU race.
        * **Hidden window**: ``CREATE_NO_WINDOW`` on Windows; ``start_new_session``
          (new session, no controlling tty) on Unix — no console window anywhere.
        * **Lifecycle**: Windows binds the child to a ``KILL_ON_JOB_CLOSE`` Job
          Object (kernel kills it when this process dies — graceful or crash).
          Unix kills the child's process group via :meth:`stop` and ``atexit``.
        * stdout/stderr → ``backend/logs/mineru-api.log`` (append), **never a
          PIPE** — avoids the historical ``[Errno 22]`` parse failures.

        If mineru-api is already healthy on the resolved port, it is reused.
        """
        # Reuse an already-healthy instance (prior session / manual launch).
        if self._health_ok():
            logger.info("mineru-api is already running on %s", self._base_url)
            if sys.platform == "win32":
                self._adopt_running_into_job()
            self._ensure_atexit()
            return True

        mineru_api_exe = self._exe_path()
        if not mineru_api_exe.exists():
            logger.error("mineru-api executable not found: %s", mineru_api_exe)
            return False

        env = os.environ.copy()
        # GPU acceleration enabled (CUDA-capable torch 2.8.0+cu128 installed)
        # pipeline backend — stable, high quality, leverages GPU where available
        env["MINERU_DEFAULT_BACKEND"] = "pipeline"
        try:
            from app.config import config as _cfg
            _default_source = _cfg.mineru.get("model_source", "modelscope")
        except Exception:
            _default_source = "modelscope"
        env.setdefault("MINERU_MODEL_SOURCE", _default_source)

        # In auto-port mode, try a few distinct free ports — ephemeral ports
        # carry a small TOCTOU race between our probe socket and mineru-api
        # binding, so retry if it loses the race. With a fixed port, one shot.
        max_attempts = 3 if self._requested_port is None else 1
        for attempt in range(1, max_attempts + 1):
            if self._requested_port is None:
                self.port = self._pick_free_port()
            if self._spawn_and_wait(mineru_api_exe, env, timeout):
                self._ensure_atexit()
                return True
            if self._requested_port is not None:
                break
            self._process = None
            if attempt < max_attempts:
                logger.warning(
                    "mineru-api start attempt %d/%d failed; trying another port",
                    attempt, max_attempts,
                )
        return False

    def _spawn_and_wait(self, exe: Path, env: dict[str, str], timeout: float) -> bool:
        """Spawn mineru-api on ``self.port`` and poll ``/health`` until ready."""
        cmd = [str(exe), "--host", self.host, "--port", str(self.port)]
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_handle = open(_MINERU_LOG, "ab", buffering=0)

        logger.info(
            "Starting mineru-api (hidden background): cwd=%s cmd=%s log=%s",
            _MINERU_ENV_DIR, cmd, _MINERU_LOG,
        )

        popen_kwargs: dict[str, Any] = dict(
            cwd=str(_MINERU_ENV_DIR),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            close_fds=True,
        )
        if sys.platform == "win32":
            # CREATE_NO_WINDOW: console app, no visible window. The new process
            # group isolates Ctrl-C; the Job Object carries lifecycle instead.
            creationflags = 0
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags |= subprocess.CREATE_NO_WINDOW
            popen_kwargs["creationflags"] = creationflags
        else:
            # New session → child leads its own process group with no controlling
            # tty, so no window opens and we can kill the whole group via killpg.
            popen_kwargs["start_new_session"] = True
            if sys.platform == "linux":
                popen_kwargs["preexec_fn"] = _linux_set_pdeathsig

        try:
            self._process = subprocess.Popen(cmd, **popen_kwargs)
        finally:
            # File handle is dup'd into the child; drop our reference.
            log_handle.close()

        # Windows: bind the freshly-spawned process to a kill-on-close Job Object.
        if sys.platform == "win32":
            try:
                if self._job_handle is None:
                    self._job_handle = _create_kill_on_close_job()
                if not _assign_pid_to_job(self._job_handle, self._process.pid):
                    logger.warning(
                        "Could not bind mineru-api (pid %s) to the lifecycle job — "
                        "it may survive a hard backend crash (non-fatal).",
                        self._process.pid,
                    )
            except Exception:
                logger.exception("Job-object lifecycle binding failed (non-fatal)")

        self._start_log_tailer(_MINERU_LOG)

        deadline = time.monotonic() + timeout
        last_err = ""
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                logger.error(
                    "mineru-api exited early (code %s) on port %s",
                    self._process.returncode, self.port,
                )
                self._process = None
                return False
            try:
                resp = httpx.get(f"{self._base_url}/health", timeout=3.0, trust_env=False)
                if resp.status_code == 200:
                    logger.info(
                        "mineru-api ready on %s (pid %s, port %s)",
                        self._base_url, self._process.pid, self.port,
                    )
                    return True
            except Exception as exc:
                last_err = str(exc)
                time.sleep(1)

        logger.error(
            "mineru-api failed to start on port %s within %.0fs: %s",
            self.port, timeout, last_err,
        )
        self.stop()
        return False

    @staticmethod
    def _start_log_tailer(log_path: Path) -> None:
        """Spawn a daemon thread that tails ``log_path`` into this process's
        logger, line by line, prefixed ``[mineru-api]``.

        This replaces the old stdout-pipe forwarder. Because mineru-api now
        writes to a log *file* (not a parent-owned pipe), this tailer is purely
        cosmetic — mineru-api's stability no longer depends on anyone reading
        its output. The thread exits when it reaches end-of-file AND the
        manager process is shutting down (best-effort: it re-checks the file
        size periodically until then).
        """
        import threading

        def _pump() -> None:
            prefix = "mineru-api"
            try:
                # Wait briefly for the file to appear / be flushed.
                for _ in range(50):
                    if log_path.exists() and log_path.stat().st_size > 0:
                        break
                    time.sleep(0.1)
                with open(log_path, "rb") as fh:
                    fh.seek(0, os.SEEK_END)
                    idle = 0
                    while idle < 30:  # stop after ~30s of no new output
                        pos = fh.tell()
                        line = fh.readline()
                        if not line:
                            # Nothing new; check if file truncated/rotated.
                            try:
                                if log_path.stat().st_size < pos:
                                    fh.seek(0)
                            except OSError:
                                pass
                            time.sleep(1.0)
                            idle += 1
                            continue
                        idle = 0
                        text = line.decode("utf-8", errors="replace").rstrip("\r\n")
                        if text:
                            logger.info("[%s] %s", prefix, text)
            except Exception:
                # Tailer must never break mineru-api.
                pass

        thread = threading.Thread(
            target=_pump,
            name="mineru-api-log-tailer",
            daemon=True,
        )
        thread.start()

    def ensure_running(self, timeout: float = 60.0) -> bool:
        """Start mineru-api if it isn't healthy right now. Thread-safe —
        concurrent callers serialize on ``_spawn_lock`` and only one actually
        spawns; the rest see it come up and return ``True``.

        Use this from sync call sites (e.g. ``parse_file``) so that "call the
        MinerU API → auto-start if it's down" just works.
        """
        if self._health_ok():
            return True
        with self._spawn_lock:
            # start() re-checks health at the top, so a concurrent starter that
            # already brought it up makes this a fast no-op.
            return self.start(timeout=timeout)

    async def ensure_running_async(self, timeout: float = 60.0) -> bool:
        """Async-safe variant of :meth:`ensure_running`. Runs the (potentially
        long, model-loading) startup in a worker thread so the event loop is
        never blocked while mineru-api boots.
        """
        if self._health_ok():
            return True
        return await asyncio.to_thread(self.ensure_running, timeout)

    def stop(self) -> None:
        """Kill the mineru-api subprocess tree and release lifecycle resources.

        Cross-platform: on Windows, ``taskkill /T /F`` the tracked PID (whole
        tree) and close the kill-on-close Job; on Unix, ``SIGTERM`` then
        ``SIGKILL`` the child's process group. Idempotent — safe to call when
        nothing is running. Called from the FastAPI lifespan on graceful
        shutdown and registered via ``atexit``; Windows additionally relies on
        the Job Object for the hard-crash case.
        """
        proc = self._process
        self._process = None
        if proc is not None and proc.poll() is None:
            self._terminate(proc)
            logger.info("Stopped mineru-api (pid %s) on port %s", proc.pid, self.port)

        # Windows: closing the job handle kills anything still in it (defensive
        # — the taskkill/SIGKILL above already handled the main pid) and frees
        # the kernel object so the next start() creates a fresh job.
        if sys.platform == "win32":
            _close_job_handle(self._job_handle)
            self._job_handle = None

    def _terminate(self, proc: "subprocess.Popen") -> None:
        """Terminate the spawned process tree, cross-platform."""
        pid = proc.pid
        try:
            if sys.platform == "win32":
                # /T = kill the whole tree (mineru-api may spawn workers).
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, timeout=10,
                    **_run_silent_kwargs(),
                )
            else:
                pgid = os.getpgid(pid)  # == pid because of start_new_session
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    return
                # Grace period, then force-kill the group.
                for _ in range(20):
                    if proc.poll() is not None:
                        return
                    time.sleep(0.1)
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except Exception:
            logger.exception("Failed to terminate mineru-api pid %s (non-fatal)", pid)

    def restart(self, timeout: float = 60.0) -> bool:
        """Stop mineru-api and start it again. In auto-port mode it lands on a
        **fresh** free port (the old one may be in TIME_WAIT); the new port is
        then used for all API calls via :attr:`api_url` / :attr:`port`.

        Returns ``True`` if mineru-api came back up healthy.
        """
        with self._spawn_lock:
            self.stop()
            # Force a fresh port pick in auto mode so the restart isn't wedged
            # by a port still in TIME_WAIT after the previous instance died.
            if self._requested_port is None:
                self.port = None
            return self.start(timeout=timeout)

        # Closing the job handle kills anything still in it (defensive — the
        # taskkill above already handled the main pid). It also frees the
        # kernel object so the next start() creates a fresh job.
        _close_job_handle(self._job_handle)
        self._job_handle = None

    def health(self) -> dict:
        try:
            resp = httpx.get(f"{self._base_url}/health", timeout=5.0, trust_env=False)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": str(exc)}

    def parse_file(self, file_path: str, return_md: bool = True) -> dict:
        """Upload file to mineru-api /file_parse (synchronous, legacy)."""
        self.ensure_running()
        url = f"{self._base_url}/file_parse"
        with open(file_path, "rb") as f:
            files = {"files": (Path(file_path).name, f)}
            data = {"return_md": "true" if return_md else "false"}
            resp = httpx.post(url, files=files, data=data, timeout=300.0, trust_env=False)
        resp.raise_for_status()
        return resp.json()

    # -- Async task API (push task + poll for result) --------------------
    # Mirrors mineru-api's FastAPI surface:
    #   POST /tasks            -> 202 {task_id, status_url, result_url, ...}
    #   GET  /tasks/{id}       -> {task_id, status, ...}
    #   GET  /tasks/{id}/result -> 200 {results: {name: {md_content, images}}}
    # Terminal states: {"completed", "failed"}.

    async def submit_task(
        self,
        file_path: str,
        *,
        backend: str = "pipeline",
        parse_method: str = "auto",
        return_md: bool = True,
        return_images: bool = True,
        formula_enable: bool = True,
        table_enable: bool = True,
        lang_list: Optional[list[str]] = None,
        start_page_id: int = 0,
        end_page_id: int = 99999,
    ) -> dict[str, Any]:
        """
        Push a file to ``POST /tasks`` and return the submission payload.

        The payload always includes ``task_id``, ``status_url`` and
        ``result_url`` (absolute URLs built by mineru-api).
        """
        await self.ensure_running_async()
        logger.info("Submitting file %s to mineru-api url %s", file_path, self._base_url)
        url = f"{self._base_url}/tasks"
        data = {
            "backend": backend,
            "parse_method": parse_method,
            "return_md": "true" if return_md else "false",
            "return_images": "true" if return_images else "false",
            "return_middle_json": "false",
            "return_model_output": "false",
            "return_content_list": "false",
            "return_original_file": "false",
            "response_format_zip": "false",
            "formula_enable": "true" if formula_enable else "false",
            "table_enable": "true" if table_enable else "false",
            "start_page_id": str(start_page_id),
            "end_page_id": str(end_page_id),
        }
        if lang_list:
            for lang in lang_list:
                data.setdefault("lang_list", []).append(lang)

        name = Path(file_path).name
        with open(file_path, "rb") as f:
            files = {"files": (name, f)}
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                resp = await client.post(url, data=data, files=files)
        resp.raise_for_status()
        return resp.json()

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Fetch the current status of a task via ``GET /tasks/{task_id}``."""
        url = f"{self._base_url}/tasks/{task_id}"
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def get_task_result(self, task_id: str) -> dict[str, Any]:
        """
        Fetch the final result of a completed task.

        Returns the raw mineru-api payload, e.g.::

            {"results": {pdf_name: {"md_content": "...",
                                    "images": {name: "data:...;base64,..."}}}}
        """
        url = f"{self._base_url}/tasks/{task_id}/result"
        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def wait_for_task(
        self,
        task_id: str,
        *,
        poll_interval: float = 2.0,
        timeout: float = 1800.0,
    ) -> dict[str, Any]:
        """
        Poll ``GET /tasks/{task_id}`` until the task reaches a terminal state.

        On ``completed`` returns the *result* payload (via ``/result``).
        On ``failed`` raises :class:`RuntimeError` with the server error.
        Raises :class:`asyncio.TimeoutError` if it does not finish in *timeout*.
        """
        deadline = asyncio.get_event_loop().time() + timeout
        last_status: dict[str, Any] = {}

        while asyncio.get_event_loop().time() < deadline:
            last_status = await self.get_task_status(task_id)
            status = last_status.get("status", "")
            if status == "completed":
                return await self.get_task_result(task_id)
            if status == "failed":
                err = last_status.get("error") or "MinerU task failed"
                raise RuntimeError(f"MinerU task {task_id} failed: {err}")
            await asyncio.sleep(poll_interval)

        raise asyncio.TimeoutError(
            f"MinerU task {task_id} did not finish within {timeout:.0f}s "
            f"(last status: {last_status.get('status', 'unknown')})"
        )


# Global instance (auto-port mode: picks a free ephemeral port on start)
mineru_manager = MineruApiManager()
