from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query

load_dotenv()

ROOT_TEXT = os.getenv("BRIDGE_ROOT", "").strip()
TOKEN = os.getenv("BRIDGE_TOKEN", "").strip()
MAX_READ_BYTES = int(os.getenv("BRIDGE_MAX_READ_BYTES", "4194304"))
AUDIT_LOG = Path(os.getenv("BRIDGE_AUDIT_LOG", "bridge-audit.log"))

if not ROOT_TEXT:
    raise RuntimeError("BRIDGE_ROOT is required")

ROOT = Path(ROOT_TEXT).expanduser().resolve()

if not ROOT.exists() or not ROOT.is_dir():
    raise RuntimeError(f"BRIDGE_ROOT does not exist or is not a directory: {ROOT}")

if not TOKEN or TOKEN == "change-me":
    raise RuntimeError("BRIDGE_TOKEN must be set to a non-default value")

if MAX_READ_BYTES < 1 or MAX_READ_BYTES > 64 * 1024 * 1024:
    raise RuntimeError("BRIDGE_MAX_READ_BYTES must be between 1 byte and 64 MiB")

app = FastAPI(
    title="ChatGPT Local Bridge",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)


def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def resolve_path(relative_path: str) -> Path:
    if not relative_path:
        relative_path = "."

    requested = Path(relative_path)
    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")

    candidate = (ROOT / requested).resolve()

    try:
        common = os.path.commonpath([str(ROOT), str(candidate)])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    if os.path.normcase(common) != os.path.normcase(str(ROOT)):
        raise HTTPException(status_code=403, detail="Path escapes the allowlisted root")

    return candidate


def relative_display(path: Path) -> str:
    try:
        value = path.relative_to(ROOT)
        text = str(value)
        return "." if text == "." else text
    except ValueError:
        return "<outside-root>"


def audit(action: str, path: Path, extra: dict | None = None) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "path": relative_display(path),
    }

    if extra:
        record.update(extra)

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "path": relative_display(path),
        "name": path.name,
        "type": "directory" if path.is_dir() else "file",
        "size": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def iter_tree(root: Path) -> Iterator[Path]:
    stack = [root]

    while stack:
        current = stack.pop()

        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            continue

        entries.sort(key=lambda item: item.name.lower(), reverse=True)

        for entry in entries:
            try:
                resolved = entry.resolve()
                common = os.path.commonpath([str(ROOT), str(resolved)])
                if os.path.normcase(common) != os.path.normcase(str(ROOT)):
                    continue
            except (OSError, ValueError):
                continue

            if resolved.is_dir():
                stack.append(resolved)
            else:
                yield resolved


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "version": "0.1.0",
        "root_name": ROOT.name,
        "max_read_bytes": MAX_READ_BYTES,
    }


@app.get("/v1/list", dependencies=[Depends(require_token)])
def list_path(path: str = Query(default=".")) -> dict:
    target = resolve_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    try:
        items = [file_info(item.resolve()) for item in target.iterdir()]
    except (PermissionError, OSError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    items.sort(key=lambda item: (item["type"] != "directory", item["name"].lower()))
    audit("list", target, {"count": len(items)})

    return {
        "path": relative_display(target),
        "count": len(items),
        "items": items,
    }


@app.get("/v1/stat", dependencies=[Depends(require_token)])
def stat_path(path: str = Query(..., min_length=1)) -> dict:
    target = resolve_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    result = file_info(target)
    audit("stat", target)
    return result


@app.get("/v1/search", dependencies=[Depends(require_token)])
def search(
    path: str = Query(default="."),
    pattern: str = Query(..., min_length=1, max_length=260),
    limit: int = Query(default=200, ge=1, le=5000),
) -> dict:
    target = resolve_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Search root is not a directory")

    results = []

    for item in iter_tree(target):
        if fnmatch.fnmatch(item.name.lower(), pattern.lower()):
            try:
                results.append(file_info(item))
            except OSError:
                continue

            if len(results) >= limit:
                break

    audit("search", target, {"pattern": pattern, "count": len(results), "limit": limit})

    return {
        "root": relative_display(target),
        "pattern": pattern,
        "count": len(results),
        "limit": limit,
        "items": results,
    }


@app.get("/v1/read-range", dependencies=[Depends(require_token)])
def read_range(
    path: str = Query(..., min_length=1),
    offset: int = Query(default=0, ge=0),
    length: int = Query(..., ge=1),
) -> dict:
    if length > MAX_READ_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Requested range exceeds BRIDGE_MAX_READ_BYTES ({MAX_READ_BYTES})",
        )

    target = resolve_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    size = target.stat().st_size
    if offset > size:
        raise HTTPException(status_code=416, detail="Offset is past end of file")

    with target.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(length)

    audit("read-range", target, {"offset": offset, "requested": length, "returned": len(data)})

    return {
        "path": relative_display(target),
        "file_size": size,
        "offset": offset,
        "requested_length": length,
        "returned_length": len(data),
        "encoding": "base64",
        "sha256": hashlib.sha256(data).hexdigest(),
        "data": base64.b64encode(data).decode("ascii"),
    }


@app.get("/v1/hash", dependencies=[Depends(require_token)])
def hash_file(path: str = Query(..., min_length=1)) -> dict:
    target = resolve_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    sha256 = hashlib.sha256()
    size = 0

    with target.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            sha256.update(chunk)
            size += len(chunk)

    audit("hash", target, {"size": size})

    return {
        "path": relative_display(target),
        "size": size,
        "sha256": sha256.hexdigest(),
    }
