"""Fast, hermetic unit tests — no MinerU, no network, no slow subprocess.

Run with: ``uv run pytest`` (integration tests are auto-skipped).
Covers the pure-logic surfaces of the backend:
  * parse route helpers — _normalize_output_dirs (lenient pairing), _resolve_output_dir
  * MinerU manager — _pick_free_port avoids common ports; _base_url is derived
  * startup guard (main._port_in_use) — free vs actively-listening
  * SSE framing + MineruParseResult schema validation
"""
from __future__ import annotations

import json
import socket

import pytest

from app.api.routes.parse import (
    _DEFAULT_OUTPUT_ROOT,
    _normalize_output_dirs,
    _resolve_output_dir,
    _sse,
)
from app.models.schemas import MineruParseResult
from app.utils.paths import PROJECT_ROOT
from main import _port_in_use
from app.utils.mineru_manager import MineruApiManager


# ── _normalize_output_dirs: lenient positional pairing ───────────────────────
class TestNormalizeOutputDirs:
    def test_empty_list_all_none(self):
        assert _normalize_output_dirs([], 3) == [None, None, None]

    def test_short_list_padded_with_none(self):
        # The exact case requested: 2 files + 1 dir → file 2 falls back.
        assert _normalize_output_dirs(["D:/a"], 2) == ["D:/a", None]

    def test_empty_string_entry_becomes_none(self):
        assert _normalize_output_dirs(["a", "  ", "c"], 3) == ["a", None, "c"]

    def test_longer_list_truncated(self):
        assert _normalize_output_dirs(["a", "b", "c", "d"], 2) == ["a", "b"]

    def test_exact_length_passes_through(self):
        assert _normalize_output_dirs(["a", "b"], 2) == ["a", "b"]

    @pytest.mark.parametrize("n", [1, 5, 100])
    def test_never_raises_on_count_mismatch(self, n):
        # The point of the lenient rewrite — no ValueError, ever.
        result = _normalize_output_dirs(["only"], n)
        assert len(result) == n
        assert result[0] == "only"
        assert all(x is None for x in result[1:])


