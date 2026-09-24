# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答

**问题**：Mr. Wickham was involved in two elopements. For each, state who the girl was, how old she was, where it happened, and whether it was carried out.

**KB**：`Novel-PridePrejudice` · 阈值 0.4 · 判断后端 `llm`

## 管线轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：28 篇
- **L2.5 候选选择**（mode `union`）：8/28 篇 → 并集后 11
- **L4 穷尽召回**：读全部 **11** 篇（无相似度筛选）
- **L5.5 Jev 判断**：后端 `llm` · 模型 `n/a` · 4.3s → 保留 **0** 篇：[]
- **L5 深读**：0 篇 × 6000 字符 → 证据 0 字符
- **L7 作答**：27.4s · $0.020533

## 每个窗口的判断分（窗口→所属 part）

| 窗口 | 所属 part | 分 | 保留 |
|---|---|---:|:--:|
| w0 | 19 | 0.05 | ✗ |
| w1 | 19 | 0.15 | ✗ |
| w2 | 19 | 0.05 | ✗ |
| w3 | 11 | 0.05 | ✗ |
| w4 | 11 | 0.1 | ✗ |
| w5 | 11 | 0.1 | ✗ |
| w6 | 2 | 0.05 | ✗ |
| w7 | 2 | 0.05 | ✗ |
| w8 | 2 | 0.05 | ✗ |
| w9 | 20 | 0.05 | ✗ |
| w10 | 20 | 0.2 | ✗ |
| w11 | 20 | 0.05 | ✗ |
| w12 | 21 | 0.15 | ✗ |
| w13 | 21 | 0.3 | ✗ |
| w14 | 21 | 0.25 | ✗ |
| w15 | 5 | 0.05 | ✗ |
| w16 | 5 | 0.05 | ✗ |
| w17 | 5 | 0.05 | ✗ |
| w18 | 6 | 0.05 | ✗ |
| w19 | 6 | 0.05 | ✗ |
| w20 | 6 | 0.05 | ✗ |
| w21 | 7 | 0.05 | ✗ |
| w22 | 7 | 0.05 | ✗ |
| w23 | 7 | 0.05 | ✗ |
| w24 | 10 | 0.05 | ✗ |
| w25 | 10 | 0.05 | ✗ |
| w26 | 10 | 0.1 | ✗ |
| w27 | 14 | 0.1 | ✗ |
| w28 | 14 | 0.15 | ✗ |
| w29 | 14 | 0.1 | ✗ |
| w30 | 16 | 0.1 | ✗ |
| w31 | 16 | 0.1 | ✗ |
| w32 | 16 | 0.05 | ✗ |

## 作答（verbatim）

The evidence is insufficient — no evidence was retrieved for this question, so I cannot answer it. I have no document paths, file names, or chunk IDs to cite, and I will not draw on prior knowledge.
