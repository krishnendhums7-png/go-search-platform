"""
JWT tests.
"""

from app.services.jwt_service import jwt_service


def test_create_token():

    token = jwt_service.create_access_token(
        {
            "user_id": "1",
            "email": "admin@test.com",
            "role": "ADMIN",
        }
    )

    assert isinstance(
        token,
        str,
    )


def test_decode_token():

    token = jwt_service.create_access_token(
        {
            "user_id": "1",
            "email": "admin@test.com",
            "role": "ADMIN",
        }
    )

    payload = jwt_service.decode_token(
        token
    )

    assert payload["email"] == "admin@test.com"

    assert payload["role"] == "ADMIN"