# 论文实验章节写作方案（2026-11-12，基于三次独立运行的有效结果）

> 数据源：`artifacts/final_bench/`（权威值）+ `artifacts/replication_bench_20261112/`（复现证据）
> + `artifacts/demo-20261112/`（回答级证据）+ `RESULTS.md`/`RESULTS-REPLICATION-20261112.md`。
> 原则：论文主数字用 final_bench 权威值；复现性小节引 R3；每个 claim 标注证据路径。

---

## 0. 三个前置问题的直接回答

**Q1 哪个实验结果最准确？**
按"跨独立运行稳定性"分级（详见 §1 证据分级表）：
- **最准（可当确定性常数）**：A1b 54.2%（两次独立运行逐题 100% 一致）、A2 34.7%（同）、F-BM25 24/40（三态逐题零翻转）。
- **最准的主结果**：A0h 70.8-72.2%（三次运行 72.2→70.8→70.8，逐题一致率 98.6%，臂序三跑全保持），
  其对 A0 的显著性两次独立复现（p=6.1e-05 / p=0.0005）。
- **只写定性**：A3（路由塌陷 72/72→37-49/72 三跑稳定，端到端数值不稳 45.8↔34.7）、A1 readall（containment 上界）、
  floor 的 dense/RRF 列（平台组成指纹，跨环境不可横比）。

**Q2 哪个最能体现系统优势？**
**A0h vs A0 的主消融 + A2/A3 两个机制隔离 + A0h vs PD 的组织价值对比**，四件套缺一不可：
1. A0h vs A0（+20.8pp，p≈1e-4，两次复现）→ "完整系统显著优于其剥离版"；
2. A2 无证据门 34.7% 显著劣（p=.0227/.0066 两次显著）→ **内容验证机制的价值被统计隔离**（系统核心卖点）；
3. A3 无描述层：路由 72/72 → 51.4%/68.1% 散布 → **内容组织的路由价值被隔离**；
4. A0h vs PD（7:1 qid 配对，p=.0703 方向性）→ **同判卷条件下，层级化组织优于无组织的大范围向量搜索**
   ——这条是回应"你们和向量 RAG 有什么区别"的关键证据。
另：字节 309KB = 通读上界的 1/80、tool 13.8s < readall 253.7s → "读取经济学"论据。

**Q3 要不要和传统 RAG 比？**
**不需要以打赢传统 RAG 为卖点，但需要三个防审稿人动作**（见 §3 详细策略）：
① floor 附表（已有，BM25/dense/RRF，定位=sanity 下限）；② **A1b/PD 就是"传统向量 RAG 的强化形态"对照**
（A1b=朴素向量+判卷、PD=无组织精确检索+全窗判卷——给对手同样的判卷引擎后我们仍赢/平，这正是最公平的比较）；
③ 精确措辞：系统的贡献不在向量召回本身（向量检索是系统的底层候选源之一），而在**内容组织（层级库+描述层）
与内容验证（证据门+判卷+溯源）**两层机制——因此对比设计是"同底层、去机制"的自我消融 + "同判卷、无组织"的 PD，
而非召回率竞赛。

---

## 1. 证据可信度分级（哪些数字能进论文、怎么写）

### Tier A（主表数字，三次运行/两次显著）
| 数字 | 值 | 证据 | 写法 |
|---|---|---|---|
| A0h | **72.2% (52/72)**, CI [.610,.812] | final_bench/s6_stats.json | 主表 + 括注 R3 复现 70.8%（98.6% 逐题一致） |
| A0h vs A0 | +20.8pp, **p=6.1e-05** | s6_stats + R3 p=0.0005 | "显著优于（两次独立运行均 p<0.001）" |
| A0 | 51.4% (37/72), CI [.401,.626] | 同上 | 基线行 |
| A2 无证据门 | **34.7% (25/72)** | 同上 | "去除内容验证后降至 34.7%（p=.0227；复现轮 p=.0066，两次独立显著）" |
| A1b 十库向量并集 | 54.2% (39/72) | 同上 | "与 A0 无显著差（p=.69）"——朴素向量+判卷的天花板 |
| A1b/A2 稳定性 | 逐题 100% ×2 | replication s6d | 复现性小节："跨日/跨平台状态逐题完全一致" |
| 字节/时延 | 309KB/题、13.8s vs 24.3MB、253.7s | traces | "读取经济学"段 |
| 路由 | A0 72/72 vs A3 37/72 (51.4%) | traces route_correct | 描述层消融段 |

