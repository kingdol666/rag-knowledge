#!/usr/bin/env bash
# v4 serial — remaining arms via stdio transport (no shared 8000 port), one pass.
set -u
ROOT="D:/codes/ClaudeGPT/rag_project/rag-knowledge"
EXP="$ROOT/review/experiment-redesign-20261101"
LOGS="$EXP/logs"
S4="$EXP/scripts/s4_run_ablation.py"
Q="$EXP/artifacts/questions.jsonl"
TS() { date +%H:%M:%S; }

echo "[$(TS)] STEP-A A2 (fast, no judge)"
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --questions "$Q" --arms "A2" --skip-done > "$LOGS/v4_A2.log" 2>&1
echo "[$(TS)] STEP-A rc=$?"

echo "[$(TS)] STEP-B A1b"
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --questions "$Q" --arms "A1b" --skip-done > "$LOGS/v4_A1b.log" 2>&1
echo "[$(TS)] STEP-B rc=$?"

echo "[$(TS)] STEP-C A3"
uv run --no-sync --directory "$ROOT/kb-mcp" python "$S4" --questions "$Q" --arms "A3" --skip-done > "$LOGS/v4_A3.log" 2>&1
echo "[$(TS)] STEP-C rc=$?"

echo "V4-DONE"
