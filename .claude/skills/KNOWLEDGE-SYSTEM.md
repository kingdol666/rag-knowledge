# Knowledge Skill System — 完全架构

## 当前 12 个 Skills 全景 + 1 个 Agent

```
knowledgebase (入口/调度器)
├── 触发检测矩阵：20+ 中英文触发模式，覆盖所有知识库作业场景
├── 场景路由引擎：检测到 KB 触发词 → 自动判断具体场景 → 委托 Archival
├── 模糊决策：无明确匹配时用"Search / Ingest / List / 等待澄清"降级
│
├── knowledgebase-ingest (入库)              A0→A8
│   ├── 触发：入库, 上传, 解析, 导入, store, upload, parse, import, ingest, add doc (20+ 中英关键词)
│   └── 能力：A0去重 → A1调研 → A2领域分类(含子域) → A3分层KB匹配 → A4存储(按文件类型分流)
│             → A5标签 → A6验证(含向量索引+图谱构建) → A7子KB创建检查 → A8报告
│   ⭐ 核心原则：按文件类型分流——PDF/Word/图片走解析路径(3步:parse→create→index)，
│      MD/TXT/代码走直接路径(2步:create→index)。不拆分文档，整篇入库。
│
├── knowledgebase-manage (管理)            M1→M6
│   ├── 触发：移动, 改名, 删除, 合并, move, rename, delete, merge, update (15+ 中英关键词)
│   └── 能力：移动/改名/删除/合并/内容更新 → 确认防误 → 重建索引(如需) → 验证
│   ⭐ 所有操作原子化：一次调用同步 磁盘文件 + .tree-fs.json + .knowledge-base.yml
│
├── knowledgebase-organize (整理)          O1→O13
│   ├── 触发：整理, 清洗, 重组, 审计, organize, restructure, cleanup, audit (20+ 中英关键词)
│   └── 能力：O1全盘调研 → O2评估(含description审计) → O3分类 → O3b内容驱动重归类
│             → O4执行 → O5验证 → O6孤儿清理 → O7评分卡 → O8标签规范
│             → O9子KB自动创建 → O10 description批量修正 → O11向量索引覆盖率审计
│             → O12三层元数据一致性(磁盘↔.tree-fs.json↔.knowledge-base.yml) → O13图谱重建
│   ⭐ 不拆分文档——文档作为整体单元存储，向量索引在嵌入时内部处理分块
│
├── knowledgebase-search (智能检索)   7步Agentic RAG
│   ├── 触发：搜索, 查询, 问答, 检索, search, find, query, ask, RAG (20+ 中英关键词)
│   └── 能力：Step0意图 → Step1 KB Catalog → Step2 Doc Catalog → Step3经验优先
│             → Step4向量确认 → Step4.5图谱扩展(可选) → Step5子KB回溯 → Step6内容验证 → Step7综合回答
│
├── knowledgebase-search-enterprise (企业检索)
│   ├── 触发：全库搜索, 跨KB, cross-KB, all KBs, 全局搜索, 全面 (自动从 search 升级)
│   └── 能力：3路并行召回(Agentic+BM25+Vector) → 交叉验证去重 → 短文本过滤 → 内容重排序 → 融合展示
│
├── knowledgebase-list (浏览)              L1→L3 只读
│   ├── 触发：查看, 列出, 展示, 浏览, list, show, overview, tree (15+ 中英关键词)
│   └── 能力：完整清单 + KB 深入 + 树形浏览
│
├── knowledgebase-verify (校验)            V1→V6
│   ├── 触发：校验, 核对, 完整性, 健康检查, verify, validate, integrity (15+ 中英关键词)
│   └── 能力：V1三层元数据一致性 → V2文档完整性 → V3解析质量 → V4索引修复(可选) → V5评分卡 → V6报告
│
├── knowledgebase-batch (批量)             B1→B7
│   ├── 触发：批量, 所有文档, batch, bulk, mass, all documents (10+ 中英关键词)
│   └── 能力：批量标签 → 批量描述 → 目录导入(按文件类型分流) → 批量移动 → 去重 → 导出报告 → 图谱重建
│
├── knowledgebase-experience (经验读/应用/评审)
│   ├── 触发：查经验, 评分, 评审, experience, lesson learned, best practice (15+ 中英关键词)
│   └── 能力：检索(严格P0/P1/P2, 短文本过滤, 可信度衰减) → 应用 → 评审 → 统计
│
├── knowledgebase-experience-summarize (经验总结入库)   S1→S5
│   ├── 触发：记录经验, 总结一下, 保存教训, save experience, summarize lesson (15+ 中英关键词)
│   └── 能力：场景诊断 → 智能提炼(LLM) → markdown模板展示 → 用户确认 → experience_create持久化 → 验证
│
└── knowledgebase-graph (知识图谱)
    ├── 触发：图谱, 知识图谱, 构建图谱, graph, knowledge graph, neo4j, entity (20+ 中英关键词)
    └── 能力：G1构建(per-KB/all) → G2查询(文档视图/KB概览/实体搜索/邻居)
              → G3跨KB分析(桥梁文档/文档路径) → G4中心度 → G5清理(文档/KB级)

Agents:
  └── archival (knowledge-admin.md)    — 全栈KB管理员, 拥有全部~60个MCP工具
                                        ← knowledgebase dispatcher 路由到本 agent
```

