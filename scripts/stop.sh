#!/usr/bin/env bash
# ============================================================
# RAG Knowledge Platform — Graceful Stop (Linux / macOS)
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT/storage/pids"

stop_one() {
  local name="$1"
  local pidfile="$PID_DIR/$name.pid"
  local pid

  if [ ! -f "$pidfile" ]; then
    echo "  [SKIP] $name — no PID file"
    return 0
  fi
  pid="$(cat "$pidfile")"

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "  [SKIP] $name — PID $pid not running (stale PID file)"
    rm -f "$pidfile"
    return 0
  fi

  echo "  Stopping $name (PID $pid)..."
  kill "$pid" 2>/dev/null || true

  # Wait up to 10s for graceful exit
  for i in $(seq 1 10); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "  [OK] $name stopped"
      rm -f "$pidfile"
      return 0
    fi
    sleep 1
  done

  # Force kill if still running
  echo "  [WARN] $name didn't stop gracefully — force killing"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pidfile"
}

echo "Stopping RAG Knowledge Platform..."
stop_one "web"
stop_one "backend"
echo "All services stopped."