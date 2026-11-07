"""Lanternfall's save format, written and read the way the game does.

    magic "LNTN" | version u16 | player name (varint length + UTF-8) | payload length u32 | CRC-32 u32 | payload

All integers are little-endian. The payload is masked: byte i is xor the player's name bytes, repeated. The
CRC-32 is of the payload before masking. The plaintext payload is

    level u16 | playtime seconds u32 | gold u32 | zone u8 | lifetime gold u32 | records | end record

and a record is type u8 | length u16 | value. An item record's value is a varint-length name and a u16 quantity.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

MAGIC = b"LNTN"
VERSION = 3
GOLD_CAP = 999_999
ITEM, QUEST, COSMETIC, END = 0x01, 0x02, 0x07, 0xFF
FIXED = struct.Struct("<HIIBI")


@dataclass
class Save:
    player: str
    level: int
    playtime_seconds: int
    gold: int
    zone: int
    lifetime_gold: int
    records: list[tuple[int, bytes]] = field(default_factory=list)
    version: int = VERSION


def varint(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append(value & 0x7F | 0x80)
        value >>= 7
    return bytes(out + bytes([value]))


def read_varint(data: bytes, position: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        byte = data[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            break
        shift += 7
    if varint(value) != data[position - (shift // 7 + 1) : position]:
        raise ValueError("a varint is not in its shortest form")
    return value, position


def item_value(name: str, quantity: int) -> bytes:
    raw = name.encode("utf-8")
    return varint(len(raw)) + raw + struct.pack("<H", quantity)


def item_of(value: bytes) -> tuple[str, int]:
    length, position = read_varint(value, 0)
    name = value[position : position + length].decode("utf-8")
    if len(value) != position + length + 2:
        raise ValueError("an item record does not end after its quantity")
    return name, struct.unpack_from("<H", value, position + length)[0]


def mask(data: bytes, player: str) -> bytes:
    key = player.encode("utf-8")
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def payload_of(save: Save) -> bytes:
    body = FIXED.pack(save.level, save.playtime_seconds, save.gold, save.zone, save.lifetime_gold)
    for kind, value in [*save.records, (END, b"")]:
        body += struct.pack("<BH", kind, len(value)) + value
    return body


def encode(save: Save) -> bytes:
    payload = payload_of(save)
    name = save.player.encode("utf-8")
    head = MAGIC + struct.pack("<H", save.version) + varint(len(name)) + name
    return head + struct.pack("<II", len(payload), zlib.crc32(payload)) + mask(payload, save.player)


def decode(data: bytes) -> tuple[Save, bool]:
    """The save in ``data``, and whether its stored CRC-32 matches its payload; a malformed file raises."""
    try:
        return read(data)
    except (struct.error, IndexError, UnicodeDecodeError) as error:
        raise ValueError(f"malformed save file: {error}") from error


def read(data: bytes) -> tuple[Save, bool]:
    if data[:4] != MAGIC:
        raise ValueError("not a Lanternfall save: the magic is missing")
    (version,) = struct.unpack_from("<H", data, 4)
    length, position = read_varint(data, 6)
    player = data[position : position + length].decode("utf-8")
    position += length
    size, stored = struct.unpack_from("<II", data, position)
    position += 8
    masked = data[position:]
    if not player or len(masked) != size:
        raise ValueError("the player name is empty or the payload length is wrong")
    payload = mask(masked, player)
    level, playtime, gold, zone, lifetime = FIXED.unpack_from(payload, 0)
    records, at = [], FIXED.size
    while True:
        kind, count = struct.unpack_from("<BH", payload, at)
        at += 3
        if kind == END:
            break
        if at + count > len(payload):
            raise ValueError("a record runs past the payload")
        records.append((kind, payload[at : at + count]))
        at += count
    if at != len(payload) or count != 0:
        raise ValueError("the payload does not end at the end record")
    return Save(player, level, playtime, gold, zone, lifetime, records, version), zlib.crc32(payload) == stored
