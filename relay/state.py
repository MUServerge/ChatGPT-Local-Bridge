from __future__ import annotations

import asyncio
import json
import secrets


class AgentConnection:
    def __init__(
        self,
        websocket,
        machine_id: str,
        projects: list[str],
        request_timeout: float,
    ):
        self.websocket = websocket
        self.machine_id = machine_id
        self.projects = projects
        self.request_timeout = request_timeout
        self.pending: dict[str, asyncio.Future] = {}

    async def call(self, tool: str, args: dict) -> dict:
        request_id = secrets.token_hex(16)
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future

        try:
            await self.websocket.send_text(
                json.dumps(
                    {
                        "type": "request",
                        "id": request_id,
                        "tool": tool,
                        "args": args,
                    }
                )
            )

            response = await asyncio.wait_for(
                future,
                timeout=self.request_timeout,
            )

            if not response.get("ok"):
                raise RuntimeError(response.get("error", "Agent error"))

            return response.get("result") or {}
        finally:
            self.pending.pop(request_id, None)

    def deliver(self, message: dict) -> None:
        future = self.pending.get(str(message.get("id", "")))

        if future and not future.done():
            future.set_result(message)

    def fail_all(self, reason: str) -> None:
        for future in list(self.pending.values()):
            if not future.done():
                future.set_exception(RuntimeError(reason))


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentConnection] = {}
        self._lock = asyncio.Lock()

    async def register(self, connection: AgentConnection) -> None:
        async with self._lock:
            previous = self._agents.get(connection.machine_id)

            if previous:
                previous.fail_all("Agent connection replaced")

            self._agents[connection.machine_id] = connection

    async def unregister(self, connection: AgentConnection) -> None:
        async with self._lock:
            if self._agents.get(connection.machine_id) is connection:
                self._agents.pop(connection.machine_id, None)

    async def get(self, machine_id: str) -> AgentConnection:
        async with self._lock:
            connection = self._agents.get(machine_id)

        if connection is None:
            raise RuntimeError(
                f"Machine is offline or unknown: {machine_id}"
            )

        return connection

    async def snapshot(self) -> list[dict]:
        async with self._lock:
            return [
                {
                    "machine": machine_id,
                    "projects": connection.projects,
                }
                for machine_id, connection in sorted(self._agents.items())
            ]


registry = AgentRegistry()
