from __future__ import annotations

from pathlib import Path

from contract import Folder, InspectInput, InspectOutput, Item
from plugin.files import resolve
from plugin.savefile import ITEM, decode, item_of


def inspect_save(given: InspectInput, workspace: Path) -> InspectOutput:
    path = resolve(workspace, given.path, (Folder.SAVES, Folder.EDITED))
    if not path.is_file():
        raise FileNotFoundError(f"{given.path} does not exist")
    save, checksum_ok = decode(path.read_bytes())
    return InspectOutput(
        path=given.path,
        player=save.player,
        level=save.level,
        gold=save.gold,
        lifetime_gold=save.lifetime_gold,
        items=[Item(name=name, quantity=quantity) for name, quantity in (item_of(v) for k, v in save.records if k == ITEM)],
        other_records=[f"type 0x{kind:02x}: {len(value)} bytes" for kind, value in save.records if kind != ITEM],
        checksum_ok=checksum_ok,
    )
