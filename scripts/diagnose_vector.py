"""Diagnose vector indexing, keyword index, graph errors without quoting issues."""
import sys, json
sys.path.insert(0, 'backend')
sys.path.insert(0, '.')

# Check storage
from app.services.storage_reader_service import storage_reader
print(f"Storage root: {storage_reader.root}")
print(f"Tree FS exists: {storage_reader.tree_fs_path.exists()}")

kbs = storage_reader.list_knowledge_bases()
print(f"KBs: {len(kbs)}")
for kb in kbs:
    docs = storage_reader.list_documents(kb['path'])
    print(f"  KB {kb['kb_id']}: {len(docs)} docs")
    for d in docs[:2]:
        dp = d.get('path','')
        content = storage_reader.read_document_content(dp, 2000)
        print(f"    - {dp} content_len={len(content)}")
        vi = d.get('vector_index')
        print(f"      vector_index={json.dumps(vi)[:100] if vi else 'NONE'}")

# Check vector service
from app.services.vector_service import vector_service
print(f"\nVector service ready: {vector_service.is_ready()}")
stats = vector_service.get_stats()
print(f"Stats: {json.dumps(stats, ensure_ascii=False)[:200]}")

# Try search
results = vector_service.search("RAG技术", top_k=5)
print(f"Vector search 'RAG': {len(results)} results")

# Build and test BM25
from app.services.keyword_index_service import keyword_index_service
all_docs = []
for kb in kbs:
    docs = storage_reader.list_documents(kb['path'])
    for doc in docs:
        dp = doc.get('path','')
        if not dp: continue
        content = storage_reader.read_document_content(dp, 2000)
        all_docs.append({'path': dp, 'name': doc.get('name',''), 'description': doc.get('description',''), 'content': content})
print(f"\nDocs for BM25: {len(all_docs)}")
keyword_index_service.build(all_docs)
kw = keyword_index_service.search("人工智能", 10)
print(f"Keyword search 'AI': {len(kw)} results")
for r in kw[:3]:
    print(f"  score={r['score']:.3f} doc={r['doc_path']}")

# Test two-stage
from app.services.two_stage_search_service import two_stage_search_service
try:
    ts = two_stage_search_service.search("检索增强生成")
    print(f"\nTwo-stage results: {ts.get('total_results', 0)}")
    print(f"  Stage1: {ts['stage1']['candidate_count']} candidates")
    print(f"  Stage2: {len(ts['stage2']['results'])} results")
except Exception as e:
    print(f"Two-stage error: {e}")
    import traceback
    traceback.print_exc()

# Test graph
from app.config import config
print(f"\nGraph enabled: {config.graph_enabled}")
if config.graph_enabled:
    try:
        from app.services.graph_service import graph_service
        gs = graph_service.get_stats()
        print(f"Graph stats: {gs}")
    except Exception as e:
        print(f"Graph error: {e}")
        import traceback
        traceback.print_exc()
