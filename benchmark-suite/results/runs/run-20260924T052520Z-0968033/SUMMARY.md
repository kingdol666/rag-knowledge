# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-24 05:28 UTC · same corpus · questions: 1 · tracks: a2, bm25, vector, rrf, rerank

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| R2Q01 | a2 | 96.8 | 6 | 106691 | 987 | 113472 | 0.6148659999999999 |
| R2Q01 | bm25 | 18.9 | 0 | 38145 | 118 | 0 | 0.19367499999999999 |
| R2Q01 | rerank | 32.4 | 0 | 244 | 97 | 37120 | 0.022205 |
| R2Q01 | rrf | 11.5 | 0 | 956 | 193 | 37184 | 0.028197 |
| R2Q01 | vector | 15.2 | 0 | 37359 | 159 | 0 | 0.19077000000000002 |

**Totals**: latency avg 35.0s · tokens in 183395 · out 1554 · cost $1.0497

## Verbatim answers

### [a2] R2Q01 — 96.8s, 6 tool calls, tokens out 987

**Q:** Compared with prior Multi-Agent Transformer (MAT) models, what aspect of the agents' decision process does AOAD-MAT explicitly model?

**Answer:** AOAD-MAT explicitly models the **order in which agents make their action decisions** — i.e., the sequence of agent action decisions — whereas prior MAT-family models (MAT itself and ACE) trained on sequential decision-making but "do not explicitly consider the importance of the order in which agents make decisions." The paper states AOAD-MAT "explicitly incorporates the sequence of action decisions into the learning process, allowing the model to learn and predict the optimal order of agent actions," via a Transformer-based actor–critic architecture with a subtask that predicts the next agent to act, integrated into a PPO-based loss. It contrasts with MAT's Multi-Agent Advantage Decomposition, which computed inter-agent advantage differences in a fixed order, while AOAD-MAT's dynamic ordering flexibly assesses each agent's contribution. The authors motivate this because order of action decisions affects MARL performance and stability, especially where agents have different capabilities or environment dynamics favor certain action sequences. AOAD-MAT is explicitly distinguished from FoX: FoX reduces the exploration space via spatial relationships, while AOAD-MAT improves exploration capability by considering the sequence of agent decisions. Note the source text writes the framework as "CTCE" in that comparison passage (likely CTDE), so treat that acronym as reported verbatim.

**Sources used:**
- `计算机与人工智能/artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep (part 1 of 2).md` — abstract; chunks 2, 11, 14, 25 (kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba`)
- `计算机与人工智能/artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep (part 2 of 2).md` — chunks 26, 33 (same kb_id)
- Mirror copies in KB `0942f1a6-d81b-413b-a60b-b994680dcaac` (doc `Corpus-Chunks800/...__k02.md`), same content

### [bm25] R2Q01 — 18.9s, 0 tool calls, tokens out 118

**Q:** Compared with prior Multi-Agent Transformer (MAT) models, what aspect of the agents' decision process does AOAD-MAT explicitly model?

The evidence answers this: AOAD-MAT explicitly models the **order in which agents make decisions** (the sequence of action decisions), which prior MAT/ACE-style models do not explicitly consider. Source: `[2510.13343] artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep (part 1/2)` — abstract. The other two retrieved documents (1909.07748 on stock market microstructure; 2412.06333 on Hanabi conventions) are unrelated to this question and were not used.

### [rerank] R2Q01 — 32.4s, 0 tool calls, tokens out 97

**Q:** Compared with prior Multi-Agent Transformer (MAT) models, what aspect of the agents' decision process does AOAD-MAT explicitly model?

Based on the evidence, AOAD-MAT explicitly models and learns the **optimal order of agent action decisions** — that is, the sequence in which agents should act.

Source:
- [2510.13343] — the only evidence chunk provided, describing AOAD-MAT as incorporating a dedicated mechanism to predict and optimize the order of agent action decisions.

The evidence is sufficient to answer this question but does not provide details on method, results, or comparisons beyond the above.

### [rrf] R2Q01 — 11.5s, 0 tool calls, tokens out 193

**Q:** Compared with prior Multi-Agent Transformer (MAT) models, what aspect of the agents' decision process does AOAD-MAT explicitly model?

**Answer:** AOAD-MAT explicitly models the **order in which agents make their action decisions** — the sequence of action decisions itself.

**Sources used:**
- `artificial-intelligence__2510.13343__aoad-mat-transformer-based-multi-agent-deep` (Part 1/2), Abstract.

Per the evidence, prior MARL models such as the Multi-Agent Transformer (MAT) and ACtion dEpendent deep Q-learning (ACE) improve performance through sequential decision-making but "do not explicitly consider the importance of the order in which agents make decisions." The proposed AOAD-MAT (Agent Order of Action Decisions-MAT) addresses this by explicitly incorporating the sequence of action decisions into the learning process. The evidence covering the other two documents (1909.07748, 2412.06333) does not bear on this question. No further detail on the mechanism is present in the retrieved excerpt.

### [vector] R2Q01 — 15.2s, 0 tool calls, tokens out 159

**Q:** Compared with prior Multi-Agent Transformer (MAT) models, what aspect of the agents' decision process does AOAD-MAT explicitly model?

**Answer:** AOAD-MAT explicitly models the **optimal order of agent action decisions** — i.e., the sequence in which agents should act.

**Source used:** chunk from [2510.13343] describing AOAD-MAT ("Order of Action Decisions-MAT"), which states that it is "a novel Transformer-based multi-agent deep reinforcement learning model that explicitly incorporates and learns the optimal order of agent action decisions," and that it "introduces a dedicated mechanism to predict and optimize the sequence in which agents should act," including a subtask for predicting the next agent to act.

Note: the evidence does not specify how prior MAT models handled action order, so the comparison to prior MAT is limited to AOAD-MAT adding explicit order modeling on top of the MAT architecture.
