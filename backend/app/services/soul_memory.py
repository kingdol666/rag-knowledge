"""SOUL 记忆管理服务 — 记忆草稿审批、检查点、回滚、反思与训练数据导出。

管理 SOUL 知识库内的记忆生命周期：草稿列表/审批/拒绝、检查点创建与回滚、
认知漂移反思、训练数据导出与 scope 变更后标记陈旧记忆。

所有文件写入经 ``atomic_write_text``；草稿与记忆严禁经 HTTP/工具 API 创建。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.utils.atomic_io import atomic_write_text
from app.utils.safe_paths import resolve_within
from app.utils.paths import get_storage_root
from app.services.vector_service import vector_service
from app.services.graph_service import graph_service
from app.services.storage_reader_service import storage_reader
from app.utils.file_lock import file_lock, yaml_lock_path

# === soul_config 常量与工具（由 Agent A 实现） ===
from app.services.soul_config import (  # type: ignore[import-untyped]  # noqa: E402
    CHECKPOINT_MAX_COUNT,
    PER_SOUL_LOCK_TIMEOUT,
    resolve_soul_kb_path,
    soul_kb_dir,
    read_soul_config,
    get_soul_lock,
)

logger = logging.getLogger(__name__)

# prompts 目录（与当前模块同级）
_PROMPTS_DIR = Path(__file__).parent / "prompts"


# ═══════════════════════════════════════════════════════════════════
#  内部辅助
# ═══════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    """UTC 感知 ISO8601 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _norm_path(p: str) -> str:
    """统一路径分隔符为 /。"""
    return (p or "").replace("\\", "/")


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """解析 Markdown 文件的 YAML frontmatter。

    返回 ``(frontmatter_dict, body_text)``。
    frontmatter 以 ``---`` 起始和结束行界定；无 frontmatter 时返回 ``({}, content)``。
    """
    if not content.startswith("---"):
        return {}, content
    rest = content[3:]
    idx = rest.find("\n---")
    if idx == -1:
        return {}, content
    fm_text = rest[:idx]
    body = rest[idx + 4:]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, body.strip()


def _read_memory_frontmatter(file_path: Path) -> dict[str, Any] | None:
    """读取记忆文件的 frontmatter，失败返回 None。"""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except Exception:
        return None
    fm, _ = _parse_frontmatter(raw)
    return fm


def _read_memory_full(file_path: Path) -> tuple[dict[str, Any], str] | None:
    """读取记忆文件的完整 ``(frontmatter, body)``，失败返回 None。"""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except Exception:
        return None
    return _parse_frontmatter(raw)


