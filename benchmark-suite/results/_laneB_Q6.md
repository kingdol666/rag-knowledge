# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答

**问题**：List every scene in the novel where Darcy and Elizabeth meet in person, in order, and say what changes in their relationship at each.

**KB**：`Novel-PridePrejudice` · 阈值 0.4 · 判断后端 `llm`

## 管线轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：28 篇
- **L2.5 候选选择**（mode `union`）：19/28 篇 → 并集后 22
- **L4 穷尽召回**：读全部 **22** 篇（无相似度筛选）
- **L5.5 Jev 判断**：后端 `llm` · 模型 `n/a` · 6.8s → 保留 **6** 篇：[5, 13, 17, 18, 24, 25]
- **L5 深读**：6 篇 × 6000 字符 → 证据 20000 字符
- **L7 作答**：36.1s · $0.049047999999999994

## 每个窗口的判断分（窗口→所属 part）

| 窗口 | 所属 part | 分 | 保留 |
|---|---|---:|:--:|
| w0 | 22 | 0.05 | ✗ |
| w1 | 10 | 0.05 | ✗ |
| w2 | 10 | 0.05 | ✗ |
| w3 | 10 | 0.1 | ✗ |
| w4 | 13 | 0.75 | ✓ |
| w5 | 13 | 0.2 | ✗ |
| w6 | 13 | 0.1 | ✗ |
| w7 | 18 | 0.05 | ✗ |
| w8 | 18 | 0.9 | ✓ |
| w9 | 18 | 0.9 | ✓ |
| w10 | 19 | 0.05 | ✗ |
| w11 | 19 | 0.05 | ✗ |
| w12 | 19 | 0.05 | ✗ |
| w13 | 2 | 0.05 | ✗ |
| w14 | 2 | 0.05 | ✗ |
| w15 | 2 | 0.05 | ✗ |
| w16 | 20 | 0.05 | ✗ |
| w17 | 20 | 0.05 | ✗ |
| w18 | 20 | 0.05 | ✗ |
| w19 | 25 | 0.05 | ✗ |
| w20 | 25 | 0.6 | ✓ |
| w21 | 25 | 0.05 | ✗ |
| w22 | 3 | 0.05 | ✗ |
| w23 | 3 | 0.2 | ✗ |
| w24 | 3 | 0.05 | ✗ |
| w25 | 4 | 0.3 | ✗ |
| w26 | 4 | 0.25 | ✗ |
| w27 | 4 | 0.3 | ✗ |
| w28 | 5 | 0.6 | ✓ |
| w29 | 5 | 0.3 | ✗ |
| w30 | 5 | 0.6 | ✓ |
| w31 | 6 | 0.05 | ✗ |
| w32 | 6 | 0.05 | ✗ |
| w33 | 6 | 0.05 | ✗ |
| w34 | 7 | 0.1 | ✗ |
| w35 | 7 | 0.2 | ✗ |
| w36 | 7 | 0.3 | ✗ |
| w37 | 11 | 0.05 | ✗ |
| w38 | 11 | 0.05 | ✗ |
| w39 | 11 | 0.05 | ✗ |
| w40 | 12 | 0.2 | ✗ |
| w41 | 12 | 0.2 | ✗ |
| w42 | 12 | 0.05 | ✗ |
| w43 | 15 | 0.05 | ✗ |
| w44 | 15 | 0.05 | ✗ |
| w45 | 15 | 0.05 | ✗ |
| w46 | 21 | 0.05 | ✗ |
| w47 | 21 | 0.05 | ✗ |
| w48 | 21 | 0.05 | ✗ |
| w49 | 8 | 0.3 | ✗ |
| w50 | 8 | 0.3 | ✗ |
| w51 | 8 | 0.05 | ✗ |
| w52 | 9 | 0.05 | ✗ |
| w53 | 9 | 0.05 | ✗ |
| w54 | 9 | 0.05 | ✗ |
| w55 | 17 | 0.1 | ✗ |
| w56 | 17 | 0.95 | ✓ |
| w57 | 17 | 0.85 | ✓ |
| w58 | 22 | 0.15 | ✗ |
| w59 | 22 | 0.05 | ✗ |
| w60 | 22 | 0.05 | ✗ |
| w61 | 24 | 0.15 | ✗ |
| w62 | 24 | 0.15 | ✗ |
| w63 | 24 | 0.95 | ✓ |

## 作答（verbatim）

**Insufficient evidence.**

The evidence provided consists of four excerpts from *Pride and Prejudice* (parts 5, 13, 18, and 25 of 26) covering only a handful of scenes — the Netherfield music/dance exchange, Darcy's visits to the Parsonage and walks in Rosings park, the Pemberley visit and Elizabeth's reflections, and the post-engagement scenes at Longbourn. It does not contain the novel's other in-person meetings between Darcy and Elizabeth (for example, the Meryton assembly where they first meet, the Lucas Lodge gathering, the first proposal at Hunsford, or the Darcy–Elizabeth encounters in London), so a complete ordered list of every such scene with the relationship change at each cannot be assembled from this evidence.

Sources used: `pride_and_prejudice` (part 5 of 26); `pride_and_prejudice` (part 13 of 26); `pride_and_prejudice` (part 18 of 26); `pride_and_prejudice` (part 25 of 26).
