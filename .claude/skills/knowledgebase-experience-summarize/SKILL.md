---
name: knowledgebase-experience-summarize
description: >
  经验总结入库 — 将用户的实践、流程或经验教训自动提炼为结构化经验并存入知识
  库。识别场景 → 智能总结 → 用户确认 → experience_create 持久化 → 验证。
  确保经验完整（问题/方案/教训/标签/指标/关联文档）且人机皆可读。Triggered
  by: "记录这个经验", "总结一下", "保存教训", "记住流程", "提炼成经验",
  "把...做成经验", "帮我记录一下", "save this as experience", "summarize as
  lesson", "record this workflow", and any phrase expressing intent to persist
  a process/lesson/experience as structured knowledge. Do NOT trigger for
  read-only experience queries ("查经验"/"有没有这方面的经验") — those route
  to knowledgebase-experience instead.
---

# Experience Summarize — 经验总结入库

## 边界（避免误触发）

- 用户要**记录/总结/保存**经验 → 本 skill（S1→S5 创建流程）
- 用户要**查询/检索/应用/评审**已有经验 → `knowledgebase-experience`（E2/E3/E4）
- 模糊时优先判断："写"类动词 → 本 skill；"读"类动词 → knowledgebase-experience

## 核心流程：S1→S5

```
S1 场景诊断  →  判断信息来源（对话/文档/手工输入）
S2 智能提炼  →  LLM 提取结构化字段
S3 模板呈现  →  生成人机可读的 markdown 经验草稿
S4 用户确认  →  展示草稿 → 用户确认/修改 → 最终定稿
S5 持久化    →  experience_create → experience_read 验证
```

---

## S1 — 场景诊断

先判断经验来源类型，决定提炼策略：

**来源类型 A — 对话复盘：** 用户刚描述了一次处理故障/完成操作的经历。
  → 从对话历史中提取关键信息（问题/方案/结果/教训）。

**来源类型 B — 文档提炼：** 用户给出一个文档路径或内容。
  → `kb_doc_read()` 读取文档 → 从中提取可复用的实践经验。

**来源类型 C — 手工输入：** 用户直接说了要记录什么。
  → 按结构化模板逐项引导用户补充。

**来源类型 D — 经验复制/迁移：** 用户说"把 XX KB 的某个经验搬到 YY KB"。
  → `experience_read()` 读取原经验 → 在目标 KB 重建。

**判断后，确认目标 KB：**

1. 如果用户指定了 KB → 直接用
2. 如果未指定 →
   ```
   kb_catalog()  →  列出所有 KB 的 description
   Agent 根据经验的领域判断 → 选择最匹配的 KB
   → 向用户确认："这个经验存入「Thermal-Power-Monitoring」知识库，可以吗？"
   ```

---

## S2 — 智能提炼

根据来源类型，用 LLM 提取以下字段。**每个字段都要有依据，不能凭空编造。**

### 核心字段

| 字段 | 要求 | 示例 |
|------|------|------|
| **title** | 简明概括，<30字，一看就知道解决什么问题 | `磨煤机振动值突升排查经验` |
| **problem** | 具体场景：什么设备/系统 + 什么异常 + 影响 | `#3机组中速磨煤机振动值由2.5mm/s突升至6.8mm/s...` |
| **solution** | 可操作的步骤，按顺序编号 | `(1)调取DCS检查煤质 (2)...` |
| **result** | 最终效果：成功/部分成功/失败 | `成功，提前2小时预警，避免非计划停机` |
| **key_lessons** | 每条是**可独立执行**的操作条目，3-5条 | `["振动值<3mm/s继续监控","3-5mm/s降负荷观察"]` |
| **tags** | 3-6个标签，覆盖设备/方法/场景 | `["磨煤机","振动","故障排查","火电厂"]` |

### 元数据字段

| 字段 | 选项/规则 |
|------|----------|
| **category** | `troubleshooting`（故障排查）\| `best_practice`（最佳实践）\| `lesson_learned`（经验教训）\| `optimization`（优化）\| `workflow`（工作流）\| `tip`（小技巧）\| `decision`（决策记录）|
| **severity** | `critical`（紧急）\| `important`（重要）\| `normal`（普通）\| `tip`（提示）|
| **scenario** | kebab-case 场景标识，用于精确匹配检索，如 `coal-mill-vibration-diagnosis` |

### 量化指标字段（metrics）

