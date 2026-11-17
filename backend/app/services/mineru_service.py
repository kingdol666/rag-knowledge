"""
MinerU Parse Service — structured PDF parsing with output directory management.
Wraps MineruApiManager with file persistence, markdown/image extraction,
and structured metadata return.
"""
from __future__ import annotations

import base64
import errno
import inspect
import logging
import os
import re
import stat
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.utils.mineru_manager import MineruApiManager

from app.models.schemas import MineruParseResult

logger = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    """Accept a single portable filename, never a path or Windows device name."""
    if (not isinstance(name, str) or not name or name in {".", ".."}
            or any(ord(c) < 32 or c in '/\\<>:"|?*' for c in name)
            or name.endswith((" ", "."))
            or re.match(r"^(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]) *(?:\.|$)", name, re.I)):
        raise ValueError("filename must be a safe basename")
    return name


def _ensure_directory(path: Path, parent: Path | None = None, *, create: bool = True) -> Path:
    """Create and verify an output directory, rejecting links and junctions."""
    raw = str(path)
    if not raw or "\x00" in raw or raw.startswith("\\\\") or (os.name == "nt" and raw.startswith("//")):
        raise ValueError("unsafe output directory")
    # Do not normalize away parent components before checking for links.
    if ".." in path.parts:
        raise ValueError("parent traversal not allowed in output directory")
    path = Path(os.path.abspath(path))
    if parent is not None:
        parent = Path(os.path.abspath(parent))
        if path.parent != parent:
            raise ValueError("invalid output subdirectory")
        _ensure_directory(parent, create=create)

    # Walk each component so mkdir never knowingly traverses a symlink/junction.
    current = Path(path.anchor)
    for component in path.parts[1:] if path.anchor else path.parts:
        current = current / component
        try:
            info = current.lstat()
        except FileNotFoundError:
            if not create:
                raise ValueError(f"missing output directory: {current}")
            try:
                current.mkdir()
            except FileExistsError:
                pass
            info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError(f"unsafe output directory: {current}")

    try:
        resolved = path.resolve(strict=True)
        lexical = Path(os.path.normcase(os.path.normpath(str(path))))
        canonical = Path(os.path.normcase(os.path.normpath(str(resolved))))
        if lexical != canonical:
            raise ValueError(f"output directory traverses a symlink or junction: {path}")
        if parent is not None and resolved.parent != parent.resolve(strict=True):
            raise ValueError(f"output directory escapes its parent: {path}")
        return resolved
    except OSError as exc:
        raise ValueError(f"unsafe output directory: {path}") from exc


@contextmanager
def _output_directory_handle(directory: Path):
    """Pin a directory on POSIX so a renamed parent cannot redirect a write."""
    if os.name != "nt" and os.open in os.supports_dir_fd:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            checked = directory.stat()
            if (info.st_dev, info.st_ino) != (checked.st_dev, checked.st_ino):
                raise ValueError(f"output directory changed: {directory}")
            _ensure_directory(directory, create=False)
            yield fd
        finally:
            os.close(fd)
    else:
        yield None


def _reuse_identical_image(directory: Path, name: str, data: bytes, dir_fd: int | None) -> Path:
    """Check an existing leaf through its descriptor; never modify it.

    A concurrent publisher briefly has two links (its temp and the published
    name). Allow it time to unlink the temp, but reject persistent hardlinks.
    """
    dest = directory / name
    deadline = time.monotonic() + 2.0
    while True:
        if dir_fd is None:
            _ensure_directory(directory, create=False)
        try:
            before = os.stat(name, dir_fd=dir_fd, follow_symlinks=False) if dir_fd is not None else dest.lstat()
        except FileNotFoundError:
            raise ValueError(f"output file changed during image reuse: {dest}")
        if not stat.S_ISREG(before.st_mode) or (hasattr(dest, "is_junction") and dest.is_junction()):
            raise ValueError(f"unsafe output file: {dest}")
        if before.st_nlink != 1:
            if before.st_nlink == 2 and time.monotonic() < deadline:
                time.sleep(0.01)
                continue
            raise ValueError(f"unsafe output file: {dest}")

        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            fd = os.open(name if dir_fd is not None else dest, flags, dir_fd=dir_fd)
        except OSError as exc:
            raise ValueError(f"unsafe or changed output file: {dest}") from exc
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
                raise ValueError(f"unsafe or changed output file: {dest}")
            identical = opened.st_size == len(data) and stream.read() == data
            after = os.fstat(stream.fileno())
        try:
            current = os.stat(name, dir_fd=dir_fd, follow_symlinks=False) if dir_fd is not None else dest.lstat()
        except FileNotFoundError as exc:
            raise ValueError(f"output file changed during image reuse: {dest}") from exc
        if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1 or after.st_nlink != 1
                or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
                or (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                != (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)):
            raise ValueError(f"output file changed during image reuse: {dest}")
        if not identical:
            raise FileExistsError(errno.EEXIST, f"image name collision with different content: {dest}", str(dest))
        return dest


