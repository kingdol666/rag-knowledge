"""Re-export the paths module for convenience."""
from app.utils.paths import (  # noqa: F401
    PROJECT_ROOT,
    CONFIG_PATH,
    SHARED_CONFIG_PATH,
    ENV_PATH,
    resolve_path,
)
