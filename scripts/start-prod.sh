#!/usr/bin/env bash
# ============================================================
# RAG Knowledge Platform — Production Launcher (Linux / macOS)
#
# Background-mode launcher with PID tracking and log redirection.
# Use with systemd, supervisor, or manual daemon management.
#
# Usage:  ./scripts/start-prod.sh
# Stops:  ./scripts/stop.sh
# Status: cat logs/backend.out | tail -20
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT/storage/pids"
LOG_DIR="$ROOT/logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

# ── Helper ─────────────────────────────────────────────────
is_running() {
  local pidfile="$1"
  local pid
  [[ -f "$pidfile" ]] || return 1
  pid="$(cat "$pidfile")"
  kill -0 "$pid" 2>/dev/null
}

# ── Check already running ─────────────────────────────────
if is_running "$PID_DIR/backend.pid"; then
  echo "[WARN] Backend already running (PID $(cat $PID_DIR/backend.pid))"
  exit 1
fi
if is_running "$PID_DIR/web.pid"; then
  echo "[WARN] Web already running (PID $(cat $PID_DIR/web.pid))"
  exit 1
fi

# ── Load .env if exists ───────────────────────────────────
if [ -f "$ROOT/.env" ]; then
  set -a; source "$ROOT/.env"; set +a
fi

export APP_MODE="${APP_MODE:-prod}"

echo "Starting RAG Knowledge Platform in PROD mode..."
echo "  Logs: $LOG_DIR/"

# ── Backend ────────────────────────────────────────────────
echo "  [1/2] Backend..."
cd "$ROOT/backend"
uv run python main.py >> "$LOG_DIR/backend.out" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_DIR/backend.pid"
echo "         PID: $BACKEND_PID"

# ── Web (Nuxt) ─────────────────────────────────────────────
echo "  [2/2] Web (Nuxt)..."
cd "$ROOT/web"
node start.mjs >> "$LOG_DIR/web.out" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" > "$PID_DIR/web.pid"
echo "         PID: $WEB_PID"

sleep 2

# ── Verify ─────────────────────────────────────────────────
FAIL=0
if ! is_running "$PID_DIR/backend.pid"; then
  echo "  [ERROR] Backend failed to start — see $LOG_DIR/backend.out"
  FAIL=1
fi
if ! is_running "$PID_DIR/web.pid"; then
  echo "  [ERROR] Web failed to start — see $LOG_DIR/web.out"
  FAIL=1
fi

if [ $FAIL -eq 0 ]; then
  echo ""
  echo "  =================================================="
  echo "  [READY] Services running (PID files in $PID_DIR)"
  echo ""
  echo "    Backend: $(cat $PID_DIR/backend.pid)"
  echo "    Web:     $(cat $PID_DIR/web.pid)"
  echo ""
  echo "  Stop with:  ./scripts/stop.sh"
  echo "  =================================================="
else
  exit 1
fi