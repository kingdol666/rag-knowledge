"""SOUL 画像模块 — 人格加载、画像摘要与风格分析。

加载 SOUL 知识库的五篇定义文档与配置，构造 persona bundle
（人格文档 + 已批准记忆摘要），并提供语言风格匹配与画像摘要生成。

依契约 §4 实现，依赖 soul_config 模块。
"""
from __future__ import annotations

import logging
import re
import string
from pathlib import Path
from typing import Any

import yaml

from app.services import soul_config
from app.services.agent_harness_manager import agent_harness
from app.services.kb_meditation_config import get_meditation_config
from app.services.storage_reader_service import storage_reader
from app.services.two_stage_search_service import two_stage_search_service
from app.utils.atomic_io import atomic_write_text

logger = logging.getLogger(__name__)

# ── 文档路径常量（相对于 SOUL KB 根） ──────────────────────────────────────

_DOC_SOUL_DEFINITION = "soul-definition.md"
_DOC_VALUES = "values.md"
_DOC_THINKING_STYLE = "thinking-style.md"
_DOC_MEMORY_CONVENTIONS = "memory-conventions.md"
_REPORT_PROFILE_SUMMARY = "reports/profile-summary.md"

_FALLBACK_CHARS = 500


# ── 文件读取辅助 ────────────────────────────────────────────────────────────

def _kb_doc_path(soul_kb_id: str, rel: str) -> str:
    """构造 SOUL KB 内文档的存储相对路径。"""
    kp = soul_config.resolve_soul_kb_path(soul_kb_id)
    if kp is None:
        raise ValueError(f"Not a soul KB: {soul_kb_id!r}")
    return f"{kp}/{rel}"


def _read_soul_doc(soul_kb_id: str, rel: str) -> str:
    """读取 SOUL KB 内某篇文档的正文。"""
    doc_path = _kb_doc_path(soul_kb_id, rel)
    return storage_reader.read_document_content(doc_path)


# ── load_profile ────────────────────────────────────────────────────────────

async def load_profile(soul_kb_id: str) -> dict[str, Any]:
    """加载 SOUL 知识库的完整画像。

    读取五篇定义文档 + 配置，返回字典包含所有人格定义内容。

    Args:
        soul_kb_id: KB UUID 或路径。

    Returns:
        ``{soul_kb_id, soul_def, values, thinking_style,
           memory_conventions, config: SoulConfig, is_template}``。
    """
    resolved = soul_config.resolve_soul_kb_path(soul_kb_id)
    if resolved is None:
        raise ValueError(f"Not a soul KB (soul- prefix required): {soul_kb_id!r}")

    cfg = soul_config.read_soul_config(soul_kb_id)

    return {
        "soul_kb_id": resolved,
        "soul_def": _read_soul_doc(soul_kb_id, _DOC_SOUL_DEFINITION),
        "values": _read_soul_doc(soul_kb_id, _DOC_VALUES),
        "thinking_style": _read_soul_doc(soul_kb_id, _DOC_THINKING_STYLE),
        "memory_conventions": _read_soul_doc(soul_kb_id, _DOC_MEMORY_CONVENTIONS),
        "config": cfg,
        "is_template": cfg.is_template,
    }


# ── build_persona_bundle ────────────────────────────────────────────────────

