---
name: soul
description: >
  SOUL 人格系统 — 人格全生命周期管理(创建/删除/配置/列表)、补天(dot-skill)
  蒸馏初始人格(含文本蒸馏)、好奇心驱动的训练与 RL 强化进化、任务控制(暂停/
  继续/训练历史)、以及按任务自动路由到对应人格的检索增强问答(QDCVR 先检索
  后人格)。人格 = soul-<name> 知识库(4 宪法层文档 + config), 记忆/认知草稿
  审批闭环。与 knowledgebase skill 平行: knowledgebase 管"知识本身", soul
  管"用哪个人格来加工知识"。触发词: 人格, SOUL, 创建/删除/训练/蒸馏人格,
  补天, 人格问答, 用XX人格回答, 人格检索增强, 一键检索, RL强化, 人格进化,
  暂停训练, 继续训练, 训练历史, persona, soul_ask, soul_qdcvr_ask, soul_init,
  soul_learn, soul_train_rl, soul_review_drafts, soul_delete, soul_router,
  自动训练, 好奇心训练, 固定轮数训练。
---

# SOUL — 人格系统调度器(先天蒸馏 + 后天进化)

**执行者:主 Agent 直接执行(SOUL 操作是管理/问答编排,不委托 Archival)**

SOUL 人格系统是知识库之上的"人格加工层":
- **知识库管"有什么"**(knowledgebase skill,72 个 kb_* 工具)
- **SOUL 管"谁来讲、怎么讲"**(soul_* MCP 工具)
- **补天(dot-skill)管"初始人格从哪来"**(源材料 → persona.md/work.md → SOUL 种子)

> **⭐ SOUL 心智模型**:每个人格 = 一个 `soul-<name>` 知识库,含 4 个人格文档
> (soul-definition/values/thinking-style/memory-conventions)+ soul-config.yml
> (kb_scope 学习范围/domain_labels 路由标签/is_template)。模板库 `soul-template`
> 是唯一 is_template=true 的库,不出现在任何人格操作中。
>
> **MANDATORY — 按需加载参考**:
> - 训练/RL/调度细节 → **必须先读** [references/soul-training.md](references/soul-training.md)(异步契约/预算/learned_hash)
> - 补天蒸馏全协议 → **必须先读** [references/soul-distill-integration.md](references/soul-distill-integration.md)
> - 架构/存储模型 → 需要时读 [references/soul-architecture.md](references/soul-architecture.md)
> - 问答策略组合 → 需要时读 [references/soul-rag-strategy.md](references/soul-rag-strategy.md)
> - **Do NOT Load**: 纯列表/状态查询(§A3)不读任何 reference; 记忆审批(§D1)不读 rag-strategy

---

## 思维框架:场景归类 ⭐

```
用户说了一句话
  └── 包含 SOUL 关键词?
       ├── 是 → 匹配下表场景
       └── 否 → 若含知识库关键词 → 交给 Skill("knowledgebase")
                否则 → "请说明: 管理人格 / 蒸馏人格 / 训练人格 / 用某个人格问答 / 查看人格状态?"
```

匹配后:
  ├── 人格蒸馏(补天种子)→ 执行 §E
  ├── 人格管理(增删改查)→ 执行 §A
  ├── 人格训练(自动/手动/固定轮数)→ 执行 §B
  ├── 人格问答(显式/自动路由/QDCVR 一键)→ 执行 §C
  ├── 人格评估(自评/校准/反思)→ 执行 §D
  └── 混合场景 → 按 管理 → 训练 → 评估 → 问答 顺序

---

## 场景分类表

