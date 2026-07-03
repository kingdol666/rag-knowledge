# Experience 机制 v2 — 补全计划摘要

> 完整计划: `.omc/plans/experience-mechanism-completion-plan-v2.md`

## v1 完成度: 70% — 核心CRUD完成，但"可搜索性"缺失

---

## 🔴 发现的 3 个 BUG

| # | BUG | 影响 |
|:-:|-----|------|
| 1 | **Nuxt `init.post.ts` HTTP 方法不匹配** | 后端是 GET，代理用 POST → 代理路径失败 |
| 2 | **Nuxt `index.post.ts` URL 末尾多了 `/`** | FastAPI 不重定向 → 创建失败 |
| 3 | **Nuxt 代理无错误处理** | 后端宕机时前端崩溃 |

## 🟡 发现的 5 个遗漏功能

| # | 遗漏 | 严重性 | 影响 |
|:-:|------|:------:|------|
| 1 | **knowledge-search Skill 无 Experience 钩子** | 🔴 致命 | Agent 检索时不会联想经验 |
| 2 | **经验创建未自动向量索引** | 🔴 致命 | 经验存了但向量搜索找不到 |
| 3 | **经验向量搜索工具未实现** | 🟡 重要 | 自然语言查询无法匹配经验 |
| 4 | **跨 KB 经验搜索未实现** | 🟢 一般 | 全库经验检索缺失 |
| 5 | **KB 删除级联清理未验证** | 🟢 一般 | 可能有残留 |

## 关键洞察

> **v1 的根本问题：经验能"存"但不能"被找到"。**
>
> 没有向量索引 = 经验无法语义搜索  
> 没有 Skill 集成 = Agent 不会主动检索经验  
> 这两个加起来 = 经验机制形同虚设

## 补全方案（6 Phase，约 4 天）

| Phase | 内容 | 优先级 | 时间 |
|:-----:|------|:------:|:----:|
| **A** | 修复 3 个 BUG | P0 | 0.5天 |
| **B** | 经验向量索引集成 | P0 | 1天 |
| **C** | 3 个搜索工具（元信息/向量/跨库） | P1 | 1天 |
| **D** | knowledge-search Skill 集成 Experience | P0 | 0.5天 |
| **E** | 级联删除与一致性 | P2 | 0.5天 |
| **F** | 扩展测试 | P2 | 0.5天 |

## 最小可用闭环 = A + B + D

修好 BUG + 经验能向量搜索 + Agent 检索时能联想经验 = **经验机制真正可用**

## 补全后的 MCP 工具总数: 9 → 12

```
v1: experience_create/read/list/update/delete/apply/review/find_by_scenario/summary
v2 新增:
  🆕 experience_search          — 元信息搜索（title/problem/tags）
  🆕 experience_search_vector   — 向量语义搜索（自然语言查询）
  🆕 experience_search_global   — 跨 KB 全库搜索
```
