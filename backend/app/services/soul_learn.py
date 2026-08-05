"""SOUL 学习模块 — 问题生成、自答、评估、蒸馏、增量学习。

实现契约 §5 全部函数：generate_questions / self_answer / eval_answer / distill /
check_budget / deduct_cost / learn_incremental / learn_all / learn_docs / calibrate。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.utils.paths import get_storage_root
from app.utils.atomic_io import atomic_write_text
from app.utils.safe_paths import resolve_within
from app.services.agent_harness_manager import agent_harness
from app.services.storage_reader_service import storage_reader
from app.services.two_stage_search_service import two_stage_search_service
from app.services.graph_service import graph_service
from app.services.experience_service import experience_service
from app.services.kb_meditation_config import (
    get_meditation_config,
    update_meditation_config,
)
from app.models.experience_models import (
    ExperienceCreate,
    ExperienceCategory,
    ExperienceSeverity,
    ExperienceResult,
)
from app.services.soul_config import (
    SOUL_PREFIX,
    SOUL_RETRIEVAL_SCORE_THRESHOLD,
    PER_SOUL_LOCK_TIMEOUT,
    SOUL_BUDGET_USD_PER_RUN,
    SoulConfig,
    resolve_soul_kb_path,
    soul_kb_dir,
    read_soul_config,
    validate_scope,
    get_soul_lock,
    list_soul_kbs,
    is_template_kb,
)

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_STORAGE_ROOT = get_storage_root()

# ── 模块级预算状态 ──────────────────────────────────────────────────────
_budget_state: dict[str, dict[str, Any]] = {}
_budget_lock = asyncio.Lock()

# ── 全局内容去重 (learn_all 跨 SOUL) ────────────────────────────────────
_global_content_hashes: set[str] = set()
_dedup_lock = asyncio.Lock()

# ── eval prompt hash 缓存 ───────────────────────────────────────────────
_eval_prompt_hash_cache: dict[str, str] = {}

# ── 常量 ────────────────────────────────────────────────────────────────
_MAX_CALLS_PER_RUN = 30
_MAX_DUAL_JUDGE_PER_RUN = 5
SOUL_QUESTIONS_PROMPT_FILE = "soul_learn_questions_v1.txt"
SOUL_EVAL_PROMPT_FILE = "soul_eval_v1.txt"

# ── 关键词分类器正则（契约 §5）──────────────────────────────────────────
_KEYWORD_RULES: list[tuple[str, str]] = [
    (r"是什么|定义|参数|数据|多少|怎么.*算|如何计算", "fact"),
    (r"原理|机制|区别|为什么|为何|原因|如何.*工作", "concept"),
    (r"对比|关系|与.*相关|异同|关联|联系", "cross_doc"),
    (r"挑战|难点|局限|瓶颈|不足|缺陷|问题.*解决", "challenge"),
]

async def _call_cb(cb, payload):
    """调用 progress_cb(兼容同步/异步回调, 如暂停门 gated_progress_cb)。"""
    if cb is None:
        return
    r = cb(payload)
    if asyncio.iscoroutine(r):
        await r




def _now_iso() -> str:
    """当前 UTC ISO8601 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _norm_path(p: str) -> str:
    """统一路径分隔符为 /。"""
    return (p or "").replace("\\", "/")


def _content_sha256(text: str) -> str:
    """文档内容的 SHA256 前 12 位（用于去重）。"""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════
# §5.1  q_hash
# ═══════════════════════════════════════════════════════════════════════════


def q_hash(q_text: str, doc_path: str, q_type: str) -> str:
    """生成问题唯一哈希：sha256(f"{q_text[:100]}|{doc_path}|{q_type}")[:12]。

    Args:
        q_text: 问题文本。
        doc_path: 来源文档路径。
        q_type: 问题类型（fact/concept/cross_doc/challenge）。

    Returns:
        12 字符十六进制哈希。
    """
    raw = f"{q_text[:100]}|{_norm_path(doc_path)}|{q_type}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════
# §5.2  关键词分类器
# ═══════════════════════════════════════════════════════════════════════════


def _keyword_classify(q_text: str) -> str | None:
    """轻量关键词分类器：返回命中类型或 None。

    按优先级匹配：fact → concept → cross_doc → challenge。
    若多条规则同时命中，返回第一条匹配的类型。
    未命中任何规则返回 None，表示无关键词证据。
    """
    for pattern, qtype in _KEYWORD_RULES:
        if re.search(pattern, q_text):
            return qtype
    return None


# ═══════════════════════════════════════════════════════════════════════════
# §5.3  generate_questions
# ═══════════════════════════════════════════════════════════════════════════


def _build_questions_prompt_inline(doc_content: str, num: int, mastery: dict | None = None, doc_path: str = "") -> str:
    """内联构建问题生成提示词（无独立 prompt 文件时使用）。

    v2(元认知好奇心): 注入该主题掌握画像 + 动态四层比例(近发展区),
    已知记忆摘要防重复(认知伙伴原则)。无 mastery 时回退静态四层。
    """
    mix = None
    meta_block = ""
    if mastery:
        from app.services.soul_curiosity import (
            DEFAULT_MIX, build_mastery_context, compute_question_mix,
            mix_to_instruction,
        )
        mix = compute_question_mix(mastery, doc_path)
        meta_block = build_mastery_context(mastery, doc_path)
    mix_text = mix_to_instruction(mix) if mastery else (
        "- fact（事实层）：是什么、定义、参数、数据、多少（约 30%）\n"
        "- concept（概念层）：原理、机制、区别、为什么（约 30%）\n"
        "- cross_doc（跨文档层）：对比、关系、与…相关、异同（约 20%）\n"
        "- challenge（挑战层）：挑战、难点、局限、瓶颈（约 20%，请重点倾斜此类）"
    )
    return f"""你是一位严谨的知识工程师。请阅读以下文档内容，生成 {num} 个高质量学习问题。

{meta_block}

问题类型要求（四层，按以下比例分配）：
{mix_text}

要求：
1. 问题必须基于文档内容，不可凭空编造
2. 每个问题独立、具体、可验证
3. 难度略高于当前掌握水平(最近发展区), 优先覆盖未知与薄弱之处
4. 输出 JSON 数组，每项含 q_text 和 q_type 字段

<USER_CONTENT>
{doc_content}
</USER_CONTENT>

请输出 JSON：
{{"questions": [{{"q_text": "...", "q_type": "fact"}}, ...]}}"""


async def generate_questions(doc_path: str, num: int = 6,
                             mastery: dict | None = None) -> list[dict]:
    """为指定文档生成学习问题(补天好奇心引擎 v2)。

    流程：
    1. 读取文档内容
    2. 若 prompts/soul_learn_questions_v1.txt 存在，用作 system prompt；否则内联构建
    3. 调用 complete() 生成问题（result_schema: {{"questions": [{{"q_text","q_type"}}]}}）
    4. 关键词分类器交叉校验 LLM 标签
    5. 按 q_hash 去重 + 新奇度过滤(与已批准记忆重复的问题丢弃)

    v2 增强(论文 arXiv:2604.25648 元认知好奇心框架):
    - mastery 画像 → 动态四层比例(近发展区 ZPD) + 元认知上下文注入
    - 已知记忆摘要 → LLM 生成时避开重复 + 规则层 novelty_filter 兜底

    Args:
        doc_path: 文档相对路径。
        num: 生成问题数，默认 6。
        mastery: 元认知掌握画像(可选, 缺省 = 静态四层, 兼容旧行为)。

    Returns:
        [{{q_text, q_type, q_hash}}, ...]
    """
    content = storage_reader.read_document_content(doc_path, max_chars=50000)
    if not content:
        logger.warning("generate_questions: empty doc %s", doc_path)
        return []

    system_prompt_path = _PROMPTS_DIR / SOUL_QUESTIONS_PROMPT_FILE
    if system_prompt_path.exists():
        spath = str(system_prompt_path)
    else:
        spath = None

    if spath:
        prompt = (
            f"请为以下文档生成 {num} 个学习问题。输出 JSON 格式。\n\n"
            f"<USER_CONTENT>\n{content}\n</USER_CONTENT>"
        )
    else:
        prompt = _build_questions_prompt_inline(content, num, mastery, doc_path)

    result_schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "q_text": {"type": "string"},
                        "q_type": {"type": "string"},
                    },
                    "required": ["q_text", "q_type"],
                },
            }
        },
        "required": ["questions"],
    }

    result = await agent_harness.complete(
        prompt=prompt,
        result_schema=result_schema,
        system_prompt_path=spath,
        timeout_sec=120,
        expected_output_tokens=1024,
    )

    if not result.get("success"):
        logger.warning("generate_questions: complete() failed: %s", result.get("error"))
        return []

    parsed = result.get("parsed")
    raw_questions: list[dict] = []
    if isinstance(parsed, dict):
        if isinstance(parsed.get("questions"), list):
            raw_questions = parsed["questions"]
        elif parsed.get("q_text"):
            # 模型偶发输出单条 question dict(损坏/截断时扫描分支产物)
            raw_questions = [parsed]
    elif isinstance(parsed, list):
        raw_questions = parsed

    if not raw_questions:
        return []

    # 交叉校验 + 去重
    seen: set[str] = set()
    out: list[dict] = []
    for item in raw_questions:
        q_text = str(item.get("q_text", "")).strip()
        llm_type = str(item.get("q_type", "fact")).strip()
        if not q_text:
            continue

        # 关键词分类器交叉校验
        kw_type = _keyword_classify(q_text)
        if kw_type and kw_type != llm_type:
            q_type = kw_type
        else:
            q_type = llm_type
        # 标准化类型名
        if q_type not in ("fact", "concept", "cross_doc", "challenge"):
            q_type = "fact"

        h = q_hash(q_text, doc_path, q_type)
        if h in seen:
            continue
        seen.add(h)

        # 新奇度过滤(认知伙伴原则): 与已批准记忆高度重叠的问题丢弃,
        # 避免重复学习(论文: AI 不应成为认知捷径)
        if mastery:
            from app.services.soul_curiosity import novelty_filter
            known = mastery.get("known_questions") or []
            if known and not novelty_filter(q_text, known):
                logger.debug("novelty_filter dropped: %s", q_text[:60])
                continue

        out.append({"q_text": q_text, "q_type": q_type, "q_hash": h})

    return out[:num]


