# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答

**问题**：Mr. Wickham was involved in two elopements. For each, state who the girl was, how old she was, where it happened, and whether it was carried out.

**KB**：`Novel-PridePrejudice` · 阈值 0.15 · 判断后端 `llm`

## 管线轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：28 篇
- **L2.5 候选选择**（mode `union`）：8/28 篇 → 并集后 11
- **L4 穷尽召回**：读全部 **11** 篇（无相似度筛选）
- **L5.5 Jev 判断**：后端 `llm` · 模型 `n/a` · 6.2s → 保留 **5** 篇：[11, 14, 16, 19, 21]
- **L5 深读**：5 篇 × 6000 字符 → 证据 20000 字符
- **L7 作答**：37.0s · $0.04798

## 每个窗口的判断分（窗口→所属 part）

| 窗口 | 所属 part | 分 | 保留 |
|---|---|---:|:--:|
| w0 | 19 | 0.1 | ✗ |
| w1 | 19 | 0.2 | ✓ |
| w2 | 19 | 0.05 | ✗ |
| w3 | 11 | 0.0 | ✗ |
| w4 | 11 | 0.1 | ✗ |
| w5 | 11 | 0.15 | ✓ |
| w6 | 2 | 0.0 | ✗ |
| w7 | 2 | 0.0 | ✗ |
| w8 | 2 | 0.0 | ✗ |
| w9 | 20 | 0.1 | ✗ |
| w10 | 20 | 0.1 | ✗ |
| w11 | 20 | 0.05 | ✗ |
| w12 | 21 | 0.15 | ✓ |
| w13 | 21 | 0.3 | ✓ |
| w14 | 21 | 0.35 | ✓ |
| w15 | 5 | 0.0 | ✗ |
| w16 | 5 | 0.0 | ✗ |
| w17 | 5 | 0.0 | ✗ |
| w18 | 6 | 0.0 | ✗ |
| w19 | 6 | 0.05 | ✗ |
| w20 | 6 | 0.05 | ✗ |
| w21 | 7 | 0.0 | ✗ |
| w22 | 7 | 0.0 | ✗ |
| w23 | 7 | 0.05 | ✗ |
| w24 | 10 | 0.0 | ✗ |
| w25 | 10 | 0.0 | ✗ |
| w26 | 10 | 0.0 | ✗ |
| w27 | 14 | 0.15 | ✓ |
| w28 | 14 | 0.15 | ✓ |
| w29 | 14 | 0.15 | ✓ |
| w30 | 16 | 0.15 | ✓ |
| w31 | 16 | 0.1 | ✗ |
| w32 | 16 | 0.05 | ✗ |

## 作答（verbatim）

The evidence is insufficient to answer this question.

No retrieved passage states the age of any girl involved, gives the locations of the elopements, or confirms completion. The chunks mention only one elopement involving Wickham — with Lydia Bennet — and only indirectly, through debate about whether they went to Scotland, whether the marriage would be private, and whether he "never intend[ed] to marry her" (pride_and_prejudice, part 19 of 26; part 11 of 26). Part 21 of 26 notes Wickham "resolved on quitting the militia" after "his marriage was fixed on," implying the Lydia affair ended in marriage, but gives no place or age. A second elopement is not described in any retrieved chunk, though part 14 of 26 references Darcy's separate account of Wickham's conduct toward Georgiana — insufficient to establish an elopement, an age, or a location.
