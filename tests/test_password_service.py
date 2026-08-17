"""
Tests for PasswordService.
"""

from app.services.password_service import password_service


def test_hash_password() -> None:
    """
    Test password hashing.
    """

    password = "MySecurePassword123"

    hashed = password_service.hash_password(password)

    assert hashed != password

    assert isinstance(hashed, str)


def test_verify_password_success() -> None:
    """
    Test successful password verification.
    """

    password = "MySecurePassword123"

    hashed = password_service.hash_password(password)

    assert password_service.verify_password(
        password,
        hashed,
    )


def test_verify_password_failure() -> None:
    """
    Test failed password verification.
    """

    password = "MySecurePassword123"

    hashed = password_service.hash_password(password)

    assert not password_service.verify_password(
        "WrongPassword",
        hashed,
    )