# ═══════════════════════════════════════════════════════════════════════════
# §5.4  self_answer
# ═══════════════════════════════════════════════════════════════════════════


def _search_scope_ids(soul_kb_id: str, kb_scope: list[str]) -> list[str] | None:
    """解析检索范围 KB ID 列表。

    - kb_scope 空 → 仅 soul KB 自身
    - 含 "*" → None(全库检索,由检索层展开为全部集合)
    - 否则 → 显式公开库列表
    """
    if "*" in kb_scope:
        return None
    if not kb_scope:
        soul_path = resolve_soul_kb_path(soul_kb_id)
        if soul_path:
            return [soul_path]
        return []
    return [s for s in kb_scope if not s.startswith(SOUL_PREFIX)]


def _merge_graph_neighbors_for_chunks(
    chunks: list[dict], doc_paths: list[str], limit: int = 20,
    allowed_prefixes: list[str] | None = None,
) -> list[dict]:
    """将图谱邻居按 doc_path 合并到 chunk 列表（同路径只保留一条关联记录）。

    allowed_prefixes: 允许的 KB 前缀(如 kb_scope),None=不限。
    图谱邻居可能跨库,超出检索范围的邻居必须过滤(多 SOUL 隔离,AC22)。
    """
    merged: dict[str, dict] = {}
    for c in chunks:
        dp = _norm_path(c.get("doc_path", ""))
        merged.setdefault(dp, c)

    for dp in doc_paths:
        try:
            neighbors = graph_service.get_related_documents(dp, limit=limit)
        except Exception as e:
            logger.debug("get_related_documents failed for %s: %s", dp, e)
            continue
        for nb in neighbors:
            nb_path = _norm_path(nb.get("path", ""))
            if not nb_path or nb_path in merged:
                continue
            if allowed_prefixes is not None:
                kb_of = nb_path.split("/", 1)[0]
                if not any(kb_of == a.strip("/") for a in allowed_prefixes):
                    continue
            # 图谱邻居无 chunk_text，构造一个标记条(尝试读真实内容,失败用文件名)
            neighbor_text = nb.get("name", nb_path)
            try:
                from app.services.storage_reader_service import storage_reader
                real = storage_reader.read_document_content(nb_path, max_chars=800)
                if real:
                    neighbor_text = real
            except Exception:
                pass
            merged[nb_path] = {
                "doc_path": nb_path,
                "chunk_text": neighbor_text,
                "score": float(nb.get("relevance", nb.get("weight", 0.3))),
                "source": "graph_neighbor",
            }

    # 按 doc_path 稳定排序
    return sorted(merged.values(), key=lambda x: x.get("doc_path", ""))


def _build_self_answer_prompt(q_text: str, chunks: list[dict]) -> str:
    """构建自答 prompt：基于 chunk 作答，带 [path] 锚点引用。"""
    chunk_lines: list[str] = []
    for i, c in enumerate(chunks):
        path = _norm_path(c.get("doc_path", "unknown"))
        text = str(c.get("chunk_text", c.get("content", "")))[:2000]
        score = c.get("score", 0)
        chunk_lines.append(
            f"[{i}] 来源: {path}  相似度: {score:.3f}\n{text}"
        )
    chunks_block = "\n\n---\n\n".join(chunk_lines)

    return (
        "你是一位严谨的知识工程师。请基于以下检索到的文档片段回答问题。\n\n"
        "规则：\n"
        "1. 答案必须引用来源，使用 [path] 格式标注锚点\n"
        "2. 如果检索片段不足以回答，请明确说明\n"
        "3. 不要编造片段中不存在的信息\n\n"
        "<USER_CONTENT>\n"
        f"# 问题\n{q_text}\n\n"
        f"# 检索片段\n{chunks_block}\n"
        "</USER_CONTENT>\n\n"
        '请用 JSON 格式回答：{{"answer_text": "...", "citations": [...]}}'
    )


async def self_answer(
    q: dict, soul_kb_id: str, kb_scope: list[str]
) -> dict:
    """自答：检索知识库 → 图谱扩展 → 前置门 → LLM 合成答案。

    Args:
        q: 问题 dict，含 q_text / q_type / q_hash。
        soul_kb_id: 当前 SOUL KB ID。
        kb_scope: 范围 KB ID 列表。

    Returns:
        - 通过：{{"answer_text", "citations": [{{path, chunk_text, score}}],
          "evidence_paths": [str], "retrieval_pass": True}}
        - 未通过：{{"retrieval_pass": False}}
    """
    q_text = q.get("q_text", "")

    scope_ids = _search_scope_ids(soul_kb_id, kb_scope)
    if scope_ids is None:
        # 全库(通配符 *): 跨库均衡检索,不限库
        search_kwargs: dict[str, Any] = {"balance_kbs": True}
    else:
        if not scope_ids:
            # 无有效检索范围 → 仅 soul KB
            soul_path = resolve_soul_kb_path(soul_kb_id)
            if soul_path:
                scope_ids = [soul_path]

        # 确定检索策略: 多库逐库检索后合并(库间无污染)
        if len(scope_ids) == 1:
            search_kwargs = {"kb_id": scope_ids[0]}
        else:
            search_kwargs = {"balance_kbs": True}

    search_kwargs.setdefault("score_threshold", SOUL_RETRIEVAL_SCORE_THRESHOLD)

    try:
        if scope_ids is not None and len(scope_ids) > 1:
            # 多库: 每个 scope 库单独检索,按 score 降序合并去重
            merged_raw: list[dict] = []
            for kid in scope_ids:
                try:
                    rr = two_stage_search_service.search(
                        query=q_text, kb_id=kid, **search_kwargs)
                except Exception:
                    continue
                merged_raw.extend(rr.get("stage2", {}).get("results", []))
            seen_pairs: set[tuple] = set()
            results_raw = []
            for r in sorted(merged_raw, key=lambda x: x.get("score", 0), reverse=True):
                key = (r.get("doc_path", ""), (r.get("content") or "")[:80])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                results_raw.append(r)
        else:
            search_result = two_stage_search_service.search(query=q_text, **search_kwargs)
            results_raw = search_result.get("stage2", {}).get("results", [])
    except Exception as e:
        logger.error("self_answer: search failed: %s", e)
        return {"retrieval_pass": False}

    # 归一化为统一 chunk 格式含 chunk_text
    chunks: list[dict] = []
    for r in results_raw:
        chunks.append({
            "doc_path": r.get("doc_path", ""),
            "chunk_text": r.get("content", ""),
            "score": r.get("score", 0.0),
        })

    # 前 5 高分 chunk 的 doc_path 去重，用于图谱扩展
    top_doc_paths = list(dict.fromkeys(
        c["doc_path"] for c in sorted(chunks, key=lambda x: x["score"], reverse=True)[:5]
        if c["doc_path"]
    ))

    # 图谱邻居合并(仅限 kb_scope 内,多 SOUL 隔离 AC22)
    chunks = _merge_graph_neighbors_for_chunks(
        chunks, top_doc_paths, allowed_prefixes=scope_ids)

    # 前置门：最高分 chunk < SOUL_RETRIEVAL_SCORE_THRESHOLD
    max_score = max((c["score"] for c in chunks), default=0.0)
    if max_score < SOUL_RETRIEVAL_SCORE_THRESHOLD:
        # 写 gaps.md
        _append_gap(soul_kb_id, q.get("q_hash", ""), q.get("doc_path", ""),
                    "retrieval_failure", f"similarity_score={max_score:.3f}")
        return {"retrieval_pass": False}

    # 调用 LLM 合成答案(result_schema 使带 prose 前缀的 JSON 也能被解析)
    prompt = _build_self_answer_prompt(q_text, chunks)
    result = await agent_harness.complete(
        prompt=prompt,
        result_schema={
            "answer_text": str,
            "citations": [{"path": str, "chunk_text": str, "score": float}],
        },
        timeout_sec=120,
        expected_output_tokens=1024,
    )

    if not result.get("success"):
        logger.warning("self_answer: complete() failed: %s", result.get("error"))
        return {"retrieval_pass": False}

    parsed = result.get("parsed", {})
    if isinstance(parsed, str):
        answer_text = parsed
        citations: list[dict] = []
    elif isinstance(parsed, dict):
        answer_text = str(parsed.get("answer_text", parsed.get("text", "")))
        citations = parsed.get("citations", [])
    else:
        answer_text = result.get("text", "")
        citations = []

    # 收集 evidence_paths（去重）— 兼容 citations 为 [{path,...}] 或 ["path",...]
    def _cit_path(c):
        if isinstance(c, dict):
            return c.get("path", c.get("doc_path", ""))
        return str(c)
    evidence_paths = list(dict.fromkeys(
        _norm_path(_cit_path(c)) for c in citations if _cit_path(c)
    ))
    # 过滤掉非路径形态的引用(如 [6] 序号引用/纯文件名);空则回退到检索高分 chunk 路径,
    # 保证 eval 代码接地性有可校验证据(LLM 偶发用序号而非 [path] 锚点)
    def _looks_like_path(p: str) -> bool:
        return ("/" in p or "\\" in p) and not p.strip().isdigit()
    path_like = [p for p in evidence_paths if _looks_like_path(p)]
    if not path_like and chunks:
        path_like = list(dict.fromkeys(
            _norm_path(c.get("doc_path", "")) for c in chunks if c.get("doc_path")
        ))[:3]
    evidence_paths = path_like

    return {
        "answer_text": answer_text,
        "citations": citations,
        "evidence_paths": evidence_paths,
        "retrieval_pass": True,
    }


