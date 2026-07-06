---
name: knowledgebase-organize
description: >
  Full collection restructuring engine. O1→O13 workflow: survey every KB,
  read document content to classify true domains, categorize KBs (proper/
  test/empty-parent/empty-orphan/overlapping/misclassified), auto-process
  empty KBs, content-driven document re-classification (O3b), execute
  merges/moves/renames/descriptions, verify each change, produce structured
  report, split oversized documents, auto-create sub-KBs when KB grows
  (O10, lowered threshold ≥5 docs), batch-fix descriptions to be
  Agent-locatable (O11), audit vector index coverage and reindex missing
  docs (O12), and clean YAML/JSON redundancy with disk↔YAML↔JSON↔vector
  four-way consistency (O13). Invoked by Archival when the collection
  needs deep reorganization.
  Trigger keywords: 整理, 清洗, 重组, 审计, 重构, 盘点, 全面梳理,
  organize, restructure, audit collection, cleanup KB, reorganize,
  清洗知识库, 整理知识库, 重建索引, 重新分类, 大扫除,
  看看哪里有问题, 有哪些问题, consolidation.
---

# Knowledge Organize — Full Collection Restructuring (v4)

Invoked by Archival when the scenario is diagnosed as **Organize**
(全盘整理, 整理, 清洗, 审计, audit, restructure, cleanup, reorganize).

This is the deep reorganization engine. Survey every KB, read content,
and restructure so the collection reflects the truth.

**v4 五大核心增强：**
1. **O3b 内容驱动重归类** — 每个文档读真实内容，自动移动到正确KB
2. **O10 子KB自动创建阈值降低** — ≥5文档+≥3子域 即触发二次归档
3. **O11 Description 批量修正** — O2-E 检测问题后自动用子Agent重写
4. **O12 向量索引覆盖率审计** ⭐ — 检测未索引文档 + 补索引 + 清孤儿collection
5. **O13 YAML/JSON 冗余清理** ⭐⭐ — 磁盘↔YAML↔JSON↔向量库 四向一致性

## O1 — Full Survey (KB + Experience)

```
kb_list()         → all KBs with names, descriptions, document counts
kb_tags_list()    → all registered tags
fs_get_tree(include_files=True, max_depth=0)  → full structural view
```

### ⚠️ O1-key — 关键工具调用约定（避免 400 错误）

**`kb_doc_read` 的 doc_path 参数规则（实测确认）：**
- 当提供 `kb_id` 时，`doc_path` 必须是 **bare filename**（如 `readme.md`），
  **不能带路径前缀**（如 `KB/readme.md` 会报 400 "path is required"）
- 当不提供 `kb_id` 时，用 `path` 参数传完整相对路径（如 `KB/readme.md`）

```python
# ✅ 正确（kb_id + bare filename）
kb_doc_read(kb_id="uuid", doc_path="01-paper.md", max_chars=800)

# ❌ 错误（带路径前缀 + kb_id → 400）
kb_doc_read(kb_id="uuid", doc_path="KB-Name/01-paper.md", max_chars=800)

# ✅ 正确（无 kb_id，用 path 参数）
kb_doc_read(path="KB-Name/01-paper.md", max_chars=800)
```

**`kb_doc_update_meta` / `kb_doc_update_tags` / `kb_doc_delete` / `kb_doc_move` 同理**：
- 提供 `kb_id` 时，`doc_path` 用 bare filename
- `kb_doc_move` 的 `doc_path` 也用 bare filename（源），`target_kb_id` 是目标 UUID

**其他工具：**
- `kb_create(name, description, parent_id)` — parent_id 可选，用于子KB
- `kb_update(kb_id, name?, description?)` — kb_id 接受 UUID 或 path
- `kb_get_documents(kb_id)` 返回的 `doc.path` 是完整路径，但传给 `doc_path` 参数时要取 `doc.name`（bare filename）

### O1-E — Experience Survey

For each KB in `kb_list()`:
```
experience_list(kb_id)          → list all experiences
experience_summary(kb_id)       → statistics (total, by_category, by_severity)
```
Check for orphaned `{KB_PATH}/experience/` dirs whose KB was deleted.

## O2 — Evaluate Every KB

For each KB, evaluate these metrics:

| Metric | How to evaluate | Red flag |
|--------|----------------|----------|
| Name quality | Meaningful? Describes the domain? | Gibberish: "213", "333333", "test" |
| Description quality | Does it describe the domain? **基于真实内容**？ | Empty, "test", meaningless, "Parsed from..." |
| Document count | How many docs inside? | 0 = stale → ask user or delete |
| **Experience health** | Are exps consistent with KB domain? | scenario=test, empty title, 0 rating |
| Domain match | Do the docs match the KB name? | KB says "AI" but doc content is energy |
| Overlap | Same content in another KB? | Duplicate domain coverage |
| Vector coverage | What % docs have vector_index set? | <50% → prompt reindex |
| **Oversized docs** | `file_size` per doc | >50KB or >2000 lines → flag for O9 smart split |
| **Doc description vs content** | description 中的关键断言是否在内容中？ | description 说 "MetaGPT" 但内容是 Generative Agents → 必须修正 |

For each KB with documents:
- Read 1-2 documents: `kb_doc_read(kb_id, <doc>, max_chars=300)`
- Classify the KB's TRUE domain based on content evidence, not its name.

### O2-E — Description 真实性审计（必做）⭐

**遍历每个文档，验证 description 与真实内容是否一致：**

