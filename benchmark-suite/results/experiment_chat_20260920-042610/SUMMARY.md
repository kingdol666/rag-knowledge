# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-20 06:21 UTC · same 50-paper corpus · questions: 10 · tracks: a, b, c

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| BQ01 | a | 311.1 | 7 | 154240 | 2560 | 76352 | 0.8733759999999999 |
| BQ01 | b | 152.5 | 3 | 34488 | 602 | 84928 | 0.229954 |
| BQ01 | c | 100.5 | 2 | 56679 | 488 | 61696 | 0.326443 |
| BQ02 | a | 142.0 | 6 | 189934 | 1837 | 41408 | 1.016299 |
| BQ02 | b | 89.8 | 4 | 101122 | 582 | 62208 | 0.551264 |
| BQ02 | c | 90.5 | 2 | 43043 | 401 | 75328 | 0.262904 |
| BQ03 | a | 190.6 | 7 | 152744 | 1899 | 117376 | 0.869883 |
| BQ03 | b | 107.9 | 3 | 58060 | 416 | 60608 | 0.331004 |
| BQ03 | c | 97.5 | 3 | 49833 | 725 | 71680 | 0.30313 |
| BQ04 | a | 111.4 | 4 | 168054 | 856 | 384 | 0.861862 |
| BQ04 | b | 57.8 | 3 | 39492 | 390 | 78080 | 0.24625000000000002 |
| BQ04 | c | 54.1 | 2 | 114744 | 393 | 4096 | 0.585593 |
| BQ05 | a | 259.4 | 8 | 220893 | 2172 | 63488 | 1.190509 |
| BQ05 | b | 100.5 | 4 | 66229 | 534 | 97856 | 0.39342299999999997 |
| BQ05 | c | 57.2 | 3 | 62724 | 594 | 58304 | 0.35762200000000005 |
| BQ06 | a | 243.9 | 7 | 140300 | 1699 | 94016 | 0.790983 |
| BQ06 | b | 219.7 | 5 | 148558 | 735 | 59520 | 0.790925 |
| BQ06 | c | 59.3 | 3 | 135932 | 552 | 28608 | 0.7077640000000001 |
| BQ07 | a | 173.3 | 6 | 165362 | 1441 | 53184 | 0.889427 |
| BQ07 | b | 160.2 | 4 | 160662 | 439 | 27456 | 0.8280130000000001 |
| BQ07 | c | 157.1 | 2 | 83705 | 414 | 34624 | 0.446187 |
| BQ08 | a | 774.1 | 15 | 303242 | 3611 | 108608 | 1.6607889999999998 |
| BQ08 | b | 186.3 | 4 | 133302 | 580 | 40896 | 0.701458 |
| BQ08 | c | 70.6 | 3 | 86145 | 525 | 34752 | 0.461226 |
| BQ09 | a | 254.3 | 7 | 215273 | 1935 | 59840 | 1.15466 |
| BQ09 | b | 125.2 | 5 | 79410 | 701 | 127168 | 0.478159 |
| BQ09 | c | 128.8 | 3 | 122287 | 559 | 42688 | 0.646754 |
| BQ10 | a | 248.4 | 9 | 219563 | 2414 | 79552 | 1.1979410000000001 |
| BQ10 | b | 162.4 | 4 | 69695 | 659 | 95552 | 0.4127259999999999 |
| BQ10 | c | 108.2 | 2 | 42991 | 396 | 75200 | 0.262455 |

**Totals**: latency avg 166.5s · tokens in 3618706 · out 31109 · cost $19.829

## Verbatim answers

### [a] BQ01 — 311.1s, 7 tool calls, tokens out 2560

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

Retrieval complete. All sources verified by content read.

## How the Transformer Computes Attention, and Why It Replaces Recurrence and Convolution

**Primary source:** "Attention Is All You Need" (Vaswani et al., 2017, arXiv:1706.03762), held in the KB *计算机与人工智能* (Computer Science & AI).

---

### 1. The Attention Function

An attention function maps **a query** and **a set of key-value pairs** to an output — all are vectors. The output is a **weighted sum of the values**, where each value's weight is produced by a *compatibility function* of the query with the corresponding key.

### 2. Scaled Dot-Product Attention (the specific mechanism)

The Transformer's variant is called **Scaled Dot-Product Attention**:
- Queries and keys have dimension **d_k**; values have dimension **d_v**.
- Compute the **dot product** of the query with all keys.
- **Divide each by √d_k** (the scaling factor).
- Apply a **softmax** to obtain the weights on the values.
- Queries are packed together into matrix **Q**, keys into **K**, values into **V**, giving a single matrix operation:

> **Attention(Q, K, V) = softmax( QKᵀ / √d_k ) · V**  — (Eq. 1)

**Why the √d_k scaling matters:** For large d_k, dot products grow large in magnitude, pushing softmax into regions with extremely small gradients. Scaling counteracts this. The paper notes that the alternative, *additive attention* (a feed-forward network with one hidden layer), is similar in theoretical complexity, but **dot-product attention is far faster and more space-efficient in practice** because it uses highly optimized matrix-multiplication code.

### 3. Multi-Head Attention

Rather than one attention function over d_model-dimensional keys/queries/values, the model **linearly projects Q, K, V h times** with different learned projections into d_k / d_k / d_v dimensions, runs attention on each projected version **in parallel**, concatenates the d_v-dimensional outputs, and projects once more:

> **MultiHead(Q,K,V) = Concat(head₁, …, head_h) · Wᴼ**, where headᵢ = Attention(QWᵢᵠ, KWᵢᴷ, VWᵢⱽ)

This lets the model "jointly attend to information from different representation subspaces at different positions" — with a single head, averaging inhibits this. The paper uses **h = 8 heads** with **d_k = d_v = d_model / h = 64**; because each head is lower-dimensional, the total cost is similar to single-head attention at full dimensionality.

### 4. Three Applications in the Model

1. **Encoder–decoder attention** — queries come from the previous decoder layer; keys and values come from the encoder output. Every decoder position can attend over all input positions.
2. **Encoder self-attention** — all keys, values and queries come from the same place (the previous encoder layer); each position attends to all positions.
3. **Decoder self-attention** — each position attends to all positions **up to and including itself**. Leftward information flow is prevented by **masking** (setting to −∞) all illegal connections before the softmax, preserving the auto-regressive property.

Architecture context: encoder and decoder are each a stack of **N = 6** identical layers; each sub-layer is wrapped in a **residual connection + layer normalization** (LayerNorm(x + Sublayer(x))), with d_model = 512. A position-wise feed-forward network (two linear transforms with ReLU, d_ff = 2048) follows attention in each layer.

### 5. Why Attention Replaces Recurrence and Convolution

The dominant sequence-transduction models were complex **recurrent or convolutional** networks; the best of them still bolted an attention mechanism onto an RNN. The Transformer **eschews recurrence entirely**, relying solely on attention to draw global dependencies between input and output — the first transduction model to do so (motivation stated in the Abstract and Introduction). Section 4, "Why Self-Attention," compares layer types against **three desiderata**: (1) total computational complexity per layer, (2) the amount of parallelizable computation (minimum number of sequential operations), (3) the **path length** between long-range dependencies.

| Layer Type | Complexity per Layer | Sequential Operations | Maximum Path Length |
|---|---|---|---|
| **Self-Attention** | O(n² · d) | **O(1)** | **O(1)** |
| Recurrent | O(n · d²) | O(n) | O(n) |
| Convolutional | O(k · n · d²) | O(1) | O(log_k(n)) |
| Self-Attention (restricted) | O(r · n · d) | O(1) | O(n/r) |

The reasons follow directly:

- **Constant sequential depth → parallelism.** A self-attention layer connects all positions with a **constant number of sequentially executed operations (O(1))**, whereas a recurrent layer requires **O(n) sequential operations**. This "allows for significantly more parallelization."
- **Shorter dependency paths → better long-range learning.** Learning long-range dependencies depends on the path length forward and backward signals must traverse: "The shorter these paths between any combination of positions in the input and output sequences, the easier it is to learn long-range dependencies." Self-attention gives **maximum path length O(1)**; recurrence gives **O(n)** and convolution **O(log_k(n))**.
- **Faster than recurrent when n < d.** Self-attention is cheaper than recurrent layers when sequence length n is smaller than representation dimension d — typically the case for word-piece/byte-pair sentence representations in MT.
- **Convolution needs stacking.** A single convolutional layer with kernel k < n cannot connect all input–output pairs; doing so requires O(n/k) layers (contiguous kernels) or O(log_k(n)) (dilated convolutions), lengthening the longest paths. Convolutional layers are also generally more expensive than recurrent ones by a factor of k, and even a separable convolution with k = n costs the same as a self-attention layer plus a point-wise feed-forward layer — which is exactly the Transformer's design.
- **Interpretability side benefit.** Individual attention heads learn to perform different tasks and appear to exhibit behavior related to the syntactic and semantic structure of sentences.

