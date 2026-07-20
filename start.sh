#!/usr/bin/env bash
# ============================================================
# RAG Knowledge Platform — Unified Launcher (Linux / macOS)
#
# Usage:  ./start.sh [dev|prod]
#   Silently launches Backend (FastAPI) + Web (Nuxt 3) — NO terminals.
#   Ports are read from config.yml (single source of truth).
#   Logs → backend/logs/desktop-stdout.log + web/logs/desktop-stdout.log
#   (same files the Tauri desktop console + `ragctl logs` read)
# ============================================================
set -euo pipefail

MODE="${1:-${APP_MODE:-dev}}"
[[ "$MODE" == "d" ]] && MODE="dev"
[[ "$MODE" == "p" ]] && MODE="prod"

ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMAND_DIR="$ROOT/command"

# ── Colors ──────────────────────────────────────────────────
if [[ -t 1 ]]; then
    CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
else
    CYAN=''; GREEN=''; YELLOW=''; RED=''; NC=''
fi

echo ""
echo -e "  💡 Tip: Use './ragctl setup' for first-time one-click deployment"
echo -e "  💡 Tip: Use './ragctl up' to start all services (silent, no terminals)"
echo -e "  💡 Tip: Use './ragctl logs [backend|web]' to view logs"
echo ""

# Try ragctl up first (silent launcher — no terminal windows, dev AND prod)
if node "$COMMAND_DIR/ragctl.js" up --mode "$MODE" 2>/dev/null; then
    exit 0
fi

# ── Fallback: SILENT direct launch ────────────────────────────
echo -e "  ${YELLOW}[WARN]${NC} ragctl up failed — using fallback silent launch..."
echo ""

# Check prerequisites
check_cmd() { command -v "$1" >/dev/null 2>&1; }
missing=0
if ! check_cmd uv; then echo -e "  ${RED}[ERROR]${NC} 'uv' not found";  missing=1; fi
if ! check_cmd node; then echo -e "  ${RED}[ERROR]${NC} 'node' not found"; missing=1; fi
[[ $missing -ne 0 ]] && exit 1

# Project integrity check
[ -d "$ROOT/backend/app" ] || { echo -e "  ${RED}[ERROR]${NC} Backend not found. Run: ragctl setup"; exit 1; }
[ -f "$ROOT/web/package.json" ] || { echo -e "  ${RED}[ERROR]${NC} Web not found. Run: ragctl setup"; exit 1; }

# Install web deps if needed
[ -d "$ROOT/web/node_modules" ] || { echo "  Installing web deps..."; (cd "$ROOT/web" && npm install); }

# Prepare log directories (shared with Tauri + ragctl)
mkdir -p "$ROOT/backend/logs" "$ROOT/web/logs"

# Neo4j check (optional)
if check_cmd docker; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q rag-knowledge-neo4j; then
        echo -e "  ${GREEN}[INFO]${NC} Neo4j container detected (graph features available)"
    else
        echo -e "  ${YELLOW}[INFO]${NC} Neo4j not running — graph features degraded"
    fi
fi
echo ""

# Launch silently — background, fully detached, output → shared log files.
# `> file 2>&1` captures stdout+stderr; `&` detaches; `disown` (bash) detaches from shell.
echo -e "  ${CYAN}Starting Backend (silent)...${NC}  log: backend/logs/desktop-stdout.log"
( cd "$ROOT/backend" && APP_MODE="$MODE" PYTHONUNBUFFERED=1 PYTHONUTF8=1 nohup uv run python main.py \
    > "$ROOT/backend/logs/desktop-stdout.log" 2>&1 & ) 2>/dev/null

echo -e "  ${CYAN}Starting Web (silent)...${NC}  log: web/logs/desktop-stdout.log"
( cd "$ROOT/web" && APP_MODE="$MODE" NODE_OPTIONS="--no-deprecation" nohup node start.mjs \
    > "$ROOT/web/logs/desktop-stdout.log" 2>&1 & ) 2>/dev/null

sleep 1
echo ""
echo "  =================================================="
echo -e "  ${GREEN}[READY]${NC} Services launched silently (no terminals)."
echo "    Logs:  ./ragctl logs backend  |  ./ragctl logs web"
echo "    Or open the Tauri desktop console."
echo "  =================================================="
echo ""
