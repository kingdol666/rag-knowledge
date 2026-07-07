#!/usr/bin/env python3
"""
O13c/O13d — Fix YAML index pollution in AI-Materials-Informatics KB hierarchy.

Problem:
1. Parent KB YAML contains 7 child-document entries that belong to sub-KBs
2. Sub-KB YAML files have empty documents: [] despite 4+3 .md files on disk

Fix:
- Remove 7 polluted child-doc entries from parent YAML
- Recover missing entries into RL-Inverse-Design and Defect-Detection YAMLs
- Update total_document counts
"""
import yaml
import json
from pathlib import Path
import shutil

STORAGE = Path("D:/codes/ClaudeGPT/rag_project/rag-knowledge/storage/tree-file-system")
PARENT_DIR = STORAGE / "AI-Materials-Informatics"
RL_DIR = PARENT_DIR / "AI-Materials-RL-Inverse-Design"
DEFECT_DIR = PARENT_DIR / "AI-Materials-Defect-Detection"

def yaml_str_representer(dumper, data):
    """Preserve multi-line strings as |- style literal blocks."""
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, yaml_str_representer)

def backup_file(path):
    backup = path.with_suffix(".yml.bak")
    shutil.copy2(path, backup)
    print(f"  Backup: {backup}")

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  Written: {path}")

def doc_belongs_to_subkb(doc, subkb_dir):
    """Check if a document entry's path is under the given sub-KB directory."""
    doc_path = doc.get('path', '')
    subkb_name = subkb_dir.name
    return subkb_name in doc_path.replace('\\', '/')

# ── Step 1: Backup & Load ──
print("=" * 60)
print("O13c/O13d — YAML Index Fix for AI-Materials-Informatics")
print("=" * 60)

parent_yml = PARENT_DIR / ".knowledge-base.yml"
rl_yml = RL_DIR / ".knowledge-base.yml"
defect_yml = DEFECT_DIR / ".knowledge-base.yml"

for fp in [parent_yml, rl_yml, defect_yml]:
    if fp.exists():
        backup_file(fp)

parent_data = load_yaml(parent_yml)
rl_data = load_yaml(rl_yml)
defect_data = load_yaml(defect_yml)

print(f"\nParent KB YAML: {len(parent_data.get('documents', []))} entries")
print(f"RL-Inverse-Design YAML: {len(rl_data.get('documents', []))} entries")
print(f"Defect-Detection YAML: {len(defect_data.get('documents', []))} entries")

# ── Step 2: Categorize parent entries ──
root_docs = []
rl_docs = []
defect_docs = []
folder_refs = []
other = []

for doc in parent_data.get('documents', []):
    doc_path = doc.get('path', '')
    doc_name = doc.get('name', '')
    file_type = doc.get('file_type', '')

    # Folder references (sub-KB entries)
    if file_type == 'knowledge-base':
        folder_refs.append(doc)
        continue

    # Check which sub-KB the document belongs to by path
    if 'AI-Materials-RL-Inverse-Design' in doc_path.replace('\\', '/'):
        rl_docs.append(doc)
    elif 'AI-Materials-Defect-Detection' in doc_path.replace('\\', '/'):
        defect_docs.append(doc)
    else:
        root_docs.append(doc)

print(f"\nCategorization:")
print(f"  Root documents: {len(root_docs)}")
print(f"  Sub-KB folder refs: {len(folder_refs)}")
print(f"  RL-Inverse-Design children (POLLUTION): {len(rl_docs)}")
print(f"  Defect-Detection children (POLLUTION): {len(defect_docs)}")

# ── Step 3: Verify disk files match ──
rl_disk_files = sorted([p.name for p in RL_DIR.glob("*.md")])
defect_disk_files = sorted([p.name for p in DEFECT_DIR.glob("*.md")])
print(f"\nRL sub-KB disk files: {rl_disk_files}")
print(f"Defect sub-KB disk files: {defect_disk_files}")

# ── Step 4: Write cleaned parent YAML ──
parent_data['documents'] = root_docs + folder_refs
parent_data['total_documents'] = len(root_docs)  # folder refs don't count as documents
save_yaml(parent_yml, parent_data)
print(f"\nParent KB YAML cleaned: {len(parent_data['documents'])} entries ({len(root_docs)} doc + {len(folder_refs)} folder refs)")
print(f"  Removed {len(rl_docs)} RL-Inverse-Design entries")
print(f"  Removed {len(defect_docs)} Defect-Detection entries")

# ── Step 5: Write recovered RL-Inverse-Design YAML ──
rl_data['documents'] = rl_docs
rl_data['total_documents'] = len(rl_docs)
rl_data['knowledge_base']['total_documents'] = len(rl_docs)
save_yaml(rl_yml, rl_data)
print(f"\nRL-Inverse-Design YAML recovered: {len(rl_data['documents'])} entries")

# ── Step 6: Write recovered Defect-Detection YAML ──
defect_data['documents'] = defect_docs
defect_data['total_documents'] = len(defect_docs)
defect_data['knowledge_base']['total_documents'] = len(defect_docs)
save_yaml(defect_yml, defect_data)
print(f"\nDefect-Detection YAML recovered: {len(defect_data['documents'])} entries")

# ── Step 7: Summary ──
print("\n" + "=" * 60)
print("FIX SUMMARY")
print("=" * 60)
print(f"  Parent KB: Removed {len(rl_docs) + len(defect_docs)} polluted entries → {len(root_docs)} root doc")
print(f"  RL-Inverse-Design: Added {len(rl_docs)} documents (was 0)")
print(f"  Defect-Detection: Added {len(defect_docs)} documents (was 0)")
print(f"  Backups: .knowledge-base.yml.bak created for all 3 KBs")
print("\nDone.")
