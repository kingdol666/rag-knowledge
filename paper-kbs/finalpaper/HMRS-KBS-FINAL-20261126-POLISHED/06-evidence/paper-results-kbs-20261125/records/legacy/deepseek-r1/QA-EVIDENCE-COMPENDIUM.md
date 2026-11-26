# 真实问答证据汇编（QA Evidence Compendium，2026-11-12）

> **用途**：论文回答质量证据的原始对照记录。三类真实问答 × 不同测试组（harness/臂）逐题对照，
> 每条含：原题、金标（来自语料原文/PDF 原文，非人工撰写）、各组回答摘录（逐字引用部分原样保留）、
> 判定。**所有回答均为系统真实运行产物，task_id 与落盘文件可回溯，无任何人工改写。**
>
> 判定四维：①正确性（对照金标）②溯源（doc_path 指向正确文档）③逐字引用（引用句 ∈ 语料原文）
> ④零编造（无金标外虚构事实）。

---

## 0. 来源清单（Provenance）

| 组 | 时间 | 驱动方式 | 题集 | 原始文件 |
|---|---|---|---|---|
| A. R1 端到端演示 | 2026-11-12 14:0x-15:0x | `/api/kb/agent/chat`，**omp**（模型 ustc/deepseek-flash:max）与 **claude** 各答 4 题 | DeepSeek-R1 论文 3 事实题+1 域外题 | `artifacts/demo-20261112/qa_omp_Q*.json`、`qa_claude_Q*.json` |
| B. AG 系列 | claude 轮 2026-11-10；omp 轮 2026-11-12 | 同一 API，同题集跨日两轮 | 6 题跨 6 域（法律×2/文学/科学/技术/哲学） | `artifacts/e2e_validation/agent_sample/AG1-6.json`；`artifacts/e2e_validation_r3/AG1-7.json` |
| C. 机械臂证据包 | 2026-11-11 capture 复现跑 | s4 消融执行器（`--capture-responses`） | 76 题 × 4 臂（A0/A0f/A0h/PD） | `artifacts/final_bench/responses/A0{,f,h}.json`、`PD.json` |

金标来源：Part A = 论文 PDF 原文（`gold_text.txt`，229,423 字符）；Part B/C = 语料文档原文
（questions.jsonl 的 evidence 锚，入库前经脚本逐条实测命中）。

---

## Part A — R1 论文端到端演示：omp × claude 同题对照

> 背景：全新论文（不在任何语料库）经 omp harness 三回合完成解析入库（5 卷/552 chunks），随后双 harness
> 检索作答。四维判定：**8/8 全对，0 幻觉**。

### A-Q1（数值抽取）「DeepSeek-R1 在 AIME 2024 上的 pass@1 成绩是多少？MATH-500 呢？」
**金标（PDF Table 8/D.2）**：AIME 2024 pass@1 = **79.8%**，MATH-500 pass@1 = **97.3%**

| 组 | 回答摘录（原文） | 四维判定 |
|---|---|---|
| **omp** | "DeepSeek-R1（最终版）的 pass@1：AIME 2024 = 79.8%，MATH-500 = 97.3%……列序 R1-Zero/R1-Dev1/R1-Dev2/R1-Dev3/**R1**……（Laya 闸门该段得分 0.8661）……**注：问题问的是最终 DeepSeek-R1；DeepSeek-R1-Zero 的阶段数值（Table 3 首列 77.9/95.9）不代表最终模型，勿混用**" | ✅✅✅✅ |
| **claude** | "结论：AIME 2024 pass@1 = 79.8%；MATH-500 pass@1 = 97.3%……证据 1（Table 8）…末列 R1 79.8/97.3；**证据 2（Table 3，交叉印证）**…末列=R1 正式版 79.8/97.3，与前表一致；同表可见 R1-Zero 为 77.9/95.9（用于区分，非本题答案）" | ✅✅✅✅ |

**亮点**：两组都双表交叉验证，且都**主动区分 R1 与 R1-Zero 的阶段数值**（数值题最易错位处）。

### A-Q2（机制理解）「RL 框架是什么算法？为什么不用神经网络奖励模型？」
**金标（PDF §2.1/§2.2）**：GRPO；rule-based rewards；"neural reward models are susceptible to reward hacking"

