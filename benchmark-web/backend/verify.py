"""Pre-flight dependency check for the benchmark-web backend.

Run this before starting the server when setting the project up on a new
machine — it reports which optional pieces are missing and what each one
disables, instead of letting a request fail later with an opaque error.

    python verify.py
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# (module, what it powers, required?)
REQUIRED = [
    ("fastapi", "the API itself", True),
    ("uvicorn", "the ASGI server", True),
    ("pydantic", "request validation", True),
    ("rank_bm25", "[REAL-CODE] bm25 baseline", True),
    ("faiss", "[REAL-CODE] dense / hybrid / ce_rerank / crag / selfrag", True),
    ("sentence_transformers", "BGE-M3 embeddings + ms-marco reranker", True),
    ("httpx", "[PROJECT] qdcvr_flat / qdcvr_domain baselines", True),
    ("numpy", "score maths", True),
    ("multipart", "POST /api/documents/upload", False),
    ("pypdf", "uploading .pdf files", False),
    ("docx", "uploading .docx files", False),
]


def main() -> int:
    print("benchmark-web backend — dependency check\n")
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for module, purpose, required in REQUIRED:
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, "__version__", "") or ""
            print(f"  OK    {module:<22} {version:<12} {purpose}")
        except Exception as exc:  # noqa: BLE001 - report, never crash
            tier = "MISS " if required else "OPT  "
            print(f"  {tier} {module:<22} {'':<12} {purpose}  ({type(exc).__name__})")
            (missing_required if required else missing_optional).append(module)

    print()
    if missing_optional:
        print(f"Optional packages missing: {', '.join(missing_optional)}")
        print("  -> uploads in those formats are rejected with a clear message;")
        print("     every other endpoint keeps working.")

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from config import get_settings

        settings = get_settings()
        print("\nResolved from the shared config.yml + .env:")
        print(f"  platform API      {settings.project_search_url}")
        print("  auth token        "
              + ("set" if settings.auth_token else "MISSING — QDCVR baselines will get 401"))
        print(f"  embedding model   {settings.embedding_model}")
        print(f"  hub cache         {settings.hf_cache_dir} "
              f"({'present' if settings.hf_cache_dir.is_dir() else 'MISSING'})")
        print(f"  chunk size        {settings.chunk_size} (overlap {settings.chunk_overlap})")
    except Exception as exc:  # noqa: BLE001
        print(f"\n  could not resolve settings: {type(exc).__name__}: {exc}")

    if missing_required:
        print(f"\nREQUIRED packages missing: {', '.join(missing_required)}")
        print("  Install with:")
        print("    uv pip install --python <this venv> -r requirements.txt")
        return 1

    print("\nAll required dependencies present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
