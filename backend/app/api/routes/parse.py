"""
PDF parsing router — uses MineruParseService for structured output extraction.
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, AsyncGenerator

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import WithJsonSchema
from app.models.schemas import MineruParseResult, ParseResponse
from app.services.mineru_service import MineruParseService
from app.utils.paths import PROJECT_ROOT, resolve_path
from app.utils.safe_paths import is_path_within
from app.api.deps.auth import verify_token

if TYPE_CHECKING:
    from app.utils.mineru_manager import MineruApiManager

logger = logging.getLogger(__name__)

# FastAPI 0.129.1+ generates ``{"type":"string","contentMediaType":
# "application/octet-stream"}`` (no ``format: binary``) for UploadFile array
# items. Swagger UI 5.x only renders a file picker when it sees
# ``format: binary``, so a bare ``list[UploadFile]`` shows up as a plain
# text-string list instead of an addable file list. Override the JSON schema
# to force ``format: binary`` so /docs renders a real multi-file picker.
_FileUpload = Annotated[UploadFile, WithJsonSchema({"type": "string", "format": "binary"})]

# Poll interval (s) for MinerU async-task status checks in the batch SSE flow.
_BATCH_POLL_INTERVAL = 3.0
# Hard ceiling per task in the batch flow (s) — MinerU OCR can be slow on big PDFs.
_BATCH_POLL_TIMEOUT = 1800.0

router = APIRouter(prefix="/api/v1", tags=["PDF Conversion"])

# Default output base — under backend/output/
_DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "output"

# Singleton instance for MineruParseService
_mineru_service_instance: MineruParseService | None = None

async def _parse_file(
    service: MineruParseService,
    fname: str,
    content: bytes,
    out_dir: str | Path,
    use_ocr: bool,
) -> MineruParseResult:
    """Parse a single file via MinerU, isolating failures into a result object.

    Shared by both the SSE-streaming and JSON batch endpoints so the per-file
    parse + error-capture logic exists in exactly one place.
    """
    try:
        return await service.parse_async(
            file_content=content,
            filename=fname,
            output_dir=out_dir,
            use_ocr=use_ocr,
            poll_interval=_BATCH_POLL_INTERVAL,
            poll_timeout=_BATCH_POLL_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001 — isolate per-file failure
        logger.exception("Batch parse failed for file (%s)", fname)
        return MineruParseResult(
            success=False,
            output_dir=str(out_dir),
            source_filename=fname,
            error=f"{type(exc).__name__}: {exc}",
        )


def _get_mineru_manager() -> "MineruApiManager | None":
    """Get the MinerU manager from app state (lazy import to avoid circular deps)."""
    try:
        from app.main import app
        return getattr(app.state, "mineru_manager", None)
    except Exception:
        return None


def _make_service() -> MineruParseService | None:
    """Create a singleton :class:`MineruParseService` from the current app-state manager."""
    global _mineru_service_instance
    if _mineru_service_instance is None:
        manager = _get_mineru_manager()
        if manager is None:
            return None
        _mineru_service_instance = MineruParseService(manager)
    return _mineru_service_instance


def _resolve_output_dir(output_dir: str | None) -> Path:
    """Resolve the user-supplied ``output_dir`` into an absolute :class:`Path`.

    * ``None`` or empty  → auto-generated ``backend/output/{uuid}/``.
    * Relative path      → joined onto ``PROJECT_ROOT`` (e.g. ``"out/a"``
      becomes ``<project>/out/a``).
    * Absolute path      → used verbatim (e.g. ``"D:\\docs\\a"``).

    The returned path is always absolute so downstream service code can rely on
    a stable root.
    """
    if output_dir:
        # 保持原语义：相对路径基于 PROJECT_ROOT(backend/)，绝对路径原样返回。
        resolved = resolve_path(output_dir)
        # 安全收敛 (P0 #7)：校验解析结果在 monorepo root（backend/ 的父）子树内，
        # 防止绝对路径逃逸到任意系统目录（如 C:\Windows\System32）。
        if not is_path_within(resolved, PROJECT_ROOT.parent):
            raise HTTPException(
                status_code=422,
                detail=f"output_dir must be within project root: {output_dir!r}",
            )
        return resolved
    return _DEFAULT_OUTPUT_ROOT / uuid.uuid4().hex[:12]


@router.post("/parse/file/vt", response_model=MineruParseResult, dependencies=[Depends(verify_token)])
async def parse_file_vt(
    file: UploadFile = File(...),
    output_dir: str | None = Form(default=None),
    use_ocr: bool = Form(default=True),
) -> MineruParseResult:
    """
    Parse a PDF file using the local MinerU API via **async task** flow.

    * Pushes the upload to MinerU ``POST /tasks`` (returns immediately with a
      ``task_id``) and then ``await``s the result by polling the task status
      endpoint — no long-held blocking HTTP connection.
    * The returned markdown and extracted images are always written under the
      specified ``output_dir`` root: ``{output_dir}/{stem}.md`` and
      ``{output_dir}/images/``.
    * ``output_dir`` accepts either an **absolute path** (used verbatim) or a
      **relative path** (resolved against the project root). If omitted, a
      UUID-based directory under ``backend/output/`` is created automatically.
    * Returns a structured :class:`MineruParseResult` with paths + metadata.
    """
    service = _make_service()
    if service is None:
        return MineruParseResult(
            success=False,
            error="MinerU API is not available (manager not initialized)",
            source_filename=file.filename or "unknown",
        )

    # Resolve output directory — absolute path as-is, relative under PROJECT_ROOT.
    out = _resolve_output_dir(output_dir)

    content = await file.read()
    result = await service.parse_async(
        file_content=content,
        filename=file.filename or "document.pdf",
        output_dir=out,
        use_ocr=use_ocr,
    )
    return result


# Keep old-style endpoint for backward compatibility
@router.post("/parse/file/vt/legacy", response_model=ParseResponse, dependencies=[Depends(verify_token)])
async def parse_file_vt_legacy(
    file: UploadFile = File(...),
    output_dir: str | None = Form(default=None),
    use_ocr: bool = Form(default=True),
) -> ParseResponse:
    """
    Legacy parse endpoint — uses the synchronous ``/file_parse`` path and
    returns the raw MinerU dict for backward compatibility.
    New clients should use :meth:`parse_file_vt` (async task flow) instead.
    """
    service = _make_service()
    if service is None:
        return ParseResponse(success=False, error="MinerU API is not available")

    # Resolve output directory — absolute path as-is, relative under PROJECT_ROOT.
    out = _resolve_output_dir(output_dir)

    content = await file.read()
    result = service.parse(
        file_content=content,
        filename=file.filename or "document.pdf",
        output_dir=out,
        use_ocr=use_ocr,
    )

    return ParseResponse(
        success=result.success,
        data=result.model_dump() if result.success else None,
        error=result.error if not result.success else None,
    )


# ── Batch SSE streaming endpoint ──────────────────────────────────────
def _sse(data: dict[str, Any]) -> str:
    """Serialize a payload as a single Server-Sent-Events ``data:`` frame."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _normalize_output_dirs(raw_dirs: list[str], n_files: int) -> list[str | None]:
    """Normalize the per-file ``output_dirs`` form list — **lenient on length**.

    ``files`` and ``output_dirs`` pair **by position** (the i-th dir belongs to
    the i-th file). This never raises: a missing/empty per-file dir simply
    falls back to ``default_output`` (and then the system default).

    * Empty list          → ``[None] * n_files`` (all use ``default_output``).
    * Shorter than files  → **padded with None** for the missing positions
      (those files fall back to ``default_output``) — no count-mismatch error.
    * Longer than files   → the extra trailing entries are ignored.
    * Each entry is stripped; an empty-string entry becomes ``None``.
    """
    dirs = [d.strip() or None for d in raw_dirs]
    if len(dirs) >= n_files:
        return dirs[:n_files]
    return dirs + [None] * (n_files - len(dirs))  # pad shortfall → fallback


