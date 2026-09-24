# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答

**问题**：Why does Elizabeth refuse Mr. Darcy's proposal at Hunsford, and what does his letter the next morning reveal about Mr. Wickham's past?

**KB**：`Novel-PridePrejudice` · 阈值 0.4 · 判断后端 `llm`

## 管线轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：28 篇
- **L2.5 候选选择**（mode `union`）：19/28 篇 → 并集后 20
- **L4 穷尽召回**：读全部 **20** 篇（无相似度筛选）
- **L5.5 Jev 判断**：后端 `llm` · 模型 `n/a` · 8.1s → 保留 **1** 篇：[14]
- **L5 深读**：1 篇 × 6000 字符 → 证据 6038 字符
- **L7 作答**：41.1s · $0.029691

## 每个窗口的判断分（窗口→所属 part）

| 窗口 | 所属 part | 分 | 保留 |
|---|---|---:|:--:|
| w0 | 2 | 0.05 | ✗ |
| w1 | 2 | 0.05 | ✗ |
| w2 | 2 | 0.05 | ✗ |
| w3 | 20 | 0.05 | ✗ |
| w4 | 20 | 0.05 | ✗ |
| w5 | 20 | 0.05 | ✗ |
| w6 | 25 | 0.05 | ✗ |
| w7 | 25 | 0.1 | ✗ |
| w8 | 25 | 0.05 | ✗ |
| w9 | 11 | 0.05 | ✗ |
| w10 | 11 | 0.05 | ✗ |
| w11 | 11 | 0.05 | ✗ |
| w12 | 13 | 0.15 | ✗ |
| w13 | 13 | 0.05 | ✗ |
| w14 | 13 | 0.2 | ✗ |
| w15 | 19 | 0.05 | ✗ |
| w16 | 19 | 0.05 | ✗ |
| w17 | 19 | 0.05 | ✗ |
| w18 | 7 | 0.05 | ✗ |
| w19 | 7 | 0.05 | ✗ |
| w20 | 7 | 0.05 | ✗ |
| w21 | 10 | 0.05 | ✗ |
| w22 | 10 | 0.05 | ✗ |
| w23 | 10 | 0.05 | ✗ |
| w24 | 12 | 0.05 | ✗ |
| w25 | 12 | 0.05 | ✗ |
| w26 | 12 | 0.05 | ✗ |
| w27 | 15 | 0.05 | ✗ |
| w28 | 15 | 0.1 | ✗ |
| w29 | 15 | 0.2 | ✗ |
| w30 | 18 | 0.05 | ✗ |
| w31 | 18 | 0.05 | ✗ |
| w32 | 18 | 0.05 | ✗ |
| w33 | 21 | 0.05 | ✗ |
| w34 | 21 | 0.05 | ✗ |
| w35 | 21 | 0.05 | ✗ |
| w36 | 22 | 0.05 | ✗ |
| w37 | 3 | 0.05 | ✗ |
| w38 | 3 | 0.1 | ✗ |
| w39 | 3 | 0.05 | ✗ |
| w40 | 4 | 0.05 | ✗ |
| w41 | 4 | 0.05 | ✗ |
| w42 | 4 | 0.05 | ✗ |
| w43 | 5 | 0.05 | ✗ |
| w44 | 5 | 0.05 | ✗ |
| w45 | 5 | 0.05 | ✗ |
| w46 | 6 | 0.05 | ✗ |
| w47 | 6 | 0.05 | ✗ |
| w48 | 6 | 0.05 | ✗ |
| w49 | 9 | 0.05 | ✗ |
| w50 | 9 | 0.05 | ✗ |
| w51 | 9 | 0.05 | ✗ |
| w52 | 8 | 0.05 | ✗ |
| w53 | 8 | 0.05 | ✗ |
| w54 | 8 | 0.1 | ✗ |
| w55 | 14 | 0.55 | ✓ |
| w56 | 14 | 0.7 | ✓ |
| w57 | 14 | 0.5 | ✓ |

## 作答（verbatim）

The evidence is insufficient to answer this question.

The retrieved chunk (pride_and_prejudice, part 14 of 26) contains only Darcy's letter — his explanation of separating Bingley from Jane Bennet and the beginnings of his account regarding Wickham. It does not include the Hunsford proposal scene or Elizabeth's stated reasons for refusing him, and it is truncated mid-sentence ("condescended to adopt the measures of art s") before the letter's revelations about Wickham's past are given.

Source used: `pride_and_prejudice` (part 14 of 26).
