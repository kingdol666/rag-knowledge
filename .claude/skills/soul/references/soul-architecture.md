# SOUL 架构参考 — 人格系统工作机制

> 供 soul / soul-rag skill 的执行者建立正确心智模型。

## 1. 人格是什么

**人格 = 一个特殊知识库 `soul-<name>`**,包含:

```
soul-<name>/
├── soul-definition.md      # 人格定义(身份五维/性格五维/知识边界/语言风格)
├── values.md               # 价值观(宪法层 — 自动流程只读)
├── thinking-style.md       # 思维风格(推理模式/论证习惯/回答组织)
├── memory-conventions.md   # 记忆约定(准入标准/生命周期/审批规则)
├── soul-config.yml         # 配置(宪法层 — 只经 soul_config_update 修改)
│     kb_scope: [...]           # 学习范围(可学的公开库;空=只问答不学)
│     domain_labels: [...]      # 路由标签(什么话题派给谁)
│     supported_task_types: []  # 路由任务类型注册值
│     route_weight: 1.0         # 路由权重(0=退出路由)
│     is_template: false        # 仅 soul-template 为 true
├── memories/               # 人格记忆(approved 注册+索引,pending 隔离)
├── cognition/              # 自我认知(反思结论)
├── cognition-drafts/       # 认知草稿(待审批)
├── checkpoints/            # 检查点(回滚依据,保留 30 个)
├── reports/                # profile-summary / drift 报告
├── questions/gaps.md       # 学习缺口记录
├── calibration/            # 校准集(人工评分)
├── training/               # 导出训练数据
└── audit/                  # 审批/成本审计日志
```

模板库 `soul-template` 是唯一的 is_template=true 库:
- 不出现在 soul_list / 路由候选 / learn_all
- 对它的写操作全部拒绝
- 新人格经 `soul_init` 从它复制 4 个人格文档

## 2. 数据流(五层一致)

```
磁盘 .md  ←→  .tree-fs.json  ←→  .knowledge-base.yml  ←→  ChromaDB 向量  ←→  Neo4j 图谱
```

与 knowledgebase 的 5 层模型完全一致。SOUL 的特殊规则:
- **pending 草稿不注册文档**(不索引,隔离)
- **approved 记忆注册 + 索引**(审批后 60s 可检索)
- soul-config.yml 是裸文件,直接 FS 读写,不参与向量索引

## 3. 人格问答(soul_ask)内部链路

```
soul_ask(query, soul_kb_id?, task_goal?, task_type?, context_override?)
  │
  ├─ soul_kb_id 为空? → soul_router 自动路由
  │     ├─ 候选 = soul_list(排除模板)
  │     ├─ >8 个 → domain_labels embedding 余弦初筛 top8
  │     ├─ 读 profile-summary 摘要(缓存,learn/审批/reflect 后刷新)
  │     ├─ LLM 打分(注入 route_weight) → top1 ≥ 阈值 0.6 → 选中
  │     └─ complete() 失败 → embedding 余弦降级路由
  │
  ├─ 加载人格(4 文档 + 配置)
  ├─ 检索知识包: kb_scope 内 two_stage(balance_kbs 多库一次)
  │     + 图谱邻居(限 scope 内) + 最近 10 条 approved 记忆摘要
  ├─ LLM 合成: 人格注入 + 知识包 → answer + citations
  ├─ PAS 评分: 人格一致性(语言风格短语命中 + 价值观对齐)
  └─ 返回: answer / citations[{path, chunk_text, score, relevance_reason}]
           / pas_score / selected_soul / route_*
```

**同步/异步**: async_mode=True 立即返回 task_id,`kb_task_status` 轮询
(合成 + PAS 两个 LLM 调用约 60-120s)。

## 4. 人格训练(soul_learn)内部链路

```
soul_learn(soul_kb_id, doc_paths, limit)
  ├─ 锁: per-soul asyncio.Lock(同人格串行)
  ├─ 校验: 非模板 / scope 非空 / 文档在 scope 内 / 预算充足
  ├─ 每文档:
  │    generate_questions(LLM 四层问题 + 关键词分类器交叉校验 + q_hash 去重)
  │      → self_answer(scope 检索 + 相似度≥0.5 前置门 + LLM 带引用自答)
  │      → eval_answer(代码接地性×LLM 四维取 min + 10% 双判官)
  │      → distill(接地性≥3 无分歧 → 记忆草稿;PAS≥4 → 同步共享经验池)
  │      → 有产出才记录 learned_hash(内容 SHA256 → metadata)
  ├─ 预算: check-and-deduct(0.15/run);调用计数 ≤30/run
  └─ 报告: questions_generated / memories_created / gaps_count / cost
```

**好奇心引擎**: 四层问题 = 事实(30%)/概念(30%)/跨文档(20%)/挑战(20%)。
挑战型问题重点倾斜 → 探索知识边界。

**评价后继续训练(增量)**:
- learned_hash 存于文档 metadata;内容 SHA256 一致 → 跳过(0 成本幂等)
- 文档更新 → hash 不匹配 → 自动重新学习
- 新入库文档 → 下轮自动进入训练范围

## 5. 自动训练调度

- 每 SOUL 独立 meditation config(mode=soul, enabled, interval_hours, budget)
- 后端调度器(experience_meditation_service)每 interval_hours 遍历:
  `mode==soul` → `_run_soul_meditation` → `learn_incremental`
- **默认 enabled=false**(安全): 需显式开启 + 全局 experience_auto.enabled=true
- 预算保护: 每 SOUL 0.15 USD/run;全局 Semaphore(2) 并发;熔断 3 连败 24h

## 6. 质量闸门链(防自嗨)

```
检索前置门(≥0.5) → 代码接地性(路径存在率×5) × LLM 接地性 → min
→ 四维评分 → 10% 双判官(分歧>1.5 拦截) → 蒸馏(≥3 才写草稿)
→ 人工审批(≥3 正常,<3 需 force+审计) → 注册+索引
→ 校准集(≥20 条)漂移检测 → reflect 漂移报告
```

## 7. 与 knowledgebase 的分工

| 场景 | 走哪个 skill |
|---|---|
| 入库/解析/管理/搜索知识 | `knowledgebase`(72 个 kb_* 工具) |
| 人格管理/训练/评估 | `soul`(16 个 soul_* 工具) |
| 检索 + 人格增强回答 | `soul-rag`(kb_search → soul_ask 组合) |
| 人格训练数据导出/微调 | `soul` §D4 + docs/soul-lora-pipeline.md |

## 8. 常见错误码

| 错误 | 含义 | 处理 |
|---|---|---|
| kb_not_found | soul_kb_id 不是 SOUL 库 | 检查名字/路径 |
| is_template | 对模板库操作 | 换真实人格 |
| scope_contains_soul_kb | kb_scope 含 soul- 前缀 | 移除 |
| scope_kb_missing | scope 内库不存在 | 用 kb_list 核实 |
| budget_exceeded | 预算不足 | 等重置或确认消耗 |
| insufficient_calibration | 校准集 <20 条 | 先补校准集 |
| no_prompt_change | 提示词未变无需重跑 | 正常状态 |
| lock_timeout | 人格被其他操作锁定 | 稍后重试 |
