from __future__ import annotations

import os
from contextlib import AsyncExitStack, asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from .core import BridgeError, execute  # noqa: E402
from .mcp_server import mcp, registry  # noqa: E402

TOKEN = os.getenv("BRIDGE_TOKEN", "").strip()
if not TOKEN or TOKEN == "change-me-local":
    raise RuntimeError("BRIDGE_TOKEN must be set to a non-default value")

VERSION = "0.4.0"


def require_token(authorization: str | None = Header(default=None)) -> None:
    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def call(tool: str, args: dict) -> dict:
    try:
        return execute(registry, tool, args)
    except BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class ToolRequest(BaseModel):
    tool: str = Field(min_length=1, max_length=100)
    args: dict = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(
    title="ChatGPT Local Bridge",
    version=VERSION,
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "version": VERSION,
        "projects": registry.project_names(),
        "mcp_path": "/mcp",
        "capabilities": {
            "write": registry.allow_write,
            "delete": registry.allow_delete,
            "command": registry.allow_command,
            "git_read": True,
        },
    }


@app.get("/readyz")
def readyz() -> dict:
    return {
        "ready": True,
        "version": VERSION,
        "projects": registry.project_names(),
        "mcp_path": "/mcp",
    }


@app.post("/v1/execute", dependencies=[Depends(require_token)])
def execute_tool(request: ToolRequest) -> dict:
    return call(request.tool, request.args)


@app.get("/v1/projects", dependencies=[Depends(require_token)])
def projects() -> dict:
    return execute(registry, "projects", {})


@app.get("/v1/list", dependencies=[Depends(require_token)])
def list_path(project: str, path: str = ".") -> dict:
    return call("list_directory", {"project": project, "path": path})


@app.get("/v1/stat", dependencies=[Depends(require_token)])
def stat_path(project: str, path: str) -> dict:
    return call("stat", {"project": project, "path": path})


@app.get("/v1/search-files", dependencies=[Depends(require_token)])
def search_files(project: str, pattern: str, path: str = ".", limit: int = 200) -> dict:
    return call("search_files", {"project": project, "path": path, "pattern": pattern, "limit": limit})


@app.get("/v1/search-text", dependencies=[Depends(require_token)])
def search_text(project: str, query: str, path: str = ".", pattern: str = "*", limit: int = 100, case_sensitive: bool = False) -> dict:
    return call("search_text", {"project": project, "path": path, "query": query, "pattern": pattern, "limit": limit, "case_sensitive": case_sensitive})


@app.get("/v1/read-text", dependencies=[Depends(require_token)])
def read_text(project: str, path: str, start_line: int = 1, line_count: int = 400) -> dict:
    return call("read_file", {"project": project, "path": path, "start_line": start_line, "line_count": line_count})


@app.get("/v1/read-range", dependencies=[Depends(require_token)])
def read_range(project: str, path: str, offset: int = 0, length: int = 65536) -> dict:
    return call("read_range", {"project": project, "path": path, "offset": offset, "length": length})


@app.get("/v1/hash", dependencies=[Depends(require_token)])
def hash_file(project: str, path: str) -> dict:
    return call("hash_file", {"project": project, "path": path})


app.mount("/mcp", mcp.streamable_http_app())
