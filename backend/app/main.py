"""FastAPI application entry point."""

from fastapi import FastAPI

from .core.config import settings


app = FastAPI(title=settings.app_name)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a lightweight application health response."""

    return {"status": "ok"}
