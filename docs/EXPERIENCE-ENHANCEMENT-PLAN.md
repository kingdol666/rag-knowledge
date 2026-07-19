# Experience Enhancement Plan — 经验系统全面增强

**日期:** 2026-07-19 | **版本:** 2.0 (新增 Phase 0 检索增强)

---

## Phase 0: 智能经验检索增强 (Intelligent Retrieval) 🔴 最高优先级

> **核心原则:** 宁可不给，不要乱给。检索第一关必须严。

### 0.1 当前检索机制的脆弱点

对 `experience_service.py:search_experiences_global()` 的逐行审计：

| 环节 | 当前实现 | 脆弱点 |
|------|---------|--------|
| **Query理解** | 无 — 查询直接送入向量搜索 | "电池太热了怎么办" 与 "battery thermal management" 无法语义连接 |
| **召回路径** | 2 路径: 向量(per-KB 遍历) + 关键词(token 匹配) | 无 scenario 精确匹配、无 tag 路径、无图谱扩展 |
| **去重** | 经验级去重 (同 exp_path 取最高分) | 无法识别语义去重 ("电池过热" 和 "BTMS故障" 可能是同一场景) |
| **内容验证** | `_content_verify()` — token 覆盖率打分 0-8 | **纯 token 匹配**，无法理解语义。"thermal management in data center" 和 "battery thermal management" 都会因 "thermal management" 获得高分 |
| **阈值** | 单一硬阈值 0.45 | 故障排查和知识学习用同一个阈值，前者应更严 |
| **排序** | 向量分排序 | 无重排序、无多样性、无新鲜度加权 |
| **多轮** | 单次检索 | 0 结果 → 直接放弃，不尝试扩展查询 |
| **解释性** | 返回 tier + vector_score + content_score | 无 "为什么排第一" 的解释 |

### 0.2 增强方案

#### 0.2a Query 理解层 (Query Understanding Layer)

**新增方法:** `_understand_query(query) → QueryIntent`

```python
@dataclass
class QueryIntent:
    original: str              # 原始查询
    type: str                  # troubleshooting | learning | best_practice | decision
    domain_tokens: list[str]   # 领域词: ["电池", "热管理", "相变材料"]
    problem_tokens: list[str]  # 问题词: ["过热", "失效", "温度不均"]
    action_tokens: list[str]   # 操作词: ["怎么修", "如何处理", "排查"]
    expanded_queries: list[str] # 扩展查询: ["battery thermal management", "BTMS failure"]
    scenarios: list[str]       # 候选 scenario 名: ["btms-overheat", "battery-cooling-failure"]
    severity_hint: str         # critical | normal | reference
```

**实现策略:**
- Agent 层实现（不侵入后端，保持轻量）
- 在 `kb-mcp/server.py` 的 `experience_search_global` MCP 工具中添加预处理
- 调用 LLM 做 query 分析和扩展（单次调用，`temperature=0`）

#### 0.2b 多路径召回 (Multi-Path Recall)

从当前 2 路径扩展到 **5 路径并行召回**:

```
Path A: 向量语义召回 (现有) — 捕获语义相似但用词不同的经验
Path B: 关键词元信息召回 (现有增强) — 在 title/problem/solution/scenario/tags/lessons 中
Path C: Scenario 精确匹配 (新增) — 查询 scenario 候选列表，精确匹配 experience.scenario 字段
Path D: Tag 路径召回 (新增) — 从 query 提取的 domain_tokens 匹配 experience.tags
Path E: 质量反馈召回 (新增) — applied_count≥2 ∧ rating≥4 的经验加分
```

**新增 MCP 工具:**

11. **`experience_search_smart(query, kb_id="", top_k=10)`** — 智能多路径检索
    - 内部调用 Query 理解层 → 5 路径并行召回 → 融合去重
    - 替代当前的 `experience_search_global` 作为推荐检索入口
    - `experience_search_global` 保留作为底层接口

#### 0.2c 语义内容验证 (Semantic Content Verification)

**替换当前的 `_content_verify()` token 匹配:**

当前的 token 覆盖率打分存在致命缺陷:
```
查询: "电池热管理 相变材料 冷却"
经验A problem: "电池BTMS系统使用双PCM实现热管理" → token_coverage=高 → 高分 ✅
经验B problem: "数据中心服务器热管理使用相变材料" → token_coverage=高 → 也高分 ❌
```

