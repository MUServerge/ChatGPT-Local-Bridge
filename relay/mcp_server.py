from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .state import registry

mcp = FastMCP(
    "ChatGPT Local Bridge",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
)


async def _call(
    machine: str,
    project: str,
    tool: str,
    **kwargs,
) -> dict:
    connection = await registry.get(machine)

    if project not in connection.projects:
        raise RuntimeError(
            f"Project '{project}' is not exposed by machine '{machine}'"
        )

    return await connection.call(
        tool,
        {
            "project": project,
            **kwargs,
        },
    )


@mcp.tool()
async def machines() -> dict:
    """List connected local machines and their read-only projects."""
    return {"machines": await registry.snapshot()}


@mcp.tool()
async def health(machine: str, project: str) -> dict:
    """Check a machine/project and return local read limits."""
    return await _call(machine, project, "health")


@mcp.tool()
async def list_files(
    machine: str,
    project: str,
    path: str = ".",
) -> dict:
    """List one directory below an allowlisted project root."""
    return await _call(machine, project, "list", path=path)


@mcp.tool()
async def stat(
    machine: str,
    project: str,
    path: str,
) -> dict:
    """Return metadata for one local file or directory."""
    return await _call(machine, project, "stat", path=path)


@mcp.tool()
async def search_files(
    machine: str,
    project: str,
    pattern: str,
    path: str = ".",
    limit: int = 200,
) -> dict:
    """Find files by wildcard name such as *.cpp or *.dll."""
    return await _call(
        machine,
        project,
        "search_files",
        path=path,
        pattern=pattern,
        limit=limit,
    )


@mcp.tool()
async def search_text(
    machine: str,
    project: str,
    query: str,
    path: str = ".",
    pattern: str = "*",
    limit: int = 100,
    case_sensitive: bool = False,
) -> dict:
    """Search bounded text files and return matching lines."""
    return await _call(
        machine,
        project,
        "search_text",
        path=path,
        query=query,
        pattern=pattern,
        limit=limit,
        case_sensitive=case_sensitive,
    )


@mcp.tool()
async def read_text(
    machine: str,
    project: str,
    path: str,
    start_line: int = 1,
    line_count: int = 400,
) -> dict:
    """Read a bounded line range from a local text file."""
    return await _call(
        machine,
        project,
        "read_text",
        path=path,
        start_line=start_line,
        line_count=line_count,
    )


@mcp.tool()
async def read_range(
    machine: str,
    project: str,
    path: str,
    offset: int,
    length: int,
) -> dict:
    """Read a bounded binary range; bytes are returned as base64."""
    return await _call(
        machine,
        project,
        "read_range",
        path=path,
        offset=offset,
        length=length,
    )


@mcp.tool()
async def hash_file(
    machine: str,
    project: str,
    path: str,
) -> dict:
    """Calculate SHA-256 locally without uploading the whole file."""
    return await _call(machine, project, "hash", path=path)


@mcp.tool()
async def pe_info(
    machine: str,
    project: str,
    path: str,
) -> dict:
    """Parse PE metadata from an executable, DLL, or runtime image."""
    return await _call(machine, project, "pe_info", path=path)


@mcp.tool()
async def pe_sections(
    machine: str,
    project: str,
    path: str,
) -> dict:
    """List PE sections with RVA, VA, virtual size, and raw mapping."""
    return await _call(machine, project, "pe_sections", path=path)


@mcp.tool()
async def va_to_offset(
    machine: str,
    project: str,
    path: str,
    va: str,
    mode: str = "auto",
) -> dict:
    """Map a virtual address like 0x00545180 to a local byte offset."""
    return await _call(
        machine,
        project,
        "va_to_offset",
        path=path,
        va=va,
        mode=mode,
    )


@mcp.tool()
async def read_va(
    machine: str,
    project: str,
    path: str,
    va: str,
    length: int = 256,
    mode: str = "auto",
) -> dict:
    """Read bounded bytes at a PE virtual address."""
    return await _call(
        machine,
        project,
        "read_va",
        path=path,
        va=va,
        length=length,
        mode=mode,
    )


@mcp.tool()
async def find_bytes(
    machine: str,
    project: str,
    path: str,
    signature: str,
    limit: int = 100,
) -> dict:
    """Search for a hex signature with ?? wildcards."""
    return await _call(
        machine,
        project,
        "find_bytes",
        path=path,
        signature=signature,
        limit=limit,
    )


@mcp.tool()
async def strings(
    machine: str,
    project: str,
    path: str,
    min_length: int = 5,
    limit: int = 500,
) -> dict:
    """Extract bounded printable ASCII strings from a local binary."""
    return await _call(
        machine,
        project,
        "strings",
        path=path,
        min_length=min_length,
        limit=limit,
    )


@mcp.tool()
async def disassemble(
    machine: str,
    project: str,
    path: str,
    va: str,
    length: int = 512,
    max_instructions: int = 80,
    mode: str = "auto",
) -> dict:
    """Disassemble bounded x86 code around a virtual address."""
    return await _call(
        machine,
        project,
        "disassemble",
        path=path,
        va=va,
        length=length,
        max_instructions=max_instructions,
        mode=mode,
    )
