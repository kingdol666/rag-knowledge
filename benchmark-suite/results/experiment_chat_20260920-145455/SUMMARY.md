# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-20 15:35 UTC · same 50-paper corpus · questions: 10 · tracks: a, b, c

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| BQ01 | a | 177.2 | 9 | 272145 | 3096 | 59968 | 1.468109 |
| BQ01 | b | 68.5 | 5 | 127376 | 1068 | 81088 | 0.704124 |
| BQ01 | c | 44.4 | 4 | 204994 | 697 | 128 | 1.042459 |
| BQ02 | a | 91.7 | 12 | 292481 | 2017 | 82880 | 1.5542699999999998 |
| BQ02 | b | 58.3 | 5 | 138090 | 736 | 68864 | 0.743282 |
| BQ02 | c | 54.0 | 3 | 159451 | 460 | 384 | 0.808947 |
| BQ03 | a | 202.9 | 16 | 378377 | 2720 | 191104 | 2.055437 |
| BQ03 | b | 24.1 | 4 | 36244 | 501 | 84800 | 0.23614500000000005 |
| BQ03 | c | 51.5 | 3 | 63637 | 650 | 95296 | 0.382083 |
| BQ04 | a | 112.7 | 12 | 305259 | 1833 | 53184 | 1.598712 |
| BQ04 | b | 30.7 | 3 | 67433 | 406 | 47680 | 0.371155 |
| BQ04 | c | 55.5 | 3 | 73564 | 412 | 86400 | 0.42132000000000003 |
| BQ05 | a | 73.0 | 10 | 135300 | 1451 | 161920 | 0.793735 |
| BQ05 | b | 21.4 | 4 | 68208 | 523 | 95296 | 0.40176300000000004 |
| BQ05 | c | 37.8 | 3 | 60989 | 475 | 97600 | 0.36562000000000006 |
| BQ06 | a | 187.7 | 10 | 219263 | 2267 | 153536 | 1.2297580000000001 |
| BQ06 | b | 37.3 | 3 | 46417 | 390 | 84928 | 0.28429899999999997 |
| BQ06 | c | 33.0 | 4 | 88461 | 633 | 112256 | 0.5142580000000001 |
| BQ07 | a | 108.4 | 7 | 127940 | 1593 | 91968 | 0.725509 |
| BQ07 | b | 52.6 | 5 | 69423 | 706 | 95424 | 0.41247700000000004 |
| BQ07 | c | 44.8 | 2 | 70713 | 360 | 47616 | 0.38637299999999997 |
| BQ08 | a | 97.4 | 5 | 131820 | 2154 | 45312 | 0.735606 |
| BQ08 | b | 95.4 | 6 | 76652 | 907 | 95424 | 0.453647 |
| BQ08 | c | 39.0 | 3 | 102617 | 455 | 58368 | 0.553644 |
| BQ09 | a | 200.1 | 13 | 282851 | 2606 | 127104 | 1.542957 |
| BQ09 | b | 60.5 | 4 | 67977 | 626 | 95424 | 0.403247 |
| BQ09 | c | 48.6 | 3 | 47621 | 488 | 111040 | 0.305825 |
| BQ10 | a | 164.2 | 8 | 266702 | 2336 | 43456 | 1.4136380000000002 |
| BQ10 | b | 92.1 | 5 | 142743 | 852 | 171136 | 0.820583 |
| BQ10 | c | 89.6 | 4 | 100044 | 611 | 108288 | 0.5696389999999999 |

**Totals**: latency avg 81.8s · tokens in 4224792 · out 34029 · cost $23.2986

## Verbatim answers

### [a] BQ01 — 177.2s, 9 tool calls, tokens out 3096

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

I now have the complete primary-source content. Here is the answer.

---

## How the Transformer Computes Attention, and Why It Replaces Recurrence and Convolution

**Source:** *Attention Is All You Need* (Vaswani et al., 2016), arXiv:1706.03762 — KB `计算机与人工智能` (Computer Science and AI), doc `artificial-intelligence__1706.03762__attention-is-all-you-need.md` (parts 1 & 2).

### 1. What an attention function is

An attention function maps a **query** and a set of **key–value pairs** to an output, where query, keys, values, and output are all vectors. The output is computed as a **weighted sum of the values**, where the weight assigned to each value is computed by a **compatibility function of the query with the corresponding key** (Section 3.2).

### 2. Scaled Dot-Product Attention (Section 3.2.1)

Inputs: queries and keys of dimension `d_k`, values of dimension `d_v`. The recipe:
1. Compute the **dot products** of the query with all keys,
2. **Divide each by √d_k** (the scaling factor),
3. Apply a **softmax** to obtain the weights on the values.

Batched into matrices Q, K, V, the output is:

$$\mathrm{Attention}(Q,K,V) = \mathrm{softmax}\!\left(\frac{QK^{T}}{\sqrt{d_k}}\right)V \quad \text{(Eq. 1)}$$

**Why the √d_k scaling:** the paper contrasts additive attention (a feed-forward net with one hidden layer) with dot-product attention. For small `d_k` the two perform similarly, but unscaled dot-product attention **underperforms additive attention for large `d_k`** — because for large `d_k` the dot products grow large in magnitude, **pushing the softmax into regions where it has extremely small gradients**. Scaling by 1/√d_k counteracts this. Dot-product attention was chosen anyway because, despite similar theoretical complexity, it is **much faster and more space-efficient in practice** since it can use highly optimized matrix-multiplication code.

### 3. Multi-Head Attention (Section 3.2.2)

Rather than one attention function over `d_model`-dimensional keys/queries/values, the model **linearly projects Q, K, V `h` times** with different learned projections to `d_k, d_k, d_v`; attention runs **in parallel** on each projected version, the `d_v`-dimensional outputs are **concatenated and projected** once more:

$$\mathrm{MultiHead}(Q,K,V) = \mathrm{Concat}(\mathrm{head}_1,\dots,\mathrm{head}_h)W^O,\quad \mathrm{head}_i = \mathrm{Attention}(QW_i^Q, KW_i^K, VW_i^V)$$

Rationale: **multi-head attention lets the model jointly attend to information from different representation subspaces at different positions**; with a single head, averaging inhibits this. In the paper: `h = 8`, `d_k = d_v = d_model/h = 64`; because each head is lower-dimensional, total cost ≈ single-head attention at full dimensionality. Ablations confirmed this matters — single-head attention was 0.9 BLEU worse than the best setting.

**Three applications in the model (3.2.3):** (a) *encoder–decoder attention* — queries from the previous decoder layer, keys/values from the encoder output; (b) *encoder self-attention* — Q, K, V all from the same place (the previous encoder layer), every position attends to all positions; (c) *decoder self-attention* — masked (illegal connections set to −∞ before softmax) so position *i* can only attend to positions ≤ *i*, preserving auto-regression.

### 4. Why it replaces recurrence and convolution (Sections 1, 2, 4 — §4 "Why Self-Attention")

The paper judges layer types on **three desiderata**: (i) **total computational complexity per layer**, (ii) **amount of parallelizable computation** (minimum number of sequential operations), (iii) **path length between long-range dependencies** — shorter paths make long-range dependencies easier to learn.

**Against recurrence.** Recurrent models factor computation along symbol positions, generating hidden state `h_t` as a function of `h_{t-1}` and the input at *t*. This **inherently sequential nature precludes parallelization within training examples**, which becomes critical at longer sequence lengths. As Table 1 shows:

| Layer Type | Complexity/Layer | Sequential Ops | Max Path Length |
|---|---|---|---|
| **Self-Attention** | O(n²·d) | **O(1)** | **O(1)** |
| Recurrent | O(n·d²) | O(n) | O(n) |
| Convolutional | O(k·n·d²) | O(1) | O(log_k n) |
| Self-Attention (restricted) | O(r·n·d) | O(1) | O(n/r) |

A self-attention layer **connects all positions with a constant number of sequentially executed operations**, whereas a recurrent layer needs **O(n)** sequential operations. Self-attention is also faster than recurrent layers **when sequence length n < representation dimensionality d** — typically true for word-piece/byte-pair sentence representations in MT.

**Against convolution.** A single convolutional layer with kernel width `k < n` **does not connect all pairs of input/output positions**; doing so requires a stack of `O(n/k)` layers (contiguous kernels) or `O(log_k(n))` (dilated), **increasing the longest path length**. Convolutional layers are generally **more expensive than recurrent layers by a factor of k**; separable convolutions reduce this to `O(k·n·d + n·d²)`, but **even with k = n, a separable convolution's complexity equals the combination of a self-attention layer plus a point-wise feed-forward layer** — exactly the Transformer's design. In the Transformer, the number of operations relating any two positions is **reduced to a constant**, versus linearly (ConvS2S) or logarithmically (ByteNet) growing with distance in the convolutional baselines.

