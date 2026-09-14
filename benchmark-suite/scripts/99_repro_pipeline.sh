#!/usr/bin/env bash
# 全流程复现重跑 — 严格按 TEST-PLAN + EXPERIMENT-DESIGN 顺序，独立 run 目录，不覆盖归档。
# 用法: bash scripts/99_repro_pipeline.sh > results/repro-full.log 2>&1
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
LOG=results/repro-full.log
say() { echo "=== $(date +%H:%M:%S) $* ==="; }

say "STEP 0 reset all KBs"
python scripts/00_reset_env.py 2>&1 | tail -3

say "STEP 0b restart backend (clear in-memory BM25)"
( cd .. && node command/ragctl.js restart backend 2>&1 | tail -2 )
sleep 20
curl -s -m 10 http://127.0.0.1:8771/health; echo ""

say "STEP 1a ingestion r1"
python scripts/01_ingestion.py 1 2>&1 | tail -3
say "STEP 1a ingestion r2"
python scripts/01_ingestion.py 2 2>&1 | tail -3

say "STEP 2b std2 ingest r1"
python scripts/21_std2_ingest.py 1 2>&1 | tail -2
say "STEP 2b std2 ingest r2"
python scripts/21_std2_ingest.py 2 2>&1 | tail -2

say "STEP 2c std2 retrieval r1"
python scripts/22_std2_retrieval.py 1 2>&1 | tail -8
say "STEP 2c std2 retrieval r2"
python scripts/22_std2_retrieval.py 2 2>&1 | tail -8

say "STEP 2 demo retrieval r1"
python scripts/02_retrieval.py 1 2>&1 | tail -2
say "STEP 2 demo retrieval r2"
python scripts/02_retrieval.py 2 2>&1 | tail -2

say "STEP 3 experience (module C) r1"
python scripts/03_experience.py 1 2>&1 | tail -3
say "STEP 3 experience (module C) r2"
python scripts/03_experience.py 2 2>&1 | tail -3

say "E1 ablation r1"
python scripts/30_ablation.py 1 2>&1 | tail -10
say "E1 ablation r2"
python scripts/30_ablation.py 2 2>&1 | tail -10

say "E8 hotpot build (9 KBs)"
python scripts/60_hotpot_build.py 2>&1 | tail -4
say "E8 hotpot eval r1"
python scripts/61_hotpot_eval.py 1 2>&1 | tail -6
say "E8 hotpot eval r2"
python scripts/61_hotpot_eval.py 2 2>&1 | tail -6

say "E13 routing oracle"
python scripts/64_routing_oracle.py 1 2>&1 | tail -4

say "E14 stratified"
python scripts/65_stratified.py 2>&1 | tail -4

say "E3-E7 experience suite"
python scripts/40_experience_suite.py 1 2>&1 | tail -6
say "E4 fix"
python scripts/42_e4_fix.py 2>&1 | tail -4
say "E15 judge agreement (8 queries)"
python scripts/66_judge_agreement.py 1 2>&1 | tail -6

say "E16 DeepRead baseline matrix (30 queries x 8 methods, omp RPC agent)"
( cd algorithms && python run_matrix.py --stage ingest 2>&1 | tail -3 )
( cd algorithms && python run_matrix.py --stage raptor 2>&1 | tail -3 )
( cd algorithms && python run_matrix.py --stage retrieve 2>&1 | tail -3 )
( cd algorithms && python run_matrix.py --stage answer 2>&1 | tail -3 )
( cd algorithms && python run_matrix.py --stage judge 2>&1 | tail -3 )
( cd algorithms && python run_matrix.py --stage report 2>&1 | tail -6 )

say "E17 platform ops eval (dedup/tags/graph)"
RAG_BENCH_WEB_URL=http://localhost:6789 python scripts/26_platform_ops_eval.py 2>&1 | tail -4

say "E16b API flow test (8 methods x 30 queries via HTTP, middle-agent ranking)"
( cd algorithms && python api_server.py > api_server.log 2>&1 & )
sleep 40
curl -s -m 10 http://127.0.0.1:8790/health | head -c 120; echo ""
python scripts/27_api_flow_test.py 2>&1 | tail -6

say "reports"
python scripts/04_report.py 2>&1 | tail -2
python scripts/70_build_report.py 2>&1 | tail -2

say "DONE"