**新增方法:** `_semantic_verify(query_intent, exp) → (relevant, score, reason)`

| 维度 | 当前(token) | 增强(语义) |
|------|------------|-----------|
| 领域匹配 | token覆盖率 | domain_tokens ∩ exp.tags 交集 + 语义距离 |
| 问题匹配 | token覆盖率 | problem_tokens 在 exp.problem 中的语义命中 |
| 方案可用性 | token覆盖率 | action_tokens 在 exp.solution 中的操作匹配 |
| 防误报 | 覆盖率阈值 | **反例检测**: query和exp的关键差异词检测 |

**反例检测 (Counter-Example Detection):**
```python
# 如果 query 和 exp 共享了通用词（如 "thermal management"），
# 但关键差异词（如 "battery" vs "data center"）不匹配 → 降分
key_diff = set(exp.domain_terms) - set(query.domain_terms)
if key_diff and len(key_diff) > 2:
    score -= penalty  # 领域不匹配处罚
```

**实现策略:**
- 内容验证仍然在 Agent 层完成（MCP 工具 → Agent LLM 裁决）
- 后端 `_content_verify` 增加语义差异检测（CJK/英文关键词差异加权）
- Agent 在 E4 Step 2 的 `experience_read` 后执行独立语义裁决

#### 0.2d 自适应阈值 (Adaptive Thresholding)

| Query类型 | 硬阈值 | 内容门槛 | 策略 |
|-----------|--------|---------|------|
| **troubleshooting** (故障排查) | 0.55 | content≥5 | 宁缺毋滥，只要高质量 |
| **best_practice** (最佳实践) | 0.45 | content≥4 | 中等门槛 |
| **learning** (学习参考) | 0.35 | content≥3 | 可接受弱相关 |
| **decision** (决策支持) | 0.50 | content≥5 | 需强证据 |

阈值在 Query 理解层自动确定，无需用户指定。

#### 0.2e 智能重排序 (Smart Reranking)

**在 MCP 工具层实现（Agent LLM 裁决），不侵入后端:**

```
召回 Top-15 → 内容验证 → 剩余 Top-8 → LLM 语义重排 → 输出 Top-5

LLM 重排提示词:
"对以下8条经验，按与查询的语义相关性重新排序。考虑：
 1. 领域是否匹配（battery vs data center）
 2. 问题描述是否精准对应查询意图
 3. 解决方案是否可直接应用
 4. 经验的可信度（rating + applied_count）
 输出排序结果和每条的排序理由。"
```

**新增 MCP 工具:**

12. **`experience_rerank(query, experiences_json)`** — LLM 语义重排序
    - 输入：查询 + 候选经验列表（含 metadata）
    - 输出：重排序后的经验列表 + 排序理由
    - 轻量：只在 MCP 工具层，不调后端

#### 0.2f 多轮检索 (Multi-Round Retrieval)

当首轮检索结果为 0 时，不直接放弃:

```
Round 1: 原始查询 → 0 结果
  → 自动扩展: query_expanded (同义词/翻译)
Round 2: 扩展查询 → 0 结果
  → 降低阈值: threshold *= 0.7
Round 3: 降阈值 + 仅向量 → 仍有结果？
  → 有: 标注 "low_confidence", 诚实声明阈值降低
  → 无: 诚实声明 "无相关经验"
```

**新增 MCP 工具属性:**
- `experience_search_smart` 返回增加字段 `rounds: int` (检索轮次) 和 `degraded: bool` (是否降级)

#### 0.2g 检索透明化 (Retrieval Transparency)

每条返回的经验增加:

```json
{
  "retrieval_paths": ["vector", "keyword"],     // 哪些路径召回了此经验
  "match_details": {
    "domain_match": ["电池", "热管理"],          // 匹配的领域词
    "problem_match": ["过热", "温度不均"],       // 匹配的问题词
    "coverages": {"topic": 0.75, "scenario": 0.6, "solution": 0.5}
  },
  "ranking_reason": "领域精准匹配(电池热管理) + 问题直接对应(BTMS故障) + 高可信度(rating=5.0)"
}
```

---

## 实施计划更新

### 最高优先级: Phase 0 检索增强

