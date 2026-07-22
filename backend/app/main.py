"""
RAG Knowledge Backend — FastAPI application.
"""
import logging
import logging.handlers
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
from app.middleware.rate_limit import init_rate_limiter, rate_limit_middleware
from app.api.routes import (
    health_router,
    parse_router,
    mineru_router,
    search_router,
    graph_router,
    experience_router,
    config_router,
    system_router,
)

# ── Logging: console + rotating file ───────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FMT = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Console handler
console = logging.StreamHandler()
console.setFormatter(LOG_FMT)

# Rotating file handler (10 files x 10 MB = 100 MB max)
file_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "backend.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=10,
    encoding="utf-8",
)
file_handler.setFormatter(LOG_FMT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[console, file_handler],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RAG Knowledge Backend...")
    logger.info("Server: %s:%s", config.server_host, config.server_port)
    logger.info("CORS origins: %s", config.cors_origins)

    # ── Auth: auto-generate runtime token if enabled but none set ────────
    if config.auth_enabled and not config.auth_token:
        import secrets
        from app.utils.paths import PROJECT_ROOT
        token = secrets.token_hex(32)
        runtime_path = PROJECT_ROOT.parent / "storage" / ".runtime-token"
        try:
            runtime_path.parent.mkdir(parents=True, exist_ok=True)
            runtime_path.write_text(token, encoding="utf-8")
            config.set_runtime_token(token)
            logger.warning(
                "Auth enabled but KB_AUTH_TOKEN unset — generated runtime token "
                "written to %s. Set KB_AUTH_TOKEN in .env for stable cross-service auth.",
                runtime_path,
            )
        except Exception:
            logger.exception("Failed to write runtime token (auth will reject all writes)")
    if config.auth_enabled:
        logger.info("Shared-token auth: ENABLED (write/dangerous endpoints protected)")
    else:
        logger.info("Shared-token auth: disabled (default)")

    # ── Start MinerU API if configured ────────────────────────────────
    mineru_cfg = config.mineru
    mineru_manager = None
    if mineru_cfg.get("enabled", False):
        try:
            from app.utils.mineru_manager import MineruApiManager

            mineru_manager = MineruApiManager(
                host=mineru_cfg.get("host", "127.0.0.1"),
                # Port is NOT read from config — a free ephemeral port is picked
                # at runtime (avoids common dev/service ports). The resolved
                # port is exposed via mineru_manager.port / .api_url.
                port=None,
            )
            timeout = int(mineru_cfg.get("startup_timeout", 60))
            if mineru_manager.start(timeout=timeout):
                app.state.mineru_manager = mineru_manager
                logger.info(
                    "MinerU API started at %s", mineru_manager.api_url
                )
            else:
                logger.error("MinerU API failed to start")
        except Exception:
            logger.exception("MinerU API startup failed (non-fatal)")

    # ── Probe Neo4j (knowledge graph) if configured ──────────────────
    # Graph features degrade gracefully: if Neo4j is unreachable, search
    # still works (BM25 + vector); only graph expansion / entity queries 503.
    if config.graph_enabled:
        try:
            from app.services.graph_service import graph_service
            health = graph_service.health()
            if health.get("available"):
                logger.info("Neo4j connected: %s", health.get("uri"))
            else:
                logger.warning(
                    "Neo4j unavailable (%s) — graph features degraded. "
                    "Start it with: docker compose up -d neo4j",
                    health.get("error", "unknown error"),
                )
        except Exception:
            logger.exception("Neo4j startup probe failed (non-fatal)")
    else:
        logger.info("Graph (Neo4j) disabled in config — skipping probe")


    yield

    # ── Shutdown: stop MinerU API ──────────────────────────────────────
    if mineru_manager is not None:
        mineru_manager.stop()

    # ── Shutdown: close Neo4j driver ───────────────────────────────────
    if config.graph_enabled:
        try:
            from app.services.graph_service import graph_service
            graph_service.close()
            logger.info("Neo4j driver closed")
        except Exception:
            pass

    logger.info("RAG Knowledge Backend stopped.")


app = FastAPI(
    title="RAG Knowledge Backend",
    description="Backend API for RAG Knowledge Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = config.cors_origins
allow_all = origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting (sliding-window per IP; configurable via config.yml) ──
init_rate_limiter(config._config.get("server", {}))
app.middleware("http")(rate_limit_middleware)

# Register routes
app.include_router(health_router)
app.include_router(parse_router)
app.include_router(mineru_router)
app.include_router(search_router)
app.include_router(graph_router)
app.include_router(experience_router)
app.include_router(config_router)
app.include_router(system_router)


@app.get("/")
async def root():
    return {
        "service": "RAG Knowledge Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/health", include_in_schema=False)
async def health_root():
    """Root-level health probe (returns 200) for any external watchdog / dev
    tool that polls ``/health`` by convention. Without this, such probes log a
    noisy 404 (the real health endpoint is ``/api/v1/health``). Hidden from
    /docs to avoid clutter — it's just an alias."""
    return {"status": "healthy"}
