"""Debug global-search and summary failures."""
import httpx, json, sys

BACKEND = "http://localhost:8766"
WEB = "http://localhost:6789"
KB_ID = "0ed30110-cdfe-4d69-8728-7b2dead33d99"  # Test-Scratch

c = httpx.Client(timeout=30)

# Create a test experience first
print("=== Creating test experience ===")
body = {
    "title": "调试-磨煤机排查",
    "scenario": "coal-mill",
    "category": "troubleshooting",
    "problem": "磨煤机压差高",
    "solution": "降给煤量",
    "key_lessons": ["偏差度>0.7=堵煤"],
    "tags": ["磨煤机"],
    "severity": "critical",
}
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}", json=body)
exp_id = r.json().get("experience", {}).get("id", "")
print(f"Created: {exp_id}")

# Debug 1: list all
print("\n=== LIST all experiences ===")
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}")
data = r.json()
print(f"count={data.get('count')}")
if data.get("experiences"):
    print(f"first exp id={data['experiences'][0].get('id')}")
    print(f"first exp path={data['experiences'][0].get('path')}")

# Debug 2: metadata search
print("\n=== METADATA search '磨煤机' ===")
r = c.post(f"{BACKEND}/api/v1/experience/{KB_ID}/search", json={"query": "磨煤机"})
data = r.json()
print(f"success={data.get('success')}, count={data.get('count')}")

# Debug 3: global search
print("\n=== GLOBAL search '磨煤机' ===")
r = c.post(f"{BACKEND}/api/v1/experience/global-search", json={"query": "磨煤机"})
data = r.json()
print(f"Full response: {json.dumps(data, ensure_ascii=False, indent=2)}")

# Debug 4: summary
print("\n=== SUMMARY ===")
r = c.get(f"{BACKEND}/api/v1/experience/{KB_ID}/summary")
data = r.json()
print(f"Full response: {json.dumps(data, ensure_ascii=False, indent=2)}")

# Debug 5: Check what search_experiences_global sees — examine tree-fs.json
print("\n=== Check .tree-fs.json KB entries ===")
import pathlib
storage = pathlib.Path("D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/storage/tree-file-system")
tree = json.loads((storage / ".tree-fs.json").read_text(encoding="utf-8"))
for folder in tree.get("folders", []):
    if folder.get("isKnowledgeBase"):
        print(f"  KB: path={folder.get('path')}, name={folder.get('name')}, id={folder.get('id')[:8]}...")
        exp_index = storage / folder.get("path", "") / "experience" / ".experience-index.yml"
        print(f"    has exp index: {exp_index.exists()}")
        if exp_index.exists():
            import yaml
            idx = yaml.safe_load(exp_index.read_text(encoding="utf-8"))
            print(f"    exp count in index: {len(idx.get('experiences', []))}")

# Cleanup
c.delete(f"{BACKEND}/api/v1/experience/{KB_ID}/{exp_id}")
print("\n=== Cleaned up ===")
