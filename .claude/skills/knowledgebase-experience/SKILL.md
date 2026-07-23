---
name: knowledgebase-experience
description: >
  Experience full lifecycle management E0-E12. Structured practice cases
  (scenario/problem/solution/lessons). Auto-extract from KB docs
  (E0 prepare+LLM refine, E1 heuristic), quality gate (E2), draft pool (E3),
  experience-first retrieval (E4 with strict P0/P1/P2 credibility tiers),
  document linkage stale detection (E6), dashboard (E8), decay cycles (E11),
  auto health check+cleanup (E12). Triggered by: 经验, 经验库, experience,
  lesson, best practice, 实践, 案例, 故障经验, 运维经验, lesson learned,
  提取经验, 从文档提炼, 总结经验, 经验看板, 经验同步.
---

# Experience — 全生命周期管理（E0-E12）

**⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型）+ [MCP 优先原则](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则)（禁止 terminal/HTTP 绕过）

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

---

## ⭐ Pre-Flight — MCP 连通性 + 项目服务预检（强制，所有作业的第一步）

> 完整规则与边界情况见 [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md)。本预检早于本 skill 的所有编号步骤（E0-E12）。

**未通过预检，禁止开始后续步骤。**

1. **一探双检** — 调用 `mcp__kb-mcp__kb_project_status`：调用成功即证明 MCP 已连接，按 `ready` 分支（`ready==true` ⇔ backend+web 双健康）；报 "No such tool" → 走 Case C。
2. **分支处置**：
   - **Case A `ready==true`** → 就绪。
   - **Case B `ready==false`** → 先 `kb_project_preflight`（未安装则报 `problems`+`ragctl setup` 让用户处理并停止）；已安装则静默 `kb_project_start(backend=true, web=true, wait=true)`，回查 `ready==true` 才继续，否则读 `ragctl logs backend` 报错停止。
   - **Case C MCP 未连接** → 会话内无法自愈（MCP 由 Claude Code 启动加载）；`node command/ragctl.js status` 诊断并通知用户重启 Claude Code；**禁止**未连通硬跑操作（HTTP 兜底须用户明确同意）。
3. **冒烟测试** — `ready==true` 后正式操作前先做一次轻量只读往返（`experience_summary()` / `kb_catalog()`），确认 MCP↔backend 返回真实数据再作业。

---

## 思维框架：什么时候用经验？什么时候用文档？[IMPORTANT]

```
用户问了一个问题
  ├── 运维/故障/操作型（"怎么XX""报错了"）→ 经验优先！E4 检索
  ├── 理论/原理/综述型（"什么是XX"）→ 文档优先
  └── "把XX总结为经验" → experience-summarize（经验总结入库）
```

---

## 核心理念
- **文档**：全文、自由 markdown、供阅读学习
- **经验**：单点、结构化 JSON、供检索应用、动态可信度
- **联动**：文档更新 → 经验自动检测 stale → 触发重新提取

---

## E0/E1 — 自动提取（从文档挖掘经验）[IMPORTANT]

### E0 提取任务包（LLM 高质量提炼）
```
experience_extract(kb_id="<KB>", mode="prepare")
→ {documents: [{path, content}], existing_scenarios, extraction_template, hint}
```
Agent 拿到任务包后用 LLM 按 `extraction_template` 提炼（去重 `existing_scenarios`），产出高质量候选。

### E1 启发式提取（规则，无需 LLM）
```
experience_extract(kb_id="<KB>", mode="heuristic", dry_run=True)
→ {total_candidates, candidates: [{title, scenario, problem, solution, key_lessons, confidence, ...}]}
```
基于文档结构（## 段落）+ 关键词（problem/solution/lesson）启发式提取。

> [WARNING] **危险操作警告**：`dry_run=False` 会将候选直接写入草稿池。实测 heuristic 提取产出大量低质候选（章节标题被误认为 key_lessons）。**强烈不推荐**直接 dry_run=False——详见下方 E2c 推荐策略。

**提取时机**：入库新文档后（Ingest A7 通过，参见 [knowledgebase-ingest](../knowledgebase-ingest/SKILL.md) 的 A7 八项终检）；批量学习某 KB；定期丰富经验库。

## E2 — 质量门控（强制，提取+创建均适用）[IMPORTANT]

