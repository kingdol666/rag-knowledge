#!/usr/bin/env python3
"""
O13 — General-purpose YAML index cleaning for any KB.

Fixes three classes of YAML pollution:
1. Orphan entries (YAML has document, disk file is gone — kb_doc_move/delete residue)
2. Parent-KB pollution (parent YAML contains child documents belonging to sub-KBs)
3. Missing entries (disk has .md file but YAML has no index entry)

Usage:
  # Clean a single KB (remove orphan entries, validate paths)
  python fix_yaml_index.py clean <kb_path>

  # Clean parent KB pollution (move child-doc entries to their sub-KB YAMLs)
  python fix_yaml_index.py unparent <parent_kb_path>

  # Full 3-way consistency check across all KBs
  python fix_yaml_index.py audit-all
"""
import yaml
import sys
import json
from pathlib import Path
import shutil

DEFAULT_STORAGE = Path(__file__).resolve().parent.parent.parent.parent.parent \
    / "storage" / "tree-file-system"
# Fall back if not found via relative path
if not DEFAULT_STORAGE.exists():
    DEFAULT_STORAGE = Path("storage/tree-file-system")
if not DEFAULT_STORAGE.exists():
    DEFAULT_STORAGE = Path("web/storage/tree-file-system")

STORAGE = DEFAULT_STORAGE


def yaml_str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(str, yaml_str_representer)


def backup_file(path):
    bak = path.with_suffix(".yml.bak")
    shutil.copy2(path, bak)
    print(f"  Backup: {bak}")


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  Written: {path}")


def get_kb_path(kb_path_str: str) -> Path:
    """Resolve KB path: either relative like 'Polymer-Biaxial-Stretching' or absolute."""
    p = Path(kb_path_str)
    if p.is_absolute() and p.exists():
        return p
    candidate = STORAGE / kb_path_str
    if candidate.exists():
        return candidate
    print(f"ERROR: KB path not found: {kb_path_str} (tried absolute and under {STORAGE})")
    sys.exit(1)


def cmd_audit_all():
    """Check all KBs for orphan entries, missing files, and count mismatches."""
    results = {}
    for kb_dir in sorted(STORAGE.iterdir()):
        if not kb_dir.is_dir() or kb_dir.name.startswith('.'):
            continue
        yml_path = kb_dir / ".knowledge-base.yml"
        if not yml_path.exists():
            continue

        data = load_yaml(yml_path)
        docs = data.get('documents', [])
        md_files = set(p.name for p in kb_dir.glob("*.md"))
        yaml_paths = set()
        orphans = []
        missing = []
        healthy = 0

        for doc in docs:
            doc_path = doc.get('path', '')
            doc_name = doc.get('name', '')
            # Try both the full path and bare name
            if (kb_dir / doc_name).exists() or (STORAGE / doc_path.replace('\\', '/')).exists():
                healthy += 1
            else:
                orphans.append(doc_name)
            yaml_paths.add(doc_name)

        missing = md_files - yaml_paths

        if orphans or missing:
            results[kb_dir.name] = {
                "total_yaml": len(docs),
                "disk_md": len(md_files),
                "orphans": orphans,
                "missing": sorted(missing),
                "healthy": healthy,
            }

    print("=" * 60)
    print("O13 — YAML Consistency Audit")
    print("=" * 60)
    for kb_name, info in sorted(results.items()):
        print(f"\n📁 {kb_name}")
        print(f"   YAML entries: {info['total_yaml']}, Disk .md files: {info['disk_md']}")
        if info['orphans']:
            print(f"   ⚠️  Orphans (in YAML, not on disk): {len(info['orphans'])}")
            for o in info['orphans'][:10]:
                print(f"       - {o}")
        if info['missing']:
            print(f"   ⚠️  Missing (on disk, not in YAML): {len(info['missing'])}")
            for m in info['missing'][:10]:
                print(f"       - {m}")
        if not info['orphans'] and not info['missing']:
            print(f"   ✅ Healthy ({info['healthy']} docs)")
    print("\nDone.")


