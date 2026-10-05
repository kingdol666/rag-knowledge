"""Tests for knowledgebase-ingest/scripts/identity_card.py (ICD schema)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parent.parent / "knowledgebase-librarian" / "scripts"))

import identity_card as ic  # noqa: E402
import complete_recall as cr  # noqa: E402

GOOD_META = {
    "genre": "小说", "identity": "傲慢与偏见 Pride and Prejudice",
    "position": "第 24/26 部分 · Chapter 58–59",
    "events": ["达西二度求婚，伊丽莎白应允 Darcy proposes again, accepted",
               "班纳特先生同意婚事"],
    "entities": ["Darcy", "Elizabeth", "Mr. Bennet"],
    "scope": "求婚场景、婚约进展类问题",
    "negative": "不含韦翰私奔情节",
}


def test_render_roundtrip_validates_ok():
    desc = ic.render(GOOD_META)
    v = ic.validate(desc)
    assert v["score"] == 6 and v["grade"] == "icd-ok", v
    assert not v["over_220"]


def test_vague_description_scores_poor():
    v = ic.validate("经典文学名著片段，值得细细品味，蕴含深刻的人生哲理。")
    assert v["grade"] == "icd-poor" and v["score"] <= 2


def test_boilerplate_part_label_fails_position():
    v = ic.validate("【小说】傲慢与偏见 Pride and Prejudice · 第 k/N 部分。事件: 版权声明与目录。实体: Gutenberg。可答: 版权信息。")
    assert not v["checks"]["D3_position"]


def test_audit_catalog_grades():
    catalog = {"catalog": [{"kb_id": "k", "docs": [
        {"doc_path": "a.md", "description": ic.render(GOOD_META)},
        {"doc_path": "b.md", "description": "内容概述，文学价值很高。"}]}]}
    out = ic.audit_catalog(catalog)
    assert out["doc_total"] == 2
    assert out["grades"]["icd-ok"] == 1 and out["grades"]["icd-poor"] == 1


# ── 2026-09-27：part 标记方言、倒置区间、CLI 失败关门 ──

def test_splitter_part_marker_dialects_pass_d3():
    # 后端拆分器输出 `【Part i/N · …】`，web 层输出 `[part i/N …]` ——
    # 两种方言都必须通过 D3，否则标准拆分产物全被误判。
    for desc in (
        "【小说】傲慢与偏见 Pride and Prejudice · Part 8/26 · Chapter 19。事件: Collins proposes and is rejected 柯林斯求婚被拒。实体: Collins、Elizabeth。可答: 求婚场景类问题。",
        "【小说】傲慢与偏见 Pride and Prejudice · 第 8/26 部分 · Chapter 19。事件: Collins proposes and is rejected 柯林斯求婚被拒。实体: Collins、Elizabeth。可答: 求婚场景类问题。",
    ):
        v = ic.validate(desc)
        assert v["checks"]["D3_position"], v["defects"]


def test_inverted_and_single_point_ranges_fail_d3():
    base = ("【小说】傲慢与偏见 Pride and Prejudice · 第 8/26 部分 · Chapter {}。"
            "事件: Collins proposes and is rejected。实体: Collins、Elizabeth。"
            "可答: 求婚类问题。")
    assert ic.validate(base.format("XV–XVI"))["checks"]["D3_position"]
    assert not ic.validate(base.format("XV–I"))["checks"]["D3_position"]
    assert not ic.validate(base.format("XV–XV"))["checks"]["D3_position"]
    assert not ic.validate(base.format("12–3"))["checks"]["D3_position"]


def test_validate_cli_exit_code_fail_closed(capsys):
    assert ic.main(["validate", ic.render(GOOD_META)]) == 0
    assert ic.main(["validate", "经典文学名著片段，人生哲理，值得品味。"]) == 2
    capsys.readouterr()


# ── the funnel-precision proof: same matcher the librarian/hybrid use ──

QUERY = "列出《傲慢与偏见》中所有求婚情节 pride prejudice proposal"
QTERMS = cr._terms(QUERY)

MULTI_NOVEL = [
    # (part, vague_desc, icd_desc)
    ("pp-part8", "经典文学名著第8部分，人生哲理，文学价值很高。",
     "傲慢与偏见 Pride and Prejudice · 第 8/26 部分 · Chapter 19。事件: Mr. Collins proposes to Elizabeth and is rejected 柯林斯求婚被拒。实体: Collins、Elizabeth、Mr. Bennet。可答: 求婚场景类问题。"),
    ("pp-part13", "经典文学名著第13部分，人生哲理，文学价值很高。",
     "傲慢与偏见 Pride and Prejudice · 第 13/26 部分 · Chapter 33–35。事件: Darcy proposes first at Hunsford and is rejected 达西首次求婚被拒，次日递长信。实体: Darcy、Elizabeth。可答: 求婚场景类问题。"),
    ("pp-part24", "经典文学名著第24部分，人生哲理，文学价值很高。",
     "傲慢与偏见 Pride and Prejudice · 第 24/26 部分 · Chapter 58–59。事件: Darcy proposes again and is accepted 达西二度求婚应允。实体: Darcy、Elizabeth。可答: 求婚场景类问题。"),
    ("moby-part3", "经典文学名著第3部分，人生哲理，文学价值很高。",
     "白鲸 Moby-Dick · 第 3/26 部分 · Chapters 21–30。事件: Ahab nails the doubloon to the mast 亚哈悬赏金币。实体: Ahab、Ishmael。可答: 捕鲸航行类问题。"),
    ("dreiser-part5", "经典文学名著第5部分，人生哲理，文学价值很高。",
     "嘉莉妹妹 Sister Carrie · 第 5/26 部分 · Chapters 30–38。事件: Carrie rises on the stage 嘉莉登上舞台。实体: Carrie、Hurstwood。可答: 都市奋斗类问题。"),
    ("warpeace-part9", "经典文学名著第9部分，人生哲理，文学价值很高。",
     "战争与和平 War and Peace · 第 9/26 部分 · Volume 2。事件: Napoleon invades Russia 拿破仑入侵。实体: Pierre、Andrew。可答: 战争史类问题。"),
]


def _select(descs: list[str], budget: int) -> list[str]:
    """The librarian L2 matcher: description term-overlap ranking (same
    _terms-based scoring as the script layer)."""
    scored = sorted(((len(QTERMS & cr._terms(d)), name)
                     for name, d in descs), key=lambda x: -x[0])
    return [name for ov, name in scored[:budget] if ov > 0]


def test_icd_filters_other_novels_vague_cannot():
    vague_pairs = [(n, v) for n, v, _ in MULTI_NOVEL]
    icd_pairs = [(n, i) for n, _, i in MULTI_NOVEL]

    vague_hits = _select(vague_pairs, 4)
    icd_hits = _select(icd_pairs, 4)

    assert vague_hits == [], "vague descriptions give the matcher nothing to rank"
    assert icd_hits == ["pp-part8", "pp-part13", "pp-part24"], icd_hits
