from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence


class BridgeError(Exception):
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class RootRegistry:
    def __init__(
        self,
        projects: dict[str, Path],
        max_read_bytes: int,
        max_text_bytes: int,
        audit_log: Path,
        allow_write: bool = True,
        allow_delete: bool = False,
        allow_command: bool = False,
        command_allowlist: Sequence[str] | None = None,
        max_command_seconds: int = 120,
        max_command_output_bytes: int = 512 * 1024,
    ):
        if not projects:
            raise BridgeError("At least one project root is required")

        self.projects: dict[str, Path] = {}

        for project, value in projects.items():
            project = str(project).strip()
            if not project:
                raise BridgeError("Project names cannot be empty")

            root = value.expanduser().resolve()
            if not root.exists() or not root.is_dir():
                raise BridgeError(f"Project root does not exist: {project}")

            self.projects[project] = root

        self.max_read_bytes = max_read_bytes
        self.max_text_bytes = max_text_bytes
        self.audit_log = audit_log.expanduser()
        self.allow_write = allow_write
        self.allow_delete = allow_delete
        self.allow_command = allow_command
        self.command_allowlist = {
            item.strip().lower() for item in (command_allowlist or []) if item.strip()
        }
        self.max_command_seconds = max_command_seconds
        self.max_command_output_bytes = max_command_output_bytes

    @classmethod
    def from_env(cls) -> "RootRegistry":
        raw_projects = os.getenv("BRIDGE_PROJECTS_JSON", "").strip()

        if raw_projects:
            try:
                data = json.loads(raw_projects)
            except json.JSONDecodeError as exc:
                raise BridgeError("BRIDGE_PROJECTS_JSON must be valid JSON") from exc

            if not isinstance(data, dict):
                raise BridgeError("BRIDGE_PROJECTS_JSON must be an object")

            projects = {str(key): Path(str(value)) for key, value in data.items()}
        else:
            project_id = os.getenv("BRIDGE_PROJECT_ID", "default").strip() or "default"
            root = os.getenv("BRIDGE_ROOT", "").strip()
            if not root:
                raise BridgeError("BRIDGE_ROOT is required")
            projects = {project_id: Path(root)}

        max_read = int(os.getenv("BRIDGE_MAX_READ_BYTES", "4194304"))
        max_text = int(os.getenv("BRIDGE_MAX_TEXT_BYTES", "1048576"))
        max_command_seconds = int(os.getenv("BRIDGE_MAX_COMMAND_SECONDS", "120"))
        max_command_output = int(os.getenv("BRIDGE_MAX_COMMAND_OUTPUT_BYTES", "524288"))

        if max_read < 1 or max_read > 64 * 1024 * 1024:
            raise BridgeError("BRIDGE_MAX_READ_BYTES must be between 1 byte and 64 MiB")
        if max_text < 1 or max_text > 16 * 1024 * 1024:
            raise BridgeError("BRIDGE_MAX_TEXT_BYTES must be between 1 byte and 16 MiB")
        if max_command_seconds < 1 or max_command_seconds > 3600:
            raise BridgeError("BRIDGE_MAX_COMMAND_SECONDS must be between 1 and 3600")
        if max_command_output < 1024 or max_command_output > 16 * 1024 * 1024:
            raise BridgeError("BRIDGE_MAX_COMMAND_OUTPUT_BYTES must be between 1 KiB and 16 MiB")

        allowlist = [
            item.strip()
            for item in os.getenv("BRIDGE_COMMAND_ALLOWLIST", "").split(",")
            if item.strip()
        ]

        return cls(
            projects=projects,
            max_read_bytes=max_read,
            max_text_bytes=max_text,
            audit_log=Path(os.getenv("BRIDGE_AUDIT_LOG", "bridge-audit.log")),
            allow_write=_env_bool("BRIDGE_ALLOW_WRITE", True),
            allow_delete=_env_bool("BRIDGE_ALLOW_DELETE", False),
            allow_command=_env_bool("BRIDGE_ALLOW_COMMAND", False),
            command_allowlist=allowlist,
            max_command_seconds=max_command_seconds,
            max_command_output_bytes=max_command_output,
        )

    def project_names(self) -> list[str]:
        return sorted(self.projects.keys())

    def root(self, project: str) -> Path:
        if project not in self.projects:
            raise BridgeError(f"Unknown project: {project}")
        return self.projects[project]

    @staticmethod
    def _contained(root: Path, candidate: Path) -> bool:
        try:
            common = os.path.commonpath([str(root), str(candidate)])
        except ValueError:
            return False
        return os.path.normcase(common) == os.path.normcase(str(root))

    def resolve(self, project: str, relative_path: str, *, allow_missing: bool = True) -> Path:
        root = self.root(project)
        requested = Path(relative_path or ".")

        if requested.is_absolute():
            raise BridgeError("Absolute paths are not allowed")

        try:
            candidate = (root / requested).resolve(strict=False)
        except OSError as exc:
            raise BridgeError(f"Unable to resolve path: {exc}") from exc

        if not self._contained(root, candidate):
            raise BridgeError("Path escapes the allowlisted project root")

        if not allow_missing and not candidate.exists():
            raise BridgeError("Path not found")

        return candidate

    def relative(self, project: str, path: Path) -> str:
        resolved = path.resolve(strict=False)
        root = self.root(project)
        if not self._contained(root, resolved):
            raise BridgeError("Path escapes the allowlisted project root")
        value = resolved.relative_to(root)
        text = str(value)
        return "." if text == "." else text

    def audit(self, project: str, action: str, path: str, extra: dict | None = None) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": project,
            "action": action,
            "path": path,
        }
        if extra:
            record.update(extra)

        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def file_info(self, project: str, path: Path) -> dict:
        stat = path.stat()
        return {
            "path": self.relative(project, path),
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }

    def iter_entries(self, project: str, start: Path) -> Iterator[Path]:
        root = self.root(project)
        stack = [start]
        visited_dirs: set[str] = set()

        while stack:
            current = stack.pop()
            current_key = os.path.normcase(str(current.resolve(strict=False)))
            if current_key in visited_dirs:
                continue
            visited_dirs.add(current_key)

            try:
                entries = list(current.iterdir())
            except (OSError, PermissionError):
                continue

            entries.sort(key=lambda item: item.name.lower(), reverse=True)
            for entry in entries:
                try:
                    resolved = entry.resolve(strict=False)
                except OSError:
                    continue
                if not self._contained(root, resolved):
                    continue
                yield resolved
                if resolved.is_dir():
                    stack.append(resolved)

    def iter_files(self, project: str, start: Path) -> Iterator[Path]:
        for item in self.iter_entries(project, start):
            if item.is_file():
                yield item


