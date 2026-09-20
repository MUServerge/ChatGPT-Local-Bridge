from __future__ import annotations

import asyncio
import json
import os
import platform
import socket

import websockets
from dotenv import load_dotenv

from .core import BridgeError, RootRegistry, execute

load_dotenv()

MACHINE_ID = os.getenv("BRIDGE_MACHINE_ID", socket.gethostname()).strip()
RELAY_WS_URL = os.getenv("RELAY_WS_URL", "").strip()
AGENT_TOKEN = os.getenv("RELAY_AGENT_TOKEN", "").strip()

if not MACHINE_ID:
    raise RuntimeError("BRIDGE_MACHINE_ID is required")

if not RELAY_WS_URL:
    raise RuntimeError("RELAY_WS_URL is required")

if not AGENT_TOKEN or AGENT_TOKEN == "change-me-agent":
    raise RuntimeError("RELAY_AGENT_TOKEN must be set")

registry = RootRegistry.from_env()


async def run() -> None:
    reconnect_delay = 1

    while True:
        try:
            async with websockets.connect(
                RELAY_WS_URL,
                additional_headers={
                    "Authorization": f"Bearer {AGENT_TOKEN}",
                },
                max_size=16 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
            ) as websocket:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "hello",
                            "machine_id": MACHINE_ID,
                            "projects": registry.project_names(),
                            "platform": platform.platform(),
                            "version": "0.2.0",
                        }
                    )
                )

                reconnect_delay = 1

                async for raw_message in websocket:
                    message = json.loads(raw_message)

                    if message.get("type") != "request":
                        continue

                    request_id = str(message.get("id", ""))
                    tool = str(message.get("tool", ""))
                    args = message.get("args") or {}

                    try:
                        result = await asyncio.to_thread(
                            execute,
                            registry,
                            tool,
                            args,
                        )

                        response = {
                            "type": "response",
                            "id": request_id,
                            "ok": True,
                            "result": result,
                        }
                    except (BridgeError, OSError, ValueError) as exc:
                        response = {
                            "type": "response",
                            "id": request_id,
                            "ok": False,
                            "error": str(exc),
                        }

                    await websocket.send(json.dumps(response))
        except Exception as exc:
            print(f"[agent] disconnected: {exc}")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 30)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
