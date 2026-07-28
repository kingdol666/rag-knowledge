"""KB Meditation Config — read/write per-KB meditation settings from YAML metadata.

Meditation config is stored in each KB's .knowledge-base.yml under
`knowledge_base.metadata.meditation`. This ensures config travels with
the KB when moved/merged/renamed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from app.utils.paths import get_storage_root
from app.utils.atomic_io import atomic_write_text
DEFAULT_MEDITATION_CONFIG: dict[str, Any] = {
    "enabled": False,
    "harness": "omp",           # "omp" or "claude" (heuristic is internal fallback only)
    "model": "",                # Empty = use harness default (OMP: deepseek-v4-pro, Claude: sonnet)
    "interval_hours": 24,
    "min_cluster_count": 2,
    "max_drafts_per_run": 3,
    "auto_publish": False,      # True = quality>=7 auto-publish; False = all go to draft pool
    "max_budget_usd": 0.05,
    "timeout_sec": 600,
    "last_run_at": None,
    "last_run_status": None,
    "last_run_report": {},
    "total_runs": 0,
    "total_experiences_generated": 0,
    "incremental_enabled": True,
    "created_at": None,
    "updated_at": None,
}


def _normalize_path(p: str) -> str:
    return p.replace("\\", "/")


def _resolve_kb_path(kb_id: str) -> Optional[str]:
    """Resolve kb_id (UUID or path) → KB relative path."""
    import json
    tree_path = get_storage_root() / ".tree-fs.json"
    if not tree_path.exists():
        return None
    try:
        tree = json.loads(tree_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    for folder in tree.get("folders", []):
        if folder.get("id") == kb_id or folder.get("path") == kb_id:
            return folder.get("path")
    if (get_storage_root() / kb_id).exists():
        return kb_id
    return None


def _get_kb_yaml_path(kb_path: str) -> Path:
    return get_storage_root() / _normalize_path(kb_path) / ".knowledge-base.yml"


def get_meditation_config(kb_id: str) -> dict:
    """Read meditation config for a KB. Returns defaults for missing fields."""
    kb_path = _resolve_kb_path(kb_id)
    if not kb_path:
        return {"success": False, "error": f"KB not found: {kb_id}"}

    yaml_path = _get_kb_yaml_path(kb_path)
    if not yaml_path.exists():
        return {
            "success": True,
            "kb_id": kb_id,
            "kb_path": kb_path,
            "config": dict(DEFAULT_MEDITATION_CONFIG),
            "source": "defaults",
        }

    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warning("Failed to read KB YAML %s: %s", yaml_path, e)
        return {"success": True, "kb_id": kb_id, "kb_path": kb_path,
                "config": dict(DEFAULT_MEDITATION_CONFIG), "source": "defaults"}

    kb_info = data.get("knowledge_base", {})
    metadata = kb_info.get("metadata", {}) or {}
    stored = metadata.get("meditation", {}) or {}

    # Merge with defaults for backward compatibility
    config = dict(DEFAULT_MEDITATION_CONFIG)
    config.update({k: v for k, v in stored.items() if v is not None or k in stored})

    return {
        "success": True,
        "kb_id": kb_id,
        "kb_path": kb_path,
        "config": config,
        "source": "yaml",
    }


def update_meditation_config(kb_id: str, updates: dict) -> dict:
    """Update meditation config fields for a KB. Persists to YAML."""
    kb_path = _resolve_kb_path(kb_id)
    if not kb_path:
        return {"success": False, "error": f"KB not found: {kb_id}"}

    yaml_path = _get_kb_yaml_path(kb_path)

    # Read existing YAML
    if yaml_path.exists():
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning("Failed to read KB YAML %s: %s", yaml_path, e)
            data = {}
    else:
        data = {}

    # Ensure structure exists
    if "knowledge_base" not in data:
        data["knowledge_base"] = {}
    kb_data = data["knowledge_base"]
    if "metadata" not in kb_data:
        kb_data["metadata"] = {}
    metadata = kb_data["metadata"]
    if "meditation" not in metadata:
        metadata["meditation"] = {}

    # Validate known fields
    known_fields = set(DEFAULT_MEDITATION_CONFIG.keys())
    for k in list(updates.keys()):
        if k not in known_fields:
            logger.warning("Unknown meditation config field: %s", k)
        else:
            metadata["meditation"][k] = updates[k]

    metadata["meditation"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    if not metadata["meditation"].get("created_at"):
        metadata["meditation"]["created_at"] = datetime.now(timezone.utc).isoformat()

    # Write back
    try:
        atomic_write_text(
            yaml_path,
            yaml.dump(data, allow_unicode=True, sort_keys=False, indent=2, default_flow_style=False),
        )
    except Exception as e:
        logger.error("Failed to write KB YAML %s: %s", yaml_path, e)
        return {"success": False, "error": str(e)}

    return {
        "success": True,
        "kb_id": kb_id,
        "kb_path": kb_path,
        "config": metadata["meditation"],
    }


def get_all_kb_meditation_configs() -> list[dict]:
    """Get meditation config for all KBs. Returns list of {kb_id, kb_path, config}."""
    import json
    tree_path = get_storage_root() / ".tree-fs.json"
    if not tree_path.exists():
        return []

    try:
        tree = json.loads(tree_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    results = []
    for folder in tree.get("folders", []):
        if not folder.get("isKnowledgeBase"):
            continue
        kb_path = folder.get("path", "")
        if not kb_path:
            continue
        config_result = get_meditation_config(kb_path)
        if config_result.get("success"):
            results.append({
                "kb_id": folder.get("id", kb_path),
                "kb_name": folder.get("name", ""),
                "kb_path": kb_path,
                "config": config_result["config"],
            })

    return results
