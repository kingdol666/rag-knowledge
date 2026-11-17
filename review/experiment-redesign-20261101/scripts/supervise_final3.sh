#!/usr/bin/env bash
# Supervisor v3 — correct SSE liveness semantics:
#   curl exit 7  (connection refused)  = process dead
#   curl exit 28 (timeout, stream open)= ALIVE (SSE streams never end)
# In-step healing: kill hung step tree only on REAL death, restart, re-enter (skip-done resumes).
set -u
ROOT="D:/codes/ClaudeGPT/rag_project/rag-knowledge"
EXP="$ROOT/review/experiment-redesign-20261101"
MARKER="$EXP/artifacts/.final_serial_done"
TS() { date +%H:%M:%S; }

# returns 0 (true) when service is DEAD
backend_dead() {
  curl -s -m 5 -o /dev/null http://127.0.0.1:8771/api/v1/health
  local rc=$?
  [ $rc -ne 0 ] && [ $rc -ne 28 ]
}
kbmcp_dead() {
  curl -s -m 6 -o /dev/null http://127.0.0.1:8000/sse
  local rc=$?
  [ $rc -ne 0 ] && [ $rc -ne 28 ]
}

ensure_backend() {
  if backend_dead; then
    echo "[$(TS)] backend dead (real) -> restarting"
    powershell -NoProfile -Command "\$c = Get-NetTCPConnection -LocalPort 8771 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if (\$c) { Stop-Process -Id \$c.OwningProcess -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
    sleep 2
    (cd "$ROOT/backend" && ./.venv/Scripts/python.exe main.py > "$TEMP/backend_sup.log" 2>&1 &)
    sleep 20
  fi
}

ensure_kbmcp() {
  if kbmcp_dead; then
    echo "[$(TS)] kb-mcp dead (real) -> restarting"
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -match 'kb-mcp' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
    sleep 2
    (cd "$ROOT" && uv run --no-sync --directory "$ROOT/kb-mcp" python "$ROOT/kb-mcp/server.py" --http > "$TEMP/kbmcp_sup.log" 2>&1 &)
    sleep 15
  fi
}

kill_serial_tree() {
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -match 's4_run_ablation|s_agent_sample|s5_floor' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  pkill -f "run_final_serial_v2.sh" 2>/dev/null
  sleep 2
}

for round in $(seq 1 30); do
  echo "[$(TS)] === supervisor round $round ==="
  if [ -f "$MARKER" ]; then echo "[$(TS)] marker present — done"; break; fi
  ensure_backend
  ensure_kbmcp
  bash "$EXP/scripts/run_final_serial_v2.sh" &
  SERPID=$!
  while kill -0 "$SERPID" 2>/dev/null; do
    sleep 25
    if kbmcp_dead || backend_dead; then
      echo "[$(TS)] IN-STEP real service death detected -> healing"
      kill_serial_tree
      ensure_backend
      ensure_kbmcp
      break
    fi
  done
  wait "$SERPID" 2>/dev/null
  if [ -f "$MARKER" ]; then echo "[$(TS)] marker present — done"; break; fi
  echo "[$(TS)] round $round ended without marker; cooling 30s"
  sleep 30
done
echo "[$(TS)] supervisor exit"
