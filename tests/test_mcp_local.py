import os
import tempfile
from pathlib import Path

import pytest

_TEMP = tempfile.TemporaryDirectory()
_ROOT = Path(_TEMP.name) / "project"
_ROOT.mkdir()

os.environ["BRIDGE_PROJECT_ID"] = "test"
os.environ["BRIDGE_ROOT"] = str(_ROOT)
os.environ["BRIDGE_TOKEN"] = "test-local-secret"

from fastapi.testclient import TestClient

from bridge.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


def test_health_exposes_local_mcp(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["ok"] is True
    assert payload["projects"] == ["test"]
    assert payload["mcp_url"].endswith("/mcp")


def test_mcp_initialize_without_public_auth(client):
    response = client.post(
        "/mcp",
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "bridge-test",
                    "version": "1.0",
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 1
    assert "result" in payload
