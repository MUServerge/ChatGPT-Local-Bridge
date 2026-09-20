from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .core import BridgeError, RootRegistry, execute

load_dotenv()
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
    """List the local project roots exposed by this bridge."""
    return execute(registry, "projects", {})


@mcp.tool()
def health(project: str) -> dict:
    """Check one local project and report active bridge capabilities."""
    return _call("health", {"project": project})


@mcp.tool()
def list_directory(project: str, path: str = ".") -> dict:
    """List one directory below an allowlisted project root."""
    return _call("list_directory", {"project": project, "path": path})


@mcp.tool()
def directory_tree(project: str, path: str = ".", max_depth: int = 4, max_entries: int = 2000) -> dict:
    """Return a bounded recursive directory tree."""
    return _call("directory_tree", {"project": project, "path": path, "max_depth": max_depth, "max_entries": max_entries})


@mcp.tool()
def stat(project: str, path: str) -> dict:
    """Return metadata for one local file or directory."""
    return _call("stat", {"project": project, "path": path})


@mcp.tool()
def search_files(project: str, pattern: str, path: str = ".", limit: int = 200) -> dict:
    """Find files by wildcard name such as *.cpp, *.vcxproj, or *.ini."""
    return _call("search_files", {"project": project, "path": path, "pattern": pattern, "limit": limit})


@mcp.tool()
def search_text(project: str, query: str, path: str = ".", pattern: str = "*", limit: int = 100, case_sensitive: bool = False) -> dict:
    """Search bounded text files and return matching lines."""
    return _call("search_text", {"project": project, "path": path, "query": query, "pattern": pattern, "limit": limit, "case_sensitive": case_sensitive})


@mcp.tool()
def read_file(project: str, path: str, start_line: int = 1, line_count: int = 400) -> dict:
    """Read a bounded line range from one local text file."""
    return _call("read_file", {"project": project, "path": path, "start_line": start_line, "line_count": line_count})


@mcp.tool()
def read_multiple_files(project: str, paths: list[str], line_count: int = 400) -> dict:
    """Read several bounded local text files in one call."""
    return _call("read_multiple_files", {"project": project, "paths": paths, "line_count": line_count})


@mcp.tool()
def read_range(project: str, path: str, offset: int = 0, length: int = 65536) -> dict:
    """Read a bounded binary byte range; data is returned as base64."""
    return _call("read_range", {"project": project, "path": path, "offset": offset, "length": length})


@mcp.tool()
def hash_file(project: str, path: str) -> dict:
    """Calculate SHA-256 locally without uploading the complete file."""
    return _call("hash_file", {"project": project, "path": path})


@mcp.tool()
def write_file(project: str, path: str, content: str, expected_sha256: str = "") -> dict:
    """Create or replace one text file atomically inside an allowlisted root."""
    return _call("write_file", {"project": project, "path": path, "content": content, "expected_sha256": expected_sha256})


@mcp.tool()
def apply_patch(project: str, path: str, old_text: str, new_text: str, replace_all: bool = False, expected_sha256: str = "") -> dict:
    """Safely replace exact text in a file. Ambiguous matches are rejected unless replace_all is true."""
    return _call("apply_patch", {"project": project, "path": path, "old_text": old_text, "new_text": new_text, "replace_all": replace_all, "expected_sha256": expected_sha256})


@mcp.tool()
def create_directory(project: str, path: str, parents: bool = True) -> dict:
    """Create a directory inside an allowlisted project root."""
    return _call("create_directory", {"project": project, "path": path, "parents": parents})


@mcp.tool()
def move_file(project: str, path: str, destination: str) -> dict:
    """Move a file or directory to another relative path inside the same project root."""
    return _call("move_file", {"project": project, "path": path, "destination": destination})


@mcp.tool()
def rename_file(project: str, path: str, new_name: str) -> dict:
    """Rename a file or directory without moving it to another parent."""
    return _call("rename_file", {"project": project, "path": path, "new_name": new_name})


@mcp.tool()
def git_status(project: str) -> dict:
    """Return read-only Git working tree status for a project root."""
    return _call("git_status", {"project": project})


@mcp.tool()
def git_diff(project: str, path: str = ".") -> dict:
    """Return a bounded read-only Git diff for the whole project or one relative path."""
    return _call("git_diff", {"project": project, "path": path})


@mcp.tool()
def delete_path(project: str, path: str, recursive: bool = False) -> dict:
    """Delete a path only when BRIDGE_ALLOW_DELETE is explicitly enabled."""
    return _call("delete_path", {"project": project, "path": path, "recursive": recursive})


@mcp.tool()
def run_command(project: str, command: list[str], cwd: str = ".", timeout_seconds: int = 120) -> dict:
    """Run an allowlisted executable without a shell. Disabled unless BRIDGE_ALLOW_COMMAND is explicitly enabled."""
    return _call("run_command", {"project": project, "command": command, "cwd": cwd, "timeout_seconds": timeout_seconds})


@mcp.tool()
def list_files(project: str, path: str = ".") -> dict:
    """Compatibility alias for list_directory."""
    return _call("list_directory", {"project": project, "path": path})


@mcp.tool()
def read_text(project: str, path: str, start_line: int = 1, line_count: int = 400) -> dict:
    """Compatibility alias for read_file."""
    return _call("read_file", {"project": project, "path": path, "start_line": start_line, "line_count": line_count})


@mcp.tool()
def pe_info(project: str, path: str) -> dict:
    """Parse PE metadata from an executable, DLL, or runtime image."""
    return _call("pe_info", {"project": project, "path": path})


@mcp.tool()
def pe_sections(project: str, path: str) -> dict:
    """List PE sections with RVA, VA, virtual size, and raw mapping."""
    return _call("pe_sections", {"project": project, "path": path})


@mcp.tool()
def va_to_offset(project: str, path: str, va: str, mode: str = "auto") -> dict:
    """Map a virtual address like 0x00545180 to a byte offset."""
    return _call("va_to_offset", {"project": project, "path": path, "va": va, "mode": mode})


@mcp.tool()
def read_va(project: str, path: str, va: str, length: int = 256, mode: str = "auto") -> dict:
    """Read bounded bytes from a PE virtual address."""
    return _call("read_va", {"project": project, "path": path, "va": va, "length": length, "mode": mode})


@mcp.tool()
def find_bytes(project: str, path: str, signature: str, limit: int = 100) -> dict:
    """Search a binary for a hex signature with ?? wildcards."""
    return _call("find_bytes", {"project": project, "path": path, "signature": signature, "limit": limit})


@mcp.tool()
def strings(project: str, path: str, min_length: int = 5, limit: int = 500) -> dict:
    """Extract bounded printable ASCII strings from a local binary."""
    return _call("strings", {"project": project, "path": path, "min_length": min_length, "limit": limit})


@mcp.tool()
def disassemble(project: str, path: str, va: str, length: int = 512, max_instructions: int = 80, mode: str = "auto") -> dict:
    """Disassemble bounded x86 code around a virtual address."""
    return _call("disassemble", {"project": project, "path": path, "va": va, "length": length, "max_instructions": max_instructions, "mode": mode})
