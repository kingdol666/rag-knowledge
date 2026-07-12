#!/usr/bin/env bash
# 启动前端：cd web → 设 APP_MODE → npm run dev|start
set -euo pipefail

MODE="${1:-${APP_MODE:-dev}}"
[[ "$MODE" == "d" ]] && MODE="dev"
[[ "$MODE" == "p" ]] && MODE="prod"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT/web"
export APP_MODE="$MODE"

echo "[start-web] mode=$MODE  dir=$ROOT/web"
if [[ "$MODE" == "prod" ]]; then
    exec npm run start
else
    exec npm run dev
fi
