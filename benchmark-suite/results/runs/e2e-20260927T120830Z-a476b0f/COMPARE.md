# 对照实验报告 — `e2e-20260927T120830Z-a476b0f`

同一问题集上，**项目（平台轨）** 与 **baseline** 逐题并列对照 + 资源监控。
生成时间 2026-09-27 15:24 UTC

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
| `bm25` | 9.84 | 8.2 | 382026 | 13772 | 2.2544 | 0.2254 | 0.0 | — | — |
| `mode_A` | 37.86 | 38.5 | 384083 | 9571 | 2.1597 | 0.216 | 0.0 | — | — |
| `mode_B` | 17.74 | 12.6 | 375050 | 6426 | 2.0359 | 0.2036 | 0.0 | — | — |
| `mode_C` | 368.33 | 40.3 | 349215 | 6879 | 1.9181 | 0.1918 | 0.0 | — | — |
| `rerank` | 14.66 | 13.2 | 378015 | 9560 | 2.1291 | 0.2129 | 0.0 | — | — |
| `rrf` | 9.83 | 8.7 | 382236 | 12914 | 2.234 | 0.2234 | 0.0 | — | — |
| `vector` | 9.03 | 7.1 | 378112 | 12056 | 2.192 | 0.2192 | 0.0 | — | — |

## 功能验证（检索命中 / 引用命中 / 诚实性双向）

| method | 检索金标命中率 | 引用金标命中率 | 正确拒答(应拒答层) | 误拒(可答层) | error 数 |
|---|---:|---:|---:|---:|---:|
| `bm25` | 1.0 | 1.0 | 2/2 (1.0) | 5/8 (0.625) | 0 |
| `mode_A` | 1.0 | 0.75 | 2/2 (1.0) | 7/8 (0.875) | 0 |
| `mode_B` | 0.0 | 0.0 | 2/2 (1.0) | 8/8 (1.0) | 0 |
| `mode_C` | 0.625 | 0.25 | 1/2 (0.5) | 8/8 (1.0) | 1 |
| `rerank` | 1.0 | 1.0 | 2/2 (1.0) | 3/8 (0.375) | 0 |
| `rrf` | 1.0 | 1.0 | 2/2 (1.0) | 5/8 (0.625) | 0 |
| `vector` | 1.0 | 1.0 | 2/2 (1.0) | 2/8 (0.25) | 0 |

> **口径说明**：baseline 的「检索命中」基于其真实 ranked 列表（可直接观测）；agent 轨（a/a2/b/c）的 SSE 轨迹只含工具**入参**、不含检索结果文档 id，故其检索命中由 trace ∪ 答案推断（`retrieval_basis=trace+answer`）。**agent 轨请以「引用命中率」为可靠功能信号。**

## QK01 — `single`

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**gold:** 1706.03762, 1706.03762

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 9.0 | 1198 | 0.22115 | 0 | 是 | The evidence shows the Transformer computes attention through multi-head attention: it uses h = 8 parallel attention layers, or heads, with each head  |
| `mode_A` | ✓ | ✓ | 42.4 | 1146 | 0.22091 | 0 | 是 | **Answer: The provided evidence is insufficient.** The evidence does contain two fragments of "Attention Is All You Need," but both are truncated at t |
| `mode_B` | ✗ | ✗ | 11.1 | 246 | 0.19315999999999997 | 0 | 是 | The evidence provided contains no retrieved content — it is explicitly empty ("no evidence retrieved"). I therefore cannot answer how the Transformer  |
| `mode_C` | ✓ | ✓ | 39.5 | 543 | 0.20617 | 0 | 是 | The evidence is insufficient to answer this question. The only relevant excerpt is the opening of "Attention Is All You Need," and it contains just th |
| `rerank` | ✓ | ✓ | 19.6 | 1619 | 0.23011500000000001 | 0 | 是 | **Answer (from the provided evidence only):** According to [2110.07844], the attention head transforms the j-th decoder state and i-th encoder state i |
| `rrf` | ✓ | ✓ | 16.0 | 2592 | 0.256 | 0 | 是 | **Answer:** The evidence only partially addresses this question. From [1706.03762], the Transformer employs h = 8 parallel attention heads with d_k =  |
| `vector` | ✓ | ✓ | 9.7 | 1436 | 0.22551499999999997 | 0 | 是 | **Answer (evidence-bounded):** The evidence explains attention computation only partially: [2110.07844] describes a cross-attention head that transfor |

<details><summary>逐字答案全文</summary>

**[bm25]**

The evidence shows the Transformer computes attention through multi-head attention: it uses h = 8 parallel attention layers, or heads, with each head set to d_k = d_v = d_model/h = 64, and because of the reduced per-head dimension the total computational cost stays similar to single-head attention at full dimensionality ([1706.03762], §3.2.2 excerpt). The same excerpt lists three applications: encoder–decoder attention, where queries come from the previous decoder layer while keys and values come from the encoder output; encoder self-attention, where queries, keys, and values all come from the same previous-layer output; and decoder self-attention ([1706.03762], §3.2.3 excerpt). However, the retrieved evidence does not contain the rationale for replacing recurrence and convolution — nothing on sequential computation, path length, or parallelization appears in these excerpts. The other excerpts are off-point for that half of the question: [1810.04805] covers BERT question-answering span prediction with start/end vectors, and [2503.21676] covers attention patching via a twin architecture. I therefore cannot answer why attention replaces recurrence and convolution from the evidence provided; that part is insufficient.

Sources used: [1706.03762] §3.2.2 and §3.2.3 excerpts; [1810.04805] excerpt (checked, not applicable); [2503.21676] excerpt (checked, not applicable).

**[mode_A]**

**Answer: The provided evidence is insufficient.**

The evidence does contain two fragments of "Attention Is All You Need," but both are truncated at the title page/author block and provide no content on how the Transformer computes attention, nor any discussion of replacing recurrence or convolution. None of the other retrieved passages (stock-market MARL, clinical drug representations, global RAG benchmark, molecular simulation) address the question either. Since the contract forbids falling back on prior knowledge, I cannot answer from memory — answering would require the paper's sections on scaled dot-product/multi-head attention and its motivation for dropping recurrence and convolution, which were not retrieved.

Sources reviewed (neither answers the question):
- `artificial-intelligence__1706.03762__attention-is-all-you-need.md.md` (Part 1/2) — title/author header only
- `Attention Is All You Need` fragment embedded in the evidence — title/author header only (duplicate)

**[mode_B]**

The evidence provided contains no retrieved content — it is explicitly empty ("no evidence retrieved"). I therefore cannot answer how the Transformer computes attention or why it replaces recurrence and convolution; doing so would require prior knowledge, which this task forbids. No sources were used because none were supplied. If you can provide relevant document passages or chunks, I can answer strictly from them.

**[mode_C]**

The evidence is insufficient to answer this question. The only relevant excerpt is the opening of "Attention Is All You Need," and it contains just the title, author list, affiliation, and a Google permission notice for reproducing tables and figures — none of the paper's actual content. It does not describe how attention is computed (e.g., query/key/value projections or scaled dot-product attention) nor any argument for replacing recurrence and convolution. The other retrieved items — the Pride and Prejudice excerpts, the industrial diagnostic report (`202609201042216_team_smoke`), and the RAG benchmark abstract — are unrelated to the question and provide no supporting content.

Sources reviewed (none usable for the answer):
- `Attention Is All You Need` (title/author header only; no body text retrieved)
- `pride_and_prejudice (part 1 of 26).md` (irrelevant)
- 工业诊断报告：5 秒窗口温度序列异常趋势判定 (irrelevant)
- Towards Global Retrieval Augmented Generation benchmark abstract (irrelevant)

Per the experiment contract, I am reporting the gap rather than answering from prior knowledge.

**[rerank]**

**Answer (from the provided evidence only):**

According to [2110.07844], the attention head transforms the j-th decoder state and i-th encoder state into query, key, and value vectors, computes attention weights as a normalized dot product between the query and key vectors, and produces an output that is a weighted sum of the value vectors. [1706.03762] states the Transformer is "the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention." However, that passage asserts the replacement without giving a *reason* for it, and convolution is never mentioned anywhere in the retrieved evidence. [1810.04805] only defines notational quantities (number of layers L, hidden size H, number of self-attention heads), and [2510.13343] only says attention "learns to focus on relevant parts of the input data." The remaining passages ([2503.21676], [1906.10015]) address model-internal learning dynamics, not attention computation or the choice of attention over recurrence/convolution. Therefore the evidence is **insufficient** to answer why the Transformer replaces recurrence and convolution; only the mechanism (query–key–value, normalized dot-product weights, weighted sum of values) and the bare fact of replacing recurrence are supported.

**Sources used:** [2110.07844]; [1706.03762]; [1810.04805]; [2510.13343]. (Passages [2503.21676] and [1906.10015] were reviewed and found not to answer the question.)

