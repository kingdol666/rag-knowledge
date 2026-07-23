---
name: knowledgebase-ingest
description: Document ingestion pipeline with quality gates A0→A9. Content-first workflow: dedup (content fingerprint), survey, parse with quality check, structured analysis, tag quality gate (blocklist+normalize+verify), description quality gate (4-elements+content-readback), KB-attribution decision tree (sub-KB first), store by file type, index+tag with post-index verification. No document splitting. Triggered by: 入库, 上传, 导入, 存储, 解析, 解析PDF, 保存到, store, upload, import, parse, save to KB, ingest, 入库文档, 上传文档, 存入知识库, 放文档, 添加文档, add doc, put document.
---

# Knowledge Ingest — 内容驱动的规范入库流水线
> **⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型+一致性不变量+76工具地图）


**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**
- Archival 禁止：跳过步骤、绕过门控、用错存储工具

---

## ⭐ Pre-Flight — MCP 连通性 + 项目服务预检（强制，所有作业的第一步）

> 完整规则与边界情况见 [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md)。本预检早于本 skill 的所有编号步骤（A0/Step 0/Step 1…）。

**未通过预检，禁止开始后续步骤。**

1. **一探双检** — 调用 `mcp__kb-mcp__kb_project_status`：调用成功即证明 MCP 已连接，按 `ready` 分支（`ready==true` ⇔ backend+web 双健康）；报 "No such tool" → 走 Case C。
2. **分支处置**：
   - **Case A `ready==true`** → 就绪。
   - **Case B `ready==false`** → 先 `kb_project_preflight`（未安装则报 `problems`+`ragctl setup` 让用户处理并停止）；已安装则静默 `kb_project_start(backend=true, web=true[, neo4j=true], wait=true)`（图谱/整理/跨库类加 `neo4j=true`），回查 `ready==true` 才继续，否则读 `ragctl logs backend` 报错停止。
   - **Case C MCP 未连接** → 会话内无法自愈（MCP 由 Claude Code 启动加载）；`node command/ragctl.js status` 诊断并通知用户重启 Claude Code；**禁止**未连通硬跑操作（HTTP 兜底须用户明确同意）。
3. **冒烟测试** — `ready==true` 后正式操作前先做一次轻量只读往返（`kb_catalog()` / `kb_tags_list()`），确认 MCP↔backend 返回真实数据再作业。

---

**Freedom Map**（每步自由度）：
| 步骤 | 自由度 | 说明 |
|------|--------|------|
| A0 去重 / A2-Q 解析质量 / A3b 标签 / A3c 描述 / A5 存储 / A6-V 索引验证 | 🔒 **强制**（低自由度） | 质量门控，必须严格执行，不可跳过或变通 |
| A1 调研 / A3 内容分析 | 🎯 **执行**（中自由度） | 按流程读内容，分析结果用于后续决策 |
| A3d KB归属 / A8 子KB评估 | 🧠 **判断**（高自由度） | 需基于内容的领域判断，决策树指导但不机械 |

**四条铁律**：
1. **整篇存储**——单文档作为完整单元，绝不截断/摘要/拆分。
2. **内容驱动**——所有决策（KB 归属、标签、描述）基于读过的真实正文，非文件名/猜测。
3. **质量门控**——A2 解析质量 / A3b 标签 / A3c 描述 三道门，任一不过即返工，不放行。
4. ⭐ **MCP 优先原则**——所有操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`）。

---

## 思维框架：入库前想清楚三件事 ⭐

1. **这是什么文件？** — 解析型（PDF/Office/图片）还是直接型（MD/TXT/代码）？路由到不同工具链。
2. **放哪个 KB？** — 根据内容领域，不是文件名。子KB优先，父KB第二，新建第三（A3d决策树）。
3. **质量门控过了吗？** — 不乱码？标签归一化？描述四要素？不过就返工，不妥协入库。

---

## A0 — 去重（内容指纹，不只是文件名）

```
# 第一道：文件名 + 元数据
kb_search(query="<filename without ext>", top_k=5)

