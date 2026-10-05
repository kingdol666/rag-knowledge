# 对照实验报告 — `run-20260924T055401Z-0968033`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-24 06:33 UTC

## 方法清单

| method | 类型 | n |
|---|---|---:|
| `a2` | 项目（平台） | 10 |
| `bm25` | baseline | 10 |
| `rerank` | baseline | 10 |
| `vector` | baseline | 10 |

## 资源监控总表

| method | 时延 avg s | 时延 median s | tokens in | tokens out | 成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `a2` | 66.81 | 53.7 | 660888 | 11806 | 4.2005 | 0.42 | 5.1 | — | — |
| `bm25` | 10.47 | 8.9 | 8687 | 1494 | 0.2667 | 0.0267 | 0.0 | — | — |
| `rerank` | 15.78 | 16.4 | 3454 | 1379 | 0.2383 | 0.0238 | 0.0 | — | — |
| `vector` | 9.53 | 8.8 | 3892 | 1580 | 0.2454 | 0.0245 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 诚实性双向）

| method | 检索金标命中率 | 引用金标命中率 | 正确拒答(应拒答层) | 误拒(可答层) | error 数 |
|---|---:|---:|---:|---:|---:|
| `a2` | 1.0 | 1.0 | 2/2 (1.0) | 0/8 (0.0) | 0 |
| `bm25` | 1.0 | 1.0 | 2/2 (1.0) | 6/8 (0.75) | 0 |
| `rerank` | 1.0 | 1.0 | 2/2 (1.0) | 4/8 (0.5) | 0 |
| `vector` | 1.0 | 1.0 | 2/2 (1.0) | 4/8 (0.5) | 0 |

> **口径说明**：baseline 的「检索命中」基于其真实 ranked 列表（可直接观测）；agent 轨（a/a2/b/c）的 SSE 轨迹只含工具**入参**、不含检索结果文档 id，故其检索命中由 trace ∪ 答案推断（`retrieval_basis=trace+answer`）。**agent 轨请以「引用命中率」为可靠功能信号。**

## QK01 — `single`

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**gold:** 1706.03762, 1706.03762

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 142.0 | 2893 | 1.0514229999999998 | 10 | 否 | I have sufficient evidence from the retrieved chunks of the original Transformer paper. Here is the answer: ## Answer The Transformer computes attenti |
| `bm25` | ✓ | ✓ | 11.7 | 224 | 0.029025000000000002 | 0 | 是 | The evidence is insufficient to answer this question as posed. The retrieved chunks cover adjacent topics but not the core claim: chunk [1706.03762] e |
| `rerank` | ✓ | ✓ | 22.8 | 285 | 0.028702 | 0 | 是 | The evidence is insufficient to answer this question fully. The retrieved chunks describe the Transformer only in fragments: chunk [1706.03762] states |
| `vector` | ✓ | ✓ | 9.6 | 207 | 0.026777000000000002 | 0 | 是 | The evidence only partially answers this. One source describes the computation: the cross-attention head transforms decoder and encoder states into qu |

<details><summary>逐字答案全文</summary>

**[a2]**

I have sufficient evidence from the retrieved chunks of the original Transformer paper. Here is the answer:

## Answer

The Transformer computes attention as a "Scaled Dot-Product Attention": each output is a weighted sum of value vectors, where the input consists of queries and keys of dimension d_k and values of dimension d_v; the dot products of the query with all keys are divided by √d_k and passed through a softmax to obtain the weights on the values, giving Attention(Q, K, V) = softmax(QK^T/√d_k)V (chunk_index 24–25). The 1/√d_k scaling counteracts the fact that dot products grow large in magnitude for large d_k, pushing the softmax into regions with extremely small gradients (chunk_index 27). Instead of one attention function, Multi-Head Attention linearly projects queries, keys, and values h times with different learned projections to d_k, d_k, and d_v dimensions and runs attention in parallel over each (chunk_index 28); it is used in three ways — encoder self-attention, decoder (masked) self-attention preserving the auto-regressive property, and encoder-decoder attention letting every decoder position attend over all input positions (chunk_index 33, 35). Each encoder/decoder layer stacks these with position-wise feed-forward layers, residual connections, and layer normalization (document body).

The paper replaces recurrence and convolution for three reasons (chunk_index 47): **total computational complexity per layer**, **amount of parallelizable computation** (minimum sequential operations), and **path length between long-range dependencies**. Recurrent layers generate hidden state h_t from h_{t-1}, which is inherently sequential and precludes parallelization within training examples (Introduction); Table 1 shows self-attention has O(n²·d) complexity with O(1) sequential operations and O(1) maximum path length, versus O(n·d²)/O(n)/O(n) for recurrence and O(log_k(n)) path length for convolutions, and self-attention is faster whenever sequence length n < dimension d, the typical case (chunk_index 39–40, 49). In convolutional models (ByteNet, ConvS2S) the number of operations to relate two distant positions grows with distance (linearly or logarithmically), whereas the Transformer reduces this to a constant number of operations, counteracting averaging-based resolution loss via Multi-Head Attention (Background). Hence it became the first sequence transduction model based entirely on attention, replacing recurrent layers with multi-headed self-attention (Conclusion).

**Sources:**
- `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md` — KB 计算机与人工智能 (kb_id: b1199132-e4d4-4305-8c2e-82dc1753b0ba), chunks 22, 24, 25, 26–27, 28, 33, 35, 39–40, 47–50 + document body (Abstract, Intro, Background, §3.1)
- `Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k19.md` — KB Corpus-Chunks800 (kb_id: 0942f1a6-d81b-413b-a60b-b994680dcaac), chunk 8 (Conclusion)

