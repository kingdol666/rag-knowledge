# 对照实验报告 — `run-20260924T061730Z-0968033`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-24 06:19 UTC

## 方法清单

| method | 类型 | n |
|---|---|---:|
| `a2` | 项目（平台） | 1 |
| `bm25` | baseline | 1 |
| `vector` | baseline | 1 |

## 资源监控总表

| method | 时延 avg s | 时延 median s | tokens in | tokens out | 成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `a2` | 111.5 | 111.5 | 139340 | 2250 | 0.9537 | 0.9537 | 14.0 | — | — |
| `bm25` | 12.7 | 12.7 | 968 | 241 | 0.0295 | 0.0295 | 0.0 | — | — |
| `vector` | 16.2 | 16.2 | 729 | 132 | 0.0255 | 0.0255 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 弃答）

| method | 检索金标命中率 | 引用金标命中率 | 弃答数 | error 数 |
|---|---:|---:|---:|---:|
| `a2` | — | — | 0 | 0 |
| `bm25` | — | — | 1 | 0 |
| `vector` | — | — | 1 | 0 |

## Q1

**Q:** Trace how Elizabeth Bennet's opinion of Mr. Darcy changes across the whole novel, and identify the specific scenes that cause each change -- from the Meryton assembly, through Wickham's account and the Hunsford proposal and Darcy's letter, to the Pemberley visit and the Lydia elopement crisis. In what ways does Darcy himself change, and how does each acknowledge their earlier error by the end?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 111.5 | 2250 | 0.9536859999999998 | 14 | 否 | I have sufficient retrieved evidence. Here is my answer. **Answer** Elizabeth's opinion of Darcy moves through five documented stages. At the **Meryto |
| `bm25` | — | — | 12.7 | 241 | 0.029457 | 0 | 是 | The evidence is insufficient. The three retrieved documents are unrelated to the question: they concern infrastructure investment and economic growth  |
| `vector` | — | — | 16.2 | 132 | 0.025537 | 0 | 是 | The evidence is insufficient. No retrieved chunk discusses *Pride and Prejudice*, Elizabeth Bennet, Mr. Darcy, Wickham, Hunsford, Pemberley, or the Ly |

<details><summary>逐字答案全文</summary>

**[a2]**

I have sufficient retrieved evidence. Here is my answer.

**Answer**

Elizabeth's opinion of Darcy moves through five documented stages. At the **Meryton assembly** his character "was decided. He was the proudest, most disagreeable man in the world, and everybody hoped that he would never come there again" (part 2, chunk 41). **Wickham's account** hardens this — Elizabeth tells him she thinks Darcy "very disagreeable," and later calls him "that abominable Mr. Darcy," blaming him for Wickham's misfortunes (part 6, chunk 41; part 10, chunk 53). At **Hunsford** she refuses him outright: "You are mistaken, Mr. Darcy, if you suppose that the mode of your declaration affected me in any other way than as it spared me the concern which I might have felt in refusing you, had you behaved in a more gentlemanlike manner" (part 13, chunk 48). **Darcy's letter** (part 14, chunk 31) produces the reversal: she "grew absolutely ashamed of herself. Of neither Darcy nor Wickham could she think, without feeling that she had been blind, partial, prejudiced, absurd — 'How despicably have I acted!'" (part 14, chunk 50). At **Pemberley**, the housekeeper's testimony and Darcy's own altered manner work on her — "at that moment she felt that to be mistress of Pemberley might be something!" (part 16, chunk 54), and she later calls Wickham's stories "lies about the whole Pemberley family" (part 19, chunk 16). During the **Lydia crisis** Darcy acts secretly, and Elizabeth tells her father "what Mr. Darcy had voluntarily done for Lydia," moving Mr. Bennet to say "he deserves you. I could not have parted with you, my Lizzy, to anyone less worthy" (part 24, chunk 66).

Darcy's change is stated by himself: his original object in meeting her again was "to show you, by every civility in my power, that I was not so mean as to resent the past; and I hoped to obtain your forgiveness, to lessen your ill opinion, by letting you see that your reproofs had been attended to" (part 24, chunk 36). Elizabeth acknowledges her error as prejudice and blindness (part 14, chunk 50); Darcy acknowledges his as pride and resentfulness, and courts her again only after she has been undeceived about Wickham (part 24, chunks 17, 66).

**Sources used:** `Novel-PridePrejudice/pride_and_prejudice (part 2 of 26).md` (chunk 41); `part 6 of 26.md` (chunk 41); `part 7 of 26.md` (chunks 25–26, 36); `part 10 of 26.md` (chunk 53); `part 13 of 26.md` (chunk 48); `part 14 of 26.md` (chunks 31, 50); `part 15 of 26.md` (chunks 46–47, 54–55); `part 16 of 26.md` (chunks 1, 54, 62); `part 17 of 26.md` (chunk 52); `part 18 of 26.md` (chunk 20); `part 19 of 26.md` (chunk 16); `part 21 of 26.md` (chunk 28); `part 24 of 26.md` (chunks 17, 36, 39, 66); `part 25 of 26.md` (chunks 8, 21, 33–34, 39).

**[bm25]**

The evidence is insufficient.

The three retrieved documents are unrelated to the question: they concern infrastructure investment and economic growth in China (1609.00415), ECB conventional and unconventional monetary policy under uncertainty (2011.14424), and large language models encoding clinical knowledge (2212.13138). None of them discusses *Pride and Prejudice*, Elizabeth Bennet, Mr. Darcy, or any of the scenes named in the question (the Meryton assembly, Wickham's account, the Hunsford proposal, Darcy's letter, the Pemberley visit, or the Lydia elopement crisis).

I therefore cannot trace Elizabeth's shifting opinion of Darcy, identify the scenes causing each change, describe how Darcy himself changes, or explain how each acknowledges their earlier error. No answer can be grounded in the supplied evidence.

Sources consulted (all irrelevant to the question): economics__1609.00415__does-infrastructure-investment-lead-to-econo.md.md; economics__2011.14424__on-the-effectiveness-of-the-european-central.md; clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md.md.

**[vector]**

The evidence is insufficient.

No retrieved chunk discusses *Pride and Prejudice*, Elizabeth Bennet, Mr. Darcy, Wickham, Hunsford, Pemberley, or the Lydia elopement. The provided chunks are from unrelated papers (e.g., [2005.14165] on language-model grammar correction, [2310.10981] on QDS triples, [2201.03675] on directionality over time), none of which contain the requested plot or character analysis. I therefore cannot answer the question from this evidence and will not fall back on prior knowledge.

Sources used: none (no chunk was relevant).

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ✅ | 0 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=1.0087 · manifest=1.0087 |
| 单元数 = 题数 × 方法数 | ✅ | rows=3 vs 1×3=3 |
| provenance 完整 | ✅ | prompt_version=v3-neutral seed=0 |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*