| 任务 | 文件 | 工具 | 工作量 |
|------|------|------|--------|
| **新增** `experience_search_smart` MCP工具 | `kb-mcp/server.py` | `experience_search_smart` | 3h |
| Query理解层 (Agent-side LLM分析) | `kb-mcp/server.py` | (内嵌在smart工具中) | 2h |
| 5路径并行召回 + 融合去重 | `kb-mcp/server.py` | (内嵌) | 2h |
| **新增** `experience_rerank` MCP工具 | `kb-mcp/server.py` | `experience_rerank` | 1h |
| 自适应阈值策略 | `kb-mcp/server.py` | (内嵌) | 1h |
| 多轮检索降级逻辑 | `kb-mcp/server.py` | (内嵌) | 1h |
| **增强** `_content_verify` 反例检测 | `backend/app/services/experience_service.py` | (内部) | 1.5h |
| 检索透明化字段 | `kb-mcp/server.py` | (内嵌) | 1h |
| 更新 experience skill E4 检索流程 | `knowledgebase-experience/SKILL.md` | 文档 | 1h |
| 更新 CLAUDE.md 经验检索说明 | `CLAUDE.md` | 文档 | 30min |
| 端到端测试 (10个场景) | — | — | 2h |

**Phase 0 总工作量: ~16h**

---

## Phase 1-4: 经验总结/创建机制全面增强

> **核心目标:** 让经验从"用户填表"升级为"Agent 引导 + 场景自适应 + 质量闭环"的智能凝练系统。
> 真正满足用户意图，从 KB 中凝练出最符合期望的可复用经验。

---

## Phase 1: 用户引导式经验构建 (User-Guided Interactive Builder) ⭐⭐⭐

**解决问题:** 当前 `knowledgebase-experience-summarize` 是"填表式"——用户必须自己想清楚所有字段。真实场景中用户只知道"我解决了问题，想存下来"，不知道如何结构化。

### 1.1 意图捕获层 (Intent Capture)

**新增 MCP 工具 13:** `experience_builder_start(kb_id, context, intent_hint="")`

在起草前先理解**为什么**要保存这条经验：

```python
IntentType = Literal[
    "future_fix",           # 未来遇到同类问题能快速修复
    "compliance_record",    # 合规/审计留痕
    "knowledge_transfer",   # 传授给新人/其他团队
    "process_standard",     # 固化为标准流程
    "lesson_learning",      # 从失败中学习
]

# Agent 内部分析（LLM 单次调用）：
intent_analysis = {
    "intent_type": "future_fix",
    "target_audience": "运维工程师",
    "urgency": "high",           # 决定是否加急审核
    "expected_lifespan": "long", # 影响是否值得长期维护
    "source": "conversation",    # conversation | document | manual
}
```

**意图决定结构侧重:**
| 意图 | problem 侧重 | solution 侧重 | key_lessons 侧重 |
|------|-------------|---------------|-----------------|
| future_fix | 症状精准描述 | 步骤化、可复制 | 预防措施、预警信号 |
| compliance_record | 背景+决策依据 | 决策本身 | 合规要点、责任人 |
| knowledge_transfer | 新人易误解的点 | 完整流程+原理 | 常见错误、最佳实践 |
| process_standard | 触发条件 | 标准步骤SOP | 验收标准、异常处理 |
| lesson_learning | 发生了什么 | 为什么会这样 | 下次怎么做不同 |

### 1.2 模板系统 (Template System)

**新增 MCP 工具 14:** `experience_templates(category="")` — 列出可用模板

5 种经验原型，每种有定制化字段结构：

```python
TEMPLATES = {
    "troubleshooting": {
        "required_fields": ["symptom", "root_cause", "fix_steps", "prevention"],
        "field_hints": {
            "symptom": "故障的可观测现象（含数值/日志/报警）",
            "root_cause": "根因分析（不是表象）",
            "fix_steps": "修复步骤（有序、可验证）",
            "prevention": "预防措施（监控/告警/巡检）",
        },
    },
    "decision": {
        "required_fields": ["context", "options", "decision", "rationale", "outcome"],
    },
    "workflow": {
        "required_fields": ["trigger", "prerequisites", "steps", "verification", "exceptions"],
    },
    "best_practice": {
        "required_fields": ["scenario", "recommendation", "evidence", "caveats"],
    },
    "lesson_learned": {
        "required_fields": ["what_happened", "why", "learned", "do_differently"],
    },
}
```

**模板自动推荐:** Agent 根据对话内容判断类型 → 推荐模板 → 用户可确认或切换。

