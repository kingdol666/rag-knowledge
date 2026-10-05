# Mode A（QDCVR v2 向量优先）— Q1 回答

**Query（Phase 0 改写后）**: How does InstructDS generate high-quality query-based dialogue summaries? (InstructDS dialogue summarization query-based instruction tuning data synthesis)

## Search Paths
Phase 1 vector (kb_search_vector, balance_kbs=True, top_k=10, threshold 0.35) → 10 raw hits → doc-level dedup 5 docs → content gate (kb_doc_read head 3000 chars + 1× 2/3 continuation, 0-8 scoring) → best **8/8** → fast exit, Phase 2 未触发。全链 10 次 MCP 调用 / 13.3s（含 2 次续读）。

## Answer
InstructDS（A\*STAR I2R）是首个在通用对话摘要与 query 型对话摘要上同时表现优异的指令化对话摘要模型。它能生成高质量、贴合用户需求的 query 型摘要，靠的是三个要素的组合：**多数据集训练**（在三个摘要数据集上以多用途指令三元组训练统一模型）、**合成的 QDS（query–dialogue–summary）三元组**、以及**长度感知增强**。实验显示其超越 SOTA 乃至更大规模的模型，并具备更高的泛化性与忠实度。检索到的消融研究部分（part 2 §4.3）进一步验证了增强 QDS 三元组对通用与 query 型摘要的贡献。

## Sources
- [P0] nlp__2310.10981__instructive-dialogue-summarization-with-quer (part 2 of 4) @ 计算机与人工智能 — 结论段直接回答生成机制；§4.3 消融研究佐证（chunk 500 字符 + 头部窗口，8/8）
- [P0] nlp__2310.10981...__k23 @ Corpus-Chunks800 — 同一论文的 chunk 副本，结论段同文（chunk 证据 8/8；该库 kb_doc_read 返回空正文，证据仅来自 chunk 文本）

## Confidence
高 — 两个独立库中的同论文副本证据一致（结论段原文可引）。

## Blind Spots (Cross-Library Perspective)
- 快速通道窗口未覆盖**三步合成法的逐步细节**（summary-anchored query generation → query filtering → query-based summary generation，位于 part 1 的摘要/方法节）——本回答给出的是结论级机制（三要素），未展开三步流程；如需流程细节应深入 part 1。
- 其余知识库（生命科学/工程/小说等）与本主题无关，本次未扫描（描述特异可信，判定 out_of_scope）。
