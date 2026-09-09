# 论文投稿总规划（Master Plan）

> **生成**: 2026-09-09 · 整合 VENUE-ANALYSIS / CIKM-WRITING-FRAMEWORK / BENCHMARK-TEST-PLAN v3.0 / reference 文献比对
> **结论一句话**: 主投 **CIKM 2027**（2027-05-23 截稿预测，悉尼），SIGIR 2027 AP Track 为加速备选（2027-01 预测），KBS 期刊保底。
> **当前最大缺口只有一个：标注评测集（Dataset C 等）尚不存在。**

---

## 一、项目完整执行流程（现状盘点 ✅）

系统链路已全部打通并全绿验证（2026-09-09）：

```
原始文档 (PDF/MD/Word/Excel)
   │  MinerU OCR 解析 (异步任务, test-parse 5s)
   ▼
解析产物落盘入库 (kb_doc_save_parsed)
   │  ① 磁盘 + .tree-fs.json + .knowledge-base.yml（5 层数据模型第 1-2 层）
   ▼
向量索引 (BGE-M3, ChromaDB, collection=kb_<uuid>)     ← 同名库 409 守卫防串号 ✅
知识图谱 (Neo4j, build-kb)                             ← 第 4 层
   │
   ├─ 检索四路: BM25 / 向量 / 图谱 / 标签 → 两阶段融合 (stage1 粗排→stage2 精排)
   ├─ QDCVR: 意图分类→KB 路由→两阶段召回→内容验证(0-8 rubric)→置信度分级→盲点声明
   ├─ 经验系统: E0-E12 生命周期 + P0/P1/P2 可信度 + 时效衰减 + 冥想自动归纳
   ├─ SOUL 人格: 蒸馏→记忆→训练(RL+好奇心)→人格问答(435s 实测可用)→评估→LoRA 导出
   └─ Agent 接入: 94 MCP 工具 + 19 技能 + 令牌鉴权(2026-09-09 上线)
```

**质量资产**：backend 139 单测 ✓ · kb-mcp 57 E2E ✓ · 全功能冒烟 60/60 ✓ · 鉴权 e2e 26/26 ✓ ·
集成整改 9 缺陷闭环 ✓ · `scripts/test_full_smoke.py` + `scripts/test_auth_e2e.py` 已入库可复跑。

**论文资产**（docs/paper/）：VENUE-ANALYSIS(123 行) · CIKM-WRITING-FRAMEWORK(526 行，逐段可填) ·
PAPER-FRAMEWORK(591 行) · SYSTEM-DESIGN-PHILOSOPHY(268 行) · reference/ 9 篇 PDF + 新颖性比对 ·
benchmark-web/ 计划 v3.0(410 行) + baselines.py/run_benchmark.py 骨架 + dashboard。

**唯一硬缺口**：`benchmark-web/benchmark/` 与标注数据集为空——论文数字尚无一存在。

---

## 二、目标会议/期刊与时间线（2026-09-09 校准）

| 目标 | 截稿（预测） | 距今 | 可行性 | 说明 |
|---|---|---|---|---|
| 🥇 **CIKM 2027** Full Paper | **~2027-05-23**（2026 模式：abstract 5/16，全文 5/23） | 8.5 个月 | ⭐⭐⭐⭐⭐ | 悉尼 2027-10-25；IR+KM+DM 完美匹配；Systems & Applications track 接受系统论文 |
| 🥈 SIGIR 2027 AP Track | ~2027-01-22（按 2026 惯例） | 4.5 个月 | ⭐⭐⭐ | Applied Research track 专为系统论文；若 QDCVR 算法贡献做深可冲 |
| 🥉 KBS 期刊 | 随时 | — | ⭐⭐⭐⭐ | 审稿 2-3 月，IF≈8.8，年内可见刊的保底 |
| WWW 2027 | **2026-10-18**（已确认） | 5 周 | ❌ 放弃 | 时间不足以完成标注+baseline+消融 |
| TKDE 期刊 | 随时 | — | 长线 | CIKM 被拒后的升级转投 |

**关键提醒**（CIKM 特有 desk-reject 陷阱，来自 2026 官方流程）：
1. **Abstract 截稿比全文早一周且冻结作者名单**——5 月中旬前定稿作者列表
2. **附录计入 10 页限制**——溢出内容必须进公开 artifact 或删除
3. 需写 **GenAI Usage Disclosure** 章节； EasyChair 的 reviewer nomination 未填 = desk reject

**结论：瞄准 CIKM 2027，8 个月做三件事——标注评测集、baseline 实验、论文撰写。**

---

