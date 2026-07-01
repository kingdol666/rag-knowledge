# Knowledge Base Skill System — 综合测试提示词

## 使用方式

1. 打开一个新的 Claude Code session（在工作目录 `rag-knowledge/` 中）
2. 确保 backend + frontend 已启动（`start.bat dev` 或手动启动）
3. 直接把以下内容粘贴给 Claude，观察 Archival agent 的技能调用

---

```
请你管理一下我的知识库！以下是我想做的几件事：

## 第一步：了解现状

先帮我看看当前知识库的整体情况——有哪些知识库、多少文档、标签情况如何。

## 第二步：健康检查

做一次完整的完整性校验。检查元数据一致性、文档可用性、解析质量，最后给我一个健康评分（/100）。

## 第三步：入库测试文档

我要在知识库里新建一个叫「测试-知识库管理」的知识库，然后创建一篇测试文档：

知识库名称：测试-知识库管理
知识库描述：用于测试知识库管理系统的功能验证

文档名称：skill-test-document.md
文档内容：（请用以下内容创建）
"""
# Knowledge Base Skill System Test

This document is created to test the automated knowledge base management skills.

## Overview
The RAG Knowledge Platform includes 8 specialized skills for managing documents:
- Ingest: Document ingestion pipeline
- Manage: Document and KB administration
- Organize: Full collection restructuring
- Search: Keyword and tag-based search
- List: Collection overview
- Verify: Integrity validation
- Batch: Bulk operations

## Tags
- skill-system
- testing
- knowledge-base

## Purpose
Validate that Archival agent can automatically classify, store, tag, and manage documents.
"""

文档描述：知识库系统功能验证文档，用于测试自动入库和标签管理

## 第四步：标签管理

给刚才创建的文档打上标签：「skill-test」「validation」「automated-testing」
然后查询一下打了「skill-test」标签的所有文档。

## 第五步：搜索验证

搜索关键字「knowledge base skill system」，看看能不能找到刚创建的文档。

## 第六步：整理一下

帮我检查当前所有知识库的状况——有没有空的、名字乱起的、描述是空的？如果有的话给我出个整理建议。

## 第七步：批量清理

把刚才为测试创建的「测试-知识库管理」知识库和里面的文档都删掉。

---

请一步一步执行，每步完成后向我汇报结果。不要跳过任何步骤！
```

---

## 预期行为

当粘贴以上提示词后，Archival agent 应该：

| 步骤 | 预期触发 skill | 预期行为 |
|------|---------------|---------|
| 第一步 → 了解现状 | `knowledge-list` | `kb_list()` + `kb_tags_list()` + `fs_get_tree()` 展示概览 |
| 第二步 → 健康检查 | `knowledge-verify` | V1 元数据 + V2 文档抽检 + V5 评分卡 |
| 第三步 → 入库 | `knowledge-ingest` | A1 Survey → A3 创建 KB → A6 kb_doc_create → A7 打标签 |
| 第四步 → 标签管理 | `knowledge-manage` / tags | `kb_doc_update_tags()` + `kb_doc_get_by_tag()` |
| 第五步 → 搜索 | `knowledge-search` | `kb_search()` 全文检索 |
| 第六步 → 整理 | `knowledge-organize` | 全盘 survey + 分类 + 建议 |
| 第七步 → 批量清理 | `knowledge-batch` (B4/B1) | 批量删除文档 + KB |
| 全流程 | Mixed 场景 | organize → verify → ingest → manage → list 顺序 |

### 成功标准

- Archival 自动诊断每个步骤的场景（无需用户提示）
- 每步完成后有清晰的汇报（做了什么、结果如何）
- 创建和删除操作之间有确认（除非 Module Mode）
- 总步骤数 7/7 全部完成
