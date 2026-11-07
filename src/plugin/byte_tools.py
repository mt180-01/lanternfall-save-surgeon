"""Generic byte helpers: none of them knows the save format."""

from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

from contract import (
    CrcInput,
    CrcOutput,
    Folder,
    ReadHexInput,
    ReadHexOutput,
    WriteHexInput,
    WriteHexOutput,
    XorInput,
    XorOutput,
)
from plugin.files import parse_hex, resolve

MOST_BYTES = 2048


def read_hex(given: ReadHexInput, workspace: Path) -> ReadHexOutput:
    path = resolve(workspace, given.path, (Folder.SAVES, Folder.EDITED))
    if not path.is_file():
        raise FileNotFoundError(f"{given.path} does not exist")
    data = path.read_bytes()
    if given.offset < 0 or not 1 <= given.length <= MOST_BYTES or given.offset + given.length > len(data):
        raise ValueError(f"offset and length must stay inside the file's {len(data)} bytes, at most {MOST_BYTES} at once")
    return ReadHexOutput(
        path=given.path,
        offset=given.offset,
        total_size=len(data),
        data_hex=data[given.offset : given.offset + given.length].hex(),
    )


def crc32_hex(given: CrcInput, workspace: Path) -> CrcOutput:
    crc = zlib.crc32(parse_hex(given.data_hex))
    return CrcOutput(crc32=crc, little_endian_hex=crc.to_bytes(4, "little").hex())


def xor_hex(given: XorInput, workspace: Path) -> XorOutput:
    data, key = parse_hex(given.data_hex), parse_hex(given.key_hex)
    return XorOutput(data_hex=bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data)).hex())


def write_hex(given: WriteHexInput, workspace: Path) -> WriteHexOutput:
    path = resolve(workspace, given.path, (Folder.EDITED,))
    data = parse_hex(given.data_hex)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(data)
    return WriteHexOutput(path=given.path, size=len(data), sha256=hashlib.sha256(data).hexdigest())
