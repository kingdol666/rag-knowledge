# RAG 知识库集合摘要报告

> 生成时间：2026-07-03 | 由 knowledgebase-batch B6 + knowledgebase-verify V6 联合产出

## 概览

| 指标 | 数值 |
|------|------|
| 知识库总数 | 6（+1 幻影文件夹） |
| 文档总数 | 18 |
| 经验总数 | 3（Thermal-Power-Monitoring） |
| 标签总数 | 77 |
| 向量 collection | 17（**12 孤儿**） |
| 健康评分 | **75/100 (GOOD)** |

## 知识库详情

| KB | 文档 | 向量chunks | 经验 | 领域 | 健康度 |
|----|------|-----------|------|------|--------|
| Thermal-Power-Monitoring | 6 | 172 | 3 | 火电监控 | ✅ 优（1经验乱码） |
| Wind-Power-Fault-Diagnostics | 4 | 14 | 0 | 风电诊断 | ✅ 良 |
| Academic-AI-Software | 4 | 9 | 0 | AI/软件 | ⚠️ 3旧文档未索引 |
| Data-Driven-Industry | 1 | 2 | 0 | 工业数据驱动 | ⚠️ 487KB超大+索引异常 |
| University-Administration | 1 | 0 | 0 | 高校行政 | ⚠️ 无向量索引 |
| test_materials | 3 | 20 | 0 | 测试残留 | ❌ 1重复+2测试桩 |

## 标签热度 Top 10

| 标签 | 用途 |
|------|------|
| architecture | 软件架构类文档 |
| AI / LLM / RAG | AI 技术栈 |
| 火电厂 / 火电 / thermal | 火电领域 |
| 磨煤机 / MSET / CNN-LSTM | 磨煤机预警方法 |
| 故障预警 / 故障诊断 | 预测性维护 |
| paper | 学术论文 |
| 嵌入式控制 / 最优控制 | 控制工程 |

## 本次会话产出（场景化验证）

### 新增内容
- 📄 `Academic-AI-Software/rag-platform-architecture.md`（v2, 5728B, 4标签, 9 chunks）— RAG 平台架构设计 + 落地最佳实践
- 💡 `exp-d79f3d6dd3b5` — 磨煤机 CNN-LSTM 预警阈值经验（rating 5.0, applied 1, scenario: coal-mill-fault-warning）
- 💡 `exp-5d042bc9c1b5` — MSET 一次风机预测记忆矩阵经验（rating 4.0, scenario: primary-fan-mset）

### 发现的 Bug / Issue（按严重度）

**🔴 Critical：**
1. `kb_doc_update_content`/`update_meta` **清空文档标签**（P4，数据丢失）— 已临时修复并记入 memory
2. `exp-f1cecd56cdea` 经验**全文中文乱码**（GBK→Latin1 编码错乱）
3. 12 个**孤儿向量 collection**（已删 KB 残留）
4. Academic-AI-Software 3 旧文档 + University-Administration + Data-Driven-Industry **向量索引缺失/异常**

**🟡 Warning：**
5. `experience_search` / `experience_search_global` 元信息搜索失效（返回 0）
6. `kb_search_vector` 文档向量检索返回 0 结果 / `kb_search_two_stage` stage2 content 为空（**经验向量检索正常**，形成对比）
7. `kb_batch_index` 报 "no content"（误导，实为超时）；`kb_index_document` 大文档 ReadTimeout（CPU embedding 性能瓶颈）
8. `.tree-fs.json` 含幻影节点（mcp_test_folder / fs-test-file.md 磁盘不存在）
9. test_materials 含 2 篇 CRUD 测试残留 + 1 跨 KB 重复（本体论论文 978-3-540-30468-5_43.md）

**🟢 已修复：**
10. ✅ memory 记录的 `file_size` 陈旧 bug（P2）**已在当前版本修复**

## 建议的整理动作（待授权）

| 优先级 | 动作 | 影响 |
|--------|------|------|
| P0 | 重建乱码经验 exp-f1cecd56cdea | 恢复可读性 |
| P0 | 清理 test_materials 测试残留 | 去噪 |
| P1 | 去重本体论论文（保留 Academic-AI-Software 副本） | 消除冗余 |
| P1 | O8 切分 Data-Driven-Industry 487KB 超大文档 | 提升检索精度 |
| P2 | 清理 12 孤儿向量 collection | 释放空间 |
| P2 | 清理 .tree-fs.json 幻影节点 | 元数据一致 |
| P2 | 修复 update 工具标签丢失 bug | 防止数据丢失 |
