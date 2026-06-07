#!/usr/bin/env bash
# RAG Knowledge - Backend Launcher
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT/.env"
[ -f "$ENV_FILE" ] || { echo "[ERROR] .env not found"; exit 1; }
set -a; while IFS='=' read -r k v; do [[ "$k" =~ ^#.*$ ]] || [[ -z "$k" ]] && continue; export "$k=$v"; done < "$ENV_FILE"; set +a
export BACKEND_PORT="${BACKEND_PORT:-8001}"
echo ""
echo "  [Backend] http://localhost:$BACKEND_PORT"
echo "  [Docs]    http://localhost:$BACKEND_PORT/docs"
echo ""
cd "$ROOT/backend"
BACKEND_PORT="$BACKEND_PORT" uv run python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload
