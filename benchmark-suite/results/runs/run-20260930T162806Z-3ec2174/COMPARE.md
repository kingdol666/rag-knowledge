# 对照实验报告 — `run-20260930T162806Z-3ec2174`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-30 16:45 UTC

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
| `a2` | 67.18 | 31.9 | 363649 | 10467 | 4.6473 | 0.4647 | 3.2 | — | — |
| `bm25` | 8.36 | 5.8 | 71738 | 2835 | 0.647 | 0.0647 | 0.0 | — | — |
| `rerank` | 16.0 | 10.5 | 60709 | 2491 | 0.585 | 0.0585 | 0.0 | — | — |
| `rrf` | 7.35 | 5.3 | 24396 | 2382 | 0.4231 | 0.0423 | 0.0 | — | — |
| `vector` | 6.05 | 4.5 | 21202 | 2102 | 0.3959 | 0.0396 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 诚实性双向）

| method | 检索金标命中率 | 引用金标命中率 | 正确拒答(应拒答层) | 误拒(可答层) | error 数 |
|---|---:|---:|---:|---:|---:|
| `a2` | 0.5 | 0.5 | 0/2 (0.0) | 0/8 (0.0) | 0 |
| `bm25` | 1.0 | 1.0 | 2/2 (1.0) | 4/8 (0.5) | 0 |
| `rerank` | 1.0 | 1.0 | 2/2 (1.0) | 4/8 (0.5) | 0 |
| `rrf` | 1.0 | 1.0 | 2/2 (1.0) | 4/8 (0.5) | 0 |
| `vector` | 1.0 | 1.0 | 2/2 (1.0) | 5/8 (0.625) | 0 |

> **口径说明**：baseline 的「检索命中」基于其真实 ranked 列表（可直接观测）；agent 轨（a/a2/b/c）的 SSE 轨迹只含工具**入参**、不含检索结果文档 id，故其检索命中由 trace ∪ 答案推断（`retrieval_basis=trace+answer`）。**agent 轨请以「引用命中率」为可靠功能信号。**

## QK01 — `single`

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**gold:** 1706.03762, 1706.03762

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✗ | ✗ | 23.8 | 235 | 0.6574929999999999 | 2 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | ✓ | ✓ | 6.7 | 180 | 0.0342688 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks describe aspects of the Transformer (multi-head attention with h=8 heads, d |
| `rerank` | ✓ | ✓ | 12.0 | 278 | 0.0353076 | 0 | 是 | The evidence is insufficient to answer the full question. What the retrieved chunks do support: [2510.13343] states the Transformer's key strength "li |
| `rrf` | ✓ | ✓ | 4.4 | 252 | 0.031571 | 0 | 是 | The retrieved evidence is insufficient to answer this question. The evidence explains only parts of the Transformer's design: it states that multi-hea |
| `vector` | ✓ | ✓ | 5.0 | 341 | 0.0361864 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved chunks explains *why* the Transformer replaces recurrence and convolution  |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

The evidence is insufficient to answer this question. The retrieved chunks describe aspects of the Transformer (multi-head attention with h=8 heads, d_k=d_v=d_model/h=64, and the three applications of attention in encoder-decoder, encoder self-attention, and decoder self-attention layers — chunk [1706.03762]), but none of them explain *why* the architecture replaces recurrence and convolution. The BERT chunk [1810.04805] covers span-based question answering, and [2503.21676] covers attention patching, neither of which addresses the question. No source in the evidence states the computational rationale for replacing recurrence and convolution (e.g., parallelization or path-length arguments).

Sources used: chunks [1706.03762], [1810.04805], [2503.21676] (examined; none answers the question).

**[rerank]**

The evidence is insufficient to answer the full question. What the retrieved chunks do support: [2510.13343] states the Transformer's key strength "lies in its attention mechanism, which learns to focus on relevant parts of the input data," and [1706.03762] (the Transformer paper's conclusion) says the model is "based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention," while [2110.07844] describes cross-attention as computing "query, key and value vectors" with attention weights being "a normalized dot product between query and key vectors," the head output being "a weighted sum of value vectors."

However, no chunk explains *why* recurrence and convolution are replaced (e.g., computational or path-length motivations), and no chunk supplies a full mechanics account (scaled dot-product, multi-head formulation) from the source paper. The documents list [1906.10015], [2503.21676], [1810.04805] are off-topic here.

Sources used: 2510.13343 (chunk quoted), 1706.03762 (conclusion chunk), 2110.07844 (cross-attention chunk).

The evidence does not contain an answer to the "why" portion; I will not answer from prior knowledge.

**[rrf]**

The retrieved evidence is insufficient to answer this question.

The evidence explains only parts of the Transformer's design: it states that multi-head attention uses $h=8$ parallel heads with $d_k = d_v = d_{\mathrm{model}}/h = 64$, producing a total computational cost similar to single-head attention of full dimensionality, and it lists the three applications of attention (encoder-decoder attention with queries from the previous decoder layer and keys/values from the encoder output; encoder self-attention where keys, values and queries all come from the previous layer; and decoder self-attention) ([1706.03762], §3.2.2–3.2.3).

It does not describe how attention scores are computed (e.g., scaled dot-product), and it contains no discussion of why recurrence or convolution is replaced. The other two passages concern BERT span-based question answering ([1810.04805]) and attention patching via a twin architecture ([2503.21676]), neither of which addresses the question.

Sources used: [1706.03762] (partial, multi-head attention only); [1810.04805] (not relevant); [2503.21676] (not relevant).

**[vector]**

