# 知识库系统全面功能验证报告

## 测试时间
2026-07-03 02:20-10:55 UTC

## 已验证通过的功能 ✅

### Health & Status
- ✅ Backend health check (200 OK)
- ✅ MinerU OCR engine running (port 50233)
- ✅ Web catalog (10+ KBs, 12 folders total)

### KB CRUD
- ✅ kb_create (含 UUID, path, auto-experience-init)
- ✅ kb_update (name + description)
- ✅ kb_delete
- ✅ kb_list/catalog

### Document CRUD
- ✅ kb_doc_create (自动 path 分配 + markdown content 写入)
- ✅ kb_doc_read (content 完整返回)
- ✅ kb_doc_update_meta, kb_doc_update_content
- ✅ kb_doc_delete
- ✅ 所有文档有完整向量索引 (vector_index metadata)

### File System
- ✅ fs_get_tree (完整嵌套结构)
- ✅ fs_get_children / fs_get_node
- ✅ fs_get_count
- ✅ fs_create_folder / fs_create_file
- ✅ fs_update_node / fs_delete_node
- ✅ fs_upload_file

### Tags
- ✅ kb_tags_list (76 个标签)
- ✅ kb_tag_create (dedup, max 50 chars)
- ✅ kb_doc_update_tags
- ✅ kb_doc_get_by_tag

### Preview
- ✅ preview_file (Markdown content 正确返回)

### Vector Search
- ✅ kb_search_vector (5 res, score 0.72)
- ✅ kb_search_batch_vector
- ✅ Search stats (15 collections, 241 chunks)
- ✅ kb_index_document / kb_batch_index

### Two-Stage Search
- ✅ Stage2 vector refinement (5 results)
- ✅ Direct BM25 test (28 docs → 5 results)
- ⚠️ Stage1 候选为0（运行中后端存储路径问题待重启）

### Experience Management
- ✅ experience_init
- ✅ experience_create (含自动向量索引)
- ✅ experience_read (content + metadata)
- ✅ experience_list (含 scenario/category/tag 过滤)
- ✅ experience_update
- ✅ experience_delete (含 verify)
- ✅ experience_apply (计数正常)
- ✅ experience_review (评分 0-5)
- ✅ experience_summary (by_category, by_severity, avg_rating)
- ✅ experience_search (跨字段关键词)
- ✅ experience_vector_search (语义)
- ✅ experience_search_global (跨 KB)

### MCP Tools
- ✅ 55 MCP tools 定义在 server.py
- ✅ Zero HTTP code in server.py (all in client.py)
- ✅ 51 client methods 匹配
- ✅ Non-blocking parse tools via task_registry

## 总计: 50+ 功能点通过 ✅

## 已修复的问题 ✅

### BUG-2 (已修复): Experience 路由顺序错乱
- **问题**: `/{kb_id}/{exp_id}` 在 `/{kb_id}/summary` 之前注册，导致 summary 被动态参数捕获
- **修复**: 重新排布路由顺序，静态路由（summary/search/vector-search）在前，动态 `{exp_id}` 路由在后
- **文件**: `backend/app/api/routes/experience.py`

### BUG-3 (已修复): Nuxt 代理路由缺失
- **问题**: Nuxt 缺少 summary, search, vector-search 代理路由
- **修复**: 创建 3 个 Nuxt 代理路由文件
- **文件**: 
  - `web/server/api/experience/[kbId]/summary.get.ts`
  - `web/server/api/experience/[kbId]/search.post.ts`
  - `web/server/api/experience/[kbId]/vector-search.post.ts`

## 待解决的问题 ⚠️

### BUG-1: Neo4j 知识图谱不可用
- **原因**: Neo4j 服务未安装/未运行 (localhost:7687 无响应)
- **影响**: 3 个 graph 端点返回 500
  - `kb_graph_search` (搜索实体)
  - `kb_graph_neighbors` (实体邻居)
  - `kb_graph_stats` (统计)
- **影响范围**: 两阶段检索的图谱邻居扩展阶段会被跳过（优雅降级）
- **待办**: 
  1. 安装 Neo4j Desktop 或 Docker (neo4j:latest)
  2. 配置 `config.yml`: `graph.password` 或 `NEO4J_PASSWORD` 环境变量
  3. 重建图谱索引: `POST /api/v1/search/reindex`

### BUG-4: 两阶段检索 Stage1 候选数在运行中后端为0
- **原因**: 当前后端进程 (PID 45624) 启动时使用了错误的存储路径
- **分析**: 代码本身正确（config.yml 设 `./web/storage/tree-file-system`），但老进程缓存了旧路径
- **待办**: 重启后端进程使新配置生效
  ```
  # PowerShell 中执行:
  Stop-Process -Id 45624 -Force
  cd backend && APP_MODE=dev uv run python main.py
  ```

## 架构验证
- ✅ MCP server 完全无 HTTP 代码（纯 client.py 委派）
- ✅ 所有端口/URL 从 config.yml 读取
- ✅ 非阻塞 parse 通过 task_registry 实现
- ✅ 经验管理创建时自动创建向量索引
- ✅ KB 创建时自动初始化经验文件夹
