# Mode C（Hybrid 并行双道）— Q1 回答

**Query**: How does InstructDS generate high-quality query-based dialogue summaries?（--extra-terms "instructds 对话摘要 指令 查询 摘要 数据合成"，--peek-heads --top-k-floor 5 --lane-agreement --require-real）

## Search Paths
Vector lane（kb_search_vector, balance_kbs, top_k=10, threshold 0.35）∥ Catalog lane（kb_list 10 shelves → 367 条文档描述 → 描述重叠 7 篇 + stem 补齐 2 篇 → 预算读 30 篇全文 → peek 300 篇头部）→ 合并 332 docs（both=7 / vector-only=2 / catalog-only=323）→ 2 篇 vector-only 补读（均 empty_content → unscanned 如实报告）→ **505/505 段真实 Laya 打分**（real_engine=true, laya_sdk）→ 绝对阈值 0.5 + 相对线 0.837（best 0.937−0.10）+ top-K 保底 + lane-agreement → 保留 24 篇 → stem 扩展 26 篇 peek 升级全读重判 → 0–8 rubric 终裁。总耗时 **19.2 min**（MCP I/O 约 2.3 min + Laya CPU 推理约 16.9 min，与模式 B 并行争核）。

## Answer
InstructDS（A\*STAR I2R；Bin Wang, Zhengyuan Liu, Nancy F. Chen）通过**三步数据合成 + 多数据集统一指令微调**来生成高质量 query 型对话摘要：

1. **三步合成 QDS 三元组**（part 1 摘要，judge 0.937）：①**摘要锚定的查询生成**（summary-anchored query generation，让 LLM 从参考摘要反向生成候选查询）→ ②**查询过滤**（query filtering，文本级 + 语义级双重过滤保证查询质量）→ ③**基于查询的摘要生成**（query-based summary generation，触发 LLM 的问答能力生成查询条件化摘要）。
2. **统一模型训练**：在三个对话摘要数据集上以多用途指令三元组训练统一模型（part 2 §4.3，judge 0.918：消融设 MixDS / MixDS+QDS / MixDS+Length / InstructDS 五个变体，分离出合成 QDS 三元组与长度感知增强各自对通用摘要和 query 型摘要的贡献）。
3. **效果**：在四个数据集（含对话摘要与对话阅读理解）上超越 SOTA 乃至更大规模模型，人工评测确认更高泛化性与忠实度。

## Sources
- [P0] nlp__2310.10981... (part 1 of 4) @ 计算机与人工智能 — lane=catalog, judge 0.937，摘要含三步法原文（8/8：主题 3 + 场景 3 + 证据 2）
- [P0] nlp__2310.10981... (part 2 of 4) @ 计算机与人工智能 — lane=both, vec 0.776 + judge 0.918，§4.3 消融五变体（8/8）
- 弃置干扰项：stroke（judge 0.919）、riddle-me-this（0.913）、bayesian state-space（0.912）等虽过引擎相对线，但按 0–8 rubric 主题相关性 ≤1 → ≤4 分弃置——引擎门只出候选，内容裁决在答案层。

## Confidence
高 — 双道独立命中同一论文（lane=both），4 个 part 全部被目录道读全，方法三步+消融证据直接可引。

## Blind Spots (Cross-Library Perspective)
- 2 篇文档不可读（Corpus-Chunks800 k22 chunk 副本与 aw-industrial mock 报告 kb_doc_read 返回空正文），已列入 unscanned，未参与打分。
- peek 覆盖 300/339 篇零重叠文档（39 篇超出 peek-limit 未 peek）；但未 peek ≠ 未命中风险为主，InstructDS 全部 4 part 已在预算内全读。
- Laya 分布头重（中位 ≈0.88），相对线保留的 24 篇中多数为主题无关高分散扰——由答案层 0–8 rubric 兜底，说明引擎门精度有限但召回充分。
