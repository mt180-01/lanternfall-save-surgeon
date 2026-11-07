from .checks import result
from .lanternfall import GOLD_CAP, ITEM, SaveError, item_of


def verify_input(value):
    if not 1 <= value.slot <= 5:
        return result(False, "slot must be between 1 and 5")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if len(output_value.sha256) != 64 or not 0 <= output_value.gold <= GOLD_CAP:
        return result(False, "the reference needs a SHA-256 and a gold value within the cap")
    try:
        for record in output_value.records:
            value = bytes.fromhex(record.value_hex)
            if not 0 <= record.type <= 254 or (record.type == ITEM and not item_of(value)[0]):
                return result(False, "a reference record is malformed")
    except (ValueError, SaveError):
        return result(False, "a reference record is not valid hexadecimal or a valid item")
    return result(True, "the reference is well formed")