```
for each doc in kb_get_documents(kb_id):
    desc = doc.description
    # ⚠️ doc_path 用 bare filename (doc.name)，不是 doc.path
    content_preview = kb_doc_read(kb_id, doc.name, max_chars=500)

    # 检测规则
    issues = []

    # 1. placeholder description
    if desc in ["test", "文档", "资料", ""] or desc.startswith("Parsed from"):
        issues.append("placeholder-description")

    # 2. 关键断言未在内容中出现
    # 提取 description 中的方法名/数据/术语，逐一在 content_preview 中验证
    key_terms = extract_key_terms(desc)  # 例如 ["CNN-LSTM", "94.5%", "磨煤机"]
    for term in key_terms:
        if term NOT in content_preview:
            issues.append(f"term-mismatch: {term}")

    # 3. 文件名 vs 实际标题
    actual_title = extract_title_from_content(content_preview)
    if doc.name suggests "MetaGPT" but actual_title contains "Generative Agents":
        issues.append("filename-content-mismatch ⚠️")

    if issues:
        # 用子 Agent 重新生成 description
        Agent(
          subagent_type="general-purpose",
          prompt="""读 {doc.name} 的前 2000 字符，生成真实的 description。
          当前 description 有问题: {issues}。
          输出 JSON: title/domain/methods/scenario/suggested_description"""
        )
        # 用真实 description 更新（doc_path 用 bare filename doc.name）
        kb_doc_update_meta(kb_id, doc.name, description="<子Agent生成的真实description>")
```

**子 Agent 批量审计**（节省主上下文）：
- 一个子 Agent 可以处理一个 KB 内的所有文档
- 主 Agent 只接收最终的 issues 列表和修正后的 descriptions
- 对每个 KB 都执行一次 O2-E，确保所有 description 与内容一致

## O3 — Categorize Every KB

| Category | Characteristics | Action |
|----------|----------------|--------|
| **Proper domain KB** | Meaningful name + description + matching content | Keep. May offer rename/rediscribe. Auto-index missing docs. |
| **Test/scratch** | Gibberish name, meaningless description | Merge content (if any) into an existing KB, delete shell |
| **Empty: parent container** | 0 docs BUT has child sub-KBs | **Keep** as container. Update description to reference sub-KBs. ✅ 合理的空KB |
| **Empty: orphan stale** | 0 docs, no children, no clear purpose | **Auto-delete** (确认无经验/无引用后). 不再只询问用户 |
| **Domain overlap** | Same domain as another KB | Merge into the better-named KB |
| **Misclassified** | KB name says X, content is Y | Move docs to correct KB, rename or delete shell |

### O3-Auto — 空KB自动处理决策（强化）⭐

```
for each KB with doc_count == 0:
    has_children = (fs_get_children(kb_id).count > 0)
    has_experiences = (experience_list(kb_id).count > 0)
    is_recent = (kb.created_at > 7_days_ago)
    referenced = any other KB.description mentions this KB.name

    if has_children:
        → KEEP as parent container
        → UPDATE description to: "[Parent domain] container. Sub-KBs: [list with topics]"
        → 这是合理的空父KB，不要删除！

    elif has_experiences:
        → KEEP (经验有保留价值)
        → 但标注 "orphan experiences — consider migrate"

    elif is_recent AND referenced:
        → KEEP as placeholder (新创建或被引用)

    else:
        → ⚠️ 真正的孤儿空KB
        → AUTO-DELETE via kb_delete(kb_id)
        → 报告: "Deleted empty orphan KB '{name}' (0 docs, 0 exps, no children)"
```

## O3b — 文档真实领域归类（内容驱动）⭐⭐

> **核心思想**：每个文档都应该在它**真实领域**的 KB 里，而不是创建时随手放的 KB。
> 这一环节读取每篇文档的真实内容，判断它的真实领域，如果当前 KB 不匹配则移动。

```
for each KB in kb_list():
    for each doc in kb_get_documents(kb_id):
        # Step 1: 读文档真实内容
        # ⚠️ 注意：kb_doc_read 提供 kb_id 时，doc_path 用 bare filename (doc.name)
        content = kb_doc_read(kb_id, doc.name, max_chars=800)
        current_kb_name = kb.name
        current_kb_desc = kb.description

        # Step 2: 用子 Agent 判断真实领域（批量处理省主上下文）
        Agent(
          subagent_type="general-purpose",
          prompt="""分析以下文档内容，判断它的真实领域。

          文档名: {doc.name}
          当前所在KB: {current_kb_name} ({current_kb_desc})
          内容前 800 字符:
          {content}

          所有候选 KB:
          {kb_list_with_descriptions}

          输出 JSON:
          {
            "doc_true_domain": "真实领域（设备/方法/主题）",
            "doc_true_subdomain": "真实子领域",
            "current_kb_match": true/false,
            "best_target_kb_id": "最匹配的KB UUID",
            "best_target_kb_name": "最匹配的KB名",
            "reason": "为什么这个KB最匹配（1句话）",
            "scenario": "该文档适用的场景"
          }"""
        )

        # Step 3: 如果不匹配，移动到正确的KB
        # ⚠️ kb_doc_move 的 doc_path 用 bare filename (doc.name)
        if NOT result.current_kb_match AND result.best_target_kb_id:
            kb_doc_move(doc_path=doc.name, target_kb_id=result.best_target_kb_id)
            report: "Moved '{doc.name}' from {current_kb_name} → {best_target_kb_name} ({reason})"

        # Step 4: 如果没有任何现有KB匹配，标记为"需要新建KB"
        if result.best_target_kb_id is None:
            → flag for new-KB-creation in O10
```

**子 Agent 批量优化**：一个子 Agent 处理一个 KB 的全部文档（10-20篇），
主 Agent 只接收"移动指令清单"，大幅节省上下文。

### O3b-R — 重归类后验证

```
# 移动后重新检查每个 KB 的内容一致性
for each KB that had docs moved in/out:
    new_doc_count = kb_get_documents(kb_id).count
    if KB now has docs all from same sub-domain:
        → KB description needs update to reflect refined focus
        → re-run O2-E description audit on this KB
```

### O3-E — Experience Alignment

For each experience found:

| Condition | Action |
|-----------|--------|
| scenario=test or title is test gibberish | Delete (test residue) |
| rating=0, key_lessons empty, applied=0 | Flag as draft → ask user |
| related_docs paths stale after KB rename | Update via experience_update() |

## O4 — Execute

