# Knowledge Skill System — 完全架构

## 当前 12 个 Skills 全景 + 1 个 Agent

```
knowledgebase (入口/调度器)
├── 触发词：knowledge base, KB, 知识库, 文档管理, store, parse, upload, import, 
│           organize, audit, search, find, list, merge, delete, 整理, 入库等
│
├── knowledgebase-ingest (入库 + 子KB自动拆分)     A0→A10 ⭐最新优化
│   ├── 触发：store, upload, parse, import, save, ingest, 存入, 解析
│   └── 能力：A0去重 → A1调研 → A2领域分类(含子域) → A3分层KB匹配 → A4场景化描述(文档+KB+子KB) 
│             → A5标签 → A5b智能分块 → A6存储 → A7贴标 → A8验证 → A9子KB创建检查(阈值8-12文档自动拆)
│             → A10报告
│   ⭐ 核心创新：A9 子KB自动创建——当父KB ≥8 文档且跨≥2 子域，自动创建子KB并移动文档，
│      父KB description 自动更新引用。确保 Agent 读 description 能精确定位。
│
├── knowledgebase-manage (管理)            M1→M6
│   ├── 触发：move, rename, delete, merge, update, 移动, 改名, 删除
│   └── 能力：移动/改名/删除/合并/内容更新 → 确认防误 → 验证
│
├── knowledgebase-organize (整理 + 子KB健康)      O1→O10 ⭐新增O10
│   ├── 触发：organize, audit, health check, restructure, 整理, 清洗
│   └── 能力：O1全盘调研(含经验) → O2评估 → O3分类 → O4执行(保留经验可信度) → O5验证 
│             → O6孤儿清理 → O7评分卡 → O8标签规范 → O9大文档拆分
│   ⭐ O10 新增：分层KB健康检查——识别≥8文档且跨子域的父KB → 创建子KB；
│      检查单人子KB → 合并回父KB；验证子KB description 聚焦度
│
├── knowledgebase-search (智能检索 + 分层KB感知)   7步Agentic RAG ⭐新增Step1/5
│   ├── 触发：search, find, query, ask, retrieve, what is, how to, explain, rag, 回答, 检索, 搜索, 问答, 查内容
│   ├── 能力：Step0意图+子域识别 → Step1分层Catalog(子KB优先匹配) → Step2子KB内DocCatalog 
│             → Step3经验优先(严格P0/P1/P2) → Step4向量确认 → Step5子KB回溯(跨子KB横向)
│             → Step6内容验证 → Step7综合回答+层级检索路径
│   ⭐ 核心创新：子KB优先策略——子KB description 比父KB精确10倍；
│      Step5 跨子KB回溯用于横向比较（如振动分析横跨多个子KB）
│
├── knowledgebase-search-enterprise (企业检索)
│   ├── 触发：跨库搜索<2个KB / 用户要求全库 / stage1候选<3
│   ├── 能力：3路并行召回(Agentic+BM25+Vector) → 交叉验证去重 → 短文本过滤 → 内容重排序 → 融合展示
│   └── ⚠️ 子KB感知升级：企业级检索也优先从子KB description 判断，而非父KB
│
├── knowledgebase-list (浏览)              L1→L3 只读
│   ├── 触发：list, show, what KBs, overview, tree, 列, 查, 查看
│   ├── 能力：完整清单 + KB 深入 + 树形浏览
│   └── ⚠️ 分层KB展示：L1 展示时区分父/子，用缩进树结构
│
├── knowledgebase-verify (校验)            V1→V6
│   ├── 触发：verify, validate, integrity, health check, quality audit, 校验, 完整性
│   └── 能力：V1元数据 → V2文档完整性 → V3解析质量 → V4修复(可选) → V5评分卡 → V6报告
│       ⭐ V3 新增：子KB健康检查（父KB≥8无子KB=警告；单人子KB=警告；父子description一致=警告）
│
├── knowledgebase-batch (批量)             B1→B6
│   ├── 触发：batch, bulk, mass, all documents, every KB, 批量, 大规模
│   └── 能力：批量标签 → 批量描述 → 目录导入 → 批量移动 → 去重 → 导出报告
│
├── knowledgebase-experience (经验读/应用/评审)
│   ├── 触发：查经验, 评分, 应用经验, lesson learned, record experience, 经验教训
│   ├── 能力：检索(严格P0/P1/P2, 短文本过滤, 可信度衰减) → 应用 → 评审 → 统计
│   └── ⚠️ 与子KB交互：经验可关联子KB而非仅父KB
│
└── knowledgebase-experience-summarize (经验总结入库)   S1→S5
    ├── 触发：记录这个经验, 总结一下, 保存教训, 记住流程, 提炼成经验, save as experience, summarize as lesson
    ├── 来源：对话复盘(A) / 文档提炼(B) / 手工输入(C) / 经验迁移(D)
    └── 能力：场景诊断 → 智能提炼(LLM) → markdown模板展示 → 用户确认(硬门槛)
               → experience_create持久化 → experience_read验证

Agents:
  └── archival (knowledge-admin.md)    — 全栈KB管理员, 拥有全部~60个MCP工具
                                        ← knowledgebase dispatcher 路由到本 agent
```

