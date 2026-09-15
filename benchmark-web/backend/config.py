"""Configuration for the benchmark-web backend.

Single source of truth is the monorepo root: `config.yml` (ports, embedding
model, vector settings) and `.env` (runtime overrides, service token). Nothing
in this package hardcodes a port, host, URL or model name — every value is read
from those two files, with the same ``env var > config.yml > default`` priority
the rest of the platform uses.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
BENCHMARK_WEB_DIR = BACKEND_DIR.parent
REPO_ROOT = BENCHMARK_WEB_DIR.parent

CONFIG_YML = REPO_ROOT / "config.yml"
ENV_FILE = REPO_ROOT / ".env"

#: Fallbacks only used when the shared config is unavailable (e.g. the package
#: is copied out of the monorepo). They mirror config.yml's dev section.
_DEFAULTS = {
    "backend_port": 8770,
    "frontend_port": 6789,
    "embedding_model": "BAAI/bge-m3",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "score_threshold": 0.35,
}


def _strip_comment(line: str) -> str:
    """Drop a YAML comment, but not a ``#`` that sits inside a value."""
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _parse_yaml_subset(text: str) -> dict:
    """Parse the nested-map subset of YAML that ``config.yml`` uses.

    Handles indentation-based mappings and scalar values; sequences (``- x``)
    are skipped because nothing this package reads lives in one. Keeping this
    dependency-free means the backend installs with no YAML library.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if stripped.startswith("- ") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            stack = [(-1, root)]
        parent = stack[-1][1]
        if value == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = value.strip("\"'")
    return root


def _read_env() -> dict[str, str]:
    """Read the repo-root ``.env`` (KEY=VALUE, ``#`` comments)."""
    values: dict[str, str] = {}
    if not ENV_FILE.is_file():
        return values
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _dig(tree: dict, *path: str):
    node = tree
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings."""

    app_mode: str
    backend_url: str
    web_url: str
    auth_token: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    score_threshold: float
    data_dir: Path
    hf_cache_dir: Path
    config_loaded: bool

    @property
    def project_search_url(self) -> str:
        """The platform's own vector-search endpoint (the QDCVR baseline)."""
        return f"{self.backend_url}/api/v1/search/vector"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Resolve settings once per process."""
    yml = _parse_yaml_subset(CONFIG_YML.read_text(encoding="utf-8")) if CONFIG_YML.is_file() else {}
    env = _read_env()
    mode = (env.get("APP_MODE") or os.environ.get("APP_MODE") or "dev").lower()
    section = "prod" if mode == "prod" else "dev"

    def pick(env_key: str, yml_path: tuple[str, ...], fallback_key: str):
        if env.get(env_key):
            return env[env_key]
        found = _dig(yml, *yml_path)
        return found if found is not None else _DEFAULTS[fallback_key]

    backend_port = int(pick("BACKEND_PORT", ("server", section, "backend_port"), "backend_port"))
    web_port = int(pick("WEB_PORT", ("server", section, "frontend_port"), "frontend_port"))
    token = env.get("MCP_AUTH_TOKEN") or os.environ.get("MCP_AUTH_TOKEN") or ""

    # Allow an explicit full-URL override; otherwise derive from the port.
    backend_url = (env.get("BACKEND_URL") or _dig(yml, "server", section, "backend_url")
                   or f"http://localhost:{backend_port}")
    backend_url = re.sub(r":\d+$", f":{backend_port}", str(backend_url).rstrip("/"))

    # The platform keeps its embedding snapshot in a shared cache. Point
    # huggingface_hub at it (and honour the offline flags from .env) so the
    # benchmark reuses the same model files instead of re-downloading ~2 GB.
    #
    # ``embedding.cache_dir`` is the *cache root*; huggingface_hub keeps repos
    # under its ``hub/`` subdirectory, and that is what ``cache_dir``/
    # ``cache_folder`` arguments must receive.
    cache_root = Path(str(_dig(yml, "embedding", "cache_dir") or "./models_cache"))
    if not cache_root.is_absolute():
        cache_root = (REPO_ROOT / cache_root).resolve()
    hub_cache = cache_root / "hub" if (cache_root / "hub").is_dir() else cache_root

    for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if env.get(key):
            os.environ.setdefault(key, env[key])

    # Point the hub cache at the platform's snapshot directory. HF_HUB_CACHE is
    # the precise knob: HF_HOME is frequently already set machine-wide (this
    # machine points it at D:\\Huggingface), so a setdefault on HF_HOME would be
    # a silent no-op and models would load from — or try to download into — the
    # wrong directory.
    if hub_cache.is_dir():
        os.environ["HF_HUB_CACHE"] = str(hub_cache)
        os.environ.setdefault("HF_HOME", str(cache_root))

    return Settings(
        app_mode=mode,
        backend_url=backend_url,
        web_url=f"http://localhost:{web_port}",
        auth_token=token.strip(),
        embedding_model=str(pick("EMBEDDING_MODEL", ("embedding", "model_name"), "embedding_model")),
        chunk_size=int(_dig(yml, "vector", "chunk_size") or _DEFAULTS["chunk_size"]),
        chunk_overlap=int(_dig(yml, "vector", "chunk_overlap") or _DEFAULTS["chunk_overlap"]),
        score_threshold=float(_dig(yml, "vector", "score_threshold") or _DEFAULTS["score_threshold"]),
        data_dir=BACKEND_DIR / "data",
        hf_cache_dir=hub_cache,
        config_loaded=CONFIG_YML.is_file(),
    )
