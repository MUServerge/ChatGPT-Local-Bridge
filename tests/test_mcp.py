import os

os.environ.setdefault("BRIDGE_PROJECT_ID", "test")
os.environ.setdefault("BRIDGE_ROOT", os.getcwd())
os.environ.setdefault("BRIDGE_TOKEN", "test-local-secret")
os.environ.setdefault("BRIDGE_ALLOW_WRITE", "true")
os.environ.setdefault("BRIDGE_ALLOW_DELETE", "false")
os.environ.setdefault("BRIDGE_ALLOW_COMMAND", "false")

import pytest
from fastapi.testclient import TestClient

from bridge.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["version"] == "0.4.0"
    assert payload["mcp_path"] == "/mcp"
    assert payload["capabilities"]["write"] is True
    assert payload["capabilities"]["delete"] is False
    assert "test" in payload["projects"]


def test_mcp_initialize(client):
    response = client.post(
        "/mcp",
        headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "bridge-test", "version": "1.0"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 1
    assert "result" in payload


def test_rest_execute_requires_token(client):
    response = client.post("/v1/execute", json={"tool": "projects", "args": {}})
    assert response.status_code == 401


def test_rest_execute_projects(client):
    response = client.post(
        "/v1/execute",
        headers={"Authorization": "Bearer test-local-secret"},
        json={"tool": "projects", "args": {}},
    )
    assert response.status_code == 200
    assert "test" in response.json()["projects"]
