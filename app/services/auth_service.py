"""
Authentication service.
"""

from app.core.exceptions import InvalidCredentialsException
from app.repositories.user_repository import user_repository
from app.services.jwt_service import jwt_service
from app.services.password_service import password_service


class AuthenticationService:
    """
    Authentication business logic.
    """

    def login(
        self,
        email: str,
        password: str,
    ) -> str:

        user = user_repository.find_by_email(
            email
        )

        if user is None:
            raise InvalidCredentialsException(
                "Invalid email or password."
            )

        if not password_service.verify_password(
            password,
            user.hashed_password,
        ):
            raise InvalidCredentialsException(
                "Invalid email or password."
            )

        return jwt_service.create_access_token(
            {
                "user_id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            }
        )


auth_service = AuthenticationService()