**[rrf]**

**Answer:** The evidence only partially addresses this question. From [1706.03762], the Transformer employs h = 8 parallel attention heads with d_k = d_v = d_model/h = 64, and because each head has reduced dimension, the total computational cost is similar to single-head attention with full dimensionality. The same chunk lists three uses of multi-head attention: encoder-decoder attention (queries from the previous decoder layer, keys and values from the encoder output, letting every decoder position attend over all input positions), encoder self-attention (keys, values, and queries all from the previous encoder layer, with each position attending to all positions there), and decoder self-attention (text truncated mid-sentence). However, the evidence does not show the actual attention computation (e.g., any scoring/softmax formulation), nor does it state why the Transformer replaces recurrence and convolution — no rationale about sequential computation or path length appears in the retrieved chunks.

**Sources used / checked:**
- [1706.03762] (used — multi-head attention configuration, §3.2.3 applications)
- [1810.04805] (checked — covers BERT span-extraction QA fine-tuning with start/end vectors; not relevant)
- [2503.21676] (checked — covers twin-architecture attention patching; not relevant)

The evidence is therefore insufficient to fully answer the question as posed; I can only report the multi-head configuration and application modes from [1706.03762].

**[vector]**

**Answer (evidence-bounded):**

The evidence explains attention computation only partially: [2110.07844] describes a cross-attention head that transforms the j-th decoder state and i-th encoder state into query, key, and value vectors, computes attention weights as a normalized dot product between query and key vectors, and outputs a weighted sum of value vectors. [2510.13343] adds that the attention mechanism "learns to focus on relevant parts of the input data, thereby enabling powerful representations" across domains beyond NLP. [1706.03762] states the Transformer is "the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention" — this confirms recurrence is replaced, but the excerpt is truncated and gives no deeper rationale. The evidence does **not** mention convolution at all, nor does it give reasons (e.g., parallelism, path length) for the replacement, so the full "why" in the question is not answerable from this evidence. [1810.04805] only defines notation (layers L, hidden size H, heads A), and [2503.21676] and [1906.10015] discuss attention in unrelated contexts (plateau formation, attention-shift modeling); none of these address the question.

**Sources used:** [1706.03762], [2110.07844], [2510.13343] (partial); [1810.04805], [2503.21676], [1906.10015] (checked, not relevant).

</details>