## 核心架构原则

### 1. 三层元数据模型（始终同步）
每个文档操作同时更新三层：
- **磁盘文件** — 实际 `.md` 文件在 `web/storage/tree-file-system/{kb-name}/`
- **`.tree-fs.json`** — 全局文件树索引（所有文件夹+文件的 UUID、路径、元信息）
- **`.knowledge-base.yml`** — 每个KB的文档索引（name, description, path, tags, size, vector_index, graph_index）

所有 API 操作都是**原子化**的——一次调用同步所有三层。不需要手动同步元信息。

### 2. 文件类型路由（无文档拆分）
```
解析路径 (PDF/Word/Excel/PPTX/Images):
  parse_doc() → 轮询 parse_task_status() → kb_doc_create() → kb_index_document()
  3个独立原子步骤

直接路径 (MD/TXT/Code/JSON/YAML):
  kb_doc_create() → kb_index_document()
  2个独立原子步骤

二进制文件:
  fs_upload_file() — 仅元数据，无索引
```

**不拆分文档。** 文档作为整体单元存储，无论大小。向量索引在嵌入时内部处理分块。

### 3. 索引非自动触发
- `kb_doc_create` 不索引
- `kb_doc_update_content` 不重建索引
- `kb_doc_move` 不在新路径重建索引
- **必须显式调用** `kb_index_document()` / `kb_batch_index()` / `kb_reindex()`

### 4. 分层知识库（Hierarchical KB）
- **父KB** 覆盖大类，description 概述子领域
- **子KB** 覆盖精确子域，description 精确描述
- **自动创建阈值**：≥8 文档且跨≥2 子域 → Ingest A7 / Organize O9 自动创建子KB
- **Search 优先匹配子KB**：Step 1 先扫子KB description

---

## ⚡ 知识库 Skill 触发策略

### 核心原则

**任意用户请求中一旦包含知识库相关的触发词，必须优先考虑路由到 knowledgebase 调度器。**
"先判断是否 KB 作业，再判断具体场景"——而不是让通用技能抢占。

### 三层触发检测

```
Layer 1 — 主调度器 (knowledgebase/SKILL.md)
├── frontmatter description 含 50+ 中英触发词
├── 触发检测矩阵：11 个场景 × 每场景 10-20 个关键词
├── 模糊决策：Search / Ingest / List / 等待澄清 降级
│
Layer 2 — 各子 Skill frontmatter description
├── 每个子 Skill 的 description 末尾标注 Trigger keywords
├── 供宿主系统识别触发场景
│
Layer 3 — KNOWLEDGE-SYSTEM.md 全局触发文档
├── 本文件：所有触发模式的完整索引
├── Archival agent 内部场景诊断表单
```

### 场景路由优先级（多场景混合作业）

```
用户请求 → 命中 KB 触发词？
  │
  是 → 调用 knowledgebase skill
  │    ↓
  │  主调度器检测触发矩阵 → 获取场景标签
  │    ↓
  │  Agent(subagent_type="archival",
  │       prompt="[Detected scenario: <场景标签>] ...")
  │    ↓
  │  Archival Step 0: 场景诊断协议（自主确认/重判）
  │    ↓
  │  路由到子 Skill 执行
  │
  否 → 正常任务处理
```

### 各子 Skill 触发词速查

| Skill | 触发关键词（中文） | 触发关键词（英文） |
|-------|-----------------|-----------------|
| **ingest** | 入库, 上传, 导入, 解析, 存储, 保存到, 放文档, 添加 | store, upload, import, parse, ingest, save, add doc |
| **manage** | 移动, 改名, 重命名, 删除文档, 删除KB, 合并, 修改 | move, rename, delete, merge, update content |
| **organize** | 整理, 清洗, 重组, 审计, 盘点, 大扫除, 重建索引 | organize, restructure, audit, cleanup, reorganize |
| **search** | 搜索, 查询, 问答, 检索, 搜, 帮我查, 问一下 | search, find, query, ask, retrieve, RAG |
| **search-enterprise** | 全库搜索, 跨库, 全局搜索, 联表 | cross-KB, all KBs, enterprise search, comprehensive |
| **list** | 查看, 列出, 展示, 浏览, 有什么 | list, show, overview, tree, browse |
| **verify** | 校验, 核对, 完整性, 检查, 一致性 | verify, validate, integrity, health check |
| **batch** | 批量, 所有文档, 全量, 统一 | batch, bulk, mass, all, repetitive |
| **experience** | 查经验, 评分, 评审, 经验教训, 怎么处理 | experience, lesson, review, best practice |
| **experience-summarize** | 记录经验, 总结, 复盘, 记住流程 | save experience, summarize lesson, record workflow |
| **graph** | 图谱, 知识图谱, 构建图谱, 重建图谱, 实体关系 | graph, knowledge graph, neo4j, entity, build graph |

### 执行保障

1. **触发不是可选的**——命中触发词必须路由，不能绕过
2. **场景不是猜测的**——用检测矩阵判断，不是"感觉"
3. **子 Skill 不是跳过可省略的**——路由后严格按子 Skill 的步骤执行
4. **Archival 不是可选的**——所有 KB 操作必须经 Archival agent 执行
5. **操作完成后验证**——按各自 Skill 的 verify 步骤验证结果
6. **索引必须显式触发**——创建/更新/移动文档后必须调用 kb_index_document
