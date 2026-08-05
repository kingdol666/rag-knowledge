---
name: soul-rag
description: >
  SOUL 检索增强适配器 — 把"知识库检索"与"SOUL 人格加工"组合成统一问答策略:
  先用 kb_search 系列定位知识,再按任务自动路由到最匹配的 SOUL 人格,用
  soul_ask 人格化增强回答(带引用 + PAS 人格一致性分)。不破坏原 knowledgebase
  search 逻辑 — 本 skill 是它的"人格增强层",仅在需要人格化回答时介入。
  触发词: 检索后用人格回答, 人格增强检索, 用XX人格查一下, 以XX口吻回答,
  SOUL 增强, persona-augmented RAG, 检索增强生成人格版, soul-rag,
  查一下并用研究人格回答, 从知识库找XX并用人格总结。
---

# SOUL-RAG — 检索增强的人格化问答

**执行者:主 Agent 直接执行(soul_ask 是单次编排调用,不委托 Archival)**

## 定位(与 knowledgebase-search 的关系)

```
普通检索:    kb_search_two_stage(query, kb_id) → 原始片段列表
SOUL-RAG:    kb_search_two_stage → soul_router 选人格 → soul_ask 人格化合成
                              ↑ 增加"人格注入 + 结构化引用 + PAS 评分"
```

- **不破坏原逻辑**: 需要原始片段/文档定位时,仍走 knowledgebase-search
- **本 skill 加一层**: 需要"谁来讲、怎么讲"时,在检索之上叠加人格加工
- **组合决策树**见下:

## 决策树 ⭐

```
用户请求含"检索 + 人格化"意图?
  ├─ 否(纯检索/纯问答)→ knowledgebase-search / soul §C
  └─ 是 → 判断:
       ├─ 明确指定人格("用研究者人格回答")→ soul_ask(soul_kb_id=显式)
       ├─ 未指定 → soul_ask(空 soul_kb_id)→ 自动路由
       └─ 需要"先看原始证据再人格总结"
            → kb_search_two_stage 取片段 → soul_ask(context_override=片段)
```

## 执行流程

### Step 0 — Pre-Flight
`soul_list` 可用 → 确认人格系统在线;`kb_list` 可用 → 知识库在线。
两者任一失败 → 报错,不继续。

### Step 1 — 解析意图
从用户请求提取: query(核心问题)、persona(指定人格?)、task_goal(教学/研究/创作)、
task_type(文献综述/技术选型/创意策划…)。

### Step 2 — 人格选择
- 指定了人格 → 直接用(显式覆盖路由)
- 未指定 → 先 `soul_router(query, task_goal, task_type)` 预览路由决策
  (看 top1 + confidence + 候选),再决定:
  - confidence ≥0.6 → 用 top1
  - 低置信度 → 把候选列表给用户选,或回退普通检索

### Step 3 — 执行人格化问答
```
soul_ask(query, soul_kb_id=<选中或空>, task_goal, task_type,
         context_override=<可选: 预检索的关键片段>, async_mode=True)
→ task_id → kb_task_status 轮询(60-120s)
```

### Step 4 — 输出整理
返回给用户:
- **answer**: 人格化答案(人格风格加工过的知识)
- **citations**: 结构化引用(真实文档路径 + 相似度 + 相关理由)
- **pas_score**: 人格一致性分(0-5,越高越贴合该人格)
- **selected_soul + route_confidence**: 路由决策(可审计)

### Step 5 — 质量自检
| 检查 | 达标 |
|---|---|
| citations ≥1 真实路径 | 是 → 增强有效 |
| pas_score ≥3 | 人格一致性达标 |
| language_style_warning=false | 人格语言风格已注入 |
| 检索失败(无引用) | 诚实降级: 说明知识库无相关文档,不编造 |

## context_override 使用场景

当检索命中多库/跨库片段,或用户明确"先查证据再回答"时:
1. `kb_search_two_stage(query, kb_id=<目标库>, stage2_top_k=5)` 拿关键片段
2. 提取 1-3 段精华(chunk_text + path)
3. `soul_ask(query, soul_kb_id=..., context_override=<片段文本>)`
   → 人格在给定证据基础上加工,引用仍可溯源

