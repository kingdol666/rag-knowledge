"""
Neo4j local CLI — `python neo4j_cli.py start|stop|status`

Thin wrapper around :class:`app.utils.neo4j_manager.Neo4jManager` so shell
scripts (ragctl / start.bat) can manage the local Neo4j without inline
python -c quoting issues. All settings come from ``config.yml`` (graph.*),
respecting the project's config-first design.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/ (utils → app → backend)


def _load_config() -> dict:
    """Parse the graph section of config.yml WITHOUT third-party deps
    (pyyaml etc.) so Neo4j installation works on a fresh clone before
    backend/.venv exists — ragctl start neo4j must not require ragctl deps."""
    import os
    import re

    cfg_path = BACKEND_DIR.parent / "config.yml"
    raw = cfg_path.read_text(encoding="utf-8")

    # expand ${NEO4J_PASSWORD:-123456} style env interpolation
    def _interp(m: re.Match) -> str:
        name, default = m.group(1), m.group(2) or ""
        return os.environ.get(name, default)

    raw = re.sub(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}", _interp, raw)

    # extract the top-level `graph:` block (2-space indented keys)
    lines = raw.splitlines()
    in_graph = False
    cfg: dict = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not in_graph:
            if re.match(r"^graph:\s*$", stripped):
                in_graph = True
            continue
        if re.match(r"^[a-z_]+:\s*$", stripped) and not line.startswith(" "):
            break  # next top-level section
        m = re.match(r"^\s{2}([a-z_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        # strip inline comment
        val = re.sub(r"\s+#.*$", "", val).strip().strip('"').strip("'")
        if val == "" or val == "null":
            cfg[key] = None
        elif val == "true":
            cfg[key] = True
        elif val == "false":
            cfg[key] = False
        # Only numeric *port* fields become int; plain-digit strings like a
        # numeric password ("123456") must stay str — subprocess args with an
        # int previously crashed with 'expected str, bytes or os.PathLike...'
        elif re.match(r"^-?\d+$", val) and key in ("bolt_port", "http_port", "startup_timeout"):
            cfg[key] = int(val)
        else:
            cfg[key] = val
    return cfg


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    cfg = _load_config()
    mode = cfg.get("mode", "local")
    if mode != "local":
        print(f"graph.mode={mode!r} — local CLI only handles mode=local")
        return 1

    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    from app.utils.neo4j_manager import Neo4jManager  # noqa: E402 (needs sys.path)

    manager = Neo4jManager(cfg)
    if cmd == "start":
        # detach=True: keep running after this CLI exits (ragctl standalone mode)
        ok = manager.start(timeout=int(cfg.get("startup_timeout", 180)), detach=True)
        print("Neo4j (local) started" if ok else "Neo4j (local) FAILED to start")
        return 0 if ok else 1
    if cmd == "stop":
        manager.stop()
        print("Neo4j (local) stop requested")
        return 0
    # status
    if manager.is_running():
        print(f"Neo4j (local) running — bolt :{manager.bolt_port}, http :{manager.http_port}")
        return 0
    print(f"Neo4j (local) stopped (home={manager.home})")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(BACKEND_DIR))
    raise SystemExit(main())
