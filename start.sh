#!/usr/bin/env bash
# ============================================
#  RAG Knowledge Platform - Unified Launcher
#  Usage: ./start.sh [dev|prod]
#    dev  = Backend (uvicorn --reload) + Frontend (vite dev)   [default]
#    prod = Backend (uvicorn) + Frontend (build if needed + vite preview)
# ============================================

set -e

MODE="${1:-dev}"
[[ "$MODE" == "d" ]] && MODE="dev"
[[ "$MODE" == "p" ]] && MODE="prod"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}  [INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}  [OK]${NC} $*"; }
err()  { echo -e "${RED}  [ERROR]${NC} $*"; exit 1; }

echo ""
echo "  ============================================"
echo "   RAG Knowledge Platform - Mode: $MODE"
echo "  ============================================"
echo ""

# ---- Resolve project root (directory of this script) ----
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"

# ---- Load .env ----
ENV_FILE="$ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    err ".env file not found at $ENV_FILE. Copy .env.example to .env and configure."
fi

set -a
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue
    export "$key=$value"
done < "$ENV_FILE"
set +a

# Set defaults
export BACKEND_PORT="${BACKEND_PORT:-8001}"
export FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export FRONTEND_PREVIEW_PORT="${FRONTEND_PREVIEW_PORT:-4173}"
export VITE_API_BASE="${VITE_API_BASE:-http://localhost:$BACKEND_PORT}"

echo "  [CONFIG] BACKEND_PORT=$BACKEND_PORT"
echo "  [CONFIG] FRONTEND_PORT=$FRONTEND_PORT"
echo "  [CONFIG] VITE_API_BASE=$VITE_API_BASE"
echo ""

# ---- Check prerequisites ----
command -v uv >/dev/null 2>&1   || err "uv not found. Install: https://docs.astral.sh/uv/"
command -v node >/dev/null 2>&1 || err "node not found. Install Node.js 18+"

[ -d "$BACKEND_DIR/app" ]  || err "Backend not found at $BACKEND_DIR. Run: git submodule update --init --recursive"
[ -f "$FRONTEND_DIR/package.json" ] || err "Frontend not found at $FRONTEND_DIR. Run: git submodule update --init --recursive"

# ---- Install frontend deps if needed ----
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log "Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm install)
fi

# ---- Cleanup function ----
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    log "Shutting down..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    ok "All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ---- Start Backend ----
log "Starting backend on http://localhost:$BACKEND_PORT"
(cd "$BACKEND_DIR" && uv run python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload) &
BACKEND_PID=$!

# Wait for backend (max 20s)
log "Waiting for backend..."
for i in $(seq 1 20); do
    if curl -s "http://localhost:$BACKEND_PORT/api/v1/health" >/dev/null 2>&1; then
        ok "Backend ready!"
        break
    fi
    sleep 1
done

# ---- Start Frontend ----
cd "$FRONTEND_DIR"
if [ "$MODE" = "prod" ]; then
    if [ ! -f "dist/index.html" ]; then
        log "Building production bundle..."
        VITE_API_BASE="$VITE_API_BASE" npm run build
        ok "Build complete!"
    else
        log "dist/ already exists, skipping build."
    fi
    log "Starting preview on http://localhost:$FRONTEND_PREVIEW_PORT"
    npm run preview -- --port "$FRONTEND_PREVIEW_PORT" &
    FRONTEND_PID=$!
else
    log "Starting dev server on http://localhost:$FRONTEND_PORT"
    VITE_API_BASE="$VITE_API_BASE" npm run dev -- --port "$FRONTEND_PORT" &
    FRONTEND_PID=$!
fi
cd "$ROOT"

echo ""
echo "  ============================================"
echo "  [READY] Services running!"
if [ "$MODE" = "prod" ]; then
    echo "    Frontend: http://localhost:$FRONTEND_PREVIEW_PORT"
else
    echo "    Frontend: http://localhost:$FRONTEND_PORT"
fi
echo "    Backend:  http://localhost:$BACKEND_PORT"
echo "    API Docs: http://localhost:$BACKEND_PORT/docs"
echo "  ============================================"
echo ""
echo "  Press Ctrl+C to stop all services."
echo ""

# Wait for processes
wait
