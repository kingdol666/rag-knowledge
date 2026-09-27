# 对照实验报告 — `e2e-20260927T111600Z-a476b0f`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-27 11:51 UTC

## 方法清单

| method | 类型 | n |
|---|---|---:|
| `bm25` | baseline | 10 |
| `mode_A` | baseline | 10 |
| `mode_B` | baseline | 10 |
| `mode_C` | baseline | 10 |
| `rerank` | baseline | 10 |
| `rrf` | baseline | 10 |
| `vector` | baseline | 10 |

## 资源监控总表

| method | 时延 avg s | 时延 median s | tokens in | tokens out | 成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `bm25` | 7.58 | 6.3 | 382011 | 9521 | 2.1481 | 0.2148 | 0.0 | — | — |
| `mode_A` | 31.01 | 29.9 | 383555 | 8468 | 2.1295 | 0.2129 | 0.0 | — | — |
| `mode_B` | 9.49 | 9.1 | 374030 | 6104 | 2.0227 | 0.2023 | 0.0 | — | — |
| `mode_C` | 57.83 | 58.6 | 385880 | 7346 | 2.113 | 0.2113 | 0.0 | — | — |
| `rerank` | 14.63 | 14.0 | 377910 | 9492 | 2.1269 | 0.2127 | 0.0 | — | — |
| `rrf` | 13.19 | 7.5 | 382236 | 21970 | 2.4604 | 0.246 | 0.0 | — | — |
| `vector` | 8.98 | 7.5 | 378107 | 11855 | 2.1869 | 0.2187 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 诚实性双向）

| method | 检索金标命中率 | 引用金标命中率 | 正确拒答(应拒答层) | 误拒(可答层) | error 数 |
|---|---:|---:|---:|---:|---:|
| `bm25` | 1.0 | 1.0 | 2/2 (1.0) | 3/8 (0.375) | 0 |
| `mode_A` | 1.0 | 0.375 | 2/2 (1.0) | 7/8 (0.875) | 0 |
| `mode_B` | 0.0 | 0.0 | 2/2 (1.0) | 8/8 (1.0) | 0 |
| `mode_C` | 1.0 | 0.625 | 2/2 (1.0) | 5/8 (0.625) | 0 |
| `rerank` | 1.0 | 1.0 | 2/2 (1.0) | 4/8 (0.5) | 0 |
| `rrf` | 1.0 | 1.0 | 2/2 (1.0) | 5/8 (0.625) | 0 |
| `vector` | 1.0 | 1.0 | 2/2 (1.0) | 3/8 (0.375) | 0 |

> **口径说明**：baseline 的「检索命中」基于其真实 ranked 列表（可直接观测）；agent 轨（a/a2/b/c）的 SSE 轨迹只含工具**入参**、不含检索结果文档 id，故其检索命中由 trace ∪ 答案推断（`retrieval_basis=trace+answer`）。**agent 轨请以「引用命中率」为可靠功能信号。**