## QK02 — `single`

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**gold:** 1602.01876, 1602.01876

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 6.4 | 729 | 0.20859 | 0 | 是 | The evidence is insufficient to answer this question. The only relevant source, [1602.01876] (the Gene Ontology primer), states that the GO project "c |
| `mode_A` | ✓ | ✓ | 39.7 | 1487 | 0.23052 | 0 | 是 | The retrieved evidence is insufficient to answer this question, so I am stopping rather than answering from prior knowledge. The only chunk that conce |
| `mode_B` | ✗ | ✗ | 12.5 | 755 | 0.20584000000000002 | 0 | 是 | The evidence is insufficient: no evidence was retrieved (the evidence block is empty), so I cannot answer which three independent ontologies subdivide |
| `mode_C` | ✓ | ✗ | 36.3 | 496 | 0.2085 | 0 | 是 | The evidence is insufficient to answer this question. I reviewed all documents provided: the industrial diagnostic report ("5 秒窗口温度序列异常趋势判定", run ID ` |
| `rerank` | ✓ | ✓ | 11.2 | 541 | 0.20188499999999998 | 0 | 否 | **Answer:** The Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: **Molecular Function (MF)**, **B |
| `rrf` | ✓ | ✓ | 7.9 | 655 | 0.207165 | 0 | 是 | **The evidence is insufficient to answer this question.** The only excerpt bearing on the Gene Ontology — [1602.01876] — stops at "The Gene Ontology i |
| `vector` | ✓ | ✓ | 3.7 | 229 | 0.19406 | 0 | 否 | The Gene Ontology subdivides its terms into three distinct ontologies representing different biological aspects: **Molecular Function (MF)**, **Biolog |

<details><summary>逐字答案全文</summary>

**[bm25]**

The evidence is insufficient to answer this question. The only relevant source, [1602.01876] (the Gene Ontology primer), states that the GO project "consists of the Gene Ontology itself, which models biological aspects in a structured way, and annotations," and that the GO is "a controlled vocabulary of terms to represent biology in a structured way" — but the excerpt cuts off ("The term") before naming any sub-ontologies. The other two provided sources ([2301.08436] on spatial transcriptomics and [2401.06823] on interpretable deep learning for single-cell omics) do not discuss the Gene Ontology's structure at all. Therefore, I cannot name the three independent ontologies from the supplied evidence.

Sources consulted: [1602.01876] (relevant but incomplete); [2301.08436], [2401.06823] (not relevant).

**[mode_A]**

The retrieved evidence is insufficient to answer this question, so I am stopping rather than answering from prior knowledge.

The only chunk that concerns the Gene Ontology — `genomics__1602.01876__primer-on-the-gene-ontology.md.md` (part 1/2) — contains only the paper's title, author names, and affiliations, and is cut off before any body text describing the GO's structure or subdivision. The other retrieved chunks do not mention the Gene Ontology at all: the Global RAG benchmark abstract ("Towards Global Retrieval Augmented Generation"), the indexing paper (`databases__2009.10669`, parts 1/4 and 3/4), and the soul-template memory-convention notes.

Sources consulted (none contained the answer):
- `genomics__1602.01876__primer-on-the-gene-ontology.md.md` (part 1/2) — title/affiliations only, truncated
- `databases__2009.10669__there-is-no-such-thing-as-an-index-or-the-ne` (parts 1/4, 3/4)
- "Towards Global Retrieval Augmented Generation: A Benchmark for Corpus-Level Reasoning" (abstract)
- Soul-template memory-convention notes (three identical chunks)

No answer is available from the provided evidence.

**[mode_B]**

The evidence is insufficient: no evidence was retrieved (the evidence block is empty), so I cannot answer which three independent ontologies subdivide the Gene Ontology. Per the task contract, I am not permitted to fall back on prior knowledge. Sources used: none (no chunks, documents, or paths were available to cite).

**[mode_C]**

The evidence is insufficient to answer this question.

I reviewed all documents provided: the industrial diagnostic report ("5 秒窗口温度序列异常趋势判定", run ID `202609201042216_team_smoke`), the paper "Attention Is All You Need", the "Towards Global Retrieval Augmented Generation" benchmark abstract, and the soul-template memory/persona definitions. None of these sources mentions the Gene Ontology, its structure, or any ontologies that subdivide it. No source path, file name, or chunk in the evidence addresses the question, so I cannot name the three ontologies without falling back on prior knowledge — which is prohibited here.

**[rerank]**

**Answer:** The Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**.

**Source used:** [1602.01876], section "2. What is the Gene Ontology?" ("The terms are subdivided in three distinct ontologies … Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)").

**[rrf]**

**The evidence is insufficient to answer this question.**

The only excerpt bearing on the Gene Ontology — [1602.01876] — stops at "The Gene Ontology is a controlled vocabulary of terms to represent biology in a structured way. The term…" and is truncated before any subdivision into separate ontologies is named. The other two excerpts ([2508.18304] on monocyte subclusters and DEG markers; [2110.07787] on SingleR/Cell-ID cell-type annotation) discuss single-cell transcriptomics and never mention the Gene Ontology or its component ontologies at all.

No source in the retrieved evidence states which three independent ontologies subdivide GO, so I am not answering from prior knowledge.

Sources used: [1602.01876] (GO primer excerpt), [2508.18304], [2110.07787].

**[vector]**

The Gene Ontology subdivides its terms into three distinct ontologies representing different biological aspects: **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**.

Source used: [1602.01876], "## 2. What is the Gene Ontology?". (The other two passages, [2110.07787] and [2508.18304], were not relevant to this question.)

</details>


## QK03 — `single`

**Q:** What physical mechanism does the dynamic electrical model use to explain the hysteretic J-V characteristics of perovskite solar cells?

**gold:** 1606.00335, 1606.00335

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 13.7 | 1994 | 0.24085499999999999 | 0 | 否 | Based on the retrieved evidence, the dynamic electrical model explains the hysteretic J–V characteristics through the **time variation of the cell's p |
| `mode_A` | ✓ | ✓ | 36.1 | 609 | 0.20747499999999997 | 0 | 是 | The retrieved evidence does not contain an answer to this question. None of the supplied chunks discuss perovskite solar cells, J-V characteristics, o |
| `mode_B` | ✗ | ✗ | 12.4 | 483 | 0.199115 | 0 | 是 | **Answer: The evidence is insufficient to answer this question.** The EVIDENCE block for this task states "(no evidence retrieved)," so no document pa |
| `mode_C` | ✓ | ✓ | 39.7 | 1114 | 0.22080499999999997 | 0 | 是 | **The evidence is insufficient to answer this question.** The only relevant chunks — `materials__1606.00335__dynamic-electrical-behavior-of-halide-per |
| `rerank` | ✓ | ✓ | 12.6 | 669 | 0.20496999999999999 | 0 | 否 | The dynamic electrical model in [1606.00335] attributes the hysteretic J-V behavior of perovskite solar cells to **polarization relaxation**: by makin |
| `rrf` | ✓ | ✓ | 9.9 | 1564 | 0.23008 | 0 | 否 | Based on the evidence provided: The retrieved evidence from [1606.00335] indicates the dynamic electrical model explains hysteretic J-V behaviour via  |
| `vector` | ✓ | ✓ | 6.7 | 855 | 0.209595 | 0 | 否 | **Answer (based only on the provided evidence):** According to the abstract of [1606.00335], the dynamic electrical model explains hysteresis in perov |

<details><summary>逐字答案全文</summary>

**[bm25]**

Based on the retrieved evidence, the dynamic electrical model explains the hysteretic J–V characteristics through the **time variation of the cell's polarization**: it extends the standard static equivalent circuit (photocurrent source, diode with ideality factor n, shunt resistance R_sh, series resistance R_s) with a **parallel capacitance C**, a capacitive element tied to that polarization. The analysis is "focused on the variation of the polarization in time, assuming a certain relaxation time scale," and it further investigates the influence of different relaxation time scales. The evidence also notes that the hysteretic effects are influenced by solar cell preconditioning and bias scan rate.

Sources used:
- **[1606.00335]** — the only source that addresses the mechanism (equivalent circuit + parallel capacitance, polarization vs. time, relaxation time scale, preconditioning, scan rate).
- [1712.01369] and [2607.03098] were retrieved but do not address the hysteresis mechanism (they concern perovskite/GeSe bilayer cell performance metrics and energy-storage dynamic models, respectively), so they contribute nothing to this answer.

**[mode_A]**

The retrieved evidence does not contain an answer to this question. None of the supplied chunks discuss perovskite solar cells, J-V characteristics, or hysteresis: they cover multi-agent RL for stock market microstructure (`finance__1909.07748`), ECB monetary policy under uncertainty (`economics__2011.14424`), a corpus-level RAG benchmark, tactile-based blind grasping control (`robotics__1709.02924`), spatial transcriptomic clustering (`genomics__2110.07787`), and single-cell multi-omics contrastive learning (`genomics__2508.18304`).

The evidence is insufficient to answer what physical mechanism the dynamic electrical model uses to explain hysteretic J-V characteristics in perovskite solar cells, and I will not answer from prior knowledge.

**Sources examined:** finance__1909.07748 (part 2/4), economics__2011.14424 (part 1/5), the RAG benchmark paper, robotics__1709.02924 (part 2/4), genomics__2110.07787 (part 2/3), genomics__2508.18304 (part 1/4).

**[mode_B]**

**Answer: The evidence is insufficient to answer this question.**

The EVIDENCE block for this task states "(no evidence retrieved)," so no document path, file name, or chunk id was available to consult. I cannot describe the physical mechanism used by the dynamic electrical model to explain hysteretic J–V behavior in perovskite solar cells without falling back on prior knowledge, which the task contract explicitly forbids. No sources were used, because none were provided. If the retrieval step can be rerun to return candidate documents, I can attempt a grounded answer from those.

**[mode_C]**

**The evidence is insufficient to answer this question.**

The only relevant chunks — `materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs（第 1/2 部分）` and `（第 2/2 部分）` — do not name the physical mechanism. Part 1/2 ends in the author affiliations, before any abstract or model description; part 2/2 ("3.2. Bias scan rate effects") only reports that hysteresis width varies with bias scan rate (widest at moderate BSRs) and that this was used to test the model's validity, but it is truncated before stating what physical mechanism the model invokes. The remaining evidence (the industrial diagnostic report, the Photosynthesis and Voyager 1 extracts, and the corpus-level RAG benchmark abstract) is unrelated to perovskite J–V hysteresis. I therefore cannot name the mechanism without drawing on prior knowledge, which the output contract prohibits.

Sources consulted: `materials__1606.00335__dynamic-electrical-behavior-of-halide-perovs` (parts 1/2 and 2/2).

**[rerank]**

The dynamic electrical model in [1606.00335] attributes the hysteretic J-V behavior of perovskite solar cells to **polarization relaxation**: by making a simple ansatz for the polarization relaxation, the model reproduces both qualitative and quantitative features of measured J-V characteristics. The same source links this mechanism to pre-poling effects, distinguishing initially over-polarized from under-polarized samples, and to the presence of a current overshoot. The second retrieved item, [1712.01369], only presents an electrical simulation of a bilayer solar cell's J-V curve (reporting Jsc, Voc, FF) and does not describe any hysteresis mechanism, so it contributes nothing to this question.

Sources used: [1606.00335] (Abstract) — answers the question; [1712.01369] — reviewed, not relevant to the mechanism.

**[rrf]**

Based on the evidence provided:

The retrieved evidence from [1606.00335] indicates the dynamic electrical model explains hysteretic J-V behaviour via the time variation of polarization, assuming a finite relaxation time scale, and it extends the static equivalent circuit (photocurrent source, diode, shunt and series resistances) with a parallel capacitance C. Hysteresis is described as influenced by solar cell preconditioning and bias scan rate, and the paper investigates the influence of different relaxation time scales. However, the chunk is truncated ("which is gen...") and the model section does not explicitly name the microscopic origin of that polarization (e.g., ion migration), so on that specific point the evidence is only partially sufficient. The other chunks do not address the mechanism: [1712.01369] only reports J-V parameters (Jsc, Voc, FF, efficiency) for a perovskite/GeSe bilayer cell, and [2607.03098] concerns dynamic models of energy storage systems (flywheels, batteries), not perovskite hysteresis.

Sources used: [1606.00335] (Sections 1–2.1 excerpts), [1712.01369], [2607.03098] (checked, found non-relevant).

**[vector]**

**Answer (based only on the provided evidence):**

According to the abstract of [1606.00335], the dynamic electrical model explains hysteresis in perovskite solar-cell J–V characteristics through **polarization relaxation**: by making a simple ansatz for the polarization relaxation, the model reproduces qualitatively and quantitatively detailed features of measured J–V curves. The same abstract indicates this polarization-relaxation treatment also captures pre-poling effects (differences between initially over-polarized and under-polarized samples) and the presence of a current overshoot, though the excerpt is truncated mid-sentence, so the full mechanism description is not available here. The second source, [1712.01369], only presents a simulated J–V curve for a bilayer cell alongside a typical perovskite cell and reports Jsc, Voc, and FF; it does not describe any physical mechanism for hysteresis. Therefore, the evidence supports "polarization relaxation" as the mechanism, but provides only a partial account because the key abstract is cut off.

**Sources used:**
- [1606.00335] — Abstract (the only source addressing the mechanism; truncated)
- [1712.01369] — excerpt (used only to confirm it does not address the mechanism)

</details>


## QK04 — `single`

**Q:** Using only what kind of information, and reaching what accuracy, does the wav2vec 2.0 approach detect within-sentence prosodic boundaries on Czech broadcast news?

**gold:** 2209.15032, 2209.15032

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 6.8 | 627 | 0.20711999999999997 | 0 | 否 | Using only acoustic information, the wav2vec 2.0 approach detects within-sentence prosodic boundaries in Czech broadcast news with 94% accuracy and an |
| `mode_A` | ✓ | ✓ | 36.4 | 728 | 0.211445 | 0 | 是 | **Answer: The evidence is insufficient.** The only relevant chunk retrieved is the header of the paper "Detection of Prosodic Boundaries in Speech Usi |
| `mode_B` | ✗ | ✗ | 14.0 | 861 | 0.20863 | 0 | 是 | The evidence is insufficient: the EVIDENCE section contains "(no evidence retrieved)," so there is no document content about wav2vec 2.0, Czech broadc |
| `mode_C` | ✗ | ✗ | 36.7 | 783 | 0.211905 | 0 | 是 | The evidence does not contain the answer. None of the retrieved passages discusses wav2vec 2.0, prosodic boundary detection, or Czech broadcast news — |
| `rerank` | ✓ | ✓ | 10.6 | 654 | 0.20400000000000001 | 0 | 否 | The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no transcript/text), achieving an **accuracy |
| `rrf` | ✓ | ✓ | 5.6 | 589 | 0.20614499999999997 | 0 | 否 | The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** — no text or transcripts — reaching **94% acc |
| `vector` | ✓ | ✓ | 6.9 | 660 | 0.204175 | 0 | 否 | Using only acoustic information from the speech signal, the wav2vec 2.0 approach detects within-sentence prosodic boundaries in Czech broadcast news w |

<details><summary>逐字答案全文</summary>