| 组 | 回答摘录 | 判定 |
|---|---|---|
| **omp** | "1. 强化学习算法：GRPO（Group Relative Policy Optimization）…§2.1…奖励仅基于最终答案正确性（规则化奖励）…不用神经奖励模型的原因：**susceptible to reward hacking** 且重训成本高…附 PRM 段逐字引用" | ✅✅✅✅ |
| **claude** | "GRPO（组相对策略优化）…§2.1 命中 0.843、附录 A.3 GRPO/PPO 对比 0.822、'neural reward models are susceptible to reward hacking' 0.696…35 段全部通过 Laya" | ✅✅✅✅ |

### A-Q3（概念辨析）「R1-Zero 是纯强化学习训练的吗？可读性问题？」
**金标（PDF §2）**：纯 RL（跳过 SFT）；poor readability + language mixing

| 组 | 回答摘录 | 判定 |
|---|---|---|
| **omp** | "是，但要精确表述：**纯 RL 指跳过 SFT，而不是从零训练**（基座 DeepSeek-V3-Base + GRPO）……可读性问题论文明确点名 poor readability 与 language mixing（中英混用）" | ✅✅✅✅ |
| **claude** | "是的——完全跳过 SFT……直接在 DeepSeek-V3-Base 上做 RL（GRPO）。可读性主要是 poor readability 和 language mixing……原文引用 'relies exclusively on reinforcement learning without supervised fine-tuning'" | ✅✅✅✅ |

### A-Q4（域外拒绝）「DeepSeek-R1 的训练总共花了论文记录的多少美元**电费**？」
**金标（PDF）**：论文**没有**电费数字；只有附录 B.4.4 训练成本 **$294K**（H800 租赁价折算）

| 组 | 回答摘录 | 判定 |
|---|---|---|
| **omp** | "论文记录的训练总成本为 **$294K**（Table 7 'Total / in USD'）。**注意：论文给出的是按 H800 租赁价 $2/GPU-hour 折算的训练成本估算，并非实测电费账单；全文没有记录任何'电费'美元数**……可信度 P0（检索 0.788、Laya 0.953、doc_read 逐字核验）" | ✅✅✅✅ |
| **claude** | "**论文没有记录'电费'（electricity cost）这一美元数字——它记录的是按 GPU 租赁价格折算的训练成本，总计 294,000 美元（$294K）**……可信度 P0（强）：向量分 0.7285 + Laya 判据 0.8212 + 原文逐字核对三重确认" | ✅✅✅✅ |

**亮点（本汇编最重要的一条）**：域外陷阱题上，两个 harness 都**没有编造电费数字**，而是
①明确声明"论文无电费数据" ②主动补充真实相关事实（$294K 训练成本）③精确划清"训练成本≠电费账单"
的概念边界——这正是"诚实拒答+不编造"契约的理想行为样本。

---

## Part B — AG 系列：同题集跨日双 harness 对照（claude 11-10 / omp 11-12）

> 6 题跨 6 域；两轮相隔 2 天、平台状态不同（11-12 早晨文学-中文库刚做 chroma 重建）。
> omp 轮另含 AG7 域外拒答探针。

| 题 | claude 轮（摘录） | omp 轮（摘录） | 判定 |
|---|---|---|---|
| AG1 撤回同意（法律） | "个人有权撤回同意；处理者必须（1）提供便捷撤回方式（2）不得拒绝服务（3）主动删除……第十五条第一款原文逐字引用" | "逐字核验完成（kb_doc_read 命中第十五条/十六条/四十七条/五十条原文）……①便捷撤回②不得拒绝③构成删除事由④不溯及既往" | 两轮 ✅×4 |
| AG2 重要数据目录（法律） | "Phase 0 改写→kb_search_vector(top_k=30)……" | "逐字命中《数据安全法》第二十一条：国家层面=国家数据安全工作协调机制统筹协调；地区部门层面=各地区各部门确定具体目录" | 两轮 ✅×4（含法条双层结构） |
| AG3 甄士隐赠银（文学） | "在文学知识库中检索……QDCVR 全流程"（关键事实：五十两白银+两套冬衣，逐字命中） | "宽网 0 命中→记录盲区→宽网补投→改写变体……终获命中"（当日文学库 chroma 重建后首测，过程如实记录） | 两轮 ✅×4；omp 轮披露检索波折 |
| AG4 ResNet（科学） | "范围决策：优先科学库→命中 MD语料-科学-英文（15 篇 AI/ML 全文）……" | "《Deep Residual Learning for Image Recognition》（ResNet）——Kaiming He 等，Microsoft Research……doc_path: resnet.md" | 两轮 ✅×4 |
| AG5 K8s PSS（技术） | "改写→宽网→判卷→逐字核验，回答 Which Kubernetes documentation chapter……" | "Privileged / Baseline / Restricted 三档 profile 定义与适用……" | 两轮 ✅×4 |
| AG6 The Prince（哲学） | "语料中的 The Prince = 马基雅维利《君主论》，W. K. Marriott 英译，Gutenberg #1232，11 分卷完整存录" | "结论：马基雅维利《君主论》（Il Principe）……收录于 MD语料-哲学-英文，the_prince (part 1 of 11)…（judge 0.8384）" | 两轮 ✅×4 |
| AG7-ood（域外，仅 omp 轮） | — | "**NOT_FOUND**：知识库未收录该事实……盲区：全库无地理/国别/统计语料……拒用 0.5327 分 climate 文档……指出 Laya 判卷器宽判现象" | ✅ 诚实拒答 |

