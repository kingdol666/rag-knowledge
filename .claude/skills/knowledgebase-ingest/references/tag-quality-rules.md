# Tag Quality Rules — 标签质量门控

> **核心原则**：标签是检索的"路标"，必须是从内容提炼的**领域概念词**，不是文件名碎片、章节标题、或测试残留。
> 垃圾标签会直接污染 `kb_doc_get_by_tag` 召回和 enterprise 检索的 Path B。

## 黄金法则

**先读内容，再提标签。** 未读文档正文（≥2000 chars）就打标签，是禁止行为。
每个标签必须满足：①是领域概念/技术/方法/材料/场景词；②在正文里真实出现；③与现有词表去重归一。

---

## T1 — 黑名单（命中即丢弃，永不入库）

### T1a 章节标题 / 论文结构词
解析 PDF 时极易把标题误提为标签。**以下模式一律拒绝**：

| 模式 | 示例（实测垃圾） |
|---|---|
| 论文章节编号 | `1 Introduction` `2 Tasks and Terminol` `3 Method` `3.1 Adapting GLIP` `4 Experiments` `5 Related Works` `6 Conclusions` `7 Limitations` `8 Ethics` |
| 附录/致谢/参考 | `Acknowledgments` `References` `A.1 GPT Prompts` `B.1 Narration Proces` `B.3 Hyperparameters` |
| 摘要/关键词 | `Abstract` `Keywords` `摘要` `关键词` |
| 截断残留 | 任何以 `...` 结尾或被截断的标题（`Localizing Active Ob`）|
| 纯结构词 | `完整版` `基线对比` `综述`（单独使用无语境时）|

**检测正则**：`^\d+(\.\d+)*\s`（章节号开头）、`^(Abstract|References|Acknowledgments|摘要|关键词|附录)`。

### T1b 测试 / 调试标签
| 模式 | 示例 |
|---|---|
| 含 "test" | `test-tag-ingest` `test` `mcp-test-tag` `ingest-test` `test-ops` `metadata-test` `edge-test-tag` `integration-test` `skill-test` `test-batch-tag` `testing` |
| 含 "tag" 元词 | `graph-test-tag` `web-api-test-tag` `tag with spaces & special!` |
| 流程标记 | `3-layer-sync` `verification` `e2e` |

### T1c 描述性 / 元标签
标签描述的是"文档状态"而非"文档内容"：
- `文件名内容不匹配` `待补` `未验证` `draft` `TODO`
→ 这类应写进 description 或审计备注，**不可作为标签**。

### T1d 格式非法
- 含空格（除非是既定复合词如 `deep learning`）
- 含特殊字符 `!@#$%^&*` 、纯标点、纯数字、超长（>30 chars）

---

## T2 — 归一化（提标签前先归一）

### T2a 大小写归一
化学式/缩写统一首大写：`pet`→`PET`、`pe`→`PE`、`pp`→`PP`、`pa6`→`PA6`、`pla`→`PLA`、`pvdf`→`PVDF`。
通用技术词统一小写（除首字母）：`Transformer`/`transformer`→`Transformer`（专有架构保留大写）、`deep-learning`/`Deep-Learning`→`深度学习`（优先中文词表词）。

### T2b 中英文同义合并（保留词表已有者优先，新词映射到既定主词）

| 领域 | 主标签 | 合并掉 |
|---|---|---|
| 聚合物 | `PET`/`聚酯` | `pet` `bopet`（除非强调薄膜工艺）|
| | `PE`/`聚乙烯` | `pe` `uhmwpe`（UHMWPE 是特例保留）|
| | `PP`/`聚丙烯` | `pp` `bopp` |
| | `PA6`/`聚酰胺` | `pa6` `pa56` `bopa6`（不同牌号分别保留）|
| | `PLA`/`聚乳酸` | `pla` |
| AI | `Transformer` | `transformer` `attention-mechanism`（后者作为补充可保留）|
| | `强化学习` | `Reinforcement Learning` |
| | `机器学习` | `machine-learning` `ML` |
| 材料 | `石墨烯` | `graphene` |
| | `MXene` | `mxene` |

**规则**：查询 `kb_tags_list()`，若中文主词已存在，新英文标签归一到中文；反之亦然。**同义只保留一个**，避免词表膨胀。

### T2c 命名风格统一
- 材料/化学：化学式大写（`PET` `TiO₂`）
- 方法/算法：中文名优先（`双向拉伸` `强化学习`），英文专有保留（`Transformer` `GraphRAG` `Self-RAG`）
- 设备/工艺：中文（`拉幅机` `挤出沉积`），除非英文是行业通用（`TDO`）

---

## T3 — 数量与内容判据

| 维度 | 要求 |
|---|---|
| **数量** | 每文档 **2-5 个**。<2 太散无法召回，>5 噪声大 |
| **复用率** | **≥90%** 从 `kb_tags_list()` 既有词表复用；新词仅当代表全新概念才新增 |
| **粒度** | 1 个材料词 + 1 个方法/工艺词 + 1 个场景/应用词 + 0-2 个细分属性。例：`PET / 双向拉伸 / 结晶度 / 拉幅机` |
| **正文验证** | 每个标签必须在正文 ≥2000 chars 采样里**真实出现**或为其直接上位词 |

---

## T4 — 执行流程（入库时）

```
1. 读正文 ≥2000 chars
2. 候选标签 = 从内容提炼 5-8 个领域词
3. 过 T1 黑名单 → 丢弃命中项
4. 过 T2 归一化 → 大小写统一、同义合并
5. 过 T3 数量裁剪 → 保留 top 2-5（材料/方法/场景/属性）
6. 比对 kb_tags_list() → ≥90% 复用；新增词确认是全新概念
7. 正文回查 → 每个标签确认在内容里出现
8. kb_doc_update_tags(tags=cleaned_tags)
```

## T5 — 清洗时（organize O8 用）

对已污染词表，扫描 `kb_tags_list()`：
- T1 黑名单命中 → 从所有文档移除该标签
- T2 同义重复 → 统一映射到主词，`kb_doc_update_tags` 替换
- 0 文档引用的孤儿标签 → 系统自动清除，无需手动
- 1 文档独有且非新概念 → 考虑归并到主词

**实测现状**：当前词表 376 个，其中 ~40 个章节标题、~17 个测试标签、~15 组同义重复 → 清洗后预期降至 ~280 个，召回精度显著提升。