**Consequence requiring compensation:** Since the model contains **no recurrence and no convolution**, sequence order must be injected explicitly via **positional encodings** added to the input embeddings — sinusoids of different frequencies (PE_(pos,2i) = sin(pos / 10000^(2i/d_model)), PE_(pos,2i+1) = cos(...)), chosen because for any fixed offset k, PE_(pos+k) is a linear function of PE_(pos), which should let the model easily learn to attend by relative positions and extrapolate to longer sequences than seen in training.

---

### Source References

- **Primary — full mechanism, equations, Table 1, Section 4:** `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md` — KB *计算机与人工智能* (b1199132-e4d4-4305-8c2e-82dc1753b0ba), chunks 2, 8, 13, 24, 33, 52.
- **Corroborating downstream use (encoder-side self-attention; bidirectional encoder built on the Transformer):** `nlp__1810.04805__bert-pre-training-of-deep-bidirectional-transfor...` — KB *e599315e / d23002bd* — confirms "the self-attention mechanism in the Transformer allows BERT to model many downstream tasks" and contrasts left-to-right attention with bidirectional attention.

**Certainty: High.** The question is answered directly and verbatim by the primary source (a top-ranked hit at vector score 0.69, self-verified by reading the full document body). No blind spots: the abstract, Section 3.2 (attention mechanics), Table 1 and Section 4 (the recurrent/convolutional comparison) were all retrieved and read.

*Note: the same source document also appears duplicated under three baseline-reproduction KBs (`Corpus-Chunks800`, `Corpus-Struct`, `Corpus-Paras`); those are index replicas, not independent evidence.*

### [b] BQ01 — 152.5s, 3 tool calls, tokens out 602

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Answer** (from `artificial-intelligence__1706.03762__attention-is-all-you-need.md`, "Attention Is All You Need"):

Attention maps a query and a set of key-value pairs to an output, computed as a weighted sum of the values where each weight comes from a compatibility function of the query with its key. Concretely, the Transformer uses Scaled Dot-Product Attention: `Attention(Q,K,V) = softmax(QKᵀ/√d_k)·V` — dot products of queries with all keys are divided by √d_k (to keep softmax out of low-gradient regions for large d_k) and softmaxed into weights on the values; multi-head attention runs h=8 such projections in parallel over different representation subspaces. It replaces recurrence and convolution because self-attention connects all positions with a constant number of sequential operations (O(1) maximum path length) rather than O(n), enabling far more parallelization — the paper notes the model reached state of the art in 12 hours on 8 P100 GPUs, and that it is the first transduction model relying entirely on self-attention without sequence-aligned RNNs or convolution. Section 4 ("Why Self-Attention") frames the comparison along total per-layer complexity, parallelizable computation (minimum sequential operations), and path length between distant dependencies, and notes interpretability as a side benefit.

### [c] BQ01 — 100.5s, 2 tool calls, tokens out 488

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

Based on the retrieved chunks, the Transformer computes attention through a "multi-headed self-attention" mechanism that draws global dependencies between input and output positions entirely through attention, dispensing with recurrence and convolutions (…1706.03762…k19, …k02, …k00). It uses multi-head attention in three ways: encoder-decoder attention (queries from the previous decoder layer, keys/values from the encoder output, letting every decoder position attend over all input positions), encoder self-attention, and decoder self-attention (…k06, …k07). The retrieved evidence shows the replacement rationale: prior dominant models relied on complex recurrent or convolutional networks, whereas the Transformer is "the first sequence transduction model based entirely on attention," replacing recurrent layers with multi-headed self-attention (…k20, …k00). Because it eschews recurrence, it "allows for significantly more parallelization" and can be trained significantly faster than recurrent or convolutional architectures (…k02, …k20). The chunks also note self-attention reduces the path length for learning dependencies between distant positions to a constant number of operations, versus linear for ConvS2S and logarithmic for ByteNet, at the cost of reduced effective resolution that Multi-Head Attention counteracts (…k02, chunk_index 3). Note that the exact scaled dot-product formula (Q/K/V projections, √dk scaling) does not appear in the retrieved chunks.

### [a] BQ02 — 142.0s, 6 tool calls, tokens out 1837

**Q:** What defines NISQ technology and what is its central limitation?

I have all the evidence needed to answer.

---

## What Defines NISQ Technology and Its Central Limitation

**Source:** John Preskill (Caltech), *"Quantum Computing in the NISQ era and beyond"* (arXiv:1801.00862, 30 July 2018) — KB `自然科学与地球科学` (`1e6199ea-f380-44e2-94fc-d431f0f9bb6b`), doc `quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond.md (part 1 of 3).md`, §4.1 "The 50-qubit barrier" (chunks 34–41).

### 1. Definition: the name itself

**NISQ = "Noisy Intermediate-Scale Quantum."** Preskill coined the term himself, literally: *"I needed a name to describe this impending new era, so I made up a word: NISQ."* Each word carries a specific meaning:

| Component | What it means in Preskill's formulation |
|---|---|
| **Noisy** | *"'Noisy' emphasizes that we'll have imperfect control over those qubits."* The devices operate without quantum error correction, so gate imperfections are intrinsic — per-gate two-qubit error rates are *"above the .1% level (and often much worse)."* |
| **Intermediate-Scale** | *"'Intermediate scale' refers to the size of quantum computers which will be available in the next few years, with a number of qubits ranging from 50 to a few hundred."* 50 qubits is called out as the significant milestone because it exceeds what the most powerful classical supercomputers can simulate by brute force — but it remains far short of the millions of physical qubits that fault tolerance would demand. |
| **Quantum** | The era in which we have real, controllable, highly entangled many-particle quantum systems — the "entanglement frontier" — but not yet fault-tolerant machines. |

Preskill frames NISQ as transitional, not transformative: NISQ devices *"will be useful tools for exploring many-body quantum physics, and may have other useful applications, but the 100-qubit quantum computer will not change the world right away."*

### 2. The central limitation: gate noise caps the executable circuit size

The defining constraint is **noise in quantum gates limiting the size of quantum circuits that can be executed reliably** — stated in the paper's abstract and developed concretely in §4.1:

> *"Naively, then... with these noisy devices we don't expect to be able to execute a circuit that contains many more than about 1000 gates — that is, 1000 fundamental two-qubit operations — because the noise will overwhelm the signal in a circuit much larger than that. **That limitation on circuit size imposes a ceiling on the computational power of NISQ technology.**"*

This is the crux. Because error cannot be corrected, error per gate (ε ≫ 1/G for G gates) means a single fault anywhere in a generic circuit can ruin the computation. The consequence is quantified as a practical operating envelope of roughly:
- **~100 qubits** in near-term experiments, and
- **circuit depth (number of time steps) of less than 100, maybe much less.**

So the limitation is not the qubit count per se — it is that **depth × fidelity, not qubit count, bounds what can be computed.** A 50–100 qubit machine with a ~1000-gate ceiling cannot run the deep circuits that fault-tolerant algorithmics (e.g., Shor-class applications) require. Preskill notes the escape route is quantum error correction to scale to larger circuits, but *"quantum error correction imposes a heavy overhead cost in number of qubits and number of gates"* — which is exactly why NISQ is a distinct era rather than a stepping stone one simply waits out.

One nuance worth flagging from the source: Preskill concedes the 1000-gate figure may be **too pessimistic** for certain problems. Some quantum simulation and tensor-network-style algorithms have only a *relatively small number of circuit locations* where a faulty gate causes bad failure — "noise resilience" that can be exploited. So the ceiling is a generic expectation, not an absolute law.

### Bottom line

NISQ is defined by the pairing of **intermediate qubit counts (50–a few hundred) available without error correction** with **noisy, imperfectly controlled gates**; its central limitation is that **gate noise caps reliable circuit size at roughly ~1000 two-qubit operations, imposing a hard ceiling on computational power** and confining near-term devices to shallow-circuit applications rather than world-changing computation.

**References**
- Preskill, J. *Quantum Computing in the NISQ era and beyond*, arXiv:1801.00862 (2018) — Abstract; §4.1 "The 50-qubit barrier"; §3.2 "Why quantum computing is hard".
- KB locations: `自然科学与地球科学/quantum-physics__1801.00862__...md (part 1 of 3).md`, kb_id `1e6199ea-f380-44e2-94fc-d431f0f9bb6b`, chunks 1, 35, 36, 40, 41, 68. The same passage is corroborated in the baseline reproduction indices `Corpus-Paras` (`e599315e-...`, p06000) and `Corpus-Struct` (`8284ae07-...`, s00/s05).

### [b] BQ02 — 89.8s, 4 tool calls, tokens out 582

**Q:** What defines NISQ technology and what is its central limitation?

