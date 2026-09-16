"""
Remote MinerU client — talks to a **mineru-api-compatible HTTP endpoint**
(self-hosted ``mineru-api`` on another machine/port, a container, or any
service speaking the same protocol).

This is the "remote" half of the dual-mode MinerU engine (see
``app.utils.mineru_engine.MineruEngine``). It is duck-type compatible with the
local :class:`~app.utils.mineru_manager.MineruApiManager` for the surface
``MineruParseService`` uses:

    POST {base_url}/tasks            -> 202 {task_id, status_url, result_url}
    GET  {base_url}/tasks/{id}       -> {task_id, status, ...}
    GET  {base_url}/tasks/{id}/result-> {results: {name: {md_content, images}}}
    POST {base_url}/file_parse       -> sync legacy parse
    GET  {base_url}/health           -> 200

Auth: when ``mineru.remote.token`` is configured (env-expanded from
``MINERU_API_TOKEN``), every request carries ``Authorization: Bearer <token>``.
Endpoints that don't use tokens simply ignore the header, so one client works
for both tokenless self-hosted instances and authenticated gateways.

The remote engine owns **no process lifecycle** — ``start``/``stop`` are
no-ops; availability is purely the ``/health`` probe. A short negative-cache
prevents every parse call from paying a probe round-trip against a dead
endpoint (the engine falls back to local on the first failed probe).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)


class RemoteMineruError(RuntimeError):
    """Raised when the remote endpoint is unreachable or misconfigured."""


def validate_remote_base_url(base_url: str) -> str:
    """Validate and normalize a remote base URL. Returns it without trailing slash.

    Only http/https schemes are accepted (the backend will issue POSTs with
    file uploads and long polls — anything else is a misconfiguration).
    """
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        raise RemoteMineruError("remote base_url is not configured")
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https"):
        raise RemoteMineruError(
            f"remote base_url must use http/https, got scheme {parts.scheme!r}: {raw!r}"
        )
    if not parts.hostname:
        raise RemoteMineruError(f"remote base_url has no host: {raw!r}")
    return raw


class RemoteMineruClient:
    """HTTP client for a mineru-api-compatible remote endpoint.

    Settings are re-read from the live config on each access (``base_url``,
    ``token``), so a config hot-reload (``PUT /api/v1/config`` or
    ``POST /api/v1/config/reload``) takes effect without recreating the client.
    """

    def __init__(self, base_url: str = "", token: str = ""):
        # Defaults; the engine usually passes the live config values in.
        self._static_base_url = base_url
        self._static_token = token
        # Negative-cache: until this monotonic deadline the endpoint is
        # presumed down (avoids hammering a dead host on every parse call).
        self._unavailable_until = 0.0
        self._NEGATIVE_CACHE_SECONDS = 30.0

    # ── live settings ───────────────────────────────────────────────

    def _live_settings(self) -> tuple[str, str]:
        """(base_url, token) from the live config, falling back to ctor values."""
        try:
            from app.config import config
            return config.mineru_remote_base_url, config.mineru_remote_token
        except Exception:
            return self._static_base_url, self._static_token

    @property
    def base_url(self) -> str:
        url, _ = self._live_settings()
        return url

    @property
    def configured(self) -> bool:
        """True when a base_url is set (even if currently unreachable)."""
        return bool(self.base_url)

    @property
    def token(self) -> str:
        _, tok = self._live_settings()
        return tok

    @property
    def api_url(self) -> str:
        return self.base_url

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).hostname or ""

    @property
    def port(self) -> Optional[int]:
        parts = urlsplit(self.base_url)
        if parts.port:
            return parts.port
        return 443 if parts.scheme == "https" else 80

    # ── auth ────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ── lifecycle (no-ops — the remote engine owns no processes) ────

    def start(self, timeout: float = 30.0) -> bool:
        """"Start" = verify the endpoint answers /health."""
        return self.ensure_running(timeout=timeout)

    def stop(self) -> None:  # pragma: no cover — nothing to stop
        return None

    async def ensure_running_async(self, timeout: float = 15.0) -> bool:
        return self._health_ok()

    def ensure_running(self, timeout: float = 15.0) -> bool:
        return self._health_ok()

    @property
    def is_running(self) -> bool:
        return self._health_ok()

    # ── health ──────────────────────────────────────────────────────

    def _health_ok(self) -> bool:
        """Probe ``GET {base_url}/health`` (2 s timeout).

        A failed probe arms the negative cache; a success clears it. When the
        negative cache is armed, probeless ``available`` reads return False
        without network I/O — use ``probe(force=True)`` to re-check.
        """
        if time.monotonic() < self._unavailable_until:
            return False
        try:
            url = validate_remote_base_url(self.base_url)
        except RemoteMineruError as exc:
            logger.debug("Remote MinerU not usable: %s", exc)
            self._arm_negative_cache()
            return False
        try:
            resp = httpx.get(
                f"{url}/health", headers=self._headers(),
                timeout=2.0, trust_env=False,
            )
            ok = resp.status_code == 200
        except Exception:
            ok = False
        if ok:
            self._unavailable_until = 0.0
        else:
            self._arm_negative_cache()
        return ok

    def _arm_negative_cache(self) -> None:
        self._unavailable_until = time.monotonic() + self._NEGATIVE_CACHE_SECONDS

    def probe(self, force: bool = True) -> bool:
        """Re-check remote availability (bypasses the negative cache)."""
        if force:
            self._unavailable_until = 0.0
        return self._health_ok()

    @property
    def available(self) -> bool:
        """Cheap availability read: honors the negative cache."""
        return self._health_ok()

    def health(self) -> dict:
        """Full health payload (or ``{"error": ...}``), like the local manager."""
        try:
            url = validate_remote_base_url(self.base_url)
        except RemoteMineruError as exc:
            return {"error": str(exc)}
        try:
            resp = httpx.get(
                f"{url}/health", headers=self._headers(),
                timeout=5.0, trust_env=False,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": str(exc)}

    # ── async task API (mirrors MineruApiManager) ───────────────────

    async def submit_task(
        self,
        file_path: str,
        *,
        backend: str = "pipeline",
        parse_method: str = "auto",
        return_md: bool = True,
        return_images: bool = True,
        formula_enable: bool = True,
        table_enable: bool = True,
        lang_list: Optional[list[str]] = None,
        start_page_id: int = 0,
        end_page_id: int = 99999,
    ) -> dict[str, Any]:
        """Push a file to ``POST {base_url}/tasks``; returns the submission
        payload (``task_id`` / ``status_url`` / ``result_url``)."""
        url = validate_remote_base_url(self.base_url)
        logger.info("Submitting file %s to remote MinerU %s", file_path, url)
        data = {
            "backend": backend,
            "parse_method": parse_method,
            "return_md": "true" if return_md else "false",
            "return_images": "true" if return_images else "false",
            "return_middle_json": "false",
            "return_model_output": "false",
            "return_content_list": "false",
            "return_original_file": "false",
            "response_format_zip": "false",
            "formula_enable": "true" if formula_enable else "false",
            "table_enable": "true" if table_enable else "false",
            "start_page_id": str(start_page_id),
            "end_page_id": str(end_page_id),
        }
        if lang_list:
            for lang in lang_list:
                data.setdefault("lang_list", []).append(lang)

        name = Path(file_path).name
        with open(file_path, "rb") as f:
            files = {"files": (name, f)}
            async with httpx.AsyncClient(
                timeout=60.0, trust_env=False, headers=self._headers(),
            ) as client:
                resp = await client.post(f"{url}/tasks", data=data, files=files)
        resp.raise_for_status()
        return resp.json()

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        url = validate_remote_base_url(self.base_url)
        async with httpx.AsyncClient(
            timeout=30.0, trust_env=False, headers=self._headers(),
        ) as client:
            resp = await client.get(f"{url}/tasks/{task_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_task_result(self, task_id: str) -> dict[str, Any]:
        url = validate_remote_base_url(self.base_url)
        async with httpx.AsyncClient(
            timeout=120.0, trust_env=False, headers=self._headers(),
        ) as client:
            resp = await client.get(f"{url}/tasks/{task_id}/result")
        resp.raise_for_status()
        return resp.json()

    async def wait_for_task(
        self,
        task_id: str,
        *,
        poll_interval: float = 2.0,
        timeout: float = 1800.0,
    ) -> dict[str, Any]:
        """Poll until terminal state; returns the result payload on
        ``completed``, raises on ``failed``/timeout (same contract as the
        local manager)."""
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        last_status: dict[str, Any] = {}

        while asyncio.get_event_loop().time() < deadline:
            last_status = await self.get_task_status(task_id)
            status = last_status.get("status", "")
            if status == "completed":
                return await self.get_task_result(task_id)
            if status == "failed":
                err = last_status.get("error") or "Remote MinerU task failed"
                raise RuntimeError(f"Remote MinerU task {task_id} failed: {err}")
            await asyncio.sleep(poll_interval)

        raise asyncio.TimeoutError(
            f"Remote MinerU task {task_id} did not finish within {timeout:.0f}s "
            f"(last status: {last_status.get('status', 'unknown')})"
        )

    # ── sync legacy parse (compat with MineruApiManager.parse_file) ─

    def parse_file(self, file_path: str, return_md: bool = True) -> dict:
        """Upload to ``{base_url}/file_parse`` (synchronous, legacy)."""
        url = validate_remote_base_url(self.base_url)
        self.ensure_running()
        with open(file_path, "rb") as f:
            files = {"files": (Path(file_path).name, f)}
            data = {"return_md": "true" if return_md else "false"}
            resp = httpx.post(
                f"{url}/file_parse", files=files, data=data,
                headers=self._headers(), timeout=300.0, trust_env=False,
            )
        resp.raise_for_status()
        return resp.json()
