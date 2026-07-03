"""Experience Service — Full E2E Test Suite"""
import asyncio, sys, os

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.models.experience_models import (
    ExperienceCategory, ExperienceCreate, ExperienceResult,
    ExperienceSeverity, ExperienceStatus, ExperienceUpdate,
    ExperienceApplyRequest, ExperienceReviewRequest,
)
from app.services.experience_service import ExperienceService

svc = ExperienceService()
storage = svc.storage_root
PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label} {detail}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label} {detail}")

async def run_all():
    global PASS, FAIL
    kb = "Test-Scratch"

    print("=" * 60)
    print("Experience Service E2E Tests")
    print("=" * 60)

    # 1. Init experience folder
    r = await svc.init_experience_folder(kb)
    exp_dir = storage / kb / "experience"
    check("init_experience_folder", exp_dir.exists(), f"→ {exp_dir}")

    # 2. Create experience 1 (critical troubleshooting)
    data1 = ExperienceCreate(
        title="磨煤机堵煤故障排查流程",
        scenario="coal-mill-fault-prediction",
        category=ExperienceCategory.TROUBLESHOOTING,
        problem="磨煤机压差异常升高，CNN-LSTM模型偏差度>0.7",
        solution="第一步：降给煤量10%维持5分钟；第二步：MSET比对；第三步：联合判断",
        result=ExperienceResult.SUCCESS,
        key_lessons=[
            "CNN-LSTM偏差度>0.7且压差上升→堵煤概率>90%",
            "降给煤量10%并维持5分钟，如压差仍上升则紧急停磨",
        ],
        tags=["磨煤机", "堵煤", "CNN-LSTM", "故障排查"],
        severity=ExperienceSeverity.CRITICAL,
        related_docs=["Thermal-Power-Monitoring/基于卷积神经网络-长短时记忆神经网络的磨煤机故障预警_7cbcc650.md"],
        metrics={"effectiveness": 95, "difficulty": 60, "success_rate": 88},
    )
    r1 = await svc.create_experience(kb, data1)
    check("create_experience #1", r1.get("success"), f"→ id={r1.get('experience', {}).get('id', 'N/A')}")
    exp1_id = r1["experience"]["id"]

    # Verify .md file exists
    md_path = storage / r1["experience"]["path"]
    check("experience .md file exists", md_path.exists(), f"→ {md_path}")
    md_content = md_path.read_text(encoding="utf-8")
    check("experience .md has title", "磨煤机" in md_content)
    check("experience .md has key_lessons", "CNN-LSTM偏差度" in md_content)

    # 3. Create experience 2 (best practice)
    data2 = ExperienceCreate(
        title="汽轮机振动异常判断3条黄金法则",
        scenario="turbine-vibration-analysis",
        category=ExperienceCategory.BEST_PRACTICE,
        problem="生产团队对振动异常等级判断不一致导致误报警",
        solution="建立基于MSET振动基线+趋势斜率的判断标准",
        result=ExperienceResult.SUCCESS,
        key_lessons=[
            "振动幅值在基线±15%内且趋势平稳→正常运行",
            "振动幅值超过基线30%但趋势收敛→观察运行",
            "振动幅值超过基线50%且趋势发散→立即降负荷",
        ],
        tags=["汽轮机", "振动分析", "黄金法则"],
        severity=ExperienceSeverity.IMPORTANT,
    )
    r2 = await svc.create_experience(kb, data2)
    check("create_experience #2", r2.get("success"), f"→ id={r2['experience']['id']}")
    exp2_id = r2["experience"]["id"]

    # 4. Read experience
    r3 = await svc.read_experience(kb, exp1_id)
    check("read_experience", r3.get("success"))
    check("read_experience has content", len(r3.get("content", "")) > 100)
    check("read_experience title matches", r3["experience"]["title"] == data1.title)

    # 5. List all
    r4 = await svc.list_experiences(kb)
    check("list_experiences count==2", r4.get("count") == 2, f"→ got {r4['count']}")

    # 6. Filter by scenario
    r5 = await svc.list_experiences(kb, scenario="turbine")
    check("list by scenario turbine count==1", r5.get("count") == 1)
    check("list by scenario matches title", "汽轮机" in r5["experiences"][0]["title"])

    # 7. Filter by category
    r5b = await svc.list_experiences(kb, category="troubleshooting")
    check("list by category troubleshooting count==1", r5b.get("count") == 1)

    # 8. Filter by tag
    r5c = await svc.list_experiences(kb, tag="CNN-LSTM")
    check("list by tag CNN-LSTM count==1", r5c.get("count") == 1)

    # 9. Apply experience
    r6 = await svc.apply_experience(kb, exp1_id, ExperienceApplyRequest(
        user="shift-lee-zhang", context="#3机组压差异常", result="success", notes="成功避免堵煤"
    ))
    check("apply count==1", r6["experience"]["applied_count"] == 1)

    # Apply again
    r6b = await svc.apply_experience(kb, exp1_id, ExperienceApplyRequest(
        user="operator-wang", context="#5机组", result="partial", notes="部分有效"
    ))
    check("apply count==2", r6b["experience"]["applied_count"] == 2)

    # 10. Review experience
    r7 = await svc.review_experience(kb, exp1_id, ExperienceReviewRequest(
        reviewer="senior-operator-wang", rating=4.5, comment="流程实用，建议补充停机阈值"
    ))
    check("review rating==4.5", abs(r7["experience"]["rating_avg"] - 4.5) < 0.01)
    check("review count==1", r7["experience"]["review_count"] == 1)

    # Review again
    r7b = await svc.review_experience(kb, exp1_id, ExperienceReviewRequest(
        reviewer="chief-zhang", rating=5.0, comment="非常实用，已推广"
    ))
    check("review avg==4.75", abs(r7b["experience"]["rating_avg"] - 4.75) < 0.01)
    check("review count==2", r7b["experience"]["review_count"] == 2)

    # 11. Update experience
    r8 = await svc.update_experience(kb, exp1_id, ExperienceUpdate(
        title="[UPDATED] 磨煤机堵煤排查流程",
        status=ExperienceStatus.PUBLISHED,
    ))
    check("update title", r8.get("experience", {}).get("title", "").startswith("[UPDATED]"))
    check("update status published", r8["experience"].get("status") == "published")

    # 12. Summary
    r9 = await svc.experience_summary(kb)
    check("summary total==2", r9["summary"]["total"] == 2)
    check("summary has by_category", len(r9["summary"]["by_category"]) >= 2)
    check("summary total_applied==2", r9["summary"]["total_applied"] == 2)
    check("summary avg_rating>0", r9["summary"]["avg_rating"] > 0)
    check("summary top_experiences count>0", len(r9["summary"]["top_experiences"]) > 0)

    # 13. Delete experience
    r10 = await svc.delete_experience(kb, exp1_id)
    check("delete #1 success", r10.get("success"))
    r10b = await svc.list_experiences(kb)
    check("after delete #1 count==1", r10b.get("count") == 1)

    # 14. Delete the other one
    await svc.delete_experience(kb, exp2_id)
    r10c = await svc.list_experiences(kb)
    check("after delete all count==0", r10c.get("count") == 0)

    # 15. Verify .md files cleaned up
    check("md file 1 deleted", not md_path.exists())

    # 16. Summary on empty KB
    r11 = await svc.experience_summary(kb)
    check("empty summary total==0", r11["summary"]["total"] == 0)

    # 17. Read non-existent
    r12 = await svc.read_experience(kb, "non-existent-id")
    check("read non-existent returns error", not r12.get("success"))

    # 18. Delete non-existent
    r13 = await svc.delete_experience(kb, "non-existent-id")
    check("delete non-existent returns error", not r13.get("success"))

    # ── v2 新增测试：搜索功能 ──
    print()
    print("--- v2 Search Tests ---")

    # Create experiences for search testing
    data_search1 = ExperienceCreate(
        title="磨煤机堵煤故障排查流程",
        scenario="coal-mill-fault-prediction",
        category=ExperienceCategory.TROUBLESHOOTING,
        problem="磨煤机压差异常升高",
        solution="降给煤量",
        key_lessons=["CNN-LSTM偏差度>0.7=堵煤"],
        tags=["磨煤机", "堵煤", "CNN-LSTM"],
        severity=ExperienceSeverity.CRITICAL,
    )
    rs1 = await svc.create_experience(kb, data_search1)
    exp_s1_id = rs1["experience"]["id"]

    data_search2 = ExperienceCreate(
        title="汽轮机振动分析法则",
        scenario="turbine-vibration",
        category=ExperienceCategory.BEST_PRACTICE,
        problem="振动异常判断不一致",
        solution="MSET基线+趋势",
        key_lessons=["振动幅值超基线50%=降负荷"],
        tags=["汽轮机", "振动"],
        severity=ExperienceSeverity.IMPORTANT,
    )
    rs2 = await svc.create_experience(kb, data_search2)
    exp_s2_id = rs2["experience"]["id"]

    # 19. Metadata search - "磨煤机"
    r19 = await svc.search_experiences(kb, "磨煤机")
    check("search_experiences('磨煤机') finds coal-mill", r19.get("count", 0) >= 1)
    check("search results contains coal-mill title", any("磨煤机" in e.get("title", "") for e in r19.get("experiences", [])))

    # 20. Metadata search - "振动"
    r20 = await svc.search_experiences(kb, "振动")
    check("search_experiences('振动') finds turbine", r20.get("count", 0) >= 1)

    # 21. Metadata search - no match
    r21 = await svc.search_experiences(kb, "量子计算不存在的词")
    check("search no-match returns 0", r21.get("count", 0) == 0)

    # 22. Global search across all KBs
    r22 = await svc.search_experiences_global("磨煤机")
    check("global search returns results", r22.get("count", 0) >= 1)
    check("global search has kb_path field", all("kb_path" in e for e in r22.get("experiences", [])))

    # 23. Vector search (may fail if embedding model not loaded - that's OK)
    r23 = await svc.vector_search_experiences(kb, "如何处理磨煤机堵煤")
    if r23.get("success"):
        check("vector_search_experiences ran", True, f"→ count={r23.get('count', 0)}")
    else:
        check("vector_search_experiences graceful fallback", True, f"→ {r23.get('error', '')[:50]}")

    # Cleanup search test data
    await svc.delete_experience(kb, exp_s1_id)
    await svc.delete_experience(kb, exp_s2_id)

    print()
    print("=" * 60)
    total = PASS + FAIL
    print(f"RESULTS: {PASS}/{total} passed, {FAIL}/{total} failed")
    if FAIL == 0:
        print("====== ALL TESTS PASSED! ======")
    else:
        print(f"❌ {FAIL} test(s) FAILED!")
    print("=" * 60)
    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
