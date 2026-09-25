"""Offline tests for complete-recall catalog-to-Jev orchestration."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("complete_recall", SCRIPT_DIR / "complete_recall.py")
assert SPEC and SPEC.loader
complete = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(complete)


def _manifest() -> dict:
    return {
        "query": "transformer evidence for retrieval grounding",
        "max_segment_chars": 80,
        "knowledge_bases": [
            {"kb_id": "kb-relevant", "name": "Retrieval", "description": "transformer retrieval grounding"},
            {"kb_id": "kb-possible", "name": "Unlabelled shelf", "description": ""},
            {"kb_id": "kb-out", "name": "Cooking", "description": "recipes ingredients"},
        ],
        "documents": [
            {
                "kb_id": "kb-relevant", "doc_id": "d1", "doc_path": "Retrieval/a.md",
                "name": "a.md", "description": "wrong boilerplate",
                "content": "## Evidence\n\nTransformer retrieval grounding result one.\n\nSecond result.",
            },
            {
                "kb_id": "kb-possible", "doc_id": "d2", "doc_path": "Unlabelled/b.md",
                "name": "b.md", "description": "",
                "content": "A possible shelf contains another grounding result.",
            },
            {
                "kb_id": "kb-relevant", "doc_id": "d3", "doc_path": "Retrieval/c.md",
                "name": "c.md", "description": "candidate but body unavailable",
                "content": "",
            },
            {
                "kb_id": "kb-out", "doc_id": "d4", "doc_path": "Cooking/d.md",
                "name": "d.md", "description": "recipes ingredients",
                "content": "irrelevant body should not enter the retained shelves.",
            },
        ],
    }


def test_complete_mode_keeps_relevant_and_possible_shelves():
    prepared = complete.build_manifest_candidates(_manifest(), max_chars=80)
    kept = {row["kb_id"] for row in prepared["catalog"] if row["catalog_status"] != "out_of_scope"}
    assert kept == {"kb-relevant", "kb-possible"}
    assert all(candidate["kb_id"] in kept for candidate in prepared["candidates"])
    assert any(row.get("description_trust") == "untrusted" for row in prepared["documents"])


def test_every_candidate_segment_is_sent_to_jev_and_keeps_offsets():
    prepared = complete.build_manifest_candidates(_manifest(), max_chars=40)
    seen: list[str] = []

    def score(query, text, criterion):
        seen.append(text)
        return 0.8, {"offline": True}

    manifest = _manifest()
    manifest["engine"] = "laya"
    result = complete.run_manifest(manifest, score_fn=score)
    assert result["candidate_count"] == len(result["candidates"])
    assert len(seen) == result["candidate_count"]
    assert result["jev"]["scored_count"] == result["candidate_count"]
    assert result["engine"] == "laya"
    assert result["result_list"]
    assert result["result_list"][0]["doc_path"]
    assert result["unscanned"] == [{
        "kb_id": "kb-relevant", "doc_id": "d3", "doc_path": "Retrieval/c.md",
        "reason": "content_missing",
    }]


def test_no_key_is_not_a_pass_through():
    result = complete.run_manifest(_manifest(), env={})
    assert result["jev"]["status"] == "unavailable"
    assert result["survivors"] == []
    assert result["evidence_pack"] == ""


def test_catalog_without_matching_vocabulary_expands_high_recall():
    manifest = _manifest()
    manifest["query"] = "完全不同的术语"
    prepared = complete.build_manifest_candidates(manifest)
    statuses = {row["catalog_status"] for row in prepared["catalog"]}
    assert "possible" in statuses
    assert prepared["candidate_count"] > 0
    assert any(row.get("catalog_reason") == "no_catalog_overlap; high-recall expansion"
               for row in prepared["catalog"] if row["catalog_status"] == "possible")
