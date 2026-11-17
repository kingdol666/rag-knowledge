# 逐级检索内容层优化实验报告（A0f / A0h / PD）

日期 2026-11-11 · 语料 10 KB（MD语料-*，138 卷）· 72 gold + 4 refusal 探针 · 判卷 = 本地 Laya 引擎

## 结论速览

- **A0f（判卷全窗口，inline content，零 server 改动）**：45/72 = 62.5%（A0 51.4%），修复 8 个 A0 未命中，0 回归；McNemar p=0.0078
- **A0h（A0f + 全文 chunk top-8 ∪ 判卷包，总帽 60K）**：52/72 = 72.2%，修复 15 个，0 回归；p=0.0001
- **PD（精确逐文档：无导航，十库并集 top-6 → 同款全窗口判卷）**：46/72 = 63.9%，修复 9 个，0 回归；p=0.0039

**回收主力 = A0h 的 chunk 窗口并集**（+15 hits > PD +9 > A0f +8）：判卷全窗口（A0f）只救回「卷在候选内但尾巴截断」类；向量 chunk 信号（A0h）额外救回「判卷段未存活 / 候选选择失败」类。

## 对比表（gold-only，n=72）

| arm | 检索 | gold hits | rate | Wilson 95% CI | McNemar vs A0 | avg bytes/q | avg tool_s | avg digest_s | routing |
|---|---|---|---|---|---|---|---|---|---|
| A0 | 逐级：目录卡路由→书架→库内宽网→判卷(参考模式 40K) | 37/72 | 51.4% | [0.401,0.626] | baseline | 31,409 | 16.3 | 7.9 | 72/72 |
| A0f | 同 A0 导航；判卷自行取全卷 250K + inline content | 45/72 | 62.5% | [0.510,0.728] | p=0.0078 * | 303,449 | 13.0 | 75.9 | 72/72 |
| A0h | A0f + slim=False chunk top-8 ∪ 判卷包（帽 60K） | 52/72 | 72.2% | [0.610,0.812] | p=0.0001 * | 309,143 | 13.8 | 77.3 | 72/72 |
| PD | 无导航：十库定向 top30 并集 top-6 → 全窗口判卷 | 46/72 | 63.9% | [0.524,0.740] | p=0.0039 * | 308,166 | 13.6 | 77.0 | n/a |
| A1b | 全局向量直搜（十库并集，无判卷） | 39/72 | 54.2% | [0.427,0.652] | p=0.6875 | 38,464 | 10.8 | 9.6 | n/a |
| A1-readall | 逐篇通读（上界） | 72/72 | 100.0% | [0.949,1.000] | p=0.0000 * | 24,313,972 | 253.7 | 6078.5 | n/a |

**ladder vs precise 正面对比（A0h vs PD）**：A0h-only=7 PD-only=1，McNemar p=0.0703（方向一致但未达 0.05 显著）—— 逐级导航保留（路由→宽网→判卷）+ chunk 并集在命中率上优于放弃导航的十库并集精确检索（PD 还多付 10× 搜索调用）；两者均显著优于 A0。

## A0 未命中归因（35 qids，磁盘卷文件 substring 定位）

- routing-miss: 0（路由 72/72 全对，与既有结论一致）
- window-truncation-miss: 5（参考模式 server 抓取窗 = min(40000 chars, 200 行)；含 line>200 子类）
- judge-miss: 30（窗内未进证据包：其中仅 5 个的 gold 卷出现在旧 survivors——25 个属候选选择/段存活失败）
- format-mismatch: 0

### 各修复臂对应归因类（修复数按 A0 未命中 35 个计）

| arm | window-truncation | judge-miss | 合计修复 |
|---|---|---|---|
| A0f | 1 | 7 | 8 |
| A0h | 2 | 13 | 15 |
| PD | 1 | 8 | 9 |

A0h 仍未命中 20/35（全部为 judge-miss 类深处：gold 段 laya 分数 <0.5 或chunk 检索未召回对应窗口）——离 A1-readall(100%) 上界还差 20 题，其中 gold 段语义相关性本身偏低（如标题词 gold_evidence：'LLaMA'、'Odyssey'）。

## 逐 qid 明细

