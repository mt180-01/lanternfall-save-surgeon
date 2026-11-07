"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LIST_SAVES = "list_saves"
    INSPECT_SAVE = "inspect_save"
    READ_HEX = "read_hex"
    CRC32_HEX = "crc32_hex"
    XOR_HEX = "xor_hex"
    WRITE_HEX = "write_hex"
    ORIGINAL_SAVE = "original_save"


class Task(Enum):
    EDIT_SAVE = "edit-lanternfall-save"


class Folder(Enum):
    SAVES = "saves"
    EDITED = "edited"


PATH = "A save file path relative to the plugin workspace, e.g. saves/slot1.sav or edited/slot1.sav"
HEX = "Bytes as hexadecimal text: two digits per byte, no spaces or prefix, e.g. 4c4e544e"
SLOT = "Which of the five saves to edit, 1 to 5: saves/slot<slot>.sav"
ITEM = "An inventory item's name, e.g. Lantern Oil"


@dataclass
class FileInfo(Output):
    path: Annotated[str, "The file's path relative to the plugin workspace"]
    size: Annotated[int, "The file's size in bytes"]
    sha256: Annotated[str, "The SHA-256 of the file's bytes"]


@dataclass
class Item(Output):
    name: Annotated[str, ITEM]
    quantity: Annotated[int, "How many the player holds"]


@dataclass
class Record(Output):
    type: Annotated[int, "The record's type byte, 0 to 255"]
    value_hex: Annotated[str, "The record's value bytes as hexadecimal text"]


@dataclass
class ListInput(Output):
    folder: Annotated[Folder, "Which folder to list; the first listing of saves creates the five save files"]


@dataclass
class ListOutput(Output):
    files: Annotated[list[FileInfo], "The .sav files in the folder, by path"]


@dataclass
class InspectInput(Output):
    path: Annotated[str, PATH]


@dataclass
class InspectOutput(Output):
    # What the game's read-only inspect command prints.
    path: Annotated[str, PATH]
    player: Annotated[str, "The player's name"]
    level: Annotated[int, "The character level"]
    gold: Annotated[int, "Current gold: what the player can spend"]
    lifetime_gold: Annotated[int, "Lifetime earnings: all the gold the player has ever earned"]
    items: Annotated[list[Item], "The inventory items, in file order"]
    other_records: Annotated[list[str], "Each inventory record that is not an item, as 'type 0xNN: N bytes'"]
    checksum_ok: Annotated[bool, "Whether the stored checksum matches the file's contents; the game rejects a file that fails"]


@dataclass
class ReadHexInput(Output):
    path: Annotated[str, PATH]
    offset: Annotated[int, "The first byte to read, counting from 0"]
    length: Annotated[int, "How many bytes to read, 1 to 2048; offset + length may not pass the end of the file"]


@dataclass
class ReadHexOutput(Output):
    path: Annotated[str, PATH]
    offset: Annotated[int, "The first byte read"]
    total_size: Annotated[int, "The whole file's size in bytes"]
    data_hex: Annotated[str, HEX]


@dataclass
class CrcInput(Output):
    data_hex: Annotated[str, HEX]


@dataclass
class CrcOutput(Output):
    crc32: Annotated[int, "The standard CRC-32 (IEEE 802.3, as in zlib) of the bytes, as a number"]
    little_endian_hex: Annotated[str, "The same CRC as four bytes in little-endian order, as hexadecimal text"]


@dataclass
class XorInput(Output):
    data_hex: Annotated[str, HEX]
    key_hex: Annotated[str, "The key bytes as hexadecimal text, repeated from its start as often as needed; not empty"]


@dataclass
class XorOutput(Output):
    data_hex: Annotated[str, "Each data byte xor the key byte at the same position, repeating the key"]


@dataclass
class WriteHexInput(Output):
    path: Annotated[str, "A new or existing file in the edited folder, e.g. edited/slot1.sav; the saves folder is read-only"]
    data_hex: Annotated[str, HEX]


@dataclass
class WriteHexOutput(Output):
    path: Annotated[str, PATH]
    size: Annotated[int, "The size written in bytes"]
    sha256: Annotated[str, "The SHA-256 of the bytes written"]


@dataclass
class EditInput(Output):
    slot: Annotated[int, SLOT]


@dataclass
class OriginalOutput(Output):
    sha256: Annotated[str, "The SHA-256 of the original save file"]
    player: Annotated[str, "The player's name"]
    version: Annotated[int, "The file format version"]
    level: Annotated[int, "The character level"]
    playtime_seconds: Annotated[int, "Seconds played"]
    zone: Annotated[int, "The zone id the player is in"]
    gold: Annotated[int, "Current gold"]
    lifetime_gold: Annotated[int, "Lifetime earnings"]
    records: Annotated[list[Record], "Every inventory record, in file order, items included"]


@dataclass
class EditedOutput(Output):
    edited_path: Annotated[str, "The edited save, relative to the plugin workspace: edited/slot<slot>.sav"]
    gold: Annotated[int, "The current gold the edited save holds"]
    ember_keys: Annotated[int, "How many Ember Keys the edited save holds in all"]


TOOLS = {
    Tool.LIST_SAVES: (ListInput, ListOutput),
    Tool.INSPECT_SAVE: (InspectInput, InspectOutput),
    Tool.READ_HEX: (ReadHexInput, ReadHexOutput),
    Tool.CRC32_HEX: (CrcInput, CrcOutput),
    Tool.XOR_HEX: (XorInput, XorOutput),
    Tool.WRITE_HEX: (WriteHexInput, WriteHexOutput),
    Tool.ORIGINAL_SAVE: (EditInput, OriginalOutput),
}
TASKS = {Task.EDIT_SAVE: (EditInput, EditedOutput)}
