# SOUL 训练协议 — 统一 RL 三角色强化学习(Actor × Critic × Updater)

> 本文件是 soul skill §B 的权威细则:统一 RL 训练架构、收敛检测、
> 自动应用机制、以及自动循环调度协议。
>
> **⭐ 重构要点(2026-08)**: 训练统一为唯一 RL 模式(soul_train_rl),
> 自动集成知识学习(Actor)+ 六维评价(Critic)+ 权重更新(Updater)。
> 旧的 learn/learn_all 降级为 RL 的 Actor 子组件, learn_incremental 升级为
> 并行批处理(learn_incremental_parallel, 提速 4-5x)。

## 0. ⭐ 异步任务契约(所有长任务统一模式)

训练/批量审批是分钟级长作业, **一律异步执行 + task_id 轮询进度**, 任何入口
都不同步阻塞等待: 触发即返回 `task_id`, 过一段时间查进度, 完成后取结果。

```
触发(MCP/web/ragctl) → 立即返回 {task_id, status: running}
  └─ 后端 soul_task_runner 独立任务执行(参考 parse 的 task_registry 模式)
轮询进度: kb_task_status(task_id)  /  GET /api/v1/soul/tasks/{task_id}
  └─ running 时返回 progress:
      训练: {round, rounds, questions, memories, docs_processed, skipped, gaps}
      审批: {processed, total, approved, rejected}
done    → result 含完整报告(souls[] / per_round / results[])
error   → error 字段含失败原因
```

- 后端: POST /api/v1/soul/{kb}/learn 与 /learn-all 传 `async_mode: true`
  → 立即返回 task_id; GET /api/v1/soul/tasks 列出全部任务
- MCP: soul_learn / soul_learn_all / soul_review_drafts(批量) 已封装异步,
  返回 task_id → kb_task_status 轮询(含 progress 镜像)
- web: /api/soul/learn /train-all /review 默认 async_mode, 返回 task_id;
  /api/soul/tasks/:taskId 代理进度; SOUL 页面训练/审批 modal 轮询展示进度
- 同步兼容: 后端 async_mode 缺省 False, 旧调用方行为不变

## 1. 训练触发方式(推荐: 统一 RL)

### 1a ⭐ RL 统一训练(唯一推荐入口)
```
soul_train_rl(soul_kb_id="soul-musk", rounds=2)   # 异步, task_id → kb_task_status 轮询
```
每轮四阶段: Actor(并行知识学习)→ Critic(六维评价)→ Updater(权重更新)→ Reward(记录)。
收敛态(连续 2 轮 reward 变化<0.25)时: Actor 减半问题数, Updater 认知草稿自动应用。

### 1b 手动单文档(Actor 单跑)
```
soul_learn(soul_kb_id="soul-催化", doc_paths=["Chemistry-Catalysis/photocatalysis.md"], limit=6)
→ task_id → kb_task_status 轮询
```
适用: 精确控制学哪些文档。

### 1b 全库自举(增量)
```
soul_learn_all(soul_kb_id="", max_docs=20, dry_run=true)   # 先看预估
soul_learn_all(soul_kb_id="", max_docs=20)                  # 实际执行
```
- 空 soul_kb_id = 遍历全部人格 × 各自 kb_scope
- 文档级内容 SHA256 去重: 已被任何人格学过的文档跳过(跨人格不重复学)
- dry_run 返回: unique_docs / duplicate_docs / cross_soul_overlap_pct / per_soul 成本

### 1c 自动调度(无人值守)⭐
```
experience_meditation_config_update(soul_kb_id, {
  "meditation_mode": "soul",
  "enabled": true,
  "interval_hours": 24,        # 学习频率
  "max_budget_usd": 0.15,      # 每轮预算上限
  "max_questions_per_run": 10, # 每轮问题上限
  "rounds_per_run": 2          # 每轮定时训练执行 N 轮 RL
})
```
前置条件(需管理员一次性配置):
1. 后端 config.yml `experience_auto.enabled: true`(默认 false,防误启动)
2. 调度器随后端启动(main.py lifespan 自动 start)

开启后: 调度器每 interval_hours 遍历所有 enabled 的 SOUL → `train_rl`(统一三角色):
- Actor 只学 learned_hash 不匹配(未学/已变更)的文档 → 零新增时 0 成本
- Critic 六维评价 + 收敛检测; Updater 认知草稿(收敛态自动应用)
- 预算/熔断/信号量全部生效

## 2. 好奇心训练协议(每次 learn 内部)

### 2a. 基础链路(四层问题 + 质量闸门)

```
Step 1  文档读取(≤50000 字符)
Step 2  生成 6 个问题(四层):
        fact 30% | concept 30% | cross_doc 20% | challenge 20%
        LLM 生成 + 关键词分类器交叉校验 + q_hash 去重
Step 3  每问题自答:
        两阶段检索(scope 限定,相似度≥0.5 前置门)
        → 图谱邻居(限 scope) → LLM 带引用合成
Step 4  每答案四维自评:
        接地性 = min(代码路径存在率×5, LLM 关联分)
        完整性/思维一致/信息增益(0-5)
        10% 抽样双判官(分歧>1.5 拦截)
Step 5  蒸馏: 接地性≥3 且无分歧 → 记忆草稿(pending)
        PAS≥4 且 info_gain≥3 → 同步共享经验池(sync_dedup_key 幂等)
Step 6  有产出 → 记录 learned_hash(内容 SHA256 → 文档 metadata)
```

