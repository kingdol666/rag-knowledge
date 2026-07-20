#!/usr/bin/env python3
"""
kb-mcp Plugin Installer
═════════════════════════════════════════════════════════════════
Install kb-mcp as a globally-available Claude Code MCP plugin.

Usage:
  python plugin_install.py install [--target /path/to/project]
  python plugin_install.py uninstall [--target /path/to/project]
  python plugin_install.py status

After installation, kb-mcp becomes available in ANY Claude Code project
as a connected MCP server, providing full knowledge base CRUD operations.
"""

import json
import os
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

KB_MCP_DIR = Path(__file__).resolve().parent

MCP_ENTRY = {
    "kb-mcp": {
        "command": "uv",
        "args": [
            "run",
            "--directory",
            str(KB_MCP_DIR),
            "python",
            "server.py",
        ],
        "env": {
            "APP_MODE": os.environ.get("APP_MODE", "dev"),
        },
    }
}


def _find_mcp_json(target: Path) -> Path | None:
    """Find .mcp.json in target directory or its parents (up to 3 levels)."""
    for _ in range(4):
        candidate = target / ".mcp.json"
        if candidate.exists():
            return candidate
        if target.parent == target:
            break
        target = target.parent
    return None


def _global_config_file() -> Path:
    """Claude Code global user config file — ~/.claude.json

    This is where global MCP servers are registered under the ``mcpServers`` key.
    (NOT ~/.claude/.mcp.json — that path is not read by Claude Code for global scope.)
    """
    return Path.home() / ".claude.json"


