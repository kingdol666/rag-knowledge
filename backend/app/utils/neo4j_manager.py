"""
Neo4j Local Manager — Docker-free Neo4j lifecycle for the RAG platform.

Design mirrors ``mineru_manager.py`` (the MinerU API manager):
  * Distribution + bundled JRE live under ``backend/.neo4j/`` (sibling of
    ``backend/.venv/``), so the project ships Neo4j like it ships MinerU —
    no Docker, no system install.
  * ``start()`` spawns Neo4j's ``neo4j.bat console`` as a subprocess with
    ``JAVA_HOME`` pointed at the bundled JRE (or a system Java 17+).
  * Lazy auto-start: ``ensure_running()`` starts Neo4j if the bolt/http
    ports are not healthy; the backend calls it at startup when
    ``graph.mode=local`` (config-driven, same as MinerU's lazy startup).
  * Windows Job Object keeps the process tree alive-bound to this process;
    ``atexit`` stop is the Unix fallback.
  * Ports are config-driven (``graph.bolt_port`` / ``graph.http_port``),
    falling back to defaults 7687 / 7474 — matching the project's
    config-first design (env vars override config.yml in ConfigLoader).

First-run auth bootstrap: Neo4j 5.x starts with auth disabled on an empty
data dir. We run ``neo4j-admin dbms set-initial-password <pwd>`` *before*
first launch so the graph.password from config.yml is authoritative — the
same single-source-of-truth contract the docker-compose file used.
"""
from __future__ import annotations

import atexit
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
DEFAULT_HOME = _BACKEND_DIR / ".neo4j"
DEFAULT_DATA_DIR = _BACKEND_DIR.parent / "neo4j_data"        # project root (docker volume compat)
DEFAULT_LOG_DIR = _BACKEND_DIR.parent / "neo4j_logs"
DEFAULT_NEO4J_VERSION = "5.20.0"
DEFAULT_JAVA_MAJOR = 17

# ── Windows Job Object helpers (same lifecycle guarantees as MinerU) ─────
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessIdList", wintypes.LPVOID),
            ("ProcessIdListLength", wintypes.ULONG),
            ("PeakProcessIdListLength", wintypes.ULONG),
            ("HandleCount", ctypes.c_size_t),
            ("PeakHandleCount", ctypes.c_size_t),
            ("MemoryLimit", ctypes.c_size_t),
            ("PeakMemoryLimit", ctypes.c_size_t),
            ("RateControlTolerance", ctypes.c_size_t),
            ("RateControlInterval", ctypes.c_size_t),
        ]

    def _create_kill_on_close_job() -> int:
        kernel32 = ctypes.windll.kernel32
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return 0
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(info), ctypes.sizeof(info))  # JobObjectExtendedLimitInformation
        return int(job)

    def _assign_pid_to_job(job: int, pid: int) -> bool:
        return bool(ctypes.windll.kernel32.AssignProcessToJobObject(int(job), int(pid)))

    def _close_job_handle(job: Optional[int]) -> None:
        if job:
            try:
                ctypes.windll.kernel32.CloseHandle(int(job))
            except Exception:
                pass

    def _run_silent_kwargs() -> dict:
        flags = 0x08000000  # CREATE_NO_WINDOW
        si = subprocess.STARTUPINFO()
        try:
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
        except Exception:
            pass
        return {"creationflags": flags, "startupinfo": si}
else:
    def _create_kill_on_close_job() -> int:
        return 0

    def _assign_pid_to_job(job: int, pid: int) -> bool:
        return True

    def _close_job_handle(job: Optional[int]) -> None:
        pass

    def _run_silent_kwargs() -> dict:
        return {}


