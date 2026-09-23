# Track C — Dense RAG (Corpus-Chunks800)

## Metadata
- question: In the paper 'Attention Is All You Need', what are the main components of the Transformer architecture, and what kind of positional encoding does the paper use?
- retrieval seconds: 0.91
- chunks retrieved: 10
- evidence characters: 4000 (cap 4000)
- chunk doc_paths+scores:
  - SRC-0 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k00.md | score=0.6395
  - SRC-1 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k19.md | score=0.6359
  - SRC-2 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k20.md | score=0.6354
  - SRC-3 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k15.md | score=0.6046
  - SRC-4 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k16.md | score=0.6046
  - SRC-5 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k02.md | score=0.6018
  - SRC-6 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k01.md | score=0.6018
  - SRC-7 Corpus-Chunks800/nlp__1810.04805__bert-pre-training-of-deep-bidirectional-transfor__k05.md | score=0.6008
  - SRC-8 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k06.md | score=0.5968
  - SRC-9 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k07.md | score=0.5957

## Evidence Pack (first 600 chars, verbatim excerpt)

[SRC-0 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k00.md | score=0.6395] ## Abstract


The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior i

## Answer

Per the evidence, the Transformer is a sequence transduction architecture consisting of an encoder and a decoder, connected through an attention mechanism, and it is based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. It replaces the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention, and uses multi-head attention in several ways, including encoder-decoder attention layers in which the queries come from the previous decoder layer while the memory keys and values come from the encoder output. As for positional encoding, the evidence is insufficient: the retrieved evidence pack contains no passage describing what kind of positional encoding the paper uses.

## Evidence Used (source ids)
- SRC-0 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k00.md (score=0.6395) — abstract: encoder/decoder, attention-only, no recurrence/convolution
- SRC-1 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k19.md (score=0.6359) — conclusion: multi-headed self-attention replacing recurrent layers
- SRC-2 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k20.md (score=0.6354) — conclusion (extended)
- SRC-5 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k02.md (score=0.6018) — intro: eschews recurrence, relies entirely on attention
- SRC-8 Corpus-Chunks800/artificial-intelligence__1706.03762__attention-is-all-you-need__k06.md (score=0.5968) — section 3.2.3: multi-head attention applications, encoder-decoder attention
