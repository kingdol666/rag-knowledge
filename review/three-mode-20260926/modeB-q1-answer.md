# Mode B（Librarian 全量召回）— Q1 回答

**Query**: How does InstructDS generate high-quality query-based dialogue summaries?（Phase 0 关键词桥接：instructds / dialogue summarization / query-based / instruction tuning / data synthesis；L1 判定：计算机与人工智能=relevant，其余 10 库描述特异可信=out_of_scope）

## Search Paths
L0 目录 11 KBs → L1 保留 1 shelf（agent 判定）→ L2 该库全部 131 条文档描述 → L3 可信度检查：0 篇不可信（该库描述由 ingest A3c 生成，无样板/空洞问题）→ L4 描述重叠排序读全文 23 篇（InstructDS 4 部分全部以 overlap 2-3 分排最前，加 stem 兄弟补齐），预算外 **108 篇如实列为 unscanned（部分扫描，非穷尽）** → L5 真实 Laya（laya_sdk, criterion=evidence, threshold 0.5，fail-closed）：**151/151 段全部打分** → 相对线 0.834（best 0.933−0.10）+ top-K 保底 → 保留 17 docs → L6 0–8 rubric → L7 作答。总耗时 **6.6 min**（无向量道，纯顺序目录遍历）。

## Answer
InstructDS（A\*STAR I2R：Bin Wang, Zhengyuan Liu, Nancy F. Chen）通过**三步合成的 QDS（query–dialogue–summary）指令三元组 + 多数据集统一指令微调**来生成高质量 query 型对话摘要：

1. **摘要锚定的查询生成**：利用大模型的条件问题生成能力，从参考摘要反向生成多个候选查询，以此绕开 query 型对话摘要训练数据稀缺、人工标注成本高的问题（part 1 摘要，judge 0.828）。
2. **查询过滤**（两级，part 1 L68-77，judge 0.790）：①文本级过滤——用二分类器判断查询可答性，淘汰约 **45%** 可能诱发幻觉的不可答查询（如 "What will…/How would…" 类）；②语义级过滤——用归一化 BERTScore 度量语义相似度去除近义重复查询（如 "think about" vs "think of"）。
3. **基于查询的摘要生成**（part 1 L78-88，judge 0.885）：以查询 + 精炼摘要为输入触发模型的问答能力生成查询条件化摘要；平均每对对话-摘要产出 **1.3 条** QDS 三元组，专家抽检 100 条显示过滤使质量分从 **45% 提升到 75%**。
4. **统一模型与验证**（part 2，judge 0.884）：三个对话摘要数据集混合（MixDS）+ 合成 QDS 三元组 + 长度感知增强训练出完整版 InstructDS，消融五变体证实各成分贡献（DREAM 上查询型摘要 56.4→59.1）；四个数据集上超越 SOTA 与更大规模模型，ChatGPT 评测中忠实度仅次于 ChatGPT 自身。

## Sources
- [P0] nlp__2310.10981... (part 1 of 4) @ 计算机与人工智能 — 摘要三步法 + 过滤/生成机制细节，多段幸存证据（L1-22 / L68-77 / L78-88），0–8 评分 8/8
- [P0] nlp__2310.10981... (part 2 of 4) @ 计算机与人工智能 — §4.3 消融与人工/ChatGPT 双评（8/8）
- [P1] nlp__2310.10981... (part 4 of 4) @ 计算机与人工智能 — 附录模板与三元组示例（7/8）
- 弃置干扰项：riddle-me-this（judge 0.933）、vision-flan（0.933）、how-do-LMs-learn-facts（0.907）——Laya 分数最高但 0–8 rubric 主题不相关（≤2 → 弃置）。

## Confidence
高 — 金标论文 4 个 part 全部被读全（overlap 排序第一名），方法三步 + 过滤细节 + 消融证据齐备且相互印证。

## Blind Spots (Cross-Library Perspective)
- **108/131 篇文档未读**（预算 35 篇封顶）——本轮是部分扫描而非穷尽召回；若答案藏在未读文档（如实验部分）存在漏检风险，好在 overlap 排序已命中主题文档。
- InstructDS part 3（ROUGE 复现细节）被相对线（0.834）剪出保留集，其幸存段（0.783/0.740）仅进入参考——对"如何生成"这一问无影响，但列表型指标问题需注意。
- Laya 头重分布再次显现：3 篇无关论文压住金标 0.15 分，若无答案层 rubric 兜底会误导。
