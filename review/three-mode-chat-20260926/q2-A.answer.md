搜索已执行完毕（exit 0，`--require-real` 通过）。以下按五段式输出。

## Search Paths

- **Path A — `kb_search_vector` 宽网（跨库，kb_id=""）**：查询 = `用机器学习从电子健康记录预测中风，哪些风险因素影响最大？ stroke prediction electronic health records machine learning risk factors`，top_k=30，向量阈值 0.35 → **26 条原始命中 → 19 篇去重文档**。
- **Path B — 内容核验门（Laya/Jev 判决）**：按 doc_id/path 批量 `kb_doc_read` 读取 → 结构感知分段 → 逐段引擎判决（`--engine laya`，Jev 为备选未启用）。
  - **判决统计**：backend=`laya_sdk`，`real_engine=true`（满足 `--require-real`），criterion=instance，阈值 0.5，**95/95 段全部打分（0 漏判、0 错误）**，global_best=0.9026 → **17 篇文档各含 ≥1 yes 段，全部进入 result_list**（引擎判决即终判，无 rubric、无截断）。
  - 读取失败 2 篇（empty_content，见 Blind Spots）；总耗时 202.3s（召回 4.6s + 重读 8.8s + 判决）。
  - ⚠️ Laya 加载时自报：checkpoint 温度参数异常，受影响条目的置信度**未校准**（见 Confidence）。
- **Path C — 补读**：最高向量命中（中风论文）在 evidence_pack 中被截断（truncated=true），已用 `mcp__kb-mcp__kb_doc_read` 补读全文（124 行）后作答。

## Answer

知识库中**唯一直接回答该问题的文档**是《Predicting Stroke from Electronic Health Records》（arXiv 1904.11280, Nwosu/Dev 等），其余 16 篇幸存文档均为无关主题（见 Sources），对答案零贡献。综合该文：

**1) 文献确认的"最大"风险因素（该文引用的既有研究 [6]-[8]）**：**高血压（hypertension）、心脏病（heart disease）、糖尿病/平均血糖水平（average glucose）** 是中风的三大主要风险因素；相关研究还发现 **风险因素的总数量与中风概率直接相关**（Jeena 等：风险因素越多，发病概率越高）。

**2) 该文自身的系统性分析（PCA，29,072 份电子健康记录）——"没有单一主导因素"**：
- 患者属性**彼此并非高度相关**：前 2 个主成分仅解释 **31.4%** 方差，需 9 个主成分才达 **96.06%** → 任何特征子集删减都会显著损失信息，**全部 10 个输入属性都应保留**用于建模。
- 双标图（biplot）中：**年龄（age）与婚姻状况（marital status）对前两个主成分贡献最高**；居住类型（urban/rural）贡献为零；PC1 把吸烟状态与其余属性对比（年长、已婚、高血糖、高血压、心脏病者倾向不吸烟）；PC2 把医学特征（血糖、BMI、性别、高血压、心脏病）与生活方式特征（年龄、婚姻、职业）分离。
- **注意**：该文并未给出逐特征的重要性排序（留作未来工作："研究特征子集对分类精度的影响"）——"影响最大"的排序结论在本文中来自其文献综述与 PCA 方差结构，而非自身的特征重要性实验。

**3) 模型基准（1000 次随机下采样实验）**：数据集 29,072 条记录、仅 548 例中风（约 1.9%，高度不平衡），均衡为 1096 条、70/30 划分。**神经网络（MLP）75.02% > 随机森林 74.53% > 决策树 74.31%**，三者分布高度重叠，性能相近。

**一句话回答**：以知识库现有证据，**高血压、心脏病、糖尿病（血糖）是被文献确认的主要风险因素**；该文 PCA 分析进一步表明各因素相互独立、缺一不可（前两主成分仅 31.4% 方差），其中 **年龄与婚姻状况对数据方差贡献最大**；MLP 以 75.02% 平均精度成为最佳预测模型。

## Sources

（result_list 全部 17 篇，⭐ = 唯一主题相关文档）

