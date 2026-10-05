# 三模式检索多轮稳定性验证报告（2026-09-30）

## 结论

**27/27 全部 HTTP 200，三行为模式逐轮一致，工具路径 27/27 合规，未发现一次幻觉或跑偏。可以投入使用。**

- 找到的题（attention）：9/9 跑全部给出正确公式 `Attention(Q,K,V)=softmax(QKᵀ/√d_k)·V`（9/9 含 softmax + √d_k 缩放 + QKV 三要素）。
- 语料不覆盖的题（seismology，事先人工核验：库内仅 2 篇超剪切破裂/震后损失论文，确无地震波分类教材内容）：9/9 跑全部如实奉告"库内无系统分类"，并指出库内相关文献实际主题——零编造。
- 明确不存在的题（pickles）：9/9 跑全部如实拒绝；B 车道全程目录层早退，不做无谓深挖。

## 矩阵（3 任务 × 3 模式 × 3 轮 = 27 跑，chat API 默认非流式）

| cell | R1 | R2 | R3 | 中位 | 行为一致 |
|---|---|---|---|---|---|
| attention_A | 76.0s | 78.0s | 61.2s | 76s | ✅ 9/9 公式正确 |
| attention_B | 54.8s | 72.7s | 42.1s | 55s | ✅ |
| attention_C | 49.6s | 66.1s | 84.9s | 66s | ✅ |
| seismology_A | 44.7s | 56.0s | 55.8s | 56s | ✅ 9/9 如实奉告 |
| seismology_B | 78.1s | 46.4s | 59.4s | 59s | ✅ |
| seismology_C | 73.3s | 69.3s | 41.8s | 69s | ✅ |
| pickles_A | 24.4s | 40.6s | 34.2s | 34s | ✅ 9/9 拒绝 |
| pickles_B | 29.0s | 64.0s | 33.5s | 34s | ✅ |
| pickles_C | 42.7s | 37.3s | 28.8s | 37s | ✅ |

全程耗时：R1 472.6s / R2 527.1s / R3 441.8s（每轮 9 跑，平均 49-59s/跑）。
费用：$0.08–0.42/跑。turns 波动 3–17（R2_attention_B 的 17 turns 为并行批量拉取多库描述，仍全程 B 车道合规）。

## 工具路径合规（session_trace 逐会话核验）

- **A 向量快车道**：`kb_search_two_stage → kb_search_vector → kb_laya_judge → kb_doc_read`，全程零 librarian 工具。
- **B 逐级检索**：`kb_list → kb_get_documents(描述层) → kb_laya_judge → kb_doc_read`，全程零向量工具。
- **C 混合**：向量先行，证据不足时按混合契约回退 `kb_list/kb_get_documents` 补全。

trace 中出现的 ≥20s "卡点" 全部落在最后一段 LLM 组织答案窗口（deepseek-flash 走本地代理、无跨轮 prompt 缓存），非工具挂起；工具侧执行均在 1-33s 内。

## 已知波动源（非缺陷）

1. 时延波动 ±35s 主因：末段答案生成为 LLM 轮次（代理链路无缓存），库/检索侧稳定。
2. B 车道 turns 波动（6↔17）：模型并行批量拉多个库描述，路径仍合规，属健康探索。
3. kb_doc_read 大文档（Attention 原论文）偶发 15s↔33s，服务端读盘/DB 波动。

## 工件

- 运行器：`run_stability.py`（rounds 参数化，可随时重跑）
- 逐跑完整回答：`results/r{1,2,3}_{task}_{A,B,C}.json`
- trace 工具：复用 `review/chat-api-stream-20260928/session_trace.py`
- 服务基线：web:6789 / backend:8771 / kb-mcp HTTP:8000 全程健康，看门狗自动化在岗
