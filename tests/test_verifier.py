from __future__ import annotations

import json
import zlib
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import (
    CrcInput,
    EditedOutput,
    EditInput,
    Folder,
    InspectInput,
    ListInput,
    ReadHexInput,
    WriteHexInput,
    XorInput,
)
from plugin import crc32_hex, inspect_save, list_saves, original_save, read_hex, write_hex, xor_hex
from plugin.savefile import encode, payload_of, varint
from plugin.saves import SAVES
from tests.solver import solve
from verifier.lanternfall import SaveError, crc32, parse
from verifier.lanternfall import varint as read_varint

TASK = "edit-lanternfall-save"


def judge(workspace: Path, slot: int, output: EditedOutput):
    reference = original_save(EditInput(slot=slot), workspace)
    reference = build_output(plain_output(reference), type(reference))
    return verifier.verify_task(TASK, EditInput(slot=slot), output, reference, str(workspace))


def failing(verdict) -> list[str]:
    return [check["name"] for check in verdict["details"]["checks"] if not check["ok"]]


@pytest.mark.parametrize("slot", [1, 2, 3, 4, 5])
def test_the_right_edit_passes_in_every_slot(tmp_path: Path, slot: int) -> None:
    verdict = judge(tmp_path, slot, solve(tmp_path, slot))
    assert verdict["valid"] is True and verdict["score"] == 1.0, verdict["message"]
    assert all(check["ok"] for check in verdict["details"]["checks"])


def test_an_existing_ember_key_is_bumped_not_duplicated(tmp_path: Path) -> None:
    assert judge(tmp_path, 2, solve(tmp_path, 2, ember="duplicate"))["valid"] is False
    two = judge(tmp_path, 2, solve(tmp_path, 2, ember="two"))
    assert two["valid"] is False and failing(two) == ["ember_key"]


@pytest.mark.parametrize("slot", [1, 3, 4])
def test_a_missing_or_misnamed_ember_key_fails(tmp_path: Path, slot: int) -> None:
    for ember in ("none", "wrong_name", "duplicate" if slot == 2 else "two"):
        verdict = judge(tmp_path, slot, solve(tmp_path, slot, ember=ember))
        assert verdict["valid"] is False and "ember_key" in failing(verdict), (slot, ember)


def test_a_stale_checksum_fails_even_with_the_right_fields(tmp_path: Path) -> None:
    verdict = judge(tmp_path, 1, solve(tmp_path, 1, checksum="stale"))
    assert verdict["valid"] is False and failing(verdict) == ["checksum"]
    assert 0.8 < verdict["score"] < 1.0 and "payload hashes to" in verdict["message"]


def test_one_million_gold_is_over_the_cap(tmp_path: Path) -> None:
    verdict = judge(tmp_path, 1, solve(tmp_path, 1, gold=1_000_000))
    assert verdict["valid"] is False and failing(verdict) == ["gold"] and "cap" in verdict["message"]


@pytest.mark.parametrize("gold", [0, 999_998, 4_294_967_295])
def test_other_gold_values_fail(tmp_path: Path, gold: int) -> None:
    assert "gold" in failing(judge(tmp_path, 1, solve(tmp_path, 1, gold=gold)))


def test_editing_lifetime_gold_instead_of_current_gold_is_named(tmp_path: Path) -> None:
    verdict = judge(tmp_path, 1, solve(tmp_path, 1, gold=3_800, lifetime=999_999))  # current untouched, lifetime set
    assert failing(verdict) == ["gold", "lifetime_gold"] and "wrong gold field" in verdict["message"]
    both = judge(tmp_path, 1, solve(tmp_path, 1, lifetime=999_999))
    assert failing(both) == ["lifetime_gold"]


