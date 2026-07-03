---
name: knowledge-experience
description: >
  经验管理系统 — 记录、检索、应用、评审经验。经验是实践总结的可复用知识，
  有评分、应用记录、场景绑定等结构化维度。用于故障排查、最佳实践、经验教训
  的动态管理和检索。Invoked by Archival 或用户直接请求。
---

# Knowledge Experience — 经验管理系统

## 触发场景
- 用户说"记录一个经验""保存这个操作经验""记住这个教训"
- 用户说"查一下有没有这方面的经验""这种情况以前怎么处理的"
- 用户说"这个经验有用/没用"、"给这个经验评分"
- 用户说"总结一下这个场景的经验"

## 经验管理流程

### E1 — 记录经验
1. 识别当前作业场景（scenario）
2. 收集关键信息: 问题→方案→结果→关键教训→标签→严重程度→关联文档
3. 调用 `experience_create` 保存
4. 验证: `experience_read` 确认写入成功

### E2 — 检索经验（核心能力，严格相关度）

> **铁律：宁可不给也不要错给。** 经验是实践总结，错给会误导决策。检索必须严格相关度过滤，灰区抑制，绝不拿低相关经验凑数。

根据查询类型选择最佳检索策略：

**策略选择:**

| 用户意图 | 推荐工具 | 说明 |
|---------|---------|------|
| 精确场景匹配（已知 scenario 标识） | `experience_find_by_scenario` | 最强信号，精确匹配 |
| 自然语言查询（"如何处理类似振动问题"） | `experience_search_vector` | 向量语义搜索（**严格 0.55 阈值**，后端已强制） |
| 全库查询（"所有故障排查经验"） | `experience_search_global` | 跨 KB 向量全局搜索 |
| 关键词精确查找（"磨煤机 堵煤"） | `experience_search` | 元信息分词匹配（兜底，需强命中） |

**检索流程:**
1. 识别查询类型 → 选择策略
2. 已知场景 → `experience_find_by_scenario(kb_id, scenario)` 精确（P0 候选）
3. 自然语言 → `experience_search_vector(kb_id, query)` 语义（严格 0.55）
4. 全库 → `experience_search_global(query)` 跨库向量
5. 详细内容 → `experience_read(kb_id, exp_id)` 确认正文真匹配
6. **置信度分层 + 短文本过滤**（下方）→ 只呈现 P0/P1，灰区抑制
7. 无 P0/P1 → **诚实说"暂无高相关经验"**，不凑数

**⚠️ 短文本误匹配过滤（关键，新增）：** 向量检索返回的 chunk 可能仅为短标题（如 "## 问题"、"## 方案"），score 虚高但无实质内容：
```
if len(chunk_content.strip()) < 50 characters:
    → 该 chunk 降为 P2 灰区（默认不呈现）
    → 除非该 chunk 的 experience 已有 P0/P1 的其他 chunk 背书
```
同一 experience >50% 的 chunk 为短文本 → experience 整体降级，必须 `experience_read` 全文确认。

**🆕 可信度衰减（新增）：**
- applied_count=0 ∧ created_at > 30天前 → 标注"未经验证"（⭐）
- rating_avg < 2.0 ∧ review_count ≥ 3 → 标注"争议经验"，降为 P1 即使 vector ≥ 0.65
- review_count = 0 ∧ applied_count = 0 → 标注"完全未核验"，P1 上限（不进入 P0）

**🆕 置信度分层（相关性 + 可信度融合，严格）：**

| 层级 | 条件 | 处理 |
|------|------|------|
| **P0 强推** | scenario 精确命中 ∧ vector ≥ 0.65 ∧ rating≥4 | 强烈推荐，置顶呈现 |
| **P1 可参考** | vector ≥ 0.55 ∧ rating≥3 | 推荐，标注可信度 |
| **P2 灰区** | 0.45 ≤ vector < 0.55（语义边界） | **默认抑制**，仅当用户明确"扩展探索"时呈现并标注"弱相关" |
| **❌ 丢弃** | vector < 0.45 或与场景不同设备/部件 | 不呈现 |

> 后端 `experience_search_vector` 已强制 0.55 阈值（P1 门槛），P2 灰区需调用方主动调低阈值或 Agent 二次判断。**默认行为是只给 P0/P1**。

**可信度标注（rating + applied，与 P 级正交）:**
- ⭐⭐⭐ 高可信度: rating ≥ 4.0 AND applied ≥ 3
- ⭐⭐ 可参考: rating ≥ 3.0
- ⭐ 待验证: applied = 0（新经验，即便 P0 也标注"未经验证"）

**呈现格式（严格）:**
```
找到 [N] 条高相关经验（P0/P1）：
⭐⭐⭐ [P0] 经验标题 (rating X.X, applied N, scenario=xxx)
   → 关键教训摘要
⭐⭐ [P1] 经验标题 (rating X.X)
   → 关键教训摘要
（若有 P2 灰区，默认隐藏；可补一句"另有 N 条弱相关经验，需深入可询问"）
```

**内容验证（必做）:** 即便 vector 高分，呈现前用 `experience_read` 抽查正文，确认 problem/solution 的设备/场景与用户问题一致。不一致 → 降级或丢弃（防向量误匹配）。

### E3 — 应用经验
1. 找到匹配经验后询问用户是否参考
2. 调用 `experience_apply` 记录使用者和效果
3. 应用成功则自动提升该经验的可信度（applied_count）

### E4 — 评审经验
1. 对使用过的经验邀请评分（0-5分）
2. 调用 `experience_review` 记录评审
3. 低评分经验标记为需 review

### E5 — 经验统计
1. 调用 `experience_summary` 获取统计
2. 报告：总经验数、类别分布、平均评分、Top经验
