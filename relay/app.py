from __future__ import annotations

import json
import os
from contextlib import AsyncExitStack, asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .mcp_server import mcp
from .state import AgentConnection, registry

load_dotenv()

AGENT_TOKEN = os.getenv("RELAY_AGENT_TOKEN", "").strip()
MCP_TOKEN = os.getenv("RELAY_MCP_TOKEN", "").strip()
REQUEST_TIMEOUT = float(os.getenv("RELAY_REQUEST_TIMEOUT", "30"))

if not AGENT_TOKEN or AGENT_TOKEN == "change-me-agent":
    raise RuntimeError("RELAY_AGENT_TOKEN must be set")

if not MCP_TOKEN or MCP_TOKEN == "change-me-mcp":
    raise RuntimeError("RELAY_MCP_TOKEN must be set")


class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            if request.headers.get("authorization") != f"Bearer {MCP_TOKEN}":
                return JSONResponse(
                    {"detail": "Unauthorized"},
                    status_code=401,
                )

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(
    title="ChatGPT Local Bridge Relay",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(MCPAuthMiddleware)


@app.get("/healthz")
async def healthz() -> dict:
    return {
        "ok": True,
        "machines": await registry.snapshot(),
    }


@app.websocket("/agent/ws")
async def agent_websocket(websocket: WebSocket):
    if websocket.headers.get("authorization") != f"Bearer {AGENT_TOKEN}":
        await websocket.close(code=4401)
        return

    await websocket.accept()

    connection = None

    try:
        hello = json.loads(await websocket.receive_text())

        if hello.get("type") != "hello":
            await websocket.close(code=4400)
            return

        machine_id = str(hello.get("machine_id", "")).strip()
        projects = [
            str(project).strip()
            for project in hello.get("projects", [])
            if str(project).strip()
        ]

        if not machine_id or not projects:
            await websocket.close(code=4400)
            return

        connection = AgentConnection(
            websocket=websocket,
            machine_id=machine_id,
            projects=projects,
            request_timeout=REQUEST_TIMEOUT,
        )

        await registry.register(connection)

        await websocket.send_text(
            json.dumps(
                {
                    "type": "ready",
                    "machine_id": machine_id,
                }
            )
        )

        while True:
            message = json.loads(await websocket.receive_text())

            if message.get("type") == "response":
                connection.deliver(message)

    except WebSocketDisconnect:
        pass
    finally:
        if connection is not None:
            connection.fail_all("Agent disconnected")
            await registry.unregister(connection)


app.mount("/mcp", mcp.streamable_http_app())