@router.post("/batch/parse/file/vt/stream", dependencies=[Depends(verify_token)])
async def batch_parse_file_vt_stream(
    files: list[_FileUpload] = File(
        ...,
        description=(
            "Multiple PDF files (multipart/form-data, repeated 'files' field). "
            "Pairs with output_dirs BY POSITION: the i-th file uses the i-th dir. "
            "In /docs, click 'Add item' to attach one file per slot."
        ),
    ),
    output_dirs: list[str] = Form(
        default=[],
        description=(
            "Per-file output dirs — a true list (click 'Add item' in /docs to "
            "append one per file). Pairs with files BY POSITION: item i is the "
            "output dir for file i. Leave an item blank — OR omit trailing "
            "items — to fall back to default_output for that file. Length need "
            "NOT match the file count (shortfall is padded with default_output)."
        ),
    ),
    default_output: str = Form(
        default="",
        description=(
            "Batch-wide fallback output dir used when a file has no per-file "
            "dir (null/empty in output_dirs). Absolute path used as-is, "
            "relative path resolved under the project root. If this is also "
            "unset, each such file lands under backend/output/{uuid}/."
        ),
    ),
    use_ocr: bool = Form(default=True),
) -> StreamingResponse:
    """
    Batch-parse multiple PDFs with **per-file output directories**, streaming
    structured progress over Server-Sent Events.

    ``files`` and ``output_dirs`` are two parallel lists that pair **by
    position** — the i-th file is parsed into the i-th output dir. In the
    Swagger UI (/docs) you can click "Add item" on either field to append one
    entry per file.

    Output directory resolution (per file, three-level fallback):
      1. The file's own entry in ``output_dirs`` (if a non-empty string).
      2. Otherwise ``default_output`` (the batch-wide default, if non-empty).
      3. Otherwise an auto-generated ``backend/output/{uuid}/`` directory.

    Absolute paths are used verbatim; relative paths resolve under the
    project root. Each file is parsed into its **own** resolved dir, so the
    returned ``result.output_dir`` / ``markdown_path`` / ``images_dir``
    always reflect that file's destination.

    Flow:
      * All uploads are submitted to MinerU ``POST /tasks`` **concurrently**
        (fast handoff — the API returns a ``task_id`` immediately).
      * Every task is then polled concurrently at a **3 s** interval until it
        reaches a terminal state (``completed`` / ``failed``).
      * Results are emitted **in upload order** — one ``progress`` event per
        file carrying its metadata and a ``current/total`` counter
        (e.g. ``1/5``, ``2/5``). A single failed file does not abort the batch.
      * A final ``complete`` event summarises the whole run.

    SSE event shapes::

        {"type":"start","total":N}
        {"type":"progress","current":i,"total":N,"index":0,
         "filename":"a.pdf","status":"completed","result":{...MineruParseResult...}}
        {"type":"progress","current":i,"total":N,"index":0,
         "filename":"a.pdf","status":"failed","error":"..."}
        {"type":"complete","summary":{total,successful,failed,results:[...]}}
    """
    service = _make_service()

    # Validate inputs up front so the stream never starts for a bad request.
    n_files = len(files)
    if n_files == 0:
        async def _no_files() -> AsyncGenerator[str, None]:
            yield _sse({"type": "error", "message": "No files provided"})
        return StreamingResponse(_no_files(), media_type="text/event-stream")

    # Lenient: a short/empty output_dirs just falls back to default_output per
    # file — never raises. (See _normalize_output_dirs.)
    per_file_dirs = _normalize_output_dirs(output_dirs, n_files)

    if service is None:
        async def _no_manager() -> AsyncGenerator[str, None]:
            yield _sse({
                "type": "error",
                "message": "MinerU API is not available (manager not initialized)",
            })
        return StreamingResponse(_no_manager(), media_type="text/event-stream")

    # Resolve the batch-wide default once. ``None`` here means "no default
    # was supplied" — the per-file fallback will then hit the system default.
    fallback_dir = default_output.strip() or None
    # Read every upload's bytes *now*, before the stream starts. UploadFile
    # reads are tied to the request lifecycle and can behave erratically when
    # deferred into a StreamingResponse generator that yields slowly.
    uploads: list[tuple[str, bytes, Path]] = []
    for idx, f in enumerate(files):
        content = await f.read()
        fname = f.filename or f"document_{idx + 1}.pdf"
        # Three-level fallback: per-file dir → batch default → system default.
        chosen = per_file_dirs[idx] or fallback_dir
        uploads.append((fname, content, _resolve_output_dir(chosen)))

    async def generate() -> AsyncGenerator[str, None]:
        total = len(uploads)
        yield _sse({"type": "start", "total": total})

        # Concurrently submit + await each file's parse. Each coroutine owns
        # its own output_dir; failures are captured per-file (never raised).
        # Delegates to the shared module-level _parse_file helper.
        async def _parse_one(index: int) -> MineruParseResult:
            fname, content, out_dir = uploads[index]
            return await _parse_file(service, fname, content, out_dir, use_ocr)

        # gather preserves input order — results[i] corresponds to uploads[i].
        results = await asyncio.gather(*(_parse_one(i) for i in range(total)))

        successful = 0
        failed = 0
        emitted: list[dict[str, Any]] = []
        for i, res in enumerate(results):
            current = i + 1
            fname = uploads[i][0]
            if res.success:
                successful += 1
                payload = res.model_dump()
                emitted.append({"success": True, "filename": fname, "result": payload})
                yield _sse({
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "index": i,
                    "filename": fname,
                    "status": "completed",
                    "result": payload,
                })
            else:
                failed += 1
                emitted.append({"success": False, "filename": fname, "error": res.error})
                yield _sse({
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "index": i,
                    "filename": fname,
                    "status": "failed",
                    "error": res.error,
                })

        yield _sse({
            "type": "complete",
            "summary": {
                "total": total,
                "successful": successful,
                "failed": failed,
                "results": emitted,
            },
        })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
        },
    )


