from app.models.role import Role
from app.models.user import User


def test_default_role():

    user = User(
        full_name="Test User",
        email="test@example.com",
        hashed_password="hashed",
    )

    assert user.role == Role.CITIZEN


def test_admin_role():

    user = User(
        full_name="Admin",
        email="admin@example.com",
        hashed_password="hashed",
        role=Role.ADMIN,
    )

    assert user.role == Role.ADMIN