## QK01 — `single`

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**gold:** 1706.03762, 1706.03762

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 13.8 | 2430 | 0.25192499999999995 | 0 | 是 | **Answer (from the provided evidence only):** The evidence shows the Transformer uses multi-head attention with h = 8 parallel attention heads, each w |
| `mode_A` | ✓ | ✓ | 40.6 | 472 | 0.20354 | 0 | 是 | **Answer: The evidence is insufficient to answer this question.** The retrieved evidence consists of two documents: (1) `经济与社会/finance__1909.07748__st |
| `mode_B` | ✗ | ✗ | 8.8 | 499 | 0.19948499999999997 | 0 | 是 | The evidence is insufficient: no evidence was retrieved (the EVIDENCE block is empty), so I cannot answer how the Transformer computes attention or wh |
| `mode_C` | ✓ | ✓ | 60.9 | 1172 | 0.22049 | 0 | 是 | **Answer:** The evidence explains *why* the Transformer replaces recurrence, but not *how* it computes attention. According to the Abstract and §1 of  |
| `rerank` | ✓ | ✓ | 18.8 | 1201 | 0.21963999999999997 | 0 | 是 | **Answer (from evidence only):** The evidence explains the *mechanics* of attention but not the *rationale* for replacing recurrence and convolution.  |
| `rrf` | ✓ | ✓ | 9.6 | 1565 | 0.23029999999999998 | 0 | 是 | The evidence shows the Transformer computes attention through multi-head attention: it uses h = 8 parallel attention layers (heads) with d_k = d_v = d |
| `vector` | ✓ | ✓ | 13.8 | 2544 | 0.25321499999999997 | 0 | 是 | Drawing only on the supplied evidence: **[2110.07844]** describes how attention is computed — the cross-attention head transforms the j-th decoder sta |

<details><summary>逐字答案全文</summary>

**[bm25]**

**Answer (from the provided evidence only):**

The evidence shows the Transformer uses multi-head attention with h = 8 parallel attention heads, each with d_k = d_v = d_model/h = 64, where the reduced per-head dimension keeps total computational cost similar to single-head attention at full dimensionality. It states attention is applied in three ways: encoder-decoder attention (queries from the previous decoder layer, keys/values from encoder output, so every decoder position attends over all input positions), encoder self-attention (keys, values, and queries all come from the previous encoder layer, with each position attending to all positions of that layer), and decoder self-attention (excerpt truncated at "allow each position in the de…"). However, the evidence does not include the actual attention computation itself (no scaled dot-product/softmax formulation is present), nor any statement of why the Transformer replaces recurrence and convolution — no motivation about sequential computation, parallelization, or path length appears in the excerpts. The BERT excerpt ([1810.04805]) and the attention-patching excerpt ([2503.21676]) address unrelated mechanisms and do not answer either part of the question. Therefore the evidence only partially answers "how" and is insufficient to answer "why it replaces recurrence and convolution."

**Sources used:** [1706.03762] excerpt (multi-head attention §3.2.2 and §3.2.3 "Applications of Attention in our Model") — the only chunk that speaks to the question. [1810.04805] and [2503.21676] excerpts were reviewed but not used, as they are off-topic.

**[mode_A]**

**Answer: The evidence is insufficient to answer this question.**

The retrieved evidence consists of two documents: (1) `经济与社会/finance__1909.07748__stock-market-microstructure-inference-via-mu (part 1 of 4).md` (multi-agent RL for stock market microstructure inference) and (2) `生命科学与医学/clinical-medicine__2110.08918__using-clinical-drug-representations-for-impr.md` (clinical drug representations for mortality/LOS prediction). Neither document discusses the Transformer architecture, attention computation, recurrence, or convolution.

No source among the retrieved evidence addresses how attention is computed or why it replaces recurrence and convolution, so per the output contract I am reporting a blind spot rather than answering from prior knowledge.

**Sources used:** `finance__1909.07748__stock-market-microstructure-inference-via-mu (part 1 of 4).md` (vec=0.483) and `clinical-medicine__2110.08918__using-clinical-drug-representations-for-impr.md (part 1 of 2).md` (vec=0.552) — both retrieved but neither is relevant.

**[mode_B]**

The evidence is insufficient: no evidence was retrieved (the EVIDENCE block is empty), so I cannot answer how the Transformer computes attention or why it replaces recurrence and convolution.

No sources were used because none were provided, and per the task contract I will not fall back on prior knowledge. Please supply the relevant documents or chunks and I will answer from them alone.

**[mode_C]**

**Answer:** The evidence explains *why* the Transformer replaces recurrence, but not *how* it computes attention.

According to the Abstract and §1 of *Attention Is All You Need*, the Transformer is "based solely on attention mechanisms, dispensing with recurrence and convolutions entirely," relying on attention "to draw global dependencies between input and output." The stated motivation against recurrence is that recurrent models factor computation along symbol positions, and this "inherently sequential nature precludes parallelization within training examples," a limitation that becomes critical at longer sequence lengths. The paper claims the resulting model "allows for significantly more parallelization" and reaches state of the art after as little as twelve hours on eight P100 GPUs, whereas the best prior models trained for 3.5 days on eight GPUs. It also notes attention permits "modeling of dependencies without regard to their distance in the input or output sequences," while prior work used attention "in conjunction with a recurrent network." The retrieved evidence, however, consists only of the Abstract, §1 (Introduction), and the opening lines of §2 (Background, which cuts off mid-sentence while describing convolutional models such as the Extended Neural GPU, ByteNet, and ConvS2S). It contains no description of the attention computation itself — no equations or mechanism details — so the "how" half of the question cannot be answered from this evidence.

**Sources used:** Attention Is All You Need — Abstract, §1 Introduction, §2 Background (first paragraph, truncated). No other sources were available in the evidence.

**[rerank]**

**Answer (from evidence only):**

The evidence explains the *mechanics* of attention but not the *rationale* for replacing recurrence and convolution. [2110.07844] describes the computation: query, key, and value vectors are produced from the decoder and encoder states, attention weights are computed as a normalized dot product between the query and key vectors, and the head output is a weighted sum of the value vectors. [1706.03762] states the Transformer is "the first sequence transduction model based entirely on attention," replacing the recurrent layers most commonly used in encoder–decoder architectures with multi-headed self-attention. [2510.13343] adds only that the attention mechanism "learns to focus on relevant parts of the input data." No retrieved chunk states *why* recurrence (and convolution) were replaced — [1706.03762] is truncated mid-sentence, and the remaining chunks ([1810.04805], [2503.21676], [1906.10015]) do not address the rationale. That part of the question is therefore insufficiently supported by this evidence.

**Sources used:**
- [1706.03762] — Conclusion (truncated)
- [2110.07844] — attention computation (query/key/value, normalized dot product, weighted sum)
- [2510.13343] — attention focuses on relevant input parts

**Sources retrieved but not answering the question:** [1810.04805], [2503.21676], [1906.10015]

**[rrf]**

The evidence shows the Transformer computes attention through multi-head attention: it uses h = 8 parallel attention layers (heads) with d_k = d_v = d_model/h = 64, and because each head has reduced dimension, the total computational cost is similar to single-head attention at full dimensionality. Multi-head attention is applied in three ways: encoder–decoder attention, where queries come from the previous decoder layer while keys and values come from the encoder output, letting every decoder position attend over all input positions; encoder self-attention, where keys, values, and queries all come from the same source (the previous encoder layer's output), so each position can attend to all positions in that layer; and decoder self-attention, described analogously (the cited text is truncated mid-sentence). The other chunks ([1810.04805], [2503.21676]) concern BERT's span-prediction scoring and attention patching with a twin architecture, not the Transformer's core attention computation.

**Insufficient evidence on the second half:** none of the supplied chunks states *why* the Transformer replaces recurrence and convolution (no discussion of path length, parallelism, or long-range dependencies appears in the evidence), so that part of the question cannot be answered from these excerpts. I therefore decline to answer it from prior knowledge, per the contract.

Sources used: [1706.03762] (§3.2.2, §3.2.3 excerpts); [1810.04805] and [2503.21676] (checked, not relevant to the answer).

**[vector]**

Drawing only on the supplied evidence: **[2110.07844]** describes how attention is computed — the cross-attention head transforms the j-th decoder state and i-th encoder state into query, key, and value vectors, computes attention weights as a normalized dot product between the query and key vectors, and produces an output that is a weighted sum of the value vectors. **[1706.03762]** states only that the Transformer was "the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention" — it states the replacement, not the rationale, and the evidence contains no explanation of why recurrence (or convolution) was replaced. **[1810.04805]** mentions the number of self-attention heads and **[2510.13343]** credits attention with focusing on relevant input parts, but neither adds computation details or replacement rationale; **[2503.21676]** and **[1906.10015]** address unrelated analyses.

**Sources used:** [2110.07844] (attention computation), [1706.03762] (replacement of recurrence; no rationale given).

**Verdict:** The "how" is partially answerable from [2110.07844]; the "why it replaces recurrence and convolution" is **not answered by the evidence** — that part is insufficient.

</details>


## QK02 — `single`

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**gold:** 1602.01876, 1602.01876

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 6.3 | 547 | 0.204065 | 0 | 是 | The evidence is insufficient to answer this question. The excerpt from [1602.01876] describes the Gene Ontology project as consisting of "the Gene Ont |
| `mode_A` | ✓ | ✗ | 36.0 | 978 | 0.216195 | 0 | 是 | The evidence is insufficient to answer this question. Neither retrieved chunk mentions the Gene Ontology or any ontologies that subdivide it: the firs |
| `mode_B` | ✗ | ✗ | 9.4 | 605 | 0.202115 | 0 | 是 | The evidence is insufficient: no evidence was retrieved for this question (the evidence block is empty), so I cannot answer which three independent on |
| `mode_C` | ✓ | ✓ | 47.7 | 1495 | 0.23401 | 0 | 是 | **The evidence is insufficient to answer this question.** The only relevant retrieved chunk, `genomics__1602.01876__primer-on-the-gene-ontology.md.md` |
| `rerank` | ✓ | ✓ | 8.4 | 243 | 0.19441 | 0 | 否 | The evidence states that the Gene Ontology's terms are subdivided into three distinct ontologies representing different biological aspects: **Molecula |
| `rrf` | ✓ | ✓ | 7.3 | 858 | 0.212215 | 0 | 是 | The evidence is insufficient to answer this question. - **[1602.01876]** — the Gene Ontology primer excerpt mentions that GO is "a controlled vocabula |
| `vector` | ✓ | ✓ | 6.0 | 424 | 0.19895999999999997 | 0 | 否 | The Gene Ontology subdivides its terms into three distinct ontologies representing different biological aspects: **Molecular Function (MF), Biological |

<details><summary>逐字答案全文</summary>

**[bm25]**

The evidence is insufficient to answer this question. The excerpt from [1602.01876] describes the Gene Ontology project as consisting of "the Gene Ontology itself, which models biological aspects in a structured way, and annotations," but it is truncated before any subdivision of GO into separate ontologies is named. The other two excerpts ([2301.08436] and [2401.06823]) concern spatial transcriptomics gene panels and interpretable deep learning for single-cell omics, respectively, and do not discuss the Gene Ontology's structure at all. No source in the provided evidence states which three independent ontologies subdivide GO.

Sources used: [1602.01876], [2301.08436], [2401.06823] (all consulted; none contain the answer).

**[mode_A]**

The evidence is insufficient to answer this question. Neither retrieved chunk mentions the Gene Ontology or any ontologies that subdivide it: the first is an abstract for the GlobalQA benchmark on "global RAG," and the second is a paper on automated index-structure generation (the GENE framework). No statement in the provided evidence identifies the three ontologies requested. Per the experiment contract, I will not answer from prior knowledge.

Sources reviewed:
- `e2e-demo-0923-022632/global-rag-benchmark.md` (vec=0.3979)
- `计算机与人工智能/databases__2009.10669__there-is-no-such-thing-as-an-index-or-the-ne (part 1 of 4).md` (vec=0.4606)

**[mode_B]**

The evidence is insufficient: no evidence was retrieved for this question (the evidence block is empty), so I cannot answer which three independent ontologies subdivide the Gene Ontology. Per the output contract, I am stopping here rather than drawing on prior knowledge. No sources were used.

**[mode_C]**

**The evidence is insufficient to answer this question.**

The only relevant retrieved chunk, `genomics__1602.01876__primer-on-the-gene-ontology.md.md` (part 1/2), is truncated mid-abstract — it states that GO "is the largest resource for cataloguing gene function" (Gaudet et al., January 2016) but never names the three independent ontologies or any subdivision of the Gene Ontology. The other chunks in the evidence (`soul-template` memory conventions and SOUL persona definitions) contain no Gene Ontology content at all. Per the grounding rules, I will not supply the answer from prior knowledge, so I report no answer rather than an ungrounded one.

Sources consulted:
- `genomics__1602.01876__primer-on-the-gene-ontology.md.md` (part 1/2) — relevant but truncated before the answer
- `soul-template` memory/`SOUL` persona chunks — irrelevant

**[rerank]**

The evidence states that the Gene Ontology's terms are subdivided into three distinct ontologies representing different biological aspects: **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**.

Source used: [1602.01876] (section "2. What is the Gene Ontology?"). The other retrieved chunks ([2110.07787], [2508.18304]) were not relevant to this question.

**[rrf]**

The evidence is insufficient to answer this question.

- **[1602.01876]** — the Gene Ontology primer excerpt mentions that GO is "a controlled vocabulary of terms to represent biology in a structured way" and that the project combines the ontology with annotations, but the passage truncates mid-sentence ("The term…") before naming any subdivision of GO into separate ontologies.
- **[2508.18304]** — monocyte subcluster / scRNA-seq analysis; contains no information about GO's structure.
- **[2110.07787]** — cell-type identification methods review (SingleR, Cell-ID); contains no information about GO's structure.

None of the retrieved sources states which three independent ontologies subdivide the Gene Ontology, so I cannot answer from the provided evidence.

**[vector]**

The Gene Ontology subdivides its terms into three distinct ontologies representing different biological aspects: **Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)**.

Source used: [1602.01876], section "2. What is the Gene Ontology?"

</details>


## QK03 — `single`

**Q:** What physical mechanism does the dynamic electrical model use to explain the hysteretic J-V characteristics of perovskite solar cells?

**gold:** 1606.00335, 1606.00335

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 9.4 | 1334 | 0.22433 | 0 | 否 | **Answer:** The dynamic electrical model explains hysteretic J-V behavior through time-dependent polarization relaxation. In the equivalent circuit of |
| `mode_A` | ✓ | ✓ | 30.3 | 976 | 0.21657 | 0 | 是 | The evidence provided does not contain the answer. Both retrieved passages are about economics/finance: one covers multi-agent reinforcement learning  |
| `mode_B` | ✗ | ✗ | 7.6 | 436 | 0.19791499999999998 | 0 | 是 | The evidence provided contains no retrieved documents, so there is insufficient evidence to answer the question about the physical mechanism used by t |
| `mode_C` | ✓ | ✓ | 58.8 | 918 | 0.21411500000000003 | 0 | 否 | **Answer:** The dynamic electrical model explains hysteretic J–V characteristics through a simple ansatz for **polarization relaxation**. Working from |
| `rerank` | ✓ | ✓ | 13.7 | 924 | 0.21132 | 0 | 否 | The evidence attributes the hysteresis to **polarization relaxation**: paper [1606.00335] introduces a dynamic electrical model whose key ingredient i |
| `rrf` | ✓ | ✓ | 7.6 | 762 | 0.210055 | 0 | 否 | The dynamic electrical model in the evidence describes the solar cell with an equivalent circuit — photocurrent source, diode (ideality factor n), shu |
| `vector` | ✓ | ✓ | 8.3 | 648 | 0.204445 | 0 | 否 | **Answer:** The dynamic electrical model attributes the hysteretic J-V behavior to **polarization relaxation**. By making a simple ansatz for the pola |

<details><summary>逐字答案全文</summary>

**[bm25]**

**Answer:** The dynamic electrical model explains hysteretic J-V behavior through time-dependent polarization relaxation. In the equivalent circuit of [1606.00335], the static elements (photocurrent source I_ph, diode with ideality factor n, shunt resistance R_sh, series resistance R_s) are supplemented by a parallel capacitance C, and the analysis focuses on the variation of the polarization in time under an assumed relaxation time scale; the influence of different relaxation time scales on the hysteretic effects (which also depend on cell preconditioning and bias scan rate) is then investigated. This is the only mechanism described in the evidence — the relevant passage is truncated ("which is gen…"), so the full physical meaning of the capacitance is not spelled out. The other two chunks do not address the hysteresis mechanism: [1712.01369] reports J-V parameters for a perovskite/GeSe bilayer cell, and [2607.03098] concerns energy-storage-system dynamics.

**Sources used:** chunk [1606.00335] (sole source for the mechanism); [1712.01369] and [2607.03098] checked but not relevant.

**[mode_A]**

The evidence provided does not contain the answer. Both retrieved passages are about economics/finance: one covers multi-agent reinforcement learning for stock market microstructure inference (`finance__1909.07748`, part 2 of 4), and the other covers the European Central Bank's conventional and unconventional policies under uncertainty (`economics__2011.14424`, part 1 of 5). Neither mentions perovskite solar cells, J-V characteristics, hysteresis, or any dynamic electrical model, so no physical mechanism can be extracted from this evidence.

Sources examined (not used for an answer, as they proved irrelevant):
- 经济与社会/finance__1909.07748__stock-market-microstructure-inference-via-mu (part 2 of 4).md
- 经济与社会/economics__2011.14424__on-the-effectiveness-of-the-european-central (part 1 of 5).md

Per the task contract, I am reporting the evidence as insufficient rather than answering from prior knowledge.

**[mode_B]**

The evidence provided contains no retrieved documents, so there is insufficient evidence to answer the question about the physical mechanism used by the dynamic electrical model to explain hysteretic J-V characteristics in perovskite solar cells.

Sources used: none (no evidence was retrieved).

**[mode_C]**

**Answer:** The dynamic electrical model explains hysteretic J–V characteristics through a simple ansatz for **polarization relaxation**. Working from that ansatz, the model reproduces both qualitatively and quantitatively the detailed features of measured J–V curves, including pre-poling effects (differences between initially over- and under-polarized samples) and the current overshoot seen in reverse characteristics. Hysteresis behavior is analyzed with respect to bias scan rate, yielding hysteresis amplitude that is maximum at intermediate scan rates and negligible at very slow or very fast rates, plus effects from different relaxation time scales.

**Caveats:** The evidence does not specify the microscopic origin of the polarization relaxation itself; it only lists competing literature attributions for the anomalous hysteresis (giant photoinduced dielectric response, ferroelectric effects, ion migration with charge trapping/detrapping, unbalanced electron/hole distributions). Any statement about the model's internal equations beyond the polarization-relaxation ansatz is not supported by this evidence.

**Source used:** `materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs` (part 1/2) — Abstract and Section 1 (Introduction) of Nemnes et al., "Dynamic electrical behavior of halide perovskite based solar cells."

**[rerank]**

The evidence attributes the hysteresis to **polarization relaxation**: paper [1606.00335] introduces a dynamic electrical model whose key ingredient is "a simple ansatz for the polarization relaxation," which allows it to reproduce measured J–V characteristics of perovskite solar cells both qualitatively and quantitatively. The same source links this to pre-poling effects, distinguishing initially over-polarized from under-polarized samples, and notes the presence of a current overshoot in the J–V response. The second source [1712.01369] only reports simulated J–V curves and extracted parameters (J_sc, V_oc, FF) for a bilayer cell versus a typical perovskite cell, and does not describe any hysteresis mechanism. Beyond naming "polarization relaxation," the evidence does not give the full physical or mathematical form of that mechanism, since the abstract of [1606.00335] is truncated.

Sources used:
- [1606.00335] — Abstract (dynamic electrical model; polarization relaxation ansatz; pre-poling effects).
- [1712.01369] — Excerpt (J–V simulation and parameters; no hysteresis mechanism).

**[rrf]**

The dynamic electrical model in the evidence describes the solar cell with an equivalent circuit — photocurrent source, diode (ideality factor n), shunt resistance R_sh, series resistance R_s — plus an added parallel capacitance C that distinguishes it from the static model [1606.00335]. Hysteretic J-V behavior is explained through the variation of the polarization in time, governed by a characteristic relaxation time scale; the influence of different relaxation time scales is explicitly investigated [1606.00335]. Hysteresis in the simulated J-V curves is also linked to solar cell preconditioning and the bias scan rate [1606.00335]. The evidence does not name a more specific microscopic physical mechanism (e.g., ion migration) beyond this time-dependent polarization/relaxation picture. The other retrieved items are not on point: [1712.01369] discusses perovskite/GeSe bilayer efficiency, and [2607.03098] concerns energy storage models, neither addressing the hysteresis mechanism.

Sources used: [1606.00335] (mechanism and hysteresis discussion); [1712.01369] and [2607.03098] (reviewed, not used as answers).

**[vector]**

**Answer:** The dynamic electrical model attributes the hysteretic J-V behavior to **polarization relaxation**. By making a simple ansatz for the polarization relaxation, the model is able to reproduce qualitatively and quantitatively detailed features of measured J-V characteristics, including pre-poling effects (differences between initially over- and under-polarized samples) and the current overshoot. The retrieved evidence also notes the model's ability to capture these measured features, though the abstract excerpt is truncated mid-sentence ("the presence of the current overshoot obse…"), so no further mechanistic detail (e.g., the specific relaxation functional form) is available in the evidence. The second evidence item ([1712.01369]) concerns a bilayer solar cell J-V simulation and does not describe the hysteresis mechanism, so it was not used.

**Sources used:**
- [1606.00335] — Abstract (dynamic electrical model; polarization relaxation ansatz)
- [1712.01369] — retrieved but not used (no mechanism information)

</details>


## QK04 — `single`

**Q:** Using only what kind of information, and reaching what accuracy, does the wav2vec 2.0 approach detect within-sentence prosodic boundaries on Czech broadcast news?

**gold:** 2209.15032, 2209.15032

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 5.8 | 733 | 0.209745 | 0 | 否 | Using only acoustic information (no text or transcripts), the wav2vec 2.0 framework was applied to detect prosodic boundaries in speech. Tested on rec |
| `mode_A` | ✓ | ✗ | 27.8 | 435 | 0.20239 | 0 | 是 | The evidence is insufficient to answer this question. Neither retrieved chunk discusses wav2vec 2.0, prosodic boundary detection, or Czech broadcast n |
| `mode_B` | ✗ | ✗ | 12.4 | 1214 | 0.21743 | 0 | 是 | The evidence retrieved for this question is empty — no document passages, paths, or chunk IDs were provided. Because the question asks specifically ab |
| `mode_C` | ✓ | ✓ | 58.4 | 753 | 0.21355500000000002 | 0 | 否 | **Answer:** The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no transcripts/text), achieving  |
| `rerank` | ✓ | ✓ | 10.0 | 613 | 0.20297500000000002 | 0 | 否 | Using only acoustic information, the wav2vec 2.0 model detects within-sentence prosodic boundaries in Czech broadcast news with 94% accuracy and an F1 |
| `rrf` | ✓ | ✓ | 7.3 | 922 | 0.21446999999999997 | 0 | 否 | The wav2vec 2.0 approach detects prosodic boundaries in speech using **only acoustic information** (no text/transcripts), and on recordings of Czech b |
| `vector` | ✓ | ✓ | 6.6 | 412 | 0.19797499999999998 | 0 | 否 | Using only acoustic information, the wav2vec 2.0 model detects within-sentence prosodic boundaries in Czech broadcast news with 94% accuracy (and an F |

<details><summary>逐字答案全文</summary>

**[bm25]**

Using only acoustic information (no text or transcripts), the wav2vec 2.0 framework was applied to detect prosodic boundaries in speech. Tested on recordings of Czech broadcast news labeled by phonetic experts, the model reached 94% accuracy and an F1 of 83% on within-sentence prosodic boundaries (or 95% accuracy / 89% F1 across all prosodic boundaries). This was achieved despite a relatively small amount of labeled data, and it outperformed the existing text-based predictor that used transcripts of the same data.

Source: [2209.15032] "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" — chunk `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (part 1/2).

