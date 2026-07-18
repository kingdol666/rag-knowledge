# Known Pitfalls（已知坑）

> 摘自项目 CLAUDE.md — 全局安装插件后技能可独立引用
> 原始来源：CLAUDE.md § Known Pitfalls (#1-#14)

## #7 层次化KB搜索返回空内容

父KB（如高分子双向拉伸文献库）的 `kb_search_two_stage` 返回子KB容器条目，content 为空。子KB本身无向量chunk。

**Workaround**：用 `kb_graph_kb_overview(kb_id)` 获取子KB UUID列表，在相关子KB内分别检索（见 knowledgebase-search Skill Step 1b）。

## #8 向量索引元数据可能缺失

部分KB的文档 `vector_index` 字段可能在索引后未写入 YAML 元数据（向量实际存在于 ChromaDB）。

**修复**：用 `kb_reindex(kb_id, force=true)` 修复。

## #9 经验启发式提取产生低质量候选

`experience_extract(mode="heuristic")` 的 key_lessons 可能返回章节标题。

**推荐**：用 `mode="prepare"` → LLM 精炼。详见 knowledgebase-experience Skill E2a 质量门控。

## #10 图谱子KB节点仅显示UUID

`kb_graph_kb_overview` 返回的 sub_kbs 列表中 name 字段为 UUID 而非可读名称。如需可读名称，需回查 `kb_catalog()`。

## #11 标签注册表积累孤儿标签

`kb_tags_list()` 返回的标签列表包含 0 文档引用的历史标签（如测试标签、章节标题）。使用 `kb_tags_cleanup(dry_run=true)` 检测，`dry_run=false` 清理。**不影响搜索功能**——文档级标签自动过滤。

## #12 `kb_graph_build_kb` 返回的 `total_relations` 可能为 0

这是 stats 统计 bug，实际图谱数据已写入 Neo4j。**不要**因为返回 0 就认为构建失败。用 `kb_graph_document(doc_path)` 或 `kb_graph_kb_overview(kb_id)` 抽检验证。

## #13 经验可信度阈值在 CLAUDE.md 和 SKILL.md 之间可能不同

P0/P1/P2 阈值以 skill 为准（含 content 验证维度）。如需调整请同时改两处。

## #14 ⭐ kb-mcp MCP 启动检查（强制规则）

在执行任何 KB 操作之前，必须先验证 kb-mcp MCP 服务器是否已连接：
- 调用 `mcp__kb-mcp__backend_status` 检测 MCP 连通性
- **如果 MCP 工具可用** → 正常执行，所有操作必须通过 MCP 工具（遵循 MCP 优先原则）
- **如果 MCP 工具不可用**（返回 "No such tool available"）：
  1. 使用 `Bash` 检查核心服务状态：`curl -s http://localhost:8765/api/v1/health`（后端）
  2. 检查 `.mcp.json` 配置
  3. 尝试手动启动 kb-mcp
  4. 如果后端健康但 MCP 仍不可用 → 通知用户 "kb-mcp MCP 未连接，请重启 Claude Code"
  5. **仅在 MCP 确认不可用且用户明确允许后**，才可用 HTTP API 作为兜底
- Archival Agent 启动时将此检查作为 **Pre-Flight** 步骤
