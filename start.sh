#!/usr/bin/env bash
# ============================================================
# RAG Knowledge Platform — Unified Launcher (Linux / macOS)
#
# Usage:  ./start.sh [dev|prod]
#   Launches Backend (FastAPI) + Web (Nuxt 3) in separate terminals.
#   Ports are read from config.yml (single source of truth).
#
# Exit codes:
#   0  success
#   1  missing dependency or submodule
# ============================================================
set -euo pipefail

MODE="${1:-${APP_MODE:-dev}}"
[[ "$MODE" == "d" ]] && MODE="dev"
[[ "$MODE" == "p" ]] && MODE="prod"

ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_DIR="$ROOT/scripts"

# ── Colors ──────────────────────────────────────────────────
if [[ -t 1 ]]; then
    CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
else
    CYAN=''; GREEN=''; YELLOW=''; RED=''; NC=''
fi

echo ""
echo "  💡 Tip: Use './ragctl init' for first-time setup, then './ragctl up' to start."
echo "  💡 Tip: Use './ragctl doctor' to diagnose any issues."
echo ""
echo "  =================================================="
echo "    RAG Knowledge Platform — Mode: $MODE"
echo "  =================================================="
echo ""

# ── Prerequisite checks ────────────────────────────────────
check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

missing=0
if ! check_cmd uv; then
    echo -e "  ${RED}[ERROR]${NC} 'uv' not found — install: https://docs.astral.sh/uv/"
    missing=1
fi
if ! check_cmd node; then
    echo -e "  ${RED}[ERROR]${NC} 'node' not found — install Node.js 18+"
    missing=1
fi
if ! check_cmd npm; then
    echo -e "  ${RED}[ERROR]${NC} 'npm' not found — install Node.js 18+"
    missing=1
fi
[[ $missing -ne 0 ]] && exit 1

# ── Submodule check ────────────────────────────────────────
[ -d "$ROOT/backend/app" ] || { echo -e "  ${RED}[ERROR]${NC} Backend submodule not found. Run: git submodule update --init --recursive"; exit 1; }
[ -f "$ROOT/web/package.json" ] || { echo -e "  ${RED}[ERROR]${NC} Web submodule not found. Run: git submodule update --init --recursive"; exit 1; }

# ── Install web deps if needed ─────────────────────────────
[ -d "$ROOT/web/node_modules" ] || { echo "  Installing web deps..."; (cd "$ROOT/web" && npm install); }

# ── Optional: Neo4j status (informational, non-blocking) ──
# Neo4j is optional — graph features degrade gracefully if unavailable.
if check_cmd docker; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q rag-knowledge-neo4j; then
        echo -e "  ${GREEN}[INFO]${NC} Neo4j container detected (graph features available)"
    else
        echo -e "  ${YELLOW}[INFO]${NC} Neo4j container not running — graph features will be degraded"
        echo "         Start it with: docker compose up -d neo4j"
    fi
fi
echo ""

# ── Launch services ────────────────────────────────────────
echo -e "  ${CYAN}[1/2]${NC} Starting Backend..."
echo -e "  ${CYAN}[2/2]${NC} Starting Web..."

if check_cmd gnome-terminal; then
    gnome-terminal --title="RAG-Backend ($MODE)" -- bash -c "$SCRIPT_DIR/start-backend.sh $MODE; exec bash"
    gnome-terminal --title="RAG-Web ($MODE)"     -- bash -c "$SCRIPT_DIR/start-web.sh $MODE; exec bash"
elif check_cmd osascript; then
    osascript -e "tell application \"Terminal\" to do script \"cd $ROOT && bash scripts/start-backend.sh $MODE\""
    osascript -e "tell application \"Terminal\" to do script \"cd $ROOT && bash scripts/start-web.sh $MODE\""
else
    # Fallback: background processes (logs to files)
    mkdir -p "$ROOT/logs"
    bash "$SCRIPT_DIR/start-backend.sh" "$MODE" >"$ROOT/logs/backend.out" 2>&1 &
    bash "$SCRIPT_DIR/start-web.sh" "$MODE"     >"$ROOT/logs/web.out" 2>&1 &
fi

sleep 1
echo ""
echo "  =================================================="
echo -e "  ${GREEN}[READY]${NC} Services launched!"
echo ""
echo "    Ports from config.yml [mode=$MODE]"
echo "    Close each terminal to stop its service."
echo "  =================================================="
echo ""