| Signal keywords | 场景 | 执行 |
|---|---|---|
| 蒸馏人格, 补天, dot-skill, 初始人格, 用聊天记录创建人格 | **Distill** | §E `ragctl soul distill` / dot-skill |
| 创建人格, 新建 SOUL, 新人格, 初始化人格, soul_init, create persona | **Create** | §A1 `soul_init` |
| 删除人格, 移除人格, soul_delete, delete persona | **Delete** | §A2 `soul_delete` |
| 人格列表, 所有人格, 查看人格, soul_list, list personas | **List** | §A3 `soul_list` + `soul_status` |
| 人格配置, 修改人格, 调整学习范围, 改领域标签, 改引擎, soul_config_update | **Configure** | §A4 `soul_config_update` + meditation config |
| 训练人格, 人格学习, 自动训练, 好奇心训练, 全库自举, 固定轮数, rounds | **Train** | §B `soul_learn`/`soul_learn_all`(rounds) |
| 开启自动训练, 定时训练, 启用调度, 自动学习循环 | **AutoTrain** | §B3 调度器启用(rounds_per_run) |
| 审批记忆, 记忆草稿, 人格记忆, soul_review_drafts, approve memory | **Review** | §D1 `soul_review_drafts` |
| 人格评估, 自评, 校准, soul_eval, soul_calibrate | **Evaluate** | §D2 `soul_eval`/`soul_calibrate` |
| 人格反思, 漂移报告, soul_reflect, reflect | **Reflect** | §D3 `soul_reflect` |
| 人格问答, 用XX人格回答, 人格检索增强, soul_ask | **Ask** | §C1/C2 `soul_ask` |
| 一键检索+人格回答, QDCVR 人格问答, soul_qdcvr_ask | **QdcvrAsk** | §C4 `soul_qdcvr_ask` |
| 先检索知识库再回答, 检索后用人格总结 | **RagAsk** | §C3 context_override 组合 |
| 导出训练数据, 微调数据, soul_export, LoRA | **Export** | §D4 `soul_export` |
| 检查点, 回滚人格, soul_checkpoint, soul_rollback | **Rollback** | §D5 `soul_checkpoint`/`soul_rollback` |

---

## Sequential Workflow

### Step 0 — Pre-Flight(强制)

SOUL 操作依赖 kb-mcp 服务(soul_* 工具)+ 后端(LLM 合成通道)。
执行任何场景前,先调 `soul_list` 验证:
- 工具可达 → MCP 连通
- 返回列表(可能为空)→ 后端在线
失败则提示"MCP/后端不可用",不得继续。

### Step 1 — 场景匹配
按上表最长关键词优先匹配。人格问答与知识库检索可能重叠:
- 用户说"帮我查/搜XX" → **knowledgebase-search**(知识检索)
- 用户说"用XX人格回答/以XX口吻回答/人格增强" → **soul Ask**(人格加工)
- 用户说"检索后用人格回答" / "一键检索+人格回答" → **soul_qdcvr_ask**(QDCVR 集成)
- 用户说"蒸馏一个人格/补天" → **§E 补天蒸馏**

### Step 2 — 执行对应场景(见下)

---

## §A 人格管理(增删改查)

### A1 Create — `soul_init`
```
soul_init(soul_name="soul-<名字>", kb_scope=[<公开库列表>],
          domain_labels=[<中文领域标签>], supported_task_types=[<任务类型>],
          harness="omp|claude(空=全局默认)", model="(空=引擎默认)")
```
- 名字规则:`soul-` 前缀 + 中英文/数字/连字符;拒绝 Windows 保留名
- kb_scope 安全默认:**缺省/空 = ["*"] 全部公开库**(默认全库可参与训练);
  需要"仅人格问答"(不学习)时创建后经 soul_config_update 显式设 kb_scope=[]
- harness 缺省 = 全局默认(config.yml soul.default_harness, 默认 omp)
- 完成后必验证:返回 docs_created=4 且 profile_summary_generated=true
- **补天蒸馏入口见 §E**(从源材料生成初始人格,替代默认模板人格)

### A2 Delete — `soul_delete`
```
soul_delete(soul_kb_id)   # 先自动 checkpoint → 删库 → 清路由缓存
```
- 删除前自动留快照(可审计);删除后 soul_list 不再出现

### A3 List — `soul_list` + `soul_status`
```
soul_list()                # 所有人格(排除模板), 含 meditation 摘要(harness/定时/轮数)
soul_status(soul_kb_id)    # 学习指标: 草稿/记忆/缺口/成本/掌握曲线
```
- 汇报: 人格名 + kb_scope + harness + 草稿/记忆数 + 预算消耗 + 定时状态

### A4 Configure — `soul_config_update` + meditation config
```
soul_config_update(soul_kb_id, kb_scope/domain_labels/supported_task_types/route_weight)
experience_meditation_config_update(soul_kb_id, {harness, model, enabled, interval_hours,
                                                 rounds_per_run, max_budget_usd, max_questions_per_run})
```
- scope 缩小 → 旧范围记忆自动标记 stale(不删)
- route_weight=0 → 该人格退出路由
- **harness 是 per-SOUL 的**(meditation config 字段), 未指定时回退全局默认
- 前端: 配置 modal 可视化管理; ragctl: `ragctl soul harness <soul> <omp|claude>`

