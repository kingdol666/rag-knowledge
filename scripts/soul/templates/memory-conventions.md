# 记忆约定 — soul-template

## 记忆类型
- 人格记忆(memories/): 高质量问答沉淀,frontmatter 含 question/q_hash/evidence_paths/scores/pas_score
- 认知文档(cognition/): 自我认知与反思结论
- 知识经验: 通过 experience 草稿池进入共享知识层

## 记忆准入标准(硬闸门)
- 接地性 ≥3(代码校验引用路径存在 + LLM 关联分)
- 检索前置门通过(≥1 chunk 相似度 ≥0.5)
- 无 judge_divergence(分歧 ≤1.5)

## 记忆生命周期
- pending(草稿,不索引)→ approved(人工审批后注册+索引)→ stale(scope 变更后标记,不删)
- 检查点可回滚 memories/ 与 cognition-drafts/

## 审批规则
- 接地性<3 或四维均分<3 需 force=True 才能批准
- 批准记录写入 audit/approval-log.jsonl
