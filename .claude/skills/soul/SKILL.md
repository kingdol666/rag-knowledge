---
name: soul
description: >
  SOUL 人格系统 — 人格生命周期管理(增删改查)、好奇心驱动的自动训练循环、
  训练评估闭环,以及按任务自动路由到对应 SOUL 人格的检索增强问答。
  与 knowledgebase skill 平行: knowledgebase 管"知识本身",soul 管"用哪个人格
  来加工知识"。触发词: 人格, SOUL, 人格训练, 训练人格, 创建人格, 删除人格,
  人格列表, 人格问答, 用某个人格回答, 用研究者人格, 用创意人格, 人格检索增强,
  persona, soul, soul_ask, soul_init, soul_learn, soul_learn_all, soul_reflect,
  soul_review_drafts, soul_export, soul_delete, soul_status, soul_router,
  自动训练, 好奇心训练, 人格进化。
---

# SOUL — 人格系统调度器

**执行者:主 Agent 直接执行(SOUL 操作是管理/问答编排,不委托 Archival)**

SOUL 人格系统是知识库之上的"人格加工层":
- **知识库管"有什么"**(knowledgebase skill,72 个 kb_* 工具)
- **SOUL 管"谁来讲、怎么讲"**(16 个 soul_* MCP 工具)

> **⭐ SOUL 心智模型**:每个人格 = 一个 `soul-<name>` 知识库,含 4 个人格文档
> (soul-definition/values/thinking-style/memory-conventions)+ soul-config.yml
> (kb_scope 学习范围/domain_labels 路由标签/is_template)。模板库 `soul-template`
> 是唯一 is_template=true 的库,不出现在任何人格操作中。
> 学习范围(kb_scope)决定人格"能学什么";路由标签(domain_labels)决定"什么
> 问题派给谁"。详细机制见 [references/soul-architecture.md](references/soul-architecture.md)。

---

## 思维框架:场景归类 ⭐

```
用户说了一句话
  └── 包含 SOUL 关键词?
       ├── 是 → 匹配下表场景
       └── 否 → 若含知识库关键词 → 交给 Skill("knowledgebase")
                否则 → "请说明: 管理人格 / 训练人格 / 用某个人格问答 / 查看人格状态?"
```

匹配后:
  ├── 人格管理(增删改查)→ 执行 §A
  ├── 人格训练(自动/手动)→ 执行 §B
  ├── 人格问答(显式/自动路由)→ 执行 §C
  ├── 人格评估(自评/校准/反思)→ 执行 §D
  └── 混合场景 → 按 管理 → 训练 → 评估 → 问答 顺序

---

## 场景分类表

| Signal keywords | 场景 | 执行 |
|---|---|---|
| 创建人格, 新建 SOUL, 新人格, 初始化人格, soul_init, create persona | **Create** | §A1 `soul_init` |
| 删除人格, 移除人格, soul_delete, delete persona | **Delete** | §A2 `soul_delete` |
| 人格列表, 所有人格, 查看人格, soul_list, list personas | **List** | §A3 `soul_list` + `soul_status` |
| 人格配置, 修改人格, 调整学习范围, 改领域标签, soul_config_update | **Configure** | §A4 `soul_config_update` |
| 训练人格, 人格学习, 自动训练, 好奇心训练, 全库自举, soul_learn, soul_learn_all | **Train** | §B `soul_learn`/`soul_learn_all` |
| 开启自动训练, 定时训练, 启用调度, 自动学习循环 | **AutoTrain** | §B2 调度器启用 |
| 审批记忆, 记忆草稿, 人格记忆, soul_review_drafts, approve memory | **Review** | §D1 `soul_review_drafts` |
| 人格评估, 自评, 校准, soul_eval, soul_calibrate | **Evaluate** | §D2 `soul_eval`/`soul_calibrate` |
| 人格反思, 漂移报告, soul_reflect, reflect | **Reflect** | §D3 `soul_reflect` |
| 人格问答, 用XX人格回答, 人格检索增强, soul_ask | **Ask** | §C `soul_ask`(显式或自动路由) |
| 导出训练数据, 微调数据, soul_export, LoRA | **Export** | §D4 `soul_export` |
| 检查点, 回滚人格, soul_checkpoint, soul_rollback | **Rollback** | §D5 `soul_checkpoint`/`soul_rollback` |

---

## Sequential Workflow

### Step 0 — Pre-Flight(强制)

SOUL 操作依赖 kb-mcp 服务(16 个 soul_* 工具)+ 后端(LLM 合成通道)。
执行任何场景前,先调 `soul_list` 验证:
- 工具可达 → MCP 连通
- 返回列表(可能为空)→ 后端在线
失败则提示"MCP/后端不可用",不得继续。

