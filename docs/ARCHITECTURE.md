# Architecture

ChatGPT connects to a self-hosted MCP relay over HTTPS. A Windows agent keeps an outbound authenticated connection to the relay and exposes only explicitly configured read-only project roots.

The local machine does not accept inbound internet connections. The relay routes bounded read-only requests and does not persist project file contents.

Initial project:
- machine: home-ssemu
- project: ssemu
- root: C:\Users\hatim\Desktop\SSEMU-2.5.9

The first tool surface is read-only: project listing, file metadata/search, bounded text/range reads, hashing, PE metadata, VA mapping, byte-pattern lookup, strings, and bounded x86 disassembly.
