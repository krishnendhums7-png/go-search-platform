"""
FastAPI application entry point.
"""

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.document import router as document_router
from app.api.health import router as health_router
from app.config import settings
from app.api.search import router as search_router
from app.api.status import router as status_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)

app.include_router(auth_router)

app.include_router(document_router)

app.include_router(search_router)
app.include_router(status_router)

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