**[bm25]**

The evidence is insufficient to answer this question as posed.

The retrieved chunks cover adjacent topics but not the core claim: chunk [1706.03762] explains multi-head attention's dimensions (h=8 heads, d_k=d_v=64) and lists the three applications of attention in the Transformer, but it does not explain what attention computation is (scaled dot-product attention) nor the motivation for replacing recurrence and convolution. Chunk [1810.04805] describes BERT's span-prediction QA fine-tuning, not Transformer attention. Chunk [2503.21676] describes an attention-patching experimental technique using a twin architecture, unrelated to the Transformer's design rationale.

Sources retrieved: [1706.03762], [1810.04805], [2503.21676]. None of them state why recurrence and convolution were replaced, nor the mechanics of computing attention; that content would most likely be in the earlier sections of [1706.03762] (Section 3.1 and Section 4), which were not provided. I cannot answer from prior knowledge.

**[rerank]**

The evidence is insufficient to answer this question fully. The retrieved chunks describe the Transformer only in fragments: chunk [1706.03762] states the Transformer is "the first sequence transduction model based entirely on attention," replacing recurrent layers in encoder-decoder architectures with multi-headed self-attention, but it does not explain *why* convolution was replaced. Chunk [2110.07844] gives a mechanism for cross-attention — transforming decoder and encoder states into query, key, and value vectors, computing normalized dot-product attention weights, and outputting a weighted sum of value vectors — and notes the mechanism "learns to focus on relevant parts of the input data" per chunk [2510.13343]. Chunk [1810.04805] only defines notation (L layers, hidden size H, attention heads). No chunk provides the reasoning for replacing recurrence or convolution.

Sources used:
- [1706.03762] — "Attention Is All You Need" (Conclusion section)
- [2110.07844] — cross-attention head mechanics (Eqs. 5–8)
- [2510.13343] — Multi-Agent Transformer Approach (attention mechanism strength)
- [1810.04805] — BERT notation for layers/heads
- [2503.21676], [1906.10015] — sampled but not relevant to mechanism or rationale

**[vector]**

The evidence only partially answers this. One source describes the computation: the cross-attention head transforms decoder and encoder states into query, key, and value vectors, computes attention weights as a normalized dot product between query and key vectors, and outputs a weighted sum of value vectors ([2110.07844]). Another states the Transformer replaces the recurrent layers commonly used in encoder-decoder architectures with multi-headed self-attention ([1706.03762]), and a third notes its strength lies in an attention mechanism that learns to focus on relevant parts of the input ([2510.13343]). However, none of the retrieved evidence explains **why** recurrence and convolution were replaced — no comparison, motivation, or rationale is given. The remaining chunks concern unrelated topics (BERT hyperparameters, plateau formation, attention-shift impairment, multi-agent transformers).

Sources used: [2110.07844], [1706.03762], [2510.13343].

**Insufficient evidence for the "why" portion of the question.**

</details>


## QK02 — `single`

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**gold:** 1602.01876, 1602.01876

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 46.6 | 840 | 0.169737 | 3 | 否 | According to the retrieved evidence, the Gene Ontology's terms are subdivided into three distinct ontologies representing different biological aspects |
| `bm25` | ✓ | ✓ | 6.3 | 121 | 0.025352 | 0 | 是 | The evidence is insufficient to answer this question. The provided chunks describe the Gene Ontology as a controlled vocabulary and explain annotation |
| `rerank` | ✓ | ✓ | 16.0 | 84 | 0.02127 | 0 | 否 | The evidence answers this directly. The Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: Molecula |
| `vector` | ✓ | ✓ | 6.5 | 87 | 0.021345 | 0 | 否 | The evidence answers this: the Gene Ontology is subdivided into three distinct ontologies representing different biological aspects — Molecular Functi |

<details><summary>逐字答案全文</summary>

**[a2]**

According to the retrieved evidence, the Gene Ontology's terms are subdivided into three distinct ontologies representing different biological aspects:

1. **Molecular Function (MF)**
2. **Biological Process (BP)**
3. **Cellular Component (CC)**

The source states these ontologies are non-redundant, share a common space of identifiers, and a well-specified syntax.

**Sources:**
- `Corpus-Chunks800/genomics__1602.01876__primer-on-the-gene-ontology__k00.md` (chunk_index 9, kb_id `0942f1a6-d81b-413b-a60b-b994680dcaac`, vector score 0.761)
- `生命科学与医学/genomics__1602.01876__primer-on-the-gene-ontology.md (part 1 of 2).md` (chunk_index 9, kb_id `b28f0a25-1e1d-40ad-96b8-61bd2b093a28`, vector score 0.759)

**[bm25]**

The evidence is insufficient to answer this question. The provided chunks describe the Gene Ontology as a controlled vocabulary and explain annotations, but only chunk [1602.01876] discusses GO directly, and it does not name the three ontologies that subdivide it. The other two chunks ([2301.08436], [2401.06823]) concern spatial transcriptomics and interpretable deep learning in single-cell omics, not GO structure.

Sources used: [1602.01876], [2301.08436], [2401.06823] — none contain the answer.

**[rerank]**

The evidence answers this directly.

The Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).

Source used: [1602.01876], section "2. What is the Gene Ontology?". The other two chunks ([2110.07787], [2508.18304]) do not address the question.

**[vector]**

The evidence answers this: the Gene Ontology is subdivided into three distinct ontologies representing different biological aspects — Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).

