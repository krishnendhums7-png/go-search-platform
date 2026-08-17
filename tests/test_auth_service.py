from app.services.auth_service import auth_service


def test_login():

    token = auth_service.login(
        "admin@gosearch.com",
        "admin123",
    )

    assert isinstance(
        token,
        str,
    )