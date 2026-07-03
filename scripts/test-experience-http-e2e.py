"""
Experience 机制 — 完整 HTTP E2E 测试
直接通过后端 API 测试所有功能（不依赖 MCP）
验证经验机制在真实 HTTP 环境下的完整闭环
"""
import httpx
import json
import sys

BACKEND = "http://localhost:8766"
PASS = 0
FAIL = 0
RESULTS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(("PASS", name, detail))
        print(f"  [PASS] {name} {detail}")
    else:
        FAIL += 1
        RESULTS.append(("FAIL", name, detail))
        print(f"  [FAIL] {name} {detail}")

def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

c = httpx.Client(timeout=30)

# ════════════════════════════════════════════════════════════
sep("Step 0: Backend health check")
# ════════════════════════════════════════════════════════════
r = c.get(f"{BACKEND}/api/v1/health")
test("backend health 200", r.status_code == 200, f"-> {r.json()}")

# Verify experience routes registered
r = c.get(f"{BACKEND}/openapi.json")
spec = r.json()
exp_paths = [p for p in spec.get("paths", {}) if "/experience" in p]
test("experience routes registered", len(exp_paths) >= 9, f"-> {len(exp_paths)} routes: {exp_paths[:3]}...")

# ════════════════════════════════════════════════════════════
sep("Step 1: Find Test-Scratch KB")
# ════════════════════════════════════════════════════════════
# 通过 web 代理获取 KB 列表
WEB = "http://localhost:6789"
try:
    r = c.get(f"{WEB}/api/kb/catalog")
    kbs = r.json()
    test_kb = next((kb for kb in kbs.get("knowledgeBases", []) if kb["name"] == "Test-Scratch"), None)
    if test_kb:
        KB_ID = test_kb["kbId"]
        test("found Test-Scratch KB", True, f"-> {KB_ID}")
    else:
        test("found Test-Scratch KB", False, "-> not found")
        sys.exit(1)
except Exception as e:
    test("KB catalog reachable", False, f"-> {e}")
    sys.exit(1)

# ════════════════════════════════════════════════════════════
sep("Step 2: Initialize experience folder")
# ════════════════════════════════════════════════════════════
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}/init")
result = r.json()
test("init experience folder", result.get("success"), f"-> {result.get('kb_path', '')}")

# ════════════════════════════════════════════════════════════
sep("Step 3: Create experience #1 (Coal Mill Troubleshooting)")
# ════════════════════════════════════════════════════════════
exp1_body = {
    "title": "HTTP测试-磨煤机堵煤故障排查流程",
    "scenario": "coal-mill-fault-prediction",
    "category": "troubleshooting",
    "problem": "磨煤机压差异常升高，CNN-LSTM模型偏差度>0.7",
    "solution": "第一步：降给煤量10%维持5分钟；第二步：MSET比对；第三步：联合判断",
    "result": "success",
    "key_lessons": [
        "CNN-LSTM偏差度>0.7且压差上升=堵煤概率>90%",
        "降给煤量10%并维持5分钟，如压差仍上升则紧急停磨",
        "三重确认（CNN-LSTM+MSET+压差趋势）准确率>95%",
    ],
    "tags": ["磨煤机", "堵煤", "CNN-LSTM", "故障排查"],
    "severity": "critical",
    "related_docs": ["Thermal-Power-Monitoring/基于卷积神经网络-长短时记忆神经网络的磨煤机故障预警_7cbcc650.md"],
    "metrics": {"effectiveness": 95, "difficulty": 60, "success_rate": 88},
}
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}", json=exp1_body)
result = r.json()
test("create experience #1", result.get("success"), f"-> id={result.get('experience', {}).get('id', 'N/A')}")
exp1 = result.get("experience", {})
EXP1_ID = exp1.get("id", "")
test("experience #1 has vector_index", "vector_index" in exp1 and exp1["vector_index"],
     f"-> chunks={exp1.get('vector_index', {}).get('total_chunks', 'N/A')}" if isinstance(exp1.get('vector_index'), dict) else "")
