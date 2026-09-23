"""Agent-executed three-mode retrieval experiment (reproduction project).

Tracks (all agent-executed, same external corpus — the 50 exported papers):
  A  platform   — the current system, accessed ONLY through its external HTTP APIs
                  (vector search / cross-KB keyword search / offset-addressed doc reads)
  B  bare       — a bare agent with plain file tools (list / grep / read) over the
                  exported markdown corpus; full-text reading + file search only
  C  rag        — a dense-RAG agent that executes real vector retrieval itself over the
                  Corpus-Chunks800 index and answers only from the retrieved chunks

Launch:
  cd benchmark-suite
  python -m experiments.runner --question "Which three ontologies subdivide the Gene Ontology?"
  python -m experiments.runner --questions data/papers/qa_questions.json --limit 2 --tracks a,c
"""
