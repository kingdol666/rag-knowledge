"""补天好奇心引擎 v2 单测 — 元认知画像 / 自适应问题分布 / 新奇度过滤。

参考: arXiv:2604.25648 (Curiosity and Metacognition, Oudeyer 团队 2026)。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import soul_curiosity as sc  # noqa: E402


# ── compute_question_mix: 近发展区自适应比例 ─────────────────────────

def test_mix_default_without_mastery():
    m = sc.compute_question_mix(None)
    assert m == sc.DEFAULT_MIX


def test_mix_new_topic_foundation_first():
    m = sc.compute_question_mix({"topics": {"a.md": {"learned": False}}}, "a.md")
    assert m["fact"] >= 30          # 新主题打基础
    assert m["challenge"] <= 15     # 挑战不倾斜


def test_mix_weak_topic_reexplore():
    m = sc.compute_question_mix({
        "topics": {"a.md": {"learned": True, "approved_memories": 1,
                            "avg_score": 2.4, "gaps": 2}},
    }, "a.md")
    assert m["fact"] < 30           # 补基深化
    assert m["cross_doc"] >= 30     # 关联补强


def test_mix_mid_topic_balanced_deepen():
    m = sc.compute_question_mix({
        "topics": {"a.md": {"learned": True, "approved_memories": 2,
                            "avg_score": 3.4, "gaps": 0}},
    }, "a.md")
    assert m["challenge"] == 30


def test_mix_strong_topic_challenge_frontier():
    m = sc.compute_question_mix({
        "topics": {"a.md": {"learned": True, "approved_memories": 5,
                            "avg_score": 4.3, "gaps": 0}},
    }, "a.md")
    assert m["challenge"] >= 50     # 强掌握 → 挑战边界(好奇心最高形态)
    assert m["fact"] <= 10


def test_mix_all_types_sum_100():
    for t in (None, "new", "weak", "mid", "strong"):
        base = {"topics": {}}
        if t == "new":
            base["topics"]["a.md"] = {"learned": False}
        elif t == "weak":
            base["topics"]["a.md"] = {"learned": True, "approved_memories": 1,
                                      "avg_score": 2.0, "gaps": 1}
        elif t == "mid":
            base["topics"]["a.md"] = {"learned": True, "approved_memories": 2,
                                      "avg_score": 3.3, "gaps": 0}
        elif t == "strong":
            base["topics"]["a.md"] = {"learned": True, "approved_memories": 6,
                                      "avg_score": 4.1, "gaps": 0}
        m = sc.compute_question_mix(base, "a.md") if t != "none" else sc.compute_question_mix(None)
        assert sum(m.values()) == 100, f"{t}: {m}"


# ── novelty_filter: 认知伙伴防重复 ───────────────────────────────────

def test_novelty_drops_similar():
    known = ["MXene 气体传感器的选择性如何提升"]
    assert sc.novelty_filter("MXene 气体传感器选择性提升方法", known) is False


def test_novelty_keeps_distinct():
    known = ["MXene 气体传感器的选择性如何提升"]
    assert sc.novelty_filter("MXene 的 MAX 相前驱体 Ti3AlC2 制备参数", known) is True


def test_novelty_empty_known_passes():
    assert sc.novelty_filter("任意问题", []) is True


def test_novelty_english_words():
    known = ["How does doping improve MXene selectivity"]
    assert sc.novelty_filter("How doping improves MXene gas selectivity", known) is False
    assert sc.novelty_filter("What is the MAX phase precursor of Ti3C2Tx", known) is True


# ── topic_mastery / build_mastery_context ────────────────────────────

def test_topic_mastery_defaults():
    t = sc.topic_mastery({"topics": {}}, "missing.md")
    assert t == {"learned": False, "approved_memories": 0, "avg_score": 0.0, "gaps": 0}


def test_build_context_injects_gaps():
    ctx = sc.build_mastery_context({
        "topics": {"a.md": {"learned": True, "approved_memories": 1,
                            "avg_score": 2.9, "gaps": 2}},
        "known_questions": ["Q1"],
    }, "a.md")
    assert "2 个未解决学习缺口" in ctx
    assert "最近发展区" in ctx
    assert "Q1" in ctx


# ── mastery profile 读写(临时 SOUL 目录) ─────────────────────────────

def _fake_soul_dir(tmp_path: Path, memories: list[dict], gaps: list[str],
                   learned: list[str]) -> Path:
    sdir = tmp_path / "soul-test"
    (sdir / "memories").mkdir(parents=True)
    (sdir / "questions").mkdir(parents=True)
    for i, m in enumerate(memories):
        fm = (
            f"---\nstatus: approved\nquestion: \"{m['question']}\"\n"
            f"scores:\n  groundedness: {m.get('groundedness', 3)}\n"
            f"  completeness: {m.get('completeness', 3)}\n"
            f"evidence_paths: ['{m['doc']}']\n---\nbody\n"
        )
        (sdir / "memories" / f"m{i}.md").write_text(fm, encoding="utf-8")
    (sdir / "questions" / "gaps.md").write_text("\n".join(gaps), encoding="utf-8")
    (sdir / "questions" / "learned-hashes.json").write_text(
        json.dumps({d: "abc123" for d in learned}), encoding="utf-8")
    return sdir


def test_update_mastery_profile_aggregates(tmp_path, monkeypatch):
    sdir = _fake_soul_dir(tmp_path, memories=[
        {"question": "Q1", "doc": "kb/a.md", "groundedness": 2, "completeness": 2},
        {"question": "Q2", "doc": "kb/a.md", "groundedness": 4, "completeness": 4},
        {"question": "Q3", "doc": "kb/b.md", "groundedness": 4, "completeness": 4},
    ], gaps=["2026-01-01\tq1\tkb/a.md\tgrounding_below_3\tx"],
       learned=["kb/a.md", "kb/c.md"])
    monkeypatch.setattr(sc, "soul_kb_dir", lambda _: sdir)

    profile = sc.update_mastery_profile("soul-test")
    a = profile["topics"]["kb/a.md"]
    assert a["approved_memories"] == 2
    assert a["avg_score"] == 3.0          # (2+4)/2
    assert a["gaps"] == 1
    b = profile["topics"]["kb/b.md"]
    assert b["avg_score"] == 4.0
    assert "kb/c.md" in profile["topics"]  # 学习足迹
    assert "kb/a.md" in profile["weak_topics"]  # 均分 3.0 有缺口 → weak
    assert profile["known_questions"]  # 已批准记忆摘要
    # 幂等回读
    again = sc.read_mastery_profile("soul-test")
    assert again["topics"]["kb/a.md"]["avg_score"] == 3.0