**[bm25]**

Using only acoustic information, the wav2vec 2.0 approach detects within-sentence prosodic boundaries in Czech broadcast news with 94% accuracy and an F1 measure of 83% (and 95% accuracy / 89% F1 across all prosodic boundaries). The recordings were labeled by phonetic experts, and the approach was compared against a text-based predictor using transcripts of the same data, which it outperformed despite the relatively small amount of labeled data.

Source used: [2209.15032] chunk `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (part 1/2).

**[mode_A]**

**Answer: The evidence is insufficient.**

The only relevant chunk retrieved is the header of the paper "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0" (Kunešová & Rezáčková, University of West Bohemia, Plzeň) — but it contains only the title, authors, and the first word of the abstract ("Prosodic..."), truncated before anything about the input information used or the detection accuracy achieved. The other retrieved chunks (a RAG benchmark paper, a Bayesian state-space monetary-policy paper, an industrial temperature-diagnostics report, and a MultiverSeg segmentation paper) are unrelated to the question. Because the wav2vec 2.0 chunk's abstract and results are cut off, no answer about the type of information used or the accuracy achieved on Czech broadcast news can be given from this evidence.

**Sources used:**
- `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u（第 1/2 部分）` (relevant but truncated)
- Remaining chunks reviewed and judged irrelevant: `economics__1911.06206...（第 1/5 部分）`, industrial diagnostics report (`202609201042216_team_smoke`), `medical-imaging__2412.15058...` (parts 2 and 5), RAG benchmark abstract.

**[mode_B]**

The evidence is insufficient: the EVIDENCE section contains "(no evidence retrieved)," so there is no document content about wav2vec 2.0, Czech broadcast news, or within-sentence prosodic boundary detection to draw on. Per the output contract, I am stating this explicitly and stopping rather than falling back on prior knowledge.

**[mode_C]**

The evidence does not contain the answer. None of the retrieved passages discusses wav2vec 2.0, prosodic boundary detection, or Czech broadcast news — they are a Jane Austen novel excerpt, a Chinese industrial temperature-anomaly diagnostic report, the title page of "Attention Is All You Need," and the abstract of a RAG benchmark paper. I therefore cannot state what kind of information or what accuracy the wav2vec 2.0 approach achieves for within-sentence prosodic boundaries on Czech broadcast news, and per the task constraints I will not fall back on prior knowledge.

Sources reviewed (none relevant):
- `pride_and_prejudice` (parts 13/26 and 2/26)
- `工业诊断报告：5 秒窗口温度序列异常趋势判定` (run ID `202609201042216_team_smoke`)
- `Attention Is All You Need` (paper header)
- `Towards Global Retrieval Augmented Generation: A Benchmark for Corpus-Level Reasoning` (abstract)

Evidence is insufficient to answer the question.

**[rerank]**

The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** (no transcript/text), achieving an **accuracy of 94%** (with an F1 measure of 83%) on Czech broadcast news recordings labeled by phonetic experts.

Source used: [2209.15032].

**[rrf]**

The wav2vec 2.0 approach detects within-sentence prosodic boundaries using **only acoustic information** — no text or transcripts — reaching **94% accuracy and an F1 of 83%** on recordings of Czech broadcast news labeled by phonetic experts. For all prosodic boundaries it reaches 95% accuracy and 89% F1, outperforming the text-based predictor despite the relatively small amount of labeled data.

Source: chunk `speech__2209.15032__detection-of-prosodic-boundaries-in-speech-u` (paper [2209.15032], "Detection of Prosodic Boundaries in Speech Using Wav2Vec 2.0").

**[vector]**

Using only acoustic information from the speech signal, the wav2vec 2.0 approach detects within-sentence prosodic boundaries in Czech broadcast news with an accuracy of 94% (F1 measure 83%), despite training on a relatively small amount of labeled data. The evidence text is truncated just after "(or 95%", so a second figure may follow in the full paper, but the passage as given supports only the 94% accuracy / 83% F1 result for within-sentence boundaries.

Source used: chunk [2209.15032] (abstract text on wav2vec 2.0 boundary detection on Czech broadcast news).

</details>


## QK05 — `single`

**Q:** In the trap-cropping optimization framework, roughly what share of the field should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant?

**gold:** 2508.05896, 2508.05896

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 5.3 | 496 | 0.20342999999999997 | 0 | 否 | Approximately **7–10% of the field** should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant. The evidence  |
| `mode_A` | ✓ | ✗ | 38.5 | 1184 | 0.22127 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved chunks discuss trap-cropping, trap plants, or any field-allocation ratio;  |
| `mode_B` | ✗ | ✗ | 12.7 | 390 | 0.19684000000000001 | 0 | 是 | The evidence is insufficient. No evidence was retrieved (the evidence block is empty), so I cannot answer the question about what share of a field sho |
| `mode_C` | ✓ | ✗ | 37.6 | 1058 | 0.21912 | 0 | 是 | The evidence is insufficient to answer this question. The provided material consists of: *Pride and Prejudice* excerpts (parts 11/26 and 20/26), the C |
| `rerank` | ✓ | ✓ | 13.9 | 1129 | 0.21589999999999998 | 0 | 否 | **Answer:** Roughly 7–10% of the field — about a tenth of the land — should be allocated to trap plants. The evidence explicitly states that at attrac |
| `rrf` | ✓ | ✓ | 7.3 | 369 | 0.20028 | 0 | 否 | Roughly **7–10% of the field** should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant, per the trap-croppi |
| `vector` | ✓ | ✓ | 16.4 | 2850 | 0.2589 | 0 | 否 | **Answer:** The retrieved evidence supports a figure of roughly 10% of the field (with an overlapping fragment citing approximately 7–10%) for trap-pl |

<details><summary>逐字答案全文</summary>

**[bm25]**

Approximately **7–10% of the field** should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant.

The evidence states directly: "For more attractive trap plants, 5 and 25 times more attractive, approximately 7–10% of the field should be allocated to trap plants" (Figure 3 caption), and separately that at five times attractiveness "it is optimal to devote roughly ten percent of the land to the trap crop (Figure 3b)."

Source used: [2508.05896] — Figure 3 caption and surrounding text. (The other two evidence items, [1609.00415] and [1512.08067], are unrelated to trap cropping and were not used.)

**[mode_A]**

The evidence is insufficient to answer this question. None of the retrieved chunks discuss trap-cropping, trap plants, or any field-allocation ratio; the topic does not appear anywhere in the provided material. The chunks concern other domains entirely (RAG benchmarking, mixed-integer optimal control, monetary-policy state-space modeling, sketch-based query optimization, quantum error mitigation, and the Transformer paper). No share or percentage for trap-plant allocation at 5–25× attractiveness is stated or implied. I therefore cannot provide the requested figure without falling back on prior knowledge, which this task forbids.

Sources examined (none contained the answer):
- `Towards Global Retrieval Augmented Generation: A Benchmark for Corpus-Level Reasoning` (abstract)
- `mathematics__2211.12700__tailored-presolve-techniques-in-branch-and-b.md.md` (part 1/5)
- `economics__1911.06206__bayesian-state-space-modeling-for-analyzing` (part 3/5)
- `databases__2102.02440__online-sketch-based-query-optimization.md.md` (part 3/5)
- `quantum-physics__2303.00445__benchmarking-noisy-intermediate-scale-quantu` (part 3/4)
- `Attention Is All You Need` (author block)

**[mode_B]**

The evidence is insufficient. No evidence was retrieved (the evidence block is empty), so I cannot answer the question about what share of a field should be allocated to trap plants in the trap-cropping optimization framework when trap plants are 5–25× more attractive than the cash plant.

Sources used: none (no documents, files, or chunk IDs were provided).

**[mode_C]**

The evidence is insufficient to answer this question.

The provided material consists of: *Pride and Prejudice* excerpts (parts 11/26 and 20/26), the Chinese industrial diagnostic report `202609201042216_team_smoke` (5-second temperature-series anomaly assessment), the *Attention Is All You Need* paper excerpt, and the *Towards Global Retrieval Augmented Generation* benchmark paper excerpt. None of these documents discusses trap cropping, trap plants, plant attractiveness ratios, or field-allocation shares in any agricultural or pest-management framework. I therefore cannot state what share of the field should be allocated to trap plants at a 5–25× attractiveness ratio, and per the output contract I stop here rather than fall back on prior knowledge.

Sources reviewed (none usable for the answer): `pride_and_prejudice` parts 11/26 and 20/26; 工业诊断报告 `202609201042216_team_smoke`; "Attention Is All You Need"; "Towards Global Retrieval Augmented Generation".

**[rerank]**

**Answer:** Roughly 7–10% of the field — about a tenth of the land — should be allocated to trap plants. The evidence explicitly states that at attractiveness level five (pests five times more likely to settle on a trap plant), it is optimal to devote roughly 10% of the land to the trap crop, and separately that approximately 7–10% of the field should be allocated to trap plants. The retrieved chunk does not explicitly restate the 25× figure, but the 7–10% statement sits in the high-attractiveness discussion matching the upper end of the question's range.

**Source used:** [2508.05896] (provided evidence chunk; trap-cropping optimization discussion around Figures 3b/3c).

**[rrf]**

Roughly **7–10% of the field** should be allocated to trap plants when they are 5 to 25 times more attractive than the cash plant, per the trap-cropping optimization framework. The evidence states that for trap plants "5 and 25 times more attractive, approximately 7–10% of the field should be allocated to trap plants," and separately notes that at five times attractiveness it is optimal to devote roughly ten percent of the land to the trap crop (Figure 3b). The evidence further contrasts this with a trap plant only twice as attractive, where trap cropping is ineffective and the grower should plant only cash plants.

Sources used: [2508.05896] — text accompanying Figure 3 (the other retrieved chunks, [1609.00415] on Chinese infrastructure and [1512.08067] on Malthusian trap/growth, are unrelated to the question).

**[vector]**

**Answer:** The retrieved evidence supports a figure of roughly 10% of the field (with an overlapping fragment citing approximately 7–10%) for trap-plant attractiveness around five times the cash plant: it states that at attractiveness five "it is optimal to devote roughly ten percent of the land to the trap crop" (Figure 3b), and the earlier fragment gives "approximately 7–10% of the field." However, the excerpt is truncated ("Interestingly, from figur…") and only explicitly discusses attractiveness up to five — it does not state the optimal share for the full 5–25× range, so a precise figure at the 25× end cannot be confirmed from the retrieved evidence.

**Source used:** arXiv 2508.05896 chunk (trap-cropping optimization text referencing Figures 2, 3b, and 3c).

</details>


## QK06 — `single`

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**gold:** 1503.07557, 1503.07557

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 9.6 | 1314 | 0.22360999999999998 | 0 | 是 | **The evidence is insufficient to name a single physical factor as the primary control.** The only relevant source ([1503.07557] `climate-science__150 |
| `mode_A` | ✓ | ✓ | 41.5 | 1553 | 0.232015 | 0 | 是 | **Insufficient evidence.** The only retrieved chunk relevant to the question — `climate-science__1503.07557__precipitation-extremes-under-climate-chan |
| `mode_B` | ✗ | ✗ | 16.1 | 1327 | 0.220175 | 0 | 是 | The evidence retrieved for this question is empty ("no evidence retrieved"), so it does not contain the answer. Per the output contract, I am stating  |
| `mode_C` | ✗ | ✗ | 40.9 | 1076 | 0.21976 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved sources — `pride_and_prejudice` (parts 16/26 and 3/26), the industrial diagnostic  |
| `rerank` | ✓ | ✓ | 23.0 | 2001 | 0.23883000000000001 | 0 | 是 | The evidence is insufficient to answer this question. The O'Gorman review ([1503.07557], "Precipitation extremes under climate change") states it focu |
| `rrf` | ✓ | ✓ | 8.7 | 1171 | 0.219915 | 0 | 是 | **Answer:** The evidence does not explicitly identify a single physical factor that "primarily" controls the response of precipitation extremes to cli |
| `vector` | ✓ | ✓ | 14.8 | 2481 | 0.25083 | 0 | 否 | **Answer:** The retrieved evidence does not explicitly identify the primary physical factor. The abstract of [1503.07557] (O'Gorman) says the response |

<details><summary>逐字答案全文</summary>

**[bm25]**

**The evidence is insufficient to name a single physical factor as the primary control.** The only relevant source ([1503.07557] `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md`, Part 1/3, O'Gorman abstract) states that "several physical contributions govern the response of precipitation extremes" — thermodynamic, microphysical, and dynamical — rather than identifying one factor as primary. It notes only that the thermodynamic contribution is "robust and well understood," while theoretical understanding of the microphysical and dynamical contributions "is still being developed." It also says the sensitivity remains uncertain where convection is important. No ranking or single controlling factor is given.

Sources used: `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (chunk [1503.07557]). The other two chunks ([2409.13934], [2409.09639]) were not used — they concern an emulator's climate-change signal and a GPC/m precipitation dataset, not the controls on precipitation extremes.

