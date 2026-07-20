"""
MinerU Parse Service — structured PDF parsing with output directory management.
Wraps MineruApiManager with file persistence, markdown/image extraction,
and structured metadata return.
"""
from __future__ import annotations

import base64
import logging
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.utils.mineru_manager import MineruApiManager

from app.models.schemas import MineruParseResult

logger = logging.getLogger(__name__)


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

    def __init__(self, manager: "MineruApiManager") -> None:
        self._manager = manager

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
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        stem = Path(filename).stem

        # 1. Persist uploaded file ──────────────────────────────────────
        source_file = self._save_upload(file_content, filename, output_path)

        # 2. Push async task ────────────────────────────────────────────
        try:
            submission = await self._manager.submit_task(
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
            result_payload = await self._manager.wait_for_task(
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

        # 5. Persist markdown under output_dir ──────────────────────────
        md_path: Optional[Path] = None
        if markdown_text:
            md_path = output_path / f"{stem}.md"
            md_path.write_text(markdown_text, encoding="utf-8")
            logger.info("Wrote markdown -> %s", md_path)

        # 6. Decode images into output_dir/images/ ──────────────────────
        images_dir = output_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        written = self._decode_images(images_meta, images_dir)
        image_count = len(written)

        # 7. Rewrite any embedded data-URIs in the markdown to relative paths
        if md_path and written:
            self._rewrite_image_links(md_path, written)

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
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        stem = Path(filename).stem

        # 1. Persist uploaded file ──────────────────────────────────────
        source_file = self._save_upload(file_content, filename, output_path)

        # 2. Call MinerU API ────────────────────────────────────────────
        try:
            raw = self._manager.parse_file(str(source_file), return_md=True)
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

        md_path: Optional[Path] = None
        if markdown_text:
            md_path = output_path / f"{stem}.md"
            md_path.write_text(markdown_text, encoding="utf-8")
            logger.info("Extracted markdown -> %s", md_path)

        # 5. Extract & copy images ──────────────────────────────────────
        images_dir = output_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        copied = self._copy_images(raw, images_dir)

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
        uploads_dir = output_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        dest = uploads_dir / filename
        dest.write_bytes(content)
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
        """Copy images from the MinerU output directory (if provided)."""
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
                dst = target_dir / img.name
                if not dst.exists():
                    shutil.copy2(img, dst)
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
        target_dir.mkdir(parents=True, exist_ok=True)

        for name, data_uri in images_meta.items():
            blob, ext = MineruParseService._decode_data_uri(data_uri)
            if blob is None:
                logger.warning("Could not decode image %r from task result", name)
                continue

            # Preserve the original key as the filename; ensure a sane suffix.
            stem = Path(name).stem or f"image_{len(written) + 1}"
            suffix = Path(name).suffix or ext
            dst = target_dir / f"{stem}{suffix}"
            if not dst.exists():
                dst.write_bytes(blob)
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
        md_path: Path, written: list[tuple[Path, bytes]]
    ) -> None:
        """
        Rewrite inline ``![](data:...;base64,...)`` image refs in the markdown
        to ``images/{name}`` relative paths, so the .md resolves to the files
        we just wrote under *output_dir/images/*.

        A data-URI is matched to a written file by comparing the decoded bytes.
        Anything that doesn't match (or that's already a path) is left alone.
        Best-effort — a write failure never invalidates the markdown file.
        """
        if not written:
            return
        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            return

        # Map decoded-bytes-identity -> relative path, so we only rewrite URIs
        # whose image we actually persisted.
        by_blob: dict[bytes, str] = {}
        for path, blob in written:
            rel = path.relative_to(md_path.parent).as_posix()
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
        new_text, n = pattern.subn(_replace, text)
        if n > 0:
            try:
                md_path.write_text(new_text, encoding="utf-8")
                logger.info("Rewrote %d inline image link(s) in %s", n, md_path)
            except Exception:
                logger.warning("Failed to rewrite image links in %s", md_path)


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
