# Agent relay protocol

The local Windows agent connects outbound to the relay WebSocket endpoint:

`/agent/ws`

It authenticates with:

`Authorization: Bearer <RELAY_AGENT_TOKEN>`

The first message advertises one machine and its read-only projects:

```json
{"type":"hello","machine_id":"home-ssemu","projects":["ssemu"],"version":"0.2.0"}
```

Relay request:

```json
{"type":"request","id":"opaque-id","tool":"read_va","args":{"project":"ssemu","path":"main-runtime-image.bin","va":"0x00545180","length":512}}
```

Successful response:

```json
{"type":"response","id":"opaque-id","ok":true,"result":{}}
```

Error response:

```json
{"type":"response","id":"opaque-id","ok":false,"error":"bounded error"}
```

The relay keeps only connection state and in-flight requests in memory. Project files are not persisted by the relay.