async def build_persona_bundle(
    soul_kb_id: str,
    query: str,
    max_memories: int = soul_config.MAX_MEMORIES_IN_BUNDLE,
) -> dict[str, Any]:
    """构造 persona bundle：人格文档检索结果 + 已批准记忆摘要。

    检索范围限定为 SOUL KB 自身（不检索外部知识库），使用两阶段搜索。
    同时扫描 ``memories/*.md``，筛选 status=approved 的记忆，
    按 learned_at 降序排列，取最多 ``max_memories`` 条生成摘要。

    Args:
        soul_kb_id: KB UUID 或路径。
        query: 检索查询文本。
        max_memories: 记忆摘要数量上限。

    Returns:
        ``{persona_docs: [{path, chunk_text, score}],
           memory_summaries: [str],
           doc_names: [str]}``。
    """
    resolved = soul_config.resolve_soul_kb_path(soul_kb_id)
    if resolved is None:
        raise ValueError(f"Not a soul KB (soul- prefix required): {soul_kb_id!r}")

    # ── 两阶段检索（限定 SOUL KB 自身） ──
    search_result = two_stage_search_service.search(
        query=query,
        kb_id=resolved,
        stage2_top_k=10,
    )

    persona_docs: list[dict[str, Any]] = []
    doc_names: list[str] = []
    seen_docs: set[str] = set()

    # BUGFIX: two_stage_search_service.search() 返回 {"stage2": {"results": [...]}},
    # 且 results 为扁平 chunk 列表 [{"content", "doc_path", "score", ...}]（非
    # 嵌套 {"chunks": [...]} 结构）。原代码: ①键路径读错(顶层 results) ②按嵌套结构
    # 遍历 → persona_docs/doc_names 恒空（soul_qdcvr_ask/soul_ask 的 persona_bundle
    # 恒为空, PAS 人格注入失效）
    results = search_result.get("stage2", {}).get("results", [])
    if not results:
        # 兼容旧结构/降级: 直接键或顶层 results
        results = search_result.get("results", []) or []
    for item in results:
        doc_path = item.get("doc_path", "")
        chunks = item.get("chunks")
        if isinstance(chunks, list) and chunks:
            # 嵌套结构（兼容未来版本）
            for ch in chunks:
                persona_docs.append({
                    "path": ch.get("path", doc_path),
                    "chunk_text": ch.get("chunk_text", ""),
                    "score": ch.get("score", 0.0),
                })
                if doc_path and doc_path not in seen_docs:
                    seen_docs.add(doc_path)
                    doc_names.append(doc_path)
        else:
            # 扁平 chunk 结构（当前版本实际返回）
            persona_docs.append({
                "path": doc_path,
                "chunk_text": item.get("content", ""),
                "score": item.get("score", 0.0),
            })
            if doc_path and doc_path not in seen_docs:
                seen_docs.add(doc_path)
                doc_names.append(doc_path)

    # 兜底: 检索零命中时无条件注入 4 宪法文档（新人格未训练时宪法文档与领域 query
    # 无词法重叠 → stage1 零候选 → bundle 空。人格注入主体虽走 load_profile 直读
    # 宪法文档, 但 bundle 空会导致合成上下文缺人格文档 chunk）
    if not persona_docs:
        try:
            kb_dir = soul_config.soul_kb_dir(soul_kb_id)
            for doc_name in ("soul-definition.md", "values.md", "thinking-style.md", "memory-conventions.md"):
                p = kb_dir / doc_name
                if not p.exists():
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    persona_docs.append({
                        "path": f"{resolved}/{doc_name}",
                        "chunk_text": text[:2000],
                        "score": 0.0,
                    })
                    if doc_name not in seen_docs:
                        seen_docs.add(doc_name)
                        doc_names.append(f"{resolved}/{doc_name}")
        except Exception as e:
            logger.warning("persona bundle fallback failed for %s: %s", soul_kb_id, e)

    # ── 记忆检索(语义相关性排序, 非简单 mtime) ──
    # 修复: 原来按 learned_at 降序取最近记忆, 但用户问"高分子聚合"时
    # 可能注入无关记忆。改为向量检索已批准记忆 → 按相关性取 top-N。
    kb_dir = soul_config.soul_kb_dir(soul_kb_id)
    memories_dir = kb_dir / "memories"
    memory_summaries: list[str] = []

    if memories_dir.exists():
        # 策略: 先向量检索 memories/ 下的文档(已批准记忆已索引为 KB 文档),
        # 按相关性取 top; 若向量检索不足, 补充高质量记忆(按评分降序)
        relevant_memories: list[dict[str, Any]] = []

        # 向量检索: 在 SOUL KB 内搜索, 会命中 memories/ 路径的文档
        try:
            mem_search = two_stage_search_service.search(
                query=query, kb_id=resolved, stage2_top_k=max_memories * 2,
            )
            mem_results = mem_search.get("stage2", {}).get("results", [])
            for item in mem_results:
                doc_path = item.get("doc_path", "")
                if "/memories/" not in doc_path:
                    continue
                relevant_memories.append({
                    "score": item.get("score", 0.0),
                    "content": item.get("content", "")[:300],
                    "path": doc_path,
                })
        except Exception as e:
            logger.warning("memory vector search failed for %s: %s", soul_kb_id, e)

        # 如果向量检索不足, 回退到文件扫描(按评分降序)
        if len(relevant_memories) < max_memories:
            mem_files = sorted(
                memories_dir.glob("*.md"),
                key=lambda p: p.stat().st_mtime, reverse=True)
            for mf in mem_files:
                if len(relevant_memories) >= max_memories * 2:
                    break
                try:
                    raw = mf.read_text(encoding="utf-8")
                    frontmatter = _parse_yaml_frontmatter(raw)
                    if frontmatter is None or frontmatter.get("status") != "approved":
                        continue
                    # 避免重复(向量检索已命中的)
                    mem_name = mf.stem
                    if any(mem_name in r.get("path", "") for r in relevant_memories):
                        continue
                    scores = frontmatter.get("scores", {})
                    mean_score = sum(scores.values()) / max(len(scores), 1)
                    body_text = _extract_body_after_frontmatter(raw)
                    relevant_memories.append({
                        "score": mean_score,
                        "content": body_text[:300],
                        "path": str(mf),
                        "question": frontmatter.get("question", ""),
                    })
                except Exception:
                    continue

        # 按分数(向量相似度或评分均值)降序
        relevant_memories.sort(key=lambda m: m.get("score", 0), reverse=True)

        for mem in relevant_memories[:max_memories]:
            content = mem.get("content", "").replace("\n", " ")[:250]
            memory_summaries.append(content)

    # ── 知识综合注入(训练蒸馏的结构化经验) ──
    synth_path = kb_dir / "knowledge-synthesis.md"
    if synth_path.exists():
        try:
            synth_text = synth_path.read_text(encoding="utf-8")
            if synth_text.strip():
                memory_summaries.insert(0, f"[知识经验综合]\n{synth_text[:800]}")
        except Exception:
            pass

    return {
        "persona_docs": persona_docs,
        "memory_summaries": memory_summaries,
        "doc_names": doc_names,
    }