**[mode_A]**

The evidence is insufficient to answer this question.

Neither retrieved chunk discusses wav2vec 2.0, prosodic boundary detection, or Czech broadcast news. The two sources provided are:

- `e2e-demo-0923-022632/global-rag-benchmark.md` — a benchmark paper on global RAG (GlobalQA / Global-RAG), covering corpus-level reasoning tasks such as counting, extremum, sorting, and top-k extraction.
- `经济与社会/economics__1911.06206__bayesian-state-space-modeling-for-analyzing (part 1 of 5).md` — an econometrics paper on Bayesian state-space modeling of heterogeneous network effects of US monetary policy.

Neither contains any information about what input signal the wav2vec 2.0 approach uses or what accuracy it achieves for within-sentence prosodic boundary detection on Czech broadcast news. Per the output contract, I am stopping here rather than answering from prior knowledge.

**[mode_B]**

The evidence retrieved for this question is empty — no document passages, paths, or chunk IDs were provided. Because the question asks specifically about wav2vec 2.0's input information type and boundary-detection accuracy on Czech broadcast news, and I am required to answer only from the supplied evidence, I cannot answer it.

Sources used: none (no evidence retrieved). The evidence is insufficient to answer the question, so I am stopping here rather than drawing on prior knowledge.

**[mode_C]**

