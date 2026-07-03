# Experience 经验机制 — 补全计划 (v2)

> 状态: `pending approval`
> 基于: v1 完成后的差距分析
> 日期: 2026-07-03

---

## 一、差距分析：v1 完成度评估

### ✅ 已完美实现（v1）

| 模块 | 状态 | 验证 |
|------|:----:|------|
| Backend Models (8个Pydantic) | ✅ | 导入成功 |
| Backend Service (CRUD+apply+review+summary) | ✅ | 34/34 测试通过 |
| Backend API Routes (9端点) | ✅ | 路由注册成功 |
| MCP Client 方法 (10个) | ✅ | 已写入 client.py |
| MCP Server 工具 (9个工具) | ✅ | 已注册 |
| kb_create 自动初始化 | ✅ | 已集成 |
| Nuxt 代理路由 (8个文件) | ⚠️ | 有 BUG |
| knowledge-experience Skill | ✅ | 已创建 |
| Archival agent 引用 | ✅ | 已添加 |
| E2E 测试脚本 | ✅ | 34/34 通过 |

---

## 二、发现的 BUG（必须修复）

### 🔴 BUG-1: Nuxt init 路由 HTTP 方法不匹配

**问题**:
- 后端: `@router.get("/{kb_id}/init")` → 接受 **GET**
- Nuxt 代理: `init.post.ts` → 发送 **POST**
- MCP client: `experience_init` → 用 `_get_backend` 发送 **GET**

**影响**: 通过 MCP 直接调后端是 OK 的（GET），但通过 Nuxt 代理会失败（405 Method Not Allowed）。

**修复**: 把 `init.post.ts` 改为 `init.get.ts`，用 GET 方法。

---

### 🔴 BUG-2: Nuxt index.post.ts URL 末尾多了斜杠

**问题**:
```typescript
// 当前（错误）
const url = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}/`
//                                                                     ^ 多了 /

// 正确
const url = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}`
```

**影响**: 后端 FastAPI 默认不重定向末尾斜杠，可能返回 307 或 404。

**修复**: 删除末尾的 `/`。

---

### 🔴 BUG-3: Nuxt 代理缺少错误处理

**问题**: 所有 Nuxt 代理路由都没有 try/catch，后端不可用或返回非 JSON 时会让前端崩溃。

**修复**: 统一加上错误处理包装器。

---

## 三、遗漏的功能（计划要求但未实现）

### 🟡 GAP-1: knowledge-search Skill 没有 Experience 钩子

**计划 7.3 要求**: 在知识检索的 S-Street 阶段后增加 Experience 阶段：
```
Globe → Region → City → Street → 🆕 Experience → A4
```

**当前状态**: `knowledge-search/SKILL.md` 完全没有提到 experience。

**影响**: Agent 做知识检索时不会自动联想相关经验，经验机制形同虚设——存了但不会被检索到。

**修复**: 在 knowledge-search SKILL.md 中新增 Experience 阶段说明。

---

### 🟡 GAP-2: 经验创建时没有自动向量索引

**计划 E1 流程要求**: "自动调用 kb_index_document 对经验正文建向量索引"

**当前状态**: `experience_service.create_experience()` 只写了 `.md` 文件和索引，**没有触发向量索引**。

**影响**: 经验无法被 `kb_search_vector` / `kb_search_two_stage` 检索到。经验的语义搜索能力缺失。

**修复**: 在 `create_experience` 成功后调用后端的 `index_document` 服务，把经验 `.md` 加入向量库（集合名 `exp_{kb_path}`）。

---

### 🟡 GAP-3: 经验向量搜索工具未实现

**计划第三章设计**:
- `experience_search` — 元信息搜索
- `experience_search_vector` — 向量语义搜索

**当前状态**: 只实现了 `experience_find_by_scenario`（场景过滤），**没有语义搜索**。

**影响**: 用户问"以前遇到类似的振动问题怎么处理的？"这种自然语言查询无法匹配到经验（场景标识需要精确匹配）。

**修复**: 新增 `experience_search` MCP 工具，复用 `kb_search_vector` 在 `exp_*` 集合中搜索。

