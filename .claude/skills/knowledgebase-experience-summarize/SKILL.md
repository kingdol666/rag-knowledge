---
name: knowledgebase-experience-summarize
description: >
  Experience authoring, meditation (auto-induction), cross-KB synthesis, and
  experience CRUD + migration. Full lifecycle: CREATE / UPDATE / DELETE /
  MIGRATE experiences, and MEDITATION (OpenClaw-style auto-induction from
  recurring user questions + KB answers). Routes write operations to the
  Archival agent. Quality-gated (specific, actionable, independently citable).
  Follows KB architecture: experience.md ↔ .experience-index.yml ↔ ChromaDB
  vector index. Do NOT trigger for read-only experience queries (use
  knowledgebase-experience E4 search instead). Triggered by: 记录经验,
  总结经验, 提炼成经验, 保存教训, 记住流程, 创建经验, 更新经验, 删除经验,
  经验跟随, 经验迁移, 冥想, 整理记忆, 归纳经验, 反思, meditation, reflect,
  save as experience, summarize as lesson, record workflow, create experience,
  update experience, delete experience.
---

# Experience Summarize — 经验总结·冥想·CRUD·迁移

**⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型）+ [MCP 优先原则](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则)（禁止 terminal/HTTP 绕过）

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

---

## ⭐ Pre-Flight（强制，所有作业第一步）

**未通过预检禁止作业。** 执行 [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) 的完整流程（一探双检 `kb_project_status` → 分支处置 → 冒烟测试）。
---

## 模式路由（Step 0：识别用户意图）

```
用户意图命中哪个模式？

① MEDITATION  — "冥想""整理记忆""归纳经验""reflect""定期总结"
② CREATE      — "记录经验""总结一下""提炼成经验""保存教训""记住流程"
③ UPDATE      — "更新经验""修改经验""补充教训"
④ DELETE      — "删除经验""清掉经验"
⑤ MIGRATE     — "经验跟随""经验迁移"（文档/KB移动后联动）
⑥ CROSS-KB    — 跨库综合（涉及多KB的经验归纳）

不确定？按最接近的 CREATE 处理，向用户确认。
```

跳转到对应模式。所有写入走 MCP 工具（experience_create/update/delete），禁止终端/HTTP 绕行。

**reference 加载指南**（避免加载不需要的文件浪费上下文）：
| 模式 | 必读 reference | 不需要加载 |
|------|--------------|-----------|
| MEDITATION | meditation.md, quality-standards.md | crud-and-migration.md, cross-kb-synthesis.md |
| CREATE | quality-standards.md | meditation.md（仅手动总结不需要采集脚本）|
| UPDATE / DELETE | crud-and-migration.md | meditation.md, cross-kb-synthesis.md |
| MIGRATE | crud-and-migration.md | meditation.md, quality-standards.md |
| CROSS-KB | cross-kb-synthesis.md, quality-standards.md | meditation.md |

---

## 模式①：MEDITATION — 冥想记忆（OpenClaw 式自动归纳）

> 定期从高频问题 + KB 回答自动归纳经验。详见 [references/meditation.md](references/meditation.md)。

### 四阶段流程

**阶段1 — 采集问题源**

优先用当前会话上下文（最精准），辅助用历史聊天库：

```bash
# 历史聊天库采集（只读，永不写入）
python scripts/meditation_source.py --days 7 --top 30
# JSON 模式（供解析）：
python scripts/meditation_source.py --json --days 14
```

脚本读 `storage/claude-chat.db` → 清洗噪声 → 聚类高频问题 → 输出 JSON。同时回顾当前会话的 KB 问答。

**阶段2 — KB 相关性确认 + 答案检索**

```
对每个候选问题簇：
  1. kb_catalog() 匹配 → 非 KB 问题丢弃
  2. experience_search_smart(query) → 已有 P0/P1 覆盖则跳过
  3. kb_search_two_stage(query, kb_id) → 提取 related_docs + 答案基础
```

**阶段3 — LLM 归纳 + 质量门控**

按 [references/quality-standards.md](references/quality-standards.md) 黄金标准提炼。任一字段不达标 → 丢弃（宁缺毋滥）。归纳信号阈值：至少 1 强信号或 2 中信号（见 meditation.md §信号判定）。

**阶段4 — 入库 + 报告**

新建或更新（已有相似走 update），输出冥想报告。

---

## 模式②：CREATE — 手动总结入库（核心流程）

> 从对话/文档/实践提炼结构化经验。质量标准详见 [references/quality-standards.md](references/quality-standards.md)。

### Step 1 — 识别场景 + 目标 KB

从对话提取：发生了什么？做了什么？学到了什么？识别操作上下文。

`kb_list()` 遍历确定 `target_kb_id`：场景属于哪个 KB 的领域？找不到精确匹配选最接近的父 KB，tags 标领域。

### Step 2 — 起草经验（质量是关键）

**黄金标准**：problem = 可复现场景；solution = 可执行步骤；key_lessons = 可独立引用。
具体达标标准、坏/好示例、完整性检查清单见 [references/quality-standards.md](references/quality-standards.md)。

