from mcp.server.fastmcp import FastMCP

from .core import BridgeError, RootRegistry, execute

registry = RootRegistry.from_env()

mcp = FastMCP(
    "ChatGPT Local Bridge",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
)


def _call(tool: str, args: dict) -> dict:
    try:
        return execute(registry, tool, args)
    except BridgeError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool()
def projects() -> dict:
    """List the read-only local project roots exposed by this bridge."""
    return execute(registry, "projects", {})


@mcp.tool()
def health(project: str) -> dict:
    """Check one local project and return the configured read limits."""
    return _call("health", {"project": project})


@mcp.tool()
def list_files(project: str, path: str = ".") -> dict:
    """List one directory below an allowlisted project root."""
    return _call("list", {"project": project, "path": path})


@mcp.tool()
def stat(project: str, path: str) -> dict:
    """Return metadata for one local file or directory."""
    return _call("stat", {"project": project, "path": path})


@mcp.tool()
def search_files(
    project: str,
    pattern: str,
    path: str = ".",
    limit: int = 200,
) -> dict:
    """Find files by wildcard name such as *.cpp, *.dll, or *.bin."""
    return _call(
        "search_files",
        {
            "project": project,
            "path": path,
            "pattern": pattern,
            "limit": limit,
        },
    )


@mcp.tool()
def search_text(
    project: str,
    query: str,
    path: str = ".",
    pattern: str = "*",
    limit: int = 100,
    case_sensitive: bool = False,
) -> dict:
    """Search bounded text files and return matching lines."""
    return _call(
        "search_text",
        {
            "project": project,
            "path": path,
            "query": query,
            "pattern": pattern,
            "limit": limit,
            "case_sensitive": case_sensitive,
        },
    )


@mcp.tool()
def read_text(
    project: str,
    path: str,
    start_line: int = 1,
    line_count: int = 400,
) -> dict:
    """Read a bounded line range from one local text file."""
    return _call(
        "read_text",
        {
            "project": project,
            "path": path,
            "start_line": start_line,
            "line_count": line_count,
        },
    )


@mcp.tool()
def read_range(
    project: str,
    path: str,
    offset: int,
    length: int,
) -> dict:
    """Read a bounded binary byte range; data is returned as base64."""
    return _call(
        "read_range",
        {
            "project": project,
            "path": path,
            "offset": offset,
            "length": length,
        },
    )


@mcp.tool()
def hash_file(project: str, path: str) -> dict:
    """Calculate SHA-256 locally without uploading the complete file."""
    return _call("hash", {"project": project, "path": path})


@mcp.tool()
def pe_info(project: str, path: str) -> dict:
    """Parse PE metadata from an executable, DLL, or runtime image."""
    return _call("pe_info", {"project": project, "path": path})


@mcp.tool()
def pe_sections(project: str, path: str) -> dict:
    """List PE sections with RVA, VA, virtual size, and raw mapping."""
    return _call("pe_sections", {"project": project, "path": path})


@mcp.tool()
def va_to_offset(
    project: str,
    path: str,
    va: str,
    mode: str = "auto",
) -> dict:
    """Map a virtual address like 0x00545180 to a byte offset."""
    return _call(
        "va_to_offset",
        {
            "project": project,
            "path": path,
            "va": va,
            "mode": mode,
        },
    )


@mcp.tool()
def read_va(
    project: str,
    path: str,
    va: str,
    length: int = 256,
    mode: str = "auto",
) -> dict:
    """Read bounded bytes from a PE virtual address."""
    return _call(
        "read_va",
        {
            "project": project,
            "path": path,
            "va": va,
            "length": length,
            "mode": mode,
        },
    )


@mcp.tool()
def find_bytes(
    project: str,
    path: str,
    signature: str,
    limit: int = 100,
) -> dict:
    """Search a binary for a hex signature with ?? wildcards."""
    return _call(
        "find_bytes",
        {
            "project": project,
            "path": path,
            "signature": signature,
            "limit": limit,
        },
    )


@mcp.tool()
def strings(
    project: str,
    path: str,
    min_length: int = 5,
    limit: int = 500,
) -> dict:
    """Extract bounded printable ASCII strings from a local binary."""
    return _call(
        "strings",
        {
            "project": project,
            "path": path,
            "min_length": min_length,
            "limit": limit,
        },
    )


@mcp.tool()
def disassemble(
    project: str,
    path: str,
    va: str,
    length: int = 512,
    max_instructions: int = 80,
    mode: str = "auto",
) -> dict:
    """Disassemble bounded x86 code around a virtual address."""
    return _call(
        "disassemble",
        {
            "project": project,
            "path": path,
            "va": va,
            "length": length,
            "max_instructions": max_instructions,
            "mode": mode,
        },
    )
