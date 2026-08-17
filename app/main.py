"""
FastAPI application entry point.
"""

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.document import router as document_router
from app.api.health import router as health_router
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(health_router)

app.include_router(auth_router)

app.include_router(document_router)


@app.get(
    "/",
    tags=["Root"],
)
def root() -> dict[str, str]:
    """
    Return application information.

    Returns:
        Application name and version.
    """
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }