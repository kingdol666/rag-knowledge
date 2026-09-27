**L5 complete — engine verdict is final, no re-scoring, no pruning.** 19/19 scored by the real local Laya SDK, 0 errors, 17 survivors; 0 truncated. The two sub-threshold items (0.3272 / 0.4786) were dropped by the engine itself, not by me.

---

## Search Paths

| Layer | Scope | Count |
|---|---|---|
| **L0 catalog** | `kb_list(lightweight=true)` — all KBs read | **16 KBs / 371 docs** (flat library, no sub-KBs) |
| **L1 shelves** | labels on all 16 descriptions | **1 relevant** (生命科学与医学) · **6 possible** (计算机与人工智能, e2e-demo-0923, ZZ×2, e2e-flow, aw-industrial-e2e) · 9 out_of_scope → **kept 7 KBs / 191 docs** |
| **L2 doc catalog** | `kb_get_documents(lightweight=true)` on all 7 kept shelves | **191 doc descriptions read** |
| **L3 trust check** | boilerplate/opaque descriptions ("repro", "E2E flow KB", "AgentWorkShop…自动入库") → content read | **7 head-verified**; 5 candidate docs additionally content-read |
| **L4 segments** | paginated `kb_doc_read`, structured into manifest `tmp/candidates-q2.json` | **12 documents read → 19 segments** (L1–L121 offsets) |
| **L5 Jev** | `jev_filter.py --engine laya --require-real` | **19/19 scored, 0 errors, 17 survivors, deduped 17, evidence pack 12,927 chars, 0 truncated** |

**Jev backend/criterion/threshold:** `laya_sdk` (real, local `model/laya` checkpoint) · **criterion=`instance`** (auto-detected from "哪些") · **threshold=0.5** · no vector/BM25/hybrid calls used in this lane.

---

## Answer

**直接回答（来自唯一的中风专项文献 `1904.11280`，全部 8 段均被引擎保留、均为最高分）：**

在 EHR 的中风预测中，该研究用 PCA 分析 29,072 条患者记录（10 个输入属性：性别、年龄、高血压、心脏病、婚姻状况、职业、居住类型、平均血糖、BMI、吸烟状态；仅 548 例中风）后得出：

1. **贡献最大的因素：年龄（age）与婚姻状况（marital status）** —— 对前两个主成分的贡献最高（Jev 0.86 段：*"The patient's age and marital status have the highest contribution to the first two principal components"*）。
2. **几乎无贡献：居住类型（urban/rural residence）** —— *"patient's residence type has no contribution to the first two principal components"*。
3. **其余因素均有贡献但彼此不高度相关**：第一主成分对比吸烟状态 vs 其余属性（老年已婚、高血糖、高血压、心脏病者不吸烟）；第二主成分把医学特征（血糖、BMI、性别、高血压、心脏病）与生活方式（年龄、婚姻、职业）分开。前两个主成分仅解释 **31.4%** 方差 → 特征空间无法压缩，**10 个属性都应保留**做预测（Jev 0.92/0.82/0.64 段）。
4. **文献层面的主要风险因素**（论文引言引述 [6]–[8]）：**高血压、糖尿病、心脏病**是导致中风的三大主要风险因素（Jev 0.92 段）。
5. **ML 基准**：多层感知机（MLP）75.02% > 随机森林 74.53% > 决策树 74.31%（1000 次随机下采样平均）；结论是"全部属性作为输入，MLP 最优"（Jev 0.91/0.64 段）。

**次要幸存段补充（EHR-ML 语境，非中风专属）**：EHR 预测建模库中还有——药物分子表征可提升死亡率/LOS 预测（MIMIC-III，AUROC +2%~6%）；预测模型应评估临床效用而非仅精度；纵向 EHR 的连续时间概率建模；NLP 从 EHR 提取患者画像（肺癌队列）。这些为"EHR + ML 预测"提供方法学背景，但不提供额外的中风风险因素证据。

**引擎保留但与本问无关的段**（如实报告、不重打分）：global RAG benchmark、AgentWorkShop 集成指南、ZZ 复现文档、aw 诊断报告——不构成风险因素证据。

---

## Sources（17 个幸存段，文档名 + 行号 + Jev 分）

**KB `生命科学与医学`（b28f0a25…）— 直接证据：**

| 文档 | 行号 | Jev |
|---|---|---|
| clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md | I. Introduction L10–17 | **0.9245** |
| 同上 | III. Stroke Prediction L74–88（含 Table I） | **0.9120** |
| 同上 | II.B PCA biplot L50–54（age/marital 最高，residence 无贡献） | **0.8582** |
| 同上 | Abstract L6–8 | 0.8365 |
| 同上 | II.D PCA Discussion L60–63 | 0.8217 |
| 同上 | I.B EHR Dataset L21–25（10 属性清单） | 0.7982 |
| 同上 | IV. Conclusion L100–103 | 0.6390 |
| 同上 | II.A PCA variance L33–40（31.4%） | 0.5062 |

**KB `生命科学与医学` — 语境证据：**

| 文档 | 行号 | Jev |
|---|---|---|
| clinical-medicine__2201.03675__continuous-time-probabilistic… (part 1 of 3).md | Abstract L13–20 | 0.7469 |
| clinical-medicine__1909.03801__aim-for-clinical-utility… (part 1 of 2).md | Abstract L9–16 | 0.7097 |
| clinical-medicine__1809.08199__profiling-lung-cancer-patients…md | Abstract L1–16 | 0.7045 |
| clinical-medicine__2110.08918__using-clinical-drug-representations… (part 1 of 2).md | Abstract L9–14 | 0.7021 |

**其他引擎保留段（背景/无关，如实列出）：**

| 文档 | 行号 | Jev |
|---|---|---|
| aw-industrial-e2e…/diag-20260926-022518.md | L1–5 | 0.7827 |
| ZZ跨库复现库/repro.md | L1–3 | 0.8015 |
| ZZ跨库复现库2/repro.md | L1–3 | 0.8015 |
| e2e-demo-0923…/global-rag-benchmark.md | L1–12 | 0.6733 |
| e2e-demo-0923…/AgentWorkShop 集成指南.md | L1–14 | 0.5144 |

引擎拒绝（低于 0.5，透明记录）：平台架构总览.md @0.3272、harness-handbook.md @0.4786。

---

## Confidence

- **覆盖度**：16/16 KB、191/191 保留架文档描述、12 篇内容读、19 段全部真实评分（`real_engine=true`，0 errors，fail-closed 通过）。
- **作答强度**：问题直接由 `1904.11280` 回答，其 8 段占据全部最高分（0.92/0.91/0.86）——答案句句可回溯到原文行号。
- **保留**：17/17 幸存段全保留、无二次筛选（引擎判决为终审）。
- **折扣项**：① 该答案实质是**单一文献来源**，库内无第二篇中风预测文献交叉验证；② Laya 运行时警告 "invalid temperatures … confidence uncalibrated"——分数应视为 0.5 阈值的**判定值**，不是校准概率；③ criterion=instance（"哪些"自动触发）较宽松，解释了为何部分边缘文档也过线。

---

## Blind Spots (Cross-Library Perspective)

- **未读文档数**：保留架 191 篇中 **179 篇未读正文**——生命科学与医学 48/53（仅 5 篇内容读），计算机与人工智能 **131/131 全部仅描述级扫描**、未读正文。
- **范围外未扫描**：9 个 out_of_scope KB（自然科学 75、工程 39、经济 24、Novel 28、aw-industrial 7、soul-e2e-tester 4、AI 基础设施 3、Corpus 0、soul-e2e 0）共 **180 篇**仅凭具体描述裁剪，未做内容读；若"中风"一词在其他库以不同术语出现，本层无法捕获。
- **知识缺口**：全库仅一篇中风专项 ML/EHR 文献；"哪些风险因素影响最大"的答案受该数据集（McKinsey/Kaggle，548 正例）与其 PCA 方法本身的局限约束，**PCA 贡献度 ≠ 因果/预测重要性**，论文自身也仅称其为主成分贡献排序。
- **引擎侧**：本地 Laya checkpoint 温度参数异常（未校准）；fail-closed 未被触发（无缺分/越界分），但 L2/其余 8 个 KB 的子 KB 层级不存在（扁平库），无更深层遗漏。
- **本报告为部分覆盖（partial）**，不宣称穷尽：L4 按任务规定仅对**描述匹配的候选文档**读全正文，非描述匹配的 179 篇保留架文档为已知盲区。