---

### 🟡 GAP-4: KB 删除时没有级联删除经验

**计划风险章节**: "实现级联删除：kb_delete 同时删除 experience/"

**当前状态**: `kb_delete` 只删 KB 文件夹，但 experience/ 子目录可能残留（或被文件系统递归删除但索引文件 `.experience-index.yml` 在 KB 内所以会一起删，这点其实没问题）。

**实际验证需要**: 确认 `kb_delete` 是否递归删除整个 KB 文件夹（含 experience/）。如果是，这个 GAP 其实不存在。

**修复**: 验证 `kb_delete` 行为，必要时显式清理。

---

### 🟡 GAP-5: 跨 KB 经验搜索

**计划第三章提到**: `POST /api/v1/experience/cross-kb-search`

**当前状态**: 所有经验操作都是单 KB 的。

**影响**: 用户问"全厂所有知识库中关于故障排查的经验有哪些？"无法一次性查全。

**修复**: 新增 `experience_search_global` 工具，遍历所有 KB 的 `.experience-index.yml`。

---

## 四、补全实现计划

### Phase A: 修复 BUG（0.5天）

| Step | 文件 | 修改 |
|:----:|------|------|
| A1 | `web/server/api/experience/[kbId]/init.post.ts` | 重命名为 `init.get.ts`，改用 GET |
| A2 | `web/server/api/experience/[kbId]/index.post.ts` | 删除 URL 末尾 `/` |
| A3 | 所有 8 个 Nuxt 代理路由 | 加 try/catch + 错误返回 |
| A4 | 创建 `web/server/utils/experience-proxy.ts` | 提取通用代理函数，避免重复代码 |

### Phase B: 经验向量索引集成（1天）

| Step | 文件 | 修改 |
|:----:|------|------|
| B1 | `backend/app/services/experience_service.py` | `create_experience` 后调用 `vector_service.index_document()`，集合名 `exp_{kb_path}` |
| B2 | `backend/app/services/experience_service.py` | `update_experience` 后重建索引 |
| B3 | `backend/app/services/experience_service.py` | `delete_experience` 后从向量库删除 |
| B4 | `backend/app/services/experience_service.py` | 经验元数据增加 `vector_index` 字段记录 chunk 数 |

### Phase C: 经验搜索工具（1天）

| Step | 文件 | 修改 |
|:----:|------|------|
| C1 | `backend/app/services/experience_service.py` | 新增 `search_experiences(query, kb_id?)` — 元信息搜索 |
| C2 | `backend/app/services/experience_service.py` | 新增 `vector_search_experiences(query, kb_id?, top_k)` — 向量搜索 |
| C3 | `backend/app/services/experience_service.py` | 新增 `search_experiences_global(query)` — 跨 KB 搜索 |
| C4 | `backend/app/api/routes/experience.py` | 新增 3 个搜索端点 |
| C5 | `kb-mcp/kb_client/client.py` | 新增 3 个搜索方法 |
| C6 | `kb-mcp/server.py` | 新增 3 个 MCP 工具: `experience_search`, `experience_search_vector`, `experience_search_global` |

### Phase D: Skill 集成（0.5天）

| Step | 文件 | 修改 |
|:----:|------|------|
| D1 | `.claude/skills/knowledge-search/SKILL.md` | 新增 Experience 阶段（在 Street 之后、A4 之前） |
| D2 | `.claude/skills/knowledge-experience/SKILL.md` | 完善 E2 流程，加入向量搜索 |
| D3 | `.claude/skills/knowledge-store/SKILL.md` | 在 dispatcher 中增加经验场景识别 |

### Phase E: 级联删除与一致性（0.5天）

| Step | 文件 | 修改 |
|:----:|------|------|
| E1 | 验证 `kb_delete` 行为 | 确认是否递归删除 experience/ |
| E2 | 如需要，修改 `web/server/api/kb/delete.delete.ts` | 显式清理 experience/ |
| E3 | `backend/app/services/experience_service.py` | 新增 `cleanup_orphan_experiences()` 工具方法 |