# ── _resolve_output_dir: abs / relative / uuid fallback ──────────────────────
class TestResolveOutputDir:
    def test_none_falls_back_to_uuid_dir(self):
        p = _resolve_output_dir(None)
        assert p.is_absolute()
        assert p.parent == _DEFAULT_OUTPUT_ROOT

    def test_absolute_path_is_canonical(self):
        legal = _DEFAULT_OUTPUT_ROOT / "test-output-legal"
        result = _resolve_output_dir(str(legal))
        assert result == legal.resolve()

    def test_unrelated_external_absolute_path_rejected(self, tmp_path, monkeypatch):
        from fastapi import HTTPException
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        output = project / "backend" / "output"
        storage = project / "storage"
        output.mkdir(parents=True)
        storage.mkdir()
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: storage)
        with pytest.raises(HTTPException) as exc:
            _resolve_output_dir(str(tmp_path / "unrelated" / "outside"))
        assert exc.value.status_code == 422

    def test_explicit_external_storage_root_allows_new_child(self, tmp_path, monkeypatch):
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        output = project / "backend" / "output"
        output.mkdir(parents=True)
        external_root = tmp_path / "external-volume" / "knowledge-store"
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: external_root)
        requested = external_root / "parse" / "new-child"
        resolved = _resolve_output_dir(str(requested))
        assert resolved == requested
        assert not external_root.exists()  # resolution does not create/write data

    def test_storage_config_is_read_via_environment(self, tmp_path, monkeypatch):
        from app.config import config
        from app.utils import paths
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        output = project / "backend" / "output"
        output.mkdir(parents=True)
        storage = tmp_path / "external-storage"
        monkeypatch.setenv("TREE_STORAGE_PATH", str(storage))
        monkeypatch.setattr(paths, "_STORAGE_ROOT", None)
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        assert config.storage_tree_fs_root == str(storage)
        assert _resolve_output_dir(str(storage / "new")) == storage / "new"
        assert not storage.exists()

    def test_relative_path_resolved_under_monorepo_root(self, tmp_path, monkeypatch):
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        output = project / "backend" / "output"
        output.mkdir(parents=True)
        storage = project / "storage"
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: storage)
        p = _resolve_output_dir("backend/output/some/rel/path")
        assert p == output / "some" / "rel" / "path"

    def test_reject_non_saveable_project_directory(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _resolve_output_dir(str(PROJECT_ROOT.parent))
        assert exc.value.status_code == 422

    @pytest.mark.parametrize("unsafe", ["../outside", r"..\outside", "backend/output/../outside", r"\\server\share\file", r"\\?\C:\outside", "//server/share/file", "safe\x00bad"])
    def test_reject_traversal_unc_and_nul(self, unsafe, tmp_path, monkeypatch):
        from fastapi import HTTPException
        import app.api.routes.parse as parse_route

        output = tmp_path / "project" / "backend" / "output"
        output.mkdir(parents=True)
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", output.parent)
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: tmp_path / "external")
        with pytest.raises(HTTPException) as exc:
            _resolve_output_dir(unsafe)
        assert exc.value.status_code == 422

    @pytest.mark.parametrize("kind", ["symlink", "junction"])
    @pytest.mark.parametrize("destination", ["external", "inside"])
    def test_redirected_default_output_root_rejected(self, tmp_path, monkeypatch, kind, destination):
        import os
        import subprocess
        from fastapi import HTTPException
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        backend = project / "backend"
        backend.mkdir(parents=True)
        target = (tmp_path / "outside") if destination == "external" else (project / "other")
        target.mkdir()
        output = backend / "output"
        if kind == "junction":
            if os.name != "nt":
                pytest.skip("Windows junction test")
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(output), str(target)], capture_output=True)
            if result.returncode:
                pytest.skip("junction creation unavailable")
        else:
            _make_symlink(output, target, directory=True)
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", backend)
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        # Even configuring the link's destination as storage cannot authorize
        # an implicit or explicit request through the redirected default root.
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: target)
        for requested in (None, str(output / "new"), "backend/output/new"):
            with pytest.raises(HTTPException) as exc:
                _resolve_output_dir(requested)
            assert exc.value.status_code == 422
        assert _resolve_output_dir(str(target / "explicit")) == target / "explicit"
        assert not list(target.iterdir())

    def test_external_storage_symlink_escape_rejected(self, tmp_path, monkeypatch):
        from fastapi import HTTPException
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        output = project / "backend" / "output"
        output.mkdir(parents=True)
        storage = tmp_path / "external" / "storage"
        storage.mkdir(parents=True)
        outside = tmp_path / "outside"
        outside.mkdir()
        _make_symlink(storage / "escape", outside, directory=True)
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: storage)
        with pytest.raises(HTTPException) as exc:
            _resolve_output_dir(str(storage / "escape" / "new"))
        assert exc.value.status_code == 422
        assert not (outside / "new").exists()

    def test_external_storage_sibling_prefix_is_rejected(self, tmp_path, monkeypatch):
        from fastapi import HTTPException
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        output = project / "backend" / "output"
        output.mkdir(parents=True)
        storage = tmp_path / "external" / "storage"
        monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: storage)
        with pytest.raises(HTTPException):
            _resolve_output_dir(str(storage.parent / "storage-other" / "new"))

    def test_existing_symlink_escape_is_rejected(self, tmp_path, monkeypatch):
        from fastapi import HTTPException
        import app.api.routes.parse as parse_route

        project = tmp_path / "project"
        output_root = project / "backend" / "output"
        storage_root = project / "storage"
        output_root.mkdir(parents=True)
        storage_root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        link = output_root / "redirect"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlink creation is unavailable")

        monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
        monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output_root)
        monkeypatch.setattr(parse_route, "get_storage_root", lambda: storage_root)
        with pytest.raises(HTTPException) as exc:
            _resolve_output_dir(str(link / "nested"))
        assert exc.value.status_code == 422
        with pytest.raises(HTTPException):
            _resolve_output_dir("backend/output/redirect/nested")


