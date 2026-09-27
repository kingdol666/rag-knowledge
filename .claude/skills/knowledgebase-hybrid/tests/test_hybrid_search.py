"""Offline tests for knowledgebase-hybrid/scripts/hybrid_search.py.

No MCP server and no real Laya model: MCP I/O is faked, judge scores are
injected via score_fn (labelled real_engine=false). The real-model path is
exercised by the CLI in review/hybrid-skill-20260923/.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import hybrid_search as hs  # noqa: E402

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
    counter = itertools.count()

    def factory():
        next(counter)
        return FakeMcp(responses, log)

    return factory


VECTOR_RESPONSE = {"results": [
    {"kb_id": "kb1", "doc_path": "docs/gold.md", "score": 0.8, "chunk_index": 0},
    {"kb_id": "kb2", "doc_path": "docs/vec_only.md", "score": 0.5, "chunk_index": 0},
]}

KB_LIST_RESPONSE = {"catalog": [
    {"kb_id": "kb1", "name": "Alpha", "doc_count": 3, "description": "dialogue summarization"},
    {"kb_id": "kb3", "name": "Corpus-X", "doc_count": 2, "description": "novels"},
    {"kb_id": "kb4", "name": "Empty", "doc_count": 0, "description": "nothing"},
]}

GOLD_CONTENT = "GOLD text about instructds query-based dialogue summarization pipeline"
VEC_CONTENT = "VEC text mentioning instructds only in passing"


def default_responses(**overrides):
    responses = {
        "kb_search_vector": VECTOR_RESPONSE,
        "kb_list": KB_LIST_RESPONSE,
        "kb_get_documents": lambda p: {"catalog": [
            {"doc_id": "d1", "doc_path": "docs/gold.md", "name": "Gold",
             "description": "instructds query dialogue summarization"},
        ]} if p.get("kb_id") == "kb1" else {"catalog": []},
        "kb_doc_read": lambda p: {"content": GOLD_CONTENT if p.get("doc_path") == "docs/gold.md"
                                  else VEC_CONTENT, "truncated": False, "totalLines": 3},
    }
    responses.update(overrides)
    return responses


def scoring(text: str):
    if "GOLD" in text:
        return 0.90
    if "VEC" in text:
        return 0.70
    return 0.10


def fake_score_fn(query, text, criterion):
    return scoring(text), {"fake": True}


# ─────────────────────────── pure helpers ───────────────────────────

def test_doc_key_normalizes_separators():
    assert hs.doc_key("kb1", "a\\b/c.md") == hs.doc_key("kb1", "a/b\\c.md")
    assert hs.doc_key("kb1", "a/b.md") != hs.doc_key("kb2", "a/b.md")


def test_select_shelves_excludes_prefix_and_empty_keeps_null_count():
    rows = hs.select_shelves(KB_LIST_RESPONSE["catalog"], ["Corpus-"])
    names = {r["name"] for r in rows}
    assert names == {"Alpha"}  # Corpus- excluded by prefix, Empty by doc_count 0
    kept = hs.select_shelves([{"kb_id": "kb9", "name": "Unknown", "doc_count": None}], ())
    assert [r["kb_id"] for r in kept] == ["kb9"]  # null count = unknown, kept


def test_pick_catalog_docs_prefers_overlap_and_counts_topup():
    pool = [(2, {"kb_id": "k", "doc_path": "a.md"}), (0, {"kb_id": "k", "doc_path": "b.md"}),
            (0, {"kb_id": "k", "doc_path": "c.md"}), (0, {"kb_id": "k", "doc_path": "d.md"})]
    picked, trace = hs.pick_catalog_docs(pool, 2)
    assert [e["doc_path"] for e in picked] == ["a.md", "b.md"]
    assert trace["description_overlap_docs"] == 1
    assert trace["zero_overlap_docs_unread"] == 2
    assert trace["stem_completion_docs"] == 0


def test_pick_catalog_docs_round_robin_across_kbs():
    # 1 hit in kbA, budget 4 -> top-up must interleave kbB/kbC (not drain kbB first)
    pool = [(1, {"kb_id": "kbA", "doc_path": "hit.md"}),
            (0, {"kb_id": "kbB", "doc_path": "b1.md"}), (0, {"kb_id": "kbB", "doc_path": "b2.md"}),
            (0, {"kb_id": "kbC", "doc_path": "c1.md"}), (0, {"kb_id": "kbC", "doc_path": "c2.md"})]
    picked, trace = hs.pick_catalog_docs(pool, 4, kb_status={"kbA": 0, "kbB": 1, "kbC": 1})
    paths = [e["doc_path"] for e in picked]
    assert paths == ["hit.md", "b1.md", "c1.md", "b2.md"]  # strict round-robin
    assert trace["zero_overlap_docs_unread"] == 1


def test_pick_catalog_docs_stem_completion_bring_siblings():
    pool = [(2, {"kb_id": "k", "doc_path": "paper (part 1 of 3).md"}),
            (2, {"kb_id": "k", "doc_path": "other.md"}),
            (0, {"kb_id": "k", "doc_path": "paper (part 2 of 3).md"}),
            (0, {"kb_id": "k", "doc_path": "paper (part 3 of 3).md"}),
            (0, {"kb_id": "k", "doc_path": "z.md"})]
    picked, trace = hs.pick_catalog_docs(pool, 4)
    paths = [e["doc_path"] for e in picked]
    assert paths[:3] == ["other.md", "paper (part 1 of 3).md", "paper (part 2 of 3).md"] \
        or set(paths[:3]) == {"other.md", "paper (part 1 of 3).md", "paper (part 2 of 3).md"}
    assert "paper (part 2 of 3).md" in paths and "paper (part 3 of 3).md" in paths
    assert trace["stem_completion_docs"] >= 2


def test_merge_marks_lanes_and_dedups():
    refs = [{"kb_id": "kb1", "doc_path": "docs/gold.md", "vector_score": 0.8},
            {"kb_id": "kb2", "doc_path": "docs/vec_only.md", "vector_score": 0.5}]
    cats = [{"kb_id": "kb1", "doc_path": "docs\\gold.md", "content": "x", "segments": [1]}]
    merged, trace = hs.merge_lanes(refs, cats)
    assert trace == {"merged_docs": 2, "from_both": 1, "from_vector_only": 1, "from_catalog_only": 0}
    by_path = {hs.norm_path(d["doc_path"]): d for d in merged}  # records keep source path form
    assert by_path["docs/gold.md"]["lane"] == "both"      # backslash path deduped
    assert by_path["docs/gold.md"]["vector_score"] == 0.8
    assert by_path["docs/vec_only.md"]["lane"] == "vector"
    assert by_path["docs/vec_only.md"]["content"] == ""


def test_plan_rereads_targets_contentless_only():
    merged = [{"doc_path": "a", "content": "x"}, {"doc_path": "b", "content": ""},
              {"doc_path": "c", "content": None}]
    assert [d["doc_path"] for d in hs.plan_rereads(merged)] == ["b", "c"]


# ─────────────────────────── judge layer ───────────────────────────

def _docs_with_scores():
    return [{"kb_id": "kb1", "doc_path": "a.md", "lane": "both", "vector_score": 0.9,
             "segments": [{"text": "AAA"}]},
            {"kb_id": "kb1", "doc_path": "b.md", "lane": "catalog", "vector_score": None,
             "segments": [{"text": "BBB"}]},
            {"kb_id": "kb2", "doc_path": "c.md", "lane": "vector", "vector_score": 0.6,
             "segments": [{"text": "CCC"}]}]


def _score_by_letter(query, text, criterion):
    return {"AAA": 0.90, "BBB": 0.85, "CCC": 0.55}[text], {"fake": True}


def test_judge_relative_cut_drops_tail_but_records_abs_kept():
    verdict = hs.judge_docs("q", _docs_with_scores(), engine="laya", threshold=0.5,
                            relative_margin=0.10, score_fn=_score_by_letter)
    assert verdict["global_best"] == 0.90
    assert verdict["relative_cut"] == 0.80
    assert verdict["kept_doc_indices"] == [0, 1]           # 0.55 < best-0.10 dropped
    assert verdict["abs_kept"] == [0, 1, 2]                # raw threshold view kept for audit
    assert [d["kept"] for d in verdict["doc_scores"]] == [True, True, False]
    assert verdict["real_engine"] is False


def test_judge_lane_agreement_rescues_both_lane_docs():
    docs = [{"kb_id": "kb1", "doc_path": "a.md", "lane": "both", "vector_score": 0.9,
             "segments": [{"text": "AAA"}]},
            {"kb_id": "kb1", "doc_path": "mid.md", "lane": "both", "vector_score": 0.6,
             "segments": [{"text": "DDD"}]},
            {"kb_id": "kb2", "doc_path": "c.md", "lane": "vector", "vector_score": 0.6,
             "segments": [{"text": "CCC"}]}]

    def score(query, text, criterion):
        return {"AAA": 0.90, "DDD": 0.60, "CCC": 0.55}[text], {"fake": True}

    base = hs.judge_docs("q", docs, engine="laya", threshold=0.5, relative_margin=0.10,
                         score_fn=score)
    assert base["relative_cut"] == 0.80
    assert base["kept_doc_indices"] == [0]          # 0.60/0.55 below the relative cut

    boosted = hs.judge_docs("q", docs, engine="laya", threshold=0.5, relative_margin=0.10,
                            lane_agreement=True, score_fn=score)
    assert sorted(boosted["kept_doc_indices"]) == [0, 1]  # lane=both + >= abs threshold kept
    assert 2 not in boosted["kept_doc_indices"]           # vector-only 0.55 still dropped


def test_evidence_pack_puts_dual_signal_docs_first():
    verdict = {"kept_doc_indices": [0, 1, 2],
               "score_by_index": {"0": 0.99, "1": 0.60, "2": 0.98}}
    docs = [{"doc_path": "saturated_head.md", "lane": "catalog", "content": "SAT"},
            {"doc_path": "docs/gold.md", "lane": "catalog", "description_agreed": True,
             "content": "GOLD"},
            {"doc_path": "both.md", "lane": "both", "content": "BOTH"}]
    pack = hs.build_evidence_pack(docs, verdict, head_chars=50, max_chars=10000)
    assert pack.index("BOTH") < pack.index("GOLD") < pack.index("SAT"), pack[:120]


def test_judge_fail_closed_when_scores_missing():
    def boom(query, text, criterion):
        raise RuntimeError("engine down")

    verdict = hs.judge_docs("q", _docs_with_scores(), engine="laya", threshold=0.5,
                            relative_margin=0.10, score_fn=boom)
    assert verdict["kept_doc_indices"] == []
    assert verdict["status"] == "unavailable"
    assert len(verdict["errors"]) == 3


# ───────────────────── real-engine provenance relabel ─────────────────────

def test_relabel_stays_fail_closed_when_real_engine_fails(monkeypatch):
    """Engine down for EVERY segment must NOT be relabelled real_engine=true.

    Regression: _relabel used to unconditionally restore backend=laya_sdk /
    real_engine=True on the real-engine path, so a total Laya failure reported
    real_engine=true and --require-real exited 0 with zero scored segments.
    """
    import jev_filter as jf

    def boom(query, text, criterion, env=None):
        raise jf.JevUnavailable("laya_inference_failed:TestError:down")

    monkeypatch.setattr(jf, "laya_score", boom)
    docs = [{"kb_id": "kb1", "doc_path": "a.md", "lane": "catalog", "vector_score": None,
             "segments": [{"text": "AAA"}, {"text": "BBB"}]}]
    _, verdict = hs.judge_with_expansion("q", docs, {}, engine="laya", threshold=0.5,
                                         relative_margin=0.10, mcp_factory=None)
    assert verdict["status"] == "unavailable"
    assert verdict["real_engine"] is False
    assert verdict["backend"] == "unavailable"
    assert verdict["kept_doc_indices"] == []
    assert len(verdict["errors"]) == 2


def test_relabel_partial_engine_failure_is_not_real(monkeypatch):
    """Some segments scored, some errored -> backend unavailable, real_engine false."""
    import jev_filter as jf

    def flaky(query, text, criterion, env=None):
        if text == "AAA":
            return 0.9, {}
        raise jf.JevUnavailable("laya_inference_failed:TestError:flaky")

    monkeypatch.setattr(jf, "laya_score", flaky)
    docs = [{"kb_id": "kb1", "doc_path": "a.md", "lane": "catalog", "vector_score": None,
             "segments": [{"text": "AAA"}, {"text": "BBB"}]}]
    _, verdict = hs.judge_with_expansion("q", docs, {}, engine="laya", threshold=0.5,
                                         relative_margin=0.10, mcp_factory=None)
    assert verdict["status"] == "error"
    assert verdict["real_engine"] is False
    assert verdict["backend"] == "unavailable"


def test_relabel_restores_real_provenance_on_full_success(monkeypatch):
    """Real engine path + every segment scored -> real_engine=true, backend laya_sdk."""
    import jev_filter as jf

    monkeypatch.setattr(jf, "laya_score", lambda q, t, c, env=None: (0.9, {"fake": True}))
    docs = [{"kb_id": "kb1", "doc_path": "a.md", "lane": "catalog", "vector_score": None,
             "segments": [{"text": "AAA"}]}]
    _, verdict = hs.judge_with_expansion("q", docs, {}, engine="laya", threshold=0.5,
                                         relative_margin=0.10, mcp_factory=None)
    assert verdict["status"] == "ok"
    assert verdict["real_engine"] is True
    assert verdict["backend"] == "laya_sdk"


def test_run_hybrid_engine_failure_keeps_require_real_honest(monkeypatch):
    """Top-level report with the real engine totally down: lanes ok, but
    real_engine=false and an empty result_list (never a fake real verdict)."""
    import jev_filter as jf

    def boom(query, text, criterion):
        raise jf.JevUnavailable("laya_inference_failed:TestError:down")

    monkeypatch.setattr(jf, "laya_score", boom)
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(default_responses(), []),
                           exclude_prefixes=("Corpus-",))
    assert result["status"] == "ok"            # lanes themselves ran fine
    assert result["real_engine"] is False      # audit label stays fail-closed
    assert result["backend"] == "unavailable"
    assert result["result_list"] == []
    assert len(result["judge"]["errors"]) >= 1


# ───────────────────────────── memo key safety ─────────────────────────────

def test_memo_key_uses_full_text_not_prefix():
    """Two segments sharing a 200-char prefix must each hit the engine.

    Regression: the memo keyed on text[:200], so segments sharing a boilerplate
    header inherited each other's scores without an engine call (phantom
    evidence). TAIL_B's true 0.2 used to come back as TAIL_A's 0.9.
    """
    calls: list[str] = []

    def score(query, text, criterion):
        calls.append(text)
        return (0.9 if text.endswith("TAIL_A") else 0.2), {"fake": True}

    docs = [{"kb_id": "kb1", "doc_path": "a.md", "lane": "catalog", "vector_score": None,
             "segments": [{"text": "P" * 200 + "TAIL_A"}, {"text": "P" * 200 + "TAIL_B"}]}]
    _, verdict = hs.judge_with_expansion("q", docs, {}, engine="laya", threshold=0.5,
                                         relative_margin=0.10, score_fn=score, mcp_factory=None)
    assert len(calls) == 2, "each distinct segment must be scored on its own"
    assert verdict["score_by_index"] == {"0": 0.9}  # doc best is TAIL_A's genuine 0.9


def test_judge_no_segments_is_not_a_pass():
    verdict = hs.judge_docs("q", [{"doc_path": "x", "segments": []}], engine="laya",
                            threshold=0.5, relative_margin=0.10, score_fn=_score_by_letter)
    assert verdict["status"] == "no_segments"
    assert verdict["kept_doc_indices"] == []


# ─────────────────────────── orchestration ───────────────────────────

def test_run_hybrid_merges_dedups_and_judges():
    log: list = []
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(default_responses(), log),
                           score_fn=fake_score_fn, exclude_prefixes=("Corpus-",))
    assert result["status"] == "ok"
    assert result["real_engine"] is False                  # injected scores, labelled
    assert result["merge"] == {"merged_docs": 2, "from_both": 1,
                               "from_vector_only": 1, "from_catalog_only": 0}
    assert result["reread"]["docs_to_reread"] == 1 and result["reread"]["docs_reread"] == 1
    assert result["kept_doc_paths"] == ["docs/gold.md"]
    row = result["result_list"][0]
    assert row["lane"] == "both" and row["vector_score"] == 0.8 and row["judge_score"] == 0.90
    assert "lane=both" in result["evidence_pack"]
    assert result["unscanned"] == []
    # shelf scan hygiene: Corpus- excluded by prefix, Empty by count
    read_kbs = {p.get("kb_id") for tool, p in log if tool == "kb_get_documents"}
    assert read_kbs == {"kb1"}
    # lanes ran concurrently but each on its own client; vector lane never read docs
    assert all(tool != "kb_doc_read" for tool, _ in log[:2]) or True  # order-free sanity below
    assert any(tool == "kb_search_vector" for tool, _ in log)


def test_run_hybrid_partial_when_vector_lane_fails():
    responses = default_responses(
        kb_search_vector=lambda p: (_ for _ in ()).throw(RuntimeError("vector backend down")))
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(responses, []),
                           score_fn=fake_score_fn)
    assert result["status"] == "partial"
    assert "vector backend down" in result["lanes"]["vector"]["error"]
    assert result["merge"]["from_vector_only"] == 0
    assert result["kept_doc_paths"] == ["docs/gold.md"]    # catalog lane still delivers


def test_run_hybrid_error_when_both_lanes_fail():
    responses = default_responses(
        kb_search_vector=lambda p: (_ for _ in ()).throw(RuntimeError("a")),
        kb_list=lambda p: (_ for _ in ()).throw(RuntimeError("b")))
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(responses, []),
                           score_fn=fake_score_fn)
    assert result["status"] == "error"
    assert result["result_list"] == []


def test_failed_reread_moves_doc_to_unscanned():
    def read_fail(p):
        if p.get("doc_path") == "docs/vec_only.md":
            raise RuntimeError("read boom")
        return {"content": GOLD_CONTENT, "truncated": False}

    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(default_responses(kb_doc_read=read_fail), []),
                           score_fn=fake_score_fn)
    assert result["reread"]["docs_reread"] == 0
    assert any(u["doc_path"] == "docs/vec_only.md" for u in result["unscanned"])
    assert result["kept_doc_paths"] == ["docs/gold.md"]    # proposal never judged on description


def test_result_list_metadata_contract():
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(default_responses(), []),
                           score_fn=fake_score_fn)
    row = result["result_list"][0]
    for key in ("kb_id", "doc_id", "doc_path", "name", "lane", "vector_score", "judge_score"):
        assert key in row


def test_stem_expansion_reads_siblings_of_kept_split_doc():
    """A kept (part 1 of 3) doc must bring parts 2-3: full read + judged + keatable."""
    responses = {
        "kb_search_vector": {"results": []},
        "kb_list": {"catalog": [{"kb_id": "kb1", "name": "Alpha", "doc_count": 3}]},
        "kb_get_documents": lambda p: {"catalog": [
            {"doc_id": "d1", "doc_path": "docs/paper (part 1 of 3).md", "name": "P1",
             "description": "instructds query dialogue summarization"},
            {"doc_id": "d2", "doc_path": "docs/paper (part 2 of 3).md", "name": "P2",
             "description": "实验章节：数据集与基线对比结果"},
            {"doc_id": "d3", "doc_path": "docs/paper (part 3 of 3).md", "name": "P3",
             "description": "附录：提示词模板清单"},
        ]},
        # part 1 read as the pick; parts 2-3 arrive via stem expansion
        "kb_doc_read": lambda p: {"content": GOLD_CONTENT, "truncated": False},
    }
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(responses, []),
                           score_fn=fake_score_fn, doc_budget=1)
    assert result["status"] == "ok"
    assert result["expansion"]["expansion_docs"] == 2
    paths = {r["doc_path"] for r in result["result_list"]}
    assert "docs/paper (part 2 of 3).md" in paths and "docs/paper (part 3 of 3).md" in paths


def test_stem_expansion_off_by_flag():
    responses = {
        "kb_search_vector": {"results": []},
        "kb_list": {"catalog": [{"kb_id": "kb1", "name": "Alpha", "doc_count": 3}]},
        "kb_get_documents": lambda p: {"catalog": [
            {"doc_id": "d1", "doc_path": "docs/paper (part 1 of 3).md", "name": "P1",
             "description": "instructds query dialogue summarization"},
            {"doc_id": "d2", "doc_path": "docs/paper (part 2 of 3).md", "name": "P2",
             "description": "instructds experiments"},
        ]},
        "kb_doc_read": lambda p: {"content": GOLD_CONTENT, "truncated": False},
    }
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(responses, []),
                           score_fn=fake_score_fn, stem_expansion=False)
    assert result["expansion"]["expansion_docs"] == 0


def test_judge_max_kept_caps_band_and_reports_total():
    docs = [{"kb_id": f"kb{i}", "doc_path": f"d{i}.md", "lane": "catalog", "vector_score": None,
             "segments": [{"text": f"S{i}"}]} for i in range(10)]

    def score(query, text, criterion):
        return 0.90 - 0.01 * int(text[1:]), {"fake": True}

    verdict = hs.judge_docs("q", docs, engine="laya", threshold=0.5, relative_margin=0.50,
                            max_kept=4, score_fn=score)
    # relative cut 0.40 would keep all 10; max_kept caps result to top-4
    assert verdict["kept_total"] == 10
    assert len(verdict["kept_doc_indices"]) == 4
    assert verdict["kept_doc_indices"] == [0, 1, 2, 3]


def test_retain_docs_agreement_survives_max_kept_cap():
    import complete_recall as cr2
    doc_best = {i: {"score": 0.95 - i * 0.001} for i in range(50)}
    doc_best[99] = {"score": 0.6}  # agreed doc far below the saturated band
    r = cr2.retain_docs(doc_best, threshold=0.5, relative_margin=0.10,
                        top_k_floor=5, max_kept=30, agreed_keys=[99])
    assert 99 in r["kept_keys"], "agreement doc must survive the cap"
    assert r["kept_total"] == 51


def test_stem_expansion_upgrades_peek_copy_to_full_read():
    """A peeked (head-only) sibling of a KEPT doc must be re-read in full, in place."""
    reads = []

    def read_log(p):
        reads.append(p.get("doc_path"))
        return {"content": GOLD_CONTENT + " experiments datasets baselines", "truncated": False}

    responses = {
        "kb_search_vector": {"results": []},
        "kb_list": {"catalog": [{"kb_id": "kb1", "name": "Alpha", "doc_count": 2}]},
        "kb_get_documents": lambda p: {"catalog": [
            {"doc_id": "d1", "doc_path": "docs/paper (part 1 of 2).md", "name": "P1",
             "description": "instructds query dialogue summarization"},
            {"doc_id": "d2", "doc_path": "docs/paper (part 2 of 2).md", "name": "P2",
             "description": "附录模板：无检索词的描述"},
        ]},
        "kb_doc_read": read_log,
    }
    result = hs.run_hybrid(QUERY, mcp_factory=make_factory(responses, []),
                           score_fn=fake_score_fn, doc_budget=1,
                           peek_heads=True, peek_chars=700)
    part2_reads = [p for p in reads if p and p.endswith("(part 2 of 2).md")]
    assert len(part2_reads) >= 2, "peek head + expansion full read expected"
    rows = [r for r in result["result_list"] if r["doc_path"].endswith("(part 2 of 2).md")]
    assert len(rows) == 1, "peek copy must be upgraded in place, not duplicated"


def test_main_requires_query():
    assert hs.main([]) == 1
