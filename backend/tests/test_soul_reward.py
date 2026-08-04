"""RL 强化训练引擎单元测试: 评价解析/草稿生成/合并幂等/失败容错。
风格与 test_soul.py 一致(纯函数级, asyncio.run 驱动协程, 不依赖外部服务)。
"""
import asyncio
import json
import uuid

import pytest

from app.services import soul_reward
from app.services.soul_reward import (
    _append_to_section,
    _extract_json,
    _normalize_lines,
    apply_cognition_draft,
    generate_cognition_drafts,
    evaluate_persona,
)


# ── JSON 提取 ───────────────────────────────────────────────────────────

def test_extract_json_bare():
    assert _extract_json('{"identity": 3}') == {"identity": 3}


def test_extract_json_fenced():
    assert _extract_json('```json\n{"identity": 3}\n```') == {"identity": 3}


def test_extract_json_with_prose():
    d = _extract_json('说明: 结果如下\n{"overall": 3.5, "suggestions": {}}\n完毕')
    assert d and d["overall"] == 3.5


def test_extract_json_invalid():
    assert _extract_json("没有 JSON") is None
    assert _extract_json("") is None


# ── 行规范化 ────────────────────────────────────────────────────────────

def test_normalize_lines_strips_bullets_and_numbers():
    raw = "1. 第一行\n- 第二行\n• 第三行\n  - 第四行\n\n\n"
    out = _normalize_lines(raw)
    assert out == ["第一行", "第二行", "第三行", "第四行"]


def test_normalize_lines_caps_and_dedups():
    out = _normalize_lines(["a", "a", "b", "c", "d", "e", "f", "g"], max_lines=6)
    assert out == ["a", "b", "c", "d", "e", "f"]


def test_normalize_lines_list_input():
    assert _normalize_lines(["x", "y"]) == ["x", "y"]


# ── 章节追加 ────────────────────────────────────────────────────────────

_TEMPLATE = """# SOUL 人格定义

## 身份定位
- 身份角色: 研究者

## 性格五维
- 开放性: 高

## 知识边界
- 只基于证据

## language-style
简洁有力
先结论后论证

## 回答格式偏好
- 结构: 结论先行
"""


def test_append_language_style_bare_lines():
    out = _append_to_section(_TEMPLATE, "## language-style", ["引用必带出处", "用数据说话"])
    assert "简洁有力\n先结论后论证\n引用必带出处\n用数据说话\n" in out
    assert "## 回答格式偏好" in out  # 后续章节未被破坏


def test_append_identity_list_lines():
    out = _append_to_section(_TEMPLATE, "## 身份定位", ["新增使命: 持续进化"])
    assert "- 新增使命: 持续进化" in out


def test_append_unknown_section_goes_to_tail():
    out = _append_to_section(_TEMPLATE, "## 不存在", ["x"])
    assert "进化日志(RL)" in out


# ── 草稿生成(不依赖 LLM: 用 mock 评价) ─────────────────────────────────

def test_generate_cognition_drafts_low_score_only(tmp_path, monkeypatch):
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    monkeypatch.setattr(soul_reward, "_now_iso", lambda: "2026-08-04T00:00:00+00:00")
    evaluation = {
        "identity": 2.0, "values": 4.0, "thinking": 3.0, "language": 4.0,
        "suggestions": {"identity": ["- 使命具象化", "2. 边界落地规则"]},
    }
    rep = asyncio.run(generate_cognition_drafts("soul-x", evaluation))
    assert rep["success"]
    assert len(rep["created"]) == 1  # 只有 identity < 3.5
    draft_path = tmp_path / "cognition-drafts" / f"{rep['created'][0]}.md"
    content = draft_path.read_text(encoding="utf-8")
    assert "trait: identity" in content
    assert "使命具象化" in content
    assert "边界落地规则" in content


def test_generate_cognition_drafts_high_scores_skip(tmp_path, monkeypatch):
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    evaluation = {"identity": 4.5, "values": 4.0, "thinking": 4.2, "language": 4.1,
                  "suggestions": {"identity": ["x"]}}
    rep = asyncio.run(generate_cognition_drafts("soul-x", evaluation))
    assert rep["created"] == []


def test_generate_cognition_drafts_no_suggestion_skips(tmp_path, monkeypatch):
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    evaluation = {"identity": 2.0, "values": 4.0, "thinking": 4.0, "language": 4.0,
                  "suggestions": {}}
    rep = asyncio.run(generate_cognition_drafts("soul-x", evaluation))
    assert rep["created"] == []
    assert any("no_suggestion" in s for s in rep["skipped"])


# ── 认知草稿审批合并 + 幂等 ─────────────────────────────────────────────

