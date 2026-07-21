import os
import re
from typing import Any

import yaml


ENV_VAR_PATTERN = re.compile(r'\$\{(\w+)(?::-([^}]*))?\}')

def _expand_env(value: str) -> str:
    """Expand ${VAR} and ${VAR:-default} patterns in a string value."""
    if not isinstance(value, str):
        return value
    def _replace(m):
        var = m.group(1)
        default = m.group(2) if m.group(2) is not None else ''
        return os.environ.get(var, default)
    return ENV_VAR_PATTERN.sub(_replace, value)

def _expand_env_in_config(obj: Any) -> Any:
    """Recursively expand env vars in all string values in a dict/list."""
    if isinstance(obj, dict):
        return {k: _expand_env_in_config(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_in_config(v) for v in obj]
    if isinstance(obj, str):
        return _expand_env(obj)
    return obj


def _detect_mode() -> str:
    """Detect 'dev' or 'prod' from environment.

    Priority:
      1. APP_MODE env — explicit choice.
      2. NO_RELOAD=1  — force prod (disable hot reload).
      3. Fallback     — dev (matches JS-side default in paths.mjs / dynamic-config.ts).
    """
    no_reload = os.environ.get("NO_RELOAD", "0").strip() == "1"
    if no_reload:
        return "prod"
    mode = os.environ.get("APP_MODE", "").strip().lower()
    if mode in ("dev", "prod"):
        return mode
    return "dev"


# Runtime-generated auth token (set by main.py lifespan when auth enabled + no env token).
_runtime_token: str = ""


class Config:
    """Configuration manager — loads from config.yml with env-aware mode.

    Reads both:
      - rag-knowledge/config.yml     (shared: server, storage, vector, graph, ...)
      - backend/config.yml           (private: mineru, ...)

    Shared config sections are merged into the private config.
    Env vars override config.yml values where applicable.
    """

    _instance = None
    _config: dict | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self):
        from app.utils.paths import CONFIG_PATH, SHARED_CONFIG_PATH

        # 1. Read backend/config.yml (private: mineru, etc.)
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

        # 2. Read rag-knowledge/config.yml (shared: server, storage, vector, graph, ...)
        shared: dict = {}
        if SHARED_CONFIG_PATH and SHARED_CONFIG_PATH.exists():
            with open(SHARED_CONFIG_PATH, encoding="utf-8") as f:
                shared = yaml.safe_load(f) or {}

        # 3. Merge: server section with mode overlay, other sections directly
        if "server" in shared:
            self._config.setdefault("server", {}).update(shared["server"])

        for section in ("storage", "vector", "embedding", "graph", "search"):
            if section in shared:
                self._config[section] = shared[section]

        # 4. Expand ${VAR:-default} env var references in all values
        self._config = _expand_env_in_config(self._config)

    def reload(self):
        self._load_config()

    # ── Server ────────────────────────────────────────────────────────

    @property
    def app_mode(self) -> str:
        return _detect_mode()

    @property
    def server_host(self) -> str:
        return self._server_cfg.get("host", "0.0.0.0")

    @property
    def server_port(self) -> int:
        return int(self._server_cfg.get("backend_port", 8765))

    @property
    def cors_origins(self) -> list:
        return self._server_cfg.get("cors_origins", ["*"])

    @property
    def auth_enabled(self) -> bool:
        """Whether shared-token auth is enabled (server.auth.enabled, default false).

        When false, all verify_token checks are skipped — zero-config local use.
        """
        return bool(self._server_cfg.get("auth", {}).get("enabled", False))

    @property
    def auth_token(self) -> str:
        """The shared auth token. Reads env KB_AUTH_TOKEN first, then runtime-generated.

        Set at runtime via set_runtime_token() when enabled=true and no env token exists.
        """
        env_token = os.environ.get("KB_AUTH_TOKEN", "").strip()
        if env_token:
            return env_token
        return _runtime_token

    def set_runtime_token(self, token: str) -> None:
        """Set a runtime-generated token (when enabled=true and no env token)."""
        global _runtime_token
        _runtime_token = token

    @property
    def _server_cfg(self) -> dict:
        mode = self.app_mode
        base = self._config.get("server", {})
        merged: dict = {}
        for k, v in base.items():
            if k not in ("dev", "prod"):
                merged[k] = v
        merged.update(base.get(mode, {}))
        return merged

    # ── MinerU ────────────────────────────────────────────────────────

    @property
    def mineru(self) -> dict:
        return self._config.get("mineru", {})

    # ── Storage ───────────────────────────────────────────────────────

    @property
    def storage(self) -> dict:
        return self._config.get("storage", {})

    @property
    def storage_tree_fs_root(self) -> str:
        """web 端 tree-file-system 的路径（相对项目根或绝对）。

        .env 的 TREE_STORAGE_PATH 优先级最高，否则从 config.yml 读取。
        """
        env_val = os.environ.get("TREE_STORAGE_PATH", "").strip()
        if env_val:
            return env_val
        return self.storage.get("tree_fs_root", "./storage/tree-file-system")

    # ── Vector ────────────────────────────────────────────────────────

    @property
    def vector(self) -> dict:
        return self._config.get("vector", {})

    @property
    def vector_enabled(self) -> bool:
        return bool(self.vector.get("enabled", False))

    @property
    def vector_persist_dir(self) -> str:
        return self.vector.get("persist_dir", "./chroma_db")

    @property
    def vector_collection_prefix(self) -> str:
        return self.vector.get("collection_prefix", "kb_")

    @property
    def vector_chunk_size(self) -> int:
        return int(self.vector.get("chunk_size", 500))

    @property
    def vector_chunk_overlap(self) -> int:
        return int(self.vector.get("chunk_overlap", 50))

    @property
    def vector_top_k(self) -> int:
        return int(self.vector.get("top_k", 5))

    @property
    def vector_score_threshold(self) -> float:
        return float(self.vector.get("score_threshold", 0.35))

    @property
    def experience_score_threshold(self) -> float:
        """经验向量检索的最低相关度（高于文档阈值，避免聚焦短内容被无关 query 错配）。"""
        return float(self.vector.get("experience_score_threshold", 0.55))

    # ── Embedding ─────────────────────────────────────────────────────

    @property
    def embedding(self) -> dict:
        return self._config.get("embedding", {})

    @property
    def embedding_model_name(self) -> str:
        return self.embedding.get("model_name", "BAAI/bge-m3")

    @property
    def embedding_cache_dir(self) -> str:
        return self.embedding.get("cache_dir", "./models_cache")

    @property
    def embedding_device(self) -> str:
        """Auto-detect best accelerator; fall back to config or cpu.

        Priority:
          1. Config file value (e.g. "cuda", "cpu", "mps")
          2. "auto" or unset → auto-detect: CUDA > MPS > CPU
          3. Fallback → "cpu"
        """
        device = self.embedding.get("device")
        if device and device != "auto":
            return device
        # auto-detect: prefer CUDA, then MPS (Apple Silicon), else CPU
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    # ── Graph (Neo4j) ─────────────────────────────────────────────────

    @property
    def graph(self) -> dict:
        return self._config.get("graph", {})

    @property
    def graph_enabled(self) -> bool:
        return bool(self.graph.get("enabled", False))

    @property
    def graph_uri(self) -> str:
        return self.graph.get("uri", "bolt://127.0.0.1:7687")

    @property
    def graph_username(self) -> str:
        return self.graph.get("username", "neo4j")

    @property
    def graph_password(self) -> str:
        """Read Neo4j password. Env NEO4J_PASSWORD wins; falls back to config.yml.

        ${VAR:-default} patterns in config.yml are already expanded by
        _expand_env_in_config() during _load_config(), so only plain
        env-override logic is needed here.
        """
        return os.environ.get("NEO4J_PASSWORD") or self.graph.get("password", "")

    @property
    def graph_database(self) -> str:
        return self.graph.get("database", "neo4j")

    @property
    def graph_pool_config(self) -> dict:
        """Neo4j driver connection-pool settings (kwargs for GraphDatabase.driver).

        Values from config.yml graph.pool section; each key is optional.
        """
        pool = self.graph.get("pool", {})
        cfg: dict[str, int | float] = {}
        raw = pool.get("max_connection_pool_size")
        if raw is not None:
            cfg["max_connection_pool_size"] = int(raw)
        raw = pool.get("connection_acquisition_timeout")
        if raw is not None:
            cfg["connection_acquisition_timeout"] = int(raw)
        raw = pool.get("max_connection_lifetime")
        if raw is not None:
            cfg["max_connection_lifetime"] = int(raw)
        # Python driver never hides our exceptions (5.x+ default)
        return cfg

    @property
    def graph_retry_config(self) -> dict[str, int | float]:
        """Retry settings for transient Neo4j failures.

        Returns {"max_attempts": int, "base_delay": float} from config.yml
        graph.retry section, falling back to sensible defaults.
        """
        retry = self.graph.get("retry", {})
        return {
            "max_attempts": int(retry.get("max_attempts", 3)),
            "base_delay": float(retry.get("base_delay", 0.5)),
        }

    # ── Search ────────────────────────────────────────────────────────

    @property
    def search_config(self) -> dict:
        return self._config.get("search", {})

    @property
    def two_stage_config(self) -> dict:
        return self.search_config.get("two_stage", {})


config = Config()


def get_config() -> Config:
    return config
