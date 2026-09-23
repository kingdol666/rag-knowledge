# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-20 04:25 UTC · same 50-paper corpus · questions: 1 · tracks: a, b, c

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| BQ01 | a | 255.9 | 8 | 186414 | 2854 | 99328 | 1.0530840000000001 |
| BQ01 | b | 146.9 | 7 | 156050 | 1170 | 49408 | 0.834204 |
| BQ01 | c | 100.1 | 2 | 86279 | 637 | 32000 | 0.46332 |

**Totals**: latency avg 167.6s · tokens in 428743 · out 4661 · cost $2.3506

## Verbatim answers

### [a] BQ01 — 255.9s, 8 tool calls, tokens out 2854

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

I now have the complete, authoritative source. Here is the answer.

---

## How the Transformer Computes Attention, and Why It Replaces Recurrence and Convolution

**Source:** Vaswani et al., *"Attention Is All You Need"* (arXiv:1706.03762) — in KB `计算机与人工智能` (Computer Science & AI), doc `artificial-intelligence__1706.03762__attention-is-all-you-need.md` (parts 1 & 2 of 2).

### 1. The attention function itself

An attention function maps **a query and a set of key–value pairs to an output**, all vectors. The output is a **weighted sum of the values**, where the weight for each value comes from a compatibility function between the query and the corresponding key:

> "An attention function can be described as mapping a query and a set of key-value pairs to an output... The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key." (§3.2)

### 2. Scaled Dot-Product Attention (§3.2.1)

The specific mechanism: queries and keys of dimension `d_k`, values of dimension `d_v`. Take the dot product of the query with all keys, **divide each by √d_k**, and apply a softmax to get the weights on the values. Queries/keys/values are packed into matrices **Q, K, V** so it computes for all positions at once:

```
Attention(Q, K, V) = softmax( QKᵀ / √d_k ) · V        (Eq. 1)
```

**Why the √d_k scaling:** for large `d_k`, dot products grow large in magnitude, pushing softmax into regions with **extremely small gradients**; scaling counteracts this. The paper notes dot-product attention is otherwise identical to "additive attention" [Bahdanau] except for this factor — and is much faster and more space-efficient because it uses highly optimized matrix multiplication code.

### 3. Multi-Head Attention (§3.2.2)

Rather than one attention function on `d_model`-dimensional Q/K/V, the model **linearly projects Q, K, V h times with different learned projections** into `d_k`, `d_k`, `d_v` dimensions, runs attention in parallel on each, concatenates the `d_v`-dimensional outputs, and projects again:

```
MultiHead(Q,K,V) = Concat(head_1, ..., head_h) W^O
   where head_i = Attention(Q W_i^Q, K W_i^K, V W_i^V)
```

- Reason: "Multi-head attention allows the model to **jointly attend to information from different representation subspaces at different positions**. With a single attention head, averaging inhibits this."
- The paper's config: **h = 8 heads, d_k = d_v = d_model/h = 64**, so total cost ≈ single-head full-dimension attention.

### 4. Where attention is used (three ways, §3.2.3)

1. **Encoder–decoder attention** — queries from the previous decoder layer, keys/values from the encoder output → each decoder position attends over all input positions.
2. **Encoder self-attention** — Q, K, V all come from the same place (previous encoder layer); each position attends to all positions in the previous layer.
3. **Decoder self-attention (masked)** — each position attends only up to and including itself; to "prevent leftward information flow... to preserve the auto-regressive property," illegal connections are **masked to −∞ before the softmax**.

Encoder and decoder are each a **stack of N = 6 identical layers**; each sub-layer is wrapped in a residual connection + layer norm: `LayerNorm(x + Sublayer(x))` (§3.1).

### 5. Why it replaces recurrence and convolution (§4 "Why Self-Attention")

The paper's three desiderata: **(a)** total computational complexity per layer, **(b)** parallelizable computation (minimum sequential operations), **(c)** path length between long-range dependencies. Comparison (Table 1):

| Layer Type | Complexity / Layer | Sequential Ops | Max Path Length |
|---|---|---|---|
| **Self-Attention** | O(n²·d) | **O(1)** | **O(1)** |
| Recurrent | O(n·d²) | **O(n)** | O(n) |
| Convolutional | O(k·n·d²) | O(1) | O(log_k(n)) |
| Self-Attention (restricted) | O(r·n·d) | O(1) | O(n/r) |

Key arguments:

- **vs. Recurrence** — recurrent models factor computation along symbol positions and generate hidden state `h_t` as a function of `h_{t-1}`; this **"inherently sequential nature precludes parallelization within training examples"** (§1). A self-attention layer **connects all positions with a constant O(1) number of sequential operations**, versus O(n) for a recurrent layer. Self-attention is faster than recurrent layers when **sequence length n < representation dimensionality d** — usually true for word-piece/byte-pair representations in translation.
- **vs. Convolution** — a single convolutional layer with kernel `k < n` **does not connect all pairs of positions**; covering them requires stacking O(n/k) contiguous layers or O(log_k(n)) dilated layers, **lengthening the longest paths**. Convolutional layers are also generally **more expensive than recurrent by a factor of k**. Separable convolutions reduce cost to O(k·n·d + n·d²) — but even with `k = n`, that equals the complexity of **a self-attention layer plus a point-wise feed-forward layer**, exactly the paper's design.
- **Long-range dependencies** — shorter paths between any two positions make long-range dependencies easier to learn. Self-attention gives **O(1) path length** vs. **O(n)** for recurrence and **O(log_k n)** for convolutions.
- **Interpretability (side benefit)** — individual heads learn different tasks and show behavior related to syntactic and semantic structure.