def test_equal_gold_fields_in_slot_4_cannot_be_edited_by_value_search(tmp_path: Path) -> None:
    # A byte search for 5400 finds both fields; changing only the first match is right, both is wrong.
    assert judge(tmp_path, 4, solve(tmp_path, 4))["valid"] is True
    assert failing(judge(tmp_path, 4, solve(tmp_path, 4, lifetime=999_999))) == ["lifetime_gold"]


def test_gold_already_at_the_cap_still_needs_the_key(tmp_path: Path) -> None:
    assert judge(tmp_path, 3, solve(tmp_path, 3, ember="none"))["valid"] is False
    assert judge(tmp_path, 3, solve(tmp_path, 3))["valid"] is True


def test_changing_anything_else_fails(tmp_path: Path) -> None:
    assert failing(judge(tmp_path, 1, solve(tmp_path, 1, level=8))) == ["header"]
    unknown = judge(tmp_path, 5, solve(tmp_path, 5, drop_unknown=True))
    assert unknown["valid"] is False and failing(unknown) == ["other_records"]


def test_forgetting_the_mask_or_the_length_makes_the_file_unreadable(tmp_path: Path) -> None:
    for options in ({"mask": False}, {"length": "short"}, {"trailing": b"\x00"}, {"truncate": 6}):
        verdict = judge(tmp_path, 2, solve(tmp_path, 2, **options))
        assert verdict["valid"] is False and verdict["score"] < 1.0, options


def test_a_wrong_path_or_dishonest_claim_is_refused(tmp_path: Path) -> None:
    other = solve(tmp_path, 1, path="edited/other.sav")
    verdict = judge(tmp_path, 1, other)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "edited/slot1.sav" in verdict["message"]
    assert judge(tmp_path, 1, solve(tmp_path, 1, path="edited/slot2.sav"))["valid"] is False
    assert failing(judge(tmp_path, 1, solve(tmp_path, 1, claim_gold=5))) == ["claims"]


def test_no_edit_at_all_is_refused(tmp_path: Path) -> None:
    list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    write_hex(WriteHexInput(path="edited/slot1.sav", data_hex=(tmp_path / "saves/slot1.sav").read_bytes().hex()), tmp_path)
    claim = EditedOutput(edited_path="edited/slot1.sav", gold=999_999, ember_keys=1)
    verdict = judge(tmp_path, 1, claim)
    assert verdict["valid"] is False and {"gold", "ember_key", "claims"} <= set(failing(verdict))


def test_a_missing_or_garbage_file_is_refused(tmp_path: Path) -> None:
    list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    claim = EditedOutput(edited_path="edited/slot1.sav", gold=999_999, ember_keys=1)
    assert "does not exist" in judge(tmp_path, 1, claim)["message"]
    write_hex(WriteHexInput(path="edited/slot1.sav", data_hex="00" * 40), tmp_path)
    assert judge(tmp_path, 1, claim)["score"] == 0.0
    write_hex(WriteHexInput(path="edited/slot1.sav", data_hex="4c4e5454"), tmp_path)
    assert judge(tmp_path, 1, claim)["valid"] is False


def test_a_tampered_original_is_detected(tmp_path: Path) -> None:
    output = solve(tmp_path, 1)
    (tmp_path / "saves/slot1.sav").write_bytes(b"changed")
    verdict = judge(tmp_path, 1, output)
    assert verdict["valid"] is False and failing(verdict) == ["original"]


def test_the_verdict_is_deterministic(tmp_path: Path) -> None:
    output = solve(tmp_path, 3, checksum="stale")
    assert json.dumps(judge(tmp_path, 3, output), sort_keys=True) == json.dumps(judge(tmp_path, 3, output), sort_keys=True)


def test_the_reference_parser_agrees_with_the_games_reader() -> None:
    for slot, save in SAVES.items():
        parsed = parse(encode(save))
        assert parsed["crc_ok"] and parsed["computed_crc"] == zlib.crc32(payload_of(save))
        assert (parsed["player"], parsed["level"], parsed["gold"], parsed["lifetime_gold"]) == (
            save.player, save.level, save.gold, save.lifetime_gold
        ), slot
        assert parsed["records"] == save.records


