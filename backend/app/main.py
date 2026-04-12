"""MirrorMind — FastAPI application entry point."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.graphrag.neo4j_client import close_neo4j

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "app_starting",
        version=get_settings().app_version,
        model=get_settings().openai_model,
    )
    yield
    await close_neo4j()
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

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import traceback as _tb

        start = time.time()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                path=request.url.path,
                error=str(exc),
                traceback=_tb.format_exc(),
            )
            raise
        duration_ms = round((time.time() - start) * 1000)
        if not request.url.path.startswith("/docs") and not request.url.path.startswith(
            "/openapi"
        ):
            logger.info(
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

    return app


app = create_app()
