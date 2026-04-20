"""MirrorMind — FastAPI application entry point."""

import time
import uuid as _uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.rate_limit import limiter
from app.graphrag.neo4j_client import close_neo4j
from app.workers import discord_bot as discord_worker
from app.workers import telegram_bot as telegram_worker

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "app_starting",
        version=get_settings().app_version,
        model=get_settings().openai_model,
    )
    try:
        await telegram_worker.resume_all_bots()
        await discord_worker.resume_all_bots()
    except Exception:
        logger.exception("worker_resume_failed")
    yield
    # Graceful shutdown — stop workers, drain connections
    await telegram_worker.stop_all_bots()
    await discord_worker.stop_all_bots()
    await close_neo4j()
    from app.db.session import engine as _db_engine

    await _db_engine.dispose()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Rate limiting (slowapi)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"Rate limit exceeded: {exc.detail}",
            },
        )

    # Domain exception handler — consistent JSON error format
    from app.core.exceptions import MirrorMindError

    @app.exception_handler(MirrorMindError)
    async def _domain_error_handler(request: Request, exc: MirrorMindError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    # Catch-all for unhandled exceptions — never leak stack traces to clients
    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    app.add_middleware(SlowAPIMiddleware)

    # Request body size limit
    max_body = settings.max_request_body_bytes

    @app.middleware("http")
    async def _limit_body_size(request: Request, call_next):
        if max_body and request.method in {"POST", "PUT", "PATCH"}:
            cl = request.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > max_body:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": (
                            f"Request body too large "
                            f"({int(cl)} > {max_body} bytes)."
                        )
                    },
                )
        return await call_next(request)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Request-ID"],
    )

    # GZip compression for responses > 500 bytes
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Request logging middleware with request-id correlation
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(_uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        if not request.url.path.startswith("/docs") and not request.url.path.startswith(
            "/openapi"
        ):
            log = logger.warning if response.status_code >= 400 else logger.info
            log(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )
        return response

    # Register routers
    from app.api import (
        admin,
        agent_configs,
        auth,
        extensions,
        graph,
        interviews,
        io,
        memories,
        personas,
        policies,
        production,
        testing,
        training,
        writing_samples,
    )

    # Auth routes (public — no token required)
    app.include_router(auth.router, prefix="/api/v1")

    app.include_router(personas.router, prefix="/api/v1")
    app.include_router(memories.router, prefix="/api/v1")
    app.include_router(writing_samples.router, prefix="/api/v1")
    app.include_router(interviews.router, prefix="/api/v1")
    app.include_router(policies.router, prefix="/api/v1")
    app.include_router(testing.router, prefix="/api/v1")
    app.include_router(training.router, prefix="/api/v1")
    app.include_router(graph.router, prefix="/api/v1")
    app.include_router(agent_configs.router, prefix="/api/v1")
    app.include_router(io.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(production.router, prefix="/api/v1")
    app.include_router(extensions.router, prefix="/api/v1")

    return app


app = create_app()
