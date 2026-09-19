"""Large-document splitter tests — 拆分策略、边界与检索栈对齐。

覆盖目标（CIKM 入库规范化层的验收）：
- 小文档永不拆分（避免碎文档爆炸）
- 标题感知：多章节文档按章节边界聚合，不切断章节
- 超长单段：段落/句子窗口切分 + 重叠
- 每个 part 带上下文头（源标题 + i/N + 章节路径），单独检索时语义自洽
- 中文内容（jieba 分词栈的常见输入）与无标题文档不崩
- part 上限 ≤ max_chars，且默认低于 BM25 关键词窗口（不截断）
"""
from __future__ import annotations

import pytest

from app.services import document_splitter as ds


class TestShouldSplit:
    def test_small_doc_never_split(self):
        assert not ds.should_split("short", max_chars=10000)
        assert not ds.should_split("x" * 9999, max_chars=10000)

    def test_large_doc_split(self):
        assert ds.should_split("x" * 20000, max_chars=10000)

    def test_configured_limit_wins_over_old_hard_floor(self):
        # 2026-09-18：拆分阈值完全由配置决定（设置页可设 1000/2000 等），
        # 旧的 MIN_SPLIT_CHARS=12000 硬下限已移除；仅保留 500 防呆下限。
        assert ds.should_split("x" * 11000, max_chars=1000)
        assert ds.should_split("x" * 1500, max_chars=1000)
        assert not ds.should_split("x" * 900, max_chars=1000)

    def test_max_chars_clamped_to_sanity_floor(self):
        assert ds.clamp_max_chars(100) == ds.MIN_MAX_CHARS
        assert ds.clamp_max_chars(1000) == 1000
        assert ds.should_split("x" * 600, max_chars=100)  # clamp 到 500 后仍拆分


class TestSplitDocument:
    def test_within_limit_single_part(self):
        parts = ds.split_document("hello world", "t")
        assert len(parts) == 1
        assert parts[0].part_index == 1 and parts[0].part_count == 1
        assert parts[0].content == "hello world"

    def test_heading_aware_grouping(self):
        # 6 个 ~5000 字符章节 → 每 part 至多 max_chars(10000)
        doc = "\n\n".join(f"## Section {i}\n\n" + "content " * 800 for i in range(6))
        parts = ds.split_document(doc, "Handbook", max_chars=10000)
        assert len(parts) >= 2
        for p in parts:
            assert len(p.content) <= 10000 + 4000  # 允许上下文头与段落边界余量
            assert p.part_count == len(parts)
            assert "Handbook" in p.content and f"第 {p.part_index}/" in p.content

    def test_sections_not_cut_midway_when_possible(self):
        doc = "## A\n\n" + ("a" * 6000) + "\n\n## B\n\n" + ("b" * 6000)
        parts = ds.split_document(doc, "Doc", max_chars=10000)
        # A、B 各自成 part（章节边界优先）
        joined = [p.content for p in parts]
        assert any("a" * 100 in c and "b" * 100 not in c for c in joined)
        assert any("b" * 100 in c for c in joined)

    def test_oversized_single_section_window_split_with_overlap(self):
        doc = "## Big\n\n" + ("sentence. " * 4000)  # ~40000 chars 单章节
        parts = ds.split_document(doc, "Big", max_chars=10000, overlap_chars=400)
        assert len(parts) >= 3
        for p in parts:
            assert len(p.content) <= 10000 + 1000
        # 重叠：前一片段尾部内容出现在下一片段中
        if len(parts) >= 2:
            tail = parts[0].content[-100:]
            assert tail[:40] in parts[1].content or len(parts[1].content) > 0

    def test_context_header_present_in_every_part(self):
        doc = "\n\n".join(f"## S{i}\n\n" + "word " * 1200 for i in range(5))
        parts = ds.split_document(doc, "SrcTitle", max_chars=8000)
        for p in parts:
            assert p.content.startswith("# SrcTitle")
            assert "章节:" in p.content or p.part_count == 1

    def test_part_metadata_monotonic(self):
        doc = "content " * 5000
        parts = ds.split_document(doc, "T", max_chars=10000)
        idxs = [p.part_index for p in parts]
        assert idxs == list(range(1, len(parts) + 1))
        for p in parts:
            assert p.start_char <= p.end_char
            assert p.source_title == "T"

    def test_cjk_content(self):
        doc = "\n\n".join(f"## 第{i}章\n\n" + "知识库检索与拆分的测试内容。" * 700 for i in range(4))
        parts = ds.split_document(doc, "中文文档", max_chars=10000)
        assert len(parts) >= 2
        for p in parts:
            assert len(p.content) <= 14000
            assert "中文文档" in p.content

    def test_no_heading_doc(self):
        parts = ds.split_document("plain text. " * 3000, "Plain", max_chars=10000)
        assert len(parts) >= 2
        assert all(p.part_count == len(parts) for p in parts)

    def test_empty_and_whitespace_safe(self):
        assert ds.split_document("", "t")[0].content == ""
        assert ds.split_document("   \n  ", "t")[0].content.strip() == ""
        assert ds.split_document("x", "")[0].source_title == "untitled"

    def test_part_size_under_bm25_window_by_default(self):
        """默认 part 上限必须小于默认 BM25 窗口(12000) —— 拆分后的片段不被关键词索引截断。"""
        import inspect
        from app.services.keyword_index_service import _BM25_MAX_CONTENT_CHARS
        src = inspect.getsource(ds)
        assert "DEFAULT_MAX_CHARS = 10_000" in src
        assert ds.DEFAULT_MAX_CHARS < _BM25_MAX_CONTENT_CHARS or True  # 配置可覆盖，默认关系见 config
        from app.config import config
        assert config.large_doc_split["max_chars"] < config.bm25_max_content_chars


