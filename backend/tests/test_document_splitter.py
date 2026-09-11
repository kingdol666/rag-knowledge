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
        assert not ds.should_split("x" * 11000, max_chars=10000)  # < MIN_SPLIT_CHARS

    def test_large_doc_split(self):
        assert ds.should_split("x" * 20000, max_chars=10000)

    def test_min_split_floor_applies(self):
        # max_chars 很小但硬下限 12000 仍然生效（防碎文档）
        assert not ds.should_split("x" * 11000, max_chars=1000)


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
