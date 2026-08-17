"""
Authentication endpoints.
"""

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.core.exceptions import InvalidCredentialsException
from app.models.auth import LoginRequest
from app.models.auth import TokenResponse
from app.services.auth_service import auth_service

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
) -> TokenResponse:
    """
    Authenticate a user.
    """

    try:

        token = auth_service.login(
            request.email,
            request.password,
        )

        return TokenResponse(
            access_token=token,
        )

    except InvalidCredentialsException as exc:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc