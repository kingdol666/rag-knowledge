#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
# Track F — 平台自身功能轨
# 只回答一个问题: 平台自己支持的每个功能(解析入库/经验生命周期/整理/Agent 面/
# 规模)实测表现如何。不与任何外部检索算法比较。
# 用法: bash pipelines/functions_track.sh > results/track-F.log 2>&1
# ══════════════════════════════════════════════════════════════════════
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
export RAG_BENCH_WEB_URL=http://localhost:6789
LOG=results/track-F.log
say() { echo "=== $(date +%H:%M:%S) $* ==="; }

say "F0 预检 (健康/token/omp; fail-loud, 不删数据)"
python scripts/00_preflight.py || { echo "预检未通过 — 中止 (处置指引见上)"; exit 1; }


say "F1 Module A 解析与入库完整性 (in-house + 标准语料)"
python scripts/01_ingestion.py 2>&1 | tail -3
python scripts/21_std2_ingest.py 2>&1 | tail -2

say "F2 经验生命周期: Module C + E3 重置多轮 + E4 双基线 + E15 判分一致性"
python scripts/03_experience.py 2>&1 | tail -3
python scripts/40_experience_suite.py 2>&1 | tail -4
python scripts/42_e4_fix.py 2>&1 | tail -2
python scripts/66_judge_agreement.py 2>&1 | tail -3

say "F3 E17 整理功能 (去重/标签/图谱/目录)"
python scripts/26_platform_ops_eval.py 2>&1 | tail -4

say "F4 Agent 面端到端 (8 组 26 项, 独立外部客户端)"
python scripts/80_e2e_surface.py 2>&1 | tail -3

say "F5 平台规模实测 (94 工具/接口/知识库)"
python scripts/82_system_scale.py 2>&1 | tail -3

say "F6 轨道报告"
python scripts/71_track_reports.py functions 2>&1 | tail -3
say "DONE — results/FUNCTIONS-BENCHMARK.md + functions-benchmark.html"
