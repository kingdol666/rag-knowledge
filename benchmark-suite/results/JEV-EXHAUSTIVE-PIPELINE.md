# 逐级检索增强：穷尽召回 → Jev 判断剔除 → 作答

**问题**：List every scene in the novel where Darcy and Elizabeth meet in person, in order, and say what changes in their relationship at each.

**KB**：`Novel-PridePrejudice` · 阈值 0.4 · 判断后端 `llm`

## 管线轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：28 篇
- **L4 穷尽召回**：读全部 **28** 篇的头部（无相似度筛选）
- **L5.5 Jev 判断**：后端 `llm` · 模型 `n/a` · 10.3s → 保留 **12** 篇：[4, 5, 7, 8, 13, 14, 16, 17, 18, 22, 24, 25]
- **L5 深读**：12 篇 × 6000 字符 → 证据 20000 字符
- **L7 作答**：56.5s · $0.049219000000000006

## 每个窗口的判断分（窗口→所属 part）

| 窗口 | 所属 part | 分 | 保留 |
|---|---|---:|:--:|
| w0 | 1 | 0.1 | ✗ |
| w1 | 1 | 0.0 | ✗ |
| w2 | 1 | 0.0 | ✗ |
| w3 | 1 | 0.0 | ✗ |
| w4 | 10 | 0.0 | ✗ |
| w5 | 10 | 0.0 | ✗ |
| w6 | 10 | 0.0 | ✗ |
| w7 | 11 | 0.0 | ✗ |
| w8 | 11 | 0.0 | ✗ |
| w9 | 11 | 0.0 | ✗ |
| w10 | 12 | 0.0 | ✗ |
| w11 | 12 | 0.0 | ✗ |
| w12 | 12 | 0.0 | ✗ |
| w13 | 13 | 0.7 | ✓ |
| w14 | 13 | 0.4 | ✓ |
| w15 | 13 | 0.4 | ✓ |
| w16 | 14 | 0.5 | ✓ |
| w17 | 14 | 0.4 | ✓ |
| w18 | 14 | 0.4 | ✓ |
| w19 | 15 | 0.3 | ✗ |
| w20 | 15 | 0.0 | ✗ |
| w21 | 15 | 0.3 | ✗ |
| w22 | 16 | 0.0 | ✗ |
| w23 | 16 | 0.0 | ✗ |
| w24 | 16 | 0.5 | ✓ |
| w25 | 17 | 0.3 | ✗ |
| w26 | 17 | 0.9 | ✓ |
| w27 | 17 | 0.9 | ✓ |
| w28 | 18 | 0.6 | ✓ |
| w29 | 18 | 0.7 | ✓ |
| w30 | 18 | 0.5 | ✓ |
| w31 | 19 | 0.0 | ✗ |
| w32 | 19 | 0.0 | ✗ |
| w33 | 19 | 0.0 | ✗ |
| w34 | 2 | 0.0 | ✗ |
| w35 | 2 | 0.0 | ✗ |
| w36 | 2 | 0.0 | ✗ |
| w37 | 20 | 0.0 | ✗ |
| w38 | 20 | 0.3 | ✗ |
| w39 | 20 | 0.0 | ✗ |
| w40 | 21 | 0.0 | ✗ |
| w41 | 21 | 0.0 | ✗ |
| w42 | 21 | 0.0 | ✗ |
| w43 | 22 | 0.6 | ✓ |
| w44 | 22 | 0.0 | ✗ |
| w45 | 22 | 0.0 | ✗ |
| w46 | 22 | 0.0 | ✗ |
| w47 | 23 | 0.0 | ✗ |
| w48 | 23 | 0.0 | ✗ |
| w49 | 23 | 0.0 | ✗ |
| w50 | 24 | 0.5 | ✓ |
| w51 | 24 | 0.6 | ✓ |
| w52 | 24 | 0.9 | ✓ |
| w53 | 25 | 0.4 | ✓ |
| w54 | 25 | 0.6 | ✓ |
| w55 | 25 | 0.5 | ✓ |
| w56 | 26 | 0.0 | ✗ |
| w57 | 26 | 0.0 | ✗ |
| w58 | 26 | 0.0 | ✗ |
| w59 | 3 | 0.3 | ✗ |
| w60 | 3 | 0.0 | ✗ |
| w61 | 3 | 0.0 | ✗ |
| w62 | 4 | 0.4 | ✓ |
| w63 | 4 | 0.4 | ✓ |
| w64 | 4 | 0.4 | ✓ |
| w65 | 5 | 0.5 | ✓ |
| w66 | 5 | 0.4 | ✓ |
| w67 | 5 | 0.5 | ✓ |
| w68 | 6 | 0.0 | ✗ |
| w69 | 6 | 0.0 | ✗ |
| w70 | 6 | 0.0 | ✗ |
| w71 | 7 | 0.3 | ✗ |
| w72 | 7 | 0.0 | ✗ |
| w73 | 7 | 0.5 | ✓ |
| w74 | 8 | 0.4 | ✓ |
| w75 | 8 | 0.4 | ✓ |
| w76 | 8 | 0.0 | ✗ |
| w77 | 9 | 0.0 | ✗ |
| w78 | 9 | 0.0 | ✗ |
| w79 | 9 | 0.0 | ✗ |

## 作答（verbatim）

The evidence is insufficient to answer this question.

The retrieved excerpts cover only a handful of chapters: part 13 (Darcy's visits to the Parsonage, Mrs. Collins's speculation, Elizabeth's walks in the park, her encounter with Colonel Fitzwilliam), part 14 (Darcy's letter explaining his conduct toward Bingley and Wickham), part 16 (Lydia's invitation to Brighton and Elizabeth's talk with her father), and part 17 (the visit to Pemberley and Mrs. Reynolds's praise of Darcy). This is a small fraction of the 26-part novel, so no complete, ordered list of every Darcy–Elizabeth meeting exists in the evidence. Moreover, the excerpts are fragmentary — several begin or end mid-sentence — and provide no continuous narrative of relationship development between scenes.

Sources used: `pride_and_prejudice (part 13 of 26)`, `pride_and_prejudice (part 14 of 26)`, `pride_and_prejudice (part 16 of 26)`, `pride_and_prejudice (part 17 of 26)`.