### E2a 启发式提取质量门控（E1 产出后强制执行）
```
对 E1 heuristic 产出的每个 candidate，逐项检查：
  1. key_lessons 黑名单检测：
     - 匹配章节标题模式（罗马数字 I./II. + 关键词如 INTRODUCTION/OVERVIEW/METHOD/CONCLUSION）→ ✗ 拒
     - 匹配数字编号模式（"1 Introduction"/"3.1 Method"/"4.2 Results"）→ ✗ 拒
     - 长度 < 20 chars 或 > 500 chars → ✗ 拒
     - 是"核心要点"/"总结"/"概述"等空洞词 → ✗ 拒
  2. problem/solution 质量检测：
     - problem 是原文 raw dump > 300 chars → ✗ 拒（须提炼为简洁问题陈述）
     - solution 是原文 raw dump > 500 chars → ✗ 拒
  3. tags 非空检测：tags=[ ] → ✗ 拒
  4. confidence < 0.8 → 走草稿池（不直接发布），需 LLM 精炼
```
**拒绝的候选不写入草稿池**——直接丢弃，避免污染草稿审核队列。

### E2b 手动创建质量门控
- scenario 必须有领域前缀（如 `llm-hallucination`），禁止 `test`
- solution ≥ 50 chars，含具体方法（非"修改了代码/调了参数"等泛泛）
- key_lessons 每条 ≥ 30 chars，可独立执行（非"需要调试"/"检查一下"）
- related_docs 必须指向真实文档
- tags ≥ 2 个（必须含领域词 + 场景词）
- 去重：同 KB 已有相似 scenario → 走草稿审核而非新建

### E2c 推荐提取策略
- **入库后自动提取**：用 `mode="prepare"` → LLM 精炼 → 直接发布（跳过草稿池）
- **批量扫描**：先 `mode="heuristic"` + `dry_run=True` 扫描 → 只保留 confidence≥0.8 的候选 → `mode="prepare"` 精炼
- **禁止**：heuristic + dry_run=False 直接写入草稿池（实测产生大量垃圾）

## E3 — 草稿池（候选审核）[IMPORTANT]
```
experience_drafts_list(kb_id)                      → 列出待审核草稿
experience_draft_read(kb_id, draft_id)             → 读取草稿详情（含来源文档证据）
experience_draft_approve(kb_id, draft_id, edits={}) → 批准→正式经验
experience_draft_reject(kb_id, draft_id, reason)    → 拒绝→rejected/（保留原因）
```
**审核流程**：`drafts_list` → 逐条 `draft_read` → LLM 精炼后 `draft_approve(edits=精炼字段)` 或 `draft_reject`。

## E4 — 经验优先检索（内容裁决）[IMPORTANT]

**核心原则：内容优先，宁可不给，不要错给**——无确认经验即诚实声明盲点。

### E4a 检索流程（两步走）

```
Step 1 — 经验优先（向量召回 → 内容裁决）
  experience_search_smart(query, top_k=8) — 推荐入口 (内部: 意图识别→自适应阈值→多轮降级→检索透明化)
  experience_search_global(query, top_k=8, score_threshold=0.45, verify_content=True) — 底层入口（兼容）
    → 内部: 向量召回 → 硬阈值 → 经验级去重 → 内容验证 → 可信度定级

Step 2 — 内容二次裁决（强制，不可跳过）⭐
  对 Step 1 返回的每条 P0/P1 经验，必须 experience_read(kb_id, exp_id, max_chars=2000)
  独立做 0-6 内容评分（向量分不左右决策）：

  | 维度 | 分 | 判据 |
  |------|-----|------|
  | **场景匹配** (0-2) | 2=直接对应查询场景；1=相关领域可迁移；0=无关 |
  | **方案可执行** (0-2) | 2=含具体步骤/配置/命令；1=方向性指导；0=泛泛描述 |
  | **教训可引用** (0-2) | 2=可独立引用的具体经验；1=需结合原文理解；0=空洞 |

  内容评分 < 3 → 丢弃（向量分再高也没用）
  内容评分 3-4 → P2 弱参考（标注置信度不足）
  内容评分 ≥ 5 → 纳入答案

Step 3 — 内容 ≥ 5 则直接作答（跳过文档检索）
  无 P0/P1 或内容 < 3 → 补充 kb_search_two_stage 文档检索
```

### E4b 检索结果呈现规范

```
## 经验（优先检索）
- [P0/P1/P2] <经验标题> @ <KB/exp_id>
  - 场景：<scenario>
  - 内容评分：<score>/6（场景X + 方案X + 教训X）
  - 可信度：<rating> 分 · <applied> 次应用 · <review> 次评审
  - 关联文档：<related_docs>

（仅内容 ≥ 5 的经验纳入答案正文）
（无内容 ≥ 3 的经验 → 诚实声明"无相关经验"→ 补充文档检索）
```

### E4c 检索透明化
- `vector_recall` — 向量召回总数（硬阈值前）
- `tier_counts` — {P0, P1, P2, discarded} 分级统计
- `content_ruling` — 内容裁决摘要（"召回5→读4→合格2 P0:1 P1:1 P2:2"）
- 每条经验含 `vector_score` + `content_score` + `tier` + `tier_reason`

