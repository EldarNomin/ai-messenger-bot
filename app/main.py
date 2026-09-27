from fastapi import FastAPI

from app.config.settings import get_settings

settings = get_settings()

app = FastAPI(title="AI Messenger Bot", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    # E0 skeleton. PostgreSQL and Redis dependency probes are added next.
    return {"status": "ready", "environment": settings.app_env}