# ── Route-level batch contract (no MinerU service or filesystem writes) ──────
@pytest.mark.parametrize("stream", [False, True])
def test_batch_output_fallback_and_per_file_overrides(tmp_path, monkeypatch, stream):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.deps.auth import verify_token
    import app.api.routes.parse as parse_route

    project = tmp_path / "project"
    output = project / "backend" / "output"
    storage = project / "storage"
    output.mkdir(parents=True)
    storage.mkdir()
    monkeypatch.setattr(parse_route, "PROJECT_ROOT", project / "backend")
    monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
    monkeypatch.setattr(parse_route, "get_storage_root", lambda: storage)
    calls = []

    class FakeService:
        async def parse_async(self, **kwargs):
            calls.append((kwargs["filename"], kwargs["output_dir"]))
            return MineruParseResult(success=True, output_dir=str(kwargs["output_dir"]))

    monkeypatch.setattr(parse_route, "_make_service", lambda: FakeService())
    app = FastAPI()
    app.include_router(parse_route.router)
    app.dependency_overrides[verify_token] = lambda: None
    url = "/api/v1/batch/parse/file/vt" + ("/stream" if stream else "")
    with TestClient(app) as client:
        response = client.post(
            url,
            data={"default_output": "backend/output/fallback", "output_dirs": "backend/output/override"},
            files=[("files", ("a.pdf", b"a", "application/pdf")),
                   ("files", ("b.pdf", b"b", "application/pdf"))],
        )
    assert response.status_code == 200
    assert calls == [("a.pdf", output / "override"), ("b.pdf", output / "fallback")]
    if stream:
        assert '"type": "complete"' in response.text
    else:
        assert response.json()["successful"] == 2


@pytest.mark.parametrize("endpoint,field", [
    ("/api/v1/parse/file/vt", "file"),
    ("/api/v1/parse/file/vt/legacy", "file"),
    ("/api/v1/batch/parse/file/vt", "files"),
    ("/api/v1/batch/parse/file/vt/stream", "files"),
])
def test_parse_routes_accept_external_configured_storage(tmp_path, monkeypatch, endpoint, field):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.deps.auth import verify_token
    import app.api.routes.parse as parse_route

    output = tmp_path / "project" / "backend" / "output"
    output.mkdir(parents=True)
    storage = tmp_path / "external-storage"
    chosen = storage / "new" / "child"
    monkeypatch.setattr(parse_route, "PROJECT_ROOT", output.parent)
    monkeypatch.setattr(parse_route, "_DEFAULT_OUTPUT_ROOT", output)
    monkeypatch.setattr(parse_route, "get_storage_root", lambda: storage)
    seen = []

    class FakeService:
        async def parse_async(self, **kwargs):
            seen.append(kwargs["output_dir"])
            return MineruParseResult(success=True, output_dir=str(kwargs["output_dir"]))

        def parse(self, **kwargs):
            seen.append(kwargs["output_dir"])
            return MineruParseResult(success=True, output_dir=str(kwargs["output_dir"]))

    monkeypatch.setattr(parse_route, "_make_service", lambda: FakeService())
    app = FastAPI()
    app.include_router(parse_route.router)
    app.dependency_overrides[verify_token] = lambda: None
    field_name = "default_output" if "batch/" in endpoint else "output_dir"
    with TestClient(app) as client:
        response = client.post(endpoint, data={field_name: str(chosen)},
                               files=[(field, ("paper.pdf", b"pdf", "application/pdf"))])
    assert response.status_code == 200
    assert seen == [chosen]
    assert not storage.exists()


