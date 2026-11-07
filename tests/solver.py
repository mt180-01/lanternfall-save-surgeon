"""A scripted agent: edits a save using only the generic byte tools, with knobs that make it fail in known ways."""

from __future__ import annotations

import struct
from pathlib import Path

from contract import (
    CrcInput,
    EditedOutput,
    Folder,
    ListInput,
    ReadHexInput,
    WriteHexInput,
    XorInput,
)
from plugin import crc32_hex, list_saves, read_hex, write_hex, xor_hex
from plugin.savefile import ITEM, item_of, item_value


def read_all(workspace: Path, slot: int) -> bytes:
    path = f"saves/slot{slot}.sav"
    size = read_hex(ReadHexInput(path=path, offset=0, length=1), workspace).total_size
    return bytes.fromhex(read_hex(ReadHexInput(path=path, offset=0, length=size), workspace).data_hex)


def split(data: bytes) -> tuple[bytes, str, bytes]:
    """(the header up to the payload length, the player's name, the masked payload)."""
    length, at = data[6], 7  # every name here is shorter than 128 bytes
    name = data[at : at + length].decode("utf-8")
    return data[: at + length], name, data[at + length + 8 :]


def plaintext(workspace: Path, name: str, masked: bytes) -> bytes:
    return bytes.fromhex(xor_hex(XorInput(data_hex=masked.hex(), key_hex=name.encode().hex()), workspace).data_hex)


def records_of(payload: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
    fixed, at, records = payload[:15], 15, []
    while payload[at] != 0xFF:
        kind, count = struct.unpack_from("<BH", payload, at)
        records.append((kind, payload[at + 3 : at + 3 + count]))
        at += 3 + count
    return fixed, records


def build(fixed: bytes, records: list[tuple[int, bytes]]) -> bytes:
    return fixed + b"".join(struct.pack("<BH", kind, len(value)) + value for kind, value in records) + b"\xff\x00\x00"


def solve(
    workspace: Path,
    slot: int,
    *,
    gold: int = 999_999,
    ember: str = "right",
    checksum: str = "right",
    mask: bool = True,
    length: str = "right",
    lifetime: int | None = None,
    drop_unknown: bool = False,
    level: int | None = None,
    trailing: bytes = b"",
    truncate: int = 0,
    path: str | None = None,
    claim_gold: int | None = None,
) -> EditedOutput:
    list_saves(ListInput(folder=Folder.SAVES), workspace)
    header, name, masked = split(read_all(workspace, slot))
    fixed, records = records_of(plaintext(workspace, name, masked))
    level_, playtime, _old_gold, zone, old_lifetime = struct.unpack("<HIIBI", fixed)
    fixed = struct.pack(
        "<HIIBI",
        level if level is not None else level_,
        playtime,
        gold,
        zone,
        old_lifetime if lifetime is None else lifetime,
    )
    held = [(i, item_of(value)[1]) for i, (kind, value) in enumerate(records) if kind == ITEM and item_of(value)[0] == "Ember Key"]
    if ember == "right":
        if held:
            records[held[0][0]] = (ITEM, item_value("Ember Key", held[0][1] + 1))
        else:
            records.append((ITEM, item_value("Ember Key", 1)))
    elif ember == "duplicate":
        records.append((ITEM, item_value("Ember Key", 1)))
    elif ember == "two":
        records.append((ITEM, item_value("Ember Key", held[0][1] + 2 if held else 2)))
    elif ember == "wrong_name":
        records.append((ITEM, item_value("Ember key", 1)))
    if drop_unknown:
        records = [(kind, value) for kind, value in records if kind in (ITEM, 0x02)]
    payload = build(fixed, records)
    crc = crc32_hex(CrcInput(data_hex=payload.hex()), workspace).little_endian_hex
    if checksum == "stale":
        crc = header_crc(read_all(workspace, slot), header)
    stored = bytes.fromhex(xor_hex(XorInput(data_hex=payload.hex(), key_hex=name.encode().hex()), workspace).data_hex)
    size = len(payload) if length == "right" else len(payload) - 1
    data = header + struct.pack("<I", size) + bytes.fromhex(crc) + (stored if mask else payload) + trailing
    data = data[: len(data) - truncate] if truncate else data
    target = path or f"edited/slot{slot}.sav"
    write_hex(WriteHexInput(path=target, data_hex=data.hex()), workspace)
    shown_gold = gold if claim_gold is None else claim_gold
    keys = sum(item_of(v)[1] for k, v in records if k == ITEM and item_of(v)[0] == "Ember Key")
    return EditedOutput(edited_path=target, gold=shown_gold, ember_keys=keys)


def header_crc(original: bytes, header: bytes) -> str:
    """The original file's stored CRC, as hex: a checksum no one recomputed."""
    return original[len(header) + 4 : len(header) + 8].hex()