@router.post("/batch/parse/file/vt", dependencies=[Depends(verify_token)])
async def batch_parse_file_vt(
    files: list[_FileUpload] = File(
        ...,
        description=(
            "Multiple PDF files (repeated 'files' field). Pairs with "
            "output_dirs BY POSITION: the i-th file uses the i-th dir."
        ),
    ),
    output_dirs: list[str] = Form(
        default=[],
        description=(
            "Per-file output dirs — pairs with files BY POSITION. Leave an "
            "item blank to fall back to default_output."
        ),
    ),
    default_output: str = Form(
        default="",
        description="Batch-wide fallback output dir (used when a file has no per-file dir).",
    ),
    use_ocr: bool = Form(default=True),
) -> dict[str, Any]:
    """
    **Non-streaming** batch parse — the same logic as
    :meth:`batch_parse_file_vt_stream` but returns the full result array in a
    single JSON response once every file finishes.

    Use this endpoint from the Swagger UI (/docs) "Try it out" panel: Swagger
    UI buffers the whole response body, so it cannot render an SSE stream
    incrementally — this endpoint works around that by waiting for the full
    batch and returning one JSON document. Programmatic clients that want live
    per-file progress should call ``/batch/parse/file/vt/stream`` instead.

    Returns::

        {"total": N, "successful": k, "failed": m,
         "results": [{"index":0,"filename":"a.pdf","status":"completed",
                      "result": {...MineruParseResult...}}, ...]}
    """
    service = _make_service()
    n_files = len(files)
    if n_files == 0:
        return {"total": 0, "successful": 0, "failed": 0, "results": [],
                "error": "No files provided"}
    if service is None:
        return {"total": n_files, "successful": 0, "failed": n_files,
                "error": "MinerU API is not available (manager not initialized)",
                "results": []}
    # Lenient: a short/empty output_dirs just falls back to default_output per
    # file — never raises. (See _normalize_output_dirs.)
    per_file_dirs = _normalize_output_dirs(output_dirs, n_files)

    fallback_dir = default_output.strip() or None
    uploads: list[tuple[str, bytes, Path]] = []
    for idx, f in enumerate(files):
        content = await f.read()
        fname = f.filename or f"document_{idx + 1}.pdf"
        uploads.append((fname, content, _resolve_output_dir(per_file_dirs[idx] or fallback_dir)))

    async def _parse_one(index: int) -> MineruParseResult:
        fname, content, out_dir = uploads[index]
        return await _parse_file(service, fname, content, out_dir, use_ocr)

    results = await asyncio.gather(*(_parse_one(i) for i in range(n_files)))

    successful = 0
    failed = 0
    emitted: list[dict[str, Any]] = []
    for i, res in enumerate(results):
        fname = uploads[i][0]
        if res.success:
            successful += 1
            emitted.append({
                "index": i, "filename": fname, "status": "completed",
                "result": res.model_dump(),
            })
        else:
            failed += 1
            emitted.append({
                "index": i, "filename": fname, "status": "failed",
                "error": res.error,
            })

    return {
        "total": n_files,
        "successful": successful,
        "failed": failed,
        "results": emitted,
    }