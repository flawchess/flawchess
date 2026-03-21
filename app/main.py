from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analysis, position_bookmarks, imports, auth
from app.routers.stats import router as stats_router
from app.routers.users import router as users_router
from app.services.import_service import cleanup_orphaned_jobs


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await cleanup_orphaned_jobs()
    yield


app = FastAPI(title="FlawChess", version="0.1.0", lifespan=lifespan)

# CORS — allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(imports.router)
app.include_router(analysis.router)
app.include_router(position_bookmarks.router)
app.include_router(stats_router)
app.include_router(users_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
