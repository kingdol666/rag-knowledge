# RAG Knowledge Platform — 优化方案

**生成日期:** 2026-07-19 | **基于:** 全面端到端测试

## 综合评分: 108/115 (93.9%)

## 已完成的修复 (Phase 0)

| # | 修复项 | 文件 |
|---|--------|------|
| 1 | 系统性输入校验 (80+ 校验点) | kb-mcp/server.py, client.py |
| 2 | Energy-Batteries 向量索引重建 (537 chunks) | MCP op |
| 3 | 60 孤儿标签清理 (文档级) | MCP op |
| 4 | 孤儿 vector collection 清理 | MCP op |
| 5 | XAI-SHAP/ReAct 向量索引补全 | MCP op |
| 6 | experience_search 空 kb_id 降级 | kb-mcp/server.py |
| 7 | kb_reindex 后自动验证 (_verify) | kb-mcp/server.py |
| 8 | health_check 共享客户端 | kb_client/client.py |
| 9 | kb_doc_read 无参数防御 | kb_client/client.py |
| 10 | Web 路由 null-body 崩溃 (7 文件) | web/server/api/kb/documents/*.ts |
| 11 | kb_reindex key name 兼容 (total_docs/total_indexed) | kb-mcp/server.py |

---

## Phase 1 — 立即修复

### P1.1 标签词表持久性清理
- 问题: kb_tags_cleanup 后词表自动聚合刷新，孤儿标签复现
- 根因: A3b 门控未拦截章节标题 ("Abstract", "1 Introduction")
- 修复: 黑名单 + 正则模式 + 文档级标签同步
- 文件: web/server/services/tag-management-service.ts

### P1.2 kb_graph_build_kb total_relations 统计修复
- 问题: 返回 0，数据已写入 Neo4j
- 修复: graph_service.py 统计聚合
- 文件: backend/app/services/graph_service.py

---

## Phase 2 — 架构改进

### P2.1 BM25 Stage1 跨库盲区自动感知
- 问题: 跨库搜索完全遗漏语义相关但无关键词的 KB
- 修复: stage1 <2 KB → 自动触发 Enterprise 3-path召回
- 文件: kb-mcp/server.py

### P2.2 Dev-Mode 稳定性
- 问题: watchfiles ~400ms 重载风暴
- 修复: 排除 logs/chroma_db/neo4j_data/storage; ragctl up --stable
- 文件: backend/main.py

### P2.3 Neo4j 连接池管理
- 问题: CLOSE_WAIT 累积 → 连接池耗尽
- 修复: ping 探活 + 超时调优 + Docker healthcheck
- 文件: kb_client/client.py, docker-compose.yml

### P2.4 MCP 代码热加载文档化
- 问题: 代码修改需重启 Claude Code 才能生效
- 修复: CLAUDE.md 添加重启契约
- 文件: CLAUDE.md

---

## Phase 3 — 完善

### P3.1 kb_tags_cleanup 全量扫描
- 问题: 仅检查 200/440 标签
- 修复: 分页全量扫描
- 文件: kb-mcp/server.py

### P3.2 图谱 Sub-KB 节点名称
- 问题: related_kbs name 为 UUID
- 修复: graph_service 回填 KB 名称
- 文件: backend/app/services/graph_service.py

### P3.3 kb_doc_read 路径规范化
- 问题: Windows 反斜杠触发 400
- 修复: client.py 自动转换
- 文件: kb_client/client.py

### P3.4 经验提取质量
- 问题: heuristic mode key_lessons 可能为章节标题
- 修复: 最低质量阈值 + 推荐 prepare 模式
- 文件: backend/app/services/experience_service.py

### P3.5 文档补全
- rag-knowledge Skill 存根补全
- CLAUDE.md 工具计数 73→77

---

## 优先级

| 级别 | 编号 | 工作量 | 影响 |
|------|------|--------|------|
| P1 | P1.1 标签 | 2h | 高 |
| P1 | P1.2 total_relations | 1h | 低 |
| P2 | P2.1 跨库盲区 | 3h | 高 |
| P2 | P2.2 Dev-Mode | 1h | 高 |
| P2 | P2.3 Neo4j | 2h | 中 |
| P2 | P2.4 MCP重启 | 1h | 中 |
| P3 | P3.1-3.5 | 6h total | 低-中 |

平台已从"功能可用"升级为"防御性健壮"。目标评分: 113+/115。