## E4d — 智能检索增强 [IMPORTANT]

**推荐入口**: `experience_search_smart(query, top_k=8)` — 内部实现查询意图识别 + 自适应阈值（troubleshooting 0.55 / best_practice 0.45 / learning 0.35 / decision 0.50）+ 多轮降级 + 反例检测 + 透明化字段。

详细机制（意图阈值表、3 轮降级逻辑、counter-example detection、rerank 权重、与 E4a 关系）见 [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E4d。

> Agent 应优先使用 `experience_search_smart`；仅在需手动控制阈值时用 `experience_search_global`。

## E5 — 可信度分级

| 条件 | 层级 | 动作 |
|---|---|---|
| vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ review≥1 | **P0 Strong** | 直接引用，置顶 |
| vector≥0.45 ∧ content≥4 | **P1 Reference** | 采用并标注 |
| vector≥0.35 ∧ content≥3 | **P2 Weak** | 默认抑制（仅 P0/P1 不足时补）|
| 内容验证不过 OR 向量<0.35 | **DISCARD** | 永不返回 |
| disputed (review≥3 ∧ rating<2) | 降级→max P2 | 有争议降级 |
| unvetted (0 review ∧ 0 applied) | 降级→max P1 | 未评审压制 |

### 可信度修饰符

| 修饰符 | 条件 | 效果 |
|--------|------|------|
| disputed | ≥3 reviews ∧ rating<2.0 | 降级至最多 P2 |
| unvetted | 0 reviews ∧ 0 applied | 上限最多 P1 |

### 短内容虚假命中防护

向量搜索可能返回极短片段（如仅"## 问题"）并伴随虚高评分：
- Chunks < 50 chars → 降级到 P2（隐藏）
- 同一文档 >50% 片段为短内容 → 降级整篇文档
- 例外：同文档存在其他 P0/P1 片段 → 短片段放行 |

## E6 — 文档联动 / stale 检测 + 自动更新 [IMPORTANT]

```
experience_check_stale(kb_id)          → 检查 KB 经验与文档一致性（空 kb_id = 全库检查）
experience_sync_kb(kb_id)              → 整库标记 needs_sync
```

**检测逻辑**：
- 文档 mtime > 经验 updated_at → **stale**（经验过时）
- 文档不存在 → **orphan**（引用失效）

### E6a 经验更新迭代流程（stale → re-extract → update）⭐

当 `experience_check_stale` 发现 stale 经验时，按以下流程更新：

```
Step 1: experience_read(kb_id, exp_id) → 读取当前经验内容
Step 2: kb_doc_read(kb_id, related_doc_path, max_chars=5000) → 读取关联文档最新内容
Step 3: LLM 对比 文档新内容 vs 经验旧内容，判断是否需要更新：
        - 文档新增了哪些内容？
        - 旧经验的 problem/solution/key_lessons 是否依然准确？
        - 是否有新的可提取经验？
Step 4a: 经验仍准确 → experience_update(kb_id, exp_id, updated_at=now) → 刷新时间戳
Step 4b: 经验需更新 → LLM 提炼新的 problem/solution/key_lessons
          → experience_update(kb_id, exp_id, **updated_fields) → 自动重建向量索引
Step 4c: 文档已不包含原经验内容 → 标记 orphan → 按 E12 orphan 矩阵处理
Step 5: experience_sync_kb(kb_id) → 清除 stale 标记
```

**更新优先级**：
| 经验状态 | 动作 | 理由 |
|----------|------|------|
| stale + P1/P0 + applied>0 | 优先更新 | 高价值经验，确保准确 |
| stale + P2 + applied=0 | 延迟处理 | 低价值，静默标记 |
| orphan + applied>0 | 保留内容，清 related_docs | 经验仍有用 |
| orphan + applied=0 + rating=0 | 直接删除 | 零价值残留 |

**联动流程**：文档更新 → `check_stale` 发现 stale → Agent 读 related_docs 重新提取 → `update_experience` 更新 → `sync_kb` 验证。

## E7 — 搜索路径
```
故障型: experience_search_smart (推荐) → P0 直接答
  优化: experience_search_smart → experience_rerank → 最终排序
通用型: kb_search_two_stage → experience_search 补充
```

## E8 — 经验看板
```
experience_dashboard(kb_id) → {total, by_tier:{P0,P1,P2}, summary, drafts_pending, stale, orphan, needs_sync}
```

## E9-E10 — 导出/批量（规划中）

## E11 — 衰减周期
```
experience_apply_decay(kb_id) → 应用规则标记
```
| 规则 | 条件 | 效果 |
|---|---|---|
| stale_unverified | 创建>30天 ∧ 0应用 | 检索降级 |
| disputed | ≥3评审 ∧ rating<2.0 | 降到 P2 |
| unvetted | 0评审 ∧ 0应用 | 最高 P1 |

**定期跑**（如每周）保持经验新鲜度。

---

## 基础 CRUD

### Create
```
experience_create(kb_id, title, scenario, category, problem, solution, result,
                  key_lessons, tags, severity, related_docs, prerequisites, metrics)
```
**创建后自动完成**：向量索引（6 chunks）+ 元数据写入 + 磁盘文件 三路一致。

### Read / List / Update / Delete
```
experience_read(kb_id, exp_id)                                    → 含 .md 正文
experience_list(kb_id, scenario="", category="", tag="")          → 按评分排序
experience_update(kb_id, exp_id, **fields)                        → 自动重建索引
experience_delete(kb_id, exp_id)                                  → 永久删除
```

### Apply / Review（动态可信度）
```
experience_apply(kb_id, exp_id, user, context, result, notes)     → applied_count+1
experience_review(kb_id, exp_id, reviewer, rating, comment)       → 重算 rating_avg
```

### Search
| 方法 | 工具 |
|---|---|
| 智能检索（推荐入口） | `experience_search_smart(query, top_k)` |
| 全局跨库 | `experience_search_global(query, top_k)` |
| 元信息 | `experience_search(kb_id, query, top_k)` |
| 向量语义 | `experience_search_vector(kb_id, query, top_k)` |
| 按场景 | `experience_list(kb_id, scenario="...")` |
| 智能重排序 | `experience_rerank(query, experiences_json)` |
| 统计 | `experience_summary(kb_id)` / `experience_dashboard(kb_id)` |

---

## 推荐工作流

### 新文档入库 → 自动丰富经验
```
Ingest A7 通过 → experience_extract(kb_id, dry_run=True)
  → 候选≥0.8 confidence: approve 入库
  → 候选<0.8: 写草稿池，等审核
```

### 故障查询 → 经验优先答
```
experience_search_global(query) → P0 经验直接答（秒级）
  → 不够才补 kb_search_two_stage
```

### 文档更新 → 经验联动
```
文档更新 → experience_check_stale(kb_id)
  → stale 经验 → experience_extract 重新提取 → update_experience
```

### 定期维护
```
每周: experience_apply_decay(kb_id) 保持新鲜度
每月: experience_dashboard(kb_id) 评估覆盖度，补充缺口
```

## E12 — 经验自动体检与清理 [IMPORTANT]

**触发**：每次 `knowledgebase-verify` V8 步骤 / 每月定期 / 删除文档后联动。

**流程**：`experience_check_stale()`（空 kb_id=全库）→ stale/orphan 检测 → 分类处理 → 测试污染清理。

清理决策矩阵（orphan/stale/test污染/disputed 各条件对应动作）和详细检测流程见 [smart-search-and-cleanup.md](references/smart-search-and-cleanup.md) §E12。

> ⚠️ 测试污染检测必须用 `experience_list`（非 summary，后者仅返回 top 5），获取 `created_at` 做 >7d 老化判断。

---

## References

- 入库流程参考：[knowledgebase-ingest](../knowledgebase-ingest/SKILL.md) — Ingest A7 终检、文档解析提交流程
- 图谱联动参考：[knowledgebase-graph](../knowledgebase-graph/SKILL.md) — 知识图谱与经验的关联检索
- 校验流程参考：[knowledgebase-verify](../knowledgebase-verify/SKILL.md) — 全库完整性校验（触发 E12 自动体检）
- 经验增强机制设计：E0-E12 完整生命周期（extract/drafts/stale/sync/dashboard/decay），分层架构（后端数据/MCP编排/Agent LLM）

## [WARNING] NEVER 清单

| 不要这样做 | 原因 | 应该这样做 |
|-------------|------|-------------|
| 创建经验缺 problem/solution/lessons | 检索命中也没用 | 三者必须非空且具体 |
| 跳过 E2 质量门控 | 低质经验污染库 | scenario/related_docs 必须验证 |
| 维护时不跑 stale 检测 | 过时经验误导决策 | `check_stale` 至少每月一次 |
| 不变动时狂跑 `apply_decay` | 没必要 | 每周一次足够 |
| 把"经验"当文档写（长文/大段落） | 经验是单点结构化 | 一个问题→一个方案→一个教训 |
| 故障查询不先查经验 | 错失秒级答案 | 故障型：`experience_search_smart` 优先，`experience_search_global` 兜底，文档补充 |
| 直接调 experience_search_global 做故障查询 | 丢失智能意图识别+多轮降级 | 用 `experience_search_smart` 作为推荐入口，`_global` 仅在手动控制时使用 |