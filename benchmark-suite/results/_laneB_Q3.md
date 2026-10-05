# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答

**问题**：How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, and what exactly did he do and pay?

**KB**：`Novel-PridePrejudice` · 阈值 0.4 · 判断后端 `llm`

## 管线轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：28 篇
- **L2.5 候选选择**（mode `union`）：19/28 篇 → 并集后 20
- **L4 穷尽召回**：读全部 **20** 篇（无相似度筛选）
- **L5.5 Jev 判断**：后端 `llm` · 模型 `n/a` · 9.9s → 保留 **3** 篇：[21, 24, 25]
- **L5 深读**：3 篇 × 6000 字符 → 证据 18118 字符
- **L7 作答**：48.2s · $0.046923000000000006

## 每个窗口的判断分（窗口→所属 part）

| 窗口 | 所属 part | 分 | 保留 |
|---|---|---:|:--:|
| w0 | 25 | 0.95 | ✓ |
| w1 | 25 | 0.05 | ✗ |
| w2 | 25 | 0.1 | ✗ |
| w3 | 20 | 0.05 | ✗ |
| w4 | 20 | 0.05 | ✗ |
| w5 | 20 | 0.15 | ✗ |
| w6 | 13 | 0.1 | ✗ |
| w7 | 13 | 0.05 | ✗ |
| w8 | 13 | 0.1 | ✗ |
| w9 | 19 | 0.3 | ✗ |
| w10 | 19 | 0.15 | ✗ |
| w11 | 19 | 0.1 | ✗ |
| w12 | 2 | 0.02 | ✗ |
| w13 | 2 | 0.02 | ✗ |
| w14 | 2 | 0.02 | ✗ |
| w15 | 22 | 0.02 | ✗ |
| w16 | 10 | 0.02 | ✗ |
| w17 | 10 | 0.05 | ✗ |
| w18 | 10 | 0.05 | ✗ |
| w19 | 18 | 0.05 | ✗ |
| w20 | 18 | 0.05 | ✗ |
| w21 | 18 | 0.05 | ✗ |
| w22 | 21 | 0.5 | ✓ |
| w23 | 21 | 0.05 | ✗ |
| w24 | 21 | 0.1 | ✗ |
| w25 | 3 | 0.02 | ✗ |
| w26 | 3 | 0.02 | ✗ |
| w27 | 3 | 0.02 | ✗ |
| w28 | 4 | 0.02 | ✗ |
| w29 | 4 | 0.02 | ✗ |
| w30 | 4 | 0.02 | ✗ |
| w31 | 5 | 0.02 | ✗ |
| w32 | 5 | 0.02 | ✗ |
| w33 | 5 | 0.02 | ✗ |
| w34 | 7 | 0.05 | ✗ |
| w35 | 7 | 0.02 | ✗ |
| w36 | 7 | 0.02 | ✗ |
| w37 | 11 | 0.02 | ✗ |
| w38 | 11 | 0.02 | ✗ |
| w39 | 11 | 0.05 | ✗ |
| w40 | 12 | 0.02 | ✗ |
| w41 | 12 | 0.02 | ✗ |
| w42 | 12 | 0.02 | ✗ |
| w43 | 15 | 0.02 | ✗ |
| w44 | 15 | 0.02 | ✗ |
| w45 | 15 | 0.1 | ✗ |
| w46 | 6 | 0.02 | ✗ |
| w47 | 6 | 0.02 | ✗ |
| w48 | 6 | 0.02 | ✗ |
| w49 | 8 | 0.02 | ✗ |
| w50 | 8 | 0.02 | ✗ |
| w51 | 8 | 0.02 | ✗ |
| w52 | 9 | 0.02 | ✗ |
| w53 | 9 | 0.02 | ✗ |
| w54 | 9 | 0.02 | ✗ |
| w55 | 24 | 0.4 | ✓ |
| w56 | 24 | 0.1 | ✗ |
| w57 | 24 | 0.15 | ✗ |

## 作答（verbatim）

The evidence does not contain the scene in which Elizabeth learns of Darcy's role — part 25 opens with Mr. Bennet already recounting it, and none of the retrieved parts (21, 24, 25) show her discovery. From Mr. Bennet's account, Darcy "did everything; made up the match, gave the money, paid the fellow's debts, and got him his commission" (part 25). Mrs. Bennet's reaction — "Ten thousand a year!" and her ecstatic chatter — follows Elizabeth's "important communication" to her mother that same evening (part 25). The letter in part 24 is from Mr. Collins, not the source of this revelation, and part 21 concerns Wickham's removal from the militia and the Gardiners' payment arrangements, not Darcy's role. So the exact payment amount and the earlier scene of Elizabeth's discovery are not in the retrieved evidence.

Sources used: `pride_and_prejudice` part 25 of 26; part 24 of 26; part 21 of 26.