**Cost of the design:** O(n²·d) per layer and reduced effective resolution from averaging attention-weighted positions — the paper counteracts the latter with **Multi-Head Attention** (§2, §3.2.2), and proposes **restricted/neighborhood self-attention** (size r) for very long sequences as future work.

### 6. The consequence: positional encoding

Because the model contains **no recurrence and no convolution**, order information must be injected explicitly — **"positional encodings" added to the input embeddings** at the bottom of the encoder/decoder stacks, using sine/cosine functions of different frequencies (§3.5). Ablations showed learned positional embeddings gave nearly identical results; sinusoids were chosen because they may **extrapolate to sequence lengths longer than seen in training**.

### 7. Empirical result (§6, §7)

- Replaces **"the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention"** — the first sequence transduction model relying **entirely on attention**, without sequence-aligned RNNs or convolution.
- Faster training, more parallelizable: **28.4 BLEU** on WMT 2014 En→De (beating prior best incl. ensembles by >2 BLEU); **41.8 BLEU** En→Fr single-model SOTA after **3.5 days on 8 GPUs**; base model 12 hours on 8 P100s.
- Ablations (Table 3): single-head attention is **0.9 BLEU worse** than the best multi-head setting; reducing key size `d_k` hurts quality; bigger models better; dropout helps against over-fitting.
- Generalizes beyond translation — applied to **English constituency parsing**, outperforming the BerkeleyParser even when trained only on the 40K-sentence WSJ set (§6.3).

### Certainty and blind spots
- **High confidence** — all claims above are verbatim-anchored in the paper's abstract, §1–§4, Table 1, §6–§7, retrieved from KB `b1199132-e4d4-4305-8c2e-82dc1753b0ba`;
- The KB also contains **BERT** (arXiv:1810.04805, same KB) as a downstream consumer of the Transformer encoder, should you want the "how it was built upon" angle — I did not read it here since the question is answerable entirely from the primary source.

### [b] BQ01 — 146.9s, 7 tool calls, tokens out 1170

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Answer**

The Transformer computes attention by mapping a query and a set of key-value pairs to an output: it takes the dot products of the query with all keys, divides each by √d_k, and applies a softmax to obtain weights on the values (Section 3.2.1, Eq. 1: Attention(Q,K,V) = softmax(QKᵀ/√d_k)V). The 1/√d_k scaling counteracts the tendency of large dot products to push softmax into regions with extremely small gradients. Rather than one attention function, multi-head attention linearly projects Q, K, V h = 8 times into d_k = d_v = 64 dimensions, runs attention in parallel per head, and concatenates and re-projects the results, letting the model attend to information from different representation subspaces. Decoder self-attention masks illegal (future) positions to −∞ before softmax to preserve auto-regression.

It replaces recurrence and convolution because it "eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output," enabling significantly more parallelization (twelve hours on eight P100 GPUs to state of the art). Table 1 justifies this: self-attention has O(1) sequential operations and O(1) maximum path length versus O(n) sequential operations and O(n) path length for recurrent layers, and O(log_k(n)) path length for convolutional ones — so self-attention connects any two positions in a constant number of operations and offers better parallelization. The cost is a trade-off: O(n²·d) complexity per layer versus O(n·d²) for recurrent and O(k·n·d²) for convolutional layers. Because the model contains no recurrence or convolution, positional encodings are added to the input embeddings to inject token order.

**File used:** `artificial-intelligence__1706.03762__attention-is-all-you-need.md` (Sections 3.2.1, 3.2.2, 3.2.3, 3.4/3.5, Table 1, Abstract).

### [c] BQ01 — 100.1s, 2 tool calls, tokens out 637

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Answer (from retrieved chunks only):**

The retrieved chunks state that the Transformer is "the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention" (`artificial-intelligence__1706.03762__attention-is-all-you-need__k20.md`; identical text in `..._k19.md`). Attention is applied as multi-head attention in three ways: in "encoder-decoder attention" layers "the queries come from the previous decoder layer, and the memory keys and values come from the output of the encoder," allowing every decoder position to attend over all input positions (`..._k06.md`, `..._k07.md`); self-attention relates "different positions of a single sequence in order to compute a represent[ation]" (`..._k01.md`). It dispenses with recurrence and convolution because the authors propose an architecture "eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output," which "allows for significantly more parallelization" (`..._k02.md`, `..._k01.md`), and it is "the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequencealigned RNNs or convolution" (`..._k03.md`, `..._k02.md`). The abstract confirms the design is "based solely on attention mechanisms, dispensing with recurrence and convolutions entirely" (`..._k00.md`), and the conclusion reports it "can be trained significantly faster than architectures based on recurrent or convolutional layers" (`..._k20.md`, `..._k19.md`).

**Caveat on grounding:** the retrieved chunks describe *that* attention is used and *why* recurrence/convolution were dropped (parallelization, speed, global dependency modeling), but they do **not** contain the actual equations for how scaled dot-product or multi-head attention is computed (Sections 3.2.1/3.2.2 were not retrieved), nor the explicit complexity arguments from Section 4. On the "how is attention computed" part, the retrieved evidence is insufficient.