### 1.3 对话上下文挖掘 (Conversation Mining)

**新增 MCP 工具 15:** `experience_mine_conversation(context_text)`

不再要求用户手动总结。Agent 从对话历史中自动提取：

```
输入: 最近 N 轮对话（用户搜索了什么、读了哪些文档、怎么讨论的、结论是什么）

LLM 提取 pipeline:
  1. 识别"问题陈述"（用户最初的问题/痛点）
  2. 识别"探索过程"（试了什么、为什么不行）
  3. 识别"最终方案"（什么有效）
  4. 识别"关键决策点"（为什么选这个方案）
  5. 识别"关联文档"（搜索/读取过哪些文档）
  6. 识别"教训/洞察"（过程中的发现）

输出: 结构化候选草稿（含 source_quotes 引用原文证据）
```

**关键设计:** 每个提取的字段附带 `source_quote`（原文引用），让用户能验证"这是我真的说过/做过的"。

### 1.4 多轮迭代精炼 (Multi-Round Refinement)

**新增 MCP 工具 16:** `experience_builder_refine(draft_id, feedback_type, feedback_content)`

```python
feedback_type = Literal[
    "more_specific",     # "不够具体" → Agent 补充细节
    "add_field",         # "加个前置条件" → Agent 添加字段
    "correct_content",   # "方案错了，应该是X" → Agent 更新
    "change_template",   # "这其实是决策记录不是故障排查" → 切换模板
    "adjust_severity",   # "这个其实是 critical" → 调整严重度
    "add_evidence",      # "加个数据支撑" → Agent 找相关数据
]
```

**迭代历史追踪:** 每次 refine 记录到 `refinement_history[]`，用户可回溯"我的经验是怎么演化出来的"。

### 1.5 创建前质量评分 (Pre-Creation Quality Scoring)

**新增 MCP 工具 17:** `experience_quality_score(draft)`

在 `experience_create` 之前强制评分（分数 < 60 阻止创建）：

| 维度 | 分值 | 评分标准 |
|------|------|---------|
| **具体性 (Specificity)** | 0-25 | 含数值/名称/版本号 → +25；纯描述性 → +5 |
| **可操作性 (Actionability)** | 0-25 | 含可执行步骤/命令/配置 → +25；方向性指导 → +10 |
| **独立性 (Independence)** | 0-20 | 不依赖上下文可独立理解 → +20；需参考原文 → +5 |
| **完整性 (Completeness)** | 0-15 | 所有模板字段有意义填写 → +15；有空字段 → 扣分 |
| **证据支撑 (Evidence)** | 0-15 | 有 related_docs + source_quotes → +15；无证据 → +0 |

**评分 < 60:** 返回具体改进建议（"problem 缺少数值"，"solution 没有步骤号"），阻止创建。
**评分 ≥ 60:** 允许创建，分数写入 `quality_score` 字段作为基线。

### Phase 1 新增工具汇总

| 工具 | 功能 | 工作量 |
|------|------|--------|
| `experience_builder_start` | 意图捕获 + 模板推荐 + 起草 | 3h |
| `experience_templates` | 模板列表 + 字段提示 | 1h |
| `experience_mine_conversation` | 对话上下文挖掘 | 2h |
| `experience_builder_refine` | 多轮迭代精炼 | 1.5h |
| `experience_quality_score` | 创建前评分 | 1.5h |
| Skill 更新 (`knowledgebase-experience-summarize`) | 集成引导式流程 | 2h |
| **Phase 1 小计** | | **11h** |

---

## Phase 2: 场景自适应自动 CRUD (Scenario-Adaptive Auto Lifecycle) ⭐⭐⭐

**解决问题:** 当前经验全靠用户/Agent 主动触发。应该让系统**自适应**：该创时创、该改时改、该删时删。

### 2.1 自动创建触发 (Auto-Creation Triggers)

**新增 MCP 工具 18:** `experience_check_creation_opportunity(context)`

在以下场景自动检测创建机会：

| 触发场景 | 判定条件 | 动作 |
|---------|---------|------|
| **搜索成功后** | kb_search_two_stage 返回结果 + 用户表示满意 | 建议保存为经验 |
| **文档入库后** | 新文档入库（Ingest A7 通过） | 扫描可提取经验 |
| **经验应用后** | experience_apply 调用 | 询问应用结果+补充 |
| **定期扫描** | 每周/每月 | 分析近期活动，发现未保存的可复用知识 |

