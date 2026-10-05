# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-20 04:09 UTC · same 50-paper corpus · questions: 1 · tracks: a

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| Q1 | a | 118.5 | 5 | 111352 | 1387 | 109312 | 0.646091 |

**Totals**: latency avg 118.5s · tokens in 111352 · out 1387 · cost $0.6461

## Verbatim answers

### [a] Q1 — 118.5s, 5 tool calls, tokens out 1387

**Q:** In the paper Attention Is All You Need, what positional encoding does the Transformer use? Answer in English.

I have the full primary source text. Here is the answer.

## Answer

In *Attention Is All You Need* (Vaswani et al., 2017), the Transformer uses **fixed sinusoidal positional encodings** — sine and cosine functions of different frequencies — rather than learned positional embeddings.

### Key facts from the paper

**Why positional encoding is needed at all.** Because the model "contains no recurrence and no convolution," the authors had to inject order information explicitly: "we must inject some information about the relative or absolute position of the tokens in the sequence. To this end, we add 'positional encodings' to the input embeddings at the bottoms of the encoder and decoder stacks. The positional encodings have the same dimension $d_{\mathrm{model}}$ as the embeddings, so that the two can be summed."

**The actual formula (Section 3.5):**

$$PE_{(pos,\,2i)} = \sin\!\left(pos / 10000^{\,2i/d_{\mathrm{model}}}\right)$$
$$PE_{(pos,\,2i+1)} = \cos\!\left(pos / 10000^{\,2i/d_{\mathrm{model}}}\right)$$

where **pos** is the position and **i** is the dimension. Even dimensions use sine, odd dimensions use cosine.

**Properties the authors highlight:**
- Each dimension of the positional encoding corresponds to a sinusoid.
- The wavelengths form a **geometric progression from $2\pi$ to $10000 \cdot 2\pi$**.
- Rationale: "We chose this function because we hypothesized it would allow the model to easily learn to attend by relative positions, since for any fixed offset $k$, $PE_{pos+k}$ can be represented as a linear function of $PE_{pos}$."

**Learned vs. sinusoidal — the ablation.** The authors also tried learned positional embeddings and report: "we also experimented with using learned positional embeddings instead, and found that the two versions produced nearly identical results (see Table 3 row (E)). We chose the sinusoidal version because it may allow the model to **extrapolate to sequence lengths longer than the ones encountered during training**."

**How it is applied.** The positional encoding is *summed* with the input embeddings (not concatenated), and both are scaled consistently with the embedding layer, which multiplies weights by $\sqrt{d_{\mathrm{model}}}$ (Section 3.4, Embeddings and Softmax).

### Summary

| Aspect | The paper's choice |
|---|---|
| Type | Fixed (non-learned) sinusoidal |
| Functions | sin for even dims, cos for odd dims |
| Frequencies | $1/10000^{2i/d_{\mathrm{model}}}$, wavelengths in geometric progression $2\pi \to 10000\cdot2\pi$ |
| Combination | Added to input embeddings at the bottom of encoder and decoder stacks |
| Dimension | $d_{\mathrm{model}}$ (same as embeddings, so summation is valid) |
| Compared against | Learned positional embeddings — nearly identical results (Table 3, row E) |
| Reason for sinusoidal | Enables extrapolation to sequence lengths longer than those seen in training; supports relative-position attention via linear offsets |

### Sources

- **KB:** `计算机与人工智能` (Computer science and AI), kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba`
- **Document:** `artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md`
- **Section:** 3.5 Positional Encoding (with supporting context from Section 3.4 Embeddings and Softmax)
- **Cross-KB note:** The same paper also appears in the `Corpus-Paras`, `Corpus-Struct`, and `Corpus-Chunks800` benchmark indexes (chunks keyed to Section 6.2 Model Variations); those copies surfaced via the automatic cross-KB vector fallback but contained no content on positional encoding. The authoritative full text above is from `计算机与人工智能`.
