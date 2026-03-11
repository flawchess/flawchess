from fastapi import FastAPI

from app.routers import imports

app = FastAPI(title="Chessalytics", version="0.1.0")

app.include_router(imports.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
