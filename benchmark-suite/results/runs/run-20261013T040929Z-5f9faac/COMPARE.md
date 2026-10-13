# 对照实验报告 — `run-20261013T040929Z-5f9faac`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-10-13 04:27 UTC

## 方法清单

| method | 类型 | n |
|---|---|---:|
| `a2` | 项目（平台） | 10 |
| `bm25` | baseline | 10 |
| `rrf` | baseline | 10 |
| `vector` | baseline | 10 |

## 资源监控总表

| method | 时延 avg s | 时延 median s | tokens in | tokens out | 成本 $ | 成本/题 $ | 工具数 avg | CPU% peak | RSS MB peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `a2` | 78.32 | 60.5 | 704493 | 11855 | 7.9117 | 0.7912 | 7.9 | — | — |
| `bm25` | 12.13 | 7.6 | 24725 | 3799 | 0.459 | 0.0459 | 0.0 | — | — |
| `rrf` | 11.19 | 7.7 | 100204 | 2974 | 0.7793 | 0.0779 | 0.0 | — | — |
| `vector` | 9.2 | 8.6 | 99610 | 1805 | 0.7459 | 0.0746 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 诚实性双向）

| method | 检索金标命中率 | 引用金标命中率 | 正确拒答(应拒答层) | 误拒(可答层) | error 数 |
|---|---:|---:|---:|---:|---:|
| `a2` | 0.75 | 0.75 | 2/2 (1.0) | 0/8 (0.0) | 0 |
| `bm25` | 1.0 | 1.0 | 2/2 (1.0) | 6/8 (0.75) | 0 |
| `rrf` | 1.0 | 1.0 | 2/2 (1.0) | 6/8 (0.75) | 0 |
| `vector` | 1.0 | 1.0 | 2/2 (1.0) | 4/8 (0.5) | 0 |

> **口径说明**：baseline 的「检索命中」基于其真实 ranked 列表（可直接观测）；agent 轨（a/a2/b/c）的 SSE 轨迹只含工具**入参**、不含检索结果文档 id，故其检索命中由 trace ∪ 答案推断（`retrieval_basis=trace+answer`）。**agent 轨请以「引用命中率」为可靠功能信号。**

## QK01 — `single`

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**gold:** 1706.03762, 1706.03762

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✗ | ✗ | 10.9 | 348 | 0.2462252 | 0 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | ✓ | ✓ | 39.3 | 1779 | 0.114374 | 0 | 是 | The evidence only partially answers this question. Per the [1706.03762] chunk, the Transformer computes attention in a multi-head fashion: it uses h = |
| `rrf` | ✓ | ✓ | 40.9 | 1549 | 0.2803622 | 0 | 是 | Based on the provided evidence, I can answer only part of this question. **How the Transformer computes attention** (from the [1706.03762] chunk): it  |
| `vector` | ✓ | ✓ | 11.8 | 254 | 0.24183739999999998 | 0 | 是 | The evidence is insufficient to answer this question as posed. What the retrieved chunks do support: [1706.03762] states the Transformer replaced the  |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