---

## §B 人格训练(好奇心驱动的自动学习)

> **⭐ 训练原理**:SOUL 的"好奇心"= 对 kb_scope 内文档自动生成四层问题
> (事实/概念/跨文档/挑战),检索知识库自答,四维自评(接地性/完整性/
> 思维一致/信息增益),≥3 分且无判官分歧才蒸馏为记忆草稿 → 人工审批 →
> 注册索引 → 人格进化。**评价后继续训练**:per-SOUL learned_hash
> (soul-<name>/questions/learned-hashes.json)记录已学文档,内容变更自动
> 重新学习;新文档随时可学;**每个 SOUL 独立记录进度**,互不阻塞。
> 完整协议见 [references/soul-training.md](references/soul-training.md)。

### B1 手动训练(单文档/多文档)
```
soul_learn(soul_kb_id, doc_paths=[...], limit=6, rounds=1)   # 异步,返回 task_id
# 轮询 kb_task_status(task_id) 直到 done; running 时 progress 含 {round, rounds,
#   questions, memories, docs_processed, skipped} 实时进度
```
- 文档必须在 kb_scope 内(`*` 范围 = 任意公开库文档);预算 0.15 USD/轮
- rounds>1: 锁内循环多轮,每轮独立预算基线 + 增量扫描(已学文档自动跳过)
- 后端/前端等价入口: POST /api/v1/soul/{kb}/learn (async_mode=true) → task_id;
  GET /api/v1/soul/tasks/{task_id} 查进度;前端 SOUL 页面训练 modal 实时显示进度

### B2 全库自举(一次训练全部未学文档, 支持固定轮数)
```
soul_learn_all(soul_kb_id="", max_docs=20, dry_run=False, rounds=1)
# 建议先 dry_run=True 看预估成本/重叠率,再实际执行
# 异步执行: 返回 task_id → kb_task_status 轮询(progress 逐 SOUL/逐轮更新)
```
- 空 soul_kb_id = 全部人格;每 SOUL 独立 learned_hash(跨人格不互相阻塞)
- rounds=N: 每轮学一批增量文档(每轮 ≤30 次 LLM 调用),直到轮数用完或全部学完;
  **每轮真实产出记忆草稿/成本扣费, 不是假训练**

### B3 ⭐ 自动训练循环(无人值守, 支持固定轮数)
```
1. 为每个 SOUL 启用调度:
   experience_meditation_config_update(soul_kb_id, {
     "meditation_mode": "soul", "enabled": true,
     "interval_hours": 24, "rounds_per_run": 2,     # 每轮定时训练执行 N 轮
     "max_budget_usd": 0.15, "max_questions_per_run": 10})
2. 调度器每 interval_hours 遍历 SOUL → learn_incremental(rounds=rounds_per_run):
   只学"内容变更/未学过"的文档(per-SOUL learned_hash 增量),零新增时 0 成本
3. 定期(每周)人工审批记忆草稿(soul_review_drafts)完成进化闭环
```
- **评价后继续训练**:per-SOUL learned_hash 保证文档更新后自动重学;
  新入库文档自动进入下轮训练
- 预算保护:每轮 0.15 USD(每轮独立预算基线, 不会因历史消耗永久锁死);
  熔断/信号量防失控
- 前端: 配置 modal "启用定时自动训练 + 间隔 + 每轮固定轮数 + 预算 + 问题上限"

### B4 ⭐ RL 强化训练(好奇心×评价 Agent×策略更新)
```
soul_train_rl(soul_kb_id, rounds=2)   # 异步, task_id → kb_task_status 轮询
# 每轮: ① 好奇心探索 learn_incremental ② evaluate_persona 评价 Agent 四维打分
#       ③ 低分维度(<3.5)生成认知草稿(cognition-drafts) ④ reward 写入进化曲线
soul_review_drafts(soul_kb_id, draft_type="cognition", action="approve",
                   draft_ids=[...])   # 审批 → 合并入 soul-definition.md 对应章节
soul_evaluate(soul_kb_id)             # RL 评价Agent四维评分(新工具, MCP重启后注册)
# soul_eval(kb, question, answer, evidence) 为单条答案四维自评(旧工具)
```
- **RL 心智模型**: 探索(learn 新知识)= 观测环境; 评价 Agent 四维打分
  (identity/values/thinking/language 0-5)= 奖励信号; 认知草稿(结构文档
  优化建议)= 策略更新; 审批合并入宪法层 = 策略落地; reward 记录于
  reports/reward-history.jsonl = 进化曲线(模拟人类学习路径)