**Answer:** The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no transcripts/text), achieving **94% accuracy and 83% F1** on Czech broadcast news recordings labeled by phonetic experts. For comparison, across all prosodic boundaries it reaches 95% accuracy and 89% F1, and it outperforms the text-based predictor despite being trained on a relatively small amount of labeled data.

**Source used:**
- `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (part 1/2), section "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" — abstract.

(The duplicated `soul-template` persona chunks in the evidence are unrelated to this question and were not used.)

**[rerank]**

Using only acoustic information, the wav2vec 2.0 model detects within-sentence prosodic boundaries in Czech broadcast news with 94% accuracy and an F1 measure of 83% (trained on a relatively small amount of expert-labeled data, without using transcripts).

Source: [2209.15032] (evidence chunk from the arXiv paper on wav2vec 2.0 prosodic boundary detection in Czech broadcast news).

**[rrf]**

The wav2vec 2.0 approach detects prosodic boundaries in speech using **only acoustic information** (no text/transcripts), and on recordings of Czech broadcast news labeled by phonetic experts it achieves **94% accuracy and an F1 measure of 83% on within-sentence prosodic boundaries** — or 95% accuracy / 89% F1 on all prosodic boundaries — despite using a relatively small amount of labeled data, outperforming the text-based predictor.

Source used: `[2209.15032] Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0` (chunk id `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u`, part 1/2).

**[vector]**

Using only acoustic information, the wav2vec 2.0 model detects within-sentence prosodic boundaries in Czech broadcast news with 94% accuracy (and an F1 measure of 83%) on expert-labeled recordings.

Source used: chunk [2209.15032].

</details>


## QK05 — `single`

**Q:** In the trap-cropping optimization framework, roughly what share of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant?

**gold:** 2508.05896, 2508.05896

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 5.9 | 395 | 0.20090499999999997 | 0 | 否 | When trap plants are 5 to 25 times more attractive than the cash plant, roughly **7–10% of the field** should be allocated to trap plants. The evidenc |
| `mode_A` | ✓ | ✗ | 26.8 | 515 | 0.20469 | 0 | 是 | The provided evidence does not contain the answer. Neither retrieved chunk relates to trap-cropping or agricultural pest management: one is the Global |
| `mode_B` | ✗ | ✗ | 9.6 | 337 | 0.195515 | 0 | 是 | The evidence provided is empty — no documents, chunks, or sources were retrieved for this question. Because I am required to answer using only the ret |
| `mode_C` | ✓ | ✗ | 57.2 | 376 | 0.201205 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved passage is from *Pride and Prejudice* (part 11/26) and concerns Jane Bennet's disa |
| `rerank` | ✓ | ✓ | 16.1 | 1365 | 0.22179999999999997 | 0 | 是 | The evidence states that roughly 7–10% of the field should be allocated to trap plants, and that when trap plants are five times more attractive than  |
| `rrf` | ✓ | ✓ | 6.8 | 694 | 0.208405 | 0 | 否 | Roughly 7–10% of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant. The evidence states tha |
| `vector` | ✓ | ✓ | 7.1 | 982 | 0.2122 | 0 | 否 | **Answer:** Roughly 7–10% of the field — about a tenth of the land — should be allocated to trap plants in that range. The evidence states that at an  |

<details><summary>逐字答案全文</summary>

**[bm25]**

When trap plants are 5 to 25 times more attractive than the cash plant, roughly **7–10% of the field** should be allocated to trap plants. The evidence states that for trap plants "5 and 25 times more attractive, approximately 7–10% of the field should be allocated to trap plants," and that at five times attractiveness it is "optimal to devote roughly ten percent of the land to the trap crop (Figure 3b)." By contrast, when trap plants are only twice as attractive, trap cropping is ineffective and the grower should plant only cash plants.

Source: [2508.05896] — text accompanying Figure 3 (panels b and c) on grower yield versus proportion of cash plants in trap-cropping systems.

**[mode_A]**

The provided evidence does not contain the answer. Neither retrieved chunk relates to trap-cropping or agricultural pest management: one is the GlobalQA benchmark paper on corpus-level RAG ("e2e-demo-0923-022632/global-rag-benchmark.md"), and the other is "mathematics__2211.12700__tailored-presolve-techniques-in-branch-and-b.md (part 1 of 5).md," which concerns presolve techniques for mixed-integer optimal control. No chunk states any proportional field allocation for trap plants, nor mentions the 5–25× attractiveness ratio. The evidence is therefore insufficient to answer this question, and I am reporting that rather than drawing on prior knowledge.

Sources used: e2e-demo-0923-022632/global-rag-benchmark.md; 工程与能源/mathematics__2211.12700__tailored-presolve-techniques-in-branch-and-b.md (part 1 of 5).md.

**[mode_B]**

The evidence provided is empty — no documents, chunks, or sources were retrieved for this question.

Because I am required to answer using only the retrieved evidence and must not fall back on prior knowledge, I cannot answer what share of the field should be allocated to trap plants under the 5–25× attractiveness scenario.

The evidence is insufficient. No sources were available to cite.

Please re-run retrieval against the relevant knowledge base (or provide the source document) so the question can be answered from grounded evidence.

**[mode_C]**

The evidence is insufficient to answer this question. The retrieved passage is from *Pride and Prejudice* (part 11/26) and concerns Jane Bennet's disappointment over Miss Bingley's changed behavior and her letter to Elizabeth — it contains nothing about trap-cropping, trap plants, field allocation, or attractiveness ratios. No source in the provided evidence addresses the trap-cropping optimization framework, so I cannot state what share of the field should be allocated to trap plants at 5–25× attractiveness.

Source used: pride_and_prejudice (part 11/26) — consulted, irrelevant to the question.

**[rerank]**

The evidence states that roughly 7–10% of the field should be allocated to trap plants, and that when trap plants are five times more attractive than the cash plant, the optimum is "roughly ten percent of the land" (Figure 3b). It also notes that for more attractive trap plants, prevented yield loss is less sensitive to the number of trap plants (comparing Figure 3b to Figure 2 and Figure 3c). However, the passage does not give an explicit allocation figure for attractiveness of 25, so for that specific end of the range the evidence is insufficient.

Source used: [2508.05896], the provided excerpt on trap-cropping optimization.

**[rrf]**

Roughly 7–10% of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant. The evidence states that for trap plants "5 and 25 times more attractive, approximately 7–10% of the field should be allocated to trap plants." It further specifies that at five times attractiveness, "it is optimal to devote roughly ten percent of the land to the trap crop (Figure 3b)." By contrast, at only twice the attractiveness, trap cropping is ineffective and the grower should plant only cash plants.

Sources used:
- Chunk from [2508.05896] — Figure 3 caption and surrounding body text (trap-cropping optimization, paragraphs preceding Figure 3b).

**[vector]**

**Answer:** Roughly 7–10% of the field — about a tenth of the land — should be allocated to trap plants in that range. The evidence states that at an attractiveness of five (five times more likely to settle than on a cash plant), it is optimal to devote roughly ten percent of the land to the trap crop (Figure 3b), and for the higher attractiveness level the fragment "approximately 7–10% of the field should be allocated to trap plants" appears, with prevented yield loss being less sensitive to trap-plant number at higher attractiveness.

**Source used:** [2508.05896] (the provided evidence excerpt; the text is truncated mid-sentence at "Interestingly, from figur", so the full 25× figure is inferred from the partial line beginning "ctive, approximately 7–10%…").

</details>


## QK06 — `single`

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**gold:** 1503.07557, 1503.07557

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 8.1 | 1192 | 0.22053499999999998 | 0 | 否 | **Answer:** The evidence does not identify a single factor as "primarily" controlling the response — it states that "several physical contributions go |
| `mode_A` | ✓ | ✗ | 27.1 | 624 | 0.20884000000000003 | 0 | 是 | **The evidence is insufficient to answer this question.** The retrieved chunks are: (1) `e2e-demo-0923-022632/global-rag-benchmark.md` — a RAG evaluat |
| `mode_B` | ✗ | ✗ | 8.4 | 300 | 0.1945 | 0 | 是 | The evidence is insufficient: no evidence was retrieved (the evidence block is empty), so I cannot answer which physical factor controls the response  |
| `mode_C` | ✓ | ✗ | 58.9 | 628 | 0.20708 | 0 | 是 | The evidence is insufficient to answer this question. The only retrieved source is "Towards Global Retrieval Augmented Generation: A Benchmark for Cor |
| `rerank` | ✓ | ✓ | 21.2 | 2370 | 0.248055 | 0 | 是 | **Answer:** The retrieved evidence does not explicitly name the physical factor that primarily controls the response of precipitation extremes to clim |
| `rrf` | ✓ | ✓ | 49.2 | 10278 | 0.447565 | 0 | 是 | The evidence points to the **thermodynamic contribution**: the abstract of O'Gorman's review states that "several physical contributions govern the re |
| `vector` | ✓ | ✓ | 9.2 | 1258 | 0.22023 | 0 | 是 | The evidence does not explicitly identify which physical factor primarily controls the response of precipitation extremes to climate change. The most  |

<details><summary>逐字答案全文</summary>

**[bm25]**

**Answer:** The evidence does not identify a single factor as "primarily" controlling the response — it states that "several physical contributions govern the response of precipitation extremes" to climate change. Among these, the **thermodynamic contribution** is described as robust and well understood, while theoretical understanding of the **microphysical** and **dynamical** contributions is still being developed. The same source adds that the sensitivity of precipitation extremes to warming remains uncertain when convection is important, and may be higher in the tropics than in the extratropics. So the strongest evidence-supported statement is that the thermodynamic contribution is the well-understood one, but the response is governed by multiple physical contributions rather than one primary factor. The other two retrieved chunks (on an emulator's climate-change signal and on a GPC/m precipitation dataset) do not address this question.

**Source used:**
- `[1503.07557] climate-science__1503.07557__precipitation-extremes-under-climate-change.md` (Part 1/3 — abstract)

**[mode_A]**

**The evidence is insufficient to answer this question.**

The retrieved chunks are: (1) `e2e-demo-0923-022632/global-rag-benchmark.md` — a RAG evaluation benchmark paper (GlobalQA, Global-RAG); (2) `soul-cs-library/memory-conventions.md`; (3) `soul-e2e-tester-024115/memory-conventions.md`; (4) `soul-demo-qa/memory-conventions.md` — SOUL persona memory conventions.

None of these documents mention precipitation extremes, climate change, or any physical controlling factor. No chunk in the evidence addresses the topic, so I cannot answer without falling back on prior knowledge, which the task forbids.

**[mode_B]**

The evidence is insufficient: no evidence was retrieved (the evidence block is empty), so I cannot answer which physical factor controls the response of precipitation extremes to climate change.

Sources used: none — no documents or chunks were provided or retrieved. I am stopping here rather than answering from prior knowledge.

**[mode_C]**

The evidence is insufficient to answer this question.

The only retrieved source is "Towards Global Retrieval Augmented Generation: A Benchmark for Corpus-Level Reasoning" (GlobalQA / Global-RAG paper by Luo et al., Fudan University). That document covers retrieval-augmented generation benchmarks, corpus-level task types (counting, extremum, sorting, top-k), and RAG baselines — it contains no content about precipitation extremes, climate change, or any physical controlling factor.

Source used: GlobalQA benchmark paper excerpt (chunk shown in EVIDENCE, image reference `images/838ff38197a58dd916888ef6cc7803a82e53db9b32898de2754d99b5b76b9a6c.jpg`).

Since no evidence addresses the physical factor controlling precipitation-extreme responses to climate change, I cannot answer without falling back on prior knowledge, which the task prohibits. No answer is given.

**[rerank]**

**Answer:** The retrieved evidence does not explicitly name the physical factor that primarily controls the response of precipitation extremes to climate change, so the question cannot be answered definitively from these chunks. The most directly relevant source, [1503.07557] (O'Gorman, "Precipitation extremes under climate change"), states the topic is examined "with a focus on the physical factors that control the response," but the excerpt is truncated before any factor is identified. [2409.13934] reports a strong warming-driven signal for extreme precipitation consistent with Clausius-Clapeyron scaling (~7%/°C), which hints at thermodynamic moisture control, but it does not frame that as the primary controlling factor. [2007.10574] mentions vertical moisture flux convergence and vertical moisture advection only in the context of MJO-induced precipitation anomalies, not the climate-change response of extremes. On this evidence, the requested "primary physical factor" is not stated.

**Sources used:**
- [1503.07557] "Precipitation extremes under climate change" (Abstract)
- [2409.13934] (extreme-precipitation / Clausius-Clapeyron excerpt)
- [2007.10574] §3.2 "Dynamical Links between Precipitation Extremes and MJO"

**[rrf]**

The evidence points to the **thermodynamic contribution**: the abstract of O'Gorman's review states that "several physical contributions govern the response of precipitation extremes" and singles out "the thermodynamic contribution" as the one that is "robust and well understood," while theoretical understanding of the microphysical and dynamical contributions is still being developed. However, the evidence does not literally state that any single factor "primarily" controls the response, and only Part 1/3 of that document (the abstract) is provided — so if the question demands one explicit primary factor, the provided evidence is insufficient beyond identifying the thermodynamic contribution as the robust, well-understood one. The other two evidence chunks ([2409.13934] on an emulator's climate-change signal; [2007.10574] on MJO modulation of extremes in Indonesia) do not address the question.

Sources used: `[1503.07557] climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (Part 1/3, abstract).