**[mode_A]**

**Insufficient evidence.** The only retrieved chunk relevant to the question — `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (part 1/3) — states the paper focuses on "the physical factors that control the response" of precipitation extremes to climate change, but it never names the factor that *primarily* controls that response; the abstract excerpt is truncated mid-sentence ("it may be higher in the...") and only mentions convection as a condition under which sensitivity remains uncertain, not as the primary controlling factor. The other retrieved chunks (the global-RAG benchmark paper, the soul-template memory conventions, the ECB monetary-policy paper, and the Vision-Flan task excerpt) do not address the question at all. Per the output contract, I am reporting the evidence as insufficient rather than falling back on prior knowledge.

**Sources used:** `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (part 1/3).

**[mode_B]**

The evidence retrieved for this question is empty ("no evidence retrieved"), so it does not contain the answer.

Per the output contract, I am stating this explicitly rather than answering from prior knowledge: I cannot say which physical factor primarily controls the response of precipitation extremes to climate change, because no supporting document, file, or chunk was provided. Asking me to answer from memory is outside the contract, so I decline.

Sources used: none — no evidence was available.

**[mode_C]**

The evidence is insufficient to answer this question. The retrieved sources — `pride_and_prejudice` (parts 16/26 and 3/26), the industrial diagnostic report `202609201042216_team_smoke`, the "Great Wall of China" Wikipedia excerpt, the "Towards Global Retrieval Augmented Generation" abstract, and the "Agentic Knowledge Base — Architecture & Development Guide" — contain no material on precipitation extremes, climate change, or any controlling physical factor. None of the retrieved chunks address atmospheric or climate physics in any form. Per the output contract, I am stopping here rather than answering from prior knowledge.

**Sources examined (none usable for this question):** `pride_and_prejudice` 16/26, `pride_and_prejudice` 3/26, `202609201042216_team_smoke` diagnostic report, Great Wall of China Wikipedia chunk, Global RAG benchmark abstract, Agentic Knowledge Base architecture guide.

**[rerank]**

The evidence is insufficient to answer this question. The O'Gorman review ([1503.07557], "Precipitation extremes under climate change") states it focuses on "the physical factors that control the response," but the provided abstract excerpt truncates before naming any such factor. [2409.13934] cites Clausius-Clapeyron scaling (~7%/°C) as a strong warming-driven signal for extreme precipitation, but does not state that this is the primary controlling factor. [2007.10574] discusses dynamical factors — vertical moisture flux convergence and vertical moisture advection — but only for MJO-induced extreme precipitation, not the general climate-change response. No excerpt in the evidence explicitly identifies a single primary controlling physical factor.

