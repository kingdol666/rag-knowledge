# QDCVR 系统 Bug 修复与复测报告（诚实评估）

> **日期**: 2026-07-29  
> **修复轮次**: 1 轮代码修复 + 1 轮数据清理  
> **复测场景**: 4 个关键场景重新执行

---

## 1. Bug 修复状态

### BUG-1 (HIGH): ChromaDB 删除后残留向量 chunks

**根因**: `vector_service.py:_delete_doc_chunks` 方法使用 `where={"doc_path": doc_path}` 精确匹配。Windows 路径用反斜杠 `\`，但 ChromaDB 元数据中存储的路径可能用正斜杠 `/`，导致匹配失败。`except Exception: pass` 静默吞掉错误。

**修复**: 重写 `_delete_doc_chunks` 方法：
- 尝试 3 种路径变体（原路径、正斜杠、反斜杠）
- 失败时执行全量扫描回退（遍历所有 chunks 做 substring 匹配）
- 替换 `except: pass` 为带日志的错误处理

**复测结果**: **PASS** — S7 测试创建→索引→搜索→删除→再搜索，删除后文档完全不可检索。S8 链式测试同样确认删除清理生效。

### BUG-2 (HIGH): 孤儿向量 Collections

**根因**: 历史索引入库时用路径名（`kb_E2E-Integration-Test`）创建 collection，后续重索引用 UUID 名（`kb_1eb3a7d9-...`），导致同一 KB 有两个 collection，旧 collection 成为孤儿。

**修复**: 执行 `kb_cleanup_orphan_collections(dry_run=false)` 清理 3 个重复 collection，回收 23 个 chunks。最终状态：14 collections, 0 orphans, 0 duplicates。

**复测结果**: **PASS** — S3 重新检查确认 0 孤儿。

### BUG-3 (MEDIUM): 图谱双扩展名节点 (.md.md)

**根因**: 在某次早期 `build_kb_graph` 过程中，`doc_path` 被传入时已含 `.md`，某代码路径又追加了 `.md`。当前代码的 `_graph_doc_id` 函数只做路径分隔符标准化，不追加扩展名，因此该 bug 不在主代码路径中。

**修复**: 手动删除图谱中的 `.md.md` 幽灵节点（`kb_graph_delete_document("E2E-Integration-Test/test-ml-basics.md.md")` — 成功删除 1 节点）。

**复测结果**: **PASS** — 节点已清除，复测中未再产生新的双扩展名节点。

### BUG-4 (MEDIUM): kb_doc_create 缺图谱索引

**真实情况**: 经代码审查，`kb_doc_create` 确实通过 `task_registry.submit(_auto_index_doc(...))` 触发后台索引，而 `_auto_index_doc` 调用 `_client().index_document()` 最终命中后端 `/api/v1/search/index-document` 端点，该端点同时执行向量索引和图谱索引。

**结论**: 这不是代码 bug，而是异步时序问题 — fire-and-forget 索引在后台运行，测试时等待时间不足导致误判。增加等待时间后功能正常。

### BUG-5 (MEDIUM): kb_id 过滤器泄漏子 KB 结果

**真实情况**: `_resolve_hierarchical_collections` 方法会解析父 KB 的所有子 KB collections。这是**设计行为**：搜索 `AI-ML-Research` 时包含其子 KB `RAG-Research` 的结果是正确的层级检索行为。S2 复测中 Q1 的 "泄漏" 是 `RAG-Research` 子 KB 结果通过层级解析出现在 `AI-ML-Research` 搜索中——这是预期行为。

**结论**: 非 bug，是设计。已在文档中标注 "层级 KB 搜索包含子 KB"。

### BUG-6 (LOW): 标签创建时不自动注册全局

**真实情况**: 标签通过 `kb_doc_update_tags` 写入文档元数据时会触发全局注册。但 `kb_doc_create` 如果直接传 tags 参数，标签写入的是文件元数据层，不一定触发全局 registry 更新。这是一个已知的小问题，workaround 是创建后显式调用 `kb_doc_update_tags`。

---

## 2. 复测结果（4 个关键场景）

| 场景 | 状态 | 关键验证 |
|------|:----:|---------|
| **S7: 五层一致性 CRUD** | **PASS** | 创建→索引→搜索(score=0.723)→删除→再搜索(不可见)→stats(78 chunks) ✓ |
| **S8: 链式多技能** | **PASS** | 8/8 步骤全部通过：入库→域搜索→跨域搜索→统计→删除→验证删除 ✓ |
| **S2: 跨域 FPR** | **PASS** | Flat FPR=0.45, Domain FPR=0.05 (**89% 降低**) ✓ |
| **S3: KB 校验** | **PASS** | 0 孤儿, 0 重复, 14 collections 全部有效 ✓ |

### S7 五层一致性详细结果

| 操作 | L1 磁盘 | L2 tree-fs | L3 YAML | L4 ChromaDB | 结果 |
|------|:-------:|:----------:|:-------:|:-----------:|:----:|
| CREATE+INDEX | ✓ | ✓ | ✓ | ✓ (score=0.723) | ✅ |
| DELETE+CLEANUP | ✓删除 | ✓删除 | ✓删除 | **✓清理** | ✅ |
| POST-DELETE SEARCH | — | — | — | **✓不可见** | ✅ |

### S2 跨域 FPR 结果

| 查询 | Flat FPR | Domain FPR | 降低 |
|------|:--------:|:----------:|:----:|
| Q1: 强化学习 | 0.80 | 0.20 | 75% |
| Q2: 热管理 | 0.20 | 0.00 | 100% |
| Q3: MXene | 0.00 | 0.00 | — |
| Q4: 医学影像 | 0.80 | 0.00 | 100% |
| **平均** | **0.45** | **0.05** | **89%** |

---

## 3. 系统最终状态

| 指标 | 值 |
|------|:--:|
| 总 Collections | 14 |
| 孤儿 Collections | **0** |
| 重复 Collections | **0** |
| 可回收 chunks | **0** |
| 图谱双扩展名节点 | **0** (已清理) |
| 删除后向量残留 | **0** (BUG-1 修复生效) |

---

## 4. 诚实评估

### 已修复的问题
- **BUG-1 (HIGH)**: ✅ 代码修复，路径标准化 + 回退扫描。复测确认删除后零残留。
- **BUG-2 (HIGH)**: ✅ 数据清理，3 个重复 collection 删除，23 chunks 回收。
- **BUG-3 (MEDIUM)**: ✅ 幽灵节点清理。根因是历史数据，当前代码路径不产生。

### 非真实 bug（测试误判）
- **BUG-4**: 异步索引时序问题，非代码缺陷。增加等待时间即可。
- **BUG-5**: 层级 KB 搜索包含子 KB 是设计行为，非泄漏。

### 仍存在的已知限制
- **BUG-6 (LOW)**: `kb_doc_create` 的 tags 参数不触发全局 registry — workaround 是显式调 `kb_doc_update_tags`。这不影响功能正确性，只影响标签列表的即时性。
- **S3 发现**: 图谱 KB 节点数 (26) > 实际 KB 数 (13) — 因为图谱为每个子 KB 单独创建 KnowledgeBase 节点。这是设计行为，非 bug。

### 结论
**系统核心功能正确，所有 HIGH 级别 bug 已修复并复测验证通过。** 删除一致性、向量索引清理、跨域 FPR 隔离、链式工作流全部在真实场景下测试通过。