### Tier B（可写，注明性质）
- PD 63.9%（R3 62.5%）+ A0h vs PD 7:1（p=.0703，写"方向性优势/directional"）
- A0f 62.5%（消融中间臂，展示设计迭代路径）
- OOD 门控数值：**精确表述**——A0 证据门对 2/4 域外探针拒绝；A0h 全窗证据包使域外题也产生存活段（0/4 拒绝）。
  → 检索层门控数值如实报告，但**拒答主张不建立在它上面**（拒答主张由回答层承担，见 Tier C）。
- 漏检归因：35 缺口=路由 0/窗口 5/判卷未命中 30（其中 25=候选选择/段存活）→ 修复杠杆 +15/+8/+9

### Tier C（只写定性/案例）
- A3 端到端数值（45.8%↔34.7% 跨 run 不稳）→ 写"路由塌陷稳定复现；端到端受薄卡路由的基础设施敏感性影响，
  这本身反证描述层是路由稳定性的来源"
- A1 readall 100%（containment 上界，digest ~6079s/题 → "全库暴露包含短锚串，不代表回答能力"）
- floor dense/RRF（平台组成敏感）→ 附录只放 BM25（60%，n=40，三态一致）+ 口径声明
- 回答级信任证据（n 小，作案例研究）：claude 6/6 + omp 7/7（含诚实 NOT_FOUND）、DeepSeek-R1 端到端 8/8
  四维全对 0 幻觉（含 $294K 诚实边界处理）、金标回贴 179/179

### 禁写清单（红线）
1. **不得声称优于 CRAG/Self-RAG/RAPTOR/HippoRAG/LightRAG**（已 pin 未跑，需 LLM endpoint）——写 future work。
2. 不得做 2×2 组织×裁决交互项声明（开关未实现）。
3. 不得声称 0-8 rubric 已校准（无人工 κ）。
4. 不得把 floor 与臂同表直比（口径不同：floor 是检索 containment n=40，臂是证据包 containment n=72）。
5. 不得用检索层门控数值宣称"正确拒答"（那是检索阶段结果；拒答证据=回答层）。
6. R3 的 A3 数值（34.7%）不单独引用。
7. gold containment 是检索代理指标 ≠ 回答正确率——必须随表声明（s6_stats metric_note 原文可用）。

---

## 2. 实验章节布局（§ 结构 + claim→evidence 映射）

### §X.1 Experimental Setup（半页）
- 系统被测配置一句话 + 图（目录卡路由→描述层→宽网→判卷→逐字核验，即 A0h 数据流）
- 语料：10 域 138 文档 → 10 库 879 分卷 23.9MB；描述层每卷内容归纳
- 题集：72 gold（每题 evidence 锚经脚本实测在库，防编造机制）+ 4 OOD 探针；2 cross 占位未入轮（披露）
- 判卷：Laya（本地 GPU、引用式 fail-closed、real_engine 标记）
- 公平性契约：同题集/同判卷/同语料；A1b/A2 十库 scoped union；A3 孪生库+name-only 卡；
  污染审计（qid 唯一、零路由卡泄漏、候选 100% 在评测范围内、金标回贴 179/179）
- **复现协议**：三次独立执行（11-11 晋升轮、11-11 capture 复现、11-12 R3，跨日+跨平台状态），
  稳定性指标=逐题一致率
