# Mode A（QDCVR v2 向量优先）— Q2 回答

**Query（Phase 0 改写后）**: 基于电子健康记录（EHR）数据用机器学习算法预测中风/卒中风险：关键风险因素及其影响分析 (stroke prediction electronic health records machine learning risk factors)

## Search Paths
Phase 1 vector (kb_search_vector, balance_kbs=True, top_k=10, threshold 0.35) → 10 raw hits → doc-level dedup 5 docs → content gate (kb_doc_read head 3000 chars + 2 次续读 @1/3、@2/3，0-8 scoring) → 最佳 **8/8** → fast exit，Phase 2 未触发。全链 10 次 MCP 调用 / 7.4s（另加 1 次定向续读）。

## Answer
可以回答。对患者的电子健康记录做主成分分析（PCA）后，论文在双标图（biplot）上量化了各风险因素的贡献：**年龄与婚姻状态对前两个主成分的贡献最高**；**居住类型（residence type）几乎无贡献**。主成分结构上：第一主成分（水平轴）把患者的吸烟状态与其余属性对峙——即高龄、已婚、高血糖、有高血压/心脏病史的患者倾向不吸烟；第二主成分（垂直轴）把医疗特征（平均血糖、BMI、性别、高血压、心脏病）与生活方式属性（年龄、婚姻状态、工作类型）分离。除因素分析外，论文还给出了多种当时 SOTA 机器学习算法在 EHR 卒中预测任务上的基准性能对比（1000 次实验的准确率密度分布，其中神经网络表现出最高的分类准确率集中区）。

## Sources
- [P0] clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec @ 生命科学与医学 — 摘要 + §B PCA/双标图节（@1/3 续读）+ 基准实验节（@2/3 续读），含可直接引用的 PCA 结论（8/8）
- [P0] clinical-medicine__1904.11280...__k00 @ Corpus-Chunks800 — 同论文 chunk 副本，摘要尾段同文（chunk 证据 8/8；该库 kb_doc_read 返回空正文，证据仅来自 chunk 文本）

## Confidence
高 — 两个独立库中的同论文副本一致；PCA 结论句为原文直接引用。

## Blind Spots (Cross-Library Perspective)
- 各算法的**具体准确率/AUC 数值表**位于未读窗口（正文表格区），如需逐算法数字需进一步读取。
- 中文提问与英文语料之间依赖向量语义匹配命中；目录描述（中文）与语料语言不同属已知风险，本次靠改写查询中的英文关键词弥合。
- 其余知识库与主题无关，判定 out_of_scope 未扫描。
