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
