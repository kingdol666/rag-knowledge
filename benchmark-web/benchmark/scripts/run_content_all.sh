#!/usr/bin/env bash
# 内容级基准一键编排: 构建 → 双轮运行 → 复现比对 → HTML 报告
# 前置: 后端/前端已启动, RAG_BENCH_TOKEN 已导出, 语料入库已完成
set -euo pipefail
cd "$(dirname "$0")"

: "${RAG_BENCH_TOKEN:?export RAG_BENCH_TOKEN=mcp-xxx}"
export RAG_BENCH_URL="${RAG_BENCH_URL:-http://localhost:8771}"
export RAG_BENCH_WEB_URL="${RAG_BENCH_WEB_URL:-http://localhost:6790}"

LIMIT="${LIMIT:-300}"            # 公开集每集抽样上限
PER_KB="${PER_KB:-40}"           # 自建集每域条数
ROUTING_PER_KB="${ROUTING_PER_KB:-15}"

echo "== 1/5 构建语料级 QA 集 (per-KB=$PER_KB) =="
python build_content_qa.py --per-kb "$PER_KB"

echo "== 2/5 Track C 双轮 =="
for r in 1 2; do
  python run_content_qa_driver.py --datasets contentqa --methods two_stage,vector_flat \
    --limit 0 --round "$r"
  python run_content_qa_driver.py --datasets hotpotqa,triviaqa,nq --methods two_stage,vector_flat \
    --limit "$LIMIT" --round "$r"
done

echo "== 3/5 Track C 复现比对 =="
python run_content_qa.py --compare contentqa || true

echo "== 4/5 Track R 入库归类双轮 =="
python run_ingest_routing.py --per-kb "$ROUTING_PER_KB" --round 1
python run_ingest_routing.py --per-kb "$ROUTING_PER_KB" --round 2 --skip-ingest

echo "== 5/5 报告 =="
python make_content_html.py
echo DONE