### Merge A into B
```
docs = kb_get_documents(A.kb_id)
for each doc:
    kb_doc_move(doc.doc_path, B.kb_id)
# Also migrate experiences (if any) — preserve credibility data
exps_resp = experience_list(kb_id=A.kb_id)
for exp in exps_resp.experiences:
    exp_full = experience_read(kb_id=A.kb_id, exp_id=exp.id)
    exp_data = exp_full.experience
    experience_create(
        kb_id=B.kb_id, title=exp_data.title, scenario=exp_data.scenario,
        category=exp_data.category, problem=exp_data.problem,
        solution=exp_data.solution, result=exp_data.result,
        key_lessons=exp_data.key_lessons, tags=exp_data.tags,
        severity=exp_data.severity, related_docs=exp_data.related_docs,
        prerequisites=exp_data.prerequisites, metrics=exp_data.metrics,
    )
    # ⚠️ CRITICAL: experience_create resets applied_count/rating_avg to 0.
    # After creating, manually replay apply & review records to restore credibility.
    # Check if original has applied_count > 0:
    if exp_data.applied_count > 0:
        experience_apply(kb_id=B.kb_id, exp_id=<new_exp_id>,
            user="merge-migration", context="merged from {A.kb_id}",
            result=exp_data.result)
    # Check if original has reviews (rating_avg > 0):
    if exp_data.rating_avg > 0:
        experience_review(kb_id=B.kb_id, exp_id=<new_exp_id>,
            reviewer="merge-migration",
            rating=exp_data.rating_avg,
            comment=f"Migrated from {A.kb_id}. Original: applied={exp_data.applied_count}, rating={exp_data.rating_avg}")
    experience_delete(kb_id=A.kb_id, exp_id=exp.id)
kb_delete(A.kb_id)    # only AFTER all docs + experiences moved
```

### Move misclassified doc
```
kb_doc_move(doc_path="SourceKB/doc.md", target_kb_id="target-UUID")
```
**After moving**: check if any experience in the target KB has `related_docs`
that reference the doc's old path. If so, update:
```
experience_update(target_kb_id, exp_id, related_docs=["NewKB/new-path.md"])
```

### Rename/rediscribe KB
```
kb_update(kb_id, name="New-Name", description="<1-3 sentences>")
```
**Bug**: path won't refresh. Use UUID for subsequent calls.
**Experience impact**: related_docs in experiences still reference OLD path.
After renaming, update all affected experiences:
```
exps = experience_list(kb_id)
for exp in exps.experiences:
    old_related = exp.related_docs
    if any(doc.startswith("Old-Name/") for doc in old_related):
        new_related = [doc.replace("Old-Name/", "New-Name/") for doc in old_related]
        experience_update(kb_id, exp.id, related_docs=new_related)
```

### Index documents (if vector coverage < 100%)
```
# For each KB with unindexed docs:
kb_get_documents(kb_id) → filter for doc_paths where vector_index is missing
kb_batch_index(kb_id, unindexed_doc_paths)
```

### Rename/rediscribe
```
kb_update(kb_id, name="New-Name", description="<1-3 sentences>")
```
**Bug**: path won't refresh. Use UUID for subsequent calls.

### Delete empty KBs (confirm first unless Module Mode)
```
kb_delete(kb_id)
```

### Delete test documents
```
kb_doc_delete(kb_id, doc_path)
kb_doc_batch_delete(kb_id, ["KB/doc.md"])    # ⚠️ MUST use full paths
```

### Fix document descriptions (read content first, never guess)
```
kb_doc_update_meta(kb_id, doc_path, description="<1-2 sentences from content>")
```

### Fix KB descriptions
```
kb_update(kb_id, description="<1-3 sentences: domain + content types + language>")
```

### Apply missing tags
```
kb_doc_update_tags(kb_id, doc_path, ["tag1", "tag2"])
```

## O5 — Verify Each Change

After each mutation (move, delete, merge, rename, update), immediately verify:
- **For moves**: `kb_get_documents(target_kb_id)` → confirm doc arrived
- **For deletes**: `kb_get_documents(kb_id)` or `fs_get_tree()` → confirm removal
- **For renames**: `kb_list()` → check new name reflects
- **For merges**: verify source KB is gone + target KB has combined docs
- **For reindex**: `kb_search_stats(kb_id)` → check chunk_count increased
- **For experience updates**: `experience_read(kb_id, exp_id)` → verify content
- **For .tree-fs.json integrity**: `fs_get_tree()` → confirm JSON parseable

## O6 — Orphan Cleanup

Check for orphaned experience directories:

1. List all directories under the storage root (fs_get_tree)
2. Cross-reference against KB paths from kb_list()
3. For any experience/ directory whose KB no longer exists:
   - List its experiences: read .experience-index.yml
   - Report to the user and delete if confirmed

## O7 — Integrity Report

Generate a structured summary with a **quantitative scorecard**:

```
## Collection Health Report

### Scorecard
  ├── Tag Coverage:    X/30  (tagged docs / total docs × 30)
  ├── Description Quality: X/25  (good descriptions / total × 25)
  ├── Uniqueness:      X/25  (unique docs / total × 25)
  └── KB Structure:    X/20  (proper-named KBs / total × 20)
  ───────────────────────
  TOTAL: X/100

### Overview
- Total KBs: N, Total Docs: N
- Unique documents: N (duplicates: N)
- Total Tags: N, Orphan tags: N

### Actions Completed
- KBs Deleted: N (list)
- KBs Merged: N (list)
- Documents Moved: N
- Descriptions Updated: N
- Tags Applied: N
### Remaining Issues
- Orphan tags (no tool to delete): list
- Weak descriptions: list
```

## O8 — Tag Hygiene Audit

Check the health of the tag vocabulary.

### O8a — Survey
```
kb_tags_list()         → all tags
```

### O8b — Check Each Tag
For each tag:
```
kb_doc_get_by_tag(tag)  → count of documents using this tag
```

