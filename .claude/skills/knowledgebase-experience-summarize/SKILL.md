---
name: knowledgebase-experience-summarize
description: Experience summarization and persistence. Distill user practices, processes, or lessons into structured experiences. 5-step flow: identify scenario+target KB → draft with quality golden standard (specific, actionable, independently citable) → user confirmation → experience_create persistence → verify. Ensures completeness (problem/solution/lessons/tags/related_docs). Do NOT trigger for read-only experience queries. Triggered by: 记录这个经验, 总结一下, 保存教训, 记住流程, 提炼成经验, save as experience, summarize as lesson, record workflow.
---

# Experience Summarize — 经验总结入库

**⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型）+ [MCP 优先原则](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则)（禁止 terminal/HTTP 绕过）

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

---

## ⭐ Pre-Flight — MCP 连通性 + 项目服务预检（强制，所有作业的第一步）

> 完整规则与边界情况见 [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md)。本预检早于本 skill 的所有编号步骤（Step 1-5）。

**未通过预检，禁止开始后续步骤。**

1. **一探双检** — 调用 `mcp__kb-mcp__kb_project_status`：调用成功即证明 MCP 已连接，按 `ready` 分支（`ready==true` ⇔ backend+web 双健康）；报 "No such tool" → 走 Case C。
2. **分支处置**：
   - **Case A `ready==true`** → 就绪。
   - **Case B `ready==false`** → 先 `kb_project_preflight`（未安装则报 `problems`+`ragctl setup` 让用户处理并停止）；已安装则静默 `kb_project_start(backend=true, web=true, wait=true)`，回查 `ready==true` 才继续，否则读 `ragctl logs backend` 报错停止。
   - **Case C MCP 未连接** → 会话内无法自愈（MCP 由 Claude Code 启动加载）；`node command/ragctl.js status` 诊断并通知用户重启 Claude Code；**禁止**未连通硬跑操作（HTTP 兜底须用户明确同意）。
3. **冒烟测试** — `ready==true` 后正式操作前先做一次轻量只读往返（`kb_catalog()` / `experience_summary()`），确认 MCP↔backend 返回真实数据再作业。

---

## 思维框架：写经验前问自己三道题 ⭐

> 经验不是"把对话记下来"——经验是**可复用的实践精华**，从具体案例中提炼抽象规律。

写每一段经验前，问自己：

1. **这解决了什么真问题？** — 别人遇到同样场景时，能否马上定位到这条经验？
2. **可操作性能打几分？** — 读完方案，别人能不能直接照着做？还是只说"要小心"？
3. **少了什么？** — `problem` / `solution` / `key_lessons` 缺一个都不行，`related_docs` 缺了等于断链。

---

## Step 1 — 识别场景 + 目标 KB

从对话提取：发生了什么？做了什么？学到了什么？识别操作上下文（设备/系统/领域）。

通过 `mcp__kb-mcp__kb_list()` 遍历所有 KB，确定 `target_kb_id`：

```
场景属于哪个 KB 的领域？(如故障→设备KB、流程→工艺KB、经验→General-KB)
找不到精确匹配时，选最接近的父KB，在 tags 中标明领域
```

---

## Step 2 — 起草经验 ⭐（质量是关键）

### 质量黄金标准

```
问题描述 → 必须是"可复现的场景"，不能是"当天发生了啥"
解决方案 → 必须是"可执行步骤"，不能是"我们修好了"
关键教训 → 必须可独立引用，不能是"注意安全"式空话
```

### ❌ 坏经验示例（太泛）
```
问题: "设备不太好用"
方案: "我们检查了一下，调整了参数"
教训: ["要注意维护"]
```
→ 别人看了等于没看，无法复用。

### ✅ 好经验示例（具体、可操作）
```
问题: "磨煤机堵管导致停炉，每次清堵耗时3小时"
方案: "搭建CNN-LSTM预警模型，基于DCS历史数据训练，提前315分钟预警堵管"
教训: ["特征工程选磨煤机电流+进出口差压+一次风量三参数",
       "预警阈值设80%时精度95%误报率3%，低于70%则误报激增"]
```
→ 别人遇到同样场景能直接套用。