def _append_gap(
    soul_kb_id: str, qh: str, doc_path: str, reason: str, detail: str
) -> None:
    """向 questions/gaps.md 追加一行 TSV。"""
    try:
        sdir = soul_kb_dir(soul_kb_id)
        gaps_dir = sdir / "questions"
        gaps_dir.mkdir(parents=True, exist_ok=True)
        gap_line = f"{_now_iso()}\t{qh}\t{_norm_path(doc_path)}\t{reason}\t{detail}\n"
        with open(str(gaps_dir / "gaps.md"), "a", encoding="utf-8") as f:
            f.write(gap_line)
    except Exception as e:
        logger.warning("_append_gap failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════
# §5.5  eval_answer
# ═══════════════════════════════════════════════════════════════════════════


def _eval_prompt_hash(prompt_version: str) -> str:
    """计算 eval prompt 文件的 SHA256 前 12 位。"""
    if prompt_version in _eval_prompt_hash_cache:
        return _eval_prompt_hash_cache[prompt_version]

    fname = f"{prompt_version}.txt" if not prompt_version.endswith(".txt") else prompt_version
    ppath = _PROMPTS_DIR / fname
    if not ppath.exists():
        return ""
    h = hashlib.sha256(ppath.read_bytes()).hexdigest()[:12]
    _eval_prompt_hash_cache[prompt_version] = h
    return h


def _check_prompt_changed(soul_kb_id: str, prompt_version: str) -> bool:
    """比对 checkpoints/eval_prompt_hashes.json，返回 prompt 是否变更。"""
    try:
        sdir = soul_kb_dir(soul_kb_id)
        cp_dir = sdir / "checkpoints"
        cp_dir.mkdir(parents=True, exist_ok=True)
        hashes_path = cp_dir / "eval_prompt_hashes.json"
        current_hash = _eval_prompt_hash(prompt_version)

        stored: dict[str, str] = {}
        if hashes_path.exists():
            stored = json.loads(hashes_path.read_text(encoding="utf-8"))
        old_hash = stored.get(prompt_version, "")
        if old_hash and old_hash != current_hash:
            # 更新记录
            stored[prompt_version] = current_hash
            atomic_write_text(hashes_path, json.dumps(stored, ensure_ascii=False, indent=2))
            return True
        if not old_hash:
            stored[prompt_version] = current_hash
            atomic_write_text(hashes_path, json.dumps(stored, ensure_ascii=False, indent=2))
        return False
    except Exception as e:
        logger.warning("_check_prompt_changed failed: %s", e)
        return False


async def eval_answer(
    q: dict,
    a: dict,
    evidence_paths: list[str],
    soul_kb_id: str,
    prompt_version: str = "soul_eval_v1",
) -> dict:
    """评估答案质量：代码接地性 × LLM 四维评分 + 双判官。

    Args:
        q: 问题 dict（含 q_text / q_hash / q_type）。
        a: 答案 dict（含 answer_text / citations）。
        evidence_paths: 证据文档路径列表。
        soul_kb_id: SOUL KB ID。
        prompt_version: eval prompt 文件名（不含扩展名）。

    Returns:
        {{
            "scores": {{groundedness, completeness, coherence, info_gain}},
            "pas_score": float|None,
            "eval_prompt_version": str,
            "judge_divergence": float|None,
            "secondary_judge_skipped": bool,
            "prompt_changed": bool,
        }}
    """
    # 代码接地性：evidence_paths 存在率 × 5
    storage_root = get_storage_root()
    if evidence_paths:
        exist_count = sum(
            1 for p in evidence_paths if (storage_root / p).exists()
        )
        code_groundedness = round((exist_count / len(evidence_paths)) * 5)
    else:
        code_groundedness = 0

    # 检查 prompt 变更
    prompt_changed = _check_prompt_changed(soul_kb_id, prompt_version)

    # 构建评估 prompt
    answer_text = a.get("answer_text", "") if isinstance(a, dict) else str(a)
    q_text = q.get("q_text", "") if isinstance(q, dict) else str(q)

    # 证据文本片段（截取前 500 字符每路径）
    evidence_lines: list[str] = []
    for p in evidence_paths[:10]:
        try:
            txt = storage_reader.read_document_content(p, max_chars=500)
            evidence_lines.append(f"[{_norm_path(p)}]\n{txt[:500]}")
        except Exception:
            evidence_lines.append(f"[{_norm_path(p)}]\n(无法读取)")

    eval_prompt = (
        f"# 问题\n{q_text}\n\n"
        f"# 答案\n{answer_text}\n\n"
        f"# 证据\n" + "\n---\n".join(evidence_lines) + "\n\n"
        "请根据四维锚点标准评分（0-5 整数），输出 JSON。"
    )

    system_prompt_path = str(_PROMPTS_DIR / f"{prompt_version}.txt")
    result_schema = {
        "type": "object",
        "properties": {
            "groundedness": {"type": "integer", "minimum": 0, "maximum": 5},
            "completeness": {"type": "integer", "minimum": 0, "maximum": 5},
            "coherence": {"type": "integer", "minimum": 0, "maximum": 5},
            "info_gain": {"type": "integer", "minimum": 0, "maximum": 5},
            "justification": {"type": "string"},
        },
        "required": ["groundedness", "completeness", "coherence", "info_gain", "justification"],
    }

    result = await agent_harness.complete(
        prompt=eval_prompt,
        result_schema=result_schema,
        system_prompt_path=system_prompt_path,
        timeout_sec=120,
        expected_output_tokens=512,
    )

    if not result.get("success"):
        logger.warning("eval_answer: complete() failed: %s", result.get("error"))
        return {
            "scores": {"groundedness": 0, "completeness": 0, "coherence": 0, "info_gain": 0},
            "pas_score": None,
            "eval_prompt_version": prompt_version,
            "judge_divergence": None,
            "secondary_judge_skipped": True,
            "prompt_changed": prompt_changed,
        }

    parsed = result.get("parsed", {})
    if isinstance(parsed, dict):
        llm_groundedness = int(parsed.get("groundedness", 0))
        completeness = int(parsed.get("completeness", 0))
        coherence = int(parsed.get("coherence", 0))
        info_gain = int(parsed.get("info_gain", 0))
        justification = str(parsed.get("justification", ""))
    else:
        llm_groundedness = 3
        completeness = 3
        coherence = 3
        info_gain = 3
        justification = ""

    # 最终接地性 = min(代码分, LLM 分)
    groundedness = min(code_groundedness, llm_groundedness)
    groundedness = max(0, min(5, groundedness))

    scores = {
        "groundedness": groundedness,
        "completeness": max(0, min(5, completeness)),
        "coherence": max(0, min(5, coherence)),
        "info_gain": max(0, min(5, info_gain)),
    }

    # 从 justification 尝试提取 pas_score（如果 LLM 包含）
    pas_score: float | None = None
    pas_match = re.search(r"pas[_\s]*score[:\s]*([\d.]+)", justification, re.IGNORECASE)
    if pas_match:
        try:
            pas_score = float(pas_match.group(1))
            pas_score = min(5.0, max(0.0, pas_score))
        except ValueError:
            pass

    # 双判官：10% 抽样（确定性: hash(q_text) % 10 == 0）
    judge_divergence: float | None = None
    secondary_judge_skipped = True

    q_text_for_hash = q.get("q_text", "") if isinstance(q, dict) else str(q)
    q_hash_int = int(hashlib.md5(q_text_for_hash.encode("utf-8")).hexdigest(), 16)

    if q_hash_int % 10 == 0:
        # 读取 system prompt 并追加质疑者角色
        try:
            sys_text = Path(system_prompt_path).read_text(encoding="utf-8").strip()
            sys_text_adv = sys_text + "\n\n你是质疑者，从严评分。"
        except Exception:
            sys_text_adv = "你是质疑者，从严评分。"

        # 写一个临时 system prompt 文件（质疑者角色）
        import os as _os
        import tempfile
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="soul_eval_adv_")
            _os.close(fd)
            Path(tmp_path).write_text(sys_text_adv, encoding="utf-8")

            result2 = await agent_harness.complete(
                prompt=eval_prompt,
                result_schema=result_schema,
                system_prompt_path=tmp_path,
                timeout_sec=120,
                expected_output_tokens=512,
            )
            secondary_judge_skipped = False

            if result2.get("success"):
                parsed2 = result2.get("parsed", {})
                if isinstance(parsed2, dict):
                    s2 = {
                        "groundedness": int(parsed2.get("groundedness", 0)),
                        "completeness": int(parsed2.get("completeness", 0)),
                        "coherence": int(parsed2.get("coherence", 0)),
                        "info_gain": int(parsed2.get("info_gain", 0)),
                    }
                    diffs = [
                        abs(scores[k] - s2.get(k, 0))
                        for k in ("groundedness", "completeness", "coherence", "info_gain")
                    ]
                    judge_divergence = sum(diffs) / len(diffs)
                else:
                    secondary_judge_skipped = True
            else:
                secondary_judge_skipped = True
        except Exception as e:
            logger.warning("eval_answer: dual judge failed: %s", e)
            secondary_judge_skipped = True
        finally:
            if tmp_path is not None:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass
    else:
        secondary_judge_skipped = True

    return {
        "scores": scores,
        "pas_score": pas_score,
        "eval_prompt_version": prompt_version,
        "judge_divergence": judge_divergence,
        "secondary_judge_skipped": secondary_judge_skipped,
        "prompt_changed": prompt_changed,
    }


# ═══════════════════════════════════════════════════════════════════════════
# §5.6  distill
# ═══════════════════════════════════════════════════════════════════════════


