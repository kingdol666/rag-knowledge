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
    """Minimal config.yml loader (graph section) — no backend imports needed."""
    cfg_path = BACKEND_DIR.parent / "config.yml"
    raw = cfg_path.read_text(encoding="utf-8")
    # expand ${NEO4J_PASSWORD:-123456} style env interpolation
    import os
    import re

    def _interp(m: re.Match) -> str:
        name, default = m.group(1), m.group(2) or ""
        return os.environ.get(name, default)

    raw = re.sub(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}", _interp, raw)

    import yaml
    return yaml.safe_load(raw).get("graph", {}) or {}


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    cfg = _load_config()
    mode = cfg.get("mode", "local")
    if mode != "local":
        print(f"graph.mode={mode!r} — local CLI only handles mode=local")
        return 1

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
