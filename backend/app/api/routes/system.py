"""
System maintenance router — cache cleanup and maintenance tasks.

Endpoints:
  POST /api/v1/system/clean  — clean caches and MinerU parse artifacts
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.utils.paths import PROJECT_ROOT
from app.api.deps.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["System Maintenance"])

# PROJECT_ROOT = backend/ (the Python project dir)
# MONOREPO_ROOT = rag-knowledge/ (the monorepo root with config.yml, web/, models_cache/)
MONOREPO_ROOT = PROJECT_ROOT.parent
BACKEND_DIR = PROJECT_ROOT  # already backend/
OUTPUT_DIR = BACKEND_DIR / "output"
LOGS_DIR = BACKEND_DIR / "logs"
WEB_LOGS_DIR = MONOREPO_ROOT / "web" / "logs"
MODELS_CACHE = MONOREPO_ROOT / "models_cache"

# ModelScope cache (MinerU models)
import os
HOME = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", Path.home())))
MODELSCOPE_CACHE = HOME / ".cache" / "modelscope"


def _dir_size(d: Path) -> int:
    """Recursively compute directory size in bytes (best-effort)."""
    if not d or not d.exists():
        return 0
    total = 0
    try:
        for p in d.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except Exception:
                pass
    except Exception:
        pass
    return total


def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    return f"{b / (1024 * 1024 * 1024):.2f} GB"


def _rm_tree(d: Path) -> bool:
    """Remove a directory tree. Returns True on success."""
    try:
        if d.is_dir():
            shutil.rmtree(d)
        elif d.exists():
            d.unlink()
        return True
    except Exception:
        return False


def _rm_contents(d: Path) -> int:
    """Remove contents of a directory, keep the dir itself. Returns bytes freed."""
    freed = 0
    if not d.is_dir():
        return 0
    for entry in d.iterdir():
        sz = _dir_size(entry)
        if _rm_tree(entry):
            freed += sz
    return freed


def _find_pycache_dirs(root: Path, max_depth: int = 4) -> list[Path]:
    """Find __pycache__ / .pytest_cache dirs under root (excludes .venv/node_modules)."""
    found: list[Path] = []
    if not root.exists():
        return found

    def _walk(current: Path, depth: int):
        if depth > max_depth:
            return
        try:
            for entry in current.iterdir():
                if not entry.is_dir():
                    continue
                name = entry.name
                if name in ("__pycache__", ".pytest_cache"):
                    found.append(entry)
                elif not name.startswith(".") and name not in (
                    "node_modules", ".venv", "site-packages", "chroma_db", "storage",
                ):
                    _walk(entry, depth + 1)
        except PermissionError:
            pass

    _walk(root, 0)
    return found

def _scan_mineru_entries() -> list[dict[str, Any]]:
    """Scan backend/output/ for individual parsed-document folders."""
    entries: list[dict[str, Any]] = []
    if not OUTPUT_DIR.exists():
        return entries
    for child in sorted(OUTPUT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not child.is_dir():
            continue
        # Find the parsed .md file (skip images/ and uploads/ subdirs)
        md_files = [f for f in child.iterdir() if f.is_file() and f.suffix == ".md"]
        filename = md_files[0].stem if md_files else child.name
        md_path = str(md_files[0].relative_to(BACKEND_DIR)) if md_files else ""
        total_size = _dir_size(child)
        images_dir = child / "images"
        uploads_dir = child / "uploads"
        has_images = images_dir.exists() and any(images_dir.iterdir())
        has_uploads = uploads_dir.exists() and any(uploads_dir.iterdir())
        created_ts = child.stat().st_mtime
        created_at = datetime.fromtimestamp(created_ts).isoformat()
        entries.append({
            "id": child.name,
            "filename": filename,
            "markdown_path": md_path,
            "size_bytes": total_size,
            "size_human": _fmt_size(total_size),
            "created_at": created_at,
            "has_images": has_images,
            "has_uploads": has_uploads,
        })
    return entries


# ── Request / Response ───────────────────────────────────────────────────


class CleanRequest(BaseModel):
    """Scope-based cache clean request."""

    scope: str = Field(
        default="mineru",
        description="mineru / logs / pycache / all / model",
    )
    dry_run: bool = Field(default=False, description="Scan only, don't delete")
    force: bool = Field(default=False, description="Skip confirmation")


class CleanItem(BaseModel):
    name: str
    desc: str
    size_bytes: int
    size_human: str
    will_clean: bool
    message: str = ""



class MineruEntry(BaseModel):
    """A single MinerU parsed-output entry (one document folder)."""
    id: str                          # folder UUID name
    filename: str                    # parsed .md filename (stem)
    markdown_path: str               # relative path to .md file
    size_bytes: int                  # total folder size
    size_human: str                  # human-readable size
    created_at: str = ""             # ISO timestamp of folder creation
    has_images: bool = False         # whether images/ subfolder has content
    has_uploads: bool = False        # whether uploads/ subfolder has content


class CleanResponse(BaseModel):
    """Cache clean result."""

    success: bool
    dry_run: bool
    items: list[CleanItem]
    total_freed_bytes: int = 0
    total_freed_human: str = ""
    note: str = ""
    mineru_entries: list[MineruEntry] = []

# ── Endpoint ──────────────────────────────────────────────────────────────


@router.get("/clean/mineru-entries")
async def list_mineru_entries() -> dict[str, Any]:
    """List MinerU parsed-output entries (backend/output/) with details."""
    return {"success": True, "entries": _scan_mineru_entries()}

@router.post("/clean", response_model=CleanResponse, dependencies=[Depends(verify_token)])
async def clean_caches(req: CleanRequest) -> CleanResponse:
    """
    Clean caches and MinerU parse artifacts.

    Scopes:
    - ``mineru`` (default): Clean ``backend/output/`` — PDF parse md/images/uploads
    - ``logs``:           Clean ``backend/logs/`` + ``web/logs/``
    - ``pycache``:        Clean ``__pycache__`` / ``.pytest_cache``
    - ``all``:            All safe scopes (mineru+logs+pycache, NOT model)
    - ``model``:          Include model cache (BGE-M3 + MinerU models, ~4 GB,
                          requires re-download)

    Model cache is NEVER included in ``--all`` — it requires explicit ``scope=model``.
    """
    scope = req.scope.lower().strip()
    if scope not in ("mineru", "logs", "pycache", "all", "model"):
        raise HTTPException(status_code=422, detail=f"Invalid scope: {scope}")

    scope_mineru = scope in ("mineru", "all")
    scope_logs = scope in ("logs", "all")
    scope_pycache = scope in ("pycache", "all")
    scope_model = scope == "model"

    items: list[CleanItem] = []

    # ── 1. MinerU parse output ──
    mineru_size = _dir_size(OUTPUT_DIR)
    items.append(
        CleanItem(
            name="MinerU 解析产物",
            desc="PDF 解析生成的 markdown / images / uploads（backend/output/）",
            size_bytes=mineru_size,
            size_human=_fmt_size(mineru_size),
            will_clean=scope_mineru and mineru_size > 0,
            message=(
                "已清理 {} 个解析产物目录".format(
                    len(list(OUTPUT_DIR.iterdir())) if OUTPUT_DIR.exists() else 0,
                )
                if scope_mineru and not req.dry_run
                else ""
            ),
        )
    )

    # ── 2. Logs ──
    logs_size = 0
    for ld in [LOGS_DIR, WEB_LOGS_DIR]:
        logs_size += _dir_size(ld)
    items.append(
        CleanItem(
            name="服务日志",
            desc="backend/logs/ + web/logs/（旧日志文件）",
            size_bytes=logs_size,
            size_human=_fmt_size(logs_size),
            will_clean=scope_logs and logs_size > 0,
        )
    )

    # ── 3. Python caches ──
    py_dirs = _find_pycache_dirs(BACKEND_DIR) + _find_pycache_dirs(
        MONOREPO_ROOT / "kb-mcp"
    )
    py_size = sum(_dir_size(p) for p in py_dirs)
    items.append(
        CleanItem(
            name="Python 缓存",
            desc="__pycache__ / .pytest_cache（可安全重建）",
            size_bytes=py_size,
            size_human=_fmt_size(py_size),
            will_clean=scope_pycache and py_size > 0,
            message=f"{len(py_dirs)} 个缓存目录" if py_size > 0 else "",
        )
    )

    # ── 4. Model caches (explicit only) ──
    model_dirs: list[Path] = [MODELS_CACHE]
    if MODELSCOPE_CACHE.exists():
        model_dirs.append(MODELSCOPE_CACHE)
    model_size = sum(_dir_size(p) for p in model_dirs)
    items.append(
        CleanItem(
            name="模型缓存",
            desc="BGE-M3 嵌入模型 + MinerU 模型（清理后需重新下载 ~4 GB）",
            size_bytes=model_size,
            size_human=_fmt_size(model_size),
            will_clean=scope_model and model_size > 0,
            message="⚠ 清理后首次向量索引/解析需重新下载" if scope_model else "",
        )
    )

    # ── Dry run → return scan results ──
    if req.dry_run:
        mineru_entries = _scan_mineru_entries()
        return CleanResponse(
            success=True,
            dry_run=True,
            items=items,
            mineru_entries=mineru_entries,
            note="--dry-run: 仅扫描，未删除任何文件",
        )

    # ── Require force for destructive changes ──
    if not req.force:
        raise HTTPException(
            status_code=400,
            detail="需要 force=true 确认清理操作（先用 dry_run=true 预览）",
        )

    # ── Execute cleanup ──
    total_freed = 0

    if scope_mineru and mineru_size > 0:
        freed = _rm_contents(OUTPUT_DIR)
        total_freed += freed
        logger.info(f"Cleaned MinerU output: {_fmt_size(freed)}")

    if scope_logs and logs_size > 0:
        for ld in [LOGS_DIR, WEB_LOGS_DIR]:
            total_freed += _rm_contents(ld)
        logger.info(f"Cleaned logs: {_fmt_size(logs_size)}")

    if scope_pycache and py_size > 0:
        for p in py_dirs:
            _rm_tree(p)
        total_freed += py_size
        logger.info(f"Cleaned pycache: {len(py_dirs)} dirs, {_fmt_size(py_size)}")

    if scope_model and model_size > 0:
        for p in model_dirs:
            total_freed += _dir_size(p)
            _rm_tree(p)
        logger.info(f"Cleaned model cache: {_fmt_size(model_size)}")

    return CleanResponse(
        success=True,
        dry_run=False,
        items=items,
        total_freed_human=_fmt_size(total_freed),
        mineru_entries=_scan_mineru_entries(),
        note="清理完成",
    )