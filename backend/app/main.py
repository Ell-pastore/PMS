"""FastAPI application entry point."""

from fastapi import FastAPI

from .core.config import settings
from .core.exceptions import register_exception_handlers
from .routes import api_router

app = FastAPI(title=settings.app_name)

# Register central exception handlers for PMSException, SQLAlchemy errors, IntegrityError, etc.
register_exception_handlers(app)

# Include aggregated API v1 router
app.include_router(api_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a lightweight application health response."""
    return {"status": "ok"}


if __name__ == "__main__":
    # Convenience entry point for `python -m backend.app.main` (run from repo root).
    # Preferred: `.venv/bin/uvicorn backend.app.main:app --reload`
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
