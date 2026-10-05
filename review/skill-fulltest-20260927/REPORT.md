# Skill 全量实测报告 v2(120) — 沙盒生命周期 + soul 全链路

- 时间: 2026-09-27 14:22:01 · 步骤: 45 · FAIL: **0**
- 沙盒: KB `s-audit-a-20260927`/`s-audit-b-20260927` + 人格 `soul-skillaudit`(全部已清理)
- 本轮包含修复后复测: .md 命名/空查询门禁/parse_doc 白名单

| # | 步骤 | 结果 | 耗时ms | 明细 |
|---|---|:--:|---:|---|
| 1 | kb_create(A) | ✅ | 477 | kb_id=177ba7b4-a2e7-4169-9974-c65e12958235 |
| 2 | kb_create(B) | ✅ | 277 | kb_id=4d9f1f52-9563-4d42-a5c3-28d79f4ca44f |
| 3 | kb_doc_save_parsed(A5 存储+.md命名) | ✅ | 270 | saved name='zephyr7-spec.md' |
| 4 | kb_doc_create(doc2+tags) | ✅ | 548 | {'success': True, 'source_chars': 160, 'document': {'id': '90f781d5-f007-4f47-8e0a-f5de07962af1', 'n |
| 5 | kb_doc_create(identical)→A0 去重不落盘 | ✅ | 1086 | deduped=True catalog=2 (A0 去重契约) |
| 6 | kb_doc_create(near-dup)落盘=3 | ✅ | 1083 | catalog=3 near-dup 落盘 |
| 7 | kb_doc_update_tags(A3b 标签) | ✅ | 265 | {'success': True, 'kb_id': '177ba7b4-a2e7-4169-9974-c65e12958235', 'kb_path': 's-audit-a-20260927',  |
| 8 | kb_index_document(A6 索引 doc1) | ✅ | 305 | {'success': True, 'vector_index': {'collection': 'kb_177ba7b4-a2e7-4169-9974-c65e12958235', 'chunk_i |
| 9 | kb_batch_index(batch 全量) | ✅ | 301 | {'success': True, 'indexed': [{'doc_path': 'aurora9-protocol.md', 'vector_index': {'collection': 'kb |
| 10 | kb_get_documents(catalog=3) | ✅ | 527 | docs=3 ['aurora9-protocol.md', 'zephyr7-spec-copy.md', 'zephyr7-spec.md'] |
| 11 | kb_doc_read(A7 终检·by doc_id) | ✅ | 774 | content 含 42 liters |
| 12 | kb_search_vector(命中≥0.35) | ✅ | 592 | top_score=0.7326109409332275 |
| 13 | kb_search_two_stage(命中) | ✅ | 11060 | two_stage 命中 aurora |
| 14 | librarian complete_recall(保真) | ✅ | 1164 | complete_recall 保留 Zephyr 事实 |
| 15 | kb_find_duplicates(organize 检出近重复) | ✅ | 825 | total=1 near=1 sims=[0.9947] (≥0.90 阈值) |
| 16 | kb_doc_update_meta(manage 改名) | ✅ | 282 | {'success': True, 'document': {'id': '127c7394-7a57-4cb8-bb5f-afafa9367f45', 'name': 'zephyr7-spec-v |
| 17 | kb_doc_move(A→B) | ✅ | 613 | {'success': True, 'document': {'id': '127c7394-7a57-4cb8-bb5f-afafa9367f45', 'name': 'zephyr7-spec-v |
| 18 | move 后计数 A=2 B=1 | ✅ | 1050 | A=2 B=1 |
| 19 | kb_search_stats(verify 向量面) | ✅ | 30 | collections=24 |
| 20 | kb_graph_build(轮询至完成) | ✅ | 4007 | task→done |
| 21 | kb_graph_search(zephyr) | ✅ | 264 | 图谱含 zephyr 节点 |
| 22 | kb_graph_central_documents | ✅ | 7 | {'success': True, 'documents': [{'gid': 'doc::s-audit-a-20260927/aurora9-protocol.md', 'name': 'auro |
| 23 | experience_create | ✅ | 283 | exp_id=exp-95be2aec060b |
| 24 | experience_search_global(命中) | ✅ | 287 | 经验检索命中 |
| 25 | experience_update(exp_id+合法枚举) | ✅ | 202 | {'success': True, 'experience': {'id': 'exp-95be2aec060b', 'title': '[SkillAudit] near-duplicate det |
| 26 | experience_list(回读校验) | ✅ | 9 | update 落盘可见 |
| 27 | experience_delete(清理) | ✅ | 46 | {'success': True, 'deleted_id': 'exp-95be2aec060b'} |
| 28 | soul_init(异步 task_id) | ✅ | 1438 | task_id=5839671f0511 profile_pending=True |
| 29 | kb_task_status(init 轮询→done) | ✅ | 4005 | status=done |
| 30 | soul_status(预算面) | ✅ | 9 | cost≈0.0 |
| 31 | soul_qdcvr_ask(检索+人格作答 42+citations) | ✅ | 24020 | pas=5.0 citations=3 answer[:60]='结论: Zephyr-7 的冷却液容量为 42 升。\n\n依据(分点陈述, 引用必带出处):\n1. Zephyr-7 Qu' |
| 32 | soul_ask(自动路由或诚实拒答) | ✅ | 36025 | routed→e2e91a7d-e602-4c38-b4c1-aa3f60b18b42 answer[:60]='结论：无法回答。检索到的知识片段中没有任何关于“Aurora-9”或“往返次数（round trips）”的信息，我不能' |
| 33 | 预算 reverence 检查 | ✅ | 0 | estimated_cost_usd=0.0 (≤0.15 才训) |
| 34 | soul_train_rl(rounds=1) | ✅ | 330094 | status=done reward=2.75 |
| 35 | soul_review_drafts(list) | ✅ | 279 | drafts=5 |
| 36 | soul_checkpoint | ✅ | 22 | ckpt=b31f68e79c53406a8d5652d7145ef155 |
| 37 | soul_rollback(回滚到检查点) | ✅ | 5710 | {'success': True, 'rolled_back_to': 'b31f68e79c53406a8d5652d7145ef155', 'restored_memories': 5, 'res |
| 38 | soul_reflect | ✅ | 4990 | D:\codes\ClaudeGPT\rag_project\rag-knowledge\storage\tree-file-system\soul-skillaudit\reports\drift- |
| 39 | soul_export(高分导出) | ✅ | 12 | D:\codes\ClaudeGPT\rag_project\rag-knowledge\storage\tree-file-system\soul-skillaudit\training\expor |
| 40 | 边界: kb_create 重名拒绝(fail-closed) | ✅ | 308 | 重名 KB 被结构化拒绝 ✓ |
| 41 | 边界: soul_init 保留名拒绝 | ✅ | 2 | Windows 保留名被结构化拒绝 ✓ |
| 42 | 边界: 空查询拒绝(新门禁) | ✅ | 2 | 空查询被拒 ✓ |
| 43 | 边界: parse_doc .md 显式拒绝(新门禁) | ✅ | 1 | .md 被 parse_doc 显式拒绝 ✓ |
| 44 | soul_delete(清理+验证) | ✅ | 4905 | deleted, soul_list 无残留=True |
| 45 | kb_delete(A/B 清理+验证) | ✅ | 2731 | 177ba7b4-a2e7-4169-9974-c65e12958235=deleted 4d9f1f52-9563-4d42-a5c3-28d79f4ca44f=deleted 残留=False |