The evidence is insufficient to answer this question.

None of the retrieved chunks explains *why* the Transformer replaces recurrence and convolution — that section of [1706.03762] (the "Why Self-Attention" / motivation discussion) is truncated before any comparison of computational complexity or path length. What the evidence does contain is fragmentary:

- [1706.03762] §7 Conclusion states the Transformer is "the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention," but gives no rationale for the replacement.
- [2110.07844] gives a partial description of attention computation: a cross-attention head maps decoder state and encoder state into query, key, and value vectors, computes attention weights as "a normalized dot product between query and key vectors," and outputs a weighted sum of value vectors.
- [2510.13343] only asserts generally that "the key strength of the Transformer lies in its attention mechanism, which learns to focus on relevant parts of the input data."
- [1810.04805] and [2503.21676] mention layer counts, head counts, and an ablation where attention is replaced with recurrence, but neither states the justification for replacing recurrence/convolution.

Since the "why" is absent and the "how" is only partially covered by one chunk, the evidence does not support a full answer. I am not filling this gap from prior knowledge.

Sources used: [1706.03762], [1810.04805], [2110.07844], [2503.21676], [2510.13343].

</details>


## QK02 — `single`

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**gold:** 1602.01876, 1602.01876

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 37.2 | 688 | 0.7774208 | 6 | 否 | The three independent ontologies that subdivide the Gene Ontology are **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Compone |
| `bm25` | ✓ | ✓ | 4.1 | 139 | 0.0312926 | 0 | 是 | The evidence is insufficient to answer the question. The retrieved chunks mention the Gene Ontology (document [1602.01876]) and state that "The GO pro |
| `rerank` | ✓ | ✓ | 18.2 | 77 | 0.0280654 | 0 | 否 | The Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: Molecular Function (MF), Biological Process  |
| `rrf` | ✓ | ✓ | 3.8 | 155 | 0.0329314 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks describe the Gene Ontology as a "controlled vocabulary of terms to represen |
| `vector` | ✓ | ✓ | 3.0 | 64 | 0.0262478 | 0 | 否 | The evidence answers this. According to the source, the Gene Ontology is subdivided into three distinct ontologies representing different biological a |

<details><summary>逐字答案全文</summary>

**[a2]**

The three independent ontologies that subdivide the Gene Ontology are **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**. This is stated verbatim in the retrieved document: "The terms are subdivided in three distinct ontologies that represent different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC) (1). These ontologies are non-redundant and share a common space of identifiers and a well-specified syntax."

Sources used:
- `生命科学与医学/genomics__1602.01876__primer-on-the-gene-ontology.md (part 1 of 2).md` — section "## 2. What is the Gene Ontology?", chunk_index 9 (vector score 0.7639)
- `Corpus-Chunks800/genomics__1602.01876__primer-on-the-gene-ontology__k01.md` — chunk_index 3 (mirror copy, same sentence)

Source paper: Gaudet, Škunca, Hu, Dessimoz, "Primer on the Gene Ontology" (arXiv 1602.01876).

**[bm25]**

The evidence is insufficient to answer the question.

The retrieved chunks mention the Gene Ontology (document [1602.01876]) and state that "The GO project consists of the Gene Ontology itself... and annotations," but none of the three supplied chunks name the three independent ontologies (molecular function, biological process, cellular component) that subdivide GO. The other two chunks ([2301.08436], [2401.06823]) concern spatial transcriptomics and interpretable deep learning, not GO's internal structure.

Sources used: [1602.01876], [2301.08436], [2401.06823] — none contain the requested subdivision.

**[rerank]**

The Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).

Source: [1602.01876] §2 "What is the Gene Ontology?"

The other two retrieved chunks ([2110.07787], [2508.18304]) are irrelevant to this question.

**[rrf]**

The evidence is insufficient to answer this question. The retrieved chunks describe the Gene Ontology as a "controlled vocabulary of terms to represent biology in a structured way" and discuss GO annotations, but none of them name the three independent ontologies that subdivide the Gene Ontology.

Sources retrieved (none contain the answer):
- [1602.01876] — GO primer chunk (introduction and "What is the Gene Ontology?")
- [2508.18304] — monocyte subcluster / GSEA chunk
- [2110.07787] — single-cell annotation chunk

None of these chunks list the three ontologies (e.g., molecular function, biological process, cellular component), so I am stopping rather than answering from prior knowledge.

**[vector]**

The evidence answers this. According to the source, the Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC).

Source used: [1602.01876], section "2. What is the Gene Ontology?"

</details>


## QK03 — `single`

**Q:** What physical mechanism does the dynamic electrical model use to explain the hysteretic J-V characteristics of perovskite solar cells?