**关键设计理念：** metrics 不设固定 schema。每一个经验可以定义自己最关键的量化指标，有多少写多少。系统不限定字段名。

提炼原则：
- **有数据的写数据**：论文有准确率写准确率，运维有提前时长写提前时长
- **没数据的写定性描述**：没精确数字就写 "显著降低""明显改善"
- **宁缺毋滥**：确实没有量化指标的字段就不写

常见指标示例：
```json
{"lead_time_hours": 2, "accuracy_pct": 94.5}
{"cost_saved": 500000, "unit": "元/年"}
{"diagnosis_time_min": 90, "success_rate": "100%"}
```

### 关联文档（related_docs）

自动尝试关联：

1. 如果来源是文档（B类）→ 自动填入文档路径
2. 如果来源是对话（A类）→ 扫描对话中提到的文档名 → `kb_search()` 查找匹配 → 建议关联
3. 用户可手动增删

### 前置条件（prerequisites）

列出复现/应用此经验需要的前提条件：
- 特定设备型号、软件版本
- 需要的数据/工具/权限
- 环境要求

无特殊前置条件就留空。

---

## S3 — 模板呈现

将提炼结果展示给用户。**格式必须同时满足：**

### 对人可读（markdown 渲染美观）

```
## 📋 经验草稿：{title}

**目标知识库：** `{kb_name}`（{kb_id}）

---

### 问题
{problem}

### 方案
{solution}

### 结果
{result}

### 关键教训
1. {key_lessons[0]}
2. {key_lessons[1]}
3. {key_lessons[2]}

### 量化指标
- 指标1：{值}
- 指标2：{值}

### 标签
`#{tag1}` `#{tag2}` `#{tag3}`

---

**类别：** {category} | **严重程度：** {severity}
**场景标识：** `{scenario}`
**关联文档：** {related_docs}
**前置条件：** {prerequisites}

---

> 请确认以上内容是否准确完整。可以说"确认"来保存，
> 或提出修改意见（"标题改一下""加一条教训"等）。
```

### 对 Agent 可读（字段清晰、结构化）

模板中的每个字段直接对应 `experience_create` 的参数，Agent 可以一眼看出每个字段的值并直接调用来创建。

---

## S4 — 用户确认

**原则：不在未经用户确认的情况下调用 `experience_create`。**

展示草稿后等待用户反馈：

- **"确认"/"可以"/"保存"** → 进入 S5 持久化
- **修改意见** → 按反馈更新对应字段 → 重新展示 → 再确认
- **"算了"/"先不存"** → 终止，不写入

---

## S5 — 持久化

用户确认后：

```
1. 调用 experience_create(
     kb_id=目标KB的ID/UUID,
     title=title,
     scenario=scenario,
     category=category,
     problem=problem,
     solution=solution,
     result=result,
     key_lessons=key_lessons,
     tags=tags,
     severity=severity,
     related_docs=related_docs,
     prerequisites=prerequisites,
     metrics=json.dumps(metrics)  # JSON字符串
   )

2. 验证：experience_read(exp_id=返回的exp_id)
   → 读取确认内容完整

3. 报告给用户：
   ✅ 经验已保存至「{kb_name}」
   经验 ID：{exp_id}
   可通过「查询经验」或在检索中按场景「{scenario}」找到
```

---

## 质量守则

1. **宁缺毋滥：** 每条 key_lesson 必须独立可执行。如果没有可提取的教训，宁可不写也不要凑数。
2. **不编造字段：** problem/solution/result 必须来自用户或原文，不能自己演绎。
3. **不编造指标：** metrics 中的数字必须有来源（用户说的/文档里的），不能凭感觉写。
4. **场景标识要精确：** scenario 用 kebab-case，避免泛化（用 `coal-mill-vibration-diagnosis` 而不是 `fault-diagnosis`）。
5. **确认是硬门槛：** 未经用户确认绝不写入。
6. **写入后必验证：** 必须 `experience_read` 确认写入成功。

## 与 knowledgebase-experience 的关系

| 操作 | 职责 skill |
|------|-----------|
| 记录经验 | **knowledgebase-experience-summarize**（本 skill）— 总结提炼→确认→写入 |
| 检索经验 | `knowledgebase-experience`（E2） |
| 应用经验 | `knowledgebase-experience`（E3） |
| 评审经验 | `knowledgebase-experience`（E4） |
| 经验统计 | `knowledgebase-experience`（E5） |
