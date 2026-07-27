try:
    from ragatouille import RAGPretrainedModel
    print("RAGatouille (ColBERT): OK")
except Exception as e:
    print(f"RAGatouille: FAILED - {e}")

try:
    from splade.models.transformer_rep import Splade
    print("SPLADE: OK")
except Exception as e:
    print(f"SPLADE: not installed ({e})")

print("\nAvailable baselines:")
print("  [REAL-CODE] BM25 (rank_bm25)")
print("  [REAL-CODE] Dense (FAISS+BGE-M3)")
print("  [REAL-CODE] Hybrid (BM25+FAISS)")
print("  [REAL-CODE] Cross-Encoder Rerank (ms-marco-MiniLM)")
try:
    from ragatouille import RAGPretrainedModel
    print("  [REAL-CODE] ColBERT (RAGatouille)")
except:
    print("  [MISSING] ColBERT (RAGatouille) - install: uv pip install ragatouille")
print("  [REAL-ALGO] CRAG (Yan et al. 2024)")
print("  [REAL-ALGO] Self-RAG (Asai et al. 2023)")
print("  [PROJECT]  QDCVR-Flat (your system)")
print("  [PROJECT]  QDCVR-Domain (your system)")