def _read_json_safe(path: Path) -> dict:
    """Read JSON file, return {} on missing/corrupt."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically (temp file + rename) to avoid corrupting large config files.

    Critical for ~/.claude.json which may be 80KB+ with many user settings —
    a partial write would wipe the user's entire Claude Code config.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # Atomic rename (on same filesystem)
    tmp.replace(path)


def cmd_install(target: str | None = None):
    """Install kb-mcp globally (~/.claude.json) or into a project (.mcp.json)."""

    is_global = not target

    if is_global:
        # Global: ~/.claude.json → mcpServers (preserves all other user config keys)
        config_file = _global_config_file()
        config = _read_json_safe(config_file)
        # Never blow away an existing ~/.claude.json — merge into it
        if not config:
            print(f"[WARN] {config_file} is empty or missing — creating new file")
        scope_label = "global (~/.claude.json → mcpServers)"
    else:
        # Project: <target>/.mcp.json
        target_path = Path(target).resolve()
        if not target_path.exists():
            print(f"Error: target directory does not exist: {target_path}")
            return 1
        config_file = target_path / ".mcp.json"
        config = _read_json_safe(config_file)
        scope_label = f"project ({config_file})"

    if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
        config["mcpServers"] = {}

    # Check if already installed
    if "kb-mcp" in config["mcpServers"]:
        print(f"kb-mcp is already installed [{scope_label}]")
        print("  To reinstall, uninstall first: python plugin_install.py uninstall" +
              (f" --target {target}" if target else ""))
        return 0

    # Build entry (copy MCP_ENTRY, augment with RAG_PROJECT_ROOT if non-local)
    entry = {
        "command": MCP_ENTRY["kb-mcp"]["command"],
        "args": MCP_ENTRY["kb-mcp"]["args"][:],
        "env": dict(MCP_ENTRY["kb-mcp"]["env"]),
    }

    # If installing outside the rag-knowledge repo, add RAG_PROJECT_ROOT
    rag_root = os.environ.get("RAG_PROJECT_ROOT")
    if not rag_root:
        # Auto-detect: if we're inside rag-knowledge/kb-mcp, use parent
        if (KB_MCP_DIR.parent / "config.yml").exists():
            rag_root = str(KB_MCP_DIR.parent.resolve())

    if rag_root:
        entry["env"]["RAG_PROJECT_ROOT"] = rag_root

    # Add backend/web URL env vars for remote access
    backend_url = os.environ.get("BACKEND_URL")
    if backend_url:
        entry["env"]["BACKEND_URL"] = backend_url
    web_url = os.environ.get("WEB_URL")
    if web_url:
        entry["env"]["WEB_URL"] = web_url

    config["mcpServers"]["kb-mcp"] = entry

    # Write back (atomic for safety — especially for ~/.claude.json)
    _write_json_atomic(config_file, config)

    print(f"[OK] kb-mcp installed [{scope_label}]")
    print(f"  File: {config_file}")
    print("  Server: kb-mcp (76 tools — KB CRUD, search, graph, experience, project lifecycle)")
    if rag_root:
        print(f"  RAG_PROJECT_ROOT: {rag_root}")
    else:
        print("  ⚠ RAG_PROJECT_ROOT not set — set it to the rag-knowledge repo path if using from another project")
    print()
    print("  Restart Claude Code (or run /mcp) to connect.")
    return 0


def cmd_uninstall(target: str | None = None):
    """Remove kb-mcp globally (~/.claude.json) or from a project (.mcp.json)."""

    is_global = not target

    if is_global:
        config_file = _global_config_file()
        scope_label = "global (~/.claude.json)"
    else:
        target_path = Path(target).resolve()
        config_file = target_path / ".mcp.json"
        scope_label = f"project ({config_file})"

    if not config_file.exists():
        print(f"No file found at {config_file}")
        return 1

    config = _read_json_safe(config_file)
    servers = config.get("mcpServers", {})

    if "kb-mcp" in servers:
        del servers["kb-mcp"]
        # Clean up empty mcpServers key (only for project .mcp.json;
        # for ~/.claude.json keep the key structure intact)
        if not servers and not is_global:
            config.pop("mcpServers", None)

        _write_json_atomic(config_file, config)
        print(f"[OK] kb-mcp uninstalled [{scope_label}]")
    else:
        print(f"kb-mcp not found [{scope_label}]")

    return 0


def cmd_status():
    """Show current kb-mcp installation status."""
    print("kb-mcp Plugin Status")
    print("════════════════════")
    print()
    print("kb-mcp directory:", str(KB_MCP_DIR))
    print()

    # Check project .mcp.json (rag-knowledge repo root)
    project_mcp = KB_MCP_DIR.parent / ".mcp.json"
    if project_mcp.exists():
        cfg = _read_json_safe(project_mcp)
        servers = cfg.get("mcpServers", {})
        if "kb-mcp" in servers:
            print("[OK] Project .mcp.json:      installed (rag-knowledge local)")
        else:
            print("○  Project .mcp.json:        kb-mcp not present")
    else:
        print("○  Project .mcp.json:        not found")

    # Check global ~/.claude.json → mcpServers (the CORRECT global location)
    global_file = _global_config_file()
    if global_file.exists():
        cfg = _read_json_safe(global_file)
        servers = cfg.get("mcpServers", {})
        if "kb-mcp" in servers:
            print("[OK] Global ~/.claude.json:   installed (available everywhere)")
            env_vars = servers["kb-mcp"].get("env", {})
            for k, v in env_vars.items():
                print(f"    {k}={v}")
        else:
            other_servers = list(servers.keys())
            print(f"○  Global ~/.claude.json:    kb-mcp not in mcpServers"
                  + (f" (has: {', '.join(other_servers)})" if other_servers else ""))
    else:
        print("○  Global ~/.claude.json:    not found")

    # Legacy path check (warn if present — old plugin_install.py wrote here)
    legacy = Path.home() / ".claude" / ".mcp.json"
    if legacy.exists():
        cfg = _read_json_safe(legacy)
        if "kb-mcp" in cfg.get("mcpServers", {}):
            print(f"[WARN] Legacy {legacy}: kb-mcp found here (NOT read by Claude Code)")
            print("       Migrate: uninstall legacy, then `plugin_install.py install`")

    print()
    print("Commands:")
    print("  python plugin_install.py install              → install globally (~/.claude.json)")
    print("  python plugin_install.py install --target /x  → install in specific project (.mcp.json)")
    print("  python plugin_install.py uninstall            → remove globally")
    print("  python plugin_install.py status               → show status")


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    target = None

    if "--target" in args:
        idx = args.index("--target")
        if idx + 1 < len(args):
            target = args[idx + 1]

    if cmd == "install":
        sys.exit(cmd_install(target))
    elif cmd == "uninstall":
        sys.exit(cmd_uninstall(target))
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python plugin_install.py [install|uninstall|status] [--target PATH]")
        sys.exit(1)