def cmd_clean(kb_path_str: str):
    """Remove orphan YAML entries where the disk file no longer exists."""
    kb_dir = get_kb_path(kb_path_str)
    yml_path = kb_dir / ".knowledge-base.yml"
    if not yml_path.exists():
        print(f"ERROR: No .knowledge-base.yml found in {kb_dir}")
        sys.exit(1)

    backup_file(yml_path)
    data = load_yaml(yml_path)
    original_count = len(data.get('documents', []))
    documents = data.get('documents', [])
    cleaned = []
    removed = []

    for doc in documents:
        doc_path = doc.get('path', '')
        doc_name = doc.get('name', '')
        if (kb_dir / doc_name).exists():
            cleaned.append(doc)
        elif doc.get('file_type') == 'knowledge-base':
            # Sub-KB folder reference — keep regardless
            cleaned.append(doc)
        else:
            removed.append(doc_name)

    data['documents'] = cleaned
    if 'total_documents' in data:
        data['total_documents'] = len([d for d in cleaned if d.get('file_type') != 'knowledge-base'])

    save_yaml(yml_path, data)
    print(f"\n🧹 Cleaned {len(removed)} orphan(s) from {kb_dir.name}:")
    for r in removed:
        print(f"   - {r}")
    print(f"   {original_count} → {len(cleaned)} entries")


def cmd_unparent(parent_path_str: str):
    """Move child-doc entries from parent YAML into their sub-KB YAML files."""
    parent_dir = get_kb_path(parent_path_str)
    yml_path = parent_dir / ".knowledge-base.yml"
    if not yml_path.exists():
        print(f"ERROR: No .knowledge-base.yml found in {parent_dir}")
        sys.exit(1)

    data = load_yaml(yml_path)
    all_docs = data.get('documents', [])

    # Discover sub-KBs (directories that are themselves KBs)
    sub_kbs = {}
    for item in parent_dir.iterdir():
        if item.is_dir() and (item / ".knowledge-base.yml").exists():
            sub_kbs[item.name] = item

    if not sub_kbs:
        print(f"No sub-KBs found under {parent_dir.name}. Nothing to unparent.")
        return

    print(f"Found sub-KBs: {list(sub_kbs.keys())}")

    root_docs = []
    folder_refs = []
    moved_by_subkb = {name: [] for name in sub_kbs}

    for doc in all_docs:
        if doc.get('file_type') == 'knowledge-base':
            folder_refs.append(doc)
            continue
        doc_path = doc.get('path', '')
        doc_name = doc.get('name', '')
        # Check if this doc's path belongs to a sub-KB
        moved = False
        for sub_name, sub_dir in sub_kbs.items():
            if sub_name in doc_path.replace('\\', '/') or sub_name in doc_name:
                moved_by_subkb[sub_name].append(doc)
                moved = True
                break
        if not moved:
            root_docs.append(doc)

    # Update parent YAML
    backup_file(yml_path)
    data['documents'] = root_docs + folder_refs
    data['total_documents'] = len(root_docs)
    save_yaml(yml_path, data)

    # Update each sub-KB YAML
    for sub_name, sub_dir in sub_kbs.items():
        sub_yml = sub_dir / ".knowledge-base.yml"
        sub_data = load_yaml(sub_yml)
        backup_file(sub_yml)
        existing = sub_data.get('documents', [])
        existing_names = {d.get('name') for d in existing}
        incoming = [d for d in moved_by_subkb[sub_name]
                    if d.get('name') not in existing_names]
        sub_data['documents'] = existing + incoming
        total = len([d for d in sub_data['documents'] if d.get('file_type') != 'knowledge-base'])
        sub_data['total_documents'] = total
        if 'knowledge_base' in sub_data:
            sub_data['knowledge_base']['total_documents'] = total
        save_yaml(sub_yml, sub_data)
        print(f"   {sub_name}: added {len(incoming)} docs (now {len(sub_data['documents'])} total)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == 'audit-all':
        cmd_audit_all()
    elif command == 'clean' and len(sys.argv) >= 3:
        cmd_clean(sys.argv[2])
    elif command == 'unparent' and len(sys.argv) >= 3:
        cmd_unparent(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
