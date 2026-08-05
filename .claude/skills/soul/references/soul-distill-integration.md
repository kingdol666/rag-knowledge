# SOUL × 补天(dot-skill)集成协议 — 先天蒸馏 + 后天进化

> soul skill §E 的权威细则:如何把补天蒸馏的初始人格接入 SOUL,
> 并通过好奇心训练让种子不断进化。

## 1. 双引擎模型

```
补天 butian 调度(一次性)                  SOUL 好奇心训练(终身)
─────────────────────                  ─────────────────────
nuwa-skill(公开人物/主题深研)              kb_scope 内文档
  [person]-perspective/SKILL.md           │
  心智模型/决策启发式/表达DNA/智识谱系      四层问题(事实/概念/跨文档/挑战)
  │ → nuwa_to_seed.py 转换                 │
dot-skill(同事/关系/本地材料)             检索自答 → 四维自评 → 蒸馏
  persona.md(身份/风格/口头禅)            │
  work.md(职责/规范/流程)                │
  meta.json(name/tags/impression)       │
   │                                      │
   └──────────┬─────────────────────────────┘
              ▼
        SOUL 人格(soul-<name>)
        ├─ 宪法层(初始化时写入, 之后只读):
        │    soul-definition.md(模板+persona.md)
        │    thinking-style.md(模板+work.md)
        │    values.md(模板 [+nuwa 价值观]) / memory-conventions.md(模板)
        └─ 进化层(训练持续写入):
             memories/(审批后记忆) · questions/learned-hashes.json
             cognition/ · checkpoints/ · audit/cost-log.jsonl
```

**先天 = 身份与风格(蒸馏一次);后天 = 知识与经验(持续积累)。**

## 2. 蒸馏产物 → SOUL 映射

| dot-skill 产物 | SOUL 文档 | 说明 |
|---|---|---|
| `persona.md`(Layer0 核心性格/Layer1 身份/Layer2 表达风格) | `soul-definition.md` 追加段 | 保留模板章节(profile-summary 生成器与 language-style 解析依赖模板结构), 补天内容作为"# 补天蒸馏人格"段落追加 |
| `work.md`(职责范围/工作规范) | `thinking-style.md` 追加段 | 同上, 补天工作方式追加 |
| `meta.json.tags.personality` | `domain_labels`(默认) | 路由标签: 什么问题派给谁 |
| `meta.json.impression` | `domain_labels` 补充 + KB description | 人格印象也参与路由打分 |
| `meta.json.slug` / `--name` | `soul-<slug>` | 人格库名 |
| (模板默认) | `values.md` / `memory-conventions.md` | 研究型价值观; 可后续按需定制 |

**nuwa-skill 产物**(经 butian `nuwa_to_seed.py` 转换后同契约落地, 章节级映射见
`../../nuwa-skill/references/soul-seed-mapping.md`):

| nuwa SKILL.md 章节 | → 种子 → SOUL 文档 | 说明 |
|---|---|---|
| 身份卡 / 表达DNA / 角色扮演规则 / 诚实边界 | persona.md → `soul-definition.md` 追加段 | 身份+语言风格+边界 |
| 回答工作流 / 核心心智模型 / 决策启发式 / 智识谱系 / 人物时间线 / 失败模式 | work.md → `thinking-style.md` 追加段 | 思维框架+工作方式 |
| 价值观与反模式 | values.md → `values.md` 追加段 | 宪法层价值观, `ragctl soul distill --values` 创建时融合 |
| frontmatter name/description | meta.json → `soul-<slug>` + domain_labels | 路由标签 = 人格名+模型名 |

## 3. 两种执行路径

### 3a. ragctl 一键(推荐, 与前端/MCP 同后端)
```bash
ragctl soul distill <dot-skill产出目录> \
  --name soul-<名字> --scope kb1,kb2 --labels 标签 --harness omp
```
内部自动完成: web 建库 → web 写 4 文档(模板+补天融合)→ 后端 bootstrap
(soul-config + profile-summary + meditation config)→ 索引 4 文档。
domain_labels 缺省 = meta.tags.personality 前 3 + impression 前 12 字。