## ⭐ 2026-07 优化要点（最新 v2）

### 1. 分层知识库（Hierarchical KB）
- **父KB** 覆盖大类（如 Thermal-Power-Monitoring），description 概述子领域和层级结构
- **子KB** 覆盖精确子域（如 Thermal-Power-Coal-Mill），description 精确描述设备+方法+场景
- **自动分裂阈值**：≥8 文档且跨≥2 子域 → Ingest A9 / Organize O10 自动创建子KB
- **子KB description 精确度提升 10x**：从"能源行业文档"→"煤磨机CNN-LSTM故障预警"
- **Search 优先匹配子KB**：Step 1 先扫子KB description，父KB作兜底

### 2. Ingest 流程强化（v2 核心）
- A2 加入子域分类（父域+子域双层）
- A3 子KB匹配优先（有parent_id的KB优先匹配）
- **A4-0 黄金法则（NEW）**：先读内容再写描述，禁止根据文件名猜测 description
- **A4-1 子Agent摘要流程（NEW）**：≥3篇文档时委托 general-purpose 子Agent 提取摘要 JSON，节省主上下文
- **A4d 读内容验证（NEW）**：description 写入后验证关键断言是否在真实内容中
- **A5b 智能拆分（MANDATORY）**：markdown_chars > 80000 或行数 > 2000 必须拆分
  - A5b-1 用 `grep -n "^# \|^## "` 提取章节标题+行号
  - A5b-3 用 `sed -n 'start,end p'` 精确提取章节内容（按行号，不按字符）
  - A5b-4 用 `kb_doc_create(content=章节文本)` 创建独立分块文档
  - A5b-6 验证全部成功后删除原始文档
- A6 改为 placeholder → 解析完成 → 读内容 → update_meta 真实描述
- A9 入库后自动评估是否需要创建子KB

### 3. Search 流程强化
- **Step 1 分层 Catalog**：子KB description 优先匹配
- **Step 5 子KB回溯**：跨子KB横向比较（如振动分析跨多个子KB）
- **分层描述呈现**：答案中标注检索路径（子KB→文档→片段）

### 4. Organize 强化（v2）
- O10a：识别子KB创建候选（≥8文档+≥2子域）
- O10b：子KB健康检查（单文档子KB、父子description一致等）
- **O2-E Description 真实性审计（NEW）**：遍历每个文档，验证 description 与内容一致性
  - 检测 placeholder（"Parsed from..."、空、test）
  - 检测关键断言 term-mismatch
  - 检测文件名 vs 真实标题不一致（如 metagpt_paper.md 实际是 Generative Agents）
  - 用子 Agent 批量修正，保持主上下文干净
- O9 大文档拆分规范同步 Ingest A5b

### 5. 已验证的真实可执行性（v2 实测）
- ✅ `grep -n` 在 7686 行博士论文上提取出 8 个 CHAPTER 边界
- ✅ `sed -n 'start,end p'` 精确提取 Chapter Five（1458行）完整内容
- ✅ `kb_doc_create(kb_id, name, content, description)` 工具签名确认
- ✅ `parse_doc` 非阻塞，返回 task_id 用于轮询
- ✅ `kb_doc_read` 支持 offset/limit 分页读取
- ✅ archival agent 拥有 Agent 工具，可调用 general-purpose 子Agent

---

## 旧版优化要点（2026-07 初版，已被 v2 覆盖）