- 表：臂定义表（每臂=一个设计开关）

### §X.2 Main Result（主表 + 主张）
**表 1**：A0/A0f/A0h/PD/A1b/A2/A3/A1 × {gold hits, Wilson CI, vs-A0 McNemar p, bytes/q, tool s, routing}
- Claim 1：**A0h 72.2% 显著优于基线 A0 51.4%（p=6.1e-05；独立复现 p=0.0005）**，
  读入字节为通读上界 1/80（309KB vs 24.3MB），工具时间反降（16.3→13.8s）
- Claim 2：去除证据门（A2）→ 34.7%，两次独立运行均显著劣 → 内容验证是必要组件
- Claim 3：同判卷条件下，无组织的 PD 63.9% 仍低于 A0h（7:1，directional）；朴素向量并集 A1b 54.2% ≈ A0
  → 组织+导航的贡献独立于判卷与召回
- 每条 claim 后括注 R3 复现数字（"replicated at 70.8%, 98.6% per-question agreement"）

### §X.3 Ablation & Mechanism Isolation（三开关叙事）
按"设计决策"组织而非按臂组织：
1. **内容验证（证据门）**：A0 vs A2 数字 + OOD 门控行为（精确表述）+ fail-closed 设计动机
2. **内容组织（描述层路由）**：A0 72/72 vs A3 37/72 路由塌陷；端到端差异不显著（p=.45）的诚实解释
   （宽网+判卷补偿）+ R3 发现"薄卡路由的基础设施敏感性反证描述层是稳定性来源"
3. **导航层**：A0h vs PD vs A1b 三方对比（组织缩小搜索空间同时提升 chunk 定位与判卷段存活）
4. **上界与成本**：A1 readall 的 containment 上界与 6,079s 消化成本 → "containment 不是目标，聚焦读取才是"

### §X.4 Failure Attribution & Design Iteration（漏检归因 → A0h 的由来）
35 缺口分类（路由 0/窗口 5/判卷 30）→ 三个修复杠杆的增益分解（chunk 并集 +15、全窗判卷 +8、精确检索 +9）
→ 剩余 20 深部判卷未命中（实体型金标 Laya<0.5）= known limitation + future work（题型分层判卷/词面回退）。
这一节是"工程诚实"的加分项，也是 A0h 设计合理性的最强论证。

### §X.5 Reproducibility & Stability（复现性小节——本论文的差异化优势）
- 三次独立运行表：逐题一致率（A0f/A0h/PD 98.6%、A1b/A2 100%、A0 94.4%）、臂序 3/3 保持、
  关键显著性两次复现、跨 run McNemar 全不显著
- 披露：A3 的基础设施敏感性（薄卡路由）；语料演进 confound（文学库 434→461 卷）；
  平台 chroma 段脆弱性 + 预检/干净重建 SOP/中止轮隔离等缓解措施（threats to validity）
- 这一节把"实验是否可信"变成论文卖点：**多数 RAG 论文只有单次运行，本工作提供三次跨日运行的逐题复现证据**

### §X.6 Answer-Level Trust Evaluation（案例研究，非统计主张）
- 真实 Agent 车道：claude 6/6 + omp 7/7（220-520s/题），doc_path 溯源 + 逐字引用 + 可信度标注
- 域外诚实拒答：AG7 NOT_FOUND（显式结论+盲区申报+拒用弱相关文档）
- 端到端案例：全新论文解析→入库→检索 8/8 四维全对（含 $294K 诚实边界处理）
- 表：逐题（问题/引用 doc_path/逐字句/可信度/判定）——放补充材料，正文给汇总行

### §X.7 Baselines & Scope（定位声明 + floor 附表）
- floor 附录表：BM25 60%（n=40，三次运行逐题零翻转）作检索下限 sanity；dense/RRF 附口径声明或省略
- 内容认知基线（CRAG/Self-RAG/RAPTOR/HippoRAG/LightRAG）：仓库已 pin + 适配契约 + 成本闸设计，
  **因无 LLM endpoint 未运行，不声称比较结果**——future work
