# Experience Quality Standards — 经验质量黄金标准

> 经验不是"把对话记下来"——经验是**可复用的实践精华**，从具体案例中提炼抽象规律。
> 检索时，低质经验即使向量命中也没用；高质经验能让人照着做。

## Table of Contents
- [三道自检题](#三道自检题)
- [字段达标标准](#字段达标标准)
- [坏经验 vs 好经验](#坏经验-vs-好经验)
- [category 选择指南](#category-选择指南)
- [去重判定](#去重判定)
- [完整性检查清单](#完整性检查清单)

---

## 三道自检题

写每段经验前问自己：

1. **这解决了什么真问题？** — 别人遇到同样场景时，能否马上定位到这条经验？
2. **可操作性能打几分？** — 读完方案，别人能不能直接照着做？还是只说"要小心"？
3. **少了什么？** — `problem` / `solution` / `key_lessons` 缺一个都不行，`related_docs` 缺了等于断链。

经验 ≠ 对话记录。经验 = 从具体案例提炼的**抽象规律**：
- ❌ "今天我搜了 RAG 的资料"（日记）
- ✅ "RAG 检索时，先用 two_stage 再用 vector 补全，召回率提升 40%"（可复用知识）

---

## 字段达标标准

| 字段 | 达标标准 | 长度 | ❌ 不达标 |
|------|---------|------|----------|
| `title` | 含场景词 + 方法词（如"磨煤机堵管预警"） | 简短 | "经验1" / "故障处理" |
| `scenario` | kebab-case，含领域前缀 | 如 `vla-deployment-sim2real` | `test` / 无前缀 |
| `problem` | 具体到时间/数量/条件的可复现场景 | ≥50 chars | "设备不太好用" |
| `solution` | 有工具/方法/步骤/配置/命令 | ≥100 chars | "我们检查了一下" |
| `key_lessons` | 每条可独立引用，从不同角度 | 每条 ≥30 chars，3-5条 | "注意安全" / 仅2条 |
| `tags` | 领域词 + 方法词 + 场景词 | ≥2 个 | 空 / 仅1个 |
| `related_docs` | 路径在 KB 真实存在 | 用 `kb_doc_read` 验证 | 不存在 / 空（除非纯对话经验）|
| `severity` | 与 category 匹配的真实严重度 | — | tip 类故障标 normal |
| `category` | 选最匹配的（见下表） | — | 故障排查标 tip |

### `solution` 长度硬门槛

| category | solution 最低 chars |
|----------|-------------------|
| troubleshooting | 80 |
| best_practice / workflow | 100 |
| optimization | 80 |
| lesson_learned | 60 |
| decision | 60 |
| tip | 40 |

---

## 坏经验 vs 好经验

### ❌ 坏经验（太泛，检索命中也没用）
```yaml
problem: "设备不太好用"
solution: "我们检查了一下，调整了参数"
key_lessons: ["要注意维护"]
```

### ✅ 好经验（具体、可操作、可复用）
```yaml
problem: "磨煤机堵管导致停炉，每次清堵耗时3小时，月均2次"
solution: |
  搭建 CNN-LSTM 预警模型：
  1. 从 DCS 历史数据提取磨煤机电流、进出口差压、一次风量三参数
  2. 滑窗 60min 标注堵管前兆样本训练
  3. 部署实时推理，超 0.8 概率触发预警
  4. 预警后 315 分钟内人工介入可避免停炉
key_lessons:
  - "特征工程选磨煤机电流+进出口差压+一次风量三参数，缺一不可"
  - "预警阈值设80%时精度95%误报率3%，低于70%则误报激增至18%"
  - "滑窗60min是堵管前兆的最优观测窗口，30min噪声大、120min滞后"
```

→ 别人遇到同样场景能直接套用。

---

## category 选择指南

| category | 何时用 | 关键信号 |
|----------|--------|---------|
| `troubleshooting` | 故障排查、错误修复 | "报错""失败""排障""修复" |
| `best_practice` | 经过验证的最佳实践 | "推荐""标准做法""最优" |
| `workflow` | 多步骤流程/标准操作程序 | "步骤""流程""SOP" |
| `optimization` | 性能/效率优化 | "提升""加速""优化""降本" |
| `lesson_learned` | 从失败/事件中得到的教训 | "教训""事后""回顾" |
| `decision` | 架构/技术选型决策及理由 | "选型""决策""为什么用X而非Y" |
| `tip` | 小技巧/快捷方式（非系统性） | "技巧""快捷""小窍门" |

> 误选 category 会误导检索分类。故障排查误标 tip → 降权。

---

## 去重判定

同 KB 内已有相似 `scenario` → **不要新建**，走更新路径（[crud-and-migration.md](crud-and-migration.md) §更新）：

```
创建前先查：
  experience_search(kb_id, query="<scenario 关键词>") → 看是否命中
  experience_list(kb_id, scenario="<同 scenario>") → 看是否已存在

命中已有 → experience_update 补充新教训/更新方案
未命中  → experience_create 新建
```

跨 KB 同主题 → 允许各自存在（不同 KB 的领域上下文不同），但 `tags` 应标明关联领域。

---

## 完整性检查清单

创建/更新前逐项过：

```
□ title 含场景词 + 方法词
□ scenario kebab-case + 领域前缀
□ problem ≥50 chars，具体可复现
□ solution ≥ 阈值（见上表），含可执行步骤
□ key_lessons ≥3 条，每条 ≥30 chars，可独立引用
□ tags ≥2 个（领域 + 方法）
□ related_docs 路径真实存在（kb_doc_read 验证）
□ category 与内容匹配
□ severity 与 category 匹配
□ 同 scenario 未重复（去重检查）
```

任一不达标 → 回退起草，不要硬入库。缺字段的经验检索命中也没用。
