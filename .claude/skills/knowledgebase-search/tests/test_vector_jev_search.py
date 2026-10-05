"""Offline tests for knowledgebase-search/scripts/vector_jev_search.py.

No MCP server and no real Laya model: MCP I/O is faked, judge scores are
injected via score_fn (labelled real_engine=false by jev_filter).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vector_jev_search as vs  # noqa: E402

QUERY = "how does instructds summarize dialogues"


class FakeMcp:
    def __init__(self, responses: dict, log: list):
        self.responses = responses
        self.log = log

    def call(self, name: str, params: dict, timeout=None):
        self.log.append((name, params))
        handler = self.responses[name]
        if callable(handler):
            return handler(params)
        return handler

    def close(self):
        pass


def make_factory(responses: dict, log: list):
    def factory():
        return FakeMcp(responses, log)
    return factory


VECTOR_RESPONSE = {"results": [
    {"kb_id": "kb1", "doc_path": "docs/gold.md", "doc_id": "d1", "score": 0.82, "chunk_index": 0},
    {"kb_id": "kb1", "doc_path": "docs/gold.md", "doc_id": "d1", "score": 0.61, "chunk_index": 3},
    {"kb_id": "kb2", "doc_path": "docs/weak.md", "doc_id": "d2", "score": 0.40, "chunk_index": 0},
    {"kb_id": "kb2", "doc_path": "docs/sub.md", "doc_id": "d3", "score": 0.30, "chunk_index": 0},
]}

GOLD = "GOLD text about instructds query-based dialogue summarization " * 40
WEAK = "WEAK text mentioning the weather only " * 40


def default_responses(**overrides):
    responses = {
        "kb_search_vector": VECTOR_RESPONSE,
        "kb_doc_read": lambda p: {"content": GOLD if p.get("doc_path") == "docs/gold.md"
                                  else WEAK, "truncated": False},
    }
    responses.update(overrides)
    return responses


def fake_score_fn(query, text, criterion):
    return (0.9 if "GOLD" in text else 0.1), {"fake": True}


def test_wide_net_dedup_keeps_all_above_threshold():
    """top_k wide net: below-threshold dropped, deduped, NO top-3/5 cut."""
    log: list = []
    out = vs.run_search(QUERY, mcp_factory=make_factory(default_responses(), log),
                        score_fn=fake_score_fn)
    assert out["recall"]["vector_raw_hits"] == 4
    assert out["recall"]["vector_dedup_docs"] == 2  # gold(2 chunks->1) + weak; sub dropped by 0.35
    vec_calls = [p for name, p in log if name == "kb_search_vector"]
    assert vec_calls[0]["top_k"] == vs.DEFAULT_TOP_K and vec_calls[0]["balance_kbs"] is True


def test_yes_docs_all_enter_result_list():
    """Both docs yes -> both in result_list (no rubric, no retention cut)."""
    def both_yes(query, text, criterion):
        return (0.9 if "GOLD" in text else 0.6), {"fake": True}

    out = vs.run_search(QUERY, mcp_factory=make_factory(default_responses(), []),
                        score_fn=both_yes)
    paths = {r["doc_path"] for r in out["result_list"]}
    assert paths == {"docs/gold.md", "docs/weak.md"}
    assert out["real_engine"] is False


def test_only_yes_docs_survive():
    out = vs.run_search(QUERY, mcp_factory=make_factory(default_responses(), []),
                        score_fn=fake_score_fn)
    assert [r["doc_path"] for r in out["result_list"]] == ["docs/gold.md"]
    assert out["kept_doc_paths"] == ["docs/gold.md"]
    assert out["result_list"][0]["judge_score"] == 0.9
    assert out["result_list"][0]["vector_score"] == 0.82  # best chunk inherited


def test_empty_read_moves_doc_to_unscanned():
    responses = default_responses(
        kb_doc_read=lambda p: {"content": "" if p.get("doc_path") == "docs/weak.md"
                               else GOLD, "truncated": False})
    out = vs.run_search(QUERY, mcp_factory=make_factory(responses, []),
                        score_fn=fake_score_fn)
    assert any(u["doc_path"] == "docs/weak.md" for u in out["unscanned"])
    assert all(r["doc_path"] != "docs/weak.md" for r in out["result_list"])


def test_engine_total_failure_is_fail_closed():
    import jev_filter as jf

    def boom(query, text, criterion, env=None):
        raise jf.JevUnavailable("laya_inference_failed:TestError:down")

    out = vs.run_search(QUERY, mcp_factory=make_factory(default_responses(), []),
                        score_fn=boom)
    assert out["result_list"] == []
    assert out["judge"]["status"] == "unavailable"
    assert out["judge"]["real_engine"] is False
    assert out["judge"]["errors"]


def test_zero_survivors_is_reported_not_hidden():
    def all_no(query, text, criterion):
        return 0.1, {"fake": True}

    out = vs.run_search(QUERY, mcp_factory=make_factory(default_responses(), []),
                        score_fn=all_no)
    assert out["status"] == "ok"            # the pipeline ran fine
    assert out["result_list"] == []          # but nothing survived the gate
    assert out["evidence_pack"] == ""


def test_evidence_pack_carries_survivor_content():
    out = vs.run_search(QUERY, mcp_factory=make_factory(default_responses(), []),
                        score_fn=fake_score_fn)
    assert "docs/gold.md" in out["evidence_pack"]
    assert "GOLD text" in out["evidence_pack"]


def test_kb_id_passthrough():
    log: list = []
    vs.run_search(QUERY, kb_id="kbX", mcp_factory=make_factory(default_responses(), log),
                  score_fn=fake_score_fn)
    call = [p for name, p in log if name == "kb_search_vector"][0]
    assert call["kb_id"] == "kbX"


def test_cli_requires_query():
    assert vs.main([]) == 1
