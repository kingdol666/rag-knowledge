"""Offline tests for knowledgebase-ingest/scripts/audit_descriptions.py
and repair_part_prefixes.py (plan building only — no MCP, no writes)."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_descriptions as ad  # noqa: E402
import repair_part_prefixes as rp  # noqa: E402

GOOD = ("【2/4·InstructDS】A*STAR 将指令微调引入对话摘要，通过查询生成、过滤、"
        "摘要生成三步合成高质量 query 型摘要三元组，可回答数据合成与训练问题。——## 5 Experiments")


def _kb(docs):
    return [{"kb_id": "kb1", "name": "Alpha", "doc_count": len(docs), "docs": docs}]


def test_broken_part_prefix_detected_and_suggested():
    catalog = {"catalog": _kb([{"doc_id": "d1", "doc_path": "Alpha\\x (part 3 of 7).md",
                                "description": "【?/?·BERT】预训练双向 Transformer 表示，可回答预训练语言模型表示学习的问题。——## 3 Method"}])}
    verdict = ad.audit_catalog(catalog)
    assert verdict["by_issue"].get("broken_part_prefix") == 1
    row = verdict["docs"][0]
    assert row["suggested_description"].startswith("【3/7·BERT】")
    assert verdict["auto_fixable"] == 1


def test_empty_short_and_degenerate_flagged():
    catalog = {"catalog": _kb([
        {"doc_id": "d1", "doc_path": "Alpha\\a.md", "description": ""},
        {"doc_id": "d2", "doc_path": "Alpha\\b.md", "description": "too short"},
        {"doc_id": "d3", "doc_path": "Alpha\\c.md",
         "description": "章节范围声明自相矛盾的样例文档，罗马数字区间同点退化 XV–XV 不可信，内容与描述需要核对。"},
    ])}
    by = ad.audit_catalog(catalog)["by_issue"]
    assert by.get("empty") == 1 and by.get("short") == 1 and by.get("degenerate_range") == 1


def test_boilerplate_flagged_at_three_repeats():
    docs = [{"doc_id": f"d{i}", "doc_path": f"Alpha\\p{i}.md",
             "description": "Gutenberg front matter placeholder text repeated across many documents"} for i in range(4)]
    docs.append({"doc_id": "ok", "doc_path": "Alpha\\ok.md", "description": GOOD})
    verdict = ad.audit_catalog({"catalog": _kb(docs)})
    boiler = [r for r in verdict["docs"] if "boilerplate" in r["issues"]]
    assert len(boiler) == 4


def test_part_anchor_missing_only_when_no_prefix_and_no_anchor():
    docs = [
        {"doc_id": "d1", "doc_path": "Alpha\\x (part 1 of 2).md",
         "description": "这段描述没有任何分部前缀也没有锚点尾巴，只是整篇的泛泛摘要，无法定位本部内容所在章节范围"},
        {"doc_id": "d2", "doc_path": "Alpha\\y (part 2 of 2).md",
         "description": "无前缀但有锚点：这一段描述足够长可以直接参与逐级检索的描述匹配，同时以锚点标明本部覆盖的章节范围。——## 4 Results"},
    ]
    issues = {r["doc_id"]: r["issues"] for r in ad.audit_catalog({"catalog": _kb(docs)})["docs"]}
    assert "part_anchor_missing" in issues["d1"]
    assert not issues.get("d2")


def test_clean_doc_not_flagged():
    verdict = ad.audit_catalog({"catalog": _kb([
        {"doc_id": "d1", "doc_path": "Alpha\\a.md", "description": GOOD},
        {"doc_id": "d2", "doc_path": "Alpha\\b (part 1 of 2).md",
         "description": "【1/2·Split】有分部前缀与锚点，正文摘要充分，不会触发任何审计规则。——## 2 Setup"}])})
    assert verdict["flagged"] == 0 and verdict["doc_total"] == 2


def test_prefix_fix_requires_part_in_path():
    assert ad.suggested_prefix_fix("【?/?·X】描述", "Alpha\\plain.md") is None
    assert ad.suggested_prefix_fix("没有前缀的描述文本", "Alpha\\x (part 1 of 2).md") is None


def test_repair_plan_only_auto_fixable():
    catalog = {"catalog": _kb([
        {"doc_id": "d1", "doc_path": "Alpha\\a (part 1 of 2).md", "description": "【?/?·A】可修复的样例描述，长度充分且带锚点尾巴。——## 1 Intro"},
        {"doc_id": "d2", "doc_path": "Alpha\\b.md", "description": ""},
        {"doc_id": "d3", "doc_path": "Alpha\\c (part 2 of 2).md",
         "description": "无前缀但有锚点：这一篇缺的不是可机械修复的前缀。——## 3 Method"},
    ])}
    plan = rp.build_plan(catalog)
    assert len(plan) == 1 and plan[0]["new_description"].startswith("【1/2·A】")
