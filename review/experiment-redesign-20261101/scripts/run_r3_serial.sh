#!/usr/bin/env bash
# R3 复现轮串行链（A2 → A1b → floor → A3 清场+重建+消融 → A1-readall）
# 在调用组1（A0/A0f/A0h/PD）完成后启动。stdio + skip-done 断点可续。
set -u
ROOT="D:/codes/ClaudeGPT/rag_project/rag-knowledge"
EXP="$ROOT/review/experiment-redesign-20261101"
OUT="$EXP/artifacts/replication_bench_20261112"
LOGS="$EXP/logs"
S4="$EXP/scripts/s4_run_ablation.py"
Q="$EXP/artifacts/questions.jsonl"
TS() { date +%H:%M:%S; }

backend_dead() {
  curl -s -m 5 -o /dev/null http://127.0.0.1:8771/api/v1/health
  local rc=$?
  [ $rc -ne 0 ] && [ $rc -ne 28 ]
}
ensure_backend() {
  if backend_dead; then
    echo "[$(TS)] backend dead -> healing (venv)"
    powershell -NoProfile -ExecutionPolicy Bypass -File "$TEMP/purge_orphan.ps1" >/dev/null 2>&1
    sleep 3
    (cd "$ROOT/backend" && ./.venv/Scripts/python.exe main.py > "$TEMP/backend_r3_serial.log" 2>&1 &)
    sleep 25
  fi
}

echo "[$(TS)] STEP-1 A2 (fast, no judge, no capture)"
ensure_backend
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --questions "$Q" --arms "A2" --skip-done --out "$OUT" > "$LOGS/r3_A2.log" 2>&1
echo "[$(TS)] STEP-1 rc=$?"

echo "[$(TS)] STEP-2 A1b"
ensure_backend
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --questions "$Q" --arms "A1b" --skip-done --out "$OUT" > "$LOGS/r3_A1b.log" 2>&1
echo "[$(TS)] STEP-2 rc=$?"

echo "[$(TS)] STEP-3 floor"
ensure_backend
python -X utf8 "$EXP/scripts/s5_floor.py" > "$LOGS/r3_floor.log" 2>&1
rc=$?
if [ -f "$EXP/artifacts/s5_floor.json" ]; then
  cp "$EXP/artifacts/s5_floor.json" "$OUT/s5_floor_r3.json"
fi
echo "[$(TS)] STEP-3 rc=$rc"

echo "[$(TS)] STEP-4 purge stale A3 twins"
ensure_backend
python -X utf8 "$EXP/scripts/s9b2_purge_a3_twins.py" > "$LOGS/r3_purge_twins.log" 2>&1
echo "[$(TS)] STEP-4 rc=$?"

echo "[$(TS)] STEP-5 prepare-a3 (rebuild 10 stripped twins)"
ensure_backend
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --prepare-a3 > "$LOGS/r3_A3prep.log" 2>&1
echo "[$(TS)] STEP-5 rc=$?"

echo "[$(TS)] STEP-6 A3 arm (name-only route cards)"
ensure_backend
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --questions "$Q" --arms "A3" --skip-done --out "$OUT" > "$LOGS/r3_A3.log" 2>&1
echo "[$(TS)] STEP-6 rc=$?"

echo "[$(TS)] STEP-7 A1-readall (long)"
ensure_backend
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --questions "$Q" --arms "A1-readall" --skip-done --out "$OUT" > "$LOGS/r3_readall.log" 2>&1
echo "[$(TS)] STEP-7 rc=$?"

touch "$OUT/.r3_serial_done"
echo "[$(TS)] R3-SERIAL-DONE"
