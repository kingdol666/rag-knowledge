# Knowledge Skill System — 完全架构

## 当前 10 个 Skills 全景 + 2 个 Agent

```
knowledge-store (入口/调度器)
├── 触发词：knowledge base, KB, 知识库, 文档管理, store, parse, upload, import, 
│           organize, audit, search, find, list, merge, delete, 整理, 入库等
│
├── knowledge-ingest (入库)            A1→A8 + A0 去重 + A5b 智能分块
│   ├── 触发：store, upload, parse, import, save, ingest, 存入, 解析
│   └── 能力：内容哈希去重 → 领域分类 → KB匹配 → A4场景化描述 → 标签选择 → 智能分块 → 存储 → 验证
│
├── knowledge-manage (管理)            M1→M5 + B6 内容更新
│   ├── 触发：move, rename, delete, merge, update, 移动, 改名, 删除
│   └── 能力：移动/改名/删除/合并/内容更新 → 确认防误 → 验证
│
├── knowledge-organize (整理)          O1→O8 + 经验迁移(保留可信度)
│   ├── 触发：organize, audit, health check, restructure, 整理, 清洗
│   └── 能力：全盘调研(含经验) → 内容分类 → 合并(保留applied_count/rating) → 重命名 → 标签迁移 → 评分卡 → 大文档拆分
│
├── knowledge-search (智能检索)         6步Agentic RAG + 升级企业级路由
│   ├── 触发：search, find, query, ask, retrieve, what is, how to, explain, rag, 回答, 检索, 搜索, 问答, 查内容
│   ├── 能力：意图识别 → Catalog判断 → DocCatalog判断 → 经验优先(严格P0/P1/P2) → 向量确认 → 内容验证
│   └── 升级：跨库BM25盲区 → 自动路由 knowledge-search-enterprise
│   └── 新增：短文本过滤(<50 chars → P2), 经验可信度衰减
│
├── knowledge-search-enterprise (企业检索)  ← NEW
│   ├── 触发：跨库搜索<2个KB / 用户要求全库 / stage1候选<3
│   └── 能力：3路并行召回(Agentic+BM25+Vector) → 交叉验证去重 → 短文本过滤 → 内容重排序 → 融合展示
│
├── knowledge-list (浏览)              L1→L3 只读
│   ├── 触发：list, show, what KBs, overview, tree, 列, 查, 查看
│   └── 能力：完整清单 → KB 深入 → 树形浏览
│
├── knowledge-verify (校验)            V1→V6
│   ├── 触发：verify, validate, integrity, health check, quality audit, 校验, 完整性
│   └── 能力：元数据一致性 → 文档可用性 → 解析质量 → 修复(可选) → 评分卡
│
├── knowledge-batch (批量)             B1→B6
│   ├── 触发：batch, bulk, mass, all documents, every KB, 批量, 大规模
│   └── 能力：批量标签 → 批量描述 → 目录导入 → 批量移动 → 去重 → 导出报告
│
└── knowledge-experience (经验管理)
    ├── 触发：记录经验, 查经验, 评分, record experience, lesson learned, 经验教训
    └── 能力：创建 → 检索(严格P0/P1/P2, 短文本过滤, 可信度衰减) → 应用 → 评审 → 统计

Agents:
  ├── archival (knowledge-admin.md)    — 全栈KB管理员, 拥有全部~60个MCP工具
  └── [auto] knowledge-store dispatcher — 路由到 Archival
```
