import os
import subprocess
from pathlib import Path

import pytest

from bridge.binary import parse_signature
from bridge.core import BridgeError, RootRegistry, execute


def registry(tmp_path: Path, **overrides) -> RootRegistry:
    root = tmp_path / "project"
    root.mkdir()
    options = {
        "projects": {"p": root},
        "max_read_bytes": 4096,
        "max_text_bytes": 4096,
        "audit_log": tmp_path / "audit.log",
        "allow_write": True,
        "allow_delete": False,
        "allow_command": False,
    }
    options.update(overrides)
    return RootRegistry(**options)


def test_root_escape_is_rejected(tmp_path: Path):
    reg = registry(tmp_path)
    with pytest.raises(BridgeError):
        reg.resolve("p", "..")


def test_absolute_path_is_rejected(tmp_path: Path):
    reg = registry(tmp_path)
    with pytest.raises(BridgeError):
        reg.resolve("p", str(tmp_path.resolve()))


def test_symlink_escape_is_rejected(tmp_path: Path):
    reg = registry(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = reg.root("p") / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this runner")
    with pytest.raises(BridgeError):
        reg.resolve("p", "escape/secret.txt")


def test_signature_parser():
    values, masks = parse_signature("8B ?? FF 15")
    assert values == bytes([0x8B, 0x00, 0xFF, 0x15])
    assert masks == bytes([0xFF, 0x00, 0xFF, 0xFF])


def test_read_range_is_bounded(tmp_path: Path):
    reg = registry(tmp_path)
    path = reg.root("p") / "data.bin"
    path.write_bytes(b"abcdef")
    result = execute(reg, "read_range", {"project": "p", "path": "data.bin", "offset": 2, "length": 3})
    assert result["returned_length"] == 3
    assert result["offset"] == 2


def test_search_text(tmp_path: Path):
    reg = registry(tmp_path)
    path = reg.root("p") / "a.cpp"
    path.write_text("alpha\nNeedle here\nomega\n", encoding="utf-8")
    result = execute(reg, "search_text", {"project": "p", "path": ".", "pattern": "*.cpp", "query": "needle"})
    assert result["count"] == 1
    assert result["results"][0]["line"] == 2


def test_write_read_patch_and_hash(tmp_path: Path):
    reg = registry(tmp_path)
    write = execute(reg, "write_file", {"project": "p", "path": "src/a.txt", "content": "hello world\n"})
    assert write["created"] is True

    read = execute(reg, "read_file", {"project": "p", "path": "src/a.txt"})
    assert read["text"] == "hello world"
    assert read["sha256"] == write["sha256"]

    patched = execute(reg, "apply_patch", {"project": "p", "path": "src/a.txt", "old_text": "world", "new_text": "bridge", "expected_sha256": write["sha256"]})
    assert patched["replacements"] == 1
    assert (reg.root("p") / "src/a.txt").read_text(encoding="utf-8") == "hello bridge\n"


def test_patch_rejects_ambiguous_match(tmp_path: Path):
    reg = registry(tmp_path)
    path = reg.root("p") / "a.txt"
    path.write_text("x x", encoding="utf-8")
    with pytest.raises(BridgeError):
        execute(reg, "apply_patch", {"project": "p", "path": "a.txt", "old_text": "x", "new_text": "y"})


def test_expected_sha_prevents_stale_write(tmp_path: Path):
    reg = registry(tmp_path)
    path = reg.root("p") / "a.txt"
    path.write_text("new", encoding="utf-8")
    with pytest.raises(BridgeError):
        execute(reg, "write_file", {"project": "p", "path": "a.txt", "content": "overwrite", "expected_sha256": "0" * 64})


def test_directory_tree_move_and_rename(tmp_path: Path):
    reg = registry(tmp_path)
    execute(reg, "create_directory", {"project": "p", "path": "src/nested"})
    execute(reg, "write_file", {"project": "p", "path": "src/nested/a.txt", "content": "a"})
    execute(reg, "rename_file", {"project": "p", "path": "src/nested/a.txt", "new_name": "b.txt"})
    execute(reg, "move_file", {"project": "p", "path": "src/nested/b.txt", "destination": "b.txt"})
    tree = execute(reg, "directory_tree", {"project": "p", "path": ".", "max_depth": 4})
    assert any(item["path"] == "b.txt" for item in tree["entries"])


def test_read_multiple_files(tmp_path: Path):
    reg = registry(tmp_path)
    for name in ("a.txt", "b.txt"):
        (reg.root("p") / name).write_text(name, encoding="utf-8")
    result = execute(reg, "read_multiple_files", {"project": "p", "paths": ["a.txt", "b.txt"]})
    assert result["count"] == 2


def test_delete_is_disabled_by_default(tmp_path: Path):
    reg = registry(tmp_path)
    (reg.root("p") / "a.txt").write_text("x", encoding="utf-8")
    with pytest.raises(BridgeError):
        execute(reg, "delete_path", {"project": "p", "path": "a.txt"})


def test_command_is_disabled_by_default(tmp_path: Path):
    reg = registry(tmp_path)
    with pytest.raises(BridgeError):
        execute(reg, "run_command", {"project": "p", "command": ["python", "--version"]})


def test_command_requires_allowlisted_executable(tmp_path: Path):
    reg = registry(tmp_path, allow_command=True, command_allowlist=["definitely-not-this"])
    with pytest.raises(BridgeError):
        execute(reg, "run_command", {"project": "p", "command": ["python", "--version"]})


def test_git_status_and_diff(tmp_path: Path):
    reg = registry(tmp_path)
    root = reg.root("p")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "bridge@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Bridge Test"], cwd=root, check=True)
    (root / "tracked.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)
    (root / "tracked.txt").write_text("after\n", encoding="utf-8")

    status = execute(reg, "git_status", {"project": "p"})
    diff = execute(reg, "git_diff", {"project": "p"})
    assert "tracked.txt" in status["stdout"]
    assert "-before" in diff["stdout"]
    assert "+after" in diff["stdout"]