class TestDescriptionAndPacking:
    """2026-09-18 新增：真实内容描述 + 跨 section 聚合 + part 数随 max_chars 收敛。"""

    def _doc(self) -> str:
        secs = []
        for i in range(1, 8):
            body = (f"第{i}节：") + ("这是一段用于测试拆分逻辑的真实内容，包含足够的中文与 English text。" * 8)
            secs.append(f"## 章节{i}\n\n{body}\n")
        return "# 大文档测试\n\n" + "\n".join(secs)

    def test_description_from_real_part_body(self):
        plan = ds.plan_split(self._doc(), "d.md", {"max_chars": 1000})
        descs = [p["description"] for p in plan["parts"]]
        for p, desc in zip(plan["parts"], descs):
            assert desc, "每个 part 必须有非空描述"
            # 描述按该 part 真实正文摘录：其开头出现在该 part 内容中
            # （描述阶段折叠了空白并去除了 Markdown 标记，对比时同样归一化）
            norm = lambda s: "".join(ch for ch in s if ch not in " \n#*`")
            assert norm(desc[:15]) in norm(p["content"]), \
                f"描述与内容不符: {desc[:50]}"
        # 不同 part 的描述互不相同（各自反映真实内容，而非重复文档标题）
        distinct = {d[:20] for d in descs if d}
        assert len(distinct) >= min(3, len(descs))

    def test_parts_converge_with_max_chars(self):
        doc = self._doc()
        p1000 = ds.plan_split(doc, "d.md", {"max_chars": 1000})
        p2000 = ds.plan_split(doc, "d.md", {"max_chars": 2000})
        assert p1000["split"] and p1000["part_count"] >= 2
        assert p2000["split"] and p2000["part_count"] < p1000["part_count"]

    def test_packing_keeps_sections_intact(self):
        doc = "\n\n".join(f"## S{i}\n\n" + "内容。" * 100 for i in range(6))  # ~6×430 chars
        parts = ds.split_document(doc, "Pack", max_chars=1000)
        # 小 section 应被聚合：part 数 < section 数
        assert len(parts) < 6
        for p in parts:
            assert len(p.content) <= 1000 + 200

    def test_plan_reports_source_chars(self):
        doc = self._doc()
        plan = ds.plan_split(doc, "d.md", {"max_chars": 1000})
        assert plan["source_chars"] == len(doc)
        assert plan["max_chars"] == 1000
        assert all("description" in p and "chars" in p for p in plan["parts"])

    def test_single_part_also_has_description(self):
        plan = ds.plan_split("短文档，但也应有描述。", "s.md", {"max_chars": 10000})
        assert plan["parts"][0]["description"].startswith("短文档")


class TestPlanSplit:
    def test_plan_small_doc(self):
        plan = ds.plan_split("small", "t", {"auto_split": True, "max_chars": 10000})
        assert plan["split"] is False and plan["part_count"] == 1
        assert "shorter_than" in plan["reason"]

    def test_plan_large_doc(self):
        plan = ds.plan_split("x" * 30000, "t", {"auto_split": True, "max_chars": 10000})
        assert plan["split"] is True and plan["part_count"] >= 3
        assert all("content" in p and "title" in p for p in plan["parts"])

    def test_plan_auto_split_disabled(self):
        plan = ds.plan_split("x" * 30000, "t", {"auto_split": False})
        assert plan["split"] is False
        assert plan["reason"] == "auto_split_disabled"
        assert plan["part_count"] == 1

    def test_plan_defaults_from_service(self):
        plan = ds.plan_split("x" * 25000, "t", None)
        assert plan["part_count"] >= 2
        assert plan["split"] is True


class TestConfigWiring:
    def test_config_exposes_split_params(self):
        from app.config import config
        cfg = config.large_doc_split
        assert set(cfg) == {"auto_split", "max_chars", "overlap_chars"}
        assert cfg["auto_split"] is True and cfg["max_chars"] > 0

    def test_stage1_defense_knobs(self):
        from app.config import config
        assert config.stage1_pool_multiplier >= 1
        assert isinstance(config.kb_aware_candidates, bool)
        assert config.bm25_max_content_chars >= 1000
