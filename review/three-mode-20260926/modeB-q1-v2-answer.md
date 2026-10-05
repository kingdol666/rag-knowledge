# Mode B v2（新契约：Jev yes 全收，无 rubric/无剪枝）— Q1 回答

**Query**: How does InstructDS generate high-quality query-based dialogue summaries?（L1 保留：计算机与人工智能）

## Search Paths
L0 目录 11 KBs → L1 保留 1 shelf → L2 131 条文档描述 → L3 全部可信 → L4 重叠排序全读 23 篇（108 篇 unscanned 如实报告，部分扫描）→ L5 真实 Laya（laya_sdk, criterion=evidence, threshold 0.5）：**151/151 段打分 → 128 段判 yes 全部保留（5 篇文档，0.529–0.933）** → L5.5 聚合（证据包 40k 字符）→ L6 直接从全幸存集作答，无任何再筛。耗时 **5.7 min**（与 v1 持平——剪枝本来就发生在判决之后，去掉它零额外成本）。

## Answer（直接回答）
InstructDS（A\*STAR I2R）用**三步合成 QDS 三元组 + 多数据集统一指令微调**生成高质量 query 型对话摘要：①**摘要锚定查询生成**——让 LLM 从参考摘要反向生成候选查询，绕开人工标注贵/少/窄的瓶颈；②**查询过滤**——文本级可答性分类器淘汰约 45% 不可答查询 + BERTScore 语义去重；③**基于查询的摘要生成**——以查询+精炼摘要触发问答能力，平均每对对话产出 1.3 条三元组，过滤后专家评质量分 45%→75%。统一模型在三个摘要数据集上以 MixDS+QDS+Length 增强训练，四个数据集上超越 SOTA 与更大模型（DREAM 查询型摘要 56.4→59.1），人工与 ChatGPT 双评确认忠实度/流畅度优势。

## Knowledge Enhancement（全幸存集附加知识——旧机制会丢掉的部分）
Jev 判 yes 的 128 段中，除金标论文 21 段（含旧机制剪掉的 **part 3 的 14 段**：ROUGE 三种实现的口径差异、DialogSum 说话人预处理模板——复现实验数字时必须对齐的细节）外，同批保留的领域知识还有：

- **vision-flan（44 段，0.529–0.933）**：人类标注任务扩展对指令微调的规模化价值——与 InstructDS"数据合成 vs 人工标注"的路线选择直接互补。
- **how-do-language-models-learn-facts（28 段）**：语言模型学习事实的动态机制——解释为什么查询条件化训练能改善摘要的事实性。
- **riddle-me-this（25 段，最高 0.933）**：针对 RAG 的隐蔽成员推断攻击，其 §5.1 查询生成方法与 InstructDS 的查询生成同源（从目标文档反推查询）——防御视角的对照知识。
- **demystifying-instruction-mixing（10 段）**：指令混合比例对微调的影响——InstructDS 三数据集混合比例设计的理论参照。

## Sources（全部 Jev yes，按分数降序节选）
- [0.933] riddle-me-this (part 2) · [0.933] vision-flan (part 5) · [0.918±] InstructDS part1/2 全部 21 段 · [0.9-] how-do-lm-learn-facts 多段 · [0.85+] demystifying-instruction-mixing 等 5 文档 128 段，逐段含 kb/doc/part/行号/Jev 分溯源（见 modeB-q1-v2.json）

## Confidence
覆盖型置信：金标文档 4 part 全读全判、21 段幸存、无引擎错误；同域 4 篇相关论文 107 段一并保留为增强材料。

## Blind Spots (Cross-Library Perspective)
- 108/131 篇未读（预算封顶，部分扫描）；本次金标在 overlap 排序第 1 不受影响。
- 幸存集中干扰/增强比例约 4:1——按新契约全部保留交付，由使用方按需取用；若下游上下文有限，`survivors` 字段带分数可再排序（排序但不丢弃）。