# 第二道：内容指纹（防"改名重复入库"）
kb_search_vector(query="<正文前 500 chars 改写为陈述句>", top_k=5, score_threshold=0.8)
```
- 文件名命中 + 文件大小相近(±10%) → 读 500 chars 二次确认 → **重复则跳过**，报告"已存在 @ <path>"。
- 向量命中 score ≥ 0.85 → **极可能重复**，读两篇前 800 chars 对比 → 重复跳过，仅补标签/描述差异。
- **不重复** → 进入 A1。

## A1 — 调研（全库现状）

```
kb_list()                    # 所有 KB（含 UUID + description + doc_count）
kb_tags_list()               # 标签词表（A3b 归一化用，≥90% 复用目标）
fs_get_tree(max_depth=3)     # KB 层级结构（子KB 可见）
```

## A2 — 获取内容 + 解析质量检测

### 获取路径选择
| 类型 | 路径 | 工具 |
|---|---|---|
| PDF/Word/Excel/PPTX/图片 | 解析路径 | `parse_doc` / `parse_doc_batch` |
| MD/TXT/Code/JSON/YAML | 直接路径 | 直接读文件 |
| 二进制(非文本) | 元数据路径 | `fs_upload_file`（不索引，仅存储）|

### 解析路径
```
parse_doc(file_path="<abs_path>", use_ocr=true)   # 非阻塞，返回 task_id
# 轮询直到完成：
parse_task_status(task_id) → {markdown, markdown_path, images_dir, image_count}
```
≥3 文件用 `parse_doc_batch(file_paths=[...], use_ocr=true)`——单 task_id 统一管理。

### ⚠️ A2-Q 解析质量门控（拒绝垃圾入库）
对解析产出的 markdown 前 1500 chars 检测，**任一命中即拒绝并报告**（不进入 A3）：

| 病症 | 检测 | 处置 |
|---|---|---|
| **OCR 垃圾** | 乱码率 >30%（非 ASCII/非中文占比异常）| 重新解析，换 OCR 模式 |
| **二进制残留** | 正文含大量 `\x00`/base64 片段 | 源文件可能损坏，报告用户 |
| **标题无正文** | 全文仅 `#` 标题 + ≤200 chars 正文 | 解析失败，重试或报告 |
| **空白过多** | 连续 >50 空行或正文 <100 chars | 视为解析失败 |
| **语言错配** | 中文 PDF 解析出全英文乱码 | 编码/OCR 问题，重试 |

## A3 — 结构化内容分析

读 3000 chars 采样，输出结构化结果（**这是后续所有决策的依据**）：

```json
{
  "title": "真实标题（取自正文 H1，非文件名）",
  "domain": "主领域（如 高分子材料 / AI / 能源）",
  "sub_domain": "子领域（如 PET双向拉伸 / RAG / 锂电池）",
  "methods": ["具体方法/模型/工艺"],
  "materials": ["具体材料/设备/数据集"],
  "scenario": "解决的问题/适用场景",
  "key_findings": ["关键数据/结论"],
  "language": "zh|en|mixed",
  "raw_tags": ["从内容提炼的 5-8 个候选领域词（未经 A3b 清洗）"],
  "target_kb_decision": "见 A3d 决策树"
}
```

**≥3 文档 或 单文档 >50KB**：委托子 Agent 分析，传入内容采样 + KB 列表 + 标签词表，按 [description-guide.md D5](references/description-guide.md) 契约验收。

## A3b — 标签质量门控 ⭐

对 A3 的 `raw_tags` 执行清洗，**严禁跳过**。完整规则见 [tag-quality-rules.md](references/tag-quality-rules.md)。

```
1. T1 黑名单过滤 → 丢弃章节标题("Abstract"/"1 Introduction"/"References")/测试标签(test-*)/描述性标签
2. T2 归一化    → 大小写统一(pet→PET) + 中英同义合并(聚乙烯/PE 取词表已有者)
3. T3 数量裁剪  → 保留 2-5 个：材料词 + 方法词 + 场景词 (+ 0-2 属性)
4. 词表比对    → ≥90% 复用 kb_tags_list() 既有词；新词仅限全新概念
5. 正文回查    → 每个标签在 ≥2000 chars 采样里真实出现
```
**不达标 → 返回 A3 重新提炼，不放行 A5。**

## A3c — 描述质量门控 ⭐

按 [description-guide.md](references/description-guide.md) 写描述，**强制四要素 + 内容回查**：

```
描述 = [主体] + [方法/技术] + [场景/问题] + [关键数据/结论] + [语言]
```
- **四要素至少含 2 个具体名词**（方法名/材料名/设备名/数据集）——禁止"一篇关于X的论文"式泛泛。
- **写完必须回查**：`kb_doc_read(..., max_chars=800)` 核对描述里每个关键 claim 在正文真实出现。
- **不匹配 → 重写描述**（不改正文迁就描述）。