- **reward 稳定性**: 训练内评价默认 2 次采样中位数平滑(抗 LLM 方差),
  评测集固定为已批准记忆(避免草稿池变化导致评分漂移); 四维均 ≥3.5
  时不再生成认知草稿(收敛态, 0 草稿 = 策略无需更新)
- **宪法层安全**: 认知草稿只做"章节内追加优化行"(不删不改既有内容),
  写前自动 checkpoint, 审批幂等(重复审批拒绝/行级去重), 审批/回滚
  通道与记忆草稿相同; language-style 追加的短语直接参与 soul_ask 注入
  与 PAS 匹配
- 等价入口: POST /api/v1/soul/{kb}/train-rl | evaluate | cognition-drafts;
  前端训练 modal "RL 强化(评价驱动)" 模式 + 审批 modal "认知草稿(RL)" 页签;
  ragctl: soul train-rl / evaluate / review-cognition --all

### B5 ⭐ 任务控制与训练历史(SQLite)
```
ragctl soul task pause|resume|status <task_id>   # 暂停/继续/状态(轮次边界生效)
ragctl soul training [soul_kb_id] [--run run_id] # 训练历史/单次事件流
curl -X POST /api/v1/soul/tasks/{id}/pause       # API 等价
```
- 暂停: 当前 LLM 调用不中断, 在下一轮边界停住; 继续后从断点续跑
- SQLite 持久化(storage/soul-training.db): 每次训练/蒸馏/审批运行
  记录 runs(指标: 轮次/问题/记忆/文档/成本/reward) + events(阶段事件流)
- 前端: 训练控制台 "📚 训练历史" 面板(列表+事件流+状态chip) + 训练中
  "⏸ 暂停/▶ 继续" 按钮; 监控带实时进度
- 查询: GET /api/v1/soul/training/history?[soul_kb_id] / training/runs/{run_id}

### B6 ⭐ 文本补天蒸馏(前端/CLI/Agent 三入口)
```
ragctl soul distill-text <name> --req "人格需求" --material "源材料" [--scope k1,k2]
POST /api/v1/soul/distill {name, personality_req, source_material, ...}  # 异步 task_id
```
- 与 ragctl soul distill(dot-skill 产物目录)互补: 本入口直接接受原始
  源材料(聊天记录/文档/描述) + 人格需求, LLM 提取身份/价值观/思维/
  语言/专长 → 建库 + 4 文档(模板+蒸馏融合) + bootstrap + 索引
- 前端创建 modal 含 "补天蒸馏(可选)" 区: 填入需求+源材料即走蒸馏,
  留空走模板初始化; 蒸馏进度经训练控制台实时追踪
- 蒸馏运行同样写入 SQLite 训练历史(soul_distill)

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

### C3 检索+人格增强组合(kb_search → soul_ask)
当用户问"从知识库查XX,用YY人格回答"或需要"先检索后人格化":
1. `kb_search_two_stage(query, kb_id=<目标库>, ...)` 定位知识
2. `soul_ask(query, soul_kb_id="soul-<name>", context_override=<检索到的关键片段>)`
   → context_override 注入检索结果作为临时背景,人格化加工
完整策略见 [references/soul-rag-strategy.md](references/soul-rag-strategy.md),
或直接用 `Skill("soul-rag")`。

### C4 ⭐ QDCVR 一键集成(soul_qdcvr_ask — 推荐入口)
```
soul_qdcvr_ask(query, soul_kb_id="", task_goal, task_type, top_k=5, async_mode=True)
```
**先按 knowledgebase-search skill 流程检索, 再注入人格增强回答** —
不是直接 soul_ask, 而是"检索 → 验证 → 人格合成"完整链路:
- 检索侧(与 skill Step 2/2.5 对齐): 两阶段检索(BM25+向量+图谱)→ 硬阈值 0.35
  → 文档级去重 → 短内容过滤(<50 chars 丢弃)→ top_k 片段
