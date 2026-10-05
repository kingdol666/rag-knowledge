# 模式 C(并行重定义) — 知识增强回答记录

- 日期：2026-09-27 · 检索脚本：`scripts/124_mode_c_parallel.py`（A∥B 并行子进程 → 去重合并 → 完整读取）
- 问题（q1）：How does InstructDS generate high-quality query-based dialogue summaries?
- 检索产物：merge A=19 docs ∥ B=23 docs → 共识 2 → 合并 12 篇 → 完整读取 179,973 字符；
  金标论文 part1(25,303 chars)+part2(28,326 chars) 均为**共识文档**且未截断。
  Worker 耗时：A 29.9s / B 并行同窗口（merge_s=33.3s），总 42.8s。
- 上下文卫生：中间检索/判决过程全部留在子进程与临时 JSON，主对话只接收下方最终文档内容。

## 知识增强回答（仅依据最终读取的文档内容）

**InstructDS 生成高质量 query-based 对话摘要的路径是：用"摘要锚定"的合成流水线把普通
dialogue-summary 对升级为 query-dialogue-summary（QDS）三元组，再用它做指令微调。**

合成流水线三步（论文 §3.2）：

1. **Query Generation（查询生成）**：用 Flan-T5-XL 的问题生成能力，对每个 dialogue-summary
   对生成 5 个候选查询（模板提示词见论文 Table 7），锚定摘要内容。
2. **Query Filtering（查询过滤，两道）**：
   - 文本过滤——用同一模型做可答性二分类，剔除"What will/How would"类无法不幻觉作答的查询，
     淘汰约 **45%**；
   - 语义去重——对同一对话对的相似查询（如 "What does Edward think about Bella?" vs
     "...of Bella?"）用归一化 BERTScore，>0.65 只保留首条，再淘汰约 **50%**。
3. **Query-guided Summary Generation（查询引导摘要生成）**：以过滤后的查询为指令生成摘要。

训练数据：SAMSum（18,245 QDS）+ DialogSum（18,600）+ TODSum（8,705）共 3 个对话摘要数据集，
外加 DREAM（对话理解，含天然 QDS 三元组），合计约 45,550 个 QDS 三元组。
效果：在 3 个对话摘要数据集 + 1 个对话理解数据集上显著超过此前模型；人类主观评测在
factuality / fluency / informativeness / conciseness 四个维度与人工撰写摘要相当。

—— 以上全部内容出自合并集中 A、B 双模式共识命中的金标文档
`计算机与人工智能/nlp__2310.10981__instructive-dialogue-summarization-with-quer (part 1/4, 2/4)`。