✅ "基于 CNN-LSTM 的磨煤机堵管预警，DCS 历史数据训练，660MW 机组实测提前 315min 预警。中文。"
❌ "磨煤机论文" / "Parsed from xxx.pdf" / "test" / "高分子研究"

## A3d — KB 归属决策树 ⭐（确保"放对位置"）

按优先级判定 target KB（**这是入库质量的核心**）：

```
① 子KB 精确匹配？
   读 A1 的 fs_get_tree，找 description 与本文档 sub_domain 高度契合的【子KB】
   → 命中：target = 该子KB（✅ 最佳）

② 父KB 领域匹配 + 尚无合适子KB？
   父KB 的 domain 与文档一致，但无精确子KB
   → 命中：target = 父KB，记录"未来可能需建子KB"（A8 评估）

③ 完全无匹配？
   → kb_create(name="<Domain>-<SubDomain>", description=按 D3 模板, parent_id="<父KB 或空>")
   → 新建时 description 必须达标（A3c），不可"待补"
```

**误归判定检测**：判定后，将 target KB 的 description 与文档 `sub_domain + methods` 比对——领域明显冲突（如把 RAG 文档归到"高分子库"）→ 重新走决策树。

## A4 — 找/建 KB（执行 A3d 决策）

- **匹配既有 KB**：用其 UUID。
- **新建**：`kb_create(name, description, parent_id)`，description 按 [D3 KB 级模板](references/description-guide.md)。
- **新建子KB**：`parent_id` 指向父 KB 的 `kb_id`。

## A5 — 存储文档（按路径分流，整篇不截断）

### 解析路径 — `kb_doc_save_parsed`（存完整内容 + 图片）⭐
```
save = kb_doc_save_parsed(
    parent_id=target_kb_id,
    task_id="<A2 的 task_id>",     # 自动提取完整 markdown + images_dir
    description=A3c 产出的合格描述
)
```
⚠️ **参数是 `parent_id`，不是 `kb_id`**（与多数工具命名不同；传 `kb_id` 会被 schema 拒绝）。推荐 **`task_id` 模式**：传 A2 的 task_id 即自动提取完整 markdown + images_dir，无需手动拼 markdown_path。
自动：完整 markdown 落盘 + 所有图片复制到 KB `images/` + 原子更新 `.tree-fs.json` + `.knowledge-base.yml`。

**绝不用 `kb_doc_create` 存解析文档**——它截断内容且丢图片。

### 直接路径 — `kb_doc_create`
```
kb_doc_create(kb_id=target_kb_id, name="doc.md", content=完整文件内容, description=A3c描述)
```

## A6 — 索引 + 图谱 + 打标 + 索引后验证 ⭐

### A6a 索引（向量 + BM25）
```
idx = kb_index_document(kb_id=target_kb_id, doc_path=doc_path)
```
返回 `{vector_index: {collection, total_chunks, graph_doc_id}, graph_stats}`。

### A6b 知识图谱构建（向量索引后立即执行）⭐
```
kb_graph_build(kb_id=target_kb_id, force=true)
```
> ⚠️ **已知问题**：`kb_graph_build` 返回的 `total_relations` 可能为 0（stats 统计 bug），**这不代表构建失败**。实际数据已写入 Neo4j。务必用 `kb_graph_document()` 抽检验证而非依赖返回值。

构建后验证：
```
kb_graph_document(doc_path=doc_path)  # 确认图谱中有该文档节点
```

### A6c 打标（A3b 清洗后的合格标签）
```
kb_doc_update_tags(kb_id=target_kb_id, doc_path=doc_path, tags=A3b 清洗后标签)
```

### A6-V 索引后验证（必做）
```
# 1. vector_index 已写入？
确认 vector_index.collection 非空
# 2. collection UUID 正确？
应为 "kb_<target_kb_uuid>"——指向其他 UUID 说明落到孤儿 collection
# 3. chunk 数合理？
total_chunks ≥ 1
# 4. 图谱构建成功？
kb_graph_document(doc_path) 返回含实体
```

## A7 — 终检 Checklist（全部 ✅ 才算入库完成）

