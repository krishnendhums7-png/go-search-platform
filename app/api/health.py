"""
Health check endpoints.
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
def health() -> dict[str, str]:
    """
    Return application health.

    Returns:
        Current application status.
    """

    return {
        "status": "healthy",
    }