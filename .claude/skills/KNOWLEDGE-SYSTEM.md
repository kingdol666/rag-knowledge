# Knowledge Skill System — 完全架构

## 当前 12 个 Skills 全景 + 1 个 Agent

```
knowledgebase (入口/调度器)
├── 触发检测矩阵：20+ 中英文触发模式，覆盖所有知识库作业场景 ⭐ 增强
├── 场景路由引擎：检测到 KB 触发词 → 自动判断具体场景 → 委托 Archival
├── 模糊决策：无明确匹配时用"Search / Ingest / List / 等待澄清"降级
│
├── knowledgebase-ingest (入库 + 子KB自动拆分)     A0→A10 ⭐最新优化
│   ├── 触发：入库, 上传, 解析, 导入, store, upload, parse, import, ingest, add doc (20+ 中英关键词)
│   └── 能力：A0去重 → A1调研 → A2领域分类(含子域) → A3分层KB匹配 → A4场景化描述(文档+KB+子KB) 
│             → A5标签 → A5b智能分块 → A6存储 → A7贴标 → A8验证 → A9子KB创建检查(阈值8-12文档自动拆)
│             → A10报告
│   ⭐ 核心创新：A9 子KB自动创建——当父KB ≥8 文档且跨≥2 子域，自动创建子KB并移动文档，
│      父KB description 自动更新引用。确保 Agent 读 description 能精确定位。
│
├── knowledgebase-manage (管理)            M1→M6
│   ├── 触发：移动, 改名, 删除, 合并, move, rename, delete, merge, update (15+ 中英关键词)
│   └── 能力：移动/改名/删除/合并/内容更新 → 确认防误 → 验证
│
├── knowledgebase-organize (整理 + 子KB健康)      O1→O13 ⭐v4 新增 O12/O13
│   ├── 触发：整理, 清洗, 重组, 审计, organize, restructure, cleanup, audit (20+ 中英关键词)
│   └── 能力：O1全盘调研(含经验) → O2评估 → O3分类 → O4执行(保留经验可信度) → O5验证 
│             → O6孤儿清理 → O7评分卡 → O8标签规范 → O9大文档拆分
│   ⭐ O10 新增：分层KB健康检查——识别≥8文档且跨子域的父KB → 创建子KB；
│      检查单人子KB → 合并回父KB；验证子KB description 聚焦度
│
├── knowledgebase-search (智能检索)   7步Agentic RAG
│   ├── 触发：搜索, 查询, 问答, 检索, search, find, query, ask, RAG (20+ 中英关键词)
│   ├── 能力：Step0意图+子域识别 → Step1分层Catalog(子KB优先匹配) → Step2子KB内DocCatalog 
│             → Step3经验优先(严格P0/P1/P2) → Step4向量确认 → Step5子KB回溯(跨子KB横向)
│             → Step6内容验证 → Step7综合回答+层级检索路径
│   ⭐ 核心创新：子KB优先策略——子KB description 比父KB精确10倍；
│      Step5 跨子KB回溯用于横向比较（如振动分析横跨多个子KB）
│
├── knowledgebase-search-enterprise (企业检索)
│   ├── 触发：全库搜索, 跨KB, cross-KB, all KBs, 全局搜索, 全面 (自动从 search 升级)
│   ├── 能力：3路并行召回(Agentic+BM25+Vector) → 交叉验证去重 → 短文本过滤 → 内容重排序 → 融合展示
│   └── ⚠️ 子KB感知升级：企业级检索也优先从子KB description 判断，而非父KB
│
├── knowledgebase-list (浏览)              L1→L3 只读
│   ├── 触发：查看, 列出, 展示, 浏览, list, show, overview, tree (15+ 中英关键词)
│   ├── 能力：完整清单 + KB 深入 + 树形浏览
│   └── ⚠️ 分层KB展示：L1 展示时区分父/子，用缩进树结构
│
├── knowledgebase-verify (校验)            V1→V6
│   ├── 触发：校验, 核对, 完整性, 健康检查, verify, validate, integrity (15+ 中英关键词)
│   └── 能力：V1元数据 → V2文档完整性 → V3解析质量 → V4修复(可选) → V5评分卡 → V6报告
│       ⭐ V3 新增：子KB健康检查（父KB≥8无子KB=警告；单人子KB=警告；父子description一致=警告）
│
├── knowledgebase-batch (批量)             B1→B6
│   ├── 触发：批量, 所有文档, batch, bulk, mass, all documents (10+ 中英关键词)
│   └── 能力：批量标签 → 批量描述 → 目录导入 → 批量移动 → 去重 → 导出报告
│
├── knowledgebase-experience (经验读/应用/评审)
│   ├── 触发：查经验, 评分, 评审, experience, lesson learned, best practice (15+ 中英关键词)
│   ├── 能力：检索(严格P0/P1/P2, 短文本过滤, 可信度衰减) → 应用 → 评审 → 统计
│   └── ⚠️ 与子KB交互：经验可关联子KB而非仅父KB
│
└── knowledgebase-experience-summarize (经验总结入库)   S1→S5
    ├── 触发：记录经验, 总结一下, 保存教训, save experience, summarize lesson (15+ 中英关键词)
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

### 4. Organize 强化（v4 最新）
- O1 全盘调研 → O2 评估 → **O2-E description 真实性审计**
- **O3-Auto 空KB自动处理** — 区分父容器空KB（保留）vs 孤儿空KB（自动删除）
- **O3b 内容驱动文档重归类（v3）** ⭐ — 读真实内容，移动到正确KB
- O4 执行（合并/移动/删除/重命名，保留经验可信度）
- O5 验证 → O6 孤儿清理 → O7 评分卡 → O8 标签规范 → O9 大文档拆分
- **O10 子KB自动创建（强化 v3）** ⭐ — 阈值降低：≥5文档+≥3子域 / ≥500KB / ≥10文档
- **O11 Description 批量修正执行（v3）** ⭐⭐ — O2-E 检测→子Agent重写→O11e 三重验证
- **O12 向量索引覆盖率审计（v4 NEW）** ⭐ — 检测未索引文档 + kb_batch_index 补索引 +
  清理孤儿 collection（向量有chunks但KB无文档）
- **O13 YAML/JSON 冗余清理（v4 NEW）** ⭐⭐ — 四向一致性（磁盘↔YAML↔JSON↔向量库）：
  - O13b 孤儿条目清理（YAML有/磁盘无，kb_doc_move残留）
  - O13c 父KB污染清理（父YAML含子KB文档，实测 Academic-AI-Survey 12个污染）
  - O13d 缺失条目补充（磁盘有/YAML无）
  - O13e .tree-fs.json 一致性修复
  - O13f 悬空向量索引修复
  - 用 Python `yaml.safe_load + pathlib.exists()` 直接操作 YAML（MCP工具无法删孤儿）

### 5. 已验证的真实可执行性（v2 实测）
- ✅ `grep -n` 在 7686 行博士论文上提取出 8 个 CHAPTER 边界
- ✅ `sed -n 'start,end p'` 精确提取 Chapter Five（1458行）完整内容
- ✅ `kb_doc_create(kb_id, name, content, description)` 工具签名确认
- ✅ `parse_doc` 非阻塞，返回 task_id 用于轮询
- ✅ `kb_doc_read` 支持 offset/limit 分页读取
- ✅ archival agent 拥有 Agent 工具，可调用 general-purpose 子Agent

---

## 旧版优化要点（2026-07 初版，已被 v2 覆盖）

---

## ⚡ 增强版：知识库 Skill 触发策略（v2 版）

### 核心原则

**任意用户请求中一旦包含知识库相关的触发词，必须优先考虑路由到 knowledgebase 调度器。**
"先判断是否 KB 作业，再判断具体场景"——而不是让通用技能抢占。

### 三层触发检测

```
Layer 1 — 主调度器 (knowledgebase/SKILL.md)
├── frontmatter description 含 50+ 中英触发词
├── 触发检测矩阵：10 个场景 × 每场景 10-20 个关键词
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

### 执行保障

1. **触发不是可选的**——命中触发词必须路由，不能绕过
2. **场景不是猜测的**——用检测矩阵判断，不是"感觉"
3. **子 Skill 不是跳过可省略的**——路由后严格按子 Skill 的步骤执行
4. **Archival 不是可选的**——所有 KB 操作必须经 Archival agent 执行
5. **前 flaged 后验证**——操作完成后按各自 Skill 的 verify 步骤验证结果
