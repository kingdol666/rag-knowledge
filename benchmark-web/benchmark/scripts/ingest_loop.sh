#!/usr/bin/env bash
# 多轮入库收敛: 阵发索引器静默窗口快速失败+续跑, 直到 5 库 checkpoint 齐
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BENCH_DIR"
export RAG_BENCH_TOKEN=$(grep MCP_AUTH_TOKEN ../../.env | cut -d= -f2)
export RAG_BENCH_URL=http://localhost:8771 RAG_BENCH_WEB_URL=http://localhost:6790
KBS="KB-People,KB-Politics-History,KB-Science-Tech,KB-Sports,KB-Transport"
for pass in 1 2 3 4 5 6 7 8 9 10; do
  echo "===== PASS $pass $(date +%H:%M:%S) ====="
  python -u scripts/ingest_corpus.py --kbs "$KBS" >> results/ingest-loop.log 2>&1 && echo "pass $pass clean exit"
  done_all=$(python scripts/check_ingest_done.py)
  echo "pass $pass complete-check: $done_all"
  [ "$done_all" = "YES" ] && echo ALL_INGESTED && exit 0
  sleep 180
done
echo MAX_PASSES_EXHAUSTED
exit 1
