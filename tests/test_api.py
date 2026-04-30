from http import HTTPStatus

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# -----------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------


def test_health_check():
    response = client.get("/health")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


# -----------------------------------------------------------------------
# /api/ping
# -----------------------------------------------------------------------


def test_ping():
    response = client.get("/api/ping")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "pong"}


def test_ping_method_not_allowed():
    response = client.post("/api/ping")
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


# -----------------------------------------------------------------------
# /api/conversations
# -----------------------------------------------------------------------


def test_new_conversation():
    response = client.post(
        "/api/conversations",
        json={"metadata": {"topic": "demo"}},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/json"
    assert response.json()["metadata"]["topic"] == "demo"
    assert isinstance(response.json()["id"], str)


def test_conversations_get_not_allowed():
    """GET on /api/conversations should return 405 Method Not Allowed."""
    response = client.get("/api/conversations")
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


# -----------------------------------------------------------------------
# General
# -----------------------------------------------------------------------


def test_unknown_route_returns_404():
    response = client.get("/api/does-not-exist")
    assert response.status_code == HTTPStatus.NOT_FOUND


# -----------------------------------------------------------------------
# Docs / OpenAPI
# -----------------------------------------------------------------------


def test_swagger_ui_available():
    response = client.get("/docs")
    assert response.status_code == HTTPStatus.OK
    assert "text/html" in response.headers["content-type"]


def test_openapi_schema_available():
    response = client.get("/openapi.json")
    assert response.status_code == HTTPStatus.OK


def test_openapi_schema_structure():
    response = client.get("/openapi.json")
    schema = response.json()
    assert schema["info"]["title"] == "HR AI Chatbot"
    assert schema["info"]["version"] == "0.1.0"


def test_openapi_schema_contains_expected_routes():
    response = client.get("/openapi.json")
    paths = response.json()["paths"]
    assert "/health" in paths
    assert "/api/ping" in paths
    assert "/api/conversations" in paths
