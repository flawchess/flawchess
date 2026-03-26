from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.routers import analysis, position_bookmarks, imports, auth
from app.routers.endgames import router as endgames_router
from app.routers.stats import router as stats_router
from app.routers.users import router as users_router
from app.services.import_service import cleanup_orphaned_jobs


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await cleanup_orphaned_jobs()
    yield


if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,  # 10% of requests traced for performance visibility
        send_default_pii=False,  # Do not send user PII (emails, IPs)
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

app.include_router(auth.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(position_bookmarks.router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(endgames_router, prefix="/api")
app.include_router(users_router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