### 2b. ⭐ 补天好奇心引擎 v2(元认知自适应 — 默认启用)

算法框架: arXiv:2604.25648(Desvaux/Oudeyer 等, Curiosity and
Metacognition)三原则 → 落地实现:

| 论文原则 | v2 实现(backend/app/services/soul_curiosity.py) |
|---|---|
| 元认知监控与控制 | 每轮训练后刷新 `questions/mastery.json` 掌握画像(per-topic 记忆数/均分/gaps/学习足迹, 零 LLM 成本) |
| 个体画像定制 | `compute_question_mix()`: 按主题掌握度动态调整四层比例(近发展区) |
| 认知伙伴防捷径 | 已知记忆摘要注入 prompt + `novelty_filter()` jaccard 去重, 防止重复学习 |

**自适应问题分布(近发展区 ZPD)**:

```
新主题(首学)     fact 35 | concept 30 | cross 20 | challenge 15   ← 打基础
薄弱/有缺口      fact 20 | concept 30 | cross 30 | challenge 20   ← 补基关联
中等掌握         fact 15 | concept 25 | cross 30 | challenge 30   ← 均衡深化
强掌握(≥4.0)    fact 10 | concept 20 | cross 20 | challenge 50   ← 挑战边界
```

**探索-利用平衡(文档选择)**: 每轮增量扫描 = 新文档(探索)优先 +
薄弱已学文档重学(利用, 有缺口/零记忆/均分<3 的主题), 预算内先探索后补强。

**元认知输入**: 训练 prompt 注入该主题掌握画像(已批准记忆摘要 + 缺口数 +
“难度略高于当前掌握”指令), 保证每轮好奇心都落在最近发展区。

**观察画像**: 训练后 `soul_status` 或直接读
`storage/tree-file-system/soul-<name>/questions/mastery.json`。


## 3. 评估后继续训练(持续进化闭环)

```
文档入库/更新
  └─> learned_hash 不匹配
        └─> 下轮 learn_incremental 自动重学
              └─> 新草稿 → 人工审批(soul_review_drafts)
                    ├─ approve → 注册+索引(60s 可检索)→ profile 刷新
                    │           → 人格记忆沉淀 → 未来 soul_ask 引用
                    └─ reject → 保留在 gaps.md(可追溯)
```

**关键机制**: learned_hash(内容 SHA256 前 12 位)存于
`.knowledge-base.yml` 文档 metadata.learned_hash:
- 内容未变 → 跳过(幂等,0 成本)
- 内容变更 → hash 不符 → 重学
- **0 问题产出时不再标记 learned**(保证解析失败的文档下轮重试)

## 4. 训练健康度检查

每次训练后调 `soul_status(soul_kb_id)` 看:
- `drafts_pending_review`: 待审批草稿(应定期清)
- `total_gaps`: 学习缺口(grounding_below_3 / retrieval_failure)
- `judge_divergence_count`: 判官分歧(质量红线)
- `mastery`: 掌握曲线(问题数 / 平均分)
- `estimated_cost_usd`: 预算消耗(>0.12 注意)

**缺口预警**: gaps 中 retrieval_failure 占比 >30% → 检索配置问题
(scope 文档覆盖不足 / chunk 参数),需排查而非硬调阈值。

## 5. 审批与进化黄金规则

| 草稿分数 | 动作 |
|---|---|
| 接地性 ≥3 且均分 ≥3 | 正常 approve |
| 接地性 <3 或均分 <3 | 需 force=True + 说明理由(写审计) |
| judge_divergence 标记 | 默认 reject(双判官不一致 = 质量存疑) |

审批后系统自动:
1. 记忆文件 status → approved
2. 注册为 KB 文档 + 向量/图谱/BM25 索引
3. profile-summary 刷新(路由依据同步)
4. 审计日志记录(操作人/时间/分数)

## 6. 预算与安全

- 每 SOUL 独立预算 0.15 USD/run(超限拒绝,不透支)
- 路由成本单独全局池(route_cost_usd,不计入学习预算)
- 所有 LLM 调用经全局 Semaphore(2)+ 熔断(3 连败 24h open)
- learn/learn_all 入口预算检查(预估不足拒绝)
- **多人格成本 = ΣN×0.15 为上限**,实际因文档去重更低

## 7. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| learn 秒回 skipped=1 | 文档已学(hash 一致) | 正常幂等,换新文档 |
| questions_generated=0 | 解析失败(罕见,已修 fence 提取) | 重试;确认不误标 learned |
| budget_exceeded | 预算耗尽 | soul_status 看消耗,等周期重置 |
| 0 记忆 4 gaps | 文档与人格 scope 知识不匹配 | 正常质量门,换更相关文档 |
| 训练慢 | 每问题 2-3 次 LLM 调用 | 用 limit=4 控制;async 轮询 |
