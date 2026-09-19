"""Clean-restart backend (uvicorn on BACKEND_PORT, default 8771) + web (nuxt dev 6789).

Windows-only helper: kills whatever holds the ports (including orphan reload
workers), then spawns both services detached with timestamped logs.
Usage: python scripts/dev_restart.py
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
WEB_DIR = os.path.join(ROOT, "web")
PY = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
LOG_DIR = os.path.join(WEB_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.join(BACKEND_DIR, "logs"), exist_ok=True)


def pids_on_port(port: int) -> set:
    out = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="replace",
    ).stdout
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING":
            if parts[1].rsplit(":", 1)[-1] == str(port):
                pids.add(int(parts[4]))
    return pids


def kill_port(port: int) -> None:
    # uvicorn --reload leaves an orphan worker that re-holds the socket after
    # the parent dies, so keep force-killing until the port is actually free.
    for _round in range(6):
        pids = pids_on_port(port)
        if not pids:
            return
        for pid in pids:
            killed = _kill_pid(pid)
            if not killed:
                _kill_orphan_workers(pid)
        time.sleep(1)
    if pids_on_port(port):
        print(f"  WARNING port {port} still held after 6 rounds")


def _kill_pid(pid: int) -> bool:
    try:
        os.kill(pid, 9)
        print(f"  killed pid {pid}")
        return True
    except (OSError, ProcessLookupError):
        return False


def _kill_orphan_workers(dead_pid: int) -> None:
    """netstat reports the socket *creator* PID; when uvicorn --reload's parent
    died, its multiprocessing worker (parent_pid=<dead>) still serves the port."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'spawn_main' -and "
        "$_.CommandLine -match 'parent_pid=%d' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" % dead_pid
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    print(f"  orphan workers of dead pid {dead_pid}: rc={r.returncode}")


def main() -> int:
    backend_port = 8771
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("BACKEND_PORT="):
                    backend_port = int(line.split("=", 1)[1].strip())
    print(f"restart targets: backend :{backend_port}, web :6789")

    kill_port(backend_port)
    kill_port(6789)
    time.sleep(2)
    leftovers = pids_on_port(backend_port) | pids_on_port(6789)
    if leftovers:
        print(f"WARNING ports still held by {leftovers}")
        return 1

    stamp = time.strftime("%Y%m%d-%H%M%S")
    be_log = open(
        os.path.join(BACKEND_DIR, "logs", f"uvicorn-{stamp}.log"), "ab"
    )
    subprocess.Popen(
        [PY, "main.py"],
        cwd=BACKEND_DIR,
        stdout=be_log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print("backend spawned")

    nw_log = open(os.path.join(LOG_DIR, f"nuxt-dev-{stamp}.log"), "ab")
    nw_err = open(os.path.join(LOG_DIR, f"nuxt-dev-{stamp}.err.log"), "ab")
    subprocess.Popen(
        ["node", "./start.mjs"],
        cwd=WEB_DIR,
        stdout=nw_log,
        stderr=nw_err,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print("web spawned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
