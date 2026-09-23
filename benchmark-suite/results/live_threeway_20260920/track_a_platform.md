# Track A — Platform KB (QDCVR v2)

## Metadata

- question: "In the paper 'Attention Is All You Need', what are the main components of the Transformer architecture, and what kind of positional encoding does the paper use?"
- rewritten_query (Phase 0): "Attention Is All You Need paper Transformer architecture main components encoder decoder multi-head self-attention feed-forward network positional encoding sinusoid"
- gate score (best doc: attention-is-all-you-need part 1 of 2): 8/8 — topic 3/3 (the corpus doc IS the queried paper), scenario 3/3 (Sections 3/3.1–3.5 directly answer architecture + positional encoding), evidence 2/2 (verbatim formulas and explicit statements read through kb_doc_read)
- phase timings:
  - Phase 1 vector search (5 KBs, top_k=10, threshold 0.35): 2.331 s total (计算机与人工智能 1.032 s, 自然科学与地球科学 0.327 s, 生命科学与医学 0.323 s, 工程与能源 0.323 s, 经济与社会 0.327 s)
  - Gate + continuation doc reads: 3.731 s total (head-window gate reads of top-3: 1.136 s; offset continuation reads of part 1: 2.595 s over 9 windows)
  - total: ~6.1 s
- librarian fallback (one targeted re-search): NOT needed — best doc scored 8 ≥ 6 at the gate

## Search Paths

- Phase 1 kb_search_vector over 5 category KBs. Merged, deduped by doc_path (best score kept), top-3:
  1. 计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md — 0.7094
  2. 计算机与人工智能/nlp__1810.04805__bert-pre-training-of-deep-bidirectional-transfor.md (part 2 of 3).md — 0.6698
  3. 计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 2 of 2).md — 0.6659
- Other KBs returned only cross-domain noise (chemistry/quantum/clinical/finance docs at 0.50–0.58), none above the AI-KB hits.
- Gate: kb_doc_read head window (max_chars 3000) on all top-3. Head of part 1 gave title/abstract only (mentions encoder-decoder + attention, no component detail); head of part 2 gave Section 6.2 model variations; BERT part 2 gave ablation tables (irrelevant). Since the head window lacked the answer, continued reading part 1 with offset windows until end-of-doc (totalLines 218, 9 windows, ~25.2k chars) and located Sections 3–3.5.
- No fallback re-search required; answer constructed only from text read through kb_doc_read.

## Answer

The paper "Attention Is All You Need" (Vaswani et al., 2017) proposes the Transformer, an encoder-decoder architecture built solely on attention mechanisms, dispensing with recurrence and convolutions entirely. The encoder is a stack of N = 6 identical layers, each with two sub-layers: a multi-head self-attention mechanism followed by a simple, position-wise fully connected feed-forward network (two linear transformations with a ReLU in between, d_model = 512, inner layer d_ff = 2048), each wrapped with a residual connection and layer normalization (LayerNorm(x + Sublayer(x))). The decoder is also a stack of N = 6 identical layers that adds a third sub-layer performing multi-head attention over the encoder stack's output, and its self-attention sub-layer is masked so positions cannot attend to subsequent positions (predictions for position i depend only on known outputs at positions < i). Attention itself is "Scaled Dot-Product Attention" — Attention(Q, K, V) = softmax(QK^T / sqrt(d_k))V — run in h parallel heads with learned linear projections and concatenated (Multi-Head Attention). Learned embeddings convert tokens to vectors, and a learned linear transformation + softmax converts the decoder output into next-token probabilities.

For positional encoding, since the model contains no recurrence and no convolution, the paper injects positional information by adding "positional encodings" to the input embeddings at the bottoms of the encoder and decoder stacks. It uses sine and cosine functions of different frequencies — PE(pos, 2i) = sin(pos / 10000^(2i/d_model)) and PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model)) — i.e., each dimension of the positional encoding corresponds to a sinusoid, with wavelengths forming a geometric progression from 2π to 10000·2π. The authors chose the fixed sinusoidal version over learned positional embeddings (which produced nearly identical results) because it may allow the model to extrapolate to sequence lengths longer than those encountered during training.

## Sources (exact kb/doc_path of what you read)

- kb: 计算机与人工智能 — doc_path: `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 1 of 2).md` — read in full (head window 3000 chars + 8 offset windows to line 218). Evidence: Abstract; §3 Model Architecture; §3.1 Encoder and Decoder Stacks; §3.2.1 Scaled Dot-Product Attention; §3.2.2 Multi-Head Attention; §3.3 Position-wise Feed-Forward Networks; §3.4 Embeddings and Softmax; §3.5 Positional Encoding (sinusoid formulas).
- kb: 计算机与人工智能 — doc_path: `计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md (part 2 of 2).md` — head window only (§6.2 Model Variations; confirms base config N=6, d_model=512, d_ff=2048, h=8).
- kb: 计算机与人工智能 — doc_path: `计算机与人工智能/nlp__1810.04805__bert-pre-training-of-deep-bidirectional-transfor.md (part 2 of 3).md` — head window only; read at the gate, ruled out as irrelevant to this question.

## Confidence

High (9/10). Every claim above maps to verbatim text read through kb_doc_read from the paper itself (gate score 8/8). The sinusoidal positional-encoding claim is directly evidenced by the §3.5 formulas and surrounding prose. Minor residual uncertainty: the retrieved markdown is an OCR/parse of the PDF, so a few formula fragments were garbled (e.g., the softmax formula truncated mid-render), but all load-bearing statements (N=6 stacks, sub-layer composition, masking, FFN dims, sinusoid formulas, wavelengths 2π to 10000·2π, extrapolation rationale) were read intact.

## Blind Spots

- Corpus parts are split into 2 parts; part 1 ends before §4–§6 fully, and part 2's head window only covered §6.2, so training details (§5, optimizer warmup steps, BLEU tables) were not read in full — they are outside the question scope but unread.
- Figure 1 (Transformer architecture diagram) is an image reference in the markdown; the diagram itself was not visible — component descriptions come from §3/§3.1 prose only.
- The exact rendering of the softmax attention formula was truncated mid-line in the parse; the form softmax(QK^T/sqrt(d_k))V is reconstructed from the surrounding prose ("dot products of the query with all keys, divide each by sqrt(d_k), and apply a softmax"), which was read verbatim.
