# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答

**问题**：Trace how Elizabeth's opinion of Mr. Darcy changes from the beginning of the novel to the end, and name the scenes that turn it.

**KB**：`Novel-PridePrejudice` · 阈值 0.4 · 判断后端 `llm`

## 管线轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：28 篇
- **L2.5 候选选择**（mode `union`）：19/28 篇 → 并集后 21
- **L4 穷尽召回**：读全部 **21** 篇（无相似度筛选）
- **L5.5 Jev 判断**：后端 `llm` · 模型 `n/a` · 7.7s → 保留 **4** 篇：[3, 5, 16, 18]
- **L5 深读**：4 篇 × 6000 字符 → 证据 20000 字符
- **L7 作答**：39.1s · $0.05018

## 每个窗口的判断分（窗口→所属 part）

| 窗口 | 所属 part | 分 | 保留 |
|---|---|---:|:--:|
| w0 | 10 | 0.05 | ✗ |
| w1 | 10 | 0.05 | ✗ |
| w2 | 10 | 0.15 | ✗ |
| w3 | 13 | 0.1 | ✗ |
| w4 | 13 | 0.05 | ✗ |
| w5 | 13 | 0.35 | ✗ |
| w6 | 18 | 0.4 | ✓ |
| w7 | 18 | 0.05 | ✗ |
| w8 | 18 | 0.15 | ✗ |
| w9 | 19 | 0.05 | ✗ |
| w10 | 19 | 0.05 | ✗ |
| w11 | 19 | 0.1 | ✗ |
| w12 | 2 | 0.0 | ✗ |
| w13 | 2 | 0.0 | ✗ |
| w14 | 2 | 0.0 | ✗ |
| w15 | 20 | 0.05 | ✗ |
| w16 | 20 | 0.15 | ✗ |
| w17 | 20 | 0.05 | ✗ |
| w18 | 22 | 0.0 | ✗ |
| w19 | 25 | 0.2 | ✗ |
| w20 | 25 | 0.25 | ✗ |
| w21 | 25 | 0.3 | ✗ |
| w22 | 3 | 0.0 | ✗ |
| w23 | 3 | 0.45 | ✓ |
| w24 | 3 | 0.05 | ✗ |
| w25 | 4 | 0.05 | ✗ |
| w26 | 4 | 0.3 | ✗ |
| w27 | 4 | 0.05 | ✗ |
| w28 | 5 | 0.4 | ✓ |
| w29 | 5 | 0.05 | ✗ |
| w30 | 5 | 0.2 | ✗ |
| w31 | 7 | 0.15 | ✗ |
| w32 | 7 | 0.1 | ✗ |
| w33 | 7 | 0.1 | ✗ |
| w34 | 11 | 0.05 | ✗ |
| w35 | 11 | 0.1 | ✗ |
| w36 | 11 | 0.05 | ✗ |
| w37 | 12 | 0.05 | ✗ |
| w38 | 12 | 0.05 | ✗ |
| w39 | 12 | 0.05 | ✗ |
| w40 | 15 | 0.05 | ✗ |
| w41 | 15 | 0.05 | ✗ |
| w42 | 15 | 0.15 | ✗ |
| w43 | 21 | 0.05 | ✗ |
| w44 | 21 | 0.05 | ✗ |
| w45 | 21 | 0.05 | ✗ |
| w46 | 6 | 0.0 | ✗ |
| w47 | 6 | 0.0 | ✗ |
| w48 | 6 | 0.05 | ✗ |
| w49 | 8 | 0.05 | ✗ |
| w50 | 8 | 0.0 | ✗ |
| w51 | 8 | 0.0 | ✗ |
| w52 | 9 | 0.0 | ✗ |
| w53 | 9 | 0.05 | ✗ |
| w54 | 9 | 0.05 | ✗ |
| w55 | 16 | 0.3 | ✗ |
| w56 | 16 | 0.05 | ✗ |
| w57 | 16 | 0.45 | ✓ |
| w58 | 22 | 0.15 | ✗ |
| w59 | 22 | 0.05 | ✗ |
| w60 | 22 | 0.0 | ✗ |

## 作答（verbatim）

The evidence is insufficient to answer this question.

The retrieved chunks are three disconnected slices of *Pride and Prejudice* (parts 3, 5, 16 and 18 of 26) and cover neither the beginning of the novel nor its end, so no continuous trace of Elizabeth's changing opinion is possible. Part 3 does contain an early stance — "I could easily forgive _his_ pride, if he had not mortified _mine_" and her pledge "never to dance with him" — and parts 5 and 18 show a later softening (respect, esteem, gratitude, and her reflection that "hatred had vanished long ago"), plus Mr. Darcy's housekeeper's testimony at Pemberley and Wickham's unpaid debts. But the pivotal scenes that would connect these states are absent: the first proposal and her rejection of it, Darcy's letter of explanation at Hunsford, the second proposal, and the closing chapters are all outside the retrieved passages. I also cannot name the turning scenes reliably, since only a fragment of the Pemberley visit (parts 18 and the opening of Chapter XLV) is present and no concluding text is available.

Sources used: pride_and_prejudice, part 3 of 26; part 5 of 26; part 16 of 26; part 18 of 26.
