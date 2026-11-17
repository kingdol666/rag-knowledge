"""Hermetic coverage of two-stage budgets, provenance and BM25 concurrency."""
import asyncio
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config import config
from app.models.search_models import TwoStageSearchRequest
from app.services import two_stage_search_service as ts
from app.services.storage_reader_service import storage_reader


@pytest.fixture
def search_setup(monkeypatch):
    monkeypatch.setitem(config._config, "graph", {"enabled": False})
    monkeypatch.setitem(config._config, "search", {"two_stage": {
        "stage1_keyword_weight": 0.5, "stage1_graph_weight": 0.5,
        "min_candidates": 3, "kb_aware_candidates": False,
    }})
    monkeypatch.setattr(ts.TwoStageSearchService, "_ensure_keyword_index", lambda *args: None)
    monkeypatch.setattr(storage_reader, "read_document_content", lambda path, max_chars: "text: " + path)
    return ts.TwoStageSearchService()


def _keywords(monkeypatch, rows):
    monkeypatch.setattr(ts.keyword_index_service, "search", lambda *args, **kwargs: rows)


def test_normal_vector_results_and_timings(search_setup, monkeypatch):
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 2, "kb_id": "kid"}])
    monkeypatch.setattr(ts.vector_service, "search", lambda **kw: [
        {"doc_path": "kb/a", "score": .9, "content": "hit", "kb_id": "kid"}])
    result = search_setup.search("q", vector_budget_ms=1000)
    assert result["stage2"]["results"][0]["score_source"] == "vector"
    assert result["stage2"]["results"][0]["stage1_sources"] == ["keyword"]
    assert result["retrieval"]["degraded"] is False
    assert result["retrieval"]["vector_status"] == "completed"
    assert set(result["retrieval"]["timings_ms"]) == {
        "bm25_build", "bm25_search", "graph", "stage1", "vector", "total"}
    assert all(value >= 0 for value in result["retrieval"]["timings_ms"].values())


def test_zero_candidates_never_broaden(search_setup, monkeypatch):
    _keywords(monkeypatch, [])
    monkeypatch.setattr(ts.vector_service, "search", lambda **kw: pytest.fail("vector invoked"))
    result = search_setup.search("nothing", vector_budget_ms=0)
    assert result["total_results"] == 0
    assert result["retrieval"]["degraded"] is False
    assert result["retrieval"]["vector_status"] == "skipped_no_candidates"


def test_bm25_failure_does_not_appear_as_no_match(search_setup, monkeypatch):
    def fail(*args):
        raise RuntimeError("failed")
    monkeypatch.setattr(search_setup, "_ensure_keyword_index", fail)
    _keywords(monkeypatch, [{"doc_path": "stale", "score": 10}])
    result = search_setup.search("q")
    assert result["total_results"] == 0
    assert result["retrieval"]["degraded_reasons"] == ["bm25_build_failed"]
    assert result["retrieval"]["bm25_status"] == "failed"


def test_vector_empty_and_failure_use_explicit_fallback(search_setup, monkeypatch):
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 4, "kb_id": "kid"}])
    monkeypatch.setattr(ts.vector_service, "search", lambda **kw: [])
    result = search_setup.search("q")
    hit = result["stage2"]["results"][0]
    assert result["retrieval"]["degraded_reasons"] == ["vector_empty_fallback"]
    assert hit["score_source"] == "stage1" and hit["score"] == 4
    assert hit["kb_id"] == "kid" and hit["content"] == "text: kb/a"
    def fail(**kwargs):
        raise RuntimeError("vector error")
    monkeypatch.setattr(ts.vector_service, "search", fail)
    assert search_setup.search("q")["retrieval"]["degraded_reasons"] == ["vector_failed"]


def test_worker_timeout_exception_is_a_failure(search_setup, monkeypatch):
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 1}])
    def fail(**kwargs):
        raise TimeoutError("underlying vector timeout")
    monkeypatch.setattr(ts.vector_service, "search", fail)
    result = search_setup.search("q", vector_budget_ms=1000)
    assert result["retrieval"]["vector_status"] == "failed"
    assert result["retrieval"]["degraded_reasons"] == ["vector_failed"]


def test_scope_resolution_failure_is_degraded(search_setup, monkeypatch):
    _keywords(monkeypatch, [])
    def fail(*args):
        raise RuntimeError("scope unavailable")
    monkeypatch.setattr(storage_reader, "resolve_kb_ids_with_children", fail)
    result = search_setup.search("q", kb_id="kb")
    assert result["retrieval"]["degraded_reasons"] == ["kb_scope_resolution_failed"]
    assert result["retrieval"]["vector_status"] == "skipped_no_candidates"


def test_real_config_preserves_ingestion_limit(monkeypatch):
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[2]
    with (root / "config.yml").open(encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file)
    assert loaded["ingestion"]["large_doc"]["max_chars"] == 60000


def test_real_loaded_config_budgets_are_finite_and_service_uses_them(search_setup, monkeypatch):
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[2]
    with (root / "config.yml").open(encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file)
    search_config = loaded["search"]["two_stage"]
    assert search_config["graph_budget_ms"] == 1000
    assert search_config["vector_budget_ms"] == 5000
    # Exercise the production loader, not just YAML parsing or injected config.
    monkeypatch.setattr(config, "_config", None)
    config.reload()
    assert config.two_stage_config["graph_budget_ms"] == 1000
    assert config.two_stage_config["vector_budget_ms"] == 5000
    monkeypatch.setitem(config._config, "graph", {"enabled": False})
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 1}])
    monkeypatch.setattr(ts.vector_service, "search", lambda **kwargs: [
        {"doc_path": "kb/a", "score": .8}])
    result = search_setup.search("q")
    assert result["retrieval"]["graph_status"] == "disabled"
    assert result["retrieval"]["vector_status"] == "completed"


