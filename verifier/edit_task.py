"""verify_task for edit-lanternfall-save: the edited file parsed by the reference parser and compared field by field."""

import hashlib
from pathlib import Path

from .checks import read_save, result
from .lanternfall import EMBER_KEY, GOLD_CAP, ITEM, SaveError, item_of

NEW_GOLD = 999_999


def check(name, ok, message):
    return {"name": name, "ok": ok, "message": message}


def ember(kind, value):
    """The quantity of an Ember Key record, or None when the record is anything else."""
    if kind != ITEM:
        return None
    try:
        name, quantity = item_of(value)
    except SaveError:
        return None
    return quantity if name == EMBER_KEY else None


def verify_task(arguments, output, reference, workspace):
    expected_path = f"edited/slot{arguments.slot}.sav"
    if output.edited_path != expected_path:
        return result(False, f"the edited save must be {expected_path}, not {output.edited_path!r}", score=0.0)
    try:
        edited = read_save(workspace, expected_path)
    except SaveError as error:
        return result(False, f"{expected_path} is not a readable Lanternfall save: {error}", score=0.0)

    checks = [check("checksum", edited["crc_ok"], "the CRC-32 matches the payload" if edited["crc_ok"] else (
        f"stored CRC-32 {edited['stored_crc']:#010x} but the payload hashes to {edited['computed_crc']:#010x}"
    ))]
    gold = edited["gold"]
    if gold > GOLD_CAP:
        gold_message = f"gold {gold} is over the game's cap of {GOLD_CAP}"
    elif gold != NEW_GOLD:
        gold_message = f"gold is {gold}, not {NEW_GOLD}"
    else:
        gold_message = "current gold is 999999"
    checks.append(check("gold", gold == NEW_GOLD, gold_message))
    lifetime_ok = edited["lifetime_gold"] == reference.lifetime_gold
    checks.append(
        check(
            "lifetime_gold",
            lifetime_ok,
            "lifetime gold is unchanged" if lifetime_ok else (
                f"lifetime gold changed from {reference.lifetime_gold} to {edited['lifetime_gold']}: the wrong gold field was edited"
            ),
        )
    )
    changed = [
        name
        for name, before in (
            ("player", reference.player),
            ("version", reference.version),
            ("level", reference.level),
            ("playtime_seconds", reference.playtime_seconds),
            ("zone", reference.zone),
        )
        if edited[name] != before
    ]
    checks.append(check("header", not changed, "name, version, level, playtime and zone are unchanged" if not changed else f"changed: {', '.join(changed)}"))

    original = [(record.type, bytes.fromhex(record.value_hex)) for record in reference.records]
    others_before = [(kind, value) for kind, value in original if ember(kind, value) is None]
    others_after = [(kind, value) for kind, value in edited["records"] if ember(kind, value) is None]
    checks.append(
        check(
            "other_records",
            others_before == others_after,
            "every other record is byte-identical, in order" if others_before == others_after else (
                f"the other records differ: {len(others_before)} before, {len(others_after)} after"
            ),
        )
    )
    keys_before = sum(ember(kind, value) or 0 for kind, value in original)
    keys_after = [ember(kind, value) for kind, value in edited["records"] if ember(kind, value) is not None]
    keys_ok = keys_after == [keys_before + 1]
    checks.append(
        check(
            "ember_key",
            keys_ok,
            f"one Ember Key record holds {keys_before + 1}" if keys_ok else (
                f"expected one Ember Key record holding {keys_before + 1}, found records holding {keys_after}"
            ),
        )
    )
    claims_ok = output.gold == gold and output.ember_keys == sum(keys_after)
    checks.append(check("claims", claims_ok, "the submitted gold and Ember Keys match the file" if claims_ok else "the submitted gold or ember_keys differs from the file"))
    original_file = Path(workspace) / f"saves/slot{arguments.slot}.sav"
    untouched = original_file.is_file() and hashlib.sha256(original_file.read_bytes()).hexdigest() == reference.sha256
    checks.append(check("original", untouched, "the original save is untouched" if untouched else "the original save is missing or was changed"))

    failed = [item for item in checks if not item["ok"]]
    if not failed:
        return result(True, "gold is 999999, one Ember Key is added, and nothing else changed", checks=checks)
    return result(
        False,
        "; ".join(f"{item['name']}: {item['message']}" for item in failed),
        score=(len(checks) - len(failed)) / len(checks),
        checks=checks,
    )
