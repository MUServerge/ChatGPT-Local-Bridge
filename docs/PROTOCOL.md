# MCP transport

The bridge serves MCP over Streamable HTTP at:

```text
http://127.0.0.1:8765/mcp
```

This endpoint is intentionally loopback-only and has no app-level authentication in the default tunnel setup.

The security boundary is:

1. the local listener is not reachable from the internet;
2. `tunnel-client` authenticates to OpenAI using the runtime API key;
3. ChatGPT reaches the MCP server through the OpenAI-hosted tunnel endpoint.

The local REST debug API under `/v1/*` remains protected by `BRIDGE_TOKEN`.

## Secure MCP Tunnel

The Windows host runs:

```text
tunnel-client
```

against the configured `tunnel_...` ID and forwards requests to:

```text
http://127.0.0.1:8765/mcp
```

No public URL is created and no project file is uploaded unless a tool explicitly returns requested bytes/text.