# ── Parse output write security ───────────────────────────────────────────────
@pytest.mark.parametrize("endpoint,field", [
    ("/api/v1/parse/file/vt", "file"),
    ("/api/v1/parse/file/vt/legacy", "file"),
    ("/api/v1/batch/parse/file/vt", "files"),
    ("/api/v1/batch/parse/file/vt/stream", "files"),
])
@pytest.mark.parametrize("name", ["../evil.pdf", "/tmp/evil.pdf", r"..\evil.pdf", "C:evil.pdf", "NUL.pdf"])
def test_parse_routes_reject_malicious_multipart_filename(monkeypatch, endpoint, field, name):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.deps.auth import verify_token
    import app.api.routes.parse as parse_route

    monkeypatch.setattr(parse_route, "_make_service", lambda: object())
    app = FastAPI()
    app.include_router(parse_route.router)
    app.dependency_overrides[verify_token] = lambda: None
    with TestClient(app) as client:
        response = client.post(endpoint, files=[(field, (name, b"data", "application/pdf"))])
    assert response.status_code == 422


@pytest.mark.parametrize("name", ["../evil.pdf", "/tmp/evil.pdf", r"C:\\evil.pdf", "file:stream.pdf", "NUL.pdf", ".", "bad.pdf "])
def test_service_rejects_unsafe_upload_names(tmp_path, name):
    from app.services.mineru_service import MineruParseService

    with pytest.raises(ValueError):
        MineruParseService._save_upload(b"data", name, tmp_path)
    assert not (tmp_path / "uploads").exists()


def _make_symlink(link, target, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")


@pytest.mark.parametrize("kind", ["uploads_dir", "upload_file", "markdown_file", "images_dir", "image_file"])
@pytest.mark.parametrize("legacy", [False, True])
def test_parse_rejects_symlink_destinations(tmp_path, kind, legacy):
    import asyncio
    from app.services.mineru_service import MineruParseService

    output = tmp_path / "output"
    output.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"unchanged")
    if kind == "uploads_dir":
        _make_symlink(output / "uploads", outside, directory=True)
    elif kind == "upload_file":
        (output / "uploads").mkdir()
        _make_symlink(output / "uploads" / "paper.pdf", sentinel)
    elif kind == "markdown_file":
        _make_symlink(output / "paper.md", sentinel)
    elif kind == "images_dir":
        _make_symlink(output / "images", outside, directory=True)
    else:
        (output / "images").mkdir()
        _make_symlink(output / "images" / "pic.png", sentinel)

    source = tmp_path / "source"
    source.mkdir()
    (source / "pic.png").write_bytes(b"image")

    class Engine:
        async def submit_task(self, *args, **kwargs):
            return {"task_id": "test"}

        async def wait_for_task(self, *args, **kwargs):
            return {"results": {"paper": {"md_content": "# content", "images": {"pic.png": "aW1hZ2U="}}}}

        def parse_file(self, *args, **kwargs):
            return {"success": True, "markdown": "# content", "images_dir": str(source)}

    service = MineruParseService(Engine())
    with pytest.raises((ValueError, OSError)):
        if legacy:
            service.parse(b"pdf", "paper.pdf", output)
        else:
            asyncio.run(service.parse_async(b"pdf", "paper.pdf", output))
    assert sentinel.read_bytes() == b"unchanged"
    assert sorted(p.name for p in outside.iterdir()) == ["sentinel"]


@pytest.mark.parametrize("name", ["../image.png", r"..\image.png", "/tmp/image.png", "C:pic.png", "CON.png"])
def test_decode_rejects_untrusted_image_names(tmp_path, name):
    from app.services.mineru_service import MineruParseService

    target = tmp_path / "images"
    target.mkdir()
    with pytest.raises(ValueError):
        MineruParseService._decode_images({name: "aW1hZ2U="}, target)
    assert list(target.iterdir()) == []


def test_atomic_write_rejects_existing_hardlink(tmp_path):
    import os
    from app.services.mineru_service import MineruParseService

    output = tmp_path / "output"
    (output / "uploads").mkdir(parents=True)
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"unchanged")
    try:
        os.link(sentinel, output / "uploads" / "paper.pdf")
    except OSError:
        pytest.skip("hardlinks unavailable")
    with pytest.raises(ValueError):
        MineruParseService._save_upload(b"new", "paper.pdf", output)
    assert sentinel.read_bytes() == b"unchanged"