## 三、同类论文与写作格式（reference/ 已备 9 篇）

### 3.1 必须击败的对手（Tier 1）

| 论文 | 会议 | 威胁点 | 我方差异化（写 Related Work 的核心话术） |
|---|---|---|---|
| **CRAG** (Yan 2024) | NAACL | 检索评估器 + Correct/Incorrect/Ambiguous 纠正动作，与内容验证强重叠 | CRAG 面向开放网页纠错；我们 content-overrides-vector 原则 + 0-8 三维可解释 rubric + 与 P0/P1/P2 经验可信度一体化 |
| **Self-RAG** (Asai 2024) | ICLR | reflection token 自评检索质量 | Self-RAG 需训练模型；我们零训练、运行时规则+LLM 混合验证，可解释可审计 |
| **MCP-Pyserini/RankLLM** (Ge 2026) | SIGIR | "首个 MCP-based RAG" 被抢 | 他们 = IR 工具包（检索服务器）；我们 = 端到端 KB 生命周期平台（入库→组织→检索→经验→人格） |

### 3.2 同类论文的写作布局（提炼自 reference PDF）

- **CRAG（NAACL 短文转长文风格）**：Intro(1p) → Related(0.75p) → Method 三小节各配 1 图 → Experiments(4 个 QA 数据集 × 3 baselines × 主表+泛化表) → Case Study → Conclusion。**启示：方法图 + 主表是命脉。**
- **Self-RAG（ICLR）**：Intro → Method(反思 token 形式化) → 实验分"事实性/引用精度/开放 QA"三组，**每组一个 RQ 一个表** → 消融单独成节 → 分析(错误类型分布图)。**启示：RQ 与表格一一对应，审稿人按表找答案。**
- **MCP-Pyserini（SIGIR 资源/系统）**：Architecture 总览图 → Capabilities 枚举 → Demo 场景 → 评测(延迟/吞吐/检索质量) → Artifact 链接。**启示：系统论文必须有 artifact + 端到端场景演示。**
- **共同规范**：所有论文主表都报 **nDCG@k / Recall@k / P@k + 显著性标记**；消融表与主表同格式；都有 Limitations 段。

### 3.3 本论文的 Section 布局（CIKM 10 页双栏 sigconf，直接用 docs/paper/ 的逐段模板）

```
1 Introduction            1.0p  场景→问题(向量误召回证据)→3 句不足→方案→4 条贡献
2 Related Work            0.8p  四小节: Dense Retrieval / Retrieval Verification /
                                KM & Graph-RAG / Agent Tool-Use + 对比表(Table 1)
3 QDCVR Methodology       2.5p  Stage 0 意图→1 KB 选择→2 两阶段召回→3 内容验证⭐→5 置信度+盲点
4 Experience Lifecycle    1.2p  E0-E12 表 + P0/P1/P2 公式 + 时效衰减 + 多路经验检索
5 System Implementation   0.5p  94 MCP 工具/鉴权/技术栈（短，细节进 artifact）
6 Evaluation              2.0p  RQ1-6 → 主表(Table 2) + 消融(Table 3) + 经验表 + 散点分析图
7 Discussion+Conclusion   0.5p  Limitations(验证延迟/标注规模/长期效果) + Threats
References + (附录进 artifact)
```

**标题建议**（角度 A 主干）：*Content-Verified Retrieval with Experience-Grounded Credibility for Agentic Knowledge Bases*

---

## 四、Benchmark 作业规范（Dataset A–E，对应 BENCHMARK-TEST-PLAN v3.0）

| 数据集 | 规模 | 内容 | 产出指标 |
|---|---|---|---|
| **A 入库集** | 30 文档 | 跨 11 领域 PDF/扫描件/表格混合 | 解析成功率、字符保真率、入库耗时 |
| **B 组织集** | 受控混乱库 | 故意构造重复/空库/深层嵌套 | 组织修复率、幂等性 |
| **C 检索集** ⭐核心 | **40+ 查询**（建议扩到 100） | 事实型/推理型/跨库型/意图干扰型/盲点型 五类 | P@5、R@5、nDCG@5、**FPR(误召回率)**、盲点正确声明率 |
| **D 经验集** | 15+ Q&A 对 | 经验命中/可信度分级/时效过期样本 | 分级准确率(κ)、衰减 F1 |
| **E 端到端集** | 10 完整任务 | 文档进→检索→经验沉淀全循环 | 任务成功率、平均时延 |