```yaml
kb_id:       "<target KB ID or path>"
title:       "含场景词+方法词"
scenario:    "kebab-case-含领域前缀"
category:    "troubleshooting|best_practice|workflow|optimization|lesson_learned|decision|tip"
problem:     "具体可复现场景（≥50 chars）"
solution:    "可执行步骤/方法（≥100 chars）"
result:      "success|partial|failed|inconclusive"
key_lessons: ["可独立引用的教训1（≥30 chars）", "教训2", "教训3"]
tags:        ["领域词", "方法词", "场景词"]
severity:    "critical|important|normal|tip"
related_docs: ["KB/doc.md"]   # kb_doc_read 验证存在
```

### Step 3 — 用户确认

呈现草稿："确认入库？可修改。" 用户确认或编辑后进入 Step 4。

### Step 4 — 持久化

```python
result = mcp__kb-mcp__experience_create(
    kb_id, title, scenario, category, problem, solution, result,
    key_lessons, tags, severity, related_docs
)
exp_id = result["experience"]["id"]  # 自动三层一致+向量索引
```

### Step 5 — 验证

`experience_read(kb_id, exp_id)` 确认字段正确 + `vector_index.total_chunks ≥ 1`。报告 exp_id。

---

## 模式③：UPDATE — 更新经验

> 详见 [references/crud-and-migration.md](references/crud-and-migration.md) §更新。

```
定位：experience_search_smart(query) 或 experience_list(kb_id, scenario=...)
读取：experience_read(kb_id, exp_id) → 当前内容
更新：experience_update(kb_id, exp_id, **需改字段)  # 只传需更新的，向量自动重索引
验证：experience_read 确认 + vector_index.indexed_at 刷新
```

更新场景：冥想补充教训、文档更新经验过时（E6 stale）、修复 related_docs 链接。

---

## 模式④：DELETE — 删除经验

> 详见 [references/crud-and-migration.md](references/crud-and-migration.md) §删除。

```
读取确认：experience_read(kb_id, exp_id) → 确认非误删
删除：experience_delete(kb_id, exp_id)  # 不可逆
验证：experience_list(kb_id) 数量减1
```

删除决策：测试污染/孤儿零价值 → 删；有应用记录 → 先评估归档 `status="archived"`。

---

## 模式⑤：MIGRATE — 经验跟随文档/KB 移动

> `kb_doc_move` 不会自动迁移经验。详见 [references/crud-and-migration.md](references/crud-and-migration.md) §跟随移动。

**文档移动后强制执行**：

```
1. experience_list(source_kb) → 筛 related_docs 含移动文档的经验
2. 对每条受影响经验：
   - 强绑定文档 → 经验迁移到 target_kb（read→create→delete→verify）
   - 文档仅参考 → 更新 related_docs 路径（旧→新）
3. 验证所有 related_docs 指向真实存在的文档
```

KB 重命名/移动：经验目录自动跟随，但需 `kb_reindex(force=true)` 重建向量 + 修复跨库引用路径。

---

## 模式⑥：CROSS-KB — 跨库综合

> 经验横跨多 KB 时的归属/去重/关联。详见 [references/cross-kb-synthesis.md](references/cross-kb-synthesis.md)。

归属决策：显式归属 > related_docs 多数归属 > 核心领域 > 通用 KB。
跨库去重：`experience_search_global` 先查，避免重复；纯重复用"指针经验"轻量引用。

---

## ⚠️ NEVER 清单

| ❌ 不要 | 原因 | ✅ 应该 |
|--------|------|---------|
| 创建缺 problem/solution/lessons 的空经验 | 检索命中也没用 | 回退起草，过质量门控 |
| 跳过质量标准（因为是自动/冥想） | 冥想≠批量产垃圾 | 同样过完整检查清单 |
| 跳过用户确认直接入库（CREATE 模式） | 用户可能有修改 | Step 3→4 |
| related_docs 写不存在路径 | 404 断链 | `kb_doc_read` 验证 |
| scenario 不带领域前缀 | 全局冲突搜不到 | 如 `vla-deployment-sim2real` |
| 文档移动后不修复经验链接 | 经验变孤儿 | MIGRATE 模式强制执行 |
| 降低质量标准只为多产 | 低质膨胀 | 宁缺毋滥 |
| 把对话原文当经验 | 无法复用 | 提炼成结构化抽象规律 |
| 采集脚本写入任何数据 | 脚本只读 | 入库只走 MCP 工具 |
| MEDITATION 产出不报告 | 用户不知情 | 阶段4 输出报告 |
| 用 summary 的 avg_rating 判断库质量 | 未评审经验算0.0拉低均值，误导 | 看 `reviewed_count` + `unrated_count` 字段区分 |
| 信任采集脚本的原始输出不经KB验证 | 聊天库含系统输出伪装为user | 每个候选经 `kb_catalog` 匹配 + 向量搜索验证 |
