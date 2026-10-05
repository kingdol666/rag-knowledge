# ⚡ Knowledge Base Skill Trigger Contract (Mandatory Rules)

> Excerpted from the project CLAUDE.md — after the plugin is installed globally, skills can reference it independently.

**In any conversation, once the user's input hits any KB keyword below, the following procedure MUST be executed unconditionally — no bypassing, no substituting subjective experience, no skipping steps.**

## Rule 1: Triggers Are Non-Bypassable

When the user's request contains keywords from the table below (Chinese/English/combinations), **handling it yourself is forbidden** — you MUST invoke the corresponding knowledgebase skill:

| Keyword signals (any hit triggers) | Skill that must be invoked |
|---|---|
| 知识库, KB, 知识库管理, 文档管理, 入库, 上传文档, 解析PDF, 导入, 存储, 保存到 kb, 放文档, 添加文档, 整理知识库, 清洗知识库, 盘点, 大扫除, store, upload, parse, ingest, save to KB, add doc, put document | `Skill("knowledgebase")` |
| 搜索知识库, 检索, 查询, 帮我查, 问一下, 知识库问答, 搜, 哪里, 办法, 怎么解决, search, find, query, ask, retrieve, what is, how to, explain, RAG | `Skill("knowledgebase")` |
| 查看, 展示, 浏览, 有什么, 列出来, 清单, 内容, list, show, overview, tree, browse, display | `Skill("knowledgebase")` |
| 移动, 改名, 重命名, 删除文档, 删除KB, 合并, 更新内容, move, rename, delete, merge, update content | `Skill("knowledgebase")` |
| 批量, 所有文档, 全部, 全量, 统一, batch, bulk, mass, all documents, every KB | `Skill("knowledgebase")` |
| 校验, 核对, 完整性, 检查, 一致性, 检测, verify, validate, integrity, health check, quality audit | `Skill("knowledgebase")` |
| 经验, 经验库, 经验教训, 故障经验, 运维经验, 实践, 案例, 怎么处理, experience, lesson, best practice, previous experience | `Skill("knowledgebase")` |
| 图谱, 知识图谱, 实体关系, graph, knowledge graph, neo4j, entity, build graph | `Skill("knowledgebase")` |

**Exception clause**: only when the user's request clearly involves no KB operation (e.g. asking about code implementation or discussing architecture design) may you skip this procedure. When in doubt, **default to routing to the knowledge base instruction**.

## Rule 2: After Routing, Must Delegate to the Archival Sub-Agent

Once `Skill("knowledgebase")` is triggered, the dispatcher's job is:
1. Read the user input → match the table above → determine the scenario label
2. **Immediately delegate to the Archival sub-agent via the `task` tool**: `task(tasks=[{"agent": "archival", "task": "[Scenario: <label>] <user request>"}])`
3. After receiving the delegation, Archival runs its `Step 0 Scenario Diagnosis Protocol` to autonomously confirm the scenario
4. Route to the sub-skill (e.g. `knowledgebase-ingest`) and strictly execute its steps

**Strictly forbidden**: for the dispatcher to execute operations itself within the skill — it must delegate to Archival.

## Rule 3: Archival Execution Must Not Skip Steps

Each sub-skill defines a complete step flow. Archival **must execute strictly per the flow and must not skip any quality gate**:

| Gate | Rule |
|---|---|
| A0 Dedup | Vector ≥0.85 fingerprint dedup, mandatory |
| A2-Q Parse quality | Garbled text / empty body / binary residue → reject ingest |
| A3b Tag quality | Blacklist filtering + normalization + body cross-check, mandatory |
| A3c Description quality | Four elements + content cross-check, mandatory |
| A5 Storage choice | Parsed documents must use `kb_doc_save_parsed`; `kb_doc_create` is forbidden |
| A6-V Index verification | After indexing, verify the collection is correct + chunks ≥ 1 |
| A7 Eight-item final check | All of C1–C8 ✅ before it counts as complete |

## Rule 4: Violation Self-Correction Mechanism

If at any point in the same conversation you discover you previously violated the rules above (e.g. operated directly without triggering the skill, or used the wrong tool):
- **Stop the current operation immediately**
- Invoke the correct skill or sub-agent and re-execute
- Fix any errors already produced
- Explain to the user what was corrected

## Rule 5: ⭐ MCP-First Principle (added 2026-07-13, enforced library-wide)

**When MCP tools are connected and available, all knowledge base operations MUST be executed through MCP tools (`mcp__kb-mcp__*`) — no bypassing.**

| ❌ Forbidden | ✅ Required |
|---------|---------|
| Writing `curl` terminal commands to operate the KB | Use the `mcp__kb-mcp__kb_*` tools |
| Writing `python -c` to call the HTTP API | Use the `mcp__kb-mcp__parse_doc` tool |
| Using `wget`/`httpx` to hit the backend directly | Use the `mcp__kb-mcp__kb_doc_*` tools |
| Hardcoding API URLs in Bash/PowerShell | MCP guarantees atomic operations and an audit trail |

**Exception clause**: only when MCP is explicitly unavailable (MCP connection failed AND the user confirms) may terminal commands or the HTTP API be used as a fallback. After falling back you must declare to the user: "MCP unavailable, fell back to the HTTP API".
