from __future__ import annotations

import hashlib
from pathlib import Path

from contract import EditInput, OriginalOutput, Record
from plugin.savefile import encode
from plugin.saves import SAVES


def original_save(given: EditInput, workspace: Path) -> OriginalOutput:
    if given.slot not in SAVES:
        raise ValueError("slot must be between 1 and 5")
    save = SAVES[given.slot]
    return OriginalOutput(
        sha256=hashlib.sha256(encode(save)).hexdigest(),
        player=save.player,
        version=save.version,
        level=save.level,
        playtime_seconds=save.playtime_seconds,
        zone=save.zone,
        gold=save.gold,
        lifetime_gold=save.lifetime_gold,
        records=[Record(type=kind, value_hex=value.hex()) for kind, value in save.records],
    )