### Phase F: 测试验证（0.5天）

| Step | 测试 | 说明 |
|:----:|------|------|
| F1 | 扩展 `scripts/test-experience-e2e.py` | 新增向量索引验证、搜索测试 |
| F2 | 新增 `scripts/test-experience-nuxt-proxy.ts` | 测试所有 Nuxt 代理路由 |
| F3 | 新增 `scripts/test-experience-mcp.py` | 通过 MCP 客户端测试所有工具 |
| F4 | 端到端 Skill 测试 | 创建经验→搜索经验→应用→评审→删除 |

---

## 五、补全后的完整能力清单

### MCP 工具（从 9 个增加到 12 个）

| 工具 | 类型 | 状态 |
|------|------|:----:|
| experience_create | CRUD | ✅ v1 |
| experience_read | CRUD | ✅ v1 |
| experience_list | CRUD | ✅ v1 |
| experience_update | CRUD | ✅ v1 |
| experience_delete | CRUD | ✅ v1 |
| experience_apply | 操作 | ✅ v1 |
| experience_review | 操作 | ✅ v1 |
| experience_find_by_scenario | 检索 | ✅ v1 |
| experience_summary | 统计 | ✅ v1 |
| **experience_search** | 检索 | 🆕 v2 元信息搜索 |
| **experience_search_vector** | 检索 | 🆕 v2 向量语义搜索 |
| **experience_search_global** | 检索 | 🆕 v2 跨 KB 搜索 |

### 三位一体完整闭环

```
用户问题: "以前遇到磨煤机堵煤怎么处理的？"
    │
    ▼
knowledge-search Skill (含 Experience 钩子)
    │
    ├─ Globe → 定位 Thermal-Power KB
    ├─ Region → 文档候选
    ├─ City → 读摘要
    ├─ Street → 向量精排文档
    ├─ 🆕 Experience → experience_search_vector("磨煤机堵煤处理")
    │                 → 命中 exp-coal-mill-001 (rating 4.5, applied 12次)
    └─ A4 → 综合回答 + "💡 推荐参考经验：磨煤机堵煤排查流程"
```

---

## 六、验收标准（v2 新增）

| # | 验收项 | 验证方式 |
|:-:|--------|---------|
| B1 | 创建经验后向量索引自动建立 | `kb_search_vector` 能搜到经验内容 |
| B2 | 删除经验后向量索引清除 | 搜索不再返回该经验 |
| C1 | 元信息搜索可用 | `experience_search("磨煤机")` 返回结果 |
| C2 | 向量搜索可用 | `experience_search_vector("如何处理堵煤")` 返回结果 |
| C3 | 跨 KB 搜索可用 | `experience_search_global("故障排查")` 返回多 KB 结果 |
| D1 | knowledge-search 集成 Experience | Skill 文档含 Experience 阶段 |
| A1 | Nuxt init 路由方法正确 | GET 请求成功 |
| A2 | Nuxt index.post URL 正确 | 创建经验成功 |
| A3 | Nuxt 代理有错误处理 | 后端宕机时返回友好错误 |

---

## 七、优先级建议

**P0（必须）**: Phase A (修BUG) + Phase B (向量索引) + Phase D (Skill集成)
**P1（重要）**: Phase C (搜索工具)
**P2（可选）**: Phase E (级联删除) + Phase F (测试)

**最小可用闭环 = A + B + D**：修好 BUG + 经验能被向量搜索 + Agent 检索时能联想经验。

---

## 八、ADR 补充

| 项目 | 内容 |
|------|------|
| **v2 Decision** | 补全向量索引、搜索工具、Skill 集成 |
| **Drivers** | v1 的经验虽然能存但"搜不到"=不可用；Skill 不集成=Agent 不会用 |
| **Why chosen** | 经验的价值在于被检索复用，没有搜索=死数据 |
| **Consequences** | 增加 3 个 MCP 工具（共12个），向量库多 exp_* 集合 |
| **Follow-ups** | 前端经验管理 UI、经验推荐算法、经验版本管理 |