Source used: [1602.01876], section "2. What is the Gene Ontology?" (the other two chunks, [2110.07787] and [2508.18304], were not relevant to this question).

</details>


## QK03 — `single`

**Q:** What physical mechanism does the dynamic electrical model use to explain the hysteretic J-V characteristics of perovskite solar cells?

**gold:** 1606.00335, 1606.00335

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 90.2 | 1593 | 0.40827399999999997 | 4 | 否 | **Answer (from retrieved evidence only):** According to the retrieved paper (Nemnes et al., *Dynamic electrical behavior of halide perovskite based so |
| `bm25` | ✓ | ✓ | 8.0 | 221 | 0.028755000000000003 | 0 | 是 | The evidence is insufficient to answer this question as posed. The retrieved chunks mention a "standard dynamic electrical model" (1606.00335) that ad |
| `rerank` | ✓ | ✓ | 11.0 | 158 | 0.023005 | 0 | 是 | The evidence is insufficient to answer the question. The abstract from [1606.00335] states only that the model "investigate[s] the hysteretic effects  |
| `vector` | ✓ | ✓ | 6.2 | 97 | 0.021743 | 0 | 否 | The evidence describes a dynamic electrical model that reproduces hysteretic J–V features by making "a simple ansatz for the polarization relaxation," |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer (from retrieved evidence only):**

According to the retrieved paper (Nemnes et al., *Dynamic electrical behavior of halide perovskite based solar cells*, arXiv:1606.00335), the dynamic electrical model explains hysteresis through **slow relaxation of a non-linear polarization**, implemented as a bias-dependent capacitance/displacement current added to the standard equivalent circuit (photocurrent source + diode + series/shunt resistances). The polarization P_nl(t) relaxes toward a bias-dependent steady state with a single relaxation time τ: ∂P_nl/∂t = [P_nl,∞(U_c) − P_nl(t)]/τ, so the device is dynamically non-equilibrium during the voltage sweep, making forward and reverse scans differ. The initial conditions (initial polarization and current) are set by pre-conditioning — pre-poling/light soaking — so over-polarized samples reproduce the current overshoot seen in reverse scans, while under-polarization causes the opposite. Consistent with experiment, the hysteresis amplitude is maximal at intermediate bias scan rates and vanishes at very fast or very slow sweeps. The paper notes several microscopic origins are compatible with this phenomenological ansatz (Maxwell–Wagner–Sillars interfacial polarization, ion/charged-defect migration, ferroelectric domain alignment), but deliberately leaves the microscopic mechanism out of scope.

**Sources:**
- `工程与能源/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs (part 1 of 2).md` (kb_id `8fa4db59-adde-4d6d-9fdb-2c375400e631`) — Abstract, Introduction, Sections 2.1–2.2 (Eqs. 4–10), chunk_index 3, 8, 9
- `工程与能源/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs (part 2 of 2).md` (same kb_id) — Section 4 Conclusions, chunk_index 15, 17
- `Corpus-Chunks800/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs__k00.md`, `__k20.md` (kb_id `0942f1a6-d81b-413b-a60b-b994680dcaac`) — duplicate chunks confirming abstract and conclusions

**[bm25]**

The evidence is insufficient to answer this question as posed.

The retrieved chunks mention a "standard dynamic electrical model" (1606.00335) that adds a parallel capacitance `C` to the static equivalent circuit, but the excerpt is cut off mid-sentence at the point where that capacitance's role is being defined, so the mechanism is never stated. A later chunk from the same source only says hysteretic effects are "influenced by solar cell preconditioning and bias scan rate" and that the analysis focuses on "the variation of the polarization in time, assuming a certain relaxation time scale" — suggestive of polarization/relaxation, but the evidence does not explicitly name or explain the physical mechanism. The other two chunks (1712.01369, 2607.03098) concern bilayer perovskite/GeSe efficiency and energy-storage modeling respectively, and are irrelevant.

Sources used: [1606.00335] (Sections 2.1 and 3 excerpts); [1712.01369]; [2607.03098] (checked and found irrelevant).

**[rerank]**

The evidence is insufficient to answer the question. The abstract from [1606.00335] states only that the model "investigate[s] the hysteretic effects in the J-V characteristics" by "making a simple ansatz for the polarization relaxation," but it does not identify or explain the underlying physical mechanism (e.g., ion migration, ferroelectric polarization, trap states) responsible for the hysteresis. The second source, [1712.01369], concerns the J-V curve of a bilayer solar cell and reports parameters such as Jsc, Voc, and FF, with no discussion of the hysteresis mechanism. Neither retrieved chunk describes the physical mechanism the dynamic electrical model uses.

Sources used: [1606.00335] (Abstract), [1712.01369].

**[vector]**

The evidence describes a dynamic electrical model that reproduces hysteretic J–V features by making "a simple ansatz for the polarization relaxation," and it discusses pre-poling effects distinguishing initially over-polarized from under-polarized samples, including current overshoot ([1606.00335], Abstract).

Sources used: [1606.00335] Abstract; [1712.01369] (cited only for comparison J–V curves and cell parameters, not for the mechanism).

</details>


## QK04 — `single`

**Q:** Using only what kind of information, and reaching what accuracy, does the wav2vec 2.0 approach detect within-sentence prosodic boundaries on Czech broadcast news?

**gold:** 2209.15032, 2209.15032

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 41.8 | 772 | 0.35001099999999996 | 4 | 否 | **Answer:** The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no text annotation or word-bound |
| `bm25` | ✓ | ✓ | 6.9 | 147 | 0.027082000000000002 | 0 | 否 | The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information**, reaching **94% accuracy** (and an F1 measure |
| `rerank` | ✓ | ✓ | 19.4 | 72 | 0.020860999999999998 | 0 | 否 | Using only acoustic information, the wav2vec 2.0 approach detects within-sentence prosodic boundaries in Czech broadcast news with an accuracy of 94%  |
| `vector` | ✓ | ✓ | 13.0 | 138 | 0.022486 | 0 | 否 | The evidence states the wav2vec 2.0 framework is applied using only acoustic information to detect prosodic boundaries in speech signals, tested on Cz |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no text annotation or word-boundary knowledge, which were used only for evaluation, and no handcrafted feature selection), tested on recordings of **Czech broadcast news** labeled by phonetic experts. On within-sentence prosodic boundaries it achieves an **accuracy of 94% and an F1 measure of 83%**, or 95% and 89% on all prosodic boundaries, thereby outperforming the text-based predictor that used transcripts of the same data. This was achieved despite using a relatively small amount of labeled data, and the paper notes that combining the audio and text model outputs improves results further.

Sources used:
- `计算机与人工智能/speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u (part 1 of 2).md` (kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba`), chunk_index 1–3 (abstract) and the Introduction/Data sections
- Duplicate chunks in `Corpus-Chunks800/speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u__k00.md` (kb_id `0942f1a6-d81b-413b-a60b-b994680dcaac`, chunk_index 2), which matched via vector search

**[bm25]**

The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information**, reaching **94% accuracy** (and an F1 measure of 83%). The work is described in "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" by Kunešová and Rezáčková, tested on Czech broadcast news recordings labeled by phonetic experts, and it outperformed a text-based predictor using the same transcripts despite training on a relatively small amount of labeled data.

Source: [2209.15032] `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (part 1/2).

**[rerank]**

Using only acoustic information, the wav2vec 2.0 approach detects within-sentence prosodic boundaries in Czech broadcast news with an accuracy of 94% and an F1 measure of 83%, despite training on a relatively small amount of labeled data.

Source: [2209.15032] (chunk excerpt provided in the evidence)

**[vector]**

The evidence states the wav2vec 2.0 framework is applied using only acoustic information to detect prosodic boundaries in speech signals, tested on Czech broadcast news recordings labeled by phonetic experts. On within-sentence prosodic boundaries, the model achieves an accuracy of 94% and an F1 measure of 83%. The evidence also notes this was achieved despite using a relatively small amount of labeled data. The retrieved snippet is truncated mid-sentence ("or 95%"), so the reported accuracy of 94% and F1 of 83% are the only complete figures available.

Source used: [2209.15032] (abstract chunk, per the provided evidence).

</details>


## QK05 — `single`

**Q:** In the trap-cropping optimization framework, roughly what share of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant?

**gold:** 2508.05896, 2508.05896

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 37.8 | 853 | 0.40314400000000006 | 4 | 否 | **Answer:** Yes — the retrieved evidence answers this directly. The paper *"Optimal trap cropping investments to maximize..."* (arXiv 2508.05896) repo |
| `bm25` | ✓ | ✓ | 5.6 | 88 | 0.025192 | 0 | 否 | The evidence states that for trap plants 5 and 25 times more attractive than the cash plant, approximately 7–10% of the field should be allocated to t |
| `rerank` | ✓ | ✓ | 6.8 | 98 | 0.021198 | 0 | 是 | The evidence is insufficient to answer this question. The cited passage only states that with an attractiveness level of five (pests five times more l |
| `vector` | ✓ | ✓ | 8.3 | 174 | 0.023385999999999997 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved passage only states that when trap-plant attractiveness is **five** ("five times m |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** Yes — the retrieved evidence answers this directly. The paper *"Optimal trap cropping investments to maximize..."* (arXiv 2508.05896) reports that for trap plants 5 and 25 times more attractive than the cash plant, **approximately 7–10% of the field** should be allocated to trap plants; the same passage separately states that at five times attractiveness it is optimal to devote "roughly ten percent of the land to the trap crop." A related figure caption puts the broader picture as: for intermediately attractive trap plants (5–20× as attractive as the cash plant), **more than 10% of the landscape** should be sacrificed to trap plants, and the abstract-level summary states that between **5–20% of the field** must typically be allocated to trap crops for effective pest control without pesticides. The optimal area is **non-monotonic** in attractiveness: highly attractive traps (e.g. ~100×) need only 5–7% depending on the yield–pest density relationship, while traps only ~1–2.6× more attractive are ineffective and the whole field should stay in cash plants.

**Sources used:**
- `生命科学与医学/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz (part 2 of 3).md` — chunk_index 10, 11 (7–10% of field; ~10% at 5×), 15, 17, 18 (Figure 4: >10% for 5–20×), 41
- `生命科学与医学/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz (part 1 of 3).md` — chunk_index 20 (5–20% of field, non-monotonic relationship)
- `Corpus-Chunks800/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz__k05.md` — chunk_index 0 (5–20% of field)

**[bm25]**

The evidence states that for trap plants 5 and 25 times more attractive than the cash plant, approximately 7–10% of the field should be allocated to trap plants; more specifically, for a pest five times more likely to settle on a trap plant, it is optimal to devote roughly 10% of the land to the trap crop.

Source used: [2508.05896], Figure 3 and its caption.

**[rerank]**

The evidence is insufficient to answer this question. The cited passage only states that with an attractiveness level of five (pests five times more likely to settle on a trap plant), roughly 7–10% of the field should be allocated to trap plants — it gives no figures for the 5-to-25× attractiveness range. No source covering the 25× case appears in the evidence.

Sources used: [2508.05896] (partial — attractiveness level five only).

**[vector]**

The evidence is insufficient to answer this question.

The retrieved passage only states that when trap-plant attractiveness is **five** ("five times more likely to settle on a trap plant"), roughly **10%** of the land should be devoted to trap crops (~7–10% cited earlier in the snippet). It says nothing about the range of **5 to 25 times**, nor about attractiveness levels of 10, 15, 20, or 25, and the snippet trails off mid-sentence ("Interestingly, from figur…") before any such figure could be given.

Source used: chunk `[2508.05896]` (trap-cropping optimization discussion, mentions Figures 2, 3b, 3c).

I cannot extrapolate the 5–25× share from prior knowledge, so I will not attempt it.

</details>


## QK06 — `single`

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**gold:** 1503.07557, 1503.07557

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 62.2 | 1010 | 0.31330800000000003 | 5 | 否 | **Answer:** The dominant control is the thermodynamic contribution — the increase in atmospheric moisture (saturation specific humidity) with warming, |
| `bm25` | ✓ | ✓ | 6.8 | 173 | 0.026182999999999998 | 0 | 是 | The evidence is insufficient to answer this question. The O'Gorman review (climate-science__1503.07557__precipitation-extremes-under-climate-change.md |
| `rerank` | ✓ | ✓ | 10.1 | 215 | 0.024702 | 0 | 是 | The evidence is insufficient to name a single primary physical factor. The first source states that the response of precipitation extremes to climate  |
| `vector` | ✓ | ✓ | 9.3 | 233 | 0.026304 | 0 | 是 | The evidence is insufficient to answer the question definitively. The first source states that the response of precipitation extremes to climate chang |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** The dominant control is the thermodynamic contribution — the increase in atmospheric moisture (saturation specific humidity) with warming, which scales close to Clausius–Clapeyron at roughly 6–7 % K⁻¹. O'Gorman decomposes the extreme precipitation rate into a thermodynamic contribution from changes in S (saturation specific humidity along a moist adiabat), a dynamical contribution from changes in vertical velocity ω, and a microphysical contribution from precipitation efficiency ε; the thermodynamic term is described as "robust and well understood," while the microphysical and dynamical contributions remain less well constrained. Observed global sensitivity (~8 % K⁻¹ over land, 5–10 % K⁻¹ 90% CI) and extratropical model sensitivity (~6 % K⁻¹) are roughly consistent with this thermodynamic scaling. In RCE simulations near present-day tropical surface temperatures, precipitation extremes increase "at close to the thermodynamic rate," i.e. close to Clausius–Clapeyron scaling, with only small contributions from vertical-velocity and precipitation-efficiency changes.

Sources used:
- `自然科学与地球科学/climate-science__1503.07557__precipitation-extremes-under-climate-change.md (part 1 of 3).md` — chunk_index 1 (abstract), 2 (conclusions summary), 23 (Theory, Eq. 1 and thermodynamic/dynamical/microphysical decomposition), and the RCE discussion in §3; KB `1e6199ea-f380-44e2-94fc-d431f0f9bb6b`
- Mirror copy: `Corpus-Chunks800/climate-science__1503.07557__precipitation-extremes-under-climate-change__k00.md` — chunk_index 1

**[bm25]**

The evidence is insufficient to answer this question.

The O'Gorman review (climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md, part 1/3) states that the response is governed by "several physical contributions" — a thermodynamic contribution, plus microphysical and dynamical contributions — and that it focuses "on the physical factors that control the response." It does not name a single factor as the primary control. The other two chunks (2409.13934, 2409.09639) concern climate-change signal evaluation and precipitation dataset construction, not the controlling physics.

Sources used: climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md (part 1/3); 2409.13934; 2409.09639.

**[rerank]**

The evidence is insufficient to name a single primary physical factor.

The first source states that the response of precipitation extremes to climate change is considered "with a focus on the physical factors that control the response," but the retrieved excerpt is truncated mid-sentence ("the sensitivity of precipitation extremes to warming remains uncert…") and never identifies which factor primarily controls it. The second source mentions Clausius-Clapeyron scaling (~7%/°C) as a warming-driven signal for extreme precipitation, but presents it as an indication of signal strength, not as a statement of the controlling physical factor. The third source discusses vertical moisture flux convergence and vertical advection of moisture, but only as processes modulating MJO-induced precipitation anomalies, not as the primary control on the climate-change response. No source among those provided directly answers which physical factor is primary.

Sources used: [1503.07557] "Precipitation extremes under climate change" (Paul A. O'Gorman); [2409.13934]; [2007.10574] Section 3.2.

**[vector]**

The evidence is insufficient to answer the question definitively. The first source states that the response of precipitation extremes to climate change is considered "with a focus on the physical factors that control the response," noting that sensitivity to warming "remains uncert[ain]" — but the abstract chunk is truncated before naming any controlling physical factor. The third source mentions a Clausius-Clapeyron warming-driven signal of roughly 7%/°C for extreme precipitation, which is a thermodynamic scaling rather than an explicit statement of the single primary controlling factor. The second source discusses vertical moisture flux convergence and vertical advection of moisture as processes modulating precipitation anomalies, but in the context of MJO-induced extremes, not as the general controlling factor. No retrieved chunk explicitly identifies the primary physical factor controlling the precipitation-extreme response.

Sources used:
- [1503.07557] "Precipitation extremes under climate change" (O'Gorman)
- [2409.13934] (chunk on future climate contexts / extreme precipitation indices)
- [2007.10574] Section 3.2 "Dynamical Links between Precipitation Extremes and MJO"

</details>


## QK07 — `distractor`

**Q:** What is MameLoshnLM and what parameter scale does it have?

**gold:** 2608.05850, 2608.05850

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 32.0 | 720 | 0.27036899999999997 | 4 | 否 | **MAMELOSHNLM** is the first open-source large language model built specifically for Yiddish, named after the traditional Yiddish term "Mame-Loshn" (" |
| `bm25` | ✓ | ✓ | 9.9 | 164 | 0.027557 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention "MAMELOSHNLM" only in the context of statistical testing methodolog |
| `rerank` | ✓ | ✓ | 23.3 | 126 | 0.022136 | 0 | 否 | The evidence describes MAMELOSHNLM as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3. |
| `vector` | ✓ | ✓ | 17.8 | 164 | 0.023086 | 0 | 是 | The evidence identifies MAMELOSHNLM as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3 |

<details><summary>逐字答案全文</summary>

**[a2]**

**MAMELOSHNLM** is the first open-source large language model built specifically for Yiddish, named after the traditional Yiddish term "Mame-Loshn" ("mother tongue"). Its parameter scale is **8B**: it is described as "the first open-source 8B-parameter language model built specifically for Yiddish," produced by continued pretraining of **Llama-3.1-8B** on a Yiddish corpus with a causal language modeling objective. It was trained in bfloat16 using 8-bit AdamW, learning rate 2×10⁻⁵, cosine schedule with 2% warmup, weight decay 0.01, one epoch, max sequence length 1,024 tokens, per-device batch size 38, and 4 gradient accumulation steps. It reportedly outperforms strong baselines of similar scale on Yiddish benchmarks (e.g., against Llama 3.1 8B).

Sources used:
- `计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md (part 1 of 4).md` — chunk_index 2 (abstract), 53 (Section 5 MAMELOSHNLM), 54 (training details); kb_id b1199132-e4d4-4305-8c2e-82dc1753b0ba
- `Corpus-Chunks800/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu__k12.md` (chunks 6–7), `__k13.md` (chunks 1–2), `__k18.md` (chunk 5); kb_id 0942f1a6-d81b-413b-a60b-b994680dcaac

**[bm25]**

The evidence is insufficient to answer this question.

The retrieved chunks mention "MAMELOSHNLM" only in the context of statistical testing methodology (McNemar's exact test for pairwise model comparisons against Llama 3.1 8B on lemmatization), and one fragment references a "suppletive paradigm but not the regular one." None of the evidence describes what MameLoshnLM is (e.g., its architecture, training data, or purpose) or states its parameter scale or size.

Sources used: [2608.05850] (E.7 Statistical Testing section; suppletive-paradigm fragment). The other chunks ([2212.13138], [2005.14165]) are unrelated to MameLoshnLM and were not usable as evidence.

**[rerank]**

The evidence describes MAMELOSHNLM as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2, and named after the traditional Yiddish term for "mother tongue." It reportedly outperforms strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks. The evidence does not state the model's parameter count or the specific scale at which it was trained — it only says performance is compared against baselines "of similar scale."

Source used: chunk [2608.05850], section "## 5 MAMELOSHNLM".

**[vector]**

The evidence identifies MAMELOSHNLM as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2, and named after the traditional Yiddish term "mame-loshn" ("mother tongue"). It is reported to outperform strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks, and was produced by continued pretraining.

However, the evidence does not state the model's parameter scale — it only mentions comparison to "baselines of similar scale." The retrieved chunk ([2608.05850], Section 5, "MAMELOSHNLM") is therefore insufficient to answer the parameter-scale portion of the question.

Sources used: [2608.05850] Section 5 "MAMELOSHNLM".

</details>


## QK08 — `crosskb`

**Q:** Beyond which percentile of precipitation did the GAN clearly outperform the deterministic baseline in capturing the climate-change wetting signal?

**gold:** 2409.13934, 2409.13934

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 57.1 | 919 | 0.387622 | 4 | 否 | **Answer:** Beyond the **95th percentile** of precipitation. **Evidence (retrieved in this session):** The paper "On the Extrapolation of Generative A |
| `bm25` | ✓ | ✓ | 17.5 | 144 | 0.026777000000000002 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved evidence (paper 2409.13934) reports that the GAN captured ~97% and ~77% of the fut |
| `rerank` | ✓ | ✓ | 16.9 | 80 | 0.021199000000000003 | 0 | 否 | The evidence states the GAN substantially better captured the wetting signal **beyond the 95th percentile** of precipitation; up to that percentile th |
| `vector` | ✓ | ✓ | 7.4 | 82 | 0.021224000000000003 | 0 | 否 | Beyond the 95th percentile. The evidence states that up to the 95th percentile the two algorithms had relatively similar signals, and beyond it the GA |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** Beyond the **95th percentile** of precipitation.

**Evidence (retrieved in this session):** The paper "On the Extrapolation of Generative Adversarial Networks for downscaling precipitation extremes in warmer climates" (arXiv:2409.13934), Section 3.2, states: "The historically trained GAN and deterministic baseline exhibit a dry bias in their climate change signals and have relatively similar signals up to the 95th percentile of precipitation. Beyond the 95th percentile, the GAN substantially better captures the wetting signal, although both algorithms underestimate its magnitude compared to CCAM." The same section quantifies this at the 99.5th percentile: the GAN captures ~77% (historically trained) or ~97% (future-trained) of the warming-driven increase, versus only 63–65% for the deterministic baselines.

**Sources:**
- `自然科学与地球科学/climate-science__2409.13934__on-the-extrapolation-of-generative-adversari (part 2 of 3).md`, chunk_index 6 (two-stage search) — Section 3.2, verified by full document read (kb_id `1e6199ea-f380-44e2-94fc-d431f0f9bb6b`)
- Corroborated by `Corpus-Chunks800/climate-science__2409.13934__on-the-extrapolation-of-generative-adversari__k16.md`, chunk_index 7 (vector search, score 0.71)

**[bm25]**

The evidence is insufficient to answer this question.

The retrieved evidence (paper 2409.13934) reports that the GAN captured ~97% and ~77% of the future increase in the **99.5th percentile** of precipitation, versus 63–65% for the deterministic baselines — but it never states a threshold percentile "beyond which" the GAN outperforms those baselines. No such comparative percentile cutoff appears in the passage. The other two chunks (2007.10574, 2409.09639) do not address this comparison at all.

Sources consulted: [2409.13934], [2007.10574], [2409.09639].

**[rerank]**

The evidence states the GAN substantially better captured the wetting signal **beyond the 95th percentile** of precipitation; up to that percentile the algorithms had relatively similar climate-change signals (with the deterministic baselines showing dry bias).

Source used: [2409.13934], chunk containing "beyond the 95th percentile, the GAN substantially better captures the wetting signal."

**[vector]**

Beyond the 95th percentile. The evidence states that up to the 95th percentile the two algorithms had relatively similar signals, and beyond it the GAN substantially better captured the wetting signal, while both underestimated its magnitude relative to CCAM.

Source: [2409.13934] (chunk excerpt on GAN climate-change signal capture, Figure 1c, Supplementary Figure S9).

</details>


## QK09 — `unanswerable`

**Q:** What is the recommended daily dosage of metformin for diabetic cats?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 50.2 | 762 | 0.259437 | 5 | 是 | The retrieved evidence does not answer the question. **Answer:** I cannot answer this question from the knowledge base. The ingested corpus covers com |
| `bm25` | — | — | 13.8 | 91 | 0.024972 | 0 | 是 | The evidence is insufficient to answer this question. The three retrieved chunks concern ICU length-of-stay and mortality prediction from clinical not |
| `rerank` | — | — | 21.5 | 168 | 0.028557 | 0 | 是 | The evidence is insufficient to answer the question. The retrieved chunks mention diabetes only in unrelated contexts: A1C-based diabetes diagnosis mo |
| `vector` | — | — | 12.1 | 201 | 0.029382 | 0 | 是 | The evidence is insufficient to answer the question. The retrieved chunks are unrelated fragments from ML/bioinformatics papers: they mention diabetes |

<details><summary>逐字答案全文</summary>

**[a2]**

The retrieved evidence does not answer the question.

**Answer:** I cannot answer this question from the knowledge base. The ingested corpus covers computer science/AI, physical and earth sciences, life sciences (genomics, medical imaging, immunology, clinical-ML papers), engineering, economics, and an industrial KB — none of it is veterinary pharmacology or feline medicine. Searching for "metformin dosage diabetic cats," "metformin feline diabetes," and "metformin / diabetes" returned only false-positive matches on the words "diabetic" and "diabetes" in human medical-imaging (retinopathy datasets), clinical drug-representation, and A1C-modeling papers; no source in the retrieved set discusses metformin in cats at all.

Sources actually retrieved and checked (none answering):
- `生命科学与医学/medical-imaging__2412.15058__multiverseg-...md` (part 5 of 6), chunks 44–57 — "diabetic retinopathy" dataset table only.
- `生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md` (part 7), chunk 46 — psychiatry question, human.
- `Corpus-Chunks800/clinical-medicine__2110.08918__using-clinical-drug-representations...` k08 — drug/NDC table (heparin, acetaminophen, lorazepam), human prescriptions.
- `Corpus-Chunks800/clinical-medicine__2201.03675__continuous-time-probabilistic-models...` k16 — A1C/diabetes modeling, human.
- `生命科学与医学/immunology__2604.01385__strategies-for-tumor-elimination-and-control.md` (part 3), chunk 35 — cancer therapy, unrelated.

`kb_search` (metadata) for "metformin feline diabetes" returned 0 hits. Per the output contract, I am stopping here rather than answering from prior knowledge.

**[bm25]**

The evidence is insufficient to answer this question. The three retrieved chunks concern ICU length-of-stay and mortality prediction from clinical notes ([2110.08918]), global precipitation estimation with machine learning ([2409.09639]), and interactive image segmentation with MultiverSeg ([2412.15058]). None discusses metformin, diabetes, or feline medicine. No source can be named beyond these unrelated documents, and I will not answer from prior knowledge.

**[rerank]**

The evidence is insufficient to answer the question.

The retrieved chunks mention diabetes only in unrelated contexts: A1C-based diabetes diagnosis modeling (2201.03675), diabetic retinopathy segmentation datasets (2412.15058), an interrogation-attack prompt mentioning type 2 diabetes (2502.00306), and a fragment on high glucose levels (1904.11280). None concern metformin, feline medicine, or dosage recommendations.

Sources used: 2201.03675, 2502.00306, 1904.11280 (consulted and found irrelevant); remaining chunks (2412.15058, 2110.08918, 2310.10981, 2212.13138, 2301.08436, 2203.15752) contain no relevant content.

**[vector]**

The evidence is insufficient to answer the question.

The retrieved chunks are unrelated fragments from ML/bioinformatics papers: they mention diabetes only in passing (A1C thresholds, diabetic retinopathy segmentation, glucose levels) and contain no veterinary dosing information. There is no mention of metformin, cats, or dosage recommendations anywhere in the evidence.

Sources retrieved (none contain the answer):
- [2201.03675] §3.2 Diabetes (A1C/diabetes onset modeling)
- [2412.15058] EOphtha / diabetic retinopathy segmentation table
- [1904.11280] high glucose level fragment
- [2212.13138], [2110.08918], [2502.00306], [2203.15752], [2301.08436], [2310.10981] (unrelated tables/fragments)

No source in the evidence addresses metformin or feline diabetes treatment, so no dosage can be reported.

</details>


## QK10 — `outofcorpus`

**Q:** How does the Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 108.2 | 1444 | 0.587161 | 8 | 是 | **The retrieved evidence does not answer this question.** I searched the knowledge base in this session — `kb_list(lightweight=true)` returned ten col |
| `bm25` | — | — | 18.2 | 121 | 0.025842 | 0 | 是 | The evidence is insufficient to answer the question. The retrieved chunks discuss unrelated topics: contextual subspace error mitigation for a 3-qubit |
| `rerank` | — | — | 10.0 | 93 | 0.026707 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks come from unrelated papers (quantum error correction, Trotter decomposition |
| `vector` | — | — | 5.1 | 197 | 0.029627 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved chunks discuss a "Herbert-Moulton collider benchmark" or any detector-drif |

<details><summary>逐字答案全文</summary>

**[a2]**

**The retrieved evidence does not answer this question.**

I searched the knowledge base in this session — `kb_list(lightweight=true)` returned ten collections (计算机与人工智能, 自然科学与地球科学, 生命科学与医学, 工程与能源, 经济与社会, aw-industrial, Corpus-Chunks800, e2e-demo-0923-022632, soul-e2e-tester-024115, Novel-PridePrejudice), none of which is a particle-physics or collider-detector corpus — and ran four cross-KB semantic/lexical queries (`kb_search_vector` ×3 with balance_kbs=true, `kb_search_two_stage` ×1) covering "Herbert-Moulton collider benchmark detector drift", "Herbert Moulton", "detector drift quantification collider benchmark particle physics", and "ATLAS CMS LHC pixel tracker alignment drift monitoring". No retrieved chunk mentions "Herbert-Moulton", a collider benchmark, or any particle-physics detector-drift metric; the top-scoring hits were false friends on the word "drift" (robotics SLAM scale drift, `robotics__2509.14191__mcgs-slam...` chunk 30; semiconductor drift current, `materials__1712.01369...` chunk 20) and Chinese-language industrial sensor-diagnostic reports (`aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md` chunks 13 and 28, the latter a steadily recurring top hit for "drift"/"calibration"/"benchmark" — a sensor-noise hypothesis H2, not a detector-drift benchmark). Sources consulted and rejected: the ten KB catalog entries above plus the chunk paths named here. I therefore report no answer rather than fall back on prior knowledge, per the output contract.

**Sources used (all non-supporting):** `robotics__2509.14191__mcgs-slam-a-multi-camera-slam-framework-usin.md (part 2 of 2).md` (chunk 30); `materials__1712.01369__ch3nh3pbi3-gese-bilayer-heterojunction-solar (part 2 of 2).md` (chunk 20); `aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md` (chunks 13, 28); `kb_list` catalog of 10 KBs.

**[bm25]**

The evidence is insufficient to answer the question.

The retrieved chunks discuss unrelated topics: contextual subspace error mitigation for a 3-qubit HCl system ([2303.00445]), coarse-grained molecular modeling mappings ([1911.02792]), and a GPT-3-generated news article about a church denomination split ([2005.14165]). None mention the Herbert-Moulton collider benchmark, detector drift, or any particle physics benchmark methodology.

Sources used: [2303.00445], [1911.02792], [2005.14165] — none of which address the question.

**[rerank]**

The evidence is insufficient to answer this question. The retrieved chunks come from unrelated papers (quantum error correction, Trotter decomposition, protein-perturbation metrics, Chemoton software, antigenic drift, seismology, black-hole horizons) and contain no mention of the Herbert-Moulton collider benchmark, detector drift, or any particle-physics collider benchmark. No source listed above addresses the question, so no answer can be grounded in this evidence.

**[vector]**

The evidence is insufficient to answer this question.

None of the retrieved chunks discuss a "Herbert-Moulton collider benchmark" or any detector-drift metric for particle physics experiments. The closest thematic matches are unrelated: q-bio-0408016 concerns antigenic drift in an antibody-affinity model, 1311.2485 mentions qubit state drift under bit-flip decoherence, and 1712.01369 defines drift current density in a semiconductor — none of these are collider detector benchmarks.

Sources retrieved but not answering the question: q-bio-0408016, 2602.10156, 2606.10843, gr-qc-9805045, 2211.04977, 2311.00487, 1311.2485, 1712.01369.

I cannot answer from prior knowledge, so I am stopping here rather than speculating about a benchmark the evidence does not contain.

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ✅ | 0 个 error |
| 成本合计 = 各方法之和 | ❌ | sum(method)=4.9509 · manifest=5.279 |
| 单元数 = 题数 × 方法数 | ✅ | rows=40 vs 10×4=40 |
| provenance 完整 | ✅ | prompt_version=v3-neutral seed=0 |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*