**gold:** 1606.00335, 1606.00335

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 25.6 | 1112 | 0.23775619999999997 | 5 | 否 | I retrieved the source paper directly and it answers the question. **Answer:** The dynamic electrical model explains perovskite J-V hysteresis through |
| `bm25` | ✓ | ✓ | 8.2 | 259 | 0.0357944 | 0 | 是 | The evidence is insufficient to answer the question as posed. Neither retrieved passage describes a *physical mechanism* explaining hysteresis. [1606. |
| `rerank` | ✓ | ✓ | 36.2 | 885 | 0.26060799999999995 | 0 | 否 | **Answer:** The model explains the hysteretic J-V characteristics through **polarization relaxation** in the perovskite material. Specifically, it "ma |
| `rrf` | ✓ | ✓ | 3.9 | 238 | 0.0310596 | 0 | 否 | The evidence describes the standard dynamic electrical model of a perovskite solar cell as an equivalent electric circuit containing a photocurrent so |
| `vector` | ✓ | ✓ | 3.7 | 132 | 0.0295954 | 0 | 是 | The evidence is insufficient to answer this question. The abstract from [1606.00335] states that a dynamic electrical model is introduced to investiga |

<details><summary>逐字答案全文</summary>

**[a2]**

I retrieved the source paper directly and it answers the question.

**Answer:** The dynamic electrical model explains perovskite J-V hysteresis through a **polarization mechanism** (a slow, time-dependent polarization relaxation). The standard static equivalent circuit (photocurrent source, diode, series/shunt resistances) is extended with a capacitor whose displacement current includes botha linear and a **non-linear polarization term** $P_{nl}(t)$, so that $I_c = C_0\,\partial U_c/\partial t + \mathcal{A}\,\partial P_{nl}(t)/\partial t$. The non-linear polarization arises from the non-linear response of charge to the combined light and electric field inside the device or at the electrode interfaces, and is described by a simple ansatz for polarization relaxation. Because this polarization relaxes on a finite time scale, forward and reverse bias sweeps are dynamically non-equivalent, producing the hysteresis; the model reproduces the reverse-scan current overshoot as an initial over-polarization effect and the C-shaped features under initial under-polarization. The hysteresis amplitude peaks at intermediate bias scan rates and vanishes at very slow or very fast sweeps, matching experiment.

Sources used:
- `工程与能源/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs (part 1 of 2).md` (KB `8fa4db59-adde-4d6d-9fdb-2c375400e631`) — abstract, Sections 2.1–2.2 (Eqs. 1–8, Fig. 1).
- Chunks `materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs__k20.md`, `__k00.md`, `__k01.md`, `__k22.md` (KB `0942f1a6-d81b-413b-a60b-b994680dcaac`).

Note: `kb_laya_judge` returned "unavailable" (its reference fetch through the web proxy at localhost:6789 failed), so verification rested on the direct `kb_doc_read` of the full text, which is quoted above.

**[bm25]**

The evidence is insufficient to answer the question as posed.

Neither retrieved passage describes a *physical mechanism* explaining hysteresis. [1606.00335] presents a standard dynamic electrical model — an equivalent circuit with photocurrent source, diode (ideality factor n), shunt resistance R_sh, series resistance R_s, and a parallel capacitance C — and states that simulated J-V characteristics show hysteretic effects influenced by solar cell preconditioning and bias scan rate, with the analysis focused on time variation of polarization under an assumed relaxation time scale. However, its quoted text stops mid-sentence at the capacitance description and never names the mechanism (e.g., ion migration, trapping) responsible for hysteresis.

[1712.01369] concerns a perovskite/GeSe bilayer cell's J_sc, V_oc, FF, and efficiency values — not hysteretic J-V behavior or its mechanism. [2607.03098] covers energy storage models (flywheels, batteries) and is unrelated to perovskite solar cells.

Sources used: [1606.00335] §2/2.1 (equivalent-circuit description); [1712.01369] (bilayer cell parameter table); [2607.03098] (ESM dynamics). None supplies the requested physical mechanism.

**[rerank]**

**Answer:** The model explains the hysteretic J-V characteristics through **polarization relaxation** in the perovskite material. Specifically, it "makes a simple ansatz for the polarization relaxation," and with this ansatz the dynamic electrical model reproduces detailed features of measured J-V curves both qualitatively and quantitatively ([1606.00335], Abstract). The central role of polarization is further supported by the model's treatment of pre-poling effects, which distinguishes initially over-polarized from under-polarized samples — i.e., the hysteresis depends on the sample's prior polarization state ([1606.00335], Abstract).

**Sources:**
- [1606.00335] — Abstract chunk (dynamic electrical model, polarization relaxation ansatz, pre-poling effects)
- [1712.01369] — (retrieved but not used; concerns bilayer cell simulation parameters, not the hysteresis mechanism)

**[rrf]**

The evidence describes the standard dynamic electrical model of a perovskite solar cell as an equivalent electric circuit containing a photocurrent source, a diode (ideality factor n), shunt resistance R_sh, series resistance R_s, and **in addition to the static model, a parallel capacitance C** ([1606.00335]). The paper states that simulated J-V characteristics are compared to experimental data, describing hysteretic effects influenced by solar cell preconditioning and bias scan rate, with the analysis focused on **the variation of the polarization in time, assuming a certain relaxation time scale**, and it investigates the influence of different relaxation time scales ([1606.00335]).

So the mechanism the evidence attributes the hysteresis to is the time-dependent polarization (relaxation-time-scale dynamics) captured by the added parallel capacitance in the equivalent circuit — the evidence does not go further into the underlying physical/ionic origin.

Sources used: [1606.00335] (Sections 1–2.1). The other two chunks ([1712.01369], [2607.03098]) are about perovskite/GeSe bilayer efficiency and energy-storage models and say nothing about the hysteresis mechanism.

**[vector]**

The evidence is insufficient to answer this question. The abstract from [1606.00335] states that a dynamic electrical model is introduced to investigate hysteretic effects in the J-V characteristics of perovskite solar cells, and mentions it makes "a simple ansatz for the polarization relaxation," but it does not describe the physical mechanism itself. The excerpt from [1712.01369] concerns a separate bilayer solar cell simulation and provides no mechanism explanation. No source in the evidence explains the physical mechanism responsible for the hysteretic behavior.

Sources used: [1606.00335] (abstract, truncated); [1712.01369] (excerpt).

</details>


## QK04 — `single`

**Q:** Using only what kind of information, and reaching what accuracy, does the wav2vec 2.0 approach detect within-sentence prosodic boundaries on Czech broadcast news?

**gold:** 2209.15032, 2209.15032

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✗ | ✗ | 35.2 | 1669 | 0.28024 | 0 | 否 | Retrieval plan: query the platform KB with `kb_search_vector` / `kb_search_two_stage` for wav2vec 2.0 prosodic-boundary detection on Czech broadcast n |
| `bm25` | ✓ | ✓ | 3.8 | 110 | 0.027739 | 0 | 否 | The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information**. It reaches an **accuracy of 94%** (and an F1 |
| `rerank` | ✓ | ✓ | 9.0 | 104 | 0.027545200000000002 | 0 | 否 | The evidence states the wav2vec 2.0 approach uses **only acoustic information** to detect these boundaries in the speech signal, tested on Czech broad |
| `rrf` | ✓ | ✓ | 6.3 | 143 | 0.033442400000000004 | 0 | 否 | The evidence answers this: the wav2vec 2.0 approach detects prosodic boundaries **using only acoustic information**, and on within-sentence prosodic b |
| `vector` | ✓ | ✓ | 3.1 | 51 | 0.0269064 | 0 | 否 | Using only acoustic information, the wav2vec 2.0 approach detects within-sentence prosodic boundaries on Czech broadcast news with an accuracy of 94%  |

<details><summary>逐字答案全文</summary>

**[a2]**

Retrieval plan: query the platform KB with `kb_search_vector` / `kb_search_two_stage` for wav2vec 2.0 prosodic-boundary detection on Czech broadcast news, then pass surviving document references to `kb_laya_judge` for segment-level verification and answer only from the verified survivors. However, my execution-time tool list contains no `mcp__kb-mcp__*` tools, so retrieval cannot proceed this turn.

KB_TOOLS_NOT_READY

**[bm25]**

The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information**. It reaches an **accuracy of 94%** (and an F1 measure of 83%) on within-sentence prosodic boundaries in Czech broadcast news recordings labeled by phonetic experts. This outperformed the existing text-based predictor that used transcripts of the same data.

Source used: `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (part 1/2).

**[rerank]**

The evidence states the wav2vec 2.0 approach uses **only acoustic information** to detect these boundaries in the speech signal, tested on Czech broadcast news recordings.

It reports an **accuracy of 94%** (and F1 measure of 83%) on within-sentence prosodic boundaries — the sentence is cut off at "or 95%", so a second figure is indicated but not fully given.

Source used: arXiv paper [2209.15032] (excerpt as provided).

**[rrf]**

The evidence answers this: the wav2vec 2.0 approach detects prosodic boundaries **using only acoustic information**, and on within-sentence prosodic boundaries it achieves an **accuracy of 94% and an F1 measure of 83%** (or 95% and 89% on all prosodic boundaries).

Source used: `[2209.15032]` — "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" (Kunešová & Rezáčková), chunk `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (part 1/2), abstract.

**[vector]**

Using only acoustic information, the wav2vec 2.0 approach detects within-sentence prosodic boundaries on Czech broadcast news with an accuracy of 94% (F1 measure of 83%).

Source: [2209.15032]

</details>


## QK05 — `single`

**Q:** In the trap-cropping optimization framework, roughly what share of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant?

**gold:** 2508.05896, 2508.05896

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 379.2 | 2123 | 1.2064237999999998 | 10 | 否 | **Answer** According to the retrieved paper ("Optimal trap cropping investments to maximize agricultural yield", arXiv 2508.05896), when trap plants a |
| `bm25` | ✓ | ✓ | 4.2 | 131 | 0.0284396 | 0 | 否 | The evidence answers this. Per Figure 3 and its discussion, when trap plants are five times and 25 times more attractive than the cash plant, approxim |
| `rerank` | ✓ | ✓ | 4.5 | 116 | 0.0282234 | 0 | 是 | The evidence is insufficient to answer this question. The excerpt states that at an attractiveness ratio of five, "it is optimal to devote roughly ten |
| `rrf` | ✓ | ✓ | 13.1 | 146 | 0.033077 | 0 | 否 | The evidence answers this: in the trap-cropping yield optimization framework, when trap plants are 5 to 25 times more attractive than the cash plant,  |
| `vector` | ✓ | ✓ | 6.6 | 127 | 0.0280326 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunk only describes the case where attractiveness equals five (a pest is five tim |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer**

According to the retrieved paper ("Optimal trap cropping investments to maximize agricultural yield", arXiv 2508.05896), when trap plants are 5 to 25 times more attractive than the cash plant, approximately **7–10% of the field should be allocated to trap plants**. The same passage notes that below that attractiveness range the grower should plant only cash plants (accepting pest losses), while at an attractiveness of 5 the optimum is roughly ten percent of the land devoted to the trap crop. (Note: the platform's content-verification judge call timed out, but the passage was retrieved verbatim from two independent vector collections that agree.)

**Sources**
- `生命科学与医学/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz (part 2 of 3).md`, chunk_index 11, kb_id `b28f0a25-1e1d-40ad-96b8-61bd2b093a28` (via `kb_search_two_stage`)
- `Corpus-Chunks800/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz__k17.md`, kb_id `0942f1a6-d81b-413b-a60b-b994680dcaac` (via `kb_search_vector`)

**[bm25]**

The evidence answers this. Per Figure 3 and its discussion, when trap plants are five times and 25 times more attractive than the cash plant, approximately 7–10% of the field should be allocated to trap plants; the text adds that for five-times attractiveness it is optimal to devote roughly ten percent of the land to the trap crop.

Source used: [2508.05896], Figure 3 (caption and accompanying text; figure image `images/9642902ba69bbbf174883714e1b417780eab02313797fc42ac01e5f6831d1d29.jpg`).

**[rerank]**

The evidence is insufficient to answer this question. The excerpt states that at an attractiveness ratio of five, "it is optimal to devote roughly ten percent of the land to the trap crop," and separately notes that 7–10% should be allocated to trap plants — but it never gives a share for the higher end of the range asked about (25 times more attractive). No figure or statement covering the 5–25× span appears in the retrieved text.

Source used: chunk from `[2508.05896]` (trap-cropping optimization excerpt).

**[rrf]**

The evidence answers this: in the trap-cropping yield optimization framework, when trap plants are 5 to 25 times more attractive than the cash plant, roughly **7–10% of the field** should be allocated to trap plants (with ~10% optimal at five-times attractiveness). For trap plants only twice as attractive, trap cropping is ineffective and the grower should plant only cash plants.

Source: [2508.05896], Figure 3 and its caption/body text. (The other two retrieved documents — [1609.00415] on Chinese infrastructure and [1512.08067] on Malthusian-trap economic growth — are irrelevant to this question and were not used.)

**[vector]**

The evidence is insufficient to answer this question.

The retrieved chunk only describes the case where attractiveness equals five (a pest is five times more likely to settle on a trap plant), for which roughly ten percent of the land should be devoted to the trap crop, and mentions an approximate 7–10% allocation range otherwise. It contains no information about the 25-times-attractiveness case, so it does not establish the allocation share across the full 5-to-25× range you asked about.

Source used: chunk from [2508.05896] (excerpt discussing Figure 3b and trap-plant attractiveness).

</details>


## QK06 — `single`

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**gold:** 1503.07557, 1503.07557

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✗ | ✗ | 28.6 | 1169 | 0.220055 | 0 | 否 | Retrieval plan: I would run `kb_search_vector` (with a high top_k over the whole library) on "physical factor controlling response of precipitation ex |
| `bm25` | ✓ | ✓ | 18.4 | 656 | 0.257297 | 0 | 否 | Based on the evidence, the response of precipitation extremes to climate change is governed by **several physical contributions**: the **thermodynamic |
| `rerank` | ✓ | ✓ | 7.6 | 179 | 0.031139399999999998 | 0 | 是 | The evidence does not contain an answer to this question. The first source ([1503.07557], O'Gorman, "Precipitation extremes under climate change") sta |
| `rrf` | ✓ | ✓ | 3.8 | 188 | 0.033508800000000005 | 0 | 是 | The evidence is insufficient to answer this question as posed. The first source (O'Gorman, *Precipitation extremes under climate change*, chunk 1/3) s |
| `vector` | ✓ | ✓ | 6.2 | 176 | 0.0310168 | 0 | 是 | The evidence is insufficient to fully answer this question. The retrieved chunks only partially address it. One source states the focus is on "the phy |

<details><summary>逐字答案全文</summary>

**[a2]**

Retrieval plan: I would run `kb_search_vector` (with a high top_k over the whole library) on "physical factor controlling response of precipitation extremes to climate change", then pass candidate documents through `kb_laya_judge` for segment-level content verification and read the survivors with `kb_doc_read`. However, no `mcp__kb-mcp__*` tools are present in my current tool list, so I cannot execute this retrieval.

KB_TOOLS_NOT_READY

**[bm25]**

Based on the evidence, the response of precipitation extremes to climate change is governed by **several physical contributions**: the **thermodynamic**, **microphysical**, and **dynamical** contributions. Among these, the **thermodynamic contribution** is the one the evidence characterizes as "robust and well understood," while theoretical understanding of the microphysical and dynamical contributions is described as still being developed. The evidence does not explicitly single out one factor as the "primary" controller — it states that several physical contributions govern the response, with the thermodynamic one being the best understood.

Sources:
- [1503.07557] climate-science__1503.07557__precipitation-extremes-under-climate-change.md (part 1/3, Abstract, O'Gorman)

**[rerank]**

The evidence does not contain an answer to this question.

The first source ([1503.07557], O'Gorman, "Precipitation extremes under climate change") states that its abstract focuses on "the physical factors that control the response" but the retrieved text is truncated at exactly that point — it does not name which factor is primary. The other two sources are off-topic for this question: [2409.13934] discusses learnability of extreme-precipitation signals under future climate contexts, and [2007.10574] covers dynamical links between MJI-induced precipitation and moisture flux convergence/advection, neither of which identifies the primary controlling factor.

Sources used: [1503.07557] (truncated abstract); [2409.13934] (irrelevant); [2007.10574] (irrelevant). No source provides the answer.

**[rrf]**

The evidence is insufficient to answer this question as posed. The first source (O'Gorman, *Precipitation extremes under climate change*, chunk 1/3) states that "several physical contributions govern the response of precipitation extremes," identifying a thermodynamic contribution (described as robust and well understood), microphysical and dynamical contributions (theoretical understanding still being developed), and noting that orographic precipitation extremes and snowfall extremes respond differently. It does not name any single factor as the primary control, so no single "primarily controls" factor can be identified from this evidence. The other two sources (2409.13934 and 2007.10574) concern emulator skill and MJO modulation respectively and do not address the controlling factor.

Sources used:
- [1503.07557] climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md (part 1/3)

**[vector]**

The evidence is insufficient to fully answer this question.

The retrieved chunks only partially address it. One source states the focus is on "the physical factors that control the response" but the abstract is truncated before naming any specific factor ([1503.07557] "Precipitation extremes under climate change"). Another chunk references the Clausius-Clapeyron relation and a "~7%/°C" warming-driven signal for extreme precipitation, but only in passing, without identifying it as the primary controlling factor ([2409.13934]). The remaining chunk discusses vertical moisture flux convergence and vertical advection of moisture as processes modulating MJO-induced precipitation, which is a different question about dynamical links, not the primary control on the climate-change response ([2007.10574]).

None of the evidence explicitly names the single physical factor that primarily controls the response of precipitation extremes to climate change.

</details>


## QK07 — `distractor`

**Q:** What is MameLoshnLM and what parameter scale does it have?

**gold:** 2608.05850, 2608.05850

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 58.8 | 2047 | 0.9700512000000001 | 8 | 否 | **Answer:** MAMELOSHNLM is the first open-source large language model built specifically for Yiddish — its name derives from "Mame-Loshn" (Yiddish for |
| `bm25` | ✓ | ✓ | 3.2 | 146 | 0.0335974 | 0 | 是 | The evidence is insufficient to answer the question. The retrieved chunks mention MAMELOSHNLM only in passing — as a model compared against Llama 3.1  |
| `rerank` | ✓ | ✓ | 7.1 | 169 | 0.0287772 | 0 | 是 | The evidence describes MAMELOSHNLM as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3. |
| `rrf` | ✓ | ✓ | 4.0 | 149 | 0.029122 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved passages mention "MAMELOSHNLM" only in the context of a statistical testing method |
| `vector` | ✓ | ✓ | 4.0 | 164 | 0.0292808 | 0 | 是 | The evidence identifies **MameLoshnLM** as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsecti |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** MAMELOSHNLM is the first open-source large language model built specifically for Yiddish — its name derives from "Mame-Loshn" (Yiddish for "mother tongue") — and it was produced by continuing pretraining of Llama 3.1 8B on Oytser, a curated Yiddish corpus, using a causal language-modeling objective. It is an 8-billion-parameter model ("8B-parameter LM for Yiddish"), and the paper also introduces two supporting resources: the Oytser pretraining corpus and the Kashes benchmark. Across the Kashes tasks it outperforms open baselines of similar scale on Yiddish-centered tasks such as translation, linguistic analysis, and named-entity recognition.

Sources used:
- 计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md (part 1 of 4).md — kb_id b1199132-e4d4-4305-8c2e-82dc1753b0ba (read directly; abstract + §1 + §5 chunks 2/53/10/12)
- Corpus-Chunks800/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu__k00.md and __k02.md — kb_id 0942f1a6-d81b-413b-a60b-b994680dcaac (vector-search chunks confirming the same text)

Note: `kb_laya_judge` returned fail-closed ("all reference fetches failed") because the web proxy's document endpoint (:6789) rejected the raw chunk paths, so I verified by reading the canonical KB document directly instead.

**[bm25]**

The evidence is insufficient to answer the question. The retrieved chunks mention MAMELOSHNLM only in passing — as a model compared against Llama 3.1 8B using McNemar's exact test ([2608.05850], §E.7) — and give no definition of what MameLoshnLM is or its parameter scale. The other chunks ([2212.13138], [2005.14165]) are unrelated to this model and do not help. I cannot supply the answer from prior knowledge.

Sources: [2608.05850] §E.7; [2212.13138]; [2005.14165] §3.9.2.

**[rerank]**

The evidence describes MAMELOSHNLM as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2, and named "Mame-Loshn" ("mother tongue") in reference to the traditional Yiddish term evoking the language's intimate connection to home and family. It reportedly outperforms strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks, and was produced by continued pretraining. However, the evidence does not state what parameter scale or model size it has — only that it outperforms "baselines of similar scale," which does not specify the actual parameter count. The evidence is therefore insufficient to answer the parameter-scale portion of the question.

Source used: [2608.05850], section "5 MAMELOSHNLM".

**[rrf]**

The evidence is insufficient to answer this question.

The retrieved passages mention "MAMELOSHNLM" only in the context of a statistical testing methodology (McNemar's exact test for pairwise model comparisons against Llama 3.1 8B) in document [2608.05850], but they do not describe what MameLoshnLM is nor state any parameter scale for it. The other retrieved chunks ([2212.13138], [2005.14165]) are unrelated to MameLoshnLM.

Sources used: [2608.05850] (Section E.7, Statistical Testing) — the only source that names MAMELOSHNLM; it provides no definition or parameter scale.

**[vector]**

The evidence identifies **MameLoshnLM** as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2, and named after the traditional Yiddish term "mame-loshn" ("mother tongue"). It was produced by continued pretraining and reportedly outperforms strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks.

However, the evidence does **not** state MameLoshnLM's parameter scale — the excerpt cuts off mid-sentence at "continued pretrain" and contains no parameter count or model size. I cannot answer the parameter-scale part of the question from this evidence.

Source used: chunk `[2608.05850] ## 5 MAMELOSHNLM` (Section 5 excerpt).

</details>


## QK08 — `crosskb`

**Q:** Beyond which percentile of precipitation did the GAN clearly outperform the deterministic baseline in capturing the climate-change wetting signal?

**gold:** 2409.13934, 2409.13934

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✗ | ✗ | 13.3 | 422 | 0.07702899999999999 | 0 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | ✓ | ✓ | 19.1 | 703 | 0.08743500000000001 | 0 | 否 | **Answer: the 99.5th percentile.** The evidence (chunk [2409.13934]) compares the GAN against two deterministic baseline algorithms specifically at th |
| `rerank` | ✓ | ✓ | 18.1 | 244 | 0.071937 | 0 | 否 | Beyond the 95th percentile of precipitation. The evidence states that the two algorithms had relatively similar climate-change signals up to the 95th  |
| `rrf` | ✓ | ✓ | 12.2 | 475 | 0.08230599999999999 | 0 | 否 | Based on the evidence, the comparison is reported for the **99.5th percentile** of precipitation: at that percentile, the GAN trained on future and hi |
| `vector` | ✓ | ✓ | 8.6 | 240 | 0.071837 | 0 | 否 | Beyond the **95th percentile** of precipitation, the GAN substantially better captured the climate-change wetting signal, while up to that percentile  |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

**Answer: the 99.5th percentile.**

The evidence (chunk [2409.13934]) compares the GAN against two deterministic baseline algorithms specifically at the 99.5th percentile of precipitation: the GAN trained on future and historical periods captures about 97% of the average future increase in the 99.5th percentile of precipitation (closely following the 1:1 line), whereas the deterministic baselines capture only 63–65% of that future increase, regardless of their training period. Even the GAN trained only on historical simulations captures about 77% of the warming-driven increase in 99.5th-percentile precipitation, still well above the baselines. The evidence only quantifies this GAN-vs-baseline gap at the 99.5th percentile, so that is the threshold supported by the provided evidence.

**Sources:** evidence chunk [2409.13934] (GAN climate-change precipitation signal passage).

**[rerank]**

Beyond the 95th percentile of precipitation. The evidence states that the two algorithms had relatively similar climate-change signals up to the 95th percentile, and that "Beyond the 95th percentile, the GAN substantially better captures the wetting signal" compared to the deterministic baseline (though both underestimate its magnitude relative to CCAM).

Source: evidence chunk [2409.13934].

**[rrf]**

Based on the evidence, the comparison is reported for the **99.5th percentile** of precipitation: at that percentile, the GAN trained on future and historical periods captured about 97% of the average future increase (and the GAN trained on historical simulations captured about 77%), while the two deterministic baseline algorithms captured only 63–65% of the future increase. Thus, the evidence identifies the 99.5th percentile as the level at which the GAN clearly outperformed the deterministic baselines in capturing the climate-change wetting signal. The evidence does not provide performance figures for other percentiles, so no statement beyond the 99.5th percentile can be made.

Source: chunk [2409.13934].

**[vector]**

Beyond the **95th percentile** of precipitation, the GAN substantially better captured the climate-change wetting signal, while up to that percentile the two algorithms showed relatively similar signals (both with a dry bias). Both algorithms still underestimated the magnitude of the wetting signal compared to CCAM.

Source: evidence chunk from document [2409.13934].

</details>


## QK09 — `unanswerable`

**Q:** What is the recommended daily dosage of metformin for diabetic cats?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 18.6 | 833 | 0.087249 | 0 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | — | — | 11.0 | 344 | 0.07782 | 0 | 是 | The retrieved evidence does not contain the answer to this question. None of the three provided chunks mention metformin, diabetic cats, or any veteri |
| `rerank` | — | — | 38.6 | 179 | 0.035487399999999995 | 0 | 是 | The evidence is insufficient to answer the question. None of the retrieved chunks address feline (cat) diabetes treatment or metformin dosing. The evi |
| `rrf` | — | — | 6.2 | 136 | 0.033080399999999996 | 0 | 是 | The evidence is insufficient to answer the question. The three retrieved sources — [2110.08918] (ICU length-of-stay and mortality prediction from mult |
| `vector` | — | — | 16.7 | 587 | 0.085815 | 0 | 是 | The provided evidence does not answer this question. None of the retrieved chunks mention metformin, veterinary medicine, or dosing information for di |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

The retrieved evidence does not contain the answer to this question. None of the three provided chunks mention metformin, diabetic cats, or any veterinary drug dosage. The evidence covers three unrelated topics: ICU length-of-stay and mortality prediction from clinical notes ([2110.08918]), machine-learning-based GPC/m precipitation estimation ([2409.09639]), and image segmentation with MultiverSeg ([2412.15058]). Therefore, the evidence is insufficient, and I cannot answer the question from the provided documents.

Sources used (all inspected, none relevant): [2110.08918], [2409.09639], [2412.15058].

**[rerank]**

The evidence is insufficient to answer the question.

None of the retrieved chunks address feline (cat) diabetes treatment or metformin dosing. The evidence consists of unrelated fragments: A1C/diabetes modeling for humans ([2201.03675]), a drug/NDC-code table listing heparin, acetaminophen, morphine ([2110.08918]), an adversarial interrogation example mentioning adiponectin ([2502.00306]), and various other clinical or benchmark snippets ([1904.11280], [2310.10981], [2412.15058], [2212.13138], [2203.15752], [2301.08436]). No source discusses metformin, and none concerns veterinary medicine or cat dosages. I cannot answer from this evidence and will not fall back on prior knowledge.

Sources used: none — no retrieved chunk contained relevant information.

**[rrf]**

The evidence is insufficient to answer the question.

The three retrieved sources — [2110.08918] (ICU length-of-stay and mortality prediction from multimodal clinical data), [2212.13138] (medical/biology QA examples on pharyngeal arches and Hardy-Weinberg equilibrium), and [2502.00306] (cost estimation for yes/no question and description generation with GPT-4o) — contain no information about metformin, feline diabetes, or veterinary drug dosages. No dosage recommendation can be drawn from these chunks, and I am not answering from prior knowledge.

Sources used: none (all retrieved chunks were checked and none addressed the question).

**[vector]**

The provided evidence does not answer this question. None of the retrieved chunks mention metformin, veterinary medicine, or dosing information for diabetic cats. The closest related content concerns human clinical data — e.g., prescription drug records (Heparin, Acetaminophen, Lorazepam, Morphine Sulfate) in [2110.08918] and a hemoglobin A1C/diabetes modeling study in [2201.03675] — but neither addresses metformin dosage in animals.

Therefore, the evidence is insufficient, and I cannot provide the recommended daily dosage of metformin for diabetic cats.

Sources examined: [2212.13138], [2110.08918], [2502.00306], [2203.15752], [2201.03675], [2301.08436], [2310.10981], [2412.15058], [1904.11280] — no relevant content found.

</details>


## QK10 — `outofcorpus`

**Q:** How does the Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 51.5 | 169 | 0.13354920000000003 | 1 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | — | — | 4.9 | 167 | 0.033329399999999995 | 0 | 是 | The evidence is insufficient to answer this question. The three retrieved chunks discuss the contextual subspace method for quantum error mitigation ( |
| `rerank` | — | — | 8.7 | 260 | 0.037946400000000005 | 0 | 是 | The evidence does not contain the answer to this question. None of the retrieved chunks mention a "Herbert-Moulton collider benchmark," nor do they de |
| `rrf` | — | — | 15.8 | 500 | 0.08299599999999999 | 0 | 是 | The evidence is insufficient to answer this question. The question references a "Herbert-Moulton collider benchmark" and quantification of "detector d |
| `vector` | — | — | 3.6 | 220 | 0.0309886 | 0 | 是 | The evidence is insufficient. The retrieved chunks concern antigenic drift in immunology (q-bio-0408016), a mode-collapse metric for perturbation pred |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

The evidence is insufficient to answer this question. The three retrieved chunks discuss the contextual subspace method for quantum error mitigation (arXiv 2303.00445), coarse-grained molecular modeling (arXiv 1911.02792), and a GPT-3 generated news article about a church split (arXiv 2005.14165). None of them mention the Herbert-Moulton collider benchmark, detector drift, or particle physics experiments.

Sources consulted (none relevant):
- arXiv 2303.00445 (chunk on contextual subspace / $S_N$ number-operator reduction)
- arXiv 1911.02792 (chunk on coarse-graining mapping)
- arXiv 2005.14165 (chunk on GPT-3 generated news text)

No fallback to prior knowledge is offered, per the output contract.

**[rerank]**

The evidence does not contain the answer to this question. None of the retrieved chunks mention a "Herbert-Moulton collider benchmark," nor do they describe a method for quantifying detector drift in particle physics experiments. The supplied chunks cover unrelated topics: antigenic drift modeling ([q-bio-0408016]), mode-collapse metrics ([2602.10156]), fault rupture motion ([2606.10843]), black-hole horizons ([gr-qc-9805045]), DFT+U methods ([2211.04977]), Trotter decomposition ([2311.00487]), qubit measurement current ([1311.2485]), and semiconductor drift current ([1712.01369]). Some chunks use the word "drift" (antigenic drift, drift current density, qubit state drift), but none relates to detector drift in particle physics. No source in this evidence answers the question, so I cannot provide an answer without resorting to prior knowledge.

Sources consulted (none sufficient): q-bio-0408016, 2602.10156, 2606.10843, gr-qc-9805045, 2211.04977, 2311.00487, 1311.2485, 1712.01369.

**[rrf]**

The evidence is insufficient to answer this question. The question references a "Herbert-Moulton collider benchmark" and quantification of "detector drift in particle physics experiments," but none of the three provided evidence chunks contain this topic or these terms.

The retrieved evidence covers unrelated subjects: [q-bio-0408016] discusses influenza vaccine effectiveness and antigenic drift of virus epitopes; [2606.10843] discusses particle motion patterns in strike-slip earthquake ruptures (seismology, not particle physics); and [2303.00445] discusses error mitigation in a quantum-computing simulation of HCl using number and spin operators. None mention a collider benchmark, detector drift, or anyone named Herbert-Moulton.

Therefore, per the contract, I state the evidence does not contain the answer and do not speculate beyond it.

Sources examined: [q-bio-0408016], [2606.10843], [2303.00445] — none relevant.

**[vector]**

The evidence is insufficient.

The retrieved chunks concern antigenic drift in immunology (q-bio-0408016), a mode-collapse metric for perturbation prediction (2602.10156), rupture-speed motion trends (2606.10843), general relativity/black holes (gr-qc-9805045), DFT+U calculations (2211.04977), Trotter decomposition error (2311.00487), qubit decoherence drift on the Bloch sphere (1311.2485), and semiconductor drift current/drift resistivity (1712.01369). None of them mention the Herbert-Moulton collider benchmark, particle-physics detectors, or any detector-drift metric.

Sources consulted: q-bio-0408016, 2602.10156, 2606.10843, gr-qc-9805045, 2211.04977, 2311.00487, 1311.2485, 1712.01369 — all irrelevant to the question. No answer can be given from the provided evidence.

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ✅ | 0 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=6.6983 · manifest=6.6983 |
| 单元数 = 题数 × 方法数 | ✅ | rows=50 vs 10×5=50 |
| provenance 完整 | ✅ | prompt_version=v4-neutral seed=0 |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*