test("experience #1 severity critical", exp1.get("severity") == "critical")
test("experience #1 status published", exp1.get("status") == "published")

# ════════════════════════════════════════════════════════════
sep("Step 4: Create experience #2 (Turbine Vibration Best Practice)")
# ════════════════════════════════════════════════════════════
exp2_body = {
    "title": "HTTP测试-汽轮机振动分析黄金法则",
    "scenario": "turbine-vibration-analysis",
    "category": "best_practice",
    "problem": "振动异常判断不一致导致误报警",
    "solution": "建立基于MSET振动基线+趋势斜率的判断标准",
    "result": "success",
    "key_lessons": [
        "振动幅值在基线±15%内=正常运行",
        "振动幅值超过基线50%且趋势发散=立即降负荷",
    ],
    "tags": ["汽轮机", "振动分析", "黄金法则"],
    "severity": "important",
}
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}", json=exp2_body)
EXP2_ID = r.json().get("experience", {}).get("id", "")
test("create experience #2", EXP2_ID, f"-> id={EXP2_ID}")

# ════════════════════════════════════════════════════════════
sep("Step 5: Read experience (metadata + content)")
# ════════════════════════════════════════════════════════════
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP1_ID}")
result = r.json()
test("read experience success", result.get("success"))
test("read has experience metadata", "experience" in result)
test("read has markdown content", len(result.get("content", "")) > 100,
     f"-> {len(result.get('content', ''))} chars")
test("content contains key lessons", "CNN-LSTM偏差度" in result.get("content", ""))

# ════════════════════════════════════════════════════════════
sep("Step 6: List experiences (with filters)")
# ════════════════════════════════════════════════════════════
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}")
result = r.json()
test("list all experiences", result.get("count") == 2, f"-> count={result.get('count')}")

# Filter by scenario
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}?scenario=turbine")
result = r.json()
test("filter by scenario turbine", result.get("count") == 1, f"-> {result.get('count')}")

# Filter by category
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}?category=troubleshooting")
result = r.json()
test("filter by category troubleshooting", result.get("count") == 1)

# Filter by tag
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}?tag=CNN-LSTM")
result = r.json()
test("filter by tag CNN-LSTM", result.get("count") == 1)

# ════════════════════════════════════════════════════════════
sep("Step 7: Metadata search")
# ════════════════════════════════════════════════════════════
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/search", json={"query": "磨煤机", "top_k": 10})
result = r.json()
test("search '磨煤机' finds coal-mill", result.get("count", 0) >= 1, f"-> {result.get('count')}")

r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/search", json={"query": "振动"})
result = r.json()
test("search '振动' finds turbine", result.get("count", 0) >= 1)

r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/search", json={"query": "量子不存在的词"})
result = r.json()
test("search no-match returns 0", result.get("count", 0) == 0)

# ════════════════════════════════════════════════════════════
sep("Step 8: Vector semantic search (KEY v2 feature)")
# ════════════════════════════════════════════════════════════
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/vector-search",
           json={"query": "如何处理磨煤机堵煤问题", "top_k": 3})
result = r.json()
test("vector search ran", result.get("success"),
     f"-> {result.get('error', '')[:60]}" if not result.get("success") else f"-> {result.get('count', 0)} results")
if result.get("success"):
    test("vector search returns experience chunks", result.get("count", 0) > 0)
    if result.get("results"):
        top = result["results"][0]
        test("vector search result has score", "score" in top, f"-> score={top.get('score', 0):.3f}")
        test("vector search result has doc_path", "doc_path" in top)

# ════════════════════════════════════════════════════════════
sep("Step 9: Global cross-KB search")
# ════════════════════════════════════════════════════════════
r = c.post(f"{BACKEND}/api/v1/experience/global-search", json={"query": "磨煤机", "top_k": 10})
result = r.json()
test("global search success", result.get("success"))
test("global search returns results", result.get("count", 0) >= 1, f"-> {result.get('count')}")
if result.get("experiences"):
    test("global search has kb_path", "kb_path" in result["experiences"][0])