def test_quoted_none_config_falls_back_to_safe_finite_budgets(search_setup, monkeypatch):
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 1}])
    config._config["search"]["two_stage"].update({
        "graph_budget_ms": "None", "vector_budget_ms": "None"})
    monkeypatch.setattr(ts.vector_service, "search", lambda **kwargs: [
        {"doc_path": "kb/a", "score": .8}])
    result = search_setup.search("q")
    assert result["retrieval"]["vector_status"] == "completed"
    assert config._config["search"]["two_stage"]["graph_budget_ms"] == "None"


def test_config_budgets_and_request_override(search_setup, monkeypatch):
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 1}])
    config._config["search"]["two_stage"]["vector_budget_ms"] = 0
    monkeypatch.setattr(ts.vector_service, "search", lambda **kwargs: [
        {"doc_path": "kb/a", "score": .8}])
    assert search_setup.search("q")["retrieval"]["vector_status"] == "budget_exhausted"
    assert search_setup.search("q", vector_budget_ms=1000)["retrieval"]["vector_status"] == "completed"


def test_vector_timeout_capacity_and_recovery(search_setup, monkeypatch):
    runner = ts._BoundedStageRunner(1)
    monkeypatch.setattr(ts, "_vector_runner", runner)
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 1}])
    started, release = threading.Event(), threading.Event()
    calls = []
    def slow(**kwargs):
        calls.append(1)
        started.set()
        assert release.wait(5)
        return [{"doc_path": "kb/a", "score": .8}]
    monkeypatch.setattr(ts.vector_service, "search", slow)
    try:
        result = search_setup.search("q", vector_budget_ms=50)
        assert started.is_set()
        assert result["retrieval"]["vector_status"] == "timeout"
        assert result["stage2"]["results"][0]["score_source"] == "stage1"
        result = search_setup.search("q", vector_budget_ms=50)
        assert result["retrieval"]["vector_status"] == "capacity_exhausted"
        assert len(calls) == 1
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_runner_slot_recovers_after_timed_out_work_finishes():
    runner = ts._BoundedStageRunner(1)
    release = threading.Event()
    def slow():
        assert release.wait(5)
        return "late"
    try:
        assert runner.run(slow, 20)[0] == "timeout"
        assert runner.run(lambda: "new", 100)[0] == "capacity_exhausted"
        release.set()
        # The executor barrier ensures the timed-out task and its callback have finished.
        runner._executor.submit(lambda: None).result(timeout=5)
        assert runner.run(lambda: "new", 1000) == ("completed", "new")
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_graph_error_is_degraded_but_keeps_keyword_results(search_setup, monkeypatch):
    monkeypatch.setitem(config._config, "graph", {"enabled": True})
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 2}])
    def fail(path):
        raise RuntimeError("graph offline")
    monkeypatch.setitem(sys.modules, "app.services.graph_service", SimpleNamespace(
        graph_service=SimpleNamespace(get_related_documents=fail)))
    monkeypatch.setattr(ts.vector_service, "search", lambda **kwargs: [
        {"doc_path": "kb/a", "score": .8}])
    result = search_setup.search("q")
    assert result["total_results"] == 1
    assert result["retrieval"]["degraded_reasons"] == ["graph_failed"]


def test_graph_budget_retains_partial_expansion_and_sources(search_setup, monkeypatch):
    monkeypatch.setitem(config._config, "graph", {"enabled": True})
    _keywords(monkeypatch, [
        {"doc_path": "kb/a", "score": 4}, {"doc_path": "kb/b", "score": 3}])
    started, release = threading.Event(), threading.Event()
    def related(path):
        if path == "kb/a":
            return [{"path": "kb\\a", "reason": "agent_judged", "weight": 1},
                    {"path": "kb/c", "reason": "agent_judged", "weight": 1}]
        started.set()
        assert release.wait(5)
        return []
    monkeypatch.setitem(sys.modules, "app.services.graph_service", SimpleNamespace(
        graph_service=SimpleNamespace(get_related_documents=related)))
    runner = ts._BoundedStageRunner(1)
    monkeypatch.setattr(ts, "_graph_runner", runner)
    monkeypatch.setattr(ts.vector_service, "search_in_documents", lambda **kw: {})
    try:
        result = search_setup.search("q", graph_budget_ms=50)
        assert started.is_set()
        assert result["retrieval"]["graph_status"] == "timeout"
        candidates = {c["doc_path"]: c for c in result["stage1"]["candidates"]}
        assert candidates["kb/a"]["stage1_sources"] == ["keyword", "graph"]
        assert candidates["kb/c"]["source"] == "graph"
        hits = {h["doc_path"]: h for h in result["stage2"]["results"]}
        assert hits["kb/a"]["stage1_sources"] == ["keyword", "graph"]
        assert hits["kb/c"]["score_source"] == "stage1"
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_zero_budgets_never_start_optional_stages(search_setup, monkeypatch):
    monkeypatch.setitem(config._config, "graph", {"enabled": True})
    _keywords(monkeypatch, [{"doc_path": "kb/a", "score": 2}])
    monkeypatch.setattr(ts.vector_service, "search", lambda **kw: pytest.fail("vector invoked"))
    result = search_setup.search("q", graph_budget_ms=0, vector_budget_ms=0)
    assert set(result["retrieval"]["degraded_reasons"]) == {
        "graph_budget_exhausted", "vector_budget_exhausted"}


def test_keyword_build_single_flight_and_incremental_update(monkeypatch, tmp_path):
    svc = ts.TwoStageSearchService()
    entered, release = threading.Event(), threading.Event()
    builds, adds = [], []
    monkeypatch.setattr(type(storage_reader), "root", property(lambda self: tmp_path))
    def list_kbs():
        entered.set()
        assert release.wait(5)
        return []
    monkeypatch.setattr(storage_reader, "list_knowledge_bases", list_kbs)
    monkeypatch.setattr(ts.keyword_index_service, "build", lambda docs: builds.append(docs))
    monkeypatch.setattr(ts.keyword_index_service, "add_document", lambda doc: adds.append(doc))
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(svc._ensure_keyword_index) for _ in range(6)]
        assert entered.wait(2)
        update = pool.submit(svc.add_document, {"path": "new"})
        release.set()
        for future in futures:
            future.result(timeout=5)
        update.result(timeout=5)
    assert builds == [[]]
    assert adds == [{"path": "new"}]