| # | 文档（doc_path） | vector | Laya judge |
|---|---|---|---|
| 1 | 经济与社会/economics__2011.14424__on-the-effectiveness-of-the-european-central (part 5 of 5).md | 0.5507 | 0.9026 |
| 2 | e2e-demo-0923-022632/global-rag-benchmark.md | 0.4952 | 0.9002 |
| 3 | aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md | 0.4933 | 0.8980 |
| 4 | 自然科学与地球科学/climate-science__2409.09639__gpc-m-global-precipitation-climatology-by-ma (part 1 of 2).md | 0.5751 | 0.8817 |
| 5 | 计算机与人工智能/large-language-models__2005.14165__language-models-are-few-shot-learners.md (part 5 of 13).md | 0.5960 | 0.8737 |
| 6 | 计算机与人工智能/neuroscience__1404.4184__airborne-ultrasonic-tactile-display-brain-co.md | 0.5669 | 0.8725 |
| 7 | 工程与能源/power-systems__2607.03098__integrating-power-electronics-based-energy-s (part 1 of 5).md | 0.5534 | 0.8722 |
| 8 | AI 基础设施/vector-index-tuning-guide (part 1 of 2).md | 0.5138 | 0.8699 |
| 9 | 工程与能源/power-systems__2607.03098__integrating-power-electronics-based-energy-s (part 2 of 5).md | 0.5594 | 0.8642 |
| 10 | Novel-PridePrejudice/pride_and_prejudice (part 24 of 26).md | 0.3857 | 0.8504 |
| 11 | Novel-PridePrejudice/pride_and_prejudice (part 13 of 26).md | 0.3930 | 0.8475 |
| 12 | 自然科学与地球科学/seismology__1308.1846__developing-and-testing-the-automated-post-ev.md (part 1 of 4).md | 0.5877 | 0.8451 |
| **13** | ⭐ **生命科学与医学/clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md** | **0.8237** | **0.8337** |
| 14 | AI 基础设施/vector-index-tuning-guide (part 2 of 2).md | 0.5025 | 0.8301 |
| 15 | 经济与社会/economics__2011.14424__on-the-effectiveness-of-the-european-central (part 2 of 5).md | 0.5798 | 0.8242 |
| 16 | soul-e2e-tester-024115/memory-conventions.md | 0.4587 | 0.7647 |
| 17 | e2e-flow-20260926-022340/harness-handbook.md | 0.3592 | 0.5193 |

## Confidence

**中等偏高（对提取内容）/ 低（对全库覆盖）** — 该结论在 **after Jev verification**（Laya 实引擎门控，95/95 段全判、real_engine=true）之后成立，但需附三条诚实声明：

1. **幸存集构成警示**：17 篇幸存文档中仅 1 篇（#13）与问题相关；Laya 门为"每篇 ≥1 yes 段即保留"的宽松通过制——**无关文档也被大量放行**（ECB 经济学参考文献拿到全场最高 judge 0.9026，Pride & Prejudice 0.85）。即判决分**不能独立区分主题相关性**，最终答案质量依赖内容核验环节。
2. **引擎自报校准缺陷**：Laya 加载时警告其温度参数越界，受影响条目置信度**未校准**——judge 分数只宜作序数参考。
3. **答案来源单一**：全部实质性答案来自 1 篇 2019 年论文；其"三大主因"表述转引自其引用的文献，论文自身未做特征重要性排序实验（70-75% 的分类精度也说明 EHR 单表特征的预测天花板有限）。

## Blind Spots (Cross-Library Perspective)

- **跨库扫描结论**：本次跨库宽网覆盖到 10+ 个 KB（经济与社会、生命科学与医学、自然科学、计算机与 AI、工程与能源、AI 基础设施、Novel、aw-industrial、e2e、soul 等），但**除生命科学与医学库外，其他库无任何中风/EHR/ML 风险因素相关内容被召回**——该类知识在本库中仅此一处，不存在跨库冗余佐证。
- **两篇不可读文档（盲区）**：① `Corpus-Chunks800/clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec__k00.md`（KB `0942f1a6…`）——是同一篇中风论文的**分块副本，但内容为空（empty_content）**，无法核验，疑似该库入库/索引完整性问题（建议另行核查，本次只读未修）；② `aw-industrial-e2e-20260926-022518/experience/exp-d45dc195a924.md`（经验库）同样为空。
- **检索网边界**：top_k=30 + 向量阈值 0.35 的宽网无法保证穷尽——以"脑卒中/cerebrovascular accident/APACHE"等同义表述入库的内容可能不在网内；且按平台已知特性（父/子 KB 向量落在父 collection），若相关文档存在于子 KB 层级，需以父 KB collection 为检索面才能召回。
- **问题本身的缺口**：库内**没有任何文档提供带排序的特征重要性证据**（如 SHAP/互信息/单变量效应量）。若需"哪个因素贡献百分比最高"级别的量化排序，当前知识库无法回答，属真实盲区而非检索失败。