async def distill(
    q: dict,
    a: dict,
    evidence_paths: list[str],
    scores: dict,
    soul_kb_id: str,
    qh: str,
    doc_source: str,
    prompt_version: str,
    judge_divergence: float | None = None,
    pas_score: float | None = None,
) -> dict:
    """蒸馏：将高质量 Q&A 写入记忆文件，并可选同步到共享经验池。

    记忆条件：groundedness >= 3 且无 judge_divergence。
    经验同步条件：pas_score >= 4 且 info_gain >= 3。

    Args:
        q: 问题 dict。
        a: 答案 dict。
        evidence_paths: 证据路径列表。
        scores: 评分 dict（来自 eval_answer）。
        soul_kb_id: SOUL KB ID。
        qh: 问题哈希。
        doc_source: 来源文档路径。
        prompt_version: eval prompt 版本。

    Returns:
        {{"memory_path": str|None, "synced_to_experience": bool,
          "pending_sync": bool, "skipped_reason": str|None}}
    """
    groundedness = scores.get("groundedness", 0)
    judge_divergence_val = judge_divergence
    info_gain = scores.get("info_gain", 0)
    pas = pas_score if pas_score is not None else scores.get("pas_score")

    skipped_reason: str | None = None
    memory_path: str | None = None
    synced_to_experience = False
    pending_sync = False

    # 条件检查：接地性 < 3 或有 judge_divergence 则跳过
    if groundedness < 3:
        skipped_reason = f"grounding_below_3"
        _append_gap(soul_kb_id, qh, doc_source, "grounding_below_3",
                    f"groundedness={groundedness}")
        return {
            "memory_path": None, "synced_to_experience": False,
            "pending_sync": False, "skipped_reason": skipped_reason,
        }

    if judge_divergence_val is not None and judge_divergence_val > 1.5:
        skipped_reason = "judge_divergence"
        _append_gap(soul_kb_id, qh, doc_source, "judge_divergence",
                    f"divergence={judge_divergence_val:.2f}")
        return {
            "memory_path": None, "synced_to_experience": False,
            "pending_sync": False, "skipped_reason": skipped_reason,
        }

    # 写记忆文件
    q_text = q.get("q_text", "") if isinstance(q, dict) else str(q)
    answer_text = a.get("answer_text", "") if isinstance(a, dict) else str(a)

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    sdir = soul_kb_dir(soul_kb_id)
    memories_dir = sdir / "memories"
    memories_dir.mkdir(parents=True, exist_ok=True)

    # 幂等守卫: 同 q_hash 已存在且为 approved 的记忆 → 跳过(避免覆盖已审批记忆)
    mem_filename = f"{today}-{qh}.md"
    mem_path = memories_dir / mem_filename
    if mem_path.exists():
        try:
            raw = mem_path.read_text(encoding="utf-8", errors="replace")
            if raw.startswith("---"):
                end = raw.find("\n---", 3)
                if end > 0:
                    existing = yaml.safe_load(raw[3:end]) or {}
                    if existing.get("status") == "approved":
                        return {
                            "memory_path": None, "synced_to_experience": False,
                            "pending_sync": False,
                            "skipped_reason": "already_approved_memory",
                        }
        except Exception:
            pass

    evidence_block = "\n".join(
        f"- {_norm_path(p)}: {scores.get('groundedness', 0)}"
        for p in evidence_paths[:10]
    )

    frontmatter = {
        "question": q_text[:500],
        "q_hash": qh,
        "evidence_paths": evidence_paths[:10],
        "doc_source": _norm_path(doc_source),
        "scores": {
            "groundedness": groundedness,
            "completeness": scores.get("completeness", 0),
            "coherence": scores.get("coherence", 0),
            "info_gain": info_gain,
        },
        "pas_score": pas,
        "eval_prompt_version": prompt_version,
        "status": "pending",
        "judge_divergence": judge_divergence_val,
        "secondary_judge_skipped": True,
        "learned_at": _now_iso(),
        "pending_sync": False,
        "sync_retries": 0,
        "sync_dedup_key": hashlib.sha256(
            f"{soul_kb_id}{qh}".encode("utf-8")
        ).hexdigest()[:12],
        "approved_at": None,
        "approved_by": None,
        "stale": False,
    }

    yaml_front = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False)
    body = (
        f"---\n{yaml_front}---\n\n"
        f"## 问题\n{q_text}\n\n"
        f"## 答案\n{answer_text}\n\n"
        f"## 证据\n{evidence_block}\n"
    )

    mem_filename = f"{today}-{qh}.md"
    mem_path = memories_dir / mem_filename
    try:
        atomic_write_text(mem_path, body)
        memory_path = str(mem_path)
    except Exception as e:
        logger.error("distill: failed to write memory %s: %s", mem_path, e)
        return {
            "memory_path": None, "synced_to_experience": False,
            "pending_sync": True, "skipped_reason": f"write_error: {e}",
        }

    # 经验同步：pas_score >= 4 且 info_gain >= 3
    if pas is not None and pas >= 4 and info_gain >= 3:
        try:
            # 确定来源文档所属 KB（非 soul KB）
            doc_kb_path = storage_reader.resolve_kb_path_for_doc(doc_source)
            if doc_kb_path and not doc_kb_path.startswith(SOUL_PREFIX):
                exp_data = ExperienceCreate(
                    title=q_text[:80],
                    scenario="soul-distill",
                    category=ExperienceCategory.BEST_PRACTICE,
                    problem=q_text[:2000],
                    solution=answer_text[:2000],
                    result=ExperienceResult.SUCCESS,
                    key_lessons=[],
                    tags=["soul"],
                    severity=ExperienceSeverity.NORMAL,
                    related_docs=evidence_paths[:5],
                    prerequisites=[],
                    metrics={},
                    source_questions=[q_text],
                )
                exp_result = await experience_service.create_experience(doc_kb_path, exp_data)
                if exp_result.get("success"):
                    synced_to_experience = True
                else:
                    pending_sync = True
                    logger.warning(
                        "distill: create_experience failed for %s: %s",
                        doc_kb_path, exp_result.get("error"),
                    )
            else:
                pending_sync = True
        except Exception as e:
            logger.error("distill: experience sync failed: %s", e)
            pending_sync = True

        # 更新 frontmatter 的 pending_sync
        if pending_sync:
            frontmatter["pending_sync"] = True
            frontmatter["sync_retries"] = 0
            yaml_front2 = yaml.dump(
                frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
            )
            body2 = (
                f"---\n{yaml_front2}---\n\n"
                f"## 问题\n{q_text}\n\n"
                f"## 答案\n{answer_text}\n\n"
                f"## 证据\n{evidence_block}\n"
            )
            try:
                atomic_write_text(mem_path, body2)
            except Exception:
                pass

    return {
        "memory_path": memory_path,
        "synced_to_experience": synced_to_experience,
        "pending_sync": pending_sync,
        "skipped_reason": skipped_reason,
    }


# ═══════════════════════════════════════════════════════════════════════════
# §5.7  预算管理
# ═══════════════════════════════════════════════════════════════════════════


