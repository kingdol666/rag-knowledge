# 对照实验报告 — `run-20260924T052520Z-0968033`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-24 05:28 UTC

## 方法清单

| method | 类型 | n |
|---|---|---:|
| `a2` | 项目（平台） | 1 |
| `bm25` | baseline | 1 |
| `rerank` | baseline | 1 |
| `rrf` | baseline | 1 |
| `vector` | baseline | 1 |

## 资源监控总表

| method | 时延 avg s | 时延 median s | tokens in | tokens out | 成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `a2` | 96.8 | 96.8 | 106691 | 987 | 0.6149 | 0.6149 | 6.0 | — | — |
| `bm25` | 18.9 | 18.9 | 38145 | 118 | 0.1937 | 0.1937 | 0.0 | — | — |
| `rerank` | 32.4 | 32.4 | 244 | 97 | 0.0222 | 0.0222 | 0.0 | — | — |
| `rrf` | 11.5 | 11.5 | 956 | 193 | 0.0282 | 0.0282 | 0.0 | — | — |
| `vector` | 15.2 | 15.2 | 37359 | 159 | 0.1908 | 0.1908 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 弃答）

| method | 检索金标命中率 | 引用金标命中率 | 弃答数 | error 数 |
|---|---:|---:|---:|---:|
| `a2` | 1.0 | 1.0 | 0 | 0 |
| `bm25` | 1.0 | 1.0 | 0 | 0 |
| `rerank` | 1.0 | 1.0 | 0 | 0 |
| `rrf` | 1.0 | 1.0 | 0 | 0 |
| `vector` | 1.0 | 1.0 | 0 | 0 |

## R2Q01

**Q:** Compared with prior Multi-Agent Transformer (MAT) models, what aspect of the agents' decision process does AOAD-MAT explicitly model?

**gold:** 2510.13343

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 96.8 | 987 | 0.6148659999999999 | 6 | 否 | **Answer:** AOAD-MAT explicitly models the **order in which agents make their action decisions** — i.e., the sequence of agent action decisions — wher |
| `bm25` | ✓ | ✓ | 18.9 | 118 | 0.19367499999999999 | 0 | 否 | The evidence answers this: AOAD-MAT explicitly models the **order in which agents make decisions** (the sequence of action decisions), which prior MAT |
| `rerank` | ✓ | ✓ | 32.4 | 97 | 0.022205 | 0 | 否 | Based on the evidence, AOAD-MAT explicitly models and learns the **optimal order of agent action decisions** — that is, the sequence in which agents s |
| `rrf` | ✓ | ✓ | 11.5 | 193 | 0.028197 | 0 | 否 | **Answer:** AOAD-MAT explicitly models the **order in which agents make their action decisions** — the sequence of action decisions itself. **Sources  |
| `vector` | ✓ | ✓ | 15.2 | 159 | 0.19077000000000002 | 0 | 否 | **Answer:** AOAD-MAT explicitly models the **optimal order of agent action decisions** — i.e., the sequence in which agents should act. **Source used: |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** AOAD-MAT explicitly models the **order in which agents make their action decisions** — i.e., the sequence of agent action decisions — whereas prior MAT-family models (MAT itself and ACE) trained on sequential decision-making but "do not explicitly consider the importance of the order in which agents make decisions." The paper states AOAD-MAT "explicitly incorporates the sequence of action decisions into the learning process, allowing the model to learn and predict the optimal order of agent actions," via a Transformer-based actor–critic architecture with a subtask that predicts the next agent to act, integrated into a PPO-based loss. It contrasts with MAT's Multi-Agent Advantage Decomposition, which computed inter-agent advantage differences in a fixed order, while AOAD-MAT's dynamic ordering flexibly assesses each agent's contribution. The authors motivate this because order of action decisions affects MARL performance and stability, especially where agents have different capabilities or environment dynamics favor certain action sequences. AOAD-MAT is explicitly distinguished from FoX: FoX reduces the exploration space via spatial relationships, while AOAD-MAT improves exploration capability by considering the sequence of agent decisions. Note the source text writes the framework as "CTCE" in that comparison passage (likely CTDE), so treat that acronym as reported verbatim.

**Sources used:**
- `计算机与人工智能/artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep (part 1 of 2).md` — abstract; chunks 2, 11, 14, 25 (kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba`)
- `计算机与人工智能/artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep (part 2 of 2).md` — chunks 26, 33 (same kb_id)
- Mirror copies in KB `0942f1a6-d81b-413b-a60b-b994680dcaac` (doc `Corpus-Chunks800/...__k02.md`), same content

**[bm25]**

The evidence answers this: AOAD-MAT explicitly models the **order in which agents make decisions** (the sequence of action decisions), which prior MAT/ACE-style models do not explicitly consider. Source: `[2510.13343] artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep (part 1/2)` — abstract. The other two retrieved documents (1909.07748 on stock market microstructure; 2412.06333 on Hanabi conventions) are unrelated to this question and were not used.

**[rerank]**

Based on the evidence, AOAD-MAT explicitly models and learns the **optimal order of agent action decisions** — that is, the sequence in which agents should act.

Source:
- [2510.13343] — the only evidence chunk provided, describing AOAD-MAT as incorporating a dedicated mechanism to predict and optimize the order of agent action decisions.

The evidence is sufficient to answer this question but does not provide details on method, results, or comparisons beyond the above.

**[rrf]**

**Answer:** AOAD-MAT explicitly models the **order in which agents make their action decisions** — the sequence of action decisions itself.

**Sources used:**
- `artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep` (Part 1/2), Abstract.

Per the evidence, prior MARL models such as the Multi-Agent Transformer (MAT) and ACtion dEpendent deep Q-learning (ACE) improve performance through sequential decision-making but "do not explicitly consider the importance of the order in which agents make decisions." The proposed AOAD-MAT (Agent Order of Action Decisions-MAT) addresses this by explicitly incorporating the sequence of action decisions into the learning process. The evidence covering the other two documents (1909.07748, 2412.06333) does not bear on this question. No further detail on the mechanism is present in the retrieved excerpt.

**[vector]**

**Answer:** AOAD-MAT explicitly models the **optimal order of agent action decisions** — i.e., the sequence in which agents should act.

**Source used:** chunk from [2510.13343] describing AOAD-MAT ("Order of Action Decisions-MAT"), which states that it is "a novel Transformer-based multi-agent deep reinforcement learning model that explicitly incorporates and learns the optimal order of agent action decisions," and that it "introduces a dedicated mechanism to predict and optimize the sequence in which agents should act," including a subtask for predicting the next agent to act.

Note: the evidence does not specify how prior MAT models handled action order, so the comparison to prior MAT is limited to AOAD-MAT adding explicit order modeling on top of the MAT architecture.

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ✅ | 0 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=1.0498 · manifest=1.0497 |
| 单元数 = 题数 × 方法数 | ✅ | rows=5 vs 1×5=5 |
| provenance 完整 | ✅ | prompt_version=v3-neutral seed=0 |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*