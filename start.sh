#!/usr/bin/env bash
# ============================================================
# RAG Knowledge Platform — Unified Launcher (Linux / macOS)
#
# Usage:  ./start.sh [dev|prod]
#   Launches Backend (FastAPI) + Web (Nuxt 3).
#   Ports are read from config.yml (single source of truth).
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
echo -e "  💡 Tip: Use './ragctl up' to start all services"
echo -e "  💡 Tip: Use './ragctl check' to audit your environment"
echo ""

# Try ragctl up first
if node "$COMMAND_DIR/ragctl.js" up --mode "$MODE" 2>/dev/null; then
    exit 0
fi

# ── Fallback: direct launch ──────────────────────────────────
echo -e "  ${YELLOW}[WARN]${NC} ragctl up failed — using fallback direct launch..."
echo ""

# Check prerequisites
check_cmd() { command -v "$1" >/dev/null 2>&1; }
missing=0
if ! check_cmd uv; then echo -e "  ${RED}[ERROR]${NC} 'uv' not found";  missing=1; fi
if ! check_cmd node; then echo -e "  ${RED}[ERROR]${NC} 'node' not found"; missing=1; fi
[[ $missing -ne 0 ]] && exit 1

# Submodule check
[ -d "$ROOT/backend/app" ] || { echo -e "  ${RED}[ERROR]${NC} Backend submodule not found. Run: git submodule update --init --recursive"; exit 1; }
[ -f "$ROOT/web/package.json" ] || { echo -e "  ${RED}[ERROR]${NC} Web submodule not found. Run: git submodule update --init --recursive"; exit 1; }

# Install web deps if needed
[ -d "$ROOT/web/node_modules" ] || { echo "  Installing web deps..."; (cd "$ROOT/web" && npm install); }

# Neo4j check (optional)
if check_cmd docker; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q rag-knowledge-neo4j; then
        echo -e "  ${GREEN}[INFO]${NC} Neo4j container detected (graph features available)"
    else
        echo -e "  ${YELLOW}[INFO]${NC} Neo4j not running — graph features degraded"
    fi
fi
echo ""

# Launch
echo -e "  ${CYAN}Starting Backend...${NC}"
(cd "$ROOT/backend" && uv run python main.py) &

echo -e "  ${CYAN}Starting Web...${NC}"
(cd "$ROOT/web" && node start.mjs) &

sleep 1
echo ""
echo "  =================================================="
echo -e "  ${GREEN}[READY]${NC} Services launched!"
echo "    Ports from config.yml [mode=$MODE]"
echo "  =================================================="
echo ""