def _make_cognition_draft(tmp_path, trait, lines):
    from app.services.soul_memory import _fmt_frontmatter
    draft_id = f"20260804-{uuid.uuid4().hex[:12]}"
    drafts_dir = tmp_path / "cognition-drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    fm = {"type": "cognition", "trait": trait, "scores": {"reward": 2.0},
          "source": "reward", "status": "pending"}
    (drafts_dir / f"{draft_id}.md").write_text(
        _fmt_frontmatter(fm) + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return draft_id


def test_apply_cognition_draft_merges_and_is_idempotent(tmp_path, monkeypatch):
    (tmp_path / "soul-definition.md").write_text(_TEMPLATE, encoding="utf-8")
    (tmp_path / "memories").mkdir(parents=True, exist_ok=True)
    (tmp_path / "cognition").mkdir(parents=True, exist_ok=True)
    (tmp_path / "training").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    monkeypatch.setattr(soul_reward, "_now_iso", lambda: "2026-08-04T00:00:00+00:00")
    # checkpoint 依赖完整 soul 结构, 单测中跳过(仅验证合并+幂等逻辑)
    async def _noop(*a, **k):
        return {"success": True}
    monkeypatch.setattr("app.services.soul_memory._create_checkpoint_locked", _noop)
    # profile 刷新也跳过
    async def _noop_profile(*a, **k):
        return ""
    monkeypatch.setattr("app.services.soul_profile.generate_profile_summary", _noop_profile)

    draft_id = _make_cognition_draft(tmp_path, "language", ["证据不足明说", "引用统一编号"])
    rep = asyncio.run(apply_cognition_draft("soul-x", draft_id))
    assert rep["success"] and rep["lines_appended"] == 2

    text = (tmp_path / "soul-definition.md").read_text(encoding="utf-8")
    assert "证据不足明说" in text
    assert "引用统一编号" in text

    # 幂等: 重复审批 → already_applied
    rep2 = asyncio.run(apply_cognition_draft("soul-x", draft_id))
    assert not rep2["success"] and rep2["error"] == "already_applied"

    fm, _ = soul_reward._read_memory_full(tmp_path / "cognition-drafts" / f"{draft_id}.md")
    assert fm["status"] == "approved"


def test_apply_cognition_draft_dedup_lines(tmp_path, monkeypatch):
    """已存在于定义中的行不重复追加。"""
    (tmp_path / "soul-definition.md").write_text(_TEMPLATE, encoding="utf-8")
    (tmp_path / "memories").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    monkeypatch.setattr(soul_reward, "_now_iso", lambda: "2026-08-04T00:00:00+00:00")
    async def _noop(*a, **k):
        return {"success": True}
    monkeypatch.setattr("app.services.soul_memory._create_checkpoint_locked", _noop)
    monkeypatch.setattr("app.services.soul_profile.generate_profile_summary",
                        lambda sid: asyncio.sleep(0) or "")

    # language-style 已有"简洁有力" → 草稿含重复行应被去重
    draft_id = _make_cognition_draft(tmp_path, "language", ["简洁有力", "新短语"])
    rep = asyncio.run(apply_cognition_draft("soul-x", draft_id))
    text = (tmp_path / "soul-definition.md").read_text(encoding="utf-8")
    assert text.count("简洁有力") == 1  # 原有一行, 未重复追加
    assert "新短语" in text


# ── evaluate_persona 失败容错 ───────────────────────────────────────────

def test_evaluate_persona_parse_failure_neutral(tmp_path, monkeypatch):
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    (tmp_path / "soul-definition.md").write_text("# x", encoding="utf-8")
    (tmp_path / "memories").mkdir(exist_ok=True)

    async def _fake_complete(**kw):
        return {"success": True, "text": "不是JSON的输出"}

    monkeypatch.setattr(soul_reward.agent_harness, "complete", _fake_complete)
    rep = asyncio.run(evaluate_persona("soul-x"))
    assert rep["success"] and rep["overall"] == 0.0
    assert "evaluation_parse_failed" in rep.get("warning", "")


def test_evaluate_persona_llm_error_neutral(tmp_path, monkeypatch):
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    (tmp_path / "soul-definition.md").write_text("# x", encoding="utf-8")
    (tmp_path / "memories").mkdir(exist_ok=True)

    async def _fail_complete(**kw):
        return {"success": False, "error": "circuit open"}

    monkeypatch.setattr(soul_reward.agent_harness, "complete", _fail_complete)
    rep = asyncio.run(evaluate_persona("soul-x"))
    assert rep["success"] and rep["overall"] == 0.0


def test_evaluate_persona_success_path(tmp_path, monkeypatch):
    monkeypatch.setattr(soul_reward, "soul_kb_dir", lambda sid: tmp_path)
    (tmp_path / "soul-definition.md").write_text("# x", encoding="utf-8")
    (tmp_path / "memories").mkdir(exist_ok=True)

    async def _good_complete(**kw):
        return {"success": True, "text": json.dumps({
            "identity": 4, "values": 4, "thinking": 3, "language": 3,
            "overall": 3.5,
            "suggestions": {"thinking": ["问题先拆解"]},
        })}

    monkeypatch.setattr(soul_reward.agent_harness, "complete", _good_complete)
    rep = asyncio.run(evaluate_persona("soul-x"))
    assert rep["identity"] == 4.0
    assert rep["overall"] == 3.5
    assert rep["suggestions"]["thinking"] == ["问题先拆解"]
