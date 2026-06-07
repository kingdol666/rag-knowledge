#!/usr/bin/env bash
# RAG Knowledge - Frontend (Vue+Vite) Launcher
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[ -f "$ENV_FILE" ] || { echo "[ERROR] .env not found"; exit 1; }
set -a; while IFS='=' read -r k v; do [[ "$k" =~ ^#.*$ ]] || [[ -z "$k" ]] && continue; export "$k=$v"; done < "$ENV_FILE"; set +a
export FRONTEND_PORT="${FRONTEND_PORT:-3008}"
export VITE_API_BASE="${VITE_API_BASE:-http://localhost:${BACKEND_PORT:-8001}}"
echo ""
echo "  [Frontend] http://localhost:$FRONTEND_PORT"
echo "  [Proxy]    /api -> $VITE_API_BASE"
echo ""
cd "$ROOT/frontend"
VITE_API_BASE="$VITE_API_BASE" npm run dev -- --port "$FRONTEND_PORT"
