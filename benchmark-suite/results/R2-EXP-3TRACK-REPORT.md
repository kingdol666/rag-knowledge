# 三模式检索实验报告 (Three-Track Experiment)

Run: `experiment_chat_20260922-211000` · 题集: `qa_questions.json` · 语料: 平台五门类库 = corpus_md 100 篇 = Corpus-Chunks800

## 分轨结果

| 轨 | 模式 | pass | gold 命中 | 关键词核验 | 平均时延 s | 平均工具数 | 平均成本 $ |
|---|---|---|---|---|---:|---:|---:|
| A | A 平台 KB(QDCVR 工具面) | 9/10 | 9/10 | 9/10 | 113.0 | 7.6 | 0.4911 |
| B | B 裸 Agent(文件工具) | 6/10 | 10/10 | 6/10 | 42.7 | 4.4 | 0.1631 |
| C | C Dense-RAG(Chunks800) | 5/10 | 9/10 | 6/10 | 48.0 | 2.4 | 0.1803 |

## 逐题判分

| QID | 轨 | gold | 关键词命中 | pass | 时延 s | 工具数 |
|---|---|---|---|---|---:|---:|
| BQ01 | A | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✅ | 174.0 | 9 |
| BQ02 | A | ✗ | 1/2 (noisy intermediate-scale) | ❌ | 99.2 | 6 |
| BQ03 | A | ✓ | 2/2 (multimedqa,67.6) | ✅ | 81.0 | 7 |
| BQ04 | A | ✓ | 3/3 (molecular function,biological process,cellular component) | ✅ | 77.7 | 5 |
| BQ05 | A | ✓ | 1/1 (unified growth theory) | ✅ | 160.9 | 8 |
| BQ06 | A | ✓ | 1/1 (precipitation efficiency) | ✅ | 117.9 | 10 |
| BQ07 | A | ✓ | 2/2 (yiddish,8b) | ✅ | 155.9 | 6 |
| BQ08 | A | ✓ | 2/2 (oxygen redox,cathode) | ✅ | 152.5 | 10 |
| BQ09 | A | ✓ | 2/2 (dynamic,multilayer perceptron) | ✅ | 56.9 | 5 |
| BQ10 | A | ✓ | 2/2 (immune evasion,chemotherapy) | ✅ | 53.5 | 10 |
| BQ01 | B | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✅ | 41.7 | 6 |
| BQ02 | B | ✓ | 2/2 (noisy intermediate-scale,error correction) | ✅ | 40.9 | 4 |
| BQ03 | B | ✓ | 2/2 (multimedqa,67.6) | ✅ | 60.3 | 3 |
| BQ04 | B | ✓ | 3/3 (molecular function,biological process,cellular component) | ✅ | 40.0 | 4 |
| BQ05 | B | ✓ | 1/1 (unified growth theory) | ✅ | 32.8 | 4 |
| BQ06 | B | ✓ | 0/1 | ❌ | 35.6 | 5 |
| BQ07 | B | ✓ | 2/2 (yiddish,8b) | ✅ | 51.3 | 7 |
| BQ08 | B | ✓ | 0/2 | ❌ | 20.5 | 4 |
| BQ09 | B | ✓ | 1/2 (dynamic) | ❌ | 61.7 | 4 |
| BQ10 | B | ✓ | 1/2 (chemotherapy) | ❌ | 41.9 | 3 |
| BQ01 | C | ✓ | 2/3 (scaled dot-product,recurrence) | ✅ | 64.4 | 3 |
| BQ02 | C | ✓ | 1/2 (noisy intermediate-scale) | ❌ | 125.1 | 3 |
| BQ03 | C | ✗ | 2/2 (multimedqa,67.6) | ❌ | 14.4 | 2 |
| BQ04 | C | ✓ | 3/3 (molecular function,biological process,cellular component) | ✅ | 35.4 | 2 |
| BQ05 | C | ✓ | 1/1 (unified growth theory) | ✅ | 42.4 | 2 |
| BQ06 | C | ✓ | 0/1 | ❌ | 35.9 | 2 |
| BQ07 | C | ✓ | 2/2 (yiddish,8b) | ✅ | 15.3 | 2 |
| BQ08 | C | ✓ | 2/2 (oxygen redox,cathode) | ✅ | 113.1 | 3 |
| BQ09 | C | ✓ | 1/2 (dynamic) | ❌ | 20.7 | 2 |
| BQ10 | C | ✓ | 1/2 (immune evasion) | ❌ | 13.8 | 3 |

## 判分说明

- pass = 金标论文可追溯(答案/工具轨迹含金标 id) 且 答案含 ≥60% 金标关键词(词边界匹配)。
- C 轨金标证据依赖提示词要求的 chunk 文件名引用; 拒答(insufficient evidence)计为未通过。
- 判分完全确定性(词边界正则), 不经 LLM; 逐题 trace 见 run 目录 track_*.json。

逐字答案与监控表见 run 目录 `SUMMARY.md`。