**返回结构:**
```json
{
  "opportunities": [
    {
      "type": "post_search",
      "trigger": "用户刚搜索了'电池热管理'并读取了3篇文档",
      "suggested_action": "create",
      "draft_seed": {  // 草稿种子，喂给 experience_builder_start
        "problem": "...",
        "solution": "...",
        "related_docs": ["..."]
      },
      "confidence": 0.85
    }
  ]
}
```

### 2.2 创建前去重检测 (Pre-Creation Duplicate Check)

**新增 MCP 工具 19:** `experience_duplicate_check(kb_id, draft)`

在 `experience_create` 前强制调用（可内嵌在 builder_start）：

```
语义相似度检测:
  sim ≥ 0.85 → 强相似，建议 UPDATE 已有经验（附 diff 建议）
  0.6 ≤ sim < 0.85 → 相关，建议 LINK (complements 关系)
  sim < 0.6 → 无重复，允许 CREATE
```

**实现:** 复用 `experience_search_global` 向量召回 + LLM 语义对比。

### 2.3 文档变更触发自动更新 (Doc-Change Auto-Update)

**新增 MCP 工具 20:** `experience_smart_update(exp_id)`

当 `experience_check_stale` 发现 stale 经验时，不再要求 Agent 手动处理：

```
experience_smart_update(exp_id) 内部流程:
  1. experience_read(exp_id) → 读取当前经验
  2. kb_doc_read(related_docs) → 读取关联文档最新内容
  3. LLM 对比:
     - 文档新增了什么？
     - 旧经验 problem/solution/key_lessons 是否仍准确？
     - 需要更新哪些字段？
  4. 自动决策:
     - 仍准确 → 刷新 updated_at，清除 stale 标记
     - 需小更新 → 直接 experience_update（高置信度）
     - 需大改 → 生成 update_draft，入审核队列（低置信度）
     - 已过时 → 标记 orphan，建议归档
  5. 记录到 history（Phase 3 版本控制）
```

**批量版本:** `experience_auto_update_kb(kb_id)` 一键处理整个 KB 的 stale 经验。

### 2.4 自动归档 (Auto-Archive)

**新增 MCP 工具 21:** `experience_auto_archive(kb_id, dry_run=true)`

低价值经验自动归档（不删除，移到 `archive/` 目录，从默认搜索排除）：

**归档条件（全部满足）:**
```python
created_at < now - 60 days          # 创建超过 60 天
AND applied_count == 0              # 从未被应用
AND review_count == 0               # 从未被评审
AND quality_score < 40              # 质量评分低
```

**例外保护:** severity=critical 的经验永不自动归档（即使低应用，可能未来关键）。

### 2.5 智能合并扫描 (Smart Merge Scan)

**新增 MCP 工具 22:** `experience_merge_scan(kb_id, threshold=0.8)`

定期扫描相似经验对，建议合并：

```json
{
  "merge_candidates": [
    {
      "exp_a": "exp-xxx (电池热管理排查)",
      "exp_b": "exp-yyy (BTMS故障处理)",
      "similarity": 0.87,
      "overlap_fields": ["problem", "key_lessons"],
      "unique_fields": {  // 各自独有的内容，合并时保留
        "a_only": ["水冷方案"],
        "b_only": ["PCM方案"]
      },
      "suggested_strategy": "combine",
      "reason": "同一场景的两种方案，合并为完整经验"
    }
  ]
}
```

**合并不自动执行** — 进审核队列，用户确认后调用 `experience_merge`（Phase 2 已规划）。

### Phase 2 新增工具汇总

| 工具 | 功能 | 工作量 |
|------|------|--------|
| `experience_check_creation_opportunity` | 创建机会检测 | 2h |
| `experience_duplicate_check` | 创建前去重 | 1.5h |
| `experience_smart_update` | 智能更新单条 | 2h |
| `experience_auto_update_kb` | 批量自动更新 | 1.5h |
| `experience_auto_archive` | 自动归档 | 1.5h |
| `experience_merge_scan` | 合并扫描 | 2h |
| **Phase 2 小计** | | **10.5h** |

---

## Phase 3: 质量反馈闭环 (Quality Feedback Loop) ⭐⭐

**解决问题:** 当前经验创建后质量是静态的（除非手动 review）。应该让质量**随使用动态演化**。