def test_parse_writes_valid_artifacts_and_rewrites_inline_image(tmp_path):
    import asyncio
    from app.services.mineru_service import MineruParseService

    class Engine:
        async def submit_task(self, *args, **kwargs):
            return {"task_id": "test"}

        async def wait_for_task(self, *args, **kwargs):
            return {"results": {"论文": {"md_content": "![x](data:image/png;base64,aW1hZ2U=)", "images": {"pic.png": "aW1hZ2U="}}}}

    result = asyncio.run(MineruParseService(Engine()).parse_async(b"pdf", "论文.pdf", tmp_path / "output"))
    assert result.success
    assert (tmp_path / "output" / "uploads" / "论文.pdf").read_bytes() == b"pdf"
    assert (tmp_path / "output" / "images" / "pic.png").read_bytes() == b"image"
    assert "images/pic.png" in (tmp_path / "output" / "论文.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("legacy", [False, True])
def test_parse_image_collision_fails_without_publishing_wrong_markdown(tmp_path, legacy):
    import asyncio
    import base64
    from app.services.mineru_service import MineruParseService

    source = tmp_path / "source"
    source.mkdir()
    (source / "pic.png").write_bytes(b"first")

    class Engine:
        blob = b"first"

        async def submit_task(self, *args, **kwargs):
            return {"task_id": "test"}

        async def wait_for_task(self, *args, **kwargs):
            encoded = base64.b64encode(self.blob).decode()
            return {"results": {"paper": {"md_content": "![x](images/pic.png)", "images": {"pic.png": encoded}}}}

        def parse_file(self, *args, **kwargs):
            return {"success": True, "markdown": "![x](images/pic.png)", "images_dir": str(source)}

    engine = Engine()
    service = MineruParseService(engine)
    output = tmp_path / "output"
    def run(filename):
        if legacy:
            return service.parse(b"pdf", filename, output)
        return asyncio.run(service.parse_async(b"pdf", filename, output))

    first = run("paper.pdf")
    assert first.success
    image_path = output / "images" / "pic.png"
    first_stat = image_path.stat()
    repeat = run("repeat.pdf")
    assert repeat.success and repeat.image_count == 1
    assert (image_path.stat().st_ino, image_path.stat().st_mtime_ns) == (first_stat.st_ino, first_stat.st_mtime_ns)
    assert "images/pic.png" in (output / "repeat.md").read_text(encoding="utf-8")
    assert (output / "images" / "pic.png").read_bytes() == b"first"
    assert "images/pic.png" in (output / "paper.md").read_text(encoding="utf-8")
    engine.blob = b"second"
    (source / "pic.png").write_bytes(b"second")
    with pytest.raises(FileExistsError, match="different content"):
        run("other.pdf")
    assert not (output / "other.md").exists()
    assert (output / "images" / "pic.png").read_bytes() == b"first"
    assert "images/pic.png" in (output / "paper.md").read_text(encoding="utf-8")


def test_concurrent_image_publication_never_overwrites(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.services.mineru_service import _atomic_write

    target = tmp_path / "images"
    target.mkdir()
    barrier = Barrier(2)
    def write(data):
        barrier.wait()
        try:
            return _atomic_write(target, "pic.png", data, replace_existing=False)
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, [b"first", b"second"]))
    assert sum(result is not None for result in results) == 1
    assert (target / "pic.png").read_bytes() in (b"first", b"second")
    assert sorted(p.name for p in target.iterdir()) == ["pic.png"]


