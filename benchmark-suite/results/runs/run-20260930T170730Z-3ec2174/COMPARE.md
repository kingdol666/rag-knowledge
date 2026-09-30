# 对照实验报告 — `run-20260930T170730Z-3ec2174`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-30 17:17 UTC

## 方法清单

| method | 类型 | n |
|---|---|---:|
| `a2` | 项目（平台） | 10 |
| `bm25` | baseline | 10 |
| `rerank` | baseline | 10 |
| `rrf` | baseline | 10 |
| `vector` | baseline | 10 |

## 资源监控总表

| method | 时延 avg s | 时延 median s | tokens in | tokens out | 成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `a2` | 34.13 | 35.3 | 221979 | 8837 | 4.5032 | 0.4503 | 5.2 | — | — |
| `bm25` | 7.25 | 5.4 | 96746 | 2675 | 0.7513 | 0.0751 | 0.0 | — | — |
| `rerank` | 7.59 | 7.6 | 3246 | 1518 | 0.3005 | 0.03 | 0.0 | — | — |
| `rrf` | 4.48 | 4.5 | 773 | 1695 | 0.294 | 0.0294 | 0.0 | — | — |
| `vector` | 5.86 | 4.7 | 878 | 1566 | 0.289 | 0.0289 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 诚实性双向）

| method | 检索金标命中率 | 引用金标命中率 | 正确拒答(应拒答层) | 误拒(可答层) | error 数 |
|---|---:|---:|---:|---:|---:|
| `a2` | 1.0 | 1.0 | 0/2 (0.0) | 0/8 (0.0) | 0 |
| `bm25` | 1.0 | 1.0 | 2/2 (1.0) | 6/8 (0.75) | 0 |
| `rerank` | 1.0 | 1.0 | 2/2 (1.0) | 5/8 (0.625) | 0 |
| `rrf` | 1.0 | 1.0 | 2/2 (1.0) | 6/8 (0.75) | 0 |
| `vector` | 1.0 | 1.0 | 2/2 (1.0) | 5/8 (0.625) | 0 |

> **口径说明**：baseline 的「检索命中」基于其真实 ranked 列表（可直接观测）；agent 轨（a/a2/b/c）的 SSE 轨迹只含工具**入参**、不含检索结果文档 id，故其检索命中由 trace ∪ 答案推断（`retrieval_basis=trace+answer`）。**agent 轨请以「引用命中率」为可靠功能信号。**