| # | 检查项 | 工具 | 达标 |
|---|---|---|---|
| C1 | 内容完整未截断 | `kb_doc_read(max_chars=500)` | 正文与 A3 采样一致 |
| C2 | 描述达标 | 读 description | 含四要素、内容回查通过 |
| C3 | 标签达标 | 读 tags | 2-5 个、无黑名单、无同义重复 |
| C4 | KB 归属正确 | doc sub_domain vs KB description | 领域一致 |
| C5 | 向量索引就绪 | vector_index 字段 | 非空、collection 正确 |
| C6 | 图片完整（解析路径）| image_count 对比 | 与 parse 结果一致 |
| C7 | 图谱索引就绪 | `kb_graph_document(doc_path)` | 图谱中查到该文档 |
| C8 | 三层元数据一致 | `.tree-fs.json` ↔ `.knowledge-base.yml` ↔ 磁盘 | 三处都有该文档 |

**任一 ✗ → 返工对应步骤，禁止"先入库后补"。**

### A7-E — 经验提取（可选，入库后丰富经验库）
入库终检通过后，如有余力可触发经验扫描：
```
experience_extract(kb_id=target_kb_id, mode="prepare")  # ⚠️ prepare 模式不支持 dry_run，始终返回 LLM 任务包
→ Agent LLM 精炼 → confidence≥0.8 直接 approved，<0.8 进草稿池
```
非强制步骤，但推荐在 KB 完整性和时效性要求高的场景执行。

## A8 — 子KB 评估 + 孤儿清理

- **子KB 自动创建**：父KB 达 `SUB_KB_AUTO_SPLIT_THRESHOLD`（**≥8 文档 且跨 ≥2 子域**）→ 按 [sub-kb-creation.md](references/sub-kb-creation.md) 拆分。阈值定义见该文件顶部权威源表。
- **孤儿清理**（入库时顺便）：`doc_count=0` 且 description 空洞的 KB → 报告用户是否删除。**不擅自删除**。

## A9 — 入库报告
```
✅ <filename> → <target KB 完整路径>
   类型: PDF(解析) | 标题: <真实标题>
   描述: <合格描述前 80 chars>...
   标签: [tag1, tag2, tag3] (A3b 清洗后)
   索引: vector=<collection> chunks=<n> | graph=<entities>e/<relations>r
   去重: 未发现重复 / 已跳过(重复于 <path>)
   终检: C1-C8 全 ✅
```

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 跳过 A0 去重 | 改名重复入库 | 文件名+指纹双通道去重 |
| 不测 A2-Q 质量门控 | OCR 垃圾入库 | A2 后用门控逐项检查 |
| `kb_doc_create` 存解析文档 | 截断内容丢图片 | 解析文档必须 `kb_doc_save_parsed` |
| 标签不经过 A3b | 章节标题/黑标签入库 | 黑名单过滤+归一化+数量裁剪 |
| 描述不过 A3c | 文件名当描述 | 四要素+内容回查 |
| 索引后不验证 collection | 落到孤儿 collection | A6-V 验证 UUID+chunks |
| 质量不过继续入库 | 垃圾进垃圾出 | 任一 C1-C8 ✗ 返工 |
| "先入库后补" | 永远不补 | 终检 C1-C8 全 ✅ 才算完成 |
| 入库后不触发经验提取 | 文档蕴含的经验因子流失 | A7-E 可选自动提取 |

## 工具速查
- `parse_doc(file_path, use_ocr=true)` / `parse_doc_batch(file_paths, use_ocr=true)` — 非阻塞解析
- `parse_task_status(task_id)` — 轮询解析结果
- `kb_doc_save_parsed(parent_id, task_id, description)` — ⭐ 解析路径存完整内容+图片
- `kb_doc_create(kb_id, name, content, description)` — 直接路径/内存文档
- `kb_index_document(kb_id, doc_path)` — 向量+图谱+BM25 索引
- `kb_doc_update_tags(kb_id, doc_path, tags)` — 打标（A3b 清洗后）
- `kb_doc_read(kb_id, doc_path, max_chars)` — 读正文（A3/A3c/C1 用）
- `kb_search_vector(query, top_k, score_threshold)` — A0 内容指纹判重
- `kb_search(query, top_k)` — A0 文件名判重
- `kb_create(name, description, parent_id)` — 建 KB/子KB
- `kb_tags_list()` — A3b 词表比对
- `fs_upload_file(file_path, parent_id, description)` — 二进制上传