Flag these issues:
- **Orphan tags**: 0 documents use this tag (can't be deleted — MCP limitation)
- **Near-duplicate tags**: pairs like "ML" / "machine-learning", "CNN" / "CNN-LSTM"
- **Low-usage tags**: tags used on only 1 document — too specific?
- **Generic tags**: "test", "doc", "misc", "important"

### O8c — Report
```
Tag Health:
  Total tags: N
  Orphan tags: N (no documents) — cannot delete, no MCP tool
  Low-usage tags (1 doc): N
  Near-duplicate pairs: N
  Suggestions:
  - "tag-a" and "tag-b" should be merged (kb_doc_update_tags to replace)
```

### O8d — Orphan Tag Resolution

When you find orphan tags (tags with 0 documents), use this workaround:

1. For orphan tag "dead-tag":
   - Check if the tag was used on a now-deleted document's KB
   - If the KB still has related documents: create a replacement tag with
     `kb_tag_create("rescue-tag")` and assign it via `kb_doc_update_tags()`
   - This "migrates" the usage away from the orphan

2. If no documents remain in the orphan tag's original domain:
   - Report: "Tag 'dead-tag' is orphaned with no related content. 
     It remains in the registry (no MCP tool to delete orphan tags)
     but does not affect search or operations."

3. If the orphan is a misspelling and you find documents that should use it:
   - Apply `kb_doc_update_tags(kb_id, doc_path, ["correct-tag"])` to the right docs
   - The orphan stays in the registry but is now unused and harmless

## O9 — Smart Document Chunk Splitting

When you find an oversized document (>50KB file_size or >2000 estimated lines),
offer to split it into smaller logical documents. This improves readability
and makes vector search more precise. Flagged in C2 table above.

[Splitting details unchanged — see existing O9 section]

---

## O10 — Hierarchical KB Health Check & Auto Sub-KB Creation ⭐⭐

**This is the proactive sub-KB creation engine.** 当 KB 文档变多时，自动二次归档为子KB结构，
让 description 更精确、检索更聚焦。

### O10a — Identify Candidates for Sub-KB Creation（强化阈值）

> **关键改进**：从"≥8文档"降低到"≥5文档或>500KB"，更积极地创建子KB。

For every "Proper domain KB" in O3:

```
kb_get_documents(kb_id) → docs
doc_count = docs.count
total_size_kb = sum(doc.file_size for doc in docs) / 1024

# 读取每个文档的真实子域（用子Agent批量处理省上下文）
sub_domains = {}
for doc in docs:
    content = kb_doc_read(kb_id, doc.path, max_chars=500)
    sub_domain = Agent_classify_subdomain(content, doc.name)
    sub_domains[sub_domain].append(doc)

distinct_subdomains = sub_domains.keys()

# 触发子KB创建的阈值（任一满足）
SHOULD_SPLIT = (
    (doc_count >= 8 AND len(distinct_subdomains) >= 2) OR          # 原: ≥8文档+≥2子域
    (doc_count >= 5 AND len(distinct_subdomains) >= 3) OR          # 新: ≥5文档+≥3子域（细化）
    (total_size_kb >= 500 AND len(distinct_subdomains) >= 2) OR    # 新: 内容总量≥500KB
    (doc_count >= 10)                                                # 新: 绝对阈值（无论子域数）
)

if SHOULD_SPLIT:
    → Proceed to O10b (auto-create sub-KBs)
else:
    if doc_count >= 4:
        → Flag for re-evaluation: "接近子KB创建阈值，下次整理时再评估"
    else:
        → "KB has {doc_count} docs — below sub-KB threshold"
```

### O10b — Auto-Create Sub-KBs（二次归档执行）

对每个识别出的子域（≥2 文档才能成为子KB）：

```
for each sub_domain with >= 2 docs:
    # Step 1: 生成子KB名（基于子域关键词）
    sub_kb_name = generate_subkb_name(parent_kb.name, sub_domain)
    # 例如: "Polymer-Processing-Research" + "PET双拉" → "Polymer-Processing-PET-Biaxial"

    # Step 2: 用子Agent生成聚焦的子KB description
    sub_kb_desc = Agent(
      subagent_type="general-purpose",
      prompt="""为以下子KB生成聚焦的 description（基于真实文档内容）：

      父KB: {parent_name} ({parent_desc})
      子域: {sub_domain}
      该子域的文档列表（每个读前300字符）:
      {docs_with_previews}

      输出格式（A4b 子KB模板）:
      "[特定设备/子领域] + [核心技术方法] + [适用场景] + [{N}篇文档] + [语言]"
      """
    )

    # Step 3: 创建子KB
    sub_kb = kb_create(
        name=sub_kb_name,
        description=sub_kb_desc,
        parent_id=parent_kb.kb_id
    )

    # Step 4: 移动该子域的所有文档到新子KB
    for doc in sub_domains[sub_domain]:
        kb_doc_move(doc.path, sub_kb.kb_id)
        # 迁移关联经验（见 O4 Merge A into B 的经验迁移逻辑）
```

**子KB命名约定（强化）：**
```
<Parent-Domain>-<Specific-Sub-Domain>
# 示例:
# Polymer-Processing-Research → Polymer-Processing-PET-Biaxial
#                              → Polymer-Processing-PLA-Biodegradable
#                              → Polymer-Processing-PVA-Films
# Thermal-Power-Monitoring   → Thermal-Power-Coal-Mill
#                              → Thermal-Power-Fan-Diagnostics
```

### O10c — 单文档子域处理（避免单人文档）

```
# 子KB至少需要2文档。子域只有1文档的怎么办？
for sub_domain with exactly 1 doc:
    # 选项A: 保留在父KB（最相关子域作为兜底）
    → 保留在父KB，不创建单人子KB

    # 选项B: 合并到最近的兄弟子KB
    if exists a sibling sub-KB with similar sub-domain:
        → kb_doc_move to that sibling

# 原则: 子KB doc_count >= 2，否则不创建（O10b 的健康检查会捕获单人文档子KB）
```

### O10d — Update Parent KB Description After Sub-KB Creation

```
# 创建子KB后，父KB description 必须引用子KB结构
kb_update(
    kb_id=parent_kb.kb_id,
    description="[原父级 description]. Contains sub-KBs: " +
                "[{sub_kb_1.name}: {1句聚焦描述}], " +
                "[{sub_kb_2.name}: {1句聚焦描述}], ..."
)
# 这是关键——让 Search 的 Step 1 知道父KB是层级结构
```

### O10e — Merge Back Single-Doc Sub-KBs（反向优化）

对现有子KB做健康检查：

```
for each existing sub-KB with parent_id:
    doc_count = kb_get_documents(sub_kb.kb_id).count

    if doc_count == 0:
        → Delete empty sub-KB shell

    elif doc_count == 1:
        → ⚠️ 单文档子KB（太小）
        → Move doc back to parent: kb_doc_move(doc.path, parent_kb.kb_id)
        → kb_delete(sub_kb.kb_id)
        → 报告: "Merged back single-doc sub-KB '{name}' to parent"

    elif description same as parent OR description too vague:
        → Rewrite sub-KB description to be more focused (用子Agent)
```

### O10f — Verify Hierarchy

```
kb_list() → 确认 parent+children 结构正确
fs_get_tree(include_files=False, max_depth=3) → 可视化层级
kb_search_stats(parent_kb_id) → 确认向量索引覆盖所有子KB
# 关键: 每个子KB都有独立的向量 collection
```

### O10g — Sub-KB Optimization Report

```
🔄 子KB二次归档完成:

├── [Parent-KB] 拆分为 {N} 个子KB:
│   ├── [Sub-KB-1]: {聚焦 description} ({N} docs)
│   ├── [Sub-KB-2]: {聚焦 description} ({N} docs)
│   └── [Sub-KB-3]: {聚焦 description} ({N} docs)
│
├── 合并回父KB的单文档子KB: {N} 个
├── 删除的空子KB: {N} 个
├── 更新父KB description: ✅ 引用了 {N} 个子KB
└── 重新向量索引: {N} 个子KB

效果: Agent 检索时先读子KB精确 description，命中率提升 10x
```

When an oversized document is flagged in O2 (>50KB file_size or >2000 lines),
offer to split it into smaller logical documents for better readability and
more precise vector search.

**⚠️ 大文档拆分规范（同步自 Ingest A5b）：**

大文档拆分必须遵循以下原则，而非简单的"按行切成N份"：

1. **必须先读大纲再拆** — `head -c 3000` 或 `kb_doc_read(max_chars=3000)` 先读文档前部
   提取 `#`/`##` 章节标题结构，确定自然拆分点
2. **按章节逻辑拆分** — 每一块是一个完整的逻辑章节（引言/方法/结果/讨论），
   不是按行数等分。保留章节标题和子标题层级。
3. **每块独立 description** — 按 Ingest A4 规范为每块写独立的 description，
   说明该节的核心内容、方法、适用场景
4. **每块独立标签** — 继承原文档的通用标签 + 该节特有的领域标签
5. **每块用 kb_doc_create 入库** — 分块文档命名 `原文件名_s{N}_{节英文slug}.md`
6. **删除原始文档** — 所有分块成功创建并验证后，删除原大文档
7. **向量索引** — `kb_batch_index(force=true)` 重新索引所有分块

**完整拆分流程参考 Ingest A5b-0→A5b-9。**

**Ratio rule guard**: The "single doc >60% of KB total" check only activates
when the KB has ≥3 documents AND total KB content >50KB. On small KBs (1-2
docs or tiny content), this rule is skipped to avoid false positives.

### O9a — Confirm

```
"The document [name] is [size KB / N lines]. I can split it into [N] smaller
documents based on its section headings. Shall I proceed?"
```

### O9b — Read & Analyze

```
kb_doc_read(kb_id, doc_path, max_chars=50000, offset=0, limit=5000)
```

Agent analyzes the content to find logical split points:

| Signal | Split Point |
|--------|-------------|
| `# Title` or `## Section` | Strong chapter break — split here |
| `Abstract`, `Introduction`, `Method`, `Results`, `Conclusion` | Standard paper sections |
| `---` horizontal rule | Possible thematic shift |
| No structural markers | Every ~400 lines, try to find a natural sentence boundary |

### O9c — Create Chunks

For each chunk N of M:

```
kb_doc_create(
  kb_id=same_kb_id,
  name="original-name_part-N.md",
  content="<chunk content>",
  description="Part N/M: <section title> — <1-sentence summary>"
)
```

Copy tags:
```
kb_doc_update_tags(kb_id, "original-name_part-N.md", ["tag1", "tag2", ...])
```

### O9d — Remove Original

After ALL chunks created successfully:
```
kb_doc_delete(kb_id, original_doc_path)
```

### O9e — Verify

```
kb_get_documents(kb_id)             → N new docs visible, original gone
kb_batch_index(kb_id, [chunk_paths], force=true)  → rebuild vector index for chunks
kb_doc_read(kb_id, chunk_1_path, max_chars=300)   → spot-check content integrity
```

### O9f — Report

```
Smart Chunk Splitting Complete:
  Original: [name] ([size])
  Split into: [N] chunks
  - Part 1: [section title] — [summary]
  - Part 2: [section title] — [summary]
  - ...
  Vector index rebuilt: ✅
  KB now has [new doc count] documents
```

---

## O11 — Description 批量修正执行流程 ⭐⭐

> **配套 O2-E**：O2-E 检测 description 问题，O11 是修正执行。
> 这一环节确保所有文档/KB 的 description 都能让 Agent **只读 description 就能定位知识**。

### O11a — 收集所有有问题的 description

```
# O2-E 已检测问题，O11a 汇总成修复队列
fix_queue = []

for each doc that has issues from O2-E:
    fix_queue.append({
        type: "doc-description",
        kb_id, doc_path,
        current_desc: doc.description,
        issues: [...],  # placeholder / term-mismatch / filename-mismatch
        content_path: doc.markdown_path or kb_doc_read(...)
    })

for each KB with weak/vague description (O2):
    fix_queue.append({
        type: "kb-description",
        kb_id,
        current_desc: kb.description,
        issue: "vague" / "outdated" / "missing-subkb-reference"
    })

# 按KB分组（让每个子Agent处理一个KB，最高效）
grouped = group_fix_queue_by_kb(fix_queue)
```

### O11b — 子Agent批量重写 description（省主上下文）

对每个需要修复的KB，**一个子Agent处理该KB内所有文档**：

```
for each (kb_id, fixes) in grouped:
    Agent(
      subagent_type="general-purpose",
      prompt="""你是知识库 description 修复专家。

      ## 任务
      为以下文档/KB 基于真实内容重写 description，遵循 A4 规范。

      ## A4 description 规范
      [研究对象] + [方法/技术] + [解决什么问题/适用场景] + [关键结论/数据] + [语言]
      要求：让 Agent 只读这一句 description 就能 100% 判断该文档/KB 是否相关。

      ## 待修复清单（该KB内）
      {for each fix:
        - doc_path: {path}
        - 当前 description: {current}
        - 问题: {issues}
        - 内容前 800 字符: {content_preview}
      }

      ## 输出 JSON 数组
      [
        {
          "doc_path": "...",
          "verified_title": "从内容提取的真实标题",
          "new_description": "基于真实内容的 A4 格式 description",
          "key_terms": ["新description中提到的关键术语"],
          "confidence": "high/medium/low"
        },
        ...
      ]

      ## 关键要求
      1. 必须读 content_preview，不要根据文件名猜测
      2. description 必须包含具体的方法名/设备名/数据（不能模糊）
      3. 如果文件名和内容不一致（如 metagpt_paper.md 实际是 Generative Agents），
         按**真实内容**写 description
      4. 标注 confidence：high=内容明确，low=内容模糊需人工确认
      """
    )
```

### O11c — 主Agent应用修复结果

```
for each result in subagent_output:
    if result.confidence == "high":
        # 自动应用
        kb_doc_update_meta(
            kb_id=result.kb_id,
            doc_path=result.doc_path,
            description=result.new_description
        )
        # 验证：新description中的key_terms是否在内容中
        content = kb_doc_read(kb_id, result.doc_path, max_chars=1000)
        for term in result.key_terms:
            if term NOT in content:
                → ⚠️ "新description仍然有term-mismatch，标记为low-confidence"
                → 不应用，保留原description，加入人工确认队列

    elif result.confidence == "low":
        # 加入人工确认队列
        manual_review_queue.append(result)
```

### O11d — KB级别 description 修正

```
for each KB with weak description:
    # 综合该KB所有文档的领域，重写KB description
    docs = kb_get_documents(kb_id)
    doc_domains = [Agent_extract_domain(doc) for doc in docs]

    Agent(
      subagent_type="general-purpose",
      prompt="""重写这个KB的 description，综合所有文档的真实领域。

      KB名: {kb_name}
      当前 description: {current_desc}
      问题: {issue}
      KB内所有文档（name + 真实领域摘要）:
      {docs_with_domains}

      ## 输出
      如果KB有子KB: "parent-container" 格式（引用子KB）
      如果KB无子KB: "domain-kb" 格式（A4b 父级KB模板）

      new_kb_description: "..."
      """
    )

    kb_update(kb_id, description=new_kb_description)
```

### O11e — Description 质量验证

修复后对所有 description 做最终质量检查：

```
for each doc/KB with new description:
    # 检查 1: 长度合理（20-300字符）
    if len(description) < 20:
        ⚠️ "Description 过短，信息不足"
    elif len(description) > 300:
        ⚠️ "Description 过长，需要精简"

    # 检查 2: 包含具体术语（非空泛）
    vague_words = ["文档", "资料", "论文", "test", "doc", "information"]
    if any(w in description.lower() for w in vague_words) AND len(description) < 50:
        ⚠️ "Description 仍含空泛词"

    # 检查 3: Agent 可定位性测试
    # 模拟 Agent 读 description 能否判断相关性
    relevant_query = "假设用户问 [{doc真实主题}]，Agent 读这条 description 能 100% 确定相关吗？"
    if NOT yes:
        ⚠️ "Description 不足以让 Agent 定位"

# 所有 ⚠️ 进入最终报告
```

### O11f — Description 修正报告

```
📝 Description 修正报告:

共检查: {N} 文档 + {M} KB 的 description
需修复: {X} 项

已自动修复 (high-confidence):
├── {doc1}: "旧desc..." → "新desc（真实内容）..."
├── {doc2}: "Parsed from..." → "基于内容的方法/场景描述"
└── {kb1}: "vague..." → "包含子KB引用的精确描述"

待人工确认 (low-confidence):
├── {doc3}: 内容模糊，建议人工确认
└── {doc4}: 多语种混合，需判断主语言

质量验证: {Y}/{X} 通过 Agent 可定位性测试
```

---

## O12 — 向量索引覆盖率审计 ⭐

> **核心问题**：文档入库后未必都进了向量数据库。未索引的文档在 `kb_search_vector` 中
> 永远搜不到，等于"隐形文档"。这一环节确保每篇文档都有向量索引。

### O12a — 检测未索引文档

```
unindexed = []

for each KB in kb_list():
    docs = kb_get_documents(kb_id)
    for doc in docs:
        has_vector = (
            doc.vector_index is not None
            AND doc.vector_index.total_chunks > 0
        )
        if NOT has_vector:
            unindexed.append({
                kb_id, kb_name,
                doc_name: doc.name,
                doc_path: doc.path,
                reason: "no-vector-index" or "zero-chunks"
            })

# 对比 kb_search_stats 的 collection chunk_count
stats = kb_search_stats()
for each collection in stats.collections:
    if collection.chunk_count == 0 AND KB has docs:
        ⚠️ "Collection 空：{kb_name} 有文档但 0 chunks"
```

### O12b — 批量补索引

```
if unindexed:
    # 按 KB 分组批量索引
    by_kb = group_by(unindexed, kb_id)
    for kb_id, docs in by_kb:
        doc_paths = [d.doc_path for d in docs]
        kb_batch_index(kb_id, doc_paths, force=true)

    # 验证：重新检查 vector_index
    for doc in unindexed:
        refreshed = kb_get_documents(doc.kb_id).find(doc.doc_name)
        if refreshed.vector_index AND refreshed.vector_index.total_chunks > 0:
            ✅ "已索引: {doc.name} ({chunks} chunks)"
        else:
            ⚠️ "索引失败: {doc.name} — 可能内容为空或 embedding 服务异常"
```

### O12c — 向量孤儿检测

```
# 反向问题：向量库有 chunks，但文档已从 KB 删除
stats = kb_search_stats()
for collection in stats.collections:
    kb_id = extract_kb_id(collection.name)
    if kb_exists(kb_id):
        kb_doc_count = kb_get_documents(kb_id).count
        if kb_doc_count == 0 AND collection.chunk_count > 0:
            ⚠️ "向量孤儿：collection {name} 有 {N} chunks 但 KB 无文档"
            → 清理：kb_reindex(kb_id) 或直接 delete_kb 清理 collection
```

### O12d — 索引一致性报告

```
📊 向量索引覆盖率:
  总文档: {N}
  已索引: {X} ({percent}%)
  未索引: {Y}  ← 已补索引
  向量孤儿 collection: {Z}  ← 已清理

所有文档现在都能被 kb_search_vector 检索到 ✅
```

---

## O13 — YAML/JSON 冗余条目清理 ⭐⭐

> **核心问题**：知识库底层有两个索引文件——`.knowledge-base.yml`（每KB）和
> `.tree-fs.json`（全局树）。长期增删改后会出现：
> 1. **孤儿条目**：YAML 有文档条目，但磁盘文件已删（kb_doc_move 后常残留）
> 2. **父KB污染**：父KB YAML 包含了子KB的文档（应为子KB独有）
> 3. **缺失条目**：磁盘有文件但 YAML/JSON 无索引（搜不到）
> 4. **路径无效**：条目的 path 字段指向不存在文件
>
> 这些冗余会让 kb_get_documents 返回错误数据，污染检索和整理流程。

### O13a — 三向交叉验证（磁盘 ↔ YAML ↔ JSON）

```
STORAGE = "web/storage/tree-file-system"

for each KB:
    yml_path = "{STORAGE}/{kb_path}/.knowledge-base.yml"
    disk_files = list_files("{STORAGE}/{kb_path}/*.md")  # 排除子目录

    # 解析 YAML
    yaml_docs = parse_yaml(yml_path).documents

    # 三向对比
    disk_set = set(disk_files)
    yaml_set = set(d.path for d in yaml_docs)
    tree_set = find_kb_docs_in_tree_json(kb_path)

    orphans_yaml = yaml_set - disk_set        # YAML有，磁盘无
    missing_yaml = disk_set - yaml_set        # 磁盘有，YAML无
    tree_mismatch = yaml_set.symmetric_difference(tree_set)
```

### O13b — 清理孤儿条目（YAML有条目，磁盘无文件）

> 典型场景：`kb_doc_move` 后旧 KB 的 YAML 残留了文档条目，但文件已移走。

```
# ⚠️ MCP 工具 kb_doc_delete 对不存在的文件会返回 "Not found"
# 所以需要直接编辑 YAML 文件

for each orphan in orphans_yaml:
    # 从 YAML documents 列表删除该条目
    yaml_docs = [d for d in yaml_docs if d.path != orphan]
    report: "删除孤儿索引: {orphan} (磁盘无文件)"

# 写回 YAML
write_yaml(yml_path, yaml_docs)
```

**安全实现（Python 脚本）：**
```python
import yaml, pathlib
yml = pathlib.Path(f"{STORAGE}/{kb_path}/.knowledge-base.yml")
data = yaml.safe_load(yml.read_text(encoding='utf-8'))
original = len(data.get('documents', []))
data['documents'] = [
    d for d in data.get('documents', [])
    if (pathlib.Path(f"{STORAGE}") / d['path'].replace('\\','/')).exists()
]
removed = original - len(data['documents'])
if removed:
    yml.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
    print(f"清理 {removed} 个孤儿条目")
```

### O13c — 清理父KB污染（父YAML含子KB文档）

> 典型场景：Academic-AI-Survey 父KB YAML 含了 12 篇论文，但这些论文
> 实际在 Academic-RAG-Research 等子KB里。父KB应只作容器，不存文档。

```
for each KB with childCount > 0 (是父KB):
    yaml_docs = parse_yaml(yml_path).documents
    disk_direct_files = list_files("{STORAGE}/{kb_path}/*.md")  # 仅直接子文件

    # 父KB YAML 中的文档，如果在子KB目录里也存在，则是污染
    polluted = []
    for doc in yaml_docs:
        doc_in_subkb = any(
            file_exists("{STORAGE}/{sub_kb_path}/{doc.name}")
            for sub_kb in get_child_kbs(kb_id)
        )
        if doc_in_subkb AND doc.path not in disk_direct_files:
            polluted.append(doc)

    # 从父YAML删除污染条目（子KB已有自己的索引）
    yaml_docs = [d for d in yaml_docs if d not in polluted]
    report: "父KB清理 {N} 个子KB污染条目"
```

### O13d — 补充缺失条目（磁盘有文件，YAML无索引）

```
for each missing in missing_yaml:
    # 磁盘有文件但 YAML 没索引 → 需要重新注册
    # 用 fs_upload_file 或 kb_doc_create 补索引
    content = read_file("{STORAGE}/{missing}")
    kb_doc_create(
        kb_id, name=basename(missing),
        content=content,
        description="recovered — needs O11 description fix"
    )
    report: "补充缺失索引: {missing}"
```

### O13e — .tree-fs.json 一致性修复

```
tree_json = parse_json("{STORAGE}/.tree-fs.json")

# 1. folders 列表与磁盘 KB 目录对比
disk_kbs = [d for d in list_dirs(STORAGE) if has_yml(d)]
tree_kbs = [f.path for f in tree_json.folders]

orphan_folders = tree_kbs - disk_kbs    # JSON有，磁盘无
missing_folders = disk_kbs - tree_kbs   # 磁盘有，JSON无

# 2. 修复：重建 tree-fs.json（从磁盘扫描 + 各KB YAML 聚合）
# 或用 fs_get_tree 重建
```

### O13f — 向量 collection 路径验证

```
# 验证 vector_index.collection 指向的 collection 真实存在
stats = kb_search_stats()
existing_collections = set(c.collection for c in stats.collections)

for each doc with vector_index:
    if doc.vector_index.collection NOT in existing_collections:
        ⚠️ "悬空向量索引: {doc.name} 指向不存在的 collection {coll}"
        → 重新索引: kb_batch_index(kb_id, [doc.name], force=true)
```

### O13g — 冗余清理报告

```
🧹 YAML/JSON 冗余清理报告:

孤儿条目（YAML有/磁盘无）:
├── {KB1}: 清理 {N} 个 (kb_doc_move 残留)
└── {KB2}: 清理 {M} 个

父KB污染（父YAML含子KB文档）:
├── Academic-AI-Survey: 清理 {N} 个子KB文档条目（子KB自有索引）
└── ...

缺失索引（磁盘有/YAML无）: 补充 {N} 个

.tree-fs.json:
├── 孤儿 folder 节点: 清理 {N} 个
└── 缺失 folder 节点: 补充 {N} 个

悬空向量索引: 修复 {N} 个

最终: 磁盘 ↔ YAML ↔ JSON ↔ 向量库 四方一致 ✅
```

### O13h — 验证四向一致

```
# 最终一致性检查
for each KB:
    disk_count = count_disk_md_files(kb_path)  # 直接子文件
    yaml_count = count_yaml_documents(kb_path)
    vector_count = count_docs_with_vector_index(kb_id)
    search_count = kb_search_stats(kb_id).chunk_count > 0 ? "OK" : "EMPTY"

    if disk_count == yaml_count == vector_count (或文档未索引已补):
        ✅ "{kb_name}: 四方一致 ({disk_count} docs)"
    else:
        ⚠️ "{kb_name}: 不一致 disk={d} yaml={y} vector={v}"
```

---

## CRITICAL RULES

1. **O2 (read content) is NOT optional**. Never classify a KB or write description by name alone.
2. **O2-E description 真实性审计必做** — 任何 "Parsed from..."、空、或与内容不一致的 description
   都必须用子 Agent 读取真实内容后重新生成。文件名可能是错的，只信任内容。
3. **O3-Auto 空 KB 自动处理** — 区分"父容器空KB"（保留）和"孤儿空KB"（自动删除）。
4. **O3b 文档真实领域归类必做** — 每个文档读真实内容，移动到正确KB。
5. **O10 子KB自动创建阈值降低** — ≥5文档+≥3子域 / ≥500KB / ≥10文档 任一满足即创建子KB。
6. **O11 description 批量修正必做** — O2-E 检测问题后，O11 必须执行修复并通过 O11e 验证。
7. **O12 向量索引覆盖率必审** ⭐ — 未索引文档必须 `kb_batch_index(force=true)` 补齐。
   未索引文档在向量搜索中"隐形"。反向也要清孤儿 collection。
8. **O13 YAML/JSON 四向一致性必查** ⭐⭐ — 整理最后必须验证 磁盘↔YAML↔JSON↔向量库 一致：
   孤儿条目、父KB污染、缺失条目、悬空向量。kb_doc_move/delete 会留 YAML 残留，
   必须用 Python 脚本直接清理。
9. Merges: move docs FIRST, delete SECOND. Deleting first loses data.
10. Confirm destructive operations unless Module Mode.
11. O5 (verify) catches mistakes. Do not skip.
12. O8 (tag audit) cannot delete orphan tags — MCP limitation.
13. **≥3 篇文档审计时用子 Agent**，主 Agent 只接收 issues 列表，保持上下文干净。

## 完整执行顺序（强化 v4）

```
整理任务执行流:
O1 全盘调研 (kb_list + fs_get_tree + tags + experiences)
  ↓
O2 评估每个KB (读内容)
  ↓
O2-E Description 真实性审计 (检测问题)
  ↓
O3 KB分类 (proper/test/empty/overlap/misclassified)
  ↓
O3-Auto 空 KB 自动处理 (父容器保留 / 孤儿删除)
  ↓
O3b 文档真实领域归类 (内容驱动移动到正确KB) ⭐
  ↓
O4 执行 (合并/移动/删除/重命名)
  ↓
O5 验证每次变更
  ↓
O6 孤儿清理
  ↓
O7 评分卡
  ↓
O8 标签审计
  ↓
O9 大文档智能拆分
  ↓
O10 子KB自动创建 (二次归档，阈值降低)
  ↓
O11 Description 批量修正执行
  ↓
O12 向量索引覆盖率审计 (补索引 + 清孤儿 collection) ⭐ 新增
  ↓
O13 YAML/JSON 冗余清理 (磁盘↔YAML↔JSON↔向量 四向一致) ⭐ 新增
  ↓
O14 图谱重建 ⭐⭐ 新增 — build_kb_graph(force=true) 重建本KB+子KB图谱
  ↓
最终报告 (含 O7 评分 + O10 子KB结构 + O11 修正 + O12/O13/O14 一致性)
```

## 三大核心能力保障

| 能力 | 保障环节 | 验证标准 |
|------|---------|---------|
| **所有内容归到正确位置** | O3b 文档真实领域归类 | 每个文档 current_kb_match=true |
| **没有空KB** | O3-Auto 空KB处理 | 只有父容器型空KB，无孤儿 |
| **多文档KB自动子KB细化** | O10 阈值降低触发 | ≥5文档KB自动二次归档 |
| **description 可定位知识** | O2-E + O11 + O11e | Agent 可定位性测试通过 |
| **所有文档都被向量索引** | O12 向量覆盖率审计 ⭐ | 未索引=0，无孤儿 collection |
| **索引文件无冗余/无悬空** | O13 四向一致性 ⭐ | 磁盘=YAML=JSON=向量库 |
| **所有文档都有知识图谱** | O14 图谱重建 ⭐⭐ | graph_count=doc_count，父子KB关联 |
