"""Dispatcher intent-routing contract tests (2026-09-27).

Parses the classification table in the dispatcher SKILL.md and asserts:
- every knowledgebase-* sub-skill on disk is routable from the table;
- representative user utterances (zh/en) route to the expected scenario under
  the documented longest-match-first rule;
- no exact keyword is claimed by two different scenarios (ambiguous single
  keywords cannot be rescued by longest-match).
"""
from __future__ import annotations

import re
from pathlib import Path

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"
SKILLS_ROOT = Path(__file__).resolve().parents[2]

_ROW_RE = re.compile(
    r"^\|(.+?)\|\s*\*\*(.+?)\*\*\s*\|\s*`Skill\(\"([a-z-]+)\"\)`", re.M)


def _rows() -> list[tuple[str, str, str]]:
    text = SKILL_MD.read_text(encoding="utf-8")
    return [(kw.strip(), scenario.strip(), skill.strip())
            for kw, scenario, skill in _ROW_RE.findall(text)]


def _keywords(cell: str) -> list[str]:
    return [k.strip() for k in cell.split(",") if k.strip()]


def _scenario_of(utterance: str) -> list[str]:
    """Longest-match-first: the longest keyword hit decides the scenario."""
    best_len, hits = 0, []
    for cell, scenario, _ in _rows():
        for kw in _keywords(cell):
            if kw in utterance:
                if len(kw) > best_len:
                    best_len, hits = len(kw), [scenario]
                elif len(kw) == best_len and scenario not in hits:
                    hits.append(scenario)
    return hits


def test_every_kb_skill_is_routable():
    routed = {skill for _, _, skill in _rows()}
    disk = {d.name for d in SKILLS_ROOT.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()}
    kb_skills = {n for n in disk if n.startswith("knowledgebase-")}
    missing = kb_skills - routed
    assert not missing, f"unroutable knowledgebase-* skills: {sorted(missing)}"


def test_librarian_and_hybrid_are_routable():
    routed = {skill for _, _, skill in _rows()}
    assert "knowledgebase-librarian" in routed
    assert "knowledgebase-hybrid" in routed


def test_utterances_route_to_expected_scenario():
    cases = {
        "帮我把这本小说入库": ["Ingest"],
        "解析PDF并存入库": ["Ingest"],
        "帮我创建知识库": ["Manage"],
        "更新文档内容": ["Manage"],
        "帮我逐级检索全库找齐所有相关文档": ["Librarian"],
        "并行检索两种方式一起跑": ["Hybrid"],
        "查一下这个问题的答案": ["Search"],
        "列出所有知识库": ["List"],
        "检查知识库完整性": ["Verify"],
        "整理一下全库结构": ["Organize"],
        "记录这次的经验教训": ["Experience-Summarize"],
    }
    for utterance, expected in cases.items():
        got = _scenario_of(utterance)
        assert got == expected, f"{utterance!r}: expected {expected}, got {got}"


def test_no_duplicate_keywords_across_scenarios():
    seen: dict[str, str] = {}
    dups: list[tuple[str, str, str]] = []
    for cell, scenario, _ in _rows():
        for kw in _keywords(cell):
            key = kw.lower()
            if key in seen and seen[key] != scenario:
                dups.append((kw, seen[key], scenario))
            seen.setdefault(key, scenario)
    assert not dups, f"keywords claimed by multiple scenarios: {dups}"