def test_budgeted_vector_route_reports_capacity_degradation(monkeypatch):
    from app.api.routes import search as route
    from app.models.search_models import VectorSearchRequest
    monkeypatch.setitem(config._config, "vector", {"enabled": True})
    monkeypatch.setattr(route, "_get_vs", lambda: SimpleNamespace(search=lambda **kwargs: []))
    monkeypatch.setattr(route, "_vector_runner", SimpleNamespace(
        run=lambda func, budget: ("capacity_exhausted", None)))
    result = asyncio.run(route.vector_search(VectorSearchRequest(query="q", wait_budget_ms=5)))
    assert result["retrieval"]["degraded"] is True
    assert result["retrieval"]["degraded_reasons"] == ["vector_capacity_exhausted"]


def test_request_budget_validation_and_route_forwarding(monkeypatch):
    from app.api.routes import search as route
    for invalid in (-1, float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            TwoStageSearchRequest(query="q", vector_budget_ms=invalid)
    monkeypatch.setitem(config._config, "vector", {"enabled": True})
    seen = {}
    def fake_search(**kwargs):
        seen.update(kwargs)
        return {"retrieval": {"degraded": True}}
    monkeypatch.setattr(route.two_stage_search_service, "search", fake_search)
    result = asyncio.run(route.two_stage_search(TwoStageSearchRequest(
        query="q", graph_budget_ms=0, vector_budget_ms=25)))
    assert result["retrieval"]["degraded"] is True
    assert seen["graph_budget_ms"] == 0 and seen["vector_budget_ms"] == 25


@pytest.mark.parametrize("stall_at", ["build", "keyword_search", "keyword_lock", "fallback"])
def test_primary_route_admission_bounds_whole_search_and_recovers(stall_at, search_setup, monkeypatch):
    """A stalled stage occupies exactly one worker, including after HTTP timeout."""
    import httpx
    from fastapi import FastAPI
    from app.api.routes import search as route

    runner = ts._PrimarySearchRunner(workers=1, queue_size=0)
    monkeypatch.setattr(ts, "_primary_search_runner", runner)
    original_search_async = search_setup.search_async
    async def short_search(**kwargs):
        return await original_search_async(wait_seconds=.15, **kwargs)
    monkeypatch.setattr(search_setup, "search_async", short_search)
    monkeypatch.setattr(route, "two_stage_search_service", search_setup)
    monkeypatch.setitem(config._config, "vector", {"enabled": True})
    entered, release = threading.Event(), threading.Event()
    calls = []

    def stall():
        calls.append(1)
        entered.set()
        assert release.wait(5)

    def build(*args):
        if stall_at == "build":
            stall()

    def keyword(*args, **kwargs):
        if stall_at == "keyword_search":
            stall()
        return [{"doc_path": "kb/a", "score": 2}]

    def read(path, max_chars):
        if stall_at == "fallback":
            stall()
        return "fallback"

    monkeypatch.setattr(search_setup, "_ensure_keyword_index", build)
    monkeypatch.setattr(ts.keyword_index_service, "search", keyword)
    monkeypatch.setattr(storage_reader, "read_document_content", read)
    lock_holder = None
    if stall_at == "keyword_lock":
        def hold_lock():
            with ts._keyword_lock:
                stall()
        lock_holder = threading.Thread(target=hold_lock)
        lock_holder.start()
        assert entered.wait(2)

    app = FastAPI()
    app.include_router(route.router)

    async def exercise():
        # Fail if this path tries to queue any work in the default executor.
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "run_in_executor", lambda *args: pytest.fail("default executor used"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            request = {"query": "q", "enable_graph_expansion": False, "vector_budget_ms": 0}
            first = asyncio.create_task(client.post("/api/v1/search/two-stage", json=request))
            for _ in range(100):
                if entered.is_set() and runner._slot._value == 0:
                    break
                await asyncio.sleep(.005)
            assert entered.is_set() and runner._slot._value == 0
            others = await asyncio.gather(*[
                client.post("/api/v1/search/two-stage", json=request) for _ in range(30)])
            assert all(response.status_code == 429 for response in others)
            assert all("queue is full" in response.json()["detail"] for response in others)
            timed_out = await first
            assert timed_out.status_code == 503
            assert "may still be running" in timed_out.json()["detail"]
            assert (await client.post("/api/v1/search/two-stage", json=request)).status_code == 429
            assert len(calls) == 1
            release.set()
            for _ in range(100):
                if runner._slot._value == 1:
                    break
                await asyncio.sleep(.005)
            recovered = await client.post("/api/v1/search/two-stage", json=request)
            assert recovered.status_code == 200
            body = recovered.json()
            assert body["stage1"]["candidate_count"] == 1
            assert body["stage2"]["results"][0]["score_source"] == "stage1"
            assert body["retrieval"]["degraded_reasons"] == ["vector_budget_exhausted"]

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        if lock_holder:
            lock_holder.join(timeout=5)
        runner._executor.shutdown(wait=True)


def test_primary_route_preserves_vector_relevance_and_zero_candidate_policy(search_setup, monkeypatch):
    import httpx
    from fastapi import FastAPI
    from app.api.routes import search as route

    runner = ts._PrimarySearchRunner()
    monkeypatch.setattr(ts, "_primary_search_runner", runner)
    monkeypatch.setattr(route, "two_stage_search_service", search_setup)
    monkeypatch.setitem(config._config, "vector", {"enabled": True})
    calls = []
    monkeypatch.setattr(ts.vector_service, "search", lambda **kwargs: calls.append(kwargs) or [
        {"doc_path": "kb/a", "score": .9, "content": "relevant"}])
    rows = [{"doc_path": "kb/a", "score": 2}]
    _keywords(monkeypatch, rows)
    app = FastAPI()
    app.include_router(route.router)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/search/two-stage", json={"query": "q"})
            assert response.status_code == 200
            result = response.json()
            assert result["stage2"]["results"][0]["score_source"] == "vector"
            assert result["stage2"]["results"][0]["content"] == "relevant"
            rows.clear()
            response = await client.post("/api/v1/search/two-stage", json={"query": "unmatched"})
            assert response.status_code == 200
            assert response.json()["retrieval"]["vector_status"] == "skipped_no_candidates"
            assert response.json()["total_results"] == 0
            assert len(calls) == 1

    try:
        asyncio.run(exercise())
    finally:
        runner._executor.shutdown(wait=True)


def test_primary_runner_cancellation_and_failure_release_only_on_completion():
    runner = ts._PrimarySearchRunner(workers=1, queue_size=0)
    started, release = threading.Event(), threading.Event()

    def blocked():
        started.set()
        assert release.wait(5)
        raise ValueError("late failure")

    async def exercise():
        task = asyncio.create_task(runner.run(blocked, 5))
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(.005)
        assert started.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert (await runner.run(lambda: None, 1))[0] == "capacity_exhausted"
        release.set()
        for _ in range(100):
            if runner._slot._value == 1:
                break
            await asyncio.sleep(.005)
        assert await runner.run(lambda: "ok", 1) == ("completed", "ok")
        def fail():
            raise TimeoutError("worker error")
        with pytest.raises(TimeoutError, match="worker error"):
            await runner.run(fail, 1)
        assert await runner.run(lambda: "ok", 1) == ("completed", "ok")

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_primary_healthy_burst_queues_without_blocking_event_loop(monkeypatch):
    runner = ts._PrimarySearchRunner(workers=2, queue_size=8)
    started, release = threading.Event(), threading.Event()
    lock = threading.Lock()
    active = 0
    peak = 0

    def work(n):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            if active == 2:
                started.set()
        assert release.wait(5)
        with lock:
            active -= 1
        return n

    async def exercise():
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "run_in_executor", lambda *args: pytest.fail("default executor used"))
        tasks = [asyncio.create_task(runner.run(lambda n=n: work(n), 2)) for n in range(10)]
        for _ in range(200):
            if started.is_set() and runner._slot._value == 0:
                break
            await asyncio.sleep(.005)
        assert started.is_set() and runner._slot._value == 0
        assert await runner.run(lambda: "overflow", 1) == ("capacity_exhausted", None)
        release.set()
        assert await asyncio.gather(*tasks) == [("completed", n) for n in range(10)]
        assert peak == 2

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_queued_timeout_and_cancel_stay_bounded_until_drained():
    runner = ts._PrimarySearchRunner(workers=1, queue_size=2)
    started, release = threading.Event(), threading.Event()
    ran = []

    def blocked():
        started.set()
        assert release.wait(5)
        return "finished"

    async def exercise():
        first = asyncio.create_task(runner.run(blocked, .05))
        while not started.is_set():
            await asyncio.sleep(.005)
        cancelled = asyncio.create_task(runner.run(lambda: ran.append("cancelled"), 2))
        queued = asyncio.create_task(runner.run(lambda: ran.append("timed out"), .05))
        await asyncio.sleep(.01)
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        assert await first == ("timeout", None)
        assert await queued == ("timeout", None)
        # Retaining queue slots avoids unbounded cancelled executor work items.
        for _ in range(20):
            assert await runner.run(lambda: ran.append("overflow"), 1) == ("capacity_exhausted", None)
        assert runner._executor._work_queue.qsize() == 2
        release.set()
        for _ in range(200):
            if runner._slot._value == 3:
                break
            await asyncio.sleep(.005)
        assert runner._slot._value == 3
        assert not ran
        assert await runner.run(lambda: "recovered", 1) == ("completed", "recovered")

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_soul_search_uses_shared_admission_without_false_success(monkeypatch):
    from app.services import soul_service

    runner = ts._PrimarySearchRunner(workers=1, queue_size=0)
    monkeypatch.setattr(ts, "_primary_search_runner", runner)
    started, release = threading.Event(), threading.Event()

    def blocked(**kwargs):
        started.set()
        assert release.wait(5)
        return {"stage2": {"results": [{"doc_path": "kb/a", "content": "evidence", "score": .9}]}}

    monkeypatch.setattr(ts.two_stage_search_service, "search", blocked)
    async def no_synthesis(*args, **kwargs):
        pytest.fail("must not synthesize after admission failure")
    monkeypatch.setattr(soul_service, "soul_ask", no_synthesis)

    async def exercise():
        task = asyncio.create_task(soul_service._retrieve_knowledge("soul", "q", ["kb"]))
        while not started.is_set():
            await asyncio.sleep(.005)
        for scope in (["kb"], ["kb", "other"], ["*"]):
            with pytest.raises(ts.PrimarySearchUnavailable):
                await soul_service._retrieve_knowledge("soul", "q", scope)
        result = await soul_service.soul_hmrs_ask("q")
        assert result["success"] is False and result["error"] == "search_unavailable"
        release.set()
        result = await task
        assert result["chunks"][0]["path"] == "kb/a"

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_soul_profile_and_learning_use_async_admission(monkeypatch):
    from app.services import soul_learn, soul_profile

    calls = []
    async def search_async(**kwargs):
        calls.append(kwargs)
        raise ts.PrimarySearchUnavailable("capacity_exhausted")

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", search_async)
    monkeypatch.setattr(soul_profile.soul_config, "resolve_soul_kb_path", lambda _: "soul-test")
    monkeypatch.setattr(soul_learn, "_search_scope_ids", lambda *_: ["kb-a", "kb-b"])
    async def exercise():
        with pytest.raises(ts.PrimarySearchUnavailable):
            await soul_profile.build_persona_bundle("soul-test", "q")
        result = await soul_learn.self_answer({"q_text": "q"}, "soul-test", ["kb-a", "kb-b"])
        assert result["retrieval_pass"] is False and result["error"] == "search_failed"
        assert len(calls) == 2
    asyncio.run(exercise())


def test_primary_route_concurrent_requests_queue_and_overload(monkeypatch):
    import httpx
    from fastapi import FastAPI
    from app.api.routes import search as route

    runner = ts._PrimarySearchRunner(workers=1, queue_size=2)
    monkeypatch.setattr(ts, "_primary_search_runner", runner)
    monkeypatch.setitem(config._config, "vector", {"enabled": True})
    started, release = threading.Event(), threading.Event()

    def fake_search(**kwargs):
        started.set()
        assert release.wait(5)
        return {"query": kwargs["query"], "stage2": {"results": []}}

    monkeypatch.setattr(ts.two_stage_search_service, "search", fake_search)
    app = FastAPI()
    app.include_router(route.router)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = asyncio.create_task(client.post("/api/v1/search/two-stage", json={"query": "one"}))
            while not started.is_set():
                await asyncio.sleep(.005)
            queued = [asyncio.create_task(client.post("/api/v1/search/two-stage", json={"query": str(i)}))
                      for i in range(2)]
            for _ in range(200):
                if runner._slot._value == 0:
                    break
                await asyncio.sleep(.005)
            assert runner._slot._value == 0
            rejected = await client.post("/api/v1/search/two-stage", json={"query": "overload"})
            assert rejected.status_code == 429 and rejected.headers["retry-after"] == "1"
            release.set()
            responses = await asyncio.gather(first, *queued)
            assert all(response.status_code == 200 and response.json()["success"] for response in responses)
            assert [response.json()["query"] for response in responses] == ["one", "0", "1"]

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner._executor.shutdown(wait=True)


def test_soul_multiscope_failure_does_not_synthesize(monkeypatch):
    from app.services import soul_service

    calls = []
    async def failing_search(**kwargs):
        calls.append(kwargs.get("kb_id"))
        if len(calls) == 1:
            return {"stage2": {"results": [{"doc_path": "kb-a/doc", "content": "x" * 80, "score": .9}]}}
        raise ts.PrimarySearchUnavailable("timeout")

    async def no_synthesis(*args, **kwargs):
        pytest.fail("must not synthesize after partial retrieval failure")

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", failing_search)
    monkeypatch.setattr(soul_service.soul_config, "read_soul_config", lambda _: SimpleNamespace(kb_scope=["kb-a", "kb-b"]))
    monkeypatch.setattr(soul_service, "soul_ask", no_synthesis)

    async def exercise():
        result = await soul_service.soul_hmrs_ask("query", soul_kb_id="soul")
        assert result["success"] is False and result["error"] == "search_unavailable"
        assert calls == ["kb-a", "kb-b"]

    asyncio.run(exercise())


def test_soul_ask_reports_search_failure(monkeypatch):
    from app.services import soul_service

    async def fail(*args, **kwargs):
        raise ts.PrimarySearchUnavailable("timeout")

    monkeypatch.setattr(soul_service, "_soul_ask_inner", fail)
    result = asyncio.run(soul_service.soul_ask("query", soul_kb_id="soul"))
    assert result["success"] is False
    assert result["error"] == "search_unavailable"


def test_soul_memory_search_does_not_swallow_admission_failure(monkeypatch, tmp_path):
    from app.services import soul_profile

    (tmp_path / "memories").mkdir()
    calls = []
    async def search_async(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {"stage2": {"results": [{"doc_path": "soul/doc", "content": "ok", "score": .9}]}}
        raise ts.PrimarySearchUnavailable("timeout")

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", search_async)
    monkeypatch.setattr(soul_profile.soul_config, "resolve_soul_kb_path", lambda _: "soul")
    monkeypatch.setattr(soul_profile.soul_config, "soul_kb_dir", lambda _: tmp_path)
    with pytest.raises(ts.PrimarySearchUnavailable):
        asyncio.run(soul_profile.build_persona_bundle("soul", "query"))
    assert len(calls) == 2


def test_soul_single_scope_bm25_status_failure_is_not_no_match(monkeypatch):
    from app.services import soul_service

    async def failed_search(**kwargs):
        return {
            "stage2": {"results": []},
            "retrieval": {
                "bm25_status": "failed",
                "degraded": True,
                "degraded_reasons": ["bm25_build_failed"],
            },
        }

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", failed_search)

    async def exercise():
        with pytest.raises(ts.PrimarySearchUnavailable, match="bm25_build_failed") as raised:
            await soul_service._retrieve_knowledge("soul", "query", ["kb-a"])
        assert raised.value.status == "bm25_failed"

    asyncio.run(exercise())


def test_soul_multiscope_bm25_status_failure_is_not_hidden_by_hits(monkeypatch):
    from app.services import soul_service

    calls = []

    async def partially_failed_search(**kwargs):
        calls.append(kwargs["kb_id"])
        if kwargs["kb_id"] == "kb-a":
            return {
                "stage2": {"results": [{
                    "doc_path": "kb-a/doc.md", "content": "evidence", "score": .9,
                }]},
                "retrieval": {"bm25_status": "ready", "degraded": False},
            }
        return {
            "stage2": {"results": []},
            "retrieval": {
                "bm25_status": "failed",
                "degraded": True,
                "degraded_reasons": ["bm25_search_failed"],
            },
        }

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", partially_failed_search)

    async def exercise():
        with pytest.raises(ts.PrimarySearchUnavailable, match="bm25_search_failed"):
            await soul_service._retrieve_knowledge("soul", "query", ["kb-a", "kb-b"])
        assert calls == ["kb-a", "kb-b"]

    asyncio.run(exercise())


@pytest.mark.parametrize("scope", [["kb-a"], ["kb-a", "kb-b"]])
def test_soul_ready_bm25_empty_results_remains_true_no_match(monkeypatch, scope):
    from app.services import soul_service

    calls = []

    async def empty_search(**kwargs):
        calls.append(kwargs.get("kb_id"))
        return {
            "stage2": {"results": []},
            "retrieval": {
                "bm25_status": "ready",
                "degraded": False,
                "degraded_reasons": [],
            },
        }

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", empty_search)

    async def exercise():
        result = await soul_service._retrieve_knowledge("soul", "query", scope)
        assert result["chunks"] == []
        assert result["candidates"] == []
        assert len(calls) == len(scope)

    asyncio.run(exercise())


def test_soul_persona_bundle_rejects_bm25_status_failure(monkeypatch):
    from app.services import soul_profile

    async def degraded_search(**kwargs):
        return {
            "stage2": {"results": []},
            "retrieval": {
                "bm25_status": "failed",
                "degraded": True,
                "degraded_reasons": ["bm25_build_failed"],
            },
        }

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", degraded_search)
    monkeypatch.setattr(soul_profile.soul_config, "resolve_soul_kb_path", lambda _: "soul")

    with pytest.raises(ts.PrimarySearchUnavailable, match="bm25_build_failed"):
        asyncio.run(soul_profile.build_persona_bundle("soul", "query"))


def test_soul_persona_memory_search_rejects_bm25_failure(monkeypatch, tmp_path):
    from app.services import soul_profile

    (tmp_path / "memories").mkdir()
    calls = []

    async def search(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {"stage2": {"results": [{"doc_path": "soul/doc", "content": "x", "score": .9}]},
                    "retrieval": {"bm25_status": "ready"}}
        return {"stage2": {"results": []}, "retrieval": {
            "bm25_status": "failed", "degraded_reasons": ["bm25_search_failed"]}}

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", search)
    monkeypatch.setattr(soul_profile.soul_config, "resolve_soul_kb_path", lambda _: "soul")
    monkeypatch.setattr(soul_profile.soul_config, "soul_kb_dir", lambda _: tmp_path)
    with pytest.raises(ts.PrimarySearchUnavailable, match="bm25_search_failed"):
        asyncio.run(soul_profile.build_persona_bundle("soul", "query"))
    assert len(calls) == 2


@pytest.mark.parametrize("scope", [["kb-a"], ["kb-a", "kb-b"], ["*"]])
def test_soul_ask_and_hmrs_fail_closed_for_bm25_status(monkeypatch, scope):
    from app.services import soul_service

    async def search(**kwargs):
        if len(scope) > 1 and kwargs.get("kb_id") == "kb-a":
            return {"stage2": {"results": [{"doc_path": "kb-a/a", "score": .9,
                                              "content": "evidence " * 10}]},
                    "retrieval": {"bm25_status": "ready"}}
        return {"stage2": {"results": []}, "retrieval": {
            "bm25_status": "failed", "degraded_reasons": ["bm25_search_failed"]}}

    async def profile(*args):
        return {"config": SimpleNamespace(kb_scope=scope)}

    async def bundle(*args):
        return {}

    async def no_synthesis(*args, **kwargs):
        pytest.fail("must not synthesize after BM25 failure")

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", search)
    monkeypatch.setattr(soul_service.soul_config, "resolve_soul_kb_path", lambda _: "soul")
    monkeypatch.setattr(soul_service.soul_config, "is_template_kb", lambda _: False)
    monkeypatch.setattr(soul_service.soul_config, "read_soul_config", lambda _: SimpleNamespace(kb_scope=scope))
    monkeypatch.setattr(soul_service.soul_profile, "load_profile", profile)
    monkeypatch.setattr(soul_service.soul_profile, "build_persona_bundle", bundle)
    monkeypatch.setattr(soul_service, "_kb_config_for", lambda _: {})
    monkeypatch.setattr(soul_service, "_complete_checked", no_synthesis)

    async def exercise():
        for ask in (soul_service.soul_ask, soul_service.soul_hmrs_ask):
            result = await ask("query", soul_kb_id="soul")
            assert result["success"] is False
            assert result["error"] == "search_unavailable"
            assert "bm25_search_failed" in result["detail"]

    asyncio.run(exercise())


@pytest.mark.parametrize("scope", [["kb-a"], ["kb-a", "kb-b"], ["*"]])
@pytest.mark.parametrize("outcome", ["failed", "empty", "hit"])
def test_soul_self_answer_distinguishes_failure_empty_and_hit(monkeypatch, scope, outcome):
    from app.services import soul_learn

    gaps, completions, calls = [], [], []
    resolved = None if scope == ["*"] else scope
    monkeypatch.setattr(soul_learn, "_search_scope_ids", lambda *_: resolved)
    monkeypatch.setattr(soul_learn, "_append_gap", lambda *args: gaps.append(args))
    monkeypatch.setattr(soul_learn, "_merge_graph_neighbors_for_chunks", lambda chunks, *args, **kwargs: chunks)

    async def search(**kwargs):
        calls.append(kwargs.get("kb_id"))
        failed = outcome == "failed" and (len(scope) == 1 or kwargs.get("kb_id") == "kb-b")
        rows = [] if outcome == "empty" or failed else [
            {"doc_path": f"{kwargs.get('kb_id') or 'kb-a'}/doc", "content": "evidence", "score": .9}]
        return {"stage2": {"results": rows}, "retrieval": {
            "bm25_status": "failed" if failed else "ready",
            "degraded_reasons": ["bm25_build_failed"] if failed else []}}

    async def complete(**kwargs):
        completions.append(kwargs)
        return {"success": True, "parsed": {"answer_text": "answer", "citations": []}}

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", search)
    monkeypatch.setattr(soul_learn.agent_harness, "complete", complete)
    result = asyncio.run(soul_learn.self_answer({"q_text": "query"}, "soul", scope))
    if outcome == "failed":
        assert result["error"] == "search_failed"
        assert "bm25_build_failed" in result["detail"]
        assert not gaps and not completions
    elif outcome == "empty":
        assert result == {"retrieval_pass": False}
        assert len(gaps) == 1 and not completions
    else:
        assert result["retrieval_pass"] is True
        assert result["answer_text"] == "answer"
        assert len(completions) == 1 and not gaps
    if len(scope) > 1:
        assert calls == scope


@pytest.mark.parametrize("mode", ["incremental", "docs", "parallel"])
def test_soul_training_aborts_on_search_failure_without_marking_doc(monkeypatch, mode):
    from app.services import soul_curiosity, soul_learn

    monkeypatch.setattr(soul_learn, "read_soul_config", lambda _: SimpleNamespace(is_template=False, kb_scope=[]))
    monkeypatch.setattr(soul_learn, "_begin_run_budget", lambda _: None)
    monkeypatch.setattr(soul_learn, "get_meditation_config", lambda _: {"config": {}})
    monkeypatch.setattr(soul_curiosity, "read_mastery_profile", lambda _: {})
    monkeypatch.setattr(soul_learn, "_get_incremental_docs", lambda *_: [{"doc_path": "kb/doc"}])
    monkeypatch.setattr(soul_learn, "_soul_learned_hashes", lambda _: {})
    monkeypatch.setattr(soul_learn.storage_reader, "read_document_content", lambda *args, **kwargs: "text")
    monkeypatch.setattr(soul_learn, "check_budget", lambda *_: (True, 1.0))
    monkeypatch.setattr(soul_learn, "deduct_cost", lambda *_: None)
    monkeypatch.setattr(soul_learn, "_record_learned_doc", lambda *_: pytest.fail("marked failed doc learned"))

    async def questions(*args, **kwargs):
        return [{"q_text": "question"}]

    async def failed_answer(*args, **kwargs):
        return {"retrieval_pass": False, "error": "search_failed", "detail": "bm25_build_failed"}

    monkeypatch.setattr(soul_learn, "generate_questions", questions)
    monkeypatch.setattr(soul_learn, "self_answer", failed_answer)
    if mode == "incremental":
        result = asyncio.run(soul_learn._learn_incremental_once("soul"))
    elif mode == "docs":
        result = asyncio.run(soul_learn._learn_docs_once("soul", ["kb/doc"]))
    else:
        result = asyncio.run(soul_learn._learn_incremental_parallel_once("soul"))
    assert result == {"success": False, "error": "search_failed", "detail": "bm25_build_failed"}


def test_soul_learn_all_surfaces_search_failure(monkeypatch):
    from app.services import soul_learn

    monkeypatch.setattr(soul_learn, "read_soul_config", lambda _: SimpleNamespace(is_template=False, kb_scope=[]))
    monkeypatch.setattr(soul_learn, "_scope_kb_paths", lambda _: [])

    async def learn(*args, **kwargs):
        return {"success": False, "error": "search_failed", "detail": "bm25_search_failed",
                "per_round": [{"detail": "bm25_search_failed"}]}

    monkeypatch.setattr(soul_learn, "learn_incremental", learn)
    result = asyncio.run(soul_learn.learn_all(soul_kb_id="soul"))
    assert result["success"] is False and result["error"] == "search_failed"
    assert result["souls"][0]["error"] == "search_failed"
    assert result["detail"] == "bm25_search_failed"


def test_soul_training_route_reports_search_failure(monkeypatch):
    from fastapi import HTTPException
    from app.api.routes import soul as route

    monkeypatch.setattr(route.soul_config, "resolve_soul_kb_path", lambda _: "soul")
    monkeypatch.setattr(route.soul_config, "is_template_kb", lambda _: False)

    async def learn(*args, **kwargs):
        return {"success": False, "error": "search_failed", "detail": "bm25_build_failed"}

    monkeypatch.setattr(route.soul_learn, "learn_docs", learn)
    with pytest.raises(HTTPException) as raised:
        asyncio.run(route.learn("soul", {"doc_paths": ["kb/doc"]}, None))
    assert raised.value.status_code == 503
    assert raised.value.detail["error"] == "search_unavailable"
    assert raised.value.detail["detail"] == "bm25_build_failed"


@pytest.mark.parametrize("scope", [["kb-a"], ["kb-a", "kb-b"]])
def test_soul_scope_success_keeps_hits(monkeypatch, scope):
    from app.services import soul_service

    async def search(**kwargs):
        kid = kwargs["kb_id"]
        return {"stage2": {"results": [{"doc_path": f"{kid}/doc", "content": kid, "score": .9}]},
                "retrieval": {"bm25_status": "ready", "degraded": False}}

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", search)
    result = asyncio.run(soul_service._retrieve_knowledge("soul", "query", scope))
    assert {chunk["path"] for chunk in result["chunks"]} == {f"{kid}/doc" for kid in scope}


def test_soul_hmrs_route_reports_bm25_failure(monkeypatch):
    from fastapi import HTTPException
    from app.api.routes import soul as route

    async def search(**kwargs):
        return {"stage2": {"results": []}, "retrieval": {
            "bm25_status": "failed", "degraded_reasons": ["bm25_build_failed"]}}

    monkeypatch.setattr(ts.two_stage_search_service, "search_async", search)
    with pytest.raises(HTTPException) as raised:
        asyncio.run(route.soul_hmrs_ask({"query": "question"}))
    assert raised.value.status_code == 503
    assert raised.value.detail["error"] == "search_unavailable"
    assert "bm25_build_failed" in raised.value.detail["detail"]


def test_soul_training_failed_report_marks_run_error(monkeypatch):
    from app.api.routes import soul as route
    from app.services import soul_training_db

    statuses = []
    monkeypatch.setattr(soul_training_db, "set_metrics", lambda *args, **kwargs: None)
    monkeypatch.setattr(soul_training_db, "finish_run", lambda _, status, report: statuses.append(status))
    asyncio.run(route._finish_run_with_metrics("run", {"success": False, "error": "search_failed"}))
    asyncio.run(route._finish_run_with_metrics("run", {"success": True}))
    assert statuses == ["error", "done"]


@pytest.fixture
def disk_bm25(monkeypatch, tmp_path):
    """Isolate the real reader and BM25 build from all configured KB storage."""
    import json
    from app.services import storage_reader_service
    from app.services.keyword_index_service import KeywordIndexService

    monkeypatch.setattr(storage_reader_service, "get_storage_root", lambda: tmp_path)
    monkeypatch.setattr(storage_reader, "_tree_fs_cache", None)
    monkeypatch.setattr(storage_reader, "_tree_fs_mtime", None)
    monkeypatch.setattr(ts, "keyword_index_service", KeywordIndexService())
    monkeypatch.setitem(config._config, "graph", {"enabled": False})
    monkeypatch.setattr(ts.vector_service, "search", lambda **kwargs: [])
    folders = []
    for name in ("kb-a", "kb-b"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / ".knowledge-base.yml").write_text(
            f"documents:\n  - path: {name}/doc.md\n    name: needle\n", encoding="utf-8")
        (folder / "doc.md").write_text("needle evidence for testing", encoding="utf-8")
        folders.append({"id": name, "path": name, "name": name, "isKnowledgeBase": True})
    (tmp_path / ".tree-fs.json").write_text(
        json.dumps({"folders": folders, "files": []}), encoding="utf-8")
    service = ts.TwoStageSearchService()
    monkeypatch.setattr(ts, "two_stage_search_service", service)
    return tmp_path, service


@pytest.mark.parametrize("invalid_yaml", [
    "documents: [unterminated", "documents: not-a-list", "documents: [not-a-mapping]", "", "[]",
])
def test_real_bm25_build_rejects_invalid_yaml_and_retries(disk_bm25, invalid_yaml):
    root, service = disk_bm25
    path = root / "kb-b" / ".knowledge-base.yml"
    valid = path.read_text(encoding="utf-8")
    path.write_text(invalid_yaml, encoding="utf-8")
    if invalid_yaml == "documents: [unterminated":
        assert storage_reader.list_documents("kb-b") == []
    result = service.search("needle", enable_graph_expansion=False, vector_budget_ms=0)
    assert result["retrieval"]["bm25_status"] == "failed"
    assert result["retrieval"]["degraded_reasons"] == ["bm25_build_failed"]
    assert not service._keyword_built
    assert not ts.keyword_index_service._built
    assert result["stage2"]["results"] == []
    path.write_text(valid, encoding="utf-8")
    recovered = service.search("needle", enable_graph_expansion=False, vector_budget_ms=0)
    assert recovered["retrieval"]["bm25_status"] == "ready"
    assert service._keyword_built
    assert {doc["kb_id"] for doc in ts.keyword_index_service._docs} == {"kb-a", "kb-b"}


def test_real_bm25_build_read_error_and_permissive_compatibility(disk_bm25, monkeypatch):
    from pathlib import Path

    root, service = disk_bm25
    path = root / "kb-b" / ".knowledge-base.yml"
    original_read_text = Path.read_text

    def deny_yaml(self, *args, **kwargs):
        if self == path:
            raise PermissionError("access denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny_yaml)
    assert storage_reader.list_documents("kb-b") == []
    with pytest.raises(PermissionError):
        storage_reader.list_documents("kb-b", strict=True)
    result = service.search("needle", enable_graph_expansion=False, vector_budget_ms=0)
    assert result["retrieval"]["bm25_status"] == "failed"
    assert result["retrieval"]["degraded_reasons"] == ["bm25_build_failed"]
    assert not service._keyword_built and not ts.keyword_index_service._built


def test_missing_yaml_fails_strict_but_stays_permissive(disk_bm25):
    root, service = disk_bm25
    (root / "kb-b" / ".knowledge-base.yml").unlink()
    assert storage_reader.list_documents("kb-b") == []
    result = service.search("needle", enable_graph_expansion=False, vector_budget_ms=0)
    assert result["retrieval"]["degraded_reasons"] == ["bm25_build_failed"]
    assert not service._keyword_built


@pytest.mark.parametrize("failure", ["malformed", "unreadable"])
@pytest.mark.parametrize("scope", [["kb-a"], ["kb-a", "kb-b"]])
def test_soul_real_build_rejects_invalid_yaml(disk_bm25, monkeypatch, scope, failure):
    from pathlib import Path
    from app.services import soul_service

    root, service = disk_bm25
    monkeypatch.setattr(soul_service, "two_stage_search_service", service)
    path = root / "kb-b" / ".knowledge-base.yml"
    if failure == "malformed":
        path.write_text("documents: [bad", encoding="utf-8")
    else:
        original_read_text = Path.read_text

        def deny_yaml(self, *args, **kwargs):
            if self == path:
                raise PermissionError("access denied")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", deny_yaml)
    with pytest.raises(ts.PrimarySearchUnavailable, match="bm25_build_failed"):
        asyncio.run(soul_service._retrieve_knowledge("soul", "needle", scope))
    assert not service._keyword_built


def test_soul_multiscope_does_not_hide_real_read_failure_after_hit(disk_bm25, monkeypatch):
    from pathlib import Path
    from app.services import soul_service

    root, service = disk_bm25
    monkeypatch.setattr(soul_service, "two_stage_search_service", service)
    path = root / "kb-b" / ".knowledge-base.yml"
    original_read_text = Path.read_text
    original_search = service.search_async
    calls = []

    def deny_yaml(self, *args, **kwargs):
        if self == path:
            raise PermissionError("access denied")
        return original_read_text(self, *args, **kwargs)

    async def search_then_break(**kwargs):
        calls.append(kwargs["kb_id"])
        if len(calls) == 2:
            monkeypatch.setattr(Path, "read_text", deny_yaml)
            service.invalidate_keyword_index()
        result = await original_search(**kwargs)
        if len(calls) == 1:
            assert result["stage2"]["results"]
        return result

    monkeypatch.setattr(service, "search_async", search_then_break)
    with pytest.raises(ts.PrimarySearchUnavailable, match="bm25_build_failed"):
        asyncio.run(soul_service._retrieve_knowledge("soul", "needle", ["kb-a", "kb-b"]))
    assert calls == ["kb-a", "kb-b"]
    assert not service._keyword_built
