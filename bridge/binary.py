from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Iterator

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

from .core import BridgeError


def open_pe(path: Path) -> pefile.PE:
    try:
        return pefile.PE(str(path), fast_load=False)
    except pefile.PEFormatError as exc:
        raise BridgeError(f"Invalid PE file: {exc}") from exc


def pe_info(path: Path) -> dict:
    pe = open_pe(path)
    image_base = int(pe.OPTIONAL_HEADER.ImageBase)
    entry_rva = int(pe.OPTIONAL_HEADER.AddressOfEntryPoint)

    return {
        "machine": f"0x{int(pe.FILE_HEADER.Machine):04X}",
        "sections": int(pe.FILE_HEADER.NumberOfSections),
        "timestamp": int(pe.FILE_HEADER.TimeDateStamp),
        "image_base": f"0x{image_base:08X}",
        "entry_point_rva": f"0x{entry_rva:08X}",
        "entry_point_va": f"0x{image_base + entry_rva:08X}",
        "size_of_image": int(pe.OPTIONAL_HEADER.SizeOfImage),
        "size_of_headers": int(pe.OPTIONAL_HEADER.SizeOfHeaders),
    }


def pe_sections(path: Path) -> dict:
    pe = open_pe(path)
    image_base = int(pe.OPTIONAL_HEADER.ImageBase)
    sections = []

    for section in pe.sections:
        name = section.Name.rstrip(b"\0").decode("ascii", "replace")

        sections.append(
            {
                "name": name,
                "rva": f"0x{int(section.VirtualAddress):08X}",
                "va": f"0x{image_base + int(section.VirtualAddress):08X}",
                "virtual_size": int(section.Misc_VirtualSize),
                "raw_offset": int(section.PointerToRawData),
                "raw_size": int(section.SizeOfRawData),
                "characteristics": f"0x{int(section.Characteristics):08X}",
            }
        )

    return {"sections": sections}


def is_memory_image(path: Path, pe: pefile.PE, mode: str) -> bool:
    if mode not in {"auto", "memory", "file"}:
        raise BridgeError("mode must be auto, memory, or file")

    if mode == "memory":
        return True

    if mode == "file":
        return False

    size_of_image = int(pe.OPTIONAL_HEADER.SizeOfImage)

    return path.suffix.lower() == ".bin" and path.stat().st_size >= size_of_image


def va_to_offset(path: Path, va: int, mode: str = "auto") -> tuple[int, str]:
    pe = open_pe(path)
    image_base = int(pe.OPTIONAL_HEADER.ImageBase)

    if va < image_base:
        raise BridgeError("VA is below ImageBase")

    rva = va - image_base
    memory = is_memory_image(path, pe, mode)

    if memory:
        return rva, "memory"

    try:
        return int(pe.get_offset_from_rva(rva)), "file"
    except pefile.PEFormatError as exc:
        raise BridgeError(f"VA is not mapped to a file offset: 0x{va:X}") from exc


def read_va(path: Path, va: int, length: int, mode: str = "auto") -> dict:
    offset, resolved_mode = va_to_offset(path, va, mode)

    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(length)

    return {
        "va": f"0x{va:08X}",
        "offset": offset,
        "mode": resolved_mode,
        "returned_length": len(data),
        "hex": data.hex(" "),
        "base64": base64.b64encode(data).decode("ascii"),
    }


def disassemble(
    path: Path,
    va: int,
    length: int,
    max_instructions: int,
    mode: str = "auto",
) -> dict:
    offset, resolved_mode = va_to_offset(path, va, mode)

    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(length)

    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    instructions = []

    for instruction in decoder.disasm(data, va):
        instructions.append(
            {
                "address": f"0x{instruction.address:08X}",
                "bytes": bytes(instruction.bytes).hex(" "),
                "mnemonic": instruction.mnemonic,
                "op_str": instruction.op_str,
            }
        )

        if len(instructions) >= max_instructions:
            break

    return {
        "va": f"0x{va:08X}",
        "offset": offset,
        "mode": resolved_mode,
        "instructions": instructions,
    }


def parse_signature(signature: str) -> tuple[bytes, bytes]:
    parts = signature.strip().split()

    if not parts:
        raise BridgeError("Empty signature")

    values = bytearray()
    masks = bytearray()

    for part in parts:
        if part in {"?", "??"}:
            values.append(0)
            masks.append(0)
        elif re.fullmatch(r"[0-9A-Fa-f]{2}", part):
            values.append(int(part, 16))
            masks.append(0xFF)
        else:
            raise BridgeError(f"Invalid signature token: {part}")

    return bytes(values), bytes(masks)


def _find_signature(data: bytes, values: bytes, masks: bytes) -> Iterator[int]:
    width = len(values)

    if len(data) < width:
        return

    for offset in range(0, len(data) - width + 1):
        matched = True

        for index in range(width):
            if masks[index] and data[offset + index] != values[index]:
                matched = False
                break

        if matched:
            yield offset


def find_bytes(path: Path, signature: str, limit: int) -> dict:
    values, masks = parse_signature(signature)
    data = path.read_bytes()
    offsets = []

    for offset in _find_signature(data, values, masks):
        offsets.append(offset)

        if len(offsets) >= limit:
            break

    return {
        "count": len(offsets),
        "offsets": offsets,
        "truncated": len(offsets) >= limit,
    }


def strings(path: Path, min_length: int, limit: int) -> dict:
    data = path.read_bytes()
    pattern = re.compile(rb"[ -~]{" + str(min_length).encode("ascii") + rb",}")
    items = []

    for match in pattern.finditer(data):
        items.append(
            {
                "offset": match.start(),
                "text": match.group(0)[:1000].decode("ascii", "replace"),
            }
        )

        if len(items) >= limit:
            break

    return {
        "count": len(items),
        "strings": items,
        "truncated": len(items) >= limit,
    }
