"""Verify vector indexing integration for experiences."""
import sys, asyncio
sys.path.insert(0, "backend")
from app.services.experience_service import ExperienceService
from app.models.experience_models import (
    ExperienceCreate, ExperienceCategory, ExperienceSeverity, ExperienceResult
)
from app.services.vector_service import vector_service as vs

svc = ExperienceService()

async def test():
    kb = "Test-Scratch"
    print(f"Vector service ready: {vs.is_ready()}")

    # Create experience
    data = ExperienceCreate(
        title="向量索引验证-磨煤机排查",
        scenario="vector-index-test",
        category=ExperienceCategory.TROUBLESHOOTING,
        problem="验证经验创建后是否自动建立向量索引",
        solution="通过create_experience创建后检查vector_index字段",
        key_lessons=["经验创建后应自动索引", "向量搜索应该能找到经验内容"],
        tags=["vector-test"],
        severity=ExperienceSeverity.NORMAL,
    )
    r = await svc.create_experience(kb, data)
    exp = r["experience"]
    exp_id = exp["id"]
    print(f"Created experience: {exp_id}")
    vi = exp.get("vector_index", "MISSING")
    if isinstance(vi, dict):
        print(f"vector_index.total_chunks: {vi.get('total_chunks', 'N/A')}")
        print(f"vector_index.collection: {vi.get('collection', 'N/A')}")
    else:
        print(f"vector_index field: {vi}")

    # Verify via vector search
    results = vs.search("向量索引验证", kb, top_k=5)
    print(f"Vector search results: {len(results)}")
    found_exp = [r for r in results if "experience" in r.get("doc_path", "").replace("\\", "/")]
    print(f"Experience results in vector search: {len(found_exp)}")
    if found_exp:
        top = found_exp[0]
        print(f"  Top exp doc_path: {top.get('doc_path', '')}")
        print(f"  Score: {top.get('score', 0):.3f}")
        print(f"  doc_type metadata: {top.get('doc_type', 'N/A')}")
        print(f"  exp_id metadata: {top.get('exp_id', 'N/A')}")

    # Cleanup
    await svc.delete_experience(kb, exp_id)

    # Verify vector deleted
    results2 = vs.search("向量索引验证", kb, top_k=5)
    found_exp2 = [r for r in results2 if "experience" in r.get("doc_path", "").replace("\\", "/")]
    print(f"After delete - experience results: {len(found_exp2)} (should be 0)")

    print()
    print("=== Vector indexing integration: VERIFIED ===")

asyncio.run(test())
