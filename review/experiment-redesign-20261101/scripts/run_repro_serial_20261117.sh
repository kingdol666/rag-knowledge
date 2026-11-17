#!/usr/bin/env bash
# Serial driver for the 2026-11-17 reproducibility rerun (arms after A0).
# Arms are strictly serial: the s4_checkpoint.jsonl in the --out dir is shared.
set -u
ROOT="D:/codes/ClaudeGPT/rag_project/rag-knowledge"
EXP="$ROOT/review/experiment-redesign-20261101"
OUT="$EXP/artifacts/repro_20261117"
QS="$EXP/artifacts/provenance/questions.jsonl"
LOGDIR="$TEMP"
TS() { date +%H:%M:%S; }

run_arm() {
  local arm="$1"; shift || true
  echo "[$(TS)] === arm $arm start ==="
  uv run --no-sync --directory "$ROOT/kb-mcp" python "$EXP/scripts/s4_run_ablation.py" \
    --questions "$QS" --arms "$arm" --skip-done --out "$OUT" "$@" \
    > "$LOGDIR/s4_${arm}.log" 2>&1
  local rc=$?
  echo "[$(TS)] === arm $arm rc=$rc ==="
  tail -3 "$LOGDIR/s4_${arm}.log" | cut -c1-160
  return $rc
}

run_arm A0f
run_arm A0h
run_arm PD
run_arm A1b
run_arm A2
# NOTE (2026-11-17): on this stack --prepare-a3 hung rebuilding the twin
# libraries from scratch (same fingerprint as R3 attempt1_aborted). The
# successful A3 rerun reused the existing twins WITHOUT this flag:
#   s4_run_ablation.py --arms A3 --skip-done --out "$OUT"
run_arm A3 --prepare-a3
echo "[$(TS)] === all 7 arms dispatched; readall decision pending ==="
wc -l "$OUT/s4_checkpoint.jsonl"
