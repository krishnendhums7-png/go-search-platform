"""
Temporary user repository.

This will be replaced with PostgreSQL in Module 2.
"""

from app.models.role import Role
from app.models.user import User
from app.services.password_service import password_service


class UserRepository:
    """
    Temporary in-memory repository.
    """

    def __init__(self) -> None:

        admin = User(
            full_name="Administrator",
            email="admin@gosearch.com",
            hashed_password=password_service.hash_password(
                "admin123"
            ),
            role=Role.ADMIN,
        )

        citizen = User(
            full_name="Citizen",
            email="citizen@gosearch.com",
            hashed_password=password_service.hash_password(
                "citizen123"
            ),
            role=Role.CITIZEN,
        )

        self._users = {
            admin.email: admin,
            citizen.email: citizen,
        }

    def find_by_email(
        self,
        email: str,
    ) -> User | None:
        """
        Find user by email.
        """

        return self._users.get(email)


user_repository = UserRepository()