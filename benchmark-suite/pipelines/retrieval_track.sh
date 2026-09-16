#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
# Track R — 检索算法对比轨
# 只回答一个问题: \sys{} 的检索与其他算法(bm25/dense/rerank/RAPTOR/ITRG/
# Search-o1/DeepRead)比, 排序与答案质量如何。
# 与 functions_track.sh 完全独立, 可单独运行与复现。
# 用法: bash pipelines/retrieval_track.sh > results/track-R.log 2>&1
# ══════════════════════════════════════════════════════════════════════
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
# R3 的 60_hotpot_build 走 web 层建库/建文档; web 实际端口 6789(6790 是死代理,
# 陷阱⑲) — 不导出时 R3 全通道静默归零(URLError 被吞, 已实测发生)
export RAG_BENCH_WEB_URL=http://localhost:6789
say() { echo "=== $(date +%H:%M:%S) $* ==="; }

say "R- 预检 (健康/token/omp/Hotpot 九库空态; fail-loud, 不删数据)"
python scripts/00_preflight.py R || { echo "预检未通过 — 中止 (处置指引见上)"; exit 1; }


say "R0 标准语料入库 (SciFact/SQuAD, 已存在则跳过式覆盖)"
python scripts/21_std2_ingest.py 2 2>&1 | tail -2

say "R1 套件四通道检索 (BM25/Two-stage/Dense/QDCVR)"
python scripts/22_std2_retrieval.py 2 2>&1 | tail -6
say "R1b 双语内部语料四通道"
python scripts/02_retrieval.py 2 2>&1 | tail -2

say "R2 E1 组件消融 + E2 显著性"
python scripts/30_ablation.py 2 2>&1 | tail -4
python scripts/31_stats.py 2>&1 | tail -3

say "R3 E8 多域 HotpotQA + E13 oracle + E14 分层"
python scripts/60_hotpot_build.py 2>&1 | tail -2
python scripts/61_hotpot_eval.py 2>&1 | tail -4
python scripts/64_routing_oracle.py 2>&1 | tail -2
python scripts/65_stratified.py 2>&1 | tail -2

say "R4 E16 八系统矩阵 (含 DeepRead 复现, omp RPC 作答+独立判分)"
# R4 前置: 基线分块 KB(DR-*)可能被此前的 00_reset_env 清空 —— 先跑幂等的
# ingest/raptor 阶段(有内容指纹缓存, 语料未变时秒级跳过), 否则 dense/RAPTOR
# 类基线会从空索引静默取回 0 命中, 数字作废。
( cd algorithms && python run_matrix.py --stage ingest 2>&1 | tail -2 )
( cd algorithms && python run_matrix.py --stage raptor 2>&1 | tail -2 )
( cd algorithms && python run_matrix.py --stage retrieve 2>&1 | tail -2 )
( cd algorithms && python run_matrix.py --stage answer  2>&1 | tail -2 )
( cd algorithms && python run_matrix.py --stage judge   2>&1 | tail -2 )
( cd algorithms && python run_matrix.py --stage report  2>&1 | tail -8 )

say "R5 E16b API 全流程 (HTTP 选算法问答 + 中间 Agent 排名)"
( cd algorithms && python api_server.py > api_server.log 2>&1 & )
sleep 40
python scripts/27_api_flow_test.py 2>&1 | tail -4

say "R6 轨道报告 + 全量问答日志"
python scripts/71_track_reports.py retrieval 2>&1 | tail -3
python scripts/28_qa_log.py 2>&1 | tail -2
say "DONE — results/RETRIEVAL-BENCHMARK.md + retrieval-benchmark.html + RETRIEVAL-QA-LOG.{log,md}"
