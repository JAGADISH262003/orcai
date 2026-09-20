import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.models import Base

logger = logging.getLogger("orcai")
settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.database import engine

    if settings.is_sqlite:
        # Dev convenience: SQLite has no migration need in single-user mode.
        Base.metadata.create_all(bind=engine)
    else:
        logger.info("Postgres detected — ensure migrations are applied with `alembic upgrade head`")

    # Register job handlers before starting the worker.
    from app.services import job_handlers  # noqa: F401
    from app.services.jobs import worker_loop

    worker_task = asyncio.create_task(worker_loop())
    logger.info("job worker started (in-process)")
    try:
        yield
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="ORCAI Platform API",
        version="0.2.0",
        description="Dual-sided recruiting marketplace — agency command center backend.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "service": "orcai-api", "version": "0.2.0"}

    @app.get("/ready", tags=["health"])
    def ready():
        from app.core.database import SessionLocal

        db = None
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception as exc:  # noqa: BLE001
            logger.error("readiness probe failed: %s", exc)
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=503, content={"status": "unavailable"})
        finally:
            if db is not None:
                db.close()

    return app


app = create_app()
