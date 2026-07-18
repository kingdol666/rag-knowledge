# ⚡ 知识库技能触发契约（强制规则）

> 摘自项目 CLAUDE.md — 全局安装插件后技能可独立引用

**任何对话中，用户输入一旦命中以下 KB 关键词，必须无条件执行以下流程，不得绕过、不得用主观经验替代、不得省略步骤。**

## 第一条：触发不可绕过

用户请求包含下表关键词（中/英/组合）时，**禁止自行处理**，必须调用对应的 knowledgebase 技能：

| 关键词信号（命中任意即触发） | 必须调用的技能 |
|---|---|
| 知识库, KB, 知识库管理, 文档管理, 入库, 上传文档, 解析PDF, 导入, 存储, 保存到 kb, 放文档, 添加文档, 整理知识库, 清洗知识库, 盘点, 大扫除, store, upload, parse, ingest, save to KB, add doc, put document | `Skill("knowledgebase")` |
| 搜索知识库, 检索, 查询, 帮我查, 问一下, 知识库问答, 搜, 哪里, 办法, 怎么解决, search, find, query, ask, retrieve, what is, how to, explain, RAG | `Skill("knowledgebase")` |
| 查看, 展示, 浏览, 有什么, 列出来, 清单, 内容, list, show, overview, tree, browse, display | `Skill("knowledgebase")` |
| 移动, 改名, 重命名, 删除文档, 删除KB, 合并, 更新内容, move, rename, delete, merge, update content | `Skill("knowledgebase")` |
| 批量, 所有文档, 全部, 全量, 统一, batch, bulk, mass, all documents, every KB | `Skill("knowledgebase")` |
| 校验, 核对, 完整性, 检查, 一致性, 检测, verify, validate, integrity, health check, quality audit | `Skill("knowledgebase")` |
| 经验, 经验库, 经验教训, 故障经验, 运维经验, 实践, 案例, 怎么处理, experience, lesson, best practice, previous experience | `Skill("knowledgebase")` |
| 图谱, 知识图谱, 实体关系, graph, knowledge graph, neo4j, entity, build graph | `Skill("knowledgebase")` |

**例外条款**：仅当用户请求明确不涉及KB操作（如问代码实现、聊架构设计）时，可以不走此流程。有疑问时**默认路由到知识库指令**。

## 第二条：路由后必须委托 Archival 子 Agent

`Skill("knowledgebase")` 触发后，调度器的职责是：
1. 读取用户输入 → 匹配上表 → 确定场景标签
2. **立即委托 Archival 子 Agent**：`Agent(subagent_type="archival", ...)`
3. Archival 接到委托后，执行其 `Step 0 场景诊断协议` 自主确认场景
4. 路由到子 Skill（如 `knowledgebase-ingest`）严格按步骤执行

**严禁**：调度器在 skill 内自行执行操作，必须委托 Archival。

## 第三条：Archival 执行不可省略步骤

每个子 Skill 定义了完整的步骤流程。Archival **必须严格按流程执行，不得跳过任何质量门控**：

| 门控 | 规则 |
|---|---|
| A0 去重 | 向量≥0.85指纹判重，必做 |
| A2-Q 解析质量 | 乱码/空正文/二进制残留 → 拒绝入库 |
| A3b 标签质量 | 黑名单过滤 + 归一化 + 正文回查，必做 |
| A3c 描述质量 | 四要素 + 内容回查，必做 |
| A5 存储选择 | 解析文档必须用 `kb_doc_save_parsed`，禁止用 `kb_doc_create` |
| A6-V 索引验证 | 索引后必验证 collection 正确 + chunks ≥ 1 |
| A7 八项终检 | C1-C8 全部 ✅ 才算完成 |

## 第四条：违规自纠机制

如果在同一对话中发现之前违反了上述规则（如未触发skill直接操作、或用错工具）：
- **立即停止当前操作**
- 调用正确 skill 或子Agent重新执行
- 修正已产生的错误
- 向用户说明纠正了什么

## 第五条：⭐ MCP 优先原则（2026-07-13 新增，全库强制执行）

**当 MCP 工具已连接可用时，所有知识库操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`），不得绕过。**

| ❌ 禁止 | ✅ 必须 |
|---------|---------|
| 写 `curl` 终端命令操作 KB | 用 `mcp__kb-mcp__kb_*` 工具 |
| 写 `python -c` 调用 HTTP API | 用 `mcp__kb-mcp__parse_doc` 工具 |
| 用 `wget`/`httpx` 直调后端 | 用 `mcp__kb-mcp__kb_doc_*` 工具 |
| Bash/PowerShell 中硬编码 API URL | MCP 保证了原子操作和审计追踪 |

**例外条款**：仅在 MCP 明确不可用（MCP 连接失败且用户确认后），才可用终端命令或 HTTP API 作为兜底。兜底后必须向用户声明 "MCP 不可用，已用 HTTP API 兜底"。
