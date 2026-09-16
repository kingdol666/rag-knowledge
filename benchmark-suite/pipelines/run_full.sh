#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
# 双轨健壮启动器 — 供 Agent/人工一键跑完整 benchmark。
#  1. 等待 backend/web 真就绪(重试循环, 容忍重置后端清理期连接拒绝)
#  2. 00_reset_env 清场 + 预检通过才开跑
#  3. 串行 F → R(§7 纪律), 每轨结束做硬验收(报告存在 + 关键指标达标)
#  4. 任一硬验收失败 → 写 _run_verdict.txt=FAIL 并停止, 不带病跑下一轨
# ══════════════════════════════════════════════════════════════════════
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
export RAG_BENCH_WEB_URL=http://localhost:6789
say() { echo "=== $(date +%H:%M:%S) $* ==="; }

# 防重入: 同一时刻只允许一条评测链(双链并发会互相污染 KB 状态与结果文件, 已实测)
LOCK=results/.run.lock
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK")" 2>/dev/null; then
  echo "另一个评测链正在运行 (pid $(cat "$LOCK")) — 拒绝启动"; exit 1
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

wait_backend() {  # 等后端健康: 要求连续 3 次 200(容忍重置级联删除阻塞事件循环)
  local ok=0
  for i in $(seq 1 40); do
    code=$(curl -s -m 15 -o /dev/null -w "%{http_code}" http://localhost:8771/api/v1/health || echo 000)
    if [ "$code" = "200" ]; then ok=$((ok+1)); else ok=0; fi
    [ "$ok" -ge 3 ] && return 0
    sleep 5
  done
  return 1
}

say "STEP 0 等待服务就绪"
wait_backend || { echo "BACKEND NOT READY"; echo "FAIL: backend not ready" > results/_run_verdict.txt; exit 1; }
# web dev 服务器重负载下会间歇拒绝连接(§7 已知) —— 预检失败自动重试 3 次
PF=1
for attempt in 1 2 3; do
  if python scripts/00_preflight.py; then PF=0; break; fi
  say "预检第 ${attempt} 次未通过 — 30s 后重试(等 web 拒绝窗口过去)"
  sleep 30
done
[ "$PF" = "0" ] || { echo "FAIL: preflight x3" > results/_run_verdict.txt; exit 1; }

say "STEP 1 重置环境(清空全部 KB)"
python scripts/00_reset_env.py 2>&1 | tail -2
wait_backend || { echo "FAIL: backend down after reset" > results/_run_verdict.txt; exit 1; }
# 重置的级联删除会同步阻塞后端事件循环几十秒 —— 长稳定窗口 + 重试预检
wait_backend
sleep 60
PF=1
for attempt in 1 2 3 4 5; do
  if python scripts/00_preflight.py; then PF=0; break; fi
  say "重置后预检第 ${attempt} 次未通过 — 30s 后重试"
  sleep 30
done
[ "$PF" = "0" ] || { echo "FAIL: preflight after reset x5" > results/_run_verdict.txt; exit 1; }

say "STEP 2 Track F"
bash pipelines/functions_track.sh > results/track-F.log 2>&1
F_E2E=$(grep -oE "E2E: [0-9]+/26" results/track-F.log | tail -1)
echo "F exit=$? E2E=$F_E2E"
[ "$F_E2E" = "E2E: 26/26" ] || { echo "FAIL: F E2E not 26/26 ($F_E2E)" > results/_run_verdict.txt; exit 1; }
[ -s results/FUNCTIONS-BENCHMARK.md ] || { echo "FAIL: F report missing" > results/_run_verdict.txt; exit 1; }
grep -q "Module A" results/FUNCTIONS-BENCHMARK.md || { echo "FAIL: F report missing Module A" > results/_run_verdict.txt; exit 1; }

say "STEP 3 Track R"
bash pipelines/retrieval_track.sh > results/track-R.log 2>&1
grep -q "DONE — results/RETRIEVAL-BENCHMARK" results/track-R.log || { echo "FAIL: R did not finish" > results/_run_verdict.txt; exit 1; }
[ -s results/RETRIEVAL-BENCHMARK.md ] || { echo "FAIL: R report missing" > results/_run_verdict.txt; exit 1; }
[ -s results/RETRIEVAL-QA-LOG.md ] || { echo "FAIL: QA log missing" > results/_run_verdict.txt; exit 1; }

say "PASS 全部验收通过"
echo "PASS" > results/_run_verdict.txt
