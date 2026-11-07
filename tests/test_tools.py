from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

import pytest

from contract import (
    CrcInput,
    EditInput,
    Folder,
    InspectInput,
    ListInput,
    ReadHexInput,
    WriteHexInput,
    XorInput,
)
from plugin import crc32_hex, inspect_save, list_saves, original_save, read_hex, write_hex, xor_hex
from plugin.savefile import GOLD_CAP, decode, encode
from plugin.saves import SAVES

GOLDEN = {
    1: "f1a82e3dbd746f4def0f9dc78459fb4e034c470f81272e353ddc5ca58aee316a",
    2: "a1463f6321f652eb4fd1f1a749d025393477d2ffd825e572d30fbb6878baedab",
    3: "76cde8146de612bd5f29184d90e22cebde0dd9b976d20d282f87c840720d0730",
    4: "3ac98da71ff716877490f7ef08f0ddfed19634a24d927bb343ef769ee28255a2",
    5: "a183ad2feb7b56ce649269e89ad5c60aad019055814b058eafab8b1fbd79be1e",
}


def test_the_five_saves_are_byte_for_byte_reproducible(tmp_path: Path) -> None:
    listed = list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    assert [f.path for f in listed.files] == [f"saves/slot{n}.sav" for n in range(1, 6)]
    assert {int(f.path[10]): f.sha256 for f in listed.files} == GOLDEN


def test_every_save_round_trips_and_has_a_valid_checksum() -> None:
    for slot, save in SAVES.items():
        decoded, checksum_ok = decode(encode(save))
        assert decoded == save and checksum_ok, slot
        assert save.gold <= GOLD_CAP


def test_the_traps_are_in_the_data() -> None:
    assert any(k == 0x01 and b"Ember Key" in v for k, v in SAVES[2].records)  # already holds one
    assert SAVES[3].gold == GOLD_CAP and len(encode(SAVES[3])) > 200  # at the cap; a long name
    assert SAVES[4].gold == SAVES[4].lifetime_gold and SAVES[4].records == []  # ambiguous gold; empty
    assert len(SAVES[5].player.encode()) != len(SAVES[5].player) and SAVES[5].lifetime_gold > 1_000_000
    assert any(k not in (0x01, 0x02, 0x07) for k, _ in SAVES[5].records)  # an unknown record type


def test_inspect_prints_what_the_game_would(tmp_path: Path) -> None:
    list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    shown = inspect_save(InspectInput(path="saves/slot2.sav"), tmp_path)
    assert (shown.player, shown.level, shown.gold, shown.lifetime_gold) == ("Bram", 14, 48_200, 120_450)
    assert [(i.name, i.quantity) for i in shown.items] == [("Ember Key", 1), ("Healing Salve", 5), ("Rope", 2)]
    assert shown.other_records == ["type 0x07: 3 bytes"] and shown.checksum_ok is True


def test_inspect_reports_a_bad_checksum_and_refuses_garbage(tmp_path: Path) -> None:
    list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    data = bytearray((tmp_path / "saves/slot1.sav").read_bytes())
    data[-5] ^= 0x01
    write_hex(WriteHexInput(path="edited/x.sav", data_hex=bytes(data).hex()), tmp_path)
    assert inspect_save(InspectInput(path="edited/x.sav"), tmp_path).checksum_ok is False
    write_hex(WriteHexInput(path="edited/junk.sav", data_hex="00" * 30), tmp_path)
    with pytest.raises(ValueError, match="magic"):
        inspect_save(InspectInput(path="edited/junk.sav"), tmp_path)
    write_hex(WriteHexInput(path="edited/short.sav", data_hex=bytes(data[:30]).hex()), tmp_path)
    with pytest.raises(ValueError):
        inspect_save(InspectInput(path="edited/short.sav"), tmp_path)


def test_byte_tools_are_exact(tmp_path: Path) -> None:
    list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    data = (tmp_path / "saves/slot1.sav").read_bytes()
    window = read_hex(ReadHexInput(path="saves/slot1.sav", offset=2, length=10), tmp_path)
    assert window.data_hex == data[2:12].hex() and window.total_size == len(data)
    assert crc32_hex(CrcInput(data_hex="313233343536373839"), tmp_path).crc32 == 0xCBF43926  # the CRC-32 check value
    assert crc32_hex(CrcInput(data_hex=data.hex()), tmp_path).crc32 == zlib.crc32(data)
    assert xor_hex(XorInput(data_hex="00ff10", key_hex="0f"), tmp_path).data_hex == "0ff01f"
    assert xor_hex(XorInput(data_hex="0102030405", key_hex="a0b0"), tmp_path).data_hex == "a1b2a3b4a5"


@pytest.mark.parametrize(
    ("offset", "length"), [(-1, 4), (0, 0), (0, 2049), (0, 10_000), (len(encode(SAVES[1])) - 1, 2)]
)
def test_read_hex_refuses_ranges_outside_the_file(tmp_path: Path, offset: int, length: int) -> None:
    list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    with pytest.raises(ValueError, match="offset and length"):
        read_hex(ReadHexInput(path="saves/slot1.sav", offset=offset, length=length), tmp_path)


@pytest.mark.parametrize("data_hex", ["", "abc", "zz", "ab cd", "0xab"])
def test_hex_must_be_strict(tmp_path: Path, data_hex: str) -> None:
    with pytest.raises(ValueError, match="hex"):
        crc32_hex(CrcInput(data_hex=data_hex), tmp_path)
    with pytest.raises(ValueError, match="hex"):
        xor_hex(XorInput(data_hex="00", key_hex=data_hex), tmp_path)


@pytest.mark.parametrize(
    "path", ["saves/slot1.sav", "../outside.sav", "edited/../saves/slot1.sav", "/etc/x.sav", "edited/a/b.sav", "edited/x.txt", "x.sav"]
)
def test_write_hex_stays_in_the_edited_folder(tmp_path: Path, path: str) -> None:
    list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    before = hashlib.sha256((tmp_path / "saves/slot1.sav").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="path must be"):
        write_hex(WriteHexInput(path=path, data_hex="00"), tmp_path)
    assert hashlib.sha256((tmp_path / "saves/slot1.sav").read_bytes()).hexdigest() == before
    assert not (tmp_path.parent / "outside.sav").exists()


def test_reading_a_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inspect_save(InspectInput(path="saves/slot1.sav"), tmp_path)
    with pytest.raises(FileNotFoundError):
        read_hex(ReadHexInput(path="edited/none.sav", offset=0, length=1), tmp_path)


def test_original_save_describes_the_generated_file(tmp_path: Path) -> None:
    listed = {f.path: f.sha256 for f in list_saves(ListInput(folder=Folder.SAVES), tmp_path).files}
    for slot in range(1, 6):
        reference = original_save(EditInput(slot=slot), tmp_path)
        assert reference.sha256 == listed[f"saves/slot{slot}.sav"]
    with pytest.raises(ValueError, match="slot"):
        original_save(EditInput(slot=6), tmp_path)


def test_listing_edited_before_any_write_is_empty(tmp_path: Path) -> None:
    assert list_saves(ListInput(folder=Folder.EDITED), tmp_path).files == []