### 3.1 应用反馈捕获 (Application Feedback)

**新增 MCP 工具 23:** `experience_feedback(exp_id, outcome, notes="", missing="")`

增强当前的 `experience_apply`：应用后必须捕获结果反馈。

```python
outcome = Literal[
    "solved",          # 完全解决了问题
    "partial",         # 部分有效，需要补充
    "failed",          # 没用，方案失效
    "not_applicable",  # 场景不匹配
    "outdated",        # 方案过时
]

# 反馈记录到 experience 的 feedback_history[]
{
    "user": "...",
    "timestamp": "...",
    "outcome": "partial",
    "notes": "方案大体对，但缺少温度阈值的具体数值",
    "missing": "需要补充 PCM 熔点选择依据"
}
```

### 3.2 质量分动态演化 (Quality Score Evolution)

`quality_score` 从 Phase 1.5 的基线开始，随使用动态调整：

```python
quality_score_adjustments = {
    "successful_application": +10,    # experience_apply + outcome=solved
    "partial_application": +3,        # outcome=partial
    "failed_application": -8,         # outcome=failed
    "5_star_review": +5,              # experience_review rating=5
    "1_star_review": -8,              # rating=1
    "30d_no_application": -3,         # 静默衰减
    "positive_feedback_note": +2,     # 用户主动补充正面评价
}

# 质量分区间:
# 80-100: verified (高可信，搜索加权)
# 50-79:  normal (默认)
# 30-49:  review_needed (标记待改进)
# 0-29:   deprecated (默认搜索隐藏，需 explicit 才返回)
```

### 3.3 自动升降级 (Auto Promotion/Demotion)

**新增 MCP 工具 24:** `experience_quality_recompute(kb_id)` — 批量重算质量分

根据质量分自动调整 tier：

| 条件 | 动作 |
|------|------|
| quality > 80 ∧ applied ≥ 3 ∧ rating ≥ 4 | **promote** → verified (P0 候选) |
| quality < 30 | **demote** → deprecated (搜索隐藏) |
| quality < 10 持续 60 天 | **archive** → 移到 archive/ |

### 3.4 质量看板 (Quality Dashboard)

**新增 MCP 工具 25:** `experience_quality_dashboard(kb_id)`

```json
{
  "total": 14,
  "by_quality_tier": {"verified": 2, "normal": 8, "review_needed": 3, "deprecated": 1},
  "avg_quality": 62.5,
  "top_quality": [{"exp_id": "...", "score": 92, "title": "..."}],
  "needs_attention": [{"exp_id": "...", "score": 28, "reason": "2次失败应用"}],
  "feedback_summary": {
    "total_applications": 15,
    "success_rate": 0.73,
    "common_missing": ["具体数值阈值", "异常处理步骤"]
  }
}
```

### 3.5 模式学习 (Pattern Learning)

**新增 MCP 工具 26:** `experience_pattern_analysis()`

分析高质量经验的共同特征，反哺创建流程：

```
分析维度:
  - 高分经验 vs 低分经验的字段差异
  - 哪些 tags 的经验应用率最高
  - 哪些 category 的经验质量波动大
  - key_lessons 的平均条数与质量的关系

输出:
  "patterns": [
    "含具体数值的经验应用率比纯描述高 3.2x",
    "key_lessons 3-5 条的经验质量最高（>5 条反而下降）",
    "troubleshooting 类经验平均质量比 best_practice 高 15%"
  ]
  → 这些模式自动注入 experience_quality_score 的评分权重
```

### Phase 3 新增工具汇总

| 工具 | 功能 | 工作量 |
|------|------|--------|
| `experience_feedback` | 应用反馈捕获 | 1.5h |
| `experience_quality_recompute` | 批量重算质量分 | 1h |
| `experience_quality_dashboard` | 质量看板 | 1.5h |
| `experience_pattern_analysis` | 模式学习 | 2h |
| 后端 quality_score 字段 + 演化逻辑 | `experience_service.py` | 2h |
| 后端 feedback_history 存储 | `experience_service.py` | 1h |
| **Phase 3 小计** | | **9h** |

---

## Phase 4: 智能提取增强 (Intelligent Extraction) ⭐⭐

**解决问题:** 当前 heuristic 模式产出垃圾（章节标题误判），prepare 模式需大量人工。需要"中间地带"——LLM 驱动但自动化的高质量提取。

