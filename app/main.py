from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from asyncpg.exceptions import CannotConnectNowError, ConnectionDoesNotExistError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.middleware.last_activity import LastActivityMiddleware
from app.routers import openings, position_bookmarks, imports, auth
from app.routers.admin import router as admin_router
from app.routers.endgames import router as endgames_router
from app.routers.insights import router as insights_router
from app.routers.stats import router as stats_router
from app.routers.users import router as users_router
from app.services.engine import start_engine, stop_engine
from app.services.import_service import cleanup_orphaned_jobs
from app.services.insights_llm import get_insights_agent

_DB_TRANSIENT_ERRORS = (ConnectionDoesNotExistError, CannotConnectNowError)
_MAX_CAUSE_CHAIN_DEPTH = 5


def _sentry_before_send(event: dict, hint: dict) -> dict:
    """Group transient DB connection errors into a single Sentry issue.

    SQLAlchemy wraps asyncpg errors in DBAPIError, so we walk the __cause__
    chain to detect the underlying asyncpg exception type.
    """
    exc_info = hint.get("exc_info")
    if exc_info is not None:
        exc = exc_info[1]
        depth = 0
        while exc is not None and depth < _MAX_CAUSE_CHAIN_DEPTH:
            if isinstance(exc, _DB_TRANSIENT_ERRORS):
                event["fingerprint"] = ["db-connection-lost"]
                break
            exc = exc.__cause__
            depth += 1
    return event


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # D-22: validate insights Agent FIRST — startup failure is a deploy-blocker.
    # Orphan cleanup is best-effort and must not run if the app can't serve
    # the insights endpoint. Any pydantic-ai UserError / ValueError
    # propagates, aborting uvicorn startup (D-36).
    get_insights_agent()
    await cleanup_orphaned_jobs()
    # Phase 78 D-02: long-lived Stockfish UCI process. Comes AFTER existing startup
    # so engine startup failure does not mask deploy-blocker validation. try/finally
    # ensures stop_engine runs on exception during yield (graceful shutdown of UCI).
    await start_engine()
    try:
        yield
    finally:
        await stop_engine()


if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        # Only trace in production — dev traces are noise and waste quota
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,  # Do not send user PII (emails, IPs)
        before_send=_sentry_before_send,
    )

app = FastAPI(title="FlawChess", version="0.1.0", lifespan=lifespan)

# CORS only needed in development — Caddy provides same-origin routing in production
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(LastActivityMiddleware)

app.include_router(auth.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(openings.router, prefix="/api")
app.include_router(position_bookmarks.router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(endgames_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
