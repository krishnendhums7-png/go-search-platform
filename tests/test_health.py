"""
Health endpoint tests.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    """
    Test health endpoint.
    """

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
    }


def test_root() -> None:
    """
    Test root endpoint.
    """

    response = client.get("/")

    assert response.status_code == 200

    assert response.json()["application"] == "Kerala GO Search"