# KBQA PIPELINE 执行分析报告（Stage 9 产出）

- 执行时间：2026-09-18 00:00 – 03:30（UTC+8）· 完整九阶段按 `PIPELINE.md` 串行执行
- 语料：50 篇真实 arXiv 论文 / 26 领域（`data/papers/manifest.json`，sha256 清单）
- 本文全部数字取自落盘工件：`upload`/`ingest_report.json`、`repro_ingest.json`、
  `bench10_qa.json`、`skill_track_evidence.json`、`skill_track_answers.json`、
  `track_bc.json`。未测量的项标注"未测量"。

## 1. 语料与入库统计（Stage 2-5）

| 项 | 结果 |
|---|---|
| 下载 | 50/50（26 领域；curl 传输；本轮全幂等跳过，PDF 复用首轮产物） |
| 解析入库（官方链路） | 50/50 解析成功，A6-V 门类库内探针 50/50 |
| 内容分类 | 50/50 分配到 5 门类库：计算机与人工智能 18 / 自然科学与地球科学 15 / 生命科学与医学 10 / 经济与社会 5 / 工程与能源 2 |
| 内容标签 | 1321 个文档 part 全部打标，0 失败 |
| 复现项目库 | Corpus-Chunks800 = 2,516 · Corpus-Struct = 1,466 · Corpus-Paras = 11,296 chunks；dense 冒烟 10 chunks、top1 命中 Attention 论文（0.708） |

## 2. 检索回归（Stage 6）

**9/10（90%）**，达标线 90%。唯一 FAIL 的 BQ06（极端降水）为已知分块窗口工件：
金标文档命中（doc_hit=True），但确切词组 "precipitation efficiency" 位于深层
part，未进入 top-3 内容窗口。该题在 Stage 7a 中通过 skill 的长文续读条款完成
取证并正常作答。

## 3. 三轨对照（Stage 7，同一 omp 引擎作答）

| 轨道 | 检索 | 时延 | 金标关键词进入回答 |
|---|---|:---:|:---:|
| A · QDCVR v2 skill 流程 | Phase1 向量均 **1.94 s**（top1 全部命中金标）+ 读正文 0.8s/篇 + 2 题兜底 ~1.4s | 检索段 ~3-4 s/题（回答由执行 Agent 撰写，不计时） | 未测量（五段式回答为长文本，关键词粗检不适用） |
| B · 裸 Agent | 无索引，自行翻 50 个 md | 均值 **55 s**（32-107 s） | 9/10 |
| C · dense 复刻 | 均值 **0.72 s**（Corpus-Chunks800 top-10） | + 作答 22 s | 10/10 |

**门控行为（Track A）**：10 题中 8 题 ≥6 快速退出；BQ06 初始 5/8（头窗止于摘要）
触发长文续读条款；BQ10 top chunk 为参考文献页（4/8）触发 Phase 2 定向兜底——
两条兜底路径均在所属门类库内一跳定位到证据章节后转为 8/8。

## 4. 诚实披露

1. **two_stage 引擎在当前拓扑下不可用作回归通道**（本次执行中发现）：Stage 5
   建 Corpus-* 后，整库 two_stage 被重复分块挤占（7/10），按库限定 two_stage 更
   差（3-4/10，重启后端无效）——检索回归与 Track A 因此统一使用
   `kb_search_vector`（skill Phase 1 规定工具）。该引擎缺陷已在 PIPELINE 故障表
   登记，属平台待修项。
2. **MCP kb_list lightweight 偶发空 catalog**（上游响应缺 success 标志时原样透
   传）：62 号首跑因此空转，已加双形状回退修复。
3. **证据预算**：A/C 的统一作答使用 4000 字符证据包，长论文深处的细节可能不在
   窗口内（上一轮 BQ01 曾因此弃答）；本轮 A 轨凭借 chunk 锚定 + 续读条款全部完
   成取证，未出现弃答。
4. **LLM 方差**：B/C 回答由 omp 生成，两轮之间金标词命中数有 ±1 波动
   （B 10→9、C 9→10），符合已记录的判读方差范围；本报告不做轮次挑选。
5. **单机单轮**：本轮为单次完整执行，未做多样本统计检验；时延数字受当时本机负
   载影响。

## 5. 结论与改进方向

- **流水线可用性**：九阶段全部跑通；发现并修复 3 个流水线缺陷（60 号 survey
  空摘要、62 号空 catalog 空转、70 号内联冒烟误判），均已固化为代码修正并记入
  故障表——这正是"执行 PIPELINE 保证没有问题"的目的。
- **平台 strengths**：官方解析链路 50/50 稳定；向量优先检索在本语料上 10/10 top1；
  门类化知识库 + 内容标签体系工作正常；skill 的兜底机制（续读/定向再检索）真实有效。
- **平台待修**：①two_stage 按库限定作用域失效（本轮最严重的发现，需修
  backend 的 KB 作用域解析）；②kb_list lightweight 需容忍上游响应缺 success；
  ③`.md.md` 双后缀与整篇名 404 问题建议在 save_parsed/create 层统一。
- **下一步**：将 two_stage 作用域修复后，把 two_stage 重新纳入回归对照；为
  Track A 增加自动化关键词粗检以外的 judge 维度（可选）。
