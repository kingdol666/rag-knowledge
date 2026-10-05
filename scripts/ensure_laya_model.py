#!/usr/bin/env python3
"""Ensure the local Laya decision model is present and loadable.

Resolution order for the model directory:
  1. environment variable LAYA_MODEL_PATH
  2. config.yml key decision.laya.model_path (repository root config)
  3. default: <repository root>/model/laya

When the resolved directory is missing or incomplete, the root checkpoint of
``convaiinnovations/laya`` is downloaded into it via huggingface_hub. A
configured path is never auto-filled by a download unless it points inside the
repository ``model/`` area (external paths are only validated).

Usage:
    python scripts/ensure_laya_model.py            # check + download if needed
    python scripts/ensure_laya_model.py --check    # status only, exit 0/1
    python scripts/ensure_laya_model.py --repo <hf-id> --subfolder multilingual

Output: one JSON object on stdout. Exit 0 when a usable model is present.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_REPO_ID = "convaiinnovations/laya"
REQUIRED_FILES = ("model.safetensors", "rl_agent_config.json")
REQUIRED_DIRS = ("tokenizer",)

_ENV_MODEL_PATH = "LAYA" + chr(95) + "MODEL" + chr(95) + "PATH"


def _config_model_path() -> str:
    """Read decision.laya.model_path from the repository root config.yml."""
    cfg = REPO / "config.yml"
    if not cfg.exists():
        return ""
    try:
        lines = cfg.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    in_decision = False
    in_laya = False
    for raw in lines:
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip())
        key, _, val = stripped.strip().partition(":")
        val = val.strip().strip('"').strip("'")
        if indent == 0:
            in_decision = key == "decision"
            in_laya = False
            continue
        if in_decision and indent == 2:
            in_laya = key == "laya"
            continue
        if in_decision and in_laya and key == "model_path":
            return val
    return ""


def resolve_model_dir(explicit: str | None = None) -> Path:
    """Resolve the model directory without downloading anything."""
    for candidate in (explicit, os.environ.get(_ENV_MODEL_PATH), _config_model_path()):
        if candidate and str(candidate).strip():
            return Path(str(candidate).strip())
    return REPO / "model" / "laya"


def _model_complete(model_dir: Path) -> bool:
    return all((model_dir / name).exists() for name in REQUIRED_FILES) \
        and all((model_dir / d).is_dir() for d in REQUIRED_DIRS)


def _hf_download(repo_id: str, subfolder: str, target: Path, mirror: bool) -> None:
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    if mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from huggingface_hub import snapshot_download

    prefix = f"{subfolder}/" if subfolder else ""
    names = ("rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*")
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id,
        local_dir=str(target),
        allow_patterns=[prefix + name for name in names],
    )


def _direct_download(repo_id: str, subfolder: str, target: Path) -> None:
    """Fallback when hf_hub metadata checks fail behind a proxy that strips
    HF headers: fetch each file with urllib following the same resolve URLs.
    urllib honours HTTP(S)_PROXY environment variables."""
    import time
    import urllib.request

    prefix = f"{subfolder}/" if subfolder else ""
    files = ("rl_agent_config.json", "model.safetensors",
             "tokenizer/tokenizer.json", "tokenizer/tokenizer_config.json",
             "encoder/config.json")
    endpoints = [f"https://huggingface.co/{repo_id}/resolve/main/"]
    if os.environ.get("HF_ENDPOINT"):
        endpoints.insert(0, os.environ["HF_ENDPOINT"].rstrip("/") + "/")
    for name in files:
        dest = target / (prefix + name if prefix else name)
        if dest.exists() and dest.stat().st_size > 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        last_error: Exception | None = None
        for endpoint in endpoints:
            url = endpoint + prefix + name
            for attempt in range(3):
                try:
                    request = urllib.request.Request(url, method="GET")
                    with urllib.request.build_opener().open(request, timeout=120) as response:
                        data = response.read()
                    if not data:
                        raise ValueError("empty response body")
                    dest.write_bytes(data)
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    time.sleep(2 * (attempt + 1))
            if last_error is None:
                break
        if last_error is not None:
            raise RuntimeError(f"direct download failed for {name}: {last_error}")


def ensure_model(repo_id: str = DEFAULT_REPO_ID, subfolder: str = "",
                 explicit: str | None = None, mirror: bool = False,
                 check_only: bool = False) -> dict:
    model_dir = resolve_model_dir(explicit)
    configured_elsewhere = bool(explicit or os.environ.get(_ENV_MODEL_PATH) or _config_model_path())
    status = {
        "engine": "laya",
        "repo_id": repo_id,
        "subfolder": subfolder,
        "model_path": str(model_dir),
        "model_path_source": ("env" if os.environ.get(_ENV_MODEL_PATH)
                              else "config" if _config_model_path()
                              else "default"),
        "complete": _model_complete(model_dir),
        "checked": True,
        "downloaded": False,
        "sdk_available": False,
    }
    try:
        import importlib.util
        status["sdk_available"] = importlib.util.find_spec("laya") is not None
    except Exception:  # noqa: BLE001
        status["sdk_available"] = False

    if status["complete"]:
        return status
    if check_only:
        status["note"] = "model incomplete; run without --check to download"
        return status
    # Auto-download only into the repository-local default area. External
    # configured paths are user-managed and never filled implicitly.
    if configured_elsewhere and model_dir != REPO / "model" / "laya":
        status["error"] = "configured model path is incomplete; download manually or clear the override"
        return status
    try:
        _hf_download(repo_id, subfolder, model_dir, mirror)
        status["downloaded"] = True
        status["complete"] = _model_complete(model_dir)
        if not status["complete"]:
            status["error"] = "download finished but required files are still missing"
    except Exception as hf_error:  # noqa: BLE001
        # Proxy environments frequently strip the HF metadata headers that
        # snapshot_download requires; fall back to plain resolve-URL fetches.
        try:
            _direct_download(repo_id, subfolder, model_dir)
            status["downloaded"] = True
            status["complete"] = _model_complete(model_dir)
            status["method"] = "direct"
            if not status["complete"]:
                status["error"] = "download finished but required files are still missing"
        except Exception as exc:  # noqa: BLE001
            status["error"] = (f"download_failed:hf={type(hf_error).__name__};"
                               f"direct={type(exc).__name__}:{str(exc)[:160]}")
            status["hint"] = "retry with --mirror (hf-mirror.com) when huggingface.co is unreachable"
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ensure the local Laya model is present")
    parser.add_argument("--repo", default=os.environ.get("LAYA_MODEL_REPO", DEFAULT_REPO_ID))
    parser.add_argument("--subfolder", default=os.environ.get("LAYA_SUBFOLDER", ""))
    parser.add_argument("--model-path", default=None, help="explicit model directory override")
    parser.add_argument("--mirror", action="store_true", help="use hf-mirror.com endpoint")
    parser.add_argument("--check", action="store_true", help="status only; never download")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    status = ensure_model(args.repo, args.subfolder, args.model_path, args.mirror, args.check)
    print(json.dumps(status, ensure_ascii=False))
    return 0 if status.get("complete") else 1


if __name__ == "__main__":
    raise SystemExit(main())