## QK01 — `single`

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**gold:** 1706.03762, 1706.03762

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 53.5 | 1983 | 1.174803 | 8 | 否 | I now have full evidence from both the "how" (Sections 3.2–3.2.2) and "why" (Section 4, Table 1) sections of the source paper. **Answer** The Transfor |
| `bm25` | ✓ | ✓ | 3.9 | 160 | 0.0293286 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved passages mention multi-head attention configurations in the Transformer (h=8 heads |
| `rerank` | ✓ | ✓ | 8.2 | 270 | 0.0336676 | 0 | 是 | The evidence does not answer this question fully. - On **how attention is computed**, one chunk gives a partial answer: the cross-attention head trans |
| `rrf` | ✓ | ✓ | 4.4 | 199 | 0.029967999999999998 | 0 | 是 | The provided evidence does not contain the answer. The retrieved chunks describe only specific details of the Transformer's multi-head attention (e.g. |
| `vector` | ✓ | ✓ | 6.5 | 259 | 0.031324 | 0 | 是 | The evidence describes attention in pieces but does not directly answer the "why replace recurrence and convolution" part. One chunk states the Transf |

<details><summary>逐字答案全文</summary>

**[a2]**

I now have full evidence from both the "how" (Sections 3.2–3.2.2) and "why" (Section 4, Table 1) sections of the source paper.

**Answer**

The Transformer computes attention as a function mapping a query and a set of key–value pairs to an output, where query, keys, values and output are all vectors; the output is a weighted sum of the values, and each weight comes from a compatibility function of the query with the corresponding key (Section 3.2, chunk k22). Its specific form, Scaled Dot-Product Attention (Eq. 1), packs queries, keys and values into matrices Q, K, V and computes `Attention(Q,K,V) = softmax(QKᵀ/√d_k)V` — dot products of each query with all keys, divided by √d_k, softmaxed into weights on the values (chunks k24, k25). The scaling by 1/√d_k counteracts the fact that for large d_k the dot products grow large in magnitude and push softmax into regions with extremely small gradients (chunks k26, k27). Multi-Head Attention instead linearly projects Q, K, V h times with different learned projections to d_k/d_k/d_v dimensions, runs attention in parallel on each projected version, then concatenates and projects the results, letting the model jointly attend to information from different representation subspaces at different positions (chunks k28, k29). It replaces recurrence and convolution because, per Table 1 and Section 4, a self-attention layer connects all positions with O(1) sequentially executed operations whereas a recurrent layer needs O(n) sequential operations, giving self-attention a constant maximum path length O(1) versus O(n) for recurrent and O(log_k(n)) for convolutional layers (chunks k40, k48, k49). Since a shorter path between any input/output positions makes long-range dependencies easier to learn, this constant path length is the key motivation (chunk k48). Self-attention is also faster than recurrent layers when sequence length n is smaller than dimensionality d, the usual case, and avoids the O(n/k) or O(log_k(n)) layer stacks a single convolutional layer with kernel k<n requires to connect all position pairs (chunks k49, k50, k51). The paper's stated result is a model based solely on attention, dispensing with recurrence and convolutions entirely and trained significantly faster (abstract and concluding chunks).

**Sources used**
- `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md` — chunks 11, 22, 24, 25, 26, 27, 28, 29, 40, 46, 48, 49, 50, 51, 52 (KB `b1199132-e4d4-4305-8c2e-82dc1753b0ba`)
- `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 2 of 2).md` — Conclusion chunk (same KB)
- Corroborating copy: `Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k02.md`, `..._k19.md`, `..._k20.md`

(Note: I ran one `kb_index_document` call that was rejected with "experiment read-only" — it made no change; all evidence above came from read-only search and judge tools.)

**[bm25]**

The evidence is insufficient to answer this question.

The retrieved passages mention multi-head attention configurations in the Transformer (h=8 heads, d_k=d_v=64, computational cost comparable to single-head attention) and its three applications (encoder-decoder attention, encoder self-attention, decoder self-attention), but they do not explain the attention computation itself nor any rationale for replacing recurrence and convolution. The other retrieved chunks concern BERT question-answering fine-tuning and attention patching in a twin architecture, which are unrelated to the question.

Sources used: [1706.03762] (Transformer multi-head attention / applications section), [1810.04805] (BERT QA), [2503.21676] (attention patching) — none of which contain the required explanation.

**[rerank]**

The evidence does not answer this question fully.

- On **how attention is computed**, one chunk gives a partial answer: the cross-attention head transforms decoder/encoder states into query, key, and value vectors, computes attention weights as a normalized dot product between query and key, and produces output as a weighted sum of value vectors ([2110.07844]). A general statement also appears that attention "learns to focus on relevant parts of the input data" ([2510.13343]). No retrieved chunk describes multi-headed self-attention mechanics (scaled dot-product, head concatenation, positional encoding).
- On **why it replaces recurrence and convolution**, the only adjacent passage states that the original sequence transduction model is based entirely on attention, "replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention" ([1706.03762]) — but it gives no rationale (e.g., parallelism, path length, computational cost), and no chunk addresses convolution at all.

Sources used: [2110.07844], [2510.13343], [1706.03762]. The remaining retrieved chunks ([1810.04805], [2503.21676], [1906.10015]) do not bear on the question. Additional evidence is needed for a complete answer.

**[rrf]**

The provided evidence does not contain the answer. The retrieved chunks describe only specific details of the Transformer's multi-head attention (e.g., h=8 heads, d_k=d_v=d_model/h=64) and its three applications (encoder-decoder attention, encoder self-attention, decoder self-attention), but nowhere do they explain *how attention is computed* in terms of a general mechanism (e.g., scaled dot-product attention) or *why it replaces recurrence and convolution* (e.g., reduced path length, parallelization, computational efficiency). The other chunks concern BERT question answering and attention patching, which are unrelated to the question.

Sources used: [1706.03762] (Transformer, §3.2.2 and §3.2.3); [1810.04805] (BERT); [2503.21676] (attention patching). The evidence is insufficient to answer the question, stopping here without falling back on prior knowledge.

**[vector]**

The evidence describes attention in pieces but does not directly answer the "why replace recurrence and convolution" part. One chunk states the Transformer is "the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention" ([1706.03762], Conclusion). Another explains the original cross-attention head "transforms the j-th decoder state and i-th encoder state into query, key and value vectors... computes attention weights as a normalized dot product between query and key vectors... [and] the output of the head is a weighted sum of value vectors" ([2110.07844]). A third notes attention "learns to focus on relevant parts of the input data, thereby enabling powerful representational" power ([2510.13343]), and one mentions it abandons recurrence in favor of token-mixing via attention ([2503.21676]). However, no chunk explains why convolution specifically is replaced, and none gives the full rationale for replacing recurrence beyond the encoder-decoder description — so the evidence is insufficient to fully answer the "why" question.

Sources used: [1706.03762], [2110.07844], [2510.13343], [2503.21676].

</details>


## QK02 — `single`

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**gold:** 1602.01876, 1602.01876

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 34.4 | 825 | 0.47534300000000007 | 5 | 否 | **Answer:** The Gene Ontology is subdivided into three independent ontologies representing different biological aspects: **Molecular Function (MF)**,  |
| `bm25` | ✓ | ✓ | 6.1 | 181 | 0.0295778 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention the Gene Ontology (chunk [1602.01876]) as "a controlled vocabulary  |
| `rerank` | ✓ | ✓ | 4.1 | 66 | 0.0266534 | 0 | 否 | The evidence answers this. According to [1602.01876], the Gene Ontology is subdivided into three distinct ontologies representing different biological |
| `rrf` | ✓ | ✓ | 4.2 | 152 | 0.028934599999999998 | 0 | 是 | The evidence is insufficient to answer the question. The provided chunks mention that the Gene Ontology is "a controlled vocabulary of terms to repres |
| `vector` | ✓ | ✓ | 2.1 | 57 | 0.0264084 | 0 | 否 | The three independent ontologies subdividing the Gene Ontology are **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component  |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** The Gene Ontology is subdivided into three independent ontologies representing different biological aspects: **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**. The retrieved source states the GO terms "are subdivided in three distinct ontologies that represent different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)."

**Source used:**
- `生命科学与医学/genomics__1602.01876__primer-on-the-gene-ontology.md (part 1 of 2).md` — KB `b28f0a25-1e1d-40ad-96b8-61bd2b093a28`, §"2. What is the Gene Ontology?" (vector hit `...__k00.md`/`...__k01.md`, chunk_index 9/3; content confirmed by kb_doc_read and kb_laya_judge, segment-0001 score 0.8498).

**[bm25]**

The evidence is insufficient to answer this question.

The retrieved chunks mention the Gene Ontology (chunk [1602.01876]) as "a controlled vocabulary of terms to represent biology in a structured way," consisting of the Gene Ontology itself plus annotations — but the supplied text is truncated at "The term…" and never enumerates the three sub-ontologies (e.g., molecular function, biological process, cellular component). The other two chunks ([2301.08436], [2401.06823]) concern spatial transcriptomics gene panels and interpretable deep learning, not GO's structure.

Sources: [1602.01876] (partial, does not contain the answer); [2301.08436] (irrelevant); [2401.06823] (irrelevant). Answering with prior knowledge is prohibited by this task's contract, so I stop here.

**[rerank]**

The evidence answers this. According to [1602.01876], the Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).

Source: [1602.01876], "2. What is the Gene Ontology?"

**[rrf]**

The evidence is insufficient to answer the question. The provided chunks mention that the Gene Ontology is "a controlled vocabulary of terms to represent biology in a structured way" and discuss GO annotations generally, but none of them name or describe three independent ontologies that subdivide GO.

Sources used (searched, none contained the answer):
- [1602.01876] — GO primer excerpt (defines GO and annotations, lists five organizing questions, but does not enumerate subdivisions)
- [2508.18304] — monocyte subcluster/GSEA paper (mentions KEGG and GENCODE, not GO subdivisions)
- [2110.07787] — single-cell annotation methods review (mentions gene signatures, not GO subdivisions)

