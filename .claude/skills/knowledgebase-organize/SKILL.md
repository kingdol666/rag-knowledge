---
name: knowledgebase-organize
description: >
  Full collection restructuring engine. O1→O9 workflow: survey every KB,
  read document content to classify true domains, categorize KBs (proper/
  test/empty/overlapping/misclassified), execute merges/moves/
  renames/descriptions, verify each change, produce structured report,
  and split oversized documents into smaller logical chunks.
  Invoked by Archival when the collection needs deep reorganization.
---

# Knowledge Organize — Full Collection Restructuring

Invoked by Archival when the scenario is diagnosed as **Organize**
(全盘整理, 整理, 清洗, 审计, audit, restructure, cleanup, reorganize).

This is the deep reorganization engine. Survey every KB, read content,
and restructure so the collection reflects the truth.

## O1 — Full Survey (KB + Experience)

```
kb_list()         → all KBs with names, descriptions, document counts
kb_tags_list()    → all registered tags
fs_get_tree(include_files=True, max_depth=0)  → full structural view
```

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
    content_preview = kb_doc_read(kb_id, doc.path, max_chars=500)
    
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
          prompt="""读 {doc.path} 的前 2000 字符，生成真实的 description。
          当前 description 有问题: {issues}。
          输出 JSON: title/domain/methods/scenario/suggested_description"""
        )
        # 用真实 description 更新
        kb_doc_update_meta(kb_id, doc.path, description="<子Agent生成的真实description>")
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
| **Empty stale** | 0 documents | Ask user → delete or keep as placeholder |
| **Domain overlap** | Same domain as another KB | Merge into the better-named KB |
| **Misclassified** | KB name says X, content is Y | Move docs to correct KB, rename or delete shell |

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

## O10 — Hierarchical KB Health Check & Sub-KB Optimization ⭐

**This step assesses the KB hierarchy.** After organizing content domain
cleanup, evaluate whether any KBs have grown large enough to benefit from
sub-KB structure. This is the proactive version of Ingest's A9.

### O10a — Identify Candidates for Sub-KB Creation

For every "Proper domain KB" in O3:

```
kb_get_documents(kb_id) → count
IF count >= 8:
    # Read each doc's opening to classify sub-domain
    for doc in kb_get_documents(kb_id):
        preview = kb_doc_read(kb_id, doc.doc_path, max_chars=300)
        classify sub-domain from content (equipment, method, or problem)
    
    distinct_subdomains = unique(sub-domains)
    IF distinct_subdomains >= 2:
        → Candidate for sub-KB creation
    
ELIF count >= 5 AND distinct_subdomains >= 3:
    → Candidate for sub-KB creation (growth room considered)
    → Flag for re-evaluation: "This KB has 5 docs across 3 sub-domains.
      Already worth considering sub-KB split for retrieval precision."
```

### O10b — Evaluate Existing Sub-KB Health

For KBs with `parent_id` (sub-KBs):

| Health Signal | Good | Warning |
|--------------|------|---------|
| doc_count | ≥ 2 | 1 (too small to be its own KB → consider merge back) |
| description specificity | Focused on sub-domain | Same as parent (defeats purpose) |
| tags consistency | All docs share a common theme | Docs spread across topics |
| cross-subKB gap | Peer sub-KBs cover distinct topics | Overlap between sub-KBs → merge |
| parent description | Mentions sub-KBs | No mention (update it) |

### O10c — Execute Sub-KB Operations

**Create Sub-KBs** (following the same pattern as Ingest A9):
```
sub_kb = kb_create(
    name="<ParentDomain>-<SubDomain>",
    description="<focused on specific sub-domain, NOT parent-level>",
    parent_id=parent_kb.kb_id
)
```

**Merge Small Sub-KBs Back** (doc count = 1):
```
for doc in kb_get_documents(small_sub_kb.kb_id):
    kb_doc_move(doc.doc_path, parent_kb.kb_id)
kb_delete(small_sub_kb.kb_id)
```

**Update Parent Description** after any hierarchy change:
```
kb_update(kb_id=parent_kb.kb_id, description="... Sub-KBs: [list]")
```

### O10d — Verify Hierarchy

```
kb_list() → confirm parent+children structure
fs_get_tree(include_files=False, max_depth=3) → visual hierarchy
kb_search_stats(parent_kb.kb_id) → confirm vector index health
```

### O10e — Report Hierarchy Changes

```
**Sub-KB Optimization Complete:**

├── [KB-Name]: split into [N] sub-KBs:
│   ├── [Sub-KB-1]: [description] ([N] docs)
│   ├── [Sub-KB-2]: [description] ([N] docs)
│   └── [Sub-KB-3]: [description] ([N] docs)
├── Merged back: [N] small sub-KBs ([names])
├── Updated parent descriptions: [N] KBs
└── Reindexed: [N] KBs for vector search
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

## CRITICAL RULES

1. **O2 (read content) is NOT optional**. Never classify a KB or write description by name alone.
2. **O2-E description 真实性审计必做** — 任何 "Parsed from..."、空、或与内容不一致的 description
   都必须用子 Agent 读取真实内容后重新生成。文件名可能是错的（如 metagpt_paper.md 实际是
   Generative Agents 论文），只信任内容。
3. Merges: move docs FIRST, delete SECOND. Deleting first loses data.
4. Confirm destructive operations unless Module Mode.
5. O5 (verify) catches mistakes. Do not skip.
6. O8 (tag audit) cannot delete orphan tags — MCP limitation. Report and suggest manual cleanup.
7. **≥3 篇文档审计时用子 Agent**，主 Agent 只接收 issues 列表和修正后的 descriptions，
   保持主上下文干净。