@pytest.mark.parametrize("legacy", [False, True])
def test_image_partial_failure_retries_without_rolling_back_shared_files(tmp_path, monkeypatch, legacy):
    import asyncio
    import app.services.mineru_service as module

    output = tmp_path / "output"
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.png").write_bytes(b"a")
    (source / "b.png").write_bytes(b"b")

    class Engine:
        async def submit_task(self, *args, **kwargs):
            return {"task_id": "test"}

        async def wait_for_task(self, *args, **kwargs):
            return {"results": {"paper": {"md_content": "![a](images/a.png) ![b](images/b.png)",
                                           "images": {"a.png": "YQ==", "b.png": "Yg=="}}}}

        def parse_file(self, *args, **kwargs):
            return {"success": True, "markdown": "![a](images/a.png) ![b](images/b.png)",
                    "images_dir": str(source)}

    original = module._atomic_write
    calls = []
    def fail_second(directory, name, data, **kwargs):
        if not kwargs.get("replace_existing", True):
            calls.append(name)
            if len(calls) == 2:
                raise OSError("simulated image write failure")
        return original(directory, name, data, **kwargs)

    service = module.MineruParseService(Engine())
    def run():
        if legacy:
            return service.parse(b"pdf", "paper.pdf", output)
        return asyncio.run(service.parse_async(b"pdf", "paper.pdf", output))

    monkeypatch.setattr(module, "_atomic_write", fail_second)
    with pytest.raises(OSError, match="simulated"):
        run()
    assert (output / "images" / calls[0]).exists()
    assert not (output / "paper.md").exists()
    monkeypatch.setattr(module, "_atomic_write", original)
    result = run()
    assert result.success and result.image_count == 2
    assert (output / "images" / "a.png").read_bytes() == b"a"
    assert (output / "images" / "b.png").read_bytes() == b"b"
    assert "images/a.png" in result.markdown and "images/b.png" in result.markdown


def test_concurrent_identical_image_publication_waits_for_temp_unlink(tmp_path, monkeypatch):
    import os
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import app.services.mineru_service as module

    target = tmp_path / "images"
    target.mkdir()
    linked, checking, release = Event(), Event(), Event()
    original = os.link
    original_reuse = module._reuse_identical_image
    def checked_reuse(*args, **kwargs):
        checking.set()
        return original_reuse(*args, **kwargs)
    monkeypatch.setattr(module, "_reuse_identical_image", checked_reuse)
    def delayed_link(*args, **kwargs):
        result = original(*args, **kwargs)
        linked.set()
        assert release.wait(5)
        return result
    monkeypatch.setattr(module.os, "link", delayed_link)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(module._atomic_write, target, "pic.png", b"same", replace_existing=False)
        assert linked.wait(5)
        second = pool.submit(module._atomic_write, target, "pic.png", b"same", replace_existing=False)
        assert checking.wait(5)
        release.set()
        assert first.result(timeout=5) == target / "pic.png"
        assert second.result(timeout=5) == target / "pic.png"
    assert (target / "pic.png").read_bytes() == b"same"
    assert sorted(p.name for p in target.iterdir()) == ["pic.png"]


def test_image_reuse_rejects_existing_hardlink(tmp_path):
    import os
    from app.services.mineru_service import _atomic_write

    target = tmp_path / "images"
    target.mkdir()
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"same")
    try:
        os.link(sentinel, target / "pic.png")
    except OSError:
        pytest.skip("hardlinks unavailable")
    with pytest.raises(ValueError, match="unsafe output file"):
        _atomic_write(target, "pic.png", b"same", replace_existing=False)
    assert sentinel.read_bytes() == b"same"


def test_image_reuse_rejects_leaf_swapped_before_open(tmp_path, monkeypatch):
    import os
    import app.services.mineru_service as module

    target = tmp_path / "images"
    target.mkdir()
    dest = target / "pic.png"
    dest.write_bytes(b"same")
    replacement = target / "replacement.png"
    replacement.write_bytes(b"same")
    original_open = os.open
    swapped = False
    def swap_before_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if str(path) in ("pic.png", str(dest)) and flags & os.O_CREAT == 0:
            os.replace(replacement, dest)
            swapped = True
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", swap_before_open)
    with pytest.raises(ValueError, match="changed output file"):
        module._atomic_write(target, "pic.png", b"same", replace_existing=False)
    assert swapped and dest.read_bytes() == b"same"


