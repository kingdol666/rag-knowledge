"""Archival — Comprehensive KB Operations Test Script.
Runs all operations in Module Mode, outputs structured JSON at the end.
"""
import asyncio, json, sys, os

# Ensure we can import from kb-mcp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kb_client.client import KbClient
from config import WEB_URL, BACKEND_URL

# Override for dev mode
WEB_URL = "http://localhost:6789"
BACKEND_URL = "http://localhost:8766"

results = []
notes = []

def rec(operation: str, data):
    """Append a result entry."""
    data_str = json.dumps(data, ensure_ascii=False, default=str)
    if len(data_str) > 500:
        data_str = data_str[:500] + "..."
    results.append({
        "operation": operation,
        "pass": isinstance(data, dict) and not data.get("error") and data.get("success") is not False,
        "output": data_str
    })

async def main():
    c = KbClient(web_url=WEB_URL, backend_url=BACKEND_URL)

    # ==== 1. Health & Status ====
    print("=== 1. Health & Status ===")

    h = await c.health_check()
    rec("1.1 - health_check", h)
    print(f"  health_check: {json.dumps(h, indent=2, default=str)[:300]}")

    bs = await c.backend_status()
    rec("1.2 - backend_status", bs)
    print(f"  backend_status: {json.dumps(bs, indent=2, default=str)[:300]}")

    # ==== 2. KB Management (CRUD) ====
    print("\n=== 2. KB Management (CRUD) ===")

    kblist1 = await c.kb_list()
    rec("2.1 - kb_list (before)", kblist1)
    print(f"  kb_list (initial): {len(kblist1) if isinstance(kblist1, list) else kblist1} KBs")

    created = await c.kb_create(name="MCP-Test-KB", description="Created via MCP agent skill test")
    rec("2.2 - kb_create", created)
    print(f"  kb_create: {json.dumps(created, indent=2, default=str)[:300]}")

    # Get the kb_id from created result
    created_kb_id = None
    if isinstance(created, dict):
        created_kb_id = created.get("id") or created.get("kbId") or created.get("name")
    if not created_kb_id:
        created_kb_id = "MCP-Test-KB"

    updated = await c.kb_update(kb_id=created_kb_id, description="Updated via MCP")
    rec("2.3 - kb_update", updated)
    print(f"  kb_update: {json.dumps(updated, indent=2, default=str)[:300]}")

    kblist2 = await c.kb_list()
    rec("2.4 - kb_list (after create)", kblist2)
    print(f"  kb_list (after): {len(kblist2) if isinstance(kblist2, list) else kblist2} KBs")

    # ==== 3. Document CRUD ====
    print("\n=== 3. Document CRUD ===")

    d1 = await c.kb_doc_create(kb_id=created_kb_id, name="mcp-doc1.md",
        content="# MCP Test Doc\n\nThis document was created by the MCP agent.\n\n## Topics\n- vector search\n- knowledge management\n- MCP tools",
        description="MCP test document 1")
    rec("3.1 - kb_doc_create (doc1)", d1)
    print(f"  doc1 create: {json.dumps(d1, default=str)[:200]}")

    d2 = await c.kb_doc_create(kb_id=created_kb_id, name="mcp-doc2.md",
        content="# Machine Learning\n\nDeep learning and neural networks for predictive maintenance.\n\n## Methods\n- TensorFlow\n- PyTorch\n- Scikit-learn",
        description="ML test document")
    rec("3.2 - kb_doc_create (doc2)", d2)
    print(f"  doc2 create: {json.dumps(d2, default=str)[:200]}")

    d3 = await c.kb_doc_create(kb_id=created_kb_id, name="mcp-doc3.md",
        content="# Cooking Recipes\n\nHow to bake a chocolate cake.\n\n## Ingredients\n- flour\n- eggs\n- chocolate\n- sugar",
        description="Cooking test document")
    rec("3.3 - kb_doc_create (doc3)", d3)
    print(f"  doc3 create: {json.dumps(d3, default=str)[:200]}")

    docs = await c.kb_get_documents(kb_id=created_kb_id)
    rec("3.4 - kb_get_documents", docs)
    print(f"  kb_get_documents: {json.dumps(docs, default=str)[:300]}")

    read1 = await c.kb_doc_read(kb_id=created_kb_id, doc_path="mcp-doc1.md", max_chars=200)
    rec("3.5 - kb_doc_read", read1)
    print(f"  doc_read: {json.dumps(read1, default=str)[:200]}")

    # ==== 4. Tags ====
    print("\n=== 4. Tags ===")

    t1 = await c.kb_tag_create(tag="mcp-test")
    rec("4.1 - kb_tag_create (mcp-test)", t1)
    print(f"  tag create mcp-test: {json.dumps(t1, default=str)[:200]}")

    t2 = await c.kb_tag_create(tag="agent-test")
    rec("4.2 - kb_tag_create (agent-test)", t2)
    print(f"  tag create agent-test: {json.dumps(t2, default=str)[:200]}")

    ut = await c.kb_doc_update_tags(kb_id=created_kb_id, doc_path="mcp-doc1.md", tags=["mcp-test", "agent-test"])
    rec("4.3 - kb_doc_update_tags", ut)
    print(f"  update tags: {json.dumps(ut, default=str)[:200]}")

    bytag = await c.kb_doc_get_by_tag(tag="mcp-test")
    rec("4.4 - kb_doc_get_by_tag", bytag)
    print(f"  get by tag: {json.dumps(bytag, default=str)[:300]}")

    # ==== 5. Vector Indexing ====
    print("\n=== 5. Vector Indexing ===")

    stats1 = await c.search_stats(kb_id=created_kb_id)
    rec("5.1 - kb_search_stats (before index)", stats1)
    print(f"  stats before: {json.dumps(stats1, default=str)[:200]}")

    idx1 = await c.index_document(kb_id=created_kb_id, doc_path="MCP-Test-KB/mcp-doc1.md", doc_name="mcp-doc1.md")
    rec("5.2 - kb_index_document (doc1)", idx1)
    print(f"  index doc1: {json.dumps(idx1, default=str)[:200]}")

    idx2 = await c.index_document(kb_id=created_kb_id, doc_path="MCP-Test-KB/mcp-doc2.md", doc_name="mcp-doc2.md")
    rec("5.3 - kb_index_document (doc2)", idx2)
    print(f"  index doc2: {json.dumps(idx2, default=str)[:200]}")

    idx3 = await c.index_document(kb_id=created_kb_id, doc_path="MCP-Test-KB/mcp-doc3.md", doc_name="mcp-doc3.md")
    rec("5.4 - kb_index_document (doc3)", idx3)
    print(f"  index doc3: {json.dumps(idx3, default=str)[:200]}")

    stats2 = await c.search_stats(kb_id=created_kb_id)
    rec("5.5 - kb_search_stats (after index)", stats2)
    print(f"  stats after index: {json.dumps(stats2, default=str)[:200]}")

    # ==== 6. Vector Search ====
    print("\n=== 6. Vector Search ===")

    vs1 = await c.vector_search(query="machine learning deep learning neural networks", kb_id=created_kb_id, top_k=3)
    rec("6.1 - kb_search_vector", vs1)
    print(f"  vector search: {json.dumps(vs1, default=str)[:300]}")

    vs2 = await c.batch_vector_search(query_doc_paths=["MCP-Test-KB/mcp-doc1.md"], kb_id=created_kb_id, top_k=2, score_threshold=0.2)
    rec("6.2 - kb_search_batch_vector", vs2)
    print(f"  batch vector: {json.dumps(vs2, default=str)[:300]}")

    vs3 = await c.two_stage_search(query="machine learning prediction", kb_id=created_kb_id, stage1_top_k=5, stage2_top_k=3)
    rec("6.3 - kb_search_two_stage", vs3)
    print(f"  two-stage: {json.dumps(vs3, default=str)[:300]}")

    stats3 = await c.search_stats(kb_id=created_kb_id)
    rec("6.4 - kb_search_stats (after search)", stats3)
    print(f"  stats after search: {json.dumps(stats3, default=str)[:200]}")

    stats4 = await c.search_stats(kb_id="")
    rec("6.5 - kb_search_stats (empty kb_id)", stats4)
    print(f"  stats empty kb: {json.dumps(stats4, default=str)[:200]}")

    # ==== 7. Batch Index ====
    print("\n=== 7. Batch Index ===")

    bi = await c.batch_index_documents(kb_id=created_kb_id, doc_paths=["MCP-Test-KB/mcp-doc1.md", "MCP-Test-KB/mcp-doc2.md"], force=True)
    rec("7.1 - kb_batch_index", bi)
    print(f"  batch index: {json.dumps(bi, default=str)[:300]}")

    await c.aclose()

    # ==== Final Summary ====
    print("\n\n" + "=" * 60)
    print("ALL OPERATIONS COMPLETE")
    print("=" * 60)

    output = {
        "results": results,
        "notes": notes
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