def _read_cost_log(soul_kb_id: str) -> float:
    """读取 cost-log.jsonl 累计成本(生命周期累计,仅供审计)。"""
    try:
        sdir = soul_kb_dir(soul_kb_id)
        log_path = sdir / "audit" / "cost-log.jsonl"
        if not log_path.exists():
            return 0.0
        total = 0.0
        with open(str(log_path), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    total += float(entry.get("cost_estimate", 0))
                except (json.JSONDecodeError, ValueError):
                    pass
        return round(total, 6)
    except Exception as e:
        logger.warning("_read_cost_log failed: %s", e)
        return 0.0


def _begin_run_budget(soul_kb_id: str) -> None:
    """开启一次学习运行: 把历史累计成本快照为本次运行的基线。

    预算语义为"每轮上限 max_budget_usd"(契约 §6/meditation config),
    而非生命周期累计: 否则上一轮耗尽的成本会让后续定时训练永久拒绝。
    per-soul 锁内调用(learn_incremental/learn_docs 均持锁后调用),
    同人格并发串行,无竞态。
    """
    _budget_state[soul_kb_id] = {
        "run_baseline": _read_cost_log(soul_kb_id),
        "cost": 0.0,
        "calls": 0,
    }


def check_budget(soul_kb_id: str, est_cost: float) -> tuple[bool, float]:
    """检查 SOUL 预算是否充足(本轮口径)。

    Args:
        soul_kb_id: SOUL KB ID。
        est_cost: 预估本次成本（美元）。

    Returns:
        (ok, remaining): ok 表示本轮预算充足，remaining 为本轮剩余预算。
    """
    # 获取 max_budget_usd(每轮上限)
    med_cfg = get_meditation_config(soul_kb_id)
    if med_cfg.get("success"):
        max_budget = float(med_cfg.get("config", {}).get("max_budget_usd", SOUL_BUDGET_USD_PER_RUN))
    else:
        max_budget = SOUL_BUDGET_USD_PER_RUN

    # 本轮成本 = 累计成本 - 本轮基线(历史成本不计入本轮预算)
    persisted = _read_cost_log(soul_kb_id)
    baseline = _budget_state.get(soul_kb_id, {}).get("run_baseline", 0.0)
    run_cost = max(0.0, persisted - baseline)
    # 未持久化的内存增量也计入本轮
    in_memory = _budget_state.get(soul_kb_id, {}).get("cost", 0.0)
    run_cost = max(run_cost, in_memory)

    remaining = max_budget - run_cost
    ok = (run_cost + est_cost) <= max_budget
    return ok, round(remaining, 6)


def deduct_cost(soul_kb_id: str, cost: float) -> None:
    """从预算中扣减成本（追加 cost-log.jsonl 行，更新内存状态）。

    Args:
        soul_kb_id: SOUL KB ID。
        cost: 实际成本（美元）。
    """
    # 写 cost-log.jsonl
    sdir = soul_kb_dir(soul_kb_id)
    audit_dir = sdir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    log_line = json.dumps({
        "timestamp": _now_iso(),
        "soul_kb_id": soul_kb_id,
        "run_id": f"run-{int(time.time_ns()):x}",
        "calls": 1,
        "cost_estimate": round(cost, 6),
        "questions": 0,
    }, ensure_ascii=False)

    log_path = audit_dir / "cost-log.jsonl"
    try:
        with open(str(log_path), "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception as e:
        logger.warning("deduct_cost: failed to write cost log: %s", e)

    # 更新内存状态
    if soul_kb_id not in _budget_state:
        _budget_state[soul_kb_id] = {"cost": 0.0, "calls": 0}
    _budget_state[soul_kb_id]["cost"] = _budget_state[soul_kb_id].get("cost", 0.0) + cost


# ═══════════════════════════════════════════════════════════════════════════
# §5.8  learn_incremental
# ═══════════════════════════════════════════════════════════════════════════


def _resolve_any_kb_path(kb_id: str) -> str | None:
    """把公开库的 UUID 或路径解析为 KB 相对路径(soul_learn 通用解析)。"""
    if not kb_id:
        return None
    norm = kb_id.replace("\\", "/").strip("/")
    try:
        for kb in storage_reader.list_knowledge_bases():
            kb_path = (kb.get("path") or "").replace("\\", "/").strip("/")
            if kb_path == norm or kb.get("kb_id") == kb_id:
                return kb["path"]
    except Exception:
        return None
    return None


def _scope_kb_paths(kb_scope: list[str]) -> list[str]:
    """把 kb_scope 解析为公开库相对路径列表(学习/训练用)。

    - 含 "*" → 全部公开库(排除 soul- 前缀人格库)
    - 否则 → 显式列表逐个解析(UUID 或路径均可)
    """
    if "*" in kb_scope:
        try:
            kbs = storage_reader.list_knowledge_bases()
        except Exception:
            return []
        return [kb["path"] for kb in kbs
                if kb.get("path") and not (kb.get("name") or "").startswith(SOUL_PREFIX)]
    paths: list[str] = []
    for kb_id in kb_scope:
        if kb_id.startswith(SOUL_PREFIX):
            continue
        p = _resolve_any_kb_path(kb_id)
        if p:
            paths.append(p)
    return paths


def _soul_learned_hashes(soul_kb_id: str) -> dict[str, str]:
    """读取 SOUL 的已学文档哈希表(per-SOUL, 存于 人格库 questions/learned-hashes.json)。

    {doc_path: content_sha256[:12]}。每个 SOUL 独立记录, 同一知识库文档可被
    不同人格各自学习(各自蒸馏自己的记忆), 不受其他 SOUL 的训练进度影响。
    """
    try:
        sdir = soul_kb_dir(soul_kb_id)
        p = sdir / "questions" / "learned-hashes.json"
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("_soul_learned_hashes failed for %s: %s", soul_kb_id, e)
        return {}


def _record_soul_learned(soul_kb_id: str, doc_path: str, content_hash: str) -> None:
    """记录该 SOUL 已学习某文档(per-SOUL 哈希表, 幂等)。"""
    if not content_hash:
        return
    try:
        sdir = soul_kb_dir(soul_kb_id)
        qdir = sdir / "questions"
        qdir.mkdir(parents=True, exist_ok=True)
        p = qdir / "learned-hashes.json"
        data: dict[str, str] = {}
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8")) or {}
            except Exception:
                data = {}
        data[_norm_path(doc_path)] = content_hash
        atomic_write_text(p, json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.warning("_record_soul_learned failed for %s: %s", doc_path, e)


def _get_incremental_docs(
    soul_kb_id: str, kb_scope: list[str],
    mastery: dict | None = None,
) -> list[dict]:
    """获取增量文档：内容 SHA256 与该 SOUL 已学哈希不一致的文档。

    计划 3.1/AC5(per-SOUL 版): 每个 SOUL 在 questions/learned-hashes.json
    记录自己的已学文档(内容 SHA256 前 12 位);内容未变 → 跳过(幂等);
    内容变更 → 哈希不匹配 → 重新学习。不同 SOUL 互不影响。

    v2 探索-利用平衡(元认知好奇心):
    - 探索: 内容变更/未学文档(原逻辑)
    - 利用: 已学但薄弱(记忆均分 <3.0 或有缺口)的文档追加进重学队列,
      优先补强薄弱主题(论文: 针对个体画像定制干预)。重学文档标记
      relearn=True, 供自适应问题生成使用重学 mix。

    Returns:
        [{{doc_path, doc_name, kb_path, updated_at, relearn?}}, ...]
    """
    learned = _soul_learned_hashes(soul_kb_id)
    docs: list[dict] = []
    for kb_path in _scope_kb_paths(kb_scope):
        try:
            doc_list = storage_reader.list_documents(kb_path)
        except Exception:
            continue
        for d in doc_list:
            doc_path = d.get("path", "")
            if not doc_path:
                continue
            # 跳过子库目录(非文档, list_documents 会把子 KB 文件夹一并返回)
            if (d.get("file_type") or "") == "knowledge-base":
                continue
            # 内容 SHA256 比对: 一致 → 已学习,跳过
            try:
                content = storage_reader.read_document_content(
                    doc_path, max_chars=50000)
                if not content:
                    # 目录或无法读取的占位条目 → 不参与学习
                    continue
                cur_hash = _content_sha256(content)
            except Exception:
                cur_hash = None
            recorded = learned.get(_norm_path(doc_path)) or ""
            if cur_hash is not None and recorded and cur_hash == recorded:
                # v2: 已学但薄弱 → 重学队列(利用通道)
                if mastery and _is_weak_topic(mastery, _norm_path(doc_path)):
                    docs.append({
                        "doc_path": _norm_path(doc_path),
                        "doc_name": d.get("name", ""),
                        "kb_path": kb_path,
                        "updated_at": d.get("updated_at", ""),
                        "content_hash": cur_hash,
                        "relearn": True,
                    })
                continue
            docs.append({
                "doc_path": _norm_path(doc_path),
                "doc_name": d.get("name", ""),
                "kb_path": kb_path,
                "updated_at": d.get("updated_at", ""),
                "content_hash": cur_hash,
            })
    # 探索优先, 利用殿后(预算内先学新知识, 剩余额度补强薄弱点)
    docs.sort(key=lambda x: (0 if not x.get("relearn") else 1, x.get("doc_path", "")))
    return docs


def _is_weak_topic(mastery: dict, doc_path: str) -> bool:
    """判断某文档主题是否薄弱(需重学): 有缺口 / 已学但零批准记忆(产出不足) /
    均分 <3.0。重学 = 探索-利用平衡的利用通道(补强薄弱主题)。"""
    from app.services.soul_curiosity import topic_mastery
    t = topic_mastery(mastery, doc_path)
    return bool(
        t["gaps"] > 0
        or (t["learned"] and t["approved_memories"] == 0)
        or (t["learned"] and 0 < t["avg_score"] < 3.0)
    )


def _record_learned_doc(soul_kb_id: str, doc: dict) -> None:
    """将该文档记入 SOUL 的已学哈希表(per-SOUL, 幂等)。

    兼容旧调用(仅 doc 参数)时回退为全局文档 metadata 记录。
    """
    h = doc.get("content_hash")
    if not h:
        return
    _record_soul_learned(soul_kb_id, doc.get("doc_path", ""), h)
    # 保留文档级 metadata 记录(信息性, 决策已改为 per-SOUL)
    try:
        kb_path = doc.get("kb_path") or ""
        if kb_path:
            storage_reader.update_document_metadata(
                kb_path, doc["doc_path"], {
                    "learned_hash": h,
                    "learned_at": _now_iso(),
                })
    except Exception as e:
        logger.warning("_record_learned_doc metadata failed for %s: %s", doc.get("doc_path"), e)


async def _learn_incremental_once(soul_kb_id: str, round_idx: int = 1) -> dict:
    """单轮增量学习(调用方必须已持有 per-soul 锁)。

    每轮独立预算基线(_begin_run_budget), 独立增量扫描。
    返回与 learn_incremental 相同的报告结构。
    """
    # 读取配置
    try:
        cfg = read_soul_config(soul_kb_id)
    except ValueError:
        return {"success": False, "error": "kb_not_found", "detail": "非 SOUL 知识库"}

    if cfg.is_template:
        return {"success": False, "error": "is_template", "detail": "模板库不可学习"}

    # 本轮预算基线(历史累计成本不计入本轮,契约 §6 每轮上限)
    _begin_run_budget(soul_kb_id)

    kb_scope = cfg.kb_scope

    # 冥想配置
    med_cfg = get_meditation_config(soul_kb_id)
    med_config = med_cfg.get("config", {})
    max_questions = int(med_config.get("max_questions_per_run", 10))

    # ⭐ 元认知画像(补天好奇心 v2): 本轮自适应问题生成 + 薄弱重学的输入
    from app.services.soul_curiosity import (
        read_mastery_profile, update_mastery_profile,
    )
    mastery = read_mastery_profile(soul_kb_id)

    # 增量文档(先于预算检查: 无增量时零成本快速返回,AC5 幂等)
    docs = _get_incremental_docs(soul_kb_id, kb_scope, mastery)
    if not docs:
        return {"success": True, "questions_generated": 0, "memories_created": 0,
                "docs_processed": 0, "skipped": 0, "gaps_count": 0,
                "judge_divergence_count": 0, "cost_estimate": 0.0, "calls": 0}

    # 预算检查（预估成本）
    est_per_call = 0.005  # 每次 complete() 约 $0.005
    ok, remaining = check_budget(soul_kb_id, est_per_call * 10)
    if not ok:
        return {"success": False, "error": "budget_exceeded",
                "detail": f"预算不足，剩余 ${remaining:.4f}"}

    # 限制文档数（来自冥想配置或合理默认）
    max_docs = min(len(docs), 10)

    # 累计统计
    total_questions = 0
    total_memories = 0
    total_docs = 0
    total_skipped = 0
    total_gaps = 0
    total_divergence = 0
    total_calls = 0
    total_cost = 0.0

    # 待写入记忆缓存（AC10：全部 LLM 完成后统一写入）
    pending_memories: list[tuple[Path, str]] = []

    for doc in docs[:max_docs]:
        if total_calls >= _MAX_CALLS_PER_RUN:
            total_skipped += 1
            break

        doc_path = doc["doc_path"]
        total_docs += 1

        # 生成问题(元认知自适应: 掌握度 → 动态比例 + 缺口聚焦 + 防重复)
        questions = await generate_questions(doc_path, num=min(max_questions, 6), mastery=mastery)
        if not questions:
            continue
        # 限制每文档问题数
        questions = questions[:max_questions]

        for q_item in questions:
            if total_calls >= _MAX_CALLS_PER_RUN:
                break

            total_questions += 1

            # 自答
            sa_result = await self_answer(q_item, soul_kb_id, kb_scope)
            total_calls += 1
            if not sa_result.get("retrieval_pass"):
                total_gaps += 1
                continue

            answer_text = sa_result.get("answer_text", "")
            citations = sa_result.get("citations", [])
            evidence_paths = sa_result.get("evidence_paths", [])

            # 评估
            a_wrap = {"answer_text": answer_text, "citations": citations}
            eval_result = await eval_answer(
                q_item, a_wrap, evidence_paths, soul_kb_id
            )
            total_calls += 1

            if eval_result.get("judge_divergence") is not None:
                total_divergence += 1

            # 蒸馏
            dist_result = await distill(
                q=q_item,
                a=a_wrap,
                evidence_paths=evidence_paths,
                scores=eval_result.get("scores", {}),
                soul_kb_id=soul_kb_id,
                qh=q_item.get("q_hash", ""),
                doc_source=doc_path,
                prompt_version=eval_result.get("eval_prompt_version", "soul_eval_v1"),
                judge_divergence=eval_result.get("judge_divergence"),
                pas_score=eval_result.get("pas_score"),
            )

            if dist_result.get("memory_path"):
                total_memories += 1

            # 累计成本
            total_cost += 0.01  # 每次 LLM 调用约 $0.005，两个调用 ≈ $0.01
            total_calls += 0  # 已在 self_answer/eval_answer 中各计一次

        # 文档已学习(内容 hash 入 SOUL 已学表,AC5 幂等)
        # 仅在有产出时标记,允许解析失败/零问题的文档下次重试
        if total_questions > 0:
            _record_learned_doc(soul_kb_id, doc)

    # AC10: 全部完成后统一 flush（记忆文件已在 distill 中原子写，此处为最终一致性）
    # 实际成本扣减
    deduct_cost(soul_kb_id, total_cost)

    # ⭐ 元认知刷新: 本轮学习足迹 → mastery.json(下一轮/RL 的画像输入, 零 LLM 成本)
    try:
        update_mastery_profile(soul_kb_id)
    except Exception as e:
        logger.warning("update_mastery_profile failed for %s: %s", soul_kb_id, e)

    return {
        "success": True,
        "round": round_idx,
        "questions_generated": total_questions,
        "memories_created": total_memories,
        "docs_processed": total_docs,
        "skipped": total_skipped,
        "gaps_count": total_gaps,
        "judge_divergence_count": total_divergence,
        "cost_estimate": round(total_cost, 6),
        "calls": total_calls,
    }


async def learn_incremental(soul_kb_id: str, rounds: int = 1,
                            progress_cb=None) -> dict:
    """增量学习：获取 SOUL scope 内变更文档 → 生成问题 → 自答 → 评估 → 蒸馏。

    固定轮数训练(rounds > 1): 锁内循环多轮, 每轮独立预算基线 + 增量扫描,
    上一轮学过的文档被 learned_hash 跳过, 下一轮继续学新文档, 直到
    rounds 用尽或全部文档学完。每轮真实产出(记忆草稿/learned_hash)并更新
    SOUL 文件, 不是假训练。

    Args:
        soul_kb_id: SOUL KB ID。
        rounds: 训练轮数(>=1)。每轮最多 30 次 LLM 调用 / 10 文档。

    Returns:
        {{success, questions_generated, memories_created, docs_processed,
          skipped, gaps_count, judge_divergence_count, cost_estimate, calls,
          rounds_completed, per_round: [...]}}
    """
    rounds = max(1, int(rounds or 1))

    # 获取锁(整轮训练持锁, 与手动/调度路径互斥语义一致)
    try:
        lock = get_soul_lock(soul_kb_id)
        await asyncio.wait_for(lock.acquire(), timeout=PER_SOUL_LOCK_TIMEOUT)
    except asyncio.TimeoutError:
        return {"success": False, "error": "lock_timeout", "detail": "无法获取 SOUL 学习锁"}

    try:
        per_round: list[dict] = []
        totals: dict[str, float | int] = {
            "questions_generated": 0, "memories_created": 0, "docs_processed": 0,
            "skipped": 0, "gaps_count": 0, "judge_divergence_count": 0,
            "cost_estimate": 0.0, "calls": 0,
        }
        first_error: str | None = None

        for r in range(1, rounds + 1):
            rep = await _learn_incremental_once(soul_kb_id, round_idx=r)
            if not rep.get("success"):
                # 预算不足/模板/锁等致命错误: 记录后停止后续轮次
                if first_error is None:
                    first_error = rep.get("error", "unknown")
                per_round.append({"round": r, **rep})
                break
            per_round.append(rep)
            for k in totals:
                totals[k] = float(totals.get(k, 0)) + float(rep.get(k, 0))
            if progress_cb:
                await _call_cb(progress_cb, {
                    "round": r,
                    "rounds": rounds,
                    "questions": int(rep.get("questions_generated", 0)),
                    "memories": int(rep.get("memories_created", 0)),
                    "docs_processed": int(rep.get("docs_processed", 0)),
                    "skipped": int(rep.get("skipped", 0)),
                    "gaps": int(rep.get("gaps_count", 0)),
                    "cost_estimate": round(float(rep.get("cost_estimate", 0.0)), 6),
                })
            # 本轮零增量(全部学完) → 提前结束, 不空转
            if rep.get("docs_processed", 0) == 0 and rep.get("questions_generated", 0) == 0:
                break

        if first_error:
            return {
                "success": False,
                "error": first_error,
                "rounds_completed": len(per_round),
                "per_round": per_round,
                "questions_generated": int(totals.get("questions_generated", 0)),
                "memories_created": int(totals.get("memories_created", 0)),
                "docs_processed": int(totals.get("docs_processed", 0)),
                "skipped": int(totals.get("skipped", 0)),
                "gaps_count": int(totals.get("gaps_count", 0)),
                "judge_divergence_count": int(totals.get("judge_divergence_count", 0)),
                "cost_estimate": round(totals.get("cost_estimate", 0.0), 6),
                "calls": int(totals.get("calls", 0)),
            }

        return {
            "success": True,
            "rounds_completed": len(per_round),
            "per_round": per_round,
            "questions_generated": int(totals.get("questions_generated", 0)),
            "memories_created": int(totals.get("memories_created", 0)),
            "docs_processed": int(totals.get("docs_processed", 0)),
            "skipped": int(totals.get("skipped", 0)),
            "gaps_count": int(totals.get("gaps_count", 0)),
            "judge_divergence_count": int(totals.get("judge_divergence_count", 0)),
            "cost_estimate": round(totals.get("cost_estimate", 0.0), 6),
            "calls": int(totals.get("calls", 0)),
        }

    except Exception as e:
        logger.error("learn_incremental failed: %s", e, exc_info=True)
        return {"success": False, "error": "internal", "detail": str(e)[:300]}
    finally:
        lock.release()


# ═══════════════════════════════════════════════════════════════════════════
# §5.9  learn_all
# ═══════════════════════════════════════════════════════════════════════════


async def learn_all(
    soul_kb_id: str = "",
    max_docs: int = 20,
    dry_run: bool = False,
    rounds: int = 1,
    progress_cb=None,
) -> dict:
    """全量学习：遍历所有 SOUL KB（排除模板），全局内容去重，执行增量学习。

    Args:
        soul_kb_id: 可选单 SOUL 过滤（空 = 全部非模板 SOUL）。
        max_docs: 最大处理文档数（总文档数上限）。
        dry_run: True 时仅返回预估，不执行实际学习。
        rounds: 固定轮数(每 SOUL 锁内循环轮次, 每轮学一批增量)。

    Returns:
        dry_run:
            {{estimated_llm_calls, unique_docs, duplicate_docs,
              cross_soul_overlap_pct, per_soul_breakdown: [...]}}
        非 dry_run:
            {{souls: [{{soul_kb_id, questions, memories, docs, rounds}}], total_*}}
    """
    if soul_kb_id:
        souls = [{"kb_id": soul_kb_id, "name": soul_kb_id}]
    else:
        souls = list_soul_kbs(include_template=False)

    if not souls:
        if dry_run:
            return {
                "estimated_llm_calls": 0, "unique_docs": 0, "duplicate_docs": 0,
                "cross_soul_overlap_pct": 0.0, "per_soul_breakdown": [],
            }
        return {"souls": [], "total_questions": 0, "total_memories": 0, "total_docs": 0}

    # 收集所有文档并计算全局去重
    all_docs: list[dict] = []
    for s in souls:
        sid = s.get("kb_id", "")
        try:
            cfg = read_soul_config(sid)
        except ValueError:
            continue
        if cfg.is_template:
            continue
        for kb_path in _scope_kb_paths(cfg.kb_scope):
            try:
                doc_list = storage_reader.list_documents(kb_path)
            except Exception:
                continue
            for d in doc_list:
                dp = _norm_path(d.get("path", ""))
                if not dp:
                    continue
                all_docs.append({
                    "doc_path": dp,
                    "soul_kb_id": sid,
                    "kb_id": kb_path,
                })

    # 去重（按内容 SHA256）
    content_hashes: dict[str, str] = {}  # doc_path → sha256
    duplicate_docs = 0
    unique_docs = 0
    total_scan = len(all_docs)
    for i, d in enumerate(all_docs):
        dp = d["doc_path"]
        try:
            content = storage_reader.read_document_content(dp, max_chars=50000)
            h = _content_sha256(content)
        except Exception:
            h = dp  # fallback
        if h in content_hashes.values():
            duplicate_docs += 1
        else:
            content_hashes[dp] = h
            unique_docs += 1
        if progress_cb and (i + 1) % 10 == 0:
            await _call_cb(progress_cb, {"phase": "scan", "scanned": i + 1, "total": total_scan,
                         "unique_docs": unique_docs, "duplicate_docs": duplicate_docs})

    # 跨 SOUL 重叠
    soul_doc_sets: dict[str, set[str]] = {}
    for d in all_docs:
        soul_doc_sets.setdefault(d["soul_kb_id"], set()).add(d["doc_path"])
    total_unique = len(set().union(*soul_doc_sets.values())) if soul_doc_sets else 0
    total_all = sum(len(v) for v in soul_doc_sets.values())
    cross_soul_overlap_pct = (
        round((1 - total_unique / total_all) * 100, 1) if total_all > 0 else 0.0
    )

    # dry_run
    if dry_run:
        per_soul = []
        for s in souls:
            sid = s.get("kb_id", "")
            try:
                cfg = read_soul_config(sid)
            except ValueError:
                continue
            if cfg.is_template:
                continue
            scope_doc_count = sum(
                1 for d in all_docs if d["soul_kb_id"] == sid
            )
            est_questions = min(scope_doc_count * 6, 30)
            per_soul.append({
                "soul_kb_id": sid,
                "scope_docs": scope_doc_count,
                "estimated_questions": est_questions,
                "estimated_llm_calls": est_questions * 2,
            })

        return {
            "estimated_llm_calls": unique_docs * 6 * 2,
            "unique_docs": unique_docs,
            "duplicate_docs": duplicate_docs,
            "cross_soul_overlap_pct": cross_soul_overlap_pct,
            "per_soul_breakdown": per_soul,
        }

    # 非 dry_run：逐 SOUL 执行 learn_incremental
    soul_results: list[dict] = []
    total_questions = 0
    total_memories = 0
    total_docs = 0

    for s in souls:
        sid = s.get("kb_id", "")
        try:
            cfg = read_soul_config(sid)
        except ValueError:
            continue
        if cfg.is_template:
            continue
        if progress_cb:
            await _call_cb(progress_cb, {"phase": "learn", "soul_kb_id": sid, "round": 0, "rounds": rounds})
            _cb = (lambda sid_: lambda p: progress_cb({"soul_kb_id": sid_, **p}))(sid)
        else:
            _cb = None
        result = await learn_incremental(sid, rounds=rounds, progress_cb=_cb)
        if result.get("success"):
            soul_results.append({
                "soul_kb_id": sid,
                "questions": result.get("questions_generated", 0),
                "memories": result.get("memories_created", 0),
                "docs": result.get("docs_processed", 0),
                "rounds": result.get("rounds_completed", rounds),
            })
            total_questions += result.get("questions_generated", 0)
            total_memories += result.get("memories_created", 0)
            total_docs += result.get("docs_processed", 0)
        elif result.get("error"):
            soul_results.append({
                "soul_kb_id": sid,
                "questions": 0, "memories": 0, "docs": 0,
                "error": result.get("error"),
            })

    return {
        "souls": soul_results,
        "total_questions": total_questions,
        "total_memories": total_memories,
        "total_docs": total_docs,
    }


# ═══════════════════════════════════════════════════════════════════════════
# §5.10  learn_docs（手动学习入口，addendum）
# ═══════════════════════════════════════════════════════════════════════════


async def learn_docs(
    soul_kb_id: str,
    doc_paths: list[str],
    limit: int = 5,
    rounds: int = 1,
    progress_cb=None,
) -> dict:
    """手动学习入口：指定文档列表，走完整 generate_questions → self_answer → eval_answer → distill 管道。

    固定轮数(rounds > 1): 锁内循环多轮, 每轮独立预算基线;
    已学文档(learned_hash 匹配)在后续轮次自动幂等跳过(0 成本)。

    Args:
        soul_kb_id: SOUL KB ID。
        doc_paths: 待学习文档路径列表。
        limit: 每文档最大问题数，默认 5。
        rounds: 训练轮数(>=1)。

    Returns:
        {{questions_generated, memories_created, docs_processed, skipped,
          gaps_count, judge_divergence_count, cost_estimate, calls,
          rounds_completed, per_round: [...]}}
    """
    rounds = max(1, int(rounds or 1))

    # 获取锁
    try:
        lock = get_soul_lock(soul_kb_id)
        await asyncio.wait_for(lock.acquire(), timeout=PER_SOUL_LOCK_TIMEOUT)
    except asyncio.TimeoutError:
        return {"success": False, "error": "lock_timeout", "detail": "无法获取 SOUL 学习锁"}

    try:
        per_round: list[dict] = []
        totals: dict[str, float | int] = {
            "questions_generated": 0, "memories_created": 0, "docs_processed": 0,
            "skipped": 0, "gaps_count": 0, "judge_divergence_count": 0,
            "cost_estimate": 0.0, "calls": 0,
        }
        first_error: str | None = None

        for r in range(1, rounds + 1):
            rep = await _learn_docs_once(soul_kb_id, doc_paths, limit, round_idx=r)
            if not rep.get("success"):
                if first_error is None:
                    first_error = rep.get("error", "unknown")
                per_round.append({"round": r, **rep})
                break
            per_round.append(rep)
            for k in totals:
                totals[k] = float(totals.get(k, 0)) + float(rep.get(k, 0))
            if progress_cb:
                await _call_cb(progress_cb, {
                    "round": r,
                    "rounds": rounds,
                    "questions": int(rep.get("questions_generated", 0)),
                    "memories": int(rep.get("memories_created", 0)),
                    "docs_processed": int(rep.get("docs_processed", 0)),
                    "skipped": int(rep.get("skipped", 0)),
                    "gaps": int(rep.get("gaps_count", 0)),
                    "cost_estimate": round(float(rep.get("cost_estimate", 0.0)), 6),
                })
            # 本轮零产出(全部已学幂等跳过) → 提前结束
            if rep.get("docs_processed", 0) == 0 and rep.get("questions_generated", 0) == 0:
                break

        if first_error:
            return {
                "success": False,
                "error": first_error,
                "rounds_completed": len(per_round),
                "per_round": per_round,
                "questions_generated": int(totals.get("questions_generated", 0)),
                "memories_created": int(totals.get("memories_created", 0)),
                "docs_processed": int(totals.get("docs_processed", 0)),
                "skipped": int(totals.get("skipped", 0)),
                "gaps_count": int(totals.get("gaps_count", 0)),
                "judge_divergence_count": int(totals.get("judge_divergence_count", 0)),
                "cost_estimate": round(totals.get("cost_estimate", 0.0), 6),
                "calls": int(totals.get("calls", 0)),
            }

        return {
            "success": True,
            "rounds_completed": len(per_round),
            "per_round": per_round,
            "questions_generated": int(totals.get("questions_generated", 0)),
            "memories_created": int(totals.get("memories_created", 0)),
            "docs_processed": int(totals.get("docs_processed", 0)),
            "skipped": int(totals.get("skipped", 0)),
            "gaps_count": int(totals.get("gaps_count", 0)),
            "judge_divergence_count": int(totals.get("judge_divergence_count", 0)),
            "cost_estimate": round(totals.get("cost_estimate", 0.0), 6),
            "calls": int(totals.get("calls", 0)),
        }

    except Exception as e:
        logger.error("learn_docs failed: %s", e, exc_info=True)
        return {"success": False, "error": "internal", "detail": str(e)[:300]}
    finally:
        lock.release()


async def _learn_docs_once(
    soul_kb_id: str,
    doc_paths: list[str],
    limit: int = 5,
    round_idx: int = 1,
) -> dict:
    """单轮显式文档学习(调用方必须已持有 per-soul 锁)。"""
    try:
        try:
            cfg = read_soul_config(soul_kb_id)
        except ValueError:
            return {"success": False, "error": "kb_not_found", "detail": "非 SOUL 知识库"}

        if cfg.is_template:
            return {"success": False, "error": "is_template", "detail": "模板库不可学习"}

        # 本轮预算基线(历史累计成本不计入本轮,契约 §6 每轮上限)
        _begin_run_budget(soul_kb_id)

        kb_scope = cfg.kb_scope

        # AC5 幂等(per-SOUL): 内容 hash 与已记录 learned_hash 一致的文档 → 跳过(不扣预算)
        learned = _soul_learned_hashes(soul_kb_id)
        pending_paths: list[str] = []
        for doc_path in doc_paths:
            try:
                content = storage_reader.read_document_content(doc_path, max_chars=50000)
                if not content:
                    continue  # 目录/占位条目 → 跳过
                cur_hash = _content_sha256(content)
                if cur_hash and learned.get(_norm_path(doc_path)) == cur_hash:
                    continue
            except Exception:
                pass
            pending_paths.append(doc_path)

        # 预算检查(与 learn_incremental 同口径: ~$0.005/次 complete 调用;
        # 每问题约 2 次调用(自答+自评),蒸馏/双判官计入运行中扣减)
        ok, remaining = check_budget(soul_kb_id, 0.005 * len(pending_paths) * limit * 2)
        if not ok:
            return {"success": False, "error": "budget_exceeded",
                    "detail": f"预算不足，剩余 ${remaining:.4f}"}

        total_questions = 0
        total_memories = 0
        total_docs = 0
        total_skipped = len(doc_paths) - len(pending_paths)
        total_gaps = 0
        total_divergence = 0
        total_calls = 0
        total_cost = 0.0

        for doc_path in pending_paths:
            if total_calls >= _MAX_CALLS_PER_RUN:
                break

            # scope 校验：文档是否在 kb_scope 内
            if kb_scope:
                # 全库通配符 "*": 所有公开库文档均在范围内(默认人格范围)
                if "*" in kb_scope:
                    doc_in_scope = True
                else:
                    doc_in_scope = False
                    for scope_id in kb_scope:
                        scope_kb_path = _resolve_any_kb_path(scope_id)
                        if scope_kb_path and doc_path.startswith(scope_kb_path + "/"):
                            doc_in_scope = True
                            break
                        if scope_kb_path and doc_path.startswith(scope_kb_path):
                            doc_in_scope = True
                            break
                    # 也检查文档路径前缀是否匹配任何 scope KB 路径
                    if not doc_in_scope:
                        try:
                            doc_kb = storage_reader.resolve_kb_path_for_doc(doc_path)
                            if doc_kb in kb_scope:
                                doc_in_scope = True
                        except Exception:
                            pass
                if not doc_in_scope:
                    _append_gap(soul_kb_id, "", doc_path, "scope_kb_missing",
                                f"doc {doc_path} outside kb_scope")
                    total_skipped += 1
                    total_gaps += 1
                    continue

            total_docs += 1

            # ⭐ v2 元认知自适应(与增量路径同源): 掌握画像 → 动态问题分布
            from app.services.soul_curiosity import read_mastery_profile
            mastery = read_mastery_profile(soul_kb_id)
            questions = await generate_questions(doc_path, num=min(limit, 6), mastery=mastery)
            total_calls += 1
            questions = questions[:limit]

            for q_item in questions:
                if total_calls >= _MAX_CALLS_PER_RUN:
                    break

                total_questions += 1

                sa_result = await self_answer(q_item, soul_kb_id, kb_scope)
                total_calls += 1
                if not sa_result.get("retrieval_pass"):
                    total_gaps += 1
                    continue

                answer_text = sa_result.get("answer_text", "")
                citations = sa_result.get("citations", [])
                evidence_paths = sa_result.get("evidence_paths", [])

                a_wrap = {"answer_text": answer_text, "citations": citations}
                eval_result = await eval_answer(q_item, a_wrap, evidence_paths, soul_kb_id)
                total_calls += 1

                if eval_result.get("judge_divergence") is not None:
                    total_divergence += 1

                dist_result = await distill(
                    q=q_item, a=a_wrap,
                    evidence_paths=evidence_paths,
                    scores=eval_result.get("scores", {}),
                    soul_kb_id=soul_kb_id,
                    qh=q_item.get("q_hash", ""),
                    doc_source=doc_path,
                    prompt_version=eval_result.get("eval_prompt_version", "soul_eval_v1"),
                    judge_divergence=eval_result.get("judge_divergence"),
                    pas_score=eval_result.get("pas_score"),
                )

                if dist_result.get("memory_path"):
                    total_memories += 1

                total_cost += 0.01

            # 文档已学习(内容 hash 入 metadata,AC5 幂等)
            # 仅在产生学习产出时记录: 问题为空(好奇心引擎未命中)或全部跳过时
            # 不标记 learned,允许下次重试(修复: 解析失败导致 0 问题也被标记)
            if total_questions > 0:
                try:
                    content = storage_reader.read_document_content(doc_path, max_chars=50000)
                    kb_path_for_doc = ""
                    for scope_id in kb_scope:
                        if scope_id == "*":
                            continue
                        scope_kb_path = _resolve_any_kb_path(scope_id)
                        if scope_kb_path and doc_path.startswith(scope_kb_path + "/"):
                            kb_path_for_doc = scope_kb_path
                            break
                    if not kb_path_for_doc:
                        # 全库范围(*): 按文档归属解析真实 KB 路径,保证文档级 metadata 可写
                        kb_path_for_doc = storage_reader.resolve_kb_path_for_doc(doc_path) or ""
                    _record_learned_doc(soul_kb_id, {
                        "kb_path": kb_path_for_doc,
                        "doc_path": doc_path,
                        "content_hash": _content_sha256(content),
                    })
                except Exception:
                    pass

        deduct_cost(soul_kb_id, total_cost)

        # ⭐ 元认知刷新: 手动学习路径同样更新画像(与增量路径同源)
        try:
            from app.services.soul_curiosity import update_mastery_profile
            update_mastery_profile(soul_kb_id)
        except Exception as e:
            logger.warning("update_mastery_profile failed for %s: %s", soul_kb_id, e)

        return {
            "success": True,
            "round": round_idx,
            "questions_generated": total_questions,
            "memories_created": total_memories,
            "docs_processed": total_docs,
            "skipped": total_skipped,
            "gaps_count": total_gaps,
            "judge_divergence_count": total_divergence,
            "cost_estimate": round(total_cost, 6),
            "calls": total_calls,
        }

    except Exception as e:
        logger.error("learn_docs failed: %s", e, exc_info=True)
        return {"success": False, "error": "internal", "detail": str(e)[:300]}


# ═══════════════════════════════════════════════════════════════════════════
# §5.11  learn_all 内部(单 SOUL 循环)
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# §5.11  calibrate（addendum）
# ═══════════════════════════════════════════════════════════════════════════


async def calibrate(soul_kb_id: str) -> dict:
    """校准评估器：读取 calibration.jsonl → 重跑 eval_answer → 检测漂移。

    Args:
        soul_kb_id: SOUL KB ID。

    Returns:
        - 条目不足：{{"message": "insufficient_calibration"}}
        - prompt 未变：{{"message": "no_prompt_change"}}
        - 成功：{{"message": "calibrated", "drift": {{dim: float}}, ...}}
    """
    sdir = soul_kb_dir(soul_kb_id)
    cal_path = sdir / "calibration" / "calibration.jsonl"
    if not cal_path.exists():
        return {"success": False, "message": "insufficient_calibration",
                "error": "insufficient_calibration"}

    entries: list[dict] = []
    with open(str(cal_path), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if len(entries) < 20:
        return {"success": False, "message": "insufficient_calibration",
                "error": "insufficient_calibration"}

    # 检查 prompt 是否变更
    prompt_version = "soul_eval_v1"
    eval_ppath = _PROMPTS_DIR / f"{prompt_version}.txt"
    current_hash = (
        hashlib.sha256(eval_ppath.read_bytes()).hexdigest()[:12]
        if eval_ppath.exists() else ""
    )

    hashes_path = sdir / "checkpoints" / "eval_prompt_hashes.json"
    stored_hash = ""
    if hashes_path.exists():
        try:
            stored_data = json.loads(hashes_path.read_text(encoding="utf-8"))
            stored_hash = stored_data.get(prompt_version, "")
        except Exception:
            pass

    if not current_hash or current_hash == stored_hash:
        return {"success": False, "message": "no_prompt_change",
                "error": "no_prompt_change"}

    # 重跑 eval_answer 对每条校准数据
    dims = ("groundedness", "completeness", "coherence", "info_gain")
    diffs: dict[str, list[float]] = {d: [] for d in dims}
    cal_count = 0

    for entry in entries:
        human_scores = entry.get("human_scores", {})
        q_data = entry.get("q", {})
        a_data = entry.get("a", {})
        evidence_paths = entry.get("evidence_paths", [])

        if not human_scores or not q_data:
            continue

        eval_result = await eval_answer(
            q_data, a_data, evidence_paths, soul_kb_id, prompt_version
        )
        model_scores = eval_result.get("scores", {})

        for d in dims:
            human_v = float(human_scores.get(d, 0))
            model_v = float(model_scores.get(d, 0))
            diffs[d].append(abs(human_v - model_v))

        cal_count += 1

    if cal_count == 0:
        return {"success": False, "message": "insufficient_calibration",
                "error": "insufficient_calibration"}

    # 每维度平均漂移
    drift: dict[str, float] = {}
    for d in dims:
        vals = diffs[d]
        drift[d] = round(sum(vals) / len(vals), 4) if vals else 0.0

    max_drift = max(drift.values())

    # 漂移 > 0.5 → eval_drift_alert + 报告
    eval_drift_alert = max_drift > 0.5

    if eval_drift_alert:
        report_lines = [
            f"# 评估器漂移报告\n",
            f"生成时间: {_now_iso()}\n",
            f"## 漂移值\n",
        ]
        for d in dims:
            report_lines.append(f"- {d}: {drift[d]:.4f}")
        report_lines.append(f"\n最大漂移: {max_drift:.4f}\n")
        report_lines.append(f"校准条目数: {cal_count}\n")

        reports_dir = sdir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"eval-drift-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
        atomic_write_text(report_path, "".join(report_lines))

    # 记录本次校准的 prompt hash（下次调用时检测变更）
    try:
        stored_data = {}
        if hashes_path.exists():
            stored_data = json.loads(hashes_path.read_text(encoding="utf-8"))
        stored_data[prompt_version] = current_hash
        atomic_write_text(hashes_path, json.dumps(stored_data, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.warning("calibrate: failed to store prompt hash: %s", e)

    return {
        "success": True,
        "message": "calibrated",
        "drift": drift,
        "max_drift": max_drift,
        "eval_drift_alert": eval_drift_alert,
        "calibration_entries": cal_count,
        "prompt_version": prompt_version,
        "prompt_hash": current_hash,
    }