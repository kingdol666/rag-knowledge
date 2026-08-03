"""SOUL 配置模块 — 人格知识库配置读写、作用域校验与基础工具。

SOUL (Self-Organizing Unified Learner) 人格知识库的配置层：
- SoulConfig 数据类定义人格库的元配置（作用域、路由权重、领域标签等）
- KB 路径解析与目录守卫
- 配置的原子读写
- 作用域合法性校验
- 基于 asyncio.Lock 的 per-soul 写操作互斥

本模块不依赖其他 soul 模块。
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.services.storage_reader_service import storage_reader
from app.utils.atomic_io import atomic_write_text
from app.utils.paths import get_storage_root
from app.utils.safe_paths import resolve_within

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────────────────────────

SOUL_PREFIX = "soul-"
SOUL_RETRIEVAL_SCORE_THRESHOLD = 0.5       # AC15 前置门
PER_SOUL_LOCK_TIMEOUT = 300                # 锁获取超时（秒）
SOUL_BUDGET_USD_PER_RUN = 0.15             # AC16
MAX_MEMORIES_IN_BUNDLE = 10                # persona_bundle 记忆数上限
ROUTE_CONFIDENCE_THRESHOLD = 0.6           # 自动路由阈值（钳位 [0.4, 0.8]）
ROUTER_TTL_SECONDS = 300
ROUTER_MAX_CANDIDATES = 8
SYNC_MAX_RETRIES = 3
CHECKPOINT_MAX_COUNT = 30
SYNTHESIS_TIMEOUT_SECONDS = 180


# ── SoulConfig 数据类 ──────────────────────────────────────────────────────

@dataclass
class SoulConfig:
    """人格知识库的元配置。

    Attributes:
        kb_scope: 该人格可检索的知识库列表。空列表表示仅人格问答（不检索外部知识库）；
            ``["*"]`` 表示全库检索。
        is_template: 是否为模板库（模板库不参与路由与自主学习）。
        route_weight: 路由排序权重乘数，默认 1.0。
        domain_labels: 领域标签列表，用于路由初筛时的 embedding 余弦匹配。
        supported_task_types: 支持的任务类型列表（如 fact / concept / cross_doc / challenge）。
    """

    kb_scope: list[str] = field(default_factory=list)
    is_template: bool = False
    route_weight: float = 1.0
    domain_labels: list[str] = field(default_factory=list)
    supported_task_types: list[str] = field(default_factory=list)


# ── 配置文件名常量 ─────────────────────────────────────────────────────────

_SOUL_CONFIG_FILENAME = "soul-config.yml"


# ── Per-soul asyncio.Lock 注册表 ──────────────────────────────────────────

_soul_locks: dict[str, asyncio.Lock] = {}
_soul_locks_guard = asyncio.Lock()


def get_soul_lock(soul_kb_id: str) -> asyncio.Lock:
    """获取指定 SOUL 知识库的 asyncio.Lock（模块级注册表，按需创建）。

    所有 per-soul 写操作（记忆写入、检查点、校准等）统一使用该锁，
    确保同一人格库的并发写串行化。
    """
    resolved = resolve_soul_kb_path(soul_kb_id)
    key = resolved or soul_kb_id
    if key not in _soul_locks:
        _soul_locks[key] = asyncio.Lock()
    return _soul_locks[key]


# ── KB 路径解析 ────────────────────────────────────────────────────────────

def resolve_soul_kb_path(soul_kb_id: str) -> str | None:
    """将 SOUL KB 的 UUID 或路径解析为 KB 相对路径。

    若传入的标识符对应一个名称以 ``soul-`` 开头的知识库，
    返回其相对路径；否则返回 ``None``。

    Args:
        soul_kb_id: KB 的 UUID 或相对路径。

    Returns:
        KB 相对路径字符串；非 soul KB 时返回 None。
    """
    if not soul_kb_id:
        return None

    # 先尝试按路径直接匹配
    norm = soul_kb_id.replace("\\", "/").strip("/")
    kbs = storage_reader.list_knowledge_bases()
    for kb in kbs:
        kb_path = (kb.get("path") or "").replace("\\", "/").strip("/")
        if kb_path == norm and (kb.get("name") or "").startswith(SOUL_PREFIX):
            return kb["path"]
        if kb.get("kb_id") == soul_kb_id and (kb.get("name") or "").startswith(SOUL_PREFIX):
            return kb["path"]

    # 作为 UUID 匹配
    for kb in kbs:
        if kb.get("kb_id") == soul_kb_id:
            name = kb.get("name") or ""
            if name.startswith(SOUL_PREFIX):
                return kb["path"]
            return None

    return None


def soul_kb_dir(soul_kb_id: str) -> Path:
    """返回 SOUL KB 在存储根下的安全目录路径。

    经过 ``resolve_within`` 守卫，确保路径不逃逸出存储根。

    Args:
        soul_kb_id: KB UUID 或路径。

    Returns:
        解析后的 ``Path`` 对象。

    Raises:
        ValueError: 路径不在存储根子树内，或 KB 不是 soul 库。
    """
    resolved = resolve_soul_kb_path(soul_kb_id)
    if resolved is None:
        raise ValueError(f"Not a soul KB: {soul_kb_id!r}")
    storage_root = get_storage_root()
    safe = resolve_within(resolved, str(storage_root))
    return Path(safe)


# ── 配置读写 ───────────────────────────────────────────────────────────────

def _default_soul_config() -> SoulConfig:
    """返回 SoulConfig 的默认实例。"""
    return SoulConfig()


def read_soul_config(soul_kb_id: str) -> SoulConfig:
    """读取 SOUL KB 的 ``soul-config.yml``，返回 ``SoulConfig``。

    文件不存在时返回默认配置（空 scope，is_template=False）。
    若 kb_id 不是 soul 库则抛出 ``ValueError``。

    Args:
        soul_kb_id: KB UUID 或路径。

    Returns:
        解析后的 ``SoulConfig`` 对象。

    Raises:
        ValueError: kb_id 不是 soul 前缀的知识库。
    """
    resolved = resolve_soul_kb_path(soul_kb_id)
    if resolved is None:
        raise ValueError(f"Not a soul KB (soul- prefix required): {soul_kb_id!r}")
    config_path = soul_kb_dir(soul_kb_id) / _SOUL_CONFIG_FILENAME
    if not config_path.exists():
        return _default_soul_config()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to parse %s: %s", config_path, e)
        return _default_soul_config()
    if not isinstance(raw, dict):
        return _default_soul_config()
    return SoulConfig(
        kb_scope=raw.get("kb_scope", []),
        is_template=bool(raw.get("is_template", False)),
        route_weight=float(raw.get("route_weight", 1.0)),
        domain_labels=raw.get("domain_labels", []),
        supported_task_types=raw.get("supported_task_types", []),
    )


def write_soul_config(soul_kb_id: str, cfg: SoulConfig) -> None:
    """原子写入 SOUL KB 的 ``soul-config.yml``。

    Args:
        soul_kb_id: KB UUID 或路径。
        cfg: 要持久化的 ``SoulConfig``。

    Raises:
        ValueError: kb_id 不是 soul 前缀的知识库。
    """
    resolved = resolve_soul_kb_path(soul_kb_id)
    if resolved is None:
        raise ValueError(f"Not a soul KB (soul- prefix required): {soul_kb_id!r}")
    kb_dir = soul_kb_dir(soul_kb_id)
    config_path = kb_dir / _SOUL_CONFIG_FILENAME
    data: dict[str, Any] = {
        "kb_scope": cfg.kb_scope,
        "is_template": cfg.is_template,
        "route_weight": cfg.route_weight,
        "domain_labels": cfg.domain_labels,
        "supported_task_types": cfg.supported_task_types,
    }
    yaml_text = yaml.dump(data, allow_unicode=True, sort_keys=False, indent=2)
    atomic_write_text(config_path, yaml_text)


# ── 作用域校验 ─────────────────────────────────────────────────────────────

def validate_scope(scope: list[str]) -> tuple[list[str], list[str]]:
    """校验 scope（kb_id 列表）中每个条目的存在性与合法性。

    依次检查：
    - 每个 kb_id 是否在 ``list_knowledge_bases()`` 中存在（id 或 path 匹配）
    - soul- 前缀的 KB 不能出现在 scope 中（soul 库仅供人格使用，不作为检索源）
    - 不存在的 kb_id 标记为 scope_kb_missing

    Args:
        scope: kb_id 列表（UUID 或 path）。

    Returns:
        ``(valid_kb_ids: list[str], reasons: list[str])``，
        reasons 中每个条目对应一个 scope 条目的校验结论：
        - ``"ok"`` — 通过
        - ``"scope_contains_soul_kb"`` — soul 库不应作为外部检索源
        - ``"scope_kb_missing"`` — 未找到该 KB
    """
    kbs = storage_reader.list_knowledge_bases()
    # 构建查找索引：id → kb, path → kb
    by_id: dict[str, dict[str, Any]] = {}
    by_path: dict[str, dict[str, Any]] = {}
    for kb in kbs:
        kid = kb.get("kb_id", "")
        kpath = (kb.get("path") or "").replace("\\", "/").strip("/")
        if kid:
            by_id[kid] = kb
        if kpath:
            by_path[kpath] = kb

    valid: list[str] = []
    reasons: list[str] = []

    for item in scope:
        item = str(item).strip()
        if not item:
            valid.append(item)
            reasons.append("scope_kb_missing")
            continue

        # 全库通配符: "*" 表示全部公开库参与(学习/检索由调用方展开)
        if item == "*":
            valid.append(item)
            reasons.append("ok")
            continue

        # 尝试匹配
        kb = by_id.get(item) or by_path.get(item)
        if kb is None:
            valid.append(item)
            reasons.append("scope_kb_missing")
            continue

        name = kb.get("name") or ""
        if name.startswith(SOUL_PREFIX):
            valid.append(item)
            reasons.append("scope_contains_soul_kb")
        else:
            valid.append(item)
            reasons.append("ok")

    return valid, reasons


def scope_hash(scope: list[str]) -> str:
    """计算 scope 的 SHA-256 哈希（排序后取 hex 摘要）。

    用于检测 scope 变更以触发记忆标记 stale 等操作。
    """
    sorted_scope = sorted(scope)
    digest = hashlib.sha256(
        "\n".join(sorted_scope).encode("utf-8")
    ).hexdigest()
    return digest


# ── SOUL KB 枚举 ───────────────────────────────────────────────────────────

def list_soul_kbs(include_template: bool = False) -> list[dict[str, Any]]:
    """列出所有 SOUL 知识库。

    从 ``storage_reader.list_knowledge_bases()`` 中过滤名称以 ``soul-``
    开头的知识库，默认排除模板库。通过读取每个 soul KB 的配置判断
    ``is_template`` 标志。

    Args:
        include_template: 是否包含模板库。

    Returns:
        每个元素包含 ``{kb_id, name, path, is_template}``。
    """
    result: list[dict[str, Any]] = []
    kbs = storage_reader.list_knowledge_bases()
    for kb in kbs:
        name = kb.get("name") or ""
        if not name.startswith(SOUL_PREFIX):
            continue
        try:
            cfg = read_soul_config(kb["path"] or kb["kb_id"])
        except ValueError:
            # 非 soul 库（理论上不应走到这里，防御）
            continue
        if cfg.is_template and not include_template:
            continue
        result.append({
            "kb_id": kb.get("kb_id", ""),
            "name": name,
            "path": kb.get("path", ""),
            "is_template": cfg.is_template,
        })
    return result


def is_template_kb(soul_kb_id: str) -> bool:
    """判断指定的 SOUL KB 是否为模板库。

    Args:
        soul_kb_id: KB UUID 或路径。

    Returns:
        ``True`` 若 is_template 标志为真，否则 ``False``。
    """
    try:
        cfg = read_soul_config(soul_kb_id)
        return cfg.is_template
    except ValueError:
        return False


# ── 目录初始化 ─────────────────────────────────────────────────────────────

_SOUL_SUBDIRS = [
    "memories",
    "cognition",
    "cognition-drafts",
    "reports",
    "questions",
    "calibration",
    "checkpoints",
    "audit",
    "training",
]


def ensure_soul_dirs(soul_kb_id: str) -> None:
    """确保 SOUL KB 的必备子目录存在（幂等）。

    创建 memories / cognition / cognition-drafts / reports / questions /
    calibration / audit / training 八个目录，已存在则跳过。

    Args:
        soul_kb_id: KB UUID 或路径。
    """
    kb_dir = soul_kb_dir(soul_kb_id)
    for subdir in _SOUL_SUBDIRS:
        (kb_dir / subdir).mkdir(parents=True, exist_ok=True)