### Step 1 — 场景匹配
按上表最长关键词优先匹配。人格问答与知识库检索可能重叠:
- 用户说"帮我查/搜XX" → **knowledgebase-search**(知识检索)
- 用户说"用XX人格回答/以XX口吻回答/人格增强" → **soul Ask**(人格加工)
- 用户说"检索后用人格回答" → **soul-rag 子 skill**(检索+人格增强组合)

### Step 2 — 执行对应场景(见下)

---

## §A 人格管理(增删改查)

### A1 Create — `soul_init`
```
soul_init(soul_name="soul-<名字>", kb_scope=[<公开库列表>],
          domain_labels=[<中文领域标签>], supported_task_types=[<任务类型>])
```
- 名字规则:`soul-` 前缀 + 中英文/数字/连字符;拒绝 Windows 保留名
- kb_scope 安全默认:**空 = 只问答不学习**;显式列库才可训练;禁含 soul- 前缀
- 完成后必验证:返回 docs_created=4 且 profile_summary_generated=true

### A2 Delete — `soul_delete`
```
soul_delete(soul_kb_id)   # 先自动 checkpoint → 删库 → 清路由缓存
```
- 删除前自动留快照(可审计);删除后 soul_list 不再出现

### A3 List — `soul_list` + `soul_status`
```
soul_list()                # 所有人格(排除模板)
soul_status(soul_kb_id)    # 学习指标: 草稿/记忆/缺口/成本/掌握曲线
```
- 汇报: 人格名 + kb_scope + 草稿/记忆数 + 预算消耗

### A4 Configure — `soul_config_update`
```
soul_config_update(soul_kb_id, kb_scope/domain_labels/supported_task_types/route_weight)
```
- scope 缩小 → 旧范围记忆自动标记 stale(不删)
- route_weight=0 → 该人格退出路由

---

## §B 人格训练(好奇心驱动的自动学习)

> **⭐ 训练原理**:SOUL 的"好奇心"= 对 kb_scope 内文档自动生成四层问题
> (事实/概念/跨文档/挑战),检索知识库自答,四维自评(接地性/完整性/
> 思维一致/信息增益),≥3 分且无判官分歧才蒸馏为记忆草稿 → 人工审批 →
> 注册索引 → 人格进化。**评价后继续训练**:已学文档记录 learned_hash,
> 内容变更自动重新学习;新文档随时可学。完整协议见
> [references/soul-training.md](references/soul-training.md)。

### B1 手动训练(单文档/多文档)
```
soul_learn(soul_kb_id, doc_paths=[...], limit=6)   # 异步,返回 task_id
# 轮询 kb_task_status(task_id) 直到 done
```
- 文档必须在 kb_scope 内;预算 0.15 USD/run
- 完成后 soul_status 看新草稿

### B2 全库自举(一次训练全部未学文档)
```
soul_learn_all(soul_kb_id="", max_docs=20, dry_run=False)
# 建议先 dry_run=True 看预估成本/重叠率,再实际执行
```
- 空 soul_kb_id = 全部人格;内容 SHA256 去重防跨人格重复学习

### B3 ⭐ 自动训练循环(无人值守)
```
1. 为每个 SOUL 启用调度:
   experience_meditation_config_update(soul_kb_id, {
     "meditation_mode": "soul", "enabled": true,
     "interval_hours": 24, "max_budget_usd": 0.15, "max_questions_per_run": 10})
2. 确认全局调度已开(backend config experience_auto.enabled=true,
   默认关闭,需管理员开启)
3. 调度器每 interval_hours 遍历 SOUL → learn_incremental:
   只学"内容变更/未学过"的文档(learned_hash 增量),零新增时 0 成本
4. 定期(每周)人工审批记忆草稿(soul_review_drafts)完成进化闭环
```
- **评价后继续训练**:learned_hash 机制保证文档更新后自动重学;
  新入库文档自动进入下轮训练
- 预算保护:每 SOUL 0.15/run,超限拒绝;熔断/信号量防失控

---

## §C 人格问答(检索增强)

> **⭐ 增强原理**:soul_ask = 按人格注入(identity/values/thinking-style)+
> kb_scope 内两阶段检索 + 人格记忆摘要 + LLM 合成 → 答案带结构化 citations
> + PAS(人格一致性分)。检索范围 = 人格绑定的 kb_scope;人格记忆也被检索。

### C1 显式指定人格
```
soul_ask(query, soul_kb_id="soul-<name>", task_goal, task_type, async_mode=True)
```
- async_mode=True 返回 task_id → 轮询 kb_task_status
- 返回: answer/citations[]/pas_score/selected_soul/route_*