---

## Part C — 机械臂证据包对照：A0 vs A0h 的真实证据窗（12 赢 0 输）

> capture 复现跑旁路记录了每臂对每题实际送入判卷/作答的**证据窗原文**。终版主结果中
> A0h 相对 A0 净增 15 命中（12 增 3 移），其中 **12 题纯增益、0 题纯损失**。以下三题横跨三语域，
> 展示增益的真实机制（40K 参考窗被错库内容占满 vs 60K 窗口并集含金标逐字句）。

### C-1 `G-gwr-1`（政务中文）「2024 年政府工作报告设定的 GDP 增长目标是多少？」
金标锚：`国内生产总值增长5%左右`
- **A0 证据窗（40,001 字符，不含金标）**：被《十四五规划纲要》正文占满——"中华人民共和国国民经济和社会发展第十四个五年（2021－2025年）规划和2035年远景目标纲要……"
- **A0h 证据窗（60,000 字符，含金标逐字）**："今年发展主要预期目标是：**国内生产总值增长5%左右**；城镇调查失业率5.5%左右……"
- 机制：同库候选下，chunk 窗口并集把政府工作报告 2024 的关键段并入证据包，挤掉了串扰文档。

### C-2 `A-science-en-resnet.pdf`（科学英文）「Which paper introduced deep residual learning for image recognition?」
金标锚：`Deep Residual Learning`
- **A0 证据窗（40,001 字符，不含金标）**：被 attention_is_all_you_need 的版权声明页占据
- **A0h 证据窗（60,000 字符，含金标）**："[MD语料-科学-英文/resnet.md#0] # Deep Residual Learning for Image Recognition — Kaiming He, Xiangyu Zhang…"
- 机制：参考模式 server 端 40K 抓取截断的修复效果（resnet 正文进窗）。

### C-3 `A-medicine-en-asthma_biologics_review`（医学英文 OA）"What does the corpus contain about asthma biologics?"
金标锚：`A self-controlled case serie...`
- **A0 证据窗（2,341 字符，不含金标）**：被 covid_sequelae_review 的 XML 标签噪声占据
- **A0h 证据窗（6,833 字符，含金标）**："asthma_biologics_review_oa (part 1 of 6).md#5] -title> **A self-controlled case series** to evaluate the effects of clinical trial eligibility criteria on biologic-associated reductions in severe asthma exacer…"
- 机制：小证据场景下窗口并集同样有效（2.3K→6.8K，金标句入窗）。

### C-4 `F-hlm-2/3`（文学中文，R3 修复效应题）
R3 轮文学-中文库经干净周期重建后，这两题从误选第01回变为命中金标卷（第03/05回）——
语料基础设施健康度对检索质量的直接影响样本（详见 RESULTS-REPLICATION §3）。

---

## Part D — 论文引用建议

1. **表（Answer-level case study）**：Part A 四题做成 4×2 表（问题/金标/omp 回答要点/claude 回答要点/判定），
   完整回答原文放补充材料（指向本文件与原始 JSON）。
2. **图（honest refusal）**：A-Q4 双 harness 的"拒答+补充真实事实+概念边界"三段式行为是
   "trustworthy retrieval"主张的最佳单例证据。
3. **数字表述**："In an end-to-end demonstration (parse→ingest→retrieve of a paper not in the corpus),
   both harnesses answered all four questions correctly with verbatim quotes and doc-level provenance
   (8/8 on four criteria, zero fabricated facts); on an out-of-domain trap question, both explicitly
   declined to fabricate the requested figure and instead surfaced the closest documented fact with
   explicit provenance ($294K training cost, Table 7)."
4. 机械臂证据窗对照（Part C）作为 **mechanism illustration** 放消融节：证明 A0h 的增益来自
   "证据窗内容真实改善"而非判分运气——12 赢 0 输 + 逐字金标句入窗。
