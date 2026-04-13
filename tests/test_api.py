from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# -----------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------
 

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# -----------------------------------------------------------------------
# /api/ping
# -----------------------------------------------------------------------
 
def test_ping():
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}
 
 
def test_ping_method_not_allowed():
    response = client.post("/api/ping")
    assert response.status_code == 405

# -----------------------------------------------------------------------
# /api/messages
# -----------------------------------------------------------------------
 
def test_messages_post():
    response = client.post(
        "/api/messages",
        json={"type": "message", "text": "How many vacation days do I get?"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "received"}
 
 
def test_messages_get_not_allowed():
    """GET on /api/messages should return 405 Method Not Allowed."""
    response = client.get("/api/messages")
    assert response.status_code == 405
 
 
def test_messages_empty_body():
    """Empty body should still return 200 at this stub stage."""
    response = client.post("/api/messages", json={})
    assert response.status_code == 200
 
 
def test_messages_content_type_json():
    """Verify the response is JSON."""
    response = client.post("/api/messages", json={"type": "message", "text": "hi"})
    assert response.headers["content-type"] == "application/json"
    
 
# -----------------------------------------------------------------------
# General
# -----------------------------------------------------------------------
 
 
def test_unknown_route_returns_404():
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
 
 
def test_root_returns_404():
    """No route is registered at / — should 404 not 500."""
    response = client.get("/")
    assert response.status_code == 404


# -----------------------------------------------------------------------
# Docs / OpenAPI
# -----------------------------------------------------------------------


def test_swagger_ui_available():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_schema_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200


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
    assert "/api/messages" in paths