"""
Standalone test for ``MineruParseService.parse_async``.

Runs end-to-end against the real local mineru-api:
  1. Boots mineru-api via ``MineruApiManager`` (left running so the backend
     can reuse the same process afterwards).
  2. Feeds ``backend/test.pdf`` through ``parse_async``.
  3. Asserts the structured result and prints a readable summary.

Usage:
    cd backend
    uv run python -m tests.test_parse_async
    # or:  uv run pytest tests/test_parse_async.py -s
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Make sure `backend/` is importable when run as a plain script.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.mineru_service import MineruParseService  # noqa: E402
from app.models.schemas import MineruParseResult  # noqa: E402
from app.utils.mineru_manager import MineruApiManager  # noqa: E402

TEST_PDF = BACKEND_ROOT / "test.pdf"
OUTPUT_DIR = BACKEND_ROOT / "output" / "test_parse_async"


def _banner(title: str) -> None:
    bar = "=" * 64
    print(f"\n{bar}\n{title}\n{bar}", flush=True)


async def run() -> int:
    _banner("STEP 1 — boot mineru-api via MineruApiManager")
    manager = MineruApiManager(host="127.0.0.1", port=8764)
    if not manager.start(timeout=120.0):
        print("FAIL: mineru-api did not start", flush=True)
        return 1
    print(f"mineru-api ready at {manager.api_url}", flush=True)

    _banner("STEP 2 — call MineruParseService.parse_async(test.pdf)")
    assert TEST_PDF.exists(), f"missing {TEST_PDF}"
    content = TEST_PDF.read_bytes()
    print(f"input: {TEST_PDF.name} ({len(content):,} bytes)", flush=True)

    service = MineruParseService(manager)
    result: MineruParseResult = await service.parse_async(
        file_content=content,
        filename=TEST_PDF.name,
        output_dir=OUTPUT_DIR,
        use_ocr=True,
    )

    _banner("STEP 3 — assert + print structured result")
    print(result.model_dump_json(indent=2), flush=True)

    assert result.success, f"parse_async reported failure: {result.error}"
    assert result.has_markdown, "has_markdown should be True"
    assert result.markdown_path and Path(result.markdown_path).exists(), (
        f"markdown file not written: {result.markdown_path}"
    )
    md_size = Path(result.markdown_path).stat().st_size
    assert md_size > 0, "markdown file is empty"

    # ASCII-only summary so it survives a GBK Windows console.
    print(
        f"\n[PASS] images={result.image_count}, "
        f"md={md_size:,} bytes",
        flush=True,
    )
    print(f"   output_dir : {result.output_dir}", flush=True)
    print(f"   markdown   : {result.markdown_path}", flush=True)
    print(f"   images_dir : {result.images_dir}", flush=True)

    # IMPORTANT: intentionally NOT calling manager.stop() so the backend
    # (started next) reuses the already-running mineru-api.
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))


# ── pytest entrypoint (so `pytest tests/test_parse_async.py -s` works too) ──
@pytest.mark.integration
def test_parse_async(tmp_path):  # noqa: D401
    """pytest wrapper — reuses the script's async runner."""
    global OUTPUT_DIR
    OUTPUT_DIR = tmp_path / "parse_async_out"
    rc = asyncio.run(run())
    assert rc == 0
