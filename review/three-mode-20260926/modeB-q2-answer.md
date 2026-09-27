# Mode B（Librarian 全量召回）— Q2 回答

**Query**: 基于电子健康记录（EHR）数据用机器学习算法预测中风/卒中风险：关键风险因素及其影响分析（英文关键词桥接 stroke / EHR / machine learning / risk factors；L1 判定：生命科学与医学=relevant，其余 10 库=out_of_scope）

## Search Paths
L0 目录 11 KBs → L1 保留 1 shelf → L2 该库全部 53 条文档描述 → L3 可信度检查：0 篇不可信 → L4 描述重叠排序读全文 11 篇（stroke 论文以中文描述词"中风/电子健康记录"直接命中 overlap 第一），预算外 **42 篇如实列为 unscanned（部分扫描）** → L5 真实 Laya（laya_sdk, criterion=evidence, threshold 0.5）：**79/79 段全打分** → 相对线 0.878（best 0.978−0.10）→ 保留 10 docs → L6 0–8 rubric → L7 作答。总耗时 **3.7 min**。

## Answer
可以回答。该论文（Nwosu et al.，*Predicting Stroke from Electronic Health Records*）对患者的电子健康记录做主成分分析（PCA）与双标图投影后给出：

- **年龄与婚姻状态对前两个主成分贡献最高**；**居住类型几乎无贡献**（Fig. 2 原文：*patient's residence type has no contribution to the first two principal components. The patient's age and marital status have the highest contribution*）。
- 第一主成分把吸烟状态与其余属性对峙——即高龄、已婚、高血糖、有高血压/心脏病的患者倾向不吸烟；第二主成分把医疗特征（血糖、BMI、性别、高血压、心脏病）与生活方式（年龄、婚姻、工作类型）分离。
- 前两个主成分无法把卒中/非卒中标签分开成簇，说明需要更高维特征空间。
- 基准性能：在 1000 次随机下采样实验中，决策树与随机森林表现接近，**前馈多层感知机（MLP）取得最佳准确率 75.02%**。

## Sources
- [P0] clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec @ 生命科学与医学 — PCA 双标图段（L47-65, judge 0.817）+ 基准实验段（L78-91, 0.719）+ 标题摘要段（0.880），0–8 评分 **8/8**
- 弃置干扰项：sci2cl 单细胞论文（judge 0.978，全局最高分！）、clinical-drug-representations（0.959）、lung-cancer（0.941）——同库临床主题邻近导致 Laya 高分，但 0–8 rubric 主题不相关 → 弃置。

## Confidence
高 — 金标文档被 L2 描述匹配直接置顶并全读，PCA 结论与基准数字均为原文可引；同库内高分干扰由答案层裁决兜住。

## Blind Spots (Cross-Library Perspective)
- **42/53 篇未读**（预算封顶），部分扫描而非穷尽；本次答案不受影响（overlap 第一即金标）。
- 同库临床主题的"语义邻近干扰"明显（全局最高分 0.978 是无关的单细胞论文）——目录道只做候选生成，依赖答案层 0–8 rubric 做最终裁决。
- 各算法完整对比表（Table I 全表）在幸存段中只有文字摘要，逐算法数字需进一步读原文表格。