The evidence only partially answers this question. Per the [1706.03762] chunk, the Transformer computes attention in a multi-head fashion: it uses h = 8 parallel attention heads with d_k = d_v = d_model/h = 64 each, and because of the reduced per-head dimension, the total computational cost is similar to single-head attention with full dimensionality. This attention is used in three ways: in encoder-decoder attention layers (queries come from the previous decoder layer; keys and values come from the encoder output, letting every decoder position attend over all input positions), in encoder self-attention layers (keys, values, and queries all come from the previous encoder layer's output, so each position attends to all positions in the previous layer), and in decoder self-attention layers. However, the evidence does not contain the underlying attention computation (e.g., a query-key-value formula), and it contains **no rationale for why the Transformer replaces recurrence and convolution** — no complexity, parallelization, or dependency-path argument appears in any provided chunk. That "why" portion therefore cannot be answered from the evidence.

**Sources:** [1706.03762] chunk — Section 3.2.2 (multi-head attention, h=8, d_k=d_v=64) and Section 3.2.3 "Applications of Attention in our Model". (Chunks [1810.04805] and [2503.21676] were not relevant and not used.)

**[rrf]**

Based on the provided evidence, I can answer only part of this question.

**How the Transformer computes attention** (from the [1706.03762] chunk): it uses multi-head attention with h = 8 parallel attention heads, each with reduced dimension d_k = d_v = d_model/h = 64, so the total computational cost is similar to single-head attention with full dimensionality. Attention is applied in three ways: (1) "encoder-decoder attention," where queries come from the previous decoder layer and memory keys/values come from the encoder output, allowing every decoder position to attend over all positions in the input sequence; (2) encoder self-attention, where all keys, values, and queries come from the same place — the output of the previous encoder layer — so each position attends to all positions in the previous layer; (3) decoder self-attention, which works similarly (the excerpt is truncated mid-sentence). The chunk does not include the scaled dot-product attention formula itself.

**Why it replaces recurrence and convolution**: the evidence does not contain this rationale — no provided chunk explains the motivation for replacing recurrence/convolution (e.g., parallelization or path-length arguments). The other two chunks ([2503.21676] on attention patching, [1810.04805] on BERT/SQuAD fine-tuning) do not address this question either, so I cannot answer that part from the evidence.

Sources: [1706.03762] chunk (Transformer paper, Section 3.2.3 "Applications of Attention in our Model" excerpt); [2503.21676] and [1810.04805] chunks consulted and found non-responsive.

**[vector]**

The evidence is insufficient to answer this question as posed.

What the retrieved chunks do support: [1706.03762] states the Transformer replaced the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention, and that for translation it trains significantly faster than recurrent or convolutional architectures. [2110.07844] describes the computation at a high level — a cross-attention head transforms decoder and encoder states into query, key and value vectors, computes attention weights as a normalized dot product between query and key, and outputs a weighted sum of value vectors — but it does so as background for a different architecture, not as the Transformer's own specification. [1810.04805] and [2510.13343] only reference the attention mechanism's role and versatility.

None of the chunks state the Transformer's attention formula (scaled dot-product, softmax over queries and keys), and none give a stated rationale for replacing convolution specifically — [1706.03762] gives a speed comparison, not a reason. The evidence does not answer the question.

Sources used: [1706.03762] §7 Conclusion; [2110.07844]; [1810.04805]; [2510.13343].

</details>


## QK02 — `single`

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**gold:** 1602.01876, 1602.01876

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 32.4 | 691 | 0.9307432000000001 | 4 | 否 | The retrieved document directly and explicitly answers the question. **Answer:** The Gene Ontology (GO) is a controlled vocabulary whose terms are sub |
| `bm25` | ✓ | ✓ | 6.0 | 174 | 0.030232 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention the Gene Ontology (GO) as a controlled vocabulary and describe it a |
| `rrf` | ✓ | ✓ | 6.8 | 128 | 0.23763140000000002 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved evidence ([1602.01876]) describes the Gene Ontology as a controlled vocabulary and |
| `vector` | ✓ | ✓ | 15.1 | 101 | 0.0304904 | 0 | 否 | The Gene Ontology (GO) is a controlled vocabulary of terms representing biology in a structured way, subdivided into three distinct independent ontolo |

<details><summary>逐字答案全文</summary>

**[a2]**

The retrieved document directly and explicitly answers the question.

**Answer:** The Gene Ontology (GO) is a controlled vocabulary whose terms are subdivided into three distinct ontologies representing different biological aspects: **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**. The source states they are non-redundant and share a common space of identifiers and a well-specified syntax. Content verification via `kb_doc_read` confirmed the passage verbatim in the document body (Section 2, "What is the Gene Ontology?").

Sources used:
- `生命科学与医学/genomics__1602.01876__primer-on-the-gene-ontology.md (part 1 of 2).md` — kb_id `b28f0a25-1e1d-40ad-96b8-61bd2b093a28`, chunk_index 9 (vector hit, score 0.799), content-verified by full read.
- Retrieved via `kb_search_vector` (cross-KB, top_k=10).

**[bm25]**

The evidence is insufficient to answer this question. The retrieved chunks mention the Gene Ontology (GO) as a controlled vocabulary and describe it as consisting of "the Gene Ontology itself, which models biological aspects in a structured way, and annotations" — but they never name or list the three independent ontologies (i.e., the standard biological-process, molecular-function, and cellular-component divisions) that subdivide GO. The chunk from [1602.01876] is truncated mid-sentence ("The term"), and the other two chunks ([2301.08436], [2401.06823]) are about spatial transcriptomics and interpretable deep learning, not GO's structure.

Sources used: [1602.01876] (GO primer intro), [2301.08436], [2401.06823] (both irrelevant to the question).

**[rrf]**

The evidence is insufficient to answer this question.

The retrieved evidence ([1602.01876]) describes the Gene Ontology as a controlled vocabulary and explains that the GO project consists of "the Gene Ontology itself, which models biological aspects in a structured way, and annotations," but it does not name or list the three independent ontologies that subdivide GO. The other retrieved chunks ([2301.08436], [2508.18304]) concern spatial transcriptomics and monocyte subsets, respectively, and are unrelated.

**Sources used:** none contained the answer; [1602.01876] was consulted and found insufficient.

**[vector]**

The Gene Ontology (GO) is a controlled vocabulary of terms representing biology in a structured way, subdivided into three distinct independent ontologies: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC). These ontologies are non-redundant and share a common space of identifiers and a well-specified syntax, with terms linked by relations to form a hierarchical vocabulary.

Source used: [1602.01876], "## 2. What is the Gene Ontology?"

</details>


## QK03 — `single`

**Q:** What physical mechanism does the dynamic electrical model use to explain the hysteretic J-V characteristics of perovskite solar cells?

**gold:** 1606.00335, 1606.00335

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 66.3 | 1340 | 0.9890932 | 5 | 否 | I have the mechanism from the paper's model section. Answering from retrieved evidence. **Answer:** The dynamic electrical model in the retrieved pape |
| `bm25` | ✓ | ✓ | 18.8 | 309 | 0.0370164 | 0 | 是 | The retrieved evidence is insufficient to answer this question. What the evidence does contain: chunk [1606.00335] describes a "standard dynamic elect |
| `rrf` | ✓ | ✓ | 12.8 | 187 | 0.0300396 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention perovskite solar cells and a "standard dynamic electrical model," a |
| `vector` | ✓ | ✓ | 4.5 | 115 | 0.0299054 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention that a "dynamic electrical model" investigates hysteretic effects i |

<details><summary>逐字答案全文</summary>

**[a2]**

I have the mechanism from the paper's model section. Answering from retrieved evidence.

**Answer:** The dynamic electrical model in the retrieved paper (Nemnes et al., arXiv 1606.00335) explains the hysteretic J-V behavior via a **polarization-relaxation mechanism** — effectively a polarization-dependent capacitance in the equivalent circuit. The cell is modeled as a static equivalent circuit (photocurrent source, diode, shunt and series resistances) plus a parallel capacitance C "which is here introduced by a polarization mechanism" and is generally responsible for the dynamically non-equivalent forward and reverse bias scans. The displacement current is written as I_c = A ∂D/∂t = A ε₀ ∂E/∂t + A ∂P/∂t, where the polarization P splits into a linear term (ε₀χ_l E) and a non-linear contribution P_nl arising from the charge's non-linear response to the combined light and electric field in the active medium/interfaces. By adopting a simple ansatz for this polarization relaxation (with a characteristic relaxation time scale), the model reproduces the measured hysteresis: in a forward scan part of the photocurrent charges the built-in capacitor (giving smaller current), while in the reverse scan the capacitor releases the charges (giving larger current), making the J-V curves sweep-rate dependent (hysteresis maximal at intermediate scan rates). The paper notes the microscopic origin of the non-linear polarization is beyond its scope, and that competing explanations (ferroelectricity, ion migration plus charge trapping) exist.

**Sources used:**
- `工程与能源/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs (part 1 of 2).md` — Abstract, §1 Introduction, §2.1 Standard dynamic electrical model, §2.2 Modeling the capacitor current (chunk_index 3, 8, 9, 13, 16; judge segments part-0/segment-0000…0004)
- `工程与能源/materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs (part 2 of 2).md` — §4 Conclusions (chunk_index 15)
- Verification: `kb_laya_judge` (criterion=evidence, threshold 0.5) — 20/20 segments survived across both documents.

**[bm25]**

The retrieved evidence is insufficient to answer this question.

What the evidence does contain: chunk [1606.00335] describes a "standard dynamic electrical model" of a solar cell as an equivalent circuit — current source (photocurrent $I_{ph}$), diode with ideality factor $n$, shunt resistance $R_{sh}$, series resistance $R_s$, plus a parallel capacitance $C$ — and its Section 3 is stated to describe hysteretic effects "influenced by solar cell preconditioning and bias scan rate," with analysis "focused on the variation of the polarization in time, assuming a certain relaxation time scale."

However, the excerpt cuts off mid-sentence at the definition of the capacitance ("which is gen..."), and no chunk in the evidence explicitly states the physical mechanism (e.g., ion migration, ferroelectric polarization, or trap-related charge accumulation) used to explain the hysteresis. The chunks [1712.01369] and [2607.03098] concern perovskite/GeSe bilayer efficiency and energy-storage-model simplifications respectively, and say nothing about the hysteresis mechanism.

The only partial hint is the phrase "variation of the polarization in time," but the evidence never identifies what is polarized or by what mechanism, so I cannot state the mechanism without falling back on prior knowledge.

Sources used: chunk [1606.00335] (partial — model description only); chunks [1712.01369], [2607.03098] (not relevant to the question).

**[rrf]**

The evidence is insufficient to answer this question.

The retrieved chunks mention perovskite solar cells and a "standard dynamic electrical model," and one chunk notes that the analysis concerns hysteretic J-V effects influenced by preconditioning and bias scan rate, focused on "the variation of the polarization in time, assuming a certain relaxation time scale." However, the retrieved text cuts off mid-sentence at the description of the equivalent circuit (the parallel capacitance C) before explaining any mechanism, and the other chunks concern a perovskite/GeSe bilayer cell's J-V parameters and energy-storage dynamic models — neither of which addresses the mechanism behind hysteresis. No retrieved source states the physical mechanism (e.g., ion migration, trap states, or ferroelectric polarization) responsible for the hysteretic J-V behavior.

Sources used: [1606.00335], [1712.01369], [2607.03098] (fragments only).

**[vector]**

The evidence is insufficient to answer this question. The retrieved chunks mention that a "dynamic electrical model" investigates hysteretic effects in perovskite solar cell J-V characteristics, but the abstract excerpt cuts off before describing the physical mechanism — it names only a "simple ansatz for the polarization relaxation" without explaining the underlying mechanism itself. The second chunk [1712.01369] concerns bilayer solar cell J-V curves and does not address the model's mechanism at all.

Sources used: [1606.00335] (abstract, truncated), [1712.01369].

</details>


## QK04 — `single`

**Q:** Using only what kind of information, and reaching what accuracy, does the wav2vec 2.0 approach detect within-sentence prosodic boundaries on Czech broadcast news?

