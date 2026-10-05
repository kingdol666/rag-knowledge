# 检索任务对照矩阵（三模式 + baseline, 纯检索无 LLM 回答）

- Run: `run-20260927T094215Z-47cc948` · 生成: 2026-09-27 09:52 UTC
- Laya 环境: {'python': 'D:\\codes\\ClaudeGPT\\rag_project\\rag-knowledge\\backend\\.venv\\Scripts\\python.exe', 'torch': '2.12.1+cu130', 'cuda': True}（判决 GPU 化, C 与 A/B 同环境同通道）
- 语料: 模式=真库(q1/q2 金标在库); bm25/rrf=corpus_md 100 篇(金标在集); vector=平台跨库

| 方法 | q1 耗时 | q2 耗时 | q1 金标 | q2 金标 | q1 docs | q2 docs |
|---|---:|---:|:--:|:--:|---:|---:|
| mode_A | 82.7s | 52.4s | ✅ | ✅ | 17 | 15 |
| mode_B | 78.5s | 29.8s | ✅ | ✅ | 23 | 11 |
| mode_C | 235.1s | 123.4s | ✅ | ✅ | 36 | 38 |
| bm25 | 0.0s | 0.0s | ✅ | ✅ | 10 | 10 |
| vector | 0.4s | 0.0s | ✅ | ✅ | 1 | 3 |
| rrf | 0.0s | 0.0s | ✅ | ✅ | 10 | 10 |

> 全部为纯检索任务（无 LLM 回答）；模式臂经硬验证门（real_engine/金标/延迟），
> baseline 臂为 retrieval_only（answer=None, 零 token 成本）。