def _sha256(text: str) -> str:
    """计算文本的 SHA256 哈希（十六进制）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    """计算文件内容的 SHA256 哈希；文件不存在返回空串。"""
    if not path.exists():
        return ""
    return _sha256(path.read_text(encoding="utf-8"))


def _memory_body_text(body: str, max_chars: int = 500) -> str:
    """从记忆 Markdown body 中提取答案文本（前 max_chars 字）。

    优先提取 ``## 答案`` 节内容；无则取 body 前 max_chars。
    """
    if "## 答案" in body:
        parts = body.split("## 答案", 1)
        answer_part = parts[1] if len(parts) > 1 else body
        next_h2 = answer_part.find("\n## ")
        if next_h2 != -1:
            answer_part = answer_part[:next_h2]
        return answer_part.strip()[:max_chars]
    return body.strip()[:max_chars]


def _fmt_frontmatter(fm: dict[str, Any]) -> str:
    """将 frontmatter dict 格式化为 YAML frontmatter（含首尾 ``---``）。"""
    lines = ["---"]
    lines.append(yaml.dump(fm, allow_unicode=True, sort_keys=False).rstrip())
    lines.append("---")
    return "\n".join(lines)


def _append_jsonl(jsonl_path: Path, record: dict[str, Any]) -> None:
    """向 JSONL 文件追加一行。"""
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(jsonl_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def _read_yaml_safe(yml_path: Path) -> dict[str, Any] | None:
    """安全读取 YAML 文件，失败返回 None。"""
    if not yml_path.exists():
        return None
    try:
        data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_yaml_atomic(yml_path: Path, data: dict[str, Any]) -> None:
    """原子写 YAML 文件。"""
    atomic_write_text(
        yml_path,
        yaml.dump(data, allow_unicode=True, sort_keys=False, indent=2),
    )


# ═══════════════════════════════════════════════════════════════════
#  草稿列表
# ═══════════════════════════════════════════════════════════════════

async def list_drafts(
    soul_kb_id: str, draft_type: str = "memory"
) -> dict[str, Any]:
    """列出 SOUL 知识库的待审批记忆草稿。

    Args:
        soul_kb_id: SOUL 知识库 ID（UUID 或路径）。
        draft_type: ``"memory"`` 扫描 ``memories/*.md``（status=pending）；
                    ``"cognition"`` 扫描 ``cognition-drafts/*.md``。

    Returns:
        ``{"drafts": [...], "count": int}``。无草稿时 count=0，非错误。
    """
    _soul_dir = soul_kb_dir(soul_kb_id)
    if draft_type == "memory":
        scan_dir = _soul_dir / "memories"
        status_target = "pending"
    elif draft_type == "cognition":
        scan_dir = _soul_dir / "cognition-drafts"
        status_target = None
    else:
        return {"drafts": [], "count": 0}

    drafts: list[dict[str, Any]] = []
    if not scan_dir.exists():
        return {"drafts": drafts, "count": 0}

    for f_path in sorted(scan_dir.glob("*.md")):
        fm, body = _read_memory_full(f_path) or ({}, "")
        if not fm:
            continue
        if status_target is not None and fm.get("status") != status_target:
            continue
        drafts.append({
            "draft_id": f_path.stem,
            "question": fm.get("question", ""),
            "answer_text": _memory_body_text(body),
            "scores": fm.get("scores", {}),
            "pas_score": fm.get("pas_score", 0.0),
            "evidence_paths": fm.get("evidence_paths", []),
            "status": fm.get("status", ""),
            "created_at": fm.get("learned_at", ""),
        })

    return {"drafts": drafts, "count": len(drafts)}


# ═══════════════════════════════════════════════════════════════════
#  批准草稿
# ═══════════════════════════════════════════════════════════════════

async def approve_draft(
    soul_kb_id: str,
    draft_id: str,
    force: bool = False,
    operator: str = "system",
    draft_type: str = "memory",
) -> dict[str, Any]:
    """批准一条草稿为正式记忆(cognition 草稿 → 合并入人格定义)。

    审批闸门：
    - ``groundedness < 3`` 且非 ``force`` → ``grounding_below_3``
    - 四维均分 ``< 3`` 且非 ``force`` → ``low_score``
    通过后：frontmatter status→approved，注册为 KB 文档，向量/图谱索引，
    审计日志写入 ``audit/approval-log.jsonl``。

    Args:
        soul_kb_id: SOUL 知识库 ID。
        draft_id: 草稿文件名（不含 .md）。
        force: 强制通过评分闸门。
        operator: 操作者标识。
        draft_type: ``memory``(默认) 或 ``cognition``(RL 认知草稿,
            审批后合并入 soul-definition.md 对应章节)。

    Returns:
        成功 ``{"success": True, "approved": [draft_id], "indexed": bool}``；
        拒绝 ``{"success": False, "error": str, "requires_force": bool}``。
    """
    # cognition 草稿: 委托 RL 引擎合并入人格定义(章节内追加优化行)
    if draft_type == "cognition":
        from app.services.soul_reward import apply_cognition_draft
        return await apply_cognition_draft(soul_kb_id, draft_id, operator=operator)

    _soul_dir = soul_kb_dir(soul_kb_id)
    mem_path = _soul_dir / "memories" / f"{draft_id}.md"

    if not mem_path.exists():
        return {
            "success": False,
            "error": f"Draft not found: {draft_id}",
            "requires_force": False,
        }

    fm, body = _read_memory_full(mem_path) or ({}, "")
    if not fm:
        return {
            "success": False,
            "error": "draft_corrupted",
            "requires_force": False,
        }

    scores = fm.get("scores", {})
    groundedness = scores.get("groundedness", 0)
    mean_score = (
        sum(scores.values()) / len(scores)
    ) if scores else 0.0

    # === 评分闸门 ===
    if groundedness < 3 and not force:
        return {
            "success": False,
            "error": "grounding_below_3",
            "requires_force": True,
        }
    if mean_score < 3 and not force:
        return {
            "success": False,
            "error": "low_score",
            "requires_force": True,
        }

    # === 写入 frontmatter: status=approved ===
    now_iso = _now_iso()
    fm["status"] = "approved"
    fm["approved_at"] = now_iso
    fm["approved_by"] = operator
    new_content = _fmt_frontmatter(fm) + "\n" + body
    atomic_write_text(mem_path, new_content)

    # === 注册为 KB 文档 + 索引 ===
    kb_path = resolve_soul_kb_path(soul_kb_id)
    if not kb_path:
        return {
            "success": True,
            "approved": [draft_id],
            "indexed": False,
            "warning": "kb_not_found",
        }

    indexed = False
    try:
        # 相对于 KB root 的文档路径
        doc_rel_path = f"{kb_path}/memories/{draft_id}.md"

        # 检查是否已注册
        existing_docs = storage_reader.list_documents(kb_path)
        already_registered = any(
            _norm_path(d.get("path", "")) == _norm_path(doc_rel_path)
            for d in existing_docs
        )

        if not already_registered:
            # 读取 .knowledge-base.yml，追加文档条目
            yml_path = get_storage_root() / kb_path / ".knowledge-base.yml"
            with file_lock(yaml_lock_path(yml_path)):
                data = _read_yaml_safe(yml_path) or {}

                file_size = mem_path.stat().st_size if mem_path.exists() else 0

                # 文档条目形状对齐现有 YAML 中的 documents[] 条目
                doc_entry: dict[str, Any] = {
                    "id": uuid.uuid4().hex,
                    "name": f"{draft_id}.md",
                    "description": fm.get("question", "")[:200],
                    "path": doc_rel_path,
                    "file_type": "md",
                    "file_size": file_size,
                    "added_at": now_iso,
                    "updated_at": now_iso,
                    "metadata": {},
                    "tags": [],
                }
                documents = data.get("documents", [])
                documents.append(doc_entry)
                data["documents"] = documents
                _write_yaml_atomic(yml_path, data)

            # 向量索引
            vec_result = vector_service.index_document(
                kb_id=kb_path,
                doc_path=doc_rel_path,
                content=body,
            )

            # 图谱索引
            graph_result = graph_service.index_document(
                doc_path=doc_rel_path,
                content=body,
                kb_id=kb_path,
                doc_name=f"{draft_id}.md",
            )

            # 写回索引元信息到 .knowledge-base.yml
            if vec_result:
                storage_reader.update_document_vector_index(
                    kb_path, doc_rel_path, vec_result
                )
            if graph_result:
                storage_reader.update_document_graph_index(
                    kb_path, doc_rel_path, graph_result
                )

            # 增量 BM25 更新(与 index_document 路由同路径;否则 two_stage stage1
            # 关键词/图谱候选找不到新记忆,AC14 的 60s 可检索会失败)
            try:
                from app.services.two_stage_search_service import two_stage_search_service
                two_stage_search_service.add_document({
                    "path": doc_rel_path,
                    "name": f"{draft_id}.md",
                    "description": fm.get("question", "")[:200],
                    "content": body,
                    "kb_id": kb_path,
                })
            except Exception as e:
                logger.warning("BM25 incremental update failed for %s: %s", draft_id, e)

            indexed = True
        else:
            # 已注册(训练期或此前审批): 校验向量索引是否真实存在, 缺失则补索引
            existing_vec = next(
                (d.get("vector_index") for d in existing_docs
                 if _norm_path(d.get("path", "")) == _norm_path(doc_rel_path)),
                None,
            )
            if not (existing_vec and existing_vec.get("indexed_at")):
                try:
                    vec_result = vector_service.index_document(
                        kb_id=kb_path, doc_path=doc_rel_path, content=body)
                    if vec_result:
                        storage_reader.update_document_vector_index(
                            kb_path, doc_rel_path, vec_result)
                        indexed = True
                except Exception as e:
                    logger.warning("re-index registered memory failed for %s: %s", draft_id, e)
            else:
                indexed = True
    except Exception as e:
        logger.warning("Registration/index failure for %s: %s", draft_id, e)
        return {
            "success": True,
            "approved": [draft_id],
            "indexed": False,
            "warning": "index_failure",
        }

    # === 审计日志 ===
    _append_jsonl(
        _soul_dir / "audit" / "approval-log.jsonl",
        {
            "timestamp": now_iso,
            "operator": operator,
            "action": "approve",
            "draft_id": draft_id,
            "force": force,
            "draft_scores": scores,
            "draft_pas_score": fm.get("pas_score", 0.0),
        },
    )

    # === 审批后刷新 profile-summary(计划 3.3: 草稿审批后刷新路由依据) ===
    try:
        from app.services.soul_profile import generate_profile_summary
        await generate_profile_summary(soul_kb_id)
    except Exception as e:
        logger.debug("profile refresh after approve failed: %s", e)

    return {
        "success": True,
        "approved": [draft_id],
        "indexed": indexed,
    }


# ═══════════════════════════════════════════════════════════════════
#  拒绝草稿
# ═══════════════════════════════════════════════════════════════════

async def reject_draft(
    soul_kb_id: str, draft_id: str, draft_type: str = "memory"
) -> dict[str, Any]:
    """拒绝一条草稿（保留文件，status→rejected）。

    Args:
        soul_kb_id: SOUL 知识库 ID。
        draft_id: 草稿文件名（不含 .md）。
        draft_type: ``memory``(默认) 或 ``cognition``(RL 认知草稿)。

    Returns:
        ``{"success": True, "rejected": draft_id}``
        或 ``{"success": False, "error": str}``。
    """
    _soul_dir = soul_kb_dir(soul_kb_id)
    scan_dir = _soul_dir / ("cognition-drafts" if draft_type == "cognition" else "memories")
    mem_path = scan_dir / f"{draft_id}.md"

    if not mem_path.exists():
        return {"success": False, "error": f"Draft not found: {draft_id}"}

    fm, body = _read_memory_full(mem_path) or ({}, "")
    if not fm:
        return {"success": False, "error": "draft_corrupted"}

    now_iso = _now_iso()
    fm["status"] = "rejected"
    fm["rejected_at"] = now_iso
    new_content = _fmt_frontmatter(fm) + "\n" + body
    atomic_write_text(mem_path, new_content)

    # === 审计日志 ===
    _append_jsonl(
        _soul_dir / "audit" / "approval-log.jsonl",
        {
            "timestamp": now_iso,
            "operator": "system",
            "action": "reject",
            "draft_id": draft_id,
            "force": False,
            "draft_scores": fm.get("scores", {}),
            "draft_pas_score": fm.get("pas_score", 0.0),
        },
    )

    return {"success": True, "rejected": draft_id}


# ═══════════════════════════════════════════════════════════════════
#  检查点（内部核心 + 公开接口）
# ═══════════════════════════════════════════════════════════════════

async def _create_checkpoint_locked(
    soul_kb_id: str, _soul_dir: Path
) -> dict[str, Any]:
    """检查点核心逻辑（调用方必须已持有 per-soul 锁）。"""
    now_iso = _now_iso()
    checkpoint_id = uuid.uuid4().hex

    # 哈希 soul root 下所有 .md 人格文档（自动发现）
    documents_hashes: dict[str, str] = {}
    for doc_path in sorted(_soul_dir.glob("*.md")):
        documents_hashes[doc_path.name] = _sha256_file(doc_path)

    # soul-config.yml
    config_path = _soul_dir / "soul-config.yml"
    documents_hashes["soul-config.yml"] = _sha256_file(config_path)

    # memories/*.md
    memories_hashes: dict[str, str] = {}
    memories_dir = _soul_dir / "memories"
    if memories_dir.exists():
        for f in sorted(memories_dir.glob("*.md")):
            rel = f"memories/{f.name}"
            memories_hashes[rel] = _sha256_file(f)

    # cognition-drafts/*.md
    drafts_hashes: dict[str, str] = {}
    drafts_dir = _soul_dir / "cognition-drafts"
    if drafts_dir.exists():
        for f in sorted(drafts_dir.glob("*.md")):
            rel = f"cognition-drafts/{f.name}"
            drafts_hashes[rel] = _sha256_file(f)

    # eval_prompt_hash
    eval_hash_path = _soul_dir / "checkpoints" / "eval_prompt_hashes.json"
    eval_prompt_hash = ""
    if eval_hash_path.exists():
        try:
            eh_data = json.loads(eval_hash_path.read_text(encoding="utf-8"))
            eval_prompt_hash = _sha256(json.dumps(eh_data, sort_keys=True))
        except Exception:
            pass

    manifest: dict[str, Any] = {
        "checkpoint_id": checkpoint_id,
        "created_at": now_iso,
        "soul_kb_id": soul_kb_id,
        "last_run_at": None,
        "documents": documents_hashes,
        "memories": memories_hashes,
        "drafts": drafts_hashes,
        "eval_prompt_hash": eval_prompt_hash,
    }

    checkpoints_dir = _soul_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = checkpoints_dir / f"{checkpoint_id}.json"
    atomic_write_text(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )

    total_files = (
        len(documents_hashes) + len(memories_hashes) + len(drafts_hashes)
    )

    # 剪枝：保留最近 CHECKPOINT_MAX_COUNT 个
    all_checkpoints = sorted(
        checkpoints_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    all_checkpoints = [
        cp for cp in all_checkpoints
        if cp.name != "eval_prompt_hashes.json"
    ]
    for stale in all_checkpoints[CHECKPOINT_MAX_COUNT:]:
        try:
            stale.unlink()
        except Exception:
            pass

    return {
        "success": True,
        "checkpoint_id": checkpoint_id,
        "manifest_path": str(manifest_path),
        "file_count": total_files,
    }


async def create_checkpoint(soul_kb_id: str) -> dict[str, Any]:
    """创建 SOUL 知识库当前状态的检查点。

    在 per-soul 锁下执行。
    见 :func:`_create_checkpoint_locked`。
    """
    _soul_dir = soul_kb_dir(soul_kb_id)

    lock = get_soul_lock(soul_kb_id)
    try:
        await asyncio.wait_for(lock.acquire(), timeout=PER_SOUL_LOCK_TIMEOUT)
    except asyncio.TimeoutError:
        return {"success": False, "error": "lock_timeout"}

    try:
        return await _create_checkpoint_locked(soul_kb_id, _soul_dir)
    finally:
        lock.release()


# ═══════════════════════════════════════════════════════════════════
#  回滚到检查点
# ═══════════════════════════════════════════════════════════════════

async def rollback_to_checkpoint(
    soul_kb_id: str, checkpoint_id: str
) -> dict[str, Any]:
    """回滚 SOUL 知识库到指定检查点。

    在 per-soul 锁下执行：
    根据 manifest 中记录的 SHA256 断言文件一致性；
    删除 manifest 未列出的 memories/ 和 cognition-drafts/ 文件；
    永不触碰 cognition/、reports/、training/、宪法层文档。
    扫描共享经验池（source_questions 匹配被回滚记忆 question）→ best-effort 计数。

    注意：检查点仅存哈希不含内容，无法从空白恢复文件内容；
    若文件已变更或丢失，回滚为 best-effort（保留现状并记日志）。

    Args:
        soul_kb_id: SOUL 知识库 ID。
        checkpoint_id: 检查点 UUID（文件名不含 .json）。

    Returns:
        ``{"success": True, "rolled_back_to": str, "restored_memories": int,
           "restored_drafts": int, "stale_experiences": int}``
        或 ``{"success": False, "error": "checkpoint_not_found"}``。
    """
    _soul_dir = soul_kb_dir(soul_kb_id)
    manifest_path = _soul_dir / "checkpoints" / f"{checkpoint_id}.json"

    if not manifest_path.exists():
        return {"success": False, "error": "checkpoint_not_found"}

    lock = get_soul_lock(soul_kb_id)
    try:
        await asyncio.wait_for(lock.acquire(), timeout=PER_SOUL_LOCK_TIMEOUT)
    except asyncio.TimeoutError:
        return {"success": False, "error": "lock_timeout"}

    try:
        manifest_raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_raw)
        expected_memories: dict[str, str] = manifest.get("memories", {})
        expected_drafts: dict[str, str] = manifest.get("drafts", {})

        # === 验证 + 删除 memories/ 多余文件 ===
        memories_dir = _soul_dir / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)

        existing_memories: set[str] = set()
        if memories_dir.exists():
            existing_memories = {
                _norm_path(f"memories/{f.name}")
                for f in memories_dir.glob("*.md")
            }

        expected_mem_norm = {_norm_path(p) for p in expected_memories}
        for exist_path in existing_memories:
            if exist_path not in expected_mem_norm:
                try:
                    (_soul_dir / exist_path).unlink()
                except Exception:
                    pass

        restored_memories = 0
        for rel_path, expected_hash in expected_memories.items():
            target = _soul_dir / rel_path
            if target.exists():
                current_hash = _sha256_file(target)
                if current_hash == expected_hash:
                    restored_memories += 1
                else:
                    logger.warning(
                        "Memory hash mismatch on rollback: %s", rel_path
                    )
                    restored_memories += 1
            else:
                logger.warning("Memory missing on rollback: %s", rel_path)

        # === 验证 + 删除 cognition-drafts/ 多余文件 ===
        drafts_dir = _soul_dir / "cognition-drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        existing_drafts: set[str] = set()
        if drafts_dir.exists():
            existing_drafts = {
                _norm_path(f"cognition-drafts/{f.name}")
                for f in drafts_dir.glob("*.md")
            }

        expected_drafts_norm = {_norm_path(p) for p in expected_drafts}
        for exist_path in existing_drafts:
            if exist_path not in expected_drafts_norm:
                try:
                    (_soul_dir / exist_path).unlink()
                except Exception:
                    pass

        restored_drafts = 0
        for rel_path, expected_hash in expected_drafts.items():
            target = _soul_dir / rel_path
            if target.exists():
                restored_drafts += 1

        # === 扫描共享经验池（best-effort） ===
        stale_experiences = 0
        try:
            from app.services.experience_service import experience_service

            restored_questions: list[str] = []
            for rel_path in expected_memories:
                target = _soul_dir / rel_path
                fm = _read_memory_frontmatter(target)
                if fm and fm.get("question"):
                    restored_questions.append(fm["question"])

            # 跨 KB 搜索 source_questions 匹配的经验草稿
            # ExperienceUpdate 无 stale 字段（经实证 experience_models.py），
            # 因此仅计数，不标记。待后续版本添加 stale 字段后再实现完整标记。
            all_kbs = storage_reader.list_knowledge_bases()
            for kb_info in all_kbs:
                kb_path_val = kb_info.get("path", "")
                if not kb_path_val or kb_path_val.startswith("soul-"):
                    continue
                try:
                    draft_result = await experience_service.list_drafts(
                        kb_path_val
                    )
                    if not draft_result.get("success"):
                        continue
                    for draft in draft_result.get("drafts", []):
                        sq = draft.get("source_questions", [])
                        if any(q in restored_questions for q in sq):
                            stale_experiences += 1
                except Exception:
                    continue
        except Exception as e:
            logger.warning(
                "Experience scan during rollback failed: %s", e
            )

        # === 刷新 profile-summary ===
        try:
            from app.services.soul_profile import generate_profile_summary
            await generate_profile_summary(soul_kb_id)
        except Exception:
            pass

        return {
            "success": True,
            "rolled_back_to": checkpoint_id,
            "restored_memories": restored_memories,
            "restored_drafts": restored_drafts,
            "stale_experiences": stale_experiences,
        }
    finally:
        lock.release()


# ═══════════════════════════════════════════════════════════════════
#  反思
# ═══════════════════════════════════════════════════════════════════

async def reflect(soul_kb_id: str) -> dict[str, Any]:
    """执行 SOUL 认知漂移反思。

    在 per-soul 锁下执行：
    1. 先创建检查点。
    2. 对比 ``cognition-drafts/*.md`` 与 ``soul-definition.md``
       的逐特质 diff 表（identity/values/thinking/language 四个章节）。
    3. 可选 LLM 注释：若 ``prompts/soul_reflect_v1.txt`` 存在则加载为
       system prompt，否则用内联 prompt。仅在有漂移时调用 LLM。
    4. 写 ``reports/drift-YYYYMMDD.md``。
    5. 刷新 profile-summary。

    Args:
        soul_kb_id: SOUL 知识库 ID。

    Returns:
        ``{"success": True, "report_path": str, "drift_detected": bool,
           "traits_diff_summary": dict}``。
    """
    _soul_dir = soul_kb_dir(soul_kb_id)

    lock = get_soul_lock(soul_kb_id)
    try:
        await asyncio.wait_for(lock.acquire(), timeout=PER_SOUL_LOCK_TIMEOUT)
    except asyncio.TimeoutError:
        return {"success": False, "error": "lock_timeout"}

    try:
        # 1. 创建检查点（已持有锁，调用内部版本）
        await _create_checkpoint_locked(soul_kb_id, _soul_dir)

        # 2. 读取 soul-definition.md
        soul_def_path = _soul_dir / "soul-definition.md"
        soul_def_text = (
            soul_def_path.read_text(encoding="utf-8")
            if soul_def_path.exists()
            else ""
        )

        # 3. 解析 soul-definition 的章节
        trait_sections = ["identity", "values", "thinking", "language"]
        soul_def_traits: dict[str, list[str]] = {}
        current_section = "preamble"
        soul_def_traits["preamble"] = []

        for line in soul_def_text.split("\n"):
            line_lower = line.strip().lower()
            if (
                line_lower.startswith("## ")
                and line_lower[3:].strip() in trait_sections
            ):
                current_section = line_lower[3:].strip()
                soul_def_traits.setdefault(current_section, [])
            else:
                soul_def_traits.setdefault(current_section, [])
                soul_def_traits[current_section].append(line)

        # 4. 读取 cognition-drafts/*.md，聚合各特质行
        drafts_dir = _soul_dir / "cognition-drafts"
        draft_traits: dict[str, list[str]] = {}
        for trait in trait_sections:
            draft_traits[trait] = []

        if drafts_dir.exists():
            for f in sorted(drafts_dir.glob("*.md")):
                try:
                    draft_text = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                current_draft_section = ""
                for line in draft_text.split("\n"):
                    line_lower = line.strip().lower()
                    if (
                        line_lower.startswith("## ")
                        and line_lower[3:].strip() in trait_sections
                    ):
                        current_draft_section = line_lower[3:].strip()
                    elif current_draft_section:
                        draft_traits.setdefault(current_draft_section, [])
                        draft_traits[current_draft_section].append(line)

        # 5. 构建逐特质 diff 表
        traits_diff: dict[str, dict[str, Any]] = {}
        drift_detected = False

        for trait in trait_sections:
            def_lines = soul_def_traits.get(trait, [])
            draft_lines_val = draft_traits.get(trait, [])

            def_set = set(def_lines)
            draft_set = set(draft_lines_val)

            added = sorted(draft_set - def_set)
            removed = sorted(def_set - draft_set)

            def_text = "\n".join(def_lines)
            draft_text_val = "\n".join(draft_lines_val)
            changed: list[str] = []
            if def_text != draft_text_val:
                changed = [
                    l for l in draft_lines_val
                    if l not in def_set
                ][:20]

            has_diff = bool(added or removed or changed)
            if has_diff:
                drift_detected = True

            traits_diff[trait] = {
                "has_diff": has_diff,
                "added_count": len(added),
                "removed_count": len(removed),
                "changed_count": len(changed),
                "added_lines": added[:10],
                "removed_lines": removed[:10],
                "changed_lines": changed[:10],
            }

        # 6. 可选 LLM 注释（仅在有漂移时调用以节约成本）
        llm_annotation = ""
        if drift_detected:
            try:
                from app.services.agent_harness_manager import agent_harness

                soul_reflect_prompt = _PROMPTS_DIR / "soul_reflect_v1.txt"
                diff_desc = json.dumps(
                    traits_diff, ensure_ascii=False, indent=2
                )

                if soul_reflect_prompt.exists():
                    result = await agent_harness.complete(
                        prompt=(
                            "<USER_CONTENT>\n"
                            + diff_desc
                            + "\n</USER_CONTENT>"
                        ),
                        system_prompt_path=str(soul_reflect_prompt),
                        expected_output_tokens=256,
                    )
                else:
                    inline_prompt = (
                        "你是一个认知档案分析师。请基于以下 SOUL 定义与现行草稿的"
                        "逐特质差异数据，指出最显著的变化并给出 ≤100 字的注释。"
                        "只描述变化方向，不评价好坏。"
                    )
                    result = await agent_harness.complete(
                        prompt=(
                            "<USER_CONTENT>\n"
                            + inline_prompt
                            + "\n\n"
                            + diff_desc
                            + "\n</USER_CONTENT>"
                        ),
                        expected_output_tokens=256,
                    )

                if result.get("success") and result.get("text"):
                    llm_annotation = result["text"][:500]
            except Exception as e:
                logger.warning(
                    "LLM annotation failed for reflect: %s", e
                )

        # 7. 写 drift 报告
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        report_path = _soul_dir / "reports" / f"drift-{today_str}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        report_lines = [
            f"# SOUL Drift Report — {today_str}",
            "",
            f"**SOUL**: `{soul_kb_id}`",
            f"**Drift Detected**: {drift_detected}",
            "",
            "## 逐特质差异",
            "",
        ]

        for trait in trait_sections:
            td = traits_diff.get(trait, {})
            report_lines.append(f"### {trait}")
            report_lines.append(f"- 新增行: {td.get('added_count', 0)}")
            report_lines.append(f"- 移除行: {td.get('removed_count', 0)}")
            report_lines.append(f"- 变更行: {td.get('changed_count', 0)}")
            if td.get("added_lines"):
                report_lines.append("- 新增示例:")
                for line_val in td["added_lines"][:5]:
                    report_lines.append(f"  + `{line_val}`")
            if td.get("removed_lines"):
                report_lines.append("- 移除示例:")
                for line_val in td["removed_lines"][:5]:
                    report_lines.append(f"  - `{line_val}`")
            report_lines.append("")

        if llm_annotation:
            report_lines.append("## LLM 注释")
            report_lines.append(f"\n{llm_annotation}\n")

        atomic_write_text(report_path, "\n".join(report_lines))

        # 8. 刷新 profile-summary
        try:
            from app.services.soul_profile import generate_profile_summary
            await generate_profile_summary(soul_kb_id)
        except Exception:
            pass

        return {
            "success": True,
            "report_path": str(report_path),
            "drift_detected": drift_detected,
            "traits_diff_summary": {
                trait: {
                    "has_diff": td["has_diff"],
                    "added_count": td["added_count"],
                    "removed_count": td["removed_count"],
                    "changed_count": td["changed_count"],
                }
                for trait, td in traits_diff.items()
            },
        }
    finally:
        lock.release()


# ═══════════════════════════════════════════════════════════════════
#  导出训练数据
# ═══════════════════════════════════════════════════════════════════

async def export_training_data(
    soul_kb_id: str,
    min_score: float = 4.0,
    limit: int = 1000,
) -> dict[str, Any]:
    """导出已批准的高质量记忆为 JSONL 训练数据。

    筛选 ``pas_score ≥ min_score`` 的 approved 记忆，
    导出到 ``training/export-<YYYYMMDD>-<min_score>.jsonl``。

    每行 JSON::

        {"question", "evidence_paths", "answer", "scores",
         "persona", "checkpoint_id", "export_time"}

    persona = ``soul-definition.md`` 前 500 字；
    checkpoint_id = 最新检查点 ID。

    Args:
        soul_kb_id: SOUL 知识库 ID。
        min_score: 最低 pas_score 阈值。
        limit: 最大导出条数。

    Returns:
        ``{"success": True, "export_path": str, "record_count": int,
           "min_score_applied": float}``。
    """
    _soul_dir = soul_kb_dir(soul_kb_id)

    # 读取 persona（soul-definition.md 前 500 字）
    soul_def_path = _soul_dir / "soul-definition.md"
    persona = ""
    if soul_def_path.exists():
        persona = soul_def_path.read_text(encoding="utf-8")[:500]

    # 最新检查点 ID
    checkpoints_dir = _soul_dir / "checkpoints"
    newest_checkpoint_id = ""
    if checkpoints_dir.exists():
        cp_files = sorted(
            [
                f for f in checkpoints_dir.glob("*.json")
                if f.name != "eval_prompt_hashes.json"
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if cp_files:
            newest_checkpoint_id = cp_files[0].stem

    now_iso = _now_iso()
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # 扫描 memories/*.md
    memories_dir = _soul_dir / "memories"
    records: list[dict[str, Any]] = []
    if memories_dir.exists():
        for f in sorted(memories_dir.glob("*.md")):
            if len(records) >= limit:
                break
            fm, body = _read_memory_full(f) or ({}, "")
            if not fm:
                continue
            if fm.get("status") != "approved":
                continue
            pas = fm.get("pas_score") or 0.0
            try:
                pas = float(pas)
            except (TypeError, ValueError):
                pas = 0.0
            if pas < min_score:
                continue

            answer_text = _memory_body_text(body, max_chars=5000)

            records.append({
                "question": fm.get("question", ""),
                "evidence_paths": fm.get("evidence_paths", []),
                "answer": answer_text,
                "scores": fm.get("scores", {}),
                "persona": persona,
                "checkpoint_id": newest_checkpoint_id,
                "export_time": now_iso,
            })

    # 写入
    training_dir = _soul_dir / "training"
    training_dir.mkdir(parents=True, exist_ok=True)
    min_label = str(min_score).replace(".", "_")
    export_path = training_dir / f"export-{today_str}-{min_label}.jsonl"

    with open(export_path, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "export_path": str(export_path),
        "record_count": len(records),
        "min_score_applied": min_score,
    }


# ═══════════════════════════════════════════════════════════════════
#  标记陈旧记忆（scope 变更后）
# ═══════════════════════════════════════════════════════════════════

async def mark_stale_scope(
    soul_kb_id: str, old_scope_hash: str
) -> int:
    """scope 变更后标记 doc_source 不在新 scope 中的记忆为 stale。

    读取 SOUL config 获取当前 kb_scope；
    遍历 ``memories/*.md`` 中 ``status=approved`` 的记忆，
    若其 ``doc_source`` 字段不在新 scope 中，
    则设置 ``stale: true``（原子写回）。

    Args:
        soul_kb_id: SOUL 知识库 ID。
        old_scope_hash: 旧 scope 的 hash（用于日志/幂等，实际比较用新 scope）。

    Returns:
        被标记为 stale 的记忆数量。
    """
    _soul_dir = soul_kb_dir(soul_kb_id)

    try:
        cfg = read_soul_config(soul_kb_id)
        new_scope = set(cfg.kb_scope) if cfg.kb_scope else set()
    except Exception:
        return 0

    memories_dir = _soul_dir / "memories"
    if not memories_dir.exists():
        return 0

    stale_count = 0
    for f in sorted(memories_dir.glob("*.md")):
        fm, body = _read_memory_full(f) or ({}, "")
        if not fm:
            continue
        if fm.get("status") != "approved":
            continue
        if fm.get("stale"):
            continue

        doc_source = fm.get("doc_source", "")
        if not doc_source:
            continue

        # 判断 doc_source 是否在 scope 中
        # scope 可能为 KB path、UUID 或 "*"（全库）
        in_scope = False
        for scope_item in new_scope:
            scope_item = scope_item.strip()
            if not scope_item:
                continue
            if scope_item == "*":
                in_scope = True
                break
            if (
                doc_source.startswith(scope_item)
                or scope_item in doc_source
            ):
                in_scope = True
                break

        if not in_scope:
            fm["stale"] = True
            new_content = _fmt_frontmatter(fm) + "\n" + body
            atomic_write_text(f, new_content)
            stale_count += 1

    return stale_count