class Neo4jManager:
    """Manages a local Neo4j Community server as a subprocess (no Docker)."""

    def __init__(self, cfg: Optional[dict[str, Any]] = None):
        cfg = cfg or {}
        # config.yml paths are project-root-relative ("home: ./backend/.neo4j",
        # "data_dir: ./neo4j_data") — resolve ALL relative paths against the
        # project root so the backend (cwd=backend/) never lands in a
        # duplicated backend/backend/... directory.
        def _resolve(p) -> Path:
            pp = Path(p)
            return pp if pp.is_absolute() else (_BACKEND_DIR.parent / pp)

        self.home = _resolve(cfg.get("home") or DEFAULT_HOME)
        self.data_dir = _resolve(cfg.get("data_dir") or DEFAULT_DATA_DIR)
        self.log_dir = _resolve(cfg.get("log_dir") or DEFAULT_LOG_DIR)
        self.bolt_port = int(cfg.get("bolt_port") or 7687)
        self.http_port = int(cfg.get("http_port") or 7474)
        self.username = cfg.get("username") or "neo4j"
        self.password = cfg.get("password") or "123456"
        self.heap = cfg.get("heap") or "1G"
        self.pagecache = cfg.get("pagecache") or "1G"
        self.mirror = (cfg.get("mirror") or "").strip()
        self.version = cfg.get("version") or DEFAULT_NEO4J_VERSION
        self.host = cfg.get("host") or "127.0.0.1"

        self._process: Optional[subprocess.Popen] = None
        self._job_handle: Optional[int] = None
        self._spawn_lock = threading.Lock()
        self._atexit_registered = False
        self._installed_checked = False
        self._installed_ok = False

    # ── Properties ────────────────────────────────────────────────────
    @property
    def distribution_dir(self) -> Optional[Path]:
        """The extracted neo4j-community-* directory (absolute), or None."""
        if not self.home.exists():
            return None
        matches = sorted(
            self.home.glob(f"neo4j-community-*"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        for m in matches:
            if m.is_dir() and (m / "bin").exists():
                return m.resolve()
        return None

    @property
    def bundled_jre_dir(self) -> Optional[Path]:
        if not self.home.exists():
            return None
        # Temurin JRE zips extract to "jdk-<ver>+<build>-jre" (or "jre-<ver>") —
        # match any dir containing a java binary. Absolute path required:
        # neo4j.bat resolves %JAVA_HOME%\bin\java.exe from the dist cwd.
        for d in sorted(self.home.iterdir(),
                        key=lambda p: p.stat().st_mtime if p.exists() else 0,
                        reverse=True):
            if d.is_dir() and _jre_has_java(d):
                return d.resolve()
        return None

    @property
    def conf_path(self) -> Optional[Path]:
        d = self.distribution_dir
        return (d / "conf" / "neo4j.conf") if d else None

    # ── Java detection ────────────────────────────────────────────────
    def _system_java_ok(self) -> bool:
        try:
            r = subprocess.run(
                ["java", "-version"], capture_output=True, text=True, timeout=15,
                **_run_silent_kwargs())
            version_line = (r.stderr or r.stdout or "").splitlines()[0]
            m = re.search(r'version "(\d+)', version_line)
            return bool(m and int(m.group(1)) >= DEFAULT_JAVA_MAJOR)
        except Exception:
            return False

    def resolve_java_home(self) -> Optional[Path]:
        """Prefer bundled JRE; fall back to a system Java 17+."""
        jre = self.bundled_jre_dir
        if jre:
            return jre
        if self._system_java_ok():
            return None  # use system java (do not set JAVA_HOME)
        return None

    # ── Installation (download + extract) ─────────────────────────────
    def ensure_installed(self, download: bool = True) -> bool:
        """Ensure the Neo4j distribution (+ JRE) is present; download if missing."""
        if self._installed_checked:
            return self._installed_ok
        try:
            self.home.mkdir(parents=True, exist_ok=True)
            dist = self.distribution_dir
            if dist is None:
                if not download:
                    self._installed_ok = False
                    return False
                dist = self._download_distribution()
            if self.resolve_java_home() is None and not self._system_java_ok():
                if not download:
                    self._installed_ok = False
                    return False
                self._download_jre()
            self._installed_ok = True
        except Exception as e:
            logger.error("Neo4j install failed: %s", e, exc_info=True)
            self._installed_ok = False
        finally:
            self._installed_checked = True
        return self._installed_ok

    def _download_distribution(self) -> Optional[Path]:
        # Windows ships a zip; Linux/macOS ship a tar.gz — pick per platform.
        if sys.platform == "win32":
            archive_name = f"neo4j-community-{self.version}-windows.zip"
            dest = self.home / archive_name
            url = self.mirror or f"https://dist.neo4j.org/{archive_name}"
            extract = _extract_zip
            dist_dir = self.home / f"neo4j-community-{self.version}"
        else:
            archive_name = f"neo4j-community-{self.version}-unix.tar.gz"
            dest = self.home / archive_name
            url = self.mirror or f"https://dist.neo4j.org/{archive_name}"
            extract = _extract_targz
            dist_dir = self.home / f"neo4j-community-{self.version}"
        logger.info("Downloading Neo4j Community %s (%s) ...", self.version, archive_name)
        _download_with_progress(url, dest)
        logger.info("Extracting Neo4j distribution ...")
        extract(dest, self.home)
        if not (dist_dir / "bin").exists():
            # fallback: first directory containing bin/
            for d in sorted(self.home.glob("neo4j-community-*")):
                if d.is_dir() and (d / "bin").exists():
                    dist_dir = d
                    break
        if not (dist_dir / "bin").exists():
            raise RuntimeError("Neo4j distribution extraction produced no bin/ dir")
        if sys.platform != "win32":
            # Unix tarballs ship non-executable bin scripts — make them runnable
            for bin_script in ("neo4j", "neo4j-admin", "cypher-shell"):
                p = dist_dir / "bin" / bin_script
                if p.exists():
                    try:
                        p.chmod(p.stat().st_mode | 0o755)
                    except Exception:
                        pass
        return dist_dir

    def _download_jre(self) -> None:
        # Adoptium (Temurin) JRE 17 — platform/arch aware:
        #   windows → zip ; linux/macos → tar.gz ; x64/aarch64 handled by API
        import platform

        platform_map = {"win32": "windows", "linux": "linux", "darwin": "mac"}
        arch_map = {"AMD64": "x64", "x86_64": "x64", "arm64": "aarch64", "aarch64": "aarch64"}
        os_name = platform_map.get(sys.platform, "linux")
        os_arch = arch_map.get(platform.machine(), "x64")
        ext = "zip" if os_name == "windows" else "tar.gz"
        archive_name = f"jre17-{os_name}-{os_arch}.{ext}"
        dest = self.home / archive_name
        if not dest.exists():
            url = ("https://api.adoptium.net/v3/binary/latest/17/ga/"
                   f"{os_name}/{os_arch}/jre/hotspot/normal/eclipse")
            logger.info("Downloading bundled JRE 17 (Temurin, %s/%s) ...", os_name, os_arch)
            _download_with_progress(url, dest)
        logger.info("Extracting bundled JRE ...")
        ( _extract_zip if ext == "zip" else _extract_targz )(dest, self.home)

    # ── Config + first-run auth ───────────────────────────────────────
    def _write_conf(self) -> Path:
        dist = self.distribution_dir
        if dist is None:
            raise RuntimeError("Neo4j not installed")
        conf = dist / "conf" / "neo4j.conf"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Neo4j rejects non-normalized paths (e.g. containing "..") — always
        # resolve to absolute before writing conf.
        data_abs = self.data_dir.resolve().as_posix()
        logs_abs = self.log_dir.resolve().as_posix()
        lines = [
            f"server.bolt.listen_address={self.host}:{self.bolt_port}",
            f"server.http.listen_address={self.host}:{self.http_port}",
            f"server.directories.data={data_abs}",
            f"server.directories.logs={logs_abs}",
            "dbms.security.auth_enabled=true",
            # 与旧 docker-compose 行为一致(NEO4J_dbms_security_auth__minimum__password__length=6):
            # 默认密码 123456 仅 6 位, 不放开则 neo4j-admin set-initial-password 拒绝
            "dbms.security.auth_minimum_password_length=6",
            f"server.memory.heap.initial_size={self.heap}",
            f"server.memory.heap.max_size={self.heap}",
            f"server.memory.pagecache.size={self.pagecache}",
            "server.default_listen_address=127.0.0.1",
        ]
        conf.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Neo4j conf written: %s (bolt %s / http %s)",
                    conf, self.bolt_port, self.http_port)
        return conf

    def _bootstrap_auth_if_needed(self) -> None:
        """Set the initial password before first launch (auth bootstraps on
        an empty data dir only; idempotent on later starts). Retries once on
        transient failure so a flaky subprocess env never leaves Neo4j in the
        default-credentials state."""
        dist = self.distribution_dir
        data_inited = (self.data_dir / "databases" / "neo4j").exists()
        if data_inited:
            return
        admin = dist / "bin" / ("neo4j-admin.bat" if sys.platform == "win32" else "neo4j-admin")
        for attempt in (1, 2):
            try:
                r = subprocess.run(
                    [str(admin), "dbms", "set-initial-password", self.password],
                    capture_output=True, text=True, timeout=120,
                    env=self._runtime_env(), **_run_silent_kwargs())
                if r.returncode == 0:
                    logger.info("Neo4j initial password set (data dir fresh, attempt %d)", attempt)
                    return
                logger.warning("neo4j-admin set-initial-password rc=%s (attempt %d): %s",
                               r.returncode, attempt, (r.stderr or r.stdout)[:300])
            except Exception as e:
                logger.warning("neo4j-admin bootstrap failed (attempt %d): %s", attempt, e,
                               exc_info=True)
        # Both attempts failed → Neo4j will start with default creds
        # (CredentialsExpired). Warn loudly so operators notice.
        logger.error(
            "Neo4j initial password could NOT be set — server will start with "
            "default credentials. Fix auth after first start or clear %s and restart.",
            self.data_dir)

    def _runtime_env(self) -> dict:
        env = os.environ.copy()
        jre = self.bundled_jre_dir
        if jre:
            env["JAVA_HOME"] = str(jre)
            env["PATH"] = str(jre / "bin") + os.pathsep + env.get("PATH", "")
        if self.distribution_dir:
            env["NEO4J_HOME"] = str(self.distribution_dir)
        return env

    # ── Lifecycle ─────────────────────────────────────────────────────
    def _health_ok(self) -> bool:
        try:
            with socket.create_connection((self.host, self.bolt_port), timeout=2.0):
                return True
        except Exception:
            return False

    def is_running(self) -> bool:
        return self._health_ok()

    def start(self, timeout: int = 120, detach: bool = False) -> bool:
        """Install-if-needed, bootstrap auth, spawn ``neo4j console``.

        detach=True (ragctl/CLI standalone management): the subprocess is NOT
        bound to this process's lifetime (no Job Object / atexit) so it keeps
        running after the CLI exits — stop via ``neo4j_cli stop`` (port kill).
        detach=False (backend startup): Neo4j lifecycle is bound to the
        backend process (Job Object kill-on-close), like MinerU.
        """
        with self._spawn_lock:
            if self._health_ok():
                logger.info("Neo4j already healthy on bolt :%s", self.bolt_port)
                return True
            if not self.ensure_installed():
                logger.error("Neo4j installation missing/failed")
                return False
            dist = self.distribution_dir
            if dist is None:
                return False
            self._write_conf()
            self._bootstrap_auth_if_needed()
            if not detach:
                self._ensure_atexit()
            console = dist / "bin" / ("neo4j.bat" if sys.platform == "win32" else "neo4j")
            self.log_dir.mkdir(parents=True, exist_ok=True)
            log_file = open(self.log_dir / "neo4j-console.log", "a", encoding="utf-8", errors="replace")
            try:
                self._process = subprocess.Popen(
                    [str(console), "console"],
                    cwd=str(dist),
                    env=self._runtime_env(),
                    stdout=log_file, stderr=subprocess.STDOUT,
                    **_run_silent_kwargs(),
                )
            except Exception:
                log_file.close()
                raise
            if self._process.pid:
                job = _create_kill_on_close_job()
                if job and not detach:
                    _assign_pid_to_job(job, self._process.pid)
                    self._job_handle = job
                elif job:
                    _close_job_handle(job)
            deadline = time.time() + timeout
            while time.time() < deadline:
                if self._health_ok():
                    logger.info("Neo4j ready (bolt :%s, http :%s, pid %s)",
                                self.bolt_port, self.http_port, self._process.pid)
                    return True
                if self._process.poll() is not None:
                    logger.error("Neo4j console exited early (rc=%s) — see %s",
                                 self._process.returncode, self.log_dir / "neo4j-console.log")
                    return False
                time.sleep(2)
            logger.warning("Neo4j did not become healthy within %ss", timeout)
            return False

    def stop(self) -> None:
        """Stop the managed console process (defensive; Job Object covers crash)."""
        proc = self._process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._process = None
        _close_job_handle(self._job_handle)
        self._job_handle = None
        logger.info("Neo4j local manager stopped")

    def _ensure_atexit(self) -> None:
        if not self._atexit_registered:
            atexit.register(self.stop)
            self._atexit_registered = True

    def ensure_running(self, timeout: int = 120) -> bool:
        """Lazy auto-start used by the backend at startup (MinerU pattern)."""
        if self._health_ok():
            return True
        return self.start(timeout=timeout)


def _jre_has_java(jre_dir: Path) -> bool:
    return (jre_dir / "bin" / ("java.exe" if sys.platform == "win32" else "java")).exists()


def _download_with_progress(url: str, dest: Path, timeout: int = 1800,
                           min_bytes: int = 5_000_000, retries: int = 3) -> None:
    """Stream download with progress logging, size + zip-header validation,
    and bounded retries. A truncated download (e.g. proxy cut-off at 27 MB of
    a 126 MB archive) previously sailed through as 'complete' and then failed
    at extract time with BadZipFile — now any incomplete/invalid payload is
    deleted and retried."""
    if dest.exists() and dest.stat().st_size >= min_bytes and _looks_like_archive(dest):
        logger.info("Cached archive found: %s", dest)
        return
    for attempt in range(1, retries + 1):
        tmp = dest.with_suffix(dest.suffix + ".part")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rag-knowledge-neo4j-installer"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                last_log = time.time()
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total and time.time() - last_log > 5:
                        logger.info("  download %d/%d MB (%.0f%%)",
                                    done // 1048576, total // 1048576, 100.0 * done / total)
                        last_log = time.time()
            size = tmp.stat().st_size
            if size < min_bytes or (total and size < total):
                raise RuntimeError(f"truncated download: {size} bytes (expected >= {max(total, min_bytes)})")
            if not _looks_like_archive(tmp):
                raise RuntimeError("payload is not a valid archive (bad magic header)")
            os.replace(tmp, dest)
            logger.info("Download complete: %s (%.1f MB)", dest.name, dest.stat().st_size / 1048576)
            return
        except Exception as e:
            logger.warning("download attempt %d/%d failed: %s", attempt, retries, e)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
    raise RuntimeError(f"download failed after {retries} attempts: {url}")


def _looks_like_archive(path: Path) -> bool:
    """PK = zip ; 1F 8B = gzip (tar.gz) — cheap magic-header check."""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic[:2] == b"PK" or magic[:2] == b"\x1f\x8b"
    except Exception:
        return False


def _extract_zip(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target)
    logger.info("Extracted %s → %s", archive.name, target)


def _extract_targz(archive: Path, target: Path) -> None:
    import tarfile

    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        try:
            tf.extractall(target, filter="data")  # safe extraction (py3.12+)
        except TypeError:
            tf.extractall(target)  # older Python: no filter arg
    logger.info("Extracted %s → %s", archive.name, target)


# ── Module-level singleton (lazy) ────────────────────────────────────────
_manager: Optional[Neo4jManager] = None


def get_neo4j_manager(cfg: Optional[dict[str, Any]] = None) -> Neo4jManager:
    global _manager
    if _manager is None:
        _manager = Neo4jManager(cfg)
    return _manager