**Novelty claim (Section 2):** the Transformer is **the first transduction model relying entirely on self-attention to compute representations of input and output without using sequence-aligned RNNs or convolution.** *(Note the trade-off the paper itself flags: constant path length comes "at the cost of reduced effective resolution due to averaging attention-weighted positions," counteracted by Multi-Head Attention.)* Because there is no recurrence and no convolution, **positional encodings** (sinusoidal functions of different frequencies — Eq. in 3.5) are added to the input embeddings so the model can use token order.

**Payoff (Abstract, §5.2, §6):** the architecture is "superior in quality while being more parallelizable and requiring significantly less time to train" — 28.4 BLEU on WMT 2014 EN–DE (beating prior best, including ensembles, by >2 BLEU), 41.8 BLEU EN–FR after 3.5 days on 8 GPUs; the base model trained in 12 hours, at a small fraction of prior training cost (Table 2: base 3.3×10¹⁸ FLOPs vs. e.g. ConvS2S 9.6×10¹⁸). A **side benefit** noted in §4: self-attention can yield **more interpretable models** — individual heads learn different tasks and exhibit behavior related to syntactic/semantic structure (Figures 3–5 show long-distance dependency and anaphora-resolution heads).

### Sources
- `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md` — KB `计算机与人工智能` (kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba`); Abstract, §1 Introduction, §2 Background, §3.2 Attention (3.2.1–3.2.3), §3.5 Positional Encoding, **§4 Why Self-Attention**, Table 1, §5.2.
- `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 2 of 2).md` — §6.2 Model Variations (head-count/k-dimension ablations), §6.3, §7 Conclusion.
- Corroborating copies in the "DeepRead baseline reproduction" indexes: `Corpus-Struct/...__s01.md`, `Corpus-Chunks800/...__k02.md`, `Corpus-Paras/...__p04003.md` (same paper, same claim that the Transformer is the first model relying entirely on self-attention without sequence-aligned RNNs or convolution).

**Certainty:** High — every claim above is quoted or directly paraphrased from the retrieved full text of the primary source, read end-to-end (no gap in the Section 4 argument).

### [b] BQ01 — 68.5s, 5 tool calls, tokens out 1068

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

The paper directly answers both parts.

**Attention computation:** An attention function maps a query and a set of key-value pairs to an output, where the weight assigned to each value is a compatibility function of the query with the corresponding key (Section 3.2). In the Transformer's Scaled Dot-Product Attention, queries and keys of dimension $d_k$ and values of dimension $d_v$ are packed into matrices Q, K, V, and the output is $\text{Attention}(Q,K,V) = \text{softmax}(QK^T/\sqrt{d_k})V$ — i.e., dot products of the query with all keys, divided by $\sqrt{d_k}$ to keep softmax gradients from vanishing at large $d_k$, then a softmax-weighted sum of the values (Equations 1, Section 3.2.1). This is run in parallel as Multi-Head Attention across several projected subspaces so the model can jointly attend to information from different representation subspaces and positions, plus masking (−∞ before softmax) in the decoder to preserve auto-regression (Sections 3.2.2, 3.2.3).

**Why it replaces recurrence and convolution:** Section 4 gives three desiderata — per-layer computational complexity, parallelizable computation (minimum sequential operations), and path length between long-range dependencies. A self-attention layer connects all positions with a constant number of sequentially executed operations, whereas a recurrent layer requires $O(n)$ sequential operations, so self-attention is faster whenever $n < d$ and allows far more parallelization (the abstract notes training in as little as twelve hours on eight P100 GPUs). Convolution is also less direct: a single layer with kernel $k < n$ cannot connect all position pairs, requiring a stack of $O(n/k)$ layers (or $O(\log_k n)$ for dilated convolutions), and convolutional layers are generally $k$ times more expensive than recurrent ones — even a separable convolution with $k=n$ merely equals a self-attention layer plus a point-wise feed-forward layer. Shorter maximum path lengths make long-range dependencies easier to learn, and the authors add interpretability of attention heads as a side benefit (Sections 1, 4, 7).

Files used: `artificial-intelligence__1706.03762__attention-is-all-you-need.md` (Sections 1, 2, 3.2, 4, 7).

### [c] BQ01 — 44.4s, 4 tool calls, tokens out 697

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

The Transformer computes attention by mapping "a query and a set of key-value pairs to an output"; the input queries and keys have dimension $d_k$ and values dimension $d_v$, and the model "compute[s] the dot products of the query with all keys, divide each by $\sqrt{d_k}$, and apply a softmax function to obtain the weights on the values," producing a weighted sum of the values. Scaling by $1/\sqrt{d_k}$ is used because "for large values of $d_k$, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients." It replaces recurrence and convolution because it is "the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention," and because convolutions make it harder to learn dependencies between distant positions—"linearly for ConvS2S and logarithmically for ByteNet"—whereas "in the Transformer this is reduced to a constant number of operations," with Multi-Head Attention counteracting the reduced effective resolution. The model also "allow[s] for significantly more parallelization," which lets it "be trained significantly faster than architectures based on recurrent or convolutional layers." Chunks used: `artificial-intelligence__1706.03762__attention-is-all-you-need__k04.md`, `__k05.md`, `__k06.md`, `__k02.md`, `__k19.md`, `__k20.md`.

### [a] BQ02 — 91.7s, 12 tool calls, tokens out 2017

**Q:** What defines NISQ technology and what is its central limitation?

I have sufficient evidence from the vector index (document body reads return 404 in this KB — the indexed chunks are the accessible layer).

## NISQ Technology — Definition and Central Limitation

**Source:** *"Quantum Computing in the NISQ Era and Beyond"* — John Preskill, Institute for Quantum Information and Matter / Walter Burke Institute for Theoretical Physics, Caltech, 30 July 2018. KB: `8284ae07-4651-4bed-8d3b-b475b9b5e7c9` (`Corpus-Struct`), with the same document also indexed in `e599315e-…` (`Corpus-Paras`), `d23002bd-…` (`Corpus-Chunks800`), and `1e6199ea-…` (自然科学与地球科学).

### What defines NISQ

**NISQ = Noisy Intermediate-Scale Quantum** — a term Preskill coined for the era of quantum technology we are entering now, before fault-tolerant quantum computing becomes available:

- **"Intermediate scale"** refers to the size of quantum computers available in the near term: **roughly 50 to a few hundred qubits**. 50 qubits is the significant milestone because that is beyond what can be simulated by brute force on the most powerful existing classical supercomputers.
- **"Noisy"** emphasizes that we will have **imperfect control over those qubits** — the gates are noisy and **unprotected by quantum error correction** (error correction is not used in the NISQ era because of its heavy overhead in qubit count and gate count).

### The central limitation

> **Noise in quantum gates limits the size of the quantum circuits that can be executed reliably.**

Concretely, with per-gate two-qubit error rates **above the 0.1% level** (and often much worse), one does not expect to execute a circuit containing many more than **~1000 gates (1000 fundamental two-qubit operations)** — because *"the noise will overwhelm the signal in a circuit much larger than that."*

Preskill states the consequence directly: *"That limitation on circuit size imposes a ceiling on the computational power of NISQ technology,"* and *"the imperfect gates in NISQ systems will severely limit their computational power, because circuits with many gates will be too noisy to give useful results."* Near-term experiments therefore operate with of order **100 qubits** and **circuit depth under 100, maybe much less**.

Put bluntly by the author: a 100-qubit quantum computer *"will not change the world"* — NISQ devices are useful tools for exploring many-body quantum physics and may find other applications, but the noise ceiling bounds what they can achieve.

### Caveat on retrieval

Chunk-level retrieval from the vector index worked well (top scores 0.78/0.75 for the limitation passages). Full-document readback via `kb_doc_read` returned **404 / 400** for this KB (`Corpus-Struct`) across all three parameter forms (`doc_id`, `path`, `kb_id`+`doc_path`) — the stored file paths resolve through the web proxy but are not registered under those keys, so my quotes above are drawn from the indexed chunk content rather than a fresh full-body read. The cited passages are verbatim from the source chunks and internally consistent across all four KB copies.

### [b] BQ02 — 58.3s, 5 tool calls, tokens out 736

**Q:** What defines NISQ technology and what is its central limitation?

**Answer** (from `quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond.md`, John Preskill, 2018):

NISQ stands for "Noisy Intermediate-Scale Quantum," a term the author coined to name the era of quantum computers with roughly 50 to a few hundred qubits — "intermediate scale" because 50 qubits already exceeds what brute-force classical simulation can handle, and "noisy" because we have imperfect control over the qubits and lack the protection of quantum error correction (Section 4.1). Its central limitation is noise: imperfect gate control means the per-gate two-qubit error rate is above 0.1% (and often much worse), so "the noise will overwhelm the signal" in circuits much larger than about 1000 gates, imposing "a ceiling on the computational power of NISQ technology" (Section 4.2). A related consequence, stated in the abstract and Section 5, is that NISQ results may be hard to validate — it can be difficult to confirm that the device is really giving the right answer.

### [c] BQ02 — 54.0s, 3 tool calls, tokens out 460

**Q:** What defines NISQ technology and what is its central limitation?

The retrieved chunks answer this directly. NISQ stands for "Noisy Intermediate-Scale Quantum," a term coined by John Preskill to describe the era of quantum computers with roughly 50 to a few hundred qubits — intermediate scale because 50 qubits is beyond what brute-force classical simulation can match, while "noisy" emphasizes that we will have only imperfect control over those qubits. Its central limitation is noise: the noise places serious limitations on what quantum devices can achieve in the near term, and because quantum error correction carries a heavy overhead cost that NISQ devices cannot yet afford, circuits are essentially limited to about 1000 gates before the noise overwhelms the signal. That limitation on circuit size imposes a ceiling on the computational power of NISQ technology.

Chunks used: `quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond__k07.md`, `__k08.md`, `__k00.md`, and `__k19.md`.

### [a] BQ03 — 202.9s, 16 tool calls, tokens out 2720

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

I have verified the facts from the source document. Here is the answer.

## MultiMedQA and Flan-PaLM's MedQA performance

**Source:** *Large Language Models Encode Clinical Knowledge* (Singhal, Azizi, Tu et al., Google Research / DeepMind; arXiv 2212.13138) — the Med-PaLM paper.

### What MultiMedQA is

MultiMedQA is a **benchmark for medical question answering** introduced in this paper to assess how well LLMs encode clinical knowledge. As the paper states, it combines:

- **Six existing open question-answering datasets:**
  - **MedQA** — US medical licensing exam (USMLE-style) questions
  - **MedMCQA** — medical entrance exam questions from India
  - **PubMedQA** — questions over biomedical research literature
  - **LiveQA** — consumer medical questions
  - **MedicationQA** — consumer medication questions
  - **MMLU clinical topics** — clinical subsets of the MMLU benchmark
- **Plus one newly introduced dataset, HealthSearchQA** — a free-response dataset of **3,375 commonly searched consumer medical questions** — bringing the total to **seven datasets**.

The benchmark spans three categories of questions: **medical exam, medical research, and consumer medical queries**. Alongside it, the authors propose a human-evaluation framework rating answers on axes including agreement with scientific consensus, correctness of comprehension/retrieval/reasoning, inappropriate or missing content, possibility and extent of harm, and bias.

### Flan-PaLM's performance on MedQA

Evaluated on MultiMedQA using a combination of **few-shot prompting + chain-of-thought (CoT) + self-consistency** prompting:

- **Flan-PaLM 540B achieved 67.6% multiple-choice accuracy on MedQA** (the 4-option, USMLE-style version).
- This **surpassed the previous state of the art by over 17%** — specifically, it exceeded the prior SOTA by **17.3%**.
- It surpassed the **DRAGON model** by **20.1%**, and beat the concurrent **PubMedGPT** (a 2.7B model) result of 50.3% on MedQA.
- On the **more difficult 5-option version of MedQA**, Flan-PaLM scored **62.0%**.

More broadly on MultiMedQA, Flan-PaLM achieved SOTA on **every multiple-choice dataset** — **67.6% on MedQA**, **57.6% on MedMCQA**, **79.0% on PubMedQA**, and the MMLU clinical topics.

### Important caveat

Despite the strong MCQ scores, the paper's **human evaluation found key gaps**: clinicians judged only **61.9% of Flan-PaLM's long-form answers** aligned with scientific consensus (vs. 92.9% for clinician answers), and **29.7% of answers were rated potentially harmful** (vs. 6.5% for clinicians). This motivated **instruction prompt tuning**, producing **Med-PaLM**, which improved consensus alignment to **92.6–92.9%** and reduced harmful answers to **5.8%** — though the authors note it still remained **inferior to clinicians**.

### Source references

- `生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md` (parts 1, 2, 3), KB `b28f0a25-1e1d-40ad-96b8-61bd2b093a28` ("生命科学与医学")
  - Part 1 — abstract, introduction, Section 3.1 (MultiMedQA composition: §3.1.1)
  - Part 2 — §4.1 "Flan-PaLM exceeds previous state-of-the-art on MedQA (USMLE) by over 17%" (the 67.6% / 17.3% / 62.0% figures)
  - Part 3 — §4.5 Human evaluation results (61.9% consensus, 29.7% harm)
- Corroborating indexed copies: `Corpus-Struct/…__s05.md` and `Corpus-Chunks800/…__k01.md` (same paper, chunked variants)

Note: the `mcp__plugin_rag-knowledge_kb-mcp__*` tool aliases returned a "read-only" notice; all retrieval was performed via the `mcp__kb-mcp__*` tools (`kb_list`, `kb_search_vector`, `kb_search_two_stage`, `kb_doc_read`).

### [b] BQ03 — 24.1s, 4 tool calls, tokens out 501

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**MultiMedQA** is a benchmark curated in this paper comprising seven medical question-answering datasets: six existing ones — MedQA, MedMCQA, PubMedQA, LiveQA, MedicationQA, and MMLU clinical topics — plus a newly introduced seventh dataset, HealthSearchQA (3,375 commonly searched consumer health questions). It spans medical exam, medical research, and consumer medical questions to assess LLMs' clinical knowledge and QA capabilities (`clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md`).

On **MedQA (USMLE)** with 4 options, Flan-PaLM 540B reached **67.6% accuracy**, exceeding the previous state of the art (PubMedGPT, 50.3%) by over 17 percentage points. Notably, this result came from self-consistency prompting — few-shot alone gave 60.3%, and CoT prompting provided no improvement over few-shot (§4.1, Table 7).

### [c] BQ03 — 51.5s, 3 tool calls, tokens out 650

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**Answer:**

MultiMedQA is a benchmark for medical question answering curated by the authors, spanning medical exam, medical research, and consumer medical questions. The retrieved chunks state that PaLM and its instruction-tuned variant, Flan-PaLM, were evaluated on MultiMedQA, and that with a combination of prompting strategies Flan-PaLM exceeded state-of-the-art performance on MedQA (USMLE), MedMCQA, PubMedQA, and MMLU clinical topics. On the MedQA (USMLE) benchmark specifically, Flan-PaLM (540B) reached **67.6% accuracy**, surpassing the prior state of the art by **over 17%**. The chunks also note that instruction tuning improved performance across all model sizes, with Flan-PaLM outperforming baseline PaLM on MedQA, MedMCQA, and PubMedQA.

**Chunk files used:**
- `Corpus-Chunks800/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k01.md`
- `Corpus-Chunks800/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k02.md`
- `Corpus-Chunks800/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k04.md`
- `Corpus-Chunks800/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k30.md`
- `Corpus-Chunks800/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k31.md`
- `Corpus-Chunks800/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k00.md`

### [a] BQ04 — 112.7s, 12 tool calls, tokens out 1833

**Q:** Which three independent ontologies subdivide the Gene Ontology?

Content readback confirmed against the source document.

## Answer

The Gene Ontology (GO) is subdivided into **three independent, non-redundant ontologies**, each covering a different biological aspect:

| # | Ontology | Abbreviation |
|---|----------|--------------|
| 1 | **Molecular Function** | MF |
| 2 | **Biological Process** | BP |
| 3 | **Cellular Component** | CC |

### Supporting evidence (verbatim from the source)

> "The Gene Ontology is a controlled vocabulary of terms to represent biology in a structured way. The terms are subdivided in **three distinct ontologies** that represent different biological aspects: **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)** (1). These ontologies are **non-redundant** and share a common space of identifiers and a well-specified syntax."

The same text continues: "Terms are linked to each other by relations to form a hierarchical vocabulary."

### Source references

- **Primary (full-text verified):** `生命科学与医学/genomics__1602.01876__primer-on-the-gene-ontology.md (part 1 of 2).md` — KB `生命科学与医学` (`b28f0a25-1e1d-40ad-96b8-61bd2b093a28`), §2 "What is the Gene Ontology?"
- **Corroborating vector hits (identical wording, independently indexed copies):**
  - `Corpus-Paras/genomics__1602.01876__primer-on-the-gene-ontology__p04000.md` — KB `Corpus-Paras` (`e599315e-...`), cosine **0.781**
  - `Corpus-Struct/genomics__1602.01876__primer-on-the-gene-ontology__s01.md` — KB `Corpus-Struct` (`8284ae07-...`), cosine **0.771**
  - `Corpus-Chunks800/genomics__1602.01876__primer-on-the-gene-ontology__k00.md` / `__k01.md` — KB `Corpus-Chunks800` (`d23002bd-...`), cosine **0.767 / 0.726**

### Provenance

The underlying work is **Gaudet, Škunca, Hu & Dessimoz, "Primer on the Gene Ontology"** (arXiv:1602.01876, January 2016). Note that the four `Corpus-*` KBs are DeepRead baseline reproduction indexes (documented `doc_count: 0`; vectors stored but the Nuxt-backed document-read route returns 404 for them — the web proxy on port 6789 resolved the path but reported "Document not found by id"). Verification of the actual document body therefore came from the `生命科学与医学` copy, which is the authoritative, readable source and uses identical wording.

### Certainty

**High** — the statement is a verbatim match across four independently indexed copies of the same document in three separate KBs, and the full document body was read back from one of them. Vector scores (0.73–0.78) are well above the P0 threshold, and the query phrasing ("subdivide the Gene Ontology") appears near-verbatim in the retrieved chunk. No conflicting answer appeared in the result set; the remaining hits (chemistry, power systems, LLM benchmarks) were unrelated and scored ≤0.58.

### [b] BQ04 — 30.7s, 3 tool calls, tokens out 406

**Q:** Which three independent ontologies subdivide the Gene Ontology?

The three independent ontologies are **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**. The primer states that GO's terms "are subdivided in three distinct ontologies that represent different biological aspects," which are non-redundant and share a common identifier space and syntax. Source: `genomics__1602.01876__primer-on-the-gene-ontology.md` (Section 2, and reaffirmed in Section 5.2, where field 9 denotes the term's sub-ontology).

### [c] BQ04 — 55.5s, 3 tool calls, tokens out 412

**Q:** Which three independent ontologies subdivide the Gene Ontology?

The retrieved evidence directly answers the question. Two top-scoring chunks from the primer state: "The terms are subdivided in three distinct ontologies that represent different biological aspects: **Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)**." These three ontologies are described as non-redundant, sharing a common space of identifiers and a well-specified syntax, with terms linked by relations to form a hierarchical vocabulary.

Sources: `Corpus-Chunks800/genomics__1602.01876__primer-on-the-gene-ontology__k00.md` and `Corpus-Chunks800/genomics__1602.01876__primer-on-the-gene-ontology__k01.md`.

### [a] BQ05 — 73.0s, 10 tool calls, tokens out 1451

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

I was unable to answer this question from the knowledge base. Here is an honest report of what happened rather than a fabricated answer.

## Retrieval attempt (executed in this session)

I ran the retrieval myself with the `kb_*` MCP tools, and **every call was refused by the server** with the response:

```
experiment read-only
```

Tools attempted, all returning the same refusal:

| Tool | Query / params | Result |
|---|---|---|
| `kb_search_vector` | "Unified Growth Theory historical European economic growth contradiction", top_k=8 | `experiment read-only` |
| `kb_search_two_stage` | "Unified Growth Theory European economic growth Malthusian stagnation industrial revolution" | `experiment read-only` |
| `kb_search` | "Unified Growth Theory economic growth Europe" | `experiment read-only` |
| `kb_search_vector` | "unified growth theory", top_k=5 (retry, narrower) | `experiment read-only` |
| `kb_search_vector` | "economic growth Europe history", top_k=5 (retry, broader) | `experiment read-only` |
| `kb_list` | `lightweight=true` | `experiment read-only` |
| `backend_status` | — | `experiment read-only` |

## What this means

- The kb-mcp server **is connected** (the tools resolve and return a structured message rather than a "no such tool" error), but it is running under a **read-only experiment guard that is rejecting even read operations** — including `kb_list` and `backend_status`, which touch no vector index at all. That points to a gate applied at the MCP server/transport layer, not a per-index or per-query restriction.
- Consequently I could **not** determine whether the corpus even contains material on Unified Growth Theory (Galor, Malthusian stagnation → post-Malthusian → modern growth regimes), European historical GDP series, or the relevant critiques.
- Because I never received any document content, **any answer I gave about the theory or its empirical contradictions would come from my own training knowledge, not from your knowledge base** — which is exactly what this task prohibits. So I am not giving one.

## Suggested next steps

1. **Lift the experiment guard**: check whether kb-mcp is being launched with a read-only/experiment flag (e.g. an env var or CLI switch set in `.mcp.json` at the repo root, or by whatever harness started this session). The string `experiment read-only` is almost certainly a literal configured response.
2. **Verify the MCP config** is `uv run --directory kb-mcp python server.py` and restart Claude Code afterwards — kb-mcp is a long-lived stdio process, so flag changes need a reconnect (project pitfall #15).
3. Re-run this query once reads are permitted; the search path I'd use is `kb_search_vector` cross-KB first, then `kb_search_two_stage`, then `kb_doc_read` on the top candidates to verify content before answering.

### [b] BQ05 — 21.4s, 4 tool calls, tokens out 523

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

**Answer:** According to Nielsen (2015), historical European growth contradicts Unified Growth Theory because Maddison's GDP data for both Western Europe (12 leading countries and the total of 30) and Eastern Europe show no evidence of the theory's central claims. The growth was hyperbolic — rising monotonically along a steadily increasing trajectory — rather than transitioning from a stagnant Malthusian regime to sustained growth, so there was no stagnation, no Malthusian trap, and therefore no "remarkable" or "stunning" escape (Galor's alleged takeoff). Europe is the decisive test case since it was the centre of the Industrial Revolution, the theory's purported "prime engine of economic growth," yet the Industrial Revolution had no visible impact on growth trajectories; around 1880–1900 growth was actually diverted to a *slower* trajectory rather than accelerating. The absence of Malthusian oscillations, and reciprocal-value plots (1/GDP) that form a decreasing straight line, are the evidence the author uses to argue the theory's three growth regimes are dissociated from the data.

**File used:** `economics__1512.08067__unified-growth-theory-contradicted-by-the-econom.md`

### [c] BQ05 — 37.8s, 3 tool calls, tokens out 475

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

Historical European economic growth contradicts Unified Growth Theory because Europe—especially Western Europe, the center of the Industrial Revolution—should have provided the theory's best confirmation, yet it does not. Analyzing Maddison's (2010) GDP data for the 12 leading and 30 total Western European countries, the study finds the theory's "prominent signature" (Galor's three regimes of growth) is missing, and that these regimes "have no relevance to the description, let alone to the explanation, of the mechanism of the economic growth"—there was no transition. In short, "the data tell one story while the Unified Growth Theory tells another and diametrically opposite story," leading the author to conclude the theory "needs to be thoroughly revised but most likely rejected."

Sources: `Corpus-Chunks800/economics__1512.08067__unified-growth-theory-contradicted-by-the-econom__k00.md`, `__k02.md`, `__k05.md`, `__k06.md`, `__k10.md`, `__k13.md`.

### [a] BQ06 — 187.7s, 10 tool calls, tokens out 2267

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

I now have comprehensive evidence from the full paper across all three parts. Here is my answer.

## Answer

**The primary physical factor is temperature — specifically the surface (near-surface) temperature, through its control on the atmosphere's saturation vapor pressure / water-vapor holding capacity.** Temperature is the controlling variable; the extreme-precipitation response is not governed by a single scalar but by the temperature-dependent *partial* ones below.

### The mechanism (thermodynamic core)

Precipitation extremes scale with column moisture, which temperature sets via the **Clausius–Clapeyron (C–C) relation**. In the paper's theoretical framework (Eq. 1), the surface precipitation rate in an extreme event is

$$P \simeq -\epsilon\{\omega(p)\,S(T,p)\}$$

where ε is precipitation efficiency, ω the vertical velocity (dynamics), and **S(T,p) = dq_s/dp along a moist adiabat — a function of temperature and pressure only (the thermodynamic term)**. Holding dynamics and efficiency fixed, extremes intensify with warming purely because the **saturation vapor pressure of water rises with temperature**, giving roughly **6–7 % K⁻¹** C–C scaling at typical surface temperatures.

### Temperature governs the *rate*, not just the sign

The most direct evidence that temperature is the dominant control is that the paper's central quantitative result is a **temperature-dependence of the sensitivity itself** (Sections 3 & 7):

| Regime | Sensitivity of extremes |
|---|---|
| **Above ~295 K** (warm, present-day tropics) | ~**6–7 % K⁻¹** — follows C–C scaling; dynamics/efficiency contributions small |
| **Below ~295 K** (colder climates) | Sensitivity **varies widely with temperature and accumulation period**; instantaneous extremes rise at **~double the C–C rate** (~14 % K⁻¹) |

The sub-295 K amplification arises because **precipitation efficiency increases with warming** (faster hydrometeor fall speed as precipitation shifts from solid to liquid), adding a microphysical term on top of the thermodynamic one. Snowfall extremes are likewise controlled by the **climatological temperature relative to the rain–snow transition** (optimal temperature ≈ −2 °C by liquid-water equivalent, ≈ −4 °C by snow depth): snowfall extremes *decrease* where mean temperature is above that optimum and *increase* below it.

### Why this is "primary" rather than "sole"

The paper is explicit that thermodynamics is the **only robust and always-understood contribution**, while dynamics and precipitation efficiency are secondary and regime-dependent:
- **Thermodynamic** contribution — "robust and well understood," always gives intensification with warming.
- **Dynamical** (ω) — matters mainly in the tropics (mesoscale convective organization, tropical cyclones, MJO), poorly resolved by global models.
- **Microphysical** (ε) — matters mainly below 295 K and is microphysics-scheme dependent.

This temperature dependence is also what explains the **stronger tropical sensitivity (~9–11 % K⁻¹ constrained) versus extratropical (~4–6 % K⁻¹)**: the tropics are warmer, sitting in the C–C-scaling regime, whereas colder environments deviate from it.

### Practical implication
Because temperature sets the moisture capacity, the paper's headline constraints are the sensitivities expressed in **% K⁻¹**: observations give a global land sensitivity of **8 % K⁻¹ (90% CI 5–10 % K⁻¹)**; CMIP5 multimodel medians are **6 % K⁻¹** (extratropics) and **11 % K⁻¹** (tropics, observationally constrained).

---

### Sources

- **O'Gorman, P. A. — "Precipitation extremes under climate change"** (arXiv:1503.07557), KB `自然科学与地球科学` (kb_id `1e6199ea-f380-44e2-94fc-d431f0f9bb6b`):
  - `自然科学与地球科学/climate-science__1503.07557__precipitation-extremes-under-climate-change.md (part 1 of 3).md` — Abstract; §1 Introduction ("increases in the saturation vapor pressure of water"); §3 Theory (Eq. 1, thermodynamic vs. dynamical vs. microphysical contributions; C–C scaling 6–7 % K⁻¹).
  - `... (part 2 of 3).md` — §6 Snowfall extremes (optimal temperature −2 °C/−4 °C); §7 Duration (Clausius–Clapeyron above vs. ~2× C–C below 295 K); §8 Conclusions ("The thermodynamic contribution is the easiest to understand and always gives an intensification with warming").
- Cross-confirmed via vector search (scores 0.66–0.73) in both the primary KB and the DeepRead baseline indices (`Corpus-Chunks800`, `Corpus-Paras`, `Corpus-Struct`), which contain the same source document.

*Retrieval note: MCP `kb-mcp` was connected and healthy; all retrieval performed with `kb_search_two_stage`, `kb_search_vector`, and `kb_doc_read`.*

### [b] BQ06 — 37.3s, 3 tool calls, tokens out 390

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

The dominant control is thermodynamic: the increase in the atmosphere's saturation vapor pressure (moisture-holding capacity) with warming, i.e. Clausius–Clapeyron scaling, which gives roughly 6–7% K⁻¹ and is robust and well understood (O'Gorman, §3 and Conclusions). The response is decomposed into thermodynamic, dynamical (changes in vertical velocity ω), and microphysical (precipitation-efficiency ε) contributions, but the thermodynamic term is the one that always intensifies precipitation extremes with warming. Dynamical and precipitation-efficiency effects can matter regionally (tropics, subdaily durations below ~295 K, orographic/snowfall cases), yet in the extratropics the simulated increase "is close to the thermodynamic contribution at all latitudes, and there is little dynamical contribution from changes in vertical velocities."

Source: `climate-science__1503.07557__precipitation-extremes-under-climate-change.md` (O'Gorman, "Precipitation extremes under climate change").

### [c] BQ06 — 33.0s, 4 tool calls, tokens out 633

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Retrieved evidence is insufficient.**

I could not answer this question from retrieved evidence. Both dense-retrieval calls I issued against `kb_id="Corpus-Chunks800"` (top_k=10, score_threshold=0) — the first with the question verbatim, the second rephrased around precipitation-extreme intensification and Clausius–Clapeyron scaling — returned no chunk payloads at all. Instead each call returned only the notice `experiment read-only`, which is a sandbox/tooling message, not index content.

Because zero chunks were returned, there is no text to ground an answer in and no chunk file names to cite. Any statement about which physical factor controls the response of precipitation extremes to climate change (e.g., atmospheric moisture / temperature scaling) would have to come from outside the retrieved evidence, which the task explicitly forbids. Recommendation: verify that the retrieval tool is actually permitted to read `Corpus-Chunks800` in this environment, then re-run the query; I can answer as soon as real chunks are returned.

### [a] BQ07 — 108.4s, 7 tool calls, tokens out 1593

**Q:** What is MameLoshnLM and what parameter scale does it have?

I have everything needed, confirmed across multiple independent retrievals.

## Answer

**MameLoshnLM** is the **first open-source 8B-parameter language model built specifically for Yiddish** — reported as **8 billion parameters**.

### What it is
- **Purpose:** A Yiddish-specific LLM addressing the language's limited digital presence and the scarcity of reliable evaluation resources. It is intended to serve Yiddish's roughly one million speakers and the academic community studying Yiddish-language culture.
- **Construction:** It is produced by **continued pretraining of Llama 3.1 8B** on a Yiddish corpus, using a causal language-modeling objective (bfloat16, 8-bit AdamW, LR 2×10⁻⁵, cosine schedule with 2% warmup, weight decay 0.01, one epoch, max sequence length 1,024 tokens). Since it continues from Llama 3.1 8B, it inherits the 8B parameter scale.
- **Authors/affiliations:** Uri Katz, Omer Goldman, Tomasz Limisiewicz, Reut Tsarfaty, Noah A. Smith — Bar-Ilan University, University of Cambridge, University of Washington, Allen Institute for AI.

### Supporting resources introduced with it
- **Oytser** — a high-quality Yiddish pretraining corpus combining contemporary web-native sources with literary materials.
- **Kashes** — a multi-task Yiddish benchmark spanning translation, linguistic analysis, information extraction, and language understanding.

### Report context
Across the benchmark, MameLoshnLM **outperforms open baselines of similar scale** (Llama 3.1 8B, Qwen3 8B, BLOOMZ 7B, Gemma-2 9B, EuroLLM 9B). The paper's key finding is that general multilingual models produce an "intelligible but systematically reduced" Yiddish, while MameLoshnLM better captures native lexical/morphological patterns (e.g., loshn-koydesh Hebrew/Aramaic vocabulary and Yiddish-specific morphology) — pointing to a broader failure mode of noisy web-scale multilingual data for low-resource languages.

### Source references
- KB: **计算机与人工智能** (`b1199132-e4d4-4305-8c2e-82dc1753b0ba`)
- Document: `nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md` (parts 1–4 of 4), derived from *"MAMELOSHNLM: Yiddish Language Model and Evaluation Benchmark"* (arXiv 2608.05850)
  - **Part 1** — Abstract & Introduction: "the first open-source 8B-parameter language model built specifically for Yiddish"; "we continue pretraining Llama 3.1 8B to obtain MAMELOSHNLM"; §6 Experimental Setup (baselines of similar scale); training hyperparameters chunk.
  - **Part 2** — §8 Analysis (Loshn-koydesh and morphology probes vs. Llama 3.1 8B, Table 5).
  - **Part 4** — §E.8 Summary of All Metrics (Table 12 comparison).

**Certainty:** High — the parameter scale (8B, inherited from Llama 3.1 8B) and the definition are stated explicitly and consistently across the abstract, introduction, and experimental setup, and were confirmed by both metadata search and vector/two-stage semantic retrieval. No conflicting parameter figures appeared for this model.

### [b] BQ07 — 52.6s, 5 tool calls, tokens out 706

**Q:** What is MameLoshnLM and what parameter scale does it have?

**MAMELOSHNLM** is presented in *"MAMELOSHNLM: Yiddish Language Model and Evaluation Benchmark"* (`nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md`) as the first open-source large language model for Yiddish, named after the traditional Yiddish term "mame-loshn" ("mother tongue"). It is an **8B-parameter** model (Llama-3.1-8B scale): it was produced by continued pretraining of **Llama-3.1-8B** on a Yiddish-dominant corpus (~5.7B tokens, 72% Yiddish words / 28% English C4) for one epoch on a single H200 GPU (~207 GPU-hours). The paper compares it against baselines of "similar scale" — Llama 3.1 8B, Qwen3 8B, BLOOMZ 7B, Gemma-2 9B, and EuroLLM 9B — and reports that it achieves the best average score (62.6) across 14 evaluations.

### [c] BQ07 — 44.8s, 2 tool calls, tokens out 360

**Q:** What is MameLoshnLM and what parameter scale does it have?

MAMELOSHNLM is the first open-source large language model built specifically for Yiddish, named after the traditional Yiddish term "Mame-Loshn" ("mother tongue") evoking the language's intimate connection to home and family. It is an **8B-parameter** model, produced by continued pretraining and reportedly outperforming strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks. It was released together with two supporting resources: Oytser, a new Yiddish pretraining corpus, and Kashes, a benchmark for evaluating Yiddish LMs.

Cited chunks: `Corpus-Chunks800/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu__k00.md`, `..._k12.md`, `..._k02.md`.

### [a] BQ08 — 97.4s, 5 tool calls, tokens out 2154

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

I retrieved the full document and confirmed it directly answers the question. Here is the answer.

---

## How Oxygen Redox Contributes to Battery Cathode Capacity

The knowledge base contains a directly relevant review — **"Oxygen redox in battery cathodes: A brief overview"** by M. Hussein N. Assadi & Dorian A. H. Hanaor (arXiv:2408.09942), held in the **工程与能源 (Engineering & Energy)** KB.

### 1. The core mechanism: anionic charge compensation

In conventional cathodes (LiTMO₂, TM = Ni/Mn/Co), charge is balanced by transition-metal oxidation:

```
LiTM³⁺O₂  —charging→  Li₍₁₋ₓ₎TM³⁺₍₁₋ₓ₎TM⁴⁺ₓO₂ + xLi⁺ + xe⁻        (1)
```

But many cathodes deliver **overcapacity exceeding the transition-metal oxidation limit**. Oxygen redox explains this: oxide anions O²⁻ donate electrons during charging — acting as reducing agents — which **compensates for the absence of oxidizable transition metals**. The reversible process is summarized as:

```
O²⁻  ⇌  (O₂)ⁿ⁻                                                     (2)
```

or, alternatively, as the formation of electron holes on oxygen (avoiding O₂ gas evolution).

### 2. Why it works: "orphaned" O 2p states

The enabling structural feature is **Li-excess (or Na-excess) environments**. In normal LiTMO₂, every O is coordinated by 3 TM + 3 Li. TM–O hybridization pulls the bonding O 2p states down to the bottom of the valence band (~10 eV below E_F). In **Li-excess Li₂TMO₃**, the TM layer also contains Li, so some O ions are coordinated by **fewer than three TM ions** (Li–O–Li coordination). These avoid TM s/p hybridization, leaving **non-bonding, "orphaned" O 2p states** close to the Fermi level — comparable in energy to the non-bonding TM t₂g states. Both O and TM can then donate/accept electrons during redox.

Example reaction showing mixed cationic/anionic redox in Li₄Mn₂O₅:

```
Li₄⁺Mn₂³⁺O₅²⁻ → 4Li⁺ + 4e⁻ + Mnₓ⁴⁺Mn₂₋ₓ⁵⁺O₅₋ₓ²⁻Oₓ¹⁻          (3)
```

where x is the extent of oxygen participation. Mn³⁺→Mn⁴⁺ oxidation occurs first, and **additional de-lithiation capacity is accommodated by oxygen oxidation**.

### 3. Capability depends on structure and TM

The extent of oxygen redox varies with crystal structure and transition-metal type:

- **Li₂MnO₃** — Mn stays +4 (its t₂g frontier level is too low to oxidize), so the capacity is attributed **almost entirely to oxygen redox**.
- **Li-excess disordered spinel-type cathodes** — where oxygen redox was first found to contribute significantly (attributed to orphaned O states from O ions with <3 coordinating TMs).
- **Ilmenite-type NaTMO₃** — here O redox arises from **under-coordination**: O is coordinated by only 2 TM + 2 Na ions. Na₂₋ₓRuO₃ shows ~180 mAh g⁻¹ (~1.4 e⁻ per formula unit), with **~0.4 e⁻ of extra capacity from reversible oxygen redox**, plus a voltage rise from 2.2 V to 3.4 V — indicating O redox can operate at **higher potential than TM redox alone**.

DFT survey results (O 2p population in −2 eV < E < E_Fermi, and predicted potential):

| 3d NaTMO₃ | NaVO₃ | NaCrO₃ | NaMnO₃ | NaFeO₃ | NaCoO₃ | NaNiO₃ |
|---|---|---|---|---|---|---|
| O 2p (e) | 0.17 | 1.43 | 1.23 | 0.34 | 0.59 | 0.78 |
| Potential (V) | 5.91 | 4.24 | 4.53 | 5.18 | 3.49 | 3.98 |

| 4d NaTMO₃ | NaNbO₃ | NaMoO₃ | NaTcO₃ | NaRuO₃ | NaRhO₃ | NaPdO₃ | NaAgO₃ |
|---|---|---|---|---|---|---|---|
| O 2p (e) | 2.58 | 0.16 | 0.38 | 1.40 | 1.50 | 2.10 | 2.51 |
| Potential (V) | 4.95 | 2.62 | 2.90 | 3.72 | 4.08* | 4.08 | 4.66 |

**Oxygen redox is more dominant in 4d (fifth-row) transition-metal oxides**, due to higher TM–O covalency that increases 4d–2p hybridization and raises O 2p population near the Fermi level. NaVO₃/NaFeO₃ (>5 V) and NaNbO₃/NaAgO₃ (>4 V) are predicted as high-voltage O-redox cathodes.

### 4. The trade-off: capacity gain vs. O₂ release

Although oxygen redox **increases cathode capacity**, the reduced O ions have a strong tendency to bond to each other and **leave the lattice as O₂ gas**. This is both a **fire hazard** and a cause of **rapid, permanent capacity fade**. Mitigation strategies against O₂ release — such as **fluorination** — must be implemented if the extra oxygen-redox capacity is to be used. This is also tied to the capacity loss often observed after initial cycling.

### 5. Computational caveat

Directly probing anionic redox is not possible; DFT is the main approach, via density-of-states analysis. Because cathode materials are strongly correlated, **standard GGA is insufficient** — Hartree-Fock hybrid functionals or Hubbard-corrected (GGA+U) methods are needed, though choosing the mixing parameter α or U_eff remains challenging.

---

### Sources

- **Primary source (full document):** 工程与能源 KB (`8fa4db59-adde-4d6d-9fdb-2c375400e631`) — `materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overvie.md` (parts 1 & 2 of 2). Sections: Abstract, §1 Introduction, §2 Anionic Redox in Battery Electrode Materials, §4 Oxygen Redox in 3d and 4d Ilmenite-type NaTMO₃, §5 Summary.
- Assadi, M.H.N.; Hanaor, D.A.H. — *Oxygen redox in battery cathodes: A brief overview*, arXiv:2408.09942.

**Note on corpus structure:** the same paper is indexed in three parallel baseline collections — `Corpus-Chunks800`, `Corpus-Struct`, and `Corpus-Paras` — which are DeepRead reproduction indices (0 documents reported at KB level), plus the canonical copy in 工程与能源. All content above is drawn from the canonical 工程与能源 copy.

### [b] BQ08 — 95.4s, 6 tool calls, tokens out 907

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

**Answer (based on `materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overvie.md`):**

Oxygen (anionic) redox contributes extra capacity by having oxide anions (O²⁻) donate electrons during charging, compensating for the absence of oxidizable transition metals and allowing capacities that exceed the transition-metal oxidation limit (typically ~200–300 mAh/g theoretical). This is enabled in Li-excess/Na-excess or under-coordinated structures where O 2p states are "orphaned" (unhybridized, e.g. Li–O–Li coordination) and lift close to the Fermi level, becoming electrochemically labile; the paper reports the ~0.4 extra electron capacity in Na2−xRuO3 and labile O 2p populations for ilmenite-type NaTMO3 compounds. However, the mechanism is double-edged: reduced O ions tend to bond and leave the lattice as O2 gas, causing irreversible capacity fade, voltage fade, and a flammability hazard, so mitigation such as surface fluorination is needed. The paper also notes directly probing anionic redox is not possible, so DFT with higher-level functionals (HF hybrid, GGA+U) is the main route. The companion file `materials__2211.04977__design-of-battery-materials-via-defects-and.md` also references anionic-redox high-capacity cathodes (e.g. Y-doped Na2ZrO3) and shows O-redox voltage regions in doped Li2MnO3.

### [c] BQ08 — 39.0s, 3 tool calls, tokens out 455

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

Oxygen redox contributes to cathode capacity by allowing oxide anions (O²⁻) to donate electrons during charging, thereby acting as reducing agents that compensate for the absence of oxidizable transition metals; this "may allow greater energy storage capacity in battery electrodes than would otherwise be theoretically predicted" (`...__k03.md`). The retrieved abstract chunk likewise states that "the participation of oxygen or other anionic species in redox activities in cathode materials for lithium and sodium-ion battery systems is known to play a role in governing the useful capacity of these batteries" (`...__k00.md`). The summary chunk adds that oxygen redox "was discovered to significantly contribute toward the overall battery capacity in Li-excess disordered spinel-type cathodes," with the extent varying by crystal structure and transition-metal type (`...__k23.md`, and its duplicate `...__k22.md`). A related chunk notes that actual cathodes can deliver "an overcapacity exceeding the transition metal oxidation limit," motivating investigation of anionic participation (`...__k01.md`).

### [a] BQ09 — 200.1s, 13 tool calls, tokens out 2606

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

# MLP-SLAM: The Problem It Addresses and How

**Source:** Li, T. & Sun, W., *"MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping"* (arXiv:2410.10669)
KB: 计算机与人工智能 · doc_path: `robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou.md` (parts 1 & 2)

## The problem

Visual SLAM systems (ORB-SLAM2/3, LSD-SLAM, DSO) are built on a **static-world assumption**. They achieve high precision in scenes with few dynamic objects, but **their accuracy degrades in dynamic environments** — scenes crowded with movable objects like pedestrians, cars, and buses, which are common outdoors. The paper targets exactly this **degradation of V-SLAM in dynamic environments** (Abstract; Sec. I; Sec. VI Conclusions).

The paper characterizes two deficient prior approaches:

- **Type I — pure geometric methods** (epipolar error, reprojection error, intensity, depth, optical flow): not general, prone to information loss.
- **Type II — semantics-only methods** (e.g., DynaSLAM with Mask R-CNN): discard *all* features inside a dynamic-class bounding box/mask. This **misclassifies genuinely static objects** — e.g., parked cars on the roadside and highway guardrails get removed as "dynamic," causing information loss and even worse ATE (DynaSLAM's average ATE 2.43 m vs. ORB-SLAM2's 1.99 m). It is also slow (519.37 ms) due to Mask R-CNN.
- **Type III — hybrid (mainstream)**: prior class info from YOLO-style detectors plus *partial* geometric cues. These "rely on only partial geometric information" (only epipolar error, or only reprojection error), and **require manual parameter tuning, lack generality, and are laborious to fine-tune**.

A second, methodological problem: there is **no public dataset for directly evaluating dynamic/static feature-point classification**. Evaluation was done *indirectly* via SLAM metrics (ATE/RTE/RRE), which is **inaccurate and unreliable because of RANSAC randomness** in camera pose estimation.

## How MLP-SLAM addresses it

**Core idea:** an MLP-based real-time **stereo** SLAM system (built on ORB-SLAM2 with an added dynamic/static discriminator module) that uses **complete geometric information** to classify dynamic vs. static feature points — claimed as the **first machine-learning-based dynamic/static feature discriminator in SLAM**, and doing so **without any manual parameter configuration**.

**Pipeline (Sec. III-D, IV):**
1. **Feature extraction + detection/tracking** — ORB features on stereo images; **YOLOv7 + Deep SORT** on the left image (chosen over semantic segmentation to cut latency, and over CFP-SLAM's EKF+Hungarian for better tracking).
2. **Depth Filter Module (DFM)** — compensates for the looser boxes of object detectors. It computes mean depth μ_d and std δ_d of features in the box and drops features outside [μ_d − ηδ_d, μ_d + ηδ_d], treating them as static background (η = 1.2). This is the key fix for the "parked car" false-positive problem.
3. **Coarse estimation** — features outside bounding boxes plus DFM-filtered static features give a rough camera pose by minimizing reprojection error.
4. **MLP module** — for each remaining in-box feature, a 3-D input vector v_i = {e_I, e_D, e_Re} is formed: **image intensity error, epipolar error, and reprojection error**. The MLP (input 3 → hidden → 2-class output; zero-mean normalized; Adam, lr 0.1, MultiStepLR γ=0.1, 150 epochs, batch 8; TensorRT with fixed input shape (200,3)) labels each point static (0) or dynamic (1). Inference is only **0.18 ms**. Using all three cues is the "complete geometric information" that prior partial-cue methods lacked.
5. **Fine estimation** — camera pose is refined using the combined static set (out-of-box features + DFM-filtered + MLP-classified-static).

**The dataset contribution:** a publicly released dataset of **>50,000 manually labeled feature points** (from KITTI Odometry sequences 00/01, 1:1 static:dynamic ratio, 70/20/10 train/test/val split), enabling **direct** evaluation of discriminators instead of indirect RANSAC-contaminated SLAM metrics.

## Reported results

- **Classification (Table I):** MLP 87.71% accuracy / 87.64 F1 vs. SVM 84.19/84.58, PointSLOT-like 81.36/81.43, CFP-SLAM-like 73.61/71.10, epipolar-only 60.10/61.32.
- **Accuracy (Table II):** lowest average ATE on KITTI Odometry — **1.48 m** vs. ORB-SLAM2 1.99, DynaSLAM 2.43, DynaSLAM II 1.77. Best on sequence 00 (0.79), which is rich in parked static cars — evidence the MLP identifies *real* dynamic objects. Also lowest average on KITTI360 (3.42 vs. 3.40/3.92 etc., Table III).
- **Speed (Table IV/V):** **62.81 ms/frame** — fastest among dynamic SLAM systems (DynaSLAM 519.37, DynaSLAM II 80.15, VDO-SLAM 86.97, PointSLOT 73.6), only 17.50 ms/frame over its ORB-SLAM2 base.
- **Ablation (Table VI):** object-tracking-only 2.67 → MLP-only 1.97 → both **1.48**, confirming the MLP is the dominant contributor and combines best with tracking.

**Notable limitations stated by the authors:** it is stereo-only in experiments (though extensible to monocular/RGB-D); the MLP was trained only on KITTI Odometry and evaluated on unseen KITTI360; DynaSLAM II was not run locally (results taken from its original paper).

**Sources:** `kb_search` (metadata hit, score 23) and `kb_search_two_stage` (chunk retrieval), then full reads of both document parts in KB `b1199132-e4d4-4305-8c2e-82dc1753b0ba` (计算机与人工智能).

### [b] BQ09 — 60.5s, 4 tool calls, tokens out 626

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**Answer:**

MLP-SLAM addresses the degradation of visual (stereo) SLAM accuracy in highly dynamic outdoor environments crowded with movable objects such as pedestrians, cars, and buses, where static-world-assuming systems like ORB-SLAM2 lose precision. It tackles the limitations of prior dynamic-SLAM approaches: geometric methods (Type I) are not general, and semantic/detection-based methods like DynaSLAM (Types II/III) discard all feature points inside dynamic-class masks — wrongly deleting genuinely static points such as parked cars and guardrails — and require laborious manual parameter tuning. Its solution is an MLP-based discriminator that classifies each feature point as dynamic or static using *complete* geometric information rather than a hand-tuned subset, requiring no manual parameter configuration and avoiding information loss; the system also releases a public dataset of 50,000+ feature points from KITTI Odometry to evaluate such discriminators directly, and reports the highest average precision and fastest speed on KITTI Odometry and KITTI360.

**File used:** `robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou.md`

### [c] BQ09 — 48.6s, 3 tool calls, tokens out 488

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**Answer:**

MLP-SLAM addresses the problem that V-SLAM systems achieve high precision only in environments with few dynamic objects, while their performance degrades in settings with numerous movable objects such as pedestrians, cars, and buses common in outdoor scenes. It proposes an MLP-based real-time stereo SLAM system to address SLAM system degradation in dynamic environments, using an MLP model to distinguish dynamic from static feature points. Static feature points — those outside bounding boxes of potential dynamic objects (filtered by a Depth Filter Module) and classified as static by the MLP model — are used in the optimization stage by minimizing re-projection error. It is built on ORB-SLAM2 as its foundation and compared against DynaSLAM and modified VDO-SLAM on KITTI360.

**Chunks used:** `robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou__k00.md`, `__k23.md`, `__k03.md`, `__k18.md`, `__k10.md`

### [a] BQ10 — 164.2s, 8 tool calls, tokens out 2336

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

I found the source document and read all three parts. Here is the answer.

## Strategies for Tumor Control Under Immune Evasion and Chemotherapy Resistance

**Source:** Mokari, N. & Morsky, B. (Florida State University), *"Strategies for tumor elimination and control under immune evasion and chemotherapy resistance"* — KB `生命科学与医学` (`b28f0a25-1e1d-40ad-96b8-61bd2b093a28`), document `生命科学与医学/immunology__2604.01385__strategies-for-tumor-elimination-and-control.md (parts 1–3 of 3)` (arXiv 2604.01385).

The paper builds an ODE model (extending Kuznetsov et al. 1994) with three state variables — effector cells (E), immune-resistant tumor cells (T₁), immune-sensitive tumor cells (T₂) — under two distinct immune-evasion mechanisms: **immune checkpoint regulation** (PD-L1/PD-1) and **reduced antigen presentation**.

### 1. The core finding: combination immuno-chemotherapy is superior to either alone

- **Immunotherapy alone is generally insufficient.** "Although immune control may occasionally suppress tumor growth, immune dynamics alone are generally insufficient to fully eliminate the tumor" (part 3, §3.3).
- **Chemotherapy significantly enlarges** the parameter region corresponding to tumor control or tumor-free equilibria — it reduces tumor burden and directly targets resistant subpopulations, while immunotherapy enhances immune-mediated suppression. Together they "expand the parameter region exhibiting tumor-free or low population equilibria" and provide "greater flexibility and improved tumor control compared to single-therapy approaches" (part 3, §3.3 / Discussion).
- The system is **bistable and nonlinear**: small parameter changes can flip qualitatively between immune control and tumor escape — hence the need for phenotype-guided treatment.

### 2. Strategy depends on the evasion mechanism

**Immune checkpoint regulation dominant (T₁-only):** tumor control is "highly sensitive to the immune exhaustion rate" (μ) — checkpoint inhibitors are the most effective therapy. Best parameter targets: **↓μ** (reduce exhaustion); checkpoint inhibitors combined with moderate chemotherapy give the most effective control.

**Reduced antigen presentation dominant (T₁-only):** stability depends more on effector **activation (ρ) and exhaustion**, supporting **CAR-T therapy, cancer vaccines, or checkpoint inhibitors** to strengthen/reprogram effector recognition. Best targets: **↑ρ, ↓μ**. This mechanism is "more robust against relatively weak chemotherapy" than checkpoint evasion.

**Immune-sensitive phenotype dominant (T₂-only):** the dominant lever is boosting the **overall effector population** — increasing effector recruitment (**↑σ**, e.g. IL-2-type recruitment) or decreasing effector death (**↓δ**). Preferred therapies: **adoptive T-cell transfer, cytotoxic therapy**.

These map to the paper's Table 2 ("Phenotype-guided immunotherapy strategies under two resistance mechanisms"), which is explicitly summarized as: *effective therapy must target the dominant mechanism in each patient*, which "explains why different tumors respond preferentially to different immunotherapy strategies."

### 3. Proposed sequential/adaptive treatment protocols

From the bifurcation analyses, the authors propose **sequential treatment guided by tumor composition** (part 3, Discussion):

- **T₁-dominant start:** chemotherapy first to reduce burden → immunotherapy to maintain control. (Alternative order: immunotherapy first to shrink tumor → chemotherapy to clear residual resistant cells.)
- **T₂-dominant start:** chemotherapy reduces burden but risks resistant escape → **immunotherapy applied afterward** to stabilize the system.
- **Predicted coexistence of both resistant types:** apply **chemotherapy first** to eliminate T₁, leaving a low T₂-only equilibrium, then **immunotherapy** to potentially eliminate the tumor. Caveat: if the tumor is only *controlled* (not eliminated), emergence of new T₁ mutants could cause resurgence.

### 4. Elimination threshold and the "fight to win vs. fight to not lose" framing

- **Proposition 1 (tumor-free equilibrium stability):** the tumor is eliminated iff effective immune strength exceeds maximal tumor growth:
  σ/(δ + ωχ) > max{ α₂ − θ₂χ, (α₁ − χ)/θ₁ }
  i.e. the effector recruitment-to-loss ratio must beat the dominant tumor phenotype's effective growth rate. Note the ratio **σ/δ** and **max{α, α₁/θ₁}** are the critical quantities, so small changes in immune competence or tumor immunogenicity can swing the outcome.
- The paper contrasts aggressive elimination ("fight to win") against **adaptive therapy** — control rather than eradicate, maintaining a balance between drug-sensitive and drug-resistant cells, exploiting competition between subpopulations, and adjusting dynamically rather than using maximum tolerated dose (MTD) (part 1, Introduction, citing Gatenby et al.).
- Resistance carries a **fitness cost** (ζᵢ): when ζᵢ is small the corresponding population tends to dominate; when costs outweigh benefits the system is driven toward the tumor-free equilibrium. Cost/benefit is captured by θ₁ (benefit of immune resistance) and θ₂ (benefit of chemo-resistance).

### 5. Precision-medicine implication

Because stability thresholds depend on σ/δ and max{α, α₁/θ₁}, the authors argue for **biomarker-guided, phenotype-specific therapy** — selecting immunotherapy based on measurable markers such as **PD-L1 expression, T-cell infiltration, exhaustion markers, and antigen-presentation profiles** — and note that this is "why non-personalized, uniform treatment often fails." Future directions raised: optimal-control treatment scheduling, microenvironment feedback (breast/prostate), oncolytic virotherapy, and ML-based personalized adaptive therapy.

**Source reference:** `生命科学与医学/immunology__2604.01385__strategies-for-tumor-elimination-and-control.md` (parts 1–3 of 3), KB "生命科学与医学" (id `b28f0a25-1e1d-40ad-96b8-61bd2b093a28`); key passages at part 1 §2.1–2.2 & Introduction, part 2 §3.1–3.2 + Table 2, part 3 §3.3 + Discussion. Vector retrieval scores 0.83/0.78/0.77 (top-3 chunks), confirming a direct content match.

### [b] BQ10 — 92.1s, 5 tool calls, tokens out 852

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

Only the immunology paper addresses the mechanism of interest; the other hits are unrelated (imaging, spatial transcriptomics, clinical decision rules).

**Answer**

The corpus answers this through a single mathematical-modeling paper, `immunology__2604.01385__strategies-for-tumor-elimination-and-control.md` (Mokari & Morsky). Its central finding is that immune control alone is generally insufficient ("immune dynamics alone are generally insufficient to fully eliminate the tumor"), so the recommended strategies are phenotype-guided *combination* immuno-chemotherapy with attention to sequence. Specifically, when the immune-evasive subpopulation (T1) dominates via **immune checkpoint regulation**, control is most sensitive to the immune exhaustion rate (↓μ), favoring checkpoint inhibitors; when evasion occurs via **reduced antigen presentation**, outcomes depend on effector activation/exhaustion, favoring checkpoint inhibitors, CAR-T therapy, or cancer vaccines (↑ρ, ↓μ) — summarized in the paper's Table 2. When the immune-sensitive wild-type (T2) dominates, the strategy shifts to boosting effector recruitment and persistence (↑σ, ↓δ), e.g. adoptive T-cell transfer or cytotoxic therapy. For sequencing, the discussion proposes starting with chemotherapy to debulk a T1-dominant tumor followed by immunotherapy, or immunotherapy first then chemotherapy to clear residual resistant cells; for predicted coexistence of both resistant types, chemotherapy first eliminates T1, leaving a low T2-only state that immunotherapy may then eliminate. The paper notes chemotherapy "significantly enlarges the parameter region corresponding to tumor control or tumor-free equilibria" and that combined treatment consistently outperforms single therapy, while cautioning that modest parameter changes can flip the system between immune control and tumor escape.

### [c] BQ10 — 89.6s, 4 tool calls, tokens out 611

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**Answer (grounded in retrieved chunks):**

Under immune evasion, the model identifies two resistance strategies — immune checkpoint regulation and reduced antigen presentation — and the optimal control strategy depends on which dominates. When immune checkpoint regulation dominates, tumor control is "highly sensitive to the immune exhaustion rate," making checkpoint inhibitors "the most effective therapy," and control is achieved mainly by decreasing immune exhaustion (μ) or increasing immune activation (ρ, σ), with "checkpoint inhibitors combined with moderate chemotherapy" giving the most effective control. When reduced antigen presentation drives resistance, stability "depends more strongly on effector activation and exhaustion," supporting checkpoint inhibitors, CAR-T therapy, or cancer vaccines, while immune-sensitive phenotypes favor boosting effector recruitment and persistence via adoptive T-cell transfer or cytotoxic therapy. Across cases, combination immuno-chemotherapy "provides greater flexibility and improved tumor control compared to single-therapy" approaches.

**Chunks cited:** `immunology__2604.01385__strategies-for-tumor-elimination-and-control__k37.md`, `__k36.md`, `__k32.md`, `__k31.md`, `__k24.md`, `__k33.md`
