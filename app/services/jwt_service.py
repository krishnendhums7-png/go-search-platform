"""
JWT Service.
"""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

from jose import JWTError
from jose import ExpiredSignatureError
from jose import jwt

from app.config import settings
from app.core.exceptions import ExpiredTokenException
from app.core.exceptions import InvalidTokenException


class JWTService:
    """
    Handles JWT creation and validation.
    """

    def create_access_token(
        self,
        data: dict[str, Any],
    ) -> str:
        """
        Create JWT token.
        """

        payload = data.copy()

        expire = datetime.now(
            UTC
        ) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

        payload["exp"] = expire

        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    def decode_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        """
        Decode JWT.
        """

        try:

            return jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

        except ExpiredSignatureError as exc:

            raise ExpiredTokenException(
                "Token expired."
            ) from exc

        except JWTError as exc:

            raise InvalidTokenException(
                "Invalid token."
            ) from exc


jwt_service = JWTService()