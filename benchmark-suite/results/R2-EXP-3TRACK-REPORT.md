# 三模式检索实验报告 (Three-Track Experiment)

Run: `run-20261013T094350Z-5f9faac` · 题集: `qa_questions.json` · 语料: 平台五门类库 = corpus_md 100 篇 = Corpus-Chunks800

## 分轨结果

| 轨 | 模式 | pass | gold 命中 | 关键词核验 | 引用命中 (part/section/table) | 平均时延 s | 平均工具数 | 平均成本 $ |
|---|---|---|---|---|---|---:|---:|---:|
| A2 | A2 平台 KB(仅KB工具,无文件工具) | 10/10 | 10/10 | 10/10 | 9/10 (chunk 5) | 52.6 | 6.0 | 0.711 |
| B | B 裸 Agent(文件工具) | 9/10 | 10/10 | 9/10 | 7/10 (chunk 0) | 22.2 | 6.4 | 0.4867 |
| C | C Dense-RAG(Chunks800) | 9/10 | 10/10 | 9/10 | 2/10 (chunk 7) | 24.5 | 3.7 | 0.5269 |

## 逐题判分

| QID | 轨 | gold | 关键词命中 | 引用标记 | pass | 时延 s | 工具数 |
|---|---|---|---|---|---|---:|---:|
| BQ01 | A2 | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✓ (Table 1, part 1 of 2, §2) | ✅ | 55.5 | 5 |
| BQ02 | A2 | ✓ | 2/2 (noisy intermediate-scale,error correction) | ✓ (part 1 of 3, part 1 of 4, §4.1) | ✅ | 35.8 | 5 |
| BQ03 | A2 | ✓ | 2/2 (multimedqa,67.6) | ✓ (Section 3.1.1, Table 4, part 1 of 8) | ✅ | 75.3 | 10 |
| BQ04 | A2 | ✓ | 3/3 (molecular function,biological process,cellular component) | ✓ (part 1 of 2, section c) | ✅ | 25.6 | 4 |
| BQ05 | A2 | ✓ | 1/1 (unified growth theory) | ✗ | ✅ | 35.6 | 5 |
| BQ06 | A2 | ✓ | 1/1 (precipitation efficiency) | ✓ (part 1 of 3, part 2 of 3, §3) | ✅ | 97.4 | 10 |
| BQ07 | A2 | ✓ | 2/2 (yiddish,8b) | ✓ (part 1 of 4) | ✅ | 25.3 | 3 |
| BQ08 | A2 | ✓ | 2/2 (oxygen redox,cathode) | ✓ (part 1 of 2, part 2 of 2) | ✅ | 77.0 | 6 |
| BQ09 | A2 | ✓ | 2/2 (dynamic,multilayer perceptron) | ✓ (part 1 of 2, part 2 of 2) | ✅ | 43.9 | 5 |
| BQ10 | A2 | ✓ | 2/2 (immune evasion,chemotherapy) | ✓ (part 1 of 3, part 2 of 3, part 3 of 3) | ✅ | 54.7 | 7 |
| BQ01 | B | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✗ | ✅ | 24.9 | 6 |
| BQ02 | B | ✓ | 2/2 (noisy intermediate-scale,error correction) | ✓ (§4.1, §4.2, §6.4) | ✅ | 24.2 | 7 |
| BQ03 | B | ✓ | 2/2 (multimedqa,67.6) | ✓ (Table 4) | ✅ | 20.3 | 8 |
| BQ04 | B | ✓ | 3/3 (molecular function,biological process,cellular component) | ✓ (Section 2) | ✅ | 12.0 | 5 |
| BQ05 | B | ✓ | 1/1 (unified growth theory) | ✓ (sections f) | ✅ | 19.6 | 4 |
| BQ06 | B | ✓ | 1/1 (precipitation efficiency) | ✓ (§2, §3, §4.1) | ✅ | 29.9 | 10 |
| BQ07 | B | ✓ | 2/2 (yiddish,8b) | ✓ (Section 1, Section 4) | ✅ | 11.6 | 4 |
| BQ08 | B | ✓ | 2/2 (oxygen redox,cathode) | ✗ | ✅ | 20.2 | 4 |
| BQ09 | B | ✓ | 1/2 (dynamic) | ✗ | ❌ | 20.4 | 4 |
| BQ10 | B | ✓ | 2/2 (immune evasion,chemotherapy) | ✓ (Table 2, §1, §3.1) | ✅ | 38.6 | 12 |
| BQ01 | C | ✓ | 3/3 (scaled dot-product,multi-head,recurrence) | ✓ (Table 1, §3.2, §3.2.1) | ✅ | 34.1 | 5 |
| BQ02 | C | ✓ | 2/2 (noisy intermediate-scale,error correction) | ✗ | ✅ | 21.4 | 2 |
| BQ03 | C | ✓ | 2/2 (multimedqa,67.6) | ✓ (Table 4) | ✅ | 18.6 | 2 |
| BQ04 | C | ✓ | 3/3 (molecular function,biological process,cellular component) | ✗ | ✅ | 17.0 | 2 |
| BQ05 | C | ✓ | 1/1 (unified growth theory) | ✗ | ✅ | 30.0 | 4 |
| BQ06 | C | ✓ | 1/1 (precipitation efficiency) | ✗ | ✅ | 48.6 | 11 |
| BQ07 | C | ✓ | 2/2 (yiddish,8b) | ✗ | ✅ | 11.2 | 2 |
| BQ08 | C | ✓ | 2/2 (oxygen redox,cathode) | ✗ | ✅ | 19.7 | 2 |
| BQ09 | C | ✓ | 2/2 (dynamic,multilayer perceptron) | ✗ | ✅ | 23.3 | 3 |
| BQ10 | C | ✓ | 1/2 (chemotherapy) | ✗ | ❌ | 21.3 | 4 |

## 判分说明

- pass = 金标论文可追溯(答案/工具轨迹含金标 id) 且 答案含 ≥60% 金标关键词(词边界匹配)。
- C 轨金标证据依赖提示词要求的 chunk 文件名引用; 拒答(insufficient evidence)计为未通过。
- `引用命中` = 论文 Metrics 的 cited 口径（part k of N / section|table|appendix 编号 / §n）;
  括号内 `chunk n` 为稠密轨按提示词要求的 chunk 引用，**不计入**论文 cited 数字，仅作附注。
  cited 正则: `part/section/table markers present: \bparts?\s+\d+\s+of\s+\d+ | \b(?:section|sections|table|tables|appendix|appendices)\s+(?:\d+(?:\.\d+)*|[A-Z](?:\.\d+)*) | §\s*\d+(?:\.\d+)*`
  附注 chunk 正则: `dense chunk references (reported separately, NOT counted in the paper's cited numbers): \bchunk[_ ]?(?:index|id)?\s*\d+`
- 判分完全确定性(词边界/标记正则), 不经 LLM; 逐题 trace 见 run 目录 track_*.json。

逐字答案与监控表见 run 目录 `SUMMARY.md`。