The file is **quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond.md** (Preskill's "Quantum Computing in the NISQ Era and Beyond").

**What defines it:** NISQ stands for "Noisy Intermediate-Scale Quantum." "Intermediate-scale" refers to devices with roughly 50 to a few hundred qubits (50 being the milestone beyond brute-force classical simulation), while "noisy" emphasizes that we have only imperfect control over those qubits — noisy gates left unprotected by quantum error correction (§4.1, line 67).

**Central limitation:** The noise imposes a ceiling on circuit size: with current two-qubit gate error rates above ~0.1%, a circuit containing many more than about 1000 gates cannot be executed reliably because "the noise will overwhelm the signal," and this "limitation on circuit size imposes a ceiling on the computational power of NISQ technology" (§4.2, line 74). A related consequence is that it may be hard to validate whether a NISQ device is really producing the right answer (line 102).

### [c] BQ02 — 90.5s, 2 tool calls, tokens out 401

**Q:** What defines NISQ technology and what is its central limitation?

The retrieved chunks define NISQ directly. NISQ stands for "Noisy Intermediate-Scale Quantum," a term coined by John Preskill to describe the impending era of quantum technology (quantum-physics__1801.00862__..._k07.md, _k31.md). "Intermediate scale" refers to quantum computers becoming available in the next few years with qubit counts "ranging from 50 to a few hundred," where 50 qubits is a significant milestone because that exceeds brute-force simulation by the most powerful existing digital supercomputers (k07.md, k00.md). The central limitation is noise: "Noisy" emphasizes imperfect control over qubits, and "the noise will place serious limitations on what quantum devices can achieve in the near term" (k07.md). Concretely, circuits cannot exceed roughly 1000 gates because "the noise will overwhelm the signal," imposing "a ceiling on the computational power of NISQ technology" until quantum error correction can scale circuits up (k08.md).

### [a] BQ03 — 190.6s, 7 tool calls, tokens out 1899

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

I have comprehensive evidence from the primary source. Here is the answer.

## What is MultiMedQA?

**MultiMedQA** is a benchmark for medical question answering, introduced in the paper *"Large Language Models Encode Clinical Knowledge"* (Singhal, Azizi, Tu et al., Google Research / DeepMind; arXiv 2212.13138).

It combines **six existing open question-answering datasets** spanning professional medical exams, medical research, and consumer medical queries, plus **HealthSearchQA** — a new free-response dataset of 3,375 medical questions searched online:

| Dataset | Format | Size (dev/test) | Domain |
|---|---|---|---|
| MedQA (USMLE) | Q + A (4–5 choices) | 11,450 / 1,273 | US medical licensing exam |
| MedMCQA (AIIMS/NEET) | Q + A (4 choices + explanations) | 187K / 6.1K | Indian medical entrance exams |
| PubMedQA | Q + Context + A (Yes/No/Maybe) | 500 / 500 | Biomedical scientific literature |
| MMLU (clinical topics) | Q + A (4 choices) | 123 / 1,089 | Anatomy, clinical knowledge, college medicine, medical genetics, professional medicine, college biology |
| LiveQA TREC-2017 | Q + long answer | 634 / 104 | General consumer medical questions |
| MedicationQA | Q + long answer | NA / 674 | Consumer medication knowledge |
| **HealthSearchQA** (new) | Q + manual expert evaluation | 3,375 | Consumer health searches |

The benchmark deliberately varies along three axes: **format** (multiple-choice vs. long-form), **capabilities tested** (fact recall vs. medical reasoning), and **domain** (open vs. closed domain). The paper also proposes a human-evaluation framework rating answers on factuality, precision, possible harm, and bias. The motivation is that existing benchmarks relying on multiple-choice accuracy or BLEU are too limited for safety-critical clinical applications.

## How Flan-PaLM performed on MedQA

Using a combination of prompting strategies, **Flan-PaLM 540B achieved 67.6% accuracy on MedQA (USMLE) questions with 4 options**, exceeding the previous state of the art by **over 17%**.

Comparison against prior SOTA on MedQA (4 options):

| Model | MedQA (USMLE) Accuracy % |
|---|---|
| **Flan-PaLM (540B)** | **67.6** |
| PubMedGPT (2.7B) | 50.3 |
| DRAGON (360M) | 47.5 |
| BioLinkBERT (340M) | 45.1 |
| Galactica (120B) | 44.4 |
| PubMedBERT (100M) | 38.1 |
| GPT-Neo (2.7B) | 33.3 |

**Supporting details from the ablations:**
- Flan-PaLM beat the DRAGON model by **20.1%**, and PubMedGPT (biomedical-domain model) by a wide margin.
- With 5-shot prompting, Flan-PaLM scored 60.3% vs. PaLM's 58.9% at 540B; the instruction-tuned variant outperformed baseline PaLM at every scale (8B: 35.4 vs 25.7; 62B: 46.1 vs 40.9).
- Scaling mattered: Flan-PaLM 540B outperformed 62B by over 14% and 8B by over 24%.
- Chain-of-thought prompting did **not** improve over standard few-shot on MedQA (nor MedMCQA/PubMedQA).

**Context / caveats:** Flan-PaLM also reached SOTA on MedMCQA (57.6%) and PubMedQA (79.0%), plus MMLU clinical topics (84.0% clinical knowledge, 83.5% professional medicine). However, human evaluation revealed key gaps — Flan-PaLM's answers to consumer medical questions were lacking, which motivated **instruction prompt tuning** to produce **Med-PaLM**. Med-PaLM performed encouragingly but remained **inferior to clinicians**.

## Sources

- **Primary:** `生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md` (parts 1 & 2 of 8) — KB `b28f0a25-1e1d-40ad-96b8-61bd2b093a28` (生命科学与医学)
  - Abstract & §3.1/§3.1.1 (MultiMedQA definition, Table 1), §4.1 ("Flan-PaLM exceeds previous SOTA on MedQA by over 17%", Table 4), §4.3–4.4 (MMLU, ablations, Table 5)
- **Corroborating copies / index variants:** `Corpus-Struct/clinical-medicine__2212.13138__...` (KB `8284ae07…`), `Corpus-Chunks800/...` (KB `d23002bd…`), `Corpus-Paras/...` (KB `e599315e…`) — independent chunking/structuring of the same source paper.

### [b] BQ03 — 107.9s, 3 tool calls, tokens out 416

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

MultiMedQA is a benchmark introduced in this paper comprising seven medical question-answering datasets: six existing ones (MedQA, MedMCQA, PubMedQA, LiveQA, MedicationQA, and MMLU clinical topics) plus a newly introduced seventh, HealthSearchQA (3,375 commonly searched consumer health questions), spanning medical exam, research, and consumer question types. On MedQA (USMLE-style, 4-option questions), Flan-PaLM 540B achieved **67.6% accuracy**, exceeding the previous state of the art by over 17% (prior best was PubMedGPT at 50.3%) — although this 67.6% figure came from self-consistency prompting, versus 60.3% with plain 5-shot prompting.

File used: `clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md`

### [c] BQ03 — 97.5s, 3 tool calls, tokens out 725

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

The retrieved chunks answer both parts of the question directly.

**What MultiMedQA is:** The paper's own summary states, "We curated MultiMedQA, a benchmark for medical question answering spanning medical exam, medical research, and consumer medical questions." It was built to assess LLMs, and the authors "newly introduce the seventh dataset, HealthSearchQA, which consists of commonly searched health questions," evaluated using PaLM and its instruction-tuned variant Flan-PaLM (Corpus-Chunks800/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k01.md, k04.md).

**Flan-PaLM's MedQA performance:** Using a combination of few-shot, chain-of-thought, and self-consistency prompting, "Flan-PaLM achieves state-of-the-art accuracy on every MultiMedQA multiple-choice dataset (MedQA, MedMCQA, PubMedQA, MMLU clinical topics), including 67.6% accuracy on MedQA (US Medical License Exam questions), surpassing prior state-of-the-art by over 17%." A results table lists Flan-PaLM (540B) at 67.6% on MedQA (USMLE), ahead of PubMedGPT (50.3%), DRAGON (47.5%), BioLinkBERT (45.1%), and Galactica (44.4%) (k00.md, k01.md, k31.md, k30.md).

An ablation chunk also notes that instruction prompt tuning produced a model reaching 67.2% accuracy on MedQA with chain-of-thought and self-consistency, "roughly matching the corresponding result with Flan-PaLM" (k76.md).

**Chunk files cited:** `clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge__k00.md`, `__k01.md`, `__k02.md`, `__k04.md`, `__k30.md`, `__k31.md`, `__k76.md` (all from the Corpus-Chunks800 index).

### [a] BQ04 — 111.4s, 4 tool calls, tokens out 856

**Q:** Which three independent ontologies subdivide the Gene Ontology?

The retrieved chunk from the vector search contains the exact answer, and the document read confirms the source. Here is the answer:

## Answer

The Gene Ontology (GO) is subdivided into **three distinct, non-redundant ontologies**, each representing a different biological aspect:

1. **Molecular Function (MF)**
2. **Biological Process (BP)**
3. **Cellular Component (CC)**

These three ontologies share a common space of identifiers and a well-specified syntax, and their terms are linked by relations to form a hierarchical vocabulary.

### Source

- **Document:** `生命科学与医学/genomics__1602.01876__primer-on-the-gene-ontology.md (part 1 of 2).md` (section "2. What is the Gene Ontology?")
- **Paper:** Gaudet, P., Škunca, N., Hu, J.C., & Dessimoz, C. — *"Primer on the Gene Ontology"* (arXiv:1602.01876), January 2016
- **KB:** 生命科学与医学 (`kb_id`: `b28f0a25-1e1d-40ad-96b8-61bd2b093a28`)
- **Exact quote:** *"The terms are subdivided in three distinct ontologies that represent different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC) (1). These ontologies are non-redundant and share a common space of identifiers and a well-specified syntax."*

### Retrieval method & confidence

- **Stage 1 (BM25):** `kb_search_two_stage` surfaced the correct document as the top candidate (score 12.35, far above the next at 1.70).
- **Stage 2 (vector):** Top chunk score 0.646 — well above the 0.35 threshold, matching the passage verbatim.
- **Content gate:** Read back via `kb_doc_read`; the "three distinct ontologies" wording was confirmed in the document body.
- **Confidence: High (P0-equivalent)** — direct verbatim match with a single unambiguous source, no conflicting candidates.

### [b] BQ04 — 57.8s, 3 tool calls, tokens out 390

**Q:** Which three independent ontologies subdivide the Gene Ontology?

The answer comes from `genomics__1602.01876__primer-on-the-gene-ontology.md`. It states that GO terms "are subdivided in three distinct ontologies that represent different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)" (line 47). The same three sub-ontologies are repeated later in the annotation-format section, where field 9 "denotes the sub-ontology of GO, either Molecular Function, Biological Process, or Cellular Component" (line 104). These three ontologies are described as non-redundant, sharing a common space of identifiers and a well-specified syntax.

### [c] BQ04 — 54.1s, 2 tool calls, tokens out 393

**Q:** Which three independent ontologies subdivide the Gene Ontology?

The retrieved evidence answers the question directly.

The Gene Ontology is subdivided into three distinct ontologies representing different biological aspects: **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**. The source text states the term vocabulary is "subdivided in three distinct ontologies that represent different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)" (chunk `genomics__1602.01876__primer-on-the-gene-ontology__k00.md`). A second chunk (`...__k01.md`) repeats this same three-way subdivision and adds that these ontologies are "non-redundant and share a common space of identifiers and a well-specified syntax."

Cited chunks: `genomics__1602.01876__primer-on-the-gene-ontology__k00.md`, `genomics__1602.01876__primer-on-the-gene-ontology__k01.md`.

### [a] BQ05 — 259.4s, 8 tool calls, tokens out 2172

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

## Answer

The knowledge base contains one directly relevant document, plus three derivative re-indexes of the same paper. The argument comes from:

**Source:** Nielsen, R. W. (2015), *"Unified Growth Theory Contradicted by the Economic Growth in Europe"* (arXiv:1512.08067)
- Path: `经济与社会/economics__1512.08067__unified-growth-theory-contradicted-by-the-econom.md.md`
- KB: 经济与社会 (`f5770687-6b05-4a8d-8645-af31686ca87e`)
- Also present as re-chunked copies in `Corpus-Chunks800`, `Corpus-Struct`, `Corpus-Paras`

### Why European growth is said to contradict Unified Growth Theory (UGT)

**1. Europe is the theory's "best-case test," so a failure there is decisive.** Western Europe was the centre of the Industrial Revolution, which Galor calls "the prime engine of economic growth" (Galor 2005a, p. 212). If UGT's proposed mechanisms were real, their effects "should be prominently manifested in Europe." Nielsen argues they are not — so Europe is the strongest possible falsification site, not a marginal case.

**2. The three-regime sequence is absent from the data.** UGT postulates: Malthusian stagnation (from 100,000 BC to ~1750), post-Malthusian regime (~1750–1870), sustained growth (from 1870). Nielsen fits Maddison (2010) GDP data with a hyperbolic model, S(t) = (a − kt)⁻¹, whose reciprocal 1/S(t) = a − kt is a straight line. If growth were genuinely stagnant then switching regimes, the reciprocal plot would show kinks and random Malthusian fluctuations. Instead the reciprocal values form an **unchanged decreasing straight line** — there is no kink, and "it makes no sense to divide a straight line into two or three arbitrarily selected sections and claim different regimes of growth."

**3. There was no stagnation, so there was no transition.** For the 12 leading Western European countries, the hyperbolic fit is "remarkably good between AD 1500 and 1900" (a = 1.147×10⁻¹, k = 5.961×10⁻⁵). The data show steadily increasing hyperbolic growth throughout the period where the stagnation signature should be visible for ~300 years. Nielsen's conclusion: "There was no transition from stagnation to growth at any time because there was no stagnation."

**4. There was no Malthusian trap, so there was no "escape."** UGT's celebrated "remarkable"/"stunning" escape from the Malthusian trap (Galor 2005a, pp. 177, 220) requires a trap to escape from. The data show "an undisturbed hyperbolic growth" instead.

**5. The Industrial Revolution produced no visible break in the growth trajectory.** Rather than the predicted takeoff coinciding with the Industrial Revolution (1760–1840), the growth trajectory was only *diverted to a slower* trajectory around 1880–1900 — i.e., the opposite of the predicted acceleration, and roughly at the point UGT claims the *sustained growth* regime began. Nielsen states the engine "had absolutely no effect on the economic growth trajectories."

**6. Eastern Europe confirms the same result.** Fitting Eastern European data (a = 7.749×10⁻¹, k = 4.048×10⁻⁴, singularity 1915), growth was likewise hyperbolic with no stagnation epoch, no trap, no escape, and no Industrial Revolution boost; it was diverted to a slower trajectory around 1890.

**7. Methodology critique — the contradiction is partly self-inflicted by bad data presentation.** Nielsen argues UGT is contradicted even by the very data used to build it (Maddison 2001), which he calls "a paradox… probably rare in science." The explanation: the data "were never properly analysed" — Maddison's series is repeatedly "mutilated" by displaying only four selected points joined by straight lines (citing Galor 2005a/2005b/2007/2008a–c/2010/2011/2012a–c; Ashraf 2009; Galor & Moav 2002; Snowdon & Galor 2008). He argues GDP/capita distributions are "linearly-modulated hyperbolic distributions," increasing monotonically, so the search for a takeoff time is "a lost effort" — any claim of such a takeoff is "scientifically unjustified" and "based only on impressions."

**8. Conclusion.** The paper's closing contrast: "The theory tells one set of stories; the data present a diametrically different account." UGT is declared to need thorough revision, or "most likely replaced by a new theory supported by a professional analysis of economic growth data." Nielsen also flags a policy-relevant consequence: UGT's claim that we have entered a final, unconstrained sustained-growth regime is "dangerously misleading" — the data indicate growth continues too fast, "pointing to the insecure future."

### Caveats on this source

- This is a **single-author, non-peer-reviewed arXiv preprint** (Griffith University, December 2015). The KB holds no counter-response or mainstream-growth-theory source to balance it — the document is the *only* substantive treatment of UGT in the corpus.
- It is part of a series by the same author (Nielsen 2014, 2015a–2015f) claiming UGT is contradicted by Africa, Asia, the former USSR, world growth, and GDP/capita data alike. The European case should be read as one instance of that broader, contested claim.
- The hyperbolic-growth framing (and the conclusion that no policy/fundamental break occurred) is the author's own modelling choice, not a settled consensus.

**Blind spot declaration:** The KB contains no Galor-side text, no rebuttal literature, and no independent econometric replication. The answer above faithfully reports the KB's holdings; it is not an adjudication of the debate.

### [b] BQ05 — 100.5s, 4 tool calls, tokens out 534

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

According to `economics__1512.08067__unified-growth-theory-contradicted-by-the-econom.md` (Nielsen 2015), Europe is the decisive test case precisely because Western Europe was the center of the Industrial Revolution, which Galor calls "the prime engine of economic growth" — so the theory's signatures should be most visible there. Yet re-analyzing Maddison's GDP data (AD 1–2008) for Western Europe (12 leading countries and 30 countries) and Eastern Europe shows the reciprocal values of GDP follow a decreasing straight line, indicating continuous hyperbolic growth rather than the three regimes Galor posits. The paper argues there was never a transition from stagnation to growth because there was no Malthusian stagnation or trap to escape, and the Industrial Revolution produced no detectable boost in the growth trajectory — growth continued undisturbed until being diverted to a *slower* trajectory around 1880–1900, the opposite of a takeoff. The author also charges that UGT's apparent fit came from unscientific data treatment (plotting only four selected points joined by straight lines), and concludes the theory must be thoroughly revised or likely replaced.

### [c] BQ05 — 57.2s, 3 tool calls, tokens out 594

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

**Answer (grounded in retrieved chunks):**

Historical European growth contradicts Unified Growth Theory (Galor 2005a, 2011) because the theory's central predictions fail on Maddison's data. The theory posits three distinct regimes with a transition from Malthusian stagnation to sustained growth — a "remarkable" or "stunning" escape from the Malthusian trap, or takeoff, supposedly coinciding with the Industrial Revolution. Nielsen argues this signature is missing: "the episode of Malthusian stagnation did not exist," "there was no trap," and "Industrial Revolution did not boost the economic growth in Eastern Europe." Europe — especially Western Europe, the centre of the Industrial Revolution — is precisely where the theory's effects "should be most prominent," yet the reciprocal-value (1/GDP) plots show no clear downward change in trajectory; instead, growth began diverting to a *slower* trajectory around the alleged onset of sustained growth. Hence "the data tell one story while the Unified Growth Theory tells another and diametrically opposite story," leading to the conclusion that the theory "needs to be thoroughly revised."

**Chunks cited:** `...unified-growth-theory-contradicted-by-the-econom__k00.md`, `..._k02.md`, `..._k04.md`, `..._k05.md`, `..._k06.md`, `..._k10.md`, `..._k11.md`, `..._k13.md`

### [a] BQ06 — 243.9s, 7 tool calls, tokens out 1699

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

I have sufficient evidence from the primary source. Here is the answer.

## Answer

**The thermodynamic contribution — specifically the increase in atmospheric water-vapor content with warming (saturation specific humidity), i.e. Clausius–Clapeyron scaling — is the primary, robust physical control on the response of precipitation extremes to climate change.**

### Evidence from the knowledge base

**Source:** `自然科学与地球科学/climate-science__1503.07557__precipitation-extremes-under-climate-change.md` (Paul A. O'Gorman, *"Precipitation extremes under climate change"*), KB `1e6199ea-f380-44e2-94fc-d431f0f9bb6b` — parts 1–3.

**1. The theoretical decomposition (Section 3, Eq. 1)**

The surface precipitation rate in an extreme event is approximated as:

> P ≃ −ε { ω(p) S(T,p) }

where ε is precipitation efficiency, ω is vertical velocity, and S = dq_s/dp |_{θ*_e} is the derivative of saturation specific humidity along a moist adiabat. Per the document, changes in P therefore have **three** components:
- **Thermodynamic** — from changes in S (depends only on temperature/pressure)
- **Dynamical** — from changes in ω
- **Microphysical** — from changes in ε

**2. Which one dominates (Abstract + Section 3 + Section 8)**

- Abstract: *"The **thermodynamic contribution is robust and well understood**, but theoretical understanding of the microphysical and dynamical contributions is still being developed."*
- Section 3: *"for a moist-adiabatic stratification and convergence confined to near the surface, the thermodynamic contribution can be shown to scale in a similar way to near surface specific humidities… This scaling is often referred to as **Clausius-Clapeyron scaling and gives a sensitivity of 6–7 % K⁻¹**."*
- The document states this is why extremes intensify at all: *"If changes in dynamics and precipitation efficiency are negligible, precipitation extremes increase with warming **because of increases in the saturation vapor pressure of water**."*
- Section 8: *"Contributions from changes in thermodynamics, dynamics, and precipitation efficiency have all been found to be important… **The thermodynamic contribution is the easiest to understand and always gives an intensification with warming.**"*

**3. Where the other factors matter (i.e. where the primary control is modified)**

- **Efficiency:** Thermodynamic scaling holds well (~6–7 % K⁻¹) at surface temperatures **above 295 K**; **below 295 K** sensitivity deviates widely and instantaneous extremes can reach ~double the C-C rate, driven by increases in precipitation efficiency (hydrometeor fall speed as precipitation shifts solid→liquid) — Section 7, Fig. 3.
- **Dynamics:** Large-scale extratropical vertical velocities (omega equation, Section 4.1) and convective updrafts; updraft increases in the upper troposphere matter little because S(p) weights lower-troposphere ω most heavily. The dynamical contribution is comparatively small in RCE.
- **Observations:** The land-based sensitivity is **8 % K⁻¹** (90% CI 5–10 % K⁻¹) versus global-mean surface temperature, and **~9 % K⁻¹** in the tropics vs **~4 % K⁻¹** in the extratropics versus latitude-band temperature — *"roughly consistent with what might be expected from theory"* (Section 2, Fig. 1).

### Bottom line

The dominant, most robust controlling factor is **temperature-dependent atmospheric moisture — the increase in saturation specific humidity with warming (the thermodynamic / Clausius–Clapeyron term)** — with dynamical (vertical velocity) and microphysical (precipitation-efficiency) contributions acting as second-order modulators that become important for convective/tropical extremes and for sub-295 K temperatures or subdaily durations. Orographic and snowfall extremes are the notable exceptions, since snowfall extremes instead peak near an optimal temperature (~−2 °C liquid-equivalent), set by the competing effects of vapor increase and the rain–snow transition.

### [b] BQ06 — 219.7s, 5 tool calls, tokens out 735

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Answer:** According to this paper, the primary control is **temperature**, acting through the **thermodynamic contribution** — specifically the increase in saturation vapor pressure / near-surface saturation specific humidity with warming, i.e. **Clausius–Clapeyron (C–C) scaling** (~6–7% K⁻¹). The paper decomposes the precipitation-rate response into a thermodynamic contribution (from changes in `S(T,p)`, the moist-adiabatic saturation specific humidity derivative), a dynamical contribution (changes in vertical velocity ω), and a microphysical contribution (changes in precipitation efficiency ε); it states the thermodynamic contribution is "robust and well understood," whereas the microphysical and dynamical contributions remain less certain, especially where convection matters. This same C–C constraint is described as the basis for observed sensitivities (global mean ~8% K⁻¹, tropics ~9% K⁻¹ vs. extratropics ~4% K⁻¹) and model projections.

**File used:** `climate-science__1503.07557__precipitation-extremes-under-climate-change.md` (Abstract; §3 Theory, Eq. 1 and surrounding discussion; §2 Observations, Fig. 1).

### [c] BQ06 — 59.3s, 3 tool calls, tokens out 552

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Based only on the retrieved chunks:**

The primary control is **temperature**, operating through the thermodynamic contribution — specifically the increase in near-surface specific humidity (moisture) with warming, which scales close to Clausius-Clapeyron (~6–7% K⁻¹). The retrieved chunks state that "The thermodynamic contribution is robust and well understood" and that for near-tropical surface temperatures "the precipitation extremes increase at close to the thermodynamic rate, and this is close to Clausius-Clapeyron scaling with the surface specific humidity, with relatively small contributions from changes in vertical velocities and precipitation efficiency." However, the chunks also note this is modulated by other factors — precipitation efficiency and dynamics become important below ~295K and for convective/subdaily extremes, where sensitivities depart from (and can exceed) Clausius-Clapeyron scaling.

Chunks used: `climate-science__1503.07557__precipitation-extremes-under-climate-change__k00.md`, `__k06.md`, `__k08.md`, `__k12.md`, `__k21.md`, `__k22.md`.

### [a] BQ07 — 173.3s, 6 tool calls, tokens out 1441

**Q:** What is MameLoshnLM and what parameter scale does it have?

The document is confirmed. I have enough to answer definitively.

## Answer

**MameLoshnLM** (stylized **MAMELOSHNLM**) is the **first open-source large language model for Yiddish**. Its name is derived from *Mame-Loshn* (מאַמע־לשון, "mother tongue"), the traditional Yiddish term evoking the language's intimate connection to home and family.

**Parameter scale: 8B (built on Llama-3.1-8B)**

It was produced by **continued pretraining of Llama-3.1-8B** on a Yiddish corpus using a causal language modeling objective — so it inherits the Llama-3.1-8B parameter scale (8 billion parameters). The authors report that it "outperforms strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks."

**Supporting details from the paper:**
- **Training corpus (Oytser):** a purpose-built Yiddish pretraining corpus of ~915M words / 5.28B tokens from 9 high-quality sources (Yiddish Book Center corpus, Ivelt and Kaveshtiebel forums, the Forward, Yiddish Wikipedia, etc.)
- **Training config:** bfloat16 precision, 8-bit AdamW, learning rate 2×10⁻⁵, cosine schedule with 2% warmup, weight decay 0.01, one epoch, max sequence length 1,024 tokens, per-device batch size 38, 4 gradient accumulation steps
- **Benchmark (Kashes):** first multi-task Yiddish evaluation benchmark (9 tasks — POS tagging, dependency parsing, lemmatization, transliteration, NER, translation, commonsense QA, question generation, paraphrase detection). On POS tagging it scores 88.6 accuracy vs. 86.9 for Llama 3.1 8B and 87.6 for Gemma-2 9B.
- **Baselines compared:** Llama 3.1 8B, Qwen3 8B, BLOOMZ 7B, Gemma-2 9B, EuroLLM 9B — confirming the 8B-class comparison group.
- **License:** released under a **non-commercial license**, consistent with the terms of the licensed data agreements used in its evaluation benchmark.

**Sources (knowledge base):**
- `计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md (part 1 of 4).md` — kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba` (Section 5 "MAMELOSHNLM", Training Details; Section 3.2 corpus tables)
- `Corpus-Paras/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu__p10001.md` — kb_id `e599315e-db3c-44ef-b31c-41974acbd1e4` (vector score 0.72, strongest match: "produced by continued pretraining of Llama-3.1-8B")
- `Corpus-Paras/...__p13001.md` — same kb_id (baseline comparison table: MAMELOSHNLM vs. Llama 3.1 8B / Qwen3 8B / BLOOMZ 7B / Gemma-2 9B / EuroLLM 9B)
- `Corpus-Chunks800/...__k12.md` — kb_id `d23002bd-176e-4ead-9a0c-c2e85fefe6f0`

The paper is arXiv/IJCNLP-style ID **2608.05850**, "MameLoshnLM: Yiddish Language Model and Evaluation."

### [b] BQ07 — 160.2s, 4 tool calls, tokens out 439

**Q:** What is MameLoshnLM and what parameter scale does it have?

MAMELOSHNLM (Mame-Loshn, "mother tongue") is described as the first open-source large language model built specifically for Yiddish. It was produced by continued pretraining of Llama-3.1-8B on a Yiddish corpus (Oytser) using a causal language modeling objective, so its parameter scale is **8 billion (8B)** parameters. The paper reports it outperformed open baselines of similar scale (Llama 3.1 8B, Qwen3 8B, BLOOMZ 7B, Gemma-2 9B, EuroLLM 9B) across the Kashes benchmark, with an average score of 62.6.

File used: `nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md`

### [c] BQ07 — 157.1s, 2 tool calls, tokens out 414

**Q:** What is MameLoshnLM and what parameter scale does it have?

MAMELOSHNLM is the first open-source large language model built specifically for Yiddish, named after the traditional Yiddish term "Mame-Loshn" ("mother tongue"), which evokes the language's intimate connection to home and family. It is an **8B-parameter** model: the abstract states "We present MAMELOSHNLM, the first open-source 8B-parameter language model built specifically for Yiddish," and the introduction likewise describes it as "an open-source 8B-parameter LM for Yiddish." The paper presents it alongside two supporting resources — Oytser, a new Yiddish pretraining corpus, and Kashes, a benchmark for evaluating Yiddish LMs — and reports that it outperforms strong baselines of similar scale across a broad set of Yiddish evaluation benchmarks.

Sources: `Corpus-Chunks800/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu__k00.md`, `..._k02.md`, `..._k01.md`, `..._k12.md`

### [a] BQ08 — 774.1s, 15 tool calls, tokens out 3611

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

I have the full source document. Here is the answer.

## How Oxygen Redox Contributes to Battery Cathode Capacity

**Source:** Assadi, M.H.N. & Hanaor, D.A.H., *"Oxygen redox in battery cathodes: A brief overview"* (arXiv:2408.09942) — KB `工程与能源` (kb_id `8fa4db59-adde-4d6d-9fdb-2c375400e631`), doc `materials__2408.09942__...md (parts 1 & 2 of 2)`.

### 1. The core contribution: extra capacity beyond the cation limit

In conventional LiTMO₂/NaTMO₂ cathodes, capacity comes from transition-metal (TM) redox — the change in TM oxidation state compensating for Li⁺/Na⁺ removal:

> LiTM³⁺O₂ → Li₍₁₋ₓ₎TM³⁺₍₁₋ₓ₎TM⁴⁺ₓO₂ + xLi⁺ + xe⁻  (Eq. 1)

But real cathodes **"have achieved and even exceeded such levels of charge density, delivering an overcapacity exceeding the transition metal oxidation limit."** Oxygen redox explains this excess: oxide anions O²⁻ themselves donate electrons during charging — **"acting as reducing agents, which may compensate for the absence of oxidizable transition metals."** This **"may allow greater energy storage capacity in battery electrodes than would otherwise be theoretically predicted."**

The canonical case is **Li₂MnO₃**, where Mn stays at +4 (its t₂g frontier level is too low to oxidize) yet 1.4 Li⁺ per formula unit de-intercalate — the capacity is attributed to oxygen redox activity (refs 2, 13, 18, 19).

The reversible reaction is summarized as peroxo-type species formation:

> O²⁻ ⟷ (O₂)ⁿ⁻   (Eq. 2)

An alternative descriptor is the **formation of electron holes on oxygen atoms**, which explains anion-driven excess capacity in alkali-rich cathodes *without* detrimental O₂ gas evolution.

### 2. The mechanism: orphaned O 2p states near the Fermi level

For oxygen redox to occur, **"orbitals with p characters should be lifted closer to the Fermi level so they, too, become labile for electrochemical electron extraction."** This happens when oxygen's coordination environment changes:

- **Normal LiTMO₂:** each O is coordinated by 3 TM + 3 Li. Hybridization with TM s/p orbitals pushes the bonding p-like orbitals ~10 eV below the Fermi level — electrochemically inert.
- **Li-excess / Na-excess (Li₂TMO₃-type):** the TM layer is partly substituted by alkali ions, so some O atoms are coordinated by **fewer than three TM ions** (Li–O–Li coordination). With no TM hybridization, **"unhybridized or orphaned O 2p states"** sit near the TM t₂g states and become **labile for redox**.

**Prerequisite (stated explicitly):** "Nonbonding O 2p states, also known as orphaned O 2p states, are widely considered to be **a prerequisite** for the occurrence of oxygen redox effects in transition metal oxides." Activation "commonly... occurs under **deep charge conditions**, such as lithium de-intercalation under high voltages."

**Ilmenite-type NaTMO₃ (second family):** here O redox arises not from over-coordination but from O being **under-coordinated** — O is coordinated by only 2 TM + 2 Na. This TM under-coordination again creates non-bonding O 2p states just below E_F.

### 3. Quantified capacity contribution

- **Na₂₋ₓRuO₃:** observed capacity of **180 mAh g⁻¹** (0 < x < 1.5), corresponding to ~**1.4 electrons per formula unit**; the additional **~0.4 electron capacity was attributed to a reversible oxygen redox mechanism** after de-sodiation to ilmenite-type Na₁RuO₃.
- Voltage signature: once O redox initiates, Na₁₋ₓRuO₃ showed a **voltage spike from 2.2 V to 3.4 V** — hinting O redox can generate a **higher operating potential than TM redox alone** (calculated 3.27 V vs. observed ~3.4 V, validating the DFT approach).
- **Li-excess Li₄Mn₂O₅ (Eq. 3):** combined cationic/anionic redox, Li₄⁺Mn₂³⁺O₅²⁻ → 4Li⁺ + 4e⁻ + Mnₓ⁴⁺Mn₂₋ₓ⁵⁺O₅₋ₓ²⁻Oₓ¹⁻, where **x indicates the extent of oxygen participation**. Sequentially: Mn³⁺→Mn⁴⁺ oxidation, then O²⁻→O¹⁻ oxidation, and finally at LiₓMnO₅ (x<1) Mn⁴⁺→Mn⁵⁺ with octahedral-to-tetrahedral change.

**Computational prediction of the contribution:** integrate the O 2p states over a narrow window below E_F (typically **2.0–2.5 eV**) in the lithiated material to count labile oxygen electrons. Table 1/2 give labile O 2p populations (e.g., NaVO₃ 0.17 e / 5.91 V; NaCrO₃ 1.43 e / 4.24 V; NaMnO₃ 1.23 e; NaRuO₃ 1.40 e; NaPdO₃ 2.10 e; NaAgO₃ 2.51 e). **4d (fifth-row) TM oxides generally show higher labile oxygen populations** due to greater 4d–2p covalency pushing O 2p population up to the Fermi level.

### 4. The cost: capacity fade and O₂ release

The gain is not free. Key drawback, stated in both §3.1 and the Summary:

- **"Although anionic redox increases the cathode capacity, the reduced O ions have a strong tendency towards bonding to each other and leaving the lattice as O₂ gas."**
- Materials with insufficient TM–O covalency undergo **TM diffusion and oxygen gas release near particle surfaces**, causing irreversible structural decay after the first cycle.
- Symptoms: **high first-cycle charge/discharge plateaus**, **voltage fade**, **lower long-term capacity**, and often a **layered-to-spinel phase transformation**. This is a known limiter on Li-rich layered Mn-oxide cathodes.
- O₂ evolution is **a significant ignition/flamillability hazard**.
- **Mitigation:** surface modification to inhibit oxygen loss; **surface fluorination** is highlighted as effective — metal-fluoride bonds strengthen TM–O bonds locally and reduce Jahn-Teller distortion, stabilizing O sites. There is a tradeoff between initial capacity diminishment and long-term retention, so an optimal modification level must be found.

### 5. Methodological caveat (why the numbers are DFT-derived)

Directly probing anionic redox is not possible experimentally; **DFT is the main approach**. But standard **GGA/PBE/revPBE/BJ functionals are unsuitable** — they delocalize 3d states and produce wrong band structures in these strongly correlated oxides. Required: **Hartree-Fock hybrid functionals** (mixing parameter α, benchmarked against GW; used here with α = 0.2 for 3d NaTMO₃) and **GGA+U** (used with U_eff = 2.0 eV for 4d compounds, where localization is weaker). Determining α and U empirically remains the central challenge.

### Bottom line

Oxygen redox adds usable cathode capacity by letting oxide anions — not just transition metals — supply the charge compensation for alkali extraction. It works where **orphaned, non-hybridized O 2p states** are lifted near the Fermi level (Li/Na-excess layered oxides with <3 TM-coordinated O, or under-coordinated O in ilmenite NaTMO₃), enabling O²⁻ ⟷ (O₂)ⁿ⁻ / O-hole formation. It delivers measured gains (e.g., ~0.4 e⁻/f.u. ≈ the extra capacity in Na₂₋ₓRuO₃, 180 mAh g⁻¹) and can even raise operating voltage — **but** the reduced O species tend to leave as O₂ gas, producing permanent capacity fade and a fire hazard unless mitigated (e.g., by fluorination).

---

**Retrieval note:** MCP connectivity was checked first (`backend_status`/`kb_list`). The first calls returned `ReadTimeout`; on retry the MCP layer recovered and all subsequent tool calls succeeded. Search path: `kb_list(lightweight=true)` → `kb_search_vector(balance_kbs=true)` → `kb_doc_read` of both document parts. The same source document appears duplicated across three separate KBs (`Corpus-Chunks800`, `Corpus-Struct`, `Corpus-Paras` — all "DeepRead baseline reproduction index" collections) and as the substantive copy in `工程与能源`; the duplicate chunk scores were 0.7893/0.7892/0.7892/0.7891, i.e., the same text indexed four times. Content verification was done against the full text of `工程与能源`, not the retrieval snippets, and the search-stats/vector-coverage dimension was not separately reported since this was a content question rather than a KB audit.

### [b] BQ08 — 186.3s, 4 tool calls, tokens out 580

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

Oxygen (anionic) redox adds usable capacity beyond what transition-metal redox alone can supply: in alkali-rich oxides, oxide anions (O²⁻) donate electrons during charging—acting as reducing agents—and can be summarized as the formation of peroxo-type species, O²⁻ ↔ (O₂)ⁿ⁻, or as electron holes on oxygen. This excess capacity arises because in Li-/Na-excess (or under-coordinated) environments some O ions are coordinated by fewer than three TM ions, leaving "orphaned"/non-bonding O 2p states lifted close to the Fermi level so they become electrochemically labile alongside the TM t₂g states. The review notes that capacities have even exceeded the transition-metal oxidation limit (e.g., ~180 mAh g⁻¹ in Na₂₋ₓRuO₃, with ~0.4 extra electron per formula unit from reversible O redox, plus a voltage rise from 2.2 V to 3.4 V), and that O redox tends to be more dominant in 4d than 3d TM oxides. However, the reduced O ions tend to bond to each other and leave the lattice as O₂ gas, causing permanent capacity fade and a flammability hazard, so mitigation strategies such as surface fluorination are needed to exploit the extra capacity. Used file: `materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overvie.md` (the only relevant file in the corpus).

### [c] BQ08 — 70.6s, 3 tool calls, tokens out 525

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

Based on the retrieved chunks, oxygen redox contributes to cathode capacity by having oxide anions (O²⁻) donate electrons during charging, "thus interestingly acting as reducing agents, which may compensate for the absence of oxidizable transition metals" — this allows "greater energy storage capacity in battery electrodes than would otherwise be theoretically predicted." The retrieved text notes that actual cathode materials "achieved and even exceeded such levels of charge density, delivering an overcapacity exceeding the transition metal oxidation limit," and that oxygen redox "was discovered to significantly contribute toward the overall battery capacity in Li-excess disordered spinel-type cathodes." Harnessing anionic redox enables "the maximization of capacities beyond what would be expected solely based on cationic redox pathways," though it is linked to "a large first-cycle capacity loss" and irreversible oxygen-mediated decompositions that limit practical use. Cited chunks: `materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overvie__k03.md`, `__k23.md`, `__k01.md`, `__k14.md`, `__k13.md`, and `__k00.md`.

### [a] BQ09 — 254.3s, 7 tool calls, tokens out 1935

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

I have everything needed. Here is the answer.

## MLP-SLAM: The Problem and the Solution

### The Problem It Addresses

**Standard V-SLAM degrades in dynamic environments.** Conventional Visual SLAM systems — including SOTA ones like ORB-SLAM2, ORB-SLAM3, LSD-SLAM, and Direct Sparse Odometry — rely on the **static-world assumption**. They perform with high precision where objects are predominantly static, but their precision **deteriorates in real-world dynamic scenes** containing numerous movable objects (pedestrians, cars, buses), which are common outdoors.

**Why prior solutions fall short** — the paper categorizes existing approaches into three types, each with limitations:

- **Type I (geometric-only):** Classifies feature points using geometric cues alone (epipolar error, reprojection error, intensity, optical flow). Limited on its own.
- **Type II (semantic prior, e.g., DynaSLAM):** Uses object detection / semantic segmentation to discard all features inside bounding boxes or masks of "dynamic-class" objects. **Key flaw — information loss:** statically parked cars on the roadside get their features erroneously removed even though they are static and actually valuable for camera pose estimation.
- **Type III (hybrid, e.g., DynaSLAM II, CFP-SLAM, PointSLOT, VDO-SLAM, D-SLAM):** Combines deep-learning priors with geometric methods, but many use only **partial geometric information** (e.g., only epipolar error, only reprojection error), and they **require manual parameter tuning, lack generality, and are laborious to fine-tune**. DynaSLAM-style approaches also suffer **high latency** (MaskRCNN dependency) and data-association problems in object pose estimation.

An additional gap: **no public dataset existed** for directly evaluating dynamic/static feature classification — evaluation was indirect via SLAM metrics, which is unreliable because of RANSAC randomness in camera pose estimation.

### How MLP-SLAM Solves It

MLP-SLAM is a **real-time stereo SLAM system built on ORB-SLAM2** with an added **dynamic/static object discriminator module** — the first application of a machine-learning (MLP) method to distinguish dynamic vs. static feature points in the SLAM field.

**Pipeline:**
1. Stereo images → **ORB feature extraction**.
2. **Object detection and tracking** on the left image (YOLOv7 + Deep SORT).
3. **Coarse camera pose estimation** using features outside the potential-dynamic-object bounding boxes, plus background static features inside the boxes filtered by a **Depth Filter Module (DFM)**.
4. Each remaining feature point inside a bounding box generates an **input feature vector vᵢ = {e_I, e_D, e_Re}** — combining **image intensity error, epipolar error, and reprojection error**. This is the "complete geometric information" that avoids the information loss of partial-geometry approaches.
5. The **MLP classifies each feature point** as static (0) or dynamic (1): cᵢ = argmax(yᵢ), where yᵢ = M(vᵢ).
6. **Fine camera pose estimation** uses all static feature points (minimizing reprojection error over static correspondences).

**Key design advantages:** it uses **comprehensive geometry** (no information loss), needs **no manual parameter configuration**, and is therefore **general across situations**.

**Supporting contributions:** a publicly released dataset of **over 50,000 feature points** from KITTI Odometry for directly training/testing such discriminators (plus a separate depth-filter dataset).

**Results (KITTI Odometry & KITTI360):** highest average precision and fastest speed among dynamic SLAM systems — **62.81 ms latency** vs. DynaSLAM 519.37 ms, DynaSLAM II 80.15 ms, VDO-SLAM 86.97 ms, PointSLOT 73.6 ms. Only **17.50 ms/frame extra cost** over ORB-SLAM2 (MLP inference itself is just **0.18 ms**). Ablation: MLP-only (avg ATE 1.97) beats object-tracking-only (2.67), and both combined is best (1.48).

### Source Reference

- **"MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping"** — Taozhe Li¹ and Wei Sun², arXiv:2410.10669 (robotics)
  - KB: **计算机与人工智能** (`kb_id: b1199132-e4d4-4305-8c2e-82dc1753b0ba`)
  - Path: `计算机与人工智能/robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou.md` (parts 1 and 2 of 2)
  - Code/dataset: https://github.com/TaozheLi/MLP-SLAM (upon paper acceptance)

*Certainty: High — the problem statement, method, and results were verified directly against the full document text (not just metadata).*

### [b] BQ09 — 125.2s, 5 tool calls, tokens out 701

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

MLP-SLAM addresses the degradation of visual SLAM accuracy in dynamic outdoor environments (pedestrians, cars, buses), where classic systems like ORB-SLAM2 rely on a static-world assumption. Prior dynamic-SLAM approaches (Type I geometric, Type II semantic-mask like DynaSLAM, Type III hybrids) either need laborious manual parameter tuning, lack generality, or discard valid static points — e.g. DynaSLAM wrongly removes features on parked cars and guardrails, causing information loss and high latency from MaskRCNN. MLP-SLAM's solution is a Multilayer Perceptron classifier that labels each feature point as static or dynamic using complete geometric information (no manual parameters), so camera pose is estimated only from static correspondences via re-projection-error minimization. It also contributes a public 50,000+ feature-point dataset from KITTI Odometry for direct discriminator evaluation, and reports the highest average precision and fastest speed among dynamic SLAM systems on KITTI Odometry and KITTI360.

Source: `robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou.md`.

### [c] BQ09 — 128.8s, 3 tool calls, tokens out 559

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

MLP-SLAM addresses the degradation of visual SLAM performance in dynamic environments containing numerous movable objects such as pedestrians, cars, and buses, where accuracy drops sharply in outdoor scenes. Its key idea is an MLP-based dynamic/static feature-point discriminator built on top of ORB-SLAM2: the system performs ORB feature extraction, then object detection and tracking on the left image, and filters out dynamic feature points before the coarse estimation stage, keeping only points outside bounding boxes or classified as static by the MLP model (`k00.md`, `k09.md`, `k10.md`). Unlike DynaSLAM, which discards all features within semantic masks and suffers high latency from MaskRCNN, MLP-SLAM uses the MLP to identify real dynamic objects rather than discarding whole regions, avoiding information loss (`k04.md`, `k18.md`, `k20.md`). The authors report this is the first application of an MLP as a dynamic/static feature discriminator in the SLAM domain, trained on a purpose-built dataset of over 50,000 feature points (`k00.md`, `k06.md`, `k15.md`).

### [a] BQ10 — 248.4s, 9 tool calls, tokens out 2414

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

I have the complete source document. Here is the synthesis.

## Strategies for Tumor Control Under Immune Evasion and Chemotherapy Resistance

The knowledge base contains one directly relevant source: a mathematical-oncology modeling study (Mokari & Morsky, Florida State University, April 2026). It builds an ODE model of B-cell lymphoma with effector (CD8⁺ T) cells, an immune-resistant tumor subpopulation **T₁**, and an immune-sensitive subpopulation **T₂** (which may or may not also be chemo-resistant), and derives control strategies via equilibrium/stability analysis and bifurcation diagrams.

### 1. The central finding: therapy must match the *mechanism* of resistance

Two distinct immune-evasion mechanisms are modeled, and they demand **different** therapies:

| Resistance mechanism | What it does | Best parameter target | Therapeutic focus |
|---|---|---|---|
| **Immune checkpoint regulation** (PD-L1/PD-1) | Blocks effector killing, but the effector survives the encounter | ↓ μ (reduce immune exhaustion) | **Checkpoint inhibitors** |
| **Reduced antigen presentation** | Lowers effector recognition and binding; reduces both activation and inactivation of effectors | ↑ ρ (effector activation), ↓ μ | **CAR-T therapy, cancer vaccines** |
| **Immune-sensitive phenotype dominant** (T₂-only) | Wild-type tumor | ↑ σ, ↓ δ (grow the effector pool) | **Adoptive T-cell transfer, cytotoxic therapy** |

> "When the immune-resistant subpopulation employing immune checkpoint regulation dominates, tumor control is highly sensitive to the immune exhaustion rate... In contrast, when reduced antigen presentation drives resistance, stability depends more strongly on effector activation and exhaustion, supporting strategies such as checkpoint inhibitors, CAR-T therapy, or cancer vaccines." (part 3, Discussion)

A key structural result: **when checkpoint evasion dominates, tumor control cannot be achieved by modulating immune parameters at all — only by altering θ₁** (the resistance phenotype itself) once φ > 0.003. Reduced-antigen-presentation tumors are also **more robust against weak chemotherapy**, requiring stronger effector responses.

### 2. Combination immuno-chemotherapy beats monotherapy

Chemotherapy alone (χ) reduces tumor burden and directly kills T₁ (which is assumed chemo-sensitive), but its main value is **synergy**:

- "Chemotherapy significantly enlarges the parameter region corresponding to tumor control or tumor-free equilibria."
- Immune dynamics alone are "generally insufficient to fully eliminate the tumor"; adding chemotherapy "expands the parameter region exhibiting tumor-free or low population equilibria."
- Critically, effector presentation gains (↑σ, ↓δ) that are **not helpful without chemotherapy** become effective **when chemotherapy is co-administered**.
- The strongest specific recommendation: *"checkpoint inhibitors combined with moderate chemotherapy provide the most effective control strategy"* (when T₁ dominates under checkpoint evasion).
- Caveat: high chemotherapy intensity is not necessarily better — "excessively large treatment intensities are neither feasible nor safe."

### 3. Sequential, composition-guided treatment protocols

The paper proposes **sequential therapy ordered by tumor composition**:

- **Starting from T₁-dominant:** chemotherapy first to reduce burden → then immunotherapy to maintain control. *(Or the reverse: immunotherapy first to shrink the tumor, then chemotherapy to clear residual resistant cells.)*
- **Starting from T₂-dominant:** chemotherapy reduces burden but risks resistant escape → immunotherapy applied afterward to stabilize.
- **If coexistence is predicted:** chemotherapy first to eliminate T₁, leaving a low-population T₂-only equilibrium → then immunotherapy to attempt elimination. **Residual risk:** if only controlled (not eliminated), emergent T₁ mutants can cause resurgence.

### 4. The "fight to not lose" framing (adaptive therapy)

Beyond elimination-vs-control, the paper contrasts aggressive elimination ("fight to win") with long-term resistance management ("fight to not lose"). It endorses **adaptive therapy** (control rather than eradicate, exploiting competition between sensitive and resistant cells, dynamically adjusting dose to tumor response) as an alternative to maximum-tolerated-dose regimens.

### 5. Threshold conditions and precision medicine

Control hinges on a **bistable threshold** (Proposition 1): tumor-free equilibrium is stable iff

σ/(δ + ωχ) > max{α₂ − θ₂χ, (α₁ − χ)/θ₁}

i.e. effective immune strength must exceed the maximal tumor growth rate. Because "small variations in immune competence or tumor immunogenicity may significantly alter therapeutic response," the authors argue for **biomarker-guided selection** — PD-L1 expression, T-cell infiltration, exhaustion markers, antigen-presentation profiles — rather than uniform treatment. *"Non-personalized, uniform treatment often fails."*

**Source:** `生命科学与医学/immunology__2604.01385__strategies-for-tumor-elimination-and-control.md (parts 1–3 of 3)`, KB `生命科学与医学` (b28f0a25-…), with mirrored chunks in `Corpus-Paras`, `Corpus-Struct`, and `Corpus-Chunks800`. Key passages: §2.2 (evasion mechanisms), §3.2 (immuno-resistance-only bifurcation, Table 2), §3.3 (chemo+immuno-resistance), Discussion (sequential protocols). Code: github.com/NazMokari/Adaptive-Cancer-Therapy.

**Certainty: high** — a single coherent primary source whose abstract, results, and discussion all consistently address the question; content verified by direct document reads, not vector snippets alone. 

*Blind spot:* this is a **theoretical modeling paper** for B-cell lymphoma, not a clinical trial or review of empirical outcomes. All parameter targets (σ, δ, μ, ρ, χ, θ) are model quantities, and the therapeutic recommendations (checkpoint inhibitors, CAR-T, vaccines, adoptive transfer) are derived from bifurcation analysis, not measured clinical results. The KB contains no other document on this topic.

### [b] BQ10 — 162.4s, 4 tool calls, tokens out 659

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**Answer:** Based on `immunology__2604.01385__strategies-for-tumor-elimination-and-control.md`, the source is a mathematical model of tumor–immune dynamics, not a clinical review. It identifies two distinct evasion mechanisms — immune checkpoint evasion and reduced antigen presentation — and shows (Table 2) that therapy must target whichever mechanism dominates: checkpoint evasion is best addressed by lowering immune exhaustion (μ) or raising effector recruitment/activation (σ, ρ), i.e., checkpoint inhibitors combined with moderate chemotherapy, whereas reduced antigen presentation is better countered by boosting antigen-presentation-linked activation (ρ, μ) via CAR-T therapy or vaccines. Its central strategic conclusion is combination therapy: chemotherapy shrinks the tumor and hits the resistant subpopulation while immunotherapy enhances immune-mediated suppression, together expanding the parameter region yielding tumor-free or low-burden equilibria and delaying resistance emergence. It also stresses phenotype-guided, precision-medicine selection using biomarkers (PD-L1, T-cell infiltration, exhaustion markers, antigen-presentation profiles), and notes that increasing immune recruitment, decreasing immune death, or enhancing activation improves outcomes — and that large coexistence equilibria are worrying because heterogeneous populations adapt to therapy. No other file in the directory addresses this topic.

### [c] BQ10 — 108.2s, 2 tool calls, tokens out 396

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

The retrieved evidence is sufficient to answer.

Tumor control under immune evasion and chemotherapy resistance hinges on which resistance mechanism dominates the tumor population. The paper models competition and cooperation among effector cells, chemo-resistant tumor cells, and immuno-resistant tumor cells across distinct immune-evasion strategies, and identifies threshold conditions governing tumor persistence, elimination, and phenotype dominance under varying therapeutic intensities. When immune checkpoint regulation drives resistance, tumor control is highly sensitive to the immune exhaustion rate, indicating that checkpoint inhibitors are the most effective therapy. In contrast, when reduced antigen presentation drives resistance, stability depends more strongly on effector activation and exhaustion, supporting a different therapeutic emphasis. The authors frame these bifurcation results as a foundation for designing targeted and combination therapies aimed at suppressing resistance and achieving long-term tumor control.

Cited chunks: `Corpus-Chunks800/immunology__2604.01385__strategies-for-tumor-elimination-and-control__k00.md`, `...__k37.md`, `...__k36.md`, `...__k14.md`.