# ════════════════════════════════════════════════════════════
sep("Step 10: Apply experience (mark as used)")
# ════════════════════════════════════════════════════════════
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP1_ID}/apply", json={
    "user": "shift-lee-zhang", "context": "#3机组压差异常", "result": "success", "notes": "成功避免堵煤"
})
result = r.json()
test("apply #1 increments count", result.get("experience", {}).get("applied_count") == 1)

r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP1_ID}/apply", json={
    "user": "operator-wang", "context": "#5机组", "result": "partial", "notes": "部分有效"
})
result = r.json()
test("apply #2 increments count", result.get("experience", {}).get("applied_count") == 2)

# ════════════════════════════════════════════════════════════
sep("Step 11: Review experience (rate)")
# ════════════════════════════════════════════════════════════
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP1_ID}/review", json={
    "reviewer": "chief-wang", "rating": 4.5, "comment": "流程实用"
})
result = r.json()
test("review #1 updates avg", abs(result.get("experience", {}).get("rating_avg", 0) - 4.5) < 0.01,
     f"-> {result.get('experience', {}).get('rating_avg')}")

r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP1_ID}/review", json={
    "reviewer": "senior-zhang", "rating": 5.0, "comment": "非常实用"
})
result = r.json()
test("review #2 recalculates avg", abs(result.get("experience", {}).get("rating_avg", 0) - 4.75) < 0.01,
     f"-> {result.get('experience', {}).get('rating_avg')}")
test("review count == 2", result.get("experience", {}).get("review_count") == 2)

# ════════════════════════════════════════════════════════════
sep("Step 12: Update experience")
# ════════════════════════════════════════════════════════════
r = c.put(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP1_ID}", json={
    "title": "[UPDATED] HTTP测试-磨煤机堵煤排查流程",
    "status": "published",
})
result = r.json()
test("update title", result.get("experience", {}).get("title", "").startswith("[UPDATED]"))

# ════════════════════════════════════════════════════════════
sep("Step 13: Summary statistics")
# ════════════════════════════════════════════════════════════
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}/summary")
result = r.json()
summary = result.get("summary", {})
test("summary total == 2", summary.get("total") == 2)
test("summary has by_category", len(summary.get("by_category", {})) >= 2, f"-> {summary.get('by_category')}")
test("summary total_applied == 2", summary.get("total_applied") == 2)
test("summary avg_rating > 0", summary.get("avg_rating", 0) > 0, f"-> {summary.get('avg_rating')}")
test("summary has top_experiences", len(summary.get("top_experiences", [])) > 0)

# ════════════════════════════════════════════════════════════
sep("Step 14: Cleanup - delete both experiences")
# ════════════════════════════════════════════════════════════
r = c.delete(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP1_ID}")
test("delete #1", r.json().get("success"))

r = c.delete(f"{BACKEND}/api/v1/experience/{KB_ID}/{EXP2_ID}")
test("delete #2", r.json().get("success"))

r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}")
test("all deleted", r.json().get("count") == 0, f"-> count={r.json().get('count')}")

# Verify vector cleanup
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/vector-search",
           json={"query": "磨煤机堵煤", "top_k": 3})
result = r.json()
if result.get("success"):
    test("vector search empty after delete", result.get("count", 0) == 0, f"-> {result.get('count')}")

# ════════════════════════════════════════════════════════════
sep("FINAL RESULTS")
# ════════════════════════════════════════════════════════════
total = PASS + FAIL
print(f"\n  Total: {PASS}/{total} passed, {FAIL} failed")
print(f"{'='*60}")
if FAIL == 0:
    print("  *** ALL HTTP E2E TESTS PASSED ***")
else:
    print(f"  !!! {FAIL} TEST(S) FAILED !!!")
    print("\n  Failed tests:")
    for status, name, detail in RESULTS:
        if status == "FAIL":
            print(f"    - {name} {detail}")
print(f"{'='*60}")

sys.exit(0 if FAIL == 0 else 1)
