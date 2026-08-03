# SOUL-RAG 策略参考 — 检索 + 人格增强的完整决策

> soul-rag skill 的权威细则。回答"什么时候该用 SOUL 增强、怎么增强、怎么降级"。

## 1. 三种问答模式(按需求选择)

| 模式 | 触发 | 流程 | 返回 |
|---|---|---|---|
| **纯检索** | "查/搜/找XX资料" | kb_search_two_stage | 原始片段 |
| **人格问答** | "用XX人格回答/以XX口吻" | soul_ask(显式人格) | 人格化答案+引用+PAS |
| **检索+人格增强** | "查一下XX,用人格总结/回答" | kb_search → soul_ask(context_override) | 证据+人格化答案 |

## 2. 自动路由的完整链路

```
query + task_goal + task_type
  → soul_router:
     (query_hash, task_type) TTL 缓存 → 命中直接返回
     → soul_list(排除模板) → 候选
     → >8 个? domain_labels embedding 余弦初筛 top8
     → 读 profile-summary(缓存;learn/审批/reflect 后刷新)
     → LLM 打分(route_weight 加权,≤8 候选)
     → top1 score ≥ 0.6 → 选中;否则 route_uncertain
     → complete() 失败 → embedding 余弦降级(标记 embedding_fallback)
     → router-log.jsonl 审计
  → soul_ask(soul_kb_id=top1): 人格注入 + scope 检索 + 记忆摘要 + 合成 + PAS
```

**路由质量度量**: 校准脚本 `scripts/soul/calibrate.py` 用
`backend/app/data/router-test-queries.jsonl`(≥20 条)测准确率,
目标 ≥80%。报告写 `reports/router-calibration-YYYYMMDD.md`。

## 3. 何时用 context_override

| 场景 | 用法 |
|---|---|
| 跨库检索后人格总结 | kb_search_two_stage(balance_kbs=True) → 片段 → context_override |
| 用户给了文档/片段 | 直接作为 context_override 注入 |
| 多轮对话补充背景 | 前序答案精华 → context_override(仅本次有效) |
| 人格 scope 外知识 | 先用全局检索拿证据,再注入让该人格加工 |

**注入格式**: 纯文本片段(≤1000 字符),标注来源路径。人格会基于它回答,
引用锚点仍校验真实路径。

## 4. 降级路径(quality degradation ladder)

```
1. soul_ask 正常 → 人格化答案 + citations + PAS
2. 路由不确定(route_uncertain=true) → 返回候选列表让用户选
3. 检索失败(citations=[]) → 人格诚实声明盲区 + 给检索建议
   (人格仍按自己的风格说明"知识库无相关证据",不编造)
4. harness 不可用 → 可读错误提示重试
```

**降级到普通检索**: 用户只要原始片段,或人格系统不可用 → 直接
kb_search_two_stage,不强行套人格。

## 5. 与知识库能力的融合

SOUL-RAG 复用的是现有知识库能力:
- 检索: two_stage(BM25+向量+图谱融合)— knowledgebase 同一套
- 索引: 人格记忆审批后走同一索引管线(向量+图谱+BM25)
- 图谱: 人格文档/记忆也入图谱,跨库邻居可扩展
- 预算: 路由成本单独池,学习预算独立

**人格是"检索结果的加工层",不是替代检索**: 没有检索证据的人格回答
会被质量闸门(接地性)拦截;这正是防幻觉的根。

## 6. 端到端示例

```
用户: "查一下 MXene 储能机理,用研究者人格回答"
  → kb_search_two_stage("MXene 储能机理", kb_id="Materials-Science")
  → 命中片段(score≥0.5)
  → soul_router("MXene 储能机理", task_type="文献综述") → soul-材料学(0.95)
  → soul_ask(query, soul_kb_id="soul-材料学", context_override=<片段>)
  → 答案: 先结论后论证的科研风格 + citations + PAS 5.0
```

## 7. 运维要点

- 人格 profile 陈旧会劣化路由: 训练/审批/反思后系统自动刷新 profile-summary
- 校准集 ≥20 条才可校准;提示词变更自动触发校准重跑
- 路由日志 router-log.jsonl 可审计每次决策(含阈值/置信度)
- 新人格上线: soul_init → soul_learn 学 1-2 文档 → 补 2 条路由测试集
  → 校准验证