- 合成侧: 证据注入 context_override → 人格合成(引用锚点校验 + PAS 评分)
- 显式 soul_kb_id 时检索范围 = 该人格 kb_scope;自动路由时跨库
- 返回 answer + citations + pas_score + route_* + **evidence_count**(注入证据数)
- 无命中时人格诚实降级(声明知识库盲区, 不编造)
- 前端: 问答 modal "一键检索+人格回答" 按钮; ragctl: `ragctl soul ask` 带 --qdcvr

---

## §D 人格评估与进化

| 场景 | 工具 | 说明 |
|---|---|---|
| D1 记忆审批 | `soul_review_drafts` action=list/approve/reject | 批准 → 注册+索引,60s 可检索;低分需 force;**批量(≥2 条)自动异步: 返回 task_id → kb_task_status 轮询 progress {processed, total, approved, rejected}(单条含索引 ~20s, 批量串行会超 MCP 30s)**; `draft_type="cognition"` 审批 → 合并入人格定义(RL 策略落地) |
| D2 自评/校准 | `soul_eval` / `soul_calibrate` | 四维评分;校准集重跑检测漂移 |
| D3 反思 | `soul_reflect` | 认知草稿 vs 人格定义结构化 diff 漂移报告 |
| D4 导出 | `soul_export(min_score)` | 高质量记忆 → JSONL 训练数据(LoRA/DPO) |
| D5 回滚 | `soul_checkpoint` / `soul_rollback` | 快照/恢复记忆层;宪法层永不回滚 |

审批黄金规则:
- 接地性 ≥3 且四维均分 ≥3 → 正常批准
- 低于 → 需 force=True 并记录理由(审计日志)
- 批准后人格 profile 自动刷新 → 路由依据同步更新

---

## §E ⭐ 补天蒸馏集成(先天种子 → 后天进化)

> **⭐ 双引擎模型**:补天(dot-skill)给"先天人格种子"(身份/风格/思维框架,
> 一次性蒸馏);SOUL 好奇心训练给"后天知识进化"(KB 证据上持续学习, 终身)。
> 两者正交互补。完整协议见
> [references/soul-distill-integration.md](references/soul-distill-integration.md)。

### E1 蒸馏初始人格(源材料 → 人格种子)
```
# 1) 用补天 skill 蒸馏源材料(聊天记录/文档/描述):
#    在 Claude Code 中: /dot-skill → 输入源材料 → 产出 skill 目录
#    产物: <dir>/meta.json + persona.md + work.md

# 2) 一键转换为 SOUL 人格(ragctl):
ragctl soul distill <dot-skill产出目录> --name soul-<名字> \
  --scope kb1,kb2 --labels 标签1,标签2 --harness omp
# 或 MCP 流程(主 agent 编排, 见 references/soul-distill-integration.md)
```
- 转换逻辑: persona.md → soul-definition.md 追加(保留模板结构,
  profile/language-style 解析正常);work.md → thinking-style.md 追加;
  meta.json tags/impression → domain_labels(路由依据)
- 自动完成: 建库 → 写 4 文档 → bootstrap(profile+meditation config)
  → 索引 → 可训练

### E2 后天好奇心进化(种子成长)
```
ragctl soul learn-all soul-<名字> --rounds 2     # 固定 2 轮好奇心训练
ragctl soul review soul-<名字> --action list      # 审查记忆草稿
ragctl soul review soul-<名字> --action approve --draft <id>
ragctl soul harness soul-<名字> omp               # 训练引擎
ragctl soul ask "问题" --soul soul-<名字>          # 人格增强问答
# 或前端 SOUL 页面: 训练(轮数)/审批/配置(定时)/问答(一键检索+人格回答)
```
- 进化闭环: 训练产出草稿 → 审批注册 → profile 刷新 → 路由更准 → 定时
  训练持续学新文档 → reflect 防漂移 → checkpoint 可回滚

---

## Rules — 强制执行

1. **MCP 优先**: 一切 SOUL 操作走 `mcp__kb-mcp__soul_*` 工具,禁止 curl/python 直调
2. **宪法层受控修改**: 自动流程不直接改 values.md / soul-definition.md / soul-config.yml 本体;
   **唯一例外是 RL 强化通道** —— 认知草稿经 `soul_review_drafts(draft_type="cognition")` 审批后
   自动合并入 soul-definition.md 对应章节(仅章节内追加优化行, 不删改既有内容, 写前 checkpoint)
