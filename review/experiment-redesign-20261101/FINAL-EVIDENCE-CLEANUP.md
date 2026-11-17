# 终版证据清理清单（2026-11-10）

## 唯一保留的终版 bench

- `artifacts/final_bench/s4_traces_final.json` — 五臂 × 76，380 trace，qid 唯一，零越界/目录卡污染
- `artifacts/final_bench/s5_floor.json` — 卫生平台 floor：BM25 24/40、dense 19/40、RRF 26/40
- `artifacts/final_bench/s6_stats.json` — gold-only CI + qid-paired McNemar
- `artifacts/final_bench/us2_reasonableness_audit.json` — 25/25 PASS
- `artifacts/final_bench/viz/chart1_gold_rate.png`
- `artifacts/final_bench/viz/chart2_refusal.png`
- `artifacts/final_bench/viz/chart3_bytes_time.png`
- `artifacts/final_bench/viz/chart4_first_hit.png`
- `artifacts/final_bench/viz/chart5_route.png`

## E2E / 功能验收证据

- `artifacts/e2e_validation/us1_preflight_record.json` + `.txt` — 10 库预检、认证、题集校验
- `artifacts/e2e_validation/us3_ingest_audit.json` — 罪与罚 27 卷自由入库全门审计
- `artifacts/e2e_validation/us3-ingest/` — 27 卷文本+源文档+ingest_result
- `artifacts/e2e_validation/us4_case_report.json` — 零提示三案例记录及限制说明
- `artifacts/e2e_validation/agent_sample/` — 6/6 Agent 回答 JSON
- `artifacts/e2e_validation/single-doc-e2e/` — CoT 论文 E2E 证据

## 语料 / 题集溯源

- `artifacts/provenance/manifest.json`
- `artifacts/provenance/questions.jsonl`
- `artifacts/provenance/corpus_spec_final.json`
- `artifacts/provenance/s2_ingest_report_v2.json`
- `artifacts/provenance/pdf_anchor_audit_20261104.json`
- `artifacts/provenance/s8_route_v2.json`

## 已删除

- 所有 timestamped `s4_traces_*.json` 中间轮
- 被污染/中断 checkpoint 与 pilot 目录
- 旧混沌期日志、旧串行器、旧监护器、旧探针尝试
- 根目录散落的临时工件与 hooks 元数据

## 不属于终版主表但必须披露

- `baselines/` 中 5 个内容认知项目源码已 pin，但缺 LLM endpoint，未生成可公平主表结果
- 题集中的 2 个 cross 占位题 `needs_expansion=true`，未进入 380-trace 主轮
- 真实 Agent 通读拒答臂未执行；脚本 readall 仅为机械全库 containment/成本臂
