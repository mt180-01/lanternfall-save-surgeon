"""The five saves a player has, fixed so every run starts from the same files."""

from __future__ import annotations

import struct

from plugin.savefile import COSMETIC, ITEM, QUEST, Save, item_value

LEDGER = (
    "The Lantern-Keeper's Complete Ledger of Wicks, Oils, Mirrors, Chimneys and Other Small Lights"
    " Left Burning Through the Long Night at Lanternfall"
)


def item(name: str, quantity: int) -> tuple[int, bytes]:
    return ITEM, item_value(name, quantity)


def quest(number: int, state: int) -> tuple[int, bytes]:
    return QUEST, struct.pack("<HB", number, state)


SAVES = {
    # No Ember Key yet.
    1: Save("Ilsa Venn", 7, 9_240, 1_250, 2, 3_800, [item("Lantern Oil", 3), item("Iron Sword", 1), quest(5, 1)]),
    # Already holds one Ember Key: adding one makes two, in one record.
    2: Save(
        "Bram", 14, 41_000, 48_200, 4, 120_450,
        [item("Ember Key", 1), item("Healing Salve", 5), (COSMETIC, bytes([200, 120, 40])), item("Rope", 2)],
    ),
    # Gold is already at the cap; one item's name needs a two-byte varint length.
    3: Save("Tamsin Holloway", 22, 188_000, 999_999, 6, 2_400_000, [item(LEDGER, 1), item("Brass Lantern", 1), quest(9, 2)]),
    # Gold and lifetime gold hold the same number, and the inventory is empty.
    4: Save("Quillon", 3, 1_900, 5_400, 1, 5_400, []),
    # A multi-byte name makes a multi-byte mask; unknown record types must be left alone.
    5: Save(
        "Zoë Aldersen", 30, 260_000, 700, 8, 5_000_000,
        [item("Cartographer's Compass", 1), (0x09, bytes([1, 2, 3, 4, 5])), (COSMETIC, bytes([9, 9, 9])), item("Rope", 40)],
    ),
}
