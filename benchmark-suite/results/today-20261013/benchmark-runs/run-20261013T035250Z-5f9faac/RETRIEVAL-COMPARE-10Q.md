# 检索任务对照矩阵（三模式 + baseline × 10 题, 纯检索无 LLM 回答）

- Run: `run-20261013T035250Z-5f9faac` · 生成: 2026-10-13 04:09 UTC（vector 行为跨库口径复跑补测）
- 题: 内置 q1/q2 + Quick10 QK01-QK08（金标双库预验证, 见 GROUND-TRUTH.md）
- 语料: 模式=真库; bm25/rrf=corpus_md 100 篇; vector=平台跨库（RAG_BENCH_VECTOR_KB 置空）

| 方法 | q1 | q2 | qk_QK01 | qk_QK02 | qk_QK03 | qk_QK04 | qk_QK05 | qk_QK06 | qk_QK07 | qk_QK08 | gold率 | 延迟均值s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mode_A | ✅ 24s | ✅ 20s | ✅ 20s | ✅ 18s | ✅ 19s | ✅ 19s | ✅ 19s | ✅ 20s | ✅ 18s | ✅ 21s | 10/10 | 19.8 |
| mode_B | ✅ 14s | ✅ 8s | ❌ 5s | ✅ 5s | ✅ 20s | ✅ 20s | ✅ 20s | ❌ 20s | ❌ 8s | ✅ 19s | 7/10 | 14.0 |
| mode_C | ✅ 29s | ✅ 29s | ❌ 30s | ✅ 26s | ✅ 36s | ✅ 37s | ✅ 37s | ✅ 44s | ✅ 27s | ✅ 37s | 9/10 | 33.1 |
| bm25 | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | 10/10 | 0.0 |
| vector | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | 10/10 | 0.1 |
| rrf | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | ✅ 0s | 10/10 | 0.0 |

> 模式臂经硬验证门（real_engine/金标/延迟）; baseline 臂 retrieval_only 零 token。
> vector baseline 首跑命中空默认库（Corpus-Chunks800, 0 docs）——2026-10-12 已知问题复发, 已按跨库口径复跑修正。
