"""Check what storage_root the backend service actually resolves to."""
import sys
sys.path.insert(0, "backend")
from app.services.experience_service import ExperienceService

svc = ExperienceService()
root = svc.storage_root
print(f"storage_root: {root}")
print(f"tree-fs.json exists: {(root / '.tree-fs.json').exists()}")

tree = svc._read_tree_fs()
for f in tree.get("folders", []):
    if "0ed30110" in f.get("id", "") or "Test-Scratch" in f.get("name", "") or "Test-Scratch" in f.get("path", ""):
        print(f"  id={f.get('id')}")
        print(f"  name={f.get('name')}")
        print(f"  path={f.get('path')}")

# Test _resolve_kb_path
result = svc._resolve_kb_path("0ed30110-cdfe-4d69-8728-7b2dead33d99")
print(f"\n_resolve_kb_path(UUID) = {result}")

result2 = svc._resolve_kb_path("Test-Scratch")
print(f"_resolve_kb_path('Test-Scratch') = {result2}")

# Check if there's a UUID-named dir on disk
import pathlib
uuid_dir = root / "0ed30110-cdfe-4d69-8728-7b2dead33d99"
print(f"\nUUID dir exists on disk: {uuid_dir.exists()}")
if uuid_dir.exists():
    print(f"  contents: {[p.name for p in uuid_dir.iterdir()]}")
