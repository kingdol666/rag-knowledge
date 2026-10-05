"""Offline tests for butian/scripts/nuwa_to_seed.py (seed conversion)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import nuwa_to_seed as ns  # noqa: E402

EN_SKILL = """---
name: test-musk
description: English-titled perspective skill
---

# Test Musk · Thinking OS

## Roleplay Rules (Most Important)
- First-principles only.
**退出角色**  (exit marker here)

## Identity Card
**Who I am**: a test persona.

## Answer Workflow
### Step 1: Classify
Classify the question.

## Core Mental Models
First-principles reasoning.

## Decision Heuristics
Prefer physics limits over analogy.

## Expression DNA
Blunt, quantitative.

## Personal Timeline
Born; built things.

## Values and Anti-Patterns
Value: truth. Anti-pattern: hand-waving.

## Intellectual Genealogy
Physicists and engineers.

## Honest Boundaries
No fabricated numbers.

## Appendix: Research Sources
(irrelevant)
"""

CN_SKILL = """---
name: test-cn
description: 中文标题视角 skill
---

# 测试人格

## 角色扮演规则
- 只用第一性原理。
**退出角色**

## 身份卡
我是测试人格。

## 回答工作流
分类问题。

## 核心心智模型
第一性原理。

## 价值观与反模式
反模式：空话。
"""


def _write_skill(tmp_path: Path, text: str) -> Path:
    d = tmp_path / "perspective-skill"
    (d / "references").mkdir(parents=True)
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    return d


def test_english_titled_skill_converts(tmp_path):
    """Regression: English section titles (musk-perspective style) must convert."""
    out = ns.convert(_write_skill(tmp_path, EN_SKILL), tmp_path / "seed", [])
    assert (out / "persona.md").exists() and (out / "work.md").exists()
    persona = (out / "persona.md").read_text(encoding="utf-8")
    work = (out / "work.md").read_text(encoding="utf-8")
    values = (out / "values.md").read_text(encoding="utf-8")
    assert "身份卡" in persona and "表达DNA" in persona
    assert "回答工作流" in work and "核心心智模型" in work and "决策启发式" in work
    # build_values 蒸馏内容本身(无标题头, ragctl --values 融合模板直接消费)
    assert "Value: truth" in values and "hand-waving" in values
    meta = (out / "meta.json").read_text(encoding="utf-8")
    assert "test-musk" in meta


def test_roleplay_summary_truncates_at_exit_marker(tmp_path):
    """Regression: the 退出角色 cut used to be dead code (wrong lookup key)."""
    out = ns.convert(_write_skill(tmp_path, EN_SKILL), tmp_path / "seed", [])
    persona = (out / "persona.md").read_text(encoding="utf-8")
    assert "**退出角色**" not in persona, "exit marker must be cut from the summary"


def test_chinese_titled_skill_still_converts(tmp_path):
    out = ns.convert(_write_skill(tmp_path, CN_SKILL), tmp_path / "seed", [])
    persona = (out / "persona.md").read_text(encoding="utf-8")
    assert "我是测试人格" in persona
    assert "**退出角色**" not in persona


def test_skill_without_persona_or_work_raises(tmp_path):
    bare = _write_skill(tmp_path, "---\nname: x\ndescription: y\n---\n\n# Nothing here\n")
    with pytest.raises(ValueError):
        ns.convert(bare, tmp_path / "seed", [])