Sources used: [1503.07557] (O'Gorman, abstract excerpt); [2409.13934] (excerpt); [2007.10574] (Section 3.2 excerpt).

**[rrf]**

**Answer:** The evidence does not explicitly identify a single physical factor that "primarily" controls the response of precipitation extremes to climate change. The O'Gorman review states that "several physical contributions govern the response," listing thermodynamic, microphysical, and dynamical contributions; among these, the thermodynamic contribution is described as "robust and well understood," while theoretical understanding of the microphysical and dynamical contributions is "still being developed." The other retrieved chunks are not on point: the 2409.13934 chunk concerns evaluating an emulator's climate change signal for annual and extreme precipitation, and the 2007.10574 chunk concerns MJO modulation of extreme precipitation frequency in Indonesia. Therefore the evidence is insufficient to answer "which single factor primarily controls" the response; it supports only the weaker claim that the thermodynamic contribution is the robust, well-understood one among several governing contributions.

**Sources used:**
- `climate-science__1503.07557__precipitation-extremes-under-climate-change.md.md` (part 1/3, O'Gorman abstract)
- [2409.13934] chunk (emulator climate change signal)
- [2007.10574] chunk (MJO and Indonesian precipitation extremes)

**[vector]**

**Answer:** The retrieved evidence does not explicitly identify the primary physical factor. The abstract of [1503.07557] (O'Gorman) says the response is examined "with a focus on the physical factors that control the response," but the retrieved text is truncated ("remains uncert…") before any factor is named; it only states that precipitation extremes intensify with warming while sensitivity remains uncertain. [2409.13934] cites a "strong warming-driven signal (Clausius-Clapeyron, ~7%/°C)" for extreme precipitation, but does not state that this is the primary controlling factor. [2007.10574] mentions vertical moisture flux convergence and vertical moisture advection, but these are discussed as MJO-related modulation processes, not the climate-change response. Therefore, on the evidence provided, I cannot name the controlling physical factor.

**Sources used:**
- [1503.07557] "Precipitation extremes under climate change" (O'Gorman) — abstract fragment
- [2409.13934] — fragment citing Clausius-Clapeyron scaling (~7%/°C)
- [2007.10574] — Section 3.2 fragment on MJO dynamical links

</details>


## QK07 — `distractor`

**Q:** What is MameLoshnLM and what parameter scale does it have?

**gold:** 2608.05850, 2608.05850

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 7.5 | 953 | 0.21532 | 0 | 是 | The provided evidence is insufficient to answer this question. The only mention of MameLoshnLM appears in chunk [2608.05850], Section E.7 "Statistical |
| `mode_A` | ✓ | ✓ | 34.4 | 474 | 0.203795 | 0 | 否 | MameLoshnLM is presented in the evidence as the first open-source language model built specifically for Yiddish, introduced in the paper "MAMELOSHNLM: |
| `mode_B` | ✗ | ✗ | 10.6 | 282 | 0.19405499999999998 | 0 | 是 | The evidence provided is empty — "(no evidence retrieved)" — so I cannot answer what MameLoshnLM is or what parameter scale it has. No sources were re |
| `mode_C` | ✓ | ✗ | 67.5 | 599 | 0.22082499999999997 | 0 | 是 | The evidence is insufficient: none of the provided chunks mentions "MameLoshnLM" or any parameter scale for it. I examined the industrial diagnostic r |
| `rerank` | ✓ | ✓ | 12.0 | 622 | 0.20315 | 0 | 是 | MAMELOSHNLM is described in the evidence as the first open-source large language model for Yiddish, named after the traditional Yiddish term "mame-los |
| `rrf` | ✓ | ✓ | 17.0 | 3194 | 0.271345 | 0 | 是 | The evidence is insufficient to answer this: MameLoshnLM is never defined, and no parameter scale for it is given. The only relevant mention is in [26 |
| `vector` | ✓ | ✓ | 7.2 | 681 | 0.204625 | 0 | 是 | **Answer:** MAMELOSHNLM is described as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection  |

<details><summary>逐字答案全文</summary>

**[bm25]**

The provided evidence is insufficient to answer this question. The only mention of MameLoshnLM appears in chunk [2608.05850], Section E.7 "Statistical Testing," where it is compared against Llama 3.1 8B on lemmatization using McNemar's exact test; the passage treats it as one of two paired binary-outcome models but never defines what MameLoshnLM is. The "8B" figure in that text attaches to Llama 3.1 8B, not to MAMELOSHNLM, so the evidence does not state MameLoshnLM's parameter scale. The other chunks ([2212.13138], [2005.14165]) are unrelated to MameLoshnLM and provide no further information. Per the output contract, I stop here rather than fall back on prior knowledge.

**Source used:** [2608.05850], Section E.7 (Statistical Testing) — the only chunk mentioning MAMELOSHNLM.

**[mode_A]**

MameLoshnLM is presented in the evidence as the first open-source language model built specifically for Yiddish, introduced in the paper "MAMELOSHNLM: Yiddish Language Model and Evaluation Benchmark" (Katz et al.). Its parameter scale is 8B parameters, per the abstract's description of it as "the first open-source 8B-parameter language model built specifically for Yiddish." The abstract also notes the work addresses Yiddish's limited digital presence and scarce evaluation resources.

Source used: nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md.md (Part 1/4, Abstract).

**[mode_B]**

The evidence provided is empty — "(no evidence retrieved)" — so I cannot answer what MameLoshnLM is or what parameter scale it has. No sources were retrieved, and I will not use prior knowledge to fill the gap. This is an explicit statement of insufficient evidence, per the contract.

**[mode_C]**

The evidence is insufficient: none of the provided chunks mentions "MameLoshnLM" or any parameter scale for it. I examined the industrial diagnostic report (`202609201042216_team_smoke`), the "Attention Is All You Need" excerpt, the "Towards Global Retrieval Augmented Generation" benchmark excerpt, the soul-template memory conventions, and the power-electronics energy storage review (part 3/5), and none of them contain the term "MameLoshnLM" or any related model description. Therefore I cannot answer what MameLoshnLM is or what parameter scale it has, and I will not fall back on prior knowledge.

**[rerank]**

MAMELOSHNLM is described in the evidence as the first open-source large language model for Yiddish, named after the traditional Yiddish term "mame-loshn" ("mother tongue"), trained on the Yiddish corpus described in subsection 3.2, and reported to outperform strong baselines of similar scale on a broad set of Yiddish evaluation benchmarks; it was produced by continued pretraining.

The evidence does **not** state its parameter scale. The provided chunk is truncated mid-sentence ("produced by continued pretrain…") and only mentions "baselines of similar scale" without giving any parameter count, so this part of the question cannot be answered from the evidence. I am not using prior knowledge to fill the gap.

Source used: chunk [2608.05850] §5 "MAMELOSHNLM".

**[rrf]**

The evidence is insufficient to answer this: MameLoshnLM is never defined, and no parameter scale for it is given. The only relevant mention is in [2608.05850] (Appendix E.7, "Statistical Testing"), where "MAMELOSHNLM" appears as a model compared pairwise against Llama 3.1 8B on lemmatization using McNemar's exact test on paired binary correct/incorrect outcomes — the 8B scale named there belongs to Llama 3.1 8B, not to MAMELOSHNLM. The other evidence chunks — [2212.13138] (a medical Q&A item) and [2005.14165] (GPT-3 word-scrambling tasks) — do not mention MameLoshnLM at all. Since the retrieved evidence does not contain the answer, I stop here rather than fall back on prior knowledge.

Source used: [2608.05850], Appendix E.7 "Statistical Testing".

**[vector]**

**Answer:** MAMELOSHNLM is described as the first open-source large language model for Yiddish, trained on the Yiddish corpus described in subsection 3.2 of the source; it is named after the traditional Yiddish term "mame-loshn" ("mother tongue"), and it is reported to outperform strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks, having been produced by continued pretraining.

**On the parameter scale:** the evidence does not state a parameter count or size. The only scale-related information given is the comparative phrase "baselines of similar scale" and that training was done via continued pretraining (the snippet is truncated mid-sentence); no numeric parameter count is present, so I cannot answer that part from the evidence.

**Source used:** [2608.05850], Section 5 "MAMELOSHNLM" (provided evidence excerpt only).

</details>


## QK08 — `crosskb`

**Q:** Beyond which percentile of precipitation did the GAN clearly outperform the deterministic baseline in capturing the climate-change wetting signal?

**gold:** 2409.13934, 2409.13934

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | ✓ | ✓ | 13.5 | 2331 | 0.249515 | 0 | 是 | The evidence reports the GAN-versus-baseline comparison only at the 99.5th percentile of precipitation, so as far as the provided evidence goes, the a |
| `mode_A` | ✓ | ✗ | 38.4 | 1018 | 0.218375 | 0 | 是 | **The evidence is insufficient to answer the question.** None of the retrieved chunks mention a GAN, precipitation percentiles, or a climate-change we |
| `mode_B` | ✗ | ✗ | 12.8 | 613 | 0.20237 | 0 | 是 | The evidence provided is empty ("no evidence retrieved"), so I cannot answer the question about the precipitation percentile beyond which the GAN outp |
| `mode_C` | ✗ | ✗ | 1819.3 | 795 | 0.2129 | 0 | 是 | **The provided evidence is insufficient to answer this question.** None of the retrieved passages mention GANs, precipitation percentiles, or a climat |
| `rerank` | ✓ | ✓ | 12.4 | 431 | 0.1983 | 0 | 否 | **Answer:** Beyond the 95th percentile of precipitation. The evidence states that the GAN and the deterministic baseline had "relatively similar signa |
| `rrf` | ✓ | ✓ | 8.7 | 1212 | 0.221515 | 0 | 是 | The evidence only supports a comparison at the 99.5th percentile of precipitation: the GAN trained on future+historical periods captures ~97% of the a |
| `vector` | ✓ | ✓ | 5.2 | 423 | 0.198075 | 0 | 否 | **Answer:** The 95th percentile. The evidence states that the GAN and deterministic baselines have relatively similar climate-change signals up to the |

<details><summary>逐字答案全文</summary>

**[bm25]**

The evidence reports the GAN-versus-baseline comparison only at the 99.5th percentile of precipitation, so as far as the provided evidence goes, the answer is the 99.5th percentile — the highest percentile of the precipitation distribution, i.e., extreme precipitation. At that percentile, the GAN trained on future and historical periods captures about 97% of the average future increase, while the two deterministic baseline algorithms capture only 63–65%, regardless of training period. The chunk never states a lower percentile threshold "beyond which" the GAN clearly outperforms, so it does not support any cut-off below the 99.5th percentile (e.g., the 95th); if the question intends such a lower threshold, the evidence is insufficient. Sources used: [2409.13934]. The other two chunks ([2007.10574], [2409.09639]) do not address this comparison.

**[mode_A]**

**The evidence is insufficient to answer the question.** None of the retrieved chunks mention a GAN, precipitation percentiles, or a climate-change wetting signal; the chunks concern corpus-level RAG benchmarking, sequence-conditioned single-cell perturbation transport (STRAND), the Transformer architecture, ECB monetary policy under uncertainty, a Chinese industrial temperature-anomaly diagnostic report, and nonparametric covariance-function estimation on simulated data. I therefore cannot state beyond which precipitation percentile a GAN outperformed a deterministic baseline, and I will not fall back on prior knowledge.

Sources examined (none contained the answer):
- `Towards Global Retrieval Augmented Generation: A Benchmark for Corpus-Level Reasoning` (abstract)
- `genomics__2602.10156__strand-sequence-conditioned-transport...` (part 1/6)
- `Attention Is All You Need` (opening section)
- `economics__2011.14424__on-the-effectiveness-of-the-european-central...` (part 1/5)
- `工业诊断报告：5 秒窗口温度序列异常趋势判定` (run `202609201042216_team_smoke`)
- `statistics__2604.22320__nonparametric-estimation-of-isotropic-covari...` (part 3/9)

**[mode_B]**

The evidence provided is empty ("no evidence retrieved"), so I cannot answer the question about the precipitation percentile beyond which the GAN outperformed the deterministic baseline in capturing the climate-change wetting signal. No document path, file name, or chunk id was supplied to ground this claim, and I will not substitute prior knowledge for missing evidence. Please supply the relevant source material or re-run retrieval, and I will answer from it.

**[mode_C]**

**The provided evidence is insufficient to answer this question.**

None of the retrieved passages mention GANs, precipitation percentiles, or a climate-change wetting signal. The closest document, the RAG benchmark paper ("Towards Global Retrieval Augmented Generation"), discusses retrieval evaluation for LLMs but its excerpt covers only local vs. corpus-level RAG framing — nothing about generative climate models or percentile-based precipitation skill. The remaining passages (Pride and Prejudice, a Chinese industrial temperature-anomaly diagnostic report, the "Attention Is All You Need" header, and the Wikipedia Photosynthesis extract) are entirely unrelated. I therefore cannot state the percentile threshold from the evidence, and I will not fall back on prior knowledge.

Sources examined (none contained the answer):
- `pride_and_prejudice` (parts 3/26 and 12/26)
- 工业诊断报告：5 秒窗口温度序列异常趋势判定 (`202609201042216_team_smoke`)
- `Attention Is All You Need` (title/author header only)
- `Photosynthesis` (Wikipedia plaintext extract)
- `Towards Global Retrieval Augmented Generation: A Benchmark for Corpus-Level Reasoning` (abstract only)

**[rerank]**

**Answer:** Beyond the 95th percentile of precipitation.

The evidence states that the GAN and the deterministic baseline had "relatively similar signals up to the 95th percentile of precipitation," and that "beyond the 95th percentile, the GAN substantially better captures the wetting signal," though both still underestimated its magnitude relative to CCAM.

**Source used:** arXiv paper [2409.13934] (chunk id [2409.13934], precipitation climate-change signal comparison passage).

**[rrf]**

The evidence only supports a comparison at the 99.5th percentile of precipitation: the GAN trained on future+historical periods captures ~97% of the average future increase in the 99.5th percentile, and the GAN trained on historical simulations captures ~77%, whereas both deterministic baselines capture only 63–65% — so at that percentile the GAN clearly outperforms them. However, the evidence does not state a percentile threshold "beyond which" the GAN clearly outperforms (no crossing point or lower percentile such as the 90th or 95th is given), so if the question asks for such a threshold, the retrieved evidence is insufficient to answer it; the only percentile documented is 99.5.

Sources used:
- [2409.13934] (chunk: GAN vs. deterministic baselines at the 99.5th percentile of precipitation, incl. Figure 2 caption)

**[vector]**

**Answer:** The 95th percentile. The evidence states that the GAN and deterministic baselines have relatively similar climate-change signals up to the 95th percentile of precipitation; beyond that percentile, the GAN substantially better captures the wetting signal (though both still underestimate its magnitude relative to CCAM).

**Source used:** [2409.13934] (provided evidence excerpt, including its reference to Figure 1c and Supplementary Figure S9).

</details>


## QK09 — `unanswerable`

**Q:** What is the recommended daily dosage of metformin for diabetic cats?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | — | — | 20.2 | 3453 | 0.27706 | 0 | 是 | **Insufficient evidence.** The retrieved passages do not contain an answer to the question about metformin dosage for diabetic cats. The evidence cons |
| `mode_A` | — | — | 30.9 | 589 | 0.20243999999999998 | 0 | 是 | **The evidence is insufficient to answer this question.** The retrieved evidence is a single excerpt from section 3.2.1 ("Clinician evaluation") of *L |
| `mode_B` | — | — | 11.5 | 501 | 0.19952000000000003 | 0 | 是 | The evidence is insufficient: the retrieved evidence block is empty ("no evidence retrieved"), so there is no document content about metformin or feli |
| `mode_C` | — | — | 65.8 | 415 | 0.19806500000000002 | 0 | 是 | The evidence is insufficient to answer this question. The retrieved chunk (clinical-medicine__2212.13138__large-language-models-encode-clinical-knowle |
| `rerank` | — | — | 14.2 | 680 | 0.20942 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved chunks mention metformin, cats, feline medicine, or veterinary dosing. The |
| `rrf` | — | — | 10.2 | 1055 | 0.217685 | 0 | 是 | The evidence is insufficient to answer this question. I reviewed all three provided sources: [2110.08918] covers ICU length-of-stay and mortality pred |
| `vector` | — | — | 12.9 | 1826 | 0.23804499999999998 | 0 | 是 | The evidence is insufficient to answer this question. None of the nine provided chunks ([2212.13138], [2110.08918], [2502.00306], [2203.15752], [2201. |

<details><summary>逐字答案全文</summary>

**[bm25]**

**Insufficient evidence.** The retrieved passages do not contain an answer to the question about metformin dosage for diabetic cats. The evidence consists of three unrelated sources: [2110.08918] (ICU length-of-stay and mortality prediction from clinical data), [2409.09639] (the GPC/m machine-learning precipitation dataset), and [2412.15058] (MultiverSeg interactive image segmentation). None of these mentions metformin, diabetes, cats, or any veterinary drug dosage. Sources consulted: [2110.08918], [2409.09639], [2412.15058]. Per the output contract, I am not falling back on prior knowledge to fill this gap.

**[mode_A]**

**The evidence is insufficient to answer this question.**

The retrieved evidence is a single excerpt from section 3.2.1 ("Clinician evaluation") of *Large Language Models Encode Clinical Knowledge* (arXiv 2212.13138). It describes a pilot framework for human evaluation of long-form LLM answers to consumer medical questions in the LiveQA, MedicationQA, and HealthSearchQA datasets, and refers to Table 2's summary of evaluation axes.

It contains no information about metformin, diabetes in cats, veterinary medicine, or any drug dosage whatsoever. Therefore I cannot provide the recommended daily dosage of metformin for diabetic cats from this evidence, and per the task contract I will not fall back on prior knowledge.

**Source used:** `clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md.md` (Part 2/8), Section 3.2.1.

**[mode_B]**

The evidence is insufficient: the retrieved evidence block is empty ("no evidence retrieved"), so there is no document content about metformin or feline diabetes to ground an answer. I cannot provide the recommended daily dosage without falling back on prior knowledge, which this task prohibits. No sources were used, because no source chunks were provided.

**[mode_C]**

The evidence is insufficient to answer this question. The retrieved chunk (clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md, part 2/8, section 3.2.1 "Clinician evaluation") discusses a pilot framework for clinician evaluation of long-form LLM answers on the LiveQA, MedicationQA, and HealthSearchQA datasets, and references Table 2 on evaluation axes. It contains no information about metformin, feline diabetes, or any drug dosage. No dosage recommendation can be derived from this evidence, and I will not supply one from prior knowledge.

Source used: clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md (section 3.2.1).

**[rerank]**

The evidence is insufficient to answer this question.

None of the retrieved chunks mention metformin, cats, feline medicine, or veterinary dosing. The diabetes-related content is limited to human contexts: [2201.03675] (A1C levels >6.5% for diabetes diagnosis), [2502.00306] (type 2 diabetes in female twins), [2412.15058] (diabetic retinopathy segmentation), [1904.11280] ("high glucose level"), and [2310.10981] (blood sugar lab values); the remaining chunks ([2110.08918], [2212.13138], [2301.08436], [2203.15752]) concern drug/NDC tables, model benchmarks, and unrelated data.

Sources reviewed: [2201.03675], [2502.00306], [1904.11280], [2412.15058], [2310.10981], [2110.08918], [2212.13138], [2301.08436], [2203.15752] — none contain the requested dosage information, so per the task constraints I make no further inference.

**[rrf]**

The evidence is insufficient to answer this question. I reviewed all three provided sources: [2110.08918] covers ICU length-of-stay and mortality prediction from clinical notes and time-series data; [2212.13138] contains biology/chemistry exam-style QA pairs (pharyngeal arches, Hardy-Weinberg equilibrium, gas laws); and [2502.00306] estimates generation costs for yes/no questions, descriptions, and ground-truth answers in a retrieval dataset pipeline. None of them mention metformin, cats, feline diabetes, or any veterinary dosing information. Since the evidence does not contain the answer, I am stopping here and not falling back on prior knowledge.

Sources reviewed: [2110.08918], [2212.13138], [2502.00306] — none relevant.

**[vector]**

The evidence is insufficient to answer this question.

None of the nine provided chunks ([2212.13138], [2110.08918], [2502.00306], [2203.15752], [2201.03675], [2301.08436], [2310.10981], [2412.15058], [1904.11280]) mention metformin, feline/veterinary medicine, or any drug dosage recommendation — they concern model benchmarks, drug/NDC code tables, human A1C–diabetes modeling, imaging datasets, and unrelated clinical snippets.

Sources used: none — no provided source contains information on metformin dosing in diabetic cats, so per the instructions I stop here rather than draw on prior knowledge.

</details>


## QK10 — `outofcorpus`

**Q:** How does the Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments?

| method | 检索命中 | 引用命中 | 时延 s | tok out | 成本 $ | 工具 | 弃答 | 答案摘要 |
|---|:--:|:--:|---:|---:|---:|---:|:--:|---|
| `bm25` | — | — | 6.4 | 677 | 0.20778 | 0 | 是 | The evidence is insufficient to answer this question. None of the three provided sources mentions the Herbert-Moulton collider benchmark, detector dri |
| `mode_A` | — | — | 40.3 | 783 | 0.211445 | 0 | 是 | The provided evidence does not contain the answer: none of the retrieved sources mention the Herbert-Moulton collider benchmark, detector drift, or pa |
| `mode_B` | — | — | 63.7 | 968 | 0.21619500000000003 | 0 | 是 | **The evidence is insufficient to answer this question.** None of the retrieved chunks mention a "Herbert-Moulton collider benchmark," detector drift, |
| `mode_C` | — | — | 1500 | None | 0.0 | 0 | 否 | (answer timed out after 300s budget with the full knowledge pack; recorded as failed cell — see REPORT for the timeout finding) |
| `rerank` | — | — | 17.1 | 1214 | 0.222505 | 0 | 是 | **The evidence is insufficient to answer this question.** None of the retrieved chunks mentions the "Herbert-Moulton collider benchmark," particle col |
| `rrf` | — | — | 7.0 | 513 | 0.2039 | 0 | 是 | The evidence is insufficient to answer this question. None of the three retrieved chunks mention the Herbert-Moulton collider benchmark, detector drif |
| `vector` | — | — | 6.8 | 615 | 0.20814 | 0 | 是 | The evidence is insufficient to answer this question. None of the retrieved chunks discuss a "Herbert-Moulton collider benchmark" or any method for qu |

<details><summary>逐字答案全文</summary>

**[bm25]**

The evidence is insufficient to answer this question. None of the three provided sources mentions the Herbert-Moulton collider benchmark, detector drift, or particle-physics detector calibration: [2303.00445] covers error mitigation in a 3-qubit contextual subspace method for HCl, [1911.02792] discusses coarse-grained molecular models, and [2005.14165] is a GPT-3-generated news article about a church denomination split. No source among these addresses the benchmark or methodology in question, so I cannot answer without falling back on prior knowledge, which the task forbids.

Sources consulted: [2303.00445], [1911.02792], [2005.14165] — none relevant to the question.

**[mode_A]**

The provided evidence does not contain the answer: none of the retrieved sources mention the Herbert-Moulton collider benchmark, detector drift, or particle-physics detector calibration. The evidence consists of: a RAG benchmark paper (Luo et al., "Towards Global Retrieval Augmented Generation"); a perovskite/GeSe solar-cell paper (materials__1712.01369, §III Electrical Properties); a MARL paper (AOAD-MAT); an ECB monetary-policy paper; an MLP-SLAM robotics paper; and an influenza epitope-analysis paper (Muñoz & Deem). I therefore cannot answer the question from this evidence.

Sources consulted (none relevant to the question): all six evidence chunks listed above.

Evidence is insufficient — stopping as instructed, without falling back on prior knowledge.

**[mode_B]**

**The evidence is insufficient to answer this question.**

None of the retrieved chunks mention a "Herbert-Moulton collider benchmark," detector drift, or particle physics experiments of any kind. The sources I examined cover unrelated topics: BERT's GLUE benchmark descriptions (`nlp__1810.04805__bert-pre-training-of-deep-bidirectional-transfor.md`, section B.1), ROUGE implementations for dialogue summarization (`nlp__2310.10981__instructive-dialogue-summarization-with-quer`, section A.1), multi-document summarization baselines (`nlp__2110.07844__modeling-endorsement-for-multi-document-abst`, section 6), tactile-based blind grasping disturbance compensators and references (`robotics__1709.02429__robust-object-manipulation-for-tactile-based`, sections 3.5 and References), and a database indexing paper's experimental evaluation (`databases__2009.10669__there-is-no-such-thing-as-an-index-or-the-ne`, section 6).

No source in the evidence addresses the question's subject, so per the output contract I make no fallback claim from prior knowledge.

**[mode_C]**

(answer timed out after 300s budget with the full knowledge pack; recorded as failed cell — see REPORT for the timeout finding)

**[rerank]**

**The evidence is insufficient to answer this question.**

None of the retrieved chunks mentions the "Herbert-Moulton collider benchmark," particle colliders, or any method for quantifying detector drift in particle physics experiments. The word "drift" appears only in unrelated senses: drift current density and drift resistivity in semiconductor physics ([1712.01369]), antigenic drift in an immunological affinity model ([q-bio-0408016]), and a qubit state drifting toward the maximally mixed state under bit-flip decoherence ([1311.2485]). The remaining chunks concern quantum circuit sampling and bootstrap distributions ([2303.00445]), Trotter decomposition ([2311.00487]), black hole horizons ([gr-qc-9805045]), and DFT+U calculations for transition-metal oxides ([2211.04977]).

**Sources examined (all provided evidence):** [1712.01369], [2303.00445], [1311.2485], [gr-qc-9805045], [2311.00487], [q-bio-0408016], [2211.04977] — none supports an answer, so I stop here and make no claim beyond the evidence.

**[rrf]**

The evidence is insufficient to answer this question. None of the three retrieved chunks mention the Herbert-Moulton collider benchmark, detector drift, or any particle-physics detector calibration methodology: [q-bio-0408016] covers influenza vaccine epitope cross-affinity, [2606.10843] covers seismic particle motion under subshear vs. supershear rupture, and [2303.00445] covers quantum error mitigation in a contextual subspace. Since the evidence contains no relevant material, I cannot describe how such a benchmark quantifies detector drift without falling back on prior knowledge, which the task prohibits. No source is cited in support of an answer because none of the retrieved sources addresses the question.

**[vector]**

The evidence is insufficient to answer this question.

None of the retrieved chunks discuss a "Herbert-Moulton collider benchmark" or any method for quantifying detector drift in particle physics experiments. The evidence consists of unrelated passages: an antigen-antibody statistical-mechanics model ([q-bio-0408016]), cosine distances between perturbation predictions ([2602.10156]), fault-rupture motion sensitivity ([2606.10843]), charged black-hole horizons in general relativity ([gr-qc-9805045]), DFT+U calculations for transition-metal oxides ([2211.04977]), Trotter decompositions in quantum simulation ([2311.00487]), qubit drift under bit-flip decoherence ([1311.2485]), and semiconductor drift current density ([1712.01369]). The closest lexical overlap is the word "drift" in [1311.2485] (qubit state drift) and [1712.01369] (drift current), but neither concerns collider detectors or the named benchmark. Because no source addresses the question, I cannot answer it without falling back on prior knowledge, which the task forbids.

</details>

## 一致性自检

| 检查 | 结果 | 详情 |
|---|---|---|
| 每 (qid,method) 都有结果 | ✅ | 0 缺失 |
| 无重复单元 | ✅ | ok |
| 无 error 单元 | ❌ | 1 个 error |
| 成本合计 = 各方法之和 | ✅ | sum(method)=14.9232 · manifest 未记总额 |
| 单元数 = 题数 × 方法数 | ✅ | rows=None vs 10×7=70 |
| provenance 完整 | ❌ | prompt_version=None seed=None |

---

*数字来自本 run 目录工件；缺失写“—/缺失”，未做任何评价性改写。*