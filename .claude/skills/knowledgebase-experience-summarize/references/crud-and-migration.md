# CRUD & Migration — 经验增删改查 + 跟随知识库移动

> 经验的创建、更新、删除全生命周期，以及文档移动时经验的跟随迁移。

## Table of Contents
- [创建](#创建)
- [更新](#更新)
- [删除](#删除)
- [跟随文档移动](#跟随文档移动experience-跟随-related_docs)
- [跟随 KB 移动](#跟随-kb-移动整个-kb-的经验迁移)
- [验证清单](#验证清单每次操作后)

---

## 创建

```
experience_create(kb_id, title, scenario, category, problem, solution, result,
                  key_lessons, tags, severity, related_docs, prerequisites, metrics)
→ {success, experience: {id, ...}}
```

**后端自动完成**（三层一致）：① 磁盘 .md 写入 ② .experience-index.yml 更新 ③ 向量索引（共享 KB collection）。

创建后必验证：
```
experience_read(kb_id, exp_id) → 确认字段正确 + vector_index.total_chunks ≥ 1
```

创建失败常见原因：
- `KB not found` → kb_id 错误，用 `kb_list` 确认
- 向量索引 0 chunks → 经验内容太短，补充 problem/solution

---

## 更新

```
experience_update(kb_id, exp_id, **fields)  # 只传需更新的字段
→ {success, experience: {...}}
```

**后端自动完成**：① 磁盘 .md 重写 ② 索引更新 ③ 向量重索引（内容变 → 向量重算）。

### 更新场景

| 场景 | 更新哪些字段 | 触发 |
|------|-------------|------|
| 冥想归纳补充新教训 | `key_lessons`, `solution`, `updated_at` | 冥想阶段4 |
| 文档内容更新经验过时 | `problem`, `solution`, `key_lessons` | E6 stale 检测 |
| 用户评审打分 | （自动）`rating_avg`, `review_count` | `experience_review` |
| 经验被应用 | （自动）`applied_count` | `experience_apply` |
| 补充 related_docs | `related_docs` | 文档移动后修复链接 |

> ⚠️ `updated_at` 不会自动刷新——内容更新时手动传 `updated_at=now`（或后端自动）。
> 向量重索引在内容字段（problem/solution/key_lessons/title）变更时自动触发。

---

## 删除

```
experience_delete(kb_id, exp_id)
→ {success, deleted_id}
```

**后端自动完成**：① 磁盘 .md 删除 ② 索引移除 ③ 向量删除。

### 删除决策矩阵

| 条件 | 动作 | 理由 |
|------|------|------|
| 测试污染（rating=0, applied=0, age>7d） | 直接删除 | 零价值残留 |
| 孤儿经验（related_docs 全失效）+ applied=0 | 直接删除 | 无引用无应用 |
| 孤儿经验 + applied>0 | 保留内容，清空 related_docs | 经验仍有用，断链修复 |
| 用户明确要求删除 | 直接删除 | 用户主权 |
| 过时但仍有参考价值 | `experience_update(status="archived")` | 软删除，检索不命中但保留 |

> 删除不可逆。删除前确认 `experience_read` 看内容，确认不是误删。

---

## 跟随文档移动：experience 的 related_docs 跟随

**这是最关键的联动**。当 `kb_doc_move` 移动文档时，引用该文档的经验会变孤儿。

### 后端现状（重要）

`kb_doc_move` **不会自动迁移经验**——它只处理文档三层（磁盘/树索引/KB元数据）。
经验索引 `.experience-index.yml` 中的 `related_docs` 路径**不会自动更新**。

**因此：文档移动后，Agent 必须手动修复经验链接。**

### 手动跟随流程（文档移动后强制执行）

```
触发：kb_doc_move(source_kb, doc_path, target_kb) 成功后

Step 1: 找出受影响的经验
  # 源 KB 中引用该文档的经验
  experience_list(source_kb) → 筛选 related_docs 含 doc_path 的经验

Step 2: 决策每条经验的去向
  对每条 affected_exp:
    ├─ 经验核心内容与文档强绑定（文档是唯一证据来源）
    │   → 经验也迁移到 target_kb：
    │     a) experience_read(source_kb, exp_id) → 读全部内容
    │     b) experience_create(target_kb, **content, related_docs=[新路径])
    │     c) experience_delete(source_kb, exp_id)
    │     d) 验证：experience_read(target_kb, new_exp_id)
    │
    ├─ 文档只是参考，经验可独立存在
    │   → 经验留原库，更新 related_docs 路径：
    │     experience_update(source_kb, exp_id,
    │       related_docs=[旧路径→新跨库路径 或 移除])
    │
    └─ 经验引用了多个文档，部分移动
        → 更新 related_docs，替换移动的路径，保留未移动的
```

### 路径替换规则

```
文档移动：source_kb/old_doc.md → target_kb/new_doc.md
经验中的 related_docs 替换：
  旧：["source_kb/old_doc.md", "source_kb/other.md"]
  新：["target_kb/new_doc.md", "source_kb/other.md"]  # 只替换移动的
```

---

## 跟随 KB 移动：整个 KB 的经验迁移

当整个 KB 被重命名/移动/合并时（见 knowledgebase-manage skill），该 KB 下所有
经验自动跟随——因为经验存储在 KB 目录的 `experience/` 子文件夹内，KB 移动时
整个目录一起搬。

**但需注意**：
- **向量索引**需重建：KB 移动后 collection 命名可能变 → `kb_reindex(force=true)`
- **跨库引用**的指针经验：指向该 KB 的别库经验需更新路径

### KB 重命名后的经验修复

```
触发：KB 从 old_name 改为 new_name

Step 1: 该 KB 内经验自动跟随（目录搬迁）✓ 后端自动
Step 2: 向量重索引：
  kb_reindex(kb_id=new_name, force=true) → 重建 collection
Step 3: 跨库引用修复：
  # 找到别库中引用旧 KB 路径的经验
  experience_search_global(query="old_name") → 检查 related_docs
  → experience_update(别库, exp_id, related_docs=[新路径])
Step 4: 验证：
  experience_list(new_name) → 确认经验数量未变
  experience_search_vector(new_name, "测试查询") → 确认检索正常
```

---

## 验证清单：每次操作后

```
创建后：
□ experience_read(kb_id, exp_id) 字段正确
□ vector_index.total_chunks ≥ 1
□ .experience-index.yml 中新经验存在

更新后：
□ experience_read 确认更新字段已生效
□ 内容更新则 vector_index.indexed_at 已刷新
□ related_docs 路径仍存在（kb_doc_read 验证）

删除后：
□ experience_read 返回 not found
□ experience_list 数量减1
□ （向量删除是 fire-and-forget，可能延迟）

移动后：
□ 源库：affected 经验已处理（迁移或更新路径）
□ 目标库：迁移的经验 experience_read 正常
□ related_docs 全部指向真实存在的文档
□ 跨库引用路径已更新
```
