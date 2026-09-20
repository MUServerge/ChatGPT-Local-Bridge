from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


class BridgeError(Exception):
    pass


class RootRegistry:
    def __init__(self, projects: dict[str, Path], max_read_bytes: int, max_text_bytes: int, audit_log: Path):
        if not projects:
            raise BridgeError("At least one project root is required")

        self.projects: dict[str, Path] = {}

        for project, value in projects.items():
            root = value.expanduser().resolve()

            if not root.exists() or not root.is_dir():
                raise BridgeError(f"Project root does not exist: {project}")

            self.projects[project] = root

        self.max_read_bytes = max_read_bytes
        self.max_text_bytes = max_text_bytes
        self.audit_log = audit_log

    @classmethod
    def from_env(cls) -> "RootRegistry":
        raw_projects = os.getenv("BRIDGE_PROJECTS_JSON", "").strip()

        if raw_projects:
            data = json.loads(raw_projects)

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

        if max_read < 1 or max_read > 64 * 1024 * 1024:
            raise BridgeError("BRIDGE_MAX_READ_BYTES must be between 1 byte and 64 MiB")

        if max_text < 1 or max_text > 16 * 1024 * 1024:
            raise BridgeError("BRIDGE_MAX_TEXT_BYTES must be between 1 byte and 16 MiB")

        return cls(
            projects=projects,
            max_read_bytes=max_read,
            max_text_bytes=max_text,
            audit_log=Path(os.getenv("BRIDGE_AUDIT_LOG", "bridge-audit.log")),
        )

    def project_names(self) -> list[str]:
        return sorted(self.projects.keys())

    def root(self, project: str) -> Path:
        if project not in self.projects:
            raise BridgeError(f"Unknown project: {project}")

        return self.projects[project]

    def resolve(self, project: str, relative_path: str) -> Path:
        root = self.root(project)
        requested = Path(relative_path or ".")

        if requested.is_absolute():
            raise BridgeError("Absolute paths are not allowed")

        candidate = (root / requested).resolve()

        try:
            common = os.path.commonpath([str(root), str(candidate)])
        except ValueError as exc:
            raise BridgeError("Invalid path") from exc

        if os.path.normcase(common) != os.path.normcase(str(root)):
            raise BridgeError("Path escapes the allowlisted project root")

        return candidate

    def relative(self, project: str, path: Path) -> str:
        value = path.relative_to(self.root(project))
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

    def iter_files(self, project: str, start: Path) -> Iterator[Path]:
        root = self.root(project)
        stack = [start]

        while stack:
            current = stack.pop()

            try:
                entries = list(current.iterdir())
            except (OSError, PermissionError):
                continue

            entries.sort(key=lambda item: item.name.lower(), reverse=True)

            for entry in entries:
                try:
                    resolved = entry.resolve()
                    common = os.path.commonpath([str(root), str(resolved)])

                    if os.path.normcase(common) != os.path.normcase(str(root)):
                        continue
                except (OSError, ValueError):
                    continue

                if resolved.is_dir():
                    stack.append(resolved)
                elif resolved.is_file():
                    yield resolved


def _must_exist(path: Path, want_file: bool | None = None) -> None:
    if not path.exists():
        raise BridgeError("Path not found")

    if want_file is True and not path.is_file():
        raise BridgeError("Path is not a file")

    if want_file is False and not path.is_dir():
        raise BridgeError("Path is not a directory")


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
        }

    relative_path = str(args.get("path", "."))
    path = registry.resolve(project, relative_path)

    if tool == "list":
        _must_exist(path, want_file=False)

        items = [registry.file_info(project, item.resolve()) for item in path.iterdir()]
        items.sort(key=lambda item: (item["type"] != "directory", item["name"].lower()))

        registry.audit(project, tool, registry.relative(project, path), {"count": len(items)})

        return {
            "path": registry.relative(project, path),
            "count": len(items),
            "items": items,
        }

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

        registry.audit(
            project,
            tool,
            registry.relative(project, path),
            {"pattern": pattern, "count": len(items)},
        )

        return {"count": len(items), "items": items}

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
                    results.append(
                        {
                            "path": registry.relative(project, item),
                            "line": line_number,
                            "text": line[:1000],
                        }
                    )

                    if len(results) >= limit:
                        registry.audit(
                            project,
                            tool,
                            registry.relative(project, path),
                            {"query": query, "count": len(results)},
                        )

                        return {
                            "count": len(results),
                            "results": results,
                            "truncated": True,
                        }

        registry.audit(
            project,
            tool,
            registry.relative(project, path),
            {"query": query, "count": len(results)},
        )

        return {
            "count": len(results),
            "results": results,
            "truncated": False,
        }

    if tool == "read_text":
        _must_exist(path, want_file=True)

        if path.stat().st_size > registry.max_text_bytes:
            raise BridgeError(f"Text file exceeds {registry.max_text_bytes} bytes")

        text = path.read_text(
            encoding=str(args.get("encoding", "utf-8")),
            errors="replace",
        )

        start_line = max(int(args.get("start_line", 1)), 1)
        line_count = min(max(int(args.get("line_count", 400)), 1), 5000)
        lines = text.splitlines()
        selected = lines[start_line - 1:start_line - 1 + line_count]

        registry.audit(
            project,
            tool,
            registry.relative(project, path),
            {"start_line": start_line, "line_count": len(selected)},
        )

        return {
            "path": registry.relative(project, path),
            "start_line": start_line,
            "returned_lines": len(selected),
            "total_lines": len(lines),
            "text": "\n".join(selected),
        }

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

        registry.audit(
            project,
            tool,
            registry.relative(project, path),
            {"offset": offset, "returned": len(data)},
        )

        return {
            "path": registry.relative(project, path),
            "file_size": size,
            "offset": offset,
            "returned_length": len(data),
            "encoding": "base64",
            "sha256": hashlib.sha256(data).hexdigest(),
            "data": base64.b64encode(data).decode("ascii"),
        }

    if tool == "hash":
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

        registry.audit(
            project,
            tool,
            registry.relative(project, path),
            {"size": size},
        )

        return {
            "path": registry.relative(project, path),
            "size": size,
            "sha256": digest.hexdigest(),
        }

    raise BridgeError(f"Unknown tool: {tool}")
