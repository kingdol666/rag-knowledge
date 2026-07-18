# 经验可信度模型 (Experience Credibility Model)

> 摘自项目 CLAUDE.md — 全局安装插件后技能可独立引用

## 可信度分级

| Tier | 条件 | 动作 |
|------|------|------|
| **P0 Strong** | vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ review≥1 | Strong recommend, pin to top |
| **P1 Reference** | vector≥0.45 ∧ content≥4 | Recommend, annotate credibility |
| **P2 Weak** | vector≥0.35 ∧ content≥3 | Suppress by default (show only on explicit expand) |
| **DISCARD** | 内容验证不通过 OR vector < 0.35 | 永不返回 |

## 可信度修饰符

| 修饰符 | 条件 | 效果 |
|--------|------|------|
| disputed | ≥3 reviews ∧ rating<2.0 | 降级至最多 P2 |
| unvetted | 0 reviews ∧ 0 applied | 上限最多 P1 |

## 衰减周期

| 规则 | 条件 | 效果 |
|------|------|------|
| stale_unverified | 创建>30天 ∧ 0应用 | 检索降级 |
| disputed | ≥3评审 ∧ rating<2.0 | 降到 P2 |
| unvetted | 0评审 ∧ 0应用 | 最高 P1 |

## 短内容虚假命中防护

向量搜索可能返回极短片段（如仅"## 问题"）并伴随虚高评分：
- Chunks < 50 chars → 降级到 P2（隐藏）
- 同一文档 >50% 片段为短内容 → 降级整篇文档
- 例外：同文档存在其他 P0/P1 片段 → 短片段放行
