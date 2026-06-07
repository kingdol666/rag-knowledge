#!/usr/bin/env bash
# RAG Knowledge - Web (Nuxt 3) Launcher
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[ -f "$ENV_FILE" ] || { echo "[ERROR] .env not found"; exit 1; }
set -a; while IFS='=' read -r k v; do [[ "$k" =~ ^#.*$ ]] || [[ -z "$k" ]] && continue; export "$k=$v"; done < "$ENV_FILE"; set +a
export WEB_PORT="${WEB_PORT:-3009}"
export PDF_PARSER_API_URL="${PDF_PARSER_API_URL:-http://localhost:${BACKEND_PORT:-8001}}"
export DEEPAGENT_API_URL="${DEEPAGENT_API_URL:-http://localhost:${BACKEND_PORT:-8001}}"
echo ""
echo "  [Web]  http://localhost:$WEB_PORT"
echo "  [API]  $PDF_PARSER_API_URL"
echo ""
cd "$ROOT/web"
NUXT_PUBLIC_API_BASE="${NUXT_PUBLIC_API_BASE:-}" \
PDF_PARSER_API_URL="$PDF_PARSER_API_URL" \
DEEPAGENT_API_URL="$DEEPAGENT_API_URL" \
npx nuxt dev --host 0.0.0.0 --port "$WEB_PORT"
