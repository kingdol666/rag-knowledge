# RAG Knowledge Platform — 开发计划与功能扩展指南

> 本文档记录当前系统的真实实现状态、待完善功能、以及后续如何追加新功能。
> 最后更新：2026-07-02（已对照源码核验）

---

## 目录

- [一、项目整体架构](#一项目整体架构)
- [二、已实现功能清单（源码核验）](#二已实现功能清单源码核验)
- [三、待完善与已知缺口](#三待完善与已知缺口)
- [四、后续功能规划](#四后续功能规划)
- [五、如何追加新功能（开发指南）](#五如何追加新功能开发指南)
- [六、里程碑路线图](#六里程碑路线图)
- [七、应保留的设计优势](#七应保留的设计优势)

---

## 一、项目整体架构

### 1.1 四层分层

```text
┌──────────────────────────────────────────────────────────┐
│  Layer 4: Claude Code Skill 层（.claude/skills/）        │
│  8 个 skill + Archival 调度 Agent                         │
│  职责：Agentic 知识治理（入库/整理/校验/搜索/批量）        │
└────────────────────────┬─────────────────────────────────┘
                         │ stdio / MCP
┌────────────────────────▼─────────────────────────────────┐
│  Layer 3: MCP 工具层（kb-mcp/server.py）                  │
│  33 个 MCP 工具                                           │
│  职责：把后端能力封装成 Agent 可调用的标准接口              │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼─────────────────────────────────┐
│  Layer 2: Web 代理层 + Web UI（web/）                     │
│  Nuxt 3 + Ant Design Vue                                 │
│  职责：页面交互 + server route 代理后端                    │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼─────────────────────────────────┐
│  Layer 1: 后端服务层（backend/）                          │
│  FastAPI + MinerU                                        │
│  职责：解析、索引、检索、图谱、配置                        │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  Layer 0: 存储层                                          │
│  文件系统 + .tree-fs.json + .knowledge-base.yml          │
│  ChromaDB（向量）+ Neo4j（图谱）+ models_cache            │
└──────────────────────────────────────────────────────────┘
```

### 1.2 核心数据流

```text
PDF 上传 → MinerU 解析 → Markdown 落盘
        → 更新 .tree-fs.json + .knowledge-base.yml + tags
        → （手动）建立向量索引 + 知识图谱
        → 检索（关键词 / 向量 / 两阶段 / 图谱）
        → 返回结果 + 来源文档路径
```

### 1.3 两层切分机制（重要，易混淆）

系统存在**两层不同的文本切分**，不要混淆：

| 层级           | 位置                                                         | 机制                                                                   | 作用                                 |
| -------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- | ------------------------------------ |
| **文档级切分** | Skill 层（`knowledge-ingest` A5b / `knowledge-organize` O8） | 按 Markdown `#`/`##` 标题拆分大文档为多个小文档                        | 防止单文档过大，提升可读性和管理粒度 |
| **向量级切分** | 后端 `vector_service.py` `_chunk_text()`                     | 先按 `#` 标题分段，超长段再按 `chunk_size`(500) + `overlap`(50) 字符切 | 生成 Embedding 的输入单元            |

> **核验结论**：后端向量切分**已经是语义感知的**（按 Markdown 标题分段），并非纯固定长度。只有当某个 section 超过 500 字符时才会做字符级切分。提升空间在于：超长 section 的字符级切分可以改为按句子边界。

---

## 二、已实现功能清单（源码核验）

### 2.1 后端（backend/）

#### PDF 解析

| 功能                   | 端点                                      | 状态 |
| ---------------------- | ----------------------------------------- | ---- |
| 单文件异步解析         | `POST /api/v1/parse/file/vt`              | ✅   |
| 单文件同步解析（兼容） | `POST /api/v1/parse/file/vt/legacy`       | ✅   |
| 批量解析（JSON）       | `POST /api/v1/batch/parse/file/vt`        | ✅   |
| 批量解析（SSE 流）     | `POST /api/v1/batch/parse/file/vt/stream` | ✅   |
| MinerU 状态查询        | `GET /api/v1/mineru/status`               | ✅   |
| MinerU 重启            | `POST /api/v1/mineru/restart`             | ✅   |

- MinerU 由后端自动管理生命周期（Windows Job Object 绑定，进程崩溃连带清理）
- 自动挑选空闲端口，避免端口冲突
- 后端退出时自动终止 MinerU 子进程

#### 检索（多信号）

| 功能                                     | 端点                                 | 状态 |
| ---------------------------------------- | ------------------------------------ | ---- |
| 关键词搜索（BM25 + jieba）               | `GET /api/v1/search/`                | ✅   |
| 向量语义搜索（BGE-M3 + ChromaDB）        | `POST /api/v1/search/vector`         | ✅   |
| 批量向量搜索                             | `POST /api/v1/search/batch-vector`   | ✅   |
| 两阶段检索（BM25 + 图谱扩展 → 向量精筛） | `POST /api/v1/search/two-stage`      | ✅   |
| 单文档索引                               | `POST /api/v1/search/index-document` | ✅   |
| 批量索引                                 | `POST /api/v1/search/batch-index`    | ✅   |
| 全库/单库重建索引                        | `POST /api/v1/search/reindex`        | ✅   |
| 索引统计                                 | `GET /api/v1/search/stats`           | ✅   |
| 路径调试                                 | `GET /api/v1/search/debug-paths`     | ✅   |

#### 知识图谱（Neo4j）

| 功能                     | 端点                                    | 状态 |
| ------------------------ | --------------------------------------- | ---- |
| 图谱统计                 | `GET /api/v1/graph/stats`               | ✅   |
| 实体搜索                 | `GET /api/v1/graph/search`              | ✅   |
| 实体邻居查询（深度 1-3） | `GET /api/v1/graph/neighbors`           | ✅   |
| 按实体查关联文档         | `GET /api/v1/graph/documents-by-entity` | ✅   |

- NER：HanLP `MSRA_NER_BERT_BASE_ZH`（文本超 50k 字截断）
- 关系抽取：共现 + 依存句法（`CTB5_DEP_ELECTRA_SMALL`）+ 8 条正则模板（子公司/收购/投资/属于/位于/成立时间/签订/支付），**不依赖 LLM**

#### 服务层能力

| 服务            | 文件                                   | 状态 | 关键实现细节                                                                                                   |
| --------------- | -------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------- |
| MinerU 解析封装 | `services/mineru_service.py`           | ✅   | 保存上传→submit_task→轮询→提取 md+base64 图片→解码落盘→改写图片链接                                            |
| 向量索引        | `services/vector_service.py`           | ✅   | 每 KB 一个 collection（cosine）；**按 `#` 标题分段再切 chunk**；`search_in_documents` 支持 Stage2 精筛         |
| Embedding       | `services/embedding_service.py`        | ✅   | BGE-M3 惰性单例；净化 `HTTPS_PROXY`；`local_files_only` 失败回退在线下载                                       |
| 关键词索引      | `services/keyword_index_service.py`    | ✅   | jieba 分词 + BM25 倒排；读 name+description+content 前 2000 字                                                 |
| 图谱服务        | `services/graph_service.py`            | ✅   | 节点 Document/Entity/KnowledgeBase；边 MENTIONED_IN/CO_OCCURRED_WITH/BELONGS_TO；Cypher 字符串拼接（深度 1-3） |
| 两阶段检索      | `services/two_stage_search_service.py` | ✅   | Stage1 BM25+图谱扩展 → Stage2 `search_in_documents`；候选不足直接向量；向量不可用回退 BM25                     |
| NER             | `services/ner_service.py`              | ✅   | HanLP BERT 模型，50k 字截断                                                                                    |
| 关系抽取        | `services/relation_extractor.py`       | ✅   | 共现 + 依存句法 + 8 条正则，不依赖 LLM                                                                         |
| 存储读取        | `services/storage_reader_service.py`   | ✅   | 读 web 端 `.tree-fs.json` 和 `.knowledge-base.yml`；list KBs/docs、read content、更新 vector_index 字段        |

#### 工程特性

- ✅ Anti-zombie port guard（`socket.bind` 探测，区分监听/TIME_WAIT）
- ✅ 配置优先级：ENV > `../config.yml` > `./config.yml` > 默认
- ✅ 向量/图谱服务不可用时优雅降级，不阻断主流程
- ✅ Embedding 模型预下载（`download_model.py`），失败不阻断启动
- ✅ 模块导入时净化 `HTTPS_PROXY`，`HF_HOME` 指向本地缓存

### 2.2 前端（web/）

#### 页面

| 页面         | 路径                       | 状态            |
| ------------ | -------------------------- | --------------- |
| 首页         | `/`                        | ✅              |
| 文件系统管理 | `/file-system`             | ✅              |
| 知识检索     | `/knowledge-search`        | ⚠️ 仅关键词搜索 |
| 关于         | `/about`、`/about-project` | ✅              |

#### Server Routes（Nuxt 代理层）

| 目录        | 路由数                                           | 状态                            |
| ----------- | ------------------------------------------------ | ------------------------------- |
| filesystem/ | 5                                                | ✅                              |
| kb/         | 17                                               | ✅                              |
| parse/      | 4                                                | ✅                              |
| search/     | 4（vector / batch-vector / two-stage / reindex） | ✅ 路由已存在，**但页面未调用** |
| graph/      | 3（stats / search / neighbors）                  | ✅ 路由已存在，**但无页面消费** |
| preview/    | 4                                                | ✅                              |

> **核验结论**：`knowledge-search.vue` 的 `handleSearch` 只调用 `/api/kb/search`（关键词）。search/ 和 graph/ 的 server route 已经写好，但前端页面没有接入。这是前端 UI 的核心缺口。

#### 前端服务

| 服务                         | 文件                             | 状态 |
| ---------------------------- | -------------------------------- | ---- |
| 树形文件系统（含 YAML 同步） | `tree-file-system-service.ts`    | ✅   |
| 知识库 YAML 管理             | `knowledge-base-yaml-service.ts` | ✅   |
| 知识库检索                   | `kb-search-service.ts`           | ✅   |
| PDF 解析代理                 | `pdf-parse-service.ts`           | ✅   |
| 标签管理                     | `tag-management-service.ts`      | ✅   |

### 2.3 MCP 服务器（kb-mcp/）

**共 33 个 MCP 工具**，全部已实现：

| 分类     | 工具                                                                                                                                                        | 状态 |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| Health   | `health_check`                                                                                                                                              | ✅   |
| KB CRUD  | `kb_list`、`kb_create`、`kb_update`、`kb_delete`、`kb_search`、`kb_get_documents`                                                                           | ✅   |
| Doc CRUD | `kb_doc_read`、`kb_doc_create`、`kb_doc_update_meta`、`kb_doc_update_content`、`kb_doc_delete`、`kb_doc_batch_delete`、`kb_doc_move`                        | ✅   |
| FS       | `fs_get_tree`、`fs_get_children`、`fs_get_node`、`fs_get_count`、`fs_create_folder`、`fs_create_file`、`fs_update_node`、`fs_delete_node`、`fs_upload_file` | ✅   |
| Preview  | `preview_file`                                                                                                                                              | ✅   |
| Parse    | `parse_doc`、`parse_doc_batch`、`parse_task_status`、`parse_tasks_list`                                                                                     | ✅   |
| Tags     | `kb_tags_list`、`kb_tag_create`、`kb_doc_update_tags`、`kb_doc_get_by_tag`                                                                                  | ✅   |
| Backend  | `backend_status`                                                                                                                                            | ✅   |
| 向量检索 | `kb_search_vector`、`kb_search_batch_vector`、`kb_search_two_stage`、`kb_reindex`、`kb_index_document`、`kb_batch_index`、`kb_search_stats`                 | ✅   |
| 图谱     | `kb_graph_search`、`kb_graph_neighbors`、`kb_graph_stats`                                                                                                   | ✅   |

- 启动时 `_startup_health_check_and_launch` 自动探测并拉起 backend + web
- 异步 httpx 客户端，PARSE_TIMEOUT 默认 5000s

### 2.4 Claude Code Skill 集成

**8 个 Skill + 1 个调度入口**，全部已实现且比预期更强大：

| Skill                | 职责                 | 核心流程                                                                                                                                    | 调用的关键 MCP 工具                                                                                                                                                                          |
| -------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `knowledge-store`    | 入口调度器           | Archival 诊断场景 → 分发                                                                                                                    | 不直接调工具                                                                                                                                                                                 |
| `knowledge-ingest`   | 入库流程             | A0 去重 → A0b 内容哈希去重 → A1 调查 → A2 分类 → A3 匹配/创建 KB → A4 写描述 → A5 选标签 → **A5b 智能分块** → A6 存储 → A7 打标签 → A8 报告 | `kb_list`、`kb_tags_list`、`kb_search`、`parse_doc`、`parse_task_status`、`kb_doc_create`、`kb_doc_update_tags`、`fs_upload_file`                                                            |
| `knowledge-manage`   | 管理操作             | M1-M5 + B6                                                                                                                                  | `kb_doc_move`、`kb_update`、`kb_doc_update_meta/content`、`kb_doc_delete`、`kb_delete`、`fs_create_folder/file`、`fs_update_node`、`fs_delete_node`                                          |
| `knowledge-organize` | 全盘整理             | O1 调查 → O2 评估 → O3 分类 → O4 执行 → O5 验证 → **O6 健康评分卡** → **O7 标签卫生审计** → **O8 智能分块**                                 | `kb_list`、`kb_tags_list`、`fs_get_tree`、`kb_get_documents`、`kb_doc_read`、`kb_doc_move/delete`、`kb_update`、`kb_doc_update_meta/tags`、`kb_batch_index`                                  |
| `knowledge-search`   | **Agentic RAG 检索** | **G1 全局扫描 → G2 区域深入 → G3 内容确认 → S 向量精排 → A4 综合回答**；**L1-L4 自适应深度**                                                | `kb_list`、`kb_tags_list`、`fs_get_tree`、`kb_get_documents`、`kb_doc_read`、**`kb_search_vector`**、**`kb_search_two_stage`**、**`kb_search_batch_vector`**、`kb_search`、`kb_search_stats` |
| `knowledge-list`     | 浏览                 | 只读                                                                                                                                        | `kb_list`、`kb_tags_list`、`fs_get_tree`、`kb_get_documents`、`kb_doc_read`、`preview_file`                                                                                                  |
| `knowledge-verify`   | 完整性校验           | V1-V6，只读默认                                                                                                                             | `kb_list`、`fs_get_tree`、`fs_get_count`、`kb_get_documents`、`kb_doc_read`、`kb_doc_get_by_tag`                                                                                             |
| `knowledge-batch`    | 批量操作             | B1-B6 + 报告导出                                                                                                                            | `kb_tags_list`、`kb_list`、`kb_get_documents`、`kb_doc_update_tags`、`kb_doc_read`、`kb_update`、`kb_doc_create`、`parse_doc`、`fs_upload_file`、`kb_doc_move/delete`                        |

#### knowledge-search 的 Agentic RAG 架构（亮点）

这是整个系统最有设计深度的部分，采用**图书馆员式渐进检索**：

```text
G1 Globe（全局扫描）   → kb_list() + kb_tags_list() + fs_get_tree()
   ↓ Agent 对每个 KB 打分场景适配度
G2 Region（区域深入）  → kb_get_documents(kb_id)
   ↓ Agent 分析文档元信息（名称/描述/标签/向量索引/更新时间）
G3 City（内容确认）    → kb_doc_read(kb_id, doc_path, max_chars=1200)
   ↓ Agent 实际阅读文档前 1200 字，打分 0-10
S Street（向量精排）   → kb_search_vector() 或 kb_search_two_stage()
   ↓ 只对 G3 确认相关的文档做向量精排
A4 Assembly（综合回答） → 融合 Agent 评分 + 向量评分 + 溯源
```

**自适应深度控制**：

| 深度    | 场景              | 流程       | 耗时      |
| ------- | ----------------- | ---------- | --------- |
| L1 浅层 | 事实性快速查找    | G→R→S      | 3-5 min   |
| L2 标准 | 知识问答          | G→R→C→S    | 5-10 min  |
| L3 深度 | 对比分析/综合报告 | G→R→C→S→C2 | 10-20 min |
| L4 探索 | 跨域探索          | G→R→C→S→A5 | 不限      |

> **关键**：`kb_search()`（元信息搜索）被明确标注为**兜底手段**，只搜 name+description 不读正文。向量检索优先。

### 2.5 配置与部署

| 项                                                                | 状态 |
| ----------------------------------------------------------------- | ---- |
| 统一 `config.yml`（server/storage/vector/embedding/graph/search） | ✅   |
| 统一 `.env`（端口/路径/密码/超时）                                | ✅   |
| `docker-compose.yml`（Neo4j 5.20 + APOC）                         | ✅   |
| `.mcp.json`（Claude Code 自动启动 kb-mcp）                        | ✅   |
| `start.sh` / `start.bat` 一键启动                                 | ✅   |
| Embedding 模型预下载脚本                                          | ✅   |

---

## 三、待完善与已知缺口

### 3.1 索引闭环缺口（P0 最高优先级）

| 缺口                       | 现状（源码核验）                                                                                                                                     | 影响                                                |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| **解析后不自动建索引**     | `web/server/api/parse/file-vt.post.ts` 和 `save-parsed-files.post.ts` 解析完成后只更新文件树和 YAML，**grep 确认无 `index-document`/`reindex` 调用** | 用户上传后必须手动 `kb_reindex` 才能用向量/图谱搜索 |
| **Skill 入库后不自动索引** | `knowledge-ingest` A6 轮询解析完成后只做 A7 打标签，**没有调用 `kb_index_document` 或 `kb_reindex`**                                                 | Agent 入库的文档同样无向量索引                      |
| **索引状态未可视化**       | `.knowledge-base.yml` 有 `vector_index` 字段，但前端不显示                                                                                           | 用户不知道哪些文档已索引                            |

### 3.2 前端 UI 缺口（P0）

| 缺口                   | 现状（源码核验）                                                                                                                               | 影响                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| **搜索模式切换**       | `knowledge-search.vue` 的 `handleSearch` 只调用 `/api/kb/search`（关键词），**grep 确认无 `/api/search/vector`、`/api/search/two-stage` 调用** | Web 用户只能用关键词搜索    |
| **知识图谱可视化页面** | 没有 `/graph` 页面                                                                                                                             | 图谱能力对 Web 用户不可见   |
| **重建索引 UI**        | 没有"重建索引"按钮                                                                                                                             | 用户必须用 curl 或 MCP 触发 |
| **来源溯源 UI**        | 搜索结果只显示文档路径，不显示 chunk 定位/score/原文片段                                                                                       | 溯源粒度粗                  |

### 3.3 算法与质量缺口（P1）

| 缺口                        | 现状（源码核验）                                                                  | 影响                       |
| --------------------------- | --------------------------------------------------------------------------------- | -------------------------- |
| **超长 section 字符级切分** | `_chunk_text` 已按 `#` 标题分段，但超长 section 仍按 500 字符硬切，不识别句子边界 | 可能切断句子，影响向量质量 |
| **关系抽取不依赖 LLM**      | 用 HanLP 依存句法 + 8 条正则模板                                                  | 图谱质量有限，复杂关系漏抽 |
| **两阶段权重固定**          | `keyword_weight=0.5, graph_weight=0.5` 写死在 config                              | 无法按查询类型自适应       |
| **无 rerank 模型**          | Stage2 只做向量相似度，没有交叉编码器精排                                         | 精确度有提升空间           |
| **无查询重写/扩展**         | 原始 query 直接送入检索                                                           | 同义改写、缩写场景召回率低 |

### 3.4 工程缺口（P2）

| 缺口                         | 现状                                                           | 影响             |
| ---------------------------- | -------------------------------------------------------------- | ---------------- |
| **双前端**                   | `web/`（Nuxt 3，活跃）和 `frontend/`（Vue 3 + Vite，过时）并存 | 维护负担         |
| **Web 代理层过薄**           | search/graph 路由只是透传，无错误包装/缓存/限流                | 后端异常直接暴露 |
| **测试覆盖不足**             | backend/tests/ 缺少 vector/graph/two-stage 单测                | 回归风险         |
| **无权限/多租户**            | 任何能访问端口的人都能操作                                     | 企业场景不可用   |
| **无审计日志**               | 谁在什么时候做了什么操作没有记录                               | 合规场景不可用   |
| **图谱 Cypher 拼接注入风险** | `graph_service.py` 用字符串拼接 Cypher                         | 需用参数化查询   |

---

## 四、后续功能规划

### 4.1 P0：闭环核心体验（1-2 周）

#### F1. 解析后自动建立索引（最高优先级）

**目标**：上传 PDF 解析完成后，自动触发向量索引和图谱构建，无需手动 reindex。

**实现位置**：

- `web/server/api/parse/file-vt.post.ts`（Web 上传路径）
- `web/server/api/parse/save-parsed-files.post.ts`（保存解析结果路径）
- `.claude/skills/knowledge-ingest/SKILL.md`（Skill 入库路径，A7 后加 A7b）

**Web 路径方案**：

```typescript
// 在 file-vt.post.ts 解析完成、文档落库后，异步触发索引
async function autoIndexDocument(
  kbId: string,
  docPath: string,
  content: string,
  docName: string,
  description: string,
) {
  try {
    await $fetch(`${backendUrl}/api/v1/search/index-document`, {
      method: "POST",
      body: {
        kb_id: kbId,
        doc_path: docPath,
        doc_name: docName,
        description: description,
        content: content,
      },
    });
    // 更新 .knowledge-base.yml 的 vector_index 状态
  } catch (e) {
    // 索引失败不阻断主流程，记录到 YAML 的 index_status
    console.warn("[auto-index] failed, document will need manual reindex:", e);
  }
}
```

**Skill 路径方案**：在 `knowledge-ingest/SKILL.md` 的 A7 和 A8 之间增加 A7b：

```markdown
## A7b — Build Vector & Graph Index

After tags are assigned, automatically build the vector and graph indexes:
```

kb_index_document(
kb_id="<target UUID>",
doc_path="<doc path>",
doc_name="<doc name>",
description="<from A4>",
content="<full markdown content>"
)

```

If indexing fails, note it in A8 report: "⚠️ Vector index pending — run `kb_reindex` manually."
```

**验收标准**：

- Web 上传 PDF → 解析完成 → 30 秒内可在向量搜索中查到
- Skill 入库 → A7b 自动执行 → A8 报告索引状态
- 索引失败不阻断解析流程
- `.knowledge-base.yml` 中 `vector_index` 字段更新为 true

#### F2. 前端搜索模式切换

**目标**：在 `knowledge-search.vue` 增加"关键词 / 向量 / 两阶段"三种搜索模式切换。

**实现方案**：

- 顶部添加 `a-radio-group` 切换组件（默认两阶段）
- 关键词模式：`GET /api/kb/search?query=...`（现有逻辑）
- 向量模式：`POST /api/search/vector` `{ query, top_k }`
- 两阶段模式：`POST /api/search/two-stage` `{ query, top_k }`
- 结果区统一渲染，但向量/两阶段模式额外显示 score 和 chunk 片段

**新增 composable**：`web/composables/useVectorSearch.ts`

```typescript
export const useVectorSearch = () => {
  const search = async (
    query: string,
    mode: "keyword" | "vector" | "two-stage",
    topK = 5,
  ) => {
    if (mode === "keyword") {
      return await $fetch("/api/kb/search", { query: { query, top_k: topK } });
    }
    const endpoint =
      mode === "vector" ? "/api/search/vector" : "/api/search/two-stage";
    return await $fetch(endpoint, {
      method: "POST",
      body: { query, top_k: topK },
    });
  };
  return { search };
};
```

**验收标准**：

- 三种模式可切换，结果正确
- 两阶段为默认模式
- 结果显示来源文档和匹配片段

#### F3. 重建索引 UI

**目标**：在文件系统页右键 KB 菜单增加"重建索引"选项。

**实现方案**：

- `file-system.vue` 右键菜单加项
- 调用 `POST /api/search/reindex` `{ kb_id, force: true }`
- 显示进度 Toast

#### F4. 索引状态可视化

**目标**：在文件树中显示每个文档的索引状态。

**实现方案**：

- `kb-documents` 返回结果已带 `vector_index` 字段
- 文件树节点显示小图标（绿色=已索引，灰色=未索引）

### 4.2 P1：图谱可视化与溯源（2-3 周）

#### F5. 知识图谱可视化页面

**目标**：新增 `/graph` 页面，支持实体搜索和邻居子图可视化。

**技术选型**：AntV G6（与 Ant Design 生态一致）或 Vis.js

**功能**：

- 搜索实体 → 展示邻居子图（深度 1-2）
- 点击节点 → 显示关联文档列表
- 点击边 → 显示关系类型
- 支持图谱统计仪表盘（实体数、关系数、文档数）

**新增文件**：

- `web/pages/graph.vue`
- `web/composables/useGraph.ts`
- `web/components/GraphCanvas.vue`

#### F6. 搜索结果溯源 UI

**目标**：搜索结果不仅显示文档，还显示具体 chunk、score、原文片段。

**实现方案**：

- 后端 `vector` / `two-stage` 端点返回 `chunk_text`、`chunk_index`、`score`
- 前端结果卡片展示片段预览 + "查看原文"按钮
- 点击跳转到文档预览并高亮对应段落

#### F7. Cypher 参数化查询（安全修复）

**目标**：消除 `graph_service.py` 的 Cypher 字符串拼接注入风险。

**实现位置**：`backend/app/services/graph_service.py`

**方案**：将所有 `$keyword` 字符串拼接改为 Neo4j 参数化查询：

```python
# 修复前（不安全）
query = f"MATCH (n) WHERE n.name CONTAINS '{keyword}' RETURN n"

# 修复后（安全）
query = "MATCH (n) WHERE n.name CONTAINS $keyword RETURN n"
result = session.run(query, keyword=keyword)
```

### 4.3 P2：检索质量提升（3-4 周）

#### F8. 超长 section 句子边界切分

**目标**：超长 section 不再按字符硬切，而是按句子边界。

**实现位置**：`backend/app/services/vector_service.py` `_chunk_text()`

**现状**：已按 `#` 标题分段，但超长 section 按 500 字符硬切。

**方案**：

```python
def _chunk_text(self, text: str) -> list[str]:
    # ... 现有标题分段逻辑保留 ...
    for section in sections:
        if len(section) <= size:
            chunks.append(section)
            continue
        # 改进：按句子边界切分，而非字符硬切
        sentences = self._split_sentences(section)
        current_chunk = ""
        for sent in sentences:
            if len(current_chunk) + len(sent) <= size:
                current_chunk += sent
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sent
        if current_chunk:
            chunks.append(current_chunk)
```

#### F9. LLM 驱动的关系抽取

**目标**：用 LLM 替代正则模板，提升图谱质量。

**方案**：

- 在 `relation_extractor.py` 增加可选的 LLM 抽取路径
- 配置项 `graph.llm_extract.enabled`
- Prompt：给定文档片段，抽取实体和关系三元组
- 与现有规则抽取并存，LLM 结果作为补充

#### F10. Cross-Encoder Rerank

**目标**：在两阶段检索的 Stage2 后，加一层 Cross-Encoder 精排。

**技术选型**：`BAAI/bge-reranker-v2-m3`

**新增文件**：`backend/app/services/rerank_service.py`

**配置**：

```yaml
search:
  rerank:
    enabled: false
    model_name: "BAAI/bge-reranker-v2-m3"
    top_k: 10
```

#### F11. 查询重写与扩展

**目标**：对用户查询做同义扩展、缩写展开、多语言改写。

**新增文件**：`backend/app/services/query_rewrite_service.py`

**方案**：

- 用 LLM 生成 3-5 个改写 query
- 多路召回后去重合并

### 4.4 P3：工程化与企业特性（持续）

#### F12. 统一前端

**目标**：移除 `frontend/` 子模块，只保留 `web/`。

#### F13. Web 代理层加固

**目标**：统一错误包装、请求日志、超时处理、简单缓存。

#### F14. 测试补齐

**目标**：

- backend/tests/ 增加 vector/graph/two-stage 单测
- E2E 测试覆盖"上传→解析→自动索引→搜索"全链路

#### F15. 权限与多租户（远期）

**目标**：

- 用户体系（登录、Token）
- KB 级权限（owner / reader）
- 操作审计日志

#### F16. 增量索引与版本控制（远期）

**目标**：

- 文档更新时只重索引变化部分
- 支持文档历史版本回溯

#### F17. 搜索反馈闭环（远期）

**目标**：

- 记录用户点击/认为有用的结果
- 用反馈数据微调检索权重
- 标记"高价值文档"用于 rerank 训练

---

## 五、如何追加新功能（开发指南）

### 5.1 新增后端 API 端点

以新增"按时间范围搜索"为例：

**Step 1**：定义 Pydantic 模型（`backend/app/models/search_models.py`）

```python
class TimeRangeSearchRequest(BaseModel):
    query: str
    start_date: str  # ISO 8601
    end_date: str
    top_k: int = 5
```

**Step 2**：在路由文件添加端点（`backend/app/api/routes/search.py`）

```python
@router.post("/time-range")
async def time_range_search(req: TimeRangeSearchRequest) -> dict[str, Any]:
    results = await some_service.search_by_time(req.query, req.start_date, req.end_date, req.top_k)
    return {"success": True, "results": results}
```

**Step 3**：在 `backend/app/services/` 实现业务逻辑

**Step 4**：在 `config.yml` 增加可配置项（如有需要）

**Step 5**：更新 `backend/README.md` 的 API 表

### 5.2 新增前端页面

以新增"图谱可视化页"为例：

**Step 1**：创建页面（`web/pages/graph.vue`）

```vue
<template>
  <div class="graph-page">
    <a-input-search
      v-model:value="keyword"
      placeholder="搜索实体..."
      @search="handleSearch"
    />
    <div ref="graphContainer" class="graph-canvas"></div>
  </div>
</template>

<script setup lang="ts">
const keyword = ref("");
const graphContainer = ref<HTMLElement>();

const handleSearch = async () => {
  const data = await $fetch("/api/graph/search", {
    query: { keyword: keyword.value },
  });
  // 用 G6/Vis.js 渲染子图
};
</script>
```

**Step 2**：如需新 server route，在 `web/server/api/graph/` 下创建（当前 `search.get.ts`、`neighbors.get.ts`、`stats.get.ts` 已存在）

**Step 3**：在导航栏添加入口（`web/layouts/default.vue`）

**Step 4**：如有可复用逻辑，提取到 `web/composables/useGraph.ts`

### 5.3 新增 MCP 工具

以新增"按标签批量搜索"为例：

**Step 1**：先在后端实现对应的 `/api/v1/search/by-tag` 端点

**Step 2**：在 `kb-mcp/kb_client/client.py` 添加 HTTP 方法

```python
async def kb_search_by_tag(self, tag: str, top_k: int = 10) -> dict:
    return await self._get_backend("/api/v1/search/by-tag", params={"tag": tag, "top_k": top_k})
```

**Step 3**：在 `kb-mcp/server.py` 注册 MCP 工具

```python
@mcp.tool()
async def kb_search_by_tag(tag: str, top_k: int = 10) -> str:
    """Search documents by tag across all KBs."""
    result = await client.kb_search_by_tag(tag, top_k)
    return json.dumps(result, ensure_ascii=False, indent=2)
```

### 5.4 新增/修改 Claude Code Skill

以新增"知识库导出"skill 为例：

**Step 1**：创建目录和文件（`.claude/skills/knowledge-export/SKILL.md`）

**Step 2**：在 `KNOWLEDGE-SYSTEM.md` 的调度器中注册新场景

**Step 3**：在 SKILL.md 中定义：

- frontmatter（name、description、触发词）
- 核心流程（分步骤，每步明确调用哪些 MCP 工具）
- 输出格式
- CRITICAL RULES

**Step 4**：确保对应的 MCP 工具已存在（如 `kb_export`）

**Skill 文件结构模板**：

```markdown
---
name: knowledge-export
description: >
  Export knowledge base contents. Invoked by Archival when...
  Triggered by: "export", "导出", "下载知识库"...
---

# Knowledge Export — 导出流程

## E1 — Survey

[调用哪些工具，做什么决策]

## E2 — Execute Export

[具体步骤]

## CRITICAL RULES

[必须遵守的规则]
```

### 5.5 新增配置项

以新增"rerank 模型"配置为例：

**Step 1**：在 `config.yml.example` 添加段落

```yaml
search:
  rerank:
    enabled: false
    model_name: "BAAI/bge-reranker-v2-m3"
    top_k: 10
```

**Step 2**：在 `backend/app/config.py` 添加属性

```python
@property
def rerank_config(self) -> dict:
    return self._search.get("rerank", {"enabled": False})
```

**Step 3**：在服务中读取配置

```python
if config.rerank_config.get("enabled"):
    # 加载 rerank 模型
```

**Step 4**：更新 `.env.example`（如有环境变量）

### 5.6 新增依赖

**后端 Python 依赖**：

- 编辑 `backend/pyproject.toml` 的 `dependencies`
- 运行 `uv sync`

**前端 Node 依赖**：

- 编辑 `web/package.json`
- 运行 `npm install`

**新增 Docker 服务**：

- 编辑 `docker-compose.yml`
- 运行 `docker compose up -d <service>`

### 5.7 新增启动脚本/测试脚本

- 启动脚本放 `scripts/`，遵循 `start-<name>.sh` + `start-<name>.bat` 双平台
- 测试脚本放 `scripts/`，命名 `test-<feature>-e2e.py`
- 在 `scripts/SKILL-TEST-PROMPT.md` 添加测试用例描述

---

## 六、里程碑路线图

### M1（近期，1-2 周）— 闭环核心体验

- [ ] F1 解析后自动建立索引（Web 路径 + Skill A7b）
- [ ] F2 前端搜索模式切换（关键词/向量/两阶段）
- [ ] F3 重建索引 UI
- [ ] F4 索引状态可视化

### M2（近期，2-4 周）— 图谱可视化与溯源

- [ ] F5 知识图谱可视化页面
- [ ] F6 搜索结果溯源 UI（chunk + score + 片段）
- [ ] F7 Cypher 参数化查询（安全修复）

### M3（中期，1-2 月）— 检索质量提升

- [ ] F8 超长 section 句子边界切分
- [ ] F9 LLM 驱动关系抽取
- [ ] F10 Cross-Encoder Rerank
- [ ] F11 查询重写与扩展

### M4（中期，持续）— 工程化

- [ ] F12 统一前端（移除 frontend/）
- [ ] F13 Web 代理层加固
- [ ] F14 测试补齐

### M5（远期）— 企业特性

- [ ] F15 权限与多租户
- [ ] F16 增量索引与版本控制
- [ ] F17 搜索反馈闭环
- [ ] 审计日志、SSO 集成

---

## 七、应保留的设计优势

在扩展过程中，以下设计优势**必须保留**，不要破坏：

### 7.1 两层切分机制

- **文档级切分**（Skill A5b/O8）：按章节拆分大文档为多个小文档
- **向量级切分**（后端 `_chunk_text`）：按 Markdown 标题分段再切 chunk

这两层切分各司其职，不要合并。文档级切分提升可读性，向量级切分提升检索精度。

### 7.2 Agentic RAG 渐进式检索

`knowledge-search` 的 G1→G2→G3→S→A4 + L1-L4 自适应深度是核心创新，**不要退化回"直接调向量搜索"**。任何新的检索能力都应融入这个框架。

### 7.3 优雅降级

- 向量不可用 → 回退 BM25
- 图谱不可用 → 返回空结果
- Embedding 模型下载失败 → 不阻断启动

新增功能必须延续这个模式：**任何可选组件的失败都不能阻断主流程**。

### 7.4 配置驱动

所有参数收口到 `config.yml` + `.env`，优先级：ENV > config.yml > 默认。不要在代码中硬编码端口、模型名、路径。

### 7.5 UUID 身份与路径解耦

KB 用 UUID v4，路径只是物理位置。重命名/移动不改 UUID。新增功能涉及 KB 引用时必须用 UUID。

### 7.6 文件系统主存 + 派生索引

- 主存储：Markdown 文件 + YAML 元数据
- 派生索引：ChromaDB 向量 + Neo4j 图谱

索引可以重建，文件不能丢失。新增索引类型（如 rerank）也应是派生的。

### 7.7 Skill 层的"先调查再操作"原则

所有 Skill 都遵循"survey first, execute second, verify third"。新增 Skill 必须延续这个原则。

---

## 附录：关键文件索引

| 模块       | 关键文件                                                                |
| ---------- | ----------------------------------------------------------------------- |
| 后端入口   | `backend/main.py`、`backend/app/main.py`                                |
| 后端配置   | `backend/app/config.py`、`config.yml`                                   |
| 后端路由   | `backend/app/api/routes/{health,parse,mineru,search,graph}.py`          |
| 后端服务   | `backend/app/services/*.py`（9 个服务）                                 |
| 向量切分   | `backend/app/services/vector_service.py` `_chunk_text()` 方法           |
| 前端入口   | `web/start.mjs`、`web/nuxt.config.ts`                                   |
| 前端页面   | `web/pages/*.vue`                                                       |
| 前端搜索页 | `web/pages/knowledge-search.vue`（`handleSearch` 函数）                 |
| 前端代理   | `web/server/api/{filesystem,kb,parse,search,graph,preview}/*.ts`        |
| 前端服务   | `web/server/services/*.ts`                                              |
| MCP 服务器 | `kb-mcp/server.py`、`kb-mcp/kb_client/client.py`                        |
| Skill 集成 | `.claude/skills/*.md`                                                   |
| 搜索 Skill | `.claude/skills/knowledge-search/SKILL.md`（G1-G3-S-A4 框架）           |
| 入库 Skill | `.claude/skills/knowledge-ingest/SKILL.md`（A0-A8 + A5b 分块）          |
| 整理 Skill | `.claude/skills/knowledge-organize/SKILL.md`（O1-O8 + 评分卡）          |
| 配置模板   | `config.yml.example`、`.env.example`、`docker-compose.yml`、`.mcp.json` |
| 启动脚本   | `start.sh`、`start.bat`、`scripts/start-{backend,web}.{sh,bat}`         |
| 测试脚本   | `scripts/test-*.py`                                                     |

---

> 本文档随项目演进持续更新。每完成一个里程碑，请勾选对应条目并更新"最后更新"日期。