def _atomic_write(directory: Path, name: str, data: bytes, *, replace_existing: bool = True) -> Path:
    """Atomically replace a leaf without ever opening a destination symlink.

    POSIX writes are relative to an O_NOFOLLOW directory descriptor. On Windows
    exclusive temp creation plus replace avoids following the destination leaf;
    directory validation is repeated but cannot pin parent directories. Windows
    ACLs remain the boundary against namespace races by other permitted writers.
    """
    name = _safe_filename(name)
    directory = _ensure_directory(directory, create=False)
    dest = directory / name
    with _output_directory_handle(directory) as dir_fd:
        # Exclusive creation defeats pre-existing symlinks and hardlinks.
        tmp_name = f".mineru-{uuid.uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        temp = directory / tmp_name
        fd = os.open(tmp_name if dir_fd is not None else temp, flags, 0o600, dir_fd=dir_fd)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            # Never overwrite a link or a hard-linked destination. A regular
            # file created by an earlier parse is the only accepted existing leaf.
            try:
                info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False) if dir_fd is not None else dest.lstat()
            except FileNotFoundError:
                info = None
            if info is not None and (not stat.S_ISREG(info.st_mode) or (replace_existing and info.st_nlink != 1) or (hasattr(dest, "is_junction") and dest.is_junction())):
                raise ValueError(f"unsafe output file: {dest}")
            if not replace_existing:
                # Publish the complete temporary file without replacing any
                # existing name. The link operation is atomic across writers.
                if dir_fd is None:
                    _ensure_directory(directory, create=False)
                try:
                    if dir_fd is None:
                        os.link(temp, dest)
                    else:
                        os.link(tmp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)
                except FileExistsError:
                    return _reuse_identical_image(directory, name, data, dir_fd)
                return dest
            if dir_fd is not None:
                current = os.stat(name, dir_fd=dir_fd, follow_symlinks=False) if info is not None else None
                if info is not None and (current.st_ino, current.st_dev) != (info.st_ino, info.st_dev):
                    raise ValueError(f"output file changed during write: {dest}")
            else:
                _ensure_directory(directory, create=False)
                try:
                    current = dest.lstat()
                except FileNotFoundError:
                    current = None
                if info is not None and (current is None or (current.st_ino, current.st_dev) != (info.st_ino, info.st_dev)):
                    raise ValueError(f"output file changed during write: {dest}")
            if (info is None) != (current is None):
                raise ValueError(f"output file changed during write: {dest}")
            if dir_fd is None:
                os.replace(temp, dest)
            else:
                os.replace(tmp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        finally:
            try:
                if dir_fd is None:
                    temp.unlink(missing_ok=True)
                else:
                    os.unlink(tmp_name, dir_fd=dir_fd)
            except FileNotFoundError:
                pass
    return dest


class MineruParseService:
    """
    Service class for parsing PDF files via the local MinerU API.

    Handles the full parse lifecycle:
      1. Save uploaded file to ``output_dir/uploads/``
      2. Submit to MinerU API via ``MineruApiManager.parse_file()``
      3. Extract markdown text + images from the raw response
      4. Persist markdown → ``output_dir/{stem}.md``
      5. Copy images → ``output_dir/images/``
      6. Return a structured ``MineruParseResult``

    The service is stateless — instantiate once and call ``.parse()`` for
    each file.  ``MineruApiManager`` is injected via the constructor so
    callers (routes / tests) can mock the dependency.
    """

    def __init__(self, manager) -> None:
        # manager is the duck-typed engine: the dual-mode MineruEngine facade
        # (preferred) or a bare MineruApiManager / RemoteMineruClient (tests).
        self._manager = manager

    def _bind_engine(self):
        """Bind ONE engine for this parse session (submit + poll + result must
        hit the same engine — a task_id from one is meaningless to the other).

        The dual-mode facade (:class:`~app.utils.mineru_engine.MineruEngine`)
        resolves remote-first with automatic local fallback; any other engine
        (bare MineruApiManager / RemoteMineruClient / test doubles) is used
        as-is. Type-checked rather than duck-typed so mock auto-attributes
        can't be mistaken for a resolver.
        """
        from app.utils.mineru_engine import MineruEngine

        if isinstance(self._manager, MineruEngine):
            return self._manager.resolve_engine_async()
        return self._manager

    def _bind_engine_sync(self):
        """Sync variant of :meth:`_bind_engine` for the legacy parse path."""
        from app.utils.mineru_engine import MineruEngine

        if isinstance(self._manager, MineruEngine):
            return self._manager.resolve_engine()
        return self._manager

    # ── Public API ──────────────────────────────────────────────────────

    async def parse_async(
        self,
        file_content: bytes,
        filename: str,
        output_dir: str | Path,
        *,
        use_ocr: bool = True,
        backend: str = "pipeline",
        poll_interval: float = 2.0,
        poll_timeout: float = 1800.0,
    ) -> MineruParseResult:
        """
        Parse a single PDF via MinerU's **async task** flow.

        1. Save the upload to ``output_dir/uploads/{filename}``.
        2. ``POST /tasks`` to push the job — get ``task_id``.
        3. Poll ``GET /tasks/{task_id}`` until terminal (sync ``await`` loop,
           no long-held HTTP connection).
        4. Fetch ``GET /tasks/{task_id}/result`` — carries ``md_content`` and
           base64-encoded ``images``.
        5. Write ``{output_dir}/{stem}.md`` and decode images into
           ``{output_dir}/images/`` so they always land under *output_dir*.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Original filename (stem drives the .md filename).
            output_dir: Target root directory for all parsed artifacts.
            use_ocr: Map to ``parse_method`` — True → ``"ocr"``, else ``"auto"``.
            backend: MinerU backend (``pipeline`` is CPU-only friendly).
            poll_interval: Seconds between status polls.
            poll_timeout: Hard ceiling for the whole wait (seconds).
        """
        safe_filename = _safe_filename(filename)
        output_path = _ensure_directory(Path(output_dir))
        stem = Path(safe_filename).stem

        # 0. Bind one engine for this whole session (remote-first w/ fallback).
        awaitable_engine = self._bind_engine()
        if inspect.isawaitable(awaitable_engine):
            engine = await awaitable_engine
        else:
            engine = awaitable_engine

        # 1. Persist uploaded file ──────────────────────────────────────
        source_file = self._save_upload(file_content, filename, output_path)

        # 2. Push async task ────────────────────────────────────────────
        try:
            submission = await engine.submit_task(
                str(source_file),
                backend=backend,
                parse_method="ocr" if use_ocr else "auto",
                return_md=True,
                return_images=True,
            )
        except Exception as exc:
            logger.exception("MinerU task submission failed")
            return MineruParseResult(
                success=False,
                output_dir=str(output_path),
                source_filename=filename,
                error=f"Task submission failed: {exc}",
            )

        task_id = submission.get("task_id")
        if not task_id:
            logger.error("MinerU submission returned no task_id: %s", submission)
            return MineruParseResult(
                success=False,
                output_dir=str(output_path),
                source_filename=filename,
                error="MinerU returned no task_id",
                metadata={"submission": submission},
            )
        logger.info("MinerU task submitted: %s (file=%s)", task_id, filename)

        # 3. Wait (async poll) for terminal state ───────────────────────
        try:
            result_payload = await engine.wait_for_task(
                task_id,
                poll_interval=poll_interval,
                timeout=poll_timeout,
            )
        except Exception as exc:
            logger.exception("MinerU task %s did not complete", task_id)
            return MineruParseResult(
                success=False,
                output_dir=str(output_path),
                source_filename=filename,
                error=str(exc),
                metadata={"task_id": task_id, "submission": submission},
            )

        # 4. Extract markdown + images from the result payload ──────────
        markdown_text, images_meta = self._extract_result_artifacts(
            result_payload, stem
        )

        # 4b. 空内容拒绝：空白页/纯色图解析出空 markdown 时不得报 success，
        # 否则调用方会带着空文档继续入库（A2-Q 质量门控空转）。
        if not (markdown_text or "").strip():
            logger.warning("Empty parse result for %s (no text content)", filename)
            return MineruParseResult(
                success=False,
                output_dir=str(output_path),
                source_filename=filename,
                error="Empty parse result: no text content extracted",
                metadata={"task_id": task_id, "submission": submission},
            )

        # Publish images first: a conflicting name fails explicitly, without
        # publishing markdown that refers to an older parse's image.
        images_dir = _ensure_directory(output_path / "images", output_path)
        written = self._decode_images(images_meta, images_dir)
        image_count = len(written)
        markdown_text = self._rewrite_image_links(markdown_text, output_path, written)
        md_path = _atomic_write(output_path, f"{stem}.md", markdown_text.encode("utf-8"))
        logger.info("Wrote markdown -> %s", md_path)

        return MineruParseResult(
            success=True,
            output_dir=str(output_path.resolve()),
            markdown_path=str(md_path.resolve()) if md_path else None,
            markdown=markdown_text or None,
            images_dir=str(images_dir.resolve()) if image_count > 0 else None,
            source_filename=filename,
            image_count=image_count,
            has_markdown=bool(markdown_text),
            metadata={
                "task_id": task_id,
                "image_count": image_count,
                "has_markdown": bool(markdown_text),
                "result_keys": list(result_payload.keys()),
            },
        )

    def parse(
        self,
        file_content: bytes,
        filename: str,
        output_dir: str | Path,
        use_ocr: bool = True,
    ) -> MineruParseResult:
        """
        Parse a single PDF and write results to *output_dir*.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Original filename (used for stem / extension).
            output_dir: Target directory for all parsed artifacts.
            use_ocr:   Unused currently — reserved for MinerU OCR toggle.

        Returns:
            :class:`MineruParseResult` with success/failure, paths, and metadata.
        """
        safe_filename = _safe_filename(filename)
        output_path = _ensure_directory(Path(output_dir))
        stem = Path(safe_filename).stem

        # 0. Bind one engine for this session (sync path).
        engine = self._bind_engine_sync()

        # 1. Persist uploaded file ──────────────────────────────────────
        source_file = self._save_upload(file_content, filename, output_path)

        # 2. Call MinerU API ────────────────────────────────────────────
        try:
            raw = engine.parse_file(str(source_file), return_md=True)
        except Exception as exc:
            logger.exception("MinerU API call failed")
            return MineruParseResult(
                success=False,
                output_dir=str(output_path),
                source_filename=filename,
                error=str(exc),
            )

        # 3. Determine success ──────────────────────────────────────────
        is_ok = (
            raw.get("status") == "success"
            or raw.get("success") is True
        )
        if not is_ok:
            error_msg = (
                raw.get("error")
                or raw.get("message", "MinerU returned non-success status")
            )
            logger.warning("MinerU parse failed: %s", error_msg)
            return MineruParseResult(
                success=False,
                output_dir=str(output_path),
                source_filename=filename,
                error=error_msg,
                metadata={"raw_response": raw},
            )

        # 4. Extract markdown content ───────────────────────────────────
        markdown_text = self._extract_markdown(raw)

        # 4b. 空内容拒绝：空白页/纯色图解析出空 markdown 时不得报 success。
        if not (markdown_text or "").strip():
            logger.warning("Empty parse result for %s (no text content)", filename)
            return MineruParseResult(
                success=False,
                output_dir=str(output_path),
                source_filename=filename,
                error="Empty parse result: no text content extracted",
                metadata={"raw_response": raw},
            )

        # Do not publish markdown if any image name conflicts.
        images_dir = _ensure_directory(output_path / "images", output_path)
        copied = self._copy_images(raw, images_dir)
        md_path = _atomic_write(output_path, f"{stem}.md", markdown_text.encode("utf-8"))
        logger.info("Extracted markdown -> %s", md_path)

        # 6. Assemble metadata ──────────────────────────────────────────
        image_count = copied

        return MineruParseResult(
            success=True,
            output_dir=str(output_path.resolve()),
            markdown_path=str(md_path.resolve()) if md_path else None,
            images_dir=str(images_dir.resolve()) if image_count > 0 else None,
            source_filename=filename,
            image_count=image_count,
            has_markdown=bool(markdown_text),
            markdown=markdown_text or None,
            metadata={
               "image_count": image_count,
                "has_markdown": bool(markdown_text),
                "raw_response_keys": list(raw.keys()),
            },
        )

    # ── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _save_upload(
        content: bytes, filename: str, output_dir: Path
    ) -> Path:
        """Write the uploaded file to ``output_dir/uploads/{filename}``."""
        safe_name = _safe_filename(filename)
        output_dir = _ensure_directory(output_dir)
        uploads_dir = _ensure_directory(output_dir / "uploads", output_dir)
        dest = _atomic_write(uploads_dir, safe_name, content)
        logger.info("Saved upload -> %s (%d bytes)", dest, len(content))
        return dest

    @staticmethod
    def _extract_markdown(raw: dict) -> str:
        """Try several common MinerU response keys for markdown text."""
        candidate = raw.get("full_text") or raw.get("md_content") or raw.get("markdown")
        if candidate:
            return str(candidate)

        # Nested under ``data``
        data = raw.get("data")
        if isinstance(data, dict):
            candidate = data.get("md_content") or data.get("full_text") or data.get("markdown")
            if candidate:
                return str(candidate)

        # Try reading from a returned ``md_path``
        md_path = raw.get("md_path") or (raw.get("data") or {}).get("md_path")
        if md_path:
            p = Path(md_path)
            if p.exists():
                return p.read_text(encoding="utf-8")

        logger.warning("No markdown content found in MinerU response keys: %s", list(raw.keys()))
        return ""

    @staticmethod
    def _copy_images(raw: dict, target_dir: Path) -> int:
        """Copy images from the trusted MinerU output directory (if provided)."""
        images_dir_key = (
            raw.get("images_dir")
            or (raw.get("data") or {}).get("images_dir")
        )
        if not images_dir_key:
            return 0

        src = Path(images_dir_key)
        if not src.exists() or not src.is_dir():
            logger.debug("images_dir %s does not exist or is not a dir", src)
            return 0

        count = 0
        for img in src.iterdir():
            if img.is_file():
                _atomic_write(target_dir, _safe_filename(img.name), img.read_bytes(), replace_existing=False)
                count += 1

        if count:
            logger.info("Copied %d images -> %s", count, target_dir)
        return count

    def _extract_result_artifacts(
        self, payload: dict[str, Any], stem: str
    ) -> tuple[str, dict[str, str]]:
        """
        Pull ``md_content`` and the ``images`` map out of a /tasks/{id}/result body.

        mineru-api returns::

            {"results": {pdf_name: {"md_content": str,
                                    "images": {name: "data:mime;base64,..."}}}}

        We prefer an exact ``stem`` match but fall back to the first result,
        so callers don't break when MinerU normalizes the stored stem.
        Returns ``(markdown_text, images_meta)`` where ``images_meta`` maps
        ``image_name -> raw_data_uri``.
        """
        results = payload.get("results")
        if not isinstance(results, dict) or not results:
            logger.warning(
                "No 'results' map in task result payload; keys=%s",
                list(payload.keys()),
            )
            return "", {}

        entry = results.get(stem)
        if not isinstance(entry, dict):
            # Fall back to the first available result entry
            entry = next(iter(results.values()), None)
        if not isinstance(entry, dict):
            return "", {}

        markdown_text = str(entry.get("md_content") or "")
        images = entry.get("images")
        images_meta: dict[str, str] = {}
        if isinstance(images, dict):
            for name, value in images.items():
                if isinstance(value, str):
                    images_meta[str(name)] = value
        return markdown_text, images_meta

    @staticmethod
    def _decode_images(
        images_meta: dict[str, str], target_dir: Path
    ) -> list[tuple[Path, bytes]]:
        """
        Decode base64 data-URI images into *target_dir*.

        Each image is written using the **dict key as the filename** (preserving
        its extension), because MinerU's ``md_content`` references images as
        ``images/{key}`` — so keeping the original name makes the markdown
        resolve to the files automatically.

        Returns a list of ``(written_path, blob)`` tuples so callers (e.g. the
        markdown link rewriter) can map inline ``data:`` URIs back to the file
        that was written. ``target_dir`` is created if missing.
        """
        written: list[tuple[Path, bytes]] = []
        if not images_meta:
            return written
        target_dir = _ensure_directory(target_dir)

        for name, data_uri in images_meta.items():
            blob, ext = MineruParseService._decode_data_uri(data_uri)
            if blob is None:
                logger.warning("Could not decode image %r from task result", name)
                continue

            # Treat MinerU keys as untrusted, including Windows separators and
            # device names even when the backend is running on Linux.
            safe_name = _safe_filename(name)
            if not Path(safe_name).suffix:
                safe_name = f"{safe_name}{ext}"
            dst = _atomic_write(target_dir, safe_name, blob, replace_existing=False)
            written.append((dst, blob))

        if written:
            logger.info("Decoded %d images -> %s", len(written), target_dir)
        return written

    @staticmethod
    def _decode_data_uri(data_uri: str) -> tuple[Optional[bytes], str]:
        """
        Split a ``data:<mime>;base64,<payload>`` URI into (bytes, ext).

        Returns ``(None, "")`` when the string cannot be parsed.
        """
        if not data_uri:
            return None, ""
        # Accept both "data:image/png;base64,..." and a bare base64 blob.
        match = re.match(
            r"data:(?P<mime>[\w/\-.+]+)?(?:;charset=[\w\-]+)?;base64,(?P<data>.+)",
            data_uri,
            flags=re.DOTALL,
        )
        if match:
            mime = match.group("mime") or "image/png"
            ext = mimetypes_extension(mime)
            try:
                blob = base64.b64decode(match.group("data"))
            except Exception:
                return None, ""
            return blob, ext

        try:
            return base64.b64decode(data_uri), ".png"
        except Exception:
            return None, ""

    @staticmethod
    def _rewrite_image_links(
        text: str, output_dir: Path, written: list[tuple[Path, bytes]]
    ) -> str:
        """Rewrite matching inline data URIs using the actual published paths."""
        if not written:
            return text

        # Map decoded-bytes-identity -> relative path, so we only rewrite URIs
        # whose image we actually persisted.
        by_blob: dict[bytes, str] = {}
        for path, blob in written:
            rel = path.relative_to(output_dir).as_posix()
            by_blob.setdefault(blob, rel)

        def _replace(match: re.Match[str]) -> str:
            data_uri = match.group("data")
            blob, _ = MineruParseService._decode_data_uri(data_uri)
            if blob is None:
                return match.group(0)
            rel = by_blob.get(blob)
            if not rel:
                return match.group(0)
            return f"![{match.group('alt')}]({rel})"

        pattern = re.compile(
            r"!\[(?P<alt>[^\]]*)\]\((?P<data>data:[^)]+)\)"
        )
        text = pattern.sub(_replace, text)

        # MinerU sometimes omits the image extension in Markdown while the
        # image map key gets an extension inferred from its MIME type.
        by_stem: dict[str, list[str]] = {}
        for path, _blob in written:
            by_stem.setdefault(path.stem, []).append(path.relative_to(output_dir).as_posix())

        def _fix_extensionless_reference(match: re.Match[str]) -> str:
            relative = match.group("path")
            name = Path(relative).name
            if Path(name).suffix:
                return match.group(0)
            matches = by_stem.get(name, [])
            if len(matches) != 1:
                return match.group(0)
            return f"![{match.group('alt')}]({matches[0]})"

        path_pattern = re.compile(
            r"!\[(?P<alt>[^\]]*)\]\((?P<path>images/[^)]+)\)"
        )
        return path_pattern.sub(_fix_extensionless_reference, text)


def mimetypes_extension(mime: str) -> str:
    """Map a MIME type like ``image/png`` to a dotted extension (``.png``)."""
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/svg+xml": ".svg",
        "image/tiff": ".tiff",
    }
    return mapping.get(mime.lower(), ".png")
