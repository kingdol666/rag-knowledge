"""Offline tests for the engine-neutral librarian decision filter."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "jev_filter.py"
SPEC = importlib.util.spec_from_file_location("jev_filter", SCRIPT)
assert SPEC and SPEC.loader
jev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(jev)


def candidate(cid: str, text: str, line: int) -> dict:
    return {
        "candidate_id": cid,
        "kb_id": "kb-1",
        "doc_id": f"doc-{cid}",
        "doc_path": f"docs/{cid}.md",
        "part_index": 1,
        "section_path": "Methods > Results",
        "start_line": line,
        "end_line": line + 3,
        "text": text,
    }


def test_auto_criterion_uses_instance_for_enumeration():
    result = jev.filter_candidates(
        {"engine": "laya", "query": "List every scene where the event occurs", "candidates": [candidate("a", "scene", 1)]},
        score_fn=lambda q, text, criterion: (0.8, {"offline": True}),
    )
    assert result["criterion"] == "instance"
    assert result["engine"] == "laya"
    assert result["backend"] == "offline"
    assert result["real_engine"] is False
    assert result["real_jev"] is False
    assert result["survivors"][0]["candidate_id"] == "a"
    assert result["result_list"][0]["doc_path"] == "docs/a.md"


def test_every_candidate_gets_a_verdict_and_errors_fail_closed():
    calls = []

    def score(query, text, criterion):
        calls.append(text)
        if text == "broken":
            raise RuntimeError("offline backend")
        return (0.9, {"offline": True})

    result = jev.filter_candidates(
        {"query": "What is the result?", "candidates": [candidate("a", "good", 1), candidate("b", "broken", 5)]},
        score_fn=score,
    )
    assert calls == ["good", "broken"]
    assert result["candidate_count"] == 2
    assert result["criterion"] == "evidence"
    assert result["scored_count"] == 1
    assert len(result["scores"]) == 2
    assert result["scores"][1]["kept"] is False
    assert result["survivors"][0]["candidate_id"] == "a"
    assert result["result_list"][0]["doc_path"] == "docs/a.md"
    assert result["status"] == "error"
    assert result["real_engine"] is False


def test_missing_real_configuration_is_unavailable_not_keep_all():
    result = jev.filter_candidates(
        {"query": "What is the result?", "candidates": [candidate("a", "text", 1)]},
        env={},
    )
    assert result["status"] == "unavailable"
    assert result["engine"] == "laya"
    assert result["real_engine"] is False
    assert result["survivors"] == []
    assert result["evidence_pack"] == ""


def test_aggregate_orders_and_deduplicates_with_provenance():
    first = candidate("b", "second", 20)
    duplicate = {**first, "candidate_id": "duplicate", "text": "second"}
    earlier = candidate("a", "first", 10)
    packed = jev.aggregate_survivors([first, duplicate, earlier], max_chars=1000)
    assert packed["deduped_count"] == 2
    assert packed["included_count"] == 2
    assert packed["evidence_pack"].index("first") < packed["evidence_pack"].index("second")
    assert [p["candidate_id"] for p in packed["provenance"]] == ["a", "b"]
    assert packed["provenance"][0]["start_line"] == 10


def test_aggregate_reports_budget_truncation():
    result = jev.filter_candidates(
        {"query": "What?", "max_evidence_chars": 40,
         "candidates": [candidate("a", "a long evidence passage", 1), candidate("b", "another passage", 20)]},
        score_fn=lambda q, text, criterion: (0.9, {"offline": True}),
    )
    assert result["truncated_candidate_ids"]
    assert result["provenance"]
    assert result["evidence_chars"] <= 40


def test_invalid_score_is_rejected():
    result = jev.filter_candidates(
        {"query": "What?", "candidates": [candidate("a", "text", 1)]},
        score_fn=lambda q, text, criterion: (1.5, {"offline": True}),
    )
    assert result["status"] == "unavailable"
    assert result["scores"][0]["score"] is None
    assert result["survivors"] == []


def test_default_laya_sdk_is_used_for_every_candidate(monkeypatch):
    calls = []

    class FakeAgent:
        def predict(self, state, questions):
            calls.append((state, questions))
            return {"answers": {"evidence": {"noul": 0.8}}}

    class FakeLaya:
        @staticmethod
        def load(model, **kwargs):
            assert model == "convaiinnovations/laya"
            return FakeAgent()

    monkeypatch.setitem(sys.modules, "laya", FakeLaya)
    jev._LAYA_AGENT = None
    jev._LAYA_AGENT_KEY = None
    result = jev.filter_candidates({
        "query": "What?",
        "candidates": [candidate("a", "first", 1), candidate("b", "second", 5)],
    }, env={})
    assert result["engine"] == "laya"
    assert result["backend"] == "laya_sdk"
    assert result["real_engine"] is True
    assert result["real_jev"] is False
    assert len(calls) == 2
    assert {r["doc_path"] for r in result["result_list"]} == {"docs/a.md", "docs/b.md"}


def test_laya_failure_does_not_fallback_to_jev(monkeypatch):
    class BrokenLaya:
        @staticmethod
        def load(model, **kwargs):
            raise RuntimeError("model missing")

    monkeypatch.setitem(sys.modules, "laya", BrokenLaya)
    jev._LAYA_AGENT = None
    jev._LAYA_AGENT_KEY = None
    result = jev.filter_candidates({"query": "What?", "candidates": [candidate("a", "x", 1)]}, env={})
    assert result["status"] == "unavailable"
    assert result["engine"] == "laya"
    assert result["survivors"] == []


def test_invalid_engine_is_rejected():
    result = jev.filter_candidates({"engine": "unknown", "query": "What?", "candidates": []})
    assert result["status"] == "error"
    assert result["result_list"] == []
