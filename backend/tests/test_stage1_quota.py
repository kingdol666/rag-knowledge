"""Stage1 corpus-scale dominance defenses — 大库淹没小库的回归测试。

背景（2026-09-11 实测）：索引 12.5K 页 wiki 语料后，未限定 KB 的全局查询
stage1 BM25 候选被大库占满，小领域库（8 篇文档）永远进不了候选集 ——
Domain-50 P@5 从 0.424 崩到 0.000。修复：
  1) 候选池倍率：全局查询先取 top_k × stage1_pool_multiplier 条 DM25 结果；
  2) KB 配额均衡：默认开启（kb_aware_candidates），按 KB 轮询选取。
本文件验证这两条防线各自的机制与协同。
"""
from __future__ import annotations

import pytest

from app.services import two_stage_search_service as ts


def _cand(path: str, score: float) -> dict:
    return {"doc_path": path, "score": score, "name": path}


class TestBalanceCandidatesByKb:
    def test_small_kb_survives_mega_corpus_flood(self):
        """10 条大库高分 + 2 条小库低分 → 均衡后小库必须有代表。"""
        mega = [_cand(f"KB-Mega/doc{i}.md", 10.0 - i * 0.01) for i in range(10)]
        small = [_cand("KB-Small/paperA.md", 3.0), _cand("KB-Small/paperB.md", 2.9)]
        out = ts.TwoStageSearchService._balance_candidates_by_kb(mega + small, top_k=5)
        kbs = {c["doc_path"].split("/")[0] for c in out}
        assert "KB-Small" in kbs, "小库在配额均衡后仍被淹没"
        assert len(out) <= 5

    def test_quota_caps_dominant_kb(self):
        mega = [_cand(f"KB-Mega/d{i}.md", 100.0 - i) for i in range(50)]
        small = [_cand(f"KB-S{i%3}/p{i}.md", 1.0) for i in range(3)]
        out = ts.TwoStageSearchService._balance_candidates_by_kb(mega + small, top_k=8)
        mega_n = sum(1 for c in out if c["doc_path"].startswith("KB-Mega"))
        assert mega_n <= max(8 // 4 + 1, 2) + 1  # per_kb_cap 量级

    def test_single_kb_unchanged(self):
        only = [_cand(f"KB-One/d{i}.md", 5.0 - i) for i in range(10)]
        out = ts.TwoStageSearchService._balance_candidates_by_kb(only, top_k=4)
        assert len(out) == 4 and all(c["doc_path"].startswith("KB-One") for c in out)

    def test_backslash_paths_grouped_correctly(self):
        """Windows 路径（反斜杠）也按 KB 正确分组。"""
        mega = [_cand(f"KB-Mega\\d{i}.md", 10.0) for i in range(10)]
        small = [_cand("KB-Small\\p.md", 1.0)]
        out = ts.TwoStageSearchService._balance_candidates_by_kb(mega + small, top_k=5)
        assert any("KB-Small" in c["doc_path"] for c in out)

    def test_top_k_respected(self):
        cands = [_cand(f"KB-{i%5}/d{i}.md", 10.0 - i * 0.1) for i in range(100)]
        out = ts.TwoStageSearchService._balance_candidates_by_kb(cands, top_k=7)
        assert len(out) == 7


class TestPoolMultiplierWiring:
    def test_config_defaults_enable_defense(self):
        from app.config import config
        assert config.stage1_pool_multiplier >= 2, "候选池倍率必须 >1 才能抗淹没"
        assert config.kb_aware_candidates is True

    def test_pool_k_computation(self, monkeypatch):
        """_stage1_broad_search 在未限定 KB 时把池放大到 top_k×倍率。"""
        calls = {}

        def fake_search(query, top_k=20, kb_ids=None):
            calls["top_k"] = top_k
            # 模拟大库淹没：池内只有 mega 库结果
            return [{"doc_path": f"KB-Mega/d{i}.md", "score": 10.0 - i, "name": ""}
                    for i in range(top_k)]

        monkeypatch.setattr(ts.keyword_index_service, "search", fake_search)
        monkeypatch.setattr(ts.TwoStageSearchService, "_ensure_keyword_index", lambda self, kb=None: None)
        svc = ts.TwoStageSearchService()
        svc._stage1_broad_search("q", None, top_k=20, kw_weight=0.5, graph_weight=0.5,
                                 enable_graph_expansion=False)
        assert calls["top_k"] == 20 * ts.config.stage1_pool_multiplier

    def test_scoped_kb_query_keeps_pool_small(self, monkeypatch):
        """限定 KB 的查询不放大池（无淹没风险，省算力）。"""
        calls = {}

        def fake_search(query, top_k=20, kb_ids=None):
            calls["top_k"] = top_k
            return [{"doc_path": "KB-One/d.md", "score": 1.0, "name": ""}]

        monkeypatch.setattr(ts.keyword_index_service, "search", fake_search)
        monkeypatch.setattr(ts.TwoStageSearchService, "_ensure_keyword_index", lambda self, kb=None: None)
        svc = ts.TwoStageSearchService()
        svc._stage1_broad_search("q", "KB-One", top_k=20, kw_weight=0.5, graph_weight=0.5,
                                 enable_graph_expansion=False)
        assert calls["top_k"] == 20

    def test_disabling_defense_restores_legacy_behaviour(self, monkeypatch):
        from app.config import config
        monkeypatch.setitem(config._config["search"]["two_stage"], "stage1_pool_multiplier", 1)
        monkeypatch.setitem(config._config["search"]["two_stage"], "kb_aware_candidates", False)
        calls = {}

        def fake_search(query, top_k=20, kb_ids=None):
            calls["top_k"] = top_k
            return [{"doc_path": f"KB-Mega/d{i}.md", "score": 10.0 - i, "name": ""} for i in range(top_k)]

        monkeypatch.setattr(ts.keyword_index_service, "search", fake_search)
        monkeypatch.setattr(ts.TwoStageSearchService, "_ensure_keyword_index", lambda self, kb=None: None)
        svc = ts.TwoStageSearchService()
        out = svc._stage1_broad_search("q", None, top_k=20, kw_weight=0.5, graph_weight=0.5,
                                       enable_graph_expansion=False)
        assert calls["top_k"] == 20
        assert all(c["doc_path"].startswith("KB-Mega") for c in out)