**[vector]**

The three independent ontologies subdividing the Gene Ontology are **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**.

Source: [1602.01876] §2 "What is the Gene Ontology?"

</details>


## QK03 — `single`

**Q:** What physical mechanism does the dynamic electrical model use to explain the hysteretic J-V characteristics of perovskite solar cells?

**gold:** 1606.00335, 1606.00335

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 18.4 | 755 | 0.259352 | 5 | 否 | The full text answers this directly. The mechanism is the slow relaxation of a non-linear (field- and light-induced) polarization, entering as a dynam |
| `bm25` | ✓ | ✓ | 3.6 | 198 | 0.030054599999999997 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks describe the *structure* of the standard dynamic electrical model (an equiv |
| `rerank` | ✓ | ✓ | 6.7 | 158 | 0.028857999999999998 | 0 | 是 | The evidence is insufficient to answer this question. Source [1606.00335] states only that a dynamic electrical model "is introduced to investigate th |
| `rrf` | ✓ | ✓ | 6.9 | 272 | 0.031852 | 0 | 是 | **Answer (from evidence):** The evidence is insufficient to answer this question. The retrieved chunks ([1606.00335], [1712.01369], [2607.03098]) do n |
| `vector` | ✓ | ✓ | 5.2 | 182 | 0.029457999999999998 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention that a dynamic electrical model exists and that it reproduces hyste |

<details><summary>逐字答案全文</summary>

**[a2]**

The full text answers this directly. The mechanism is the slow relaxation of a non-linear (field- and light-induced) polarization, entering as a dynamic capacitor/displacement current in the equivalent circuit.

Sources used:
- `工程与能源/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs (part 1 of 2).md` (Ch. 2.1–2.2, Abstract, Introduction) — kb_id `8fa4db59-adde-4d6d-9fdb-2c375400e631`
- `Corpus-Chunks800/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs__k22.md` (vector hit, kb_id `0942f1a6-d81b-413b-a60b-b994680dcaac`)

**[bm25]**

The evidence is insufficient to answer this question.

The retrieved chunks describe the *structure* of the standard dynamic electrical model (an equivalent circuit with a photocurrent source, diode, shunt resistance, series resistance, and an added parallel capacitance) and note that Section 3 presents simulated J-V curves "describing the hysteretic effects, which are influenced by solar cell preconditioning and bias scan rate," with analysis "focused on the variation of the polarization in time, assuming a certain relaxation time scale." However, no chunk states the physical mechanism itself — the text stops at "[1606.00335] ... a parallel capacitance C is present, which is gen-" before reaching the explanatory content. The other chunks concern bilayer perovskite/GeSe cells and energy-storage models, unrelated to the hysteresis mechanism.

Sources used: chunk [1606.00335]; chunk [1712.01369] (not relevant); chunk [2607.03098] (not relevant).

**[rerank]**

The evidence is insufficient to answer this question.

Source [1606.00335] states only that a dynamic electrical model "is introduced to investigate the hysteretic effects in the J-V characteristics" and that "by making a simple ansatz for the polarization relaxation, our model is able to reproduce... detailed features of measured J-V characteristics." It mentions polarization relaxation and pre-poling/over- vs under-polarized samples, but the retrieved snippet does not state a complete named mechanism (e.g., ion migration) explaining the hysteresis. Source [1712.01369] only discusses a bilayer solar cell's J-V curve and device parameters, not a hysteresis mechanism.

Sources used:
- [1606.00335] (abstract snippet)
- [1712.01369]

**[rrf]**

**Answer (from evidence):**

The evidence is insufficient to answer this question. The retrieved chunks ([1606.00335], [1712.01369], [2607.03098]) do not contain the mechanism requested.

[1606.00335] comes closest: it describes the standard dynamic electrical model as an equivalent electric circuit (photocurrent source, diode with ideality factor n, shunt resistance R_sh, series resistance R_s, plus a parallel capacitance C) and states that J-V hysteresis is analyzed via **the variation of the polarization in time, assuming a certain relaxation time scale**, with the influence of different relaxation time scales investigated. However, the passage is cut off mid-sentence ("which is gen…") and never states the underlying physical mechanism (e.g., ion migration or ferroelectric polarization) driving that polarization/relaxation. [1712.01369] discusses J_sc/V_oc/FF/efficiency of a perovskite/GeSe bilayer cell but not hysteresis mechanisms. [2607.03098] concerns energy storage model simplification, unrelated to perovskite hysteresis.

**Sources used:** [1606.00335] §2.1 "The standard dynamic electrical model"; [1712.01369]; [2607.03098].

No further inference will be drawn beyond the supplied text.

**[vector]**

The evidence is insufficient to answer this question.

The retrieved chunks mention that a dynamic electrical model exists and that it reproduces hysteretic J-V features, but they do not state the physical mechanism the model uses. The abstract chunk **[1606.00335]** says only that "By making a simple ansatz for the polarization relaxation, our model is able to reproduce qualitatively and quantitatively detailed features of measured J-V characteristics" — it names a polarization-relaxation ansatz but does not explain the underlying physical mechanism, and the sentence is truncated before any further detail. The second chunk **[1712.01369]** is about a bilayer solar cell J-V simulation and is not relevant to the mechanism question.

**Sources used:** [1606.00335] (abstract chunk), [1712.01369]. Neither contains a statement of the physical mechanism; no answer can be given from this evidence.

</details>


## QK04 — `single`

**Q:** Using only what kind of information, and reaching what accuracy, does the wav2vec 2.0 approach detect within-sentence prosodic boundaries on Czech broadcast news?

**gold:** 2209.15032, 2209.15032

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 51.5 | 830 | 0.6793100000000001 | 10 | 否 | The wav2vec 2.0 approach detects within-sentence prosodic boundaries on Czech broadcast news **using only acoustic information** — learned representat |
| `bm25` | ✓ | ✓ | 10.1 | 498 | 0.038122 | 0 | 否 | The wav2vec 2.0 approach detects prosodic boundaries using **only acoustic information** from the speech signal. On recordings of Czech broadcast news |
| `rerank` | ✓ | ✓ | 13.1 | 54 | 0.0262952 | 0 | 否 | The wav2vec 2.0 approach uses only acoustic information to detect within-sentence prosodic boundaries on Czech broadcast news. It achieves an accuracy |
| `rrf` | ✓ | ✓ | 2.5 | 130 | 0.0285194 | 0 | 否 | The evidence says the wav2vec 2.0 model was applied using **only acoustic information** (no transcripts). On **within-sentence prosodic boundaries** i |
| `vector` | ✓ | ✓ | 4.0 | 121 | 0.0279176 | 0 | 否 | Based solely on the provided evidence: the wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no te |

<details><summary>逐字答案全文</summary>

**[a2]**

The wav2vec 2.0 approach detects within-sentence prosodic boundaries on Czech broadcast news **using only acoustic information** — learned representations from raw audio, with no text annotation, no knowledge of word boundaries, and no handcrafted feature selection. It reaches **94% accuracy and 83% F1 on within-sentence prosodic boundaries** (and 95% accuracy / 89% F1 on all prosodic boundaries), outperforming a text-based T5 baseline. The experiments used 42 minutes (486 sentences) of Czech Radio broadcast news, annotated by phonetic experts, with the pre-trained Czech wav2vec 2.0 base model "ClTRUS."

Sources used:
- `计算机与人工智能/speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u (part 1 of 2).md` — KB `计算机与人工智能` (kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba`), chunk_index 2 (abstract) and chunk 63 (conclusion); read-verified full text.
- Duplicate copy: `Corpus-Chunks800/speech__2209.15032__...__k00.md` — KB `Corpus-Chunks800` (kb_id `0942f1a6-d81b-413b-a60b-b994680dcaac`), vector-verified only.

Paper: "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" (Kunešová & Rezáčková, arXiv 2209.15032).

**[bm25]**

The wav2vec 2.0 approach detects prosodic boundaries using **only acoustic information** from the speech signal. On recordings of Czech broadcast news labeled by phonetic experts, it reaches an **accuracy of 94%** (with an F1 measure of 83%) on within-sentence prosodic boundaries, despite using a relatively small amount of labeled data. For reference, on all prosodic boundaries it achieves 95% accuracy and 89% F1, outperforming an existing text-based predictor that uses transcripts of the same data.

Source: `[2209.15032] speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (part 1/2), Abstract of "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0".

**[rerank]**

The wav2vec 2.0 approach uses only acoustic information to detect within-sentence prosodic boundaries on Czech broadcast news.

It achieves an accuracy of 94%.

Source: [2209.15032] (chunk excerpt quoted in the evidence).

**[rrf]**

The evidence says the wav2vec 2.0 model was applied using **only acoustic information** (no transcripts). On **within-sentence prosodic boundaries** in Czech broadcast news, it reached **94% accuracy and 83% F1**. On **all prosodic boundaries** (not within-sentence only), it reached 95% accuracy and 89% F1. The approach outperformed the text-based predictor.

Source used: `[2209.15032] # speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (chunk 1/2).

**[vector]**

Based solely on the provided evidence: the wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no text/transcripts), and achieves an **accuracy of 94%** (with an F1 measure of 83%).

Source used: [2209.15032].

Note: the evidence is truncated mid-sentence ("or 95%…"), so the full second figure is not available; the clearly stated results are 94% accuracy and 83% F1 for within-sentence prosodic boundaries on Czech broadcast news recordings.

</details>


## QK05 — `single`

**Q:** In the trap-cropping optimization framework, roughly what share of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant?

**gold:** 2508.05896, 2508.05896

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 53.7 | 535 | 0.7322229999999998 | 10 | 否 | The answer is found in the paper "Optimal trap cropping investments to maximize agricultural yield" (arXiv 2508.05896). For trap plants that are 5 to  |
| `bm25` | ✓ | ✓ | 3.8 | 154 | 0.029024599999999998 | 0 | 否 | The evidence answers this. According to [2508.05896], when trap plants are 5 to 25 times more attractive than the cash plant, roughly **7–10% of the f |
| `rerank` | ✓ | ✓ | 5.6 | 137 | 0.0281 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved excerpt only states that at an attractiveness level of five (five times more attra |
| `rrf` | ✓ | ✓ | 5.4 | 108 | 0.0275816 | 0 | 否 | The evidence answers this: for trap plants 5 and 25 times more attractive than the cash plant, approximately 7–10% of the field should be allocated to |
| `vector` | ✓ | ✓ | 5.0 | 191 | 0.029685200000000002 | 0 | 是 | The evidence is insufficient to answer this question as asked. The retrieved passage states that at attractiveness level five (a pest is five times mo |

<details><summary>逐字答案全文</summary>

**[a2]**

The answer is found in the paper "Optimal trap cropping investments to maximize agricultural yield" (arXiv 2508.05896).

For trap plants that are 5 to 25 times more attractive than the cash plant, roughly **7–10% of the field should be allocated to trap plants** (the paper's illustrative baseline gives ~7.1–8.5% trap area, i.e., 91.5–92.9% cash plants, for the 5–25× range). A companion result states that for the intermediate 5–20× attractiveness range more than 10% of the landscape should be sacrificed to trap plants.

Source: `生命科学与医学/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz (part 2 of 3).md` (mirrored in `Corpus-Chunks800/...__k17.md` and `__k05.md`).

**[bm25]**

The evidence answers this.

According to [2508.05896], when trap plants are 5 to 25 times more attractive than the cash plant, roughly **7–10% of the field should be allocated to trap plants**. Figure 3 states that for trap plants "5 and 25 times more attractive, approximately 7–10% of the field should be allocated to trap plants," and the text adds that at five times attractiveness "it is optimal to devote roughly ten percent of the land to the trap crop (Figure 3b)." By contrast, at only twice the attractiveness, trap cropping is ineffective and all cash plants should be planted.

Sources used:
- [2508.05896] (Figure 3 caption and accompanying text)

**[rerank]**

The evidence is insufficient to answer this question.

The retrieved excerpt only states that at an attractiveness level of five (five times more attractive), it is optimal to devote "roughly ten percent" of the land to the trap crop, and separately that at a lower attractiveness level, approximately 7–10% of the field should be allocated to trap plants. The excerpt does not cover the 5-to-25× attractiveness range, nor does it give a share for higher attractiveness values up to 25.

Source used: [2508.05896] (excerpt, chunk beginning "ctive, approximately 7–10% of the field should be allocated to trap plants").

**[rrf]**

The evidence answers this: for trap plants 5 and 25 times more attractive than the cash plant, approximately 7–10% of the field should be allocated to trap plants; for the five-times case specifically, it is optimal to devote roughly ten percent of the land to the trap crop. If a trap plant is only twice as attractive, trap cropping is ineffective and the grower should plant only cash plants.

Source used: [2508.05896] (Figure 3 and its caption, plus the following paragraph).

**[vector]**

The evidence is insufficient to answer this question as asked.

The retrieved passage states that at attractiveness level five (a pest is five times more likely to settle on a trap plant), it is optimal to devote roughly **ten percent** of the land to the trap crop — but it does not cover the 5-to-25-times range. The only other figure given is that approximately **7–10%** of the field should be allocated to trap plants under some (unspecified in the excerpt) attractiveness condition. No value for attractiveness levels above five, up to twenty-five, appears in the evidence.

Source used: [2508.05896], chunk containing "ctive, approximately 7–10% of the field should be allocated to trap plants." and the Figure 3b discussion.

Because the specific 5–25× range is not addressed, I cannot give a grounded answer without falling back on prior knowledge, which the task prohibits.

</details>


## QK06 — `single`

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**gold:** 1503.07557, 1503.07557

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 36.2 | 1284 | 0.5498390000000001 | 5 | 否 | The judge's reference fetch failed (web proxy), but `kb_doc_read` succeeded and gave direct evidence. I have what I need. **Answer:** The evidence ide |
| `bm25` | ✓ | ✓ | 5.6 | 243 | 0.031173599999999996 | 0 | 是 | The evidence is insufficient to answer the question. The retrieved evidence includes the abstract of O'Gorman's "Precipitation extremes under climate  |
| `rerank` | ✓ | ✓ | 9.5 | 305 | 0.0325038 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks establish only the general framework — that precipitation extremes intensif |
| `rrf` | ✓ | ✓ | 5.5 | 187 | 0.0299752 | 0 | 是 | The evidence is insufficient to answer the question as posed, because the retrieved chunks do not identify a single primary physical factor. - The O'G |
| `vector` | ✓ | ✓ | 4.4 | 202 | 0.0298812 | 0 | 是 | The evidence is insufficient to answer which physical factor *primarily* controls the response of precipitation extremes to climate change. - [1503.07 |

<details><summary>逐字答案全文</summary>

**[a2]**

The judge's reference fetch failed (web proxy), but `kb_doc_read` succeeded and gave direct evidence. I have what I need.

**Answer:** The evidence identifies the **thermodynamic contribution — specifically the increase in atmospheric water-vapor content via the saturation specific humidity S (the Clausius–Clapeyron / "saturation vapor pressure of water" scaling)** — as the primary, robust physical factor controlling the response of precipitation extremes to warming. O'Gorman's review states that if dynamical and precipitation-efficiency changes are negligible, precipitation extremes intensify with warming because of increases in the saturation vapor pressure of water (~7%/K), and that among the governing contributions "the thermodynamic contribution is robust and well understood, but theoretical understanding of the microphysical and dynamical contributions is still being developed." The precipitation-rate decomposition P ≈ −ε{ωS(T,p)} attributes the thermodynamic part to S(T,p) — the moist-adiabatic derivative of saturation specific humidity — which varies with the moist adiabatic lapse rate. Observed sensitivities (~8% K⁻¹ global; ~9% K⁻¹ tropics vs ~4% K⁻¹ extratropics) are described as roughly consistent with this theory, though dynamical (ω) and microphysical (ε) contributions remain major uncertainties, especially where convection matters.

Sources used:
- `自然科学与地球科学/climate-science__1503.07557__precipitation-extremes-under-climate-change.md (part 1 of 3).md` (KB `1e6199ea-f380-44e2-94fc-d431f0f9bb6b`), Abstract + §1 Introduction + §3 Theory (chunks 1, 8, 9) — read via `kb_doc_read`.
- Vector/keyword hits from `kb_search_vector` and `kb_search_two_stage` on the same document and its chunk copies (`Corpus-Chunks800/...__k01.md`, `__k02.md`, `__k34.md`) — note: `kb_laya_judge` could not verify these (its server-side fetch returned "unavailable, fail-closed" because the web proxy at localhost:6789 did not respond), so verification rests on the directly read document above.

**[bm25]**

The evidence is insufficient to answer the question. The retrieved evidence includes the abstract of O'Gorman's "Precipitation extremes under climate change," which states that the response is governed by several contributions — thermodynamic (robust and well understood), microphysical, and dynamical (theoretical understanding still being developed) — and notes that no single factor is identified as *the* primary control; rather, the abstract frames the response as multi-factorial and emphasizes "the physical factors that control the response." The other two retrieved chunks (from 2409.13934 and 2409.09639) concern emulator evaluation and machine-learning precipitation dataset construction, respectively, and do not address which physical factor primarily controls precipitation-extreme response. Because the evidence names multiple competing contributions without ranking one as primary, and the relevant abstract text is truncated before further detail, I cannot identify a single primary physical factor from this evidence alone.

Sources used:
- `climate-science__1503.07557__precipitation-extremes-under-climate-change.md` (chunk 1/3, abstract)
- 2409.13934 (partial excerpt)
- 2409.09639 (partial excerpt)

**[rerank]**

The evidence is insufficient to answer this question.

The retrieved chunks establish only the general framework — that precipitation extremes intensify with warming and that the response is often discussed in terms of the Clausius-Clapeyron relation (~7%/°C) — but none of them identifies the primary controlling physical factor. The O'Gorman abstract (1503.07557) explicitly states it focuses on "the physical factors that control the response" yet truncates before naming them, ending at "the sensitivity of precipitation extremes to warming remains uncert[ain]". Chunk 2409.13934 discusses the learning challenge of extreme-precipitation signals and cites Clausius-Clapeyron, but does not isolate a single controlling factor. Chunk 2007.10574 addresses MJO-related dynamical links (vertical moisture flux convergence and vertical moisture advection) as modulating processes for MJO-induced extremes specifically, not as the primary control of the general precipitation-extremes response. Because the decisive statement appears to lie in truncated text I did not receive, I cannot name the factor without falling back on prior knowledge.

Sources consulted:
- [1503.07557] "Precipitation extremes under climate change" (O'Gorman) — abstract, truncated
- [2409.13934] — chunk on extreme precipitation (99.5th percentile) and Clausius-Clapeyron
- [2007.10574] §3.2 — Dynamical Links between Precipitation Extremes and MJO

**[rrf]**

The evidence is insufficient to answer the question as posed, because the retrieved chunks do not identify a single primary physical factor.

- The O'Gorman abstract states that "several physical contributions govern the response of precipitation extremes," that the thermodynamic contribution "is robust and well understood," and that "theoretical understanding of the microphysical and dynamical contributions is still being developed." It does not name any one of these as the dominant control.
- The other two chunks are about emulator evaluation of climate change signals (2409.13934) and MJO modulation of extreme precipitation in Indonesia (2007.10574); neither addresses which physical factor primarily controls the response.

Sources used: `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (chunk 1/3); `[2409.13934]`; `[2007.10574]`.

**[vector]**

The evidence is insufficient to answer which physical factor *primarily* controls the response of precipitation extremes to climate change.

- [1503.07557] O'Gorman, "Precipitation extremes under climate change" states the response is considered "with a focus on the physical factors that control the response" and that the sensitivity "remains uncert[ain]" — but the retrieved chunk is truncated before any factor is named.
- [2007.10574] examines "vertical moisture flux convergence" and "vertical advection of moisture" for MJO-induced extremes, but covers only the MJO dynamical link, not the primary controlling factor.
- [2409.13934] cites the Clausius-Clapeyron scaling (~7%/°C) for extreme precipitation, but does not identify a primary physical control.

Sources: 1503.07557 (O'Gorman, abstract); 2007.10574 (§3.2); 2409.13934.

</details>


## QK07 — `distractor`

**Q:** What is MameLoshnLM and what parameter scale does it have?

**gold:** 2608.05850, 2608.05850

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 40.7 | 948 | 0.25828 | 4 | 否 | **Answer:** MameLoshnLM is an open-source language model for Yiddish, introduced with two supporting resources — the Oytser pretraining corpus (contem |
| `bm25` | ✓ | ✓ | 4.3 | 193 | 0.030222 | 0 | 是 | The evidence is insufficient to answer this question. What the retrieved evidence contains: - From `[2608.05850]`, section E.7 "Statistical Testing" m |
| `rerank` | ✓ | ✓ | 7.9 | 159 | 0.0287526 | 0 | 是 | The evidence identifies **MAMELOSHNLM** as "the first open-source large language model for Yiddish," trained on the Yiddish corpus described in subsec |
| `rrf` | ✓ | ✓ | 5.4 | 223 | 0.030684 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention "MAMELOSHNLM" only in the context of a statistical testing section  |
| `vector` | ✓ | ✓ | 19.1 | 119 | 0.027810200000000004 | 0 | 是 | The evidence is insufficient to fully answer the question. It does identify MameLoshnLM as "the first open-source large language model for Yiddish," t |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** MameLoshnLM is an open-source language model for Yiddish, introduced with two supporting resources — the Oytser pretraining corpus (contemporary web-native Yiddish plus literary-tradition material) and the Kashes evaluation benchmark — created to address the scarcity and low quality of publicly available Yiddish pretraining text (the paper documents that less than half of mC4's putative Yiddish content is genuine Yiddish). Its parameter scale is **8B**: it was produced by continued pretraining of Llama-3.1-8B on a Yiddish corpus using a causal language modeling objective. Training details confirm this: bfloat16 precision, 8-bit AdamW, learning rate 2×10⁻⁵, cosine schedule with 2% warmup, weight decay 0.01, one epoch, max sequence length 1,024 tokens, per-device batch size 38, and 4 gradient accumulation steps. Across the Kashes benchmark it outperforms open models of similar scale, with strong gains on Yiddish-centered tasks such as translation, linguistic analysis, and named entity recognition. The evidence is consistent across all retrieved sources, and the content-verification judge confirmed the primary document (segments scoring 0.90 and 0.51).

**Sources used:**
- `计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md (part 1 of 4).md` — kb `b1199132-e4d4-4305-8c2e-82dc1753b0ba` (primary; judge survivors segment-0001, segment-0009)
- `Corpus-Chunks800/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu__k12.md` — kb `0942f1a6-d81b-413b-a60b-b994680dcaac` (training paragraph)
- `计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md (part 4 of 4).md` — kb `b1199132-e4d4-4305-8c2e-82dc1753b0ba` (Kashes comparison table)

**[bm25]**

The evidence is insufficient to answer this question. 

What the retrieved evidence contains:
- From `[2608.05850]`, section E.7 "Statistical Testing" mentions **MAMELOSHNLM** only as a model compared against Llama 3.1 8B on lemmatization, using McNemar's exact test — no description of what it is or its parameter scale.
- The other two chunks (`[2212.13138]` and `[2005.14165]`) do not mention MameLoshnLM at all.

None of the evidence states what MameLoshnLM is or its parameter scale, so I cannot answer without falling back on prior knowledge, which is disallowed here.

**Sources used:** `[2608.05850]` (sec. E.7); `[2212.13138]`; `[2005.14165]`.

**[rerank]**

The evidence identifies **MAMELOSHNLM** as "the first open-source large language model for Yiddish," trained on the Yiddish corpus described in subsection 3.2, and named after the traditional Yiddish term "Mame-Loshn" ("mother tongue"). It is reported to outperform strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks. It was produced by "continued pretrain..." (the sentence is truncated). However, the evidence does **not** state the parameter scale of the model — no parameter count is given in the provided text, so the evidence is insufficient to answer that part of the question.

Source used: [2608.05850] §5 "MAMELOSHNLM" (the provided excerpt only).

**[rrf]**

The evidence is insufficient to answer this question. The retrieved chunks mention "MAMELOSHNLM" only in the context of a statistical testing section (E.7) describing McNemar's exact test used to compare it against Llama 3.1 8B on lemmatization tasks — specifically counting discordant pairs where one model is correct and the other incorrect. Nothing in the evidence defines what MameLoshnLM is (e.g., its architecture, training data, or purpose) or states its parameter scale. The other two chunks are unrelated: one concerns a medical QA question about Parkinson's disease drugs, and the other describes GPT-3's word scrambling tasks.

Sources: [2608.05850] §E.7 Statistical Testing (chunk mentioning MAMELOSHNLM); [2212.13138] (unrelated medical QA example); [2005.14165] §3.9.2 (unrelated GPT-3 word manipulation tasks).

No retrieved evidence answers the question, so I am stopping here rather than drawing on prior knowledge.

**[vector]**

The evidence is insufficient to fully answer the question.

It does identify MameLoshnLM as "the first open-source large language model for Yiddish," trained on the Yiddish corpus described in subsection 3.2, and notes that it outperforms baselines "of similar scale." However, the excerpt is truncated mid-sentence at "produced by continued pretrain..." and never states the model's parameter count or parameter scale. No parameter scale is given in the retrieved evidence.

Source used: [2608.05850] §5 "MAMELOSHNLM".

</details>


## QK08 — `crosskb`

**Q:** Beyond which percentile of precipitation did the GAN clearly outperform the deterministic baseline in capturing the climate-change wetting signal?

**gold:** 2409.13934, 2409.13934

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 27.7 | 643 | 0.18804700000000002 | 4 | 否 | **95th percentile.** Both searches converge on the same paper. The retrieved text states that the GAN and deterministic baselines have "relatively sim |
| `bm25` | ✓ | ✓ | 5.2 | 174 | 0.029416 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks describe GAN performance relative to deterministic baselines only at the 99 |
| `rerank` | ✓ | ✓ | 5.3 | 73 | 0.0265126 | 0 | 否 | The evidence states that beyond the 95th percentile of precipitation, the GAN substantially better captures the wetting signal than the deterministic  |
| `rrf` | ✓ | ✓ | 4.5 | 180 | 0.0297714 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved evidence mentions GAN performance relative to deterministic baselines only for the |
| `vector` | ✓ | ✓ | 3.0 | 46 | 0.0258802 | 0 | 否 | The evidence states that beyond the **95th percentile** of precipitation, the GAN substantially better captures the wetting signal than the determinis |

<details><summary>逐字答案全文</summary>

**[a2]**

**95th percentile.** Both searches converge on the same paper.

The retrieved text states that the GAN and deterministic baselines have "relatively similar signals up to the 95th percentile of precipitation," but "beyond the 95th percentile, the GAN substantially better captures the wetting signal," though both underestimate its magnitude versus CCAM. GANs trained on the future period accurately capture the climate-change signal across nearly all percentiles, whereas the deterministic baselines underestimate it.

Sources used:
- `自然科学与地球科学/climate-science__2409.13934__on-the-extrapolation-of-generative-adversari (part 2 of 3).md` (chunk_index 6, KB `1e6199ea-f380-44e2-94fc-d431f0f9bb6b`)
- `Corpus-Chunks800/climate-science__2409.13934__on-the-extrapolation-of-generative-adversari__k17.md` (KB `0942f1a6-d81b-413b-a60b-b994680dcaac`) — same sentence, verbatim
- Document description of `climate-science__2409.13934__on-the-extrapolation-of-generative-adversari (part 1/2 of 3).md` — corroborates the "95 分位以上仍能更好捕捉湿化信号" summary

**[bm25]**

The evidence is insufficient to answer this question. The retrieved chunks describe GAN performance relative to deterministic baselines only at the 99.5th percentile of precipitation ([2409.13934]), stating the GAN captured ~97% (future-trained) or ~77% (historical-trained) of the increase while baselines captured 63–65%. No evidence identifies a percentile threshold *beyond which* the GAN clearly outperformed the deterministic baseline; only the 99.5th percentile is discussed. The other chunks ([2007.10574], [2409.09639]) concern MJO modulation of extreme precipitation and GPC/m dataset construction, respectively, and are unrelated.

Sources used: [2409.13934] (partially relevant); [2007.10574], [2409.09639] (not relevant).

**[rerank]**

The evidence states that beyond the 95th percentile of precipitation, the GAN substantially better captures the wetting signal than the deterministic baselines (which showed dry bias and similar signals up to that percentile).

Source: [2409.13934], chunk containing "Beyond the 95th percentile, the GAN substantially better captures the wetting signal…"

**[rrf]**

The evidence is insufficient to answer this question.

The retrieved evidence mentions GAN performance relative to deterministic baselines only for the **99.5th percentile** of precipitation (the GAN captured ~97% of the average future increase, vs. 63–65% for the deterministic baselines), and it does not state the threshold percentile above which the GAN clearly outperformed the baselines. No source among the evidence ([2409.13934], [2007.10574], [2409.09639]) establishes such a percentile threshold, so the question cannot be answered from the provided evidence.

Sources used: [2409.13934] (only source discussing GAN vs. deterministic baseline performance, mentioning the 99.5th percentile); [2007.10574] and [2409.09639] (retrieved but not relevant to the question).

**[vector]**

The evidence states that beyond the **95th percentile** of precipitation, the GAN substantially better captures the wetting signal than the deterministic baselines.

Source: [2409.13934] (chunk quoted above).

</details>


## QK09 — `unanswerable`

**Q:** What is the recommended daily dosage of metformin for diabetic cats?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 6.2 | 243 | 0.099785 | 1 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | — | — | 14.4 | 385 | 0.25023860000000003 | 0 | 是 | The evidence does not contain the answer. I reviewed all three provided chunks — [2110.08918] (ICU length-of-stay and mortality prediction from clinic |
| `rerank` | — | — | 7.3 | 133 | 0.033986800000000005 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks concern A1C/diabetes modeling, drug and NDC codes, adiponectin and type 2 d |
| `rrf` | — | — | 3.0 | 150 | 0.029168 | 0 | 是 | The retrieved evidence does not contain the answer. The three chunks provided discuss (1) ICU length-of-stay and mortality prediction models in clinic |
| `vector` | — | — | 3.9 | 152 | 0.0292252 | 0 | 是 | The retrieved evidence does not contain the answer. The chunks are table fragments and unrelated snippets from papers on biomedical QA benchmarks, dru |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

The evidence does not contain the answer. I reviewed all three provided chunks — [2110.08918] (ICU length-of-stay and mortality prediction from clinical notes), [2409.09639] (machine learning methods for GPC/m precipitation estimation), and [2412.15058] (MultiverSeg interactive image segmentation experiments) — and none of them mention metformin, feline diabetes, or any veterinary drug dosage. Therefore, the recommended daily dosage of metformin for diabetic cats cannot be determined from the provided evidence, and I will not answer from prior knowledge.

**[rerank]**

The evidence is insufficient to answer this question. The retrieved chunks concern A1C/diabetes modeling, drug and NDC codes, adiponectin and type 2 diabetes, diabetic retinopathy segmentation, and glucose/hypertension mentions, but none address metformin or feline diabetes dosing.

Sources checked for a relevant answer (none contained it): [2201.03675], [2110.08918], [2310.10981], [2502.00306], [2412.15058], [1904.11280], [2301.08436], [2212.13138], [2203.15752].

**[rrf]**

The retrieved evidence does not contain the answer. The three chunks provided discuss (1) ICU length-of-stay and mortality prediction models in clinical NLP (arXiv 2110.08918), (2) medical/biology exam Q&A examples on pharyngeal arches and Hardy-Weinberg equilibrium (arXiv 2212.13138), and (3) cost estimates for question generation and answer generation pipelines (arXiv 2502.00306). None of these sources mention metformin, feline diabetes, or veterinary dosing.

Sources used: [2110.08918], [2212.13138], [2502.00306] — none relevant to the question. Evidence is insufficient; I cannot answer without falling back on prior knowledge.

**[vector]**

The retrieved evidence does not contain the answer. The chunks are table fragments and unrelated snippets from papers on biomedical QA benchmarks, drug/NDC codes, adversarial attacks, Mastodon statistics, A1C–diabetes modeling, MERFISH imaging, segmentation datasets, and glucose mentions — none discuss metformin or feline diabetes dosing.

Sources consulted (all insufficient): [2212.13138], [2110.08918], [2502.00306], [2203.15752], [2201.03675], [2301.08436], [2310.10981], [2412.15058], [1904.11280].

Evidence is insufficient to answer the question, and no prior knowledge is being used.

</details>


## QK10 — `outofcorpus`

**Q:** How does the Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 19.0 | 791 | 0.086222 | 0 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | — | — | 15.5 | 489 | 0.254131 | 0 | 是 | The evidence provided does not answer this question. None of the three evidence chunks mention a "Herbert-Moulton collider benchmark," detector drift, |
| `rerank` | — | — | 8.2 | 163 | 0.03513240000000001 | 0 | 是 | The evidence is insufficient to answer this question. None of the eight retrieved chunks mention a "Herbert-Moulton collider benchmark," detector drif |
| `rrf` | — | — | 3.0 | 94 | 0.027593599999999996 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks cover influenza vaccine epitope cross-affinity (q-bio-0408016), supershear  |
| `vector` | — | — | 5.4 | 237 | 0.031443599999999995 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved chunks discuss a "Herbert-Moulton collider benchmark," nor do they describ |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

The evidence provided does not answer this question. None of the three evidence chunks mention a "Herbert-Moulton collider benchmark," detector drift, or particle physics experiments:

- **[2303.00445]** discusses error mitigation with number/spin operators in an HCl 3-qubit contextual subspace (quantum computing context) — no collider benchmark.
- **[1911.02792]** discusses coarse-grained molecular modeling with beads and mapping functions — no detector drift.
- **[2005.14165]** contains a GPT-3 generated news article about a Methodist church schism — unrelated.

The evidence is insufficient to answer this question, so I cannot provide an answer.

**Sources checked:** [2303.00445], [1911.02792], [2005.14165] — none contained relevant content.

**[rerank]**

The evidence is insufficient to answer this question. None of the eight retrieved chunks mention a "Herbert-Moulton collider benchmark," detector drift in particle physics, or any related collider instrumentation. The chunks cover unrelated topics: Chemoton software reaction steps ([2109.05887]), quantum circuit bootstrapping ([2303.00445]), cosine distance for perturbation effects ([2602.10156]), qubit decoherence ([1311.2485]), Trotter decompositions ([2311.00487]), antigenic drift affinity constants ([q-bio-0408016]), fault rupture motion ([2606.10843]), and black hole horizons ([gr-qc-9805045]). No source addresses the named benchmark or detector drift quantification, so I have no grounded basis to answer.

**[rrf]**

The evidence is insufficient to answer this question. The retrieved chunks cover influenza vaccine epitope cross-affinity (q-bio-0408016), supershear vs. subshear rupture particle motion (2606.10843), and contextual subspace error mitigation for HCl (2303.00445). None of them concerns a "Herbert-Moulton collider benchmark" or any method for quantifying detector drift in particle physics experiments. I cannot answer from prior knowledge.

**[vector]**

The evidence is insufficient to answer this question.

None of the retrieved chunks discuss a "Herbert-Moulton collider benchmark," nor do they describe how any collider benchmark quantifies detector drift. The chunks concern unrelated topics: antigenic drift in a statistical-mechanics affinity model (q-bio-0408016), cosine distance for perturbation prediction (2602.10156), rupture-speed sensitivity of ground motion (2606.10843), charged black-hole horizons (gr-qc-9805045), DFT+U for transition-metal oxides (2211.04977), Trotter decomposition error (2311.00487), qubit measurement current under bit-flip decoherence (1311.2485), and drift current density in semiconductors (1712.01369). No source addresses the named benchmark or detector drift in particle physics.

Sources retrieved (none relevant): q-bio-0408016, 2602.10156, 2606.10843, gr-qc-9805045, 2211.04977, 2311.00487, 1311.2485, 1712.01369.

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ✅ | 0 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=6.138 · manifest=6.138 |
| 单元数 = 题数 × 方法数 | ✅ | rows=50 vs 10×5=50 |
| provenance 完整 | ✅ | prompt_version=v4-neutral seed=0 |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*