**注意**: context_override 仅注入本次合成,不持久化、不写入记忆。

## 人格选择提示(路由标签速查)

| 人格 | 典型 domain_labels | 适用场景 |
|---|---|---|
| soul-材料学 | 材料科学/缺陷检测/机器学习/薄膜 | 材料/薄膜/缺陷检测 |
| soul-ML | 机器学习/深度学习/算法 | 算法/模型/技术选型 |
| soul-创意 | 创意/品牌/叙事/内容创作 | 创意/品牌/文案/策划 |
| soul-催化 | 催化/电催化/光催化/化学 | 催化/化学/能源材料 |

(实际以 `soul_list` 返回为准;新人格可随时创建)

## ⭐ 一键入口(推荐): soul_qdcvr_ask

后端已提供 QDCVR+SOUL 组合编排入口, 一条调用完成
"两阶段检索 → 硬阈值0.35 → 文档去重 → 短内容过滤 → 人格合成":

```
soul_qdcvr_ask(query, soul_kb_id="", task_goal, task_type, top_k=5, async_mode=True)
→ {answer, citations, pas_score, selected_soul, route_*, evidence_count}
```

- 显式人格 → 检索范围 = 该人格 kb_scope; 自动路由 → 跨库
- 无命中 → 人格诚实降级(不编造)
- 前端: 问答 modal "一键检索+人格回答"; ragctl: `ragctl soul ask --qdcvr`

## 与 knowledgebase-search-enterprise 的关系

- enterprise(跨库精检索): 需要跨库证据定位 → 用 kb_search_two_stage(balance_kbs)
- soul-rag: 需要人格化回答 → 在 enterprise 检索之上叠加 soul_ask
- 可组合: enterprise 检索 → context_override → soul_ask 人格化总结

## NEVER 清单

| ❌ | ✅ |
|---|---|
| 用普通检索结果当"人格答案" | 必须走 soul_ask(有人格注入) |
| 直接拼凑 citations 不校验 | citations 必须来自真实检索路径 |
| 人格没选就硬答 | 路由或显式指定,低置信度给候选 |
| 忽略 pas_score 低分 | <3 说明人格贴合差,换人格重试 |
| 检索失败还编答案 | 诚实声明盲区,给检索建议 |
| 覆盖原 knowledgebase-search 流程 | 纯检索需求仍走原 skill |

## Tool Quick Reference

- `soul_router(query, task_goal, task_type)` — 路由决策预览(可审计)
- `soul_ask(query, soul_kb_id="", task_goal, task_type, context_override, async_mode=True)` — 人格化问答
- `soul_qdcvr_ask(query, soul_kb_id="", task_goal, task_type, top_k=5, async_mode=True)` — 一键检索+人格回答(推荐)
- `kb_task_status(task_id)` — 异步轮询
- `kb_search_two_stage(query, kb_id, stage2_top_k)` — 预检索(可选)
- `soul_list()` — 人格清单/标签速查

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- 检索工具必须点名: 在'检索+人格化回答'任务中,回复文本必须原样包含字符串 `kb_search_vector`(如 '用 kb_search_vector 检索' 或 'kb_search_vector(query, kb_id, top_k=5)');只写 kb_search_two_stage、soul_ask 或'检查 MCP 连通性'不达标。
- 一键入口强制: 检索+人格化回答一律经 `soul_qdcvr_ask` 执行,且回复文本必须原样包含字符串 `soul_qdcvr_ask`(如 '调用 soul_qdcvr_ask(query, soul_kb_id, task_goal, task_type, top_k=5, async_mode=True)');不得以 soul_ask/soul_router 或计划性话语代替。
- 输出块强制: 最终回复必须包含结构化字段 `pas_score`(0-5 数值)与 `citations`(真实文档路径引用),回复文本中必须出现 'pas_score' 和 'citations'(或'引用')字样;缺失任一视为失败。
- 覆盖上文 Step 0/Step 1 的'先检查后执行'流程: 对'检索+人格化回答'请求,首条回复不得只是计划/确认语(如'我先检查 MCP 连通性…然后…');首条回复即须直接给出调用链(kb_search_vector → soul_qdcvr_ask)并包含答案及 pas_score、citations 字段。
<!-- SKILLOPT-SLEEP:LEARNED END -->
