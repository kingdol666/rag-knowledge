#!/usr/bin/env bash
# ============================================
#  RAG Knowledge Platform - Unified Launcher
#  Usage: ./start.sh [dev|prod]
#    Each service starts in its own terminal.
# ============================================

set -e

MODE="${1:-dev}"
[[ "$MODE" == "d" ]] && MODE="dev"
[[ "$MODE" == "p" ]] && MODE="prod"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "  ============================================"
echo "   RAG Knowledge Platform - Mode: $MODE"
echo "  ============================================"
echo ""

ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "[ERROR] .env not found. Copy .env.example to .env"
    exit 1
fi

# Load .env
set -a
while IFS='=' read -r k v; do [[ "$k" =~ ^#.*$ ]] || [[ -z "$k" ]] && continue; export "$k=$v"; done < "$ENV_FILE"
set +a

export BACKEND_PORT="${BACKEND_PORT:-8001}"
export FRONTEND_PORT="${FRONTEND_PORT:-3008}"
export WEB_PORT="${WEB_PORT:-3009}"

echo -e "  ${CYAN}[CONFIG]${NC} BACKEND_PORT=$BACKEND_PORT"
echo -e "  ${CYAN}[CONFIG]${NC} FRONTEND_PORT=$FRONTEND_PORT"
echo -e "  ${CYAN}[CONFIG]${NC} WEB_PORT=$WEB_PORT"
echo ""

# Install deps if needed
[ -d "$ROOT/frontend/node_modules" ] || (echo "Installing frontend deps..." && cd "$ROOT/frontend" && npm install)
[ -d "$ROOT/web/node_modules" ] || (echo "Installing web deps..." && cd "$ROOT/web" && npm install)

# Launch each in a new terminal
SCRIPT_DIR="$ROOT"

if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="RAG-Backend" -- bash -c "$SCRIPT_DIR/start-backend.sh; exec bash"
    gnome-terminal --title="RAG-Frontend" -- bash -c "$SCRIPT_DIR/start-frontend.sh; exec bash"
    gnome-terminal --title="RAG-Web" -- bash -c "$SCRIPT_DIR/start-web.sh; exec bash"
elif command -v osascript >/dev/null 2>&1; then
    osascript -e "tell application \"Terminal\" to do script \"cd $ROOT && bash start-backend.sh\""
    osascript -e "tell application \"Terminal\" to do script \"cd $ROOT && bash start-frontend.sh\""
    osascript -e "tell application \"Terminal\" to do script \"cd $ROOT && bash start-web.sh\""
else
    echo "[WARN] No terminal launcher found. Running in background..."
    bash "$SCRIPT_DIR/start-backend.sh" &
    bash "$SCRIPT_DIR/start-frontend.sh" &
    bash "$SCRIPT_DIR/start-web.sh" &
fi

sleep 1
echo ""
echo "  ============================================"
echo -e "  ${GREEN}[READY]${NC} 3 terminals launched!"
echo ""
echo "    Backend (API):   http://localhost:$BACKEND_PORT"
echo "    API Docs:        http://localhost:$BACKEND_PORT/docs"
echo "    Frontend (Vue):  http://localhost:$FRONTEND_PORT"
echo "    Web (Nuxt):      http://localhost:$WEB_PORT"
echo ""
echo "    Close each terminal to stop."
echo "  ============================================"
echo ""
