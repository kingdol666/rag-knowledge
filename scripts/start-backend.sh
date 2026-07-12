#!/usr/bin/env bash
# 启动后端：cd backend → 设 APP_MODE → uv run python main.py
# Usage: scripts/start-backend.sh [dev|prod]
set -euo pipefail

MODE="${1:-${APP_MODE:-dev}}"
[[ "$MODE" == "d" ]] && MODE="dev"
[[ "$MODE" == "p" ]] && MODE="prod"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT/backend"
export APP_MODE="$MODE"

echo "[start-backend] mode=$MODE  dir=$ROOT/backend"
exec uv run python main.py
