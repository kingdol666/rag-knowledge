# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-20 04:12 UTC · same 50-paper corpus · questions: 1 · tracks: c

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| Q1 | c | 140.2 | 3 | 124772 | 587 | 0 | 0.638535 |

**Totals**: latency avg 140.2s · tokens in 124772 · out 587 · cost $0.6385

## Verbatim answers

### [c] Q1 — 140.2s, 3 tool calls, tokens out 587

**Q:** In the paper Attention Is All You Need, what positional encoding does the Transformer use? Answer in English.

The Transformer uses fixed sinusoidal positional encodings built from sine and cosine functions of different frequencies, defined as PE(pos,2i) = sin(pos/10000^(2i/d_model)) and PE(pos,2i+1) = cos(pos/10000^(2i/d_model)), where pos is the position and i is the dimension (Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k10.md). These encodings have the same dimension d_model as the embeddings so the two can be summed, and they are added to the input embeddings at the bottoms of the encoder and decoder stacks (Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k09.md). The wavelengths form a geometric progression from 2π to 10000·2π, chosen because the authors hypothesized this would let the model easily learn to attend by relative positions, since PE(pos+k) can be represented as a linear function of PE(pos) (Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k09.md). The paper notes it also tried learned positional embeddings and got nearly identical results, but chose the sinusoidal version for its potential to extrapolate to longer sequence lengths (Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k09.md).