# ── YAML frontmatter 解析 ──────────────────────────────────────────────────

def _parse_yaml_frontmatter(text: str) -> dict[str, Any] | None:
    """从 Markdown 文本中提取 YAML frontmatter（``---`` 包裹部分）。"""
    text = text.strip()
    if not text.startswith("---"):
        return None
    # 查找结束的 ---
    end_idx = text.find("---", 3)
    if end_idx == -1:
        return None
    yaml_block = text[3:end_idx].strip()
    if not yaml_block:
        return None
    try:
        parsed = yaml.safe_load(yaml_block)
        if isinstance(parsed, dict):
            return parsed
    except yaml.YAMLError:
        pass
    return None


def _extract_body_after_frontmatter(text: str) -> str:
    """提取 frontmatter 之后的正文部分。"""
    text = text.strip()
    if not text.startswith("---"):
        return text
    end_idx = text.find("---", 3)
    if end_idx == -1:
        return text
    return text[end_idx + 3:].strip()


# ── language_style_phrases ──────────────────────────────────────────────────

def language_style_phrases(soul_kb_id: str) -> list[str]:
    """从 ``soul-definition.md`` 中解析 ``## language-style`` 章节，
    返回每行一个短语的列表。

    跳过空行和以 ``#`` 开头的子标题行。

    Args:
        soul_kb_id: KB UUID 或路径。

    Returns:
        短语字符串列表。
    """
    soul_def = _read_soul_doc(soul_kb_id, _DOC_SOUL_DEFINITION)
    if not soul_def:
        return []

    # 定位 ## language-style 章节
    lines = soul_def.split("\n")
    in_section = False
    phrases: list[str] = []

    for line in lines:
        stripped = line.strip()
        # 检测章节标题
        if stripped.startswith("## ") and not stripped.startswith("### "):
            if stripped.lower().startswith("## language-style"):
                in_section = True
            else:
                in_section = False
                # 不要在这里 break，因为 language-style 可能不是最后一个章节；
                # 继续扫描但不再收集
            continue
        if not in_section:
            continue
        # 子标题结束本小节吗？不——contract 说 one phrase per line。
        # 子标题（###）视为分隔，跳过
        if stripped.startswith("#"):
            continue
        if stripped:
            phrases.append(stripped)

    return phrases


# ── count_style_matches ─────────────────────────────────────────────────────

def count_style_matches(answer: str, phrases: list[str]) -> int:
    """统计 answer 中包含多少个风格短语（标准化后子串匹配）。

    标准化规则：去除首尾空白、标点符号后，对每个短语做子串检查。

    Args:
        answer: 待检查的回答文本。
        phrases: 风格短语列表。

    Returns:
        匹配的短语数量。
    """
    if not answer or not phrases:
        return 0

    normalized = _normalize_text(answer)
    count = 0
    for phrase in phrases:
        np = _normalize_text(phrase)
        if np and np in normalized:
            count += 1
    return count


