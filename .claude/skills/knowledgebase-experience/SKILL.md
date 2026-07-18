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

**[IMPORTANT] MCP 优先原则（强制）**：所有 kb-mcp 操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`）。禁止用 `curl`/`python -c`/`wget` 等终端命令或直调 HTTP API。MCP 不可用时才可向用户报告。

**执行者：此技能由 Archival agent 执行**
- 当 knowledgebase 调度器检测到对应场景后 → 路由到本 skill
- 本 skill **必须**委托 Archival agent（`Agent(subagent_type="archival", ...)`）执行

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

**提取时机**：入库新文档后（Ingest A7 通过，参见 [knowledgebase-ingest](knowledgebase-ingest) 的 A7 八项终检）；批量学习某 KB；定期丰富经验库。

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

## E4 — 经验优先检索（QDCVR 流程）[IMPORTANT]

**核心原则：宁可不给，不要错给**——无确认经验即诚实声明盲点。

```
# Step 1: 经验优先
experience_search_global(query, top_k=10, score_threshold=0.45, verify_content=True)
  → 内部: 向量召回 → 硬阈值 → 经验级去重 → 内容验证 → 可信度定级
  → 返回 P0/P1/P2 分级经验，含 vector_score/content_score/tier_reason
  → count=0 表示"召回N条但内容验证不过"——诚实声明无相关经验

# Step 2: 经验不足才补文档
if P0+P1 < 2: kb_search_two_stage(query, balance_kbs=True)
```

### E4 检索流程透明化
返回值含完整检索质量元信息，Agent 应据此决策：
- `vector_recall` — 向量召回总数（硬阈值前）
- `tier_counts` — {P0, P1, P2, discarded} 分级统计
- `message` — 检索路径摘要（如 "召回5→验证通过2→返回2 P0:1 P1:1"）
- 每条经验含 `vector_score` + `content_score` + `tier` + `tier_reason`

## E5 — 可信度分级
| 条件 | 层级 | 动作 |
|---|---|---|
| vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ review≥1 | **P0 Strong** | 直接引用，置顶 |
| vector≥0.45 ∧ content≥4 | **P1 Reference** | 采用并标注 |
| vector≥0.35 ∧ content≥3 | **P2 Weak** | 默认抑制（仅 P0/P1 不足时补）|
| 内容验证不过 OR 向量<0.35 | **DISCARD** | 永不返回 |
| disputed (review≥3 ∧ rating<2) | 降级→max P2 | 有争议降级 |
| unvetted (0 review ∧ 0 applied) | 降级→max P1 | 未评审压制 |

## E6 — 文档联动 / stale 检测 [IMPORTANT]
```
experience_check_stale(kb_id)          → 检查 KB 经验与文档一致性
experience_check_stale_global()        → 全库检查
experience_sync_kb(kb_id)              → 整库标记 needs_sync
```
**检测逻辑**：
- 文档 mtime > 经验 updated_at → **stale**（经验过时）
- 文档不存在 → **orphan**（引用失效）

**联动流程**：文档更新 → `check_stale` 发现 stale → `sync_kb` 标记 → Agent 读 related_docs 重新提取 → `update_experience` 更新。

## E7 — 搜索路径
```
故障型: experience_search_global + experience_search_vector → P0 直接答
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
| 全局跨库 | `experience_search_global(query, top_k)` |
| 元信息 | `experience_search(kb_id, query, top_k)` |
| 向量语义 | `experience_search_vector(kb_id, query, top_k)` |
| 按场景 | `experience_list(kb_id, scenario="...")` |
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

## E12 — 经验自动体检与清理（[IMPORTANT] Phase 1 新增）

### 触发时机
- 每次 `knowledgebase-verify` V8 步骤触发
- 每月定期维护
- 删除文档后自动联动

### 自动检测流程
```
# Step 1: 全库 stale/orphan 检测
experience_check_stale_global()
  → stale=0, orphan=0 → 健康
  → stale>0 → Step 2
  → orphan>0 → Step 3

# Step 2: 处理 stale 经验
for each stale_exp:
    experience_sync_kb(kb_id)
    # 重新从关联文档提取（如文档仍存在）
    # 无法恢复 → 标记 needs_cleanup

# Step 3: 处理 orphan 经验
for each orphan_exp:
    read_detail = experience_read(kb_id, exp_id)
    if applied_count == 0 and rating == 0:
        # 无人使用的 orphan → 直接删除
        experience_delete(kb_id, exp_id)
    elif applied_count > 0:
        # 有价值但关联断开 → 更新 related_docs
        experience_update(kb_id, exp_id, related_docs=[])
    # 否则保留并标注 needs_sync

# Step 4: 测试污染检测
for each kb with experiences:
    exp_list = experience_list(kb_id)   # ⚠️ 使用 list 而非 summary——summary 仅返回 top 5
    for exp in exp_list where rating==0 and applied==0:
        detail = experience_read(kb_id, exp.id)  # 获取 created_at 用于老化检查
        age_days = (now - detail.created_at).days
        if age_days > 7:
            experience_delete(kb_id, exp.id)
```

### 清理决策矩阵

| 条件 | 动作 |
|------|------|
| orphan + applied=0 + rating=0 | 直接删除 |
| orphan + applied>0 | 清空 `related_docs`，保留经验内容 |
| stale + 文档仍存在 | `experience_sync_kb` → 重新提取 |
| stale + 文档已删除 | → 转为 orphan，按上表处理 |
| test 污染 (rating=0, applied=0, age>7d) | 直接删除 |
| disputed (review≥3, rating<2) | 标记降级，建议人工审查 |

---

## References

- 入库流程参考：[knowledgebase-ingest](knowledgebase-ingest) — Ingest A7 终检、文档解析提交流程
- 图谱联动参考：[knowledgebase-graph](knowledgebase-graph) — 知识图谱与经验的关联检索
- 校验流程参考：[knowledgebase-verify](knowledgebase-verify) — 全库完整性校验（触发 E12 自动体检）
- MEMORY.md: 参见项目 memory 目录下的 experience-enhancement-implemented 记录
- CLAUDE.md: 经验可信度阈值定义（P0/P1/P2 分级标准）

## [WARNING] NEVER 清单

| 不要这样做 | 原因 | 应该这样做 |
|-------------|------|-------------|
| 创建经验缺 problem/solution/lessons | 检索命中也没用 | 三者必须非空且具体 |
| 跳过 E2 质量门控 | 低质经验污染库 | scenario/related_docs 必须验证 |
| 维护时不跑 stale 检测 | 过时经验误导决策 | `check_stale` 至少每月一次 |
| 不变动时狂跑 `apply_decay` | 没必要 | 每周一次足够 |
| 把"经验"当文档写（长文/大段落） | 经验是单点结构化 | 一个问题→一个方案→一个教训 |
| 故障查询不先查经验 | 错失秒级答案 | 故障型：经验优先，文档补充 |