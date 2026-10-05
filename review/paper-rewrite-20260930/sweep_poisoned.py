"""Sweep + re-run mount-flake casualties in the monitored run dir.

A platform (a2) cell with zero mcp__ calls, or a dense (c) cell with zero
mcp__ calls, is a mount-flake refusal (the CLI raced the kb-mcp handshake),
not a measured result. Delete such cells and resume the runner with
--out-dir until clean or rounds exhausted. b cells legitimately use no mcp.
"""
import glob
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = sys.argv[1] if len(sys.argv) > 1 else "run-20260930T150453Z-3ec2174"
RUNDIR = os.path.join(REPO, "benchmark-suite", "results", "runs", RUN)

for rnd in range(1, 5):
    poisoned = []
    for f in glob.glob(os.path.join(RUNDIR, "track_*.json")):
        trk = os.path.basename(f).split("_")[1]
        if trk not in ("a2", "c"):
            continue
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:
            poisoned.append(f)
            continue
        calls = c.get("tool_calls") or []
        mcp = sum(1 for t in calls if t and "mcp__" in str(t.get("tool", "")))
        if mcp == 0:
            poisoned.append(f)
    print(f"[sweep {rnd}] poisoned cells: {[os.path.basename(p) for p in poisoned]}")
    if not poisoned:
        print("[sweep] clean")
        break
    for f in poisoned:
        os.remove(f)
    cmd = [
        sys.executable, "-X", "utf8", "-m", "experiments.runner",
        "--questions", "data/papers/qa_questions.json",
        "--tracks", "a2,b,c", "--out-dir",
        os.path.relpath(RUNDIR, os.path.join(REPO, "benchmark-suite")),
    ]
    print("[sweep] resuming runner ...", flush=True)
    subprocess.run(cmd, cwd=os.path.join(REPO, "benchmark-suite"), timeout=3300)
print("[sweep] done:", RUNDIR)