### 3b. MCP/前端手动编排(主 agent 执行)
```
1. kb_create(name=soul-<名字>, description=impression)      # web 层
2. kb_doc_create ×4:                                         # web 层
     soul-definition.md = 模板 + persona.md
     thinking-style.md  = 模板 + work.md
     values.md / memory-conventions.md = 模板
3. POST /api/v1/soul/bootstrap {
     soul_kb_id, kb_scope(缺省 ["*"]), domain_labels, harness }
4. index_document ×4(soul-definition/thinking-style/values/memory-conventions)
```
完成后 soul_list 可见; 前端 SOUL 页面卡片展示 harness/scope/定时状态。

## 4. 后天进化(种子成长闭环)

```
阶段1 好奇心训练(立即):
  soul_learn_all(soul_kb_id, rounds=2)   # 每轮学一批增量文档
  # 或 soul_learn(soul_kb_id, doc_paths=[...], rounds=1) 指定文档

阶段2 记忆审批(进化唯一通道):
  soul_review_drafts(soul_kb_id, action=list)
  soul_review_drafts(soul_kb_id, action=approve, draft_ids=[...])
  # 批准 → 注册+向量/图谱索引 → profile 刷新 → 路由依据更新

阶段3 定时自动进化(无人值守):
  experience_meditation_config_update(soul_kb_id, {
    meditation_mode: soul, enabled: true,
    interval_hours: 24, rounds_per_run: 2,   # 每轮定时训练 2 轮
    max_budget_usd: 0.15, max_questions_per_run: 10})

阶段4 健康检查(防漂移):
  soul_reflect(soul_kb_id)     # 认知草稿 vs 人格定义 diff
  soul_calibrate(soul_kb_id)   # 评估器校准(需校准集 ≥20 条)
  soul_checkpoint / soul_rollback   # 安全网

阶段5 使用(人格增强检索):
  soul_qdcvr_ask(query, soul_kb_id)   # 一键: QDCVR 检索 → 人格合成
  # 或 ragctl soul ask "..." --soul soul-<名字>
  # 或前端问答 modal "一键检索+人格回答"
```

## 5. 与三入口的一致性

| 操作 | 前端(SOUL 页面) | ragctl | MCP 工具 | 同一数据 |
|---|---|---|---|---|
| 蒸馏创建 | —(建议 ragctl) | `soul distill` | soul_init + 文档覆盖 | ✅ |
| 训练 | 训练 modal(轮数/文档/全库) | `soul learn/learn-all` | soul_learn/learn_all | ✅ |
| 审批 | 审批 modal | `soul review` | soul_review_drafts | ✅ |
| 问答 | 一键检索+人格回答 | `soul ask --soul` | soul_qdcvr_ask / soul_ask | ✅ |
| 定时 | 配置 modal(间隔/轮数) | `meditation config` | experience_meditation_config_update | ✅ |
| harness | 配置 modal | `harness` / `soul harness` | soul_init harness / config | ✅ |

所有入口读写同一后端存储(.knowledge-base.yml / memories / learned-hashes),
任一入口操作后其他入口立即可见(刷新即得)。

## 6. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| distill 后 profile 是通用风格 | bootstrap 的 profile-summary 基于融合文档生成, 补天内容在后半段 | 可再跑 soul_config_update 触发 profile 刷新; 或直接编辑 profile-summary(不推荐) |
| 训练秒回 skipped | 该 SOUL 已学(per-SOUL learned_hash) | 换新文档; 或等待文档内容变更自动重学 |
| 问答风格不像蒸馏人格 | 蒸馏内容在 soul-definition 追加段, 注入 prompt 截取前 1500 字 | 把 persona 核心段放到文档靠前位置; 或精简模板头 |
| domain_labels 太泛 | meta 无 personality tags | distill 时显式 --labels |
