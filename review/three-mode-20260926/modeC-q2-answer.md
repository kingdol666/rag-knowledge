# Mode C（Hybrid 并行双道）— Q2 回答

**Query**: 用机器学习从电子健康记录预测中风，哪些风险因素影响最大？（--extra-terms "stroke electronic health records EHR machine learning risk factors PCA principal component"，--peek-heads --top-k-floor 5 --lane-agreement --require-real）

## Search Paths
Vector lane（10 hits → 10 dedup docs，含 stroke 文档 0.688——中文查询与英文语料语义匹配成功）∥ Catalog lane（367 条描述 → 重叠 22 篇（stroke 中文描述直接命中）+ stem 补齐 8 → 预算读 30 篇全文 → peek 300 篇头部）→ 合并 335 docs（both=5 / vector=5 / catalog=325）→ 统一补读 → **893/893 段真实 Laya 打分**（real_engine=true）→ 相对线 0.877（best 0.977−0.10）+ top-5 保底 + lane-agreement → 保留 75 → max_kept 30 封顶 → stem 扩展 26 篇全读重判 → 0–8 rubric 终裁。总耗时 **30.3 min**（本测最重负载：893 段 CPU 推理）。

## Answer
可以回答。金标文档（Nwosu et al., *Predicting Stroke from EHR*）被**双道独立命中**（lane=both：向量 0.688 + Laya 0.920）并全读。PCA 双标图分析给出：

- **年龄与婚姻状态贡献最高；居住类型几乎无贡献**（原文：*patient's residence type has no contribution to the first two principal components. The patient's age and marital status have the highest contribution*）。
- 第一主成分对峙吸烟状态与其余属性；第二主成分分离医疗特征（血糖/BMI/高血压/心脏病）与生活方式（年龄/婚姻/工作类型）；前两主成分无法分开卒中标签簇，需更高维特征。
- 基准性能：1000 次随机下采样实验，MLP 最佳准确率 **75.02%**，决策树≈随机森林。
- 证据包补救记录：12k 字符 evidence_pack 被高分干扰文档挤占、stroke 段被截断——按 hybrid 契约对幸存者执行 `kb_doc_read` 补读，PCA 段确认在文（offset≈41 行）。

## Sources
- [P0] clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec @ 生命科学与医学 — lane=both（vec 0.688 / judge 0.920），目录道描述直接命中 + 向量道跨语言命中，0–8 评分 **8/8**
- 弃置干扰项（Laya 0.926–0.977 但 rubric ≤2 → 弃置）：GPT-3 few-shot（0.977，全局最高）、sci2cl（0.971）、speech enhancement（0.970）、convex-optimization（0.960）、pride_and_prejudice（0.957）、aw-industrial 冒烟文档（0.967）等。

## Confidence
高 — 双道独立一致命中金标（lane-agreement 机制的对象场景），PCA 结论与基准数字原文可引。

## Blind Spots (Cross-Library Perspective)
- 1 篇 unscanned（Corpus-Chunks800 k00 chunk 副本，kb_doc_read 空正文，与模式 A/B 观察一致——该库 chunk 文档不可读是数据面问题）。
- 相对线在 peek 全库扫描下保留 75 篇（max_kept 封顶 30）：头重分布导致大量主题无关文档挤占保留集与证据包（12k 截断把金标段挤出证据包，需 agent 补读步骤兜底）——引擎门召回充分、精度不足的两层设计在跨语言中文问句上代价最高。
- peek 覆盖 300/330 篇零重叠文档，30 篇未 peek（peek-limit 上限）。