### C2 自动路由(不指定人格)
```
soul_ask(query, task_goal, task_type, async_mode=True)
# 空 soul_kb_id → soul_router 按 domain_labels + profile 摘要打分选最优人格
```
- 路由决策可审计(router-log);显式指定可覆盖
- 低置信度 → route_uncertain=true + 候选列表,不硬选

### C3 ⭐ 检索+人格增强组合(kb_search → soul_ask)
当用户问"从知识库查XX,用YY人格回答"或需要"先检索后人格化":
1. `kb_search_two_stage(query, kb_id=<目标库>, ...)` 定位知识
2. `soul_ask(query, soul_kb_id="soul-<name>", context_override=<检索到的关键片段>)`
   → context_override 注入检索结果作为临时背景,人格化加工
完整策略见 [references/soul-rag-strategy.md](references/soul-rag-strategy.md),
或直接用 `Skill("soul-rag")`。

---

## §D 人格评估与进化

| 场景 | 工具 | 说明 |
|---|---|---|
| D1 记忆审批 | `soul_review_drafts` action=list/approve/reject | 批准 → 注册+索引,60s 可检索;低分需 force |
| D2 自评/校准 | `soul_eval` / `soul_calibrate` | 四维评分;校准集重跑检测漂移 |
| D3 反思 | `soul_reflect` | 认知草稿 vs 人格定义结构化 diff 漂移报告 |
| D4 导出 | `soul_export(min_score)` | 高质量记忆 → JSONL 训练数据(LoRA/DPO) |
| D5 回滚 | `soul_checkpoint` / `soul_rollback` | 快照/恢复记忆层;宪法层永不回滚 |

审批黄金规则:
- 接地性 ≥3 且四维均分 ≥3 → 正常批准
- 低于 → 需 force=True 并记录理由(审计日志)
- 批准后人格 profile 自动刷新 → 路由依据同步更新

---

## Rules — 强制执行

1. **MCP 优先**: 一切 SOUL 操作走 `mcp__kb-mcp__soul_*` 工具,禁止 curl/python 直调
2. **不碰宪法层**: 自动流程永不修改 values.md / soul-definition.md / soul-config.yml 本体
3. **预算敬畏**: 训练前检查 soul_status.estimated_cost_usd;超 0.15 拒绝
4. **模板隔离**: soul-template 永不参与训练/路由/问答
5. **审批闭环**: 记忆草稿必须经 soul_review_drafts 审批才生效(人格进化唯一通道)
6. **路由可覆盖**: 自动路由结果不理想 → 显式 soul_kb_id 重试
7. **与 knowledgebase 分工**: 知识操作(入库/搜索/管理)走 knowledgebase skill;
   本 skill 只处理"人格层"。混合需求 → knowledgebase 执行后 soul 增强。

## NEVER 清单

| ❌ | ✅ |
|---|---|
| 用 kb_doc_create 建人格记忆 | 记忆只经 soul_learn→soul_review_drafts |
| 直接改 soul-config.yml | 只经 soul_config_update |
| 训练模板库 soul-template | is_template 拒绝 |
| 对无 kb_scope 的人格训练 | 空 scope=只问答,learn 拒绝 |
| 跳过审批直接当记忆用 | 审批后注册+索引才可检索 |
| 忽略预算跑全库自举 | 先 dry_run 看成本 |
| 把 SOUL 问答当普通检索 | 人格问答必须走 soul_ask(带人格注入) |

## Tool Quick Reference

- `soul_list()` / `soul_status(soul_kb_id)` — 查看人格与学习指标
- `soul_init(soul_name, kb_scope, domain_labels, supported_task_types)` — 创建人格
- `soul_config_update(soul_kb_id, ...)` — 修改配置(scope/标签/权重)
- `soul_delete(soul_kb_id)` — 删除人格(先留快照)
- `soul_learn(soul_kb_id, doc_paths, limit)` / `soul_learn_all(soul_kb_id, max_docs, dry_run)` — 训练(异步)
- `soul_eval(soul_kb_id, question, answer, evidence_paths)` / `soul_calibrate` — 评估
- `soul_review_drafts(soul_kb_id, action, draft_ids, force)` — 记忆审批
- `soul_reflect(soul_kb_id)` / `soul_checkpoint` / `soul_rollback` — 反思/回滚
- `soul_export(soul_kb_id, min_score)` — 训练数据导出
- `soul_router(query, task_goal, task_type)` — 路由决策预览
- `soul_ask(query, soul_kb_id, task_goal, task_type, context_override, async_mode)` — 人格问答(核心)
- `experience_meditation_config_update(soul_kb_id, {...})` — 自动训练调度配置
