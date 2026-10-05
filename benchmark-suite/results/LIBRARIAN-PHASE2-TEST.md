# 图书馆员逐级检索测试（L0–L7）— 长篇小说长弧问题

**问题**：Trace how Elizabeth Bennet's opinion of Fitzwilliam Darcy changes across the whole novel — from the Meryton assembly to their final engagement. Which scenes are the turning points, and how does Darcy himself change?

**KB**：`Novel-PridePrejudice` · 证据预算 12000 chars · 同一 chat API 作答

## L0–L5 逐级轨迹

- **L0** 读库描述：10 个库
- **L2** 读文档描述：26 个 part
- **L3 描述信任检查**：样板化标签 [] · 无信息标签 ['Part 10/26 · Gutenberg front/back matter', 'Part 11/26 · Gutenberg front/back matter', 'Part 12/26 · Gutenberg front/back matter', 'Part 13/26 · Gutenberg front/back matter', 'Part 14/26 · Gutenberg front/back matter', 'Part 15/26 · Gutenberg front/back matter', 'Part 16/26 · Gutenberg front/back matter', 'Part 17/26 · Gutenberg front/back matter', 'Part 19/26 · Gutenberg front/back matter', 'Part 20/26 · Gutenberg front/back matter', 'Part 21/26 · Gutenberg front/back matter', 'Part 22/26 · Gutenberg front/back matter', 'Part 23/26 · Gutenberg front/back matter', 'Part 24/26 · Gutenberg front/back matter', 'Part 25/26 · Gutenberg front/back matter', 'Part 26/26 · Gutenberg front/back matter', 'Part 3/26 · Gutenberg front/back matter', 'Part 4/26 · Gutenberg front/back matter', 'Part 5/26 · Gutenberg front/back matter', 'Part 6/26 · Gutenberg front/back matter', 'Part 7/26 · Gutenberg front/back matter', 'Part 8/26 · Gutenberg front/back matter', 'Part 9/26 · Gutenberg front/back matter'] → 不可信 part **23**/26；退化章节区间 [18, 2]
- **P3 选择策略**：content_probes (descriptions distrusted)

## 三路对照

> **稳健指标 = 检索召回**：选中的 part 是否覆盖 7 个关键情节的**真值 part**（由内容核对得出，与答案措辞无关）。答案覆盖列受 LLM 单次运行方差影响，仅供参考。

| 路径 | 选中 part | **检索召回(真值 part)** | 答案覆盖 | 成本 $ |
|---|---|:--:|:--:|---:|
| P1 向量优先 | [6, 8, 15, 17, 18, 21, 23, 24, 25] | **0.571** | 4/7 | 0.024627 |
| P2 图书馆员（只信描述） | [1, 18] | **0.143** | 5/7 | 0.025445000000000002 |
| P3 图书馆员 + L3 信任检查 | [2, 7, 12, 15, 17, 25] | **0.429** | 6/7 | 0.039602 |

## 逐 beat 覆盖（答案措辞）

| beat | P1 | P2 | P3 |
|---|:--:|:--:|:--:|
| B1 | ✓ | ✓ | ✓ |
| B2 | ✓ | ✗ | ✓ |
| B3 | ✓ | ✓ | ✓ |
| B4 | ✗ | ✓ | ✓ |
| B5 | ✓ | ✓ | ✓ |
| B6 | ✗ | ✗ | ✗ |
| B7 | ✗ | ✓ | ✓ |

## P1 答案（verbatim）

The evidence retrieved does not answer the question. The chunks are scattered fragments of *Pride and Prejudice* dialogue and narration (parts 6, 8, 15, 17, 18, 21, 23, 24, 25) — chiefly covering Elizabeth's refusal of Mr. Collins, the Wickham conversation, and events around Pemberley — but they contain no material on the Meryton assembly, no account of Elizabeth's opinion shifting over time, and no depiction of Darcy's own change of character. The fragments are too few and too disconnected to trace any arc, identify turning points, or compare the two characters' development.

Sources actually used (all evidence provided, none of which answers the question): [part 6], [part 8], [part 15], [part 17], [part 18], [part 21], [part 23], [part 24], [part 25].


## P2 答案（verbatim）

The evidence is insufficient to answer this question.

The two retrieved excerpts cover only disjoint fragments: part 1 is literary criticism of Austen's novels (comparing *Pride and Prejudice* to *Emma*, *Mansfield Park*, etc.), and part 18 is a single scene from *Pride and Prejudice* (the visit to Pemberley, Chapter XLV). Neither covers the Meryton assembly, the first proposal, the letter at Hunsford, or the final engagement, so no arc of Elizabeth's changing opinion — and no account of Darcy's own change — can be traced from these sources. Part 18 alone shows Elizabeth feeling "astonishment," "gratitude," respect, and esteem toward Darcy at Pemberley, but that is one point in the novel, not a trajectory across it.

Sources used: [part 1] (critical essay excerpt on Austen's novels); [part 18] (*Pride and Prejudice*, Chapter XLV excerpt).


## P3 答案（verbatim）

The evidence is insufficient to answer this question.

The retrieved chunks are excerpts from *Pride and Prejudice* (parts 2, 7, 12, 15, 17, 25), but they do not trace Elizabeth Bennet's evolving opinion of Darcy across the novel. Sources used: chunk [part 2] (the Meryton assembly setup and Bingley's arrival — Darcy is not even mentioned), [part 7] (the Netherfield ball invitation and Elizabeth's wish to dance with Wickham), [part 12] (Hunsford Parsonage life with Mr. Collins), [part 15] (Jane's loss of Bingley and Wickham's character revealed), [part 17] (a walk at Pemberley), and [part 25] (the final engagement conversation with Darcy).

Only [part 25] directly depicts the resolved relationship, and [part 17] gestures at Pemberley; the pivotal scenes the question asks about — the assembly insult, the "fine eyes" remark, the first proposal at Hunsford, Darcy's letter, and the second proposal — are absent or only indirectly referenced. Darcy's own transformation is likewise not covered by these excerpts, and I cannot supply it from prior knowledge.