def test_the_pure_crc_matches_zlib_and_varints_round_trip() -> None:
    for data in (b"", b"123456789", bytes(range(256)) * 9, b"\x00" * 1000):
        assert crc32(data) == zlib.crc32(data)
    for value in (0, 1, 127, 128, 300, 16_383, 16_384, 2**21, 2**32 - 1):
        assert read_varint(varint(value) + b"\x99", 0) == (value, len(varint(value)))
    with pytest.raises(SaveError, match="shortest"):
        read_varint(b"\x80\x00", 0)
    with pytest.raises(SaveError, match="ends inside"):
        read_varint(b"\x80", 0)


def test_tool_verifiers_accept_exact_output_and_refuse_wrong_output(tmp_path: Path) -> None:
    listing = list_saves(ListInput(folder=Folder.SAVES), tmp_path)
    assert verifier.verify_output("list_saves", ListInput(folder=Folder.SAVES), listing, str(tmp_path))["valid"]
    listing.files[0].size += 1
    assert not verifier.verify_output("list_saves", ListInput(folder=Folder.SAVES), listing, str(tmp_path))["valid"]

    call = InspectInput(path="saves/slot5.sav")
    shown = inspect_save(call, tmp_path)
    assert verifier.verify_output("inspect_save", call, shown, str(tmp_path))["valid"]
    shown.gold += 1
    assert "gold" in verifier.verify_output("inspect_save", call, shown, str(tmp_path))["message"]
    assert not verifier.verify_input("inspect_save", InspectInput(path="../saves/slot5.sav"))["valid"]

    window = ReadHexInput(path="saves/slot1.sav", offset=4, length=8)
    got = read_hex(window, tmp_path)
    assert verifier.verify_output("read_hex", window, got, str(tmp_path))["valid"]
    got.data_hex = "00" * 8
    assert not verifier.verify_output("read_hex", window, got, str(tmp_path))["valid"]
    assert not verifier.verify_input("read_hex", ReadHexInput(path="saves/slot1.sav", offset=0, length=4096))["valid"]

    crc = CrcInput(data_hex="313233343536373839")
    made = crc32_hex(crc, tmp_path)
    assert verifier.verify_output("crc32_hex", crc, made, str(tmp_path))["valid"]
    made.crc32 ^= 1
    assert not verifier.verify_output("crc32_hex", crc, made, str(tmp_path))["valid"]
    assert not verifier.verify_input("crc32_hex", CrcInput(data_hex="xyz"))["valid"]

    xor = XorInput(data_hex="0102030405", key_hex="a0b0")
    out = xor_hex(xor, tmp_path)
    assert verifier.verify_output("xor_hex", xor, out, str(tmp_path))["valid"]
    out.data_hex = "00"
    assert not verifier.verify_output("xor_hex", xor, out, str(tmp_path))["valid"]

    write = WriteHexInput(path="edited/a.sav", data_hex="deadbeef")
    done = write_hex(write, tmp_path)
    assert verifier.verify_output("write_hex", write, done, str(tmp_path))["valid"]
    (tmp_path / "edited/a.sav").write_bytes(b"other")
    assert not verifier.verify_output("write_hex", write, done, str(tmp_path))["valid"]
    assert not verifier.verify_input("write_hex", WriteHexInput(path="saves/slot1.sav", data_hex="00"))["valid"]

    reference = original_save(EditInput(slot=2), tmp_path)
    assert verifier.verify_output("original_save", EditInput(slot=2), reference, str(tmp_path))["valid"]
    assert not verifier.verify_input("original_save", EditInput(slot=0))["valid"]


def test_bytes_after_the_end_record_inside_the_payload_are_refused(tmp_path: Path) -> None:
    verdict = judge(tmp_path, 1, solve(tmp_path, 1, padding=b"\x00\x00"))
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "end record" in verdict["message"]