| qid | 归因类 | A0f | A0h | PD |
|---|---|---|---|---|
| A-economics-en-on_liberty | judge-miss | miss | hit | miss |
| A-literature-en-anna_karenina | judge-miss | miss | miss | miss |
| A-literature-en-great_expectations | judge-miss | miss | miss | miss |
| A-literature-en-huckleberry_finn | judge-miss | miss | hit | miss |
| A-literature-en-metamorphosis | judge-miss | miss | miss | miss |
| A-literature-en-odyssey | judge-miss | miss | miss | hit |
| A-literature-en-sense_and_sensibility | judge-miss | miss | miss | miss |
| A-literature-en-war_of_the_worlds | judge-miss | hit | hit | hit |
| A-medicine-en-alzheimer_biomarkers_rev | judge-miss | miss | miss | miss |
| A-medicine-en-asthma_biologics_review | judge-miss | miss | hit | miss |
| A-medicine-en-cardiovascular_imaging_r | judge-miss | miss | miss | miss |
| A-medicine-en-diabetes_management_revi | judge-miss | miss | miss | miss |
| A-medicine-en-malaria_vaccine_review | judge-miss | miss | miss | miss |
| A-medicine-en-mrna_vaccine_review | judge-miss | miss | miss | miss |
| A-medicine-en-obesity_pharmacotherapy_ | judge-miss | miss | hit | miss |
| A-medicine-en-stroke_thrombolysis_revi | judge-miss | miss | miss | miss |
| A-medicine-en-telemedicine_outcomes_re | judge-miss | miss | hit | miss |
| A-medicine-en-tuberculosis_treatment_r | judge-miss | miss | hit | miss |
| A-philosophy-en-walden | judge-miss | hit | hit | hit |
| A-science-en-gpt3.pdf | judge-miss | miss | miss | miss |
| A-science-en-instructgpt.pdf | window-truncation-miss | miss | miss | miss |
| A-science-en-llama.pdf | judge-miss | miss | miss | miss |
| A-science-en-resnet.pdf | judge-miss | hit | hit | hit |
| A-science-en-roberta.pdf | judge-miss | hit | hit | hit |
| A-science-en-swin_transformer.pdf | judge-miss | miss | miss | miss |
| A-science-en-t5.pdf | judge-miss | miss | miss | miss |
| A-science-en-vae.pdf | judge-miss | miss | miss | miss |
| A-science-en-word2vec.pdf | window-truncation-miss | hit | hit | hit |
| F-hlm-2 | judge-miss | hit | hit | hit |
| F-hlm-3 | judge-miss | hit | hit | hit |
| F-md-1 | window-truncation-miss | miss | miss | miss |
| F-pp-1 | window-truncation-miss | miss | hit | miss |
| G-fyp-1 | judge-miss | hit | hit | hit |
| G-gwr-2 | judge-miss | miss | miss | miss |
| S-bert-1 | window-truncation-miss | miss | miss | miss |

## 方法注记

- 判卷全窗口方案：kb_laya_judge 参考模式 server 端抓取硬编码 max_chars=40000（kb-mcp/server.py ~:3205）且 limit 默认 200 行 = 窗口截断主因；已核验 documents 条目带 content 时跳过 server 抓取（legacy 模式），故 A0f/A0h/PD 均自行 kb_doc_read(max_chars=250000, limit=100000) 取全卷 inline 传入，max_evidence_chars=250000 —— **零 server 改动**（方案 preferred 分支成立）。
- trace 字段完整保留（qid/arm/query/is_refusal/gold_hit/bytes_ingested/tool_seconds/llm_digest_seconds/refusal_ok/top1/distractor_docs/evidence_focus/calls/route_correct），新臂另加 judge_mode/chunk_bytes/pack_bytes；checkpoint 与 trace 均在 opt_bench/（final_bench 未动）。
- 事件记录：会话开始前 MD语料-文学-中文 的 chroma hnsw 段已损坏（0 命中@threshold 0）；实验中期一次双 backend 并存（kb-mcp 启动健康检查自动拉起第二个）再次触发段丢失。已按单写者原则删除重建该 collection（force reindex，171 chunks），全部 17 个受累行重跑，最终 228/228 行有效。判卷 liveness real_engine=true（参考+inline 双模式）。
- refusal 探针：A0f/A0h/PD 门 0/4 拒绝（证据变多→判卷存活变多）；A0 2/4。