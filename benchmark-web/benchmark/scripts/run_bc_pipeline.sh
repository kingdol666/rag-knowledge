#!/usr/bin/env bash
# B/C 段流水线(eval 修复后): B MCP 三语×2 → Agent 三语 → C 冥想×2
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BENCH_DIR"
export RAG_BENCH_TOKEN=$(grep MCP_AUTH_TOKEN ../../.env | cut -d= -f2)
export RAG_BENCH_URL=http://localhost:8771 RAG_BENCH_WEB_URL=http://localhost:6790

echo "== 4/6 模块 B MCP 管线 三语 双轮(eval 修复版) =="
for lang in en zh ja; do
  python scripts/benchmark_content_mcp.py --lang $lang --round 1
  python scripts/benchmark_content_mcp.py --lang $lang --round 2
done

echo "== 5/6 模块 B Agent 真链路 =="
python scripts/benchmark_content_agent.py --lang zh --n-queries 3 --runs 2 --timeout 480
python scripts/benchmark_content_agent.py --lang ja --n-queries 3 --runs 2 --timeout 480
python scripts/benchmark_content_agent.py --lang en --n-queries 3 --runs 2 --timeout 480

echo "== 6/6 模块 C 冥想 双轮 =="
python scripts/benchmark_meditation.py --kbs KB-CrossLang-EN,KB-CrossLang-ZH --harness omp --round 1
python scripts/benchmark_meditation.py --kbs KB-CrossLang-EN,KB-CrossLang-ZH --harness omp --round 2

echo ALL_DONE