**标注规范（C 集是论文生死线）**：
1. 每查询标注：相关文档列表（3 标注者独立标注，**Cohen's κ ≥ 0.7**，分歧仲裁）
2. 额外标注"应拒答"样本（黄金盲点集）——这是 FPR 与 blind-spot 指标的 ground truth
3. 查询由真实科研场景生成，禁止用 LLM 批量造题（审稿人会问 leakage）
4. 评测集冻结后公开（anonymous artifact）——CIKM 看重可复现性

---

## 五、实验作业规范（RQ → 表格映射）

| RQ | 实验 | 表/图 | Baseline |
|---|---|---|---|
| RQ1 内容验证降低误召回 | C 集检索质量 | Table 2 主表 | BM25 / BGE-M3 向量 / BM25+Vec / Vec+CE-Rerank / RAG-Fusion / **CRAG 式评估器** / **Self-RAG 式自评** |
| RQ2 content-overrides-vector | 构造"向量高分内容不符"对抗样本 | Table 2 的 FPR 列 + 散点图 Fig.6 | 同上 |
| RQ3 跨库多样性 | balance_kbs 开关对比 | Table 2 附列 | 无 balance 版本 |
| RQ4 经验可信度分级 | D 集 | Table 4 (κ) | 无分级基线 / 纯时序排序 |
| RQ5 时效衰减 | D 集过期样本 | Table 4 | 无衰减版本 |
| RQ6 端到端任务成功率 | E 集 | Table 5 | 无经验 / 无人格版本（消融） |

**消融（Table 3）**：−Content Verify / −Query Rewrite / −KB Selection / −balance_kbs / −经验路由。

**统计规范**：每配置 **5 次运行**（LLM 温度抖动），配对 t 检验，p<0.05 标 †；报均值±标准差；
固定随机种子与模型版本（deepseek-v4-pro / BGE-M3），LLM 调用 token 记录进 artifact。

**算力/成本预估**：40 查询 × 8 方法 × 5 次 × ~3s = 约 1.5h 纯检索评测；LLM 打分部分约 2 万次调用，
按当前 omp 通道成本可忽略；瓶颈在**人工标注（约 3 人 × 2 周）**。

---

## 六、执行时间表（倒排至 2027-05-23）

| 阶段 | 时间 | 交付物 |
|---|---|---|
| **T1 评测集构建** | 2026-09 ~ 10-15 | Dataset A-E 标注完成并冻结（κ 达标） |
| **T2 Baseline 跑通** | 2026-10 ~ 11-15 | benchmark-web/backend 全部 8 方法跑通出数 |
| **T3 主实验+消融** | 2026-11 ~ 12-31 | Table 2/3/4/5 + Fig 6 数据齐 |
| **T4 论文初稿** | 2027-01 ~ 02-28 | ACM sigconf 全文初稿（用 CIKM-WRITING-FRAMEWORK 逐段填） |
| **T5 内审+修改** | 2027-03 ~ 04-15 | 2 轮内审（1 位 IR 背景审稿人视角）+ 图表精修 |
| **T6 投稿** | 2027-05 上旬 | abstract 5/16 前冻结作者 → 5/23 全文 |
| **Plan B** | 随时 | 若 T3 严重延期 → 改投 KBS（内容复用 80%） |
| **Plan C（加速）** | 2026-12 检查点 | 若 12 月底主表已出且质量高 → 冲 SIGIR 2027 AP（1 月截稿） |

---

## 七、提高命中率的 10 条策略

1. **FPR/blind-spot 是独家指标**——所有对手都没报"该拒答时的拒答率"，把它放主表最右列并加粗
2. **对比表（Table 1）必须显式引 MCP-Pyserini 并划清边界**（工具包 vs 生命周期平台），否则创新性一击即溃
3. **经验生命周期（E0-E12）是最干净的创新**（无等价系统）——摘要与贡献列表把它放第 1 条，QDCVR 放第 2 条
4. 主表 baseline 至少含 **CRAG 式与 Self-RAG 式**两个复现（审稿人必查）
5. Latency 分析单独小节（内容验证 2-5s 开销 vs 收益）——系统论文审稿人必问
6. Failure case 分析配真实例子（人格问答"诚实拒答"案例现成：双拉薄膜问题 435s 拒答+引导）
7. 公开 artifact：代码(已就绪) + 评测集 + 运行脚本 + README 复现指南，投稿时 anonymous 链接
8. Limitations 主动写三条（LLM 打分延迟/标注规模/长周期效果）——诚实减分最少加分最多
9. 图表规范：管线总览图(Fig.2)单栏置顶、主表用 booktabs、全文 ≤10 页含附录
10. **GenAI Usage Disclosure** 与匿名自查（代码仓库署名、.env、路径泄露）投稿前专项检查