- 边界声明四条（= 禁写清单的红线 1-4 落进正文）

### 图/表清单（建议 4 表 3 图）
- 表 1 主结果（八臂）、表 2 消融三开关（可并入表 1）、表 3 漏检归因、表 4 复现性（三跑逐题一致率）
- 图 1 系统数据流（A0h）、图 2 主结果 CI 瀑布图（八臂 Wilson CI 一张图，视觉冲击最强）、
  图 3 读取经济学散点（x=bytes/q 对数轴，y=gold rate，标出 A1 上界/A0h/PD/A1b/floor）

---

## 3. "和传统 RAG 比"的精确策略（措辞模板）

**不要写**："我们的方法优于传统 RAG"（会招来 naive baseline 缺失的拒稿理由）。
**要写**（三段式）：
1. *"The system uses dense vector retrieval as one of its candidate sources; its contribution lies in the
   layers above retrieval—content organization (hierarchical libraries with per-volume descriptions) and
   content verification (citation-style adjudication with an evidence gate)."*（定位句，Methods 末尾）
2. *"We therefore compare against (i) the strongest unorganized variant that shares our adjudication
   engine (PD: flat union search over all ten libraries), (ii) the naive vector-union variant (A1b), and
   (iii) retrieval-only sanity floors (BM25/dense/RRF, appendix)—isolating the contribution of organization
   and verification rather than of vector recall itself."*（实验设计句）
3. *"Removing content verification drops the baseline pipeline from 51.4% to 34.7% (both runs significant);
   replacing tiered navigation with flat precise search yields 63.9% vs our 72.2% (7:1 in favor, directional);
   stripping descriptions collapses routing from 72/72 to 37/72."*（结果句——用消融数字回答"凭什么说你不是 RAG"）

这样审稿人的三个必问问题都有表/数字可指：①"和 naive RAG 比了吗"→A1b/PD/floor；②"增益是调参还是机制"→
A2/A3 消融两次显著；③"结果可信吗"→三次运行逐题复现。

## 4. 可选强化项（按性价比排序）
1. **【已完成 2026-11-12】A0h vs A1b 直接配对 McNemar：final = 零回归(0/13)，p=2.4e-04；R3 = 零回归(0/12)，p=4.9e-04**
   —— "推荐主臂显著优于朴素向量并集（传统 RAG 形态）且无一题回归，两次独立复现"。
   这是此前 s6_stats（只做 vs A0）漏掉的强主张，建议升入主表；A0h vs PD 确认为 1/7、p=.0703（directional）。
2. **【高】判卷内核声明**：Laya real_engine 标记 + fail-closed 语义写进 Methods（已有 real_engine=True 证据）
3. **【中】拿到任一 OpenAI-compatible endpoint 后跑 CRAG 或 LightRAG 20 题成本闸**——即使只进附录也堵住最大的审稿风险
4. 【中】5 次重复运行（红线"每个 LLM 通道 ≥5 次"仅对 LLM 通道适用；机械臂 3 次已足，若判卷或路由引入 LLM 需补）
5. 【低】qrels 池化标注 + 人工 κ（时间允许再做）

## 5. 论文数字口径备忘
- 主数字一律 final_bench；R3 数字只出现在复现性小节，格式 "（replicated at X%, k/72 agreement）"
- n 的表述："n=76 per arm (72 gold + 4 out-of-domain probes); two cross-domain placeholders excluded (disclosed)"
- 三套题集（BQ/QK/R2Q）数字不得混用——本论文实验只用 ladder 题集（questions.jsonl）
- readall 的 digest 6079s 是 bytes÷吞吐率估算，写 "estimated digest time" 不是实测墙钟
