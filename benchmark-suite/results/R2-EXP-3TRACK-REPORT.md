# 三模式检索实验报告 (Three-Track Experiment)

Run: `run-20260930T150453Z-3ec2174` · 题集: `qa_questions.json` · 语料: 平台五门类库 = corpus_md 100 篇 = Corpus-Chunks800

## 分轨结果

| 轨 | 模式 | pass | gold 命中 | 关键词核验 | 平均时延 s | 平均工具数 | 平均成本 $ |
|---|---|---|---|---|---:|---:|---:|
| A2 | A2 平台 KB(仅KB工具,无文件工具) | 10/10 | 10/10 | 10/10 | 116.2 | 6.8 | 0.5457 |
| B | B 裸 Agent(文件工具) | 8/10 | 10/10 | 8/10 | 47.6 | 4.9 | 0.6346 |
| C | C Dense-RAG(Chunks800) | 6/10 | 8/10 | 6/10 | 41.1 | 3.7 | 0.2784 |

## 逐题判分

| QID | 轨 | gold | 关键词命中 | pass | 时延 s | 工具数 |
|---|---|---|---|---|---:|---:|
| BQ01 | A2 | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✅ | 169.8 | 6 |
| BQ02 | A2 | ✓ | 2/2 (noisy intermediate-scale,error correction) | ✅ | 115.1 | 4 |
| BQ03 | A2 | ✓ | 2/2 (multimedqa,67.6) | ✅ | 99.3 | 9 |
| BQ04 | A2 | ✓ | 3/3 (molecular function,biological process,cellular component) | ✅ | 23.7 | 5 |
| BQ05 | A2 | ✓ | 1/1 (unified growth theory) | ✅ | 108.1 | 10 |
| BQ06 | A2 | ✓ | 1/1 (precipitation efficiency) | ✅ | 136.8 | 7 |
| BQ07 | A2 | ✓ | 2/2 (yiddish,8b) | ✅ | 31.5 | 3 |
| BQ08 | A2 | ✓ | 2/2 (oxygen redox,cathode) | ✅ | 372.6 | 12 |
| BQ09 | A2 | ✓ | 2/2 (dynamic,multilayer perceptron) | ✅ | 55.9 | 6 |
| BQ10 | A2 | ✓ | 2/2 (immune evasion,chemotherapy) | ✅ | 49.3 | 6 |
| BQ01 | B | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✅ | 64.7 | 7 |
| BQ02 | B | ✓ | 2/2 (noisy intermediate-scale,error correction) | ✅ | 77.8 | 7 |
| BQ03 | B | ✓ | 2/2 (multimedqa,67.6) | ✅ | 55.6 | 7 |
| BQ04 | B | ✓ | 3/3 (molecular function,biological process,cellular component) | ✅ | 27.1 | 4 |
| BQ05 | B | ✓ | 1/1 (unified growth theory) | ✅ | 63.6 | 5 |
| BQ06 | B | ✓ | 1/1 (precipitation efficiency) | ✅ | 88.0 | 3 |
| BQ07 | B | ✓ | 2/2 (yiddish,8b) | ✅ | 25.9 | 5 |
| BQ08 | B | ✓ | 1/2 (oxygen redox) | ❌ | 24.6 | 4 |
| BQ09 | B | ✓ | 2/2 (dynamic,multilayer perceptron) | ✅ | 31.0 | 4 |
| BQ10 | B | ✓ | 1/2 (chemotherapy) | ❌ | 17.3 | 3 |
| BQ01 | C | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✅ | 115.6 | 8 |
| BQ02 | C | ✓ | 1/2 (noisy intermediate-scale) | ❌ | 40.3 | 2 |
| BQ03 | C | ✗ | 0/2 | ❌ | 50.2 | 8 |
| BQ04 | C | ✓ | 3/3 (molecular function,biological process,cellular component) | ✅ | 41.6 | 2 |
| BQ05 | C | ✓ | 1/1 (unified growth theory) | ✅ | 15.1 | 2 |
| BQ06 | C | ✓ | 1/1 (precipitation efficiency) | ✅ | 92.0 | 6 |
| BQ07 | C | ✓ | 2/2 (yiddish,8b) | ✅ | 18.3 | 2 |
| BQ08 | C | ✓ | 2/2 (oxygen redox,cathode) | ✅ | 14.0 | 3 |
| BQ09 | C | ✓ | 1/2 (dynamic) | ❌ | 20.5 | 3 |
| BQ10 | C | ✗ | 0/2 | ❌ | 3.7 | 1 |

## 判分说明

- pass = 金标论文可追溯(答案/工具轨迹含金标 id) 且 答案含 ≥60% 金标关键词(词边界匹配)。
- C 轨金标证据依赖提示词要求的 chunk 文件名引用; 拒答(insufficient evidence)计为未通过。
- 判分完全确定性(词边界正则), 不经 LLM; 逐题 trace 见 run 目录 track_*.json。

逐字答案与监控表见 run 目录 `SUMMARY.md`。