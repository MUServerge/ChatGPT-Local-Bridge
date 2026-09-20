import json
import os

os.environ.setdefault("RELAY_AGENT_TOKEN", "test-agent-secret")
os.environ.setdefault("RELAY_MCP_TOKEN", "test-mcp-secret")
os.environ.setdefault("RELAY_REQUEST_TIMEOUT", "2")

from fastapi.testclient import TestClient

from relay.app import app


def test_health_and_agent_registration():
    with TestClient(app) as client:
        response = client.get("/healthz")

        assert response.status_code == 200
        assert response.json()["ok"] is True

        with client.websocket_connect(
            "/agent/ws",
            headers={"Authorization": "Bearer test-agent-secret"},
        ) as websocket:
            websocket.send_text(
                json.dumps(
                    {
                        "type": "hello",
                        "machine_id": "test-machine",
                        "projects": ["test-project"],
                        "version": "test",
                    }
                )
            )

            ready = json.loads(websocket.receive_text())

            assert ready["type"] == "ready"
            assert ready["machine_id"] == "test-machine"

            response = client.get("/healthz")
            machines = response.json()["machines"]

            assert {
                "machine": "test-machine",
                "projects": ["test-project"],
            } in machines


def test_mcp_requires_authentication():
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
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

        assert response.status_code == 401


def test_mcp_initialize():
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={
                "Authorization": "Bearer test-mcp-secret",
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
