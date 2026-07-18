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


def _global_config_dir() -> Path:
    """Claude Code global config directory — ~/.claude"""
    return Path.home() / ".claude"


def cmd_install(target: str | None = None):
    """Install kb-mcp into .mcp.json of the given project (or globally)."""

    # Determine target
    if target:
        target_path = Path(target).resolve()
        if not target_path.exists():
            print(f"Error: target directory does not exist: {target_path}")
            return 1
    else:
        # Default: global Claude Code MCP config
        target_path = _global_config_dir()
        target_path.mkdir(parents=True, exist_ok=True)

    mcp_file = target_path / ".mcp.json"

    # Read or create .mcp.json
    if mcp_file.exists():
        with open(mcp_file, encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Check if already installed
    if "kb-mcp" in config["mcpServers"]:
        print("kb-mcp is already installed in", str(mcp_file))
        print("  To reinstall, uninstall first: python plugin_install.py uninstall", f"--target {target_path}" if target else "")
        return 0

    # Set RAG_PROJECT_ROOT in env if not already set (for non-local installs)
    entry = MCP_ENTRY.copy()
    entry["kb-mcp"] = MCP_ENTRY["kb-mcp"].copy()
    entry["kb-mcp"]["env"] = MCP_ENTRY["kb-mcp"]["env"].copy()

    # If installing outside the rag-knowledge repo, add RAG_PROJECT_ROOT
    rag_root = os.environ.get("RAG_PROJECT_ROOT")
    if not rag_root:
        # Auto-detect: if we're inside rag-knowledge/kb-mcp, use parent
        if (KB_MCP_DIR.parent / "config.yml").exists():
            rag_root = str(KB_MCP_DIR.parent.resolve())

    if rag_root:
        entry["kb-mcp"]["env"]["RAG_PROJECT_ROOT"] = rag_root

    # Add backend/web URL env vars for remote access
    backend_url = os.environ.get("BACKEND_URL")
    if backend_url:
        entry["kb-mcp"]["env"]["BACKEND_URL"] = backend_url
    web_url = os.environ.get("WEB_URL")
    if web_url:
        entry["kb-mcp"]["env"]["WEB_URL"] = web_url

    config["mcpServers"]["kb-mcp"] = entry["kb-mcp"]

    # Write back
    with open(mcp_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("[OK] kb-mcp installed to", str(mcp_file))
    print("  Servers: kb-mcp (~63 tools — KB CRUD, search, graph, experience)")
    if rag_root:
        print("  RAG_PROJECT_ROOT:", rag_root)
    else:
        print("  ⚠ RAG_PROJECT_ROOT not set — set it to the rag-knowledge repo path if using from another project")
    print()
    print("  Restart Claude Code (or run /mcp) to connect.")
    return 0


def cmd_uninstall(target: str | None = None):
    """Remove kb-mcp from .mcp.json."""
    if target:
        target_path = Path(target).resolve()
    else:
        target_path = _global_config_dir()

    mcp_file = target_path / ".mcp.json"
    if not mcp_file.exists():
        print("No .mcp.json found at", str(mcp_file))
        return 1

    with open(mcp_file, encoding="utf-8") as f:
        config = json.load(f)

    if "mcpServers" in config and "kb-mcp" in config["mcpServers"]:
        del config["mcpServers"]["kb-mcp"]
        if not config["mcpServers"]:
            del config["mcpServers"]

        with open(mcp_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print("[OK] kb-mcp uninstalled from", str(mcp_file))
    else:
        print("kb-mcp not found in", str(mcp_file))

    return 0


def cmd_status():
    """Show current kb-mcp installation status."""
    print("kb-mcp Plugin Status")
    print("════════════════════")
    print()
    print("kb-mcp directory:", str(KB_MCP_DIR))
    print()

    # Check project .mcp.json
    project_mcp = KB_MCP_DIR.parent / ".mcp.json"
    if project_mcp.exists():
        with open(project_mcp, encoding="utf-8") as f:
            cfg = json.load(f)
        servers = cfg.get("mcpServers", {})
        if "kb-mcp" in servers:
            print("[OK] Project .mcp.json:  installed (rag-knowledge local)")
        else:
            print("○ Project .mcp.json:  not present")
    else:
        print("○ Project .mcp.json:  not found")

    # Check global ~/.claude/.mcp.json
    global_mcp = _global_config_dir() / ".mcp.json"
    if global_mcp.exists():
        with open(global_mcp, encoding="utf-8") as f:
            cfg = json.load(f)
        servers = cfg.get("mcpServers", {})
        if "kb-mcp" in servers:
            print("[OK] Global ~/.claude/.mcp.json: installed (available everywhere)")
            env_vars = servers["kb-mcp"].get("env", {})
            for k, v in env_vars.items():
                print(f"    {k}={v}")
        else:
            print("○ Global ~/.claude/.mcp.json: not present")
    else:
        print("○ Global ~/.claude/.mcp.json: not found (run `python plugin_install.py install` to activate globally)")

    print()
    print("Commands:")
    print("  python plugin_install.py install              → install globally (available in ALL projects)")
    print("  python plugin_install.py install --target /x  → install in specific project")
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
