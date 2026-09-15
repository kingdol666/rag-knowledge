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

## 真实场景泛化(E19, 2026-09-16): 用户上传文档 × 同一算法矩阵

`user_scenario.py` + `../scripts/29_real_scenario_test.py` 把八算法矩阵从冻结
SciFact 语料移植到**任意用户上传文档**, 与 E16 完全解耦:

- **生产 KB**: `kb_doc_create`(平台真实用户路径: tree-fs + 后台向量/图索引,
  大文档自动按 "(part N of M)" 拆分) → `qdcvr` 直接在该库上两阶段+内容裁决。
- **基线 KB**: 各论文自己的分块方案(suite 侧复现) `UserDemo-{Chunks800,Struct,
  Paras,Raptor}` — `index_kb.items_*/build_kb` 与 `raptor.build_tree` 已参数化
  (默认值不变, E16 行为逐位保留)。
- **问题**: omp Agent 从文档内容生成(附逐字金标引文+期望答案, 全程留痕);
  **作答**: 同一 omp Harness 同一模型同一开放 QA prompt; **评审**: 独立 omp
  Agent 注入金标引文; **中间 Agent** 对匿名答案排名。评测命中按**文档级**
  归一(part 后缀剥离后与源文档比对)。

### 泛化过程中发现并修复的平台缺陷(P1 级)

`/api/v1/search/index-document` 的增量 BM25 更新把调用方原始 `kb_id`(常为
KB **名**)存入倒排, 而检索侧 `resolve_kb_ids_with_children()` 归一化为
**UUID** → 新建库(后端启动后经 kb_doc_create 上传)的 KB 限定两阶段检索
stage1 恒为 0(静默)。全量重建路径存的是规范 UUID, 故 KB-SciFact 等老库
不受影响 — 该缺陷只咬"后端启动后新上传"的真实用户。已修复: 增量更新改存
`owner_kb_id`(UUID) + 路径统一正斜杠(修复与 ChromaDB 元数据不对齐)。
验证: KB-UserDemo 限定检索 stage1 0→13, 中文题 qdcvr hit@1 0→1。

### 首轮实测要点(2 文档: 英文架构指南 15.3KB + 中文投稿规划 6.9KB)

- 生产 KB 上传+后台索引可查: 7.2s; 四基线索引全探针通过。
- **真实困难案例**: "HARD DISCARD 阈值"英文题 — 生产库将 ARCHITECTURE 拆成
  15 个 part(≈1KB/片, 上下文稀释), 且中文文档的 QDCVR 描述块与问题语义
  更近, BM25 与向量双双把竞争文档排前; qdcvr 的内容裁决只能在召回候选内
  重排(recall-bounded), 无法无中生有。suite 侧 dense_rag(整文档 3200 字符
  块)答对该题 — 生产分块粒度 vs suite 分块粒度是真实差异轴, 如实入报告。

### 复现审计(2026-09-16): 全轨重跑 + 逐项对比

F/R 两轨按 pipeline 重跑并与历史 run 逐项对比(compare_runs.py), 结论:
- **E16 矩阵**: 重跑 240/240 证据/作答/判分全部缓存回放, 与权威 run
  20260914T194057Z **9837 字段逐位一致(0 diff)** — 检索层+作答层+评审层全可复现。
- **功能轨(F)**: 经验套件 884/887 一致(唯一差异是 E3 首轮 reset.deleted 3→0,
  为运行前遗留状态不同, 两轮均收敛 remaining=0); ops/e2e/scale/E4/判分一致性
  五对产物聚合层 0 差异, 差异全部落在溯源字段/环境清单/LLM 评审逐条方差。
- **检索轨(R)活检阶段**: R1 SciFact qdcvr hit@1 0.7667 与历史一致; R1b 曾因
  并发执行污染下滑 0.25, 串行重跑恢复至会话方差内(陷阱⑭ Δ≤0.05-0.1)。
- **R3(HotpotQA) 修复链**: retrieval_track.sh 缺 RAG_BENCH_WEB_URL 导出(已修)
  + 遗留实验 KB 挤占 balance 候选池 + 重复构建累积 497 个 "(1)" 副本(含反斜杠
  路径) → stage2 doc_path $in 全失配 → two_stage/qdcvr 静默归零。平台修复:
  two_stage_search_service 在 BM25 构建与候选产出统一正斜杠。
- **新陷阱速查**: ㉕compare_runs 只匹配 module_*.json, 对新产物是空对比假
  PASS(已修: 回退到双方共有顶层 JSON, 溯源字段跳过); ㉖两轨并发共享单后端
  不安全(web 拒连+互致 KB 污染), pipeline 注释"完全独立"仅指逻辑独立;
  ㉗文档删除不失效内存 BM25, 批量删改后须重启; ㉘hotpot 重建须空库起步,
  反复构建产生 (N) 改名副本 + 静默去重叠加。
- **遗留待修(平台 P1, E8 通道)**: tree-fs 创建层对同名冲突自动改名 "(N)" 后,
  向量元数据仍记**改名前**请求名(BM25/YAML 世界 = "(1).md", ChromaDB 世界 =
  "X.md") → 全局 two_stage 的 stage2 `doc_path $in` 对该库**永久静默失配**
  (61 号脚本的 two_stage/qdcvr 通道 0, 而 dense/KB 限定/oracle 正常)。
  kb_get_documents 与磁盘清单亦不同步(YAML 与 tree-fs 双世界)。修法方向:
  改名同步向量元数据, 或 create 前做含不可见注册项的查重; 修复前 E8 的
  全局两阶段协议不可在干净重建语料上复现(09-14 历史数字产生于失配发生前)。