**gold:** 2209.15032, 2209.15032

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 119.5 | 1035 | 0.9739937999999999 | 7 | 否 | The retrieval found an exact match: the paper "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" (arXiv 2209.15032, Kunešová & Rezáčková,  |
| `bm25` | ✓ | ✓ | 16.5 | 591 | 0.08504400000000001 | 0 | 否 | According to the abstract of arXiv paper 2209.15032 ("Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0"), the wav2vec 2.0 approach detects |
| `rrf` | ✓ | ✓ | 6.5 | 184 | 0.034784999999999996 | 0 | 否 | The evidence answers this. According to the paper's abstract, the wav2vec 2.0 framework detects prosodic boundaries in speech **using only acoustic in |
| `vector` | ✓ | ✓ | 13.0 | 413 | 0.247954 | 0 | 否 | According to the evidence, the wav2vec 2.0 approach detects these boundaries **using only acoustic information** from the speech signal — no transcrip |

<details><summary>逐字答案全文</summary>

**[a2]**

The retrieval found an exact match: the paper "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" (arXiv 2209.15032, Kunešová & Rezáčková, Univ. of West Bohemia), stored in KB `b1199132-e4d4-4305-8c2e-82dc1753b0ba` as two parts under `计算机与人工智能/`.

**Answer:** The approach uses **only acoustic information** — a Czech-pretrained wav2vec 2.0 base model ("ClTRUS") fine-tuned with `Wav2Vec2ForAudioFrameClassification` on the News-Reading Speech (NRS) corpus of Czech Radio broadcast-news bulletins; it requires **no text annotation and no knowledge of word boundaries** (word-boundary alignment within 100 ms was used for evaluation only), making it audio-modality-only with no handcrafted feature selection. On **within-sentence prosodic boundaries** it reaches **94% accuracy and 83% F1**, rising to **95% accuracy / 89% F1 on all prosodic boundaries**, outperforming a text-based T5 predictor; whole-file frame-level results are Acc 94.87 / F1 88.56 (prosodic boundaries only). Worth noting: the paper's headline is 94%/83% for within-sentence boundaries, while Table 2/3 leave-one-out "all-data" rows print lower numbers (F1 77.40 wav2vec2 vs 82.73 T5 at 0.5 threshold), so the "outperforming the text-based approach" claim is strongest on the abstract-level within-sentence figures.

**Sources used:**
- `计算机与人工智能/speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u (part 1 of 2).md` — chunks 0–3, 32, 39, 40, 46, 56, 63 (KB `b1199132-e4d4-4305-8c2e-82dc1753b0ba`, collection `kb_b1199132-e4d4-4305-8c2e-82dc1753b0ba`)
- `计算机与人工智能/speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u (part 2 of 2).md` (reference list only)

Verified via `kb_search_two_stage`, `kb_search_vector` (top hit, score 0.733), and `kb_laya_judge` (11/12 segments survived, top segment 0.8972).

**[bm25]**

According to the abstract of arXiv paper 2209.15032 ("Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0"), the wav2vec 2.0 approach detects prosodic boundaries using **only acoustic information** from the speech signal — no transcripts. Despite using a relatively small amount of labeled data, it reaches an **accuracy of 94%** (with an F1 measure of 83%) on within-sentence prosodic boundaries in the Czech broadcast news recordings, which were labeled by phonetic experts. This outperformed the existing text-based predictor that relied on transcripts.

Source: chunk `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u（第 1/2 部分）`, section "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0", Abstract ([2209.15032]).

**[rrf]**

The evidence answers this. According to the paper's abstract, the wav2vec 2.0 framework detects prosodic boundaries in speech **using only acoustic information** (not text). Tested on recordings of Czech broadcast news labeled by phonetic experts, the model achieved an **accuracy of 94%** and an **F1 measure of 83%** on within-sentence prosodic boundaries (or 95% and 89% on all prosodic boundaries), outperforming the text-based approach despite using a relatively small amount of labeled data.

Source used: `[2209.15032] speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (chunk 1/2, abstract section, "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" by Kunešová and Rezáčková).

**[vector]**

According to the evidence, the wav2vec 2.0 approach detects these boundaries **using only acoustic information** from the speech signal — no transcripts. Tested on Czech broadcast news recordings labeled by phonetic experts, it reaches an **accuracy of 94%** (with an F1 measure of 83%) on within-sentence prosodic boundaries, despite using a relatively small amount of labeled data.

Source: evidence chunk from arXiv abstract [2209.15032].

</details>


## QK05 — `single`

**Q:** In the trap-cropping optimization framework, roughly what share of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant?

**gold:** 2508.05896, 2508.05896

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 283.9 | 3429 | 3.1821518 | 37 | 否 | Retrieved and verified. The evidence is consistent across the retrieved chunks and the Laya content-verification pass. **Answer:** In this framework,  |
| `bm25` | ✓ | ✓ | 4.8 | 105 | 0.027704000000000003 | 0 | 否 | The evidence answers this. When trap plants are 5 and 25 times more attractive than the cash plant, approximately 7–10% of the field should be allocat |
| `rrf` | ✓ | ✓ | 8.5 | 194 | 0.0347674 | 0 | 否 | The evidence answers this directly. Roughly 7–10% of the field should be allocated to trap plants when trap plants are 5 to 25 times more attractive t |
| `vector` | ✓ | ✓ | 3.5 | 81 | 0.0275804 | 0 | 否 | The evidence answers this directly. When trap plants are 5 and 25 times more attractive than the cash plant, roughly 7–10% of the field should be allo |

<details><summary>逐字答案全文</summary>

**[a2]**

Retrieved and verified. The evidence is consistent across the retrieved chunks and the Laya content-verification pass.

**Answer:** In this framework, when trap plants are 5 to 25 times more attractive than the cash plant, roughly **7–10% of the field** should be allocated to trap plants (the rest to the cash crop). The paper states it directly: "For more attractive trap plants, 5 and 25 times more attractive, approximately 7–10% of the field should be allocated to trap plants." Related summary sentences frame the general range as "5–20% of the field" for intermediately attractive trap plants and "more than 10% of the landscape" for 5–20× attractiveness. Note a nearby baseline result differs: at 49× attractiveness (the eggplant/poinsettia baseline), only ~7.1–8.5% goes to trap plants, and the optimal trap-plant area is actually *larger* at intermediate 5–25× attractiveness than at 49×, because intermediate attractiveness diverts pests but less efficiently.

Sources used:
- `生命科学与医学/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz (part 2 of 3).md` (kb_id `b28f0a25-1e1d-40ad-96b8-61bd2b093a28`; chunks 15, 17, 19, 27 — including the "7–10%" sentence)
- `生命科学与医学/agriculture__2508.05896__optimal-trap-cropping-investments-to-maximiz (part 1 of 3).md` (same kb_id; chunks 2, 6, 11, 20, 51)

Verification: `kb_laya_judge` (real Laya engine, criterion=instance, threshold=0.5) scored 18 candidate segments and returned status "ok" with survivors containing the quoted sentences.

**[bm25]**

The evidence answers this. When trap plants are 5 and 25 times more attractive than the cash plant, approximately 7–10% of the field should be allocated to trap plants ([2508.05896], Figure 3 caption). The same source states that at five times attractiveness it is "optimal to devote roughly ten percent of the land to the trap crop" (Figure 3b).

Source used: chunk [2508.05896] (trap-cropping optimization, Figure 3).

**[rrf]**

The evidence answers this directly.

Roughly 7–10% of the field should be allocated to trap plants when trap plants are 5 to 25 times more attractive than the cash plant. For a trap plant only twice as attractive as the cash plant, trap cropping is ineffective and the grower should plant only cash plants; but for more attractive trap plants (5× and 25×), approximately 7–10% of the field is optimal. The text notes that at five times attractiveness it is optimal to devote roughly ten percent of the land to the trap crop.

Sources:
- [2508.05896] — Figure 3 caption (chunk: "Figure 3: Grower yield as a function of the proportion of cash plants…") and the following paragraph on five-times attractiveness.

The other retrieved documents ([1609.00415], [1512.08067]) are unrelated to the trap-cropping optimization framework.

**[vector]**

The evidence answers this directly.

When trap plants are 5 and 25 times more attractive than the cash plant, roughly 7–10% of the field should be allocated to trap plants. At an attractiveness of five times, about ten percent of the land is optimal.

Sources used:
- [2508.05896] (retrieved evidence chunks quoting the trap-cropping allocation result)

</details>


## QK06 — `single`

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**gold:** 1503.07557, 1503.07557

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 44.5 | 1252 | 0.3035418 | 6 | 否 | **Answer** The retrieved evidence (O'Gorman, *Precipitation extremes under climate change*) identifies the **thermodynamic contribution — the increase |
| `bm25` | ✓ | ✓ | 6.6 | 188 | 0.0339178 | 0 | 是 | The evidence is insufficient to answer the question as posed. The first source ([1503.07557], O'Gorman, "Precipitation extremes under climate change") |
| `rrf` | ✓ | ✓ | 6.8 | 151 | 0.0318646 | 0 | 是 | The evidence is insufficient to name the physical factor that *primarily* controls the response. [1503.07557] states only that "several physical contr |
| `vector` | ✓ | ✓ | 8.8 | 224 | 0.031753 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks explicitly state that the response of precipitation extremes to climate cha |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer**

The retrieved evidence (O'Gorman, *Precipitation extremes under climate change*) identifies the **thermodynamic contribution — the increase in saturation specific humidity / saturation vapor pressure with warming, i.e. Clausius–Clapeyron scaling — as the primary physical control** on the response of precipitation extremes. The paper decomposes extreme precipitation, via P ≈ −ε{ω·S(T,p)}, into a dynamical contribution (changes in ω), a thermodynamic contribution (changes in S, temperature-dependent), and a microphysical one (changes in precipitation efficiency ε). It states the thermodynamic contribution "is robust and well understood" and "always gives an intensification with warming," and that in idealized radiative-convective-equilibrium and extratropical CMIP simulations the extremes increase "at close to the thermodynamic rate… close to Clausius-Clapeyron scaling" (6–7 % K⁻¹). Dynamical and microphysical/precipitation-efficiency contributions matter in some regimes (notably convection, tropics, subdaily durations below ~295 K), but their theoretical understanding "is still being developed." The Laya judge confirmed these segments as surviving evidence (per-segment scores 0.63–0.87, 17/19 segments across both parts).

Sources used:
- `自然科学与地球科学/climate-science__1503.07557__precipitation-extremes-under-climate-change.md (part 1 of 3).md` — Abstract, §1, §3 (Eq. 1 and thermodynamic/Clausius–Clapeyron discussion), chunk_index 1, 2, 9, 23
- `自然科学与地球科学/climate-science__1503.07557__precipitation-extremes-under-climate-change.md (part 2 of 3).md` — §7, §8 (thermodynamic contribution "always gives an intensification"), segment-0002 verdict score 0.873

**[bm25]**

The evidence is insufficient to answer the question as posed. The first source ([1503.07557], O'Gorman, "Precipitation extremes under climate change") states that several physical contributions govern the response — thermodynamic, microphysical, and dynamical — and that no single factor "primarily" controls it: the thermodynamic contribution is described as robust and well understood, while theoretical understanding of the microphysical and dynamical contributions is still being developed. The remaining two sources ([2409.13934] and [2409.09639]) concern climate-change signal emulation and precipitation dataset construction, respectively, and do not address the controlling physical factors.

Sources used: `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (part 1/3); [2409.13934]; [2409.09639] (checked and found not to answer the question).

**[rrf]**

The evidence is insufficient to name the physical factor that *primarily* controls the response.

[1503.07557] states only that "several physical contributions govern the response," that the thermodynamic contribution is "robust and well understood," and that theoretical understanding of the microphysical and dynamical contributions "is still being developed." It does not identify any one of these as the primary control. The other two chunks (2007.10574, 2409.13934) concern MJO modulation in Indonesia and emulator skill evaluation, respectively, and do not address the question.

Sources used: `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (part 1/3).

**[vector]**

The evidence is insufficient to answer this question.

The retrieved chunks explicitly state that the response of precipitation extremes to climate change is "considered using results from theory, modeling, and observations, with a focus on the physical factors that control the response" ([1503.07557] O'Gorman, "Precipitation extremes under climate change"), but the text cuts off mid-word at the very point where the answer would appear ("the sensitivity of precipitation extremes to warming remains uncert—"). The abstract never names the controlling physical factor. The second chunk ([2007.10574], "Dynamical Links between Precipitation Extremes and MJO") discusses vertical moisture flux convergence and vertical moisture advection for MJO-induced extremes, but that is specific to MJO dynamics, not a statement of what *primarily* controls the general response to climate change.

Sources used:
- [1503.07557] Precipitation extremes under climate change (O'Gorman) — abstract only, truncated
- [2007.10574] Dynamical Links between Precipitation Extremes and MJO — section 3.2

</details>


## QK07 — `distractor`

**Q:** What is MameLoshnLM and what parameter scale does it have?

**gold:** 2608.05850, 2608.05850

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✗ | ✗ | 13.9 | 480 | 0.250051 | 0 | 否 | KB_TOOLS_NOT_READY |
| `bm25` | ✓ | ✓ | 4.8 | 126 | 0.03341499999999999 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks mention "MAMELOSHNLM" only in the context of statistical testing (McNemar's |
| `rrf` | ✓ | ✓ | 5.1 | 166 | 0.030368 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks do not describe what MameLoshnLM is, nor do they state its parameter scale. |
| `vector` | ✓ | ✓ | 16.9 | 228 | 0.0339704 | 0 | 是 | The evidence is insufficient to fully answer this question. The retrieved evidence describes **MAMELOSHNLM** as "the first open-source large language  |

<details><summary>逐字答案全文</summary>

**[a2]**

KB_TOOLS_NOT_READY

**[bm25]**

The evidence is insufficient to answer this question. The retrieved chunks mention "MAMELOSHNLM" only in the context of statistical testing (McNemar's exact test) and a lemmatization comparison against Llama 3.1 8B (source: [2608.05850]), but they do not define what MameLoshnLM is, nor do they state its parameter scale. No other retrieved source ([2212.13138], [2005.14165]) discusses MameLoshnLM. I therefore cannot answer from the provided evidence and will not rely on prior knowledge.

**[rrf]**

The evidence is insufficient to answer this question.

The retrieved chunks do not describe what MameLoshnLM is, nor do they state its parameter scale. The first source ([2608.05850], §E.7) only mentions "MAMELOSHNLM" incidentally — as one of two models compared on lemmatization using McNemar's exact test against Llama 3.1 8B — without defining the model or giving its size. The other two sources ([2212.13138], [2402.11690]) are unrelated (medical QA and visual dialogue) and say nothing about it.

Sources used: [2608.05850] (chunk containing "## E.7 Statistical Testing"); [2212.13138]; [2402.11690].

**[vector]**

The evidence is insufficient to fully answer this question.

The retrieved evidence describes **MAMELOSHNLM** as "the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2," named after the Yiddish term "Mame-Loshn" ("mother tongue"), and reported to outperform strong baselines of similar scale across Yiddish evaluation benchmarks (source: [2608.05850], §5 "MAMELOSHNLM").

However, the evidence does **not** state the parameter scale (model size) of MameLoshnLM. The passage's "Training Details" is truncated mid-sentence ("produced by continued pretrain..."). Parameter-scale figures in the evidence (135M, 360M, 1.7B for SmolLM; 540B for PaLM) belong to different models in other documents and do not apply.

**Sources used:**
- [2608.05850], §5 "MAMELOSHNLM"

No parameter scale for MameLoshnLM is recoverable from this evidence.

</details>


## QK08 — `crosskb`

**Q:** Beyond which percentile of precipitation did the GAN clearly outperform the deterministic baseline in capturing the climate-change wetting signal?

**gold:** 2409.13934, 2409.13934

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | ✓ | ✓ | 63.3 | 757 | 0.2722112 | 4 | 否 | **Answer:** The 95th percentile. The source states that the historically trained GAN and the deterministic baseline "have relatively similar signals u |
| `bm25` | ✓ | ✓ | 8.6 | 210 | 0.030551000000000002 | 0 | 是 | The evidence is insufficient to answer this question. What the retrieved chunks do support: the GAN trained on future and historical periods captures  |
| `rrf` | ✓ | ✓ | 5.7 | 178 | 0.034364000000000006 | 0 | 是 | The evidence does not answer this question. The retrieved chunks compare the GAN against deterministic baselines only for **one specific threshold — t |
| `vector` | ✓ | ✓ | 3.3 | 56 | 0.0265354 | 0 | 否 | The evidence answers this: beyond the **95th percentile** of precipitation, the GAN substantially better captures the wetting signal compared to the d |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer:** The 95th percentile. The source states that the historically trained GAN and the deterministic baseline "have relatively similar signals up to the 95th percentile of precipitation. Beyond the 95th percentile, the GAN substantially better captures the wetting signal," though both still underestimate its magnitude relative to CCAM truth.

**Sources used:**
- `自然科学与地球科学/climate-science__2409.13934__on-the-extrapolation-of-generative-adversari (part 2 of 3).md` (Section 3.2 "Extreme Precipitation Climate Change Signal"), chunk_index 6 — retrieved via `kb_search_vector` and verified by full `kb_doc_read`.
- Corroborating chunks from the same KB (part 1 of 3, chunk 58): extreme precipitation at the 99.5th percentile shows GANs with smaller climate-change-signal error than the deterministic baseline.

**[bm25]**

The evidence is insufficient to answer this question.

What the retrieved chunks do support: the GAN trained on future and historical periods captures ~97% of the average future increase in the **99.5th percentile** of precipitation, while the two deterministic baselines capture only 63–65% (source: [2409.13934]). The GAN trained on historical simulations captures ~77%.

However, no retrieved chunk states the *threshold percentile* above which the GAN begins to clearly outperform the deterministic baselines. The evidence names 99.5th percentile as the metric evaluated, but reports no comparison across multiple percentiles from which such a threshold could be derived.

Sources used: [2409.13934] (chunk containing the 97% / 77% / 63–65% figures); [2409.09639], [2007.10574] were retrieved but contain nothing relevant to the question.

No answer can be given from this evidence without relying on prior knowledge, so I stop here.

**[rrf]**

The evidence does not answer this question. The retrieved chunks compare the GAN against deterministic baselines only for **one specific threshold — the 99.5th percentile of precipitation** — reporting that the GAN captures ~97% (future-trained) or ~77% (historical-trained) of the future increase versus only 63–65% for the deterministic baselines. No other percentile is mentioned, so the evidence does not establish a percentile threshold *beyond which* the GAN clearly outperforms the baselines; it only shows that at the 99.5th percentile the GAN does outperform them.

Sources used: [2409.13934] (GAN vs. deterministic baseline statistics, Figure 2 caption). Chunks [2007.10574] and [2409.09639] were retrieved but are irrelevant to the comparison and were not used.

**[vector]**

The evidence answers this: beyond the **95th percentile** of precipitation, the GAN substantially better captures the wetting signal compared to the deterministic baselines (though both still underestimate its magnitude relative to CCAM).

Source used: chunk from [2409.13934].

</details>


## QK09 — `unanswerable`

**Q:** What is the recommended daily dosage of metformin for diabetic cats?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 90.9 | 1291 | 0.44942279999999996 | 8 | 是 | **Answer: The retrieved evidence does not answer this question.** I searched all 21 knowledge bases in this platform (vector search, BM25→vector two-s |
| `bm25` | — | — | 10.7 | 163 | 0.0333554 | 0 | 是 | The evidence is insufficient to answer this question. The three retrieved chunks concern unrelated topics — ICU length-of-stay and mortality predictio |
| `rrf` | — | — | 9.4 | 102 | 0.032172400000000004 | 0 | 是 | The evidence is insufficient. The three retrieved chunks are about unrelated topics — qualifying-exam questions (Hardy-Weinberg genetics, pharyngeal a |
| `vector` | — | — | 6.8 | 107 | 0.0385144 | 0 | 是 | The evidence is insufficient. None of the retrieved chunks address the recommended daily dosage of metformin for diabetic cats. The only diabetes-rela |

<details><summary>逐字答案全文</summary>

**[a2]**

**Answer: The retrieved evidence does not answer this question.**

I searched all 21 knowledge bases in this platform (vector search, BM25→vector two-stage search, metadata search) for feline metformin dosage, and also verified the only superficially related passages with the content judge. Findings:

- No document in the corpus addresses cats, feline diabetes, or veterinary metformin dosing. The 21 KBs cover computer science/AI, natural/earth sciences, life sciences & medicine, engineering/energy, economics, industrial knowledge, and demo/test corpora — none veterinary.
- The top hits were false positives: the "临床医学" LLM-benchmark papers (`clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md`, `clinical-medicine__2201.03675__continuous-time-probabilistic-models-for-lon`) contain human clinical quiz items and diabetes/A1C modeling, never metformin in cats.
- `kb_laya_judge` scored all 23 candidate segments from those two documents against "recommended daily dosage of metformin for diabetic cats": **0 survivors**, engine verdict — the material is not relevant.

Since no retrieved evidence supports an answer, I am stopping here rather than answering from prior knowledge, per the output contract.

Sources actually used (all negative for the question): `生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md (part 6/7 of 8)`, `生命科学与医学/clinical-medicine__2201.03675__continuous-time-probabilistic-models-for-lon (part 1 of 3)`, plus full `kb_list` catalog review.

**[bm25]**

The evidence is insufficient to answer this question.

The three retrieved chunks concern unrelated topics — ICU length-of-stay and mortality prediction from clinical notes ([2110.08918]), a global precipitation dataset built with machine-learning methods ([2409.09639]), and interactive image segmentation evaluation with MultiverSeg ([2412.15058]). None of them discusses metformin, feline diabetes, or veterinary drug dosages. No source among the retrieved evidence addresses the question, so I cannot provide an answer without falling back on outside knowledge.

Sources used: [2110.08918] (chunk on ICU LOS/mortality prediction); [2409.09639] (chunk on GPC/m precipitation dataset); [2412.15058] (chunk on MultiverSeg Experiment 1 setup).

**[rrf]**

The evidence is insufficient.

The three retrieved chunks are about unrelated topics — qualifying-exam questions (Hardy-Weinberg genetics, pharyngeal arches), ICU length-of-stay and mortality prediction from clinical notes, and image segmentation with MultiverSeg — and none of them discusses metformin, feline diabetes, or any veterinary dosage.

Sources retrieved (none answering the question): `[2212.13138]`, `[2110.08918]`, `[2412.15058]`.

**[vector]**

The evidence is insufficient.

None of the retrieved chunks address the recommended daily dosage of metformin for diabetic cats. The only diabetes-related evidence ([2201.03675] §3.2 Diabetes) discusses hemoglobin A1C thresholds and 250.XX diagnosis codes for a human cohort — it does not mention metformin, cats, or any dosage. The other chunks are unrelated (biomedical QA leaderboards, drug/NDC tables, medical imaging datasets, sequencing data). I cannot answer this from the provided evidence.

</details>


## QK10 — `outofcorpus`

**Q:** How does the Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `a2` | — | — | 57.6 | 1232 | 0.31424420000000003 | 8 | 是 | All retrieval paths return off-topic results (seismology, quantum benchmarking, materials drift current, finance) and no hits for "Herbert-Moulton" or |
| `bm25` | — | — | 5.2 | 154 | 0.033352 | 0 | 是 | The evidence is insufficient to answer this question. None of the three retrieved chunks mention the Herbert-Moulton collider benchmark or any method  |
| `rrf` | — | — | 9.4 | 135 | 0.0329704 | 0 | 是 | The evidence is insufficient. The three retrieved chunks concern unrelated topics: coarse-grained molecular dynamics mapping ([1911.02792]), particle- |
| `vector` | — | — | 8.3 | 226 | 0.037314400000000005 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunks are unrelated to the Herbert-Moulton collider benchmark or to any method fo |

<details><summary>逐字答案全文</summary>

**[a2]**

All retrieval paths return off-topic results (seismology, quantum benchmarking, materials drift current, finance) and no hits for "Herbert-Moulton" or for a collider/particle-physics detector-drift benchmark. Reporting the evidence gap.

**The retrieved evidence does not answer this question.** I ran four retrieval paths this session — `kb_search_vector` (two query variants), `kb_search_two_stage`, `kb_search` (metadata), `kb_graph_search`, plus `kb_search_stats` — over a corpus of ~24 vector collections / 20K+ chunks. `kb_search` for the literal string "Herbert-Moulton" returned 0 hits, and `kb_graph_search` for "collider" returned 0 documents. Semantic hits clustered at only 0.51–0.56 cosine (weak) on unrelated topics: seismology rupture-speed benchmark chunks (`自然科学与地球科学/seismology__2606.10843__...`), NISQ quantum-error-mitigation benchmarking (`自然科学与地球科学/quantum-physics__2303.00445__...`), a semiconductor "drift current" passage (`工程与能源/materials__1712.01369__...`), and a Chinese industrial sensor-diagnosis smoke-test report (`aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md`). None concerns a collider benchmark, detector drift, or particle physics. I did not verify any candidate through `kb_laya_judge`, because no candidate was plausibly on-topic to justify a verification call.

**Sources consulted (none answer the question):** `kb_search_vector` results — seismology__2606.10843, quantum-physics__2303.00445, materials__1712.01369, aw-industrial/【冒烟测试】工业诊断报告; `kb_search` "Herbert-Moulton" → 0 hits; `kb_graph_search` "collider" → 0 docs; `kb_search_stats` → 24 collections.

I cannot answer how a "Herbert-Moulton collider benchmark" quantifies detector drift from this knowledge base, and per the output contract I will not fall back on prior knowledge. The term does not appear to be present in the indexed corpus.

**[bm25]**

The evidence is insufficient to answer this question. None of the three retrieved chunks mention the Herbert-Moulton collider benchmark or any method for quantifying detector drift in particle physics experiments. The retrieved passages concern unrelated topics: a contextual-subspace error-mitigation operator in a 3-qubit HCl quantum simulation ([2303.00445]), coarse-grained molecular models for protein systems ([1911.02792]), and a GPT-3-generated news article about a church denomination split ([2005.14165]). I cannot answer from prior knowledge, so I am stopping here rather than speculating.

Sources used: [2303.00445], [1911.02792], [2005.14165] (all retrieved chunks examined and found non-responsive).

**[rrf]**

The evidence is insufficient.

The three retrieved chunks concern unrelated topics: coarse-grained molecular dynamics mapping ([1911.02792]), particle-motion patterns from strike-slip earthquake rupture modeling ([2606.10843]), and gravitational-wave interferometer response functions ([0706.3294], which mentions a beam-splitter but only in the context of GW tidal forces, not collider detectors). None of them discusses the Herbert-Moulton collider benchmark, detector drift, or particle physics collider experiments.

Sources retrieved (none answering the question):
- [1911.02792]
- [2606.10843]
- [0706.3294]

**[vector]**

The evidence is insufficient to answer this question.

The retrieved chunks are unrelated to the Herbert-Moulton collider benchmark or to any method for quantifying detector drift in particle physics. They cover the Kullback-Leibler divergence and Boltzmann generation (1911.02792), a detector-pattern amplitude expression (0706.3294), strike-slip rupture modeling (2606.10843), event-horizon coordinates in Reissner-Nordström spacetime (gr-qc-9805045), a semiconductor drift-resistivity formula (1712.01369), microlensing parallax (2304.12442), and an industrial diagnostic smoke-test report. None mention the Herbert-Moulton benchmark, detector drift quantification, or a relevant measurement methodology.

Sources used: 1911.02792, 0706.3294, 2606.10843, gr-qc-9805045, 1712.01369, 2304.12442, and the 【冒烟测试】 industrial diagnostic report chunk. I cannot answer from prior knowledge per the experiment constraints.

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ✅ | 0 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=9.8959 · manifest=9.8958 |
| 单元数 = 题数 × 方法数 | ✅ | rows=40 vs 10×4=40 |
| provenance 完整 | ✅ | prompt_version=v4-neutral seed=0 |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*