### 4.1 LLM 引导提取 (Smart Extraction)

**新增 MCP 工具 27:** `experience_extract_smart(kb_id, doc_paths=[], topic="", mode="smart")`

在 heuristic（规则、低质）和 prepare（任务包、手动）之间的**第三模式**：

```
smart 模式流程:
  1. 选定目标文档（指定或按 topic 检索）
  2. LLM 逐文档阅读（max_chars=5000）
  3. 按 Phase 1.2 模板提取候选经验
  4. 每候选打 quality_score（Phase 1.5）
  5. score ≥ 0.7 → 进 draft 池
     score < 0.7 → 丢弃（不污染审核队列）
  6. 返回提取报告（提取了几条、质量分布、丢弃原因）
```

**与 heuristic 区别:**
| 维度 | heuristic | smart |
|------|-----------|-------|
| 提取方式 | 正则+关键词 | LLM 理解语义 |
| 章节标题误判 | 严重（实测垃圾多） | 几乎无（LLM 能识别） |
| key_lessons 质量 | 章节标题 raw dump | 提炼后的可引用要点 |
| 质量门控 | 事后过滤（E2a） | 事前评分（score ≥ 0.7 才入池） |
| 成本 | 零（纯规则） | 每文档 1 次 LLM 调用 |

### 4.2 主题驱动批量提取 (Topic-Driven Batch)

**新增 MCP 工具 28:** `experience_extract_topic(kb_id, topic, max_docs=10)`

用户说 "从 Energy-Batteries 提取所有 thermal management 经验"：

```
流程:
  1. kb_search_two_stage(kb_id, topic) → 找到相关文档
  2. 对 top-N 文档调用 experience_extract_smart
  3. 跨文档去重（Phase 2.2 duplicate_check）
  4. 批量入 draft 池
  5. 返回提取摘要 + 草稿列表
```

### 4.3 跨文档综合 (Cross-Document Synthesis)

**新增 MCP 工具 29:** `experience_synthesize(kb_id, topic)`

某些经验**跨多个文档**，单文档提取会遗漏：

```
用户: "我们在材料设计方面整体学到了什么？"
流程:
  1. 搜索 KB 内所有相关文档
  2. LLM 综合阅读所有文档（每篇 max_chars=3000）
  3. 提炼跨文档的共性经验（不是单文档经验）
  4. 标注 evidence_docs（多条文档作为证据）
  5. 产出"综合性经验"（category=best_practice，evidence 多源）
```

**与单文档提取区别:** 综合性经验的 `related_docs` 是多条，`key_lessons` 是跨文档提炼的共性，质量分天然更高（证据充足）。

### 4.4 提取质量门控增强 (Extraction Quality Gate)

更新 E2a 质量门控，从"只拒绝垃圾"升级为"正向评分+拒绝"：

```python
# 现有 E2a: 拒绝垃圾（章节标题、空 tags、raw dump）
# 增强 E2a+: 正向质量评分

candidate_score = {
    "specificity": check_specificity(candidate),    # 含数值/名称/版本
    "novelty": check_novelty(candidate, existing),  # 与已有经验的差异度
    "actionability": check_actionability(candidate),# 可执行步骤
    "evidence": check_evidence(candidate, doc),     # 文档中有原文支撑
}
total = sum(candidate_score.values())

# 决策:
total ≥ 0.7 → 进 draft 池（高质量）
0.4 ≤ total < 0.7 → 标记 "needs_refinement"，进 draft 池但标注
total < 0.4 → 丢弃（现有 E2a 行为）
```

### Phase 4 新增工具汇总

| 工具 | 功能 | 工作量 |
|------|------|--------|
| `experience_extract_smart` | LLM 引导提取 | 3h |
| `experience_extract_topic` | 主题批量提取 | 2h |
| `experience_synthesize` | 跨文档综合 | 2.5h |
| E2a+ 质量评分增强 | `experience_service.py` | 1.5h |
| Skill 更新 (E0/E1 增加 smart 模式) | `knowledgebase-experience/SKILL.md` | 1h |
| **Phase 4 小计** | | **10h** |

---

## 总体工作量更新