def _must_exist(path: Path, want_file: bool | None = None) -> None:
    if not path.exists():
        raise BridgeError("Path not found")
    if want_file is True and not path.is_file():
        raise BridgeError("Path is not a file")
    if want_file is False and not path.is_dir():
        raise BridgeError("Path is not a directory")


def _require_write(registry: RootRegistry) -> None:
    if not registry.allow_write:
        raise BridgeError("Write tools are disabled by BRIDGE_ALLOW_WRITE")


def _read_text_file(registry: RootRegistry, project: str, path: Path, start_line: int, line_count: int, encoding: str = "utf-8") -> dict:
    _must_exist(path, want_file=True)
    size = path.stat().st_size
    if size > registry.max_text_bytes:
        raise BridgeError(f"Text file exceeds {registry.max_text_bytes} bytes")

    text = path.read_text(encoding=encoding, errors="replace")
    start_line = max(start_line, 1)
    line_count = min(max(line_count, 1), 5000)
    lines = text.splitlines()
    selected = lines[start_line - 1:start_line - 1 + line_count]

    return {
        "path": registry.relative(project, path),
        "start_line": start_line,
        "returned_lines": len(selected),
        "total_lines": len(lines),
        "text": "\n".join(selected),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _run_process(args: list[str], cwd: Path, timeout: int, output_limit: int) -> dict:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise BridgeError(f"Executable not found: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise BridgeError(f"Command timed out after {timeout} seconds") from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    raw = (stdout + stderr).encode("utf-8", errors="replace")
    truncated = len(raw) > output_limit
    if truncated:
        joined = (stdout + stderr).encode("utf-8", errors="replace")[:output_limit].decode("utf-8", errors="replace")
        stdout = joined
        stderr = ""

    return {
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": truncated,
    }


def execute(registry: RootRegistry, tool: str, args: dict) -> dict:
    if tool == "projects":
        return {"projects": registry.project_names()}

    project = str(args.get("project", "")).strip()
    if not project:
        raise BridgeError("project is required")

    if tool == "health":
        return {
            "ok": True,
            "project": project,
            "root_name": registry.root(project).name,
            "max_read_bytes": registry.max_read_bytes,
            "max_text_bytes": registry.max_text_bytes,
            "capabilities": {
                "write": registry.allow_write,
                "delete": registry.allow_delete,
                "command": registry.allow_command,
                "git_read": True,
            },
        }

    relative_path = str(args.get("path", "."))
    path = registry.resolve(project, relative_path)

    if tool in {"list", "list_directory"}:
        _must_exist(path, want_file=False)
        items = []
        for item in path.iterdir():
            try:
                resolved = item.resolve(strict=False)
            except OSError:
                continue
            if not registry._contained(registry.root(project), resolved):
                continue
            items.append(registry.file_info(project, resolved))
        items.sort(key=lambda item: (item["type"] != "directory", item["name"].lower()))
        registry.audit(project, "list_directory", registry.relative(project, path), {"count": len(items)})
        return {"path": registry.relative(project, path), "count": len(items), "items": items}

    if tool == "directory_tree":
        _must_exist(path, want_file=False)
        max_depth = min(max(int(args.get("max_depth", 4)), 0), 20)
        max_entries = min(max(int(args.get("max_entries", 2000)), 1), 20000)
        entries: list[dict] = []
        root_path = path
        visited_dirs: set[str] = set()

        def walk(current: Path, depth: int) -> None:
            if depth > max_depth or len(entries) >= max_entries:
                return
            current_key = os.path.normcase(str(current.resolve(strict=False)))
            if current_key in visited_dirs:
                return
            visited_dirs.add(current_key)
            try:
                children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except (OSError, PermissionError):
                return
            for child in children:
                if len(entries) >= max_entries:
                    return
                try:
                    resolved = child.resolve(strict=False)
                except OSError:
                    continue
                if not registry._contained(registry.root(project), resolved):
                    continue
                rel_depth = len(resolved.relative_to(root_path).parts)
                info = registry.file_info(project, resolved)
                info["depth"] = rel_depth
                entries.append(info)
                if resolved.is_dir() and rel_depth < max_depth:
                    walk(resolved, depth + 1)

        walk(path, 0)
        registry.audit(project, tool, registry.relative(project, path), {"count": len(entries), "max_depth": max_depth})
        return {"path": registry.relative(project, path), "count": len(entries), "entries": entries, "truncated": len(entries) >= max_entries}

    if tool == "stat":
        _must_exist(path)
        registry.audit(project, tool, registry.relative(project, path))
        return registry.file_info(project, path)

    if tool == "search_files":
        _must_exist(path, want_file=False)
        pattern = str(args.get("pattern", "*"))
        limit = min(max(int(args.get("limit", 200)), 1), 5000)
        items = []
        for item in registry.iter_files(project, path):
            if fnmatch.fnmatch(item.name.lower(), pattern.lower()):
                items.append(registry.file_info(project, item))
                if len(items) >= limit:
                    break
        registry.audit(project, tool, registry.relative(project, path), {"pattern": pattern, "count": len(items)})
        return {"count": len(items), "items": items, "truncated": len(items) >= limit}

    if tool == "search_text":
        _must_exist(path, want_file=False)
        query = str(args.get("query", ""))
        if not query:
            raise BridgeError("query is required")
        pattern = str(args.get("pattern", "*"))
        limit = min(max(int(args.get("limit", 100)), 1), 1000)
        case_sensitive = bool(args.get("case_sensitive", False))
        needle = query if case_sensitive else query.lower()
        results = []

        for item in registry.iter_files(project, path):
            if not fnmatch.fnmatch(item.name.lower(), pattern.lower()):
                continue
            try:
                if item.stat().st_size > registry.max_text_bytes:
                    continue
                text = item.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
                    results.append({"path": registry.relative(project, item), "line": line_number, "text": line[:1000]})
                    if len(results) >= limit:
                        registry.audit(project, tool, registry.relative(project, path), {"query": query, "count": len(results)})
                        return {"count": len(results), "results": results, "truncated": True}

        registry.audit(project, tool, registry.relative(project, path), {"query": query, "count": len(results)})
        return {"count": len(results), "results": results, "truncated": False}

    if tool in {"read_text", "read_file"}:
        result = _read_text_file(
            registry,
            project,
            path,
            int(args.get("start_line", 1)),
            int(args.get("line_count", 400)),
            str(args.get("encoding", "utf-8")),
        )
        registry.audit(project, "read_file", registry.relative(project, path), {"start_line": result["start_line"], "line_count": result["returned_lines"]})
        return result

    if tool == "read_multiple_files":
        raw_paths = args.get("paths", [])
        if not isinstance(raw_paths, list) or not raw_paths:
            raise BridgeError("paths must be a non-empty list")
        if len(raw_paths) > 50:
            raise BridgeError("A maximum of 50 files can be read at once")
        line_count = int(args.get("line_count", 400))
        results = []
        total_bytes = 0
        for raw in raw_paths:
            item = registry.resolve(project, str(raw))
            _must_exist(item, want_file=True)
            size = item.stat().st_size
            total_bytes += size
            if total_bytes > registry.max_text_bytes * 4:
                raise BridgeError("Combined read exceeds the multi-file limit")
            results.append(_read_text_file(registry, project, item, 1, line_count))
        registry.audit(project, tool, ".", {"count": len(results)})
        return {"count": len(results), "files": results}

    if tool == "read_range":
        _must_exist(path, want_file=True)
        offset = max(int(args.get("offset", 0)), 0)
        length = int(args.get("length", 65536))
        if length < 1 or length > registry.max_read_bytes:
            raise BridgeError(f"length must be 1..{registry.max_read_bytes}")
        size = path.stat().st_size
        if offset > size:
            raise BridgeError("Offset is past end of file")
        with path.open("rb") as handle:
            handle.seek(offset)
            data = handle.read(length)
        registry.audit(project, tool, registry.relative(project, path), {"offset": offset, "returned": len(data)})
        return {
            "path": registry.relative(project, path),
            "file_size": size,
            "offset": offset,
            "returned_length": len(data),
            "encoding": "base64",
            "sha256": hashlib.sha256(data).hexdigest(),
            "data": base64.b64encode(data).decode("ascii"),
        }

    if tool in {"hash", "hash_file"}:
        _must_exist(path, want_file=True)
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
        registry.audit(project, "hash_file", registry.relative(project, path), {"size": size})
        return {"path": registry.relative(project, path), "size": size, "sha256": digest.hexdigest()}

    if tool == "write_file":
        _require_write(registry)
        content = args.get("content")
        if not isinstance(content, str):
            raise BridgeError("content must be a string")
        if len(content.encode("utf-8")) > registry.max_text_bytes:
            raise BridgeError(f"Content exceeds {registry.max_text_bytes} bytes")
        expected_sha = str(args.get("expected_sha256", "")).strip().lower()
        if path.exists():
            _must_exist(path, want_file=True)
            if expected_sha:
                current = hashlib.sha256(path.read_bytes()).hexdigest()
                if current != expected_sha:
                    raise BridgeError("File changed since it was read; expected_sha256 does not match")
            created = False
        else:
            created = True
        _atomic_write(path, content, str(args.get("encoding", "utf-8")))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        registry.audit(project, tool, registry.relative(project, path), {"created": created, "size": path.stat().st_size})
        return {"path": registry.relative(project, path), "created": created, "size": path.stat().st_size, "sha256": digest}

    if tool == "apply_patch":
        _require_write(registry)
        _must_exist(path, want_file=True)
        if path.stat().st_size > registry.max_text_bytes:
            raise BridgeError(f"Text file exceeds {registry.max_text_bytes} bytes")
        old_text = args.get("old_text")
        new_text = args.get("new_text")
        if not isinstance(old_text, str) or not isinstance(new_text, str):
            raise BridgeError("old_text and new_text must be strings")
        if not old_text:
            raise BridgeError("old_text cannot be empty")
        original = path.read_text(encoding="utf-8", errors="strict")
        occurrences = original.count(old_text)
        if occurrences == 0:
            raise BridgeError("old_text was not found")
        replace_all = bool(args.get("replace_all", False))
        if occurrences > 1 and not replace_all:
            raise BridgeError(f"old_text appears {occurrences} times; use replace_all=true or provide a more specific patch")
        expected_sha = str(args.get("expected_sha256", "")).strip().lower()
        if expected_sha:
            current = hashlib.sha256(path.read_bytes()).hexdigest()
            if current != expected_sha:
                raise BridgeError("File changed since it was read; expected_sha256 does not match")
        updated = original.replace(old_text, new_text) if replace_all else original.replace(old_text, new_text, 1)
        _atomic_write(path, updated, "utf-8")
        registry.audit(project, tool, registry.relative(project, path), {"replacements": occurrences if replace_all else 1})
        return {"path": registry.relative(project, path), "replacements": occurrences if replace_all else 1, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    if tool == "create_directory":
        _require_write(registry)
        if path.exists() and not path.is_dir():
            raise BridgeError("A file already exists at this path")
        existed = path.exists()
        path.mkdir(parents=bool(args.get("parents", True)), exist_ok=True)
        registry.audit(project, tool, registry.relative(project, path), {"already_existed": existed})
        return {"path": registry.relative(project, path), "created": not existed}

    if tool == "move_file":
        _require_write(registry)
        _must_exist(path)
        destination_raw = str(args.get("destination", "")).strip()
        if not destination_raw:
            raise BridgeError("destination is required")
        destination = registry.resolve(project, destination_raw)
        if destination.exists():
            raise BridgeError("Destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
        registry.audit(project, tool, relative_path, {"destination": registry.relative(project, destination)})
        return {"from": relative_path, "to": registry.relative(project, destination)}

    if tool == "rename_file":
        _require_write(registry)
        _must_exist(path)
        new_name = str(args.get("new_name", "")).strip()
        if not new_name or Path(new_name).name != new_name or new_name in {".", ".."}:
            raise BridgeError("new_name must be a single valid name, not a path")
        destination = registry.resolve(project, str(Path(relative_path).parent / new_name))
        if destination.exists():
            raise BridgeError("Destination already exists")
        path.rename(destination)
        registry.audit(project, tool, relative_path, {"destination": registry.relative(project, destination)})
        return {"from": relative_path, "to": registry.relative(project, destination)}

    if tool == "delete_path":
        _require_write(registry)
        if not registry.allow_delete:
            raise BridgeError("Delete tools are disabled by BRIDGE_ALLOW_DELETE")
        _must_exist(path)
        if path == registry.root(project):
            raise BridgeError("Deleting a project root is never allowed")
        if path.is_dir():
            if not bool(args.get("recursive", False)):
                path.rmdir()
            else:
                shutil.rmtree(path)
        else:
            path.unlink()
        registry.audit(project, tool, relative_path)
        return {"deleted": relative_path}

    if tool in {"git_status", "git_diff"}:
        root = registry.root(project)
        git_dir = root / ".git"
        if not git_dir.exists():
            raise BridgeError("Project root is not a Git repository")
        if tool == "git_status":
            proc_args = ["git", "-C", str(root), "status", "--short", "--branch"]
        else:
            proc_args = ["git", "-C", str(root), "diff", "--no-ext-diff", "--"]
            requested = str(args.get("path", "")).strip()
            if requested and requested != ".":
                target = registry.resolve(project, requested)
                proc_args.append(registry.relative(project, target))
        result = _run_process(proc_args, root, min(registry.max_command_seconds, 60), registry.max_command_output_bytes)
        registry.audit(project, tool, str(args.get("path", ".")), {"returncode": result["returncode"]})
        return result

    if tool == "run_command":
        if not registry.allow_command:
            raise BridgeError("Command execution is disabled by BRIDGE_ALLOW_COMMAND")
        raw_command = args.get("command")
        if not isinstance(raw_command, list) or not raw_command or not all(isinstance(x, str) and x for x in raw_command):
            raise BridgeError("command must be a non-empty list of strings")
        executable = Path(raw_command[0]).name.lower()
        if executable.endswith(".exe"):
            executable = executable[:-4]
        allowed = {item[:-4] if item.endswith(".exe") else item for item in registry.command_allowlist}
        if not allowed or executable not in allowed:
            raise BridgeError(f"Executable is not allowlisted: {raw_command[0]}")
        cwd = registry.resolve(project, str(args.get("cwd", ".")))
        _must_exist(cwd, want_file=False)
        timeout = min(max(int(args.get("timeout_seconds", registry.max_command_seconds)), 1), registry.max_command_seconds)
        result = _run_process(list(raw_command), cwd, timeout, registry.max_command_output_bytes)
        registry.audit(project, tool, registry.relative(project, cwd), {"command": raw_command, "returncode": result["returncode"]})
        return result

    if tool in {"pe_info", "pe_sections", "va_to_offset", "read_va", "find_bytes", "strings", "disassemble"}:
        _must_exist(path, want_file=True)
        from . import binary

        if tool == "pe_info":
            result = binary.pe_info(path)
        elif tool == "pe_sections":
            result = binary.pe_sections(path)
        elif tool == "va_to_offset":
            va = int(str(args.get("va", "0")), 0)
            offset, mode = binary.va_to_offset(path, va, str(args.get("mode", "auto")))
            result = {"va": f"0x{va:08X}", "offset": offset, "mode": mode}
        elif tool == "read_va":
            va = int(str(args.get("va", "0")), 0)
            length = int(args.get("length", 256))
            if length < 1 or length > registry.max_read_bytes:
                raise BridgeError(f"length must be 1..{registry.max_read_bytes}")
            result = binary.read_va(path, va, length, str(args.get("mode", "auto")))
        elif tool == "find_bytes":
            limit = min(max(int(args.get("limit", 100)), 1), 1000)
            result = binary.find_bytes(path, str(args.get("signature", "")), limit)
        elif tool == "strings":
            min_length = min(max(int(args.get("min_length", 5)), 3), 128)
            limit = min(max(int(args.get("limit", 500)), 1), 5000)
            result = binary.strings(path, min_length, limit)
        else:
            va = int(str(args.get("va", "0")), 0)
            length = int(args.get("length", 512))
            max_instructions = min(max(int(args.get("max_instructions", 80)), 1), 500)
            if length < 1 or length > registry.max_read_bytes:
                raise BridgeError(f"length must be 1..{registry.max_read_bytes}")
            result = binary.disassemble(path, va, length, max_instructions, str(args.get("mode", "auto")))

        registry.audit(project, tool, registry.relative(project, path), {"args": {key: value for key, value in args.items() if key != "project"}})
        return {"path": registry.relative(project, path), **result}

    raise BridgeError(f"Unknown tool: {tool}")
