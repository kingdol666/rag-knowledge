# Live Three-Way Same-Question Test — 2026-09-20 (real subagent run)

**Question (identical for all tracks):**
> In the paper "Attention Is All You Need", what are the main components of the Transformer architecture, and what kind of positional encoding does the paper use?

**Gold check:** encoder–decoder, N=6 layers each; encoder sub-layers = multi-head self-attention + position-wise FFN (ReLU, 512→2048); decoder adds masked self-attention + cross-attention; residual + LayerNorm; positional encoding = fixed sine/cosine functions of different frequencies (sinusoids), chosen over learned embeddings for possible length extrapolation.

| | Track A · Platform (QDCVR v2) | Track B · Bare agent | Track C · Dense RAG |
|---|---|---|---|
| Retrieval path | kb_search_vector ×5 category KBs → top-1 gold doc (0.7094) | filename + grep "positional encoding" | Corpus-Chunks800 top-10 → top chunk = gold paper k00 (0.6395) |
| Retrieval time | 2.33 s | ~0 (scripted I/O) | 0.91 s |
| Evidence window | head 3k + **9 continuation reads (~25.2k chars, §3–§3.5)** | read lines 55–160 directly | 4,000-char pack — **cut mid-SRC-8; k07+ never entered evidence** |
| Gate/abstain | 8/8 fast-exit, no fallback | n/a | **partial abstention** on the positional-encoding sub-question |
| Total time | ~175 s (incl. gate reads + composing) | ~60 s | ~177 s (incl. pack + answer) |
| Correctness | ✅ full (components + sinusoid formulas + wavelength detail) | ✅ full (formulas + extrapolation rationale) | ⚠️ partial (components ✅; positional encoding → honest "insufficient evidence") |

## Key observations
1. **Track C live-reproduced the paper's fig3 behavior**: 4,000-char pack truncation → honest abstention on the part outside the window. The abstention is CORRECT pipeline behavior (the k07+ chunks cut by the cap are exactly where §3.5 positional encoding lives).
2. **Track A's continuation-read machinery fired for real** (abstract-only head → 9 offset windows), the first live same-question demonstration of that capability.
3. **Track B was fastest and most complete** — but depends on the filename being greppable (corpus design gives baselines this advantage).
4. Cross-track consistency: both A and B quote identical PE formulas — mutual corroboration, zero fabrication detected.

Raw transcripts: `track_a_platform.md` · `track_b_bare.md` · `track_c_rag.md` (this directory).