3. **预算敬畏**: 训练前检查 soul_status.estimated_cost_usd;每轮超 0.15 拒绝
4. **模板隔离**: soul-template 永不参与训练/路由/问答
5. **审批闭环**: 记忆/认知草稿必须经 soul_review_drafts 审批才生效(人格进化唯一通道)
6. **路由可覆盖**: 自动路由结果不理想 → 显式 soul_kb_id 重试
7. **与 knowledgebase 分工**: 知识操作(入库/搜索/管理)走 knowledgebase skill;
   本 skill 只处理"人格层"。混合需求 → knowledgebase 执行后 soul 增强
8. **三入口一致**: 前端(SOUL 页面)/ ragctl(soul 子命令)/ MCP(soul_* 工具)
   走同一后端同一数据, 任何一处操作其他入口立即可见

## NEVER 清单

| ❌ | ✅ | 为什么 |
|---|---|---|
| 用 kb_doc_create 建人格记忆 | 记忆只经 soul_learn→soul_review_drafts | 绕过自评闸门=无质量门, 污染人格记忆库 |
| 直接改 soul-config.yml | 只经 soul_config_update | 绕过校验/索引, 路由数据不一致 |
| 训练模板库 soul-template | is_template 拒绝 | 模板是复制源, 训练会污染所有新人格 |
| 对无 kb_scope 的人格训练 | 空 scope=只问答, learn 拒绝 | 无可学文档=空转烧预算 |
| 跳过审批直接当记忆用 | 审批后注册+索引才可检索 | 未注册=向量/图谱检索不到, 白训练 |
| 忽略预算跑全库自举 | 先 dry_run 看成本 | 全库自举成本 = Σ人格×0.15, 必须先预估 |
| 把 SOUL 问答当普通检索 | 人格问答必须走 soul_ask(带人格注入) | 普通检索无人格注入, 回答失去身份一致性 |
| 把补天产物直接塞进记忆 | 补天 persona 只做初始化文档(宪法层), 知识进化走训练 | persona 是"先天身份"非"后天知识", 混用破坏宪法层 |

**失败回退**: 训练/审批任务不可见(可能 MCP 未重启) → 用 REST 等价入口
`GET/POST http://localhost:8765/api/v1/soul/*`(与 MCP 同数据); 仍失败 →
`kb_project_status()` 查服务健康。

## Tool Quick Reference

- `soul_list()` / `soul_status(soul_kb_id)` — 查看人格与学习指标
- `soul_init(soul_name, kb_scope, domain_labels, supported_task_types, harness, model)` — 创建人格
- `soul_config_update(soul_kb_id, ...)` — 修改配置(scope/标签/权重)
- `soul_delete(soul_kb_id)` — 删除人格(先留快照)
- `soul_learn(soul_kb_id, doc_paths, limit, rounds)` / `soul_learn_all(soul_kb_id, max_docs, dry_run, rounds)` — 训练(异步, 支持固定轮数)
- `soul_train_rl(soul_kb_id, rounds)` — RL 强化训练(好奇心×评价 Agent×认知草稿策略更新, 异步)
- `soul_evaluate(soul_kb_id)` — 评价 Agent 四维人格评分(RL 奖励信号)
- `soul_eval(soul_kb_id, question, answer, evidence_paths)` / `soul_calibrate` — 评估
- `soul_review_drafts(soul_kb_id, action, draft_ids, force, draft_type=memory|cognition)` — 记忆/认知草稿审批
- `soul_reflect(soul_kb_id)` / `soul_checkpoint` / `soul_rollback` — 反思/回滚
- `soul_export(soul_kb_id, min_score)` — 训练数据导出
- `soul_router(query, task_goal, task_type)` — 路由决策预览
- `soul_ask(query, soul_kb_id, task_goal, task_type, context_override, async_mode)` — 人格问答
- `soul_qdcvr_ask(query, soul_kb_id, task_goal, task_type, top_k, async_mode)` — QDCVR 一键检索+人格回答(推荐)
- `experience_meditation_config_update(soul_kb_id, {...})` — 自动训练调度配置(含 rounds_per_run)
- `ragctl soul distill <dot-skill目录> [--name] [--scope] [--labels] [--harness]` — 补天蒸馏 → SOUL
- `ragctl harness [omp|claude]` — 全局默认 harness; `ragctl soul harness <soul> <harness>` — 单人格覆盖
