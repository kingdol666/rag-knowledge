# KB Skill 冒烟测试报告（只读 · 经 kb-mcp MCP stdio 通道）

- 覆盖 skill：**18** · 调用：**26** 次 · 失败：**0**
- 全部为**只读**调用；未做任何写操作；未调用被测系统的对外问答 API。

| skill | 工具 | 结果 | 耗时 ms | 返回 | 验证点 |
|---|---|:--:|---:|---|---|
| `knowledgebase` | `kb_list` | ✅ | 543 | 3 | 调度器：列库（catalog） |
| `knowledgebase-list` | `kb_get_documents` | ✅ | 552 | 4 | 列文档（轻量） |
| `knowledgebase-search` | `kb_search_vector` | ✅ | 2010 | 3 | 向量召回（Phase 1 主工具） |
| `knowledgebase-search` | `kb_search_stats` | ✅ | 350 | 2 | 向量索引统计 |
| `knowledgebase-search` | `kb_search` | ✅ | 317 | 4 | 元数据检索 |
| `knowledgebase-ingest` | `kb_get_documents` | ✅ | 546 | 4 | 入库后读回（A7 终检面） |
| `knowledgebase-ingest` | `fs_get_tree` | ✅ | 533 | 2 | 目录树（入库落盘面） |
| `knowledgebase-librarian` | `kb_list` | ✅ | 562 | 3 | L0 全库目录（图书馆员入口） |
| `knowledgebase-librarian` | `kb_get_documents` | ✅ | 548 | 4 | L2 全文档描述 |
| `knowledgebase-hybrid` | `kb_search_vector` | ✅ | 7 | 3 | lane A 向量召回 |
| `knowledgebase-hybrid` | `kb_list` | ✅ | 531 | 3 | lane B 目录扫描 |
| `knowledgebase-organize` | `kb_find_duplicates` | ✅ | 17819 | 8 | 重复检测（O 层审计面） |
| `knowledgebase-manage` | `kb_get_documents` | ✅ | 553 | 4 | 文档清单（移动/改名前置） |
| `knowledgebase-verify` | `kb_search_stats` | ✅ | 34 | 2 | 三源一致性·向量覆盖 |
| `knowledgebase-verify` | `kb_graph_stats` | ✅ | 27 | 3 | 三源一致性·图谱 |
| `knowledgebase-graph` | `kb_graph_stats` | ✅ | 26 | 3 | 图谱统计 |
| `knowledgebase-graph` | `kb_graph_central_documents` | ✅ | 9 | 3 | 中心文档 |
| `knowledgebase-experience` | `experience_search_global` | ✅ | 581 | 11 keys | 经验检索 |
| `knowledgebase-experience` | `experience_dashboard` | ✅ | 20 | 9 | 经验看板 |
| `knowledgebase-experience-summarize` | `experience_list` | ✅ | 8 | 3 | 经验清单（汇总前置） |
| `knowledgebase-batch` | `kb_list` | ✅ | 533 | 3 | 批量操作目标枚举 |
| `knowledgebase-init` | `kb_project_status` | ✅ | 924 | 6 | 项目运行状态 |
| `knowledgebase-update` | `kb_project_status` | ✅ | 1025 | 6 | 版本检查 |
| `soul` | `soul_list` | ✅ | 31 | list | 人格清单 |
| `soul-rag` | `soul_list` | ✅ | 16 | list | 人格清单（检索+人格入口） |
| `butian` | `kb_list` | ✅ | 546 | 3 | 蒸馏产物落地为库 |