| 阶段 | 内容 | 新增工具 | 工作量 |
|------|------|---------|--------|
| **Phase 0** | 智能检索 | 2 | 16h |
| **Phase 1** | 用户引导式构建 | 5 | 11h |
| **Phase 2** | 场景自适应 CRUD | 5 | 10.5h |
| **Phase 3** | 质量反馈闭环 | 4 | 9h |
| **Phase 4** | 智能提取增强 | 3 | 10h |
| **总计** | | **19 新工具** | **~56.5h** |

## 实施优先级（建议顺序）

```
Phase 0 (检索) ──────────────────────────────────── 🔴 立即（解决"乱给"问题）
    ↓
Phase 1.5 (质量评分) + Phase 4.1 (smart提取) ──────── 🔴 立即（解决"垃圾经验"问题）
    ↓
Phase 1.1-1.4 (引导式构建) ───────────────────────── 🟡 高优（解决"用户不会填"问题）
    ↓
Phase 2.1-2.3 (自动创建+去重+更新) ───────────────── 🟡 高优（解决"被动维护"问题）
    ↓
Phase 3 (质量闭环) ───────────────────────────────── 🟢 中优（让经验越用越好）
    ↓
Phase 2.4-2.5 (归档+合并) + Phase 4.2-4.3 ────────── 🟢 增强（锦上添花）
```

## 经验总结增强前后对比

| 维度 | 增强前 | 增强后 |
|------|--------|--------|
| **创建触发** | 用户主动调用 | 对话上下文自动挖掘 + 场景自适应触发 |
| **起草方式** | 用户填表式 | Agent 引导 + 模板化 + 多轮精炼 |
| **意图理解** | 无 | 5 种意图类型决定结构侧重 |
| **模板** | 单一结构 | 5 种原型（故障/决策/工作流/最佳实践/教训） |
| **创建前质检** | 无 | 5 维度评分 < 60 阻止创建 |
| **去重** | 无 | 语义相似度 ≥ 0.85 建议 UPDATE |
| **更新** | 手动 E6a 流程 | LLM 自动 smart_update + 批量处理 |
| **归档** | 手动删除 | 条件触发自动归档（保留可恢复） |
| **质量演化** | 静态（rating_avg） | 动态 quality_score 随应用演化 |
| **反馈** | apply_count 仅计数 | 结构化 outcome + 缺失内容捕获 |
| **提取** | heuristic(垃圾)/prepare(手动) | smart(LLM驱动+质量评分) |
| **跨文档** | 不支持 | 综合性经验（多源证据） |

## 兼容性保证（再次确认）

- 所有 19 个新工具为**增量添加**，不影响现有 77 个工具
- 现有经验数据结构不变，新增字段（`quality_score`, `feedback_history`, `refinement_history`, `template_type`, `intent_type`, `source`）为**可选**
- 现有 Skill 流程不变，新流程为可选增强路径
- 现有 `experience_create/read/update/delete` 接口不变
- MCP 优先原则保持不变
- 所有 LLM 工作在 MCP/Agent 层，后端只做数据持久化

## 总体工作量: ~40h

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| **Phase 0** | 智能检索 | 16h |
| Phase 1 | 对话引导创建 | 6.5h |
| Phase 2 | 经验链路融合 | 6.5h |
| Phase 3 | 自动更新版本 | 5.5h |
| Phase 4 | 场景驱动 | 5.5h |
| **总计** | | **~40h** |

## 检索增强前后对比

| 指标 | 增强前 | 增强后 |
|------|--------|--------|
| 召回路径 | 2 (向量+关键词) | 5 (向量+关键词+scenario+tag+质量) |
| Query理解 | 无 (裸查询) | 意图分类+实体提取+查询扩展 |
| 内容验证 | token覆盖率 (易误判) | token覆盖率+语义差异检测+反例防护 |
| 阈值 | 单一 0.45 | 自适应 (故障0.55/最佳实践0.45/学习0.35) |
| 排序 | 向量分 | LLM语义重排+多样性+新鲜度 |
| 0结果处理 | 直接放弃 | 查询扩展→降阈值→诚实声明 |
| 解释性 | tier+score | 召回路径+匹配详情+排序理由 |
| 误召回率 | 中 (token匹配导致) | 低 (反例检测+语义验证) |

## 兼容性保证

- `experience_search_global` 保留不变作为底层接口
- `experience_search_smart` 作为新的推荐检索入口
- `experience_search` 和 `experience_search_vector` 不变
- 现有 P0/P1/P2 分级不变
- 所有 Skill 向下兼容