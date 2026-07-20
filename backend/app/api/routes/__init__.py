"""API routes package."""
from app.api.routes.health import router as health_router
from app.api.routes.parse import router as parse_router
from app.api.routes.mineru import router as mineru_router
from app.api.routes.search import router as search_router
from app.api.routes.graph import router as graph_router
from app.api.routes.experience import router as experience_router
from app.api.routes.config import router as config_router
from app.api.routes.system import router as system_router

__all__ = [
    "health_router",
    "parse_router",
    "mineru_router",
    "search_router",
    "graph_router",
    "experience_router",
    "config_router",
    "system_router",
]