### Draft 结构

```yaml
kb_id:       "<target KB ID or path>"
title:       "VLA 三阶段训练步骤"   # 简短、含方法词/场景词
scenario:    "vla-training-steps"    # kebab-case，可搜索
category:    "workflow"              # best_practice|troubleshooting|lesson_learned|optimization|tip|workflow|decision
problem:     "什么问题/什么场景需要这个经验"
solution:    "具体可执行的步骤/方法（≥100 chars）"
result:      "success"               # success|partial|failed|inconclusive
key_lessons: ["可独立引用的教训1（≥30 chars）", "教训2"]
tags:        ["领域词", "方法词", "设备词"]
severity:    "normal"                # critical|important|normal|tip
related_docs: ["KB/doc.md"]          # 真实存在的文档路径
```

### 完整性检查清单（Step 2 通过条件）

| 字段 | 达标标准 | ❌ 不达标则 |
|------|---------|-----------|
| `title` | 含场景词+方法词（如"磨煤机堵管预警"） | 不回退 Step 1，补场景词 |
| `problem` | 具体到时间/数量/条件（≥50 chars） | 补充细节 |
| `solution` | 有工具/方法/步骤引用号（≥100 chars） | 重写 |
| `key_lessons` | 每条独立可引用（≥30 chars），≥3条 | 从 solution 拆解 |
| `related_docs` | 路径在 KB 真实存在 | 用 `mcp__kb-mcp__kb_doc_read` 验证或调整 |
| `scenario` | kebab-case，含领域前缀 | 重命名 |

---

### 起草技巧

- **从已有搜索中提取**：用户之前搜了大量资料？从 top 命中里提取 `related_docs` 和 `key_lessons`
- **从对话中提取**：用户说了"我上次做X时，Y出了问题，后来用Z修好了" → 这就是 raw experience
- **从文档中总结**：文档里的"## 经验"或"## Lessons Learned"章节直接结构化
- **多个教训时分类组同类**：3-5条就够了，过多稀释可操作性

---

## Step 3 — 用户确认

呈现草稿。问："确认入库？可修改。" 用户确认或编辑后进入 Step 4。

---

## Step 4 — 持久化

调用 `mcp__kb-mcp__experience_create`：

```python
result = mcp__kb-mcp__experience_create(
    kb_id, title, scenario, category,
    problem, solution, result,
    key_lessons, tags, severity, related_docs
)
exp_id = result.experience.id
```

## Step 5 — 验证

调用 `mcp__kb-mcp__experience_read(kb_id, exp_id)` — 确认所有字段正确存储。向用户报告 `exp_id`。

示例输出：
```
✅ 经验已创建并自动向量索引
   ID: exp-xxxxxxxxxxxx
   标题: VLA模型三阶段训练范式经验
   场景: vla-training-steps
   教训: 5条可独立引用
   索引: Embodied-AI/experience/exp-xxx.md (6 chunks)
```

---

## ⚠️ NEVER 清单（反模式）

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 创建空经验（缺 problem/solution/lessons） | 检索命中也没用 | 缺字段就回退 Step 2 |
| 跳过用户确认直接入库 | 用户可能有修改意见 | 必须 Step 3 → 4 |
| `related_docs` 写不存在路径 | 引发 404 | 用 `mcp__kb-mcp__kb_doc_read` 验证再写 |
| `scenario` 不带领域前缀 | 全局冲突，搜不到 | 如 `vla-deployment-sim2real` |
| 只写2条lessons | 不够可操作 | 最少3条，从不同角度 |
| 把对话原文当经验 | 无人称/无边界的场景描述无法复用 | 总结成结构化、抽象化的可复用知识 |
| `key_lessons` 写"注意安全"式空话 | 无法操作 | 写"安全检查清单：先A后B最后C" |
| 类型写成 "tip" 但内容是故障排查 | 误导检索分类 | 选最匹配的 category |