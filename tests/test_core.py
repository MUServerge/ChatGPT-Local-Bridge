from pathlib import Path

import pytest

from bridge.binary import parse_signature
from bridge.core import BridgeError, RootRegistry, execute


def registry(tmp_path: Path) -> RootRegistry:
    root = tmp_path / "project"
    root.mkdir()
    return RootRegistry(
        projects={"p": root},
        max_read_bytes=4096,
        max_text_bytes=4096,
        audit_log=tmp_path / "audit.log",
    )


def test_root_escape_is_rejected(tmp_path: Path):
    reg = registry(tmp_path)

    with pytest.raises(BridgeError):
        reg.resolve("p", "..")


def test_signature_parser():
    values, masks = parse_signature("8B ?? FF 15")

    assert values == bytes([0x8B, 0x00, 0xFF, 0x15])
    assert masks == bytes([0xFF, 0x00, 0xFF, 0xFF])


def test_read_range_is_bounded(tmp_path: Path):
    reg = registry(tmp_path)
    path = reg.root("p") / "data.bin"
    path.write_bytes(b"abcdef")

    result = execute(
        reg,
        "read_range",
        {
            "project": "p",
            "path": "data.bin",
            "offset": 2,
            "length": 3,
        },
    )

    assert result["returned_length"] == 3
    assert result["offset"] == 2


def test_search_text(tmp_path: Path):
    reg = registry(tmp_path)
    path = reg.root("p") / "a.cpp"
    path.write_text("alpha\nNeedle here\nomega\n", encoding="utf-8")

    result = execute(
        reg,
        "search_text",
        {
            "project": "p",
            "path": ".",
            "pattern": "*.cpp",
            "query": "needle",
        },
    )

    assert result["count"] == 1
    assert result["results"][0]["line"] == 2
