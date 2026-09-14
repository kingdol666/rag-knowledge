# REPRODUCTION NOTES — DeepRead 基线矩阵复现口径与偏差

复现对象: **DeepRead: Document Structure-Aware Reasoning to Enhance Agentic Search**
(arXiv:2602.05014v3, 2026-02-12)。复现范围为该文 Table 1 的**全部对比算法**
(含本文方法 DeepRead 本身), 在本项目冻结语料 (BEIR SciFact 148 篇, KB-SciFact)
与冻结查询 (30 条 claim, 官方 qrels) 上运行, 检索层指标 + 统一作答 + 第三方
Agent 判分。任何与本论文设置不一致之处都在此显式登记; 未登记 = 忠实实现。

## 逐算法对照

| 本实现 | 论文方法 (Table 1) | 论文设置 | 本实现 | 偏差 |
|---|---|---|---|---|
| `dense_rag` | Dense RAG | chunk 800 tok/overlap 400, 稠密 top-10 | 同左; token≈4 chars 近似; 嵌入 bge-m3(被测系统自有) | ①嵌入模型 |
| `dense_rag_rerank` | Dense RAG w/ Reranker | 一阶段 30 候选 → Qwen3-reranker-8b → 截断至预算 | 稠密 top-30 → **omp Agent listwise 重排** → top-10 | ①②重排器代理 |
| `raptor` | RAPTOR | Collapsed Tree; node ≤800 tok; 5 层; cluster top-5; 检索 top-10 节点 | 同左; 聚类=互为 top-5 相似 union-find(嵌入同源) | ①③聚类算法 |
| `itrg_refresh` | ITRG (refresh) | 4 轮, 每轮 top-6 | 每轮以 claim+当前假设句 重检索; 证据仅保留本轮 | ①④假设生成模型 |
| `itrg_refine` | ITRG (refine) | 4 轮, 每轮 top-6 | 同上, 证据跨轮累积 | 同上 |
| `search_o1` | Search-o1 | structure 分块 overlap 0; 每次 search 返 2 chunks; 上限 50 轮 | 同左; **轮数上限 8** | ⑤轮数上限 |
| `deepread` | DeepRead (论文方法) | TOC 注入 + Retrieve(扫描窗 ω=(1,1), 段落坐标) + ReadSection(连续有序); ≤50 轮 | 同左, markdown 标题/段落结构替代 OCR 坐标; **轮数上限 8** | ⑤⑥结构来源 |

统一不变式(对全部方法对称):
- **同一语料、同一 30 条查询**(与套件 std2 赛道同源同序, 冻结于 `data/standard2/scifact/`);
- **同一作答 Agent、同一证据预算 4000 字符**(隔离检索差异的归因, 见下"评测协议");
- 检索层指标与套件同式: Hit@k / Recall@k / nDCG@10 / P@5 / MRR (BEIR qrels)。

## 偏差明细

1. **嵌入模型**: 论文 Qwen3-embedding-8b(8B, 未开源权重本地不可得)。本实现用
   被测系统自有的 `BAAI/bge-m3`(后端嵌入服务, GPU)。所有稠密基线与系统向量
   通道同嵌入源, 方法间公平; 与论文绝对数不可直接对比。
2. **重排器**: 论文 Qwen3-reranker-8b(交叉编码器)。本环境无该权重, 以 omp
   Agent 的 listwise 重排替代(一次调用对 30 候选输出 JSON 序)。这是重排质量
   的下界近似, 若该基线因此偏低, 方向对本系统(QDCVR)不利 — 保守偏差。
3. **RAPTOR 聚类**: 论文(沿 RAPTOR 原文)用 GMM 软分配。本实现以互为 top-5
   相似关系的 union-find 硬聚类近似, 摘要 ≤150 词由 omp Agent 生成。树落盘
   `cache/raptor_tree.json` 可完整审计。
4. **ITRG 内循环生成**: 论文策略模型 DeepSeek v3.2; 本实现统一走 omp Agent
   (实测 provider=ustc, model=deepseek-flash, temperature 默认)。轮内假设句
   ≤300 字符。
5. **agentic 轮数上限 8**(论文 50): 论文 Table 3 实测两法均值 5.8–11.0 次
   工具调用, 上限 8 覆盖其观测均值区间; 30 条查询 × ~10 轮的 50 轮上限在本
   预算下不可行。每次截断在 trace 中标记 `cap_reached`。
6. **结构来源**: 论文用 PaddleOCR-VL 解析 PDF 坐标。本语料为原生 markdown
   (BEIR SciFact 抽象层): 标题=层级、空行段=序列、坐标 (doc, sec, para)。
   语义等价, 无 OCR 误差项。
7. **语料形态退化(重要)**: SciFact 每篇 = 标题 + 单段摘要(中位 1278 字符)。
   因此 800/400 定窗、structure-o0 分块、段落单元**三者逐篇等长(1 块/篇)**,
   分块轴在本语料上不产生差异; 方法间差异来自检索策略(平铺 top-k / 层级
   摘要树 / agentic 定位-阅读), 而非分块。这是摘要级语料的固有属性, 与论文
   长文档场景(FinanceBench 财报/教材/小说)不同 — 结论外推需谨慎。
8. **评测协议差异**: 论文报 end-to-end accuracy(方法自带作答)。本矩阵把
   作答从检索中**剥离**: 每方法检索证据 → 同一 omp Agent、同一 4000 字符
   预算、同一冻结 prompt 作答 → 第三方 omp Agent(独立 fresh 进程, 注入金标
   文档) 0-10 打分。agentic 方法自己的 `Final Answer` 仍记录于 trace
   (`own_final_answer`)但不计分。目的: 分数差异可归因于检索质量本身。
9. **第三方判分**: 单一 judge(omp, fresh 进程, 与作答无共享上下文, 注入
   金标)。论文用 3 judge 做稳健性(DeepSeek V3.2 / GLM-4.7 / Qwen3-235B);
   本环境仅 omp 通道可用, 多 judge 稳健性未复现 — 已列入局限。

## 成本与缓存

- LLM 调用全部经 **omp RPC/oneshot** 协议, 以 (stage, prompt) SHA-256 哈希
  落盘 `cache/llm_<stage>_<hash>.json`; `DR_NO_LLM_CACHE=1` 可强制真实调用。
- 证据/作答/判分逐 (method, qid) 落盘 `cache/{ev,ans,judge}_*.json` → 断点
  续跑、逐位可复检。
- 全量 30 查询 × 8 方法的 LLM 量级: 重排 30 + RAPTOR 建树 ~35 + ITRG 假设
  ~180 + agentic 循环 ~250 + 作答 240 + 判分 240 ≈ **~1000 次**, 3 并发。

## 复现命令

见 `README.md`(一键) 与 `../TEST-PLAN.md` §Stage D(含端到端冒烟)。
