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

### E2 — 检索经验（核心能力）

根据查询类型选择最佳检索策略：

**策略选择:**

| 用户意图 | 推荐工具 | 说明 |
|---------|---------|------|
| 精确场景匹配（"coal-mill-fault"） | `experience_find_by_scenario` | 场景标识精确匹配 |
| 关键词查询（"磨煤机 堵煤"） | `experience_search` | 元信息多字段匹配 |
| 自然语言查询（"如何处理类似振动问题"） | `experience_search_vector` | 向量语义搜索（需要已建索引） |
| 全库查询（"所有故障排查经验"） | `experience_search_global` | 跨 KB 全局搜索 |

**检索流程:**
1. 识别查询类型 → 选择策略
2. 按场景匹配 → `experience_find_by_scenario(kb_id, scenario)`
3. 无场景 → `experience_search_vector(kb_id, query)` 语义搜索
4. 向量不可用 → `experience_search(kb_id, query)` 元信息兜底
5. 全库需求 → `experience_search_global(query)`
6. 结果按 rating_avg + applied_count 排序
7. 详细内容 → `experience_read(kb_id, exp_id)`

**经验排序标准:**
- ⭐⭐⭐ 高可信度: rating ≥ 4.0 AND applied ≥ 3
- ⭐⭐ 可参考: rating ≥ 3.0
- ⭐ 待验证: applied = 0（新经验）

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
