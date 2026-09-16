"""
MinerU engine facade — config-driven routing between two engines:

* **remote** — :class:`~app.utils.mineru_remote.RemoteMineruClient`, talking to
  a mineru-api-compatible HTTP endpoint (``mineru.remote.base_url`` + optional
  ``MINERU_API_TOKEN`` bearer).
* **local**  — :class:`~app.utils.mineru_manager.MineruApiManager`, the
  lifecycle-bound local ``mineru-api`` subprocess (models under
  ``$MODELSCOPE_CACHE``, started lazily on first use).

Mode comes from ``mineru.mode`` in backend/config.yml (hot-reloadable via the
config API — the facade re-reads it per resolve):

* ``mode: "remote"`` (default) — probe the remote endpoint; when it is not
  configured or unreachable, **automatically fall back to the local engine**
  (starting it on demand). This is the "远程优先，没有 API 就用本地" behavior.
* ``mode: "local"`` — always local; the remote endpoint is never contacted.

The facade exposes the duck-typed surface ``MineruParseService`` expects.
Engine resolution is made **sticky per parse session** through
:meth:`resolve_engine_async` / :meth:`resolve_engine`: a returned engine is
used for *both* the task submission and the subsequent status/result polling
(a task_id from one engine is meaningless to the other).
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional, Union

import httpx

from app.utils.mineru_remote import RemoteMineruClient, RemoteMineruError

logger = logging.getLogger(__name__)

Engine = Union["MineruApiManager", RemoteMineruClient]  # noqa: F821 (TYPE only)


class MineruEngine:
    """Dual-mode MinerU engine (remote-first with automatic local fallback)."""

    def __init__(self) -> None:
        self._remote = RemoteMineruClient()
        self._local: Optional["MineruApiManager"] = None  # lazy — heavy imports
        self._resolve_lock = threading.Lock()
        # Which engine actually served the last resolve ("remote"/"local") —
        # surfaced by status() so operators can see fallbacks happening.
        self.last_mode: Optional[str] = None

    # ── engines ─────────────────────────────────────────────────────

    @property
    def remote(self) -> RemoteMineruClient:
        return self._remote

    @property
    def local(self) -> "MineruApiManager":
        """The local manager singleton (created on first touch)."""
        if self._local is None:
            from app.utils.mineru_manager import MineruApiManager

            self._local = MineruApiManager()  # auto-port mode
        return self._local

    @property
    def local_installed(self) -> bool:
        """True when the venv's mineru-api executable exists (local usable)."""
        try:
            return self.local._exe_path().exists()
        except Exception:
            return False

    # ── mode ────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        """Configured mode, re-read live so config hot-reloads apply."""
        try:
            from app.config import config
            return config.mineru_mode
        except Exception:
            return "remote"

    def remote_usable(self) -> bool:
        """True when remote mode can actually serve a parse right now
        (configured AND the /health probe answers; honors the negative cache)."""
        if not self._remote.configured:
            return False
        return self._remote.available

    # ── resolution (sticky per parse session) ───────────────────────

    async def resolve_engine_async(self, timeout: float = 120.0) -> Engine:
        """Pick the engine for one parse session (async call sites).

        Returns the engine to use for submit + poll + result. Never returns
        None: remote mode with an unusable endpoint falls back to local
        (starting it on demand); if that start fails the error propagates.
        """
        mode = self.mode
        if mode == "local":
            logger.debug("MinerU mode=local → local engine")
            ok = await self.local.ensure_running_async(timeout=timeout)
            self.last_mode = "local"
            if not ok:
                raise RuntimeError(
                    "MinerU mode=local but the local mineru-api failed to start "
                    "(check backend/logs/mineru-api.log and `ragctl mineru-model`)"
                )
            return self.local

        # remote mode (default)
        if self.remote_usable():
            self.last_mode = "remote"
            logger.debug("MinerU mode=remote → remote engine %s", self._remote.base_url)
            return self._remote

        reason = (
            "not configured (mineru.remote.base_url is empty)"
            if not self._remote.configured
            else f"unreachable ({self._remote.base_url})"
        )
        logger.warning(
            "MinerU mode=remote but the remote endpoint is %s — "
            "falling back to the local engine", reason,
        )
        ok = await self.local.ensure_running_async(timeout=timeout)
        self.last_mode = "local"
        if not ok:
            raise RuntimeError(
                f"MinerU remote endpoint is {reason} and the local mineru-api "
                "failed to start either. Install MinerU locally "
                "(`cd backend && uv sync` + `ragctl mineru-model`) or fix "
                "mineru.remote.base_url."
            )
        return self.local

    def resolve_engine(self, timeout: float = 120.0) -> Engine:
        """Sync variant of :meth:`resolve_engine_async`."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            # Inside a running loop (rare for sync call sites) — offload.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(asyncio.run, self.resolve_engine_async(timeout)).result()
        return asyncio.run(self.resolve_engine_async(timeout))

    # ── status / lifecycle surface (status route, kb-mcp health) ────

    @property
    def is_running(self) -> bool:
        """The engine that would serve a parse right now is healthy."""
        if self.mode == "local":
            return self.local.is_running
        if self.remote_usable():
            return True
        return self.local.is_running  # fallback target usable?

    @property
    def api_url(self) -> str:
        if self.mode == "remote" and self.remote_usable():
            return self._remote.api_url
        if self.last_mode == "remote" and self._remote.configured:
            return self._remote.api_url
        return self.local.api_url

    @property
    def host(self) -> str:
        if self.mode == "remote" and self.remote_usable():
            return self._remote.host
        return self.local.host

    @property
    def port(self) -> Optional[int]:
        if self.mode == "remote" and self.remote_usable():
            return self._remote.port
        return self.local.port

    @property
    def _process(self):  # noqa: D401 — compat with mineru.py status introspection
        """Underlying local process (None in remote mode) — status route reads it."""
        return self.local._process if self._local is not None else None

    def health(self) -> dict:
        if self.mode == "remote" and self.remote_usable():
            return self._remote.health()
        return self.local.health()

    def restart(self, timeout: float = 120.0) -> bool:
        """Restart the serving engine: local → subprocess restart; remote →
        re-probe (nothing to restart server-side)."""
        if self.mode == "remote" and self.remote_usable():
            self._remote.probe(force=True)
            return True
        return self.local.restart(timeout=timeout)

    def stop(self) -> None:
        """Stop the local subprocess (no-op for remote)."""
        if self._local is not None:
            self.local.stop()

    def ensure_running(self, timeout: float = 60.0) -> bool:
        """Legacy sync entry: make *some* engine available, preferring the
        configured mode's pick (with remote→local fallback in remote mode)."""
        try:
            return self.resolve_engine(timeout=timeout) is not None
        except Exception:
            logger.exception("MineruEngine.ensure_running failed")
            return False

    async def ensure_running_async(self, timeout: float = 60.0) -> bool:
        try:
            return await self.resolve_engine_async(timeout=timeout) is not None
        except Exception:
            logger.exception("MineruEngine.ensure_running_async failed")
            return False

    # ── parse passthroughs (legacy sync callers) ────────────────────

    def parse_file(self, file_path: str, return_md: bool = True) -> dict:
        """Sync legacy parse routed to the resolved engine."""
        engine = self.resolve_engine()
        return engine.parse_file(file_path, return_md=return_md)

    # ── rich status for /api/v1/mineru/status ───────────────────────

    def status(self) -> dict[str, Any]:
        """Dual-mode status payload (superset of the legacy single-engine one)."""
        remote_available = self.remote_usable()
        local_running = self.local.is_running if self._local is not None else False
        proc = self._process
        configured_mode = self.mode
        # Effective engine for the *next* parse call.
        effective = (
            "remote" if configured_mode == "remote" and remote_available
            else "local"
        )
        if configured_mode == "local":
            effective = "local"
        return {
            # legacy keys (kb-mcp / web health checks read these)
            "available": True,
            "running": self.is_running,
            "host": self.host,
            "port": self.port,
            "api_url": self.api_url,
            "pid": proc.pid if proc is not None else None,
            # dual-mode extensions
            "mode": configured_mode,
            "effective_mode": effective,
            "last_mode": self.last_mode,
            "remote": {
                "configured": self._remote.configured,
                "base_url": self._remote.base_url,
                "token_set": bool(self._remote.token),
                "available": remote_available,
            },
            "local": {
                "installed": self.local_installed,
                "running": local_running,
                "port": self.local.port,
                "api_url": self.local.api_url,
            },
        }


# Module-level singleton + accessor. `get_mineru_manager()` is the historical
# name some call sites already import (soul_distill_files.py) — it now returns
# the dual-mode engine facade.
mineru_engine = MineruEngine()


def get_mineru_manager() -> MineruEngine:
    return mineru_engine