**[vector]**

The evidence does not explicitly identify which physical factor primarily controls the response of precipitation extremes to climate change. The most on-topic source, O'Gorman [1503.07557], states only that the analysis focuses "on the physical factors that control the response" and then truncates before naming them. The remaining chunks give only indirect hints: [2409.13934] references a warming-driven Clausius-Clapeyron signal (~7%/°C) for extreme precipitation, which points toward atmospheric moisture, and [2007.10574] examines vertical moisture flux convergence and vertical moisture advection — but in the specific context of MJO-induced events, not the general climate-change response. On this evidence, I cannot state which factor primarily controls the response; that specific claim is insufficiently supported.

Sources used: [1503.07557] O'Gorman, "Precipitation extremes under climate change"; [2409.13934]; [2007.10574] Section 3.2.

</details>


## QK07 — `distractor`

**Q:** What is MameLoshnLM and what parameter scale does it have?

**gold:** 2608.05850, 2608.05850

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 5.2 | 551 | 0.20527 | 0 | 是 | **Answer: The evidence is insufficient to answer this question.** The only relevant evidence is chunk [2608.05850], which mentions “MAMELOSHNLM” solel |
| `mode_A` | ✓ | ✓ | 28.1 | 594 | 0.206485 | 0 | 否 | MAMELOSHNLM is the first open-source 8B-parameter language model built specifically for Yiddish, described as being obtained by continuing pretraining |
| `mode_B` | ✗ | ✗ | 7.5 | 312 | 0.19477999999999998 | 0 | 是 | The evidence is insufficient: no documents or chunks were retrieved for this question ("no evidence retrieved"), so I cannot state what MameLoshnLM is |
| `mode_C` | ✓ | ✗ | 56.5 | 360 | 0.200185 | 0 | 是 | The evidence does not contain the answer. The provided material is an excerpt from the paper "Attention Is All You Need" (Vaswani et al., Google), cov |
| `rerank` | ✓ | ✓ | 11.1 | 660 | 0.204075 | 0 | 是 | **Answer:** The evidence identifies MAMELOSHNLM (Mame-Loshn, "mother tongue") as the first open-source large language model for Yiddish, trained on th |
| `rrf` | ✓ | ✓ | 15.5 | 2736 | 0.25992 | 0 | 是 | The evidence is insufficient to fully answer the question. - **What the evidence does support:** The only source mentioning the model, [2608.05850] (§ |
| `vector` | ✓ | ✓ | 7.2 | 836 | 0.208475 | 0 | 是 | **Answer:** According to the evidence, MAMELOSHNLM is described as the first open-source large language model for Yiddish, trained on the Yiddish corp |

<details><summary>逐字答案全文</summary>

**[bm25]**

**Answer: The evidence is insufficient to answer this question.**

The only relevant evidence is chunk [2608.05850], which mentions “MAMELOSHNLM” solely inside a description of statistical testing: it compares MAMELOSHNLM against Llama 3.1 8B on lemmatization using McNemar's exact test. That chunk never states what MameLoshnLM is (e.g., its architecture, purpose, or language) and gives no parameter count or scale for it. The other two chunks ([2212.13138] and [2005.14165]) do not mention MameLoshnLM at all.

**Sources used:** [2608.05850] (only source that mentions the model, but only re: McNemar's test); [2212.13138] and [2005.14165] (checked, not relevant).

**[mode_A]**

MAMELOSHNLM is the first open-source 8B-parameter language model built specifically for Yiddish, described as being obtained by continuing pretraining of Llama 3.1 8B. It was developed using two introduced resources: **Oytser**, a high-quality Yiddish pretraining corpus combining contemporary web-native sources with literary materials, and **Kashes**, a multi-task benchmark covering translation, linguistic analysis, information extraction, and language understanding. Its parameter scale is therefore **8 billion (8B) parameters**.

Source used:
- `计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md (part 1 of 4).md` (abstract)

The second retrieved chunk (clinical-medicine paper) was not relevant and was not used.

**[mode_B]**

The evidence is insufficient: no documents or chunks were retrieved for this question ("no evidence retrieved"), so I cannot state what MameLoshnLM is or its parameter scale. I am instructed to answer only from the provided evidence and not fall back on prior knowledge, so I will not speculate. No sources were used, since none were supplied. If you can retrieve relevant documents (e.g., a paper, model card, or KB entry mentioning MameLoshnLM), I can answer from them.

**[mode_C]**

The evidence does not contain the answer. The provided material is an excerpt from the paper "Attention Is All You Need" (Vaswani et al., Google), covering the abstract, introduction, and background on the Transformer architecture, BLEU results for WMT 2014 translation, and related work such as ByteNet and ConvS2S. The term "MameLoshnLM" does not appear anywhere in this evidence, and no parameter scale for it is mentioned. Therefore, I cannot answer what MameLoshnLM is or what parameter scale it has based solely on the provided evidence.

Source used: "Attention Is All You Need" excerpt (only source provided).

**[rerank]**

**Answer:** The evidence identifies MAMELOSHNLM (Mame-Loshn, "mother tongue") as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2, and reports that it outperforms strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks. Its training method is described as continued pretraining, but the retrieved text is truncated at that point.

On the parameter scale: the provided evidence does **not** contain the model's parameter count — it only refers to "baselines of similar scale." That part of the question cannot be answered from this evidence.

**Source used:** [2608.05850] §5 "MAMELOSHNLM" (only this chunk; it is truncated mid-sentence at "continued pretrain").

**[rrf]**

The evidence is insufficient to fully answer the question.

- **What the evidence does support:** The only source mentioning the model, [2608.05850] (§E.7 "Statistical Testing"), identifies MAMELOSHNLM as one of two models in pairwise lemmatization (and sentence-level translation) comparisons against Llama 3.1 8B, evaluated with McNemar's exact test on paired token-level correct/incorrect outcomes — i.e., it is a model that produces lemmatization predictions.
- **What the evidence does not support:** It never states what MameLoshnLM is (no description of its architecture, training data, or purpose) and never gives its parameter scale; the only scale mentioned ("8B") belongs to the comparison model Llama 3.1 8B, not to MAMELOSHNLM.
- The other two evidence items ([2212.13138], [2005.14165]) do not mention MameLoshnLM at all.

**Sources used:** [2608.05850] §E.7 Statistical Testing (chunk containing the McNemar's test description); [2212.13138]; [2005.14165] (checked — no mention).

**[vector]**

**Answer:** According to the evidence, MAMELOSHNLM is described as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2. Its name derives from the traditional Yiddish term "mame-loshn" ("mother tongue"), evoking the language's intimate connection to home and family. The evidence states that it outperforms strong baselines "of similar scale" across a broad set of Yiddish evaluation benchmarks, and that it was produced by continued pretraining — but the sentence is truncated there. **The evidence does not state MameLoshnLM's parameter count or parameter scale**; the only scale-related information is the vague reference to baselines "of similar scale." Therefore the parameter-scale part of the question cannot be answered from this evidence.

**Source used:** chunk from [2608.05850], section "## 5 MAMELOSHNLM".

</details>


## QK08 — `crosskb`

**Q:** Beyond which percentile of precipitation did the GAN clearly outperform the deterministic baseline in capturing the climate-change wetting signal?

**gold:** 2409.13934, 2409.13934

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 8.9 | 1307 | 0.22389 | 0 | 否 | **Answer:** The evidence places this at the **99.5th percentile** of precipitation: the GAN trained on both future and historical periods captures ~97 |
| `mode_A` | ✓ | ✗ | 32.8 | 1723 | 0.234635 | 0 | 是 | **Insufficient evidence.** The two retrieved sources do not address this question: `e2e-demo-0923-022632/global-rag-benchmark.md` is a RAG benchmark p |
| `mode_B` | ✗ | ✗ | 9.9 | 796 | 0.20692 | 0 | 是 | The evidence is insufficient to answer this question: no evidence was retrieved (the evidence block is empty), so there is no document, file, or chunk |
| `mode_C` | ✓ | ✓ | 58.0 | 437 | 0.202595 | 0 | 否 | The evidence states that the historically trained GAN and the deterministic baseline had relatively similar signals up to the 95th percentile, and tha |
| `rerank` | ✓ | ✓ | 9.1 | 340 | 0.196 | 0 | 否 | **Answer:** Beyond the **95th percentile** of precipitation. Per the evidence: the GAN and deterministic baselines show relatively similar climate-cha |
| `rrf` | ✓ | ✓ | 14.2 | 2501 | 0.253765 | 0 | 是 | The retrieved evidence quantifies the GAN-versus-baseline comparison only at the 99.5th percentile of precipitation: the GAN trained on future and his |
| `vector` | ✓ | ✓ | 5.3 | 464 | 0.1991 | 0 | 否 | **Answer:** The 95th percentile. The GAN and the deterministic baselines had relatively similar climate-change signals up to the 95th percentile of pr |

<details><summary>逐字答案全文</summary>

**[bm25]**

**Answer:** The evidence places this at the **99.5th percentile** of precipitation: the GAN trained on both future and historical periods captures ~97% of the average future increase in the 99.5th percentile, and even the historically-trained GAN captures ~77%, whereas the two deterministic baselines capture only 63–65% — so the GAN clearly outperforms the baselines at the 99.5th percentile. However, the evidence does not state a percentile threshold "beyond which" the GAN outperforms; the 99.5th percentile is the only percentile level for which a GAN-vs-baseline comparison is reported here, so any finer boundary would be an unsupported extrapolation.

**Sources used:** [2409.13934] (text on the climate-change signal in the 99.5th percentile of precipitation, plus the Figure 2 caption). The other two evidence chunks ([2007.10574] on MJO effects in Indonesia; [2409.09639] on GSMaP/GPC precipitation datasets) contain no GAN-vs-baseline percentile comparison and were not used.

**[mode_A]**

**Insufficient evidence.** The two retrieved sources do not address this question: `e2e-demo-0923-022632/global-rag-benchmark.md` is a RAG benchmark paper on corpus-level reasoning (GlobalQA / Global-RAG), and `生命科学与医学/genomics__2602.10156__strand-sequence-conditioned-transport-for-si (part 1 of 6).md` is a genomics paper on sequence-conditioned single-cell perturbation modeling. Neither mentions precipitation percentiles, GANs, deterministic baselines, or a climate-change wetting signal. Per the instructions, I cannot supply the percentile from prior knowledge, so no answer can be given from the evidence provided.

**[mode_B]**

The evidence is insufficient to answer this question: no evidence was retrieved (the evidence block is empty), so there is no document, file, or chunk to ground an answer about the precipitation percentile beyond which a GAN outperformed a deterministic baseline.

Sources used: none (no evidence retrieved). Per the output contract, I am stopping here rather than answering from prior knowledge.

**[mode_C]**

The evidence states that the historically trained GAN and the deterministic baseline had relatively similar signals up to the 95th percentile, and that **beyond the 95th percentile** the GAN substantially better captured the wetting signal (though both underestimated its magnitude versus CCAM). So the answer is the 95th percentile of precipitation.

Source used: `climate-science__2409.13934__on-the-extrapolation-of-generative-adversari` (part 2/3), section "3.2 Extreme Precipitation Climate Change Signal".

**[rerank]**

**Answer:** Beyond the **95th percentile** of precipitation.

Per the evidence: the GAN and deterministic baselines show relatively similar climate-change signals up to the 95th percentile of precipitation, but beyond the 95th percentile the GAN substantially better captures the wetting signal (though both underestimate its magnitude compared to CCAM). GANs trained on future periods also accurately capture the climate change signal across nearly all percentiles (Figure 1c, Supplementary Figure S9), which the deterministic baselines underestimate.

**Source used:** [2409.13934] (chunk containing the dry-bias / wetting-signal comparison text).

**[rrf]**

The retrieved evidence quantifies the GAN-versus-baseline comparison only at the 99.5th percentile of precipitation: the GAN trained on future and historical periods captures about 97% of the average future increase in the 99.5th percentile, and the GAN trained on historical simulations about 77%, whereas the two deterministic baseline algorithms capture only 63–65% of that increase regardless of training period. So at the 99.5th percentile, the GAN clearly outperforms the deterministic baselines. The evidence does not state a lower percentile threshold beyond which this outperformance begins; if the question asks for such a cutoff, the evidence is insufficient to determine it.

Sources used: [2409.13934] (chunk on GAN vs. deterministic baselines, 99.5th-percentile precipitation).

**[vector]**

**Answer:** The 95th percentile. The GAN and the deterministic baselines had relatively similar climate-change signals up to the 95th percentile of precipitation, but **beyond the 95th percentile the GAN substantially better captured the wetting signal**, though both still underestimated its magnitude relative to CCAM.

**Sources used:**
- Evidence chunk `[2409.13934]` (quoted excerpt on dry bias, the 95th-percentile threshold, and the GAN's wetting-signal capture).

</details>


## QK09 — `unanswerable`

**Q:** What is the recommended daily dosage of metformin for diabetic cats?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | — | — | 6.0 | 610 | 0.20598499999999997 | 0 | 是 | The evidence is insufficient to answer this question. The three retrieved sources concern entirely different topics: [2110.08918] covers ICU length-of |
| `mode_A` | — | — | 29.5 | 1438 | 0.22606 | 0 | 是 | The evidence is insufficient to answer this question. The only retrieved source — `生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode |
| `mode_B` | — | — | 12.9 | 1013 | 0.21229499999999996 | 0 | 是 | The evidence provided contains no retrieved content at all ("no evidence retrieved"), so I cannot answer this question from the given material. The ev |
| `mode_C` | — | — | 61.1 | 551 | 0.20525000000000002 | 0 | 是 | The evidence is insufficient to answer this question. The only source provided — `clinical-medicine__2212.13138__large-language-models-encode-clinical |
| `rerank` | — | — | 14.3 | 782 | 0.21197 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved passages mentions metformin, feline patients, or any drug dosage: the only |
| `rrf` | — | — | 7.0 | 667 | 0.20798499999999998 | 0 | 是 | The provided evidence does not contain an answer to this question. The three retrieved chunks cover unrelated topics: ICU length-of-stay and mortality |
| `vector` | — | — | 18.5 | 3446 | 0.278545 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved chunks mention metformin, feline/cat patients, or any drug dosage recommen |

<details><summary>逐字答案全文</summary>

**[bm25]**

The evidence is insufficient to answer this question. The three retrieved sources concern entirely different topics: [2110.08918] covers ICU length-of-stay and mortality prediction from clinical notes; [2409.09639] describes machine-learning precipitation estimation (GPC/m dataset); [2412.15058] concerns interactive image segmentation with MultiverSeg. None of them mention metformin, diabetes, cats, or any veterinary drug dosage. I therefore cannot provide the recommended daily dosage of metformin for diabetic cats, and per the task contract I will not fall back on prior knowledge.

Sources examined (all irrelevant to the question):
- [2110.08918] — clinical predictive modeling (ICU LOS/mortality)
- [2409.09639] — GPC/m precipitation dataset
- [2412.15058] — MultiverSeg image segmentation

No further answer can be given from this evidence.

**[mode_A]**

The evidence is insufficient to answer this question. The only retrieved source — `生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md (part 2 of 8)` — is a section on clinician evaluation of large language model answers to consumer medical questions (Table 2's axes: scientific consensus, harm, comprehension, retrieval, reasoning), and it contains no mention of metformin, cats, diabetes treatment, or any drug dosage. I therefore cannot provide the recommended daily dosage from this evidence, and per the task constraints I will not fall back on prior knowledge.

**Sources used:** `生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md (part 2 of 8)` (chunk vec=0.4823) — does not answer the question.

**[mode_B]**

The evidence provided contains no retrieved content at all ("no evidence retrieved"), so I cannot answer this question from the given material. The evidence does not contain any information about metformin, dosages, or diabetic cats. I am explicitly stating that the evidence is insufficient rather than falling back on prior knowledge, as the contract requires.

Sources used: none — no evidence was retrieved.

**[mode_C]**

The evidence is insufficient to answer this question. The only source provided — `clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md` (Section 3.2.1, "Clinician evaluation") — describes a human-evaluation framework for long-form LLM answers to consumer medical questions, covering axes such as agreement with scientific consensus, extent and likelihood of harm, comprehension, retrieval, reasoning, inappropriate/missing content, and bias. It contains no mention of metformin, feline medicine, or any drug dosage information. Therefore, no recommended daily dosage of metformin for diabetic cats can be derived from this evidence.

Source used: clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md (Part 2/8, Section 3.2.1).

**[rerank]**

The evidence is insufficient to answer this question. None of the retrieved passages mentions metformin, feline patients, or any drug dosage: the only diabetes-related content concerns hemoglobin A1C thresholds for human 250.XX diagnoses (2201.03675), a table of generic drug names and NDC codes that does not include metformin (2110.08918), and unrelated diabetes mentions such as diabetic retinopathy datasets (2412.15058) and type 2 diabetes in a prompt-injection example (2502.00306). The remaining chunks (1904.11280, 2310.10981, 2301.08436, 2212.13138, 2203.15752) contain no relevant information. Because the evidence does not contain the answer, I cannot provide the recommended daily metformin dosage for diabetic cats without falling back on prior knowledge, which is not permitted here.

Sources examined: [2201.03675], [1904.11280], [2502.00306], [2310.10981], [2412.15058], [2110.08918], [2301.08436], [2212.13138], [2203.15752] — none supports an answer.

**[rrf]**

The provided evidence does not contain an answer to this question. The three retrieved chunks cover unrelated topics: ICU length-of-stay and mortality prediction from clinical notes ([2110.08918]), a Hardy-Weinberg genetics exam question ([2212.13138]), and cost/token estimates for GPT-based question and answer generation ([2502.00306]). None of them mention metformin, diabetes, or feline medicine. Per the task contract, I am reporting the evidence as insufficient rather than answering from prior knowledge.

Sources consulted: [2110.08918], [2212.13138], [2502.00306].

**[vector]**

The evidence is insufficient to answer this question. None of the retrieved chunks mention metformin, feline/cat patients, or any drug dosage recommendation. The chunks that touch on diabetes concern human A1C modeling ([2201.03675]), a diabetic-retinopathy dataset listing ([2412.15058]), and a fragment about patients with high glucose ([1904.11280]); none discuss treatment dosing. The only drug table present ([2110.08918]) lists heparin, acetaminophen, lorazepam, and morphine sulfate with NDC codes — no metformin and no dosing information. Per the output contract, I am reporting this blind spot rather than answering from prior knowledge.

Sources examined (none contain the answer):
- [2212.13138] — biomedical model benchmark scores
- [2110.08918] — prescription drug name / NDC code table
- [2502.00306] — adversarial interrogation-attack example
- [2203.15752] — Mastodon instance statistics
- [2201.03675] — diabetes / A1C relationship modeling
- [2301.08436] — MERFISH dataset table
- [2310.10981] — fragment mentioning cholesterol/blood sugar/WBC count
- [2412.15058] — medical segmentation dataset table (incl. diabetic retinopathy)
- [1904.11280] — fragment on patients with high glucose/hypertension

</details>


## QK10 — `outofcorpus`

**Q:** How does the Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | — | — | 6.4 | 422 | 0.20143 | 0 | 是 | The evidence is insufficient to answer this question. None of the three retrieved sources mention a "Herbert-Moulton collider benchmark," detector dri |
| `mode_A` | — | — | 31.1 | 713 | 0.21007 | 0 | 是 | **Insufficient evidence.** The two retrieved chunks do not mention the "Herbert-Moulton collider benchmark," detector drift, or particle physics exper |
| `mode_B` | — | — | 8.4 | 592 | 0.20179500000000003 | 0 | 是 | The evidence is insufficient to answer this question: no evidence was retrieved (the evidence block is empty), so I have no document paths, file names |
| `mode_C` | — | — | 60.8 | 656 | 0.214565 | 0 | 是 | **The evidence is insufficient to answer this question.** None of the retrieved material mentions the Herbert-Moulton collider benchmark, particle phy |
| `rerank` | — | — | 23.6 | 994 | 0.21660500000000002 | 0 | 是 | The evidence is insufficient to answer the question: none of the retrieved chunks mention the "Herbert-Moulton collider benchmark," detector drift, or |
| `rrf` | — | — | 7.4 | 987 | 0.21575 | 0 | 是 | **The provided evidence is insufficient to answer this question.** None of the three retrieved chunks mentions the Herbert–Moulton collider benchmark, |
| `vector` | — | — | 7.8 | 841 | 0.21376499999999998 | 0 | 是 | **The evidence is insufficient to answer this question.** None of the retrieved chunks mentions the "Herbert-Moulton collider benchmark," detector dri |

<details><summary>逐字答案全文</summary>

**[bm25]**

The evidence is insufficient to answer this question.

None of the three retrieved sources mention a "Herbert-Moulton collider benchmark," detector drift, or any particle-physics collider experiment. The sources I retrieved are:

- **[2303.00445]** — a quantum-computing paper on contextual subspace methods, the reduced number operator $S_N$, and error mitigation for terms commuting with number/spin operators.
- **[1911.02792]** — a paper on coarse-grained molecular models built from bead mappings of atomistic systems.
- **[2005.14165]** — a GPT-3 paper excerpt containing a generated news article about a church denomination split.

Since no retrieved chunk addresses the Herbert-Moulton collider benchmark or detector drift quantification, I cannot answer the question from the evidence provided, and I will not fall back on prior knowledge.

**[mode_A]**

**Insufficient evidence.** The two retrieved chunks do not mention the "Herbert-Moulton collider benchmark," detector drift, or particle physics experiments at all. The first source is a RAG evaluation paper introducing the GlobalQA benchmark for corpus-level reasoning (counting, extremum, sorting, top-k), and the second is a materials-science paper on CH₃NH₃PbI₃/GeSe bilayer heterojunction solar cells covering electrical properties and carrier generation/recombination profiles. Neither contains any information about how detector drift is quantified, so I cannot answer the question from the provided evidence, and per the task contract I will not fall back on prior knowledge.

Sources reviewed (both irrelevant to the question):
- `e2e-demo-0923-022632/global-rag-benchmark.md` (vec=0.4097)
- `工程与能源/materials__1712.01369__ch3nh3pbi3-gese-bilayer-heterojunction-solar (part 2 of 2).md` (vec=0.4893)

**[mode_B]**

The evidence is insufficient to answer this question: no evidence was retrieved (the evidence block is empty), so I have no document paths, file names, or chunk IDs to cite.

I cannot describe how the "Herbert-Moulton collider benchmark" quantifies detector drift without falling back on prior knowledge, which this task prohibits.

No sources were used, because none were provided.

**[mode_C]**

**The evidence is insufficient to answer this question.** None of the retrieved material mentions the Herbert-Moulton collider benchmark, particle physics experiments, or detector drift. The evidence consists of: (1) "记忆约定 — soul-template" memory conventions (memory types, admission gates, lifecycle, approval rules); (2) "SOUL 人格定义 — soul-template" persona definition (identity dimensions, personality traits, knowledge boundaries, language style); and (3) the industrial diagnostic report "工业诊断报告：5 秒窗口温度序列异常趋势判定" (run ID `202609201042216_team_smoke`, source `data/auth_test.csv`), which addresses temperature-trend anomaly adjudication, not collider detector drift. Even the temperature work uses different terminology — `COMPETING_SET` diagnostic output with H1/H2/H3 hypotheses — and never discusses detector benchmarking or particle physics. Per the output contract, I am stating the evidence is insufficient and stopping rather than answering from prior knowledge.

Sources consulted (all retrieved evidence blocks): "记忆约定 — soul-template"; "SOUL 人格定义 — soul-template"; "工业诊断报告：5 秒窗口温度序列异常趋势判定" (`202609201042216_team_smoke`).

**[rerank]**

The evidence is insufficient to answer the question: none of the retrieved chunks mention the "Herbert-Moulton collider benchmark," detector drift, or particle-physics collider experiments at all. The only chunk containing "drift" is [1712.01369], which concerns semiconductor drift current density and resistivity, not detector drift. The remaining chunks cover unrelated topics: quantum circuit bootstrapping [2303.00445], qubit error correction [1311.2485], the Chemoton software [2109.05887], Trotter decompositions [2311.00487], stellar activity/radial velocity [1105.1887], and DFT+U calculations [2211.04977]. Per the instructions, I make no attempt to answer from prior knowledge.

Sources reviewed (none contain the answer): arXiv:2303.00445, arXiv:1712.01369, arXiv:1311.2485, arXiv:2109.05887, arXiv:2311.00487, arXiv:1105.1887, arXiv:2211.04977.

**[rrf]**

**The provided evidence is insufficient to answer this question.**

None of the three retrieved chunks mentions the Herbert–Moulton collider benchmark, particle colliders, or detector drift. The chunks cover unrelated topics: influenza vaccine epitope cross-affinity (chunk `q-bio-0408016`), supershear earthquake rupture particle motion (chunk `[2606.10843]`), and quantum error mitigation via contextual subspace operators (chunk `[2303.00445]`). Since the evidence contains no information on the benchmark or on any drift-quantification methodology, I cannot answer without falling back on prior knowledge, which the task forbids.

Sources examined (none relevant): `q-bio-0408016`, `[2606.10843]`, `[2303.00445]`.

**[vector]**

**The evidence is insufficient to answer this question.** None of the retrieved chunks mentions the "Herbert-Moulton collider benchmark," detector drift, or particle physics experiments: [q-bio-0408016] concerns antigenic drift in an antigen–antibody affinity model, [2602.10156] covers mode collapse and cosine distance for perturbation effects, [2606.10843] addresses rupture speed in seismology, [gr-qc-9805045] discusses black-hole event horizons, [2211.04977] is about DFT+U for transition-metal oxides, [2311.00487] concerns Trotter decompositions in quantum simulation, [1311.2485] is about qubit drift under bit-flip decoherence, and [1712.01369] covers drift current density in semiconductors. Since the retrieved evidence does not address the question, I cannot answer it, and per the task constraints I make no fallback to prior knowledge. Sources consulted (none usable): q-bio-0408016, 2602.10156, 2606.10843, gr-qc-9805045, 2211.04977, 2311.00487, 1311.2485, 1712.01369.

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ✅ | 0 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=15.1875 · manifest 未记总额 |
| 单元数 = 题数 × 方法数 | ✅ | rows=None vs 10×7=70 |
| provenance 完整 | ❌ | prompt_version=None seed=None |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*