def _normalize_text(text: str) -> str:
    """标准化文本：去除标点与空白，用于子串匹配。"""
    # 去除 ASCII 标点
    text = text.translate(str.maketrans("", "", string.punctuation))
    # 去除中文常见标点与空白（Unicode 转义避免引号冲突）
    text = re.sub(
        r"[\u3001\u3002\uff0c\uff0e\u300d\u300e\uff01\uff1f\uff1b\uff1a"
        r"\u201c\u201d\u2018\u2019\uff08\uff09\u3010\u3011\u300a\u300b\s]",
        "", text,
    )
    # 合并多余空白（可能残留）
    text = re.sub(r"\s+", "", text)
    return text.strip()


# ── generate_profile_summary ────────────────────────────────────────────────

_SYSTEM_PROMPT_PATH = str(
    Path(__file__).resolve().parent / "prompts" / "soul_profile_summary_v1.txt"
)


async def generate_profile_summary(soul_kb_id: str) -> str:
    """调用 agent_harness.complete() 生成人格画像摘要（≤200 字），
    原子写入 ``reports/profile-summary.md``。

    若 LLM 调用失败，返回空字符串并记录 warning 日志。

    Args:
        soul_kb_id: KB UUID 或路径。

    Returns:
        生成的摘要文本；失败时返回 ``""``。
    """
    resolved = soul_config.resolve_soul_kb_path(soul_kb_id)
    if resolved is None:
        return ""

    # 读取五篇定义文档构造 prompt
    try:
        profile = await load_profile(soul_kb_id)
    except Exception as e:
        logger.warning("Failed to load profile for %s: %s", soul_kb_id, e)
        return ""

    user_content = (
        "<USER_CONTENT>\n"
        f"## soul-definition\n{profile['soul_def'][:3000]}\n\n"
        f"## values\n{profile['values'][:2000]}\n\n"
        f"## thinking-style\n{profile['thinking_style'][:2000]}\n\n"
        f"## memory-conventions\n{profile['memory_conventions'][:2000]}\n"
        "</USER_CONTENT>"
    )

    # 获取冥想配置中的 harness 设置
    try:
        med_cfg = get_meditation_config(resolved)
    except Exception:
        med_cfg = {}
    harness = med_cfg.get("harness") or "omp"
    model = med_cfg.get("model") or ""

    kb_config: dict[str, Any] = {"harness": harness}
    if model:
        kb_config["model"] = model

    try:
        result = await agent_harness.complete(
            prompt=user_content,
            kb_config=kb_config,
            result_schema=None,
            system_prompt_path=_SYSTEM_PROMPT_PATH,
            timeout_sec=300,
            expected_output_tokens=256,
        )
    except Exception as e:
        logger.warning("agent_harness.complete failed for %s: %s", soul_kb_id, e)
        return ""

    if not result.get("success"):
        logger.warning(
            "generate_profile_summary failed for %s: error=%s harness=%s",
            soul_kb_id,
            result.get("error") or "unknown",
            result.get("harness") or "?",
        )
        return ""

    summary_text = (result.get("text") or "").strip()
    if not summary_text:
        return ""

    # 原子写 reports/profile-summary.md
    summary_path = _kb_doc_path(soul_kb_id, _REPORT_PROFILE_SUMMARY)
    report_full = soul_config.soul_kb_dir(soul_kb_id) / _REPORT_PROFILE_SUMMARY
    atomic_write_text(report_full, summary_text)

    return summary_text


# ── read_profile_summary ────────────────────────────────────────────────────

def read_profile_summary(soul_kb_id: str) -> str:
    """读取缓存的画像摘要（``reports/profile-summary.md``）。

    若缓存文件缺失，回退为 soul-config 摘要 + soul-definition.md 前
    ``_FALLBACK_CHARS`` 字符的组合。

    Args:
        soul_kb_id: KB UUID 或路径。

    Returns:
        画像摘要文本。
    """
    summary_rel = _kb_doc_path(soul_kb_id, _REPORT_PROFILE_SUMMARY)
    content = storage_reader.read_document_content(summary_rel)
    if content and content.strip():
        return content.strip()

    # 回退：读取 soul-config + soul-definition 前 500 字
    try:
        cfg = soul_config.read_soul_config(soul_kb_id)
    except ValueError:
        cfg = None

    soul_def = _read_soul_doc(soul_kb_id, _DOC_SOUL_DEFINITION)
    fallback = ""
    if cfg is not None:
        fallback += (
            f"scope: {cfg.kb_scope}, "
            f"is_template: {cfg.is_template}, "
            f"route_weight: {cfg.route_weight}, "
            f"domain_labels: {cfg.domain_labels}, "
            f"supported_task_types: {cfg.supported_task_types}\n"
        )
    if soul_def:
        fallback += soul_def[:_FALLBACK_CHARS]
    return fallback.strip()