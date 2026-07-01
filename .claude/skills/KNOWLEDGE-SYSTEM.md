# Knowledge Skill System — 完全架构

## 当前 8 个 Skills 全景

```
knowledge-store (入口/调度器)
├── 触发词：knowledge base, KB, 知识库, 文档管理, store, parse, upload, import, 
│           organize, audit, search, find, list, merge, delete, 整理, 入库等
│
├── knowledge-ingest (入库)       A1→A8 + A0 去重
│   ├── 触发：store, upload, parse, import, save, ingest, 存入, 解析
│   └── 能力：内容哈希去重 → 领域分类 → KB匹配 → 标签选择 → 存储 → 验证
│
├── knowledge-manage (管理)       M1→M5 + B6 内容更新
│   ├── 触发：move, rename, delete, merge, update, 移动, 改名, 删除
│   └── 能力：移动/改名/删除/合并/内容更新 → 确认防误 → 验证
│
├── knowledge-organize (整理)     O1→O7 全盘重构
│   ├── 触发：organize, audit, health check, restructure, 整理, 清洗
│   └── 能力：全盘调研 → 内容分类 → 合并 → 重命名 → 标签迁移 → 评分卡
│
├── knowledge-search (搜索)       S1→S5 全文检索
│   ├── 触发：search, find, query, 搜索, 查找, 查内容
│   └── 能力：关键词搜索 + 标签搜索 + 按KB分组 + 推荐阅读
│
├── knowledge-list (浏览)         L1→L3 只读
│   ├── 触发：list, show, what KBs, overview, tree, 列, 查, 查看
│   └── 能力：完整清单 → KB 深入 → 树形浏览
│
├── knowledge-verify (校验)  ← NEW
│   ├── 触发：verify, validate, integrity, health check, quality audit, 校验, 完整性
│   └── 能力：元数据一致性 → 文档可用性 → 解析质量 → 修复(可选) → 评分卡
│
└── knowledge-batch (批量)  ← NEW
    ├── 触发：batch, bulk, mass, all documents, every KB, 批量, 大规模
    └── 能力：批量标签 → 批量描述 → 目录导入 → 批量移动 → 去重 → 导出报告
```

## 调用链

### Main Claude → Archival

```
用户: "帮我整理一下当前的知识库，看看有没有需要处理的"
  → knowledge-store 被触发
  → 调度：Agent(subagent_type="archival", prompt="...")
  → Archival 诊断场景 → Organize
  → Skill("knowledge-organize")
  → O1 Survey → O2 Evaluate → O3 Categorize → O4 Execute → O5 Verify → O6 Scorecard
```

### Archival → Sub-skill 自动路由

```
Archival 诊断后：
  Ingest  → Skill("knowledge-ingest")
  Manage  → Skill("knowledge-manage")
  Organize→ Skill("knowledge-organize")
  Search  → Skill("knowledge-search")
  List    → Skill("knowledge-list")
  Verify  → Skill("knowledge-verify")
  Batch   → Skill("knowledge-batch")
  Mixed   → organize → verify → ingest → manage → list
```

## 关键改进点已到位

- ✅ Error Recovery Protocol：3 级降级（retry → fallback → report）
- ✅ Content-Hash Dedup：文件名 + 内容签名双重去重
- ✅ Orphan Tag Resolution：迂回迁移策略
- ✅ Partial Completion：不因部分失败回滚成功操作
- ✅ Audit Trail：批量操作自动写 changelog
- ✅ Health Scorecard：**/100 量化健康评分
- ✅ Multi-Scenario Dispatch：最优执行顺序
