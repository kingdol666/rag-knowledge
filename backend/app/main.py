"""
RAG Knowledge Backend — FastAPI application.
"""
import logging
import logging.handlers
from pathlib import Path
from contextlib import asynccontextmanager
from app.api.routes.meditation import router as meditation_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
from app.middleware.rate_limit import init_rate_limiter, rate_limit_middleware
from app.middleware.auth_middleware import AuthMiddleware
from app.api.routes.auth import router as auth_router
from app.api.routes import (
    health_router,
    parse_router,
    mineru_router,
    search_router,
    graph_router,
    experience_router,
    config_router,
    system_router,
    soul_router,
    documents_router,
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

    # ── Auth: bootstrap MCP service token + user/token DB at startup ─────
    if config.auth_enabled:
        try:
            from app.services.auth_service import get_mcp_token, _get_conn
            _get_conn()  # ensure schema exists
            mcp_tok = get_mcp_token()  # reads env MCP_AUTH_TOKEN; generates into .env once
            logger.info("Token auth: ENABLED (MCP service token ready: %s...)",
                        mcp_tok[:12])
        except Exception:
            logger.exception("Auth bootstrap failed (middleware will reject all requests)")
    else:
        logger.info("Token auth: disabled (maintenance mode)")

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

    # ── Start local Neo4j if configured (Docker-free mode) ────────────
    graph_cfg = config.graph
    neo4j_manager = None
    if graph_cfg.get("enabled", False) and graph_cfg.get("mode", "local") == "local":
        if graph_cfg.get("auto_start", True):
            try:
                from app.utils.neo4j_manager import Neo4jManager

                neo4j_manager = Neo4jManager(graph_cfg)
                timeout = int(graph_cfg.get("startup_timeout", 120))
                if neo4j_manager.ensure_running(timeout=timeout):
                    app.state.neo4j_manager = neo4j_manager
                    logger.info(
                        "Neo4j (local) ready — bolt :%s, http :%s",
                        neo4j_manager.bolt_port, neo4j_manager.http_port)
                else:
                    logger.error("Neo4j (local) failed to start — graph features degraded")
            except Exception:
                logger.exception("Neo4j (local) startup failed (non-fatal)")

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
                    "Local mode: check backend/.neo4j; Docker mode: docker compose up -d neo4j",
                    health.get("error", "unknown error"),
                )
        except Exception:
            logger.exception("Neo4j startup probe failed (non-fatal)")
    else:
        logger.info("Graph (Neo4j) disabled in config — skipping probe")

    # ── Init Meditation DB ─────────────────────────────────────────
    try:
        from app.services.meditation_db import init_db
        init_db()
        logger.info("Meditation DB initialized")
    except Exception:
        logger.exception("Meditation DB init failed (non-fatal)")

    # ── Start Experience Meditation Scheduler ────────────────────────
    try:
        from app.services.experience_meditation_service import meditation_scheduler
        meditation_scheduler.start()
        if config.experience_auto_config.get("enabled", False):
            logger.info("Experience meditation: ENABLED (interval=%dh)",
                        config.experience_auto_config.get("interval_hours", 24))
        else:
            logger.info("Experience meditation: disabled (will activate if config enables it)")
    except Exception:
        logger.exception("Meditation scheduler startup failed (non-fatal)")

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

    # ── Stop Experience Meditation Scheduler ─────────────────────────
    try:
        from app.services.experience_meditation_service import meditation_scheduler
        await meditation_scheduler.stop()
    except Exception:
        pass

    logger.info("RAG Knowledge Backend stopped.")


from app.version import get_version

app = FastAPI(
    title="RAG Knowledge Backend",
    description="Backend API for RAG Knowledge Platform",
    version=get_version(),
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

# ── Token auth (2026-09-09): intercepts all /api/* — user tokens, MCP
#    service token, legacy shared token; whitelist = health + auth bootstrap.
#    Registered BEFORE routes so it wraps every endpoint (except health/auth).
app.add_middleware(AuthMiddleware)

# Register routes
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(parse_router)
app.include_router(mineru_router)
app.include_router(search_router)
app.include_router(graph_router)
app.include_router(experience_router)
app.include_router(config_router)
app.include_router(meditation_router)
app.include_router(soul_router)
app.include_router(system_router)
app.include_router(documents_router)


@app.get("/")
async def root():
    return {
        "service": "RAG Knowledge Backend",
        "version": get_version(),
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