def test_extensionless_image_reference_is_preserved(tmp_path):
    import asyncio
    from app.services.mineru_service import MineruParseService

    class Engine:
        async def submit_task(self, *args, **kwargs):
            return {"task_id": "test"}

        async def wait_for_task(self, *args, **kwargs):
            return {"results": {"paper": {"md_content": "![x](images/pic)", "images": {"pic": "aW1hZ2U="}}}}

    result = asyncio.run(MineruParseService(Engine()).parse_async(b"pdf", "paper.pdf", tmp_path / "out"))
    assert result.success
    assert (tmp_path / "out" / "images" / "pic.png").read_bytes() == b"image"
    assert "images/pic.png" in result.markdown
    assert "images/pic.png" in (tmp_path / "out" / "paper.md").read_text(encoding="utf-8")


# ── MinerU manager: free-port picker + derived base_url ──────────────────────
class TestMineruApiManagerPort:
    def test_base_url_derived_from_port_never_drifts(self):
        m = MineruApiManager()
        m.port = None
        assert m._base_url == ""
        m.port = 12345
        assert m._base_url == "http://127.0.0.1:12345"
        m.port = 99
        assert m._base_url == "http://127.0.0.1:99"  # tracks instantly

    @pytest.mark.parametrize("iteration", range(15))
    def test_pick_free_port_avoids_common(self, iteration):
        m = MineruApiManager()
        assert m._pick_free_port() not in MineruApiManager._AVOID_PORTS

    def test_avoid_list_covers_project_and_common_ports(self):
        for must_avoid in (80, 443, 3000, 5432, 6379, 8000, 8080, 8764, 8765):
            assert must_avoid in MineruApiManager._AVOID_PORTS

    def test_pick_free_port_returns_valid_int(self):
        m = MineruApiManager()
        p = m._pick_free_port()
        assert isinstance(p, int)
        assert 1024 < p < 65536

    def test_manager_defaults_to_auto_port(self):
        m = MineruApiManager()
        assert m._requested_port is None
        assert m.port is None


# ── main startup guard: _port_in_use ─────────────────────────────────────────
class TestPortInUse:
    def test_free_port_is_not_in_use(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        assert _port_in_use("127.0.0.1", port) is False

    def test_active_listener_is_in_use(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen()
        port = srv.getsockname()[1]
        try:
            assert _port_in_use("127.0.0.1", port) is True
        finally:
            srv.close()


# ── SSE framing + schema validation ──────────────────────────────────────────
class TestSseFrame:
    def test_frame_format(self):
        frame = _sse({"type": "start", "total": 3})
        assert frame.startswith("data: ")
        assert frame.endswith("\n\n")
        assert json.loads(frame[len("data: "):].strip()) == {"type": "start", "total": 3}

    def test_frame_handles_unicode(self):
        frame = _sse({"msg": "中文 / émoji 🎉"})
        assert "中文" in frame and "🎉" in frame


class TestMineruParseResultSchema:
    def test_minimal_success(self):
        r = MineruParseResult(success=True, source_filename="a.pdf")
        assert r.success is True
        assert r.has_markdown is False
        assert r.image_count == 0
        assert r.metadata == {}

    def test_failure_with_error(self):
        r = MineruParseResult(success=False, source_filename="a.pdf", error="boom")
        assert r.success is False
        assert r.error == "boom"

    def test_success_is_required(self):
        with pytest.raises(Exception):
            MineruParseResult(source_filename="a.pdf")  # type: ignore[call-arg]

    def test_full_payload_roundtrip(self):
        r = MineruParseResult(
            success=True,
            output_dir="/out",
            markdown_path="/out/a.md",
            images_dir="/out/images",
            source_filename="a.pdf",
            image_count=5,
            has_markdown=True,
        )
        d = r.model_dump()
        assert d["image_count"] == 5
        # re-validate
        assert MineruParseResult(**d).success is True
