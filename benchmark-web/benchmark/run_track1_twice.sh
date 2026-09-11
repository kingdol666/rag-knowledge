#!/usr/bin/env bash
# ============================================================================
# Track 1 可复现性双轮评测 — CIKM 锚点集 (hotpotqa / 2wiki)
# 按 BENCHMARK-EXECUTION-PLAN.md Step 4: 5 方法 × 锚点数据集, 跑两轮取一致率。
# 前置: 语料已入库 (results/corpus-ingest-report.json 全 OK)
# 用法:
#   export RAG_BENCH_TOKEN=... RAG_BENCH_URL=http://127.0.0.1:8771 RAG_BENCH_WEB_URL=...
#   bash run_track1_twice.sh [LIMIT]   # LIMIT 默认 200 (锚点集足够出统计信号)
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

LIMIT="${1:-200}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/repro"
mkdir -p "$OUT"

for ROUND in 1 2; do
  echo "=== Track 1 round $ROUND (limit=$LIMIT) ==="
  for ds in hotpotqa 2wiki; do
    python scripts/run_eval.py --dataset "$ds" --methods all --limit "$LIMIT"
    # run_eval 文件名内嵌方法列表 → 取该数据集最新的结果快照
    NEWEST=$(ls -t results/eval-"${ds}"-*.json | head -1)
    cp "$NEWEST" "${OUT}/track1-${ds}-run${ROUND}.json"
  done
done

echo "=== reproducibility verdicts ==="
for ds in hotpotqa 2wiki; do
  python scripts/compare_repro.py "${OUT}/track1-${ds}-run1.json" "${OUT}/track1-${ds}-run2.json" || true
done
echo "done: snapshots in ${OUT}/"
